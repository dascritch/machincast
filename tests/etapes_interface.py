"""Étapes partagées des scénarios de la fenêtre de l'interface : onglets, listes et fiches
(https://github.com/dascritch/machincast/issues/26, https://github.com/dascritch/machincast/issues/31,
https://github.com/dascritch/machincast/issues/112).

Chargé comme greffon pytest par tests/conftest.py. La fenêtre s'affiche hors de l'écran du poste
(QT_QPA_PLATFORM=offscreen, réglé par tests/conftest.py). Elle lit la base de test, avec le rôle de l'interface. Le
fixture « interface » tient la fenêtre et ce que le scénario en observe. À l'ouverture de la fenêtre, les fenêtres de
dialogue (machincast.interface.dialogues) sont remplacées par les réponses du scénario, qui note chaque question
posée : aucune fenêtre modale n'attend un clic.
"""

import dataclasses
import json
import re
import shutil
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
import shiboken6
import tomlkit
from PySide6.QtCore import QCoreApplication, QEvent, QMimeData, QModelIndex, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import (
	QAction,
	QDragEnterEvent,
	QDragLeaveEvent,
	QDragMoveEvent,
	QDropEvent,
	QIcon,
	QImage,
	QKeySequence,
)
from PySide6.QtWidgets import (
	QAbstractItemView,
	QApplication,
	QLineEdit,
	QListView,
	QMenu,
	QPushButton,
	QTabBar,
	QWidget,
)
from pytest_bdd import given, parsers, then, when
from pytestqt.qtbot import QtBot

from machincast import audio
from machincast.audio import Peripherique
from machincast.base import Role, connecter
from machincast.configuration import PEREMPTION, Crossfades, Interface, SortieAudio, charger
from machincast.horloge import HorlogeFixe
from machincast.interface import dialogues
from machincast.interface.dialogues import Fermeture, Retrait
from machincast.interface.fenetre import FenetrePrincipale
from machincast.interface.fiche import Fiche
from machincast.interface.listes import Liste
from machincast.interface.preferences import Reglages
from machincast.interface.suggestions import Manques, Reponse
from machincast.lecture.etat import Demande, SocketEtat
from tests.base_test import configuration_test, parametres_base_test
from tests.sons import FICHIERS_SONORES

Connexion = psycopg.Connection[tuple[object, ...]]
NOM = re.compile(r"« ([^»]+) »")
MODES = {"séquentielle": "sequentiel", "aléatoire": "aleatoire"}


@dataclass
class Contexte:
	repertoire: Path
	monkeypatch: pytest.MonkeyPatch
	horloge: HorlogeFixe | None = None
	fenetre: FenetrePrincipale | None = None
	connexion: Connexion | None = None
	demandes: list[tuple[str, int]] = field(default_factory=list)
	"""Écrans de détail demandés : genre et identifiant."""
	questions: list[str] = field(default_factory=list)
	"""Questions posées par les fenêtres de dialogue, dans l'ordre."""
	fermeture: Fermeture = Fermeture.ABANDONNER
	"""Réponse à la question de fermeture d'une fiche modifiée."""
	retrait: Retrait = Retrait.ANNULER
	maintenance: bool = True
	sauvegardes_choisies: Path | None = None
	"""L'emplacement des sauvegardes choisi dans la confirmation de la maintenance ; None : celui proposé."""
	"""Réponse à la confirmation de la maintenance de la base (https://github.com/dascritch/machincast/issues/127)."""
	"""Réponse à l'avertissement de réintégration d'un sonore retiré."""
	suppression: bool = False
	"""Réponse à la question de suppression : True pour supprimer."""
	creation: bool = False
	"""Réponse à la question de création d'un événement depuis le calendrier : True pour créer."""
	rafraichir_apres_verification: bool = True
	"""Réponse à la question après la vérification complète d'un sonore : True pour rafraîchir sa fiche
	(https://github.com/dascritch/machincast/issues/190)."""
	action: bool = True
	"""Réponse à la confirmation d'une action sur une sélection : True pour la faire
	(https://github.com/dascritch/machincast/issues/114)."""
	banques_proposees: list[list[int] | None] = field(default_factory=list)
	"""Banques que chaque choix de banques a proposées ; None : toutes."""
	audio: dict[str, object] = field(default_factory=dict)
	"""Ce qui remplace la section [audio] de la configuration des tests : sortie, périphériques."""
	reglages_audio: tuple[str, str] | None = None
	"""Périphériques de l'antenne et de la pré-écoute que donnera la fenêtre des préférences ; None : inchangés."""
	audio_montre: list[tuple[str | None, str]] = field(default_factory=list)
	"""Périphériques de l'antenne et de la pré-écoute montrés par la fenêtre des préférences."""
	repertoires_choisis: list[str | None] = field(default_factory=list)
	"""Répertoires que donneront les choix suivants, None pour un choix abandonné."""
	sonores_choisis: list[int] = field(default_factory=list)
	"""Sonores que donnera le prochain choix."""
	banques_choisies: list[int] = field(default_factory=list)
	"""Banques que donnera le prochain choix."""
	sequences_choisies: list[int] = field(default_factory=list)
	feeds_choisis: list[int] = field(default_factory=list)
	"""Séquences que donnera le prochain choix."""
	remarques: list[str] = field(default_factory=list)
	"""Remarques des choix de sonores ou de banques ouverts."""
	dossiers_ouverts: list[Path] = field(default_factory=list)
	"""Dossiers ouverts dans le navigateur de fichiers."""
	fermes: list[QWidget] = field(default_factory=list)
	"""Écrans des onglets que le scénario a fermés."""
	fichiers: dict[Path, bytes] = field(default_factory=dict)
	"""Fichiers créés par le scénario, avec leur contenu."""
	depots: list[tuple[bool, Qt.DropAction]] = field(default_factory=list)
	"""Dépôts de fichiers : acceptés ou non, et l'action retenue."""
	fichiers_choisis: list[Path] = field(default_factory=list)
	"""Fichiers que donnera le prochain choix de fichiers ; aucun pour un choix abandonné."""
	annonces: list[str] = field(default_factory=list)
	"""Messages de la barre d'état, dans l'ordre."""
	pages_ouvertes: list[str] = field(default_factory=list)
	"""Adresses ouvertes dans le navigateur web du poste."""
	versions: list[str] = field(default_factory=list)
	"""Textes montrés par la fenêtre de version."""
	configuration: Path | None = None
	"""Fichier de configuration de la fenêtre : une copie de celui des tests, dans le répertoire du scénario."""
	preferences_reglees: Crossfades | None = None
	"""Ce que donnera la fenêtre des préférences ; None : elle est abandonnée."""
	preferences_montrees: list[Crossfades] = field(default_factory=list)
	"""Les réglages que la fenêtre des préférences a montrés, à chaque ouverture."""
	seuil_regle: float | None = None
	"""Le seuil de blanc que donnera la fenêtre des préférences (https://github.com/dascritch/machincast/issues/146) ;
	None : celui qu'elle a montré."""
	seuils_montres: list[float] = field(default_factory=list)
	"""Les seuils de blanc que la fenêtre des préférences a montrés, à chaque ouverture."""
	peremption_reglee: int | None = None
	"""La durée de péremption, en jours, que donnera la fenêtre des préférences
	(https://github.com/dascritch/machincast/issues/268) ; None : celle qu'elle a montrée."""
	peremptions_montrees: list[int] = field(default_factory=list)
	jours_choisis: list[date | None] = field(default_factory=list)
	"""Ce que donneront les prochains choix d'un jour, None pour un choix abandonné
	(https://github.com/dascritch/machincast/issues/273)."""
	choix_de_jour: list[tuple[str, date]] = field(default_factory=list)
	"""Le texte et le premier jour possible de chaque choix d'un jour."""
	suggestions_actives: bool = False
	"""Les scénarios n'ont pas de suggestions au lancement, sauf ceux qui les activent
	(https://github.com/dascritch/machincast/issues/119) : sans elles, le fil musical est recréé comme avant."""
	reponse_aux_suggestions: Callable[[Manques], Reponse] = lambda _manques: Reponse(creer=False)
	"""Ce que donnera la fenêtre des suggestions, d'après ce qu'elle propose : « Plus tard » par défaut."""
	suggestions_faites: list[Manques] = field(default_factory=list)
	"""Ce que la fenêtre des suggestions a proposé, à chaque lancement."""
	duree_de_reponse: float = 0.0
	"""Temps qu'a pris la dernière action mesurée, en secondes (https://github.com/dascritch/machincast/issues/194)."""
	saturation_reglee: bool | None = None
	"""Le voyant « Saturation » que donnera la fenêtre des préférences ; None : inchangé
	(https://github.com/dascritch/machincast/issues/191)."""
	saturations_montrees: list[bool] = field(default_factory=list)
	"""Le voyant « Saturation » montré par la fenêtre des préférences, à chaque ouverture."""
	icone_reglee: tuple[Path | None] | None = None
	"""L'icône que donnera la fenêtre des préférences, None dans le tuple pour celle de MachinCast ; None : inchangée
	(https://github.com/dascritch/machincast/issues/111)."""
	icones_montrees: list[Path | None] = field(default_factory=list)
	"""L'icône montrée par la fenêtre des préférences, à chaque ouverture."""
	configuration_initiale: bytes = b""
	"""Le fichier de configuration à l'ouverture de la fenêtre."""

	def chemin_dans(self, texte: str) -> str:
		"""Chaque « …/ » du texte désigne le répertoire temporaire du scénario."""
		return texte.replace("…/", f"{self.repertoire}/")

	def chemin(self, texte: str) -> str:
		"""Un chemin qui commence par « …/ » est dans le répertoire temporaire du scénario."""
		if texte.startswith("…/"):
			return f"{self.repertoire}/{texte.removeprefix('…/')}"
		return texte


