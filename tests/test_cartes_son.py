"""Scénarios du bloc des cartes son (https://github.com/dascritch/machincast/issues/339).

Le bloc s'ouvre hors de l'écran du poste, sur les périphériques du scénario (« les périphériques audio du poste »,
tests/etapes_interface.py). Le son de test joue sur une sortie factice, raccourci : aucun son ne part du poste.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QComboBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast import audio
from machincast.audio import SortieAudioIndisponible
from machincast.configuration import SortieAudio
from machincast.interface import cartes_son
from machincast.interface.cartes_son import CartesSon
from machincast.service import ABSENT, EtatDuService

scenarios("cartes_son.feature")

SERVICES = {
	"sans service de diffusion": ABSENT,
	"service de diffusion à l'arrêt": EtatDuService(installe=True, actif="inactive"),
	"service de diffusion en marche": EtatDuService(installe=True, actif="active"),
}
ATTENTE = 5000
"""Millisecondes laissées au son de test pour finir."""


@dataclass
class Bloc:
	cartes: CartesSon | None = None
	demandes: list[tuple[str, str | None]] = field(default_factory=list)


@pytest.fixture
def bloc() -> Bloc:
	return Bloc()


@pytest.fixture
def parent(qtbot: QtBot) -> Iterator[QWidget]:
	widget = QWidget()
	qtbot.addWidget(widget)
	yield widget


def ouvert(bloc: Bloc) -> CartesSon:
	assert bloc.cartes is not None
	return bloc.cartes


def _liste(texte: str) -> list[str]:
	return re.findall(r"« ([^»]+) »", texte)


# ─── Ouverture ─────────────────────────────────────────────


@when(
	parsers.re(
		r"le bloc des cartes son s'ouvre sur la sortie « (?P<sortie>[^»]+) »,"
		r" l'antenne (?:« (?P<antenne>[^»]+) »|non renseignée) et la pré-écoute « (?P<preecoute>[^»]+) »,"
		r" (?P<service>.+)"
	)
)
def ouvrir(
	bloc: Bloc, parent: QWidget, qtbot: QtBot, sortie: str, antenne: str | None, preecoute: str, service: str
) -> None:
	bloc.cartes = CartesSon(sortie, antenne, preecoute, SERVICES[service], parent)  # type: ignore[arg-type]
	parent.show()
	qtbot.waitExposed(parent)


# ─── Choix ─────────────────────────────────────────────────


def _choix(bloc: Bloc, nom: str) -> QComboBox:
	ui = ouvert(bloc).ui
	return {"l'antenne": ui.antenne, "la pré-écoute": ui.preecoute}[nom]


@then(parsers.re(r"son type de sortie est « (?P<type>[^»]+) », parmi (?P<types>«.+)"))
def type_de_sortie(bloc: Bloc, type: str, types: str) -> None:
	choix = ouvert(bloc).ui.sortie
	assert choix.currentText() == type
	assert [choix.itemText(indice) for indice in range(choix.count())] == _liste(types)


@then(parsers.re(r"son choix de (?P<nom>l'antenne|la pré-écoute) propose :"))
def propose(bloc: Bloc, nom: str, datatable: list[list[str]]) -> None:
	choix = _choix(bloc, nom)
	modele = choix.model()
	assert isinstance(modele, QStandardItemModel)
	montres = [
		[choix.itemText(indice), "active" if modele.item(indice).isEnabled() else "inactive"]
		for indice in range(choix.count())
	]
	assert montres == [[carte.strip(), etat.strip()] for carte, etat in datatable[1:]]


@when(parsers.re(r"j'y choisis pour (?P<nom>l'antenne|la pré-écoute) « (?P<texte>[^»]+) »"))
def choisir(bloc: Bloc, nom: str, texte: str) -> None:
	choix = _choix(bloc, nom)
	indice = choix.findText(texte)
	assert indice >= 0, texte
	choix.setCurrentIndex(indice)


@when(parsers.parse("j'y choisis le type de sortie « {texte} »"))
def choisir_le_type(bloc: Bloc, texte: str) -> None:
	choix = ouvert(bloc).ui.sortie
	indice = choix.findText(texte)
	assert indice >= 0, texte
	choix.setCurrentIndex(indice)


@then(
	parsers.re(
		r"il donne la sortie « (?P<sortie>[^»]+) », l'antenne (?:« (?P<antenne>[^»]+) »|non renseignée)"
		r" et la pré-écoute « (?P<preecoute>[^»]+) »"
	)
)
def donne(bloc: Bloc, sortie: str, antenne: str | None, preecoute: str) -> None:
	cartes = ouvert(bloc)
	assert (cartes.sortie_choisie(), cartes.antenne_choisie(), cartes.preecoute_choisie()) == (
		sortie,
		antenne,
		preecoute,
	)


@then(parsers.parse("dans son choix de l'antenne, « {texte} » a pour infobulle « {infobulle} »"))
def infobulle_de_la_ligne(bloc: Bloc, texte: str, infobulle: str) -> None:
	choix = ouvert(bloc).ui.antenne
	modele = choix.model()
	assert isinstance(modele, QStandardItemModel)
	assert modele.item(choix.findText(texte)).toolTip() == infobulle


# ─── Service de diffusion ──────────────────────────────────


@then(
	parsers.re(
		r"le choix de l'antenne, son bouton « Tester » et le type de sortie sont"
		r" (?P<etat>actifs|inactifs, avec l'infobulle « (?P<infobulle>[^»]+) »)"
	)
)
def antenne_verrouillee(bloc: Bloc, etat: str, infobulle: str | None) -> None:
	ui = ouvert(bloc).ui
	elements = (ui.antenne, ui.tester_antenne, ui.sortie)
	assert [element.isEnabled() for element in elements] == [etat == "actifs"] * 3
	if infobulle is not None:
		assert [element.toolTip() for element in elements] == [infobulle] * 3


@then("le choix de la pré-écoute et son bouton « Tester » sont actifs")
def preecoute_libre(bloc: Bloc) -> None:
	ui = ouvert(bloc).ui
	assert (ui.preecoute.isEnabled(), ui.tester_preecoute.isEnabled()) == (True, True)


# ─── Son de test ───────────────────────────────────────────


@when(
	parsers.parse("je construis le son de test de la sortie « {sortie} », carte « {carte} »"),
	target_fixture="pipeline",
)
def construire(sortie: str, carte: str) -> Iterator[audio.Gst.Pipeline]:
	pipeline = cartes_son.son_de_test(sortie, carte)  # type: ignore[arg-type]
	yield pipeline
	pipeline.set_state(audio.Gst.State.NULL)


@then("c'est une sinusoïde à 1000 Hz, à -3 dB, de 2 secondes")
def sinusoide(pipeline: audio.Gst.Pipeline) -> None:
	source = pipeline.get_by_name("source")
	assert source is not None
	assert source.get_property("wave").value_nick == "sine"
	assert source.get_property("freq") == 1000
	assert source.get_property("volume") == pytest.approx(0.708, abs=0.001)
	echantillons = source.get_property("num-buffers") * source.get_property("samplesperbuffer")
	assert echantillons / cartes_son.TAUX == pytest.approx(2.0)


@then(
	parsers.parse(
		"il joue sur l'élément « {fabrique} », carte « {carte} », présenté comme « {programme} », flux « {flux} »"
	)
)
def puits(pipeline: audio.Gst.Pipeline, fabrique: str, carte: str, programme: str, flux: str) -> None:
	element = pipeline.get_by_name("puits")
	assert element is not None
	usine = element.get_factory()
	assert (usine is not None) and (usine.get_name() == fabrique)
	assert element.get_property("target-object") == carte
	proprietes = element.get_property("stream-properties")
	assert (proprietes.get_string("application.name"), proprietes.get_string("media.name")) == (programme, flux)


@given("des sons de test de 0,2 seconde, sur une sortie factice")
def sons_factices(bloc: Bloc, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(cartes_son, "DUREE_DU_SON_DE_TEST", 0.2)

	def creer(sortie: SortieAudio, peripherique: str | None, presentation: audio.Presentation) -> audio.Gst.Element:
		bloc.demandes.append((sortie, peripherique))
		puits = audio.creer_sortie("factice", None, presentation=presentation)
		# Au rythme du temps réel, pour que le scénario voie le son en cours.
		puits.set_property("sync", True)
		return puits

	monkeypatch.setattr(cartes_son, "fabrique_de_sortie", creer)


@given("des sons de test sur une sortie qui ne peut pas être créée")
def sons_impossibles(monkeypatch: pytest.MonkeyPatch) -> None:
	def creer(_sortie: SortieAudio, _peripherique: str | None, presentation: audio.Presentation) -> audio.Gst.Element:
		raise SortieAudioIndisponible("sortie introuvable")

	monkeypatch.setattr(cartes_son, "fabrique_de_sortie", creer)


@when(parsers.re(r"je clique sur « Tester » de (?P<nom>l'antenne|la pré-écoute)"))
def cliquer_sur_tester(bloc: Bloc, nom: str) -> None:
	ui = ouvert(bloc).ui
	bouton = {"l'antenne": ui.tester_antenne, "la pré-écoute": ui.tester_preecoute}[nom]
	assert bouton.isEnabled()
	bouton.click()


@then(parsers.parse("le bloc dit « {texte} »"))
def dit(bloc: Bloc, texte: str) -> None:
	assert ouvert(bloc).texte() == texte


@then(parsers.parse("le bloc dit bientôt « {texte} »"))
def dit_bientot(bloc: Bloc, qtbot: QtBot, texte: str) -> None:
	qtbot.waitUntil(lambda: ouvert(bloc).texte() == texte, timeout=ATTENTE)


@then(parsers.re(r"ses boutons « Tester » sont (?P<etat>actifs|inactifs)"))
def boutons(bloc: Bloc, etat: str) -> None:
	ui = ouvert(bloc).ui
	assert (ui.tester_antenne.isEnabled(), ui.tester_preecoute.isEnabled()) == (etat == "actifs",) * 2


@then(parsers.parse("le son de test a été demandé sur la sortie « {sortie} », carte « {carte} »"))
def demande(bloc: Bloc, sortie: str, carte: str) -> None:
	assert bloc.demandes[-1] == (sortie, carte)


@then(parsers.parse("le bouton « Tester » de l'antenne est inactif, avec l'infobulle « {infobulle} »"))
def bouton_tester_inactif(bloc: Bloc, infobulle: str) -> None:
	bouton = ouvert(bloc).ui.tester_antenne
	assert (bouton.isEnabled(), bouton.toolTip()) == (False, infobulle)
