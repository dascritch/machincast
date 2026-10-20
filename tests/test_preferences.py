"""Scénarios des préférences de l'interface (https://github.com/dascritch/machincast/issues/145).

Les étapes de la fenêtre, de sa barre de menus et des fiches sont dans tests/etapes_interface.py, où la fenêtre des
préférences est remplacée par les réglages du scénario. La vraie fenêtre des préférences s'ouvre ici, hors de l'écran
du poste.
"""

import re
import tomllib
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from PySide6.QtWidgets import QDialogButtonBox, QDoubleSpinBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import Crossfades, charger
from machincast.interface import dialogues, preferences
from machincast.interface.fiche_banque import FicheBanque
from machincast.interface.fiche_sonore import FicheSonore
from machincast.interface.preferences import FenetrePreferences
from tests.etapes_interface import Connexion, Contexte, fenetre, fichier_de_configuration, ouvrir_la_fenetre
from tests.modales import quand_modale

scenarios("preferences.feature")

REGLAGES = (
	r"granularité « (?P<granularite>seconde|dixieme) », maximum (?P<maximum>[\d,]+) s,"
	r" début par défaut (?:(?P<debut>[\d,]+) s|aucune), fin par défaut (?:(?P<fin>[\d,]+) s|aucune)"
)
"""Les réglages des crossfades, tels que les écrit un scénario."""


def _secondes(texte: str | None) -> timedelta | None:
	if texte is None:
		return None
	return timedelta(seconds=float(texte.replace(",", ".")))


def reglages(granularite: str, maximum: str, debut: str | None, fin: str | None) -> Crossfades:
	duree = _secondes(maximum)
	assert duree is not None
	assert granularite in ("seconde", "dixieme")
	return Crossfades(_secondes(debut), _secondes(fin), duree, "seconde" if granularite == "seconde" else "dixieme")


def lire_reglages(texte: str) -> Crossfades:
	trouve = re.fullmatch(REGLAGES, texte)
	assert trouve is not None, texte
	return reglages(**trouve.groupdict())


# ─── Fenêtre de l'interface ────────────────────────────────


@given("le fichier de configuration de l'interface, avec :")
def configuration_avec(interface: Contexte, docstring: str) -> None:
	chemin = fichier_de_configuration(interface)
	chemin.write_text(f"{chemin.read_text(encoding='utf-8')}\n{docstring}\n", encoding="utf-8")


@given("le fichier de configuration de l'interface, que le poste refuse d'écrire")
def configuration_refusee(interface: Contexte, monkeypatch: pytest.MonkeyPatch) -> None:
	"""Les tests tournent parfois sous root, que les droits d'un fichier n'arrêtent pas : l'écriture est refusée."""
	fichier_de_configuration(interface)

	def refuser(chemin: Path, _crossfades: Crossfades) -> None:
		raise PermissionError(13, "Permission non accordée", str(chemin))

	monkeypatch.setattr(preferences, "ecrire", refuser)


@given(parsers.re(rf"les préférences seront réglées : {REGLAGES}"))
def preferences_reglees(
	interface: Contexte, granularite: str, maximum: str, debut: str | None, fin: str | None
) -> None:
	interface.preferences_reglees = reglages(granularite, maximum, debut, fin)


@then(parsers.re(rf"les préférences ont montré : {REGLAGES}"))
def preferences_montrees(
	interface: Contexte, granularite: str, maximum: str, debut: str | None, fin: str | None
) -> None:
	assert interface.preferences_montrees == [reglages(granularite, maximum, debut, fin)]


@then(parsers.re(rf"le fichier de configuration donne les crossfades : {REGLAGES}"))
def crossfades_du_fichier(
	interface: Contexte, granularite: str, maximum: str, debut: str | None, fin: str | None
) -> None:
	assert charger(fichier_de_configuration(interface)).crossfades == reglages(granularite, maximum, debut, fin)


@then(parsers.parse("le fichier de configuration contient encore « {ligne} »"))
def contient_encore(interface: Contexte, ligne: str) -> None:
	assert ligne in fichier_de_configuration(interface).read_text(encoding="utf-8").splitlines()


@then("le fichier de configuration contient encore les autres sections")
def autres_sections(interface: Contexte) -> None:
	avant = tomllib.loads(interface.configuration_initiale.decode("utf-8"))
	apres = tomllib.loads(fichier_de_configuration(interface).read_text(encoding="utf-8"))
	avant.pop("crossfades", None)
	apres.pop("crossfades", None)
	assert apres == avant


