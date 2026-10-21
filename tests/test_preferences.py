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
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QComboBox, QDialogButtonBox, QDoubleSpinBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import Crossfades, charger
from machincast.interface import __main__ as module_interface
from machincast.interface import application as module_application
from machincast.interface import dialogues, preferences
from machincast.interface.fenetre import FenetrePrincipale
from machincast.interface.fiche_banque import FicheBanque
from machincast.interface.fiche_sonore import FicheSonore
from machincast.interface.preferences import FenetrePreferences, Reglages
from machincast.interface.suggestions import Reponse
from tests.base_test import configuration_test
from tests.etapes_interface import Connexion, Contexte, fenetre, fichier_de_configuration, ouvrir_la_fenetre
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


@then(parsers.parse("elle s'intitule « {titre} », avec la page « {page} »"))
def titre_et_page(ouverte: Ouverte, titre: str, page: str) -> None:
	ui = la_fenetre(ouverte).ui
	pages = [ui.pages.tabText(rang) for rang in range(ui.pages.count())]
	assert (la_fenetre(ouverte).windowTitle(), pages[0]) == (titre, page)


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
