"""Scénarios des préférences de l'interface (https://github.com/dascritch/machincast/issues/145).

Les étapes de la fenêtre, de sa barre de menus et des fiches sont dans tests/etapes_interface.py, où la fenêtre des
préférences est remplacée par les réglages du scénario. La vraie fenêtre des préférences s'ouvre ici, hors de l'écran
du poste.
"""

import dataclasses
import re
import stat
import tomllib
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
import tomlkit
from PySide6.QtGui import QColor, QIcon, QImage, QStandardItemModel
from PySide6.QtWidgets import QApplication, QComboBox, QDialogButtonBox, QDoubleSpinBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast import raccourci
from machincast.configuration import Crossfades, charger
from machincast.interface import __main__ as module_interface
from machincast.interface import application as module_application
from machincast.interface import dialogues, preferences
from machincast.interface.fenetre import FenetrePrincipale
from machincast.interface.fiche_banque import FicheBanque
from machincast.interface.fiche_sonore import FicheSonore
from machincast.interface.preferences import FenetrePreferences, Reglages
from machincast.interface.suggestions import Reponse
from machincast.raccourci import ICONE
from tests.base_test import configuration_test
from tests.etapes_interface import NOM, Connexion, Contexte, fenetre, fichier_de_configuration, ouvrir_la_fenetre
from tests.modales import quand_modale

scenarios("preferences.feature")

REGLAGES = (
	r"granularité « (?P<granularite>seconde|dixieme) », maximum (?P<maximum>[\d,]+) s,"
	r" début par défaut (?:(?P<debut>[\d,]+) s|aucune), fin par défaut (?:(?P<fin>[\d,]+) s|aucune)"
)
"""Les réglages des crossfades, tels que les écrit un scénario."""
PREECOUTE_DES_TESTS = "preecoute-factice"
"""Le périphérique de pré-écoute de la configuration des tests."""


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

	def refuser(chemin: Path, _reglages: Reglages) -> None:
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


@then(parsers.re(r"le fichier de configuration contient encore les autres sections(?P<hors_audio>, hors \[audio\])?"))
def autres_sections(interface: Contexte, hors_audio: str | None) -> None:
	avant = tomllib.loads(interface.configuration_initiale.decode("utf-8"))
	apres = tomllib.loads(fichier_de_configuration(interface).read_text(encoding="utf-8"))
	# Les préférences tiennent toujours [crossfades], [blancs] (https://github.com/dascritch/machincast/issues/146) et
	# [interface] (https://github.com/dascritch/machincast/issues/191).
	retirees = ["crossfades", "blancs", "interface"]
	if hors_audio is not None:
		retirees.append("audio")
	for section in retirees:
		avant.pop(section, None)
		apres.pop(section, None)
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
	donnes: Reglages | None = None


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
	tous = Reglages(reglages(granularite, maximum, debut, fin), None, PREECOUTE_DES_TESTS)
	ouverte.fenetre = FenetrePreferences(tous, "factice", parent)


@then(parsers.re(r"elle s'intitule « (?P<titre>[^»]+) », avec les pages (?P<pages>«.+)"))
def titre_et_pages(ouverte: Ouverte, titre: str, pages: str) -> None:
	"""Les pages dans l'ordre, la première ouverte : les crossfades ont la leur
	(https://github.com/dascritch/machincast/issues/234)."""
	ui = la_fenetre(ouverte).ui
	lues = [ui.pages.tabText(rang) for rang in range(ui.pages.count())]
	assert (la_fenetre(ouverte).windowTitle(), lues) == (titre, NOM.findall(pages))
	assert ui.pages.currentIndex() == 0


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
	assert ouverte.donnes is not None
	assert ouverte.donnes.crossfades == reglages(granularite, maximum, debut, fin)


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
	tous = Reglages(reglages(granularite, maximum, debut, fin), None, PREECOUTE_DES_TESTS)
	ouverte.donnes = dialogues.regler_preferences(parent, tous, "factice")


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
		attendus = Reglages(reglages(granularite, maximum, debut, fin), None, PREECOUTE_DES_TESTS)
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


# ─── Page « Audio » ────────────────────────────────────────