@then(parsers.parse("le fichier de configuration n'a plus de clé « {cle} »"))
def plus_de_cle(interface: Contexte, cle: str) -> None:
	document = tomllib.loads(fichier_de_configuration(interface).read_text(encoding="utf-8"))
	assert cle not in document["crossfades"], document["crossfades"]


@then("le fichier de configuration n'a pas changé")
def inchange(interface: Contexte) -> None:
	assert fichier_de_configuration(interface).read_bytes() == interface.configuration_initiale


@then(parsers.parse("la barre d'état annonce une erreur qui commence par « {debut} »"))
def erreur_annoncee(interface: Contexte, debut: str) -> None:
	message = fenetre(interface).statusBar().currentMessage()
	assert message.startswith(interface.chemin_dans(debut)), message


@then(
	parsers.re(
		r"les crossfades de la fiche se règlent (?P<granularite>au dixième de seconde|à la seconde),"
		r" jusqu'à (?P<maximum>\d+) s"
	)
)
def crossfades_de_la_fiche(interface: Contexte, granularite: str, maximum: str) -> None:
	ouverte = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(ouverte, (FicheSonore, FicheBanque)), ouverte
	champs = (ouverte.ui.crossfade_debut, ouverte.ui.crossfade_fin)
	decimales, pas = {"au dixième de seconde": (1, 0.1), "à la seconde": (0, 1.0)}[granularite]
	reglages_lus = [(champ.decimals(), champ.singleStep(), champ.maximum()) for champ in champs]
	assert reglages_lus == [(decimales, pas, float(maximum))] * 2


# ─── Fenêtre des préférences ───────────────────────────────


@pytest.fixture
def parent(qtbot: QtBot) -> Iterator[QWidget]:
	widget = QWidget()
	qtbot.addWidget(widget)
	yield widget


class Ouverte:
	fenetre: FenetrePreferences | None = None
	donnes: Crossfades | None = None


@pytest.fixture
def ouverte() -> Ouverte:
	return Ouverte()


def la_fenetre(ouverte: Ouverte) -> FenetrePreferences:
	assert ouverte.fenetre is not None
	return ouverte.fenetre


@when(parsers.re(rf"la fenêtre des préférences s'ouvre sur : {REGLAGES}"))
def ouvrir_les_preferences(
	ouverte: Ouverte, parent: QWidget, granularite: str, maximum: str, debut: str | None, fin: str | None
) -> None:
	ouverte.fenetre = FenetrePreferences(reglages(granularite, maximum, debut, fin), parent)


@then(parsers.parse("elle s'intitule « {titre} », avec la page « {page} »"))
def titre_et_page(ouverte: Ouverte, titre: str, page: str) -> None:
	ui = la_fenetre(ouverte).ui
	pages = [ui.pages.tabText(rang) for rang in range(ui.pages.count())]
	assert (la_fenetre(ouverte).windowTitle(), pages) == (titre, [page])


def _montree(case_et_champ: tuple[object, QDoubleSpinBox] | QDoubleSpinBox) -> str | None:
	if isinstance(case_et_champ, QDoubleSpinBox):
		return case_et_champ.text()
	case, champ = case_et_champ
	assert hasattr(case, "isChecked")
	if not case.isChecked():  # type: ignore[attr-defined]
		assert not champ.isEnabled()
		return None
	assert champ.isEnabled()
	return champ.text()


@then(
	parsers.re(
		r"elle montre : granularité « (?P<granularite>[^»]+) », maximum « (?P<maximum>[^»]+) »,"
		r" début par défaut (?:« (?P<debut>[^»]+) »|aucune), fin par défaut (?:« (?P<fin>[^»]+) »|aucune)"
	)
)
def montre(ouverte: Ouverte, granularite: str, maximum: str, debut: str | None, fin: str | None) -> None:
	ui = la_fenetre(ouverte).ui
	montres = (
		ui.granularite.currentText(),
		_montree(ui.maximum),
		_montree((ui.a_debut, ui.debut)),
		_montree((ui.a_fin, ui.fin)),
	)
	assert montres == (granularite, maximum, debut, fin)


