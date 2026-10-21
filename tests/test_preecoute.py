"""Scénarios de la pré-écoute d'un sonore (https://github.com/dascritch/machincast/issues/116,
https://github.com/dascritch/machincast/issues/29).

Les étapes de la fenêtre et des fiches sont dans tests/etapes_interface.py, celles du serveur de flux local dans
tests/etapes_diffusion.py. La pré-écoute joue sur la sortie factice des tests, en temps réel : ses positions et son
VU-mètre avancent comme sur un vrai périphérique. Les périphériques du poste sont remplacés par ceux du scénario.
"""

import re
import shutil
import tomllib
from datetime import timedelta
from pathlib import Path

import psycopg
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QApplication
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.exceptions import TimeoutError as DelaiDepasse
from pytestqt.qtbot import QtBot

from machincast.interface.preecoute import FenetrePreecoute
from tests.etapes_interface import NOM, Contexte, fenetre, fichier_de_configuration
from tests.etapes_preecoute import fenetre_de_preecoute
from tests.sons import FICHIERS_SONORES

scenarios("preecoute.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
DELAI = 5000
"""Millisecondes laissées à GStreamer pour ce qui arrive « bientôt »."""


def inserer(base: Connexion, interface: Contexte, titre: str, artiste: str | None, fichier: str) -> None:
	copie = interface.repertoire / fichier
	shutil.copyfile(FICHIERS_SONORES / fichier, copie)
	base.execute(
		"INSERT INTO sonores (type, emplacement, artiste, titre, etat, duree)"
		" VALUES ('fichier', %s, %s, %s, 'actif', %s)",
		(str(copie), artiste, titre, timedelta(seconds=1)),
	)


@given(parsers.parse("le sonore « {titre} » de « {artiste} », pour une copie du fichier de test « {fichier} »"))
def sonore_avec_artiste(interface: Contexte, base_vide: Connexion, titre: str, artiste: str, fichier: str) -> None:
	inserer(base_vide, interface, titre, artiste, fichier)


@given(parsers.re(r"le sonore « (?P<titre>[^»]+) », pour une copie du fichier de test « (?P<fichier>[^»]+) »"))
def sonore(interface: Contexte, base_vide: Connexion, titre: str, fichier: str) -> None:
	inserer(base_vide, interface, titre, None, fichier)


@given(parsers.parse("le fichier du sonore « {titre} » supprimé"))
def fichier_supprime(base_vide: Connexion, titre: str) -> None:
	ligne = base_vide.execute("SELECT emplacement FROM sonores WHERE titre = %s", (titre,)).fetchone()
	assert ligne is not None
	# Une copie de test, dans le répertoire temporaire du scénario.
	Path(str(ligne[0])).unlink()


@given(parsers.parse("le périphérique de l'antenne « {identifiant} »"))
def antenne(interface: Contexte, identifiant: str) -> None:
	interface.audio["peripherique"] = identifiant


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("je place la position de la pré-écoute à {pourcentage:d} %"))
def placer(interface: Contexte, pourcentage: int) -> None:
	barre = fenetre_de_preecoute(interface).ui.position
	# Comme à la souris : la barre est tenue, déplacée, puis relâchée.
	barre.setSliderDown(True)
	barre.setValue(round(barre.maximum() * pourcentage / 100))
	barre.sliderReleased.emit()
	barre.setSliderDown(False)


@when(parsers.parse("je choisis la sortie « {nom} » pour la pré-écoute"))
def choisir_la_sortie(interface: Contexte, nom: str) -> None:
	choix = fenetre_de_preecoute(interface).ui.sortie
	indice = choix.findText(nom)
	assert indice >= 0, nom
	choix.setCurrentIndex(indice)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("il n'y a qu'une fenêtre de pré-écoute, titrée « {titre} »"))
def une_seule(interface: Contexte, titre: str) -> None:
	ouvertes = [w for w in QApplication.topLevelWidgets() if (isinstance(w, FenetrePreecoute)) and (w.isVisible())]
	assert len(ouvertes) == 1
	assert ouvertes[0].windowTitle() == titre


@then(parsers.parse("la sortie de la pré-écoute est « {identifiant} »"))
def sortie(interface: Contexte, identifiant: str) -> None:
	ouverte = fenetre_de_preecoute(interface)
	assert ouverte.ui.sortie.currentData() == identifiant
	assert ouverte.lecteur.peripherique == identifiant


@then("le VU-mètre de la pré-écoute est au silence")
def au_silence(interface: Contexte) -> None:
	assert fenetre_de_preecoute(interface).vumetre.niveaux == []


