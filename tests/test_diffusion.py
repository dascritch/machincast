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
from pytest_bdd import given, scenarios, then, when

from machincast.lecture.diffusion import installer_arret
from tests.base_test import CONFIGURATION_TEST

scenarios("diffusion.feature")


@dataclass
class Processus:
	arret: threading.Event | None = None
	resultat: subprocess.CompletedProcess[str] | None = None


@pytest.fixture
def processus() -> Processus:
	return Processus()


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
	chemin = shutil.which("Machin_lecture") or str(Path(sys.executable).parent / "Machin_lecture")
	processus.resultat = subprocess.run(
		[chemin, "--config", str(configuration)], capture_output=True, text=True, timeout=60
	)


@then("l'arrêt de la diffusion est demandé")
def arret_demande(processus: Processus) -> None:
	assert processus.arret is not None and processus.arret.wait(2)


@then("il s'arrête avec le code 1, en signalant la base de données injoignable")
def code_un(processus: Processus) -> None:
	assert processus.resultat is not None
	assert processus.resultat.returncode == 1, processus.resultat.stderr
	assert "base de données injoignable" in processus.resultat.stderr
