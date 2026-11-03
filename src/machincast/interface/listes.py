"""Listes filtrables des sonores, des banques, des séquences et des événements
(https://github.com/dascritch/machincast/issues/26, spec § 8.2).

Chaque liste est un onglet de la fenêtre (machincast.interface.fenetre). Elle se lit en base avec le rôle de
l'interface, chaque fois que son onglet s'ouvre : jamais en boucle. Le filtre garde les lignes dont une colonne contient
le texte tapé, sans tenir compte des majuscules ni des accents. Ouvrir une ligne (double-clic ou Entrée) demande
l'écran de détail de l'élément (signal ouverte). Une liste peut avoir un bouton qui crée un élément
(signal creation_demandee) : « Nouvelle banque » (https://github.com/dascritch/machincast/issues/31). Une ligne en
anomalie a une infobulle qui l'explique, et le compte les dénombre (https://github.com/dascritch/machincast/issues/138,
https://github.com/dascritch/machincast/issues/140) : une séquence ou un événement vide, une banque sans sonore actif,
une banque qui contient un sonore erroné ou non supporté, et ce sonore. Les listes des événements, des séquences, des
banques et des sonores la marquent de ⚠️ dans leur première colonne, COLONNE_D_ANOMALIE
(https://github.com/dascritch/machincast/issues/327).
Le clic droit sur une ligne d'événement, de séquence ou de banque propose « Dupliquer » (signal duplication_demandee,
https://github.com/dascritch/machincast/issues/130). Les listes des sonores et des banques sélectionnent plusieurs
lignes (Ctrl, Maj) ; leur clic droit propose les actions sur la sélection, ou sur la seule ligne cliquée hors de la
sélection (signal action_demandee, machincast.interface.groupes, https://github.com/dascritch/machincast/issues/114).
"""

import logging
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView, QLabel, QLineEdit, QMenu, QTableView, QWidget

from machincast.interface import affichage, groupes
from machincast.interface.colonnes import Colonnes
from machincast.interface.depot import DepotDeFichiers
from machincast.interface.intentions import AJOUTER, libelle
from machincast.interface.ui.liste import Ui_Liste
from machincast.lecture.grille import JOURS, NOMS_DES_JOURS

journal = logging.getLogger(__name__)

Connexion = psycopg.Connection[TupleRow]
IDENTIFIANT = Qt.ItemDataRole.UserRole
"""Rôle qui porte, sur la première cellule d'une ligne, l'identifiant de l'élément en base."""
TRI = IDENTIFIANT + 2
"""Rôle de chaque cellule par lequel la liste se trie : son texte, sauf quand la ligne en donne un autre
(Ligne.tris)."""
ETATS = {
	"preview": "aperçu",
	"active": "actif",
	"disabled": "désactivé",
	"expired": "expiré",
	"corrupt": "erroné",
	"unsupported": "non supporté",
	"missing": "supprimé",
}
TYPES = {"file": "fichier", "stream": "stream"}
"""Le type d'un sonore à l'écran, par sa valeur en base (https://github.com/dascritch/machincast/issues/358)."""
PRIORITES = {"special": "spécial", "show": "émission", "background_programming": "fil musical", "fallback": "secours"}
IMPORTANCE = {priorite: rang for rang, priorite in enumerate(PRIORITES)}
APRES_TOUT = float("inf")
"""Clé de tri d'une durée ou d'une date inconnue : après les autres (https://github.com/dascritch/machincast/issues/302)."""
SANS_DUREE = 1e12
"""Clé de tri d'un fichier dont la durée n'est pas encore mesurée : après les durées connues, avant les streams."""
SANS_JOUR = "~"
"""Clé de tri d'un événement sans récurrence : après les jours, que leurs chiffres classent."""
"""Le tri de la colonne « Priorité » : du plus important au moins important, jamais par ordre alphabétique
(https://github.com/dascritch/machincast/issues/272)."""
MODES = {"sequential": "séquentielle", "random": "aléatoire"}
SEQUENCE_VIDE = "Séquence vide : elle ne joue rien, et un événement qui l'appelle passe à son élément suivant."
_RELAIS = "Événement vide : il ne joue rien, et l'événement de priorité inférieure prend le relais pendant sa plage."
EVENEMENT_VIDE = {
	"special": _RELAIS,
	"show": _RELAIS,
	"background_programming": (
		"Événement vide : il ne joue rien, et la diffusion se tait, avec une alerte, quand il est à l'antenne."
	),
	"fallback": "Événement vide : il ne joue rien, et l'événement de priorité inférieure remplace le stream tombé.",
}
"""Ce que fait la diffusion d'un événement vide, selon sa priorité (spec § 4.2,
https://github.com/dascritch/machincast/issues/140)."""
BANQUE_SANS_SONORE_ACTIF = (
	"Banque sans sonore actif : elle ne fournit rien, et l'élément qui l'appelle passe à son élément suivant."
)


