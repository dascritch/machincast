"""Scénarios de la recherche globale (https://github.com/dascritch/machincast/issues/27,
https://github.com/dascritch/machincast/issues/105).

Les étapes de la fenêtre, des onglets et des éléments en base sont dans tests/etapes_interface.py.
"""

import psycopg
import pytest
from PySide6.QtCore import Qt
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.interface import recherche
from machincast.interface.recherche import EcranRecherche
from tests.etapes_interface import NOM, Contexte, fenetre

scenarios("recherche.feature")

Connexion = psycopg.Connection[tuple[object, ...]]


def ecran(interface: Contexte) -> EcranRecherche:
	onglets = fenetre(interface).ui.onglets
	(trouve,) = [
		widget for indice in range(onglets.count()) if isinstance(widget := onglets.widget(indice), EcranRecherche)
	]
	return trouve


def lignes(interface: Contexte) -> list[list[str]]:
	modele = ecran(interface).modele
	return [
		[str((modele.index(rangee, colonne).data()) or ("")) for colonne in range(modele.columnCount())]
		for rangee in range(modele.rowCount())
	]


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("{nombre:d} sonores titrés « {premier} » à « {dernier} »"))
def sonores_numerotes(base_vide: Connexion, nombre: int, premier: str, dernier: str) -> None:
	prefixe = premier.rsplit(" ", 1)[0]
	assert dernier == f"{prefixe} {nombre:02d}"
	for numero in range(1, nombre + 1):
		base_vide.execute(
			"INSERT INTO sonores (type, emplacement, titre, etat) VALUES ('fichier', %s, %s, 'actif')",
			(f"/srv/spots/{numero:02d}.flac", f"{prefixe} {numero:02d}"),
		)


@given(parsers.parse("une table de résultats limitée à {limite:d} lignes"))
def limite(monkeypatch: pytest.MonkeyPatch, limite: int) -> None:
	monkeypatch.setattr(recherche, "LIMITE", limite)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("je tape « {texte} » dans le champ de recherche"))
def taper(interface: Contexte, texte: str) -> None:
	ecran(interface).champ.setText(texte)


@when(parsers.parse("je choisis la suggestion « {texte} »"))
def choisir_la_suggestion(interface: Contexte, texte: str) -> None:
	completer = ecran(interface).completer
	popup = completer.popup()
	assert popup is not None
	modele = popup.model()
	(rangee,) = [rangee for rangee in range(modele.rowCount()) if modele.index(rangee, 0).data() == texte]
	popup.setCurrentIndex(modele.index(rangee, 0))
	completer.activated.emit(texte)


@when(parsers.parse("j'ouvre le résultat « {nom} »"))
def ouvrir_le_resultat(interface: Contexte, nom: str) -> None:
	ouvert = ecran(interface)
	(rangee,) = [rangee for rangee, ligne in enumerate(lignes(interface)) if ligne[1] == nom]
	ouvert.table.activated.emit(ouvert.modele.index(rangee, 0))


@when(parsers.parse("la banque « {nom} » est ajoutée en base"))
def banque_ajoutee(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("INSERT INTO banques (nom_interne, mode) VALUES (%s, 'aleatoire')", (nom,))


# ─── Alors ─────────────────────────────────────────────────


@then("le champ de recherche a le focus")
def a_le_focus(interface: Contexte) -> None:
	assert fenetre(interface).focusWidget() is ecran(interface).champ


@then(parsers.parse("le champ de recherche a le focus, avec « {texte} » sélectionné"))
def a_le_focus_et_selectionne(interface: Contexte, texte: str) -> None:
	assert fenetre(interface).focusWidget() is ecran(interface).champ
	assert ecran(interface).champ.selectedText() == texte


@then(parsers.parse("le champ de recherche contient « {texte} »"))
def contient(interface: Contexte, texte: str) -> None:
	assert ecran(interface).champ.text() == texte


@then(parsers.re(r"les suggestions sont (?P<textes>aucune|«.+)"))
def suggestions(interface: Contexte, textes: str) -> None:
	assert ecran(interface).suggestions() == NOM.findall(textes)


@then("les résultats sont :")
def resultats(interface: Contexte, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	modele = ecran(interface).modele
	titres = [str(modele.headerData(colonne, Qt.Orientation.Horizontal)) for colonne in range(modele.columnCount())]
	assert titres == [entete.strip() for entete in entetes]
	assert lignes(interface) == [[valeur.strip() for valeur in valeurs] for valeurs in rangees]


@then(parsers.parse("le compte des résultats est « {texte} »"))
def compte(interface: Contexte, texte: str) -> None:
	assert ecran(interface).compte.text() == texte


@then(parsers.parse("la table montre {nombre:d} résultats"))
def nombre_de_lignes(interface: Contexte, nombre: int) -> None:
	assert len(lignes(interface)) == nombre