@when(
	parsers.re(
		r"la fenêtre des préférences s'ouvre sur l'antenne (?:« (?P<antenne>[^»]+) »|non renseignée)"
		r" et la pré-écoute « (?P<preecoute>[^»]+) »"
	)
)
def ouvrir_sur_l_audio(ouverte: Ouverte, parent: QWidget, antenne: str | None, preecoute: str) -> None:
	ouverte.fenetre = FenetrePreferences(Reglages(Crossfades(), antenne, preecoute), "pipewire", parent)


def choix_audio(ouverte: Ouverte, nom: str) -> QComboBox:
	ui = la_fenetre(ouverte).ui
	return {"antenne": ui.antenne, "pré-écoute": ui.preecoute}[nom]


@then(parsers.re(r"le choix (?:de l'|de la )(?P<nom>antenne|pré-écoute) propose :"))
def choix_propose(ouverte: Ouverte, nom: str, datatable: list[list[str]]) -> None:
	choix = choix_audio(ouverte, nom)
	modele = choix.model()
	assert isinstance(modele, QStandardItemModel)
	lues = []
	for indice in range(choix.count()):
		etat_de_la_ligne = "inactive"
		if modele.item(indice).isEnabled():
			etat_de_la_ligne = "active"
		lues.append([choix.itemText(indice), etat_de_la_ligne])
	assert lues == [[cellule.strip() for cellule in rangee] for rangee in datatable[1:]]


@when(parsers.re(r"j'y choisis (?:pour l'|pour la )(?P<nom>antenne|pré-écoute) « (?P<texte>[^»]+) »"))
def choisir_peripherique(ouverte: Ouverte, nom: str, texte: str) -> None:
	choix = choix_audio(ouverte, nom)
	indice = choix.findText(texte)
	assert indice >= 0, texte
	choix.setCurrentIndex(indice)


@then(parsers.re(r"son bouton « OK » est (?P<etat>actif|inactif)"))
def bouton_ok(ouverte: Ouverte, etat: str) -> None:
	bouton = la_fenetre(ouverte).ui.boutons.button(QDialogButtonBox.StandardButton.Ok)
	assert bouton.isEnabled() == (etat == "actif")


@then(
	parsers.re(
		r"elle a donné l'antenne (?:« (?P<antenne>[^»]+) »|non renseignée) et la pré-écoute « (?P<preecoute>[^»]+) »"
	)
)
def audio_donne(ouverte: Ouverte, antenne: str | None, preecoute: str) -> None:
	assert ouverte.donnes is not None
	assert (ouverte.donnes.antenne, ouverte.donnes.preecoute) == (antenne, preecoute)


@then(
	parsers.re(
		r"les préférences ont montré l'antenne (?:« (?P<antenne>[^»]+) »|non renseignée)"
		r" et la pré-écoute « (?P<preecoute>[^»]+) »"
	)
)
def audio_montre(interface: Contexte, antenne: str | None, preecoute: str) -> None:
	assert interface.audio_montre[-1] == (antenne, preecoute)


@then(parsers.parse("le fichier de configuration donne l'antenne « {antenne} » et la pré-écoute « {preecoute} »"))
def audio_du_fichier(interface: Contexte, antenne: str, preecoute: str) -> None:
	audio = charger(fichier_de_configuration(interface)).audio
	assert (audio.peripherique, audio.preecoute) == (antenne, preecoute)


@then(parsers.re(r"la barre d'état (?P<signale>signale|ne signale pas) « Périphérique de l'antenne à renseigner »"))
def antenne_signalee(interface: Contexte, signale: str) -> None:
	etiquette = fenetre(interface).antenne_a_renseigner
	assert etiquette.isVisibleTo(fenetre(interface)) == (signale == "signale")
	assert etiquette.text() == "Périphérique de l'antenne à renseigner"
	assert etiquette.toolTip().startswith("Machin lecture refuse de diffuser sans lui")


# ─── Machin interface ──────────────────────────────────────


