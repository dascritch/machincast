"""Scénarios du calendrier de la grille (https://github.com/dascritch/machincast/issues/36,
https://github.com/dascritch/machincast/issues/118).

Les étapes de la fenêtre, de ses menus et de ses onglets sont dans tests/etapes_interface.py. Le calendrier se montre
dans une fenêtre visible, hors écran, à une taille fixe : ses blocs y ont une place, où les étapes cliquent et
survolent.
"""

import re
import uuid
from datetime import date, datetime, time, timedelta

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QApplication, QCheckBox, QPushButton, QToolTip, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.calendrier import Bande, Bloc, Calendrier, libelle_du_jour
from machincast.interface.fiche_evenement import FicheEvenement
from tests.etapes_interface import NOM, Connexion, Contexte, fenetre, identifiant

scenarios("calendrier.feature")

TAILLE = (1400, 900)
"""Taille de la fenêtre pendant les scénarios du calendrier."""
SUPPRIME = "(supprimé)"
"""Un passage dont l'événement a été supprimé : son evenement_id est vide."""


def calendrier(interface: Contexte) -> Calendrier:
	"""Le calendrier ouvert, dans une fenêtre montrée à sa taille, ses blocs placés."""
	principale = fenetre(interface)
	if not principale.isVisible():
		principale.resize(*TAILLE)
		principale.show()
	QApplication.processEvents()
	ouvert = principale.ui.onglets.currentWidget()
	assert isinstance(ouvert, Calendrier), ouvert
	return ouvert


def jour_nomme(vue: Calendrier, libelle: str) -> date:
	jours = {libelle_du_jour(jour): jour for jour in vue.jours()}
	assert libelle in jours, list(jours)
	return jours[libelle]


def horaire(jour: date, moment: datetime) -> str:
	"""« 07:00 », ou « 24:00 » pour la fin du jour."""
	if moment == datetime.combine(jour + timedelta(days=1), datetime.min.time()):
		return "24:00"
	return f"{moment:%H:%M}"


def tableau(datatable: list[list[str]]) -> list[list[str]]:
	return [[valeur.strip() for valeur in rangee] for rangee in datatable[1:]]


def bloc_nomme(vue: Calendrier, nom: str, libelle: str, journee: bool = False) -> Bloc:
	jour = jour_nomme(vue, libelle)
	blocs = vue.blocs()
	if journee:
		blocs = vue.journee()
	trouves = [bloc for bloc in blocs if (bloc.jour == jour) and (bloc.evenement.nom == nom)]
	assert len(trouves) == 1, trouves
	return trouves[0]


def bande_nommee(vue: Calendrier, nom: str, debut: str, libelle: str) -> Bande:
	jour = jour_nomme(vue, libelle)
	trouvees = [b for b in vue.bandes() if (b.jour == jour) and (b.nom == nom) and (horaire(jour, b.debut) == debut)]
	assert len(trouvees) == 1, vue.bandes()
	return trouvees[0]


def infobulle(widget: QWidget, point: QPointF) -> str:
	"""Ce que montre le survol du point : l'infobulle que le widget affiche à l'événement ToolTip de Qt."""
	QToolTip.hideText()
	position = point.toPoint()
	survol = QHelpEvent(QEvent.Type.ToolTip, position, widget.mapToGlobal(position))
	QApplication.sendEvent(widget, survol)
	texte = QToolTip.text()
	QToolTip.hideText()
	return texte


def bouton(vue: Calendrier, texte: str) -> QPushButton:
	boutons = [b for b in vue.findChildren(QPushButton) if b.text() == texte]
	assert len(boutons) == 1, [b.text() for b in vue.findChildren(QPushButton)]
	return boutons[0]


def case(vue: Calendrier, texte: str) -> QCheckBox:
	cases = [c for c in vue.findChildren(QCheckBox) if c.text() == texte]
	assert len(cases) == 1, texte
	return cases[0]


# ─── Étant donné ───────────────────────────────────────────


@given("les passages de l'airplay :")
def passages(base_vide: Connexion, datatable: list[list[str]]) -> None:
	"""Une ligne de début, et une de fin quand le passage est terminé ; « (supprimé) » : sans événement."""
	for nom, debut, fin in tableau(datatable):
		evenement = None
		if nom != SUPPRIME:
			evenement = identifiant(base_vide, "evenements", "nom_interne", nom)
		passage = uuid.uuid4()
		depart = datetime.fromisoformat(debut).astimezone()
		base_vide.execute(
			"INSERT INTO airplay (passage_id, type_ligne, horodatage, evenement_id) VALUES (%s, 'debut', %s, %s)",
			(passage, depart, evenement),
		)
		if fin == "":
			continue
		arrivee = datetime.fromisoformat(fin).astimezone()
		base_vide.execute(
			"INSERT INTO airplay (passage_id, type_ligne, horodatage, evenement_id, duree_diffusee, sans_incident)"
			" VALUES (%s, 'fin', %s, %s, %s, true)",
			(passage, arrivee, evenement, arrivee - depart),
		)


