"""Étapes du mode simulation de Machin lecture (https://github.com/dascritch/machincast/issues/21).

Les étapes de la diffusion viennent de tests/etapes_diffusion.py. Les sorties de la simulation sont écrites dans le
répertoire temporaire du scénario.
"""

import csv
import logging
import shlex
import shutil
import subprocess
import sys
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import machincast.audio
import machincast.lecture.moteur
from machincast.audio import SortieAudioIndisponible
from machincast.base import Role, connecter
from machincast.configuration import Metadonnees
from machincast.lecture.simulation import Resultat, lecture_seule, simuler
from tests.base_test import CONFIGURATION_TEST, parametres_base_test
from tests.etapes_diffusion import Banc, Connexion, evenement, heure, sonore

scenarios("simulation.feature")


@dataclass
class Contexte:
	repertoire: Path | None = None
	resultats: list[Resultat] = field(default_factory=list)
	avant: tuple[object, ...] | None = None
	metadonnees: Metadonnees = field(default_factory=lambda: Metadonnees(masquer=False, texte_public=""))
	erreur: Exception | None = None
	processus: subprocess.CompletedProcess[str] | None = None


@pytest.fixture
def contexte() -> Contexte:
	return Contexte()


def resultat(contexte: Contexte) -> Resultat:
	assert contexte.resultats
	return contexte.resultats[-1]


def etat_de_la_base(base: Connexion) -> tuple[object, ...]:
	"""Tout ce que la simulation pourrait changer : airplay, log, et chaque sonore."""
	ligne = base.execute(
		"SELECT (SELECT count(*) FROM airplay), (SELECT count(*) FROM log),"
		" (SELECT COALESCE(jsonb_agg(to_jsonb(s) ORDER BY s.id), '[]') FROM sonores s)"
	).fetchone()
	assert ligne is not None
	return tuple(ligne)


def lancer_simulation(
	contexte: Contexte, base: Connexion, debut: str, fin: str, graine: int | None = None, nom: str | None = None
) -> None:
	assert contexte.repertoire is not None
	contexte.avant = etat_de_la_base(base)
	with connecter(*parametres_base_test(), Role.LECTURE) as connexion:
		contexte.resultats.append(
			simuler(connexion, contexte.repertoire, heure(debut), heure(fin), graine, nom, contexte.metadonnees)
		)


def titres(contexte: Contexte) -> list[str]:
	return [str(ligne.titre) for ligne in resultat(contexte).passages]


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("des sorties de simulation dans un répertoire temporaire, avec le texte public « {texte} »"))
def sorties_temporaires(contexte: Contexte, tmp_path: Path, caplog: pytest.LogCaptureFixture, texte: str) -> None:
	caplog.set_level(logging.INFO, logger="machincast")
	contexte.repertoire = tmp_path / "sorties"
	contexte.metadonnees = Metadonnees(masquer=False, texte_public=texte)


@given(parsers.parse("chaque sonore dure {minutes:d} minute"))
def duree_des_sonores(base_vide: Connexion, minutes: int) -> None:
	base_vide.execute("UPDATE sonores SET duree = %s WHERE type = 'fichier'", (timedelta(minutes=minutes),))


@given(parsers.parse("l'émission « {nom} » du « {debut} » au « {fin} », avec le sonore « {nom_sonore} »"))
def emission_datee(
	banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, debut: str, fin: str, nom_sonore: str
) -> None:
	evenement(banc, base_vide, tmp_path, nom, "emission", heure(debut), heure(fin), [nom_sonore])


@given(parsers.parse("le stream « {nom} » à l'adresse « {adresse} »"))
def stream(base_vide: Connexion, nom: str, adresse: str) -> None:
	base_vide.execute("INSERT INTO sonores (type, url_stream, titre) VALUES ('stream', %s, %s)", (adresse, nom))


@given(parsers.parse("« {nom} » a été joué dans le fil « {fil} » le « {instant} »"))
def joue_dans_le_fil(base_vide: Connexion, nom: str, fil: str, instant: str) -> None:
	ligne = base_vide.execute(
		"SELECT e.id, ee.id FROM evenements e JOIN evenements_elements ee ON ee.evenement_id = e.id"
		" WHERE e.nom_interne = %s AND ee.sonore_id = %s",
		(fil, sonore(base_vide, nom)),
	).fetchone()
	assert ligne is not None
	base_vide.execute(
		"INSERT INTO airplay (passage_id, type_ligne, horodatage, sonore_id, evenement_id, element_id, titre)"
		" VALUES (%s, 'debut', %s, %s, %s, %s, %s)",
		(uuid.uuid4(), heure(instant), sonore(base_vide, nom), ligne[0], ligne[1], nom),
	)


@given("le masquage de tous les sonores")
def masquer_tous(base_vide: Connexion) -> None:
	base_vide.execute("UPDATE sonores SET masquer_metadonnees = true")


