"""Liste ordonnée des éléments d'une séquence ou d'un événement (https://github.com/dascritch/machincast/issues/112,
https://github.com/dascritch/machincast/issues/32).

Commune aux fiches d'une séquence (machincast.interface.fiche_sequence) et d'un événement
(machincast.interface.fiche_evenement) :

- les éléments sont des sonores et des banques, et des séquences dans un événement ; un même élément peut revenir.
  Chaque ligne montre son genre, son nom (artiste et titre d'un sonore, le nom du fichier d'un sonore pas encore
  décodé, le nom interne d'une banque ou d'une séquence) et un détail ;
- ils se réordonnent par glisser-déposer, ou par « Monter » et « Descendre » ; une ligne ne se dépose pas dans une
  autre. Ils s'ajoutent parmi ceux déjà en base (machincast.interface.choix), ou par dépôt de fichiers sonores
  (machincast.interface.depot), toujours comme une copie ; un fichier pas encore en base devient un sonore à l'état
  aperçu à l'enregistrement seulement. Dans un événement, un marque-page choisi ajoute le premier stream, par titre, qui
  le suit ; sans stream qui le suive, un stream actif, titré du nom du marque-page, est créé à l'enregistrement, un
  seul par marque-page (https://github.com/dascritch/machincast/issues/167) ;
- une banque « ne pas répéter » appelée juste après elle-même est signalée : cet appel sera sauté à la diffusion
  (machincast.lecture.deroule.appels_ignores_aux_bords). Une séquence compte par la première et la dernière de ses
  lignes, quand ce sont des banques ;
- à l'enregistrement, une ligne restée dans la liste garde son identifiant en base, à sa nouvelle position :
  l'historique de diffusion la désigne pour reprendre la liste. Un élément effacé de la base entre-temps est oublié.
"""

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QMenu, QPushButton, QTreeWidget, QTreeWidgetItem

from machincast.conversion import entier_ou_rien, texte_ou_rien
from machincast.interface import affichage, dialogues
from machincast.interface.colonnes import Colonnes
from machincast.interface.depot import DepotDeFichiers
from machincast.interface.fiche import Fiche, fichiers_sonores
from machincast.interface.listes import MODES
from machincast.lecture.deroule import appels_ignores_aux_bords

GENRE = Qt.ItemDataRole.UserRole
"""Rôle qui porte, sur la première colonne d'une ligne, le genre de l'élément : « sonore », « banque », « séquence »."""
ELEMENT = Qt.ItemDataRole.UserRole + 1
"""Rôle qui porte l'identifiant de l'élément ; None pour un fichier déposé, pas encore en base."""
FICHIER = Qt.ItemDataRole.UserRole + 2
"""Rôle qui porte le chemin d'un fichier déposé, pas encore en base."""
LIGNE_EN_BASE = Qt.ItemDataRole.UserRole + 3
"""Rôle qui porte l'identifiant de la ligne en base ; None pour une ligne ajoutée."""
ENTREE = Qt.ItemDataRole.UserRole + 4
"""Rôle qui porte la banque par laquelle commence une ligne : la banque elle-même, la première ligne d'une séquence
si c'est une banque ; None sinon."""
SORTIE = Qt.ItemDataRole.UserRole + 5
"""Rôle qui porte la banque par laquelle finit une ligne, comme ENTREE."""
MARQUE_PAGE = Qt.ItemDataRole.UserRole + 6
"""Rôle qui porte le marque-page d'un stream à créer à l'enregistrement, faute de stream qui le suive."""
LIGNE = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDragEnabled
"""Une ligne se glisse, mais rien ne se dépose dedans : la liste reste à plat."""

COLONNES = {"sonore": "sonore_id", "banque": "banque_id", "séquence": "sequence_id"}
"""Colonne de chaque genre d'élément, dans sequences_elements et evenements_elements."""
TABLES = {"sonore": "sonores", "banque": "banques", "séquence": "sequences"}
LECTURES = {
	"sonore": (
		"SELECT s.id, s.artiste, s.titre, s.emplacement, COALESCE(s.emplacement, s.url_stream, m.url)"
		" FROM sonores s LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id WHERE s.id = ANY(%s)"
	),
	"banque": "SELECT b.id, b.nom_interne, b.mode::text, b.ne_pas_repeter FROM banques b WHERE b.id = ANY(%s)",
	"séquence": (
		"SELECT q.id, q.nom_interne, (SELECT count(*) FROM sequences_elements e WHERE e.sequence_id = q.id),"
		" (SELECT e.banque_id FROM sequences_elements e WHERE e.sequence_id = q.id ORDER BY e.position LIMIT 1),"
		" (SELECT e.banque_id FROM sequences_elements e WHERE e.sequence_id = q.id ORDER BY e.position DESC LIMIT 1)"
		" FROM sequences q WHERE q.id = ANY(%s)"
	),
}
"""Ce que montre la ligne d'un élément, lu par identifiants."""
SONORES_PAR_FICHIER = LECTURES["sonore"].replace("s.id = ANY(%s)", "s.emplacement = ANY(%s)")
STREAM_DU_MARQUE_PAGE = "SELECT id FROM sonores WHERE marque_page_id = %s ORDER BY titre, id LIMIT 1"
"""Le stream repris pour un marque-page : le premier par titre qui le suit."""
SAUTE = "ne passe jamais deux fois de suite : cet appel sera sauté."