@given(parsers.parse("l'événement « {nom} » supprimé le « {moment} »"))
def evenement_supprime(base_vide: Connexion, nom: str, moment: str) -> None:
	base_vide.execute(
		"UPDATE evenements SET supprime_le = %s WHERE nom_interne = %s",
		(datetime.fromisoformat(moment).astimezone(), nom),
	)


@given(parsers.parse("je répondrai « {reponse} » à la question de création"))
def reponse_de_creation(interface: Contexte, reponse: str) -> None:
	interface.creation = reponse == "Créer"


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je (?P<action>coche|décoche) la case « (?P<texte>[^»]+) » du calendrier"))
def cocher(interface: Contexte, qtbot: QtBot, action: str, texte: str) -> None:
	coche = case(calendrier(interface), texte)
	assert coche.isChecked() == (action == "décoche")
	qtbot.mouseClick(coche, Qt.MouseButton.LeftButton, pos=QPoint(2, coche.height() // 2))
	assert coche.isChecked() == (action == "coche")


@when(parsers.re(r"je clique (?:(?P<fois>\d+) fois )?sur « (?P<texte>[^»]+) » du calendrier"))
def cliquer_sur(interface: Contexte, qtbot: QtBot, fois: str | None, texte: str) -> None:
	for _ in range(int((fois) or ("1"))):
		qtbot.mouseClick(bouton(calendrier(interface), texte), Qt.MouseButton.LeftButton)


@when(parsers.parse("je double-clique sur le bloc « {nom} » du {jour}"))
def double_clic_bloc(interface: Contexte, qtbot: QtBot, nom: str, jour: str) -> None:
	vue = calendrier(interface)
	centre = vue.grille.rectangle(bloc_nomme(vue, nom, jour)).center().toPoint()
	qtbot.mouseDClick(vue.grille, Qt.MouseButton.LeftButton, pos=centre)


@when(parsers.parse("je double-clique sur la bande d'airplay « {nom} » de {debut} du {jour}"))
def double_clic_bande(interface: Contexte, qtbot: QtBot, nom: str, debut: str, jour: str) -> None:
	vue = calendrier(interface)
	centre = vue.grille.rectangle(bande_nommee(vue, nom, debut, jour)).center().toPoint()
	qtbot.mouseDClick(vue.grille, Qt.MouseButton.LeftButton, pos=centre)


@when(parsers.re(r"je clique dans le calendrier le (?P<jour>\w+ \d+(?:er)?) à (?P<heure>\d\d:\d\d)"))
def cliquer_a(interface: Contexte, qtbot: QtBot, jour: str, heure: str) -> None:
	vue = calendrier(interface)
	moment = datetime.combine(jour_nomme(vue, jour), time.fromisoformat(heure))
	qtbot.mouseClick(vue.grille, Qt.MouseButton.LeftButton, pos=vue.grille.point(moment).toPoint())


@when(parsers.parse("l'événement « {nom} » est effacé de la base"))
def effacer_evenement(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("DELETE FROM evenements WHERE nom_interne = %s", (nom,))


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le calendrier montre « {titre} »"))
def titre(interface: Contexte, titre: str) -> None:
	assert calendrier(interface).titre.text() == titre


@then(parsers.re(r"le calendrier a les jours (?P<jours>«.+)"))
def jours(interface: Contexte, jours: str) -> None:
	vue = calendrier(interface)
	assert [libelle_du_jour(jour) for jour in vue.jours()] == NOM.findall(jours)
	assert vue.entete.libelles() == NOM.findall(jours)


@then("le calendrier montre les blocs :")
def blocs(interface: Contexte, datatable: list[list[str]]) -> None:
	vue = calendrier(interface)
	lus = [
		[libelle_du_jour(b.jour), horaire(b.jour, b.debut), horaire(b.jour, b.fin), b.evenement.nom, b.etat]
		for b in vue.blocs()
	]
	assert lus == tableau(datatable)
	for bloc in vue.blocs():
		assert vue.grille.rect().contains(vue.grille.rectangle(bloc).toRect()), bloc


@then("la bande de la journée entière montre :")
def journee(interface: Contexte, datatable: list[list[str]]) -> None:
	vue = calendrier(interface)
	assert [[libelle_du_jour(b.jour), b.evenement.nom, b.etat] for b in vue.journee()] == tableau(datatable)
	for bloc in vue.journee():
		assert vue.entete.rect().contains(vue.entete.rectangle(bloc).toRect()), bloc


@then("le calendrier montre les bandes d'airplay :")
def bandes(interface: Contexte, datatable: list[list[str]]) -> None:
	vue = calendrier(interface)
	lues = [
		[libelle_du_jour(b.jour), horaire(b.jour, b.debut), horaire(b.jour, b.fin), b.nom, str(b.passages)]
		for b in vue.bandes()
	]
	assert lues == tableau(datatable)


@then("le calendrier ne montre aucun bloc")
def aucun_bloc(interface: Contexte) -> None:
	vue = calendrier(interface)
	assert (vue.blocs(), vue.journee()) == ([], [])


@then(parsers.parse("le calendrier montre {nombre:d} blocs"))
def nombre_de_blocs(interface: Contexte, nombre: int) -> None:
	assert len(calendrier(interface).blocs()) == nombre


@then(parsers.parse("les blocs « {premier} » et « {second} » du {jour} sont côte à côte"))
def cote_a_cote(interface: Contexte, premier: str, second: str, jour: str) -> None:
	vue = calendrier(interface)
	gauche = vue.grille.rectangle(bloc_nomme(vue, premier, jour))
	droite = vue.grille.rectangle(bloc_nomme(vue, second, jour))
	assert gauche.right() <= droite.left(), (gauche, droite)
	assert (gauche.width() > 0) and (droite.width() > 0)


@then(parsers.parse("le bloc « {nom} » du {jour} a toute la largeur des blocs prévus"))
def pleine_largeur(interface: Contexte, nom: str, jour: str) -> None:
	vue = calendrier(interface)
	bloc = bloc_nomme(vue, nom, jour)
	seul = vue.grille.rectangle(bloc)
	voisins = [vue.grille.rectangle(b) for b in vue.blocs() if (b.jour == bloc.jour) and (b != bloc)]
	assert all(seul.width() >= autre.width() for autre in voisins), (seul, voisins)
	assert any(seul.width() > autre.width() for autre in voisins), (seul, voisins)


@then(parsers.parse("le bloc « {nom} » du {jour} est à la place du bloc « {autre} »"))
def meme_place(interface: Contexte, nom: str, jour: str, autre: str) -> None:
	vue = calendrier(interface)
	premier = vue.grille.rectangle(bloc_nomme(vue, nom, jour))
	second = vue.grille.rectangle(bloc_nomme(vue, autre, jour))
	assert (premier.left(), premier.width()) == (second.left(), second.width())


@then(parsers.parse("le bloc « {nom} » du {jour} a l'infobulle :"))
def infobulle_du_bloc(interface: Contexte, nom: str, jour: str, docstring: str) -> None:
	vue = calendrier(interface)
	assert infobulle(vue.grille, vue.grille.rectangle(bloc_nomme(vue, nom, jour)).center()) == docstring


@then(parsers.parse("le bloc « {nom} » de la journée du {jour} a l'infobulle :"))
def infobulle_de_la_journee(interface: Contexte, nom: str, jour: str, docstring: str) -> None:
	vue = calendrier(interface)
	centre = vue.entete.rectangle(bloc_nomme(vue, nom, jour, journee=True)).center()
	assert infobulle(vue.entete, centre) == docstring


@then(parsers.parse("la bande d'airplay « {nom} » de {debut} du {jour} a l'infobulle :"))
def infobulle_de_la_bande(interface: Contexte, nom: str, debut: str, jour: str, docstring: str) -> None:
	vue = calendrier(interface)
	assert infobulle(vue.grille, vue.grille.rectangle(bande_nommee(vue, nom, debut, jour)).center()) == docstring


@then(parsers.re(r"le calendrier a les cases cochées (?P<textes>«.+)"))
def cases_cochees(interface: Contexte, textes: str) -> None:
	vue = calendrier(interface)
	assert [c.text() for c in vue.findChildren(QCheckBox) if c.isChecked()] == NOM.findall(textes)


@then(parsers.re(r"le calendrier grise les jours (?P<jours>«.+)"))
def jours_grises(interface: Contexte, jours: str) -> None:
	vue = calendrier(interface)
	assert [libelle_du_jour(jour) for jour in vue.jours_perimes()] == re.findall(r"« ([^»]+) »", jours)


@then(parsers.parse("le bouton « {texte} » du calendrier est inactif"))
def bouton_inactif(interface: Contexte, texte: str) -> None:
	assert not bouton(calendrier(interface), texte).isEnabled()


@then(parsers.parse("la question de création a dit « {texte} »"))
def question_de_creation(interface: Contexte, texte: str) -> None:
	assert interface.questions == [f"création : {texte}"]


@then(parsers.parse("la fiche de l'événement a pour début « {debut} » et pour fin « {fin} »"))
def dates_de_la_fiche(interface: Contexte, debut: str, fin: str) -> None:
	fiche = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(fiche, FicheEvenement)
	ui = fiche.ui
	assert (ui.a_debut.isChecked(), ui.a_fin.isChecked()) == (True, True)
	lues = [ui.debut.dateTime().toString("yyyy-MM-dd HH:mm"), ui.fin.dateTime().toString("yyyy-MM-dd HH:mm")]
	assert lues == [debut, fin]


@then(parsers.parse("la base a toujours {nombre:d} événements"))
def evenements_en_base(base_vide: Connexion, nombre: int) -> None:
	ligne = base_vide.execute("SELECT count(*) FROM evenements").fetchone()
	assert ligne is not None
	assert ligne[0] == nombre
