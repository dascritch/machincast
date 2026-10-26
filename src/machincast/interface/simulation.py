"""Écran de simulation (https://github.com/dascritch/machincast/issues/37, spec § 8.7).

L'onglet « Simulation » (EcranSimulation), qui se ferme, s'ouvre par « Affichage → Ouvrir l'onglet Simulation »
(machincast.interface.fenetre). On y règle le début et la fin de la période, d'abord de l'heure qu'il est, à la
minute, à un jour plus tard. « Simuler » lance Machin lecture --simulation (commande_simulation), par le Python de
l'interface et avec sa configuration, dans un processus à part (QProcess) : l'interface reste utilisable, et la
simulation garde le rôle de la lecture en base, où elle n'écrit rien (spec § 5.5). Ses sorties vont dans un répertoire
temporaire, propre à l'onglet et effacé à sa fermeture : jamais dans les sorties de la configuration.

À la fin du processus, la table montre les passages de son CSV, avec l'artiste et le titre masqués comme sur la page
publique ; la liste, les alertes et incidents qu'il a signalés sur sa sortie d'erreur (« simulation : … »). Un échec
donne la dernière ligne de sa sortie d'erreur. « Exporter… » enregistre l'une des trois sorties, .csv, .pls ou .html,
selon le filtre choisi dans le sélecteur de fichier (dialogues.choisir_export) ; le nom reçoit l'extension du format
s'il ne l'a pas déjà : un export ne peut donc jamais remplacer un fichier sonore
(https://github.com/dascritch/machincast/issues/96, machincast.protection).
"""

import csv
import logging
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QDate, QDateTime, QProcess, QTime, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
	QAbstractItemView,
	QDateTimeEdit,
	QHBoxLayout,
	QLabel,
	QListWidget,
	QPushButton,
	QTableView,
	QVBoxLayout,
	QWidget,
)

from machincast.horloge import Horloge
from machincast.interface import dialogues
from machincast.interface.colonnes import Colonnes
from machincast.journal import HORODATAGE
from machincast.lecture.simulation import nom_par_defaut
from machincast.protection import verifier_ecriture

journal = logging.getLogger(__name__)

PERIODE = timedelta(days=1)
"""Durée de la période proposée à l'ouverture de l'onglet."""
NOM = "simulation"
"""Nom des sorties dans le répertoire temporaire de l'onglet."""
FORMAT_DES_DATES = "yyyy-MM-dd HH:mm"
COLONNES = ("Début", "Fin", "Artiste", "Titre", "Emplacement", "Événement", "Séquence", "Banque")
CHAMPS = ("debut", "fin", "artiste", "titre", "emplacement", "evenement", "sequence", "banque")
"""Les colonnes du CSV de la simulation montrées dans la table, dans l'ordre de COLONNES."""
FORMATS = {
	"Tableur CSV (*.csv)": ".csv",
	"Playlist PLS (*.pls)": ".pls",
	"Page HTML (*.html)": ".html",
}
"""Filtres du sélecteur d'export, et l'extension de la sortie que chacun enregistre."""
PREFIXE_DES_ANOMALIES = "simulation : "
INVITE = "Réglez la période, puis cliquez sur « Simuler »."
EN_COURS = "Simulation en cours…"
PERIODE_INVALIDE = "La fin doit suivre le début."


def commande_simulation(configuration: Path | None) -> list[str]:
	"""Machin lecture, lancé par le Python de l'interface, avec la même configuration qu'elle."""
	commande = [sys.executable, "-m", "machincast.lecture"]
	if configuration is not None:
		commande += ["--config", str(configuration.expanduser().absolute())]
	return commande


def avec_extension(chemin: Path, extension: str) -> Path:
	"""Le chemin, avec l'extension du format exporté s'il ne l'a pas déjà : « grille » devient « grille.pls »,
	« matinale.flac » devient « matinale.flac.csv »."""
	if chemin.suffix.lower() == extension:
		return chemin
	return chemin.with_name(f"{chemin.name}{extension}")


def _pluriel(nombre: int, singulier: str, pluriel: str) -> str:
	if nombre > 1:
		return f"{nombre} {pluriel}"
	return f"{nombre} {singulier}"


