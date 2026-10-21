"""Scénarios de la duplication d'un événement, d'une séquence ou d'une banque
(https://github.com/dascritch/machincast/issues/130).

Les étapes de la fenêtre, des fiches et des éléments en base sont dans tests/etapes_interface.py.
"""

from datetime import datetime

import psycopg
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import QTreeWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.fiche import Fiche
from machincast.interface.fiche_banque import FicheBanque
from machincast.interface.fiche_evenement import FicheEvenement
from machincast.interface.listes import Liste
from tests.etapes_interface import ELEMENT, NOM, Contexte, fenetre, identifiant

scenarios("dupliquer.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
TABLES = {"séquence": "sequences", "événement": "evenements", "banque": "banques"}
ELEMENTS = {
	"séquence": ("sequences_elements", "sequence_id"),
	"événement": ("evenements_elements", "evenement_id"),
}
"""La liste d'éléments de chaque genre : sa table et sa colonne du parent."""


def fiche_ouverte(interface: Contexte) -> Fiche:
	ouverte = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(ouverte, Fiche), ouverte
	return ouverte


def liste_d_elements(interface: Contexte) -> QTreeWidget:
	liste = fiche_ouverte(interface).findChild(QTreeWidget, "elements")
	assert liste is not None
	return liste


def lignes(liste: QTreeWidget) -> list[str]:
	"""Le nom de l'élément de chaque ligne, deuxième colonne."""
	return [item.text(1) for rangee in range(liste.topLevelItemCount()) if (item := liste.topLevelItem(rangee))]


def instant(texte: str) -> datetime:
	return datetime.fromisoformat(texte).astimezone()


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'événement « {nom} » masque les métadonnées"))
def masque(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("UPDATE evenements SET masquer_metadonnees = true WHERE nom_interne = %s", (nom,))


@given(parsers.parse("la séquence au nom interne de {longueur:d} caractères « {lettre} »"))
def sequence_au_long_nom(base_vide: Connexion, longueur: int, lettre: str) -> None:
	base_vide.execute("INSERT INTO sequences (nom_interne) VALUES (%s)", (lettre * longueur,))


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je retire les éléments (?P<noms>.+)"))
def retirer(interface: Contexte, qtbot: QtBot, noms: str) -> None:
	liste = liste_d_elements(interface)
	retirer_element = fiche_ouverte(interface).ui.retirer_element  # type: ignore[attr-defined]
	for nom in NOM.findall(noms):
		(rangee,) = [rangee for rangee, texte in enumerate(lignes(liste)) if texte == nom]
		liste.setCurrentItem(liste.topLevelItem(rangee))
		qtbot.mouseClick(retirer_element, Qt.MouseButton.LeftButton)


@when(parsers.parse("je donne à l'événement copié le début « {texte} »"))
def donner_le_debut(interface: Contexte, texte: str) -> None:
	ouverte = fiche_ouverte(interface)
	assert isinstance(ouverte, FicheEvenement)
	ouverte.ui.a_debut.setChecked(True)
	ouverte.ui.debut.setDateTime(QDateTime.fromSecsSinceEpoch(int(instant(texte).timestamp())))


@when(parsers.parse("je choisis « Dupliquer » au clic droit sur la ligne de {longueur:d} caractères « {lettre} »"))
def dupliquer_le_long_nom(interface: Contexte, longueur: int, lettre: str) -> None:
	dupliquer_au_clic_droit(interface, lettre * longueur)


@when(parsers.parse("je choisis « Dupliquer » au clic droit sur la ligne « {nom} »"))
def dupliquer_au_clic_droit(interface: Contexte, nom: str) -> None:
	liste = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(liste, Liste)
	trouvees = liste.proxy.match(
		liste.proxy.index(0, 0), Qt.ItemDataRole.DisplayRole, nom, -1, Qt.MatchFlag.MatchExactly
	)
	assert len(trouvees) == 1, nom
	menu = liste.menu_de_la_ligne(trouvees[0])
	assert menu is not None
	(action,) = [action for action in menu.actions() if action.text() == "Dupliquer"]
	action.trigger()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"le bouton « Dupliquer » de la fiche est (?P<etat>actif|inactif)"))
def bouton_dupliquer(interface: Contexte, etat: str) -> None:
	bouton = fiche_ouverte(interface).bouton_dupliquer
	assert bouton is not None
	assert bouton.isEnabled() == (etat == "actif")


