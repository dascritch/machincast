"""Étapes des listes filtrables de l'interface (https://github.com/dascritch/machincast/issues/26).

La fenêtre s'affiche hors de l'écran du poste (QT_QPA_PLATFORM=offscreen, réglé par tests/conftest.py). Les listes se
lisent dans la base de test, avec le rôle de l'interface.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from PySide6.QtCore import QModelIndex, QPoint, Qt
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.base import Role, connecter
from machincast.horloge import HorlogeFixe
from machincast.interface.fenetre import FenetrePrincipale
from machincast.interface.listes import Liste
from tests.base_test import parametres_base_test

scenarios("listes.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
NOM = re.compile(r"« ([^»]+) »")
MODES = {"séquentielle": "sequentiel", "aléatoire": "aleatoire"}


@dataclass
class Contexte:
	repertoire: Path
	horloge: HorlogeFixe | None = None
	fenetre: FenetrePrincipale | None = None
	connexion: Connexion | None = None
	demandes: list[tuple[str, int]] = field(default_factory=list)
	"""Écrans de détail demandés : genre et identifiant."""


@pytest.fixture
def contexte(tmp_path: Path) -> Iterator[Contexte]:
	contexte = Contexte(tmp_path)
	yield contexte
	if contexte.fenetre is not None:
		contexte.fenetre.close()
	if contexte.connexion is not None:
		contexte.connexion.close()


def fenetre(contexte: Contexte) -> FenetrePrincipale:
	assert contexte.fenetre is not None
	return contexte.fenetre


def liste(contexte: Contexte) -> Liste:
	ouverte = fenetre(contexte).ui.onglets.currentWidget()
	assert isinstance(ouverte, Liste), ouverte
	return ouverte


def lignes(contexte: Contexte) -> list[dict[str, str]]:
	"""Les lignes affichées, après filtre et tri, par titre de colonne."""
	modele = liste(contexte).table.model()
	titres = [
		str(modele.headerData(colonne, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole))
		for colonne in range(modele.columnCount())
	]
	return [
		{titre: str(modele.index(rangee, colonne).data() or "") for colonne, titre in enumerate(titres)}
		for rangee in range(modele.rowCount())
	]


def identifiant(base: Connexion, table: str, colonne: str, valeur: str) -> int:
	ligne = base.execute(f"SELECT id FROM {table} WHERE {colonne} = %s", (valeur,)).fetchone()  # noqa: S608
	assert ligne is not None, f"{valeur} absent de {table}"
	return int(str(ligne[0]))


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'horloge de l'interface au « {instant} »"))
def horloge(contexte: Contexte, instant: str) -> None:
	contexte.horloge = HorlogeFixe(datetime.fromisoformat(instant).astimezone())


@given("les sonores :")
def sonores(base_vide: Connexion, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	for valeurs in rangees:
		ligne = dict(zip(entetes, (v.strip() for v in valeurs), strict=True))
		stream = ligne["type"] == "stream"
		base_vide.execute(
			"INSERT INTO sonores (type, emplacement, url_stream, artiste, titre, etat, duree)"
			" VALUES (%s, %s, %s, %s, %s, %s, %s)",
			(
				ligne["type"],
				None if stream else ligne["emplacement"],
				ligne["emplacement"] if stream else None,
				ligne["artiste"] or None,
				ligne["titre"],
				ligne["etat"],
				timedelta(seconds=int(ligne["duree"])) if ligne["duree"] else None,
			),
		)


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
def repertoires(base_vide: Connexion, liste: str, nom: str) -> None:
	banque = identifiant(base_vide, "banques", "nom_interne", nom)
	for repertoire in NOM.findall(liste):
		base_vide.execute(
			"INSERT INTO banques_repertoires (banque_id, repertoire) VALUES (%s, %s)", (banque, repertoire)
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
def ouvrir(contexte: Contexte, base_vide: Connexion, qtbot: QtBot) -> None:
	assert contexte.horloge is not None
	contexte.connexion = connecter(*parametres_base_test(), Role.INTERFACE)
	contexte.fenetre = FenetrePrincipale(contexte.connexion, contexte.repertoire / "lecture.sock", contexte.horloge)
	contexte.fenetre.detail_demande.connect(lambda genre, numero: contexte.demandes.append((genre, numero)))
	qtbot.addWidget(contexte.fenetre)
	contexte.fenetre.show()
	qtbot.waitExposed(contexte.fenetre)


@when(parsers.parse("j'ouvre l'onglet « {titre} »"))
def ouvrir_onglet(contexte: Contexte, titre: str) -> None:
	onglets = fenetre(contexte).ui.onglets
	titres = [onglets.tabText(indice) for indice in range(onglets.count())]
	assert titre in titres, titres
	onglets.setCurrentIndex(titres.index(titre))


@when(parsers.parse("le sonore « {titre} » est ajouté en base"))
def ajouter(base_vide: Connexion, titre: str) -> None:
	base_vide.execute(
		"INSERT INTO sonores (type, emplacement, titre) VALUES ('fichier', %s, %s)", (f"/srv/{titre}.flac", titre)
	)


@when(parsers.parse("je tape « {texte} » dans le filtre de la liste"))
def filtrer(contexte: Contexte, qtbot: QtBot, texte: str) -> None:
	champ = liste(contexte).filtre
	champ.clear()
	for lettre in texte:
		# QTest ne sait taper que l'ASCII : une lettre accentuée s'insère comme le ferait une méthode de saisie.
		if lettre.isascii():
			qtbot.keyClicks(champ, lettre)
		else:
			champ.insert(lettre)


@when(parsers.parse("je clique sur le titre de la colonne « {titre} »"))
def trier(contexte: Contexte, qtbot: QtBot, titre: str) -> None:
	table = liste(contexte).table
	entete = table.horizontalHeader()
	modele = table.model()
	titres = [str(modele.headerData(colonne, Qt.Orientation.Horizontal)) for colonne in range(modele.columnCount())]
	colonne = titres.index(titre)
	position = QPoint(entete.sectionViewportPosition(colonne) + entete.sectionSize(colonne) // 2, entete.height() // 2)
	qtbot.mouseClick(entete.viewport(), Qt.MouseButton.LeftButton, pos=position)


@when(parsers.parse("j'ouvre la ligne « {nom} »"))
def ouvrir_ligne(contexte: Contexte, qtbot: QtBot, nom: str) -> None:
	table = liste(contexte).table
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


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"la fenêtre a les onglets (?P<titres>.+)"))
def onglets(contexte: Contexte, titres: str) -> None:
	onglets = fenetre(contexte).ui.onglets
	assert [onglets.tabText(indice) for indice in range(onglets.count())] == NOM.findall(titres)


@then(parsers.parse("l'onglet ouvert est « {titre} »"))
def onglet_ouvert(contexte: Contexte, titre: str) -> None:
	onglets = fenetre(contexte).ui.onglets
	assert onglets.tabText(onglets.currentIndex()) == titre


@then("l'onglet « Accueil » montre l'écran par défaut")
def accueil(contexte: Contexte) -> None:
	assert fenetre(contexte).ui.onglets.widget(0) is fenetre(contexte).accueil


@then("la liste montre :")
def liste_attendue(contexte: Contexte, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	attendues = [dict(zip(entetes, (v.strip() for v in valeurs), strict=True)) for valeurs in rangees]
	assert lignes(contexte) == attendues, lignes(contexte)


@then(parsers.re(r"la liste montre les titres (?P<titres>.+)"))
def titres_affiches(contexte: Contexte, titres: str) -> None:
	assert [ligne["Titre"] for ligne in lignes(contexte)] == NOM.findall(titres), lignes(contexte)


@then(parsers.parse("le compte de la liste est « {texte} »"))
def compte(contexte: Contexte, texte: str) -> None:
	assert liste(contexte).compte.text() == texte


@then(parsers.parse("l'écran de détail de {genre} « {nom} » est demandé"))
def detail(contexte: Contexte, base_vide: Connexion, genre: str, nom: str) -> None:
	tables = {
		"sonore": ("sonores", "titre"),
		"banque": ("banques", "nom_interne"),
		"séquence": ("sequences", "nom_interne"),
		"événement": ("evenements", "nom_interne"),
	}
	table, colonne = tables[genre]
	assert contexte.demandes == [(genre, identifiant(base_vide, table, colonne, nom))], contexte.demandes


@then(parsers.parse("la barre d'état annonce « {texte} »"))
def barre_d_etat(contexte: Contexte, texte: str) -> None:
	assert fenetre(contexte).statusBar().currentMessage() == texte