@given(
	parsers.parse(
		"un fichier de configuration sur la base de test, la sortie « {sortie} », l'antenne « {antenne} »"
		" et la pré-écoute « {preecoute} »"
	),
	target_fixture="configuration_lancee",
)
def configuration_lancee(base_vide: Connexion, tmp_path: Path, sortie: str, antenne: str, preecoute: str) -> Path:
	"""La configuration des tests, sur la base de test comme base de production : sa base de test, qui doit en
	différer, en devient une autre, que l'interface n'ouvre pas."""
	source = configuration_test()
	texte = (
		source.chemin.read_text(encoding="utf-8")
		.replace(f'test = "{source.base.test}"', f'test = "{source.base.test}_inutilisee"')
		.replace(f'production = "{source.base.production}"', f'production = "{source.base.test}"')
		.replace('sortie = "factice"', f'sortie = "{sortie}"\nperipherique = "{antenne}"')
		.replace(f'preecoute = "{source.audio.preecoute}"', f'preecoute = "{preecoute}"')
	)
	chemin = tmp_path / "machincast.toml"
	chemin.write_text(texte, encoding="utf-8")
	return chemin


class Lancement:
	fenetre: FenetrePrincipale | None = None
	montres: tuple[Reglages, str] | None = None


@pytest.fixture
def lancement() -> Lancement:
	return Lancement()


@when("Machin interface est lancé avec ce fichier")
def lancer_l_interface(
	configuration_lancee: Path, lancement: Lancement, monkeypatch: pytest.MonkeyPatch, qtbot: QtBot
) -> None:
	"""Son point d'entrée, jusqu'à la boucle de Qt, qui rend la main aussitôt : la fenêtre reste à examiner."""

	class Application:
		def exec(self) -> int:
			return 0

	def montrer(fenetre: FenetrePrincipale) -> None:
		qtbot.addWidget(fenetre)
		lancement.fenetre = fenetre

	monkeypatch.setattr(module_application, "application", lambda _nom: Application())
	monkeypatch.setattr(FenetrePrincipale, "show", montrer)
	# La fenêtre des suggestions au lancement est refermée par « Plus tard »
	# (https://github.com/dascritch/machincast/issues/119).
	monkeypatch.setattr(dialogues, "suggerer", lambda _parent, _manques: Reponse(creer=False))
	assert module_interface.main(["--config", str(configuration_lancee)]) == 0


@then(parsers.parse("sa fenêtre a la sortie « {sortie} », l'antenne « {antenne} » et la pré-écoute « {preecoute} »"))
def audio_de_la_fenetre(lancement: Lancement, sortie: str, antenne: str, preecoute: str) -> None:
	assert lancement.fenetre is not None
	audio = lancement.fenetre.audio
	assert (audio.sortie, audio.peripherique, audio.preecoute) == (sortie, antenne, preecoute)


@then(
	parsers.parse(
		"ses préférences montrent l'antenne « {antenne} » et la pré-écoute « {preecoute} », sur la sortie « {sortie} »"
	)
)
def preferences_de_la_fenetre(
	lancement: Lancement, monkeypatch: pytest.MonkeyPatch, antenne: str, preecoute: str, sortie: str
) -> None:
	def regler(_parent: QWidget, montres: Reglages, sortie_montree: str) -> None:
		lancement.montres = (montres, sortie_montree)

	monkeypatch.setattr(dialogues, "regler_preferences", regler)
	assert lancement.fenetre is not None
	lancement.fenetre._preferences()
	assert lancement.montres is not None
	montres, sortie_montree = lancement.montres
	assert (montres.antenne, montres.preecoute, sortie_montree) == (antenne, preecoute, sortie)


# ─── Seuil de blanc (https://github.com/dascritch/machincast/issues/146) ───


def _decibels(texte: str) -> float:
	return float(texte.replace(",", "."))


@given(parsers.re(r"les préférences seront réglées avec le seuil de blanc (?P<seuil>-?[\d,]+) dB"))
def seuil_regle(interface: Contexte, seuil: str) -> None:
	interface.seuil_regle = _decibels(seuil)


@then(parsers.re(r"les préférences ont montré le seuil de blanc (?P<seuil>-?[\d,]+) dB"))
def seuil_montre(interface: Contexte, seuil: str) -> None:
	assert interface.seuils_montres == [_decibels(seuil)]


