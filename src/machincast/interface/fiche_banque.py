"""Fiche d'une banque (https://github.com/dascritch/machincast/issues/31, spec § 8.4).

La fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.fenetre), depuis la liste des banques, ou vide pour
une nouvelle banque. Enregistrement, annulation et fermeture : machincast.interface.fiche.

- Les noms sont enregistrés sans les espaces qui les entourent ; un nom public vide n'en est pas un (NULL).
- Le masquage « hérité du sonore » (NULL) laisse décider le sonore ; « masqués » et « affichés » l'imposent.
- Les répertoires sont enregistrés sous leur forme normale, comme les lit Machin indexation.
- Les sonores se réordonnent par glisser-déposer, ou par les boutons « Monter » et « Descendre », en mode séquentiel
  seulement. Ils s'ajoutent parmi les sonores déjà en base (machincast.interface.choix_sonores), y compris hors des
  répertoires de la banque.
- Des dossiers déposés depuis le navigateur de fichiers s'ajoutent aux répertoires, des fichiers sonores aux sonores
  (machincast.interface.depot), toujours comme une copie. Un fichier pas encore en base devient un sonore à l'état
  aperçu à l'enregistrement seulement.
- Retirer un sonore dont le fichier est dans l'un des répertoires de la fiche prévient que la prochaine indexation
  l'y remettra, et propose d'ouvrir son dossier : le fichier ne s'écarte que hors de MachinCast
  (https://github.com/dascritch/machincast/issues/96).
- À l'enregistrement, les sonores qu'une indexation a rattachés à la banque depuis l'ouverture de la fiche sont gardés,
  en fin de liste ; un sonore effacé de la base entre-temps est oublié.

Les fenêtres de dialogue sont celles de machincast.interface.dialogues.
"""

import os
from datetime import timedelta
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTreeWidgetItem, QWidget

from machincast.horloge import Horloge
from machincast.interface import affichage, dialogues
from machincast.interface.depot import DepotDeFichiers
from machincast.interface.dialogues import Retrait
from machincast.interface.fiche import Connexion, Fiche, Refus
from machincast.interface.ui.fiche_banque import Ui_FicheBanque
from machincast.protection import est_fichier_sonore

MODES = (("sequentiel", "Séquentielle"), ("aleatoire", "Aléatoire"))
MASQUAGES: tuple[tuple[bool | None, str], ...] = ((None, "Hérité du sonore"), (True, "Masqués"), (False, "Affichés"))
"""Valeurs de banques.masquer_metadonnees, dans l'ordre du choix de la fiche."""
SONORE = Qt.ItemDataRole.UserRole
"""Rôle qui porte, sur la première colonne d'une ligne de sonore, son identifiant en base."""
FICHIER = Qt.ItemDataRole.UserRole + 1
"""Rôle qui porte le chemin du fichier du sonore, None pour un stream."""
LIGNE = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDragEnabled
"""Une ligne de sonore se glisse, mais rien ne se dépose dedans : la liste reste à plat."""
SONORES_LUS = (
	"SELECT s.id, s.artiste, s.titre, s.duree, s.emplacement, COALESCE(s.emplacement, s.url_stream, m.url)"
	" FROM sonores s LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id"
)


DOSSIER_SUR_LES_SONORES = " Un dossier se dépose sur les répertoires indexés."
"""Conseil pour un dossier déposé sur les sonores."""


def avertissement_retrait(sonore: str, repertoire: str) -> str:
	return (
		f"« {sonore} » est un fichier du répertoire {repertoire}, indexé par cette banque : la prochaine indexation "
		"l'y remettra. Pour l'écarter pour de bon, déplacez son fichier hors de ce répertoire, en dehors de MachinCast."
	)


