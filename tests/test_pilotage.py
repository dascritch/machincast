"""Scénarios du pilotage de la diffusion depuis l'interface (https://github.com/dascritch/machincast/issues/25).

Les étapes de la fenêtre et de ses menus sont dans tests/etapes_interface.py. systemctl et le terminal du poste sont
remplacés par des imitations, en tête du PATH : un script qui note ses arguments, et répond selon les variables
d'environnement que règle le scénario.
"""

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import REPERTOIRE_PROJET
from machincast.installation import Compte, unite_systemd
from machincast.interface import pilotage
from machincast.interface.pilotage import configuration_du_service
from tests.etapes_interface import Contexte, fenetre, fichier_de_configuration, menu_nomme

scenarios("pilotage.feature")

SYSTEMCTL = """#!/bin/sh
echo "$*" >> "${MACHINCAST_TEST_SYSTEMCTL}"
if [ "$1" = show ]; then
	case "$*" in *LoadState*) echo "LoadState=$(cat "${MACHINCAST_TEST_SERVICE}/charge")" ;; esac
	case "$*" in *ActiveState*) echo "ActiveState=$(cat "${MACHINCAST_TEST_SERVICE}/actif")" ;; esac
	exit 0
fi
if [ -n "${MACHINCAST_TEST_ERREUR}" ]; then
	echo "${MACHINCAST_TEST_ERREUR}" >&2
	exit 4
fi
case "$1" in
	start | restart) echo active > "${MACHINCAST_TEST_SERVICE}/actif" ;;
	stop) echo inactive > "${MACHINCAST_TEST_SERVICE}/actif" ;;
esac
"""
"""systemctl imité : « show » donne les propriétés demandées de l'état du service, noté dans deux fichiers ; les
autres verbes le changent, ou échouent avec l'erreur et le code de systemctl pour une autorisation refusée (4)."""
TERMINAL = """#!/bin/sh
if [ -e "${MACHINCAST_TEST_ESSAI}" ]; then echo arrêtée; else echo aucune; fi > "${MACHINCAST_TEST_TERMINAL}.essai"
for argument in "$@"; do
	echo "${argument}"
done > "${MACHINCAST_TEST_TERMINAL}"
"""
"""Un terminal imité : il note ses arguments, un par ligne, et si une diffusion d'essai s'était arrêtée avant."""
LECTEUR_D_ESSAI = """
import signal, sys, time
from pathlib import Path
from machincast.lecture.etat import SocketEtat

socket = SocketEtat(Path(sys.argv[1]))
socket.ouvrir()
socket.publier({"horodatage": "2026-10-20T16:40:00+02:00", "etat": "diffusion", "en_cours": None, "prochain": None})


def arreter(_numero, _cadre):
	# Comme Machin lecture : un dernier état pendant que le passage en cours se termine, puis la socket se ferme.
	socket.publier({"horodatage": "2026-10-20T16:40:01+02:00", "etat": "blanc", "en_cours": None, "prochain": None})
	time.sleep(0.5)
	Path(sys.argv[2]).write_text("SIGTERM", encoding="utf-8")
	socket.fermer()
	sys.exit(0)


signal.signal(signal.SIGTERM, arreter)
while True:
	time.sleep(1)
"""
"""Un Machin lecture lancé à la main : il annonce la diffusion sur sa socket d'état, s'arrête proprement à SIGTERM."""
ETATS = {"arrêté": "inactive", "en marche": "active", "en échec": "failed"}


class Poste:
	def __init__(self, repertoire: Path) -> None:
		self.commandes = repertoire / "commandes"
		self.commandes.mkdir()
		self.systemctl = repertoire / "systemctl.log"
		self.terminal = repertoire / "terminal.log"
		self.service = repertoire / "service"
		self.service.mkdir()
		self.essai: subprocess.Popen[bytes] | None = None
		self.arret_de_l_essai = repertoire / "essai.signal"

	def imiter(self, nom: str, script: str) -> None:
		chemin = self.commandes / nom
		chemin.write_text(script, encoding="utf-8")
		chemin.chmod(0o755)

	def regler(self, charge: str, actif: str) -> None:
		(self.service / "charge").write_text(f"{charge}\n", encoding="utf-8")
		(self.service / "actif").write_text(f"{actif}\n", encoding="utf-8")

	def appels(self) -> list[str]:
		if not self.systemctl.exists():
			return []
		return self.systemctl.read_text(encoding="utf-8").splitlines()