@pytest.fixture
def interface(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Contexte]:
	# monkeypatch est demandé ici, avant qtbot : la fenêtre se ferme en fin de scénario, dialogues encore remplacés.
	interface = Contexte(tmp_path, monkeypatch)
	yield interface
	if interface.fenetre is not None:
		interface.fenetre.close()
	if interface.connexion is not None:
		interface.connexion.close()
	# pytest-qt a fermé la fenêtre et demandé sa suppression (deleteLater), qui n'est faite que dans une boucle
	# d'événements : elle se fait ici, avec celle de ce que la fenêtre emporte. Sinon, les fenêtres des scénarios qui
	# n'attendent rien s'accumulent, et le premier scénario qui attend les supprime toutes, au détriment de son délai
	# (https://github.com/dascritch/machincast/issues/262).
	QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


QUESTIONS_DE_MODIFICATION = {"fermer la fiche": "fermeture", "rafraîchir la fiche": "rafraîchissement"}
"""La question sur les modifications d'une fiche, selon ce qui l'a posée."""


def remplacer_dialogues(interface: Contexte) -> None:
	"""Les fenêtres de dialogue donnent les réponses du scénario, et notent les questions posées."""
	monkeypatch = interface.monkeypatch

	def fermeture(_parent: QWidget, titre: str, avant: str = "fermer la fiche") -> Fermeture:
		interface.questions.append(f"{QUESTIONS_DE_MODIFICATION[avant]} : {titre}")
		return interface.fermeture

	def retrait(_parent: QWidget, avertissement: str) -> Retrait:
		interface.questions.append(f"retrait : {avertissement}")
		return interface.retrait

	def suppression(_parent: QWidget, titre: str, texte: str) -> bool:
		interface.questions.append(f"suppression : {titre}\n{texte}")
		return interface.suppression

	def creation(_parent: QWidget, texte: str) -> bool:
		interface.questions.append(f"création : {texte}")
		return interface.creation

	def repertoire(_parent: QWidget, *_titre_et_depart: str) -> str | None:
		return interface.repertoires_choisis.pop(0)

	def sonores(_parent: QWidget, _connexion: Connexion, remarque: str = "") -> list[int]:
		interface.remarques.append(remarque)
		return interface.sonores_choisis

	def banques(
		_parent: QWidget, _connexion: Connexion, remarque: str = "", parmi: list[int] | None = None
	) -> list[int]:
		interface.remarques.append(remarque)
		interface.banques_proposees.append(parmi)
		return interface.banques_choisies

	def action(_parent: QWidget, titre: str, texte: str) -> bool:
		interface.questions.append(f"action : {titre}\n{texte}")
		return interface.action

	monkeypatch.setattr(dialogues, "confirmer_fermeture", fermeture)
	monkeypatch.setattr(dialogues, "confirmer_retrait", retrait)
	monkeypatch.setattr(dialogues, "confirmer_suppression", suppression)
	monkeypatch.setattr(dialogues, "confirmer_creation", creation)
	monkeypatch.setattr(dialogues, "confirmer_action", action)

	def maintenance(_parent: QWidget, sauvegardes: Path) -> Path | None:
		interface.questions.append(f"maintenance : {sauvegardes}")
		if not interface.maintenance:
			return None
		return (interface.sauvegardes_choisies) or (sauvegardes)

	monkeypatch.setattr(dialogues, "confirmer_maintenance", maintenance)

	def apres_verification(_parent: QWidget, texte: str) -> bool:
		interface.questions.append(f"après vérification : {texte} Rafraîchir la fiche ?")
		return interface.rafraichir_apres_verification

	monkeypatch.setattr(dialogues, "proposer_rafraichissement", apres_verification)
	monkeypatch.setattr(dialogues, "choisir_repertoire", repertoire)
	monkeypatch.setattr(dialogues, "choisir_fichiers", lambda _parent: interface.fichiers_choisis)
	monkeypatch.setattr(dialogues, "choisir_sonores", sonores)

	def sequences(_parent: QWidget, _connexion: Connexion, remarque: str = "") -> list[int]:
		interface.remarques.append(remarque)
		return interface.sequences_choisies

	def feeds(_parent: QWidget, _connexion: Connexion, remarque: str = "") -> list[int]:
		interface.remarques.append(remarque)
		return interface.feeds_choisis

	monkeypatch.setattr(dialogues, "choisir_banques", banques)
	monkeypatch.setattr(dialogues, "choisir_sequences", sequences)
	monkeypatch.setattr(dialogues, "choisir_feeds", feeds)
	monkeypatch.setattr(dialogues, "ouvrir_dossier", interface.dossiers_ouverts.append)
	monkeypatch.setattr(dialogues, "ouvrir_page", interface.pages_ouvertes.append)
	monkeypatch.setattr(dialogues, "montrer_version", lambda _parent, texte: interface.versions.append(texte))

	def jour(_parent: QWidget, _titre: str, texte: str, minimum: date) -> date | None:
		interface.choix_de_jour.append((texte, minimum))
		return interface.jours_choisis.pop(0)

	monkeypatch.setattr(dialogues, "choisir_jour", jour)

	def preferences(_parent: QWidget, montres: Reglages, _sortie: SortieAudio) -> Reglages | None:
		"""Les crossfades et les périphériques du scénario ; ceux qu'il ne règle pas restent ceux montrés."""
		interface.preferences_montrees.append(montres.crossfades)
		interface.audio_montre.append((montres.antenne, montres.preecoute))
		interface.seuils_montres.append(montres.seuil_blancs)
		interface.peremptions_montrees.append(montres.peremption)
		interface.saturations_montrees.append(montres.saturation)
		interface.icones_montrees.append(montres.icone)
		if (
			(interface.preferences_reglees is None)
			and (interface.reglages_audio is None)
			and (interface.seuil_regle is None)
			and (interface.peremption_reglee is None)
			and (interface.saturation_reglee is None)
			and (interface.icone_reglee is None)
		):
			return None
		antenne, preecoute = (interface.reglages_audio) or ((montres.antenne, montres.preecoute))
		seuil = montres.seuil_blancs
		if interface.seuil_regle is not None:
			seuil = interface.seuil_regle
		saturation = montres.saturation
		if interface.saturation_reglee is not None:
			saturation = interface.saturation_reglee
		icone = montres.icone
		if interface.icone_reglee is not None:
			icone = interface.icone_reglee[0]
		peremption = montres.peremption
		if interface.peremption_reglee is not None:
			peremption = interface.peremption_reglee
		return Reglages(
			(interface.preferences_reglees) or (montres.crossfades),
			antenne,
			preecoute,
			seuil,
			saturation,
			montres.suggestions,
			icone,
			peremption,
		)

	monkeypatch.setattr(dialogues, "regler_preferences", preferences)

	def suggerer(_parent: QWidget, manques: Manques) -> Reponse:
		interface.suggestions_faites.append(manques)
		return interface.reponse_aux_suggestions(manques)

	monkeypatch.setattr(dialogues, "suggerer", suggerer)


def fichier_de_configuration(interface: Contexte) -> Path:
	"""La copie du fichier de configuration des tests dans le répertoire du scénario, créée au besoin."""
	if interface.configuration is None:
		interface.configuration = interface.repertoire / "machincast.toml"
		shutil.copyfile(configuration_test().chemin, interface.configuration)
	return interface.configuration


def fenetre(interface: Contexte) -> FenetrePrincipale:
	assert interface.fenetre is not None
	return interface.fenetre


def liste(interface: Contexte) -> Liste:
	ouverte = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(ouverte, Liste), ouverte
	return ouverte


def lignes(interface: Contexte) -> list[dict[str, str]]:
	"""Les lignes affichées, après filtre et tri, par titre de colonne."""
	modele = liste(interface).table.model()
	titres = [
		str(modele.headerData(colonne, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole))
		for colonne in range(modele.columnCount())
	]
	return [
		{titre: str((modele.index(rangee, colonne).data()) or ("")) for colonne, titre in enumerate(titres)}
		for rangee in range(modele.rowCount())
	]


def fiche_ouverte(interface: Contexte) -> Fiche:
	ouverte = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(ouverte, Fiche), ouverte
	return ouverte


def onglet(interface: Contexte, titre: str) -> int:
	onglets = fenetre(interface).ui.onglets
	titres = [onglets.tabText(indice) for indice in range(onglets.count())]
	assert titre in titres, titres
	return titres.index(titre)


def bouton_de_fermeture(barre: QTabBar, indice: int) -> QWidget | None:
	"""Le bouton de fermeture d'un onglet, à gauche ou à droite selon le style."""
	for cote in (QTabBar.ButtonPosition.LeftSide, QTabBar.ButtonPosition.RightSide):
		bouton = barre.tabButton(indice, cote)
		if bouton is not None:
			return bouton
	return None


