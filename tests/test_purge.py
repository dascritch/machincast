"""Scénarios de la purge de la base (https://github.com/dascritch/machincast/issues/268).

Comme la maintenance (test_maintenance_base.py), la purge travaille sur la base de test, désignée comme base de
production d'une configuration du scénario, modifiée après lecture : le chargement d'un fichier refuse une base de
production égale à la base de test. Les dates des tableaux sont prises à midi, heure de Paris.
"""

import dataclasses
import logging
import subprocess
import time
import tomllib
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import purge
from machincast.cli import creer_analyseur
from machincast.configuration import REPERTOIRE_PROJET, Configuration
from machincast.horloge import HorlogeFixe
from tests.base_test import configuration_test

scenarios("purge.feature")

PARIS = ZoneInfo("Europe/Paris")
Connexion = psycopg.Connection[tuple[object, ...]]


@dataclasses.dataclass
class Execution:
	code: int = -1
	informations: list[str] = dataclasses.field(default_factory=list)
	erreurs: list[str] = dataclasses.field(default_factory=list)


@pytest.fixture
def execution() -> Execution:
	return Execution()


def _jour(date: str) -> datetime:
	return datetime.fromisoformat(f"{date} 12:00:00").replace(tzinfo=PARIS)


def _instant(texte: str) -> datetime:
	return datetime.fromisoformat(texte).replace(tzinfo=PARIS)


@given("une configuration dont la base de production est la base de test", target_fixture="configuration")
def configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, base_vide: Connexion) -> Configuration:
	monkeypatch.setenv("TZ", "Europe/Paris")
	time.tzset()
	lue = configuration_test()
	base = dataclasses.replace(lue.base, production=lue.base.test)
	return dataclasses.replace(lue, base=base, chemin=tmp_path / "machincast.toml")


@given("une configuration dont la base de production est injoignable", target_fixture="configuration")
def configuration_injoignable(configuration: Configuration, tmp_path: Path) -> Configuration:
	base = dataclasses.replace(configuration.base, socket=tmp_path / "sans-postgresql")
	return dataclasses.replace(configuration, base=base)


@given(parsers.parse("l'horloge de la purge au « {instant} »"))
def horloge(monkeypatch: pytest.MonkeyPatch, instant: str) -> None:
	monkeypatch.setattr(purge, "HORLOGE", HorlogeFixe(_instant(instant)))


@given(parsers.parse("la durée de péremption de {jours:d} jours dans la configuration"), target_fixture="configuration")
def peremption(configuration: Configuration, jours: int) -> Configuration:
	return dataclasses.replace(configuration, base=dataclasses.replace(configuration.base, peremption=jours))


def _passage(
	connexion: Connexion,
	titre: str,
	debut: datetime,
	fin: datetime,
	sonore_id: object = None,
	emplacement: str | None = None,
) -> None:
	passage = uuid.uuid4()
	connexion.execute(
		"INSERT INTO airplay (passage_id, type_ligne, horodatage, sonore_id, emplacement, titre)"
		" VALUES (%s, 'debut', %s, %s, %s, %s)",
		(passage, debut, sonore_id, emplacement, titre),
	)
	connexion.execute(
		"INSERT INTO airplay (passage_id, type_ligne, horodatage, sonore_id, emplacement, titre, duree_diffusee,"
		" sans_incident) VALUES (%s, 'fin', %s, %s, %s, %s, %s, true)",
		(passage, fin, sonore_id, emplacement, titre, fin - debut),
	)


@given("les passages de l'airplay, et autant de lignes du log :")
def passages_et_log(base_vide: Connexion, datatable: list[list[str]]) -> None:
	_entete, *lignes = datatable
	for date, titre in lignes:
		moment = _jour(date)
		_passage(base_vide, titre, moment.replace(minute=0), moment.replace(minute=3))
		base_vide.execute(
			"INSERT INTO log (horodatage, niveau, nature, message) VALUES (%s, 'alerte', 'essai', %s)",
			(moment, titre),
		)


def _sonore(connexion: Connexion, nom: str, emplacement: str) -> object:
	ligne = connexion.execute(
		"INSERT INTO sonores (type, emplacement, titre) VALUES ('fichier', %s, %s) RETURNING id", (emplacement, nom)
	).fetchone()
	assert ligne is not None
	return ligne[0]


