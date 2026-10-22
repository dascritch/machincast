"""Frise de la pré-écoute d'un fichier (https://github.com/dascritch/machincast/issues/224, spec § 8.3).

La frise remplace la barre de position de la pré-écoute d'un fichier. Elle s'étend sur toute la durée du fichier :

- Plan : ce que l'antenne fera du fichier, d'après la base. Ses blancs détectés (debut_detecte, fin_detectee,
  https://github.com/dascritch/machincast/issues/146), retirés s'il active la détection ; la partie jouée, qui suit la
  règle de la diffusion (machincast.lecture.diffusion.rognage) ; ses crossfades, posés sur la partie jouée, ceux des
  préférences pour un crossfade non paramétré (machincast.lecture.diffusion.crossfade, sans banque), et le volume de
  l'écoute comme à l'antenne, le long de l'enveloppe de la diffusion (machincast.lecture.moteur.enveloppe). La
  pré-écoute ne connaît pas la banque par laquelle passera le sonore : ses règles n'y figurent pas.
- FormeDOnde : la forme d'onde, calculée en tâche de fond par un pipeline GStreamer à part (uridecodebin, level,
  fakesink sans synchronisation : aussi vite que le décodage). Le minuteur de la pré-écoute relève son bus : rien ne
  bloque l'interface, et la forme apparaît au fil du décodage. Le fichier n'est que lu.
- Frise : le dessin. La forme d'onde, les blancs hachurés (hachures pleines s'ils sont retirés à l'antenne, pâles s'ils
  y sont joués), les fondus en rampes, la tête de lecture. Un clic, ou un glissement relâché, demande une position
  (placee) ; au clavier, les flèches déplacent d'une seconde. L'infobulle nomme la zone sous la souris, ou l'instant.
"""

import math
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Literal

import gi

gi.require_version("Gst", "1.0")
import psycopg  # noqa: E402
from gi.repository import Gst  # noqa: E402
from psycopg.rows import TupleRow  # noqa: E402
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
	QBrush,
	QColor,
	QHelpEvent,
	QKeyEvent,
	QMouseEvent,
	QPainter,
	QPaintEvent,
	QPalette,
	QPen,
	QPolygonF,
)
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget  # noqa: E402

from machincast.configuration import Crossfades  # noqa: E402
from machincast.lecture.diffusion import crossfade, rognage  # noqa: E402
from machincast.lecture.moteur import enveloppe  # noqa: E402

APPROCHE = 5.0
"""Secondes avant le fondu de sortie où « Fin jouée » place la lecture : de quoi entendre l'enchaînement arriver."""
PICS = 1500
"""Nombre de mesures de la forme d'onde sur tout le fichier : bien plus que de points sur la largeur de la frise."""
PAS_MINIMAL = 0.01
"""Secondes de la plus courte mesure de la forme d'onde, celle des fichiers courts."""
PAS_SANS_DUREE = 0.05
"""Secondes d'une mesure, quand la durée du fichier n'est pas connue."""
HAUTEUR = 72
"""Points de la frise en hauteur."""
INDISPONIBLE = "Forme d'onde indisponible :"
Hachures = Literal["pleines", "pâles", "aucune"]


def secondes(valeur: float) -> str:
	"""« 0,50 s »."""
	return f"{valeur:.2f} s".replace(".", ",")


def instant(valeur: float) -> str:
	"""« 0:01,50 », ou « 1:02:03,25 » au-delà d'une heure : au centième de seconde."""
	centiemes = round(max(0.0, valeur) * 100)
	entieres, reste = divmod(centiemes, 100)
	heures, entieres = divmod(entieres, 3600)
	minutes, unites = divmod(entieres, 60)
	if heures > 0:
		return f"{heures}:{minutes:02d}:{unites:02d},{reste:02d}"
	return f"{minutes}:{unites:02d},{reste:02d}"


@dataclass(frozen=True)
class Zone:
	"""Une zone de la frise, en secondes du fichier."""

	nom: str
	debut: float
	fin: float
	hachures: Hachures
	infobulle: str


