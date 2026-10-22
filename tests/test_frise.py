"""Scénarios de la frise de la pré-écoute d'un fichier (https://github.com/dascritch/machincast/issues/224).

La frise s'essaie seule, hors de la fenêtre de pré-écoute : un plan donné par le scénario, sans base, et pour la forme
d'onde, un fichier de test décodé par GStreamer. Ses positions demandées sont notées.
"""

import re
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtWidgets import QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import Crossfades
from machincast.interface.frise import FormeDOnde, Frise, Plan, plan_du_sonore
from tests.sons import FICHIERS_SONORES

scenarios("frise.feature")

DELAI = 5000
"""Millisecondes laissées à GStreamer pour ce qui arrive « bientôt »."""


def secondes(texte: str) -> float:
	return float(texte.replace(",", ".").removesuffix(" s"))


def facultative(texte: str) -> timedelta | None:
	"""« 0,5 s », ou « aucun » : pas de blanc détecté de ce côté, NULL en base."""
	if texte == "aucun":
		return None
	return timedelta(seconds=secondes(texte))


@dataclass
class Essai:
	parent: QWidget
	plan: Plan | None = None
	frise: Frise | None = None
	demandees: list[float] = field(default_factory=list)
	forme: FormeDOnde | None = None
	en_cours_au_retour: bool = False
	souris: int = 0
	"""Où la souris est, en points depuis la gauche de la frise."""
	"""Le calcul n'était pas fini quand demarrer a rendu la main."""

	def la_frise(self) -> Frise:
		if self.frise is None:
			assert self.plan is not None
			self.frise = Frise(self.parent)
			self.frise.resize(400, 72)
			self.frise.montrer(self.plan, self.plan.duree)
			self.frise.placee.connect(self.demandees.append)
		return self.frise


@pytest.fixture
def essai(qtbot: QtBot) -> Essai:
	parent = QWidget()
	qtbot.addWidget(parent)
	return Essai(parent)


# ─── Étant donné ───────────────────────────────────────────


@given(
	parsers.re(
		r"un fichier de (?P<duree>[\d,]+) s, aux blancs de (?P<debut>[\d,]+ s|aucun) au début"
		r" et (?P<fin>[\d,]+ s|aucun) à la fin, (?P<retires>retirés|joués) à l'antenne, (?P<crossfades>.+)"
	)
)
def fichier(essai: Essai, duree: str, debut: str, fin: str, retires: str, crossfades: str) -> None:
	defauts = Crossfades()
	debut_du_sonore: timedelta | None = timedelta(0)
	fin_du_sonore: timedelta | None = timedelta(0)
	reglage = re.fullmatch(r"aux crossfades de (?P<cd>[\d,]+) s au début et (?P<cf>[\d,]+) s à la fin", crossfades)
	if reglage is not None:
		debut_du_sonore = timedelta(seconds=secondes(reglage["cd"]))
		fin_du_sonore = timedelta(seconds=secondes(reglage["cf"]))
	defaut = re.fullmatch(
		r"aux crossfades non paramétrés, par défaut de (?P<cd>[\d,]+) s au début et absent à la fin", crossfades
	)
	if defaut is not None:
		debut_du_sonore, fin_du_sonore = None, None
		defauts = Crossfades(debut=timedelta(seconds=secondes(defaut["cd"])))
	assert (crossfades == "sans crossfade") or (reglage is not None) or (defaut is not None), crossfades
	essai.plan = plan_du_sonore(
		timedelta(seconds=secondes(duree)),
		facultative(debut),
		facultative(fin),
		retires == "retirés",
		debut_du_sonore,
		fin_du_sonore,
		defauts,
		audite=True,
	)


@given(parsers.parse("un fichier de {duree} s jamais audité, sans crossfade"))
def jamais_audite(essai: Essai, duree: str) -> None:
	essai.plan = plan_du_sonore(
		timedelta(seconds=secondes(duree)), None, None, False, timedelta(0), timedelta(0), Crossfades(), audite=False
	)


@given(parsers.parse("la frise large de {largeur:d} points"))
def largeur(essai: Essai, largeur: int) -> None:
	essai.la_frise().resize(largeur, 72)


@given(parsers.parse("la tête de lecture de la frise à {position} secondes"))
def tete(essai: Essai, position: str) -> None:
	essai.la_frise().placer_la_tete(secondes(position))


@given(parsers.parse("la forme d'onde du fichier de test « {fichier} », de {duree:d} secondes, en cours de calcul"))
def forme_en_cours(essai: Essai, fichier: str, duree: int) -> None:
	essai.forme = FormeDOnde(FICHIERS_SONORES / fichier, float(duree))
	essai.forme.demarrer()
	essai.en_cours_au_retour = not essai.forme.finie


