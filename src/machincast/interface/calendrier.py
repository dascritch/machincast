"""Calendrier de la grille (https://github.com/dascritch/machincast/issues/36,
https://github.com/dascritch/machincast/issues/118, spec § 8.2).

Un onglet de la fenêtre, ouvert depuis le menu « Affichage », qui montre à la fois ce qui est prévu et ce qui a été
diffusé, en vue semaine (du lundi au dimanche) ou en vue jour, de 0 h à 24 h, de 28 jours avant à 28 jours après
aujourd'hui.

- Prévu : chaque occurrence d'un événement, récurrences comprises, et ce qui en joue
  (machincast.lecture.grille.prevoir). Un bloc qu'un autre événement masque en entier est estompé ; en partie, seuls ses
  moments à l'antenne sont pleins. Une occurrence de 24 heures ou plus, et un fil musical permanent, vont dans la bande
  de la journée entière, entre le nom du jour et les heures. Deux blocs qui se chevauchent se placent côte à côte.
- Diffusé : l'airplay, en bandes étroites à droite de chaque jour. Les passages successifs d'un même événement font
  une seule bande ; un passage sans fin dure jusqu'au passage suivant, ou jusqu'à maintenant pour le dernier.
- Une case par priorité montre ou cache ses blocs et ses bandes ; ce qui joue ne change pas.
- Survoler un bloc ou une bande donne son infobulle ; un double-clic ouvre son événement (signal ouverte). Un clic
  sur une heure libre, pas encore passée, demande la création d'un événement sur son heure entière (creation_demandee).

Le calendrier se relit à l'ouverture de son onglet, à chaque changement de période et par « Rafraîchir les onglets » ;
jamais en boucle.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QHelpEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
	QCheckBox,
	QHBoxLayout,
	QLabel,
	QPushButton,
	QScrollArea,
	QStyle,
	QToolTip,
	QVBoxLayout,
	QWidget,
)

from machincast.conversion import texte_ou_rien
from machincast.horloge import Horloge
from machincast.interface.affichage import MOIS
from machincast.lecture.grille import JOURS, RANGS, Evenement, Prevue, Priorite, heure_murale, lire_grille, prevoir

Connexion = psycopg.Connection[TupleRow]

PRIORITES = (
	(Priorite.SPECIAL, "Spécial"),
	(Priorite.EMISSION, "Émission"),
	(Priorite.FIL_MUSICAL, "Fil musical"),
)
"""Les priorités de la grille, de la plus haute à la plus basse, et le nom de leur case."""
NOMS = dict(PRIORITES)
COULEURS = {
	Priorite.SPECIAL: QColor("#f08c8c"),
	Priorite.EMISSION: QColor("#8cb4f0"),
	Priorite.FIL_MUSICAL: QColor("#8fd19e"),
}
SUPPRIME = QColor("#b0b0b0")
"""La couleur de l'airplay d'un événement supprimé."""
TEXTE = QColor(0x20, 0x20, 0x20)
ESTOMPE = 70
"""Opacité, sur 255, de ce qu'un autre événement masque."""
PORTEE = timedelta(days=28)
"""Le calendrier va de PORTEE avant à PORTEE après aujourd'hui."""
UNE_HEURE = timedelta(hours=1)
"""Un événement créé depuis le calendrier occupe l'heure entière cliquée : 13:37 donne 13:00 – 14:00."""
UN_JOUR = timedelta(days=1)
HAUTEUR_HEURE = 48
MARGE = 52
"""Largeur de la colonne des heures, à gauche."""
PART_PREVUE = 0.72
"""Part de la largeur d'un jour pour les blocs prévus ; le reste, moins un écart, pour l'airplay."""
ECART = 4
HAUTEUR_NOMS = 24
HAUTEUR_LIGNE = 22
"""Hauteur d'un bloc de la journée entière."""
OUVRIR = "Double-clic : ouvrir l'événement"
EVENEMENT_SUPPRIME = "Événement supprimé"
MASQUE = "par un autre événement"