@dataclass(frozen=True)
class Plan:
	"""Ce que l'antenne fera du fichier : ses blancs, sa partie jouée, ses crossfades. Durées en secondes."""

	duree: float
	blanc_debut: float | None = None
	"""Blanc détecté au début ; None : aucun de ce côté."""
	blanc_fin: float | None = None
	"""Blanc détecté à la fin, compté depuis la fin du fichier ; None : aucun de ce côté."""
	blancs_retires: bool = False
	"""Le sonore active la détection de blanc : ses blancs ne sont pas joués."""
	crossfade_debut: float = 0.0
	crossfade_fin: float = 0.0
	origine_debut: str | None = None
	"""D'où vient le crossfade de début, quand ce n'est pas du sonore : « défaut », les préférences, ou la banque
	(« imposé par la banque », « de la banque »). None : celui du sonore, ou aucun."""
	origine_fin: str | None = None
	audite: bool = True
	"""Un audit complet a mesuré ses blancs (audite_le)."""

	def _rognage(self) -> tuple[float, float | None]:
		def duree(valeur: float | None) -> timedelta | None:
			if valeur is None:
				return None
			return timedelta(seconds=valeur)

		jouee, decalage = rognage(timedelta(seconds=self.duree), duree(self.blanc_debut), duree(self.blanc_fin))
		if decalage is None:
			return jouee.total_seconds(), None
		return jouee.total_seconds(), decalage.total_seconds()

	def rogne(self) -> bool:
		"""Les blancs sont retirés à l'antenne : le sonore les active, et ils laissent quelque chose du fichier."""
		return (self.blancs_retires) and (self._rognage()[1] is not None)

	def partie(self) -> tuple[float, float]:
		"""Début et fin de la partie jouée à l'antenne, en secondes du fichier."""
		jouee, decalage = self._rognage()
		if (not self.blancs_retires) or (decalage is None):
			return 0.0, self.duree
		return decalage, decalage + jouee

	def _points(self) -> list[tuple[timedelta, float]]:
		de, a = self.partie()
		return enveloppe(
			timedelta(seconds=a - de), timedelta(seconds=self.crossfade_debut), timedelta(seconds=self.crossfade_fin)
		)

	def fondus(self) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
		"""Les fondus d'entrée et de sortie, en secondes du fichier, comme l'enveloppe de la diffusion les place ;
		None sans crossfade de ce côté."""
		de, _a = self.partie()
		points = [(de + moment.total_seconds(), volume) for moment, volume in self._points()]
		entree = None
		if self.crossfade_debut > 0:
			entree = (points[0][0], points[1][0])
		sortie = None
		if self.crossfade_fin > 0:
			sortie = (points[-2][0], points[-1][0])
		return entree, sortie

	def zones(self) -> list[Zone]:
		"""Les blancs et les fondus, dans l'ordre du fichier : blanc de début, fondus, blanc de fin."""
		hachures: Hachures = "pâles"
		sort = "joué à l'antenne"
		if self.rogne():
			hachures, sort = "pleines", "retiré à l'antenne"
		zones: list[Zone] = []
		if (self.blanc_debut is not None) and (self.blanc_debut > 0):
			texte = f"Blanc de début : {secondes(self.blanc_debut)}, {sort}"
			zones.append(Zone("blanc de début", 0.0, self.blanc_debut, hachures, texte))
		entree, sortie = self.fondus()
		if entree is not None:
			texte = (
				f"Crossfade de début : {secondes(self.crossfade_debut)}{_origine(self.origine_debut)},"
				" montée si le sonore précédent a un crossfade de fin"
			)
			zones.append(Zone("fondu d'entrée", entree[0], entree[1], "aucune", texte))
		if sortie is not None:
			texte = f"Crossfade de fin : {secondes(self.crossfade_fin)}{_origine(self.origine_fin)}"
			zones.append(Zone("fondu de sortie", sortie[0], sortie[1], "aucune", texte))
		if (self.blanc_fin is not None) and (self.blanc_fin > 0):
			texte = f"Blanc de fin : {secondes(self.blanc_fin)}, {sort}"
			zones.append(Zone("blanc de fin", self.duree - self.blanc_fin, self.duree, hachures, texte))
		return zones

	def resume(self) -> str:
		"""« Joué à l'antenne : 0:00,50 → 0:01,50 (0:01,00) », et si ses blancs n'ont jamais été mesurés, le dire."""
		de, a = self.partie()
		texte = f"Joué à l'antenne : {instant(de)} → {instant(a)} ({instant(a - de)})"
		if not self.audite:
			texte = f"{texte} · blancs jamais mesurés"
		return texte

	def repere_de_debut(self) -> float:
		"""Où « Début joué » place la lecture : au début de la partie jouée."""
		return self.partie()[0]

	def repere_de_fin(self) -> float:
		"""Où « Fin jouée » place la lecture : APPROCHE secondes avant le fondu de sortie, ou avant la fin de la partie
		jouée sans fondu ; jamais avant son début."""
		de, a = self.partie()
		_entree, sortie = self.fondus()
		fin = a
		if sortie is not None:
			fin = sortie[0]
		return max(de, fin - APPROCHE)

	def volume(self, position: float) -> float:
		"""Le volume de l'écoute comme à l'antenne à cette position du fichier, de 0 à 1 : nul hors de la partie jouée,
		le long de l'enveloppe de la diffusion dedans."""
		de, a = self.partie()
		if (position < de) or (position > a):
			return 0.0
		relative = position - de
		points = [(moment.total_seconds(), volume) for moment, volume in self._points()]
		for (avant, depuis), (apres, vers) in zip(points, points[1:], strict=False):
			if avant <= relative <= apres:
				if apres == avant:
					return vers
				return depuis + (vers - depuis) * (relative - avant) / (apres - avant)
		return points[-1][1]


