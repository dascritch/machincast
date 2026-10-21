"""Suggestions au lancement de l'interface (https://github.com/dascritch/machincast/issues/119).

La fenêtre des suggestions est remplacée par les réponses du scénario (tests/etapes_interface.py) ; la vraie fenêtre
s'ouvre ici, hors de l'écran du poste.
"""

import re
from collections.abc import Iterator

import pytest
import tomlkit
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialogButtonBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.suggestions import BANQUES, FIL_MUSICAL, FenetreSuggestions, Manques, Reponse, libelle
from tests.etapes_interface import NOM, Connexion, Contexte, fenetre, fichier_de_configuration

scenarios("suggestions.feature")


# ─── Étant donné ───────────────────────────────────────────


@given("les suggestions au lancement sont actives")
def actives(interface: Contexte) -> None:
	interface.suggestions_actives = True


@given("les suggestions au lancement sont éteintes dans le fichier de configuration")
def eteintes(interface: Contexte) -> None:
	chemin = fichier_de_configuration(interface)
	document = tomlkit.parse(chemin.read_text(encoding="utf-8"))
	section = tomlkit.table()
	section["suggestions"] = False
	document["interface"] = section
	chemin.write_text(tomlkit.dumps(document), encoding="utf-8")


@given("les banques suggérées existent déjà")
def banques_existantes(base_vide: Connexion) -> None:
	for nom in BANQUES:
		base_vide.execute("INSERT INTO banques (nom_interne, mode) VALUES (%s, 'aleatoire')", (nom,))


@given(
	parsers.re(
		r"les suggestions seront refermées par « Plus tard »(?P<case>, en cochant « Ne plus proposer au lancement »)?"
	)
)
def plus_tard(interface: Contexte, case: str | None) -> None:
	interface.reponse_aux_suggestions = lambda _manques: Reponse(creer=False, ne_plus_proposer=case is not None)


@given(
	parsers.re(
		r"les suggestions seront acceptées par « Créer »(?:, sans « (?P<sans>.+) »)?"
		r"(?:, avec l'antenne « (?P<antenne>[^»]+) »)?$"
	)
)
def creer(interface: Contexte, sans: str | None, antenne: str | None) -> None:
	def repondre(manques: Manques) -> Reponse:
		banques = tuple(banque for banque in manques.banques if libelle(banque) != sans)
		return Reponse(
			creer=True,
			fil_musical=(manques.fil_musical) and (sans != FIL_MUSICAL),
			banques=banques,
			antenne=antenne,
		)

	interface.reponse_aux_suggestions = repondre


# ─── Alors ─────────────────────────────────────────────────


def premieres(interface: Contexte) -> Manques:
	assert interface.suggestions_faites, "aucune suggestion"
	return interface.suggestions_faites[0]


@then("les suggestions ont proposé :")
def proposees(interface: Contexte, datatable: list[list[str]]) -> None:
	_entete, *lignes = datatable
	assert premieres(interface).elements() == [ligne.strip() for (ligne,) in lignes]


@then("les suggestions n'ont pas proposé de périphérique d'antenne")
def sans_antenne(interface: Contexte) -> None:
	assert premieres(interface).antennes is None


@then(parsers.re(r"les suggestions ont proposé les périphériques d'antenne (?P<liste>«.+)"))
def antennes_proposees(interface: Contexte, liste: str) -> None:
	antennes = premieres(interface).antennes
	assert antennes is not None
	assert [peripherique.identifiant for peripherique in antennes] == NOM.findall(liste)


@then("aucune suggestion n'a été faite")
def aucune(interface: Contexte) -> None:
	assert interface.suggestions_faites == []


@then(parsers.parse("les suggestions ont été faites {nombre:d} fois"))
def nombre_de_fois(interface: Contexte, nombre: int) -> None:
	assert len(interface.suggestions_faites) == nombre


@then(parsers.re(r"il n'y a aucun(?:e)? (?P<genre>événement|banque) en base"))
def rien_en_base(base_vide: Connexion, genre: str) -> None:
	table = {"événement": "evenements", "banque": "banques"}[genre]
	ligne = base_vide.execute(f"SELECT count(*) FROM {table}").fetchone()  # noqa: S608
	assert ligne == (0,), ligne


@then(parsers.parse("le fil musical « {nom} » est en base, permanent"))
def fil_permanent(base_vide: Connexion, nom: str) -> None:
	lignes = base_vide.execute(
		"SELECT priorite::text, debut, fin, jours_recurrence::text[] FROM evenements WHERE nom_interne = %s", (nom,)
	).fetchall()
	assert lignes == [("fil_musical", None, None, [])], lignes


@then(parsers.re(r"la liste de l'événement « (?P<nom>[^»]+) » est en base (?P<banques>«.+)"))
def liste_du_fil(base_vide: Connexion, nom: str, banques: str) -> None:
	lignes = base_vide.execute(
		"SELECT b.nom_interne FROM evenements_elements x JOIN evenements e ON e.id = x.evenement_id"
		" JOIN banques b ON b.id = x.banque_id WHERE e.nom_interne = %s ORDER BY x.position",
		(nom,),
	).fetchall()
	assert [str(banque) for (banque,) in lignes] == NOM.findall(banques)


@then(parsers.re(r"les fils musicaux en base sont (?P<noms>«.+)"))
def fils(base_vide: Connexion, noms: str) -> None:
	lignes = base_vide.execute(
		"SELECT nom_interne FROM evenements WHERE priorite = 'fil_musical' ORDER BY nom_interne"
	).fetchall()
	assert [str(nom) for (nom,) in lignes] == NOM.findall(noms)


