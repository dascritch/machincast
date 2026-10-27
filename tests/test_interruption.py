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

from machincast.lecture.diffusion import EVENEMENT_AVANCE, INTERRUPTION_MANUELLE
from machincast.lecture.etat import DEMANDE_IGNOREE, demande_d_avance
from tests.etapes_diffusion import Banc, diffusion, horloge

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


def log_des_avances(base: Connexion) -> list[str]:
	return [
		str(message)
		for (message,) in base.execute(
			"SELECT message FROM log WHERE niveau = 'info' AND nature = %s ORDER BY id", (EVENEMENT_AVANCE,)
		).fetchall()
	]


def identifiant(base: Connexion, nom: str) -> int:
	"""L'identifiant de l'événement ; 0, qu'aucun n'a, pour un événement absent."""
	ligne = base.execute("SELECT id FROM evenements WHERE nom_interne = %s", (nom,)).fetchone()
	if ligne is None:
		return 0
	return int(str(ligne[0]))


# ─── Étant donné ───────────────────────────────────────────


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("j'avance l'événement suivant « {nom} »"))
def avancer_l_evenement(banc: Banc, base_vide: Connexion, nom: str) -> None:
	"""https://github.com/dascritch/machincast/issues/257 : la demande nomme l'événement suivant attendu."""
	diffusion(banc).avancer(identifiant(base_vide, nom))


@when(parsers.parse("un client de la socket d'état demande d'avancer l'événement « {nom} »"))
def demander_l_avance(banc: Banc, base_vide: Connexion, caplog: pytest.LogCaptureFixture, nom: str) -> None:
	demander(banc, caplog, demande_d_avance(identifiant(base_vide, nom)).strip())


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


@then(parsers.parse("le log note l'avance « {message} »"))
def avance_notee(base_vide: Connexion, message: str) -> None:
	assert log_des_avances(base_vide) == [message]


@then("le log ne note aucune avance")
def aucune_avance(base_vide: Connexion) -> None:
	assert log_des_avances(base_vide) == []


@then(parsers.parse("Machin lecture annonce l'événement suivant « {nom} », du « {debut} » au « {fin} »"))
def annonce_du_suivant(banc: Banc, base_vide: Connexion, nom: str, debut: str, fin: str) -> None:
	annonce = diffusion(banc)._etat(horloge(banc).maintenant(), False)["evenement_suivant"]
	attendue = {"id": identifiant(base_vide, nom), "nom": nom, "priorite": "emission", "debut": debut, "fin": fin}
	assert annonce == attendue


@then("le log ne note aucune interruption manuelle")
def aucune_interruption(base_vide: Connexion) -> None:
	assert log_des_interruptions(base_vide) == []


@then(parsers.parse("le journal du binaire a signalé « {texte} »"))
def journal_signale(caplog: pytest.LogCaptureFixture, texte: str) -> None:
	assert any((r.levelno == logging.WARNING) and (texte in r.getMessage()) for r in caplog.records), caplog.text
