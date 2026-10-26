"""Étapes partagées des scénarios de la diffusion (https://github.com/dascritch/machincast/issues/88).

Chargé comme greffon pytest par tests/conftest.py : la boucle de diffusion
(https://github.com/dascritch/machincast/issues/88) et les streams (https://github.com/dascritch/machincast/issues/16)
s'en servent. Le banc tient l'horloge, le moteur sur la sortie factice et la diffusion, connectée avec le rôle de
la lecture.
"""

import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, then, when

from machincast.base import Role, connecter
from machincast.configuration import Audio, Crossfades
from machincast.hasard import creer_hasard
from machincast.horloge import HorlogeFixe
from machincast.lecture.analyse import Analyseur
from machincast.lecture.diffusion import Diffusion
from machincast.lecture.etat import SocketEtat
from machincast.lecture.moteur import MoteurAudio, Voie, VoieLecture
from machincast.lecture.simulation import MoteurSimule
from machincast.lecture.sorties import Sorties
from tests.base_test import configuration_test, parametres_base_test
from tests.flux import ServeurDeFlux
from tests.sons import copie_de_test

Connexion = psycopg.Connection[tuple[object, ...]]
PAS_REEL = 0.05
DELAI_RECONNEXION_TEST = timedelta(seconds=0.2)
"""Délai entre deux tentatives de reconnexion d'un stream, raccourci pour les scénarios."""


class MoteurNote(MoteurAudio):
	"""Le moteur audio de la diffusion, qui garde chaque voie jouée, par fichier, même finie."""

	def __init__(self, audio: Audio, temps_reel: bool = True) -> None:
		super().__init__(audio, temps_reel)
		self.jouees: dict[str, Voie] = {}

	def jouer(
		self,
		chemin: Path | str,
		duree: timedelta | None,
		crossfade_debut: timedelta = timedelta(0),
		crossfade_fin: timedelta = timedelta(0),
		muette: bool = False,
		decalage: timedelta | None = None,
		depart: float = 0.0,
		arrivee: float = 0.0,
	) -> Voie:
		voie = super().jouer(chemin, duree, crossfade_debut, crossfade_fin, muette, decalage, depart, arrivee)
		self.jouees[str(chemin)] = voie
		return voie


class MoteurSimuleNote(MoteurSimule):
	"""Le moteur simulé de la simulation, qui garde la montée de chaque sonore joué, par nom de sonore : chaque
	fichier est dans un répertoire au nom de son sonore (creer_sonore)."""

	def __init__(self, horloge: HorlogeFixe) -> None:
		super().__init__(horloge)
		self.montees: dict[str, timedelta] = {}

	def jouer(
		self,
		chemin: Path | str,
		duree: timedelta | None,
		crossfade_debut: timedelta = timedelta(0),
		crossfade_fin: timedelta = timedelta(0),
		muette: bool = False,
		decalage: timedelta | None = None,
		depart: float = 0.0,
		arrivee: float = 0.0,
	) -> VoieLecture:
		self.montees[Path(str(chemin)).parent.name] = crossfade_debut
		return super().jouer(chemin, duree, crossfade_debut, crossfade_fin, muette, decalage, depart, arrivee)


ELEMENTS = {
	"saute au sonore suivant": "sonore",
	"saute après la séquence": "sequence",
	"coupe l'événement par le fil musical": "evenement",
}
"""Interruptions manuelles (https://github.com/dascritch/machincast/issues/228), par leur texte dans les scénarios."""


@dataclass
class Banc:
	horloge: HorlogeFixe | None = None
	diffusion: Diffusion | None = None
	moteur: MoteurNote | None = None
	connexion: Connexion | None = None
	sorties: Sorties | None = None
	"""Modules de sortie de la diffusion ; aucun par défaut."""
	etat: SocketEtat | None = None
	"""Socket d'état de la diffusion ; aucune par défaut."""
	fichiers: dict[str, Path] = field(default_factory=dict)
	crossfades: Crossfades = field(default_factory=Crossfades)
	"""Crossfades de la configuration : sans durée par défaut, sauf si le scénario en donne."""
	analyseur: Analyseur | None = None
	"""Analyse du prochain sonore (https://github.com/dascritch/machincast/issues/181) : aucune par défaut."""
	simule: MoteurSimuleNote | None = None
	"""Moteur simulé, qui suit l'horloge du binaire, quand la diffusion démarre sur lui."""


@pytest.fixture
def banc() -> Iterator[Banc]:
	banc = Banc()
	yield banc
	if banc.etat is not None:
		banc.etat.fermer()
	if banc.moteur is not None:
		banc.moteur.fermer()
	if banc.connexion is not None:
		banc.connexion.close()


def secondes(texte: str) -> float:
	return float(texte.replace(",", "."))


def heure(texte: str) -> datetime:
	return datetime.fromisoformat(texte).astimezone()