@given("la forme d'onde d'un fichier qui n'est pas un sonore, en cours de calcul")
def forme_illisible(essai: Essai, tmp_path: Path) -> None:
	faux = tmp_path / "faux.flac"
	faux.write_text("Ceci n'est pas un sonore.\n" * 200, encoding="utf-8")
	essai.forme = FormeDOnde(faux, 2.0)
	essai.forme.demarrer()


# ─── Quand ─────────────────────────────────────────────────


def _point(frise: Frise, x: int) -> QPoint:
	return QPoint(x, frise.height() // 2)


@when(parsers.parse("je clique sur la frise à {x:d} points"))
def cliquer(essai: Essai, qtbot: QtBot, x: int) -> None:
	frise = essai.la_frise()
	qtbot.mouseClick(frise, Qt.MouseButton.LeftButton, pos=_point(frise, x))


@when(parsers.parse("j'appuie sur la frise à {depart:d} points, puis glisse jusqu'à {arrivee:d} points"))
def glisser(essai: Essai, qtbot: QtBot, depart: int, arrivee: int) -> None:
	frise = essai.la_frise()
	qtbot.mousePress(frise, Qt.MouseButton.LeftButton, pos=_point(frise, depart))
	qtbot.mouseMove(frise, _point(frise, arrivee))
	essai.souris = arrivee


@when("je relâche la frise")
def relacher(essai: Essai, qtbot: QtBot) -> None:
	frise = essai.la_frise()
	qtbot.mouseRelease(frise, Qt.MouseButton.LeftButton, pos=_point(frise, essai.souris))


@when(parsers.re(r"je tape la flèche (?P<sens>droite|gauche) sur la frise"))
def fleche(essai: Essai, qtbot: QtBot, sens: str) -> None:
	touche = {"droite": Qt.Key.Key_Right, "gauche": Qt.Key.Key_Left}[sens]
	qtbot.keyClick(essai.la_frise(), touche)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("la frise joue le fichier de {de} à {a} seconde"))
def partie(essai: Essai, de: str, a: str) -> None:
	assert essai.plan is not None
	assert essai.plan.partie() == pytest.approx((secondes(de), secondes(a)))


@then(parsers.parse("la frise résume « {texte} »"))
def resume(essai: Essai, texte: str) -> None:
	assert essai.plan is not None
	assert essai.plan.resume() == texte


@then("la frise ne montre aucune zone")
def aucune_zone(essai: Essai) -> None:
	assert essai.plan is not None
	assert essai.plan.zones() == []


@then("la frise montre les zones :")
def zones(essai: Essai, datatable: list[list[str]]) -> None:
	assert essai.plan is not None
	lues = [
		[
			zone.nom,
			f"{zone.debut:.2f}".replace(".", ","),
			f"{zone.fin:.2f}".replace(".", ","),
			zone.hachures,
			zone.infobulle,
		]
		for zone in essai.plan.zones()
	]
	assert lues == [[cellule.strip() for cellule in rangee] for rangee in datatable[1:]]


@then(parsers.parse("l'infobulle de la frise à {x:d} points est « {texte} »"))
def infobulle(essai: Essai, x: int, texte: str) -> None:
	assert essai.la_frise().infobulle_a(x) == texte


@then(parsers.parse("« Début joué » place la lecture à {debut} seconde, et « Fin jouée » à {fin} seconde"))
def reperes(essai: Essai, debut: str, fin: str) -> None:
	assert essai.plan is not None
	assert essai.plan.repere_de_debut() == pytest.approx(secondes(debut))
	assert essai.plan.repere_de_fin() == pytest.approx(secondes(fin))


@then(parsers.parse("à {position} seconde, le volume de l'écoute comme à l'antenne est de {volume:d} %"))
def volume(essai: Essai, position: str, volume: int) -> None:
	assert essai.plan is not None
	assert essai.plan.volume(secondes(position)) == pytest.approx(volume / 100)


@then(parsers.re(r"la frise a demandé la position (?P<position>[\d,]+) secondes?"))
def demandee(essai: Essai, position: str) -> None:
	assert essai.demandees, "aucune position demandée"
	assert essai.demandees[-1] == pytest.approx(secondes(position), abs=0.01)


@then("la frise n'a demandé aucune position")
def rien_demande(essai: Essai) -> None:
	assert essai.demandees == []


@then(parsers.parse("la tête de lecture de la frise est à {position} seconde"))
def tete_a(essai: Essai, position: str) -> None:
	tete = essai.la_frise().tete
	assert tete is not None
	assert tete == pytest.approx(secondes(position), abs=0.01)


@then("l'interface a rendu la main avant la fin du calcul")
def rendu_la_main(essai: Essai) -> None:
	assert essai.en_cours_au_retour


def _relever_jusqu_a(qtbot: QtBot, forme: FormeDOnde, condition: str) -> None:
	def atteint() -> bool:
		forme.relever()
		return bool(getattr(forme, condition))

	qtbot.waitUntil(atteint, timeout=DELAI)


