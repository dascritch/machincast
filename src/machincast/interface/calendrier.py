"""Calendrier de la grille (https://github.com/dascritch/machincast/issues/36,
https://github.com/dascritch/machincast/issues/118, spec § 8.2).

Un onglet de la fenêtre, ouvert depuis le menu « Affichage », qui montre à la fois ce qui est prévu et ce qui a été
diffusé, en vue semaine (du lundi au dimanche) ou en vue jour, de 0 h à 24 h, jusqu'à 28 jours après aujourd'hui.
Il ne remonte pas avant la durée de péremption des préférences (https://github.com/dascritch/machincast/issues/269) :
Machin purge efface de la base ce qui est plus vieux (https://github.com/dascritch/machincast/issues/268). En vue
semaine, les jours d'avant sont grisés, vides.

- Prévu : chaque occurrence d'un événement, récurrences comprises, et ce qui en joue
  (machincast.lecture.grille.prevoir). Un bloc qu'un autre événement masque en entier est estompé ; en partie, seuls ses
  moments à l'antenne sont pleins. Une occurrence de 24 heures ou plus, et un fil musical permanent, vont dans la bande
  de la journée entière, entre le nom du jour et les heures. Deux blocs qui se chevauchent se placent côte à côte.
  Un événement supprimé garde ses occurrences d'avant sa suppression, jusqu'à leur péremption.
- Diffusé : l'airplay, en bandes étroites à droite de chaque jour. Les passages successifs d'un même événement font
  une seule bande ; un passage sans fin dure jusqu'au passage suivant, ou jusqu'à maintenant pour le dernier.
- Une case par priorité montre ou cache ses blocs et ses bandes ; ce qui joue ne change pas.
- Survoler un bloc ou une bande donne son infobulle ; un double-clic ouvre son événement (signal ouverte). Un clic
  sur une heure libre, pas encore passée, demande la création d'un événement sur son heure entière (creation_demandee).
- Sessions sautées (https://github.com/dascritch/machincast/issues/273) : le clic droit sur une session à venir d'un
  événement récurrent la saute, seule ou avec les suivantes jusqu'à un jour choisi (dialogues.choisir_jour) ; sautée,
  elle reste dessinée, hachurée, ne cache rien, se clique comme une heure libre, et se rétablit au clic droit, sauf si
  un événement de même priorité a pris sa place. Chaque saut s'annonce (annonce), et demande à Machin player de
  relire la grille (grille_modifiee).

Navigation (https://github.com/dascritch/machincast/issues/326) : en tête de ligne, « Aujourd'hui », puis « ◀ Avant »
et « Après ▶ », d'une semaine ou d'un jour selon la vue, que choisit une liste déroulante, « Jour » ou « Semaine ».
Zoom des heures : la liste « 🔍 » montre 4, 8, 12 ou 24 heures dans la hauteur de la grille (ZOOMS, 12 par défaut) ;
Maj + molette, dans la grille, passe au zoom voisin. Le zoom garde l'heure du haut de la grille.

Le calendrier se relit à l'ouverture de son onglet, à chaque changement de période et par « Rafraîchir les onglets » ;
jamais en boucle.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
	QBrush,
	QColor,
	QContextMenuEvent,
	QHelpEvent,
	QIcon,
	QMouseEvent,
	QPainter,
	QPaintEvent,
	QPen,
	QPixmap,
	QWheelEvent,
)
from PySide6.QtWidgets import (
	QCheckBox,
	QComboBox,
	QHBoxLayout,
	QLabel,
	QMenu,
	QPushButton,
	QScrollArea,
	QStyle,
	QToolTip,
	QVBoxLayout,
	QWidget,
)

from machincast.conversion import texte_ou_rien
from machincast.horloge import Horloge
from machincast.interface import dialogues, preferences
from machincast.interface.affichage import MOIS
from machincast.interface.sessions import Session, chevauchee, retablir
from machincast.lecture.grille import (
	NOMS_DES_JOURS,
	RANGS,
	Evenement,
	Prevue,
	Priorite,
	heure_murale,
	lire_grille,
	prevoir,
	sessions,
)

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
TEINTES = {Priorite.SPECIAL: "rouge", Priorite.EMISSION: "bleu", Priorite.FIL_MUSICAL: "vert"}
"""Le nom de la couleur de chaque priorité, pour l'infobulle de sa case (https://github.com/dascritch/machincast/issues/293)."""
PLURIELS = {Priorite.SPECIAL: "spéciaux", Priorite.EMISSION: "émissions", Priorite.FIL_MUSICAL: "fils musicaux"}
TAILLE_DU_CARRE = 14
"""Côté, en pixels, du carré de couleur devant le nom de la case d'une priorité."""
SUPPRIME = QColor("#b0b0b0")
"""La couleur de l'airplay d'un événement supprimé."""
TEXTE = QColor(0x20, 0x20, 0x20)
ESTOMPE = 70
"""Opacité, sur 255, de ce qu'un autre événement masque."""
PORTEE = timedelta(days=28)
"""Le calendrier va jusqu'à PORTEE après aujourd'hui ; avant, jusqu'à la durée de péremption."""
PERIME = QColor(128, 128, 128, 90)
"""Le voile d'un jour d'avant la durée de péremption, dont la base n'a plus rien."""
UNE_HEURE = timedelta(hours=1)
"""Un événement créé depuis le calendrier occupe l'heure entière cliquée : 13:37 donne 13:00 – 14:00."""
UN_JOUR = timedelta(days=1)
HAUTEUR_MINIMALE = 16
"""Pixels d'une heure au moins, quel que soit le zoom : la place de son libellé."""
ZOOMS = (4, 8, 12, 24)
"""Les heures que montre la hauteur de la grille, au choix du zoom (https://github.com/dascritch/machincast/issues/326)."""
ZOOM_PAR_DEFAUT = 12
LOUPE = "🔍"
INFOBULLE_DU_ZOOM = "Heures montrées dans la hauteur de la grille ; aussi Maj + molette dans la grille"
VUES = (("Jour", False), ("Semaine", True))
"""La liste déroulante des vues : son texte, et s'il s'agit de la vue semaine."""
AVANT = "◀ Avant"
APRES = "Après ▶"
PREMIERE_HEURE = 7
"""L'heure en haut de la grille à l'ouverture du calendrier."""
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
SUITE_SUPPRIMEE = "la suite n'est plus prévue"
SAUTER = "Sauter cette session"
SAUTER_JUSQU_AU = "Sauter les sessions jusqu'au…"
RETABLIR = "Rétablir cette session"
SAUTEE = "Session sautée"