def horloge(banc: Banc) -> HorlogeFixe:
	assert banc.horloge is not None
	return banc.horloge


def diffusion(banc: Banc) -> Diffusion:
	assert banc.diffusion is not None
	return banc.diffusion


def sonore(base: Connexion, nom: str) -> int:
	ligne = base.execute("SELECT id FROM sonores WHERE titre = %s", (nom,)).fetchone()
	assert ligne is not None, f"sonore {nom} inconnu"
	return int(str(ligne[0]))


def creer_sonore(banc: Banc, base: Connexion, repertoire: Path, nom: str) -> int:
	dossier = repertoire / nom
	dossier.mkdir()
	fichier = copie_de_test("flac", dossier)
	banc.fichiers[nom] = fichier
	etat = fichier.stat()
	ligne = base.execute(
		"INSERT INTO sonores (type, emplacement, etat, titre, duree, fichier_modifie_le, fichier_taille)"
		" VALUES ('fichier', %s, 'actif', %s, '1 s', %s, %s) RETURNING id",
		(str(fichier), nom, datetime.fromtimestamp(etat.st_mtime, tz=UTC), etat.st_size),
	).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


def evenement(
	banc: Banc,
	base: Connexion,
	repertoire: Path,
	nom: str,
	priorite: str,
	debut: datetime | None,
	fin: datetime | None,
	sonores: list[str],
) -> None:
	cree = base.execute(
		"INSERT INTO evenements (nom_interne, priorite, debut, fin) VALUES (%s, %s, %s, %s) RETURNING id",
		(nom, priorite, debut, fin),
	).fetchone()
	assert cree is not None
	for position, nom_sonore in enumerate(sonores, start=1):
		existant = base.execute("SELECT id FROM sonores WHERE titre = %s", (nom_sonore,)).fetchone()
		if existant is None:
			identifiant = creer_sonore(banc, base, repertoire, nom_sonore)
		else:
			identifiant = int(str(existant[0]))
		base.execute(
			"INSERT INTO evenements_elements (evenement_id, position, sonore_id) VALUES (%s, %s, %s)",
			(cree[0], position, identifiant),
		)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'horloge du binaire au « {instant} »"))
def horloge_au(banc: Banc, instant: str) -> None:
	banc.horloge = HorlogeFixe(heure(instant))


@given(parsers.re(r"le fil musical permanent « (?P<nom>[^»]+) », avec les sonores (?P<liste>.+)"))
def fil(banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, liste: str) -> None:
	noms = [n.strip(" «»") for n in liste.split(",")]
	evenement(banc, base_vide, tmp_path, nom, "fil_musical", None, None, noms)


@given(
	parsers.re(
		r"le fil musical permanent « (?P<nom>[^»]+) », avec la banque (?P<mode>séquentielle|aléatoire)"
		r" « (?P<banque>[^»]+) » des sonores (?P<liste>.+)"
	)
)
def fil_avec_banque(
	banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, mode: str, banque: str, liste: str
) -> None:
	creee = base_vide.execute(
		"INSERT INTO banques (nom_interne, mode) VALUES (%s, %s) RETURNING id",
		(banque, "sequentiel" if mode == "séquentielle" else "aleatoire"),
	).fetchone()
	assert creee is not None
	for position, nom_sonore in enumerate((n.strip(" «»") for n in liste.split(",")), start=1):
		base_vide.execute(
			"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, %s)",
			(creee[0], creer_sonore(banc, base_vide, tmp_path, nom_sonore), position),
		)
	evenement_cree = base_vide.execute(
		"INSERT INTO evenements (nom_interne, priorite) VALUES (%s, 'fil_musical') RETURNING id", (nom,)
	).fetchone()
	assert evenement_cree is not None
	base_vide.execute(
		"INSERT INTO evenements_elements (evenement_id, position, banque_id) VALUES (%s, 1, %s)",
		(evenement_cree[0], creee[0]),
	)


@given(
	parsers.re(
		r"(?P<genre>l'émission|le spécial) « (?P<nom>[^»]+) » de (?P<debut>[\d:]+) à (?P<fin>[\d:]+),"
		r" avec le sonore « (?P<nom_sonore>[^»]+) »"
	)
)
def emission(
	banc: Banc, base_vide: Connexion, tmp_path: Path, genre: str, nom: str, debut: str, fin: str, nom_sonore: str
) -> None:
	evenement(
		banc,
		base_vide,
		tmp_path,
		nom,
		"emission" if genre == "l'émission" else "special",
		heure(f"2026-10-14 {debut}"),
		heure(f"2026-10-14 {fin}"),
		[nom_sonore],
	)