@when(parsers.re(r"la fenêtre des préférences s'ouvre sur le seuil de blanc (?P<seuil>-?[\d,]+) dB"))
def ouvrir_sur_le_seuil(ouverte: Ouverte, parent: QWidget, seuil: str) -> None:
	tous = Reglages(Crossfades(), None, PREECOUTE_DES_TESTS, _decibels(seuil))
	ouverte.fenetre = FenetrePreferences(tous, "factice", parent)


@then(
	parsers.re(
		r"elle montre le seuil de blanc « (?P<texte>[^»]+) », réglable de (?P<minimum>-?[\d,]+)"
		r" à (?P<maximum>-?[\d,]+) dB"
	)
)
def seuil_affiche(ouverte: Ouverte, texte: str, minimum: str, maximum: str) -> None:
	champ = la_fenetre(ouverte).ui.seuil_blancs
	assert (champ.text(), champ.minimum(), champ.maximum()) == (texte, _decibels(minimum), _decibels(maximum))


@when(parsers.re(r"j'y saisis le seuil de blanc (?P<seuil>-?[\d,]+)"))
def saisir_le_seuil(ouverte: Ouverte, seuil: str) -> None:
	la_fenetre(ouverte).ui.seuil_blancs.setValue(_decibels(seuil))


@then(parsers.re(r"elle a donné le seuil de blanc (?P<seuil>-?[\d,]+) dB"))
def seuil_donne(ouverte: Ouverte, seuil: str) -> None:
	assert ouverte.donnes is not None
	assert ouverte.donnes.seuil_blancs == _decibels(seuil)


# ─── Voyant « Saturation » (https://github.com/dascritch/machincast/issues/191) ───


@given(parsers.re(r"les préférences seront réglées avec le voyant « Saturation » (?P<etat>affiché|caché)"))
def saturation_reglee(interface: Contexte, etat: str) -> None:
	interface.saturation_reglee = etat == "affiché"


@then(parsers.re(r"les préférences ont montré le voyant « Saturation » (?P<etat>affiché|caché)"))
def saturation_montree(interface: Contexte, etat: str) -> None:
	assert interface.saturations_montrees == [etat == "affiché"]


@then(parsers.re(r"le voyant « (?P<nom>Saturation|Silence) » de l'antenne est (?P<etat>affiché|caché) à l'accueil"))
def voyant_a_l_accueil(interface: Contexte, nom: str, etat: str) -> None:
	ui = fenetre(interface).accueil.ui
	voyant = {"Saturation": ui.voyant_saturation, "Silence": ui.voyant_silence}[nom]
	assert voyant.isHidden() is (etat == "caché")


@when(parsers.re(r"la fenêtre des préférences s'ouvre sur le voyant « Saturation » (?P<etat>affiché|caché)"))
def ouvrir_sur_la_saturation(ouverte: Ouverte, parent: QWidget, etat: str) -> None:
	tous = Reglages(Crossfades(), None, PREECOUTE_DES_TESTS, saturation=etat == "affiché")
	ouverte.fenetre = FenetrePreferences(tous, "factice", parent)


@then(parsers.re(r"elle montre la case « (?P<texte>[^»]+) », (?P<etat>cochée|décochée)"))
def case_de_saturation(ouverte: Ouverte, texte: str, etat: str) -> None:
	case = la_fenetre(ouverte).ui.saturation
	assert (case.text(), case.isChecked()) == (texte, etat == "cochée")


@when("j'y décoche la case du voyant « Saturation »")
def decocher_la_saturation(ouverte: Ouverte) -> None:
	la_fenetre(ouverte).ui.saturation.setChecked(False)


@then(parsers.re(r"elle a donné le voyant « Saturation » (?P<etat>affiché|caché)"))
def saturation_donnee(ouverte: Ouverte, etat: str) -> None:
	assert ouverte.donnes is not None
	assert ouverte.donnes.saturation is (etat == "affiché")


# ─── Suggestions au lancement (https://github.com/dascritch/machincast/issues/119) ───


@when(parsers.re(r"la fenêtre des préférences s'ouvre sur les suggestions au lancement (?P<etat>actives|éteintes)"))
def ouvrir_sur_les_suggestions(ouverte: Ouverte, parent: QWidget, etat: str) -> None:
	tous = Reglages(Crossfades(), None, PREECOUTE_DES_TESTS, suggestions=etat == "actives")
	ouverte.fenetre = FenetrePreferences(tous, "factice", parent)