@when(parsers.parse("j'y choisis la granularité « {texte} »"))
def choisir_granularite(ouverte: Ouverte, texte: str) -> None:
	liste = la_fenetre(ouverte).ui.granularite
	rang = liste.findText(texte)
	assert rang >= 0, texte
	liste.setCurrentIndex(rang)


@when(parsers.parse("j'y saisis le maximum {secondes:d}"))
def saisir_maximum(ouverte: Ouverte, secondes: int) -> None:
	la_fenetre(ouverte).ui.maximum.setValue(secondes)


@when(parsers.re(r"j'y retire la durée de (?P<cote>début|fin) par défaut"))
def retirer_defaut(ouverte: Ouverte, cote: str) -> None:
	ui = la_fenetre(ouverte).ui
	case = {"début": ui.a_debut, "fin": ui.a_fin}[cote]
	assert case.isChecked(), cote
	case.setChecked(False)


@when(parsers.re(r"j'y saisis la durée de (?P<cote>début|fin) par défaut (?P<secondes>[\d,]+)"))
def saisir_defaut(ouverte: Ouverte, cote: str, secondes: str) -> None:
	ui = la_fenetre(ouverte).ui
	case, champ = {"début": (ui.a_debut, ui.debut), "fin": (ui.a_fin, ui.fin)}[cote]
	case.setChecked(True)
	champ.setValue(float(secondes.replace(",", ".")))


@when(parsers.parse("j'y clique sur « {bouton} »"))
def cliquer(ouverte: Ouverte, bouton: str) -> None:
	fenetre_preferences = la_fenetre(ouverte)
	role = {"OK": QDialogButtonBox.StandardButton.Ok, "Annuler": QDialogButtonBox.StandardButton.Cancel}[bouton]
	fenetre_preferences.ui.boutons.button(role).click()
	ouverte.donnes = None
	if fenetre_preferences.result() == FenetrePreferences.DialogCode.Accepted:
		ouverte.donnes = fenetre_preferences.reglages()


@then(parsers.re(rf"elle a donné : {REGLAGES}"))
def donnes(ouverte: Ouverte, granularite: str, maximum: str, debut: str | None, fin: str | None) -> None:
	assert ouverte.donnes == reglages(granularite, maximum, debut, fin)


@when(parsers.re(rf"je réponds « (?P<bouton>OK|Annuler) » à la fenêtre des préférences ouverte sur : {REGLAGES}"))
def repondre(
	ouverte: Ouverte,
	parent: QWidget,
	bouton: str,
	granularite: str,
	maximum: str,
	debut: str | None,
	fin: str | None,
) -> None:
	def faire(modale: QWidget) -> None:
		assert isinstance(modale, FenetrePreferences), modale
		role = {"OK": QDialogButtonBox.StandardButton.Ok, "Annuler": QDialogButtonBox.StandardButton.Cancel}[bouton]
		modale.ui.boutons.button(role).click()

	quand_modale(faire)
	ouverte.donnes = dialogues.regler_preferences(parent, reglages(granularite, maximum, debut, fin))


@then(parsers.re(rf"les réglages donnés sont (?:aucun|{REGLAGES})"))
def reglages_donnes(
	ouverte: Ouverte,
	granularite: str | None,
	maximum: str | None,
	debut: str | None,
	fin: str | None,
) -> None:
	attendus = None
	if (granularite is not None) and (maximum is not None):
		attendus = reglages(granularite, maximum, debut, fin)
	assert ouverte.donnes == attendus


@then(parsers.parse("le fichier de configuration contient la ligne « {ligne} »"))
def contient_la_ligne(interface: Contexte, ligne: str) -> None:
	assert ligne in fichier_de_configuration(interface).read_text(encoding="utf-8").splitlines()


@when("la fenêtre de l'interface s'ouvre, sans fichier de configuration")
def ouvrir_sans_configuration(interface: Contexte, base_vide: Connexion, qtbot: QtBot) -> None:
	ouvrir_la_fenetre(interface, qtbot, avec_configuration=False)


@then(parsers.re(r"son maximum se règle par pas de (?P<pas>[\d,]+) s, à partir de (?P<minimum>[\d,]+) s"))
def pas_du_maximum(ouverte: Ouverte, pas: str, minimum: str) -> None:
	champ = la_fenetre(ouverte).ui.maximum
	attendus = tuple(float(valeur.replace(",", ".")) for valeur in (pas, minimum))
	assert (champ.singleStep(), champ.minimum()) == attendus
