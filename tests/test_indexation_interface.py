"""Scénarios du lancement de l'indexation depuis l'interface (https://github.com/dascritch/machincast/issues/38).

Les étapes de la fenêtre, des listes et des fenêtres de dialogue sont dans tests/etapes_interface.py. L'indexation
décode vraiment les fichiers de test ; ses scénarios peuvent la faire attendre, ou lui retirer ses décodeurs, en
remplaçant le décodage de l'indexeur.
"""

import logging
import threading
from pathlib import Path

import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.indexation.decodage import DecodeurIndisponible, Verification, verifier_fichier
from machincast.indexation.verification import LIBELLES
from machincast.interface import indexation
from tests.etapes_interface import ATTENTE, NOM, Connexion, Contexte, fenetre

scenarios("indexation_interface.feature")


@pytest.fixture
def reprise() -> threading.Event:
	"""Ce qu'attend une indexation qui attend."""
	return threading.Event()


@pytest.fixture
def en_attente() -> threading.Event:
	"""Une indexation qui attend en est à son premier décodage."""
	return threading.Event()


def actions(interface: Contexte, menu: str) -> list[QAction]:
	"""Les actions du menu de la barre de menus, dans l'ordre."""
	barre = fenetre(interface).menuBar()
	trouves = [
		sous_menu
		for sous_menu in barre.findChildren(QMenu)
		if (sous_menu.title().replace("&", "") == menu) and (sous_menu.menuAction() in barre.actions())
	]
	assert len(trouves) == 1, f"menu « {menu} » absent"
	return list(trouves[0].actions())


def attendre_l_indexation(interface: Contexte, qtbot: QtBot) -> None:
	lanceur = fenetre(interface).indexation
	qtbot.waitUntil(lambda: not lanceur.en_cours(), timeout=ATTENTE)


def dernier_rapport(interface: Contexte) -> tuple[str, str, list[str]]:
	assert interface.rapports != [], "aucun rapport montré"
	return interface.rapports[-1]


# ─── Étant donné ───────────────────────────────────────────


@given("une indexation qui attend")
def indexation_qui_attend(
	monkeypatch: pytest.MonkeyPatch, reprise: threading.Event, en_attente: threading.Event
) -> None:
	def decoder(chemin: Path) -> Verification:
		en_attente.set()
		assert reprise.wait(ATTENTE / 1000), "l'indexation attendue n'a jamais repris"
		return verifier_fichier(chemin)

	monkeypatch.setattr(indexation, "verifier_fichier", decoder)


@given("un indexeur qui ne sait pas décoder les fichiers")
def sans_decodeur(monkeypatch: pytest.MonkeyPatch) -> None:
	def decoder(_chemin: Path) -> Verification:
		raise DecodeurIndisponible("aucun décodeur pour ce format")

	monkeypatch.setattr(indexation, "verifier_fichier", decoder)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("je lance « {titre} » depuis le menu « {menu} »"))
def lancer(interface: Contexte, titre: str, menu: str) -> None:
	choisies = [action for action in actions(interface, menu) if action.text() == titre]
	assert len(choisies) == 1, f"« {titre} » absent du menu « {menu} »"
	choisies[0].trigger()


@when("l'indexation se termine")
def terminer(interface: Contexte, qtbot: QtBot) -> None:
	attendre_l_indexation(interface, qtbot)


@when("l'indexation en est à son premier décodage")
def premier_decodage(en_attente: threading.Event) -> None:
	"""Elle a déjà choisi les sonores qu'elle décode."""
	assert en_attente.wait(ATTENTE / 1000), "l'indexation n'a jamais commencé à décoder"


@when("l'indexation attendue reprend, et se termine")
def reprendre(interface: Contexte, qtbot: QtBot, reprise: threading.Event) -> None:
	reprise.set()
	attendre_l_indexation(interface, qtbot)


@when("je ferme la fenêtre de l'interface, pendant que l'indexation attendue reprend")
def fermer_pendant(interface: Contexte, reprise: threading.Event) -> None:
	assert fenetre(interface).indexation.en_cours()
	threading.Timer(0.3, reprise.set).start()
	fenetre(interface).close()
	assert not fenetre(interface).indexation.en_cours()


@when("la fenêtre fermée a tout traité")
def apres_fermeture(qtbot: QtBot) -> None:
	qtbot.wait(300)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"le menu « (?P<menu>[^»]+) » propose (?P<titres>«.+)"))
def menu_propose(interface: Contexte, menu: str, titres: str) -> None:
	assert [action.text() for action in actions(interface, menu) if action.isEnabled()] == NOM.findall(titres)
	assert [action.text() for action in actions(interface, menu)] == NOM.findall(titres)


@then(parsers.parse("le menu « {menu} » ne propose plus rien"))
def menu_inactif(interface: Contexte, menu: str) -> None:
	assert [action.text() for action in actions(interface, menu) if action.isEnabled()] == []


@then(parsers.parse("le rapport « {titre} » a dit « {texte} »"))
def rapport(interface: Contexte, titre: str, texte: str) -> None:
	assert dernier_rapport(interface)[:2] == (titre, texte)


@then("aucun rapport n'a été montré")
def sans_rapport(interface: Contexte) -> None:
	assert interface.rapports == []


@then("le journal de l'indexeur n'est plus écouté")
def journal_libre() -> None:
	assert logging.getLogger("machincast.indexation").handlers == []


@then("le rapport n'a signalé aucune anomalie")
def sans_anomalie(interface: Contexte) -> None:
	assert dernier_rapport(interface)[2] == []


@then(parsers.re(r"le rapport a signalé (?P<nombre>\d+) anomalies?, sur (?P<chemins>«.+)"))
def anomalies(interface: Contexte, nombre: str, chemins: str) -> None:
	signalees = dernier_rapport(interface)[2]
	assert len(signalees) == int(nombre), signalees
	for anomalie, chemin in zip(signalees, NOM.findall(chemins), strict=True):
		assert anomalie.startswith(f"{interface.chemin(chemin)} : "), anomalie


@then(parsers.parse("les sonores de la banque « {nom} » en base sont :"))
def sonores_de_la_banque(interface: Contexte, base_vide: Connexion, nom: str, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	lus = base_vide.execute(
		"SELECT s.emplacement, s.etat::text, s.titre FROM sonores s"
		" JOIN banques_sonores bs ON bs.sonore_id = s.id JOIN banques b ON b.id = bs.banque_id"
		" WHERE b.nom_interne = %s ORDER BY bs.position",
		(nom,),
	).fetchall()
	assert [entete.strip() for entete in entetes] == ["emplacement", "etat", "titre"]
	attendus = [tuple(interface.chemin(valeur.strip()) for valeur in rangee) for rangee in rangees]
	assert [tuple(str(valeur) for valeur in ligne) for ligne in lus] == attendus


@then(parsers.parse("le sonore « {titre} » est à l'état « {libelle} »"))
def etat(base_vide: Connexion, titre: str, libelle: str) -> None:
	lu = base_vide.execute("SELECT etat::text FROM sonores WHERE titre = %s", (titre,)).fetchone()
	assert lu is not None, f"sonore « {titre} » absent"
	assert LIBELLES[lu[0]] == libelle