def banque_aux_sonores_en_anomalie(nombre: int) -> str:
	"""Une banque qui a des sonores actifs, mais aussi des sonores erronés ou non supportés : ceux-là ne passent pas."""
	if nombre == 1:
		return "Banque avec 1 sonore erroné ou non supporté : la diffusion ne le joue pas."
	return f"Banque avec {nombre} sonores erronés ou non supportés : la diffusion ne les joue pas."


SONORE_EN_ANOMALIE = {
	"corrupt": "Sonore erroné : son fichier est illisible ou endommagé, et la diffusion ne le joue pas.",
	"unsupported": "Sonore non supporté : son fichier n'est pas un son lisible, et la diffusion ne le joue pas.",
}
"""Les états d'un sonore que la diffusion ne joue pas sans que personne l'ait voulu (spec § 3.1, § 4.5)."""
COLONNE_D_ANOMALIE = "⚠️"
"""Titre de la première colonne des listes en anomalie, et ce qu'elle montre sur une ligne en anomalie
(https://github.com/dascritch/machincast/issues/327)."""
INFOBULLE_D_ANOMALIE = "Anomalie : la ligne a un problème, que dit son infobulle"


@dataclass(frozen=True)
class Ligne:
	identifiant: int
	nom: str
	"""Nom de l'élément, pour l'annoncer."""
	cellules: list[str]
	anomalie: str = ""
	"""Ce qui ne va pas, en une phrase, pour l'infobulle de la ligne ; rien pour une ligne saine."""
	tris: dict[int, int | float | str] = field(default_factory=dict)
	"""Par colonne, la clé de tri d'une cellule qui ne se trie pas par son texte (TRI)."""


@dataclass(frozen=True)
class Source:
	"""Un type d'élément : ses colonnes, sa lecture en base, et les mots pour le compter."""

	genre: str
	colonnes: tuple[str, ...]
	lire: Callable[[Connexion], list[Ligne]]
	singulier: str
	pluriel: str
	aucun: str
	nouveau: str = ""
	"""Texte du bouton qui crée un élément de ce type ; aucun bouton sans texte."""
	fichiers: str = ""
	"""Texte du bouton qui ajoute des fichiers, qui se déposent aussi sur la liste ; ni bouton ni dépôt sans texte."""
	duplicable: bool = False
	"""Le clic droit sur une ligne propose « Dupliquer »."""
	anomalies: bool = False
	"""Une première colonne, COLONNE_D_ANOMALIE, marque les lignes en anomalie."""


def _texte(valeur: object) -> str:
	if valeur is None:
		return ""
	return str(valeur)


def _date(valeur: object) -> str:
	if not isinstance(valeur, datetime):
		return ""
	return f"{valeur.astimezone():%Y-%m-%d %H:%M}"


COLONNES_DES_SONORES = ("Artiste", "Titre", "Type", "État", "Durée", "Emplacement")
POSITION_DE_LA_DUREE = COLONNES_DES_SONORES.index("Durée")