@given(
	parsers.re(
		r"(?P<genre>l'émission|le spécial) « (?P<nom>[^»]+) » de (?P<debut>[\d:]+) à (?P<fin>[\d:]+),"
		r" avec les sonores (?P<liste>.+)"
	)
)
def emission_des_sonores(
	banc: Banc, base_vide: Connexion, tmp_path: Path, genre: str, nom: str, debut: str, fin: str, liste: str
) -> None:
	evenement(
		banc,
		base_vide,
		tmp_path,
		nom,
		"emission" if genre == "l'émission" else "special",
		heure(f"2026-10-14 {debut}"),
		heure(f"2026-10-14 {fin}"),
		[n.strip(" «»") for n in liste.split(",")],
	)


@given(parsers.re(r"l'émission « (?P<nom>[^»]+) » de (?P<debut>[\d:]+) à (?P<fin>[\d:]+), sans élément"))
def emission_vide(banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, debut: str, fin: str) -> None:
	"""Une émission à compléter plus tard (https://github.com/dascritch/machincast/issues/253)."""
	evenement(
		banc, base_vide, tmp_path, nom, "emission", heure(f"2026-10-14 {debut}"), heure(f"2026-10-14 {fin}"), []
	)


@given(
	parsers.re(r"le spécial « (?P<nom>[^»]+) » à partir de (?P<debut>[\d:]+), sans fin, avec les sonores (?P<liste>.+)")
)
def special_sans_fin_des_sonores(
	banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, debut: str, liste: str
) -> None:
	noms = [n.strip(" «»") for n in liste.split(",")]
	evenement(banc, base_vide, tmp_path, nom, "special", heure(f"2026-10-14 {debut}"), None, noms)


@given(parsers.parse("chaque sonore dure {duree:d} secondes"))
def duree_des_sonores(base_vide: Connexion, duree: int) -> None:
	base_vide.execute("UPDATE sonores SET duree = %s", (timedelta(seconds=duree),))


@given(
	parsers.re(
		r"la séquence « (?P<nom>[^»]+) » des sonores « (?P<premier>[^»]+) », « (?P<second>[^»]+) », jouée par le fil"
		r" musical permanent « (?P<fil>[^»]+) », avant le sonore « (?P<apres>[^»]+) »"
	)
)
def sequence_du_fil(
	banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, premier: str, second: str, fil: str, apres: str
) -> None:
	sequence = base_vide.execute("INSERT INTO sequences (nom_interne) VALUES (%s) RETURNING id", (nom,)).fetchone()
	evenement = base_vide.execute(
		"INSERT INTO evenements (nom_interne, priorite) VALUES (%s, 'fil_musical') RETURNING id", (fil,)
	).fetchone()
	assert (sequence is not None) and (evenement is not None)
	for position, nom_sonore in enumerate((premier, second), start=1):
		base_vide.execute(
			"INSERT INTO sequences_elements (sequence_id, position, sonore_id) VALUES (%s, %s, %s)",
			(sequence[0], position, creer_sonore(banc, base_vide, tmp_path, nom_sonore)),
		)
	base_vide.execute(
		"INSERT INTO evenements_elements (evenement_id, position, sequence_id) VALUES (%s, 1, %s)",
		(evenement[0], sequence[0]),
	)
	base_vide.execute(
		"INSERT INTO evenements_elements (evenement_id, position, sonore_id) VALUES (%s, 2, %s)",
		(evenement[0], creer_sonore(banc, base_vide, tmp_path, apres)),
	)


@given(parsers.re(r"le fil musical permanent « (?P<fil>[^»]+) » joue les séquences (?P<liste>.+)"))
def fil_des_sequences(banc: Banc, base_vide: Connexion, tmp_path: Path, fil: str, liste: str) -> None:
	"""« A » des sonores « a1 », « a2 », puis « B » des sonores « b1 » : chaque séquence est un élément du fil."""
	evenement_cree = base_vide.execute(
		"INSERT INTO evenements (nom_interne, priorite) VALUES (%s, 'fil_musical') RETURNING id", (fil,)
	).fetchone()
	assert evenement_cree is not None
	for rang, partie in enumerate(liste.split(", puis "), start=1):
		nom, sonores = partie.split(" des sonores ")
		sequence = base_vide.execute(
			"INSERT INTO sequences (nom_interne) VALUES (%s) RETURNING id", (nom.strip(" «»"),)
		).fetchone()
		assert sequence is not None
		for position, nom_sonore in enumerate((n.strip(" «»") for n in sonores.split(",")), start=1):
			base_vide.execute(
				"INSERT INTO sequences_elements (sequence_id, position, sonore_id) VALUES (%s, %s, %s)",
				(sequence[0], position, creer_sonore(banc, base_vide, tmp_path, nom_sonore)),
			)
		base_vide.execute(
			"INSERT INTO evenements_elements (evenement_id, position, sequence_id) VALUES (%s, %s, %s)",
			(evenement_cree[0], rang, sequence[0]),
		)