@then("les banques en base sont :")
def banques_en_base(base_vide: Connexion, datatable: list[list[str]]) -> None:
	_entete, *lignes = datatable
	lues = base_vide.execute(
		'SELECT nom_interne, mode::text, ne_pas_repeter FROM banques ORDER BY nom_interne COLLATE "C"'
	).fetchall()
	attendues = [(nom.strip(), mode.strip(), repeter.strip() == "oui") for nom, mode, repeter in lignes]
	assert lues == attendues, lues


@then(parsers.parse("le fichier de configuration contient la ligne « {ligne} »"))
def contient_la_ligne(interface: Contexte, ligne: str) -> None:
	assert ligne in fichier_de_configuration(interface).read_text(encoding="utf-8").splitlines()


@then(parsers.parse("le fichier de configuration contient encore « {texte} »"))
def contient_encore(interface: Contexte, texte: str) -> None:
	assert texte in fichier_de_configuration(interface).read_text(encoding="utf-8")


@then("le fichier de configuration n'a pas changé")
def inchange(interface: Contexte) -> None:
	assert fichier_de_configuration(interface).read_bytes() == interface.configuration_initiale


# ─── Vraie fenêtre ─────────────────────────────────────────


@pytest.fixture
def parent(qtbot: QtBot) -> Iterator[QWidget]:
	widget = QWidget()
	qtbot.addWidget(widget)
	yield widget


@pytest.fixture
def ouverte() -> dict[str, object]:
	return {}


def la_fenetre(ouverte: dict[str, object]) -> FenetreSuggestions:
	fenetre = ouverte["fenetre"]
	assert isinstance(fenetre, FenetreSuggestions)
	return fenetre


@when(
	parsers.re(
		r"la fenêtre des suggestions s'ouvre sur le fil musical et la banque « (?P<banque>[^»]+) »,"
		r" avec l'antenne à choisir sur « (?P<sortie>[^»]+) »"
	)
)
def ouvrir(ouverte: dict[str, object], parent: QWidget, banque: str, sortie: str) -> None:
	from machincast import audio

	antennes = tuple(p for p in audio.peripheriques("pipewire") if p.identifiant != "preecoute-factice")
	assert sortie == "pipewire"
	ouverte["fenetre"] = FenetreSuggestions(Manques(True, (banque,), antennes), parent)


@then(parsers.parse("elle s'intitule « {titre} »"))
def titre(ouverte: dict[str, object], titre: str) -> None:
	assert la_fenetre(ouverte).windowTitle() == titre


@then(parsers.re(r"elle propose, cochés, (?P<elements>«.+)"))
def coches(ouverte: dict[str, object], elements: str) -> None:
	liste = la_fenetre(ouverte).ui.elements
	lignes = [liste.item(rang) for rang in range(liste.count())]
	assert [ligne.text() for ligne in lignes] == re.findall(r"« ((?:[^«»]|« [^»]+ »)+) »", elements)
	assert all(ligne.checkState() == Qt.CheckState.Checked for ligne in lignes)


@then(parsers.re(r"son choix de l'antenne propose (?P<noms>«.+), sans la pré-écoute"))
def choix_antenne(ouverte: dict[str, object], noms: str) -> None:
	choix = la_fenetre(ouverte).ui.antenne
	assert la_fenetre(ouverte).ui.groupe_antenne.isVisibleTo(la_fenetre(ouverte))
	assert [choix.itemText(rang) for rang in range(choix.count())] == NOM.findall(noms)


@when(parsers.parse("j'y décoche « {texte} »"))
def decocher(ouverte: dict[str, object], texte: str) -> None:
	liste = la_fenetre(ouverte).ui.elements
	(ligne,) = [liste.item(rang) for rang in range(liste.count()) if liste.item(rang).text() == texte]
	ligne.setCheckState(Qt.CheckState.Unchecked)


@when(parsers.parse("j'y choisis l'antenne « {nom} »"))
def choisir_antenne(ouverte: dict[str, object], nom: str) -> None:
	choix = la_fenetre(ouverte).ui.antenne
	choix.setCurrentIndex(choix.findText(nom))


@when("j'y coche « Ne plus proposer au lancement »")
def cocher_ne_plus(ouverte: dict[str, object]) -> None:
	la_fenetre(ouverte).ui.ne_plus_proposer.setChecked(True)


@when("j'y clique sur « Créer »")
def cliquer_creer(ouverte: dict[str, object]) -> None:
	fenetre = la_fenetre(ouverte)
	fenetre.ui.boutons.button(QDialogButtonBox.StandardButton.Ok).click()
	ouverte["reponse"] = fenetre.reponse()


@then(parsers.re(r"elle a donné : la banque « (?P<banque>[^»]+) », l'antenne « (?P<antenne>[^»]+) », ne plus proposer"))
def donne(ouverte: dict[str, object], banque: str, antenne: str) -> None:
	assert la_fenetre(ouverte).result() == FenetreSuggestions.DialogCode.Accepted
	assert ouverte["reponse"] == Reponse(
		creer=True, fil_musical=False, banques=(banque,), antenne=antenne, ne_plus_proposer=True
	)


@then(parsers.re(r"la barre d'état (?P<signale>signale|ne signale pas) « Périphérique de l'antenne à renseigner »"))
def antenne_signalee(interface: Contexte, signale: str) -> None:
	ouverte = fenetre(interface)
	assert ouverte.antenne_a_renseigner.isVisibleTo(ouverte) == (signale == "signale")
