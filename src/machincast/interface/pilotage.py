"""Pilotage de la diffusion depuis l'interface (https://github.com/dascritch/machincast/issues/25, spec § 8.11).

Avec le service (install.sh --service, https://github.com/dascritch/machincast/issues/22), démarrer et arrêter
appellent systemctl sur machincast.service, dans un processus à part : la règle polkit du service les
autorise avec l'authentification d'un administrateur, que demande l'agent polkit de la session. Jamais sudo.

Sans le service, l'installation n'est pas définitive, et le menu pilote une diffusion d'essai : Machin lecture lancé
dans une fenêtre de terminal (konsole, sinon x-terminal-emulator), par la commande du service, sur sa configuration :
la diffusion d'essai sort sur le même périphérique que sortirait le service. L'arrêter
lui envoie SIGTERM, comme Ctrl-C dans ce terminal ; son processus est celui qui répond sur la socket d'état
(ClientEtat.pid_du_lecteur). Ce n'est pas « Machin lecture --simulation », qui ne joue rien.
"""

import os
import shutil
import signal
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

from machincast.configuration import REPERTOIRE_PROJET, fichier_par_defaut
from machincast.maintenance import sauvegardes_par_defaut
from machincast.service import UNITE

VERBES = {
	"start": ("Démarrer la diffusion", "Diffusion démarrée.", "Diffusion non démarrée"),
	"stop": ("Arrêter la diffusion", "Diffusion arrêtée.", "Diffusion non arrêtée"),
}
"""Pour chaque verbe de systemctl : l'entrée du menu, ce qu'annonce sa réussite, et son échec."""
ESSAI = {
	"start": "Démarrer la diffusion d'essai",
	"stop": "Arrêter la diffusion d'essai",
}
"""Les entrées du menu sans le service."""
TERMINAUX = ("konsole", "x-terminal-emulator")
"""Les terminaux essayés, dans l'ordre : celui de Kubuntu, puis celui que choisit le poste."""
SANS_TERMINAL = "Aucun terminal trouvé (konsole, x-terminal-emulator) : lancer Machin lecture à la main."
COMMANDE_DU_SERVICE = [str(REPERTOIRE_PROJET / "bin" / "Machin"), "lecture"]
"""Comme l'ExecStart de machincast.service : la diffusion d'essai sort là où sortirait le service."""
LANCE = "Diffusion d'essai lancée dans un terminal : Ctrl-C l'y arrête."
MAINTENANCE = "Maintenance de la base de données…"
"""L'entrée du menu « Maintenance » (https://github.com/dascritch/machincast/issues/127)."""
MAINTENANCE_LANCEE = (
	"Maintenance de la base de données lancée dans un terminal : sauvegarde, vérification du schéma, optimisation."
)
MAINTENANCE_ABANDONNEE = "Maintenance de la base de données abandonnée : rien n'a été lancé."
SANS_TERMINAL_POUR_LA_MAINTENANCE = (
	"Aucun terminal trouvé (konsole, x-terminal-emulator) : lancer Machin maintenance-db à la main."
)
ARRET_DEMANDE = "Arrêt de la diffusion d'essai demandé…"
ARRETEE = "Diffusion d'essai arrêtée."


class Pilotage(QObject):
	termine = Signal(str)
	"""Ce qu'il advient d'une commande : réussite ou échec, avec le message de systemctl."""

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self._processus: list[QProcess] = []

	def piloter(self, verbe: str) -> None:
		"""systemctl <verbe> machincast.service, sans attendre : l'authentification peut prendre du temps."""
		processus = QProcess(self)
		self._processus.append(processus)
		processus.finished.connect(lambda code, _statut: self._fin(processus, verbe, code))
		processus.start("systemctl", [verbe, UNITE])

	def _fin(self, processus: QProcess, verbe: str, code: int) -> None:
		self._processus.remove(processus)
		_entree, reussite, echec = VERBES[verbe]
		if code == 0:
			self.termine.emit(reussite)
			return
		erreur = bytes(processus.readAllStandardError().data()).decode("utf-8", "replace").strip()
		self.termine.emit(f"{echec} : {(erreur) or (processus.errorString())}")


def ouvrir_un_terminal(commande: list[str]) -> bool:
	"""La commande, détachée de l'interface, dans le premier terminal trouvé ; False sans terminal."""
	for terminal in TERMINAUX:
		chemin = shutil.which(terminal)
		if chemin is not None:
			QProcess.startDetached(chemin, ["-e", *commande])
			return True
	return False


def lancer_dans_un_terminal(configuration: Path | None, lance: str = LANCE) -> str:
	"""Machin lecture, détaché, dans le premier terminal trouvé, par la commande même du service : il lit la
	configuration du service, le machincast.toml du répertoire de MachinCast, et diffuse donc sur le même périphérique
	que lui. Ce que la barre d'état en dit : lance, et l'écart avec la configuration de l'interface s'il y en a un."""
	if ouvrir_un_terminal(COMMANDE_DU_SERVICE):
		return f"{lance}{_ecart(configuration)}"
	return SANS_TERMINAL


def sauvegardes_de_la_maintenance(configuration: Path | None) -> Path:
	"""Où la maintenance lancée par l'interface écrira sa sauvegarde, en chemin absolu : le répertoire « sauvegardes »
	à côté de la configuration de l'interface, ou du machincast.toml du répertoire de MachinCast."""
	fichier = fichier_par_defaut()
	if configuration is not None:
		fichier = configuration
	return sauvegardes_par_defaut(fichier.resolve())


def lancer_la_maintenance(configuration: Path | None, sauvegardes: Path) -> str:
	"""Machin maintenance-db sur la base de l'interface, avec ses sauvegardes dans sauvegardes, dans un terminal
	qui reste ouvert à la fin (https://github.com/dascritch/machincast/issues/127) ; ce qu'en dit la barre d'état."""
	commande = [str(REPERTOIRE_PROJET / "bin" / "Machin")]
	if configuration is not None:
		commande += ["--config", str(configuration)]
	if ouvrir_un_terminal([*commande, "maintenance-db", "--sauvegardes", str(sauvegardes), "--garder-ouvert"]):
		return MAINTENANCE_LANCEE
	return SANS_TERMINAL_POUR_LA_MAINTENANCE


def _ecart(configuration: Path | None) -> str:
	du_service = configuration_du_service()
	if (configuration is None) or (configuration.resolve() == du_service.resolve()):
		return ""
	return f" Elle lit {du_service}, comme le service, et non {configuration}, celle de l'interface."


def configuration_du_service() -> Path:
	"""Le fichier que lit le service, lancé sans --config (machincast.installation.unite_systemd)."""
	return fichier_par_defaut()


def arreter_le_lecteur(pid: int) -> str:
	"""SIGTERM, comme Ctrl-C : Machin lecture termine proprement le passage en cours, puis ferme sa socket d'état."""
	try:
		os.kill(pid, signal.SIGTERM)
	except OSError as erreur:
		return f"Diffusion d'essai non arrêtée : {erreur.strerror}"
	return ARRET_DEMANDE
