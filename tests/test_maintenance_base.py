"""Scénarios de la maintenance de la base de données (https://github.com/dascritch/machincast/issues/127).

La maintenance travaille sur la base de test, désignée comme base de production d'une configuration du scénario : le
chargement d'un fichier refuse une base de production égale à la base de test, la configuration est donc modifiée
après lecture, et la maintenance exécutée sans passer par le fichier. pg_dump peut être retiré du PATH.
"""

import dataclasses
import io
import logging
import subprocess
import time
import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from yoyo import get_backend, read_migrations

from machincast import maintenance
from machincast.base import REPERTOIRE_MIGRATIONS, appliquer_migrations, url_yoyo
from machincast.cli import creer_analyseur
from machincast.configuration import REPERTOIRE_PROJET, Configuration
from machincast.horloge import HorlogeFixe
from tests.base_test import configuration_test

scenarios("maintenance_base.feature")

LANCEMENT = datetime(2026, 10, 22, 8, 30, tzinfo=ZoneInfo("Europe/Paris"))


@dataclasses.dataclass
class Execution:
	code: int = -1
	informations: list[str] = dataclasses.field(default_factory=list)
	erreurs: list[str] = dataclasses.field(default_factory=list)
	demande: str = ""
	entree_restante: str = ""
	"""Ce qui reste à lire sur l'entrée standard après la maintenance : vide, si elle a attendu sa fin."""
	debut: datetime | None = None
	"""L'heure du serveur PostgreSQL au lancement : le VACUUM de la maintenance la suit."""


@pytest.fixture
def execution() -> Execution:
	return Execution()


@given("une configuration dont la base de production est la base de test", target_fixture="configuration")
def configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, base_vide: object) -> Configuration:
	"""La configuration des tests, comme si elle était dans le répertoire du scénario."""
	monkeypatch.setenv("TZ", "Europe/Paris")
	time.tzset()
	monkeypatch.setattr(maintenance, "HORLOGE", HorlogeFixe(LANCEMENT))
	lue = configuration_test()
	base = dataclasses.replace(lue.base, production=lue.base.test)
	return dataclasses.replace(lue, base=base, chemin=tmp_path / "machincast.toml")


@given("la dernière migration retirée de la base de test")
def retirer_la_derniere(configuration: Configuration, request: pytest.FixtureRequest) -> None:
	"""La base de test sert aux autres scénarios : son schéma est remis en état à la fin, quoi qu'il arrive."""
	url = url_yoyo(configuration.base.socket, configuration.base.test)
	request.addfinalizer(lambda: appliquer_migrations(url))
	with get_backend(url) as backend, backend.lock():
		backend.rollback_migrations(backend.to_rollback(read_migrations(str(REPERTOIRE_MIGRATIONS)))[:1])


