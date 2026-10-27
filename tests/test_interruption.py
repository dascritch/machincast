"""Scénarios de l'interruption manuelle de l'antenne (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228).

La diffusion tourne sur le moteur simulé de la simulation (machincast.lecture.simulation.MoteurSimule), qui suit
l'horloge du binaire : un sonore d'une minute s'interrompt à la seconde voulue, sans attendre. Les étapes partagées de
la diffusion sont dans tests/etapes_diffusion.py.
"""

import logging
import socket
import time

import psycopg
import pytest
from pytest_bdd import parsers, scenarios, then, when

from machincast.lecture.diffusion import INTERRUPTION_MANUELLE
from machincast.lecture.etat import DEMANDE_IGNOREE
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


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("un client de la socket d'état demande « {demande} »"))
def demander(banc: Banc, caplog: pytest.LogCaptureFixture, demande: str) -> None:
	"""La demande est envoyée, puis le scénario attend qu'elle arrive, ou que le journal du binaire dise qu'elle est
	ignorée : jamais la fin d'un délai (https://github.com/dascritch/machincast/issues/280)."""
	etat = banc.etat
	assert etat is not None

	def ignoree() -> bool:
		return any(DEMANDE_IGNOREE in r.getMessage() for r in caplog.records)

	with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
		client.connect(str(etat.chemin))
		client.sendall(f"{demande}\n".encode())
		# Le message d'état qu'envoie la socket à la connexion montre qu'elle sert ce client.
		client.settimeout(ATTENTE)
		client.recv(1)
		limite = time.monotonic() + ATTENTE
		while (etat._demandes.empty()) and (not ignoree()) and (time.monotonic() < limite):
			time.sleep(0.01)


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