def numero(jour: date) -> str:
	if jour.day == 1:
		return "1er"
	return str(jour.day)


def libelle_du_jour(jour: date) -> str:
	"""« mardi 20 », « dimanche 1er »."""
	return f"{JOURS[jour.weekday()]} {numero(jour)}"


def jour_et_mois(jour: date) -> str:
	"""« mardi 20 octobre »."""
	return f"{libelle_du_jour(jour)} {MOIS[jour.month - 1]}"


def date_longue(jour: date) -> str:
	"""« mardi 20 octobre 2026 »."""
	return f"{jour_et_mois(jour)} {jour.year}"


def titre_de_semaine(lundi: date) -> str:
	"""« Semaine du lundi 19 au dimanche 25 octobre 2026 » ; le mois, ou l'année, du lundi quand ils changent."""
	dimanche = lundi + timedelta(days=6)
	depart = numero(lundi)
	if lundi.year != dimanche.year:
		depart = f"{depart} {MOIS[lundi.month - 1]} {lundi.year}"
	elif lundi.month != dimanche.month:
		depart = f"{depart} {MOIS[lundi.month - 1]}"
	return f"Semaine du lundi {depart} au dimanche {numero(dimanche)} {MOIS[dimanche.month - 1]} {dimanche.year}"


def horaire(jour: date, moment: datetime) -> str:
	"""« 07:00 », ou « 24:00 » pour la fin du jour."""
	if moment == minuit(jour + UN_JOUR):
		return "24:00"
	return f"{moment:%H:%M}"


def minuit(jour: date) -> datetime:
	return datetime.combine(jour, time())


def _croiser(
	moments: Iterable[tuple[datetime, datetime]], debut: datetime, fin: datetime
) -> tuple[tuple[datetime, datetime], ...]:
	croises = ((max(depart, debut), min(arrivee, fin)) for depart, arrivee in moments)
	return tuple((depart, arrivee) for depart, arrivee in croises if depart < arrivee)


@dataclass(frozen=True)
class Bloc:
	"""Une occurrence prévue, sur un jour du calendrier."""

	prevue: Prevue
	jour: date
	debut: datetime
	fin: datetime
	joue: tuple[tuple[datetime, datetime], ...]
	"""Ses moments à l'antenne, ce jour-là."""
	journee: bool
	"""Dans la bande de la journée entière."""
	nom_public: str | None

	@property
	def evenement(self) -> Evenement:
		return self.prevue.occurrence.evenement

	@property
	def etat(self) -> str:
		if not self.joue:
			return "estompé"
		if self.joue == ((self.debut, self.fin),):
			return "joue"
		return "joue en partie"

	def infobulle(self) -> str:
		evenement = self.evenement
		nom = evenement.nom
		if self.nom_public:
			nom = f"{nom} ({self.nom_public})"
		lignes = [f"{nom} — {NOMS[evenement.priorite]}", self._horaires()]
		if evenement.jours:
			lignes.append(f"Revient le {', '.join(JOURS[jour] for jour in sorted(evenement.jours))}")
		lignes += [self._ce_qui_joue(), OUVRIR]
		return "\n".join(lignes)

	def _horaires(self) -> str:
		occurrence = self.prevue.occurrence
		if occurrence.debut is None:
			return "Fil musical permanent"
		depart = f"{jour_et_mois(occurrence.debut.date())}, "
		if occurrence.fin is None:
			return f"{depart}à partir de {occurrence.debut:%H:%M}, sans fin : jusqu'à l'épuisement de sa liste"
		if occurrence.fin.date() == occurrence.debut.date():
			return f"{depart}{occurrence.debut:%H:%M} – {occurrence.fin:%H:%M}"
		return f"{depart}{occurrence.debut:%H:%M} – {jour_et_mois(occurrence.fin.date())}, {occurrence.fin:%H:%M}"

	def _ce_qui_joue(self) -> str:
		etat = self.etat
		if etat == "joue":
			return "Joue en entier"
		if etat == "estompé":
			return f"Masqué en entier {MASQUE}"
		moments = " et ".join(f"de {horaire(self.jour, d)} à {horaire(self.jour, f)}" for d, f in self.joue)
		return f"Joue {moments} ; masqué le reste du temps {MASQUE}"