@then("la pré-écoute montre bientôt les informations :")
def informations(interface: Contexte, qtbot: QtBot, datatable: list[list[str]]) -> None:
	ui = fenetre_de_preecoute(interface).ui
	champs = {"Format": ui.format, "Échantillonnage": ui.echantillonnage, "Canaux": ui.canaux}
	attendues = [(nom.strip(), valeur.strip()) for nom, valeur in datatable[1:]]

	def conforme(lue: str, attendue: str) -> bool:
		"""« contient « FLAC » » : le libellé, qui vient de GStreamer, contient ce nom ; sinon, égal."""
		contenu = re.fullmatch(r"contient « (.+) »", attendue)
		if contenu is not None:
			return contenu.group(1) in lue
		return lue == attendue

	def toutes() -> bool:
		return all(conforme(champs[nom].text(), valeur) for nom, valeur in attendues)

	try:
		qtbot.waitUntil(toutes, timeout=DELAI)
	except DelaiDepasse as erreur:
		# Les valeurs lues, pour comprendre l'écart sur un autre poste.
		lues = {nom: champs[nom].text() for nom, _valeur in attendues}
		raise AssertionError(f"informations lues : {lues}, attendues : {dict(attendues)}") from erreur


@then("le débit de la pré-écoute est bientôt donné en kbit/s")
def debit(interface: Contexte, qtbot: QtBot) -> None:
	champ = fenetre_de_preecoute(interface).ui.debit
	qtbot.waitUntil(lambda: champ.text().endswith(" kbit/s"), timeout=DELAI)


@then("la pré-écoute donne bientôt des secondes pré-décodées")
def predecode(interface: Contexte, qtbot: QtBot) -> None:
	champ = fenetre_de_preecoute(interface).ui.predecode
	qtbot.waitUntil(lambda: (champ.text().endswith(" s")) and (champ.text() != "0,0 s"), timeout=DELAI)


@then(parsers.parse("la position de la pré-écoute est bientôt entre {minimum} et {maximum} seconde"))
def position(interface: Contexte, qtbot: QtBot, minimum: str, maximum: str) -> None:
	lecteur = fenetre_de_preecoute(interface).lecteur
	bas, haut = float(minimum.replace(",", ".")), float(maximum.replace(",", "."))
	qtbot.waitUntil(lambda: bas <= ((lecteur.position()) or (0.0)) <= haut, timeout=DELAI)


@then("la pré-écoute ne joue plus rien")
def plus_rien(interface: Contexte) -> None:
	assert not fenetre_de_preecoute(interface).lecteur.actif()


@then(parsers.re(r"la pré-écoute propose les sorties (?P<noms>«.+)"))
def sorties_proposees(interface: Contexte, noms: str) -> None:
	choix = fenetre_de_preecoute(interface).ui.sortie
	assert [choix.itemText(indice) for indice in range(choix.count())] == NOM.findall(noms)


@then(parsers.parse("le fichier de configuration a pour pré-écoute « {identifiant} », avec ses commentaires"))
def configuration_ecrite(interface: Contexte, identifiant: str) -> None:
	chemin = fichier_de_configuration(interface)
	texte = chemin.read_text(encoding="utf-8")
	assert tomllib.loads(texte)["audio"]["preecoute"] == identifiant
	initiale = interface.configuration_initiale.decode("utf-8")
	commentaires = [ligne for ligne in initiale.splitlines() if ligne.startswith("#")]
	assert commentaires == [ligne for ligne in texte.splitlines() if ligne.startswith("#")]


@then("le bouton « Pré-écoute… » de la fiche est inactif")
def bouton_inactif(interface: Contexte) -> None:
	fiche = fenetre(interface).ui.onglets.currentWidget()
	assert not fiche.ui.preecouter.isEnabled()


@when(parsers.parse("je force la sortie « {nom} » pour la pré-écoute"))
def forcer_la_sortie(interface: Contexte, nom: str) -> None:
	"""Une ligne grisée ne se choisit pas à la souris : le programme la choisit, comme le ferait au pire le clavier."""
	choix = fenetre_de_preecoute(interface).ui.sortie
	indice = choix.findText(nom)
	assert indice >= 0, nom
	choix.setCurrentIndex(indice)


@then("la pré-écoute propose les sorties :")
def sorties_et_etats(interface: Contexte, datatable: list[list[str]]) -> None:
	choix = fenetre_de_preecoute(interface).ui.sortie
	modele = choix.model()
	assert isinstance(modele, QStandardItemModel)
	lues = []
	for indice in range(choix.count()):
		etat_de_la_ligne = "inactive"
		if modele.item(indice).isEnabled():
			etat_de_la_ligne = "active"
		lues.append([choix.itemText(indice), etat_de_la_ligne])
	assert lues == [[cellule.strip() for cellule in rangee] for rangee in datatable[1:]]


@then(parsers.parse("le fichier de configuration a toujours pour pré-écoute « {identifiant} »"))
def configuration_intacte(interface: Contexte, identifiant: str) -> None:
	chemin = fichier_de_configuration(interface)
	assert tomllib.loads(chemin.read_text(encoding="utf-8"))["audio"]["preecoute"] == identifiant
	assert chemin.read_bytes() == interface.configuration_initiale
