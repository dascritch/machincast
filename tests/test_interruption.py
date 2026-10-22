"""Scénarios de l'interruption manuelle de l'antenne (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228).

La diffusion tourne sur le moteur simulé de la simulation (machincast.lecture.simulation.MoteurSimule), qui suit
l'horloge du binaire : un sonore d'une minute s'interrompt à la seconde voulue, sans attendre. Les étapes partagées de
la diffusion sont dans tests/etapes_diffusion.py.
"""

import logging
import socket
import time
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.lecture.diffusion import INTERRUPTION_MANUELLE
from machincast.lecture.etat import SocketEtat
from tests.etapes_diffusion import Banc

scenarios("interruption.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
ATTENTE = 5.0
"""Secondes qu'une demande a pour arriver par la socket d'état."""


def log_des_interruptions(base: Connexion) -> list[str]:
	return [
		str(message)
		for (message,) in base.execute(
			"SELECT message FROM log WHERE niveau = 'info' AND nature = %s ORDER BY id", (INTERRUPTION_MANUELLE,)
		).fetchall()
	]


# ─── Étant donné ───────────────────────────────────────────


@given("la socket d'état dans un répertoire temporaire")
def socket_temporaire(banc: Banc, tmp_path: Path) -> None:
	banc.etat = SocketEtat(tmp_path / "run" / "machincast" / "lecture.sock")


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("un client de la socket d'état demande « {demande} »"))
def demander(banc: Banc, demande: str) -> None:
	"""La demande est envoyée, puis la socket attend qu'elle arrive, ou qu'elle soit ignorée."""
	etat = banc.etat
	assert etat is not None
	with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
		client.connect(str(etat.chemin))
		client.sendall(f"{demande}\n".encode())
		# Le message d'état qu'envoie la socket à la connexion montre qu'elle sert ce client.
		client.settimeout(ATTENTE)
		client.recv(1)
		limite = time.monotonic() + ATTENTE
		while (etat._demandes.empty()) and (time.monotonic() < limite):
			time.sleep(0.01)
		# Une demande ignorée ne laisse rien à attendre : le temps de la lire suffit.
		time.sleep(0.1)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le log note l'interruption manuelle « {message} »"))
def interruption_notee(base_vide: Connexion, message: str) -> None:
	assert log_des_interruptions(base_vide) == [message]


@then("le log ne note aucune interruption manuelle")
def aucune_interruption(base_vide: Connexion) -> None:
	assert log_des_interruptions(base_vide) == []


@then(parsers.parse("le journal du binaire a signalé « {texte} »"))
def journal_signale(caplog: pytest.LogCaptureFixture, texte: str) -> None:
	assert any((r.levelno == logging.WARNING) and (texte in r.getMessage()) for r in caplog.records), caplog.text
