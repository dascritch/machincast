"""Scénarios des sessions sautées, à la diffusion (https://github.com/dascritch/machincast/issues/273).

La diffusion tourne sur le moteur simulé, qui suit l'horloge du binaire. Les étapes partagées de la diffusion sont dans
tests/etapes_diffusion.py ; une demande arrive par une vraie socket d'état, comme dans test_interruption.py.
"""

import socket
import time
from datetime import date
from pathlib import Path

import psycopg
from pytest_bdd import given, parsers, scenarios, when

from machincast.lecture.etat import SocketEtat, demande_de_relire_la_grille
from machincast.lecture.grille import JOURS
from tests.etapes_diffusion import Banc

scenarios("sessions_sautees.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
ATTENTE = 5.0
"""Secondes qu'une demande a pour arriver par la socket d'état."""


@given("la socket d'état dans un répertoire temporaire")
def socket_temporaire(banc: Banc, tmp_path: Path) -> None:
	banc.etat = SocketEtat(tmp_path / "run" / "machincast" / "lecture.sock")


@given(parsers.re(r"l'émission « (?P<nom>[^»]+) » revient (?P<jours>chaque .+)"))
def recurrence(base_vide: Connexion, nom: str, jours: str) -> None:
	noms = [jour.strip() for jour in jours.replace("chaque", "").split(" et ")]
	assert all(jour in JOURS for jour in noms), noms
	base_vide.execute("UPDATE evenements SET jours_recurrence = %s WHERE nom_interne = %s", (noms, nom))


@given(parsers.parse("la session du {jour} de l'événement « {nom} » est rétablie"))
def retablir(base_vide: Connexion, jour: str, nom: str) -> None:
	base_vide.execute(
		"DELETE FROM evenements_sauts"
		" WHERE jour = %s AND evenement_id = (SELECT id FROM evenements WHERE nom_interne = %s)",
		(date.fromisoformat(jour), nom),
	)


@when("l'interface demande à Machin lecture de relire la grille")
def demander(banc: Banc) -> None:
	"""La demande est envoyée, puis la socket attend qu'elle arrive."""
	etat = banc.etat
	assert etat is not None
	with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
		client.connect(str(etat.chemin))
		client.sendall(demande_de_relire_la_grille().encode())
		client.settimeout(ATTENTE)
		client.recv(1)
		limite = time.monotonic() + ATTENTE
		while (etat._demandes.empty()) and (time.monotonic() < limite):
			time.sleep(0.01)
	assert not etat._demandes.empty()
