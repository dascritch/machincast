"""Scénarios du VU-mètre de la sortie d'antenne (https://github.com/dascritch/machincast/issues/24).

Les étapes de la fenêtre sont dans tests/etapes_interface.py, celles de la pré-écoute dans
tests/etapes_preecoute.py. Sur la sortie factice, le port de monitoring est un signal de test de GStreamer, que le
scénario choisit (moniteur.SIGNAL_FACTICE).
"""

import re

import pytest
from PySide6.QtCore import QRectF, Qt
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import Audio
from machincast.interface import moniteur
from machincast.interface.ecran_par_defaut import EcranParDefaut
from machincast.interface.moniteur import Moniteur, source_du_moniteur
from machincast.interface.vumetre import VuMetre
from tests.etapes_interface import Contexte, fenetre

scenarios("vumetre.feature")

DELAI = 5000
SIGNAUX = {
	"sinusoïde à -10 dB": "audiotestsrc is-live=true wave=sine volume=0.316",
	"silence": "audiotestsrc is-live=true wave=silence",
	"carré à 0 dB": "audiotestsrc is-live=true wave=square volume=1.0",
	"introuvable": "elementintrouvable",
	"bref": "audiotestsrc is-live=true num-buffers=10 wave=sine",
}
"""Les signaux de test du port de monitoring de la sortie factice."""


def accueil(interface: Contexte) -> EcranParDefaut:
	return fenetre(interface).accueil


class Pendule:
	"""Une horloge fictive, en secondes, pour le moniteur et le VU-mètre."""

	def __init__(self) -> None:
		self.instant = 0.0

	def __call__(self) -> float:
		return self.instant


def decibels(texte: str) -> list[float]:
	"""« -10, -1,1 » : un niveau par canal, à la virgule décimale."""
	return [float(valeur.replace(",", ".")) for valeur in texte.split(", ")]


def lignes(datatable: list[list[str]]) -> list[dict[str, str]]:
	entete, *reste = datatable
	return [dict(zip(entete, ligne, strict=True)) for ligne in reste]


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.re(r"le silence de l'antenne constaté après (?P<duree>une demi-seconde|5 secondes)"))
def silence_constate(monkeypatch: pytest.MonkeyPatch, duree: str) -> None:
	monkeypatch.setattr(moniteur, "DUREE_DU_SILENCE", {"une demi-seconde": 0.5, "5 secondes": 5.0}[duree])


@given(parsers.parse("le signal de test « {signal} » sur l'antenne factice"))
def signal_de_test(monkeypatch: pytest.MonkeyPatch, signal: str) -> None:
	monkeypatch.setattr(moniteur, "SIGNAL_FACTICE", SIGNAUX[signal])


@given("un moniteur de l'antenne, à l'horloge fictive", target_fixture="pendule")
def moniteur_fictif(qtbot: QtBot) -> tuple[Pendule, Moniteur]:
	pendule = Pendule()
	return pendule, Moniteur(None, horloge=pendule)


@given("un VU-mètre, à l'horloge fictive", target_fixture="pendule")
def vumetre_fictif(qtbot: QtBot) -> tuple[Pendule, VuMetre]:
	pendule = Pendule()
	vumetre = VuMetre(horloge=pendule)
	qtbot.addWidget(vumetre)
	return pendule, vumetre