def taper(qtbot: QtBot, champ: QLineEdit, texte: str) -> None:
	"""Vide le champ, puis y tape le texte."""
	champ.clear()
	for lettre in texte:
		# QTest ne sait taper que l'ASCII : une lettre accentuée s'insère comme le ferait une méthode de saisie.
		if lettre.isascii():
			qtbot.keyClicks(champ, lettre)
		else:
			champ.insert(lettre)


def ouvrir_dans(qtbot: QtBot, table: QAbstractItemView, nom: str) -> None:
	"""Double-clic sur la ligne d'une table dont une cellule est le nom."""
	modele = table.model()
	colonnes = 1
	if not isinstance(table, QListView):
		# Le modèle d'une liste n'a qu'une colonne, et ne dit pas son nombre.
		colonnes = modele.columnCount()
	trouve: QModelIndex | None = None
	for rangee in range(modele.rowCount()):
		for colonne in range(colonnes):
			if modele.index(rangee, colonne).data() == nom:
				trouve = modele.index(rangee, colonne)
	assert trouve is not None, f"aucune ligne « {nom} »"
	table.scrollTo(trouve)
	centre = table.visualRect(trouve).center()
	qtbot.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=centre)
	qtbot.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=centre)


def glisser(interface: Contexte, liste: QAbstractItemView, quoi: str, deposer: bool, deplacement: bool) -> None:
	"""Un glisser venu du navigateur de fichiers, qui propose la copie, le déplacement et le lien. Maj est enfoncée :
	le navigateur propose le déplacement, que la fiche doit changer en copie. « un texte » glisse du texte, sans
	fichier ; un chemin en https:// est une adresse web. Le dépôt est noté dans interface.depots."""
	cible = liste.viewport()
	donnees = QMimeData()
	if quoi == "un texte":
		donnees.setText("Café à minuit")
	else:
		adresses = []
		for chemin in NOM.findall(quoi):
			adresse = QUrl(chemin)
			if not chemin.startswith("https://"):
				adresse = QUrl.fromLocalFile(interface.chemin(chemin))
			adresses.append(adresse)
		donnees.setUrls(adresses)
	actions = Qt.DropAction.CopyAction | Qt.DropAction.MoveAction | Qt.DropAction.LinkAction
	if deplacement:
		actions = Qt.DropAction.MoveAction
	centre = cible.rect().center()
	bouton, touches = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier
	QApplication.sendEvent(cible, QDragEnterEvent(centre, actions, donnees, bouton, touches))
	QApplication.sendEvent(cible, QDragMoveEvent(centre, actions, donnees, bouton, touches))
	if not deposer:
		QApplication.sendEvent(cible, QDragLeaveEvent())
		return
	depot = QDropEvent(QPointF(centre), actions, donnees, bouton, touches)
	assert depot.proposedAction() == Qt.DropAction.MoveAction
	QApplication.sendEvent(cible, depot)
	interface.depots.append((depot.isAccepted(), depot.dropAction()))


def duree_ou_rien(secondes: str) -> timedelta | None:
	"""Une durée en secondes ; aucune pour une cellule vide."""
	if secondes == "":
		return None
	return timedelta(seconds=int(secondes))


def date_ou_rien(texte: str) -> datetime | None:
	"""« 2026-10-12 20:00 » en heure du poste ; aucune pour une cellule vide."""
	if texte == "":
		return None
	return datetime.fromisoformat(texte).astimezone()


def identifiant(base: Connexion, table: str, colonne: str, valeur: str) -> int:
	ligne = base.execute(f"SELECT id FROM {table} WHERE {colonne} = %s", (valeur,)).fetchone()  # noqa: S608
	assert ligne is not None, f"{valeur} absent de {table}"
	return int(str(ligne[0]))


def bouton_de_suppression(interface: Contexte) -> QPushButton:
	(bouton,) = [
		bouton for bouton in fiche_ouverte(interface).findChildren(QPushButton) if bouton.text() == "Supprimer…"
	]
	return bouton


def questions_de_suppression(interface: Contexte) -> list[str]:
	return [question for question in interface.questions if question.startswith("suppression : ")]


def lignes_attendues(interface: Contexte, datatable: list[list[str]]) -> str:
	_entete, *lignes = datatable
	return "\n".join(ligne[0].strip().replace("…/", f"{interface.repertoire}/") for ligne in lignes)


TABLES = {
	"le sonore": ("sonores", "titre"),
	"la banque": ("banques", "nom_interne"),
	"la séquence": ("sequences", "nom_interne"),
	"l'événement": ("evenements", "nom_interne"),
	"le feed": ("feeds", "nom"),
}
"""Table et colonne du nom de chaque genre d'élément, pour le retrouver en base."""


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'horloge de l'interface au « {instant} »"))
def horloge(interface: Contexte, instant: str) -> None:
	interface.horloge = HorlogeFixe(datetime.fromisoformat(instant).astimezone())