@dataclass(frozen=True)
class Passage:
	debut: datetime
	fin: datetime | None
	evenement_id: int | None
	nom: str | None
	priorite: Priorite | None


@dataclass(frozen=True)
class Bande:
	"""Des passages successifs d'un même événement, sur un jour du calendrier."""

	jour: date
	debut: datetime
	fin: datetime
	evenement_id: int | None
	nom: str
	priorite: Priorite | None
	passages: int
	depart: datetime
	"""Début du premier passage, à la seconde."""
	arrivee: datetime | None
	"""Fin du dernier passage, à la seconde ; None pour un passage en cours."""

	def infobulle(self) -> str:
		depart = f"{jour_et_mois(self.depart.date())}, "
		if self.arrivee is None:
			moments = f"{depart}depuis {self.depart:%H:%M:%S}, en cours"
		elif self.arrivee.date() == self.depart.date():
			moments = f"{depart}{self.depart:%H:%M:%S} – {self.arrivee:%H:%M:%S}"
		else:
			moments = f"{depart}{self.depart:%H:%M:%S} – {jour_et_mois(self.arrivee.date())}, {self.arrivee:%H:%M:%S}"
		pluriel = ""
		if self.passages > 1:
			pluriel = "s"
		lignes = [f"Diffusé : {self.nom}", moments, f"{self.passages} passage{pluriel}"]
		if self.evenement_id is not None:
			lignes.append(OUVRIR)
		return "\n".join(lignes)


def decouper(prevues: Iterable[Prevue], jours: list[date], noms_publics: dict[int, str | None]) -> list[Bloc]:
	"""Les blocs de chaque jour : une occurrence qui passe minuit en donne un par jour qu'elle touche."""
	blocs = []
	for prevue in prevues:
		journee = (prevue.occurrence.debut is None) or (prevue.fin - prevue.debut >= UN_JOUR)
		for jour in jours:
			debut, fin = max(prevue.debut, minuit(jour)), min(prevue.fin, minuit(jour + UN_JOUR))
			if debut >= fin:
				continue
			nom_public = noms_publics.get(prevue.occurrence.evenement.id)
			blocs.append(Bloc(prevue, jour, debut, fin, _croiser(prevue.joue, debut, fin), journee, nom_public))
	return sorted(blocs, key=lambda b: (b.jour, b.debut, RANGS[b.evenement.priorite], b.evenement.id))


def lire_passages(connexion: Connexion, de: datetime, a: datetime) -> list[Passage]:
	"""Les passages commencés dans la période, ou la veille : ceux-là peuvent encore la toucher."""
	lignes = connexion.execute(
		"SELECT d.horodatage, f.horodatage, d.evenement_id, e.nom_interne, e.priorite::text"
		" FROM airplay d"
		" LEFT JOIN airplay f ON (f.passage_id = d.passage_id) AND (f.type_ligne = 'fin')"
		" LEFT JOIN evenements e ON e.id = d.evenement_id"
		" WHERE (d.type_ligne = 'debut') AND (d.horodatage >= %s) AND (d.horodatage < %s)"
		" ORDER BY d.horodatage, d.id",
		((de - UN_JOUR).astimezone(), a.astimezone()),
	).fetchall()
	passages = []
	for debut, fin, evenement_id, nom, priorite in lignes:
		assert isinstance(debut, datetime)
		arrivee = None
		if isinstance(fin, datetime):
			arrivee = heure_murale(fin)
		identifiant = None
		if evenement_id is not None:
			identifiant = int(str(evenement_id))
		rang = None
		if priorite is not None:
			rang = Priorite(str(priorite))
		passages.append(Passage(heure_murale(debut), arrivee, identifiant, texte_ou_rien(nom), rang))
	return passages