def numero(jour: date) -> str:
	if jour.day == 1:
		return "1er"
	return str(jour.day)


def libelle_du_jour(jour: date) -> str:
	"""« mardi 20 », « dimanche 1er »."""
	return f"{NOMS_DES_JOURS[jour.weekday()]} {numero(jour)}"


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
	def sautee(self) -> bool:
		return self.prevue.sautee

	@property
	def etat(self) -> str:
		if self.sautee:
			return "sauté"
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
			lignes.append(f"Revient le {', '.join(NOMS_DES_JOURS[jour] for jour in sorted(evenement.jours))}")
		if evenement.supprime_le is not None:
			supprime = heure_murale(evenement.supprime_le)
			lignes.append(f"Supprimé le {jour_et_mois(supprime.date())} à {supprime:%H:%M} : {SUITE_SUPPRIMEE}")
		lignes += [self._ce_qui_joue(), OUVRIR]
		return "\n".join(lignes)

	def infobulle_a(self, maintenant: datetime) -> str:
		"""L'infobulle ; celle d'une session sautée à venir dit comment la rétablir."""
		texte = self.infobulle()
		if (self.sautee) and (_a_venir(self, maintenant)):
			return texte.replace(f"\n{SAUTEE}\n", f"\n{SAUTEE} : « {RETABLIR} » au clic droit\n")
		return texte

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
		if etat == "sauté":
			return SAUTEE
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


