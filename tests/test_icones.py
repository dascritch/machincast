"""Scénarios des icônes des genres (https://github.com/dascritch/machincast/issues/215).

Les étapes de la fenêtre, des fiches, des menus et des éléments en base sont dans tests/etapes_interface.py.
"""

from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPalette
from PySide6.QtWidgets import QApplication
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import icones
from machincast.interface.fiche_sonore import FicheSonore
from machincast.interface.recherche import EcranRecherche
from tests.etapes_interface import NOM, Contexte, actions, fenetre

scenarios("icones.feature")

TAILLE = 24


def image(icone: QIcon, taille: int = TAILLE) -> QImage:
	return icone.pixmap(taille).toImage().convertToFormat(QImage.Format.Format_ARGB32)


def _attendue(nom: str) -> QImage | None:
	"""L'image de l'icône d'un genre, ou None pour « aucune »."""
	if nom == "aucune":
		return None
	return image(icones.icone(nom))


def _portee(icone: QIcon | None) -> QImage | None:
	if (icone is None) or (icone.isNull()):
		return None
	return image(icone)


@then(
	parsers.re(
		r"l'icône « (?P<genre>[^»]+) », dessinée en (?P<couleur>#[0-9a-f]{6}), n'a que cette couleur,"
		r" et se voit à (?P<tailles>.+) pixels"
	)
)
def monochrome(qapp: QApplication, genre: str, couleur: str, tailles: str) -> None:
	attendue = QColor(couleur)
	for taille in (int(texte) for texte in tailles.replace(" et ", ", ").split(", ")):
		dessin = image(icones.icone(genre, attendue), taille)
		assert (dessin.width(), dessin.height()) == (taille, taille)
		pixels = [dessin.pixelColor(x, y) for x in range(taille) for y in range(taille)]
		# Chaque pixel net est de la couleur demandée ; les bords lissés, presque transparents, perdent un peu de
		# précision, d'où la marge d'arrondi.
		nets = [pixel for pixel in pixels if pixel.alpha() > 128]
		ecarts = [
			max(
				abs(pixel.red() - attendue.red()),
				abs(pixel.green() - attendue.green()),
				abs(pixel.blue() - attendue.blue()),
			)
			for pixel in nets
		]
		assert max(ecarts) <= 3, (genre, taille, max(ecarts))
		assert len(nets) >= len(pixels) / 10, (genre, taille)


@then(parsers.re(r"les icônes (?P<noms>«.+) sont toutes différentes"))
def differentes(qapp: QApplication, noms: str) -> None:
	images = [image(icones.icone(nom)) for nom in NOM.findall(noms)]
	assert all((a != b) for rang, a in enumerate(images) for b in images[rang + 1 :])


@pytest.fixture
def palette_d_origine(qapp: QApplication) -> Iterator[None]:
	origine = QPalette(qapp.palette())
	yield
	qapp.setPalette(origine)


@when(parsers.parse("le thème de l'application écrit en {couleur}"))
def theme(qapp: QApplication, palette_d_origine: None, couleur: str) -> None:
	palette = QPalette(qapp.palette())
	palette.setColor(QPalette.ColorRole.WindowText, QColor(couleur))
	qapp.setPalette(palette)


@then(parsers.parse("l'icône « {genre} » de l'application est dessinée en {couleur}"))
def suit_le_theme(qapp: QApplication, genre: str, couleur: str) -> None:
	assert image(icones.icone(genre)) == image(icones.icone(genre, QColor(couleur)))


def _onglets(interface: Contexte) -> dict[str, QIcon]:
	onglets = fenetre(interface).ui.onglets
	return {onglets.tabText(indice): onglets.tabIcon(indice) for indice in range(onglets.count())}