def bandes(passages: list[Passage], jours: list[date], maintenant: datetime) -> list[Bande]:
	"""Les passages successifs d'un même événement réunis, puis découpés par jour.

	Un passage sans fin dure jusqu'au passage suivant ; le dernier, s'il n'a pas de fin, est en cours."""
	groupes: list[tuple[Passage, datetime, datetime | None, int]] = []
	for indice, passage in enumerate(passages):
		arrivee = passage.fin
		if (arrivee is None) and (indice + 1 < len(passages)):
			arrivee = passages[indice + 1].debut
		if (groupes) and (groupes[-1][0].evenement_id == passage.evenement_id):
			premier, depart, _arrivee, nombre = groupes[-1]
			groupes[-1] = (premier, depart, arrivee, nombre + 1)
			continue
		groupes.append((passage, passage.debut, arrivee, 1))
	trouvees = []
	for passage, depart, arrivee, nombre in groupes:
		fin = (arrivee) or (maintenant)
		for jour in jours:
			debut_du_jour, fin_du_jour = max(depart, minuit(jour)), min(fin, minuit(jour + UN_JOUR))
			if debut_du_jour >= fin_du_jour:
				continue
			nom = (passage.nom) or (EVENEMENT_SUPPRIME)
			trouvees.append(
				Bande(
					jour,
					debut_du_jour,
					fin_du_jour,
					passage.evenement_id,
					nom,
					passage.priorite,
					nombre,
					depart,
					arrivee,
				)
			)
	return trouvees


def colonnes(blocs: list[Bloc]) -> dict[Bloc, tuple[int, int]]:
	"""La colonne de chaque bloc d'un jour, et le nombre de colonnes de son groupe : ceux qui se chevauchent se
	placent côte à côte, à la première colonne libre."""
	places: dict[Bloc, tuple[int, int]] = {}
	groupe: list[tuple[Bloc, int]] = []
	fin_du_groupe: datetime | None = None
	for bloc in sorted(blocs, key=lambda b: (b.debut, b.fin)):
		if (fin_du_groupe is not None) and (bloc.debut >= fin_du_groupe):
			_placer(groupe, places)
			groupe, fin_du_groupe = [], None
		occupees = {colonne for autre, colonne in groupe if autre.fin > bloc.debut}
		colonne = next(numero for numero in range(len(groupe) + 1) if numero not in occupees)
		groupe.append((bloc, colonne))
		fin_du_groupe = max((fin_du_groupe) or (bloc.fin), bloc.fin)
	_placer(groupe, places)
	return places


def _placer(groupe: list[tuple[Bloc, int]], places: dict[Bloc, tuple[int, int]]) -> None:
	nombre = max((colonne for _bloc, colonne in groupe), default=-1) + 1
	for bloc, colonne in groupe:
		places[bloc] = (colonne, nombre)