@given("les éléments en base :")
def elements(base_vide: Connexion, datatable: list[list[str]]) -> None:
	_entete, *lignes = datatable
	for genre, nom, supprime, disparu in lignes:
		supprime_le = None
		if supprime:
			supprime_le = _jour(supprime)
		if genre == "sonore":
			identifiant = _sonore(base_vide, nom, f"/srv/{nom}.flac")
			base_vide.execute("UPDATE sonores SET supprime_le = %s WHERE id = %s", (supprime_le, identifiant))
			if disparu:
				base_vide.execute(
					"UPDATE sonores SET etat = 'supprime', disparu_le = %s WHERE id = %s", (_jour(disparu), identifiant)
				)
		elif genre == "banque":
			base_vide.execute(
				"INSERT INTO banques (nom_interne, mode, supprime_le) VALUES (%s, 'sequentiel', %s)", (nom, supprime_le)
			)
		elif genre == "séquence":
			base_vide.execute("INSERT INTO sequences (nom_interne, supprime_le) VALUES (%s, %s)", (nom, supprime_le))
		else:
			assert genre == "événement", genre
			base_vide.execute(
				"INSERT INTO evenements (nom_interne, priorite, debut, supprime_le) VALUES (%s, 'emission', %s, %s)",
				(nom, _jour("2026-09-01"), supprime_le),
			)


@given(parsers.parse("un passage du sonore « {titre} » le {date}"))
def passage_du_sonore(base_vide: Connexion, titre: str, date: str) -> None:
	ligne = base_vide.execute("SELECT id, emplacement FROM sonores WHERE titre = %s", (titre,)).fetchone()
	assert ligne is not None
	moment = _jour(date)
	_passage(base_vide, titre, moment, moment.replace(minute=3), ligne[0], str(ligne[1]))


@given(parsers.parse("un passage « {titre} », commencé le « {debut} » et fini le « {fin} »"))
def passage_a_cheval(base_vide: Connexion, titre: str, debut: str, fin: str) -> None:
	_passage(base_vide, titre, _instant(debut), _instant(fin))


@given(parsers.parse("le fichier sonore « {chemin} » du sonore « {titre} », supprimé le {date}"))
def fichier_supprime(base_vide: Connexion, configuration: Configuration, chemin: str, titre: str, date: str) -> None:
	fichier = Path(chemin.replace("…/", f"{configuration.chemin.parent}/"))
	fichier.parent.mkdir(parents=True, exist_ok=True)
	fichier.write_bytes(b"fLaC un vieux sonore")
	identifiant = _sonore(base_vide, titre, str(fichier))
	base_vide.execute("UPDATE sonores SET supprime_le = %s WHERE id = %s", (_jour(date), identifiant))


@given(parsers.parse("le feed « {feed} », suivi par le stream « {stream} », supprimé le {date}"))
def feed_et_stream(base_vide: Connexion, feed: str, stream: str, date: str) -> None:
	base_vide.execute("INSERT INTO feeds (nom, url) VALUES (%s, 'http://localhost:8000/direct')", (feed,))
	base_vide.execute(
		"INSERT INTO sonores (type, feed_id, titre, supprime_le) SELECT 'stream', id, %s, %s FROM feeds WHERE nom = %s",
		(stream, _jour(date), feed),
	)


@when(parsers.parse("je lance « {commande} »"))
def lancer(configuration: Configuration, execution: Execution, caplog: pytest.LogCaptureFixture, commande: str) -> None:
	_machin, _binaire, *arguments = commande.split()
	analyseur = creer_analyseur(purge.EXECUTABLE, purge.DESCRIPTION)
	options = analyseur.parse_args(arguments)
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"):
		execution.code = purge.executer(configuration, options)
	execution.informations = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
	execution.erreurs = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


@then(parsers.parse("la purge se termine avec le code {code:d}"))
def code_de_sortie(execution: Execution, code: int) -> None:
	assert execution.code == code, (execution.informations, execution.erreurs)


@then(parsers.parse("la purge a annoncé « {texte} »"))
def annonce(execution: Execution, texte: str) -> None:
	assert texte in execution.informations, execution.informations


@then("la purge n'a rien signalé")
def rien_signale(execution: Execution) -> None:
	assert execution.erreurs == []