def lire_sonores(connexion: Connexion) -> list[Ligne]:
	with connexion.transaction():
		rangees = connexion.execute(
			"SELECT s.id, s.artist, s.title, s.type::text, s.state::text, s.audit_requested, s.duration,"
			" COALESCE(s.location, s.stream_url, m.url)"
			" FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.deleted_at IS NULL"
			" ORDER BY s.artist NULLS LAST, s.title, s.id"
		).fetchall()
	lignes = []
	for identifiant, artiste, titre, type_sonore, etat, audit_demande, duree, emplacement in rangees:
		texte_duree = ""
		if type_sonore == "stream":
			texte_duree = affichage.duree(None)
		elif isinstance(duree, timedelta):
			texte_duree = affichage.duree(duree)
		texte_etat = ETATS.get(str(etat), str(etat))
		if audit_demande is True:
			# https://github.com/dascritch/machincast/issues/114
			texte_etat = f"{texte_etat}, audit demandé"
		# Les durées d'une banque ne se signalent que dans sa fiche, et parmi les relations du sonore, jamais ici
		# (https://github.com/dascritch/machincast/issues/210).
		cellules = [
			_texte(artiste),
			_texte(titre),
			TYPES.get(str(type_sonore), str(type_sonore)),
			texte_etat,
			texte_duree,
		]
		cellules.append(_texte(emplacement))
		# https://github.com/dascritch/machincast/issues/302 : par les secondes ; sans durée mesurée, après les durées
		# connues ; un stream, sans fin, en dernier.
		tri_duree: float = SANS_DUREE
		if type_sonore == "stream":
			tri_duree = APRES_TOUT
		elif isinstance(duree, timedelta):
			tri_duree = duree.total_seconds()
		nom_du_sonore = (_texte(titre)) or (_texte(emplacement))
		anomalie = SONORE_EN_ANOMALIE.get(str(etat), "")
		tris: dict[int, int | float | str] = {POSITION_DE_LA_DUREE: tri_duree}
		lignes.append(Ligne(int(str(identifiant)), nom_du_sonore, cellules, anomalie, tris))
	return lignes


def lire_banques(connexion: Connexion) -> list[Ligne]:
	with connexion.transaction():
		rangees = connexion.execute(
			"SELECT b.id, b.internal_name, b.public_name, b.mode::text, b.no_repeat,"
			" (SELECT min(r.directory) FROM bank_directories r WHERE r.bank_id = b.id),"
			" NOT EXISTS (SELECT 1 FROM bank_sounds x JOIN sounds s ON s.id = x.sound_id"
			" WHERE x.bank_id = b.id AND s.state = 'active' AND s.deleted_at IS NULL),"
			" (SELECT count(*) FROM bank_sounds x JOIN sounds s ON s.id = x.sound_id"
			" WHERE x.bank_id = b.id AND s.state IN ('corrupt', 'unsupported') AND s.deleted_at IS NULL)"
			" FROM banks b WHERE b.deleted_at IS NULL ORDER BY b.internal_name, b.id"
		).fetchall()
	lignes = []
	for identifiant, nom, nom_public, mode, marquee, repertoire, sans_sonore_actif, en_anomalie in rangees:
		cellules = [str(nom), _texte(nom_public), MODES.get(str(mode), str(mode))]
		cellules += [affichage.oui_non(bool(marquee)), _texte(repertoire)]
		anomalie = ""
		if sans_sonore_actif:
			anomalie = BANQUE_SANS_SONORE_ACTIF
		elif int(str(en_anomalie)) > 0:
			anomalie = banque_aux_sonores_en_anomalie(int(str(en_anomalie)))
		lignes.append(Ligne(int(str(identifiant)), str(nom), cellules, anomalie))
	return lignes