class Calendrier(QWidget):
	ouverte = Signal(str, int, str)
	"""Double-clic sur un bloc ou une bande : genre, identifiant et nom de son événement."""
	creation_demandee = Signal(object)
	"""Clic sur une heure libre : le début, en heure murale, de l'événement à créer."""

	def __init__(self, connexion: Connexion, horloge: Horloge, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.connexion = connexion
		self.horloge = horloge
		self._semaine = True
		self._debut = self._lundi(self._aujourd_hui())
		self._blocs: list[Bloc] = []
		self._bandes: list[Bande] = []
		self.precedent = QPushButton()
		self.aujourd_hui = QPushButton("Aujourd'hui")
		self.suivant = QPushButton()
		self.titre = QLabel()
		police = self.titre.font()
		police.setBold(True)
		self.titre.setFont(police)
		self.vue_jour = QPushButton("Jour")
		self.vue_semaine = QPushButton("Semaine")
		self.cases: dict[Priorite, QCheckBox] = {}
		barre = QHBoxLayout()
		for widget in (self.precedent, self.aujourd_hui, self.suivant):
			barre.addWidget(widget)
		barre.addWidget(self.titre, 1)
		for priorite, nom in PRIORITES:
			coche = QCheckBox(nom)
			coche.setChecked(True)
			coche.toggled.connect(self._filtrer)
			self.cases[priorite] = coche
			barre.addWidget(coche)
		barre.addWidget(self.vue_jour)
		barre.addWidget(self.vue_semaine)
		self.precedent.clicked.connect(lambda: self._avancer(-1))
		self.suivant.clicked.connect(lambda: self._avancer(1))
		self.aujourd_hui.clicked.connect(self._revenir)
		self.vue_jour.clicked.connect(lambda: self._changer_de_vue(False))
		self.vue_semaine.clicked.connect(lambda: self._changer_de_vue(True))
		self.entete = EnTete(self)
		self.grille = Grille(self)
		self.defilement = QScrollArea()
		self.defilement.setWidget(self.grille)
		self.defilement.setWidgetResizable(True)
		self.defilement.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
		# L'en-tête s'aligne sur les jours de la grille, que la barre de défilement rétrécit.
		barre_de_defilement = self.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)
		self.entete.setContentsMargins(0, 0, barre_de_defilement + 2 * self.defilement.frameWidth(), 0)
		disposition = QVBoxLayout(self)
		disposition.addLayout(barre)
		disposition.addWidget(self.entete)
		disposition.addWidget(self.defilement, 1)
		self._presenter()
		self.defilement.verticalScrollBar().setValue(7 * HAUTEUR_HEURE)

	def _aujourd_hui(self) -> date:
		return heure_murale(self.horloge.maintenant()).date()

	@staticmethod
	def _lundi(jour: date) -> date:
		return jour - timedelta(days=jour.weekday())

	def maintenant(self) -> datetime:
		return heure_murale(self.horloge.maintenant())

	def jours(self) -> list[date]:
		nombre = 1
		if self._semaine:
			nombre = 7
		return [self._debut + timedelta(days=ecart) for ecart in range(nombre)]

	def blocs(self) -> list[Bloc]:
		"""Les blocs des heures, des priorités cochées."""
		return [bloc for bloc in self._blocs if (not bloc.journee) and (self._montree(bloc.evenement.priorite))]

	def journee(self) -> list[Bloc]:
		"""Les blocs de la journée entière, des priorités cochées."""
		return [bloc for bloc in self._blocs if (bloc.journee) and (self._montree(bloc.evenement.priorite))]

	def bandes(self) -> list[Bande]:
		"""L'airplay des priorités cochées ; celui d'un événement supprimé est toujours montré."""
		return [bande for bande in self._bandes if (bande.priorite is None) or (self._montree(bande.priorite))]

	def _montree(self, priorite: Priorite) -> bool:
		return self.cases[priorite].isChecked()

	def actualiser(self) -> None:
		"""Relit la grille et l'airplay de la période."""
		jours = self.jours()
		de, a = minuit(jours[0]), minuit(jours[-1] + UN_JOUR)
		with self.connexion.transaction():
			evenements = lire_grille(self.connexion)
			noms_publics = {
				int(str(identifiant)): texte_ou_rien(nom_public)
				for identifiant, nom_public in self.connexion.execute("SELECT id, nom_public FROM evenements")
			}
			passages = lire_passages(self.connexion, de, a)
		self._blocs = decouper(prevoir(evenements, de, a), jours, noms_publics)
		self._bandes = bandes(passages, jours, self.maintenant())
		self._filtrer()

	def _filtrer(self) -> None:
		self.entete.relire()
		self.grille.update()

	def _avancer(self, sens: int) -> None:
		self._debut += sens * timedelta(days=len(self.jours()))
		self._presenter()

	def _revenir(self) -> None:
		self._debut = self._aujourd_hui()
		if self._semaine:
			self._debut = self._lundi(self._debut)
		self._presenter()

	def _changer_de_vue(self, semaine: bool) -> None:
		"""La vue jour montre aujourd'hui s'il est dans la semaine montrée, sinon son lundi."""
		aujourd_hui = self._aujourd_hui()
		if semaine:
			self._debut = self._lundi(self._debut)
		elif aujourd_hui in self.jours():
			self._debut = aujourd_hui
		self._semaine = semaine
		self._presenter()

	def _presenter(self) -> None:
		periode = timedelta(days=len(self.jours()))
		aujourd_hui = self._aujourd_hui()
		self.titre.setText(date_longue(self._debut))
		self.precedent.setText("Jour précédent")
		self.suivant.setText("Jour suivant")
		if self._semaine:
			self.titre.setText(titre_de_semaine(self._debut))
			self.precedent.setText("Semaine précédente")
			self.suivant.setText("Semaine suivante")
		# Une période se montre tant qu'elle touche les PORTEE jours avant ou après aujourd'hui.
		self.precedent.setEnabled(self._debut - timedelta(days=1) >= aujourd_hui - PORTEE)
		self.suivant.setEnabled(self._debut + periode <= aujourd_hui + PORTEE)
		self.vue_jour.setEnabled(self._semaine)
		self.vue_semaine.setEnabled(not self._semaine)
		self.actualiser()


