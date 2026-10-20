"""Scénarios de l'analyse du prochain sonore au dernier moment (https://github.com/dascritch/machincast/issues/181).

Les étapes de la diffusion sont dans tests/etapes_diffusion.py. Machin indexation y est remplacé par un script, qui
note ses arguments un par ligne, ou plante ; le dernier scénario lance le vrai, sur la base de test.
"""

import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
from pytest_bdd import given, parsers, scenarios, then

from machincast.lecture.analyse import Analyseur, commande_d_analyse
from tests.base_test import configuration_test
from tests.etapes_diffusion import Banc, sonore

scenarios("analyse_au_dernier_moment.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
DELAI = 20.0
"""Secondes laissées à une analyse lancée pour se faire : le vrai Machin indexation charge GStreamer."""
IMITATION = """#!/bin/sh
cut -d ' ' -f 6 /proc/$$/stat > "{journal}.session"
for argument in "$@"; do
	echo "${argument}"
done >> "{journal}"
echo -- >> "{journal}"
"""
"""Machin indexation imité : chaque appel note ses arguments, un par ligne, puis « -- », et sa session."""


def attendre(condition: object, delai: float = DELAI) -> bool:
	"""Vrai dès que la condition, une fonction sans argument, est remplie ; faux au bout du délai."""
	assert callable(condition)
	fin = time.monotonic() + delai
	while time.monotonic() < fin:
		if condition():
			return True
		time.sleep(0.05)
	return bool(condition())


def appels(journal: Path) -> list[list[str]]:
	if not journal.exists():
		return []
	texte = journal.read_text(encoding="utf-8")
	return [bloc.strip().splitlines() for bloc in texte.split("--\n") if bloc.strip()]


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le sonore « {nom} » a été vérifié en entier"))
def verifie(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("UPDATE sonores SET verifie_le = %s WHERE id = %s", (datetime.now(UTC), sonore(base_vide, nom)))


@given(parsers.parse("le fichier du sonore « {nom} » a changé depuis sa vérification"))
def fichier_change(base_vide: Connexion, nom: str) -> None:
	"""La taille enregistrée n'est plus celle du fichier : il a été remplacé depuis sa vérification."""
	base_vide.execute("UPDATE sonores SET fichier_taille = fichier_taille + 1 WHERE id = %s", (sonore(base_vide, nom),))


@given("une commande d'analyse imitée", target_fixture="journal_d_analyse")
def imitee(banc: Banc, tmp_path: Path) -> Path:
	journal = tmp_path / "analyses.txt"
	script = tmp_path / "Machin_indexation"
	script.write_text(IMITATION.replace("{journal}", str(journal)), encoding="utf-8")
	script.chmod(0o755)
	banc.analyseur = Analyseur([str(script), "--audit-complet", "--sonore"])
	return journal


@given("une commande d'analyse introuvable")
def introuvable(banc: Banc, tmp_path: Path) -> None:
	banc.analyseur = Analyseur([str(tmp_path / "absent" / "Machin_indexation"), "--sonore"])


@given("une commande d'analyse qui plante")
def plante(banc: Banc, tmp_path: Path) -> None:
	script = tmp_path / "Machin_indexation"
	script.write_text("#!/bin/sh\necho 'plantage imité' >&2\nexit 1\n", encoding="utf-8")
	script.chmod(0o755)
	banc.analyseur = Analyseur([str(script), "--sonore"])


@given("Machin indexation comme commande d'analyse, sur la base de test")
def vrai_machin_indexation(banc: Banc, tmp_path: Path) -> None:
	"""La configuration des tests, recopiée avec la base de test comme base de production : sa base de test, qui doit
	en différer, en devient une autre, que Machin indexation n'ouvre pas."""
	source = configuration_test()
	texte = (
		source.chemin.read_text(encoding="utf-8")
		.replace(f'test = "{source.base.test}"', f'test = "{source.base.test}_inutilisee"')
		.replace(f'production = "{source.base.production}"', f'production = "{source.base.test}"')
	)
	assert f'production = "{source.base.test}"' in texte
	configuration = tmp_path / "machincast.toml"
	configuration.write_text(texte, encoding="utf-8")
	commande = commande_d_analyse(configuration)
	assert commande[:3] == [sys.executable, "-m", "machincast.indexation"]
	banc.analyseur = Analyseur(commande)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("l'analyse est demandée bientôt pour le sonore « {nom} », en audit complet"))
def demandee(base_vide: Connexion, journal_d_analyse: Path, nom: str) -> None:
	attendu = ["--audit-complet", "--sonore", str(sonore(base_vide, nom))]
	assert attendre(lambda: appels(journal_d_analyse) != []), "aucune analyse lancée"
	assert appels(journal_d_analyse) == [attendu]


@then("aucune analyse n'a été demandée")
def aucune(journal_d_analyse: Path) -> None:
	assert appels(journal_d_analyse) == []


@then(parsers.parse("le sonore « {nom} » a bientôt sa date de vérification complète"))
def verifie_bientot(base_vide: Connexion, nom: str) -> None:
	identifiant = sonore(base_vide, nom)

	def verifie_le() -> object:
		ligne = base_vide.execute("SELECT verifie_le FROM sonores WHERE id = %s", (identifiant,)).fetchone()
		assert ligne is not None
		return ligne[0]

	assert attendre(lambda: verifie_le() is not None), "le sonore n'a pas été vérifié"
	date = verifie_le()
	assert isinstance(date, datetime)
	assert datetime.now(UTC) - date < timedelta(seconds=DELAI)


@then("l'analyse tourne dans sa propre session, à l'abri d'un Ctrl-C dans le terminal de la diffusion")
def propre_session(journal_d_analyse: Path) -> None:
	session = journal_d_analyse.with_name(f"{journal_d_analyse.name}.session")
	assert attendre(session.exists)
	assert int(session.read_text(encoding="utf-8")) != os.getsid(0)