def lire_passages(connexion: Connexion, de: datetime, a: datetime, premier: datetime | None = None) -> list[Passage]:
	"""Les passages commencés dans la période, ou la veille : ceux-là peuvent encore la toucher ; jamais avant le
	premier moment montré, que la purge efface."""
	depuis = de - UN_JOUR
	if premier is not None:
		depuis = max(depuis, premier)
	lignes = connexion.execute(
		"SELECT d.logged_at, f.logged_at, d.event_id, e.internal_name, e.priority::text"
		" FROM airplay d"
		" LEFT JOIN airplay f ON (f.play_id = d.play_id) AND (f.line_type = 'end')"
		" LEFT JOIN events e ON e.id = d.event_id"
		" WHERE (d.line_type = 'start') AND (d.logged_at >= %s) AND (d.logged_at < %s)"
		" ORDER BY d.logged_at, d.id",
		(depuis.astimezone(), a.astimezone()),
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


def carre_de_couleur(couleur: QColor) -> QIcon:
	"""Un carré plein de la couleur, bordé comme un bloc du calendrier."""
	image = QPixmap(TAILLE_DU_CARRE, TAILLE_DU_CARRE)
	image.fill(Qt.GlobalColor.transparent)
	peintre = QPainter(image)
	peintre.fillRect(0, 0, TAILLE_DU_CARRE, TAILLE_DU_CARRE, couleur)
	peintre.setPen(QPen(couleur.darker(140)))
	peintre.drawRect(0, 0, TAILLE_DU_CARRE - 1, TAILLE_DU_CARRE - 1)
	peintre.end()
	return QIcon(image)


class Calendrier(QWidget):
	ouverte = Signal(str, int, str)
	"""Double-clic sur un bloc ou une bande : genre, identifiant et nom de son événement."""
	creation_demandee = Signal(object)
	"""Clic sur une heure libre : le début, en heure murale, de l'événement à créer."""
	annonce = Signal(str)
	"""Ce qu'a fait un clic droit, pour la barre d'état."""
	grille_modifiee = Signal()
	"""Une session sautée ou rétablie : Machin player doit relire la grille."""

	def __init__(self, connexion: Connexion, horloge: Horloge, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.connexion = connexion
		self.horloge = horloge
		self._semaine = True
		self._debut = self._lundi(self._aujourd_hui())
		self._blocs: list[Bloc] = []
		self._bandes: list[Bande] = []
		self.heures_visibles = ZOOM_PAR_DEFAUT
		self.heure_du_haut: float = PREMIERE_HEURE
		"""L'heure au bord haut de la grille, que gardent un zoom et un changement de taille."""
		self._ajustement = False
		"""La hauteur de la grille change : la barre de défilement bouge, sans que l'heure du haut change."""
		self.aujourd_hui = QPushButton("Aujourd'hui")
		self.precedent = QPushButton(AVANT)
		self.suivant = QPushButton(APRES)
		self.titre = QLabel()
		police = self.titre.font()
		police.setBold(True)
		self.titre.setFont(police)
		self.vue = QComboBox()
		for texte, semaine in VUES:
			self.vue.addItem(texte, semaine)
		self.vue.setToolTip("Vue d'un jour ou d'une semaine")
		self.loupe = QLabel(LOUPE)
		self.zoom = QComboBox()
		for heures in ZOOMS:
			self.zoom.addItem(f"vue {heures}h", heures)
		self.zoom.setCurrentIndex(ZOOMS.index(ZOOM_PAR_DEFAUT))
		self.loupe.setBuddy(self.zoom)
		self.loupe.setToolTip(INFOBULLE_DU_ZOOM)
		self.zoom.setToolTip(INFOBULLE_DU_ZOOM)
		self.cases: dict[Priorite, QCheckBox] = {}
		barre = QHBoxLayout()
		for widget in (self.aujourd_hui, self.precedent, self.suivant):
			barre.addWidget(widget)
		barre.addWidget(self.titre, 1)
		for priorite, nom in PRIORITES:
			coche = QCheckBox(nom)
			# La couleur de ses blocs, devant son nom (https://github.com/dascritch/machincast/issues/293).
			coche.setIcon(carre_de_couleur(COULEURS[priorite]))
			coche.setToolTip(f"Montrer ou cacher les {PLURIELS[priorite]}, en {TEINTES[priorite]}")
			coche.setChecked(True)
			coche.toggled.connect(self._filtrer)
			self.cases[priorite] = coche
			barre.addWidget(coche)
		barre.addWidget(self.vue)
		barre.addWidget(self.loupe)
		barre.addWidget(self.zoom)
		self.precedent.clicked.connect(lambda: self._avancer(-1))
		self.suivant.clicked.connect(lambda: self._avancer(1))
		self.aujourd_hui.clicked.connect(self._revenir)
		self.vue.activated.connect(lambda indice: self._changer_de_vue(VUES[indice][1]))
		self.zoom.activated.connect(lambda indice: self.zoomer(ZOOMS[indice]))
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
		# La hauteur d'une heure suit celle de la grille visible : elle change avec la fenêtre.
		self.defilement.viewport().installEventFilter(self)
		self.defilement.verticalScrollBar().valueChanged.connect(self._suivre_le_defilement)
		self.actualiser()
		self._ajuster_la_hauteur()

	def hauteur_heure(self) -> float:
		"""Les pixels d'une heure : la hauteur visible de la grille, moins le trait de minuit en bas, partagée entre
		les heures du zoom."""
		return max(HAUTEUR_MINIMALE, (self.defilement.viewport().height() - 1) / self.heures_visibles)

	def zoomer(self, heures: int) -> None:
		"""Montre ces heures dans la hauteur de la grille, en gardant l'heure du haut."""
		self.heures_visibles = heures
		self.zoom.setCurrentIndex(ZOOMS.index(heures))
		self._ajuster_la_hauteur()

	def zoomer_d_un_cran(self, plus_pres: bool) -> None:
		"""Le zoom voisin : moins d'heures, plus près, ou plus d'heures ; rien au-delà des bouts."""
		rang = ZOOMS.index(self.heures_visibles) + (-1 if plus_pres else 1)
		if 0 <= rang < len(ZOOMS):
			self.zoomer(ZOOMS[rang])

	def _ajuster_la_hauteur(self) -> None:
		"""La hauteur de la grille selon le zoom et la place visible, puis l'heure du haut à sa place, si la grille
		descend jusque-là ; sinon, le bas de la grille au bas de la place."""
		self._ajustement = True
		try:
			self.grille.setFixedHeight(int(24 * self.hauteur_heure()) + 1)
			# La barre de défilement prend aussitôt la nouvelle hauteur : la position suivante n'est pas
			# bornée par l'ancienne.
			self.defilement.setWidgetResizable(True)
			self.defilement.verticalScrollBar().setValue(round(self.heure_du_haut * self.hauteur_heure()))
		finally:
			self._ajustement = False
		self.grille.update()

	def _suivre_le_defilement(self, valeur: int) -> None:
		"""Défilée à la main ou à la molette, la grille a une autre heure en haut."""
		if not self._ajustement:
			self.heure_du_haut = valeur / self.hauteur_heure()

	def eventFilter(self, objet: QObject, evenement: QEvent) -> bool:
		if (objet is self.defilement.viewport()) and (evenement.type() == QEvent.Type.Resize):
			self._ajuster_la_hauteur()
		return False

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

	def premier_jour(self) -> date:
		"""Le premier jour que montre le calendrier : la base n'a plus rien d'avant la durée de péremption."""
		return self._aujourd_hui() - timedelta(days=preferences.peremption())

	def jours_perimes(self) -> list[date]:
		"""Les jours montrés d'avant le premier jour : grisés, vides."""
		return [jour for jour in self.jours() if jour < self.premier_jour()]

	def blocs(self) -> list[Bloc]:
		"""Les blocs des heures, des priorités cochées."""
		return [bloc for bloc in self._blocs if (not bloc.journee) and (self._montree(bloc.evenement.priorite))]

	def journee(self) -> list[Bloc]:
		"""Les blocs de la journée entière, des priorités cochées."""
		return [bloc for bloc in self._blocs if (bloc.journee) and (self._montree(bloc.evenement.priorite))]

	def bandes(self) -> list[Bande]:
		"""L'airplay des priorités cochées ; celui d'un événement effacé de la base est toujours montré."""
		return [bande for bande in self._bandes if (bande.priorite is None) or (self._montree(bande.priorite))]

	def _montree(self, priorite: Priorite) -> bool:
		return self.cases[priorite].isChecked()

	def actualiser(self) -> None:
		"""Relit la grille et l'airplay de la période, ramenée au premier jour si la péremption l'a dépassée."""
		self._borner()
		self._presenter()
		perimes = set(self.jours_perimes())
		jours = [jour for jour in self.jours() if jour not in perimes]
		self._blocs, self._bandes = [], []
		if jours != []:
			self._relire(jours)
		self._filtrer()

	def _relire(self, jours: list[date]) -> None:
		de, a = minuit(jours[0]), minuit(jours[-1] + UN_JOUR)
		with self.connexion.transaction():
			evenements = lire_grille(self.connexion, supprimes=True)
			noms_publics = {
				int(str(identifiant)): texte_ou_rien(nom_public)
				for identifiant, nom_public in self.connexion.execute("SELECT id, public_name FROM events")
			}
			passages = lire_passages(self.connexion, de, a, minuit(self.premier_jour()))
		self._blocs = decouper(prevoir(evenements, de, a), jours, noms_publics)
		self._bandes = bandes(passages, jours, self.maintenant())

	def _filtrer(self) -> None:
		self.entete.relire()
		self.grille.update()

	def _avancer(self, sens: int) -> None:
		self._debut += sens * timedelta(days=len(self.jours()))
		self.actualiser()

	def _revenir(self) -> None:
		self._debut = self._aujourd_hui()
		if self._semaine:
			self._debut = self._lundi(self._debut)
		self.actualiser()

	def _changer_de_vue(self, semaine: bool) -> None:
		"""La vue jour montre aujourd'hui s'il est dans la semaine montrée, sinon son lundi."""
		aujourd_hui = self._aujourd_hui()
		if semaine:
			self._debut = self._lundi(self._debut)
		elif aujourd_hui in self.jours():
			self._debut = aujourd_hui
		self._semaine = semaine
		self.actualiser()

	# ─── Sessions sautées (https://github.com/dascritch/machincast/issues/273) ───

	def sauter(self, bloc: Bloc) -> None:
		"""Saute la session du bloc."""
		debut = bloc.prevue.occurrence.debut
		assert debut is not None
		self._sauter(bloc.evenement, [debut])

	def sauter_jusqu_au(self, bloc: Bloc) -> None:
		"""Saute la session du bloc, et les suivantes jusqu'au jour choisi, compris."""
		debut = bloc.prevue.occurrence.debut
		assert debut is not None
		nom = bloc.evenement.nom
		texte = f"Sauter les sessions de « {nom} » à partir du {jour_et_mois(debut.date())}, jusqu'au :"
		dernier = dialogues.choisir_jour(self, "Sauter des sessions", texte, debut.date())
		if dernier is None:
			return
		# Les sessions déjà sautées le restent, sans compter de nouveau.
		a_sauter = [
			depart
			for depart, _fin in sessions(bloc.evenement, debut.date(), dernier + UN_JOUR)
			if depart.date() not in bloc.evenement.sautees
		]
		self._sauter(bloc.evenement, a_sauter)

	def _sauter(self, evenement: Evenement, debuts: list[datetime]) -> None:
		with self.connexion.transaction():
			for debut in debuts:
				self.connexion.execute(
					"INSERT INTO event_skips (event_id, day) VALUES (%s, %s) ON CONFLICT DO NOTHING",
					(evenement.id, debut.date()),
				)
		premier, dernier = debuts[0], debuts[-1]
		texte = f"Session de « {evenement.nom} » du {jour_et_mois(premier.date())} à {premier:%H:%M} sautée."
		if len(debuts) > 1:
			texte = (
				f"{len(debuts)} sessions de « {evenement.nom} » sautées, du {jour_et_mois(premier.date())}"
				f" au {jour_et_mois(dernier.date())}."
			)
		self._grille_changee(texte)

	def retablir(self, bloc: Bloc) -> None:
		"""Rétablit la session sautée du bloc, sauf si un événement de même priorité a pris sa place
		(machincast.interface.sessions)."""
		occurrence = bloc.prevue.occurrence
		assert occurrence.debut is not None
		session = Session(occurrence.evenement, occurrence.debut, occurrence.fin)
		nom, jour = session.evenement.nom, session.debut.date()
		with self.connexion.transaction():
			trouve = chevauchee(self.connexion, session, self.maintenant())
			if trouve is None:
				retablir(self.connexion, session)
		if trouve is not None:
			autre, instant = trouve
			self.annonce.emit(
				f"Session de « {nom} » du {jour_et_mois(jour)} non rétablie : elle chevaucherait"
				f" « {autre.nom} » à {instant:%H:%M}."
			)
			return
		self._grille_changee(f"Session de « {nom} » du {jour_et_mois(jour)} à {session.debut:%H:%M} rétablie.")

	def _grille_changee(self, texte: str) -> None:
		self.actualiser()
		self.annonce.emit(texte)
		self.grille_modifiee.emit()

	def _borner(self) -> None:
		"""Une période tout entière d'avant le premier jour, après une durée de péremption raccourcie, revient à
		celle du premier jour."""
		premier = self.premier_jour()
		if self.jours()[-1] >= premier:
			return
		self._debut = premier
		if self._semaine:
			self._debut = self._lundi(premier)

	def _presenter(self) -> None:
		periode = timedelta(days=len(self.jours()))
		aujourd_hui = self._aujourd_hui()
		self.titre.setText(date_longue(self._debut))
		self.precedent.setToolTip("Jour précédent")
		self.suivant.setToolTip("Jour suivant")
		if self._semaine:
			self.titre.setText(titre_de_semaine(self._debut))
			self.precedent.setToolTip("Semaine précédente")
			self.suivant.setToolTip("Semaine suivante")
		# Une période se montre tant qu'elle touche les jours d'après le premier, et les PORTEE jours après aujourd'hui.
		self.precedent.setEnabled(self._debut - timedelta(days=1) >= self.premier_jour())
		self.suivant.setEnabled(self._debut + periode <= aujourd_hui + PORTEE)
		self.vue.setCurrentIndex([semaine for _texte, semaine in VUES].index(self._semaine))


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
			_infobulle(self, evenement, self._bloc_en(QPointF(evenement.pos())), self.calendrier.maintenant())
			return True
		return super().event(evenement)

	def mouseDoubleClickEvent(self, evenement: QMouseEvent) -> None:
		_ouvrir(self.calendrier, self._bloc_en(evenement.position()))

	def menu_en(self, point: QPointF) -> QMenu | None:
		return _menu(self.calendrier, self._bloc_en(point), self)

	def contextMenuEvent(self, evenement: QContextMenuEvent) -> None:
		menu = self.menu_en(QPointF(evenement.pos()))
		if menu is not None:
			menu.exec(evenement.globalPos())

	def paintEvent(self, _evenement: QPaintEvent) -> None:
		peintre = QPainter(self)
		jours = self.calendrier.jours()
		x = _x_des_jours(self, len(jours))
		peintre.setPen(self.palette().text().color())
		perimes = self.calendrier.jours_perimes()
		for indice, jour in enumerate(jours):
			cadre = QRectF(x[indice], 0, x[indice + 1] - x[indice], HAUTEUR_NOMS)
			couleur = self.palette().text().color()
			if jour in perimes:
				couleur = self.palette().placeholderText().color()
				peintre.fillRect(QRectF(x[indice], 0, x[indice + 1] - x[indice], self.height()), PERIME)
			peintre.setPen(couleur)
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
		self.setMouseTracking(True)

	def _x(self) -> list[float]:
		return _x_des_jours(self, len(self.calendrier.jours()))

	def _y(self, jour: date, moment: datetime) -> float:
		return (moment - minuit(jour)) / timedelta(hours=1) * self.calendrier.hauteur_heure()

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
				return minuit(jour) + timedelta(hours=point.y() / self.calendrier.hauteur_heure())
		return None

	def event(self, evenement: QEvent) -> bool:
		if (isinstance(evenement, QHelpEvent)) and (evenement.type() == QEvent.Type.ToolTip):
			_infobulle(self, evenement, self.element_en(QPointF(evenement.pos())), self.calendrier.maintenant())
			return True
		return super().event(evenement)

	def mouseDoubleClickEvent(self, evenement: QMouseEvent) -> None:
		_ouvrir(self.calendrier, self.element_en(evenement.position()))

	def menu_en(self, point: QPointF) -> QMenu | None:
		element = self.element_en(point)
		if not isinstance(element, Bloc):
			return None
		return _menu(self.calendrier, element, self)

	def contextMenuEvent(self, evenement: QContextMenuEvent) -> None:
		menu = self.menu_en(QPointF(evenement.pos()))
		if menu is not None:
			menu.exec(evenement.globalPos())

	def wheelEvent(self, evenement: QWheelEvent) -> None:
		"""Maj + molette passe au zoom voisin : vers le haut, plus près ; sans Maj, la grille défile."""
		if not evenement.modifiers() & Qt.KeyboardModifier.ShiftModifier:
			super().wheelEvent(evenement)
			return
		# Avec Maj, certains bureaux donnent la molette à l'horizontale.
		angle = evenement.angleDelta()
		cran = (angle.y()) or (angle.x())
		if cran != 0:
			self.calendrier.zoomer_d_un_cran(cran > 0)
		evenement.accept()

	def mousePressEvent(self, evenement: QMouseEvent) -> None:
		"""Une heure libre, pas encore passée, propose un événement sur l'heure entière : 13:00 – 14:00 pour 13:37. Le
		créneau d'une session sautée est libre."""
		element = self.element_en(evenement.position())
		libre = (element is None) or ((isinstance(element, Bloc)) and (element.sautee))
		if (evenement.button() != Qt.MouseButton.LeftButton) or (not libre):
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
		hauteur_heure = self.calendrier.hauteur_heure()
		for heure in range(25):
			y = heure * hauteur_heure
			peintre.drawLine(QPointF(MARGE, y), QPointF(x[-1], y))
			if heure < 24:
				peintre.setPen(self.palette().text().color())
				peintre.drawText(QRectF(0, y, MARGE - ECART, 16), Qt.AlignmentFlag.AlignRight, f"{heure:02d}:00")
				peintre.setPen(ligne)
		for bord in x:
			peintre.drawLine(QPointF(bord, 0), QPointF(bord, 24 * hauteur_heure))
		for bloc in self.calendrier.blocs():
			_peindre_bloc(peintre, self.rectangle(bloc), bloc, self._part_des_heures)
		maintenant = self.calendrier.maintenant()
		for jour in self.calendrier.jours_perimes():
			indice = jours.index(jour)
			peintre.fillRect(QRectF(x[indice], 0, x[indice + 1] - x[indice], 24 * hauteur_heure), PERIME)
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
	"""Estompé là où il ne joue pas, plein là où il joue, avec son nom ; hachuré pour une session sautée."""
	couleur = COULEURS[bloc.evenement.priorite]
	estompee = QColor(couleur)
	estompee.setAlpha(ESTOMPE)
	peintre.fillRect(cadre, estompee)
	if bloc.sautee:
		peintre.fillRect(cadre, QBrush(couleur.darker(140), Qt.BrushStyle.BDiagPattern))
	for debut, fin in bloc.joue:
		peintre.fillRect(part(cadre, bloc, debut, fin), couleur)
	peintre.setPen(QPen(couleur.darker(140)))
	peintre.setBrush(QBrush())
	peintre.drawRect(cadre)
	peintre.setPen(TEXTE)
	peintre.drawText(
		cadre.adjusted(3, 1, -2, -1), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, bloc.evenement.nom
	)


def _infobulle(widget: QWidget, evenement: QHelpEvent, element: Bloc | Bande | None, maintenant: datetime) -> None:
	if element is None:
		QToolTip.hideText()
		evenement.ignore()
		return
	texte = element.infobulle()
	if isinstance(element, Bloc):
		texte = element.infobulle_a(maintenant)
	QToolTip.showText(evenement.globalPos(), texte, widget)


def _a_venir(bloc: Bloc, maintenant: datetime) -> bool:
	"""Une session pas encore commencée, d'un événement récurrent qui n'est pas supprimé : elle se saute, ou se
	rétablit."""
	occurrence = bloc.prevue.occurrence
	evenement = occurrence.evenement
	return (
		(occurrence.debut is not None)
		and (occurrence.debut > maintenant)
		and (evenement.jours != frozenset())
		and (evenement.supprime_le is None)
	)


def _menu(calendrier: "Calendrier", bloc: Bloc | None, parent: QWidget) -> QMenu | None:
	"""Le menu du clic droit sur un bloc : sauter une session à venir, ou la rétablir ; aucun pour un autre bloc."""
	if (bloc is None) or (not _a_venir(bloc, calendrier.maintenant())):
		return None
	menu = QMenu(parent)
	if bloc.sautee:
		menu.addAction(RETABLIR).triggered.connect(lambda: calendrier.retablir(bloc))
		return menu
	menu.addAction(SAUTER).triggered.connect(lambda: calendrier.sauter(bloc))
	menu.addAction(SAUTER_JUSQU_AU).triggered.connect(lambda: calendrier.sauter_jusqu_au(bloc))
	return menu


def _ouvrir(calendrier: Calendrier, element: Bloc | Bande | None) -> None:
	if isinstance(element, Bloc):
		calendrier.ouverte.emit("événement", element.evenement.id, element.evenement.nom)
	if (isinstance(element, Bande)) and (element.evenement_id is not None):
		calendrier.ouverte.emit("événement", element.evenement_id, element.nom)
