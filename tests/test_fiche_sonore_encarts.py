"""Scénarios des encarts dépliables et de la vérification complète de la fiche d'un sonore
(https://github.com/dascritch/machincast/issues/190).

Les étapes de la fenêtre, des fiches et des sonores en base sont dans tests/etapes_interface.py. Le décodage de la
vérification complète passe par machincast.interface.verification._verifier_fichier_complet, que le scénario peut
retenir jusqu'à ce qu'il le laisse finir.
"""

import threading
from pathlib import Path

import psycopg
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QGroupBox, QPushButton
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.indexation.decodage import Verification
from machincast.interface import verification
from machincast.interface.depliable import est_replie
from machincast.interface.fiche_sonore import FicheSonore
from tests.etapes_interface import NOM, Contexte, fenetre

scenarios("fiche_sonore_encarts.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
DELAI = 10000
"""Millisecondes laissées à la vérification complète d'un fichier de test."""


def fiche(interface: Contexte) -> FicheSonore:
	ouverte = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(ouverte, FicheSonore), ouverte
	return ouverte


def encarts(interface: Contexte) -> list[QGroupBox]:
	"""Les encarts montrés par la fiche, dans l'ordre de leur création."""
	return [groupe for groupe in fiche(interface).findChildren(QGroupBox) if not groupe.isHidden()]


def titre(groupe: QGroupBox) -> str:
	"""Le titre de l'encart, sans la flèche d'un encart dépliable."""
	return groupe.title().removeprefix("▸ ").removeprefix("▾ ")


# ─── Étant donné ───────────────────────────────────────────


@pytest.fixture
def retenue() -> threading.Event:
	"""Posé par le scénario pour laisser finir la vérification complète retenue."""
	return threading.Event()


@given("la vérification complète retenue par le scénario")
def retenir(monkeypatch: pytest.MonkeyPatch, retenue: threading.Event) -> None:
	vraie = verification._verifier_fichier_complet

	def attendre(chemin: Path, *, seuil_blancs: float | None = None) -> Verification:
		assert retenue.wait(timeout=DELAI / 1000), "vérification jamais laissée finir"
		return vraie(chemin, seuil_blancs=seuil_blancs)

	monkeypatch.setattr(verification, "_verifier_fichier_complet", attendre)


@given("le refus de rafraîchir la fiche après la vérification")
def refuser(interface: Contexte) -> None:
	interface.rafraichir_apres_verification = False


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("je clique sur le titre de l'encart « {nom} »"))
def cliquer_le_titre(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	(groupe,) = [groupe for groupe in encarts(interface) if titre(groupe) == nom]
	# Le titre est en haut de l'encart, à gauche.
	qtbot.mouseClick(groupe, Qt.MouseButton.LeftButton, pos=QPoint(12, 6))


@when("la vérification complète se termine")
def terminer(interface: Contexte, qtbot: QtBot, retenue: threading.Event) -> None:
	retenue.set()
	qtbot.waitUntil(lambda: not fenetre(interface).verification_complete.en_cours(), timeout=DELAI)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"les encarts (?P<etat>repliés|dépliés) de la fiche sont (?P<noms>«.+)"))
def encarts_selon_l_etat(interface: Contexte, etat: str, noms: str) -> None:
	trouves = [titre(groupe) for groupe in encarts(interface) if est_replie(groupe) is (etat == "repliés")]
	assert trouves == NOM.findall(noms)


@then(parsers.parse("la fiche montre la dernière vérification complète « {texte} »"))
def derniere_verification(interface: Contexte, texte: str) -> None:
	assert fiche(interface).ui.verifie_le.text() == texte


@then("la fiche montre une dernière vérification complète datée")
def verification_datee(interface: Contexte) -> None:
	assert fiche(interface).ui.verifie_le.text() not in ("", "jamais")


@then(parsers.re(r"le bouton « (?P<texte>[^»]+) » de la fiche est (?P<etat>actif|inactif)"))
def bouton(interface: Contexte, texte: str, etat: str) -> None:
	(trouve,) = [bouton for bouton in fiche(interface).findChildren(QPushButton) if bouton.text() == texte]
	assert trouve.isEnabled() is (etat == "actif")


@then(parsers.parse("la question après la vérification a dit « {texte} »"))
def question(interface: Contexte, texte: str) -> None:
	assert interface.questions == [f"après vérification : {texte}"]


@then(parsers.parse("le sonore du fichier « {chemin} » a été vérifié en entier, ses blancs mesurés"))
def verifie_en_entier(interface: Contexte, base_vide: Connexion, qtbot: QtBot, chemin: str) -> None:
	def lu() -> tuple[object, ...] | None:
		return base_vide.execute(
			"SELECT verifie_le IS NOT NULL, duree IS NOT NULL, fin_detectee IS NOT NULL FROM sonores"
			" WHERE emplacement = %s",
			(interface.chemin(chemin),),
		).fetchone()

	qtbot.waitUntil(lambda: lu() == (True, True, True), timeout=DELAI)


@when(parsers.parse("je clique dans l'encart « {nom} », sous son titre"))
def cliquer_le_contenu(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	(groupe,) = [groupe for groupe in encarts(interface) if titre(groupe) == nom]
	# Déplié, l'encart grandit quand sa disposition s'applique.
	qtbot.waitUntil(lambda: groupe.height() > 4 * groupe.fontMetrics().height(), timeout=1000)
	qtbot.mouseClick(groupe, Qt.MouseButton.LeftButton, pos=QPoint(12, groupe.height() - 4))


@then(
	parsers.re(
		r"l'encart « (?P<nom>[^»]+) » a pour titre « (?P<texte>[^»]+) », et (?P<geste>cache|montre)"
		r" la dernière vérification complète"
	)
)
def titre_et_contenu(interface: Contexte, nom: str, texte: str, geste: str) -> None:
	(groupe,) = [groupe for groupe in encarts(interface) if titre(groupe) == nom]
	assert groupe.title() == texte
	assert fiche(interface).ui.verifie_le.isVisible() is (geste == "montre")