@given("aucune sortie audio ne peut être créée")
def sans_sortie_audio(monkeypatch: pytest.MonkeyPatch) -> None:
	def refuser(*arguments: object, **options: object) -> object:
		raise SortieAudioIndisponible("aucune sortie audio dans ce scénario")

	monkeypatch.setattr(machincast.audio, "creer_sortie", refuser)
	monkeypatch.setattr(machincast.lecture.moteur, "creer_sortie", refuser)


@given(parsers.re(r"le sonore « (?P<nom>[^»]+) » a un maximum de (?P<maximum>\d+) lectures?"))
def maximum_du_sonore(base_vide: Connexion, nom: str, maximum: str) -> None:
	base_vide.execute("UPDATE sonores SET max_lectures = %s WHERE id = %s", (int(maximum), sonore(base_vide, nom)))


# ─── Quand ─────────────────────────────────────────────────


@when(
	parsers.re(
		r"je simule la diffusion du « (?P<debut>[^»]+) » au « (?P<fin>[^»]+) »"
		r"(?:, avec la graine (?P<graine>\d+))?(?:, sous le nom « (?P<nom>[^»]+) »)?$"
	)
)
def simuler_la_diffusion(
	contexte: Contexte, base_vide: Connexion, debut: str, fin: str, graine: str | None, nom: str | None
) -> None:
	lancer_simulation(contexte, base_vide, debut, fin, None if graine is None else int(graine), nom)


@when(parsers.parse("je simule deux fois la diffusion du « {debut} » au « {fin} », avec la graine {graine:d}"))
def simuler_deux_fois(contexte: Contexte, base_vide: Connexion, debut: str, fin: str, graine: int) -> None:
	lancer_simulation(contexte, base_vide, debut, fin, graine)
	lancer_simulation(contexte, base_vide, debut, fin, graine)


@when("une écriture dans le log est tentée pendant une simulation")
def ecrire_pendant_la_simulation(contexte: Contexte, base_vide: Connexion) -> None:
	with connecter(*parametres_base_test(), Role.LECTURE) as connexion:
		try:
			with lecture_seule(connexion):
				connexion.execute("INSERT INTO log (niveau, nature, message) VALUES ('info', 'essai', 'interdit')")
		except psycopg.Error as erreur:
			contexte.erreur = erreur


def machin_lecture() -> str:
	return shutil.which("Machin_lecture") or str(Path(sys.executable).parent / "Machin_lecture")


@when(parsers.re(r"je lance Machin_lecture avec « (?P<arguments>.+) »(?P<sans_base> et une socket inexistante)?$"))
def lancer(contexte: Contexte, tmp_path: Path, arguments: str, sans_base: str | None) -> None:
	configuration = CONFIGURATION_TEST
	if sans_base:
		configuration = tmp_path / "sans-base.toml"
		texte = CONFIGURATION_TEST.read_text(encoding="utf-8")
		configuration.write_text(
			texte.replace('socket = "/var/run/postgresql"', f'socket = "{tmp_path / "aucune-socket"}"'),
			encoding="utf-8",
		)
	contexte.processus = subprocess.run(
		[machin_lecture(), "--config", str(configuration), *shlex.split(arguments)],
		capture_output=True,
		text=True,
		timeout=60,
	)


# ─── Alors ─────────────────────────────────────────────────


@then("la simulation donne les passages :")
def passages_attendus(contexte: Contexte, datatable: list[list[str]]) -> None:
	_, *lignes = datatable
	obtenus = [
		[
			f"{p.debut.astimezone():%Y-%m-%d %H:%M:%S}",
			f"{p.fin.astimezone():%Y-%m-%d %H:%M:%S}" if p.fin else "",
			str(p.titre),
		]
		for p in resultat(contexte).passages
	]
	assert obtenus == lignes, obtenus


@then(parsers.parse("la simulation donne {nombre:d} passages"))
def nombre_de_passages(contexte: Contexte, nombre: int) -> None:
	assert len(resultat(contexte).passages) == nombre


@then(parsers.re(r"la simulation donne les titres (?P<liste>.+)"))
def titres_attendus(contexte: Contexte, liste: str) -> None:
	assert titres(contexte) == [n.strip(" «»") for n in liste.split(",")], titres(contexte)


@then("la base n'a pas changé")
def base_intacte(contexte: Contexte, base_vide: Connexion) -> None:
	assert etat_de_la_base(base_vide) == contexte.avant


@then("PostgreSQL la refuse, la transaction étant en lecture seule")
def refus(contexte: Contexte, base_vide: Connexion) -> None:
	assert isinstance(contexte.erreur, psycopg.errors.ReadOnlySqlTransaction), repr(contexte.erreur)
	assert base_vide.execute("SELECT count(*) FROM log WHERE nature = 'essai'").fetchone() == (0,)


@then(parsers.parse("chaque tranche de 3 passages joue « a », « b » et « c », chacun une fois"))
def cycles(contexte: Contexte) -> None:
	vus = titres(contexte)
	assert len(vus) == 6, vus
	assert sorted(vus[:3]) == ["a", "b", "c"] and sorted(vus[3:]) == ["a", "b", "c"], vus


@then("les deux simulations donnent les mêmes passages")
def memes_passages(contexte: Contexte) -> None:
	premiere, seconde = ([str(p.titre) for p in r.passages] for r in contexte.resultats)
	assert premiere == seconde and len(set(premiere)) > 1, (premiere, seconde)