def _origine(origine: str | None) -> str:
	if origine is None:
		return ""
	return f" ({origine})"


@dataclass(frozen=True)
class RegleDeBanque:
	"""La règle d'un côté des crossfades de la banque qui fournit le sonore (regle_crossfade), et sa durée."""

	regle: str | None = None
	duree: timedelta | None = None


SANS_BANQUE = RegleDeBanque()


def origine_du_crossfade(du_sonore: timedelta | None, banque: RegleDeBanque, defaut: timedelta | None) -> str | None:
	"""D'où vient le crossfade que retient machincast.lecture.diffusion.crossfade, dans le même ordre."""
	if banque.regle == "impose":
		return "imposé par la banque"
	if du_sonore is not None:
		return None
	if banque.regle == "a_defaut":
		return "de la banque"
	if defaut is not None:
		return "défaut"
	return None


def plan_du_sonore(
	duree: timedelta,
	debut_detecte: timedelta | None,
	fin_detectee: timedelta | None,
	detection_blancs: bool,
	crossfade_debut: timedelta | None,
	crossfade_fin: timedelta | None,
	defauts: Crossfades,
	audite: bool,
	banque: tuple[RegleDeBanque, RegleDeBanque] = (SANS_BANQUE, SANS_BANQUE),
) -> Plan:
	"""Le plan d'un sonore d'après ses colonnes en base. Sans banque, un crossfade non paramétré (None) est celui des
	préférences ; avec, les règles de crossfade de début et de fin de la banque s'appliquent avant, comme à la
	diffusion (https://github.com/dascritch/machincast/issues/230). detection_blancs : celle du sonore, ou de sa
	banque."""

	def facultative(valeur: timedelta | None) -> float | None:
		if valeur is None:
			return None
		return valeur.total_seconds()

	debut, fin = banque
	return Plan(
		duree=duree.total_seconds(),
		blanc_debut=facultative(debut_detecte),
		blanc_fin=facultative(fin_detectee),
		blancs_retires=detection_blancs,
		crossfade_debut=crossfade(crossfade_debut, debut.regle, debut.duree, defauts.debut).total_seconds(),
		crossfade_fin=crossfade(crossfade_fin, fin.regle, fin.duree, defauts.fin).total_seconds(),
		origine_debut=origine_du_crossfade(crossfade_debut, debut, defauts.debut),
		origine_fin=origine_du_crossfade(crossfade_fin, fin, defauts.fin),
		audite=audite,
	)