@then(parsers.parse("la fiche montre le nom interne « {nom} » et le nom public « {nom_public} »"))
def noms_montres(interface: Contexte, nom: str, nom_public: str) -> None:
	ui = fiche_ouverte(interface).ui  # type: ignore[attr-defined]
	assert (ui.nom_interne.text(), ui.nom_public.text()) == (nom, nom_public)


@then(parsers.re(r"la fiche montre les éléments (?P<noms>«.+)"))
def elements_montres(interface: Contexte, noms: str) -> None:
	assert lignes(liste_d_elements(interface)) == NOM.findall(noms)


@then(
	parsers.parse(
		"la fiche de l'événement copié montre la priorité « {priorite} », le masquage « {masquage} », ni début,"
		" ni fin, ni jours"
	)
)
def evenement_copie(interface: Contexte, priorite: str, masquage: str) -> None:
	ouverte = fiche_ouverte(interface)
	assert isinstance(ouverte, FicheEvenement)
	ui = ouverte.ui
	assert (ui.priorite.currentText(), ui.masquage.currentText()) == (priorite, masquage)
	assert not ui.a_debut.isChecked()
	assert not ui.a_fin.isChecked()
	assert not any(jour.isChecked() for jour in ouverte.jours)


@then(
	parsers.re(
		r"la fiche de la banque copiée montre le mode « (?P<mode>[^»]+) », « ne pas répéter » coché,"
		r" les répertoires (?P<repertoires>.+), et aucun sonore"
	)
)
def banque_copiee(interface: Contexte, mode: str, repertoires: str) -> None:
	ouverte = fiche_ouverte(interface)
	assert isinstance(ouverte, FicheBanque)
	ui = ouverte.ui
	assert (ui.mode.currentText(), ui.ne_pas_repeter.isChecked()) == (mode, True)
	montres = [ui.repertoires.item(rangee).text() for rangee in range(ui.repertoires.count())]
	assert montres == [interface.chemin(repertoire) for repertoire in NOM.findall(repertoires)]
	assert ui.sonores.topLevelItemCount() == 0


@then(parsers.re(r"(?:la |l')(?P<genre>séquence|événement|banque) « (?P<nom>[^»]+) » n'est pas en base"))
def absent(base_vide: Connexion, genre: str, nom: str) -> None:
	table = TABLES[genre]
	assert base_vide.execute(f"SELECT 1 FROM {table} WHERE nom_interne = %s", (nom,)).fetchone() is None  # noqa: S608


def elements_en_base(base: Connexion, genre: str, nom: str) -> list[tuple[str, str]]:
	"""Chaque élément de la liste, dans l'ordre : « le sonore » et son titre, « la banque » ou « la séquence » et son
	nom. Dans une séquence, sequence_id désigne la séquence elle-même : ses éléments n'en sont jamais une."""
	table, parent = ELEMENTS[genre]
	numero = identifiant(base, TABLES[genre], "nom_interne", nom)
	sequence_citee = "e.sequence_id"
	if genre == "séquence":
		sequence_citee = "NULL"
	rangees = base.execute(
		"SELECT CASE WHEN e.sonore_id IS NOT NULL THEN 'le sonore' WHEN e.banque_id IS NOT NULL THEN 'la banque'"
		" ELSE 'la séquence' END, COALESCE(s.titre, b.nom_interne, q.nom_interne)"
		f" FROM {table} e LEFT JOIN sonores s ON s.id = e.sonore_id"  # noqa: S608
		" LEFT JOIN banques b ON b.id = e.banque_id"
		f" LEFT JOIN sequences q ON q.id = {sequence_citee}"
		f" WHERE e.{parent} = %s ORDER BY e.position",
		(numero,),
	).fetchall()
	return [(str(quoi), str(qui)) for quoi, qui in rangees]


@then(
	parsers.re(
		r"la séquence « (?P<nom>[^»]+) » a en base le nom public « (?P<nom_public>[^»]+) » et les éléments"
		r" (?P<elements>.+)"
	)
)
def sequence_en_base(base_vide: Connexion, nom: str, nom_public: str, elements: str) -> None:
	ligne = base_vide.execute("SELECT nom_public FROM sequences WHERE nom_interne = %s", (nom,)).fetchone()
	assert ligne == (nom_public,)
	assert elements_en_base(base_vide, "séquence", nom) == ELEMENT.findall(elements)