def lire_sequences(connexion: Connexion) -> list[Ligne]:
	with connexion.transaction():
		rangees = connexion.execute(
			"SELECT q.id, q.internal_name, q.public_name,"
			" NOT EXISTS (SELECT 1 FROM sequence_items e WHERE e.sequence_id = q.id)"
			" FROM sequences q WHERE q.deleted_at IS NULL ORDER BY q.internal_name, q.id"
		).fetchall()
	lignes = []
	for identifiant, nom, nom_public, vide in rangees:
		cellules = [str(nom), _texte(nom_public), ""]
		anomalie = ""
		if vide:
			cellules[2] = "séquence vide"
			anomalie = SEQUENCE_VIDE
		lignes.append(Ligne(int(str(identifiant)), str(nom), cellules, anomalie))
	return lignes


def lire_feeds(connexion: Connexion) -> list[Ligne]:
	"""Par nom, avec le nombre de streams qui suivent chacun (https://github.com/dascritch/machincast/issues/34)."""
	with connexion.transaction():
		rangees = connexion.execute(
			"SELECT m.id, m.name, m.url,"
			" (SELECT count(*) FROM sounds s WHERE s.feed_id = m.id AND s.deleted_at IS NULL)"
			" FROM feeds m ORDER BY m.name, m.id"
		).fetchall()
	return [
		Ligne(int(str(identifiant)), str(nom), [str(nom), str(url), str(streams)])
		for identifiant, nom, url, streams in rangees
	]


COLONNES_DES_EVENEMENTS = ("Nom", "Nom public", "Priorité", "Début", "Fin", "Récurrence", "Anomalie")
POSITION_DE_LA_PRIORITE = COLONNES_DES_EVENEMENTS.index("Priorité")
POSITION_DU_DEBUT = COLONNES_DES_EVENEMENTS.index("Début")
POSITION_DE_LA_FIN = COLONNES_DES_EVENEMENTS.index("Fin")
POSITION_DE_LA_RECURRENCE = COLONNES_DES_EVENEMENTS.index("Récurrence")


def _instant(valeur: object) -> float:
	"""Clé de tri d'une date : son instant ; sans date, après les autres."""
	if not isinstance(valeur, datetime):
		return APRES_TOUT
	return valeur.timestamp()


def _jours(valeur: object) -> str:
	"""Clé de tri d'une récurrence : le rang de ses jours, du lundi au dimanche, « 01 » pour lundi et mardi ; sans
	jour, après les autres."""
	if (not isinstance(valeur, list)) or (valeur == []):
		return SANS_JOUR
	return "".join(sorted(str(JOURS.index(str(jour))) for jour in valeur))


def lire_evenements(connexion: Connexion) -> list[Ligne]:
	"""Du plus prioritaire au moins prioritaire, puis par nom."""
	with connexion.transaction():
		rangees = connexion.execute(
			"SELECT e.id, e.internal_name, e.public_name, e.priority::text, e.starts_at, e.ends_at,"
			" e.recurrence_days::text[],"
			" NOT EXISTS (SELECT 1 FROM event_items x WHERE x.event_id = e.id)"
			# e.priorite : l'ordre du type énuméré, pas celui du texte de la colonne affichée.
			" FROM events e WHERE e.deleted_at IS NULL ORDER BY e.priority DESC, e.internal_name, e.id"
		).fetchall()
	lignes = []
	for identifiant, nom, nom_public, priorite, debut, fin, jours, vide in rangees:
		recurrence = ""
		if isinstance(jours, list):
			recurrence = ", ".join(NOMS_DES_JOURS[JOURS.index(str(jour))] for jour in jours)
		cellules = [str(nom), _texte(nom_public), PRIORITES.get(str(priorite), str(priorite)), _date(debut), _date(fin)]
		cellules += [recurrence, ""]
		anomalie = ""
		if vide:
			cellules[-1] = "événement vide"
			anomalie = EVENEMENT_VIDE[str(priorite)]
		tris: dict[int, int | float | str] = {
			POSITION_DE_LA_PRIORITE: IMPORTANCE.get(str(priorite), len(IMPORTANCE)),
			POSITION_DU_DEBUT: _instant(debut),
			POSITION_DE_LA_FIN: _instant(fin),
			POSITION_DE_LA_RECURRENCE: _jours(jours),
		}
		lignes.append(Ligne(int(str(identifiant)), str(nom), cellules, anomalie, tris))
	return lignes


