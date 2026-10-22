"""Scénarios de l'interruption de l'antenne depuis l'interface (https://github.com/dascritch/machincast/issues/104).

Une vraie socket d'état (machincast.lecture.etat.SocketEtat), là où l'interface la cherche, publie l'état d'un Machin
lecture imaginaire et reçoit les demandes de l'interface. Les étapes de la fenêtre sont dans tests/etapes_interface.py.
"""

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from PySide6.QtGui import QAction
from PySide6.QtNetwork import QLocalSocket
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import interruption
from machincast.interface.etat import lire_message
from machincast.lecture.etat import Demande, SocketEtat
from tests.etapes_interface import Contexte, fenetre

scenarios("interruption_interface.feature")

ATTENTE = 5000
"""Millisecondes qu'un état ou une demande a pour arriver."""


@dataclass
class Lecteur:
	socket: SocketEtat | None = None
	publie: str = ""
	"""Le dernier état publié, tel que la socket l'envoie."""
	recues: list[Demande] = field(default_factory=list)


@pytest.fixture
def lecteur() -> Iterator[Lecteur]:
	lecteur = Lecteur()
	yield lecteur
	if lecteur.socket is not None:
		lecteur.socket.fermer()


def publier(lecteur: Lecteur, etat: str, en_cours: dict[str, object] | None = None) -> None:
	assert lecteur.socket is not None
	message = {"etat": etat, "en_cours": en_cours, "prochain": None}
	lecteur.publie = json.dumps({"version": 1, **message})
	lecteur.socket.publier(message)


def entrees(interface: Contexte) -> dict[str, QAction]:
	return fenetre(interface).interruptions


# ─── Étant donné ───────────────────────────────────────────


@given("la socket d'état de Machin lecture ouverte pour l'interface")
def socket_ouverte(interface: Contexte, lecteur: Lecteur) -> None:
	lecteur.socket = SocketEtat(interface.repertoire / "lecture.sock")
	lecteur.socket.ouvrir()


@given(
	parsers.re(
		r"Machin lecture diffuse « (?P<titre>[^»]+) »(?:, de la séquence « (?P<sequence>[^»]+) »)?,"
		r" dans (?P<fil>le fil musical )?« (?P<evenement>[^»]+) »"
	)
)
def diffuse(lecteur: Lecteur, titre: str, sequence: str | None, fil: str | None, evenement: str) -> None:
	"""Un événement sans précision est une émission."""
	en_cours = {
		"sonore": 12,
		"type": "fichier",
		"artiste": None,
		"titre": titre,
		"evenement": evenement,
		"evenement_priorite": "emission" if fil is None else "fil_musical",
		"sequence": sequence,
		"emplacement": "/srv/musique/minuit.flac",
		"debut": "2026-10-21T08:59:00+02:00",
		"duree": 214.0,
		"fin_estimee": "2026-10-21T09:02:34+02:00",
		"position": 60.0,
		"progression": 0.28,
	}
	publier(lecteur, "diffusion", en_cours)


@given("Machin lecture est en silence")
@when("Machin lecture passe en silence")
def en_silence(lecteur: Lecteur) -> None:
	publier(lecteur, "silence")


@given("Machin lecture s'est arrêté")
def arrete(lecteur: Lecteur) -> None:
	publier(lecteur, "arret")


# ─── Quand ─────────────────────────────────────────────────


@when("l'interface a reçu l'état de Machin lecture")
def etat_recu(interface: Contexte, lecteur: Lecteur, qtbot: QtBot) -> None:
	"""Les entrées montrent ce que propose le dernier état publié."""
	attendues = interruption.proposer(lire_message(lecteur.publie))

	def a_jour() -> bool:
		return all(
			(action.isEnabled() == attendues[element].active) and (action.toolTip() == attendues[element].infobulle)
			for element, action in entrees(interface).items()
		)

	qtbot.waitUntil(a_jour, timeout=ATTENTE)


@when(parsers.parse("Machin lecture ferme sa socket d'état, juste avant que je choisisse « {entree} »"))
def socket_fermee_avant_le_choix(interface: Contexte, lecteur: Lecteur, qtbot: QtBot, entree: str) -> None:
	"""Le choix arrive avant que l'interface ait vu la socket se fermer : l'entrée est encore active."""
	assert lecteur.socket is not None
	lecteur.socket.fermer()
	lecteur.socket = None
	client = fenetre(interface).accueil.client
	qtbot.waitUntil(lambda: client._socket.state() != QLocalSocket.LocalSocketState.ConnectedState, timeout=ATTENTE)
	(action,) = [action for action in entrees(interface).values() if action.text() == entree]
	action.setEnabled(True)
	action.trigger()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("les interruptions du menu « {menu} » sont :"))
def interruptions(interface: Contexte, menu: str, datatable: list[list[str]]) -> None:
	_, *lignes = datatable
	assert menu == "Diffusion"
	menu_diffusion = fenetre(interface).menu_diffusion
	obtenues = [
		[action.text(), "active" if action.isEnabled() else "inactive", action.toolTip()]
		for action in menu_diffusion.actions()
		if action in entrees(interface).values()
	]
	assert obtenues == [[valeur.strip() for valeur in ligne] for ligne in lignes]


@then("aucune interruption n'est active")
def aucune_active(interface: Contexte) -> None:
	assert not any(action.isEnabled() for action in entrees(interface).values())


@then(parsers.parse("Machin lecture a reçu la demande d'interrompre « {element} »"))
def demande_recue(lecteur: Lecteur, qtbot: QtBot, element: str) -> None:
	socket = lecteur.socket
	assert socket is not None

	def recue() -> bool:
		lecteur.recues += socket.demandes()
		return lecteur.recues != []

	qtbot.waitUntil(recue, timeout=ATTENTE)
	time.sleep(0.1)
	lecteur.recues += socket.demandes()
	assert lecteur.recues == [Demande(element)]
