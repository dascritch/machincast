"""Scénarios d'un blanc dans un sonore à l'antenne (https://github.com/dascritch/machincast/issues/122).

Les premiers jouent de vrais fichiers, faits de morceaux de sinusoïde à un niveau crête donné (tests.sons
.generer_silences), sur la sortie factice, au plus vite. Les suivants tournent sur le moteur simulé : la voie du sonore
nommé imite un blanc, constaté une fois la durée d'un blanc écoulée, comme la voie GStreamer
(machincast.lecture.moteur.Voie.blanc). Les étapes partagées de la diffusion sont dans tests/etapes_diffusion.py.
"""

import contextlib
import dataclasses
import re
import time
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.configuration import BlancAntenne, Configuration
from machincast.horloge import HorlogeFixe
from machincast.lecture import __main__ as module_lecture
from machincast.lecture import diffusion
from machincast.lecture.moteur import Blanc, Voie, VoieLecture
from machincast.lecture.simulation import MoteurSimule, VoieSimulee
from tests.base_test import configuration_test
from tests.etapes_diffusion import Banc, heure, passages, secondes, sonore
from tests.sons import generer_silences

scenarios("blanc_dans_un_sonore.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
FREQUENCE = 8000
"""Fréquence d'échantillonnage des fichiers des scénarios : basse, pour qu'ils s'écrivent vite."""
ATTENTE_MAXIMALE = 10.0
MARGE_DE_POSITION = 0.15
"""Secondes d'écart admises sur la position d'un blanc : une mesure du niveau dure 0,1 seconde."""
MARGE_DE_NIVEAU = 1.0
"""dB d'écart admis sur un niveau moyen : la sinusoïde à -80 dB n'a que quelques pas de quantification."""


@pytest.fixture
def fichiers() -> dict[str, Path]:
	return {}


@pytest.fixture
def lecture() -> dict[str, object]:
	"""La voie jouée par le scénario, et les blancs qu'elle a présentés."""
	return {}


def amplitude(niveau: str) -> float:
	"""Amplitude crête d'un niveau en dB ; 0 pour un silence numérique."""
	if niveau == "silence numérique":
		return 0.0
	return float(10 ** (secondes(niveau) / 20))


@given(parsers.re(r"le fichier « (?P<nom>[^»]+) » : (?P<morceaux>.+)"))
def fichier_par_morceaux(tmp_path: Path, fichiers: dict[str, Path], nom: str, morceaux: str) -> None:
	"""« 1 seconde à -20 dB, 3 secondes de silence numérique, puis 1 seconde à -20 dB »."""
	trouves = re.findall(r"([\d,]+) secondes? (?:à (-[\d,]+) dB|de (silence numérique))", morceaux)
	assert trouves, morceaux
	plan = tuple((secondes(duree), amplitude((niveau) or (silence))) for duree, niveau, silence in trouves)
	fichiers[nom] = generer_silences(tmp_path / f"{nom}.flac", plan, FREQUENCE)


@when(
	parsers.re(
		r"une (?P<sorte>voie|voie muette) joue le fichier « (?P<nom>[^»]+) »(?: à partir de (?P<decalage>[\d,]+)"
		r" seconde du fichier,)? jusqu'au bout, au plus vite"
	)
)
def jouer(
	banc: Banc, fichiers: dict[str, Path], lecture: dict[str, object], sorte: str, nom: str, decalage: str | None
) -> None:
	depart = None
	if decalage is not None:
		depart = timedelta(seconds=secondes(decalage))
	voie = Voie(
		fichiers[nom],
		configuration_test().audio,
		None,
		temps_reel=False,
		muette=sorte == "voie muette",
		decalage=depart,
		blanc=banc.blanc,
	)
	blancs: list[Blanc] = []
	try:
		voie.demarrer()
		limite = time.monotonic() + ATTENTE_MAXIMALE
		while (voie.etat == "en cours") and (time.monotonic() < limite):
			time.sleep(0.01)
			voie.traiter()
			while (blanc := voie.blanc()) is not None:
				blancs.append(blanc)
		while (blanc := voie.blanc()) is not None:
			blancs.append(blanc)
	finally:
		voie.fermer()
	assert voie.etat == "finie", (voie.etat, voie.erreur)
	lecture["voie"], lecture["blancs"] = voie, blancs


def blancs_de(lecture: dict[str, object]) -> list[Blanc]:
	blancs = lecture["blancs"]
	assert isinstance(blancs, list)
	return blancs


@then(parsers.re(r"la voie a présenté (?P<nombre>\d+) blancs?$"))
def blancs_presentes(lecture: dict[str, object], nombre: str) -> None:
	assert len(blancs_de(lecture)) == int(nombre), blancs_de(lecture)


@then(
	parsers.re(
		r"le blanc n°(?P<rang>\d+) commence à (?P<position>[\d,]+) secondes? du fichier, (?:au niveau moyen de"
		r" (?P<niveau>-[\d,]+) dB|en (?P<silence>silence numérique))"
	)
)
def blanc_n(lecture: dict[str, object], rang: str, position: str, niveau: str | None, silence: str | None) -> None:
	blanc = blancs_de(lecture)[int(rang) - 1]
	assert abs(blanc.position.total_seconds() - secondes(position)) <= MARGE_DE_POSITION, blanc
	if silence is not None:
		assert blanc.niveau is None, blanc
	else:
		assert (blanc.niveau is not None) and (abs(blanc.niveau - secondes(str(niveau))) <= MARGE_DE_NIVEAU), blanc


@then(parsers.re(r"la voie (?P<quoi>a été entendue|n'est plus entendue)"))
def entendue(lecture: dict[str, object], quoi: str) -> None:
	voie = lecture["voie"]
	assert isinstance(voie, Voie)
	assert voie.entendue() is (quoi == "a été entendue")


# ─── Diffusion, sur le moteur simulé ───────────────────────


class VoieABlanc(VoieSimulee):
	"""Une voie simulée qui présente un blanc à une position donnée, constaté une fois la durée d'un blanc écoulée ;
	son son revient à retour, s'il est donné."""

	def __init__(
		self,
		horloge: HorlogeFixe,
		duree: timedelta | None,
		blanc: Blanc,
		retour: timedelta | None,
	) -> None:
		super().__init__(horloge, duree)
		self._blanc: Blanc | None = blanc
		self._debut = blanc.position
		self._retour = retour

	def blanc(self) -> Blanc | None:
		blanc = self._blanc
		if (blanc is None) or (self.position() < blanc.position + blanc.duree):
			return None
		self._blanc = None
		return blanc

	def entendue(self) -> bool:
		"""Pas de son du début du blanc au retour du son."""
		position = self.position()
		return not ((self._debut <= position) and ((self._retour is None) or (position < self._retour)))


@pytest.fixture
def ouvertures() -> dict[str, int]:
	"""Les voies ouvertes par le moteur simulé, par sonore nommé."""
	return {}


@given(
	parsers.re(
		r"le sonore « (?P<nom>[^»]+) » présente un blanc à (?P<position>\d+) secondes de son début, au niveau moyen de"
		r" (?P<niveau>-[\d,]+) dB(?:, et son son revient à (?P<retour>\d+) secondes)?"
	)
)
def sonore_a_blanc(
	monkeypatch: pytest.MonkeyPatch,
	banc: Banc,
	ouvertures: dict[str, int],
	nom: str,
	position: str,
	niveau: str,
	retour: str | None,
) -> None:
	"""Les fichiers des sonores sont dans un répertoire à leur nom (etapes_diffusion.creer_sonore) ; l'adresse d'un
	stream factice finit par son nom. Seule la première voie du sonore présente le blanc."""
	vrai_jouer = MoteurSimule.jouer
	fin_du_blanc = None
	if retour is not None:
		fin_du_blanc = timedelta(seconds=int(retour))

	def jouer(
		self: MoteurSimule, chemin: Path | str, duree: timedelta | None, *args: object, **options: object
	) -> VoieLecture:
		vise = (Path(str(chemin)).parent.name == nom) or (str(chemin).endswith(f"/{nom}"))
		if not vise:
			return vrai_jouer(self, chemin, duree, *args, **options)  # type: ignore[arg-type]
		ouvertures[nom] = ouvertures.get(nom, 0) + 1
		if ouvertures[nom] > 1:
			return vrai_jouer(self, chemin, duree, *args, **options)  # type: ignore[arg-type]
		assert isinstance(self.horloge, HorlogeFixe)
		blanc = Blanc(timedelta(seconds=int(position)), banc.blanc.duree, secondes(niveau))
		voie = VoieABlanc(self.horloge, duree, blanc, fin_du_blanc)
		self._voies.append(voie)
		return voie

	monkeypatch.setattr(MoteurSimule, "jouer", jouer)


def lignes_du_log(base: Connexion, nature: str) -> list[tuple[str, object, object, object]]:
	lignes = base.execute(
		"SELECT message, horodatage, sonore_id, evenement_id FROM log WHERE nature = %s ORDER BY id", (nature,)
	).fetchall()
	return [
		(str(message), horodatage, sonore_id, evenement_id) for message, horodatage, sonore_id, evenement_id in lignes
	]


@then(parsers.parse("l'incident « {nature} » dit « {texte} »"))
def incident_dit(base_vide: Connexion, nature: str, texte: str) -> None:
	lignes = lignes_du_log(base_vide, nature)
	assert (lignes) and (all(texte in message for message, *_ in lignes)), lignes


@then(parsers.parse("l'incident « {nature} » a été noté au « {instant} », pour le sonore « {nom} » de « {evenement} »"))
def incident_note(base_vide: Connexion, nature: str, instant: str, nom: str, evenement: str) -> None:
	ligne = base_vide.execute("SELECT id FROM evenements WHERE nom_interne = %s", (evenement,)).fetchone()
	assert ligne is not None, evenement
	lignes = [
		(horodatage, sonore_id, evenement_id)
		for _, horodatage, sonore_id, evenement_id in lignes_du_log(base_vide, nature)
	]
	assert lignes == [(heure(instant), sonore(base_vide, nom), ligne[0])], lignes


@then(parsers.parse("le moteur n'a ouvert qu'une voie pour « {nom} »"))
def une_seule_voie(ouvertures: dict[str, int], nom: str) -> None:
	assert ouvertures.get(nom) == 1, ouvertures


@then(parsers.parse("le passage « {nom} » a fini sans incident"))
def fini_sans_incident(base_vide: Connexion, nom: str) -> None:
	trouves = [(fin, sain) for titre, _debut, fin, sain in passages(base_vide) if titre == nom]
	assert (trouves) and (all((fin is not None) and (sain is True) for fin, sain in trouves)), trouves


# ─── Machin lecture ────────────────────────────────────────


@pytest.fixture
def lancement() -> dict[str, object]:
	"""La configuration de Machin lecture, et ce que son moteur et sa diffusion ont reçu."""
	return {}


@given(
	parsers.re(
		r"la configuration des tests, avec un blanc dans un sonore de (?P<duree>[\d,]+) secondes sous"
		r" (?P<seuil>-[\d,]+) dB, qui fait passer au secours"
	)
)
def configuration_avec_blanc(lancement: dict[str, object], duree: str, seuil: str) -> None:
	blanc = BlancAntenne(timedelta(seconds=secondes(duree)), secondes(seuil), True)
	lancement["configuration"] = dataclasses.replace(configuration_test(), blanc_antenne=blanc)


@when("Machin lecture diffuse avec cette configuration, sans base ni sortie audio")
def diffuser(monkeypatch: pytest.MonkeyPatch, lancement: dict[str, object]) -> None:
	"""La base de production n'est jamais jointe : la connexion est remplacée."""

	@contextlib.contextmanager
	def connecter(*_arguments: object) -> Iterator[object]:
		yield object()

	class Moteur:
		def __init__(self, _audio: object, **options: object) -> None:
			lancement["moteur"] = options

		def fermer(self) -> None:
			pass

	def diffusion(*_arguments: object, **options: object) -> object:
		lancement["diffusion"] = options
		return object()

	monkeypatch.setattr(module_lecture, "connecter", connecter)
	monkeypatch.setattr(module_lecture, "MoteurAudio", Moteur)
	monkeypatch.setattr(module_lecture, "Diffusion", diffusion)
	monkeypatch.setattr(module_lecture, "diffuser", lambda _diffusion, _arret: None)
	configuration = lancement["configuration"]
	assert isinstance(configuration, Configuration)
	assert module_lecture.executer_diffusion(configuration) == 0


@then(
	parsers.re(
		r"son moteur mesure un blanc de (?P<duree>[\d,]+) secondes sous (?P<seuil>-[\d,]+) dB, et sa diffusion fait"
		r" passer au secours"
	)
)
def blanc_pris(lancement: dict[str, object], duree: str, seuil: str) -> None:
	attendu = BlancAntenne(timedelta(seconds=secondes(duree)), secondes(seuil), True)
	moteur, diffusion = lancement["moteur"], lancement["diffusion"]
	assert (isinstance(moteur, dict)) and (isinstance(diffusion, dict)), lancement
	assert (moteur["blanc"], diffusion["blanc_antenne"]) == (attendu, attendu)


@then(parsers.parse("un blanc à {position} secondes s'écrit « {texte} »"))
def timecode(position: str, texte: str) -> None:
	assert diffusion._timecode(timedelta(seconds=secondes(position))) == texte
