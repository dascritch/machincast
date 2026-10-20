"""Fiche d'une séquence (https://github.com/dascritch/machincast/issues/112, spec § 8.12).

La fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.fenetre), depuis la liste des séquences, ou vide
pour une nouvelle séquence. Enregistrement, annulation et fermeture : machincast.interface.fiche.

- Les noms sont enregistrés sans les espaces qui les entourent ; un nom public vide n'en est pas un (NULL).
- Le masquage « selon la banque ou le sonore » (NULL) laisse décider le niveau suivant ; « masqués » et « affichés »
  l'imposent.
- Les éléments sont des sonores et des banques, jamais une autre séquence (machincast.interface.elements). Une
  séquence vide s'enregistre, pour être complétée plus tard, avec un avertissement : elle ne joue rien, la diffusion
  la saute, et la liste des séquences la montre en anomalie (https://github.com/dascritch/machincast/issues/138).
  L'avertissement d'une banque « ne pas répéter » appelée deux fois de suite ne boucle pas : la séquence ne reprend
  pas à son début.
- Les événements où la séquence figure sont montrés ; ouvrir un événement ouvre sa fiche.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QWidget

from machincast.horloge import Horloge
from machincast.interface.elements import Boutons, ListeElements
from machincast.interface.fiche import Connexion, Fiche, Refus
from machincast.interface.listes import SEQUENCE_VIDE
from machincast.interface.ui.fiche_sequence import Ui_FicheSequence

MASQUAGES: tuple[tuple[bool | None, str], ...] = (
	(None, "Selon la banque ou le sonore"),
	(True, "Masqués"),
	(False, "Affichés"),
)
"""Valeurs de sequences.masquer_metadonnees, dans l'ordre du choix de la fiche."""
EVENEMENT = Qt.ItemDataRole.UserRole
"""Rôle qui porte l'identifiant d'un événement, dans la liste des événements."""
REPETITION = "Un sonore ou une banque peut revenir plusieurs fois dans une séquence."
"""Remarque des choix de sonores et de banques."""


class FicheSequence(Fiche):
	genre = "séquence"

	def __init__(
		self, connexion: Connexion, identifiant: int | None, horloge: Horloge, parent: QWidget | None = None
	) -> None:
		super().__init__(connexion, identifiant, horloge, parent)
		self.ui = Ui_FicheSequence()
		self.ui.setupUi(self)
		self.brancher(self.ui.enregistrer, self.ui.annuler, self.ui.supprimer, self.ui.message)
		for _valeur, texte in MASQUAGES:
			self.ui.masquage.addItem(texte)
		self._nom = ""
		ui = self.ui
		boutons = Boutons(
			{"sonore": ui.ajouter_sonores, "banque": ui.ajouter_banques}, ui.retirer_element, ui.monter, ui.descendre
		)
		self.elements = ListeElements(self, ui.elements, boutons, "sequences_elements", "sequence_id", REPETITION)
		self.elements.changee.connect(self._modifier)
		self.elements.changee.connect(self._avertir)
		ui.nom_interne.textChanged.connect(self._modifier)
		ui.nom_public.textChanged.connect(self._modifier)
		ui.masquage.currentIndexChanged.connect(self._modifier)
		ui.evenements.itemActivated.connect(self._ouvrir_evenement)
		self.charger()

	def titre(self) -> str:
		if self.identifiant is None:
			return "Nouvelle séquence"
		return f"Séquence : {self._nom}"

	def _lire(self) -> None:
		"""Lit la séquence en base ; une nouvelle séquence est vide, au masquage hérité de la banque ou du sonore."""
		sequence: tuple[object, ...] = ("", None, None)
		evenements: list[tuple[object, ...]] = []
		with self.connexion.transaction():
			if self.identifiant is not None:
				ligne = self.connexion.execute(
					"SELECT nom_interne, nom_public, masquer_metadonnees FROM sequences WHERE id = %s",
					(self.identifiant,),
				).fetchone()
				assert ligne is not None, f"séquence {self.identifiant} absente"
				sequence = ligne
				evenements = self.connexion.execute(
					"SELECT DISTINCT ev.id, ev.nom_interne FROM evenements ev"
					" JOIN evenements_elements ee ON ee.evenement_id = ev.id"
					" WHERE ee.sequence_id = %s ORDER BY ev.nom_interne, ev.id",
					(self.identifiant,),
				).fetchall()
			self.elements.charger(self.identifiant)
		nom, nom_public, masquage = sequence
		self._nom = str(nom)
		self.ui.nom_interne.setText(self._nom)
		self.ui.nom_public.setText(str((nom_public) or ("")))
		self.ui.masquage.setCurrentIndex(next(i for i, (valeur, _texte) in enumerate(MASQUAGES) if valeur is masquage))
		self.ui.evenements.clear()
		for identifiant, nom_evenement in evenements:
			item = QListWidgetItem(str(nom_evenement))
			item.setData(EVENEMENT, int(str(identifiant)))
			self.ui.evenements.addItem(item)
		# Une liste lue vide ne change pas : l'avertissement d'une séquence vide se pose ici.
		self._avertir()

	def _ecrire(self) -> int:
		nom = self.ui.nom_interne.text().strip()
		if nom == "":
			raise Refus("Le nom interne est obligatoire.")
		pris = self.connexion.execute(
			"SELECT 1 FROM sequences WHERE nom_interne = %s AND id IS DISTINCT FROM %s", (nom, self.identifiant)
		).fetchone()
		if pris is not None:
			raise Refus(f"Une autre séquence s'appelle déjà « {nom} ».")
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
		self.elements.ecrire(identifiant)
		return identifiant

	def _avertir(self) -> None:
		"""Une séquence vide, ou une banque « ne pas répéter » appelée juste après elle-même : cet appel sera sauté."""
		avertissements = self.elements.avertissements(False)
		if self.elements.lignes() == []:
			avertissements = [SEQUENCE_VIDE]
		self.ui.avertissement.setText("\n".join(avertissements))

	def _ouvrir_evenement(self, item: QListWidgetItem) -> None:
		self.ouverture_demandee.emit("événement", int(item.data(EVENEMENT)), item.text())