@given("pg_dump absent du poste")
def sans_pg_dump(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
	vide = tmp_path / "sans-pg-dump"
	vide.mkdir()
	monkeypatch.setenv("PATH", str(vide))


@given(parsers.parse("un rôle « {role} » attendu en plus par MachinCast"))
def role_en_plus(monkeypatch: pytest.MonkeyPatch, role: str) -> None:
	monkeypatch.setattr(maintenance, "ROLES", (*maintenance.ROLES, role))


def _lancer(
	configuration: Configuration,
	execution: Execution,
	caplog: pytest.LogCaptureFixture,
	commande: str,
	entree: str = "",
	monkeypatch: pytest.MonkeyPatch | None = None,
) -> None:
	_machin, _binaire, *arguments = commande.replace("…/", f"{configuration.chemin.parent}/").split()
	analyseur = creer_analyseur(maintenance.EXECUTABLE, maintenance.DESCRIPTION)
	maintenance.options_propres(analyseur)
	options = analyseur.parse_args(arguments)
	with psycopg.connect(host=str(configuration.base.socket), dbname=configuration.base.test) as connexion:
		ligne = connexion.execute("SELECT clock_timestamp()").fetchone()
	assert ligne is not None
	execution.debut = ligne[0]
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"):
		execution.code = maintenance.executer(configuration, options)
	execution.informations = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
	execution.erreurs = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


@when(parsers.parse("je lance « {commande} »"))
def lancer(configuration: Configuration, execution: Execution, caplog: pytest.LogCaptureFixture, commande: str) -> None:
	_lancer(configuration, execution, caplog, commande)


class CtrlC(io.StringIO):
	def read(self, _taille: int | None = -1) -> str:
		raise KeyboardInterrupt


@when(parsers.parse("je lance « {commande} », puis je tape Ctrl-C"))
def lancer_et_interrompre(
	configuration: Configuration,
	execution: Execution,
	caplog: pytest.LogCaptureFixture,
	monkeypatch: pytest.MonkeyPatch,
	commande: str,
) -> None:
	monkeypatch.setattr("sys.stdin", CtrlC())
	monkeypatch.setattr("sys.stdout", io.StringIO())
	_lancer(configuration, execution, caplog, commande)


@when(parsers.parse("je lance « {commande} », j'appuie deux fois sur Entrée, puis je ferme le terminal"))
def lancer_et_fermer(
	configuration: Configuration,
	execution: Execution,
	caplog: pytest.LogCaptureFixture,
	monkeypatch: pytest.MonkeyPatch,
	commande: str,
) -> None:
	sortie = io.StringIO()
	# Deux fois Entrée, puis la fin de l'entrée standard : le terminal se ferme.
	clavier = io.StringIO("\n\n")
	monkeypatch.setattr("sys.stdin", clavier)
	monkeypatch.setattr("sys.stdout", sortie)
	_lancer(configuration, execution, caplog, commande)
	execution.demande = sortie.getvalue()
	execution.entree_restante = clavier.read()


@then(parsers.parse("la maintenance se termine avec le code {code:d}"))
def code_de_sortie(execution: Execution, code: int) -> None:
	assert execution.code == code, (execution.informations, execution.erreurs)


def _sauvegardes(configuration: Configuration, repertoire: str) -> list[Path]:
	return sorted((configuration.chemin.parent / repertoire).glob("*.dump"))


@then(
	parsers.parse(
		"une sauvegarde datée de la base est dans le répertoire « {repertoire} » de la configuration,"
		" lisible par pg_restore"
	)
)
def sauvegarde(configuration: Configuration, repertoire: str) -> None:
	(fichier,) = _sauvegardes(configuration, repertoire)
	assert fichier.name == f"{configuration.base.test}-2026-10-22T08-30-00.dump"
	liste = subprocess.run(["pg_restore", "--list", str(fichier)], capture_output=True, text=True, timeout=60)
	assert (liste.returncode == 0) and ("TABLE public sonores" in liste.stdout), liste.stderr


@then("la maintenance a annoncé, dans l'ordre :")
def annonces(configuration: Configuration, execution: Execution, datatable: list[list[str]]) -> None:
	_entete, *lignes = datatable
	attendues = [ligne.strip().replace("…/", f"{configuration.chemin.parent}/") for (ligne,) in lignes]
	assert [ligne for ligne in execution.informations if not ligne.startswith("sauvegarde faite")] == [
		ligne for ligne in attendues if ligne != "sauvegarde faite"
	]
	assert any(ligne.startswith("sauvegarde faite") for ligne in execution.informations), execution.informations


@then(parsers.parse("la maintenance a annoncé « {texte} »"))
def annonce(execution: Execution, texte: str) -> None:
	assert texte in execution.informations, execution.informations


@then(parsers.parse("la maintenance a signalé « {texte} »"))
def signale(execution: Execution, texte: str) -> None:
	attendu = texte.replace("<compte>", maintenance.compte())
	assert attendu in execution.erreurs, execution.erreurs


@then("la maintenance n'a annoncé ni le schéma ni l'optimisation")
def rien_d_autre(execution: Execution) -> None:
	assert not any(("schéma" in ligne) or ("optimisée" in ligne) for ligne in execution.informations)


@then(parsers.parse("la maintenance a dit « {texte} »"))
def demande(execution: Execution, texte: str) -> None:
	assert texte in execution.demande, execution.demande


@then("la maintenance n'a rendu la main qu'à la fermeture du terminal")
def entree_lue(execution: Execution) -> None:
	assert execution.entree_restante == "", repr(execution.entree_restante)


@then(parsers.parse("la table « {table} » vient d'être nettoyée par VACUUM, et ses statistiques recalculées"))
def statistiques(configuration: Configuration, execution: Execution, table: str) -> None:
	"""Les statistiques cumulées parviennent au serveur peu après la fin du VACUUM : jusqu'à 5 secondes. Seuls un
	VACUUM et un ANALYZE lancés à la main, après le lancement de la maintenance, comptent : pas ceux d'autovacuum."""
	limite = time.monotonic() + 5
	while True:
		with psycopg.connect(host=str(configuration.base.socket), dbname=configuration.base.test) as connexion:
			ligne = connexion.execute(
				"SELECT (last_vacuum >= %s) AND (last_analyze >= %s) FROM pg_stat_user_tables WHERE relname = %s",
				(execution.debut, execution.debut, table),
			).fetchone()
		if (ligne == (True,)) or (time.monotonic() > limite):
			break
		time.sleep(0.2)
	assert ligne == (True,), ligne


@then("la base de test a toutes ses migrations")
def migrations_completes(configuration: Configuration) -> None:
	with get_backend(url_yoyo(configuration.base.socket, configuration.base.test)) as backend:
		assert len(backend.to_apply(read_migrations(str(REPERTOIRE_MIGRATIONS)))) == 0


@then(parsers.parse("« {binaire} » est un binaire du wrapper, déclaré dans pyproject.toml"))
def binaire_du_wrapper(binaire: str) -> None:
	scripts = tomllib.loads((REPERTOIRE_PROJET / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
	assert scripts[f"Machin_{binaire}"] == "machincast.maintenance:main"
	sortie = subprocess.run(
		[str(REPERTOIRE_PROJET / "bin" / "Machin"), "--binaires"], capture_output=True, text=True, timeout=30
	)
	assert binaire in sortie.stdout.split(), sortie.stdout