@given(
	parsers.re(
		r"le fil musical permanent « (?P<fil>[^»]+) » joue la séquence « (?P<sequence>[^»]+) » des sonores"
		r" (?P<de_la_sequence>.+), puis la banque aléatoire « (?P<banque>[^»]+) » des sonores (?P<de_la_banque>.+)"
	)
)
def fil_sequence_puis_banque(
	banc: Banc,
	base_vide: Connexion,
	tmp_path: Path,
	fil: str,
	sequence: str,
	de_la_sequence: str,
	banque: str,
	de_la_banque: str,
) -> None:
	fil_des_sequences(banc, base_vide, tmp_path, fil, f"« {sequence} » des sonores {de_la_sequence}")
	creee = base_vide.execute(
		"INSERT INTO banques (nom_interne, mode) VALUES (%s, 'aleatoire') RETURNING id", (banque,)
	).fetchone()
	assert creee is not None
	for position, nom_sonore in enumerate((n.strip(" «»") for n in de_la_banque.split(",")), start=1):
		base_vide.execute(
			"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, %s)",
			(creee[0], creer_sonore(banc, base_vide, tmp_path, nom_sonore), position),
		)
	base_vide.execute(
		"INSERT INTO evenements_elements (evenement_id, position, banque_id)"
		" SELECT id, 2, %s FROM evenements WHERE nom_interne = %s",
		(creee[0], fil),
	)


@given(
	parsers.re(
		r"le spécial « (?P<nom>[^»]+) » à partir de (?P<debut>[\d:]+), sans fin,"
		r" avec le sonore « (?P<nom_sonore>[^»]+) »"
	)
)
def special_sans_fin(banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, debut: str, nom_sonore: str) -> None:
	evenement(banc, base_vide, tmp_path, nom, "special", heure(f"2026-10-14 {debut}"), None, [nom_sonore])


@given(parsers.parse("l'événement « {nom} » a pour nom public « {nom_public} », et masque ses sonores"))
def evenement_masque(base_vide: Connexion, nom: str, nom_public: str) -> None:
	base_vide.execute(
		"UPDATE evenements SET nom_public = %s, masquer_metadonnees = true WHERE nom_interne = %s", (nom_public, nom)
	)


@given(parsers.parse("chaque sonore a {duree} seconde de crossfade de début et de fin"))
def crossfades(base_vide: Connexion, duree: str) -> None:
	valeur = timedelta(seconds=secondes(duree))
	base_vide.execute("UPDATE sonores SET crossfade_debut = %s, crossfade_fin = %s", (valeur, valeur))


@given(parsers.re(r"les crossfades de chaque sonore sont (?:de (?P<duree>[\d,]+) seconde|non paramétrés)"))
def crossfades_des_sonores(base_vide: Connexion, duree: str | None) -> None:
	"""Non paramétrés : NULL ; 0 seconde est un crossfade paramétré (https://github.com/dascritch/machincast/issues/145)."""
	valeur = None
	if duree is not None:
		valeur = timedelta(seconds=secondes(duree))
	base_vide.execute("UPDATE sonores SET crossfade_debut = %s, crossfade_fin = %s", (valeur, valeur))


@given(
	parsers.re(
		r"les crossfades par défaut de la configuration sont (?:absents|de (?P<debut>[\d,]+) seconde au début"
		r"(?: et de (?P<fin>[\d,]+) à la fin|, et absent à la fin)"
		r"|absent au début, et de (?P<fin_seule>[\d,]+) à la fin)"
	)
)
def crossfades_par_defaut(banc: Banc, debut: str | None, fin: str | None, fin_seule: str | None) -> None:
	durees: list[timedelta | None] = []
	for valeur in (debut, (fin) or (fin_seule)):
		duree = None
		if valeur is not None:
			duree = timedelta(seconds=secondes(valeur))
		durees.append(duree)
	banc.crossfades = Crossfades(debut=durees[0], fin=durees[1])


REGLES_DE_CROSSFADE = {
	"laisse ses sonores décider, malgré": "sonore",
	"applique à défaut": "a_defaut",
	"impose": "impose",
}
"""La règle de crossfade d'une banque, telle que la disent les scénarios (https://github.com/dascritch/machincast/issues/143)."""


@given(
	parsers.re(
		r"la banque « (?P<nom>[^»]+) » (?P<regle>laisse ses sonores décider, malgré|applique à défaut|impose)"
		r" (?P<duree>[\d,]+) seconde de crossfade de (?P<cote>début|fin)"
	)
)
def crossfade_de_banque(base_vide: Connexion, nom: str, regle: str, duree: str, cote: str) -> None:
	colonne = {"début": "crossfade_debut", "fin": "crossfade_fin"}[cote]
	base_vide.execute(
		f"UPDATE banques SET {colonne}_regle = %s, {colonne} = %s WHERE nom_interne = %s",  # noqa: S608
		(REGLES_DE_CROSSFADE[regle], timedelta(seconds=secondes(duree)), nom),
	)