def _x_des_jours(widget: QWidget, nombre: int) -> list[float]:
	"""Le bord gauche de chaque jour, et le bord droit du dernier."""
	largeur = (widget.contentsRect().width() - MARGE) / nombre
	return [MARGE + indice * largeur for indice in range(nombre + 1)]


class EnTete(QWidget):
	"""Le nom des jours, et la bande de la journée entière."""

	def __init__(self, calendrier: Calendrier) -> None:
		super().__init__(calendrier)
		self.calendrier = calendrier

	def libelles(self) -> list[str]:
		return [libelle_du_jour(jour) for jour in self.calendrier.jours()]

	def relire(self) -> None:
		par_jour = [sum(1 for b in self.calendrier.journee() if b.jour == jour) for jour in self.calendrier.jours()]
		self.setFixedHeight(HAUTEUR_NOMS + max([1, *par_jour]) * HAUTEUR_LIGNE + ECART)
		self.update()

	def rectangle(self, bloc: Bloc) -> QRectF:
		jours = self.calendrier.jours()
		x = _x_des_jours(self, len(jours))
		indice = jours.index(bloc.jour)
		rang = [b for b in self.calendrier.journee() if b.jour == bloc.jour].index(bloc)
		y = HAUTEUR_NOMS + rang * HAUTEUR_LIGNE
		return QRectF(x[indice] + 1, y + 1, x[indice + 1] - x[indice] - 2, HAUTEUR_LIGNE - 2)

	def _bloc_en(self, point: QPointF) -> Bloc | None:
		return next((b for b in self.calendrier.journee() if self.rectangle(b).contains(point)), None)

	def event(self, evenement: QEvent) -> bool:
		if (isinstance(evenement, QHelpEvent)) and (evenement.type() == QEvent.Type.ToolTip):
			_infobulle(self, evenement, self._bloc_en(QPointF(evenement.pos())))
			return True
		return super().event(evenement)

	def mouseDoubleClickEvent(self, evenement: QMouseEvent) -> None:
		_ouvrir(self.calendrier, self._bloc_en(evenement.position()))

	def paintEvent(self, _evenement: QPaintEvent) -> None:
		peintre = QPainter(self)
		jours = self.calendrier.jours()
		x = _x_des_jours(self, len(jours))
		peintre.setPen(self.palette().text().color())
		for indice, jour in enumerate(jours):
			cadre = QRectF(x[indice], 0, x[indice + 1] - x[indice], HAUTEUR_NOMS)
			police = peintre.font()
			police.setBold(jour == self.calendrier.maintenant().date())
			peintre.setFont(police)
			peintre.drawText(cadre, Qt.AlignmentFlag.AlignCenter, libelle_du_jour(jour))
		police = peintre.font()
		police.setBold(False)
		peintre.setFont(police)
		for bloc in self.calendrier.journee():
			_peindre_bloc(peintre, self.rectangle(bloc), bloc, _part_du_jour)
		peintre.end()