@pytest.fixture
def poste(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Poste]:
	imite = Poste(tmp_path)
	imite.imiter("systemctl", SYSTEMCTL)
	monkeypatch.setenv("PATH", f"{imite.commandes}{os.pathsep}{os.environ['PATH']}")
	monkeypatch.setenv("MACHINCAST_TEST_SYSTEMCTL", str(imite.systemctl))
	monkeypatch.setenv("MACHINCAST_TEST_TERMINAL", str(imite.terminal))
	monkeypatch.setenv("MACHINCAST_TEST_SERVICE", str(imite.service))
	monkeypatch.setenv("MACHINCAST_TEST_ESSAI", str(imite.arret_de_l_essai))
	monkeypatch.setenv("MACHINCAST_TEST_ERREUR", "")
	yield imite
	if imite.essai is not None:
		imite.essai.kill()
		imite.essai.wait()


@given(parsers.re(r"le service de diffusion installé, (?P<etat>arrêté|en marche|en échec)"))
def service_installe(poste: Poste, etat: str) -> None:
	poste.regler("loaded", ETATS[etat])


@given("le service de diffusion non installé")
def service_absent(poste: Poste) -> None:
	poste.regler("not-found", "inactive")


@given(parsers.parse("systemctl refuse en disant « {erreur} »"))
def refus(monkeypatch: pytest.MonkeyPatch, erreur: str) -> None:
	monkeypatch.setenv("MACHINCAST_TEST_ERREUR", erreur)


@given(parsers.parse("le terminal « {nom} » du poste"))
def terminal(poste: Poste, nom: str) -> None:
	poste.imiter(nom, TERMINAL)


@given("aucun terminal sur le poste")
def sans_terminal(poste: Poste, monkeypatch: pytest.MonkeyPatch) -> None:
	"""Seules les commandes imitées restent dans le PATH : aucun terminal n'y est."""
	monkeypatch.setenv("PATH", str(poste.commandes))


@given("la maintenance de la base non confirmée")
def maintenance_refusee(interface: Contexte) -> None:
	interface.maintenance = False


@given("une diffusion d'essai qui tourne, lancée à la main")
def diffusion_d_essai(interface: Contexte, poste: Poste) -> None:
	"""Dans un processus à part, sur la socket d'état où l'interface la cherche : c'est lui qu'arrête SIGTERM."""
	socket = interface.repertoire / "lecture.sock"
	poste.essai = subprocess.Popen([sys.executable, "-c", LECTEUR_D_ESSAI, str(socket), str(poste.arret_de_l_essai)])


@when("le service de diffusion passe en marche")
def en_marche(poste: Poste) -> None:
	poste.regler("loaded", "active")


@when("le service de diffusion s'installe, arrêté")
def installation_du_service(poste: Poste) -> None:
	"""./install.sh --service, lancé pendant que l'interface est ouverte."""
	poste.regler("loaded", "inactive")


@when(parsers.parse("j'ouvre le menu « {menu} »"))
def ouvrir_le_menu(interface: Contexte, menu: str) -> None:
	menu_nomme(interface, menu).aboutToShow.emit()


@when("l'état du binaire lecture est bientôt « En diffusion » sur l'accueil")
def diffusion_sur_l_accueil(interface: Contexte, qtbot: QtBot) -> None:
	etiquette = fenetre(interface).accueil.ui.etat_lecture
	qtbot.waitUntil(lambda: etiquette.text() == "En diffusion", timeout=5000)


@then(parsers.parse("systemctl a reçu bientôt « {appel} »"))
def appel_recu(poste: Poste, qtbot: QtBot, appel: str) -> None:
	qtbot.waitUntil(lambda: appel in poste.appels(), timeout=5000)


@then("systemctl n'a reçu que des demandes d'état")
def demandes_d_etat(poste: Poste) -> None:
	appels = poste.appels()
	assert (appels) and (all(appel.startswith("show ") for appel in appels)), appels


@then(parsers.parse("la barre d'état annonce bientôt « {texte} »"))
def annonce_bientot(interface: Contexte, qtbot: QtBot, texte: str) -> None:
	barre = fenetre(interface).statusBar()
	qtbot.waitUntil(lambda: barre.currentMessage() == texte, timeout=5000)


@then("la barre d'état ne signale pas d'installation à terminer")
def sans_signal(interface: Contexte) -> None:
	assert not fenetre(interface).sans_service.isVisibleTo(fenetre(interface))