def lire_le_plan(
	connexion: psycopg.Connection[TupleRow], sonore: int, banque: int | None, defauts: Crossfades
) -> Plan | None:
	"""Le plan d'un fichier tel que la diffusion le joue, fourni par cette banque ou sans banque (None) : ses blancs
	retirés si le sonore ou la banque active la détection, ses crossfades selon les règles de la banque ; None pour un
	stream, un fichier sans durée, ou un sonore qui n'est plus en base (https://github.com/dascritch/machincast/issues/230)."""
	with connexion.transaction():
		ligne = connexion.execute(
			"SELECT s.type::text, s.duree, s.debut_detecte, s.fin_detectee,"
			" s.detection_blancs OR coalesce(b.detection_blancs, false), s.crossfade_debut, s.crossfade_fin,"
			" s.audite_le IS NOT NULL, b.crossfade_debut_regle::text, b.crossfade_debut, b.crossfade_fin_regle::text,"
			" b.crossfade_fin"
			" FROM sonores s LEFT JOIN banques b ON b.id = %s WHERE s.id = %s",
			(banque, sonore),
		).fetchone()
	if ligne is None:
		return None
	genre, duree, debut, fin, detection, cd, cf, audite, regle_debut, banque_debut, regle_fin, banque_fin = ligne
	if (genre != "fichier") or (not isinstance(duree, timedelta)):
		return None
	return plan_du_sonore(
		duree,
		_intervalle(debut),
		_intervalle(fin),
		bool(detection),
		_intervalle(cd),
		_intervalle(cf),
		defauts,
		bool(audite),
		(
			RegleDeBanque(_texte(regle_debut), _intervalle(banque_debut)),
			RegleDeBanque(_texte(regle_fin), _intervalle(banque_fin)),
		),
	)


def _intervalle(valeur: object) -> timedelta | None:
	if isinstance(valeur, timedelta):
		return valeur
	return None


def _texte(valeur: object) -> str | None:
	if valeur is None:
		return None
	return str(valeur)


class FormeDOnde:
	"""La forme d'onde d'un fichier : le niveau crête de chaque mesure, de 0 à 1, calculé en tâche de fond."""

	def __init__(self, chemin: Path, duree: float | None) -> None:
		Gst.init(None)
		self.chemin = chemin
		self.pas = PAS_SANS_DUREE
		"""Secondes de chaque mesure."""
		if (duree is not None) and (duree > 0):
			self.pas = max(PAS_MINIMAL, duree / PICS)
		self.pics: list[float] = []
		self.finie = False
		"""Le calcul est fini : tout le fichier est mesuré, ou une erreur l'a arrêté."""
		self.erreur: str | None = None
		self._pipeline: Gst.Element | None = None
		self._niveau: Gst.Element | None = None

	def demarrer(self) -> None:
		"""Lance le décodage, sans l'attendre."""
		if not self.chemin.is_file():
			self._echouer(f"fichier introuvable, {self.chemin}")
			return
		pipeline = Gst.parse_launch("uridecodebin name=source ! audioconvert ! level name=niveau ! fakesink sync=false")
		assert isinstance(pipeline, Gst.Bin)
		source, niveau = pipeline.get_by_name("source"), pipeline.get_by_name("niveau")
		assert (source is not None) and (niveau is not None), "installer gstreamer1.0-plugins-base et -good"
		source.set_property("uri", Gst.filename_to_uri(str(self.chemin)))
		niveau.set_property("interval", round(self.pas * Gst.SECOND))
		niveau.set_property("post-messages", True)
		self._pipeline, self._niveau = pipeline, niveau
		pipeline.set_state(Gst.State.PLAYING)

	def relever(self) -> bool:
		"""Les mesures arrivées depuis la dernière relève ; vrai s'il y en a de nouvelles, ou si le calcul vient de
		finir."""
		pipeline = self._pipeline
		if pipeline is None:
			return False
		bus = pipeline.get_bus()
		assert bus is not None
		nouvelles = False
		while (message := bus.pop()) is not None:
			if message.type == Gst.MessageType.EOS:
				self.arreter()
				self.finie = True
				return True
			if message.type == Gst.MessageType.ERROR:
				erreur, _detail = message.parse_error()
				self._echouer(str(erreur.message))
				return True
			if (message.type == Gst.MessageType.ELEMENT) and (message.src == self._niveau):
				nouvelles = (self._mesurer(message.get_structure())) or (nouvelles)
		return nouvelles

	def arreter(self) -> None:
		if self._pipeline is not None:
			self._pipeline.set_state(Gst.State.NULL)
		self._pipeline, self._niveau = None, None

	def couverte(self) -> float:
		"""Secondes du fichier déjà mesurées."""
		return len(self.pics) * self.pas

	def amplitudes(self, de: float, a: float) -> list[float]:
		"""Les mesures entièrement comprises entre ces deux instants."""
		return [
			pic for indice, pic in enumerate(self.pics) if (indice * self.pas >= de) and ((indice + 1) * self.pas <= a)
		]

	def _echouer(self, erreur: str) -> None:
		self.arreter()
		self.erreur = erreur
		self.finie = True

	def _mesurer(self, structure: Gst.Structure | None) -> bool:
		if (structure is None) or (structure.get_name() != "level"):
			return False
		crete = structure.get_value("peak")
		if not crete:
			return False
		# Le canal le plus fort ; un silence numérique donne -inf, ou un niveau très bas.
		decibels = max(float(valeur) for valeur in crete)
		amplitude = 0.0
		if math.isfinite(decibels):
			amplitude = min(1.0, max(0.0, 10 ** (decibels / 20)))
		self.pics.append(amplitude)
		return True