def _part_du_jour(cadre: QRectF, bloc: Bloc, debut: datetime, fin: datetime) -> QRectF:
	"""La part d'un bloc de la journée entière qui va de debut à fin, de gauche à droite."""
	depart = minuit(bloc.jour)
	gauche = cadre.left() + cadre.width() * (debut - depart) / UN_JOUR
	droite = cadre.left() + cadre.width() * (fin - depart) / UN_JOUR
	return QRectF(gauche, cadre.top(), droite - gauche, cadre.height())


class Grille(QWidget):
	"""Les heures de chaque jour : les blocs prévus à gauche, l'airplay à droite."""

	def __init__(self, calendrier: Calendrier) -> None:
		super().__init__(calendrier)
		self.calendrier = calendrier
		self.setMinimumHeight(24 * HAUTEUR_HEURE + 1)
		self.setMouseTracking(True)

	def _x(self) -> list[float]:
		return _x_des_jours(self, len(self.calendrier.jours()))

	@staticmethod
	def _y(jour: date, moment: datetime) -> float:
		return (moment - minuit(jour)) / timedelta(hours=1) * HAUTEUR_HEURE

	def rectangle(self, element: Bloc | Bande) -> QRectF:
		jours = self.calendrier.jours()
		x = self._x()
		indice = jours.index(element.jour)
		largeur = x[indice + 1] - x[indice]
		haut, bas = self._y(element.jour, element.debut), self._y(element.jour, element.fin)
		if isinstance(element, Bande):
			gauche = x[indice] + largeur * PART_PREVUE + ECART
			return QRectF(gauche, haut, x[indice + 1] - ECART - gauche, bas - haut)
		colonne, nombre = colonnes([b for b in self.calendrier.blocs() if b.jour == element.jour])[element]
		part = (largeur * PART_PREVUE - ECART) / nombre
		return QRectF(x[indice] + ECART + colonne * part, haut, part - 1, bas - haut)

	def point(self, moment: datetime) -> QPointF:
		"""Un point à l'heure dite, du côté des blocs prévus de son jour."""
		x = self._x()
		indice = self.calendrier.jours().index(moment.date())
		return QPointF(x[indice] + 2 * ECART, self._y(moment.date(), moment))

	def element_en(self, point: QPointF) -> Bloc | Bande | None:
		elements: list[Bloc | Bande] = [*self.calendrier.bandes(), *self.calendrier.blocs()]
		return next((element for element in elements if self.rectangle(element).contains(point)), None)

	def _moment_en(self, point: QPointF) -> datetime | None:
		x = self._x()
		for indice, jour in enumerate(self.calendrier.jours()):
			if x[indice] <= point.x() < x[indice + 1]:
				return minuit(jour) + timedelta(hours=point.y() / HAUTEUR_HEURE)
		return None

	def event(self, evenement: QEvent) -> bool:
		if (isinstance(evenement, QHelpEvent)) and (evenement.type() == QEvent.Type.ToolTip):
			_infobulle(self, evenement, self.element_en(QPointF(evenement.pos())))
			return True
		return super().event(evenement)

	def mouseDoubleClickEvent(self, evenement: QMouseEvent) -> None:
		_ouvrir(self.calendrier, self.element_en(evenement.position()))

	def mousePressEvent(self, evenement: QMouseEvent) -> None:
		"""Une heure libre, pas encore passée, propose un événement sur l'heure entière : 13:00 – 14:00 pour 13:37."""
		if (evenement.button() != Qt.MouseButton.LeftButton) or (self.element_en(evenement.position()) is not None):
			return
		moment = self._moment_en(evenement.position())
		if moment is None:
			return
		debut = moment.replace(minute=0, second=0, microsecond=0)
		if debut + UNE_HEURE <= self.calendrier.maintenant():
			return
		self.calendrier.creation_demandee.emit(debut)

	def paintEvent(self, _evenement: QPaintEvent) -> None:
		peintre = QPainter(self)
		jours = self.calendrier.jours()
		x = self._x()
		ligne = QPen(self.palette().mid().color())
		peintre.setPen(ligne)
		for heure in range(25):
			y = heure * HAUTEUR_HEURE
			peintre.drawLine(QPointF(MARGE, y), QPointF(x[-1], y))
			if heure < 24:
				peintre.setPen(self.palette().text().color())
				peintre.drawText(QRectF(0, y, MARGE - ECART, 16), Qt.AlignmentFlag.AlignRight, f"{heure:02d}:00")
				peintre.setPen(ligne)
		for bord in x:
			peintre.drawLine(QPointF(bord, 0), QPointF(bord, 24 * HAUTEUR_HEURE))
		for bloc in self.calendrier.blocs():
			_peindre_bloc(peintre, self.rectangle(bloc), bloc, self._part_des_heures)
		maintenant = self.calendrier.maintenant()
		# Le passé de chaque jour, du côté de l'airplay : la place de ce qui a été diffusé.
		for indice, jour in enumerate(jours):
			passe = min(max(maintenant, minuit(jour)), minuit(jour + UN_JOUR))
			gauche = x[indice] + (x[indice + 1] - x[indice]) * PART_PREVUE + ECART
			fond = QRectF(gauche, 0, x[indice + 1] - ECART - gauche, self._y(jour, passe))
			peintre.fillRect(fond, self.palette().alternateBase())
		for bande in self.calendrier.bandes():
			couleur = SUPPRIME
			if bande.priorite is not None:
				couleur = COULEURS[bande.priorite].darker(130)
			cadre = self.rectangle(bande)
			peintre.fillRect(cadre, couleur)
			peintre.setPen(QPen(couleur.darker(150)))
			peintre.drawRect(cadre)
		if maintenant.date() in jours:
			indice = jours.index(maintenant.date())
			hauteur = self._y(maintenant.date(), maintenant)
			peintre.setPen(QPen(QColor("#d03030"), 2))
			peintre.drawLine(QPointF(x[indice], hauteur), QPointF(x[indice + 1], hauteur))
		peintre.end()

	def _part_des_heures(self, cadre: QRectF, bloc: Bloc, debut: datetime, fin: datetime) -> QRectF:
		haut, bas = self._y(bloc.jour, debut), self._y(bloc.jour, fin)
		return QRectF(cadre.left(), haut, cadre.width(), bas - haut)


