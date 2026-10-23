"""Scénarios de la conformation des textes (https://github.com/dascritch/machincast/issues/108).

Les étapes de la fenêtre, des fiches et de la base sont dans tests/etapes_interface.py. « \\u{a0} » écrit dans un
scénario le caractère U+00A0 : les caractères invisibles ou de contrôle ne se lisent pas dans un tableau Gherkin.
"""

import re

import gi
import psycopg
from PySide6.QtWidgets import QLineEdit
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.conformation import conformer
from tests.etapes_interface import Contexte, fenetre, ouvrir_ligne, ouvrir_onglet

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from machincast.indexation.tags import Tags, extraire  # noqa: E402

scenarios("conformation.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
ECHAPPEMENT = re.compile(r"\\u\{([0-9a-fA-F]+)\}")
TABLES = {"banques", "sequences", "evenements", "feeds", "sonores"}
"""Les tables dont un scénario lit une colonne : chacune n'a qu'une ligne."""


def decoder(texte: str) -> str:
	"""« \\u{a0} » devient le caractère U+00A0."""
	return ECHAPPEMENT.sub(lambda trouve: chr(int(trouve.group(1), 16)), texte)


# ─── Fonction ──────────────────────────────────────────────


@when(parsers.re(r"je conforme le texte « (?P<texte>.*) »"), target_fixture="conforme")
def conformer_le_texte(texte: str) -> str:
	return conformer(decoder(texte))


@then(parsers.re(r"le texte conformé est « (?P<attendu>.*) »"))
def texte_conforme(conforme: str, attendu: str) -> None:
	assert conforme == attendu, ascii(conforme)


# ─── Tags ──────────────────────────────────────────────────


@given("les tags d'un fichier :", target_fixture="liste_de_tags")
def tags_du_fichier(datatable: list[list[str]]) -> Gst.TagList:
	Gst.init(None)
	liste = Gst.TagList.new_empty()
	for tag, valeur in (rangee for rangee in datatable[1:]):
		liste.add_value(Gst.TagMergeMode.APPEND, tag.strip(), decoder(valeur.strip()))
	return liste


@when("l'indexeur extrait ces tags", target_fixture="tags_extraits")
def extraire_les_tags(liste_de_tags: Gst.TagList) -> Tags:
	return extraire(liste_de_tags)


@then(parsers.parse("l'artiste extrait est « {artiste} », le titre « {titre} »"))
def artiste_et_titre(tags_extraits: Tags, artiste: str, titre: str) -> None:
	assert (tags_extraits.artiste, tags_extraits.titre) == (artiste, titre)


@then(parsers.parse("les métadonnées musicales extraites sont « {cle} » « {valeur} », sans genre"))
def metadonnees(tags_extraits: Tags, cle: str, valeur: str) -> None:
	assert tags_extraits.metadonnees == {cle: valeur}


# ─── Fiches ────────────────────────────────────────────────


@when(parsers.parse("j'ouvre la fiche du feed « {nom} »"))
def ouvrir_feed(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	ouvrir_onglet(interface, "Feeds")
	ouvrir_ligne(interface, qtbot, nom)


@when(parsers.re(r"je saisis « (?P<saisie>.*) » dans le champ « (?P<champ>\w+) » de la fiche"))
def saisir(interface: Contexte, saisie: str, champ: str) -> None:
	"""Comme une méthode de saisie : le texte entre tel quel dans le champ."""
	fiche = fenetre(interface).ui.onglets.currentWidget()
	ligne = getattr(fiche.ui, champ)
	assert isinstance(ligne, QLineEdit)
	ligne.selectAll()
	ligne.insert(decoder(saisie))


@then(parsers.re(r"en base, (?P<colonne>[\w.]+) de (?P<table>\w+) vaut « (?P<attendu>.*) »"))
def en_base(base_vide: Connexion, colonne: str, table: str, attendu: str) -> None:
	assert table in TABLES
	cle = None
	if "." in colonne:
		colonne, cle = colonne.split(".")
	lignes = base_vide.execute(f"SELECT {colonne} FROM {table}").fetchall()  # noqa: S608
	assert len(lignes) == 1, lignes
	valeur = lignes[0][0]
	if (cle is not None) and (isinstance(valeur, dict)):
		valeur = valeur.get(cle)
	assert ((valeur) or ("")) == attendu, ascii(valeur)
