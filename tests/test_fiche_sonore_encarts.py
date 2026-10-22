"""Scénarios des encarts dépliables et de la vérification complète de la fiche d'un sonore
(https://github.com/dascritch/machincast/issues/190).

Les étapes de la fenêtre, des fiches et des sonores en base sont dans tests/etapes_interface.py. Le décodage de la
vérification complète passe par machincast.interface.verification._verifier_fichier_complet, que le scénario peut
retenir jusqu'à ce qu'il le laisse finir.
"""

import threading
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QCheckBox, QFormLayout, QGroupBox, QLabel, QPushButton, QSlider
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import Crossfades
from machincast.empreinte import etat_du_fichier
from machincast.indexation.decodage import Verification
from machincast.interface import preferences, verification
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


@given(
	parsers.re(
		r"le sonore « (?P<titre>[^»]+) » déjà audité au seuil de (?P<seuil>-?\d+) dB, son fichier inchangé depuis"
	)
)
def deja_audite(interface: Contexte, base_vide: Connexion, titre: str, seuil: str) -> None:
	"""Sa date et sa taille sont celles du fichier, audité après sa dernière modification."""
	ligne = base_vide.execute("SELECT emplacement FROM sonores WHERE titre = %s", (titre,)).fetchone()
	assert ligne is not None
	emplacement = ligne[0]
	etat = etat_du_fichier(Path(str(emplacement)))
	assert etat is not None
	modifie_le, taille = etat
	base_vide.execute(
		"UPDATE sonores SET fichier_modifie_le = %s, fichier_taille = %s, verifie_le = clock_timestamp(),"
		" audite_le = clock_timestamp(), audit_seuil = %s WHERE titre = %s",
		(modifie_le, taille, float(seuil), titre),
	)


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


@given(parsers.parse("les crossfades des préférences au dixième de seconde, jusqu'à {maximum:d} secondes"))
def preferences_au_dixieme(monkeypatch: pytest.MonkeyPatch, maximum: int) -> None:
	monkeypatch.setattr(
		preferences, "_courantes", Crossfades(granularite="dixieme", maximum=timedelta(seconds=maximum))
	)


@when(
	parsers.re(
		r"je coche le crossfade de (?P<cote>début|fin) de la fiche, et pousse son curseur de (?P<crans>\d+) crans"
	)
)
def pousser(interface: Contexte, qtbot: QtBot, cote: str, crans: str) -> None:
	ui = fiche(interface).ui
	case, champ = (
		(ui.a_crossfade_debut, ui.crossfade_debut) if cote == "début" else (ui.a_crossfade_fin, ui.crossfade_fin)
	)
	case.setChecked(True)
	curseur = champ.findChild(QSlider)
	assert curseur is not None
	curseur.setFocus()
	for _ in range(int(crans)):
		qtbot.keyClick(curseur, Qt.Key.Key_Right)


@when(parsers.parse("je coche le début détecté de la fiche, à {secondes} seconde"))
def debut_detecte(interface: Contexte, secondes: str) -> None:
	ui = fiche(interface).ui
	ui.a_debut_detecte.setChecked(True)
	ui.debut_detecte.setValue(float(secondes.replace(",", ".")))


@when(parsers.re(r"je (?P<geste>coche|décoche) « Jouer sans les blancs détectés » dans la fiche"))
def jouer_sans_blancs(interface: Contexte, geste: str) -> None:
	fiche(interface).ui.detection_blancs.setChecked(geste == "coche")


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


def libelles(groupe: QGroupBox) -> list[str]:
	"""Les libellés des lignes du formulaire de l'encart, dans l'ordre : l'étiquette, la case, ou la case seule."""
	formulaire = groupe.findChild(QFormLayout)
	assert formulaire is not None
	trouves: list[str] = []
	for ligne in range(formulaire.rowCount()):
		for role in (QFormLayout.ItemRole.LabelRole, QFormLayout.ItemRole.SpanningRole):
			element = formulaire.itemAt(ligne, role)
			if element is None:
				continue
			widget = element.widget()
			if isinstance(widget, (QLabel, QCheckBox)):
				trouves.append(widget.text())
	return trouves


@then(parsers.re(r"l'encart « (?P<nom>[^»]+) » a les champs (?P<noms>«.+)"))
def champs_de_l_encart(interface: Contexte, nom: str, noms: str) -> None:
	(groupe,) = [groupe for groupe in encarts(interface) if titre(groupe) == nom]
	assert libelles(groupe) == NOM.findall(noms)


