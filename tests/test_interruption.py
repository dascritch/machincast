"""Scénarios de l'interruption manuelle de l'antenne (https://github.com/dascritch/machincast/issues/104).

La diffusion tourne sur le moteur simulé de la simulation (machincast.lecture.simulation.MoteurSimule), qui suit
l'horloge du binaire : un sonore d'une minute s'interrompt à la seconde voulue, sans attendre. Les étapes partagées de
la diffusion sont dans tests/etapes_diffusion.py.
"""

import logging
import socket
import time
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, connecter
from machincast.hasard import creer_hasard
from machincast.lecture.diffusion import INTERRUPTION_MANUELLE, Diffusion
from machincast.lecture.etat import SocketEtat
from machincast.lecture.simulation import MoteurSimule
from tests.base_test import parametres_base_test
from tests.etapes_diffusion import Banc, diffusion, horloge, passages

scenarios("interruption.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
ELEMENTS = {"le sonore": "sonore", "la séquence": "sequence", "l'événement": "evenement"}
ATTENTE = 5.0
"""Secondes qu'une demande a pour arriver par la socket d'état."""


def log_des_interruptions(base: Connexion) -> list[str]:
	return [
		str(message)
		for (message,) in base.execute(
			"SELECT message FROM log WHERE niveau = 'info' AND nature = %s ORDER BY id", (INTERRUPTION_MANUELLE,)
		).fetchall()
	]


def heure_de_fin(fin: datetime | None) -> str:
	if fin is None:
		return ""
	return f"{fin.astimezone():%H:%M:%S}"


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("chaque sonore dure {duree:d} secondes"))
def duree(base_vide: Connexion, duree: int) -> None:
	base_vide.execute("UPDATE sonores SET duree = %s", (timedelta(seconds=duree),))


@given("la socket d'état dans un répertoire temporaire")
def socket_temporaire(banc: Banc, tmp_path: Path) -> None:
	banc.etat = SocketEtat(tmp_path / "run" / "machincast" / "lecture.sock")


# ─── Quand ─────────────────────────────────────────────────


@when("la diffusion démarre sur un moteur simulé")
def demarrer(banc: Banc, base_vide: Connexion) -> None:
	banc.connexion = connecter(*parametres_base_test(), Role.LECTURE)
	banc.diffusion = Diffusion(
		banc.connexion,
		MoteurSimule(horloge(banc)),
		horloge(banc),
		creer_hasard(0),
		etat=banc.etat,
		crossfades=banc.crossfades,
	)
	banc.diffusion.demarrer()


@when(parsers.parse("la diffusion avance de {secondes:d} secondes"))
def avancer(banc: Banc, secondes: int) -> None:
	for _ in range(secondes):
		diffusion(banc).pas()
		horloge(banc).avancer(timedelta(seconds=1))


@when(parsers.re(r"j'interromps (?P<quoi>le sonore|la séquence|l'événement)"))
def interrompre(banc: Banc, quoi: str) -> None:
	diffusion(banc).interrompre(ELEMENTS[quoi])


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


@then("l'airplay montre :")
def airplay(base_vide: Connexion, datatable: list[list[str]]) -> None:
	_, *lignes = datatable
	obtenus = [
		[titre, f"{debut.astimezone():%H:%M:%S}", heure_de_fin(fin), "oui" if sans_incident else "non"]
		for titre, debut, fin, sans_incident in passages(base_vide)
	]
	assert obtenus == [[valeur.strip() for valeur in ligne] for ligne in lignes], obtenus


@then(parsers.parse("le log note l'interruption manuelle « {message} »"))
def interruption_notee(base_vide: Connexion, message: str) -> None:
	assert log_des_interruptions(base_vide) == [message]


@then("le log ne note aucune interruption manuelle")
def aucune_interruption(base_vide: Connexion) -> None:
	assert log_des_interruptions(base_vide) == []


@then(parsers.parse("le journal du binaire a signalé « {texte} »"))
def journal_signale(caplog: pytest.LogCaptureFixture, texte: str) -> None:
	assert any((r.levelno == logging.WARNING) and (texte in r.getMessage()) for r in caplog.records), caplog.text