SONORES = Source(
	"sonore",
	COLONNES_DES_SONORES,
	lire_sonores,
	"sonore",
	"sonores",
	"aucun sonore",
	"Nouveau stream",
	libelle(AJOUTER, "Ajouter des fichiers…"),
	anomalies=True,
)
BANQUES = Source(
	"banque",
	("Nom", "Nom public", "Mode", "Ne pas répéter", "Répertoire"),
	lire_banques,
	"banque",
	"banques",
	"aucune banque",
	"Nouvelle banque",
	duplicable=True,
	anomalies=True,
)
SEQUENCES = Source(
	"séquence",
	("Nom", "Nom public", "Anomalie"),
	lire_sequences,
	"séquence",
	"séquences",
	"aucune séquence",
	"Nouvelle séquence",
	duplicable=True,
	anomalies=True,
)
EVENEMENTS = Source(
	"événement",
	COLONNES_DES_EVENEMENTS,
	lire_evenements,
	"événement",
	"événements",
	"aucun événement",
	"Nouvel événement",
	duplicable=True,
	anomalies=True,
)
FEEDS = Source(
	"feed",
	("Nom", "Adresse", "Streams"),
	lire_feeds,
	"feed",
	"feeds",
	"aucun feed",
	"Nouveau feed",
)


def nom_de_vue(texte: str) -> str:
	"""« feeds », « evenements » : sans accents, ni majuscules, ni espaces."""
	return sans_accents(texte).replace(" ", "-")


def sans_accents(texte: str) -> str:
	"""Le texte en minuscules, sans accents ni cédilles : « Été » donne « ete »."""
	decompose = unicodedata.normalize("NFKD", texte.casefold())
	return "".join(lettre for lettre in decompose if not unicodedata.combining(lettre))


class FiltreSansAccents(QSortFilterProxyModel):
	"""Garde les lignes dont une colonne contient le texte, sans tenir compte des majuscules ni des accents."""

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._texte = ""

	def filtrer(self, texte: str) -> None:
		self.beginFilterChange()
		self._texte = sans_accents(texte)
		self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

	def filterAcceptsRow(self, rangee: int, parent: QModelIndex | QPersistentModelIndex) -> bool:
		modele = self.sourceModel()
		for colonne in range(modele.columnCount()):
			valeur = modele.index(rangee, colonne, parent).data()
			if self._texte in sans_accents(str((valeur) or (""))):
				return True
		return False