@given("les sonores :")
def sonores(interface: Contexte, base_vide: Connexion, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	for valeurs in rangees:
		ligne = dict(zip(entetes, (v.strip() for v in valeurs), strict=True))
		ligne["emplacement"] = interface.chemin(ligne["emplacement"])
		stream = ligne["type"] == "stream"
		base_vide.execute(
			"INSERT INTO sonores (type, emplacement, url_stream, artiste, titre, etat, duree)"
			" VALUES (%s, %s, %s, %s, %s, %s, %s)",
			(
				ligne["type"],
				None if stream else ligne["emplacement"],
				ligne["emplacement"] if stream else None,
				(ligne["artiste"]) or (None),
				(ligne["titre"]) or (None),
				ligne["etat"],
				duree_ou_rien(ligne["duree"]),
			),
		)


@given(parsers.re(r"les dossiers (?P<chemins>.+) du scénario"))
def dossiers_du_scenario(interface: Contexte, chemins: str) -> None:
	for chemin in NOM.findall(chemins):
		Path(interface.chemin(chemin)).mkdir(parents=True)


@given(parsers.re(r"les fichiers (?P<chemins>.+) du scénario"))
def fichiers_du_scenario(interface: Contexte, chemins: str) -> None:
	for chemin in NOM.findall(chemins):
		fichier = Path(interface.chemin(chemin))
		fichier.parent.mkdir(parents=True, exist_ok=True)
		interface.fichiers[fichier] = f"contenu de {fichier.name}".encode()
		fichier.write_bytes(interface.fichiers[fichier])


@given(
	parsers.re(
		r"la banque « (?P<nom>[^»]+) », (?P<mode>séquentielle|aléatoire),"
		r" (?:de nom public « (?P<nom_public>[^»]+) »|sans nom public)"
		r"(?P<marquee>, marquée « ne pas répéter »)?, avec (?P<liste>.+)"
	)
)
def banque(base_vide: Connexion, nom: str, mode: str, nom_public: str | None, marquee: str | None, liste: str) -> None:
	creee = base_vide.execute(
		"INSERT INTO banques (nom_interne, nom_public, mode, ne_pas_repeter) VALUES (%s, %s, %s, %s) RETURNING id",
		(nom, nom_public, MODES[mode], marquee is not None),
	).fetchone()
	assert creee is not None
	for position, titre in enumerate(NOM.findall(liste), start=1):
		base_vide.execute(
			"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, %s)",
			(creee[0], identifiant(base_vide, "sonores", "titre", titre), position),
		)


@given(parsers.re(r"les répertoires (?P<liste>.+) de la banque « (?P<nom>[^»]+) »"))
def repertoires(interface: Contexte, base_vide: Connexion, liste: str, nom: str) -> None:
	banque = identifiant(base_vide, "banques", "nom_interne", nom)
	for repertoire in NOM.findall(liste):
		base_vide.execute(
			"INSERT INTO banques_repertoires (banque_id, repertoire) VALUES (%s, %s)",
			(banque, interface.chemin(repertoire)),
		)


ELEMENT = re.compile(r"(le sonore|la banque|la séquence) « ([^»]+) »")
ELEMENTS = r"(?:le sonore|la banque|la séquence) « [^»]+ »(?:, (?:le sonore|la banque|la séquence) « [^»]+ »)*"
"""Une liste d'éléments : « le sonore « Jingle », la banque « Publicité », la séquence « Passage pub » »."""
REFERENCES = {
	"le sonore": ("sonores", "titre", "sonore_id"),
	"la banque": ("banques", "nom_interne", "banque_id"),
	"la séquence": ("sequences", "nom_interne", "sequence_id"),
}
"""Table, colonne du nom et colonne de la liste de chaque genre d'élément."""


@given(
	parsers.re(
		r"la séquence « (?P<nom>[^»]+) », (?:de nom public « (?P<nom_public>[^»]+) »|sans nom public),"
		rf" avec (?P<elements>{ELEMENTS}|rien)"
	)
)
def sequence(base_vide: Connexion, nom: str, nom_public: str | None, elements: str) -> None:
	"""Chaque sonore par son titre, chaque banque par son nom, dans l'ordre."""
	creee = base_vide.execute(
		"INSERT INTO sequences (nom_interne, nom_public) VALUES (%s, %s) RETURNING id", (nom, nom_public)
	).fetchone()
	assert creee is not None
	for position, (genre, element) in enumerate(ELEMENT.findall(elements), start=1):
		table, colonne, reference = REFERENCES[genre]
		base_vide.execute(
			f"INSERT INTO sequences_elements (sequence_id, position, {reference}) VALUES (%s, %s, %s)",  # noqa: S608
			(creee[0], position, identifiant(base_vide, table, colonne, element)),
		)


@given(parsers.re(rf"l'événement « (?P<evenement>[^»]+) » joue (?P<elements>{ELEMENTS})"))
def evenement_jouant(base_vide: Connexion, evenement: str, elements: str) -> None:
	"""Les éléments s'ajoutent en fin de la liste de l'événement, dans l'ordre."""
	numero = identifiant(base_vide, "evenements", "nom_interne", evenement)
	for genre, element in ELEMENT.findall(elements):
		table, colonne, reference = REFERENCES[genre]
		base_vide.execute(
			f"INSERT INTO evenements_elements (evenement_id, position, {reference})"  # noqa: S608
			" SELECT %s, COALESCE(MAX(position), 0) + 1, %s FROM evenements_elements WHERE evenement_id = %s",
			(numero, identifiant(base_vide, table, colonne, element), numero),
		)


@given(parsers.parse("le stream « {titre} » a pour événement de secours « {secours} »"))
def stream_secouru(base_vide: Connexion, titre: str, secours: str) -> None:
	base_vide.execute(
		"UPDATE sonores SET secours_evenement_id = %s WHERE titre = %s",
		(identifiant(base_vide, "evenements", "nom_interne", secours), titre),
	)


@given(parsers.re(r"les feeds (?P<marques>.+)"))
def feeds(base_vide: Connexion, marques: str) -> None:
	noms = NOM.findall(marques)
	for nom, url in zip(noms[::2], noms[1::2], strict=True):
		base_vide.execute("INSERT INTO feeds (nom, url) VALUES (%s, %s)", (nom, url))


@given(parsers.re(r"(?:les streams|le stream) (?P<titres>.+) (?:suivent|suit) le feed « (?P<marque>[^»]+) »"))
def suivent(base_vide: Connexion, titres: str, marque: str) -> None:
	for titre in NOM.findall(titres):
		base_vide.execute(
			"UPDATE sonores SET url_stream = NULL, feed_id = %s WHERE titre = %s",
			(identifiant(base_vide, "feeds", "nom", marque), titre),
		)


def _minutes(texte: str | None) -> timedelta | None:
	"""« 2:00 » : deux minutes ; None sans texte."""
	if texte is None:
		return None
	minutes, secondes = texte.split(":")
	return timedelta(minutes=int(minutes), seconds=int(secondes))


@given(
	parsers.re(
		r"la banque « (?P<nom>[^»]+) » veut des sonores"
		r" (?:de (?P<de>[\d:]+) à (?P<a>[\d:]+)"
		r"|d'au moins (?P<au_moins>[\d:]+)(?: et d'au plus (?P<puis_au_plus>[\d:]+))?"
		r"|d'au plus (?P<au_plus>[\d:]+))$"
	)
)
def durees_de_banque(
	base_vide: Connexion,
	nom: str,
	de: str | None,
	a: str | None,
	au_moins: str | None,
	puis_au_plus: str | None,
	au_plus: str | None,
) -> None:
	"""Les durées minimale et maximale des sonores de la banque (https://github.com/dascritch/machincast/issues/147)."""
	minimum = _minutes((de) or (au_moins))
	maximum = _minutes((a) or (puis_au_plus) or (au_plus))
	base_vide.execute(
		"UPDATE banques SET duree_min = %s, duree_max = %s WHERE nom_interne = %s", (minimum, maximum, nom)
	)


@when(parsers.parse("le feed « {nom} » est effacé de la base"))
def effacer_feed(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("DELETE FROM feeds WHERE nom = %s", (nom,))


@given(parsers.parse("le fichier de test « {source} » copié en « {chemin} »"))
def copie(interface: Contexte, source: str, chemin: str) -> None:
	fichier = Path(interface.chemin(chemin))
	fichier.parent.mkdir(parents=True, exist_ok=True)
	shutil.copyfile(FICHIERS_SONORES / source, fichier)
	interface.fichiers[fichier] = fichier.read_bytes()


@given(parsers.parse("le fichier « {chemin} », qui n'est pas un son"))
def faux_son(interface: Contexte, chemin: str) -> None:
	fichier = Path(interface.chemin(chemin))
	fichier.parent.mkdir(parents=True, exist_ok=True)
	interface.fichiers[fichier] = b"Ceci n'est pas un son."
	fichier.write_bytes(interface.fichiers[fichier])


@given("les événements :")
def evenements(base_vide: Connexion, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	for valeurs in rangees:
		ligne = dict(zip(entetes, (v.strip() for v in valeurs), strict=True))
		base_vide.execute(
			"INSERT INTO evenements (nom_interne, nom_public, priorite, debut, fin, jours_recurrence)"
			" VALUES (%s, %s, %s, %s, %s, %s::jour_semaine[])",
			(
				ligne["nom"],
				(ligne["nom_public"]) or (None),
				ligne["priorite"],
				date_ou_rien(ligne["debut"]),
				date_ou_rien(ligne["fin"]),
				[jour.strip() for jour in ligne["jours"].split(",") if jour.strip()],
			),
		)


@given(parsers.parse("la session du {jour} de l'événement « {nom} » est sautée"))
@when(parsers.parse("la session du {jour} de l'événement « {nom} » est sautée"))
def session_sautee(base_vide: Connexion, jour: str, nom: str) -> None:
	"""Comme depuis le calendrier (https://github.com/dascritch/machincast/issues/273), pour l'interface comme pour la
	diffusion."""
	base_vide.execute(
		"INSERT INTO evenements_sauts (evenement_id, jour) SELECT id, %s FROM evenements WHERE nom_interne = %s",
		(date.fromisoformat(jour), nom),
	)


# ─── Quand ─────────────────────────────────────────────────


@when("la fenêtre de l'interface s'ouvre")
def ouvrir(interface: Contexte, base_vide: Connexion, qtbot: QtBot) -> None:
	ouvrir_la_fenetre(interface, qtbot)


@when("la fenêtre de l'interface se ferme, puis s'ouvre de nouveau")
def rouvrir(interface: Contexte, qtbot: QtBot) -> None:
	fenetre(interface).close()
	ouvrir_la_fenetre(interface, qtbot)


def ouvrir_la_fenetre(interface: Contexte, qtbot: QtBot, avec_configuration: bool = True) -> None:
	"""La fenêtre de l'interface, sur une copie du fichier de configuration des tests ; sans lui, elle ne peut pas
	enregistrer ses préférences."""
	assert interface.horloge is not None
	remplacer_dialogues(interface)
	interface.connexion = connecter(*parametres_base_test(), Role.INTERFACE)
	chemin: Path | None = None
	crossfades = None
	blancs = None
	peremption = PEREMPTION
	reglages_de_l_interface = None
	audio = configuration_test().audio
	if avec_configuration:
		chemin = fichier_de_configuration(interface)
		interface.configuration_initiale = chemin.read_bytes()
		crossfades = charger(chemin).crossfades
		blancs = charger(chemin).blancs
		peremption = charger(chemin).base.peremption
		reglages_de_l_interface = charger(chemin).interface
		audio = charger(chemin).audio
	if not interface.suggestions_actives:
		reglages_de_l_interface = dataclasses.replace((reglages_de_l_interface) or (Interface()), suggestions=False)
	audio = dataclasses.replace(audio, **interface.audio)  # type: ignore[arg-type]
	interface.fenetre = FenetrePrincipale(
		interface.connexion,
		interface.repertoire / "lecture.sock",
		interface.horloge,
		configuration=chemin,
		crossfades=crossfades,
		audio=audio,
		blancs=blancs,
		interface=reglages_de_l_interface,
		peremption=peremption,
	)
	interface.fenetre.detail_demande.connect(lambda genre, numero: interface.demandes.append((genre, numero)))

	def annoncer(texte: str) -> None:
		# Effacer la barre d'état n'annonce rien.
		if texte != "":
			interface.annonces.append(texte)

	# Ce que la fenêtre annonce en s'ouvrant, avant que l'étape l'écoute.
	annoncer(interface.fenetre.statusBar().currentMessage())
	interface.fenetre.statusBar().messageChanged.connect(annoncer)

	def abandonner(_fenetre: QWidget) -> None:
		# À la fin du scénario, la fenêtre se ferme en abandonnant les modifications de ses fiches.
		interface.fermeture = Fermeture.ABANDONNER

	qtbot.addWidget(interface.fenetre, before_close_func=abandonner)
	interface.fenetre.show()
	qtbot.waitExposed(interface.fenetre)
	# Comme Machin_interface, une fois la fenêtre montrée (https://github.com/dascritch/machincast/issues/119).
	interface.fenetre.proposer_au_lancement()


@when("la base devient injoignable pour l'interface")
def base_injoignable(interface: Contexte) -> None:
	assert interface.connexion is not None
	interface.connexion.close()


A_LA_DEMANDE = {"Sonores": "Ouvrir l'onglet Sonores", "Feeds": "Ouvrir l'onglet Feeds"}
"""Les listes qui ne s'ouvrent pas au lancement, et l'entrée du menu « Affichage » qui les ouvre
(https://github.com/dascritch/machincast/issues/180)."""


@when(parsers.parse("j'ouvre l'onglet « {titre} »"))
def ouvrir_onglet(interface: Contexte, titre: str) -> None:
	"""Une liste ouverte à la demande, pas encore ouverte, s'ouvre par le menu « Affichage », comme le ferait
	l'utilisateur (https://github.com/dascritch/machincast/issues/180)."""
	onglets = fenetre(interface).ui.onglets
	titres = [onglets.tabText(indice) for indice in range(onglets.count())]
	if (titre in A_LA_DEMANDE) and (titre not in titres):
		choisir_dans_le_menu(interface, A_LA_DEMANDE[titre], "Affichage")
		return
	onglets.setCurrentIndex(onglet(interface, titre))


@when(parsers.parse("j'ouvre la fiche de la banque « {nom} »"))
def ouvrir_fiche_banque(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	ouvrir_onglet(interface, "Banques")
	ouvrir_ligne(interface, qtbot, nom)


@when(parsers.parse("j'ouvre la fiche de la séquence « {nom} »"))
def ouvrir_fiche_sequence(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	ouvrir_onglet(interface, "Séquences")
	ouvrir_ligne(interface, qtbot, nom)


@when(parsers.parse("j'ouvre la fiche de l'événement « {nom} »"))
def ouvrir_fiche_evenement(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	ouvrir_onglet(interface, "Événements")
	ouvrir_ligne(interface, qtbot, nom)


@when(parsers.parse("j'ouvre la fiche du sonore « {nom} »"))
def ouvrir_fiche_sonore(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	"""Par son titre, ou son emplacement pour un sonore sans titre."""
	ouvrir_onglet(interface, "Sonores")
	ouvrir_ligne(interface, qtbot, nom)


@when(parsers.parse("je clique sur « {texte} »"))
def cliquer_sur(interface: Contexte, qtbot: QtBot, texte: str) -> None:
	ouvert = fenetre(interface).ui.onglets.currentWidget()
	boutons = [bouton for bouton in ouvert.findChildren(QPushButton) if bouton.text() == texte]
	assert len(boutons) == 1, f"bouton « {texte} » : {len(boutons)} trouvés"
	qtbot.mouseClick(boutons[0], Qt.MouseButton.LeftButton)


@when(parsers.re(r"je saisis le (?P<champ>nom interne|nom public) « (?P<texte>[^»]*) »"))
def saisir_nom(interface: Contexte, qtbot: QtBot, champ: str, texte: str) -> None:
	ui = fiche_ouverte(interface).ui  # type: ignore[attr-defined]
	champs = {"nom interne": ui.nom_interne, "nom public": ui.nom_public}
	taper(qtbot, champs[champ], texte)


@when(parsers.re(r"je choisis (?:le|la) (?P<champ>mode|masquage|priorité) « (?P<texte>[^»]+) »"))
def choisir_dans_la_fiche(interface: Contexte, champ: str, texte: str) -> None:
	ui = fiche_ouverte(interface).ui  # type: ignore[attr-defined]
	liste = getattr(ui, {"priorité": "priorite"}.get(champ, champ))
	indice = liste.findText(texte, Qt.MatchFlag.MatchFixedString)
	assert indice >= 0, f"« {texte} » absent du choix du {champ}"
	liste.setCurrentIndex(indice)


@when("j'enregistre la fiche")
def enregistrer(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(fiche_ouverte(interface).bouton_enregistrer, Qt.MouseButton.LeftButton)


@when("j'annule les modifications de la fiche")
def annuler(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(fiche_ouverte(interface).bouton_annuler, Qt.MouseButton.LeftButton)


@given(parsers.parse("le sonore « {titre} » est effacé de la base"))
@when(parsers.parse("le sonore « {titre} » est effacé de la base"))
def effacer(base_vide: Connexion, titre: str) -> None:
	base_vide.execute("DELETE FROM sonores WHERE titre = %s", (titre,))


@when(parsers.re(r"la banque « (?P<nom>[^»]+) » (?P<etat>est|n'est plus) marquée « ne pas répéter » en base"))
def marquer(base_vide: Connexion, nom: str, etat: str) -> None:
	base_vide.execute("UPDATE banques SET ne_pas_repeter = %s WHERE nom_interne = %s", (etat == "est", nom))


@when(parsers.re(r"la (?P<genre>banque|séquence) « (?P<nom>[^»]+) » est effacée de la base"))
def effacer_banque(base_vide: Connexion, genre: str, nom: str) -> None:
	table = {"banque": "banques", "séquence": "sequences"}[genre]
	base_vide.execute(f"DELETE FROM {table} WHERE nom_interne = %s", (nom,))  # noqa: S608


@when(parsers.re(r"j'ajoute les feeds (?P<noms>aucun|« [^»]+ »(?:, « [^»]+ »)*)"))
def ajouter_feeds(interface: Contexte, qtbot: QtBot, base_vide: Connexion, noms: str) -> None:
	"""Le choix donnera ces feeds, par leur nom ; « aucun » : le choix est abandonné
	(https://github.com/dascritch/machincast/issues/167)."""
	ui = fiche_ouverte(interface).ui  # type: ignore[attr-defined]
	interface.feeds_choisis = [identifiant(base_vide, "feeds", "nom", nom) for nom in NOM.findall(noms)]
	qtbot.mouseClick(ui.ajouter_feeds, Qt.MouseButton.LeftButton)


@then(parsers.parse("le stream « {titre} » est en base, actif, et suit le feed « {marque} »"))
def stream_du_feed(base_vide: Connexion, titre: str, marque: str) -> None:
	ligne = base_vide.execute(
		"SELECT s.type::text, s.etat::text, s.url_stream, m.nom FROM sonores s"
		" JOIN feeds m ON m.id = s.feed_id WHERE s.titre = %s",
		(titre,),
	).fetchall()
	assert ligne == [("stream", "actif", None, marque)], ligne


@then(parsers.re(r"(?P<nombre>\d+) streams? (?:suit|suivent) le feed « (?P<marque>[^»]+) »"))
def nombre_de_streams(base_vide: Connexion, nombre: str, marque: str) -> None:
	ligne = base_vide.execute(
		"SELECT count(*) FROM sonores s JOIN feeds m ON m.id = s.feed_id WHERE m.nom = %s",
		(marque,),
	).fetchone()
	assert ligne is not None
	assert int(str(ligne[0])) == int(nombre)


@when(parsers.re(r"j'ajoute les (?P<genre>sonores|banques|séquences) (?P<noms>aucun|« [^»]+ »(?:, « [^»]+ »)*)"))
def ajouter_elements(interface: Contexte, qtbot: QtBot, base_vide: Connexion, genre: str, noms: str) -> None:
	"""Le choix donnera ces sonores, par leur titre, ou ces banques ou ces séquences, par leur nom ; « aucun » : le
	choix est abandonné."""
	ui = fiche_ouverte(interface).ui  # type: ignore[attr-defined]
	if genre == "sonores":
		interface.sonores_choisis = [identifiant(base_vide, "sonores", "titre", nom) for nom in NOM.findall(noms)]
	elif genre == "banques":
		interface.banques_choisies = [
			identifiant(base_vide, "banques", "nom_interne", nom) for nom in NOM.findall(noms)
		]
	else:
		interface.sequences_choisies = [
			identifiant(base_vide, "sequences", "nom_interne", nom) for nom in NOM.findall(noms)
		]
	bouton = {"sonores": "ajouter_sonores", "banques": "ajouter_banques", "séquences": "ajouter_sequences"}[genre]
	qtbot.mouseClick(getattr(ui, bouton), Qt.MouseButton.LeftButton)


@when(parsers.parse("je ferme l'onglet « {titre} »"))
def fermer_onglet(interface: Contexte, qtbot: QtBot, titre: str) -> None:
	onglets = fenetre(interface).ui.onglets
	indice = onglet(interface, titre)
	bouton = bouton_de_fermeture(onglets.tabBar(), indice)
	assert bouton is not None, f"l'onglet « {titre} » n'a pas de bouton de fermeture"
	interface.fermes.append(onglets.widget(indice))
	qtbot.mouseClick(bouton, Qt.MouseButton.LeftButton)


@when("je ferme la fenêtre de l'interface")
def fermer_fenetre(interface: Contexte) -> None:
	fenetre(interface).close()


@when(parsers.re(r"je réponds « (?P<reponse>[^»]+) » à la question de (?:fermeture|rafraîchissement)"))
def repondre_fermeture(interface: Contexte, reponse: str) -> None:
	interface.fermeture = Fermeture(reponse)


@when(parsers.parse("je réponds « {reponse} » à l'avertissement de réintégration"))
def repondre_retrait(interface: Contexte, reponse: str) -> None:
	interface.retrait = Retrait(reponse)


@when(parsers.parse("le sonore « {titre} » est ajouté en base"))
def ajouter(base_vide: Connexion, titre: str) -> None:
	base_vide.execute(
		"INSERT INTO sonores (type, emplacement, titre) VALUES ('fichier', %s, %s)", (f"/srv/{titre}.flac", titre)
	)


@when(parsers.parse("je tape « {texte} » dans le filtre de la liste"))
def filtrer(interface: Contexte, qtbot: QtBot, texte: str) -> None:
	taper(qtbot, liste(interface).filtre, texte)


@when(parsers.parse("je clique sur le titre de la colonne « {titre} »"))
def trier(interface: Contexte, qtbot: QtBot, titre: str) -> None:
	table = liste(interface).table
	entete = table.horizontalHeader()
	modele = table.model()
	titres = [str(modele.headerData(colonne, Qt.Orientation.Horizontal)) for colonne in range(modele.columnCount())]
	colonne = titres.index(titre)
	position = QPoint(entete.sectionViewportPosition(colonne) + entete.sectionSize(colonne) // 2, entete.height() // 2)
	qtbot.mouseClick(entete.viewport(), Qt.MouseButton.LeftButton, pos=position)


@when(parsers.parse("j'ouvre la ligne « {nom} »"))
def ouvrir_ligne(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	ouvrir_dans(qtbot, liste(interface).table, nom)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"la fenêtre a les onglets (?P<titres>.+)"))
def onglets(interface: Contexte, titres: str) -> None:
	onglets = fenetre(interface).ui.onglets
	assert [onglets.tabText(indice) for indice in range(onglets.count())] == NOM.findall(titres)


@then(parsers.parse("l'onglet ouvert est « {titre} »"))
def onglet_ouvert(interface: Contexte, titre: str) -> None:
	onglets = fenetre(interface).ui.onglets
	assert onglets.tabText(onglets.currentIndex()) == titre


def fermables(interface: Contexte) -> list[str]:
	onglets = fenetre(interface).ui.onglets
	return [
		onglets.tabText(indice)
		for indice in range(onglets.count())
		if bouton_de_fermeture(onglets.tabBar(), indice) is not None
	]


@then("aucun onglet n'a de bouton de fermeture")
def aucun_fermable(interface: Contexte) -> None:
	assert fermables(interface) == []


@then(parsers.re(r"seuls les onglets (?P<titres>«.+) ont un bouton de fermeture"))
def seuls_fermables(interface: Contexte, titres: str) -> None:
	assert fermables(interface) == NOM.findall(titres)


@when("j'efface le filtre de la liste")
def effacer_le_filtre(interface: Contexte) -> None:
	liste(interface).filtre.clear()


@then(parsers.parse("seul l'onglet « {titre} » a un bouton de fermeture"))
def seul_fermable(interface: Contexte, titre: str) -> None:
	onglets = fenetre(interface).ui.onglets
	fermables = [
		onglets.tabText(indice)
		for indice in range(onglets.count())
		if bouton_de_fermeture(onglets.tabBar(), indice) is not None
	]
	assert fermables == [titre]


@then(parsers.re(r"la fenêtre de l'interface est (?P<etat>fermée|ouverte)"))
def fenetre_ouverte(interface: Contexte, etat: str) -> None:
	assert fenetre(interface).isVisible() == (etat == "ouverte")


@then("la fiche fermée est libérée")
def liberee(interface: Contexte) -> None:
	QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
	assert [shiboken6.isValid(ferme) for ferme in interface.fermes] == [False]


@then("aucune question n'a été posée")
def aucune_question(interface: Contexte) -> None:
	assert interface.questions == []


@then(parsers.re(r"la question de (?P<quoi>fermeture|rafraîchissement) a nommé « (?P<titre>[^»]+) »"))
def question_de_fermeture(interface: Contexte, quoi: str, titre: str) -> None:
	assert interface.questions == [f"{quoi} : {titre}"]


@then(parsers.re(r"le navigateur de fichiers a ouvert (?P<dossier>.+)"))
def dossier_ouvert(interface: Contexte, dossier: str) -> None:
	assert interface.dossiers_ouverts == [Path(chemin) for chemin in NOM.findall(dossier)]


@then(parsers.parse("la fiche signale « {message} »"))
def signale(interface: Contexte, message: str) -> None:
	assert fiche_ouverte(interface).message.text() == message


@then("la fiche signale un enregistrement impossible")
def enregistrement_impossible(interface: Contexte) -> None:
	assert fiche_ouverte(interface).message.text().startswith("Enregistrement impossible : ")


@then("la fiche ne signale rien")
def ne_signale_rien(interface: Contexte) -> None:
	assert fiche_ouverte(interface).message.text() == ""


@then(parsers.re(r"les boutons « Enregistrer » et « Annuler » de la fiche sont (?P<etat>actifs|inactifs)"))
def boutons(interface: Contexte, etat: str) -> None:
	ouverte = fiche_ouverte(interface)
	actifs = (ouverte.bouton_enregistrer.isEnabled(), ouverte.bouton_annuler.isEnabled())
	assert actifs == (etat == "actifs", etat == "actifs")


@then(parsers.re(r"la fenêtre (?P<verdict>n'a plus|a encore) d'onglet de fiche"))
def onglet_de_fiche(interface: Contexte, verdict: str) -> None:
	onglets = fenetre(interface).ui.onglets
	fiches = [onglets.widget(indice) for indice in range(onglets.count())]
	assert any(isinstance(ouverte, Fiche) for ouverte in fiches) == (verdict == "a encore")


@then(parsers.re(r"les listes qui proposent de créer un élément sont (?P<boutons>.+)"))
def boutons_nouveau(interface: Contexte, boutons: str) -> None:
	onglets = fenetre(interface).ui.onglets
	avec = []
	for indice in range(onglets.count()):
		ouverte = onglets.widget(indice)
		if (isinstance(ouverte, Liste)) and (not ouverte.ui.nouveau.isHidden()):
			avec.append(f"{onglets.tabText(indice)} : {ouverte.ui.nouveau.text()}")
	assert avec == NOM.findall(boutons)


@then("l'onglet « Accueil » montre l'écran par défaut")
def accueil(interface: Contexte) -> None:
	assert fenetre(interface).ui.onglets.widget(0) is fenetre(interface).accueil


@then("la liste montre :")
def liste_attendue(interface: Contexte, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	attendues = [dict(zip(entetes, (interface.chemin(v.strip()) for v in valeurs), strict=True)) for valeurs in rangees]
	assert lignes(interface) == attendues, lignes(interface)


@then(parsers.re(r"la liste montre les titres (?P<titres>.+)"))
def titres_affiches(interface: Contexte, titres: str) -> None:
	assert [ligne["Titre"] for ligne in lignes(interface)] == NOM.findall(titres), lignes(interface)


@then(parsers.re(r"la liste marque en anomalie les lignes (?P<noms>.+), avec l'infobulle « (?P<infobulle>[^»]+) »"))
def anomalies(interface: Contexte, noms: str, infobulle: str) -> None:
	"""Une ligne en anomalie a l'icône d'avertissement sur sa première cellule, et l'infobulle sur toutes ; les autres
	n'ont ni l'une ni l'autre (https://github.com/dascritch/machincast/issues/138)."""
	modele = liste(interface).table.model()
	marquees = []
	for rangee in range(modele.rowCount()):
		icone = modele.index(rangee, 0).data(Qt.ItemDataRole.DecorationRole)
		bulles = {
			modele.index(rangee, colonne).data(Qt.ItemDataRole.ToolTipRole) for colonne in range(modele.columnCount())
		}
		if icone is not None:
			assert bulles == {infobulle}, bulles
			marquees.append(str(modele.index(rangee, 0).data()))
		else:
			assert bulles == {None}, bulles
	assert marquees == NOM.findall(noms)


@then("la liste marque en anomalie les lignes et infobulles :")
def anomalies_et_infobulles(interface: Contexte, datatable: list[list[str]]) -> None:
	"""Chaque ligne en anomalie a son infobulle, propre à la ligne (https://github.com/dascritch/machincast/issues/140)."""
	modele = liste(interface).table.model()
	marquees = []
	for rangee in range(modele.rowCount()):
		if modele.index(rangee, 0).data(Qt.ItemDataRole.DecorationRole) is not None:
			infobulle = modele.index(rangee, 0).data(Qt.ItemDataRole.ToolTipRole)
			marquees.append([str(modele.index(rangee, 0).data()), str(infobulle)])
	_entetes, *rangees = datatable
	assert marquees == [[ligne.strip(), infobulle.strip()] for ligne, infobulle in rangees]


@then(parsers.parse("le compte de la liste est « {texte} »"))
def compte(interface: Contexte, texte: str) -> None:
	assert liste(interface).compte.text() == texte


@then(parsers.parse("l'écran de détail de {genre} « {nom} » est demandé"))
def detail(interface: Contexte, base_vide: Connexion, genre: str, nom: str) -> None:
	tables = {
		"sonore": ("sonores", "titre"),
		"banque": ("banques", "nom_interne"),
		"séquence": ("sequences", "nom_interne"),
		"événement": ("evenements", "nom_interne"),
		"feed": ("feeds", "nom"),
	}
	table, colonne = tables[genre]
	assert interface.demandes == [(genre, identifiant(base_vide, table, colonne, nom))], interface.demandes


@then(parsers.re(r"(?:le choix a|les choix ont) précisé « (?P<remarque>[^»]+) »"))
def remarque(interface: Contexte, remarque: str) -> None:
	"""Chaque choix ouvert par la fiche a donné cette remarque."""
	assert interface.remarques != []
	assert set(interface.remarques) == {remarque}


@then("le dépôt est accepté comme une copie")
def depot_copie(interface: Contexte) -> None:
	assert interface.depots == [(True, Qt.DropAction.CopyAction)]


@then("le dépôt est refusé")
def depot_refuse(interface: Contexte) -> None:
	assert [accepte for accepte, _action in interface.depots] == [False]


@then(parsers.parse("le fichier « {chemin} » est en base, à l'état aperçu, sans artiste ni titre"))
def fichier_en_apercu(interface: Contexte, base_vide: Connexion, chemin: str) -> None:
	lignes = base_vide.execute(
		"SELECT type::text, etat::text, artiste, titre FROM sonores WHERE emplacement = %s", (interface.chemin(chemin),)
	).fetchall()
	assert lignes == [("fichier", "apercu", None, None)]


@then("les fichiers déposés sont intacts")
def intacts(interface: Contexte) -> None:
	assert {fichier: fichier.read_bytes() for fichier in interface.fichiers} == interface.fichiers


@then(parsers.re(r"le bouton « Supprimer… » de la fiche est (?P<etat>actif|inactif)"))
def bouton_supprimer(interface: Contexte, etat: str) -> None:
	assert fiche_ouverte(interface).bouton_supprimer.isEnabled() == (etat == "actif")


@then(parsers.parse("la barre d'état annonce « {texte} »"))
def barre_d_etat(interface: Contexte, texte: str) -> None:
	assert fenetre(interface).statusBar().currentMessage() == interface.chemin_dans(texte)


# ─── Barre de menus ────────────────────────────────────────


def menus(interface: Contexte) -> list[QMenu]:
	"""Les menus de la barre de menus, dans l'ordre."""
	barre = fenetre(interface).menuBar()
	trouves = {sous_menu.menuAction(): sous_menu for sous_menu in barre.findChildren(QMenu)}
	return [trouves[action] for action in barre.actions()]


def menu_nomme(interface: Contexte, menu: str) -> QMenu:
	trouves = [sous_menu for sous_menu in menus(interface) if sous_menu.title().replace("&", "") == menu]
	assert len(trouves) == 1, f"menu « {menu} » absent"
	return trouves[0]


def actions(interface: Contexte, menu: str) -> list[QAction]:
	"""Les entrées d'un menu de la barre de menus, séparateurs compris, dans l'ordre."""
	return list(menu_nomme(interface, menu).actions())


@when(parsers.parse("je choisis « {titre} » dans le menu « {menu} »"))
def choisir_dans_le_menu(interface: Contexte, titre: str, menu: str) -> None:
	"""Le menu s'ouvre d'abord, comme sous la souris : il peut relire ce qu'il propose (aboutToShow)."""
	menu_nomme(interface, menu).aboutToShow.emit()
	choisies = [action for action in actions(interface, menu) if action.text() == titre]
	assert len(choisies) == 1, f"« {titre} » absent du menu « {menu} »"
	choisies[0].trigger()


@when(parsers.parse("j'appuie sur « {touches} »"))
def appuyer(interface: Contexte, qtbot: QtBot, touches: str) -> None:
	"""Les touches vont au widget qui a le focus dans la fenêtre, activée ; à la fenêtre, si aucun ne l'a."""
	with qtbot.waitActive(fenetre(interface)):
		fenetre(interface).activateWindow()
	cible: QWidget = fenetre(interface)
	focus = fenetre(interface).focusWidget()
	if focus is not None:
		cible = focus
	combinaison = QKeySequence(touches)[0]
	qtbot.keyClick(cible, combinaison.key(), combinaison.keyboardModifiers())


@then(parsers.re(r"la barre de menus a les menus (?P<titres>«.+)"))
def barre_de_menus(interface: Contexte, titres: str) -> None:
	assert [sous_menu.title().replace("&", "") for sous_menu in menus(interface)] == NOM.findall(titres)


@then(parsers.parse("le menu « {menu} » a les entrées :"))
def entrees_du_menu(interface: Contexte, menu: str, datatable: list[list[str]]) -> None:
	"""Un séparateur s'écrit « — ». Une infobulle s'affiche au survol de son entrée, même inactive."""
	entetes, *rangees = datatable
	assert [entete.strip() for entete in entetes] == ["entrée", "état", "raccourci", "infobulle"]
	lues = []
	for action in actions(interface, menu):
		if action.isSeparator():
			lues.append(["—", "", "", ""])
			continue
		infobulle = ""
		if action.toolTip() != action.text().replace("&", ""):
			infobulle = action.toolTip()
		etat = "inactive"
		if action.isEnabled():
			etat = "active"
		lues.append([action.text(), etat, action.shortcut().toString(), infobulle])
	attendues = [[valeur.strip() for valeur in rangee] for rangee in rangees]
	assert lues == attendues
	if any((rangee[3] != "") for rangee in attendues):
		assert menu_nomme(interface, menu).toolTipsVisible()


@then(parsers.re(r"le menu « (?P<menu>[^»]+) » propose (?P<titres>«.+)"))
def menu_propose(interface: Contexte, menu: str, titres: str) -> None:
	actives = [action for action in actions(interface, menu) if (action.isEnabled()) and (not action.isSeparator())]
	assert [action.text() for action in actives] == NOM.findall(titres)


@then(parsers.parse("le menu « {menu} » ne propose plus rien"))
def menu_inactif(interface: Contexte, menu: str) -> None:
	actives = [action for action in actions(interface, menu) if (action.isEnabled()) and (not action.isSeparator())]
	assert actives == []


@then(parsers.parse("le navigateur web a ouvert « {adresse} »"))
def page_ouverte(interface: Contexte, adresse: str) -> None:
	assert interface.pages_ouvertes == [adresse]


ATTENTE = 20_000
"""Millisecondes accordées à une vérification ou une indexation : un fichier de test se décode en moins d'1 s."""


def attendre_la_verification(interface: Contexte, qtbot: QtBot) -> None:
	verificateur = fenetre(interface).verificateur
	qtbot.waitUntil(lambda: not verificateur.en_cours(), timeout=ATTENTE)


@when(parsers.re(r"j'ajoute les fichiers (?P<chemins>aucun|«.+)"))
def ajouter_fichiers(interface: Contexte, qtbot: QtBot, chemins: str) -> None:
	"""Depuis la liste des sonores ouverte, par le sélecteur de fichiers."""
	interface.fichiers_choisis = [Path(interface.chemin(chemin)) for chemin in NOM.findall(chemins)]
	qtbot.mouseClick(liste(interface).ui.ajouter_fichiers, Qt.MouseButton.LeftButton)


@when("la vérification des fichiers ajoutés se termine")
def verification_terminee(interface: Contexte, qtbot: QtBot) -> None:
	attendre_la_verification(interface, qtbot)


@then(parsers.parse("la barre d'état a annoncé « {texte} »"))
def annonce(interface: Contexte, texte: str) -> None:
	assert interface.chemin_dans(texte) in interface.annonces, interface.annonces


@then("la barre d'état n'a rien annoncé")
def rien_annonce(interface: Contexte) -> None:
	assert interface.annonces == []


@when(parsers.re(r"je supprime l'élément de la fiche, en répondant « (?P<reponse>Supprimer|Annuler) »"))
def supprimer(interface: Contexte, qtbot: QtBot, reponse: str) -> None:
	interface.suppression = reponse == "Supprimer"
	qtbot.mouseClick(bouton_de_suppression(interface), Qt.MouseButton.LeftButton)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("la question de suppression, intitulée « {titre} », a dit :"))
def question(interface: Contexte, titre: str, datatable: list[list[str]]) -> None:
	assert questions_de_suppression(interface) == [f"suppression : {titre}\n{lignes_attendues(interface, datatable)}"]


@then("la dernière question de suppression a dit :")
def derniere_question(interface: Contexte, datatable: list[list[str]]) -> None:
	_titre, texte = questions_de_suppression(interface)[-1].split("\n", 1)
	assert texte == lignes_attendues(interface, datatable)


@then(
	parsers.re(
		r"(?P<genre>le sonore|la banque|la séquence|l'événement|le feed) « (?P<nom>[^»]+) »"
		r" (?P<etat>n'est plus|est toujours|est marquée? « supprimée? ») en base"
	)
)
def en_base(base_vide: Connexion, genre: str, nom: str, etat: str) -> None:
	"""« Toujours en base » : pas supprimé ; « marqué « supprimé » » : supprimé, en attendant sa péremption
	(https://github.com/dascritch/machincast/issues/267). Un feed n'est jamais marqué : il quitte la base."""
	table, colonne = TABLES[genre]
	marque = "NULL"
	if genre != "le feed":
		marque = "supprime_le"
	lignes = base_vide.execute(
		f"SELECT {marque} FROM {table} WHERE {colonne} = %s",  # noqa: S608
		(nom,),
	).fetchall()
	if etat == "n'est plus":
		assert lignes == [], lignes
	elif etat == "est toujours":
		assert [ligne[0] for ligne in lignes] == [None], lignes
	else:
		assert (len(lignes) == 1) and (lignes[0][0] is not None), lignes


@given("les périphériques audio du poste :")
def peripheriques_du_poste(monkeypatch: pytest.MonkeyPatch, datatable: list[list[str]]) -> None:
	"""Ceux que donnerait le fournisseur de périphériques de GStreamer, pour la pré-écoute et les préférences."""
	trouves = [Peripherique(identifiant.strip(), nom.strip()) for identifiant, nom in datatable[1:]]

	def lister(_sortie: SortieAudio) -> list[Peripherique]:
		return trouves

	monkeypatch.setattr(audio, "peripheriques", lister)


CONFIGURATION_AUDIO = (
	r"(?:sortie « (?P<sortie>[^»]+) », )?"
	r"(?:sans périphérique d'antenne|avec le périphérique d'antenne « (?P<antenne>[^»]+) »)"
	r"(?: et de pré-écoute « (?P<preecoute>[^»]+) »)?"
)


@given(parsers.re(r"la configuration audio (?P<reglages>.+)"))
def configuration_audio(interface: Contexte, reglages: str) -> None:
	"""« sortie « pipewire », sans périphérique d'antenne » ou « avec le périphérique d'antenne « x » », suivi ou non
	de « et de pré-écoute « y » »."""
	trouvee = re.fullmatch(CONFIGURATION_AUDIO, reglages)
	assert trouvee is not None, reglages
	if trouvee["sortie"] is not None:
		interface.audio["sortie"] = trouvee["sortie"]
	interface.audio["peripherique"] = trouvee["antenne"]
	if trouvee["preecoute"] is not None:
		interface.audio["preecoute"] = trouvee["preecoute"]


@given(parsers.parse("les préférences régleront l'antenne « {antenne} » et la pré-écoute « {preecoute} »"))
def audio_regle(interface: Contexte, antenne: str, preecoute: str) -> None:
	interface.reglages_audio = (antenne, preecoute)


def meme_icone(une: QIcon, autre: QIcon, taille: int = 24) -> bool:
	"""Deux icônes dessinent la même image, à cette taille ; une icône nulle n'est la même que nulle autre."""
	if (une.isNull()) or (autre.isNull()):
		return False
	format_ = QImage.Format.Format_ARGB32
	return une.pixmap(taille).toImage().convertToFormat(format_) == autre.pixmap(taille).toImage().convertToFormat(
		format_
	)


# ─── Machin lecture imaginaire, sur la socket d'état (https://github.com/dascritch/machincast/issues/104) ─────


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


@given("la socket d'état de Machin lecture ouverte pour l'interface")
def socket_ouverte(interface: Contexte, lecteur: Lecteur) -> None:
	lecteur.socket = SocketEtat(interface.repertoire / "lecture.sock")
	lecteur.socket.ouvrir()


@given(parsers.parse("Machin lecture diffuse un sonore au texte public « {texte} »"))
@when(parsers.parse("Machin lecture diffuse un sonore au texte public « {texte} »"))
def diffuse_au_texte_public(lecteur: Lecteur, texte: str) -> None:
	"""Le texte public du sonore en cours, ce que la page publique en affiche
	(https://github.com/dascritch/machincast/issues/223)."""
	en_cours = {
		"sonore": 12,
		"type": "fichier",
		"artiste": None,
		"titre": texte,
		"evenement": "Continue",
		"emplacement": "/srv/musique/minuit.flac",
		"debut": "2026-10-21T08:59:00+02:00",
		"duree": 214.0,
		"fin_estimee": "2026-10-21T09:02:34+02:00",
		"position": 60.0,
		"progression": 0.28,
		"texte_public": texte,
	}
	publier(lecteur, "diffusion", en_cours)


# ─── Airplay (https://github.com/dascritch/machincast/issues/244) ───

JOUR_DE_L_AIRPLAY = "2026-10-16"
"""Le jour des passages des scénarios de l'airplay, quand seule leur heure est donnée."""


def heure(texte: str) -> datetime:
	return datetime.fromisoformat(texte).astimezone()


def heure_ou_rien(texte: str) -> datetime | None:
	if texte == "":
		return None
	return heure(texte)


def a(horaire: str) -> datetime:
	return heure(f"{JOUR_DE_L_AIRPLAY} {horaire}")


def reference(base: Connexion, table: str, nom: str) -> int | None:
	"""Identifiant de l'entrée de ce nom interne, créée au besoin ; None pour un nom vide."""
	if not nom:
		return None
	valeurs = {"evenements": ", priorite) VALUES (%s, 'fil_musical')", "banques": ", mode) VALUES (%s, 'sequentiel')"}
	ligne = base.execute(f"SELECT id FROM {table} WHERE nom_interne = %s", (nom,)).fetchone()  # noqa: S608
	if ligne is None:
		suite = valeurs.get(table, ") VALUES (%s)")
		ligne = base.execute(f"INSERT INTO {table} (nom_interne{suite} RETURNING id", (nom,)).fetchone()  # noqa: S608
	assert ligne is not None
	return int(str(ligne[0]))


def inserer_passage(
	base: Connexion,
	debut: datetime,
	fin: datetime | None,
	artiste: str,
	titre: str,
	evenement: str,
	sequence: str = "",
	banque: str = "",
	sans_incident: str = "",
) -> None:
	emplacement = f"/musique/{uuid.uuid4()}.flac"
	ligne = base.execute(
		"INSERT INTO sonores (type, emplacement, artiste, titre) VALUES ('fichier', %s, %s, %s) RETURNING id",
		(emplacement, (artiste) or (None), titre),
	).fetchone()
	assert ligne is not None
	references = (
		ligne[0],
		reference(base, "evenements", evenement),
		reference(base, "sequences", sequence),
		reference(base, "banques", banque),
	)
	passage = uuid.uuid4()
	colonnes = (
		"passage_id, type_ligne, horodatage, sonore_id, evenement_id, sequence_id, banque_id, artiste, titre,"
		" emplacement"
	)
	base.execute(
		f"INSERT INTO airplay ({colonnes}) VALUES (%s, 'debut', %s, %s, %s, %s, %s, %s, %s, %s)",
		(passage, debut, *references, (artiste) or (None), titre, emplacement),
	)
	if fin is not None:
		base.execute(
			f"INSERT INTO airplay ({colonnes}, duree_diffusee, sans_incident)"
			" VALUES (%s, 'fin', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
			(passage, fin, *references, (artiste) or (None), titre, emplacement, fin - debut, sans_incident == "oui"),
		)


@given("les passages dans l'airplay :")
def passages(base_vide: Connexion, datatable: list[list[str]]) -> None:
	entetes, *lignes = datatable
	for valeurs in lignes:
		ligne = dict(zip(entetes, (v.strip() for v in valeurs), strict=True))
		inserer_passage(
			base_vide,
			heure(ligne["debut"]),
			heure_ou_rien(ligne["fin"]),
			ligne["artiste"],
			ligne["titre"],
			ligne["evenement"],
			ligne["sequence"],
			ligne["banque"],
			ligne["sans_incident"],
		)


@given("le masquage de tous les sonores et de tous les événements")
def masquer(base_vide: Connexion) -> None:
	base_vide.execute("UPDATE sonores SET masquer_metadonnees = true")
	base_vide.execute("UPDATE evenements SET masquer_metadonnees = true")


@when(parsers.parse("le passage de « {titre} » commence dans l'airplay à {debut}"))
def nouveau_passage(base_vide: Connexion, titre: str, debut: str) -> None:
	inserer_passage(base_vide, a(debut), None, "Radio", titre, "Fil de jour")


@given(
	parsers.re(
		r"(?P<genre>le sonore|la banque|la séquence|l'événement) « (?P<nom>[^»]+) » est supprimée? depuis l'interface"
	)
)
def supprime_depuis_l_interface(base_vide: Connexion, genre: str, nom: str) -> None:
	"""Comme « Supprimer… » de sa fiche, sans ses retraits des listes
	(https://github.com/dascritch/machincast/issues/267)."""
	table, colonne = TABLES[genre]
	modifie = base_vide.execute(
		f"UPDATE {table} SET supprime_le = clock_timestamp() WHERE {colonne} = %s RETURNING id",  # noqa: S608
		(nom,),
	).fetchall()
	assert len(modifie) == 1, modifie


@then(parsers.parse("le fichier « {chemin} » a {nombre:d} sonores en base, dont {supprimes:d} supprimé"))
def sonores_du_fichier(interface: Contexte, base_vide: Connexion, chemin: str, nombre: int, supprimes: int) -> None:
	lignes = base_vide.execute(
		"SELECT supprime_le IS NOT NULL FROM sonores WHERE emplacement = %s", (interface.chemin(chemin),)
	).fetchall()
	assert (len(lignes), sum(1 for (supprime,) in lignes if supprime)) == (nombre, supprimes), lignes


@given(parsers.parse("les préférences seront réglées avec la durée de péremption de {jours:d} jours"))
def peremption_reglee(interface: Contexte, jours: int) -> None:
	interface.peremption_reglee = jours


@given(parsers.parse("la durée de péremption du fichier de configuration de l'interface est de {jours:d} jours"))
def peremption_du_fichier(interface: Contexte, jours: int) -> None:
	"""https://github.com/dascritch/machincast/issues/268"""
	chemin = fichier_de_configuration(interface)
	document = tomlkit.parse(chemin.read_text(encoding="utf-8"))
	base = document["base"]
	assert isinstance(base, tomlkit.items.Table)
	base["peremption"] = jours
	chemin.write_text(tomlkit.dumps(document), encoding="utf-8")