class FicheBanque(Fiche):
	genre = "banque"

	def __init__(
		self, connexion: Connexion, identifiant: int | None, horloge: Horloge, parent: QWidget | None = None
	) -> None:
		super().__init__(connexion, identifiant, horloge, parent)
		self.ui = Ui_FicheBanque()
		self.ui.setupUi(self)
		self.brancher(self.ui.enregistrer, self.ui.annuler, self.ui.message)
		for valeur, texte in MODES:
			self.ui.mode.addItem(texte, valeur)
		for _valeur, texte in MASQUAGES:
			self.ui.masquage.addItem(texte)
		entete = self.ui.sonores.header()
		entete.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
		entete.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
		self._nom = ""
		self._charges: set[int] = set()
		"""Sonores de la banque à la dernière lecture : ceux qui manquent à la fiche en ont été retirés."""
		self.depot_repertoires = DepotDeFichiers(self.ui.repertoires)
		self.depot_repertoires.deposes.connect(self._deposer_repertoires)
		self.depot_sonores = DepotDeFichiers(self.ui.sonores)
		self.depot_sonores.deposes.connect(self._deposer_sonores)
		self.ui.nom_interne.textChanged.connect(self._modifier)
		self.ui.nom_public.textChanged.connect(self._modifier)
		self.ui.mode.currentIndexChanged.connect(self._modifier)
		self.ui.mode.currentIndexChanged.connect(self._actualiser_boutons)
		self.ui.masquage.currentIndexChanged.connect(self._modifier)
		self.ui.ne_pas_repeter.toggled.connect(self._modifier)
		modele = self.ui.sonores.model()
		# Le glisser-déposer déplace une ligne en la retirant, puis en l'insérant.
		modele.rowsInserted.connect(self._modifier)
		modele.rowsRemoved.connect(self._modifier)
		self.ui.repertoires.currentItemChanged.connect(self._actualiser_boutons)
		self.ui.sonores.currentItemChanged.connect(self._actualiser_boutons)
		self.ui.ajouter_repertoire.clicked.connect(self._ajouter_repertoire)
		self.ui.retirer_repertoire.clicked.connect(self._retirer_repertoire)
		self.ui.ajouter_sonores.clicked.connect(self._ajouter_sonores)
		self.ui.retirer_sonore.clicked.connect(self._retirer_sonore)
		self.ui.monter.clicked.connect(lambda: self._deplacer(-1))
		self.ui.descendre.clicked.connect(lambda: self._deplacer(1))
		self.charger()

	def titre(self) -> str:
		if self.identifiant is None:
			return "Nouvelle banque"
		return f"Banque : {self._nom}"

	def _lire(self) -> None:
		"""Lit la banque en base ; une nouvelle banque est vide, séquentielle, au masquage hérité du sonore."""
		banque: tuple[object, ...] = ("", None, MODES[0][0], None, False)
		repertoires: list[str] = []
		sonores: list[tuple[object, ...]] = []
		with self.connexion.transaction():
			if self.identifiant is not None:
				ligne = self.connexion.execute(
					"SELECT nom_interne, nom_public, mode::text, masquer_metadonnees, ne_pas_repeter"
					" FROM banques WHERE id = %s",
					(self.identifiant,),
				).fetchone()
				assert ligne is not None, f"banque {self.identifiant} absente"
				banque = ligne
				repertoires = [
					str(repertoire)
					for (repertoire,) in self.connexion.execute(
						"SELECT repertoire FROM banques_repertoires WHERE banque_id = %s", (self.identifiant,)
					)
				]
				sonores = self.connexion.execute(
					f"{SONORES_LUS} JOIN banques_sonores bs ON bs.sonore_id = s.id"
					" WHERE bs.banque_id = %s ORDER BY bs.position",
					(self.identifiant,),
				).fetchall()
		nom, nom_public, mode, masquage, ne_pas_repeter = banque
		self._nom = str(nom)
		self.ui.nom_interne.setText(self._nom)
		self.ui.nom_public.setText(str(nom_public or ""))
		self.ui.mode.setCurrentIndex(self.ui.mode.findData(mode))
		self.ui.masquage.setCurrentIndex(next(i for i, (valeur, _texte) in enumerate(MASQUAGES) if valeur is masquage))
		self.ui.ne_pas_repeter.setChecked(bool(ne_pas_repeter))
		self._montrer_repertoires(repertoires)
		self.ui.sonores.clear()
		self.ui.sonores.addTopLevelItems([self._ligne(sonore) for sonore in sonores])
		self._charges = set(self._sonores())
		self._actualiser_boutons()

	def _ecrire(self) -> int:
		nom = self.ui.nom_interne.text().strip()
		if nom == "":
			raise Refus("Le nom interne est obligatoire.")
		pris = self.connexion.execute(
			"SELECT 1 FROM banques WHERE nom_interne = %s AND id IS DISTINCT FROM %s", (nom, self.identifiant)
		).fetchone()
		if pris is not None:
			raise Refus(f"Une autre banque s'appelle déjà « {nom} ».")
		valeurs = (
			nom,
			self.ui.nom_public.text().strip() or None,
			self.ui.mode.currentData(),
			MASQUAGES[self.ui.masquage.currentIndex()][0],
			self.ui.ne_pas_repeter.isChecked(),
		)
		if self.identifiant is None:
			creee = self.connexion.execute(
				"INSERT INTO banques (nom_interne, nom_public, mode, masquer_metadonnees, ne_pas_repeter)"
				" VALUES (%s, %s, %s, %s, %s) RETURNING id",
				valeurs,
			).fetchone()
			assert creee is not None
			identifiant = int(str(creee[0]))
		else:
			identifiant = self.identifiant
			self.connexion.execute(
				"UPDATE banques SET nom_interne = %s, nom_public = %s, mode = %s, masquer_metadonnees = %s,"
				" ne_pas_repeter = %s WHERE id = %s",
				(*valeurs, identifiant),
			)
		self.connexion.execute("DELETE FROM banques_repertoires WHERE banque_id = %s", (identifiant,))
		self.connexion.execute(
			"INSERT INTO banques_repertoires (banque_id, repertoire) SELECT %s, unnest(%s::text[])",
			(identifiant, self._repertoires()),
		)
		self._ecrire_sonores(identifiant)
		return identifiant

	def _ecrire_sonores(self, banque: int) -> None:
		voulus = []
		for ligne in self._lignes():
			identifiant = ligne.data(0, SONORE)
			if identifiant is None:
				identifiant = self._enregistrer_fichier(str(ligne.data(0, FICHIER)))
			voulus.append(int(identifiant))
		en_base = [
			int(str(sonore))
			for (sonore,) in self.connexion.execute(
				"SELECT sonore_id FROM banques_sonores WHERE banque_id = %s ORDER BY position FOR UPDATE", (banque,)
			)
		]
		# Rattachés par une indexation depuis la lecture de la fiche : gardés, en fin de liste.
		rattaches = [sonore for sonore in en_base if (sonore not in self._charges) and (sonore not in voulus)]
		existants = {
			int(str(sonore))
			for (sonore,) in self.connexion.execute("SELECT id FROM sonores WHERE id = ANY(%s)", (voulus,))
		}
		ordre = [sonore for sonore in voulus if sonore in existants] + rattaches
		self.connexion.execute("DELETE FROM banques_sonores WHERE banque_id = %s", (banque,))
		with self.connexion.cursor() as curseur:
			curseur.executemany(
				"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, %s)",
				[(banque, sonore, position) for position, sonore in enumerate(ordre, start=1)],
			)

	def _enregistrer_fichier(self, fichier: str) -> int:
		"""Un fichier déposé devient un sonore à l'état aperçu, que Machin indexation décodera ; s'il a été enregistré
		entre-temps, le sonore est repris."""
		ligne = self.connexion.execute("SELECT id FROM sonores WHERE emplacement = %s", (fichier,)).fetchone()
		if ligne is None:
			ligne = self.connexion.execute(
				"INSERT INTO sonores (type, emplacement, etat) VALUES ('fichier', %s, 'apercu') RETURNING id",
				(fichier,),
			).fetchone()
			assert ligne is not None
		return int(str(ligne[0]))

	def _ligne(self, sonore: tuple[object, ...]) -> QTreeWidgetItem:
		"""Une ligne de sonore ; un fichier déposé, pas encore en base, n'a pas d'identifiant."""
		identifiant, artiste, titre, duree, fichier, emplacement = sonore
		texte_duree = ""
		if fichier is None:
			texte_duree = affichage.duree(None)
		elif isinstance(duree, timedelta):
			texte_duree = affichage.duree(duree)
		texte = affichage.artiste_et_titre(_texte(artiste), _texte(titre))
		if (artiste is None) and (titre is None) and (fichier is not None):
			# Pas encore décodé : le nom du fichier en attendant ses tags.
			texte = Path(str(fichier)).name
		ligne = QTreeWidgetItem([texte, texte_duree, str(emplacement or "")])
		if identifiant is not None:
			ligne.setData(0, SONORE, int(str(identifiant)))
		ligne.setData(0, FICHIER, _texte(fichier))
		ligne.setFlags(LIGNE)
		return ligne

	def _lignes(self) -> list[QTreeWidgetItem]:
		liste = self.ui.sonores
		lignes = [liste.topLevelItem(rangee) for rangee in range(liste.topLevelItemCount())]
		return [ligne for ligne in lignes if ligne is not None]

	def _sonores(self) -> list[int]:
		"""Les sonores de la fiche déjà en base."""
		identifiants = [ligne.data(0, SONORE) for ligne in self._lignes()]
		return [int(identifiant) for identifiant in identifiants if identifiant is not None]

	def _repertoires(self) -> list[str]:
		liste = self.ui.repertoires
		return [liste.item(rangee).text() for rangee in range(liste.count())]

	def _actualiser_boutons(self) -> None:
		"""Les boutons d'une ligne ne servent qu'à une ligne choisie. L'ordre des sonores ne compte, et ne se change,
		qu'en mode séquentiel : « Monter » et « Descendre » ne servent pas en tête et en fin de liste."""
		self.ui.retirer_repertoire.setEnabled(self.ui.repertoires.currentItem() is not None)
		sequentiel = self.ui.mode.currentData() == "sequentiel"
		mode = QAbstractItemView.DragDropMode.NoDragDrop
		if sequentiel:
			mode = QAbstractItemView.DragDropMode.InternalMove
		self.ui.sonores.setDragDropMode(mode)
		self.depot_sonores.accepter()
		liste = self.ui.sonores
		ligne = liste.currentItem()
		self.ui.retirer_sonore.setEnabled(ligne is not None)
		rangee = -1
		if ligne is not None:
			rangee = liste.indexOfTopLevelItem(ligne)
		self.ui.monter.setEnabled((sequentiel) and (rangee > 0))
		self.ui.descendre.setEnabled((sequentiel) and (0 <= rangee < liste.topLevelItemCount() - 1))

	def _ajouter_repertoire(self) -> None:
		choisi = dialogues.choisir_repertoire(self)
		if choisi is None:
			return
		self._ajouter_repertoires([choisi])

	def _ajouter_repertoires(self, choisis: list[str]) -> None:
		"""Sous leur forme normale, sans doublon."""
		presents = self._repertoires()
		nouveaux = [repertoire for repertoire in map(os.path.normpath, choisis) if repertoire not in presents]
		if nouveaux == []:
			return
		self._montrer_repertoires(presents + list(dict.fromkeys(nouveaux)))
		self._modifier()

	def _deposer_repertoires(self, chemins: list[Path]) -> None:
		"""Les dossiers déposés s'ajoutent aux répertoires ; un fichier est ignoré, et la fiche le dit."""
		self._ajouter_repertoires([str(chemin) for chemin in chemins if chemin.is_dir()])
		self._signaler_ignores([chemin for chemin in chemins if not chemin.is_dir()], "ce ne sont pas des répertoires")

	def _deposer_sonores(self, chemins: list[Path]) -> None:
		"""Les fichiers sonores déposés s'ajoutent en fin de liste, une fois chacun. Un fichier pas encore en base est
		montré par son nom, et deviendra un sonore à l'état aperçu à l'enregistrement."""
		sonores = [chemin for chemin in chemins if (chemin.is_file()) and (est_fichier_sonore(chemin))]
		fichiers = [os.path.normpath(chemin) for chemin in sonores]
		with self.connexion.transaction():
			lus = self.connexion.execute(f"{SONORES_LUS} WHERE s.emplacement = ANY(%s)", (fichiers,)).fetchall()
		par_fichier = {str(sonore[4]): sonore for sonore in lus}
		presents: set[object] = set(self._sonores())
		presents |= {ligne.data(0, FICHIER) for ligne in self._lignes()}
		lignes = []
		for fichier in fichiers:
			sonore = par_fichier.get(fichier, (None, None, None, None, fichier, fichier))
			cle = sonore[0]
			if cle is None:
				cle = fichier
			if cle not in presents:
				presents.add(cle)
				lignes.append(self._ligne(sonore))
		self.ui.sonores.addTopLevelItems(lignes)
		self._actualiser_boutons()
		ignores = [chemin for chemin in chemins if chemin not in sonores]
		self._signaler_ignores(ignores, "ce ne sont pas des fichiers sonores", DOSSIER_SUR_LES_SONORES)

	def _signaler_ignores(self, ignores: list[Path], raison: str, conseil: str = "") -> None:
		if ignores != []:
			self.ui.message.setText(f"Ignorés, {raison} : {', '.join(chemin.name for chemin in ignores)}.{conseil}")

	def _montrer_repertoires(self, repertoires: list[str]) -> None:
		"""Dans l'ordre de leurs caractères, quelle que soit la langue du poste."""
		self.ui.repertoires.clear()
		self.ui.repertoires.addItems(sorted(repertoires))

	def _retirer_repertoire(self) -> None:
		self.ui.repertoires.takeItem(self.ui.repertoires.currentRow())
		self._modifier()

	def _ajouter_sonores(self) -> None:
		choisis = dialogues.choisir_sonores(self, self.connexion)
		presents = set(self._sonores())
		nouveaux = [sonore for sonore in choisis if sonore not in presents]
		with self.connexion.transaction():
			lus = self.connexion.execute(f"{SONORES_LUS} WHERE s.id = ANY(%s)", (nouveaux,)).fetchall()
		par_identifiant = {int(str(sonore[0])): sonore for sonore in lus}
		lignes = [self._ligne(par_identifiant[sonore]) for sonore in nouveaux if sonore in par_identifiant]
		self.ui.sonores.addTopLevelItems(lignes)
		self._actualiser_boutons()

	def _retirer_sonore(self) -> None:
		ligne = self.ui.sonores.currentItem()
		if ligne is None:
			return
		fichier = ligne.data(0, FICHIER)
		repertoire = self._repertoire_de(fichier)
		reponse = Retrait.RETIRER
		if repertoire is not None:
			reponse = dialogues.confirmer_retrait(self, avertissement_retrait(ligne.text(0), repertoire))
		if reponse is Retrait.RETIRER:
			self.ui.sonores.takeTopLevelItem(self.ui.sonores.indexOfTopLevelItem(ligne))
		elif reponse is Retrait.OUVRIR_DOSSIER:
			dialogues.ouvrir_dossier(Path(str(fichier)).parent)
		self._actualiser_boutons()

	def _repertoire_de(self, fichier: object) -> str | None:
		"""Le répertoire de la fiche où se trouve le fichier, même dans un sous-répertoire ; None hors de tous."""
		if not isinstance(fichier, str):
			return None
		chemin = Path(fichier)
		for repertoire in self._repertoires():
			if chemin.is_relative_to(repertoire):
				return repertoire
		return None

	def _deplacer(self, decalage: int) -> None:
		liste = self.ui.sonores
		ligne = liste.currentItem()
		if ligne is None:
			return
		rangee = liste.indexOfTopLevelItem(ligne)
		liste.takeTopLevelItem(rangee)
		liste.insertTopLevelItem(rangee + decalage, ligne)
		# Rendue courante, la ligne déplacée met à jour les boutons (currentItemChanged).
		liste.setCurrentItem(ligne)


def _texte(valeur: object) -> str | None:
	if valeur is None:
		return None
	return str(valeur)