class Frise(QWidget):
	"""La frise d'un fichier : forme d'onde, blancs, fondus et tête de lecture."""

	placee = Signal(float)
	"""Une position demandée, en secondes du fichier."""

	def __init__(self, parent: QWidget | None = None, interactive: bool = True) -> None:
		"""interactive : un clic, un glissement ou les flèches demandent une position ; sur l'accueil, la frise ne fait
		que se regarder (https://github.com/dascritch/machincast/issues/230)."""
		super().__init__(parent)
		self.interactive = interactive
		self.plan: Plan | None = None
		self.duree: float | None = None
		self.forme: FormeDOnde | None = None
		self.tete: float | None = None
		"""La tête de lecture, en secondes du fichier ; None : pas de lecture."""
		self._glisse = False
		self.setMinimumHeight(HAUTEUR)
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
		self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
		self.setAccessibleName("Frise du fichier")
		if interactive:
			self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
			self.setAccessibleName("Position dans le fichier")
		self.setAttribute(Qt.WidgetAttribute.WA_Hover)

	def montrer(self, plan: Plan | None, duree: float | None) -> None:
		"""Le plan du fichier, et sa durée ; sans plan, la frise ne montre que la forme d'onde et la tête."""
		self.plan = plan
		self.duree = duree
		if plan is not None:
			self.duree = plan.duree
		self.tete = None
		description = ""
		if plan is not None:
			description = plan.resume()
		self.setAccessibleDescription(description)
		self.update()

	def montrer_la_forme(self, forme: FormeDOnde | None) -> None:
		self.forme = forme
		self.update()

	def placer_la_tete(self, position: float | None) -> None:
		"""La tête de lecture suit la lecture, sauf pendant un glissement : elle suit alors la souris."""
		if self._glisse:
			return
		if position != self.tete:
			self.tete = position
			self.update()

	def remarque(self) -> str:
		"""Ce que la frise dit en clair : « Forme d'onde indisponible : … », ou rien."""
		if (self.forme is not None) and (self.forme.erreur is not None):
			return f"{INDISPONIBLE} {self.forme.erreur}"
		return ""

	def etendue(self) -> float:
		"""Les secondes que couvre la largeur de la frise : la durée du fichier, sinon ce que la forme en a mesuré."""
		if (self.duree is not None) and (self.duree > 0):
			return self.duree
		if self.forme is not None:
			return max(self.forme.couverte(), PAS_SANS_DUREE)
		return 1.0

	def x_vers_secondes(self, x: float) -> float:
		largeur = max(1, self.width())
		return max(0.0, min(1.0, x / largeur)) * self.etendue()

	def secondes_vers_x(self, valeur: float) -> float:
		return valeur / self.etendue() * self.width()

	def infobulle_a(self, x: float) -> str:
		"""La zone sous ce point, la plus précise d'abord, ou l'instant du fichier."""
		position = self.x_vers_secondes(x)
		if self.plan is not None:
			for zone in self.plan.zones():
				if zone.debut <= position <= zone.fin:
					return zone.infobulle
		return instant(position)

	# ─── Événements ────────────────────────────────────────

	def event(self, evenement: QEvent) -> bool:
		if evenement.type() == QEvent.Type.ToolTip:
			assert isinstance(evenement, QHelpEvent)
			QToolTip.showText(evenement.globalPos(), self.infobulle_a(evenement.pos().x()), self)
			return True
		return super().event(evenement)

	def mousePressEvent(self, evenement: QMouseEvent) -> None:
		if not self.interactive:
			super().mousePressEvent(evenement)
			return
		if evenement.button() != Qt.MouseButton.LeftButton:
			super().mousePressEvent(evenement)
			return
		self._glisse = True
		self._suivre(evenement.position().x())

	def mouseMoveEvent(self, evenement: QMouseEvent) -> None:
		if not self.interactive:
			super().mouseMoveEvent(evenement)
			return
		if self._glisse:
			self._suivre(evenement.position().x())

	def mouseReleaseEvent(self, evenement: QMouseEvent) -> None:
		if not self.interactive:
			super().mouseReleaseEvent(evenement)
			return
		if (evenement.button() != Qt.MouseButton.LeftButton) or (not self._glisse):
			super().mouseReleaseEvent(evenement)
			return
		self._suivre(evenement.position().x())
		self._glisse = False
		assert self.tete is not None
		self.placee.emit(self.tete)

	def keyPressEvent(self, evenement: QKeyEvent) -> None:
		if not self.interactive:
			super().keyPressEvent(evenement)
			return
		pas = {Qt.Key.Key_Right: 1.0, Qt.Key.Key_Left: -1.0}.get(Qt.Key(evenement.key()))
		if pas is None:
			super().keyPressEvent(evenement)
			return
		position = max(0.0, min(self.etendue(), ((self.tete) or (0.0)) + pas))
		self.tete = position
		self.update()
		self.placee.emit(position)

	def _suivre(self, x: float) -> None:
		self.tete = self.x_vers_secondes(x)
		self.update()

	# ─── Dessin ────────────────────────────────────────────

	def paintEvent(self, _evenement: QPaintEvent) -> None:
		peintre = QPainter(self)
		peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
		palette = self.palette()
		# Jamais grisée : à l'arrêt, la frise reste lisible, et se lit comme pendant la lecture.
		groupe = QPalette.ColorGroup.Normal
		cadre = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
		peintre.fillRect(cadre, palette.color(groupe, QPalette.ColorRole.Base))
		self._dessiner_la_forme(peintre, palette.color(groupe, QPalette.ColorRole.Text))
		if self.plan is not None:
			self._dessiner_les_zones(peintre, palette.color(groupe, QPalette.ColorRole.Text))
			self._dessiner_les_fondus(peintre, palette.color(groupe, QPalette.ColorRole.Highlight))
		self._dessiner_la_tete(peintre, palette.color(groupe, QPalette.ColorRole.Highlight))
		remarque = self.remarque()
		if remarque != "":
			peintre.setPen(palette.color(groupe, QPalette.ColorRole.Text))
			peintre.drawText(cadre, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, remarque)
		peintre.setPen(QPen(palette.color(groupe, QPalette.ColorRole.Mid), 1))
		peintre.setBrush(Qt.BrushStyle.NoBrush)
		peintre.drawRect(cadre)
		peintre.end()

	def colonnes(self) -> list[float]:
		"""L'amplitude de chaque colonne de points : la plus forte des mesures qui y tombent."""
		if (self.forme is None) or (not self.forme.pics):
			return []
		hauteurs = [0.0] * max(1, self.width())
		pas = self.forme.pas
		for indice, pic in enumerate(self.forme.pics):
			# Une mesure plus large qu'un point en couvre plusieurs : aucune colonne ne reste vide entre deux mesures.
			gauche = min(len(hauteurs) - 1, int(self.secondes_vers_x(indice * pas)))
			droite = max(gauche + 1, min(len(hauteurs), math.ceil(self.secondes_vers_x((indice + 1) * pas))))
			for colonne in range(gauche, droite):
				hauteurs[colonne] = max(hauteurs[colonne], pic)
		derniere = min(len(hauteurs), math.ceil(self.secondes_vers_x(self.forme.couverte())))
		return hauteurs[:derniere]

	def _dessiner_la_forme(self, peintre: QPainter, couleur: QColor) -> None:
		hauteurs = self.colonnes()
		if not hauteurs:
			return
		milieu = self.height() / 2
		demi = milieu - 2
		haut = [QPointF(x + 0.5, milieu - hauteur * demi) for x, hauteur in enumerate(hauteurs)]
		bas = [QPointF(x + 0.5, milieu + hauteur * demi) for x, hauteur in reversed(list(enumerate(hauteurs)))]
		teinte = QColor(couleur)
		teinte.setAlpha(110)
		peintre.setPen(Qt.PenStyle.NoPen)
		peintre.setBrush(teinte)
		peintre.drawPolygon(QPolygonF(haut + bas))

	def _dessiner_les_zones(self, peintre: QPainter, couleur: QColor) -> None:
		"""Les blancs : hachures pleines et voile s'ils sont retirés à l'antenne, hachures pâles sans voile s'ils y
		sont joués. La différence tient au motif, pas qu'à la couleur."""
		assert self.plan is not None
		for zone in self.plan.zones():
			if zone.hachures == "aucune":
				continue
			rectangle = QRectF(
				self.secondes_vers_x(zone.debut), 0, self.secondes_vers_x(zone.fin - zone.debut), self.height()
			)
			trait = QColor(couleur)
			motif = Qt.BrushStyle.BDiagPattern
			if zone.hachures == "pleines":
				voile = QColor(couleur)
				voile.setAlpha(45)
				peintre.fillRect(rectangle, voile)
				trait.setAlpha(190)
			else:
				motif = Qt.BrushStyle.FDiagPattern
				trait.setAlpha(70)
			peintre.fillRect(rectangle, QBrush(trait, motif))

	def _dessiner_les_fondus(self, peintre: QPainter, couleur: QColor) -> None:
		"""Les fondus : une rampe, et le volume retiré au-dessus d'elle, voilé."""
		assert self.plan is not None
		entree, sortie = self.plan.fondus()
		haut, bas = 1.0, self.height() - 1.0
		voile = QColor(couleur)
		voile.setAlpha(50)
		for fondu, montee in ((entree, True), (sortie, False)):
			if fondu is None:
				continue
			gauche, droite = self.secondes_vers_x(fondu[0]), self.secondes_vers_x(fondu[1])
			depart, arrivee = QPointF(gauche, bas), QPointF(droite, haut)
			coin = QPointF(gauche, haut)
			if not montee:
				depart, arrivee = QPointF(gauche, haut), QPointF(droite, bas)
				coin = QPointF(droite, haut)
			peintre.setPen(Qt.PenStyle.NoPen)
			peintre.setBrush(voile)
			peintre.drawPolygon(QPolygonF([depart, arrivee, coin]))
			peintre.setPen(QPen(couleur, 2))
			peintre.drawLine(depart, arrivee)

	def _dessiner_la_tete(self, peintre: QPainter, couleur: QColor) -> None:
		if self.tete is None:
			return
		x = self.secondes_vers_x(self.tete)
		peintre.setPen(QPen(couleur, 2))
		peintre.drawLine(QPointF(x, 0), QPointF(x, self.height()))
		peintre.setPen(Qt.PenStyle.NoPen)
		peintre.setBrush(couleur)
		peintre.drawPolygon(QPolygonF([QPointF(x - 5, 0), QPointF(x + 5, 0), QPointF(x, 6)]))
