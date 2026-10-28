"""Scénarios de la liste des périphériques audio (https://github.com/dascritch/machincast/issues/289).

Le moniteur de périphériques est imité par MoniteurImite, à la place de GStreamer dans machincast.audio ; le dernier
scénario liste, avec GStreamer, les périphériques du poste dans des processus à part : un processus tué par un signal,
ou qui ne rend pas la main, compte comme une chute.
"""

import logging
import subprocess
import sys
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import audio

scenarios("peripheriques_liste.feature")

DEMARRE = 1
"""Le type de message DEVICE_MONITOR_STARTED de l'imitation."""
DELAI_DES_PROCESSUS = 120.0
"""Secondes laissées à un processus pour toutes ses listes."""


class BusImite:
	def __init__(self, moniteur: "MoniteurImite") -> None:
		self.moniteur = moniteur

	def timed_pop_filtered(self, delai: int, types: int) -> object | None:
		assert types == DEMARRE
		assert delai == int(audio.DEMARRAGE_DU_MONITEUR * GstImite.SECOND)
		self.moniteur.appels.append("attendre le démarrage")
		if not self.moniteur.annonce:
			return None
		return object()


class MoniteurImite:
	def __init__(self, demarre: bool, annonce: bool) -> None:
		self.demarre = demarre
		self.annonce = annonce
		self.appels: list[str] = []
		self.appareils = [object(), object()]

	def add_filter(self, classes: str, caps: object) -> None:
		assert classes == audio.CLASSE_DES_SORTIES

	def start(self) -> bool:
		self.appels.append("start")
		return self.demarre

	def get_bus(self) -> BusImite:
		return BusImite(self)

	def get_devices(self) -> list[object]:
		self.appels.append("get_devices")
		return self.appareils

	def stop(self) -> None:
		self.appels.append("stop")


class GstImite:
	SECOND = 1_000_000_000

	def __init__(self, moniteur: MoniteurImite, avec_message: bool) -> None:
		self.crees = 0
		"""Les moniteurs créés : chacun est le même moniteur imité, qui note tous les appels."""

		def nouveau() -> MoniteurImite:
			self.crees += 1
			return moniteur

		self.DeviceMonitor = SimpleNamespace(new=nouveau)
		self.MessageType = SimpleNamespace()
		if avec_message:
			self.MessageType = SimpleNamespace(DEVICE_MONITOR_STARTED=DEMARRE)

	def init(self, arguments: object) -> None:
		pass


@pytest.fixture
def contexte() -> SimpleNamespace:
	return SimpleNamespace(moniteur=None, gst=None, appareils=None, chutes=[])


@given(
	parsers.re(
		r"un moniteur de périphériques imité, (?P<cas>qui annonce son démarrage|qui n'annonce pas son démarrage"
		r"|d'un GStreamer sans message de démarrage|qui ne démarre pas)"
	)
)
def moniteur_imite(contexte: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, cas: str) -> None:
	moniteur = MoniteurImite(demarre=cas != "qui ne démarre pas", annonce=cas == "qui annonce son démarrage")
	contexte.moniteur = moniteur
	contexte.gst = GstImite(moniteur, avec_message=cas != "d'un GStreamer sans message de démarrage")
	monkeypatch.setattr(audio, "Gst", contexte.gst)
	# Le moniteur du processus, s'il y en a déjà un, n'est pas celui du scénario.
	monkeypatch.setattr(audio, "_moniteur", None)


@when("je liste les appareils du poste")
def lister(contexte: SimpleNamespace) -> None:
	contexte.appareils = audio.appareils()


@when(parsers.parse("{processus:d} processus listent chacun {listes:d} fois les périphériques du poste"))
def lister_en_boucle(contexte: SimpleNamespace, processus: int, listes: int) -> None:
	code = f"from machincast import audio\nfor _ in range({listes}):\n\taudio.appareils()\n"
	for _ in range(processus):
		try:
			fini = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=DELAI_DES_PROCESSUS)
		except subprocess.TimeoutExpired:
			contexte.chutes.append("sans réponse")
			continue
		if fini.returncode != 0:
			contexte.chutes.append(f"code {fini.returncode} : {fini.stderr.decode(errors='replace')[-300:]}")


@then(parsers.re(r"le moniteur imité a reçu (?P<appels>«.+»)"))
def appels_recus(contexte: SimpleNamespace, appels: str) -> None:
	assert contexte.moniteur.appels == appels.strip("« »").split(" », « ")


@then("la liste des appareils est celle du moniteur imité")
def liste_du_moniteur(contexte: SimpleNamespace) -> None:
	assert contexte.appareils == contexte.moniteur.appareils


@then(parsers.re(r"(?:un seul moniteur imité a été créé|(?P<nombre>\d+) moniteurs imités ont été créés)"))
def moniteurs_crees(contexte: SimpleNamespace, nombre: str | None) -> None:
	assert contexte.gst.crees == int((nombre) or ("1"))


@then("la liste des appareils est vide")
def liste_vide(contexte: SimpleNamespace) -> None:
	assert contexte.appareils == []


@then("le journal avertit que le moniteur de périphériques n'a pas fini de démarrer")
def avertissement(caplog: pytest.LogCaptureFixture) -> None:
	messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
	assert any(("moniteur de périphériques" in m) and ("pas fini de démarrer" in m) for m in messages), messages


@then("chaque processus a rendu la main normalement")
def sans_chute(contexte: SimpleNamespace) -> None:
	assert contexte.chutes == []