@then(parsers.re(r"elle montre la case des suggestions « (?P<texte>[^»]+) », (?P<etat>cochée|décochée)"))
def case_des_suggestions(ouverte: Ouverte, texte: str, etat: str) -> None:
	case = la_fenetre(ouverte).ui.suggestions
	assert (case.text(), case.isChecked()) == (texte, etat == "cochée")


@when("j'y décoche la case des suggestions au lancement")
def decocher_les_suggestions(ouverte: Ouverte) -> None:
	la_fenetre(ouverte).ui.suggestions.setChecked(False)


@then(parsers.re(r"elle a donné les suggestions au lancement (?P<etat>actives|éteintes)"))
def suggestions_donnees(ouverte: Ouverte, etat: str) -> None:
	assert ouverte.donnes is not None
	assert ouverte.donnes.suggestions is (etat == "actives")


# ─── Icône de l'interface (https://github.com/dascritch/machincast/issues/111) ───


def _image(chemin: Path | None) -> QImage:
	"""L'icône, à 32 pixels : celle de MachinCast pour None."""
	return QIcon(str((chemin) or (ICONE))).pixmap(32).toImage()


def _icone(interface: Contexte, texte: str | None) -> Path | None:
	"""« de MachinCast » donne None, « « …/logo.png » » le chemin dans le répertoire du scénario."""
	if texte is None:
		return None
	return Path(interface.chemin_dans(texte))


ICONE_DU_SCENARIO = r"(?:de MachinCast|« (?P<chemin>[^»]+) »)"


@given(parsers.parse("une image PNG « {chemin} »"))
def image_png(interface: Contexte, chemin: str) -> None:
	image = QImage(32, 32, QImage.Format.Format_ARGB32)
	image.fill(QColor("#c0392b"))
	assert image.save(interface.chemin_dans(chemin), "PNG")


@given(parsers.parse("un fichier « {chemin} » qui n'est pas une image"))
def fausse_image(interface: Contexte, chemin: str) -> None:
	Path(interface.chemin_dans(chemin)).write_text("pas une image", encoding="utf-8")


@given(parsers.re(rf"les préférences seront réglées avec l'icône {ICONE_DU_SCENARIO}"))
def icone_reglee(interface: Contexte, chemin: str | None) -> None:
	interface.icone_reglee = (_icone(interface, chemin),)


@given(parsers.parse("le fichier de configuration de l'interface a l'icône « {chemin} »"))
def configuration_avec_icone(interface: Contexte, chemin: str) -> None:
	fichier = fichier_de_configuration(interface)
	document = tomlkit.parse(fichier.read_text(encoding="utf-8"))
	if "interface" not in document:
		document.add("interface", tomlkit.table())
	section = document["interface"]
	assert isinstance(section, tomlkit.items.Table)
	section["icone"] = interface.chemin_dans(chemin)
	fichier.write_text(tomlkit.dumps(document), encoding="utf-8")


def _lieu(lieu: str) -> Path:
	if lieu == "dans le menu des applications":
		return raccourci.dossier_du_menu() / raccourci.NOM
	dossier = raccourci.dossier_du_bureau()
	assert dossier is not None
	return dossier / raccourci.NOM


@given(parsers.re(r"le raccourci de MachinCast installé (?P<lieu>dans le menu des applications|sur le bureau)"))
def raccourci_installe(lieu: str) -> None:
	chemin = _lieu(lieu)
	chemin.parent.mkdir(parents=True, exist_ok=True)
	chemin.write_text(raccourci.rediger(), encoding="utf-8")
	chemin.chmod(0o755 if lieu == "sur le bureau" else 0o644)


def _icone_du_raccourci(chemin: Path) -> str:
	lignes = [ligne for ligne in chemin.read_text(encoding="utf-8").splitlines() if ligne.startswith("Icon=")]
	assert len(lignes) == 1, lignes
	return lignes[0].removeprefix("Icon=")