@then("la purge a signalé une base de données injoignable")
def injoignable(execution: Execution) -> None:
	assert any(erreur.startswith("base de données injoignable") for erreur in execution.erreurs), execution.erreurs


def _liste(texte: str) -> list[str]:
	return sorted(nom.strip().strip("«»").strip() for nom in texte.split(","))


@then(parsers.parse("l'airplay garde les passages « {titres} »"))
def airplay_garde(base_vide: Connexion, titres: str) -> None:
	lignes = base_vide.execute("SELECT DISTINCT titre FROM airplay ORDER BY titre").fetchall()
	assert [titre for (titre,) in lignes] == _liste(titres)


@then(parsers.parse("l'airplay garde le début et la fin du passage « {titre} »"))
def airplay_entier(base_vide: Connexion, titre: str) -> None:
	lignes = base_vide.execute("SELECT type_ligne::text FROM airplay WHERE titre = %s ORDER BY 1", (titre,)).fetchall()
	assert lignes == [("debut",), ("fin",)]


@then(parsers.parse("l'airplay garde le passage « {titre} », à l'emplacement « {emplacement} », sans sonore en base"))
def airplay_sans_sonore(base_vide: Connexion, titre: str, emplacement: str) -> None:
	lignes = base_vide.execute("SELECT titre, emplacement, sonore_id FROM airplay").fetchall()
	assert lignes == [(titre, emplacement, None), (titre, emplacement, None)]
	assert base_vide.execute("SELECT count(*) FROM sonores").fetchone() == (0,)


@then(parsers.parse("le log garde ses lignes du {date}, et une ligne « purge » qui reprend l'annonce"))
def log_garde(base_vide: Connexion, execution: Execution, date: str) -> None:
	lignes = base_vide.execute("SELECT horodatage, niveau::text, nature, message FROM log ORDER BY id").fetchall()
	gardee, purgee = lignes
	assert gardee[0] == _jour(date)
	assert purgee[1:] == ("info", "purge", execution.informations[-1])


TABLES = {
	"sonores": ("sonores", "titre"),
	"banques": ("banques", "nom_interne"),
	"événements": ("evenements", "nom_interne"),
}


@then(parsers.parse("en base restent les {genre} « {noms} »"))
def restent(base_vide: Connexion, genre: str, noms: str) -> None:
	table, colonne = TABLES[genre]
	lignes = base_vide.execute(f"SELECT {colonne} FROM {table} ORDER BY {colonne}").fetchall()  # noqa: S608
	assert [nom for (nom,) in lignes] == _liste(noms)


@then(parsers.parse("en base ne reste aucune séquence"))
def aucune_sequence(base_vide: Connexion) -> None:
	assert base_vide.execute("SELECT count(*) FROM sequences").fetchone() == (0,)


@then("en base ne reste aucun sonore")
def aucun_sonore(base_vide: Connexion) -> None:
	assert base_vide.execute("SELECT count(*) FROM sonores").fetchone() == (0,)


@then(parsers.parse("le fichier « {chemin} » est toujours là, intact"))
def fichier_intact(configuration: Configuration, chemin: str) -> None:
	fichier = Path(chemin.replace("…/", f"{configuration.chemin.parent}/"))
	assert fichier.read_bytes() == b"fLaC un vieux sonore"


@then(parsers.parse("aucun stream ne suit plus le feed « {feed} », qui peut se supprimer"))
def feed_libre(base_vide: Connexion, feed: str) -> None:
	assert base_vide.execute("SELECT count(*) FROM sonores").fetchone() == (0,)
	base_vide.execute("DELETE FROM feeds WHERE nom = %s", (feed,))


@then(parsers.parse("« {binaire} » est un binaire du wrapper, déclaré dans pyproject.toml"))
def binaire_du_wrapper(binaire: str) -> None:
	scripts = tomllib.loads((REPERTOIRE_PROJET / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
	assert scripts[f"Machin_{binaire}"] == "machincast.purge:main"
	sortie = subprocess.run(
		[str(REPERTOIRE_PROJET / "bin" / "Machin"), "--binaires"], capture_output=True, text=True, timeout=30
	)
	assert binaire in sortie.stdout.split(), sortie.stdout