def bilan(passages: int, anomalies: int) -> str:
	texte_des_passages = "Aucun passage"
	if passages > 0:
		texte_des_passages = _pluriel(passages, "passage", "passages")
	texte_des_anomalies = "aucune alerte ni incident"
	if anomalies > 0:
		texte_des_anomalies = _pluriel(anomalies, "alerte ou incident", "alertes ou incidents")
	return f"{texte_des_passages}, {texte_des_anomalies}. Rien n'a été écrit en base."


def _instant(edition: QDateTimeEdit) -> datetime:
	"""L'instant réglé, en heure du poste."""
	moment = edition.dateTime().toPython()
	assert isinstance(moment, datetime)
	return moment.astimezone()


class EcranSimulation(QWidget):
	terminee = Signal()
	"""La simulation lancée s'est terminée, réussie ou non."""

	def __init__(self, horloge: Horloge, configuration: Path | None, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.configuration = configuration
		self.temporaire = Path(tempfile.mkdtemp(prefix="machincast-simulation-"))
		"""Répertoire des sorties de la simulation, effacé à la fermeture de l'onglet."""
		self.processus: QProcess | None = None
		self.lancees = 0
		"""Simulations lancées depuis l'ouverture de l'onglet."""
		self.periode: tuple[datetime, datetime] | None = None
		"""Période de la dernière simulation réussie, celle qu'on exporte."""
		disposition = QVBoxLayout(self)
		reglage = QHBoxLayout()
		# Les champs sont à la minute : les secondes de l'horloge tombent.
		debut = horloge.maintenant().astimezone()
		self.debut = self._edition(debut)
		self.fin = self._edition(debut + PERIODE)
		reglage.addWidget(QLabel("Du", self))
		reglage.addWidget(self.debut)
		reglage.addWidget(QLabel("au", self))
		reglage.addWidget(self.fin)
		self.simuler = QPushButton("Simuler", self)
		self.simuler.setToolTip("Machin lecture simule la diffusion de la période, sans son et sans écrire en base")
		self.simuler.clicked.connect(self.lancer)
		reglage.addWidget(self.simuler)
		self.exporter = QPushButton("Exporter…", self)
		self.exporter.setToolTip("Enregistre le résultat en .csv, .pls ou .html")
		self.exporter.setEnabled(False)
		self.exporter.clicked.connect(self._exporter)
		reglage.addWidget(self.exporter)
		reglage.addStretch()
		disposition.addLayout(reglage)
		self.compte = QLabel(INVITE, self)
		self.compte.setWordWrap(True)
		disposition.addWidget(self.compte)
		self.modele = QStandardItemModel(0, len(COLONNES), self)
		self.modele.setHorizontalHeaderLabels(list(COLONNES))
		self.table = QTableView(self)
		self.table.setModel(self.modele)
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.verticalHeader().hide()
		self.table.horizontalHeader().setStretchLastSection(True)
		self.colonnes = Colonnes(self.table, "simulation")
		disposition.addWidget(self.table, 1)
		self.anomalies = QListWidget(self)
		self.anomalies.setToolTip("Alertes et incidents de la simulation")
		self.anomalies.setMaximumHeight(120)
		self.anomalies.hide()
		disposition.addWidget(self.anomalies)

	def _edition(self, instant: datetime) -> QDateTimeEdit:
		local = instant.astimezone()
		moment = QDateTime(QDate(local.year, local.month, local.day), QTime(local.hour, local.minute))
		edition = QDateTimeEdit(moment, self)
		edition.setDisplayFormat(FORMAT_DES_DATES)
		edition.setCalendarPopup(True)
		return edition

	def en_cours(self) -> bool:
		return self.processus is not None

	def actualiser(self) -> None:
		"""Rien à relire : le résultat est celui de la dernière simulation, que seul « Simuler » relance."""

	def lancer(self) -> None:
		debut, fin = _instant(self.debut), _instant(self.fin)
		if fin <= debut:
			self.compte.setText(PERIODE_INVALIDE)
			return
		self._vider()
		programme, *arguments = commande_simulation(self.configuration)
		arguments += [
			"--simulation",
			debut.isoformat(timespec="minutes"),
			fin.isoformat(timespec="minutes"),
			"--repertoire",
			str(self.temporaire),
			"--nom",
			NOM,
		]
		processus = QProcess(self)
		processus.finished.connect(lambda code, _statut: self._terminer(processus, code, (debut, fin)))
		processus.errorOccurred.connect(lambda erreur: self._echouer(processus, erreur))
		self.processus = processus
		self.lancees += 1
		self.simuler.setEnabled(False)
		self.compte.setText(EN_COURS)
		journal.info(f"simulation du {debut.isoformat(timespec='minutes')} au {fin.isoformat(timespec='minutes')}")
		processus.start(programme, arguments)

	def _vider(self) -> None:
		self.periode = None
		self.exporter.setEnabled(False)
		self.modele.setRowCount(0)
		self.anomalies.clear()
		self.anomalies.hide()
		for ancienne in self.temporaire.glob(f"{NOM}.*"):
			# fichier de MachinCast : une sortie de la simulation précédente, dans le répertoire temporaire de l'onglet.
			ancienne.unlink()

	def _echouer(self, processus: QProcess, erreur: QProcess.ProcessError) -> None:
		"""Un programme qui ne démarre pas ne finit jamais : finished n'est pas émis."""
		if erreur == QProcess.ProcessError.FailedToStart:
			self._fin(processus)
			self.compte.setText(f"Simulation impossible : {processus.errorString()}")

	def _fin(self, processus: QProcess) -> None:
		self.processus = None
		self.simuler.setEnabled(True)
		processus.deleteLater()
		self.terminee.emit()

	def _terminer(self, processus: QProcess, code: int, periode: tuple[datetime, datetime]) -> None:
		erreurs = bytes(processus.readAllStandardError().data()).decode("utf-8", errors="replace").splitlines()
		self._fin(processus)
		anomalies = [ligne.split(PREFIXE_DES_ANOMALIES, 1)[1] for ligne in erreurs if PREFIXE_DES_ANOMALIES in ligne]
		chemin = self.temporaire / f"{NOM}.csv"
		if (code != 0) or (not chemin.exists()):
			raison = "Machin lecture s'est arrêté sans rien dire"
			# Chaque message de Machin lecture commence par son horodatage (machincast.journal) ; un message peut tenir
			# sur plusieurs lignes.
			messages = [HORODATAGE.sub("", ligne) for ligne in erreurs if HORODATAGE.match(ligne)]
			if messages:
				raison = messages[-1]
			self.compte.setText(f"Simulation impossible : {raison}")
			return
		passages = self._lire(chemin)
		self.anomalies.addItems(anomalies)
		self.anomalies.setVisible(bool(anomalies))
		self.compte.setText(bilan(passages, len(anomalies)))
		self.periode = periode
		self.exporter.setEnabled(True)

	def _lire(self, chemin: Path) -> int:
		with chemin.open(encoding="utf-8-sig", newline="") as fichier:
			for ligne in csv.DictReader(fichier, delimiter=";"):
				self.modele.appendRow([QStandardItem(ligne[champ]) for champ in CHAMPS])
		return self.modele.rowCount()

	def lignes(self) -> list[list[str]]:
		return [
			[str(self.modele.item(rangee, colonne).text()) for colonne in range(self.modele.columnCount())]
			for rangee in range(self.modele.rowCount())
		]

	def _exporter(self) -> None:
		assert self.periode is not None
		propose = f"{nom_par_defaut(*self.periode)}.csv"
		choix = dialogues.choisir_export(self, propose, list(FORMATS))
		if choix is None:
			return
		chemin, filtre = choix
		extension = FORMATS[filtre]
		destination = avec_extension(chemin, extension)
		try:
			verifier_ecriture(destination)
			shutil.copyfile(self.temporaire / f"{NOM}{extension}", destination)
		except OSError as erreur:
			self._annoncer(f"Export impossible : {erreur}")
			return
		self._annoncer(f"Simulation exportée dans {destination}.")

	def _annoncer(self, texte: str) -> None:
		fenetre = self.window()
		barre = getattr(fenetre, "statusBar", None)
		if barre is not None:
			barre().showMessage(texte)

	def fermer(self) -> None:
		"""Arrête la simulation en cours, puis efface le répertoire temporaire de l'onglet."""
		processus = self.processus
		if processus is not None:
			processus.kill()
			processus.waitForFinished()
		# fichier de MachinCast : le répertoire temporaire de l'onglet, et les sorties de ses simulations.
		shutil.rmtree(self.temporaire, ignore_errors=True)
