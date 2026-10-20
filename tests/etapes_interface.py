"""Étapes partagées des scénarios de la fenêtre de l'interface : onglets, listes et fiches
(https://github.com/dascritch/machincast/issues/26, https://github.com/dascritch/machincast/issues/31,
https://github.com/dascritch/machincast/issues/112).

Chargé comme greffon pytest par tests/conftest.py. La fenêtre s'affiche hors de l'écran du poste
(QT_QPA_PLATFORM=offscreen, réglé par tests/conftest.py). Elle lit la base de test, avec le rôle de l'interface. Le
fixture « interface » tient la fenêtre et ce que le scénario en observe. À l'ouverture de la fenêtre, les fenêtres de
dialogue (machincast.interface.dialogues) sont remplacées par les réponses du scénario, qui note chaque question
posée : aucune fenêtre modale n'attend un clic.
"""

import re
import shutil
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent, QMimeData, QModelIndex, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QAction, QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QKeySequence
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

from machincast.base import Role, connecter
from machincast.configuration import Crossfades, charger
from machincast.horloge import HorlogeFixe
from machincast.interface import dialogues
from machincast.interface.dialogues import Fermeture, Retrait
from machincast.interface.fenetre import FenetrePrincipale
from machincast.interface.fiche import Fiche
from machincast.interface.listes import Liste
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
	"""Réponse à l'avertissement de réintégration d'un sonore retiré."""
	suppression: bool = False
	"""Réponse à la question de suppression : True pour supprimer."""
	repertoires_choisis: list[str | None] = field(default_factory=list)
	"""Répertoires que donneront les choix suivants, None pour un choix abandonné."""
	sonores_choisis: list[int] = field(default_factory=list)
	"""Sonores que donnera le prochain choix."""
	banques_choisies: list[int] = field(default_factory=list)
	"""Banques que donnera le prochain choix."""
	sequences_choisies: list[int] = field(default_factory=list)
	marques_pages_choisis: list[int] = field(default_factory=list)
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

	def repertoire(_parent: QWidget) -> str | None:
		return interface.repertoires_choisis.pop(0)

	def sonores(_parent: QWidget, _connexion: Connexion, remarque: str = "") -> list[int]:
		interface.remarques.append(remarque)
		return interface.sonores_choisis

	def banques(_parent: QWidget, _connexion: Connexion, remarque: str = "") -> list[int]:
		interface.remarques.append(remarque)
		return interface.banques_choisies

	monkeypatch.setattr(dialogues, "confirmer_fermeture", fermeture)
	monkeypatch.setattr(dialogues, "confirmer_retrait", retrait)
	monkeypatch.setattr(dialogues, "confirmer_suppression", suppression)
	monkeypatch.setattr(dialogues, "choisir_repertoire", repertoire)
	monkeypatch.setattr(dialogues, "choisir_fichiers", lambda _parent: interface.fichiers_choisis)
	monkeypatch.setattr(dialogues, "choisir_sonores", sonores)

	def sequences(_parent: QWidget, _connexion: Connexion, remarque: str = "") -> list[int]:
		interface.remarques.append(remarque)
		return interface.sequences_choisies

	def marques_pages(_parent: QWidget, _connexion: Connexion, remarque: str = "") -> list[int]:
		interface.remarques.append(remarque)
		return interface.marques_pages_choisis

	monkeypatch.setattr(dialogues, "choisir_banques", banques)
	monkeypatch.setattr(dialogues, "choisir_sequences", sequences)
	monkeypatch.setattr(dialogues, "choisir_marques_pages", marques_pages)
	monkeypatch.setattr(dialogues, "ouvrir_dossier", interface.dossiers_ouverts.append)
	monkeypatch.setattr(dialogues, "ouvrir_page", interface.pages_ouvertes.append)
	monkeypatch.setattr(dialogues, "montrer_version", lambda _parent, texte: interface.versions.append(texte))

	def preferences(_parent: QWidget, crossfades: Crossfades) -> Crossfades | None:
		interface.preferences_montrees.append(crossfades)
		return interface.preferences_reglees

	monkeypatch.setattr(dialogues, "regler_preferences", preferences)


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
	"le marque-page": ("marques_pages_streams", "nom"),
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


@given(parsers.re(r"les marques-pages (?P<marques>.+)"))
def marques_pages(base_vide: Connexion, marques: str) -> None:
	noms = NOM.findall(marques)
	for nom, url in zip(noms[::2], noms[1::2], strict=True):
		base_vide.execute("INSERT INTO marques_pages_streams (nom, url) VALUES (%s, %s)", (nom, url))


