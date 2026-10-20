"""Scénarios des marques-pages de streams : leur liste et leur fiche (https://github.com/dascritch/machincast/issues/34).

Les étapes de la fenêtre, des listes, des fiches, de la suppression et des fenêtres de dialogue sont dans
tests/etapes_interface.py ; le serveur de flux local, dans tests/etapes_diffusion.py.
"""

from PySide6.QtCore import Qt
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.fiche_marque_page import FicheMarquePage
from tests.etapes_interface import NOM, Connexion, Contexte, fenetre, ouvrir_dans, taper
from tests.flux import ServeurDeFlux

scenarios("fiche_marque_page.feature")


def fiche(interface: Contexte) -> FicheMarquePage:
	ouverte = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(ouverte, FicheMarquePage), ouverte
	return ouverte


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le flux « {flux} » du serveur local est avare"))
def avare(serveur: ServeurDeFlux, flux: str) -> None:
	serveur.avares.add(flux)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je saisis (?:le nom|(?P<adresse>l'adresse)) du marque-page « (?P<texte>[^»]*) »"))
def saisir(interface: Contexte, qtbot: QtBot, adresse: str | None, texte: str) -> None:
	ui = fiche(interface).ui
	champ = ui.nom
	if adresse is not None:
		champ = ui.url
	taper(qtbot, champ, texte)


@when(parsers.parse("je saisis l'adresse du flux « {flux} » du serveur local dans la fiche du marque-page"))
def adresse_locale(interface: Contexte, qtbot: QtBot, serveur: ServeurDeFlux, flux: str) -> None:
	taper(qtbot, fiche(interface).ui.url, serveur.adresse(flux))


@when("je teste le flux du marque-page")
def lancer_essai(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(fiche(interface).ui.tester, Qt.MouseButton.LeftButton)


@when(parsers.parse("le serveur de flux local a bientôt {nombre:d} connexion"))
@then(parsers.parse("le serveur de flux local a bientôt {nombre:d} connexion"))
def connexions(serveur: ServeurDeFlux, qtbot: QtBot, nombre: int) -> None:
	qtbot.waitUntil(lambda: serveur.connexions == nombre, timeout=5000)


@then("le serveur de flux local n'a bientôt plus de connexion")
def plus_de_connexion(serveur: ServeurDeFlux, qtbot: QtBot) -> None:
	qtbot.waitUntil(lambda: serveur.connexions == 0, timeout=5000)


@when(parsers.parse("j'ouvre le stream « {titre} » du marque-page"))
def ouvrir_stream(interface: Contexte, qtbot: QtBot, titre: str) -> None:
	ouvrir_dans(qtbot, fiche(interface).ui.streams, titre)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"la fiche du marque-page montre le nom « (?P<nom>[^»]*) » et l'adresse « (?P<url>[^»]*) »"))
def champs(interface: Contexte, nom: str, url: str) -> None:
	ui = fiche(interface).ui
	assert (ui.nom.text(), ui.url.text()) == (nom.strip(), url.strip())


@then(parsers.re(r"la fiche du marque-page montre les streams (?P<titres>aucun|«.+)"))
def streams(interface: Contexte, titres: str) -> None:
	liste = fiche(interface).ui.streams
	assert [liste.item(rangee).text() for rangee in range(liste.count())] == NOM.findall(titres)


@then(parsers.parse("le marque-page « {nom} » est en base, à l'adresse « {url} »"))
def en_base(base_vide: Connexion, nom: str, url: str) -> None:
	lignes = base_vide.execute("SELECT url FROM marques_pages_streams WHERE nom = %s", (nom,)).fetchall()
	assert lignes == [(url,)]


@then(parsers.parse("le stream « {titre} » joue l'adresse « {url} »"))
def adresse_jouee(base_vide: Connexion, titre: str, url: str) -> None:
	lignes = base_vide.execute(
		"SELECT COALESCE(s.url_stream, m.url) FROM sonores s"
		" LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id WHERE s.titre = %s",
		(titre,),
	).fetchall()
	assert lignes == [(url,)]


@then(parsers.parse("le test du flux du marque-page dit bientôt « {verdict} »"))
def verdict(interface: Contexte, qtbot: QtBot, verdict: str) -> None:
	ui = fiche(interface).ui
	qtbot.waitUntil(lambda: ui.resultat_essai.text() == verdict, timeout=15000)


@then("le test du flux du marque-page dit bientôt qu'il ne répond pas")
def muet(interface: Contexte, qtbot: QtBot) -> None:
	ui = fiche(interface).ui
	qtbot.waitUntil(lambda: ui.resultat_essai.text().startswith("Le flux ne répond pas : "), timeout=15000)
	assert ui.tester.isEnabled()
