"""Scénarios d'un périphérique audio qui ne répond plus (https://github.com/dascritch/machincast/issues/259).

Le serveur audio simulé remplace Gst.Element.set_state : tant qu'il ne répond plus, chaque changement d'état d'un
pipeline attend qu'il réponde de nouveau, et note qui l'a demandé. Une demande faite dans le fil de l'interface est une
faute : elle la figerait. Le serveur répond toujours de nouveau à la fin du scénario, pour libérer les fils qui
l'attendent.
"""

import re
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import gi
import pytest
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # noqa: E402

from tests.etapes_interface import Contexte  # noqa: E402
from tests.etapes_preecoute import DELAI, accueil, fenetre_de_preecoute  # noqa: E402

scenarios("peripheriques_bloques.feature")

ATTENTE_AU_PLUS = 3.0
"""Secondes au plus qu'une demande attend le serveur, pour qu'un scénario qui échoue ne reste pas bloqué."""
INTERFACE = Path(__file__).parent.parent / "src" / "machincast" / "interface"
SET_STATE = re.compile(r"\.set_state\(")


@dataclass
class ServeurAudio:
	repond: threading.Event = field(default_factory=threading.Event)
	suivi: bool = False
	"""Le serveur a cessé de répondre au moins une fois : ses demandes sont notées."""
	demandes: list[tuple[Gst.Element, Gst.State]] = field(default_factory=list)
	"""Les changements d'état demandés depuis que le serveur a cessé de répondre, dans l'ordre."""
	attentes_de_l_interface: list[Gst.State] = field(default_factory=list)
	"""Ceux que le fil de l'interface a demandés : il les a attendus."""
	pipeline: Gst.Element | None = None
	"""Le pipeline de la pré-écoute, quand le serveur a cessé de répondre."""


@pytest.fixture
def serveur(monkeypatch: pytest.MonkeyPatch) -> Iterator[ServeurAudio]:
	serveur = ServeurAudio()
	serveur.repond.set()
	original: Callable[[Gst.Element, Gst.State], Gst.StateChangeReturn] = Gst.Element.set_state

	def set_state(element: Gst.Element, etat: Gst.State) -> Gst.StateChangeReturn:
		if serveur.suivi:
			serveur.demandes.append((element, etat))
		if not serveur.repond.is_set():
			if threading.current_thread() is threading.main_thread():
				serveur.attentes_de_l_interface.append(etat)
			serveur.repond.wait(ATTENTE_AU_PLUS)
		return original(element, etat)

	monkeypatch.setattr(Gst.Element, "set_state", set_state)
	yield serveur
	serveur.repond.set()


# ─── Quand ─────────────────────────────────────────────────


@when("le serveur audio ne répond plus")
def ne_repond_plus(interface: Contexte, serveur: ServeurAudio) -> None:
	if (interface.fenetre is not None) and (interface.fenetre.preecoute is not None):
		serveur.pipeline = interface.fenetre.preecoute.lecteur._pipeline
	serveur.suivi = True
	serveur.repond.clear()


@when("le serveur audio répond de nouveau")
def repond(serveur: ServeurAudio) -> None:
	serveur.repond.set()


@when(parsers.parse("la sortie de la pré-écoute signale l'erreur « {message} »"))
def erreur_de_sortie(interface: Contexte, message: str) -> None:
	pipeline = fenetre_de_preecoute(interface).lecteur._pipeline
	assert pipeline is not None
	erreur = GLib.Error.new_literal(Gst.ResourceError.quark(), message, Gst.ResourceError.WRITE)
	pipeline.post_message(Gst.Message.new_error(pipeline, erreur, "serveur audio simulé"))


# ─── Alors ─────────────────────────────────────────────────


@then("l'interface n'a jamais attendu le serveur audio")
def jamais_attendu(serveur: ServeurAudio) -> None:
	assert serveur.attentes_de_l_interface == []


@then("le pipeline de la pré-écoute est bientôt arrêté")
def arrete(qtbot: QtBot, serveur: ServeurAudio) -> None:
	pipeline = serveur.pipeline
	assert pipeline is not None

	def a_l_arret() -> bool:
		demande = any((element is pipeline) and (etat == Gst.State.NULL) for element, etat in serveur.demandes)
		_retour, etat, _attendu = pipeline.get_state(0)
		return (demande) and (etat == Gst.State.NULL)

	qtbot.waitUntil(a_l_arret, timeout=DELAI)


@then("le pipeline de la pré-écoute est passé, dans l'ordre, en pause, en lecture, puis à l'arrêt")
def dans_l_ordre(serveur: ServeurAudio) -> None:
	etats = [etat for element, etat in serveur.demandes if element is serveur.pipeline]
	assert etats == [Gst.State.PAUSED, Gst.State.PLAYING, Gst.State.NULL], etats


@then("le port de monitoring de l'antenne est bientôt réessayé")
def reessaye(interface: Contexte, qtbot: QtBot, serveur: ServeurAudio) -> None:
	qtbot.waitUntil(lambda: Gst.State.PLAYING in [etat for _e, etat in serveur.demandes], timeout=DELAI)
	assert accueil(interface).moniteur.actif()


@then("aucun autre module de l'interface n'appelle set_state")
def seul_etats() -> None:
	fautes = [
		str(chemin.relative_to(INTERFACE))
		for chemin in sorted(INTERFACE.rglob("*.py"))
		if (chemin.name != "etats.py") and (SET_STATE.search(chemin.read_text(encoding="utf-8")))
	]
	assert fautes == [], fautes