@then(
	parsers.re(
		r"le crossfade de début de la fiche est un curseur horizontal de 0 à (?P<maximum>\d+) secondes,"
		r" au pas de (?P<pas>[\d,]+) seconde"
	)
)
def curseur_du_crossfade(interface: Contexte, maximum: str, pas: str) -> None:
	champ = fiche(interface).ui.crossfade_debut
	curseur = champ.findChild(QSlider)
	assert curseur is not None
	assert curseur.orientation() == Qt.Orientation.Horizontal
	assert (curseur.minimum(), champ.maximum()) == (0, float(maximum))
	assert curseur.maximum() * float(pas.replace(",", ".")) == float(maximum)


@given(parsers.parse("le sonore « {nom} » a {secondes:d} secondes de crossfade de début en base"))
def crossfade_en_base(base_vide: Connexion, nom: str, secondes: int) -> None:
	base_vide.execute("UPDATE sonores SET crossfade_debut = %s WHERE titre = %s", (timedelta(seconds=secondes), nom))


@then(parsers.parse("la frise de la fiche montre un crossfade de fin de {fin} seconde"))
def crossfade_de_fin_de_la_frise(interface: Contexte, fin: str) -> None:
	plan = fiche(interface).frise.plan
	assert (plan is not None) and (plan.crossfade_fin == float(fin.replace(",", "."))), plan


@then(parsers.parse("le crossfade de début de la fiche montre « {texte} »"))
def valeur_du_crossfade(interface: Contexte, texte: str) -> None:
	assert fiche(interface).ui.crossfade_debut.text() == texte


@then("l'état de la fiche propose :")
def etats_proposes(interface: Contexte, datatable: list[list[str]]) -> None:
	choix = fiche(interface).ui.etat
	modele = choix.model()
	trouves = []
	for rang in range(choix.count()):
		actif = bool(modele.flags(modele.index(rang, 0)) & Qt.ItemFlag.ItemIsEnabled)
		etat = "possible" if actif else "grisé"
		if rang == choix.currentIndex():
			etat = "choisi"
		trouves.append([choix.itemText(rang), etat])
	_entetes, *rangees = datatable
	assert trouves == [[etat.strip(), quoi.strip()] for etat, quoi in rangees]


@then("la frise de la fiche est sur toute sa largeur, au-dessus des encarts")
def frise_pleine_largeur(interface: Contexte, qtbot: QtBot) -> None:
	ouverte = fiche(interface)
	fenetre(interface).show()
	qtbot.wait(50)
	frise = ouverte.frise
	assert frise.isVisibleTo(ouverte)
	assert frise.width() >= ouverte.width() - 40, (frise.width(), ouverte.width())
	bas = frise.mapTo(ouverte, QPoint(0, frise.height())).y()
	assert bas <= ouverte.ui.groupe_sonore.mapTo(ouverte, QPoint(0, 0)).y()


@then("la frise de la fiche dessine bientôt la forme d'onde de son fichier")
def forme_de_la_fiche(interface: Contexte, qtbot: QtBot) -> None:
	frise = fiche(interface).frise
	qtbot.waitUntil(
		lambda: (frise.forme is not None) and (frise.forme.finie) and (frise.forme.erreur is None), timeout=DELAI
	)
	assert frise.forme is not None
	assert len(frise.forme.pics) > 0


@then(
	parsers.parse(
		"la frise de la fiche montre un crossfade de fin de {fin} seconde, un blanc de {blanc} seconde au début,"
		" retiré à l'antenne"
	)
)
def plan_de_la_fiche(interface: Contexte, fin: str, blanc: str) -> None:
	plan = fiche(interface).frise.plan
	assert plan is not None
	assert (plan.crossfade_fin, plan.blanc_debut, plan.blancs_retires) == (
		float(fin.replace(",", ".")),
		float(blanc.replace(",", ".")),
		True,
	), plan


@then("la frise de la fiche montre les blancs joués")
def blancs_joues(interface: Contexte) -> None:
	plan = fiche(interface).frise.plan
	assert (plan is not None) and (not plan.blancs_retires), plan


@then("la fiche n'a pas de frise")
def sans_frise(interface: Contexte) -> None:
	assert not fiche(interface).ui.place_frise.isVisibleTo(fiche(interface))
