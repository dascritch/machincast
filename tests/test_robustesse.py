"""Scénarios de robustesse relevés au tour du code (https://github.com/dascritch/machincast/issues/187).

Les étapes de la diffusion sont dans tests/etapes_diffusion.py.
"""

import logging
import os
import socket
import subprocess
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import fiche_sonore, version
from machincast.interface.etat import ClientEtat, EtatLecture
from machincast.lecture.diffusion import diffuser
from machincast.lecture.etat import SocketEtat
from tests.etapes_diffusion import Banc, diffusion

scenarios("robustesse.feature")


@dataclass
class Robustesse:
	socket_etat: SocketEtat | None = None
	descripteurs: set[str] = field(default_factory=set)
	erreur: BaseException | None = None
	serveur: socket.socket | None = None
	connexion: socket.socket | None = None
	client: ClientEtat | None = None
	recus: list[EtatLecture] = field(default_factory=list)
	date: datetime | None = None


@pytest.fixture
def robustesse() -> Iterator[Robustesse]:
	contexte = Robustesse()
	yield contexte
	for ouvert in (contexte.connexion, contexte.serveur):
		if ouvert is not None:
			ouvert.close()
	if contexte.client is not None:
		contexte.client.fermer()


def _descripteurs() -> set[str]:
	return set(os.listdir("/proc/self/fd"))


# ─── Socket d'état de Machin lecture ──────────────────────


@given("une socket d'état dont le chemin est trop long pour le système")
def socket_trop_longue(robustesse: Robustesse, tmp_path: Path) -> None:
	# Une socket Unix a un chemin de 108 octets au plus.
	robustesse.socket_etat = SocketEtat(tmp_path / ("s" * 120) / "lecture.sock")


@when("Machin lecture tente de l'ouvrir")
def ouvrir(robustesse: Robustesse) -> None:
	assert robustesse.socket_etat is not None
	robustesse.descripteurs = _descripteurs()
	try:
		robustesse.socket_etat.ouvrir()
	except OSError as erreur:
		robustesse.erreur = erreur


@then("l'ouverture échoue")
def ouverture_echouee(robustesse: Robustesse) -> None:
	assert isinstance(robustesse.erreur, OSError), robustesse.erreur


@then("aucun descripteur de fichier n'est resté ouvert")
def aucun_descripteur(robustesse: Robustesse) -> None:
	assert _descripteurs() == robustesse.descripteurs


@given("la socket d'état de la diffusion dans un répertoire temporaire")
def socket_de_la_diffusion(banc: Banc, tmp_path: Path) -> None:
	banc.etat = SocketEtat(tmp_path / "run" / "lecture.sock")


@when("une erreur interrompt la boucle de diffusion")
def erreur_dans_la_boucle(banc: Banc, robustesse: Robustesse) -> None:
	"""La diffusion a déjà démarré : la boucle de Machin lecture reprend au premier pas, qui échoue."""
	lancee = diffusion(banc)

	def echouer() -> None:
		raise RuntimeError("base de données perdue")

	lancee.demarrer = lambda: None  # type: ignore[method-assign]
	lancee.pas = echouer  # type: ignore[method-assign]
	try:
		diffuser(lancee, threading.Event(), pause=0)
	except RuntimeError as erreur:
		robustesse.erreur = erreur


@then("l'erreur remonte jusqu'à Machin lecture")
def erreur_remontee(robustesse: Robustesse) -> None:
	assert isinstance(robustesse.erreur, RuntimeError), robustesse.erreur


@then("la socket d'état est effacée, et plus rien n'y répond")
def socket_fermee(banc: Banc) -> None:
	assert banc.etat is not None
	chemin = banc.etat.chemin
	assert not chemin.exists()
	with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as essai, pytest.raises(OSError):
		essai.connect(str(chemin))


# ─── Client de la socket d'état, dans l'interface ─────────


@given("un serveur de socket d'état de test")
def serveur_de_test(robustesse: Robustesse, tmp_path: Path) -> None:
	serveur = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	serveur.bind(str(tmp_path / "etat.sock"))
	serveur.listen()
	robustesse.serveur = serveur


@when("l'interface s'y connecte")
def client_connecte(robustesse: Robustesse, qtbot: QtBot, tmp_path: Path) -> None:
	assert robustesse.serveur is not None
	client = ClientEtat(tmp_path / "etat.sock")
	client.etat_recu.connect(robustesse.recus.append)
	client.connecter()
	robustesse.client = client
	robustesse.serveur.settimeout(5)
	robustesse.connexion, _ = robustesse.serveur.accept()


@when(parsers.parse("le serveur envoie {nombre:d} octets sans fin de ligne, puis un message complet"))
def envoyer_trop(robustesse: Robustesse, qtbot: QtBot, caplog: pytest.LogCaptureFixture, nombre: int) -> None:
	assert robustesse.connexion is not None
	caplog.set_level(logging.WARNING, logger="machincast")
	robustesse.connexion.sendall(b"x" * nombre)
	# L'interface lit d'abord les octets sans fin de ligne, puis la suite.
	qtbot.waitUntil(lambda: any("trop long" in enregistrement.getMessage() for enregistrement in caplog.records))
	robustesse.connexion.sendall(b'\n{"etat": "silence", "en_cours": null, "prochain": null}\n')
	qtbot.waitUntil(lambda: any(etat.etat == "silence" for etat in robustesse.recus), timeout=5000)


@then("l'interface a ignoré les octets en trop, en le signalant")
def octets_ignores(robustesse: Robustesse, caplog: pytest.LogCaptureFixture) -> None:
	assert robustesse.client is not None
	assert len(robustesse.client.tampon_en_attente()) == 0
	assert any("trop long" in enregistrement.getMessage() for enregistrement in caplog.records), caplog.records


@then("elle a reçu le message complet")
def message_recu(robustesse: Robustesse) -> None:
	assert [etat.etat for etat in robustesse.recus if etat.etat == "silence"] == ["silence"]


# ─── Commandes système de l'interface ─────────────────────


def _remplacer_la_commande(monkeypatch: pytest.MonkeyPatch, cas: str, sortie: str) -> None:
	def executer(commande: list[str], **options: object) -> subprocess.CompletedProcess[str]:
		assert options.get("timeout") is not None, "commande sans délai"
		if cas == "ne répond pas":
			raise subprocess.TimeoutExpired(commande, float(str(options["timeout"])))
		if cas == "n'existe pas sur le poste":
			raise FileNotFoundError(commande[0])
		return subprocess.CompletedProcess(commande, 0, sortie, "")

	monkeypatch.setattr(subprocess, "run", executer)


@when(parsers.parse("la fiche d'un sonore demande la date de création de son fichier, et que stat {cas}"))
def naissance(robustesse: Robustesse, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, cas: str) -> None:
	_remplacer_la_commande(monkeypatch, cas, "?\n")
	robustesse.date = fiche_sonore._naissance(tmp_path)


@then("la date de création est inconnue")
def creation_inconnue(robustesse: Robustesse) -> None:
	assert robustesse.date is None


@when(parsers.parse("Aide → Version demande la date du dernier commit, et que git {cas}"))
def dernier_commit(robustesse: Robustesse, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, cas: str) -> None:
	(tmp_path / ".git").mkdir()
	_remplacer_la_commande(monkeypatch, cas, "\n")
	robustesse.date = version.derniere_modification(tmp_path)


@then("la date du dernier commit est inconnue")
def commit_inconnu(robustesse: Robustesse) -> None:
	assert robustesse.date is None