@then(parsers.re(rf"le raccourci du menu des applications a l'icône {ICONE_DU_SCENARIO}"))
def raccourci_du_menu(interface: Contexte, chemin: str | None) -> None:
	attendue = (_icone(interface, chemin)) or (ICONE)
	assert _icone_du_raccourci(_lieu("dans le menu des applications")) == str(attendue)


@then(parsers.re(rf"le raccourci du bureau a l'icône {ICONE_DU_SCENARIO}, et reste exécutable"))
def raccourci_du_bureau(interface: Contexte, chemin: str | None) -> None:
	fichier = _lieu("sur le bureau")
	assert _icone_du_raccourci(fichier) == str((_icone(interface, chemin)) or (ICONE))
	assert stat.S_IMODE(fichier.stat().st_mode) == 0o755


@then("il n'y a pas de raccourci de MachinCast sur le bureau")
def pas_de_raccourci_sur_le_bureau() -> None:
	assert not _lieu("sur le bureau").exists()


@then(parsers.re(rf"l'application a l'icône {ICONE_DU_SCENARIO}"))
def icone_de_l_application(interface: Contexte, chemin: str | None) -> None:
	application = QApplication.instance()
	assert isinstance(application, QApplication)
	assert application.windowIcon().pixmap(32).toImage() == _image(_icone(interface, chemin))


@then(parsers.re(rf"les préférences ont montré l'icône {ICONE_DU_SCENARIO}"))
def icone_montree(interface: Contexte, chemin: str | None) -> None:
	assert interface.icones_montrees == [_icone(interface, chemin)]


@then(parsers.parse("le fichier de configuration donne l'icône « {chemin} »"))
def icone_du_fichier(interface: Contexte, chemin: str) -> None:
	document = tomllib.loads(fichier_de_configuration(interface).read_text(encoding="utf-8"))
	assert document["interface"]["icone"] == interface.chemin_dans(chemin)


@then("le fichier de configuration n'a pas d'icône")
def sans_icone(interface: Contexte) -> None:
	document = tomllib.loads(fichier_de_configuration(interface).read_text(encoding="utf-8"))
	assert "icone" not in document.get("interface", {}), document


@then(parsers.re(r"la barre d'état (?P<sens>dit|ne dit pas) « (?P<texte>[^»]+) »"))
def barre_d_etat_dit(interface: Contexte, sens: str, texte: str) -> None:
	message = fenetre(interface).statusBar().currentMessage()
	assert (interface.chemin_dans(texte) in message) is (sens == "dit"), message


@when(parsers.re(rf"la fenêtre des préférences s'ouvre sur l'icône {ICONE_DU_SCENARIO}"))
def ouvrir_sur_l_icone(interface: Contexte, ouverte: Ouverte, parent: QWidget, chemin: str | None) -> None:
	tous = Reglages(Crossfades(), None, PREECOUTE_DES_TESTS, icone=_icone(interface, chemin))
	ouverte.fenetre = FenetrePreferences(tous, "factice", parent)


@then(parsers.re(rf"elle montre l'icône {ICONE_DU_SCENARIO}"))
def montre_l_icone(interface: Contexte, ouverte: Ouverte, chemin: str | None) -> None:
	ui = la_fenetre(ouverte).ui
	attendue = _icone(interface, chemin)
	texte = preferences.ICONE_PAR_DEFAUT
	if attendue is not None:
		texte = str(attendue)
	assert ui.icone_chemin.text() == texte
	assert ui.icone_apercu.pixmap().toImage() == QIcon(str((attendue) or (ICONE))).pixmap(48).toImage()


@then(parsers.re(r"son bouton « Icône de MachinCast » est (?P<etat>actif|inactif)"))
def bouton_par_defaut(ouverte: Ouverte, etat: str) -> None:
	assert la_fenetre(ouverte).ui.icone_par_defaut.isEnabled() is (etat == "actif")


@when(parsers.re(r"j'y (?:choisis l'image « (?P<chemin>[^»]+) »|renonce au choix d'une image)"))
def choisir_l_image(interface: Contexte, ouverte: Ouverte, monkeypatch: pytest.MonkeyPatch, chemin: str | None) -> None:
	monkeypatch.setattr(dialogues, "choisir_icone", lambda _parent: _icone(interface, chemin))
	la_fenetre(ouverte).ui.choisir_icone.click()


