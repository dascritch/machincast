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
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent, QMimeData, QModelIndex, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QAbstractItemView, QApplication, QLineEdit, QListView, QPushButton, QTabBar, QWidget
from pytest_bdd import given, parsers, then, when
from pytestqt.qtbot import QtBot

from machincast.base import Role, connecter
from machincast.horloge import HorlogeFixe
from machincast.interface import dialogues
from machincast.interface.dialogues import Fermeture, Retrait
from machincast.interface.fenetre import FenetrePrincipale
from machincast.interface.fiche import Fiche
from machincast.interface.listes import Liste
from tests.base_test import parametres_base_test

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
	repertoires_choisis: list[str | None] = field(default_factory=list)
	"""Répertoires que donneront les choix suivants, None pour un choix abandonné."""
	sonores_choisis: list[int] = field(default_factory=list)
	"""Sonores que donnera le prochain choix."""
	banques_choisies: list[int] = field(default_factory=list)
	"""Banques que donnera le prochain choix."""
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


def remplacer_dialogues(interface: Contexte) -> None:
	"""Les fenêtres de dialogue donnent les réponses du scénario, et notent les questions posées."""
	monkeypatch = interface.monkeypatch

	def fermeture(_parent: QWidget, titre: str) -> Fermeture:
		interface.questions.append(f"fermeture : {titre}")
		return interface.fermeture

	def retrait(_parent: QWidget, avertissement: str) -> Retrait:
		interface.questions.append(f"retrait : {avertissement}")
		return interface.retrait

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
	monkeypatch.setattr(dialogues, "choisir_repertoire", repertoire)
	monkeypatch.setattr(dialogues, "choisir_sonores", sonores)
	monkeypatch.setattr(dialogues, "choisir_banques", banques)
	monkeypatch.setattr(dialogues, "ouvrir_dossier", interface.dossiers_ouverts.append)


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


ELEMENT = re.compile(r"(le sonore|la banque) « ([^»]+) »")
ELEMENTS = r"(?:le sonore|la banque) « [^»]+ »(?:, (?:le sonore|la banque) « [^»]+ »)*"
"""Une liste d'éléments de séquence : « le sonore « Jingle » , la banque « Publicité » »."""


@given(
	parsers.re(
		r"la séquence « (?P<nom>[^»]+) », (?:de nom public « (?P<nom_public>[^»]+) »|sans nom public),"
		rf" avec (?P<elements>{ELEMENTS})"
	)
)
def sequence(base_vide: Connexion, nom: str, nom_public: str | None, elements: str) -> None:
	"""Chaque sonore par son titre, chaque banque par son nom, dans l'ordre."""
	creee = base_vide.execute(
		"INSERT INTO sequences (nom_interne, nom_public) VALUES (%s, %s) RETURNING id", (nom, nom_public)
	).fetchone()
	assert creee is not None
	for position, (genre, element) in enumerate(ELEMENT.findall(elements), start=1):
		colonne = {"le sonore": "sonore_id", "la banque": "banque_id"}[genre]
		numero = identifiant(
			base_vide, *{"le sonore": ("sonores", "titre"), "la banque": ("banques", "nom_interne")}[genre], element
		)
		base_vide.execute(
			f"INSERT INTO sequences_elements (sequence_id, position, {colonne}) VALUES (%s, %s, %s)",  # noqa: S608
			(creee[0], position, numero),
		)


@given(parsers.parse("l'événement « {evenement} » joue la séquence « {nom} »"))
def evenement_jouant(base_vide: Connexion, evenement: str, nom: str) -> None:
	"""La séquence s'ajoute en fin de la liste de l'événement."""
	numero = identifiant(base_vide, "evenements", "nom_interne", evenement)
	base_vide.execute(
		"INSERT INTO evenements_elements (evenement_id, position, sequence_id)"
		" SELECT %s, COALESCE(MAX(position), 0) + 1, %s FROM evenements_elements WHERE evenement_id = %s",
		(numero, identifiant(base_vide, "sequences", "nom_interne", nom), numero),
	)


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
	assert interface.horloge is not None
	remplacer_dialogues(interface)
	interface.connexion = connecter(*parametres_base_test(), Role.INTERFACE)
	interface.fenetre = FenetrePrincipale(interface.connexion, interface.repertoire / "lecture.sock", interface.horloge)
	interface.fenetre.detail_demande.connect(lambda genre, numero: interface.demandes.append((genre, numero)))

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


@when(parsers.re(r"je choisis le (?P<champ>mode|masquage) « (?P<texte>[^»]+) »"))
def choisir_dans_la_fiche(interface: Contexte, champ: str, texte: str) -> None:
	ui = fiche_ouverte(interface).ui  # type: ignore[attr-defined]
	liste = getattr(ui, champ)
	indice = liste.findText(texte, Qt.MatchFlag.MatchFixedString)
	assert indice >= 0, f"« {texte} » absent du choix du {champ}"
	liste.setCurrentIndex(indice)


@when("j'enregistre la fiche")
def enregistrer(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(fiche_ouverte(interface).bouton_enregistrer, Qt.MouseButton.LeftButton)


@when("j'annule les modifications de la fiche")
def annuler(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(fiche_ouverte(interface).bouton_annuler, Qt.MouseButton.LeftButton)


@when(parsers.parse("le sonore « {titre} » est effacé de la base"))
def effacer(base_vide: Connexion, titre: str) -> None:
	base_vide.execute("DELETE FROM sonores WHERE titre = %s", (titre,))


@when(parsers.parse("la banque « {nom} » est effacée de la base"))
def effacer_banque(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("DELETE FROM banques WHERE nom_interne = %s", (nom,))


@when(parsers.re(r"j'ajoute les (?P<genre>sonores|banques) (?P<noms>aucun|« [^»]+ »(?:, « [^»]+ »)*)"))
def ajouter_elements(interface: Contexte, qtbot: QtBot, base_vide: Connexion, genre: str, noms: str) -> None:
	"""Le choix donnera ces sonores, par leur titre, ou ces banques, par leur nom ; « aucun » : le choix est
	abandonné."""
	ui = fiche_ouverte(interface).ui  # type: ignore[attr-defined]
	if genre == "sonores":
		interface.sonores_choisis = [identifiant(base_vide, "sonores", "titre", nom) for nom in NOM.findall(noms)]
		qtbot.mouseClick(ui.ajouter_sonores, Qt.MouseButton.LeftButton)
	else:
		interface.banques_choisies = [
			identifiant(base_vide, "banques", "nom_interne", nom) for nom in NOM.findall(noms)
		]
		qtbot.mouseClick(ui.ajouter_banques, Qt.MouseButton.LeftButton)


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


@when(parsers.parse("je réponds « {reponse} » à la question de fermeture"))
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


@then(parsers.parse("la question de fermeture a nommé « {titre} »"))
def question_de_fermeture(interface: Contexte, titre: str) -> None:
	assert interface.questions == [f"fermeture : {titre}"]


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
	attendues = [dict(zip(entetes, (v.strip() for v in valeurs), strict=True)) for valeurs in rangees]
	assert lignes(interface) == attendues, lignes(interface)


@then(parsers.re(r"la liste montre les titres (?P<titres>.+)"))
def titres_affiches(interface: Contexte, titres: str) -> None:
	assert [ligne["Titre"] for ligne in lignes(interface)] == NOM.findall(titres), lignes(interface)


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


@then(parsers.parse("la barre d'état annonce « {texte} »"))
def barre_d_etat(interface: Contexte, texte: str) -> None:
	assert fenetre(interface).statusBar().currentMessage() == texte