@then(parsers.parse("la barre d'état signale « {texte} », avec l'infobulle « {infobulle} »"))
def signal(interface: Contexte, texte: str, infobulle: str) -> None:
	etiquette = fenetre(interface).sans_service
	assert etiquette.isVisibleTo(fenetre(interface))
	assert (etiquette.text(), etiquette.toolTip()) == (texte, infobulle)


@then("le terminal a lancé bientôt Machin lecture, comme le service")
def lance_dans_le_terminal(poste: Poste, qtbot: QtBot) -> None:
	"""La commande de l'ExecStart de machincast.service, sans --config : la configuration du service."""
	qtbot.waitUntil(poste.terminal.exists, timeout=5000)
	arguments = poste.terminal.read_text(encoding="utf-8").splitlines()
	assert arguments == ["-e", str(REPERTOIRE_PROJET / "bin" / "Machin"), "lecture"], arguments
	assert (
		unite_systemd(Compte("radio", "antenne", 1001), REPERTOIRE_PROJET).count(
			f"ExecStart={REPERTOIRE_PROJET}/bin/Machin lecture\n"
		)
		== 1
	)


@given("l'interface lancée sur la configuration du service")
def sur_la_configuration_du_service(interface: Contexte, monkeypatch: pytest.MonkeyPatch) -> None:
	"""Le machincast.toml du répertoire de MachinCast n'est jamais touché : la copie des tests en tient lieu."""
	copie = fichier_de_configuration(interface)
	monkeypatch.setattr(pilotage, "configuration_du_service", lambda: copie)


@then("la barre d'état annonce que la diffusion d'essai lit la configuration du service, et non celle de l'interface")
def ecart_annonce(interface: Contexte) -> None:
	attendu = (
		f"{pilotage.LANCE} Elle lit {configuration_du_service()}, comme le service,"
		f" et non {fichier_de_configuration(interface)}, celle de l'interface."
	)
	assert fenetre(interface).statusBar().currentMessage() == attendu


@then("la diffusion d'essai s'est arrêtée par SIGTERM")
def essai_arrete(poste: Poste) -> None:
	assert poste.essai is not None
	assert poste.essai.wait(timeout=5) == 0
	assert poste.arret_de_l_essai.read_text(encoding="utf-8") == "SIGTERM"


@then("le terminal a été lancé après l'arrêt de la diffusion d'essai")
def relance_apres_l_arret(poste: Poste) -> None:
	essai = poste.terminal.with_name(f"{poste.terminal.name}.essai")
	assert essai.read_text(encoding="utf-8") == "arrêtée\n"


@given(parsers.parse("l'emplacement « {repertoire} » choisi pour les sauvegardes de la maintenance"))
def emplacement_choisi(interface: Contexte, repertoire: str) -> None:
	interface.sauvegardes_choisies = Path(repertoire)


@then(
	parsers.re(
		r"le terminal a lancé bientôt Machin maintenance-db, sur la configuration de l'interface, avec les sauvegardes"
		r" dans « (?P<sauvegardes>[^»]+) »(?P<a_cote> à côté d'elle)?, le terminal restant ouvert"
	)
)
def maintenance_dans_le_terminal(
	interface: Contexte, poste: Poste, qtbot: QtBot, sauvegardes: str, a_cote: str | None
) -> None:
	repertoire = Path(sauvegardes)
	if a_cote is not None:
		repertoire = fichier_de_configuration(interface).resolve().parent / sauvegardes
	qtbot.waitUntil(poste.terminal.exists, timeout=5000)
	arguments = poste.terminal.read_text(encoding="utf-8").splitlines()
	assert arguments == [
		"-e",
		str(REPERTOIRE_PROJET / "bin" / "Machin"),
		"--config",
		str(fichier_de_configuration(interface)),
		"maintenance-db",
		"--sauvegardes",
		str(repertoire),
		"--garder-ouvert",
	], arguments


@then(
	"l'interface a demandé confirmation, avec l'emplacement des sauvegardes : le répertoire « sauvegardes » de sa"
	" configuration"
)
def confirmation_demandee(interface: Contexte) -> None:
	attendu = fichier_de_configuration(interface).resolve().parent / "sauvegardes"
	assert interface.questions == [f"maintenance : {attendu}"], interface.questions


@then("le terminal n'a rien lancé")
def rien_lance(poste: Poste) -> None:
	"""Le terminal se lance avant que la barre d'état ne le dise : après l'annonce, il n'y a plus rien à attendre."""
	assert not poste.terminal.exists()