@given(parsers.re(r"la banque « (?P<nom>[^»]+) », séquentielle, avec les sonores (?P<liste>.+)"))
def banque_des_sonores(base_vide: Connexion, nom: str, liste: str) -> None:
	"""Une banque des sonores déjà en base, sans qu'un événement l'appelle."""
	creee = base_vide.execute(
		"INSERT INTO banques (nom_interne, mode) VALUES (%s, 'sequentiel') RETURNING id", (nom,)
	).fetchone()
	assert creee is not None
	for position, nom_sonore in enumerate((n.strip(" «»") for n in liste.split(",")), start=1):
		base_vide.execute(
			"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, %s)",
			(creee[0], sonore(base_vide, nom_sonore), position),
		)


@given(parsers.parse("chaque sonore a {duree} seconde de crossfade de fin, et aucun de début"))
def crossfade_de_fin(base_vide: Connexion, duree: str) -> None:
	base_vide.execute("UPDATE sonores SET crossfade_fin = %s", (timedelta(seconds=secondes(duree)),))


# ─── Détection de blanc (https://github.com/dascritch/machincast/issues/146) ───


@given(
	parsers.re(
		r"chaque sonore a (?:aucun blanc détecté|(?P<debut>[\d,]+) secondes? de blanc détecté au début"
		r"(?:, et aucun à la fin| et (?P<fin>[\d,]+) à la fin))"
	)
)
def blancs_detectes(base_vide: Connexion, debut: str | None, fin: str | None) -> None:
	"""La fin détectée se compte depuis la fin du fichier ; aucun blanc détecté : NULL."""
	durees: list[timedelta | None] = []
	for valeur in (debut, fin):
		duree = None
		if valeur is not None:
			duree = timedelta(seconds=secondes(valeur))
		durees.append(duree)
	base_vide.execute(
		"UPDATE sonores SET debut_detecte = %s, fin_detectee = %s WHERE type = 'fichier'", (durees[0], durees[1])
	)


