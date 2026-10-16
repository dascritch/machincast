"""Étapes partagées des scénarios de la fenêtre de l'interface : onglets, listes et fiches
(https://github.com/dascritch/machincast/issues/26, https://github.com/dascritch/machincast/issues/31).

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
from PySide6.QtCore import QCoreApplication, QEvent, QModelIndex, QPoint, Qt
from PySide6.QtWidgets import QAbstractItemView, QLineEdit, QPushButton, QTabBar, QWidget
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

	def sonores(_parent: QWidget, _connexion: Connexion) -> list[int]:
		return interface.sonores_choisis

	monkeypatch.setattr(dialogues, "confirmer_fermeture", fermeture)
	monkeypatch.setattr(dialogues, "confirmer_retrait", retrait)
	monkeypatch.setattr(dialogues, "choisir_repertoire", repertoire)
	monkeypatch.setattr(dialogues, "choisir_sonores", sonores)
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
		{titre: str(modele.index(rangee, colonne).data() or "") for colonne, titre in enumerate(titres)}
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
	trouve: QModelIndex | None = None
	for rangee in range(modele.rowCount()):
		for colonne in range(modele.columnCount()):
			if modele.index(rangee, colonne).data() == nom:
				trouve = modele.index(rangee, colonne)
	assert trouve is not None, f"aucune ligne « {nom} »"
	table.scrollTo(trouve)
	centre = table.visualRect(trouve).center()
	qtbot.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=centre)
	qtbot.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=centre)


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
				ligne["artiste"] or None,
				ligne["titre"] or None,
				ligne["etat"],
				timedelta(seconds=int(ligne["duree"])) if ligne["duree"] else None,
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


@given(
	parsers.parse(
		"la séquence « {nom} », de nom public « {nom_public} », avec le sonore « {sonore} » et la banque « {banque} »"
	)
)
def sequence(base_vide: Connexion, nom: str, nom_public: str, sonore: str, banque: str) -> None:
	creee = base_vide.execute(
		"INSERT INTO sequences (nom_interne, nom_public) VALUES (%s, %s) RETURNING id", (nom, nom_public)
	).fetchone()
	assert creee is not None
	base_vide.execute(
		"INSERT INTO sequences_elements (sequence_id, position, sonore_id) VALUES (%s, 1, %s)",
		(creee[0], identifiant(base_vide, "sonores", "titre", sonore)),
	)
	base_vide.execute(
		"INSERT INTO sequences_elements (sequence_id, position, banque_id) VALUES (%s, 2, %s)",
		(creee[0], identifiant(base_vide, "banques", "nom_interne", banque)),
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
				ligne["nom_public"] or None,
				ligne["priorite"],
				datetime.fromisoformat(ligne["debut"]).astimezone() if ligne["debut"] else None,
				datetime.fromisoformat(ligne["fin"]).astimezone() if ligne["fin"] else None,
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


@when("j'enregistre la fiche")
def enregistrer(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(fiche_ouverte(interface).bouton_enregistrer, Qt.MouseButton.LeftButton)


@when("j'annule les modifications de la fiche")
def annuler(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(fiche_ouverte(interface).bouton_annuler, Qt.MouseButton.LeftButton)


@when(parsers.parse("le sonore « {titre} » est effacé de la base"))
def effacer(base_vide: Connexion, titre: str) -> None:
	base_vide.execute("DELETE FROM sonores WHERE titre = %s", (titre,))


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


@then(parsers.parse("la barre d'état annonce « {texte} »"))
def barre_d_etat(interface: Contexte, texte: str) -> None:
	assert fenetre(interface).statusBar().currentMessage() == texte