@given("la forme d'onde est bientôt complète")
@then("la forme d'onde est bientôt complète")
def complete(essai: Essai, qtbot: QtBot) -> None:
	assert essai.forme is not None
	_relever_jusqu_a(qtbot, essai.forme, "finie")
	assert essai.forme.erreur is None


@then(parsers.parse("la forme d'onde est silencieuse de {de} à {a} seconde, et de {de_2} à {a_2} secondes"))
def silencieuse(essai: Essai, de: str, a: str, de_2: str, a_2: str) -> None:
	assert essai.forme is not None
	for debut, fin in ((de, a), (de_2, a_2)):
		amplitudes = essai.forme.amplitudes(secondes(debut), secondes(fin))
		assert (amplitudes) and (max(amplitudes) < 0.01), amplitudes


@then(parsers.parse("la forme d'onde est sonore de {de} à {a} seconde, à mi-hauteur"))
def sonore(essai: Essai, de: str, a: str) -> None:
	assert essai.forme is not None
	amplitudes = essai.forme.amplitudes(secondes(de), secondes(a))
	assert (amplitudes) and (all(0.4 <= amplitude <= 0.6 for amplitude in amplitudes)), amplitudes


@then("la forme d'onde est bientôt indisponible")
def indisponible(essai: Essai, qtbot: QtBot) -> None:
	assert essai.forme is not None
	_relever_jusqu_a(qtbot, essai.forme, "erreur")


@then(parsers.parse("la frise de cette forme d'onde dit « {debut} » suivi de l'erreur de GStreamer"))
def remarque(essai: Essai, debut: str) -> None:
	assert essai.forme is not None
	frise = Frise(essai.parent)
	frise.montrer(None, 2.0)
	frise.montrer_la_forme(essai.forme)
	texte = frise.remarque()
	assert texte.startswith(f"{debut} "), texte
	assert texte != f"{debut} ", texte
	# Le calcul s'arrête sur l'erreur : rien ne reste en cours.
	assert essai.forme.finie


@then(
	parsers.parse(
		"dessinée sur une frise de {largeur:d} points, la forme d'onde couvre chaque point de {de} à {a} seconde,"
		" sans trou"
	)
)
def sans_trou(essai: Essai, largeur: int, de: str, a: str) -> None:
	"""Des mesures plus larges qu'un point : chacune remplit tous les points qu'elle couvre."""
	assert essai.forme is not None
	frise = Frise(essai.parent)
	frise.resize(largeur, 72)
	frise.montrer(None, 2.0)
	frise.montrer_la_forme(essai.forme)
	colonnes = frise.colonnes()
	gauche, droite = round(frise.secondes_vers_x(secondes(de))), round(frise.secondes_vers_x(secondes(a)))
	assert all(hauteur > 0.4 for hauteur in colonnes[gauche:droite]), colonnes[gauche:droite]


@then("la frise de cette forme d'onde se dessine pareil, active ou inactive")
def pareil(essai: Essai) -> None:
	"""Inactive, à l'arrêt, la frise ne se grise pas : sa forme d'onde, ses blancs et ses fondus gardent leurs
	couleurs."""
	assert essai.forme is not None
	frise = Frise(essai.parent)
	frise.resize(400, 72)
	frise.montrer(
		plan_du_sonore(
			timedelta(seconds=2),
			timedelta(seconds=0.5),
			timedelta(seconds=0.5),
			True,
			timedelta(seconds=0.2),
			timedelta(seconds=0.3),
			Crossfades(),
			audite=True,
		),
		2.0,
	)
	frise.montrer_la_forme(essai.forme)
	active = frise.grab().toImage()
	frise.setEnabled(False)
	inactive = frise.grab().toImage()
	assert active == inactive


@when(parsers.parse("la frise a pour légende « {texte} »"))
def legende(essai: Essai, texte: str) -> None:
	essai.la_frise().montrer_la_legende(texte)


@then("la légende de la frise est centrée, sur un fond qui l'entoure")
def legende_centree(essai: Essai) -> None:
	"""Calculée à part du dessin (https://github.com/dascritch/machincast/issues/230) : le fond, centré sur la frise,
	contient le texte, et tient dans la frise."""
	frise = essai.la_frise()
	fond = frise.fond_de_la_legende()
	assert fond is not None
	centre = QRectF(frise.rect()).center()
	assert abs(fond.center().x() - centre.x()) <= 1, (fond, centre)
	assert abs(fond.center().y() - centre.y()) <= 1, (fond, centre)
	texte = frise.fontMetrics().boundingRect(frise.legende)
	assert (fond.width() > texte.width()) and (fond.height() > texte.height()), (fond, texte)
	assert QRectF(frise.rect()).contains(fond), (fond, frise.rect())
