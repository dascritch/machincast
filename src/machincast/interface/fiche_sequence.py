"""Fiche d'une séquence (https://github.com/dascritch/machincast/issues/112, spec § 8.12).

La fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.fenetre), depuis la liste des séquences, ou vide
pour une nouvelle séquence. Enregistrement, annulation et fermeture : machincast.interface.fiche.

- Les noms sont enregistrés sans les espaces qui les entourent ; un nom public vide n'en est pas un (NULL).
- Le masquage « selon la banque ou le sonore » (NULL) laisse décider le niveau suivant ; « masqués » et « affichés »
  l'imposent.
- Les éléments sont des sonores et des banques, jamais une autre séquence ; un même élément peut revenir. Ils se
  réordonnent par glisser-déposer, ou par « Monter » et « Descendre ». Ils s'ajoutent parmi les sonores et les banques
  déjà en base (machincast.interface.choix), ou par dépôt de fichiers sonores (machincast.interface.depot), toujours
  comme une copie ; un fichier pas encore en base devient un sonore à l'état aperçu à l'enregistrement seulement.
- Une séquence vide ne s'enregistre pas : la base ne la refuse pas, mais elle ne jouerait rien.
- Une banque « ne pas répéter » sur deux lignes contiguës est signalée : le deuxième appel sera sauté à la diffusion
  (machincast.lecture.deroule.appels_ignores, sans boucle). L'avertissement n'empêche pas d'enregistrer.
- À l'enregistrement, un élément resté dans la liste garde sa ligne en base, où l'historique de diffusion le désigne
  pour reprendre la séquence ; un sonore ou une banque effacé de la base entre-temps est oublié.
- Les événements où la séquence figure sont montrés ; ouvrir un élément ou un événement demande son écran.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QListWidgetItem, QTreeWidgetItem, QWidget

from machincast.horloge import Horloge
from machincast.interface import affichage, dialogues
from machincast.interface.depot import DepotDeFichiers
from machincast.interface.fiche import Connexion, Fiche, Refus, fichiers_sonores
from machincast.interface.listes import MODES
from machincast.interface.ui.fiche_sequence import Ui_FicheSequence
from machincast.lecture.deroule import appels_ignores

MASQUAGES: tuple[tuple[bool | None, str], ...] = (
	(None, "Selon la banque ou le sonore"),
	(True, "Masqués"),
	(False, "Affichés"),
)
"""Valeurs de sequences.masquer_metadonnees, dans l'ordre du choix de la fiche."""
GENRE = Qt.ItemDataRole.UserRole
"""Rôle qui porte, sur la première colonne d'une ligne, le genre de l'élément : « sonore » ou « banque »."""
ELEMENT = Qt.ItemDataRole.UserRole + 1
"""Rôle qui porte l'identifiant du sonore ou de la banque ; None pour un fichier déposé, pas encore en base."""
FICHIER = Qt.ItemDataRole.UserRole + 2
"""Rôle qui porte le chemin d'un fichier déposé, pas encore en base."""
LIGNE_EN_BASE = Qt.ItemDataRole.UserRole + 3
"""Rôle qui porte l'identifiant de la ligne dans sequences_elements ; None pour une ligne ajoutée."""
LIGNE = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDragEnabled
"""Une ligne se glisse, mais rien ne se dépose dedans : la liste reste à plat."""
EVENEMENT = Qt.ItemDataRole.UserRole
"""Rôle qui porte l'identifiant d'un événement, dans la liste des événements."""
REPETITION = "Un sonore ou une banque peut revenir plusieurs fois dans une séquence."
"""Remarque des choix de sonores et de banques."""
BANQUES_LUES = "SELECT b.id, b.nom_interne, b.mode::text, b.ne_pas_repeter FROM banques b"
SONORES_LUS = (
	"SELECT s.id, s.artiste, s.titre, s.emplacement, COALESCE(s.emplacement, s.url_stream, m.url)"
	" FROM sonores s LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id"
)


def _texte(valeur: object) -> str | None:
	if valeur is None:
		return None
	return str(valeur)


