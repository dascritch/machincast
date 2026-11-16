"""Étapes partagées des scénarios de l'interface : Machin player imaginaire, sur la socket d'état (https://github.com/dascritch/machincast/issues/104).

Chargé comme greffon pytest par tests/conftest.py (https://github.com/dascritch/machincast/issues/444 : découpé de
tests/interface_steps.py, par domaine).
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from pytest_bdd import given, parsers, then, when
from pytestqt.qtbot import QtBot

from machincast.player.state import REREAD_GRID, Request, StateSocket
from tests.interface_steps import Context
from tests.waiting import quiet

# ─── Machin player imaginaire, sur la socket d'état (https://github.com/dascritch/machincast/issues/104) ─────


@dataclass
class Player:
	socket: StateSocket | None = None
	published: str = ""
	"""Le dernier état publié, tel que la socket l'envoie."""
	received_list: list[Request] = field(default_factory=list)


@pytest.fixture
def player() -> Iterator[Player]:
	player = Player()
	yield player
	if player.socket is not None:
		player.socket.shut_down()


def publish(
	player: Player, state: str, ongoing: dict[str, object] | None = None, **others: dict[str, object] | None
) -> None:
	"""Un état de Machin player ; autres donne d'autres champs, comme le prochain sonore ou l'événement suivant."""
	assert player.socket is not None
	# Les arguments nommés suivent les noms du code (next_, following_event) ; le message, ceux du protocole.
	keys = {"next_": "next", "following_event": "next_event"}
	k_dict = {}
	for k, v in others.items():
		k_dict[keys.get(k, k)] = v
	message = {"state": state, "current": ongoing, "next": None, **k_dict}
	player.published = json.dumps({"version": 3, **message})
	player.socket.publish(message)


@then("Machin player a reçu la demande de relire la grille")
def requested_rereading(player: Player, qtbot: QtBot) -> None:
	"""Après une session sautée (https://github.com/dascritch/machincast/issues/273), ou une fiche enregistrée,
	supprimée ou restaurée (https://github.com/dascritch/machincast/issues/266) : une seule demande."""
	socket = player.socket
	assert socket is not None

	def received() -> bool:
		player.received_list += socket.requests()
		return player.received_list != []

	qtbot.waitUntil(received, timeout=5000)
	# Une seconde demande, envoyée juste après, aurait le temps d'arriver.
	quiet(qtbot, 100, reason="une seconde demande de relecture")
	player.received_list += socket.requests()
	assert player.received_list == [Request(command=REREAD_GRID)]


@given("la socket d'état de Machin player ouverte pour l'interface")
def opened_socket(interface: Context, player: Player) -> None:
	player.socket = StateSocket(interface.directory / "lecture.sock")
	player.socket.open_()


@given(parsers.parse("Machin player diffuse un sonore au texte public « {text} »"))
@when(parsers.parse("Machin player diffuse un sonore au texte public « {text} »"))
def broadcasts_to_public_text(player: Player, text: str) -> None:
	"""Le texte public du sonore en cours, ce que la page publique en affiche
	(https://github.com/dascritch/machincast/issues/223)."""
	ongoing = {
		"sound_id": 12,
		"type": "file",
		"artist": None,
		"title": text,
		"event": "Continue",
		"location": "/srv/musique/minuit.flac",
		"start": "2026-10-21T08:59:00+02:00",
		"duration": 214.0,
		"estimated_end": "2026-10-21T09:02:34+02:00",
		"position": 60.0,
		"progress": 0.28,
		"public_text": text,
	}
	publish(player, "playing", ongoing)