@dataclass(frozen=True)
class Boutons:
	"""Les boutons qui agissent sur la liste : un bouton d'ajout par genre, et ceux de la ligne choisie."""

	ajouter: dict[str, QPushButton]
	retirer: QPushButton
	monter: QPushButton
	descendre: QPushButton


VUES = {"sequences_elements": "fiche-sequence-elements", "evenements_elements": "fiche-evenement-elements"}
"""Le nom de la vue des éléments, selon la table de la fiche (https://github.com/dascritch/machincast/issues/207)."""


class ListeElements(QObject):
	changee = Signal()
	"""Une ligne a été ajoutée, retirée ou déplacée : le glisser-déposer déplace en retirant, puis en insérant."""

	def __init__(
		self, fiche: Fiche, liste: QTreeWidget, boutons: Boutons, table: str, parent_colonne: str, remarque: str
	) -> None:
		"""table et parent_colonne : la table des éléments, et sa colonne qui désigne la séquence ou l'événement.
		remarque : celle des choix d'éléments, qu'un élément peut revenir."""
		super().__init__(fiche)
		self.fiche = fiche
		self.liste = liste
		self.boutons = boutons
		self.table = table
		self.parent_colonne = parent_colonne
		self.remarque = remarque
		self.marquees: dict[int, str] = {}
		"""Banques « ne pas répéter », par identifiant, avec leur nom."""
		self.colonnes = Colonnes(liste, VUES[table])
		liste.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
		self.depot = DepotDeFichiers(liste)
		self.depot.deposes.connect(self._deposer)
		modele = liste.model()
		for signal in (modele.rowsInserted, modele.rowsRemoved):
			signal.connect(self.changee)
		liste.currentItemChanged.connect(self._actualiser_boutons)
		liste.itemActivated.connect(self._ouvrir)
		liste.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		liste.customContextMenuRequested.connect(self._menu)
		for genre, bouton in boutons.ajouter.items():
			bouton.clicked.connect(lambda _coche=False, genre=genre: self._ajouter(genre))
		boutons.retirer.clicked.connect(self._retirer)
		boutons.monter.clicked.connect(lambda: self._deplacer(-1))
		boutons.descendre.clicked.connect(lambda: self._deplacer(1))

	def charger(self, parent: int | None, copie: bool = False) -> None:
		"""Lit en base les éléments de la séquence ou de l'événement, dans l'ordre ; aucun pour un nouveau. Une copie
		(https://github.com/dascritch/machincast/issues/130) les lit comme des lignes ajoutées : l'enregistrement les
		crée pour elle, et laisse celles de l'original. À appeler dans une transaction."""
		self._lire_marquees()
		rangees: list[tuple[object, ...]] = []
		if parent is not None:
			colonnes = ", ".join(f"e.{colonne}" for colonne in self._colonnes().values())
			rangees = self.fiche.connexion.execute(
				f"SELECT e.id, {colonnes} FROM {self.table} e"  # noqa: S608
				f" WHERE e.{self.parent_colonne} = %s ORDER BY e.position",
				(parent,),
			).fetchall()
		genres = list(self._colonnes())
		elements = []
		for ligne_en_base, *identifiants in rangees:
			((genre, identifiant),) = [(g, i) for g, i in zip(genres, identifiants, strict=True) if i is not None]
			elements.append((int(str(ligne_en_base)), genre, int(str(identifiant))))
		lus = self._lire({genre: [i for _l, g, i in elements if g == genre] for genre in genres})
		self.liste.clear()
		lignes = []
		for ligne_en_base, genre, identifiant in elements:
			# Un même élément peut revenir : chaque ligne a son exemplaire.
			ligne = lus[genre][identifiant].clone()
			if not copie:
				ligne.setData(0, LIGNE_EN_BASE, ligne_en_base)
			lignes.append(ligne)
		self.liste.addTopLevelItems(lignes)
		self._actualiser_boutons()

	def lignes(self) -> list[QTreeWidgetItem]:
		lignes = [self.liste.topLevelItem(rangee) for rangee in range(self.liste.topLevelItemCount())]
		return [ligne for ligne in lignes if ligne is not None]

	def avertissements(self, boucle: bool) -> list[str]:
		"""Une ligne par appel d'une banque « ne pas répéter » juste après elle-même ; pour une liste qui boucle, la
		première ligne suit la dernière."""
		lignes = self.lignes()
		bords = [(ligne.data(0, ENTREE), ligne.data(0, SORTIE)) for ligne in lignes]
		textes = []
		for numero in appels_ignores_aux_bords(bords, self.marquees, boucle):
			ligne = lignes[numero - 1]
			banque = self.marquees[bords[numero - 1][0]]
			texte = f"Ligne {numero} : la banque « {banque} » vient de passer, et {SAUTE}"
			if ligne.data(0, GENRE) == "séquence":
				texte = (
					f"Ligne {numero} : la séquence « {ligne.text(1)} » commence par la banque « {banque} », qui vient"
					f" de passer, et {SAUTE}"
				)
			textes.append(texte)
		return textes

	def ecrire(self, parent: int) -> None:
		"""Dans la transaction d'« Enregistrer » : les lignes restées dans la liste gardent leur identifiant, à leur
		nouvelle position ; les autres sont retirées ou ajoutées. L'unicité des positions n'est vérifiée qu'en fin de
		transaction."""
		connexion = self.fiche.connexion
		elements: list[tuple[int | None, str, int]] = []
		"""Ligne en base, genre et identifiant de l'élément."""
		for item in self.lignes():
			identifiant = item.data(0, ELEMENT)
			if item.data(0, MARQUE_PAGE) is not None:
				identifiant = self._enregistrer_stream(int(item.data(0, MARQUE_PAGE)), item.text(1))
			elif identifiant is None:
				identifiant = self.fiche.enregistrer_fichier(str(item.data(0, FICHIER)))
			if identifiant is not None:
				elements.append((item.data(0, LIGNE_EN_BASE), str(item.data(0, GENRE)), int(identifiant)))
		existants: set[tuple[str, int]] = set()
		for genre in self._colonnes():
			demandes = [element for _ligne, g, element in elements if g == genre]
			lus = connexion.execute(f"SELECT id FROM {TABLES[genre]} WHERE id = ANY(%s)", (demandes,))  # noqa: S608
			existants |= {(genre, int(str(identifiant))) for (identifiant,) in lus}
		gardes = [(ligne, genre, element) for ligne, genre, element in elements if (genre, element) in existants]
		en_base = [ligne for ligne, _genre, _element in gardes if ligne is not None]
		connexion.execute(
			f"DELETE FROM {self.table} WHERE {self.parent_colonne} = %s AND NOT (id = ANY(%s))",  # noqa: S608
			(parent, en_base),
		)
		for position, (ligne, genre, element) in enumerate(gardes, start=1):
			if ligne is not None:
				# Une ligne n'est jamais reprise d'une autre séquence ou d'un autre événement.
				connexion.execute(
					f"UPDATE {self.table} SET position = %s WHERE id = %s AND {self.parent_colonne} = %s",  # noqa: S608
					(position, ligne, parent),
				)
				continue
			connexion.execute(
				f"INSERT INTO {self.table} ({self.parent_colonne}, position, {COLONNES[genre]})"  # noqa: S608
				" VALUES (%s, %s, %s)",
				(parent, position, element),
			)

	def _enregistrer_stream(self, marque_page: int, nom: str) -> int | None:
		"""Dans la transaction d'« Enregistrer » : le stream qui suit le marque-page, créé s'il n'y en a pas, actif et
		titré du nom du marque-page ; un second ajout du même marque-page le reprend. None pour un marque-page effacé
		de la base entre-temps : la ligne est oubliée."""
		connexion = self.fiche.connexion
		if connexion.execute("SELECT 1 FROM marques_pages_streams WHERE id = %s", (marque_page,)).fetchone() is None:
			return None
		ligne = connexion.execute(STREAM_DU_MARQUE_PAGE, (marque_page,)).fetchone()
		if ligne is None:
			ligne = connexion.execute(
				"INSERT INTO sonores (type, marque_page_id, titre, etat) VALUES ('stream', %s, %s, 'actif')"
				" RETURNING id",
				(marque_page, nom),
			).fetchone()
			assert ligne is not None
		return int(str(ligne[0]))

	def _colonnes(self) -> dict[str, str]:
		"""Les genres d'éléments de la liste, et leur colonne : jamais une séquence dans une séquence."""
		return {genre: colonne for genre, colonne in COLONNES.items() if colonne != self.parent_colonne}

	def _lire_marquees(self) -> None:
		lues = self.fiche.connexion.execute("SELECT id, nom_interne FROM banques WHERE ne_pas_repeter").fetchall()
		self.marquees = {int(str(identifiant)): str(nom) for identifiant, nom in lues}

	def _lire(self, identifiants: dict[str, list[int]]) -> dict[str, dict[int, QTreeWidgetItem]]:
		"""Les lignes des éléments, par genre et par identifiant ; un élément absent de la base n'en a pas."""
		construire = {"sonore": self._ligne_sonore, "banque": self._ligne_banque, "séquence": self._ligne_sequence}
		lignes: dict[str, dict[int, QTreeWidgetItem]] = {}
		for genre, demandes in identifiants.items():
			lus = self.fiche.connexion.execute(LECTURES[genre], (demandes,)).fetchall()
			lignes[genre] = {int(str(lu[0])): construire[genre](lu) for lu in lus}
		return lignes

	def _ligne_banque(self, banque: tuple[object, ...]) -> QTreeWidgetItem:
		identifiant, nom, mode, marquee = banque
		detail = MODES.get(str(mode), str(mode))
		if marquee:
			detail = f"{detail}, ne pas répéter"
		ligne = self._ligne("banque", [str(nom), detail], (entier_ou_rien(identifiant), entier_ou_rien(identifiant)))
		ligne.setData(0, ELEMENT, int(str(identifiant)))
		return ligne

	def _ligne_sequence(self, sequence: tuple[object, ...]) -> QTreeWidgetItem:
		identifiant, nom, nombre, premiere, derniere = sequence
		detail = f"{nombre} éléments"
		if int(str(nombre)) == 1:
			detail = "1 élément"
		ligne = self._ligne("séquence", [str(nom), detail], (entier_ou_rien(premiere), entier_ou_rien(derniere)))
		ligne.setData(0, ELEMENT, int(str(identifiant)))
		return ligne

	def _ligne_sonore(self, sonore: tuple[object, ...]) -> QTreeWidgetItem:
		"""Une ligne de sonore ; un fichier déposé, pas encore en base, n'a pas d'identifiant."""
		identifiant, artiste, titre, fichier, emplacement = sonore
		texte = affichage.artiste_et_titre(texte_ou_rien(artiste), texte_ou_rien(titre))
		if (artiste is None) and (titre is None) and (fichier is not None):
			# Pas encore décodé : le nom du fichier en attendant ses tags.
			texte = Path(str(fichier)).name
		ligne = self._ligne("sonore", [texte, str((emplacement) or (""))], (None, None))
		if identifiant is not None:
			ligne.setData(0, ELEMENT, int(str(identifiant)))
		else:
			ligne.setData(0, FICHIER, str(fichier))
		return ligne

	def _ligne(self, genre: str, cellules: list[str], bords: tuple[int | None, int | None]) -> QTreeWidgetItem:
		ligne = QTreeWidgetItem([genre, *cellules])
		ligne.setData(0, GENRE, genre)
		ligne.setData(0, ELEMENT, None)
		ligne.setData(0, ENTREE, bords[0])
		ligne.setData(0, SORTIE, bords[1])
		ligne.setFlags(LIGNE)
		return ligne

	def _actualiser_boutons(self) -> None:
		"""Les boutons d'une ligne ne servent qu'à une ligne choisie ; « Monter » et « Descendre », pas aux
		extrémités."""
		ligne = self.liste.currentItem()
		self.boutons.retirer.setEnabled(ligne is not None)
		rangee = -1
		if ligne is not None:
			rangee = self.liste.indexOfTopLevelItem(ligne)
		self.boutons.monter.setEnabled(rangee > 0)
		self.boutons.descendre.setEnabled(0 <= rangee < self.liste.topLevelItemCount() - 1)

	def _ajouter(self, genre: str) -> None:
		"""Les éléments choisis s'ajoutent en fin de liste, dans l'ordre du choix ; un élément effacé de la base
		pendant le choix est oublié."""
		if genre == "marque-page":
			self._ajouter_marques_pages()
			return
		choisir = {
			"sonore": dialogues.choisir_sonores,
			"banque": dialogues.choisir_banques,
			"séquence": dialogues.choisir_sequences,
		}[genre]
		choisis = choisir(self.fiche, self.fiche.connexion, self.remarque)
		with self.fiche.connexion.transaction():
			self._lire_marquees()
			lus = self._lire({genre: choisis})[genre]
		self.liste.addTopLevelItems([lus[choisi] for choisi in choisis if choisi in lus])
		self._actualiser_boutons()

	def _ajouter_marques_pages(self) -> None:
		"""Pour chaque marque-page choisi, le stream qui le suit ; sans stream, une ligne qui en créera un à
		l'enregistrement (https://github.com/dascritch/machincast/issues/167)."""
		choisis = dialogues.choisir_marques_pages(self.fiche, self.fiche.connexion, self.remarque)
		connexion = self.fiche.connexion
		lignes: list[QTreeWidgetItem] = []
		with connexion.transaction():
			for marque_page in choisis:
				marque = connexion.execute(
					"SELECT nom, url FROM marques_pages_streams WHERE id = %s", (marque_page,)
				).fetchone()
				if marque is None:
					continue
				stream = connexion.execute(STREAM_DU_MARQUE_PAGE, (marque_page,)).fetchone()
				if stream is not None:
					lignes += self._lire({"sonore": [int(str(stream[0]))]})["sonore"].values()
					continue
				nom, url = marque
				ligne = self._ligne("sonore", [str(nom), f"{url}, nouveau stream"], (None, None))
				ligne.setData(0, MARQUE_PAGE, marque_page)
				lignes.append(ligne)
		self.liste.addTopLevelItems(lignes)
		self._actualiser_boutons()

	def _deposer(self, chemins: list[Path]) -> None:
		"""Les fichiers sonores déposés s'ajoutent en fin de liste. Un fichier pas encore en base est montré par son
		nom, et deviendra un sonore à l'état aperçu à l'enregistrement."""
		fichiers, ignores = fichiers_sonores(chemins)
		with self.fiche.connexion.transaction():
			lus = self.fiche.connexion.execute(SONORES_PAR_FICHIER, (fichiers,)).fetchall()
		par_fichier = {str(sonore[3]): sonore for sonore in lus}
		lignes = [
			self._ligne_sonore(par_fichier.get(fichier, (None, None, None, fichier, fichier))) for fichier in fichiers
		]
		self.liste.addTopLevelItems(lignes)
		self._actualiser_boutons()
		self.fiche.signaler_ignores(ignores, "ce ne sont pas des fichiers sonores")

	def _retirer(self) -> None:
		self.liste.takeTopLevelItem(self.liste.indexOfTopLevelItem(self.liste.currentItem()))

	def _deplacer(self, decalage: int) -> None:
		ligne = self.liste.currentItem()
		rangee = self.liste.indexOfTopLevelItem(ligne)
		self.liste.takeTopLevelItem(rangee)
		self.liste.insertTopLevelItem(rangee + decalage, ligne)
		# Rendue courante, la ligne déplacée met à jour les boutons (currentItemChanged).
		self.liste.setCurrentItem(ligne)

	def menu_de_la_ligne(self, ligne: QTreeWidgetItem | None) -> QMenu | None:
		"""Le menu du clic droit sur une ligne : « Pré-écoute… » d'un sonore en base ; aucun pour une banque, une
		séquence, un fichier déposé pas encore enregistré, ou hors d'une ligne (https://github.com/dascritch/machincast/issues/226)."""
		if (ligne is None) or (ligne.data(0, GENRE) != "sonore") or (ligne.data(0, ELEMENT) is None):
			return None
		menu = QMenu(self.liste)
		affichage.proposer_la_preecoute(menu, int(ligne.data(0, ELEMENT)), self.fiche.preecoute_demandee.emit)
		return menu

	def _menu(self, position: QPoint) -> None:
		menu = self.menu_de_la_ligne(self.liste.itemAt(position))
		if menu is not None:
			menu.exec(self.liste.viewport().mapToGlobal(position))
			menu.deleteLater()

	def _ouvrir(self, ligne: QTreeWidgetItem) -> None:
		"""Ouvrir un élément demande sa fiche ; un fichier déposé n'en a pas avant l'enregistrement."""
		identifiant = ligne.data(0, ELEMENT)
		if identifiant is not None:
			self.fiche.ouverture_demandee.emit(str(ligne.data(0, GENRE)), int(identifiant), ligne.text(1))