class FicheSequence(Fiche):
	genre = "séquence"

	def __init__(
		self, connexion: Connexion, identifiant: int | None, horloge: Horloge, parent: QWidget | None = None
	) -> None:
		super().__init__(connexion, identifiant, horloge, parent)
		self.ui = Ui_FicheSequence()
		self.ui.setupUi(self)
		self.brancher(self.ui.enregistrer, self.ui.annuler, self.ui.message)
		for _valeur, texte in MASQUAGES:
			self.ui.masquage.addItem(texte)
		entete = self.ui.elements.header()
		entete.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
		entete.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
		self.ui.elements.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
		self._nom = ""
		self._marquees: set[int] = set()
		"""Banques « ne pas répéter » de la fiche."""
		self.depot = DepotDeFichiers(self.ui.elements)
		self.depot.deposes.connect(self._deposer)
		self.ui.nom_interne.textChanged.connect(self._modifier)
		self.ui.nom_public.textChanged.connect(self._modifier)
		self.ui.masquage.currentIndexChanged.connect(self._modifier)
		modele = self.ui.elements.model()
		# Toute modification de la liste passe par ces signaux, qui recalculent l'avertissement : le glisser-déposer
		# déplace une ligne en la retirant, puis en l'insérant.
		for signal in (modele.rowsInserted, modele.rowsRemoved):
			signal.connect(self._modifier)
			signal.connect(self._avertir)
		self.ui.elements.currentItemChanged.connect(self._actualiser_boutons)
		self.ui.elements.itemActivated.connect(self._ouvrir_element)
		self.ui.evenements.itemActivated.connect(self._ouvrir_evenement)
		self.ui.ajouter_sonores.clicked.connect(self._ajouter_sonores)
		self.ui.ajouter_banques.clicked.connect(self._ajouter_banques)
		self.ui.retirer_element.clicked.connect(self._retirer)
		self.ui.monter.clicked.connect(lambda: self._deplacer(-1))
		self.ui.descendre.clicked.connect(lambda: self._deplacer(1))
		self.charger()

	def titre(self) -> str:
		if self.identifiant is None:
			return "Nouvelle séquence"
		return f"Séquence : {self._nom}"

	def _lire(self) -> None:
		"""Lit la séquence en base ; une nouvelle séquence est vide, au masquage hérité de la banque ou du sonore."""
		sequence: tuple[object, ...] = ("", None, None)
		self._marquees = set()
		elements: list[tuple[object, ...]] = []
		evenements: list[tuple[object, ...]] = []
		with self.connexion.transaction():
			if self.identifiant is not None:
				ligne = self.connexion.execute(
					"SELECT nom_interne, nom_public, masquer_metadonnees FROM sequences WHERE id = %s",
					(self.identifiant,),
				).fetchone()
				assert ligne is not None, f"séquence {self.identifiant} absente"
				sequence = ligne
				elements = self.connexion.execute(
					"SELECT e.id, e.banque_id, b.nom_interne, b.mode::text, b.ne_pas_repeter,"
					" e.sonore_id, s.artiste, s.titre, s.emplacement, COALESCE(s.emplacement, s.url_stream, m.url)"
					" FROM sequences_elements e"
					" LEFT JOIN banques b ON b.id = e.banque_id"
					" LEFT JOIN sonores s ON s.id = e.sonore_id"
					" LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id"
					" WHERE e.sequence_id = %s ORDER BY e.position",
					(self.identifiant,),
				).fetchall()
				evenements = self.connexion.execute(
					"SELECT DISTINCT ev.id, ev.nom_interne FROM evenements ev"
					" JOIN evenements_elements ee ON ee.evenement_id = ev.id"
					" WHERE ee.sequence_id = %s ORDER BY ev.nom_interne, ev.id",
					(self.identifiant,),
				).fetchall()
		nom, nom_public, masquage = sequence
		self._nom = str(nom)
		self.ui.nom_interne.setText(self._nom)
		self.ui.nom_public.setText(str((nom_public) or ("")))
		self.ui.masquage.setCurrentIndex(next(i for i, (valeur, _texte) in enumerate(MASQUAGES) if valeur is masquage))
		self.ui.elements.clear()
		lignes = []
		for ligne_en_base, banque, nom_banque, mode, marquee, *sonore in elements:
			element = self._ligne_sonore(tuple(sonore))
			if banque is not None:
				element = self._ligne_banque((banque, nom_banque, mode, marquee))
			element.setData(0, LIGNE_EN_BASE, int(str(ligne_en_base)))
			lignes.append(element)
		self.ui.elements.addTopLevelItems(lignes)
		self.ui.evenements.clear()
		for identifiant, nom_evenement in evenements:
			item = QListWidgetItem(str(nom_evenement))
			item.setData(EVENEMENT, int(str(identifiant)))
			self.ui.evenements.addItem(item)
		self._actualiser_boutons()

	def _ecrire(self) -> int:
		nom = self.ui.nom_interne.text().strip()
		if nom == "":
			raise Refus("Le nom interne est obligatoire.")
		pris = self.connexion.execute(
			"SELECT 1 FROM sequences WHERE nom_interne = %s AND id IS DISTINCT FROM %s", (nom, self.identifiant)
		).fetchone()
		if pris is not None:
			raise Refus(f"Une autre séquence s'appelle déjà « {nom} ».")
		if self._lignes() == []:
			raise Refus("Une séquence contient au moins un sonore ou une banque.")
		valeurs = (
			nom,
			(self.ui.nom_public.text().strip()) or (None),
			MASQUAGES[self.ui.masquage.currentIndex()][0],
		)
		if self.identifiant is None:
			creee = self.connexion.execute(
				"INSERT INTO sequences (nom_interne, nom_public, masquer_metadonnees) VALUES (%s, %s, %s) RETURNING id",
				valeurs,
			).fetchone()
			assert creee is not None
			identifiant = int(str(creee[0]))
		else:
			identifiant = self.identifiant
			self.connexion.execute(
				"UPDATE sequences SET nom_interne = %s, nom_public = %s, masquer_metadonnees = %s WHERE id = %s",
				(*valeurs, identifiant),
			)
		self._ecrire_elements(identifiant)
		return identifiant

	def _ecrire_elements(self, sequence: int) -> None:
		"""Les lignes restées dans la liste gardent leur identifiant, à leur nouvelle position ; les autres sont
		retirées ou ajoutées. L'unicité des positions n'est vérifiée qu'en fin de transaction."""
		elements: list[tuple[int | None, str, int]] = []
		"""Ligne en base, genre et identifiant de l'élément."""
		for item in self._lignes():
			identifiant = item.data(0, ELEMENT)
			if identifiant is None:
				identifiant = self.enregistrer_fichier(str(item.data(0, FICHIER)))
			elements.append((item.data(0, LIGNE_EN_BASE), str(item.data(0, GENRE)), int(identifiant)))
		existants: set[tuple[str, int]] = set()
		for genre, table in (("sonore", "sonores"), ("banque", "banques")):
			demandes = [element for _ligne, g, element in elements if g == genre]
			lus = self.connexion.execute(f"SELECT id FROM {table} WHERE id = ANY(%s)", (demandes,))  # noqa: S608
			existants |= {(genre, int(str(identifiant))) for (identifiant,) in lus}
		gardes = [(ligne, genre, element) for ligne, genre, element in elements if (genre, element) in existants]
		en_base = [ligne for ligne, _genre, _element in gardes if ligne is not None]
		self.connexion.execute(
			"DELETE FROM sequences_elements WHERE sequence_id = %s AND NOT (id = ANY(%s))", (sequence, en_base)
		)
		for position, (ligne, genre, element) in enumerate(gardes, start=1):
			if ligne is not None:
				self.connexion.execute("UPDATE sequences_elements SET position = %s WHERE id = %s", (position, ligne))
				continue
			colonne = {"sonore": "sonore_id", "banque": "banque_id"}[genre]
			self.connexion.execute(
				f"INSERT INTO sequences_elements (sequence_id, position, {colonne}) VALUES (%s, %s, %s)",  # noqa: S608
				(sequence, position, element),
			)

	def _ligne_banque(self, banque: tuple[object, ...]) -> QTreeWidgetItem:
		identifiant, nom, mode, marquee = banque
		detail = MODES.get(str(mode), str(mode))
		if marquee:
			detail = f"{detail}, ne pas répéter"
			self._marquees.add(int(str(identifiant)))
		return self._ligne("banque", int(str(identifiant)), [str(nom), detail])

	def _ligne_sonore(self, sonore: tuple[object, ...]) -> QTreeWidgetItem:
		"""Une ligne de sonore ; un fichier déposé, pas encore en base, n'a pas d'identifiant."""
		identifiant, artiste, titre, fichier, emplacement = sonore
		texte = affichage.artiste_et_titre(_texte(artiste), _texte(titre))
		if (artiste is None) and (titre is None) and (fichier is not None):
			# Pas encore décodé : le nom du fichier en attendant ses tags.
			texte = Path(str(fichier)).name
		ligne = self._ligne("sonore", None, [texte, str((emplacement) or (""))])
		if identifiant is not None:
			ligne.setData(0, ELEMENT, int(str(identifiant)))
		else:
			ligne.setData(0, FICHIER, str(fichier))
		return ligne

	def _ligne(self, genre: str, identifiant: int | None, cellules: list[str]) -> QTreeWidgetItem:
		ligne = QTreeWidgetItem([genre, *cellules])
		ligne.setData(0, GENRE, genre)
		ligne.setData(0, ELEMENT, identifiant)
		ligne.setFlags(LIGNE)
		return ligne

	def _lignes(self) -> list[QTreeWidgetItem]:
		liste = self.ui.elements
		lignes = [liste.topLevelItem(rangee) for rangee in range(liste.topLevelItemCount())]
		return [ligne for ligne in lignes if ligne is not None]

	def _actualiser_boutons(self) -> None:
		"""Les boutons d'une ligne ne servent qu'à une ligne choisie ; « Monter » et « Descendre », pas aux
		extrémités."""
		liste = self.ui.elements
		ligne = liste.currentItem()
		self.ui.retirer_element.setEnabled(ligne is not None)
		rangee = -1
		if ligne is not None:
			rangee = liste.indexOfTopLevelItem(ligne)
		self.ui.monter.setEnabled(rangee > 0)
		self.ui.descendre.setEnabled(0 <= rangee < liste.topLevelItemCount() - 1)

	def _avertir(self) -> None:
		"""Une banque « ne pas répéter » sur deux lignes contiguës : le deuxième appel sera sauté."""
		lignes = self._lignes()
		banques: list[int | None] = []
		for ligne in lignes:
			banques.append(None)
			if ligne.data(0, GENRE) == "banque":
				banques[-1] = int(ligne.data(0, ELEMENT))
		avertissements = [
			f"Ligne {numero} : la banque « {lignes[numero - 1].text(1)} » vient de passer, et ne passe jamais deux fois"
			" de suite : cet appel sera sauté."
			for numero in appels_ignores(banques, self._marquees, False)
		]
		self.ui.avertissement.setText("\n".join(avertissements))

	def _ajouter_sonores(self) -> None:
		choisis = dialogues.choisir_sonores(self, self.connexion, REPETITION)
		with self.connexion.transaction():
			lus = self.connexion.execute(f"{SONORES_LUS} WHERE s.id = ANY(%s)", (choisis,)).fetchall()
		par_identifiant = {int(str(sonore[0])): sonore for sonore in lus}
		lignes = [self._ligne_sonore(par_identifiant[sonore]) for sonore in choisis if sonore in par_identifiant]
		self.ui.elements.addTopLevelItems(lignes)
		self._actualiser_boutons()

	def _ajouter_banques(self) -> None:
		choisies = dialogues.choisir_banques(self, self.connexion, REPETITION)
		with self.connexion.transaction():
			lues = self.connexion.execute(f"{BANQUES_LUES} WHERE b.id = ANY(%s)", (choisies,)).fetchall()
		par_identifiant = {int(str(banque[0])): banque for banque in lues}
		lignes = [self._ligne_banque(par_identifiant[banque]) for banque in choisies if banque in par_identifiant]
		self.ui.elements.addTopLevelItems(lignes)
		self._actualiser_boutons()

	def _deposer(self, chemins: list[Path]) -> None:
		"""Les fichiers sonores déposés s'ajoutent en fin de liste. Un fichier pas encore en base est montré par son
		nom, et deviendra un sonore à l'état aperçu à l'enregistrement."""
		fichiers, ignores = fichiers_sonores(chemins)
		with self.connexion.transaction():
			lus = self.connexion.execute(f"{SONORES_LUS} WHERE s.emplacement = ANY(%s)", (fichiers,)).fetchall()
		par_fichier = {str(sonore[3]): sonore for sonore in lus}
		lignes = [
			self._ligne_sonore(par_fichier.get(fichier, (None, None, None, fichier, fichier))) for fichier in fichiers
		]
		self.ui.elements.addTopLevelItems(lignes)
		self._actualiser_boutons()
		self.signaler_ignores(ignores, "ce ne sont pas des fichiers sonores")

	def _retirer(self) -> None:
		liste = self.ui.elements
		liste.takeTopLevelItem(liste.indexOfTopLevelItem(liste.currentItem()))

	def _deplacer(self, decalage: int) -> None:
		liste = self.ui.elements
		ligne = liste.currentItem()
		rangee = liste.indexOfTopLevelItem(ligne)
		liste.takeTopLevelItem(rangee)
		liste.insertTopLevelItem(rangee + decalage, ligne)
		# Rendue courante, la ligne déplacée met à jour les boutons (currentItemChanged).
		liste.setCurrentItem(ligne)

	def _ouvrir_element(self, ligne: QTreeWidgetItem) -> None:
		identifiant = ligne.data(0, ELEMENT)
		if identifiant is not None:
			self.ouverture_demandee.emit(str(ligne.data(0, GENRE)), int(identifiant), ligne.text(1))

	def _ouvrir_evenement(self, item: QListWidgetItem) -> None:
		self.ouverture_demandee.emit("événement", int(item.data(EVENEMENT)), item.text())