@given("un nouvel essai du port de monitoring après une demi-seconde")
def reessai_court(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(moniteur, "REESSAI", 500)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le signal de test « {signal} » remplace celui de l'antenne factice"))
def retablir(monkeypatch: pytest.MonkeyPatch, signal: str) -> None:
	monkeypatch.setattr(moniteur, "SIGNAL_FACTICE", SIGNAUX[signal])


@when("je clique sur le VU-mètre de l'antenne")
def cliquer(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(accueil(interface).vumetre, Qt.MouseButton.LeftButton)


@when(
	parsers.parse("je construis le port de monitoring de la sortie « {sortie} », périphérique « {peripherique} »"),
	target_fixture="port",
)
def construire(sortie: str, peripherique: str) -> object:
	return source_du_moniteur(Audio(sortie, peripherique, "casque"))  # type: ignore[arg-type]


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le VU-mètre de l'antenne est intitulé « {titre} », avec l'infobulle « {infobulle} »"))
def intitule(interface: Contexte, titre: str, infobulle: str) -> None:
	ecran = accueil(interface)
	assert (ecran.ui.colonne_antenne.title(), ecran.vumetre.toolTip()) == (titre, infobulle)


@when(
	parsers.re(
		r"le VU-mètre de l'antenne montre bientôt (?P<nombre>\d+) canaux, entre (?P<bas>-?\d+) et (?P<haut>-?\d+) dB"
	)
)
@then(
	parsers.re(
		r"le VU-mètre de l'antenne montre bientôt (?P<nombre>\d+) canaux, entre (?P<bas>-?\d+) et (?P<haut>-?\d+) dB"
	)
)
def canaux(interface: Contexte, qtbot: QtBot, nombre: str, bas: str, haut: str) -> None:
	vumetre = accueil(interface).vumetre

	def montres() -> bool:
		niveaux = vumetre.niveaux
		return (len(niveaux) == int(nombre)) and (all(int(bas) <= niveau <= int(haut) for niveau in niveaux))

	qtbot.waitUntil(montres, timeout=DELAI)


@then("la crête de chaque canal est au moins au niveau du VU")
def cretes(interface: Contexte) -> None:
	vumetre = accueil(interface).vumetre
	assert all(crete >= niveau for crete, niveau in zip(vumetre.cretes, vumetre.niveaux, strict=True))


@then("le VU-mètre de l'antenne est disponible")
def disponible(interface: Contexte) -> None:
	ecran = accueil(interface)
	assert ecran.moniteur.indisponible is None
	assert (ecran.ui.etat_moniteur.text(), ecran.ui.etat_moniteur.isVisibleTo(ecran)) == ("", False)


@then(parsers.parse("le VU-mètre de l'antenne ne dit plus « {texte} »"))
def ne_dit_plus(interface: Contexte, texte: str) -> None:
	assert accueil(interface).ui.etat_moniteur.text() != texte


@then("le port de monitoring ne sera pas rouvert")
def pas_rouvert(interface: Contexte) -> None:
	assert not accueil(interface).moniteur.reessai_prevu()


@then("la colonne de l'antenne montre, de haut en bas : « Saturation », le VU-mètre, « Silence »")
def ordre_de_la_colonne(interface: Contexte) -> None:
	ui = accueil(interface).ui
	disposition = ui.disposition_antenne
	ordre = [disposition.itemAt(indice).widget() for indice in range(disposition.count())]
	assert ordre[:3] == [ui.voyant_saturation, ui.place_vumetre, ui.voyant_silence]


@then("ses voyants sont écrits plus petit que le titre de la colonne")
def voyants_petits(interface: Contexte) -> None:
	ui = accueil(interface).ui
	titre = ui.colonne_antenne.font().pointSizeF()
	assert all(lampe.font().pointSizeF() < titre for lampe in (ui.voyant_silence, ui.voyant_saturation))


@then(parsers.parse("le voyant « {nom} » de l'antenne reste éteint une seconde"))
def reste_eteint(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	lampe = voyant(interface, nom)
	for _fois in range(10):
		qtbot.wait(100)
		assert not lampe.property("allume")  # type: ignore[attr-defined]


@then("ses voyants suivent ses relevés du VU et de la crête de chaque canal :")
def voyants_des_releves(pendule: tuple[Pendule, Moniteur], datatable: list[list[str]]) -> None:
	horloge, moniteur = pendule
	for ligne in lignes(datatable):
		horloge.instant = decibels(ligne["instant"])[0]
		moniteur.noter(decibels(ligne["vu"]), decibels(ligne["crete"]))
		attendu = (ligne["silence"] == "oui", ligne["saturation"] == "oui")
		assert (moniteur.silence, moniteur.saturation) == attendu, ligne


@then("son repère suit le VU et la crête de chaque canal qu'il montre :")
def repere(pendule: tuple[Pendule, VuMetre], datatable: list[list[str]]) -> None:
	horloge, vumetre = pendule
	for ligne in lignes(datatable):
		horloge.instant = decibels(ligne["instant"])[0]
		vumetre.montrer(decibels(ligne["vu"]), decibels(ligne["crete"]))
		assert vumetre.cretes == decibels(ligne["crete"]), ligne
		assert [gardee for gardee, _depuis in vumetre.maintenues] == decibels(ligne["repere"]), ligne


@then("les voyants de l'antenne sont éteints")
def eteints(interface: Contexte) -> None:
	ui = accueil(interface).ui
	assert [bool(ui.voyant_silence.property("allume")), bool(ui.voyant_saturation.property("allume"))] == [False] * 2


def voyant(interface: Contexte, nom: str) -> object:
	ui = accueil(interface).ui
	return {"Silence": ui.voyant_silence, "Saturation": ui.voyant_saturation}[nom]


@then(parsers.parse("le voyant « {nom} » de l'antenne s'allume bientôt"))
def s_allume(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	lampe = voyant(interface, nom)
	qtbot.waitUntil(lambda: bool(lampe.property("allume")), timeout=DELAI)  # type: ignore[attr-defined]


@then(parsers.parse("le voyant « {nom} » de l'antenne est éteint"))
def est_eteint(interface: Contexte, nom: str) -> None:
	assert not voyant(interface, nom).property("allume")  # type: ignore[attr-defined]


@then(parsers.parse("le VU-mètre de l'antenne est indisponible : « {texte} »"))
def indisponible(interface: Contexte, texte: str) -> None:
	ecran = accueil(interface)
	assert ecran.ui.etat_moniteur.text() == texte
	assert ecran.ui.etat_moniteur.isVisibleTo(ecran)
	assert ecran.vumetre.niveaux == []


@then(parsers.parse("le VU-mètre de l'antenne est bientôt indisponible, avec une erreur qui commence par « {debut} »"))
def indisponible_bientot(interface: Contexte, qtbot: QtBot, debut: str) -> None:
	etiquette = accueil(interface).ui.etat_moniteur
	qtbot.waitUntil(lambda: etiquette.text().startswith(debut), timeout=DELAI)


@then("l'accueil ne capture rien")
def ne_capture_rien(interface: Contexte) -> None:
	moniteur = accueil(interface).moniteur
	assert (moniteur.actif(), moniteur.niveaux, moniteur.cretes) == (False, [], [])


@then(parsers.re(r"c'est l'élément « (?P<fabrique>[^»]+) », avec (?P<proprietes>.+)"))
def element(port: object, fabrique: str, proprietes: str) -> None:
	assert hasattr(port, "get_factory")
	assert port.get_factory().get_name() == fabrique
	for cle, valeur in re.findall(r"([\w-]+) « ([^»]+) »", proprietes):
		if cle == "stream-properties":
			champ, attendu = valeur.split("=")
			assert port.get_property(cle).get_value(champ) == (attendu == "true")  # type: ignore[attr-defined]
			continue
		assert port.get_property(cle) == valeur  # type: ignore[attr-defined]


@then("il n'y a pas de fenêtre de pré-écoute")
def sans_preecoute(interface: Contexte) -> None:
	assert fenetre(interface).preecoute is None


@when("l'accueil rouvre le port de monitoring de la même antenne", target_fixture="capture_precedente")
def rouvrir(interface: Contexte) -> object:
	ecran = accueil(interface)
	precedente = ecran.moniteur._pipeline
	assert precedente is not None
	ecran.changer_d_antenne(ecran.moniteur.audio)
	return precedente


@then("la capture précédente de l'antenne est arrêtée")
def precedente_arretee(capture_precedente: object) -> None:
	_retour, etat, _attente = capture_precedente.get_state(0)  # type: ignore[attr-defined]
	assert etat.value_nick == "null"


# ─── Échelle ───────────────────────────────────────────────


@given(
	parsers.re(r"un VU-mètre (?P<sens>vertical|couché) de (?P<largeur>\d+) × (?P<hauteur>\d+) pixels"),
	target_fixture="vumetre_seul",
)
def vumetre_de_taille(qtbot: QtBot, sens: str, largeur: str, hauteur: str) -> VuMetre:
	vumetre = VuMetre(vertical=sens == "vertical")
	qtbot.addWidget(vumetre)
	vumetre.setFixedSize(int(largeur), int(hauteur))
	vumetre.montrer([-20.0, -20.0])
	return vumetre


@then(parsers.parse("son échelle porte les nombres « {nombres} »"))
def nombres_de_l_echelle(vumetre_seul: VuMetre, nombres: str) -> None:
	assert [texte for texte, _cadre in vumetre_seul.etiquettes()] == nombres.split(", ")


def sans_chevauchement(vumetre: VuMetre) -> list[tuple[str, QRectF]]:
	etiquettes = vumetre.etiquettes()
	for indice, (_texte, cadre) in enumerate(etiquettes):
		assert all(not cadre.intersects(autre) for _t, autre in etiquettes[indice + 1 :]), etiquettes
		assert vumetre.rect().toRectF().contains(cadre), (cadre, vumetre.rect())
	return etiquettes


@then("de gauche à droite, le VU-mètre de l'antenne montre le canal « G », l'échelle, le canal « D »")
def canaux_separes(interface: Contexte) -> None:
	vumetre = accueil(interface).vumetre
	disposition = vumetre.disposition()
	gauche, droite = disposition.canaux
	assert gauche.right() < disposition.echelle.left() < disposition.echelle.right() < droite.left()
	assert [nom for nom, _cadre in disposition.noms] == ["G", "D"]
	assert [cadre.center().x() for _nom, cadre in disposition.noms] == [gauche.center().x(), droite.center().x()]
	assert all(cadre.top() >= gauche.bottom() for _nom, cadre in disposition.noms)


@then("l'échelle du VU-mètre de l'antenne va de 0 dB en haut à -60 dB en bas, sans nombres qui se chevauchent")
def echelle_verticale(interface: Contexte) -> None:
	vumetre = accueil(interface).vumetre
	etiquettes = sans_chevauchement(vumetre)
	canal = vumetre.disposition().canaux[0]
	assert (etiquettes[0][0], etiquettes[-1][0]) == ("0", "-60")
	assert abs(etiquettes[0][1].center().y() - canal.top()) <= 1
	assert abs(etiquettes[-1][1].center().y() - canal.bottom()) <= 1
	hauts = [cadre.center().y() for _texte, cadre in etiquettes]
	assert hauts == sorted(hauts)


@then(
	"l'échelle du VU-mètre de la pré-écoute va de -60 dB à gauche à 0 dB à droite, sous ses canaux, "
	"sans nombres qui se chevauchent"
)
def echelle_couchee(interface: Contexte) -> None:
	preecoute = fenetre(interface).preecoute
	assert preecoute is not None
	vumetre = preecoute.vumetre
	etiquettes = sans_chevauchement(vumetre)
	disposition = vumetre.disposition()
	canal = disposition.canaux[0]
	assert (etiquettes[0][0], etiquettes[-1][0]) == ("0", "-60")
	assert abs(etiquettes[0][1].center().x() - canal.right()) <= 1
	assert abs(etiquettes[-1][1].center().x() - canal.left()) <= 1
	assert disposition.echelle.top() >= max(cadre.bottom() for cadre in disposition.canaux)
	assert all(cadre.top() >= disposition.echelle.top() for _texte, cadre in etiquettes)