@when("j'y clique sur le bouton « Icône de MachinCast »")
def revenir_a_l_icone_par_defaut(ouverte: Ouverte) -> None:
	la_fenetre(ouverte).ui.icone_par_defaut.click()


@then(parsers.re(rf"elle a donné l'icône {ICONE_DU_SCENARIO}"))
def icone_donnee(interface: Contexte, ouverte: Ouverte, chemin: str | None) -> None:
	assert ouverte.donnes is not None
	assert ouverte.donnes.icone == _icone(interface, chemin)


@then(parsers.parse("elle signale « {texte} »"))
def signale(interface: Contexte, ouverte: Ouverte, texte: str) -> None:
	assert la_fenetre(ouverte).ui.icone_erreur.text() == interface.chemin_dans(texte)


# ─── Positions des fondus (https://github.com/dascritch/machincast/issues/234) ───


def _choix_de_position(ouverte: Ouverte, fondu: str) -> QComboBox:
	ui = la_fenetre(ouverte).ui
	return {"fade-in": ui.position_entree, "fade-out": ui.position_sortie}[fondu]


@then(
	parsers.re(
		r"le (?P<fondu>fade-in|fade-out) se propose (?P<textes>«.+») (?:au début détecté|à la fin détectée),"
		r" et « (?P<choisi>[^»]+) » est choisi"
	)
)
def positions_proposees(ouverte: Ouverte, fondu: str, textes: str, choisi: str) -> None:
	choix = _choix_de_position(ouverte, fondu)
	assert [choix.itemText(rang) for rang in range(choix.count())] == NOM.findall(textes)
	assert choix.currentText() == choisi


@when(parsers.parse("j'y choisis le fade-in « {entree} » et le fade-out « {sortie} »"))
def choisir_les_positions(ouverte: Ouverte, entree: str, sortie: str) -> None:
	for fondu, texte in (("fade-in", entree), ("fade-out", sortie)):
		choix = _choix_de_position(ouverte, fondu)
		rang = choix.findText(texte)
		assert rang >= 0, texte
		choix.setCurrentIndex(rang)


@then(parsers.parse("elle a donné les positions : fade-in « {entree} », fade-out « {sortie} »"))
def positions_donnees(ouverte: Ouverte, entree: str, sortie: str) -> None:
	assert ouverte.donnes is not None
	assert (ouverte.donnes.crossfades.entree, ouverte.donnes.crossfades.sortie) == (entree, sortie)


@then(
	parsers.parse(
		"la frise de démonstration montre le fade-in de {de_entree:d} à {a_entree:d} s, et le fade-out de"
		" {de_sortie:d} à {a_sortie:d} s"
	)
)
def frise_de_demonstration(ouverte: Ouverte, de_entree: int, a_entree: int, de_sortie: int, a_sortie: int) -> None:
	plan = la_fenetre(ouverte).demonstration.plan
	assert plan is not None
	entree, sortie = plan.fondus()
	assert (entree, sortie) == (
		pytest.approx((de_entree, a_entree)),
		pytest.approx((de_sortie, a_sortie)),
	), (entree, sortie)


@then("la frise de démonstration a sa forme d'onde, sans tête de lecture")
def forme_de_demonstration(ouverte: Ouverte) -> None:
	frise = la_fenetre(ouverte).demonstration
	assert (frise.forme is not None) and (frise.forme.finie) and (frise.forme.pics)
	assert frise.tete is None
	assert not frise.interactive


@given(parsers.parse("les positions des fondus seront réglées : fade-in « {entree} », fade-out « {sortie} »"))
def positions_reglees(interface: Contexte, entree: str, sortie: str) -> None:
	interface.preferences_reglees = dataclasses.replace(
		(interface.preferences_reglees) or (Crossfades()), entree=entree, sortie=sortie
	)


@then(
	parsers.parse(
		"le fichier de configuration donne les positions des fondus : fade-in « {entree} », fade-out « {sortie} »"
	)
)
def positions_du_fichier(interface: Contexte, entree: str, sortie: str) -> None:
	crossfades = charger(fichier_de_configuration(interface)).crossfades
	assert (crossfades.entree, crossfades.sortie) == (entree, sortie)
