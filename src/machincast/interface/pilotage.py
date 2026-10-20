"""Pilotage de la diffusion depuis l'interface (https://github.com/dascritch/machincast/issues/25, spec § 8.11).

Avec le service (install.sh --service, https://github.com/dascritch/machincast/issues/22), démarrer, arrêter et
redémarrer appellent systemctl sur machincast.service, dans un processus à part : la règle polkit du service les
autorise avec l'authentification d'un administrateur, que demande l'agent polkit de la session. Jamais sudo.

Sans le service, l'installation n'est pas définitive : Machin lecture se lance dans une fenêtre de terminal (konsole,
sinon x-terminal-emulator), avec la configuration de l'interface ; Ctrl-C l'y arrête.
"""

import shutil
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

from machincast.configuration import REPERTOIRE_PROJET
from machincast.service import UNITE

VERBES = {
	"start": ("Démarrer la diffusion", "Diffusion démarrée.", "Diffusion non démarrée"),
	"stop": ("Arrêter la diffusion", "Diffusion arrêtée.", "Diffusion non arrêtée"),
	"restart": ("Redémarrer la diffusion", "Diffusion redémarrée.", "Diffusion non redémarrée"),
}
"""Pour chaque verbe de systemctl : l'entrée du menu, ce qu'annonce sa réussite, et son échec."""
TERMINAUX = ("konsole", "x-terminal-emulator")
"""Les terminaux essayés, dans l'ordre : celui de Kubuntu, puis celui que choisit le poste."""
SANS_TERMINAL = "Aucun terminal trouvé (konsole, x-terminal-emulator) : lancer Machin lecture à la main."
LANCE = "Machin lecture lancé dans un terminal : Ctrl-C l'y arrête."


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


def lancer_dans_un_terminal(configuration: Path | None) -> str:
	"""Machin lecture, détaché, dans le premier terminal trouvé ; ce que la barre d'état en dit."""
	commande = [str(REPERTOIRE_PROJET / "bin" / "Machin"), "lecture"]
	if configuration is not None:
		commande += ["--config", str(configuration)]
	for terminal in TERMINAUX:
		chemin = shutil.which(terminal)
		if chemin is not None:
			QProcess.startDetached(chemin, ["-e", *commande])
			return LANCE
	return SANS_TERMINAL