@then(parsers.re(r"l'événement « (?P<nom>[^»]+) » a en base les éléments (?P<elements>.+)"))
def elements_de_l_evenement(base_vide: Connexion, nom: str, elements: str) -> None:
	assert elements_en_base(base_vide, "événement", nom) == ELEMENT.findall(elements)


@then(
	parsers.re(
		r"l'événement « (?P<nom>[^»]+) » a en base la priorité « (?P<priorite>[^»]+) »,"
		r" le nom public « (?P<nom_public>[^»]+) », masqué, le début « (?P<debut>[^»]+) »,"
		r" (?:sans fin ni jours|la fin « (?P<fin>[^»]+) », les jours « (?P<jours>[^»]+) »)"
	)
)
def evenement_en_base(
	base_vide: Connexion, nom: str, priorite: str, nom_public: str, debut: str, fin: str | None, jours: str | None
) -> None:
	ligne = base_vide.execute(
		"SELECT priorite::text, nom_public, masquer_metadonnees, debut, fin, jours_recurrence::text[]"
		" FROM evenements WHERE nom_interne = %s",
		(nom,),
	).fetchone()
	fin_attendue = None
	if fin is not None:
		fin_attendue = instant(fin)
	jours_attendus: list[str] = []
	if jours is not None:
		jours_attendus = jours.split(", ")
	assert ligne == (priorite, nom_public, True, instant(debut), fin_attendue, jours_attendus)


@then(
	parsers.re(
		r"la banque « (?P<nom>[^»]+) » a en base le nom public « (?P<nom_public>[^»]+) »,"
		r" le mode « (?P<mode>[^»]+) », « ne pas répéter », les répertoires (?P<repertoires>.+)"
		r" et les sonores (?P<sonores>aucun|«.+)"
	)
)
def banque_en_base(
	interface: Contexte, base_vide: Connexion, nom: str, nom_public: str, mode: str, repertoires: str, sonores: str
) -> None:
	ligne = base_vide.execute(
		"SELECT id, nom_public, mode::text, ne_pas_repeter FROM banques WHERE nom_interne = %s", (nom,)
	).fetchone()
	assert ligne is not None
	numero, *reglages = ligne
	assert reglages == [nom_public, mode, True]
	lus = base_vide.execute(
		'SELECT repertoire FROM banques_repertoires WHERE banque_id = %s ORDER BY repertoire COLLATE "C"', (numero,)
	).fetchall()
	assert [str(repertoire) for (repertoire,) in lus] == [interface.chemin(r) for r in NOM.findall(repertoires)]
	titres = base_vide.execute(
		"SELECT s.titre FROM banques_sonores bs JOIN sonores s ON s.id = bs.sonore_id"
		" WHERE bs.banque_id = %s ORDER BY bs.position",
		(numero,),
	).fetchall()
	assert [str(titre) for (titre,) in titres] == NOM.findall(sonores)


@then(parsers.re(r"les listes qui proposent de dupliquer au clic droit sont (?P<onglets>.+)"))
def listes_qui_dupliquent(interface: Contexte, onglets: str) -> None:
	"""Le menu de la première ligne de chaque liste ; toutes en ont une."""
	ui = fenetre(interface).ui
	trouvees = []
	for rangee in range(ui.onglets.count()):
		liste = ui.onglets.widget(rangee)
		if not isinstance(liste, Liste):
			continue
		liste.actualiser()
		assert liste.proxy.rowCount() > 0, ui.onglets.tabText(rangee)
		menu = liste.menu_de_la_ligne(liste.proxy.index(0, 0))
		if (menu is not None) and (any(action.text() == "Dupliquer" for action in menu.actions())):
			trouvees.append(ui.onglets.tabText(rangee))
	assert trouvees == NOM.findall(onglets)


@then("la fiche ne montre aucun événement où figure la séquence")
def sans_evenement(interface: Contexte) -> None:
	assert fiche_ouverte(interface).ui.evenements.count() == 0  # type: ignore[attr-defined]


@then(parsers.parse("le nom interne de la copie est de {longueur:d} caractères « {lettre} », suivis de « {suffixe} »"))
def nom_raccourci(interface: Contexte, longueur: int, lettre: str, suffixe: str) -> None:
	nom = fiche_ouverte(interface).ui.nom_interne.text()  # type: ignore[attr-defined]
	assert nom == f"{lettre * longueur} {suffixe}"
	assert len(nom) == 255