Partie = Callable[[QRectF, Bloc, datetime, datetime], QRectF]
"""Le rectangle d'un bloc qui va d'un moment à un autre."""


def _peindre_bloc(peintre: QPainter, cadre: QRectF, bloc: Bloc, part: Partie) -> None:
	"""Estompé là où il ne joue pas, plein là où il joue, avec son nom."""
	couleur = COULEURS[bloc.evenement.priorite]
	estompee = QColor(couleur)
	estompee.setAlpha(ESTOMPE)
	peintre.fillRect(cadre, estompee)
	for debut, fin in bloc.joue:
		peintre.fillRect(part(cadre, bloc, debut, fin), couleur)
	peintre.setPen(QPen(couleur.darker(140)))
	peintre.setBrush(QBrush())
	peintre.drawRect(cadre)
	peintre.setPen(TEXTE)
	peintre.drawText(
		cadre.adjusted(3, 1, -2, -1), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, bloc.evenement.nom
	)


def _infobulle(widget: QWidget, evenement: QHelpEvent, element: Bloc | Bande | None) -> None:
	if element is None:
		QToolTip.hideText()
		evenement.ignore()
		return
	QToolTip.showText(evenement.globalPos(), element.infobulle(), widget)


def _ouvrir(calendrier: Calendrier, element: Bloc | Bande | None) -> None:
	if isinstance(element, Bloc):
		calendrier.ouverte.emit("événement", element.evenement.id, element.evenement.nom)
	if (isinstance(element, Bande)) and (element.evenement_id is not None):
		calendrier.ouverte.emit("événement", element.evenement_id, element.nom)
