"""Étapes de la boucle de diffusion de Machin lecture (https://github.com/dascritch/machincast/issues/88).

Les étapes communes aux scénarios de la diffusion sont dans tests/etapes_diffusion.py.
"""

import shutil
import signal
import subprocess
import sys
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.lecture.diffusion import installer_arret
from tests.base_test import CONFIGURATION_TEST
from tests.etapes_diffusion import Banc, Connexion, creer_sonore

scenarios("diffusion.feature")


@dataclass
class Processus:
	arret: threading.Event | None = None
	resultat: subprocess.CompletedProcess[str] | None = None


@pytest.fixture
def processus() -> Processus:
	return Processus()


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


@then(
	parsers.parse(
		"chaque passage de « {premier} » et de « {second} » note la séquence « {nom} » et son élément, au début"
		" comme à la fin"
	)
)
def passages_de_la_sequence(base_vide: Connexion, premier: str, second: str, nom: str) -> None:
	lignes = base_vide.execute(
		"SELECT a.titre, a.type_ligne::text, q.nom_interne, e.position FROM airplay a"
		" LEFT JOIN sequences q ON q.id = a.sequence_id"
		" LEFT JOIN sequences_elements e ON e.id = a.sequence_element_id AND e.sequence_id = a.sequence_id"
		" WHERE a.titre IN (%s, %s) ORDER BY a.id",
		(premier, second),
	).fetchall()
	positions = {premier: 1, second: 2}
	assert len(lignes) == 6, lignes
	assert all((sequence == nom) and (position == positions[str(titre)]) for titre, _, sequence, position in lignes), (
		lignes
	)
	assert {type_ligne for _, type_ligne, _, _ in lignes} == {"debut", "fin"}, lignes


@given("l'arrêt de la diffusion branché sur les signaux")
def arret_branche(processus: Processus) -> Iterator[None]:
	anciens = {numero: signal.getsignal(numero) for numero in (signal.SIGTERM, signal.SIGINT)}
	processus.arret = installer_arret()
	yield
	for numero, ancien in anciens.items():
		signal.signal(numero, ancien)


@when("le processus reçoit SIGTERM")
def sigterm() -> None:
	# raise_signal le délivre au fil principal, aussitôt : jamais à un fil de GStreamer, ni après la restauration
	# des gestionnaires d'origine, qui arrêterait pytest.
	signal.raise_signal(signal.SIGTERM)


@when("je lance Machin_lecture avec une configuration dont la socket n'existe pas")
def lancer_sans_base(processus: Processus, tmp_path: Path) -> None:
	configuration = tmp_path / "sans-base.toml"
	texte = CONFIGURATION_TEST.read_text(encoding="utf-8")
	configuration.write_text(
		texte.replace('socket = "/var/run/postgresql"', f'socket = "{tmp_path / "aucune-socket"}"'), encoding="utf-8"
	)
	chemin = (shutil.which("Machin_lecture")) or (str(Path(sys.executable).parent / "Machin_lecture"))
	processus.resultat = subprocess.run(
		[chemin, "--config", str(configuration)], capture_output=True, text=True, timeout=60
	)


@then("l'arrêt de la diffusion est demandé")
def arret_demande(processus: Processus) -> None:
	assert (processus.arret is not None) and (processus.arret.wait(2))


@then("il s'arrête avec le code 1, en signalant la base de données injoignable")
def code_un(processus: Processus) -> None:
	assert processus.resultat is not None
	assert processus.resultat.returncode == 1, processus.resultat.stderr
	assert "base de données injoignable" in processus.resultat.stderr