@given(parsers.parse("la banque « {nom} » active la détection de blanc"))
def banque_detecte_les_blancs(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("UPDATE banques SET detection_blancs = true WHERE nom_interne = %s", (nom,))


@given(parsers.re(r"le sonore « (?P<nom>[^»]+) » active la détection de blanc$"))
def sonore_detecte_les_blancs(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("UPDATE sonores SET detection_blancs = true WHERE id = %s", (sonore(base_vide, nom),))


@given(
	parsers.re(
		r"le sonore « (?P<nom>[^»]+) » active la détection de blanc, avec (?P<debut>[\d,]+) secondes? de blanc"
		r" détecté au début et (?P<fin>[\d,]+) à la fin"
	)
)
def sonore_rogne(base_vide: Connexion, nom: str, debut: str, fin: str) -> None:
	base_vide.execute(
		"UPDATE sonores SET detection_blancs = true, debut_detecte = %s, fin_detectee = %s WHERE id = %s",
		(timedelta(seconds=secondes(debut)), timedelta(seconds=secondes(fin)), sonore(base_vide, nom)),
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"la diffusion démarre (?P<rythme>au plus vite|en temps réel)"))
def demarrer(banc: Banc, base_vide: Connexion, rythme: str) -> None:
	banc.connexion = connecter(*parametres_base_test(), Role.LECTURE)
	banc.moteur = MoteurNote(configuration_test().audio, temps_reel=rythme == "en temps réel")
	banc.diffusion = Diffusion(
		banc.connexion,
		banc.moteur,
		horloge(banc),
		creer_hasard(0),
		delai_reconnexion=DELAI_RECONNEXION_TEST,
		sorties=banc.sorties,
		etat=banc.etat,
		# À chaque pas, pour que la socket d'état donne la progression du moment.
		publication_minimale=0.0,
		crossfades=banc.crossfades,
		analyseur=banc.analyseur,
	)
	banc.diffusion.demarrer()


@when("la diffusion démarre sur un moteur simulé")
def demarrer_sur_un_moteur_simule(banc: Banc, base_vide: Connexion) -> None:
	"""Le moteur simulé suit l'horloge du binaire : un sonore d'une minute se joue sans attendre."""
	banc.connexion = connecter(*parametres_base_test(), Role.LECTURE)
	banc.simule = MoteurSimuleNote(horloge(banc))
	banc.diffusion = Diffusion(
		banc.connexion,
		banc.simule,
		horloge(banc),
		creer_hasard(0),
		etat=banc.etat,
		crossfades=banc.crossfades,
	)
	banc.diffusion.demarrer()


@when(parsers.re(r"la diffusion avance de (?P<nombre>\d+) secondes?"))
def avancer(banc: Banc, nombre: str) -> None:
	"""Un pas par seconde, sur le moteur simulé."""
	for _ in range(int(nombre)):
		diffusion(banc).pas()
		horloge(banc).avancer(timedelta(seconds=1))


@when(parsers.re(r"je (?P<quoi>saute au sonore suivant|saute après la séquence|coupe l'événement par le fil musical)$"))
def interrompre(banc: Banc, quoi: str) -> None:
	diffusion(banc).interrompre(ELEMENTS[quoi])


@when(parsers.re(r"la diffusion tourne (?P<nombre>\d+) pas d(?:'une|e (?P<duree>[\d,]+)) seconde"))
def tourner(banc: Banc, nombre: str, duree: str | None) -> None:
	ecart = 1.0
	if duree is not None:
		ecart = secondes(duree)
	rythme_reel = (banc.moteur is not None) and (banc.moteur.temps_reel)
	for _ in range(int(nombre)):
		diffusion(banc).pas()
		# En temps réel, la pause suit l'horloge ; au plus vite, la voie finit pendant une courte pause réelle.
		if rythme_reel:
			time.sleep(ecart)
		else:
			attendre_la_fin_des_voies(banc)
		horloge(banc).avancer(timedelta(seconds=ecart))


def attendre_la_fin_des_voies(banc: Banc, delai: float = 5.0) -> None:
	assert banc.moteur is not None
	limite = time.monotonic() + delai
	while (any(v.etat == "en cours" for v in banc.moteur.voies_en_cours())) and (time.monotonic() < limite):
		time.sleep(PAS_REEL / 5)
		for voie in banc.moteur.voies_en_cours():
			voie.traiter()


@when(parsers.parse("la diffusion tourne pendant {duree} seconde en temps réel"))
def tourner_en_temps_reel(banc: Banc, duree: str) -> None:
	fin = time.monotonic() + secondes(duree)
	precedent = time.monotonic()
	while time.monotonic() < fin:
		diffusion(banc).pas()
		time.sleep(PAS_REEL)
		maintenant = time.monotonic()
		horloge(banc).avancer(timedelta(seconds=maintenant - precedent))
		precedent = maintenant


@when(parsers.parse("l'horloge du binaire passe au « {instant} »"))
def horloge_passe(banc: Banc, instant: str) -> None:
	horloge(banc).avancer(heure(instant) - horloge(banc).maintenant())


@when(parsers.parse("le sonore « {nom} » redevient actif"))
def redevient_actif(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = 'actif' WHERE id = %s", (sonore(base_vide, nom),))


@when("la diffusion s'arrête")
def arreter(banc: Banc) -> None:
	diffusion(banc).arreter()


# ─── Alors ─────────────────────────────────────────────────


def passages(base: Connexion) -> list[tuple[str, datetime, datetime | None, bool | None]]:
	lignes = base.execute(
		"SELECT d.titre, d.horodatage, f.horodatage, f.sans_incident FROM airplay d"
		" LEFT JOIN airplay f ON f.passage_id = d.passage_id AND f.type_ligne = 'fin'"
		" WHERE d.type_ligne = 'debut' ORDER BY d.horodatage, d.id"
	).fetchall()
	return [(str(t), d, f, s) for t, d, f, s in lignes]  # type: ignore[misc]


def passage(base: Connexion, nom: str) -> tuple[str, datetime, datetime | None, bool | None]:
	return next(p for p in passages(base) if p[0] == nom)


def log(base: Connexion) -> list[tuple[str, str]]:
	return [(str(n), str(t)) for n, t in base.execute("SELECT niveau::text, nature FROM log ORDER BY id").fetchall()]


@then(parsers.re(r"l'airplay montre les passages (?P<liste>.+)"))
def airplay(base_vide: Connexion, liste: str) -> None:
	assert [p[0] for p in passages(base_vide)] == [n.strip(" «»") for n in liste.split(",")], passages(base_vide)


def titre(base: Connexion, sonore: int) -> str:
	ligne = base.execute("SELECT titre FROM sonores WHERE id = %s", (sonore,)).fetchone()
	assert ligne is not None
	return str(ligne[0])


def annonces(banc: Banc, base: Connexion) -> list[str]:
	return [titre(base, prevu.choix.sonore) for prevu in diffusion(banc).a_venir]


def liste(texte: str) -> list[str]:
	return [nom.strip(" «»") for nom in texte.split(",")]


@then(parsers.parse("le prochain sonore réservé est « {nom} »"))
def prochain_reserve(banc: Banc, base_vide: Connexion, nom: str) -> None:
	reserve = diffusion(banc).reserve
	assert reserve is not None
	assert titre(base_vide, reserve.choix.sonore) == nom


@then(parsers.re(r"les sonores à venir sont (?P<noms>.+)"))
def a_venir(banc: Banc, base_vide: Connexion, noms: str) -> None:
	assert annonces(banc, base_vide) == liste(noms)


@pytest.fixture
def notes() -> list[str]:
	"""Les sonores annoncés, notés par le scénario."""
	return []


@when("je note les sonores annoncés")
def noter(banc: Banc, base_vide: Connexion, notes: list[str]) -> None:
	reserve = diffusion(banc).reserve
	assert reserve is not None
	notes.extend([titre(base_vide, reserve.choix.sonore), *annonces(banc, base_vide)])


@then(parsers.parse("le passage n°{passage:d} est le sonore noté n°{rang:d}"))
def passage_note(base_vide: Connexion, notes: list[str], passage: int, rang: int) -> None:
	joues = [p[0] for p in passages(base_vide)]
	assert joues[passage - 1] == notes[rang - 1], (joues, notes)


@then(parsers.parse("le prochain sonore et les sonores à venir reprennent les sonores notés à partir du n°{rang:d}"))
def suite_notee(banc: Banc, base_vide: Connexion, notes: list[str], rang: int) -> None:
	reserve = diffusion(banc).reserve
	assert reserve is not None
	annonces_ = [titre(base_vide, reserve.choix.sonore), *annonces(banc, base_vide)]
	assert annonces_[: len(notes) - rang + 1] == notes[rang - 1 :], (annonces_, notes)


def heure_de_fin(fin: datetime | None) -> str:
	if fin is None:
		return ""
	return f"{fin.astimezone():%H:%M:%S}"


@then("l'airplay montre :")
def airplay_detaille(base_vide: Connexion, datatable: list[list[str]]) -> None:
	_, *lignes = datatable
	obtenus = [
		[titre, f"{debut.astimezone():%H:%M:%S}", heure_de_fin(fin), "oui" if sans_incident else "non"]
		for titre, debut, fin, sans_incident in passages(base_vide)
	]
	assert obtenus == [[valeur.strip() for valeur in ligne] for ligne in lignes], obtenus


@then(
	parsers.re(r"le sonore « (?P<nom>[^»]+) » a démarré (?:avec une montée de (?P<duree>[\d,]+) secondes|sans montée)")
)
def montee(banc: Banc, nom: str, duree: str | None) -> None:
	assert banc.simule is not None
	attendue = timedelta(0)
	if duree is not None:
		attendue = timedelta(seconds=secondes(duree))
	assert banc.simule.montees[nom] == attendue, banc.simule.montees


@then("chaque passage a sa ligne de fin, sans incident")
def lignes_de_fin(base_vide: Connexion) -> None:
	lignes = passages(base_vide)
	assert (lignes) and (all((fin is not None) and (sans_incident) for _, _, fin, sans_incident in lignes)), lignes


@then(parsers.parse("le log commence par « {niveau} » « {nature} » et finit par « {niveau_fin} » « {nature_fin} »"))
def bornes_du_log(base_vide: Connexion, niveau: str, nature: str, niveau_fin: str, nature_fin: str) -> None:
	lignes = log(base_vide)
	assert (lignes[0] == (niveau, nature)) and (lignes[-1] == (niveau_fin, nature_fin)), lignes


@then(parsers.parse("le log finit par « {niveau} » « {nature} »"))
def fin_du_log(base_vide: Connexion, niveau: str, nature: str) -> None:
	assert log(base_vide)[-1] == (niveau, nature)


@then(parsers.re(r"le log contient (?P<nombre>\d+) (?P<niveau>info|alerte|incident) « (?P<nature>[^»]+) »"))
def lignes_du_log(base_vide: Connexion, nombre: str, niveau: str, nature: str) -> None:
	assert log(base_vide).count((niveau, nature)) == int(nombre), log(base_vide)


NATURES_DE_L_ANTENNE = ("début d'événement", "fin d'événement", "début de séquence", "fin de séquence")
"""Ce que le log note des événements et des séquences à l'antenne (https://github.com/dascritch/machincast/issues/153)."""


@then("le log note pour les événements et les séquences :")
def log_de_l_antenne(base_vide: Connexion, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	lues = base_vide.execute(
		"SELECT l.horodatage, l.niveau::text, l.nature, l.message, e.nom_interne FROM log l"
		" LEFT JOIN evenements e ON e.id = l.evenement_id WHERE l.nature = ANY(%s) ORDER BY l.id",
		(list(NATURES_DE_L_ANTENNE),),
	).fetchall()
	attendues = [
		(heure(horodatage.strip()), "info", nature.strip(), message.strip(), evenement.strip())
		for horodatage, nature, message, evenement in rangees
	]
	assert lues == attendues, lues


@then(parsers.parse("le passage « {nom} » a été coupé net au « {instant} »"))
def coupe_net(base_vide: Connexion, nom: str, instant: str) -> None:
	assert passage(base_vide, nom)[2] == heure(instant)


@then(
	parsers.re(
		r"le passage « (?P<suivant>[^»]+) » a commencé (?P<quand>avant|après) la fin du passage « (?P<nom>[^»]+) »"
	)
)
def chevauchement(base_vide: Connexion, suivant: str, quand: str, nom: str) -> None:
	fin = passage(base_vide, nom)[2]
	debut = passage(base_vide, suivant)[1]
	assert fin is not None
	assert (debut < fin) if quand == "avant" else (debut >= fin), (debut, fin)


@given(parsers.re(r"le sonore « (?P<nom>[^»]+) » a (?P<duree>[\d,]+) seconde de crossfade de (?P<cote>début|fin)"))
def crossfade_du_sonore(base_vide: Connexion, nom: str, duree: str, cote: str) -> None:
	colonne = "crossfade_debut" if cote == "début" else "crossfade_fin"
	base_vide.execute(
		f"UPDATE sonores SET {colonne} = %s WHERE id = %s",
		(timedelta(seconds=secondes(duree)), sonore(base_vide, nom)),
	)


@given(parsers.re(r"l'événement de secours « (?P<nom>[^»]+) », avec les sonores (?P<liste>.+)"))
def evenement_de_secours(banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, liste: str) -> None:
	evenement(banc, base_vide, tmp_path, nom, "secours", None, None, [n.strip(" «»") for n in liste.split(",")])


@given(parsers.parse("le fichier du sonore « {nom} » a été supprimé"))
def fichier_supprime(banc: Banc, nom: str) -> None:
	banc.fichiers[nom].unlink()


@given(parsers.parse("le sonore « {nom} » est à l'état « {etat} »"))
def etat(base_vide: Connexion, nom: str, etat: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = %s WHERE id = %s", (etat, sonore(base_vide, nom)))


@given(parsers.parse("le fil musical « {nom} » est supprimé"))
def fil_supprime(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("DELETE FROM evenements WHERE nom_interne = %s", (nom,))


def sonores_de(base: Connexion, evenement: str) -> set[str]:
	lignes = base.execute(
		"SELECT s.titre FROM evenements e JOIN evenements_elements ee ON ee.evenement_id = e.id"
		" JOIN sonores s ON s.id = ee.sonore_id WHERE e.nom_interne = %s",
		(evenement,),
	).fetchall()
	return {str(ligne[0]) for ligne in lignes}


@then("l'airplay ne montre aucun passage")
def aucun_passage(base_vide: Connexion) -> None:
	assert passages(base_vide) == []


# ─── Streams (https://github.com/dascritch/machincast/issues/16) ───


@pytest.fixture
def serveur() -> Iterator[ServeurDeFlux]:
	serveur = ServeurDeFlux()
	yield serveur
	serveur.fermer()


@given(parsers.parse("un serveur de flux local, avec le flux « {flux} » en ligne"))
def flux_en_ligne(serveur: ServeurDeFlux, flux: str) -> None:
	serveur.en_ligne[flux] = True


@given(parsers.parse("le stream « {nom} » à l'adresse du flux « {flux} »"))
def stream_direct(serveur: ServeurDeFlux, base_vide: Connexion, nom: str, flux: str) -> None:
	base_vide.execute(
		"INSERT INTO sonores (type, url_stream, titre) VALUES ('stream', %s, %s)", (serveur.adresse(flux), nom)
	)


@then(parsers.parse("le passage « {nom} » a duré {duree} seconde, à {marge} seconde près"))
def duree_du_passage(base_vide: Connexion, nom: str, duree: str, marge: str) -> None:
	"""Du début à la fin du passage, à l'heure du binaire (https://github.com/dascritch/machincast/issues/146)."""
	trouves = [(debut, fin) for titre, debut, fin, _ in passages(base_vide) if titre == nom]
	assert trouves, f"aucun passage de {nom}"
	debut, fin = trouves[0]
	assert fin is not None, f"passage de {nom} sans fin"
	assert abs((fin - debut).total_seconds() - secondes(duree)) <= secondes(marge), fin - debut


@then(parsers.parse("la voie de « {nom} » a joué son fichier de {debut} à {fin} seconde, à {marge} seconde près"))
def voie_jouee(banc: Banc, nom: str, debut: str, fin: str, marge: str) -> None:
	assert banc.moteur is not None
	voie = banc.moteur.jouees[str(banc.fichiers[nom])]
	assert voie.position_finale is not None, voie.etat
	ecart = secondes(marge)
	assert abs(voie.decalage.total_seconds() - secondes(debut)) <= ecart, voie.decalage
	assert abs((voie.decalage + voie.position_finale).total_seconds() - secondes(fin)) <= ecart, voie.position_finale