@then(parsers.re(r"la simulation a consigné (?P<nombre>\d+) (?P<niveau>info|alerte|incident) « (?P<nature>[^»]+) »"))
def consigne(contexte: Contexte, nombre: str, niveau: str, nature: str) -> None:
	lignes = Counter((n, t) for n, t, _ in resultat(contexte).log)
	assert lignes[(niveau, nature)] == int(nombre), resultat(contexte).log


@then(parsers.parse("le sonore « {nom} » est toujours à l'état « {etat} » en base"))
def etat_en_base(base_vide: Connexion, nom: str, etat: str) -> None:
	ligne = base_vide.execute("SELECT etat::text FROM sonores WHERE id = %s", (sonore(base_vide, nom),)).fetchone()
	assert ligne == (etat,)


@then(parsers.parse("la simulation a écrit « {nom} » en .csv, .pls et .html"))
def fichiers_ecrits(contexte: Contexte, nom: str) -> None:
	assert contexte.repertoire is not None
	attendus = tuple(contexte.repertoire / f"{nom}{extension}" for extension in (".csv", ".pls", ".html"))
	assert resultat(contexte).fichiers == attendus
	assert all(chemin.is_file() for chemin in attendus), list(contexte.repertoire.iterdir())


def fichier(contexte: Contexte, extension: str) -> Path:
	return next(chemin for chemin in resultat(contexte).fichiers if chemin.suffix == extension)


@then(parsers.parse("le CSV de la simulation a {nombre:d} lignes de passage, sur les deux jours"))
def csv_de_la_simulation(contexte: Contexte, nombre: int) -> None:
	with fichier(contexte, ".csv").open(encoding="utf-8-sig", newline="") as source:
		lignes = list(csv.DictReader(source, delimiter=";"))
	assert len(lignes) == nombre
	assert {ligne["debut"][:10] for ligne in lignes} == {"2026-10-20", "2026-10-21"}, lignes


@then(parsers.parse("la playlist de la simulation compte {nombre:d} entrées"))
def playlist_de_la_simulation(contexte: Contexte, nombre: int) -> None:
	assert f"NumberOfEntries={nombre}" in fichier(contexte, ".pls").read_text(encoding="utf-8")


@then("la page de la simulation montre l'emplacement de chaque fichier joué")
def page_avec_emplacements(contexte: Contexte) -> None:
	page = fichier(contexte, ".html").read_text(encoding="utf-8")
	for ligne in resultat(contexte).passages:
		assert f">{ligne.emplacement}<" in page, page
	assert ">f1<" not in page and ">f2<" not in page, page


@given(parsers.parse("le masquage du sonore « {nom} »"))
def masquer_un_sonore(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("UPDATE sonores SET masquer_metadonnees = true WHERE id = %s", (sonore(base_vide, nom),))


def sorties_lues(contexte: Contexte) -> dict[str, str]:
	return {chemin.suffix: chemin.read_text(encoding="utf-8-sig") for chemin in resultat(contexte).fichiers or ()}


@then(
	parsers.parse(
		"les sorties de la simulation montrent « {visible} », mais pas « {masque} », remplacé par « {texte} »"
	)
)
def sorties_masquees(contexte: Contexte, visible: str, masque: str, texte: str) -> None:
	for extension, contenu in sorties_lues(contexte).items():
		assert visible in contenu and texte in contenu, (extension, contenu)
		assert f">{masque}<" not in contenu and f";{masque};" not in contenu and f"={masque}\n" not in contenu, (
			extension,
			contenu,
		)


@then(
	parsers.parse("les sorties de la simulation donnent l'emplacement des fichiers de « {premier} » et de « {second} »")
)
def sorties_avec_emplacements(contexte: Contexte, base_vide: Connexion, premier: str, second: str) -> None:
	for nom in (premier, second):
		ligne = base_vide.execute("SELECT emplacement FROM sonores WHERE id = %s", (sonore(base_vide, nom),)).fetchone()
		assert ligne is not None
		for extension, contenu in sorties_lues(contexte).items():
			assert str(ligne[0]) in contenu, (extension, nom)


@then(parsers.parse("la page de la simulation signale l'alerte « {nature} »"))
def page_alerte(contexte: Contexte, nature: str) -> None:
	page = fichier(contexte, ".html").read_text(encoding="utf-8")
	assert "alerte" in page and nature in page, page


@then(parsers.parse("il s'arrête avec le code {code:d}, en signalant « {motif} »"))
def arret(contexte: Contexte, code: int, motif: str) -> None:
	assert contexte.processus is not None
	assert contexte.processus.returncode == code, contexte.processus.stderr
	assert motif in contexte.processus.stderr, contexte.processus.stderr


@then(parsers.parse("le journal du binaire a signalé « {texte} »"))
def journal_signale(caplog: pytest.LogCaptureFixture, texte: str) -> None:
	assert any(r.levelno == logging.WARNING and texte in r.getMessage() for r in caplog.records), caplog.text
