"""Suggestions au lancement de l'interface (https://github.com/dascritch/machincast/issues/119).

La fenêtre des suggestions est remplacée par les réponses du scénario (tests/etapes_interface.py) ; la vraie fenêtre
s'ouvre ici, hors de l'écran du poste.
"""

import re
from collections.abc import Iterator
from datetime import timedelta

import pytest
import tomlkit
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QDialogButtonBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import Audio
from machincast.interface.cartes_son import CartesSon
from machincast.interface.suggestions import BANQUES, FIL_MUSICAL, FenetreSuggestions, Manques, Reponse, libelle
from machincast.service import ABSENT, EtatDuService
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
		base_vide.execute("INSERT INTO banks (internal_name, mode) VALUES (%s, 'random')", (nom,))


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
		r"(?:, avec la sortie « (?P<sortie>[^»]+) », l'antenne « (?P<antenne>[^»]+) »"
		r" et la pré-écoute « (?P<preecoute>[^»]+) »)?$"
	)
)
def creer(
	interface: Contexte, sans: str | None, sortie: str | None, antenne: str | None, preecoute: str | None
) -> None:
	def repondre(manques: Manques) -> Reponse:
		banques = tuple(banque for banque in manques.banques if libelle(banque) != sans)
		return Reponse(
			creer=True,
			fil_musical=(manques.fil_musical) and (sans != FIL_MUSICAL),
			banques=banques,
			sortie=sortie,  # type: ignore[arg-type]
			antenne=antenne,
			preecoute=preecoute,
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


@then("les suggestions n'ont pas proposé les cartes son")
def sans_cartes(interface: Contexte) -> None:
	assert premieres(interface).audio is None


@then(
	parsers.re(
		r"les suggestions ont proposé les cartes son de la sortie « (?P<sortie>[^»]+) », l'antenne non renseignée"
		r" et la pré-écoute « (?P<preecoute>[^»]+) »"
	)
)
def cartes_proposees(interface: Contexte, sortie: str, preecoute: str) -> None:
	assert premieres(interface).audio == Audio(sortie, None, preecoute)  # type: ignore[arg-type]


@then("aucune suggestion n'a été faite")
def aucune(interface: Contexte) -> None:
	assert interface.suggestions_faites == []


@then(parsers.parse("les suggestions ont été faites {nombre:d} fois"))
def nombre_de_fois(interface: Contexte, nombre: int) -> None:
	assert len(interface.suggestions_faites) == nombre


@then(parsers.re(r"il n'y a aucun(?:e)? (?P<genre>événement|banque) en base"))
def rien_en_base(base_vide: Connexion, genre: str) -> None:
	table = {"événement": "events", "banque": "banks"}[genre]
	ligne = base_vide.execute(f"SELECT count(*) FROM {table}").fetchone()  # noqa: S608
	assert ligne == (0,), ligne


@then(parsers.parse("le fil musical « {nom} » est en base, permanent"))
def fil_permanent(base_vide: Connexion, nom: str) -> None:
	lignes = base_vide.execute(
		"SELECT priority::text, starts_at, ends_at, recurrence_days::text[] FROM events WHERE internal_name = %s",
		(nom,),
	).fetchall()
	assert lignes == [("background_programming", None, None, [])], lignes


@then(parsers.re(r"la liste de l'événement « (?P<nom>[^»]+) » est en base (?P<banques>«.+)"))
def liste_du_fil(base_vide: Connexion, nom: str, banques: str) -> None:
	lignes = base_vide.execute(
		"SELECT b.internal_name FROM event_items x JOIN events e ON e.id = x.event_id"
		" JOIN banks b ON b.id = x.bank_id WHERE e.internal_name = %s ORDER BY x.position",
		(nom,),
	).fetchall()
	assert [str(banque) for (banque,) in lignes] == NOM.findall(banques)


@then(parsers.re(r"les fils musicaux en base sont (?P<noms>«.+)"))
def fils(base_vide: Connexion, noms: str) -> None:
	lignes = base_vide.execute(
		"SELECT internal_name FROM events WHERE priority = 'background_programming' AND deleted_at IS NULL"
		" ORDER BY internal_name"
	).fetchall()
	assert [str(nom) for (nom,) in lignes] == NOM.findall(noms)


def _crossfade(regle: str, duree: timedelta) -> str:
	if regle == "sound":
		return "des sonores"
	return f"{REGLES[regle]}, {duree.total_seconds():g} s"


REGLES = {"default": "à défaut", "forced": "imposé"}


@then("les banques en base sont :")
def banques_en_base(base_vide: Connexion, datatable: list[list[str]]) -> None:
	_entete, *lignes = datatable
	lues = []
	for nom, mode, repeter, maximum, debut_regle, debut, fin_regle, fin in base_vide.execute(
		"SELECT internal_name, mode::text, no_repeat, max_duration, crossfade_start_rule::text, crossfade_start,"
		' crossfade_end_rule::text, crossfade_end FROM banks ORDER BY internal_name COLLATE "C"'
	).fetchall():
		repetition = "non"
		if repeter:
			repetition = "oui"
		lues.append(
			(
				str(nom),
				str(mode),
				repetition,
				str((maximum) or ("")),
				_crossfade(str(debut_regle), debut),
				_crossfade(str(fin_regle), fin),
			)
		)
	attendues = [tuple(valeur.strip() for valeur in ligne) for ligne in lignes]
	assert lues == attendues, lues


@then(parsers.parse("la banque « {nom} » en base a pour durée maximale « {maximum} », sans durée minimale"))
def duree_maximale(base_vide: Connexion, nom: str, maximum: str) -> None:
	ligne = base_vide.execute(
		"SELECT min_duration, max_duration FROM banks WHERE internal_name = %s", (nom,)
	).fetchone()
	assert ligne is not None
	assert (ligne[0], str(ligne[1])) == (None, maximum)


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


SERVICES = {
	"sans service de diffusion": ABSENT,
	"service de diffusion à l'arrêt": EtatDuService(installe=True, actif="inactive"),
}


@when(
	parsers.re(
		r"la fenêtre des suggestions s'ouvre sur (?:le fil musical et la banque « (?P<banque>[^»]+) », avec les"
		r"|(?P<seules>les seules)) cartes son de la sortie « (?P<sortie>[^»]+) », (?P<service>.+)"
	)
)
def ouvrir(
	ouverte: dict[str, object], parent: QWidget, banque: str | None, seules: str | None, sortie: str, service: str
) -> None:
	"""La pré-écoute de la configuration des tests ; l'antenne à renseigner."""
	audio = Audio(sortie, None, "preecoute-factice")  # type: ignore[arg-type]
	manques = Manques(False, (), audio)
	if seules is None:
		assert banque is not None
		manques = Manques(True, (banque,), audio)
	ouverte["fenetre"] = FenetreSuggestions(manques, parent, SERVICES[service])


@then(parsers.parse("elle s'intitule « {titre} »"))
def titre(ouverte: dict[str, object], titre: str) -> None:
	assert la_fenetre(ouverte).windowTitle() == titre


@then(parsers.re(r"elle propose, cochés, (?P<elements>«.+)"))
def coches(ouverte: dict[str, object], elements: str) -> None:
	liste = la_fenetre(ouverte).ui.elements
	lignes = [liste.item(rang) for rang in range(liste.count())]
	assert [ligne.text() for ligne in lignes] == re.findall(r"« ((?:[^«»]|« [^»]+ »)+) »", elements)
	assert all(ligne.checkState() == Qt.CheckState.Checked for ligne in lignes)


@then("elle montre les cartes son en tête, avant ce qui est à créer")
def cartes_en_tete(ouverte: dict[str, object]) -> None:
	fenetre = la_fenetre(ouverte)
	disposition = fenetre.layout()
	assert disposition is not None
	assert disposition.indexOf(fenetre.ui.groupe_cartes_son) == 0
	assert disposition.indexOf(fenetre.ui.groupe_cartes_son) < disposition.indexOf(fenetre.ui.elements)
	assert fenetre.ui.groupe_cartes_son.isVisibleTo(fenetre)


@then("elle ne propose rien à créer")
def rien_a_creer(ouverte: dict[str, object]) -> None:
	fenetre = la_fenetre(ouverte)
	assert not fenetre.ui.elements.isVisibleTo(fenetre)
	assert not fenetre.ui.explication.isVisibleTo(fenetre)


def _cartes(ouverte: dict[str, object]) -> CartesSon:
	cartes = la_fenetre(ouverte).cartes
	assert cartes is not None
	return cartes


@then(parsers.re(r"son choix de l'antenne propose (?P<noms>«.+)"))
def choix_antenne(ouverte: dict[str, object], noms: str) -> None:
	choix = _cartes(ouverte).ui.antenne
	assert [choix.itemText(rang) for rang in range(choix.count())] == NOM.findall(noms)


@then(parsers.parse("dans son choix de l'antenne, « {texte} » est inactive"))
def ligne_inactive(ouverte: dict[str, object], texte: str) -> None:
	choix = _cartes(ouverte).ui.antenne
	modele = choix.model()
	assert isinstance(modele, QStandardItemModel)
	assert not modele.item(choix.findText(texte)).isEnabled()


@then(parsers.re(r"son bouton « (?P<texte>Créer|Enregistrer) » est (?P<etat>actif|inactif)"))
def bouton_ok(ouverte: dict[str, object], texte: str, etat: str) -> None:
	bouton = la_fenetre(ouverte).ui.boutons.button(QDialogButtonBox.StandardButton.Ok)
	assert (bouton.text(), bouton.isEnabled()) == (texte, etat == "actif")


@when(parsers.parse("j'y décoche « {texte} »"))
def decocher(ouverte: dict[str, object], texte: str) -> None:
	liste = la_fenetre(ouverte).ui.elements
	(ligne,) = [liste.item(rang) for rang in range(liste.count()) if liste.item(rang).text() == texte]
	ligne.setCheckState(Qt.CheckState.Unchecked)


@when(parsers.re(r"j'y choisis pour (?P<role>l'antenne|la pré-écoute) « (?P<nom>[^»]+) »"))
def choisir_carte(ouverte: dict[str, object], role: str, nom: str) -> None:
	ui = _cartes(ouverte).ui
	choix = {"l'antenne": ui.antenne, "la pré-écoute": ui.preecoute}[role]
	indice = choix.findText(nom)
	assert indice >= 0, nom
	choix.setCurrentIndex(indice)


@when("j'y coche « Ne plus proposer au lancement »")
def cocher_ne_plus(ouverte: dict[str, object]) -> None:
	la_fenetre(ouverte).ui.ne_plus_proposer.setChecked(True)


@when(parsers.re(r"j'y clique sur « (?:Créer|Enregistrer) »"))
def cliquer_creer(ouverte: dict[str, object]) -> None:
	fenetre = la_fenetre(ouverte)
	fenetre.ui.boutons.button(QDialogButtonBox.StandardButton.Ok).click()
	ouverte["reponse"] = fenetre.reponse()


@then(
	parsers.re(
		r"elle a donné : (?:la banque « (?P<banque>[^»]+) », )?la sortie « (?P<sortie>[^»]+) »,"
		r" l'antenne « (?P<antenne>[^»]+) », la pré-écoute « (?P<preecoute>[^»]+) »(?P<ne_plus>, ne plus proposer)?"
	)
)
def donne(
	ouverte: dict[str, object],
	banque: str | None,
	sortie: str,
	antenne: str,
	preecoute: str,
	ne_plus: str | None,
) -> None:
	assert la_fenetre(ouverte).result() == FenetreSuggestions.DialogCode.Accepted
	banques: tuple[str, ...] = ()
	if banque is not None:
		banques = (banque,)
	assert ouverte["reponse"] == Reponse(
		creer=True,
		fil_musical=False,
		banques=banques,
		sortie=sortie,  # type: ignore[arg-type]
		antenne=antenne,
		preecoute=preecoute,
		ne_plus_proposer=ne_plus is not None,
	)


@then(parsers.re(r"la barre d'état (?P<signale>signale|ne signale pas) « Périphérique de l'antenne à renseigner »"))
def antenne_signalee(interface: Contexte, signale: str) -> None:
	ouverte = fenetre(interface)
	assert ouverte.antenne_a_renseigner.isVisibleTo(ouverte) == (signale == "signale")