@given(parsers.re(r"(?:les streams|le stream) (?P<titres>.+) (?:suivent|suit) le marque-page « (?P<marque>[^»]+) »"))
def suivent(base_vide: Connexion, titres: str, marque: str) -> None:
	for titre in NOM.findall(titres):
		base_vide.execute(
			"UPDATE sonores SET url_stream = NULL, marque_page_id = %s WHERE titre = %s",
			(identifiant(base_vide, "marques_pages_streams", "nom", marque), titre),
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


@when(parsers.parse("le marque-page « {nom} » est effacé de la base"))
def effacer_marque_page(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("DELETE FROM marques_pages_streams WHERE nom = %s", (nom,))


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


# ─── Quand ─────────────────────────────────────────────────


@when("la fenêtre de l'interface s'ouvre")
def ouvrir(interface: Contexte, base_vide: Connexion, qtbot: QtBot) -> None:
	ouvrir_la_fenetre(interface, qtbot)


def ouvrir_la_fenetre(interface: Contexte, qtbot: QtBot, avec_configuration: bool = True) -> None:
	"""La fenêtre de l'interface, sur une copie du fichier de configuration des tests ; sans lui, elle ne peut pas
	enregistrer ses préférences."""
	assert interface.horloge is not None
	remplacer_dialogues(interface)
	interface.connexion = connecter(*parametres_base_test(), Role.INTERFACE)
	chemin: Path | None = None
	crossfades = None
	if avec_configuration:
		chemin = fichier_de_configuration(interface)
		interface.configuration_initiale = chemin.read_bytes()
		crossfades = charger(chemin).crossfades
	interface.fenetre = FenetrePrincipale(
		interface.connexion,
		interface.repertoire / "lecture.sock",
		interface.horloge,
		configuration=chemin,
		crossfades=crossfades,
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


@when("la base devient injoignable pour l'interface")
def base_injoignable(interface: Contexte) -> None:
	assert interface.connexion is not None
	interface.connexion.close()


@when(parsers.parse("j'ouvre l'onglet « {titre} »"))
def ouvrir_onglet(interface: Contexte, titre: str) -> None:
	fenetre(interface).ui.onglets.setCurrentIndex(onglet(interface, titre))


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


@when(parsers.re(r"j'ajoute les marques-pages (?P<noms>aucun|« [^»]+ »(?:, « [^»]+ »)*)"))
def ajouter_marques_pages(interface: Contexte, qtbot: QtBot, base_vide: Connexion, noms: str) -> None:
	"""Le choix donnera ces marques-pages, par leur nom ; « aucun » : le choix est abandonné
	(https://github.com/dascritch/machincast/issues/167)."""
	ui = fiche_ouverte(interface).ui  # type: ignore[attr-defined]
	interface.marques_pages_choisis = [
		identifiant(base_vide, "marques_pages_streams", "nom", nom) for nom in NOM.findall(noms)
	]
	qtbot.mouseClick(ui.ajouter_marques_pages, Qt.MouseButton.LeftButton)


@then(parsers.parse("le stream « {titre} » est en base, actif, et suit le marque-page « {marque} »"))
def stream_du_marque_page(base_vide: Connexion, titre: str, marque: str) -> None:
	ligne = base_vide.execute(
		"SELECT s.type::text, s.etat::text, s.url_stream, m.nom FROM sonores s"
		" JOIN marques_pages_streams m ON m.id = s.marque_page_id WHERE s.titre = %s",
		(titre,),
	).fetchall()
	assert ligne == [("stream", "actif", None, marque)], ligne


@then(parsers.re(r"(?P<nombre>\d+) streams? (?:suit|suivent) le marque-page « (?P<marque>[^»]+) »"))
def nombre_de_streams(base_vide: Connexion, nombre: str, marque: str) -> None:
	ligne = base_vide.execute(
		"SELECT count(*) FROM sonores s JOIN marques_pages_streams m ON m.id = s.marque_page_id WHERE m.nom = %s",
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
		"marque-page": ("marques_pages_streams", "nom"),
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
		r"(?P<genre>le sonore|la banque|la séquence|l'événement|le marque-page) « (?P<nom>[^»]+) »"
		r" (?P<etat>n'est plus|est toujours) en base"
	)
)
def en_base(base_vide: Connexion, genre: str, nom: str, etat: str) -> None:
	table, colonne = TABLES[genre]
	lignes = base_vide.execute(f"SELECT id FROM {table} WHERE {colonne} = %s", (nom,)).fetchall()  # noqa: S608
	assert len(lignes) == {"n'est plus": 0, "est toujours": 1}[etat], lignes