@then("les onglets portent les icônes :")
def icones_des_onglets(interface: Contexte, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	portees = _onglets(interface)
	assert list(portees) == [titre.strip() for titre, _icone in rangees]
	for titre, nom in rangees:
		assert _portee(portees[titre.strip()]) == _attendue(nom.strip()), titre


@then(parsers.parse("l'onglet « {titre} » porte l'icône « {nom} »"))
def icone_d_un_onglet(interface: Contexte, titre: str, nom: str) -> None:
	assert _portee(_onglets(interface)[titre]) == _attendue(nom)


@then(parsers.parse("les entrées du menu « {menu} » portent les icônes :"))
def icones_du_menu(interface: Contexte, menu: str, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	portees = {action.text(): action.icon() for action in actions(interface, menu) if not action.isSeparator()}
	for entree, nom in rangees:
		assert _portee(portees[entree.strip()]) == _attendue(nom.strip()), entree


@then("les résultats de la recherche portent les icônes :")
def icones_de_la_recherche(interface: Contexte, qtbot: QtBot, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	(recherche,) = fenetre(interface).findChildren(EcranRecherche)
	modele = recherche.table.model()
	qtbot.waitUntil(lambda: modele.rowCount() == len(rangees))
	for rangee, (genre, nom, icone) in enumerate(rangees):
		type_ = modele.index(rangee, 0)
		assert (type_.data(), modele.index(rangee, 1).data()) == (genre.strip(), nom.strip())
		assert _portee(type_.data(Qt.ItemDataRole.DecorationRole)) == _attendue(icone.strip()), genre


@then("les relations de la fiche portent les icônes :")
def icones_des_relations(interface: Contexte, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	fiche = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(fiche, FicheSonore)
	table = fiche.ui.relations
	assert table.rowCount() == len(rangees)
	for rangee, (genre, nom, icone) in enumerate(rangees):
		cellule_genre, cellule_nom = table.item(rangee, 0), table.item(rangee, 1)
		assert (cellule_genre is not None) and (cellule_nom is not None)
		assert (cellule_genre.text(), cellule_nom.text()) == (genre.strip(), nom.strip())
		assert _portee(cellule_genre.icon()) == _attendue(icone.strip()), genre


@when(parsers.parse("je tape « {texte} » dans le champ de recherche"))
def taper(interface: Contexte, texte: str) -> None:
	(recherche,) = fenetre(interface).findChildren(EcranRecherche)
	recherche.champ.setText(texte)


@then("les boutons de l'accueil portent les icônes :")
def icones_de_l_accueil(interface: Contexte, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	ui = fenetre(interface).accueil.ui
	for nom, icone in rangees:
		bouton = getattr(ui, nom.strip())
		assert _portee(bouton.icon()) == _attendue(icone.strip()), nom


@then(
	parsers.re(
		r"le bouton « (?P<nom>[^»]+) » de (?P<ou>la fiche ouverte|l'accueil|la fenêtre)"
		r" porte l'icône « (?P<icone>[^»]+) »"
	)
)
def icone_du_bouton(interface: Contexte, nom: str, ou: str, icone: str) -> None:
	ouverte = fenetre(interface)
	porteur: object = ouverte.ui
	if ou == "l'accueil":
		porteur = ouverte.accueil.ui
	if ou == "la fiche ouverte":
		porteur = ouverte.ui.onglets.currentWidget().ui
	assert _portee(getattr(porteur, nom).icon()) == _attendue(icone), nom


@then("les icônes du thème des écrans sont seulement :")
def icones_du_theme(datatable: list[list[str]]) -> None:
	"""Chaque iconset theme des fichiers .ui, avec le widget qui le porte."""
	_entetes, *rangees = datatable
	trouvees = []
	for fichier in sorted((Path(icones.__file__).parent / "ui").glob("*.ui")):
		for widget in ElementTree.parse(fichier).iter("widget"):
			for propriete in widget.findall("property[@name='icon']"):
				for iconset in propriete.iter("iconset"):
					trouvees.append([fichier.name, str(widget.get("name")), str(iconset.get("theme"))])
	assert trouvees == [[cellule.strip() for cellule in rangee] for rangee in rangees]