class Liste(QWidget):
	ouverte = Signal(str, int, str)
	"""Ligne ouverte : genre, identifiant et nom de l'élément."""
	creation_demandee = Signal(str)
	"""Bouton de création cliqué : genre de l'élément à créer."""
	ajout_demande = Signal()
	"""Bouton d'ajout de fichiers cliqué."""
	fichiers_deposes = Signal(list)
	"""Fichiers déposés sur la liste (list[Path]) : https://github.com/dascritch/machincast/issues/30."""
	duplication_demandee = Signal(str, int)
	"""« Dupliquer » choisi au clic droit sur une ligne : genre et identifiant de l'élément."""
	action_demandee = Signal(str, list)
	"""Une action choisie au clic droit (machincast.interface.groupes) : sa clé, et les éléments (list[int])."""
	preecoute_demandee = Signal(int)
	"""« Pré-écoute… » choisi au clic droit sur une ligne de la liste des sonores : le sonore de cette ligne
	(https://github.com/dascritch/machincast/issues/226)."""

	def __init__(
		self,
		source: Source,
		connexion: Connexion,
		parent: QWidget | None = None,
		actions: bool = True,
		vue: str | None = None,
	) -> None:
		"""vue : le nom sous lequel ses colonnes sont gardées ; par défaut, « liste- » suivi du pluriel du genre
		({I})."""
		"""actions : les boutons de création et d'ajout, et le dépôt de fichiers ; pas dans un choix d'éléments."""
		super().__init__(parent)
		self.source = source
		self.connexion = connexion
		self.ui = Ui_Liste()
		self.ui.setupUi(self)
		titres = list(source.colonnes)
		if source.anomalies:
			titres.insert(0, COLONNE_D_ANOMALIE)
		self.modele = QStandardItemModel(0, len(titres), self)
		self.modele.setHorizontalHeaderLabels(titres)
		if source.anomalies:
			self.modele.setHeaderData(0, Qt.Orientation.Horizontal, INFOBULLE_D_ANOMALIE, Qt.ItemDataRole.ToolTipRole)
		self.proxy = FiltreSansAccents(self)
		self.proxy.setSourceModel(self.modele)
		self.proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
		self.proxy.setSortRole(TRI)
		self.table.setModel(self.proxy)
		entete = self.table.horizontalHeader()
		if vue is None:
			vue = f"liste-{nom_de_vue(source.pluriel)}"
		self.colonnes = Colonnes(self.table, vue)
		# Un clic sur un titre de colonne trie la liste ; avant, elle garde l'ordre de la base.
		self.table.setSortingEnabled(True)
		entete.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
		self.filtre.textChanged.connect(self._filtrer)
		self.table.activated.connect(self._ouvrir)
		self.ui.nouveau.setText(source.nouveau)
		self.ui.nouveau.setVisible((actions) and (source.nouveau != ""))
		self.ui.nouveau.clicked.connect(lambda: self.creation_demandee.emit(source.genre))
		self.ui.ajouter_fichiers.setText(source.fichiers)
		self.ui.ajouter_fichiers.setVisible((actions) and (source.fichiers != ""))
		self.ui.ajouter_fichiers.clicked.connect(self.ajout_demande)
		if (actions) and (source.fichiers != ""):
			self.depot = DepotDeFichiers(self.table)
			self.depot.deposes.connect(self.fichiers_deposes)
		self.duplicable = (actions) and (source.duplicable)
		self.actions_groupees: tuple[groupes.Action, ...] = ()
		"""Les actions sur la sélection ; aucune hors des listes des sonores et des banques, ou dans un choix."""
		if actions:
			self.actions_groupees = groupes.ACTIONS.get(source.genre, ())
		if self.actions_groupees != ():
			self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
		self.preecoutable = (actions) and (source.genre == "sonore")
		"""La liste des sonores, hors d'un choix : le clic droit sur une ligne en propose la pré-écoute."""
		self.menu_de_l_element: Callable[[QMenu, int, str], None] | None = None
		"""Des entrées que la fenêtre ajoute au clic droit sur une ligne : le menu, l'élément et son nom. Celles
		d'un feed, sa pré-écoute et la coupure de l'antenne par lui (https://github.com/dascritch/machincast/issues/323)."""
		self.colonnes.menu_des_lignes = lambda position: self.menu_de_la_ligne(self.table.indexAt(position))
		self._compter()

	@property
	def filtre(self) -> QLineEdit:
		return self.ui.filtre

	@property
	def compte(self) -> QLabel:
		return self.ui.compte

	@property
	def table(self) -> QTableView:
		return self.ui.table

	def actualiser(self) -> None:
		"""Relit la liste en base ; une base injoignable laisse la liste telle qu'elle était."""
		try:
			lignes = self.source.lire(self.connexion)
		except psycopg.Error as erreur:
			journal.error(f"liste des {self.source.pluriel} illisible : {erreur}")
			return
		self.modele.setRowCount(0)
		for ligne in lignes:
			cellules = [QStandardItem(texte) for texte in ligne.cellules]
			for colonne, cellule in enumerate(cellules):
				cellule.setData(ligne.tris.get(colonne, cellule.text()), TRI)
			if self.source.anomalies:
				marque = ""
				if ligne.anomalie:
					marque = COLONNE_D_ANOMALIE
				cellules.insert(0, QStandardItem(marque))
				cellules[0].setData(marque, TRI)
				cellules[0].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			cellules[0].setData(ligne.identifiant, IDENTIFIANT)
			cellules[0].setData(ligne.nom, IDENTIFIANT + 1)
			if ligne.anomalie:
				for cellule in cellules:
					cellule.setToolTip(ligne.anomalie)
			self.modele.appendRow(cellules)
		self._compter()

	def _filtrer(self, texte: str) -> None:
		self.proxy.filtrer(texte)
		self._compter()

	def _compter(self) -> None:
		total = self.modele.rowCount()
		visibles = self.proxy.rowCount()
		if self.filtre.text() != "":
			texte = f"{visibles} {self._mot(visibles)} sur {total}"
		elif total == 0:
			texte = self.source.aucun
		else:
			texte = f"{total} {self._mot(total)}"
		# Les lignes en anomalie parmi celles que montre le filtre.
		anomalies = sum(
			1 for rangee in range(visibles) if self.proxy.index(rangee, 0).data(Qt.ItemDataRole.ToolTipRole)
		)
		if anomalies > 0:
			texte = f"{texte}, dont {anomalies} en anomalie"
		self.compte.setText(texte)

	def _mot(self, nombre: int) -> str:
		if nombre > 1:
			return self.source.pluriel
		return self.source.singulier

	def selection(self) -> list[int]:
		"""Les éléments des lignes sélectionnées, dans l'ordre de la liste affichée."""
		rangees = sorted(index.row() for index in self.table.selectionModel().selectedRows())
		return [self._element(self.proxy.index(rangee, 0)) for rangee in rangees]

	def _element(self, index: QModelIndex) -> int:
		premiere = self.modele.index(self.proxy.mapToSource(index).row(), 0)
		return int(premiere.data(IDENTIFIANT))

	def menu_de_la_ligne(self, index: QModelIndex) -> QMenu | None:
		"""Le menu du clic droit sur cette ligne de la table : sur la sélection si elle en fait partie, sur elle seule
		sinon ; aucun hors d'une ligne, ou pour une liste sans actions. « Dupliquer » ne vaut que pour un élément.
		« Pré-écoute… », en tête, vaut pour la ligne cliquée seule, même dans une sélection."""
		sans_actions = (
			(not self.duplicable)
			and (self.actions_groupees == ())
			and (not self.preecoutable)
			and (self.menu_de_l_element is None)
		)
		if (not index.isValid()) or (sans_actions):
			return None
		cliquee = self._element(index)
		elements = self.selection()
		if cliquee not in elements:
			elements = [cliquee]
		menu = QMenu(self)
		if (self.duplicable) and (len(elements) == 1):
			dupliquer = menu.addAction("Dupliquer")
			dupliquer.triggered.connect(lambda: self.duplication_demandee.emit(self.source.genre, cliquee))
		for action in self.actions_groupees:
			entree = menu.addAction(action.texte)
			entree.triggered.connect(lambda _coche=False, cle=action.cle: self.action_demandee.emit(cle, elements))
		if self.preecoutable:
			affichage.proposer_la_preecoute(menu, cliquee, self.preecoute_demandee.emit)
		if self.menu_de_l_element is not None:
			premiere = self.modele.index(self.proxy.mapToSource(index).row(), 0)
			self.menu_de_l_element(menu, cliquee, str(premiere.data(IDENTIFIANT + 1)))
		return menu

	def _ouvrir(self, index: QModelIndex) -> None:
		premiere = self.modele.index(self.proxy.mapToSource(index).row(), 0)
		self.ouverte.emit(self.source.genre, int(premiere.data(IDENTIFIANT)), str(premiere.data(IDENTIFIANT + 1)))
