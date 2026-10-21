"""Fiche d'une banque (https://github.com/dascritch/machincast/issues/31, spec § 8.4).

La fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.fenetre), depuis la liste des banques, ou vide pour
une nouvelle banque. Enregistrement, annulation et fermeture : machincast.interface.fiche.

- Les noms sont enregistrés conformés (machincast.conformation, https://github.com/dascritch/machincast/issues/108) ; un
  nom public vide n'en est pas un (NULL).
- Le masquage « hérité du sonore » (NULL) laisse décider le sonore ; « masqués » et « affichés » l'imposent.
- Les répertoires sont enregistrés sous leur forme normale, comme les lit Machin indexation.
- Crossfades (https://github.com/dascritch/machincast/issues/143) : pour le début comme pour la fin, une règle et une
  durée. « Garder ceux des sonores » laisse le crossfade de chaque sonore, et la durée de la banque, gardée pour
  plus tard, ne se modifie pas ; « Appliquer si le sonore n'en a pas » la donne aux sonores sans crossfade
  (0 seconde) ; « Imposer à tous les sonores », à tous. La diffusion l'applique aux sonores joués via la banque
  (machincast.lecture.diffusion.crossfade).
- Durées des sonores (https://github.com/dascritch/machincast/issues/147) : une durée minimale et une durée maximale,
  facultatives, à cocher. Un sonore qui en sort est marqué dans la liste, d'après les durées de la fiche, avant même
  l'enregistrement ; rien n'est refusé, la diffusion n'en tient pas compte. Une minimale qui dépasse la maximale
  n'est pas enregistrée.
- Ouvrir un sonore, par un double-clic ou Entrée, ouvre sa fiche (https://github.com/dascritch/machincast/issues/115) ;
  la banque reste telle quelle, modifications comprises. Un fichier déposé n'a de fiche qu'une fois enregistré.
- Les sonores se réordonnent par glisser-déposer, ou par les boutons « Monter » et « Descendre », en mode séquentiel
  seulement. Ils s'ajoutent parmi les sonores déjà en base (machincast.interface.choix), y compris hors des
  répertoires de la banque.
- Des dossiers déposés depuis le navigateur de fichiers s'ajoutent aux répertoires, des fichiers sonores aux sonores
  (machincast.interface.depot), toujours comme une copie. Un fichier pas encore en base devient un sonore à l'état
  aperçu à l'enregistrement seulement.
- Retirer un sonore dont le fichier est dans l'un des répertoires de la fiche prévient que la prochaine indexation
  l'y remettra, et propose d'ouvrir son dossier : le fichier ne s'écarte que hors de MachinCast
  (https://github.com/dascritch/machincast/issues/96).
- À l'enregistrement, les sonores qu'une indexation a rattachés à la banque depuis l'ouverture de la fiche sont gardés,
  en fin de liste ; un sonore effacé de la base entre-temps est oublié.
- Sélection multiple (https://github.com/dascritch/machincast/issues/114) : Ctrl et Maj choisissent plusieurs sonores.
  « Retirer le sonore » les retire tous, avec un seul avertissement pour ceux des répertoires de la fiche ; « Monter »
  et « Descendre » ne servent qu'à un sonore seul. Le clic droit propose « Activer » et « Désactiver » : la colonne
  État montre aussitôt l'état choisi, que « Enregistrer » écrit avec le reste de la fiche et qu'« Annuler » oublie.
  Un sonore en aperçu reste en aperçu, un fichier déposé aussi.
- Sa copie (https://github.com/dascritch/machincast/issues/130) garde tout sauf sa liste de sonores : nom public, mode,
  masquage, « ne pas répéter », crossfades, durées et répertoires. Ses répertoires la rempliront à la prochaine
  indexation.

Les fenêtres de dialogue sont celles de machincast.interface.dialogues.
"""

import os
from datetime import timedelta
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTime
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
	QAbstractItemView,
	QCheckBox,
	QComboBox,
	QDoubleSpinBox,
	QHeaderView,
	QMenu,
	QTimeEdit,
	QTreeWidgetItem,
	QWidget,
)

from machincast.conformation import conformer
from machincast.horloge import Horloge
from machincast.interface import affichage, dialogues, preferences
from machincast.interface.depot import DepotDeFichiers
from machincast.interface.dialogues import Retrait
from machincast.interface.fiche import Connexion, Fiche, Refus, fichiers_sonores
from machincast.interface.listes import ETATS
from machincast.interface.ui.fiche_banque import Ui_FicheBanque

MODES = (("sequentiel", "Séquentielle"), ("aleatoire", "Aléatoire"))
REGLES_DE_CROSSFADE = (
	("sonore", "Garder ceux des sonores"),
	("a_defaut", "Appliquer si le sonore n'en a pas"),
	("impose", "Imposer à tous les sonores"),
)
MASQUAGES: tuple[tuple[bool | None, str], ...] = ((None, "Hérité du sonore"), (True, "Masqués"), (False, "Affichés"))
"""Valeurs de banques.masquer_metadonnees, dans l'ordre du choix de la fiche."""
SONORE = Qt.ItemDataRole.UserRole
"""Rôle qui porte, sur la première colonne d'une ligne de sonore, son identifiant en base."""
FICHIER = Qt.ItemDataRole.UserRole + 1
"""Rôle qui porte le chemin du fichier du sonore, None pour un stream."""
DUREE = Qt.ItemDataRole.UserRole + 2
"""Rôle qui porte la durée du sonore, absente quand elle est inconnue."""
ETAT = Qt.ItemDataRole.UserRole + 3
"""Rôle qui porte l'état du sonore en base ; « apercu » pour un fichier déposé."""
ETAT_CHOISI = Qt.ItemDataRole.UserRole + 4
"""Rôle qui porte l'état choisi au clic droit, écrit à l'enregistrement ; absent sans choix."""
COLONNE_ETAT = 2
ETATS_CHOISIS = (("actif", "Activer"), ("desactive", "Désactiver"))
"""Les états qui se choisissent au clic droit sur les sonores, et leur entrée de menu."""
LIGNE = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDragEnabled
"""Une ligne de sonore se glisse, mais rien ne se dépose dedans : la liste reste à plat."""
SONORES_LUS = (
	"SELECT s.id, s.artiste, s.titre, s.duree, s.emplacement, COALESCE(s.emplacement, s.url_stream, m.url),"
	" s.etat::text"
	" FROM sonores s LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id"
)


DEJA_DANS_LA_BANQUE = "Un sonore qui est déjà dans la banque n'y est pas ajouté une seconde fois."
"""Remarque du choix des sonores."""
DOSSIER_SUR_LES_SONORES = " Un dossier se dépose sur les répertoires indexés."
"""Conseil pour un dossier déposé sur les sonores."""


def avertissement_retrait_groupe(sonores: list[str], repertoires: list[str]) -> str:
	"""L'avertissement d'un retrait de sonores des répertoires de la banque ; celui d'un seul sonore, pour un seul."""
	if (len(sonores) == 1) and (len(repertoires) == 1):
		return avertissement_retrait(sonores[0], repertoires[0])
	noms = ", ".join(f"« {sonore} »" for sonore in sonores)
	ou = f"du répertoire {repertoires[0]}, indexé"
	if len(repertoires) > 1:
		ou = f"des répertoires {', '.join(repertoires)}, indexés"
	return (
		f"{noms} sont des fichiers {ou} par cette banque : la prochaine indexation les y remettra. Pour les écarter"
		" pour de bon, déplacez leurs fichiers hors de ces répertoires, en dehors de MachinCast."
	)


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
		self.brancher(self.ui.enregistrer, self.ui.annuler, self.ui.supprimer, self.ui.message, self.ui.dupliquer)
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
		self.ui.detection_blancs.toggled.connect(self._modifier)
		for regle, duree in self._crossfades():
			for valeur, texte in REGLES_DE_CROSSFADE:
				regle.addItem(texte, valeur)
			# Le pas et la durée maximale des préférences (https://github.com/dascritch/machincast/issues/145).
			preferences.regler_selon_les_preferences(duree)
			regle.currentIndexChanged.connect(self._modifier)
			regle.currentIndexChanged.connect(self._actualiser_crossfades)
			duree.valueChanged.connect(self._modifier)
		for case, champ in self._durees():
			case.toggled.connect(champ.setEnabled)
			case.toggled.connect(self._modifier)
			case.toggled.connect(self._marquer_hors_durees)
			champ.timeChanged.connect(self._modifier)
			champ.timeChanged.connect(self._marquer_hors_durees)
		modele = self.ui.sonores.model()
		# Le glisser-déposer déplace une ligne en la retirant, puis en l'insérant.
		modele.rowsInserted.connect(self._modifier)
		modele.rowsInserted.connect(self._marquer_hors_durees)
		modele.rowsRemoved.connect(self._modifier)
		self.ui.repertoires.currentItemChanged.connect(self._actualiser_boutons)
		self.ui.sonores.currentItemChanged.connect(self._actualiser_boutons)
		self.ui.sonores.itemSelectionChanged.connect(self._actualiser_boutons)
		self.ui.sonores.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.ui.sonores.customContextMenuRequested.connect(self._menu_des_sonores)
		self.ui.sonores.itemActivated.connect(self._ouvrir_sonore)
		self.ui.ajouter_repertoire.clicked.connect(self._ajouter_repertoire)
		self.ui.retirer_repertoire.clicked.connect(self._retirer_repertoire)
		self.ui.ajouter_sonores.clicked.connect(self._ajouter_sonores)
		self.ui.retirer_sonore.clicked.connect(self._retirer_sonore)
		self.ui.monter.clicked.connect(lambda: self._deplacer(-1))
		self.ui.descendre.clicked.connect(lambda: self._deplacer(1))
		self.charger()

	def titre(self) -> str:
		if self.est_une_copie():
			return f"Nouvelle banque, copie de {self._nom}"
		if self.identifiant is None:
			return "Nouvelle banque"
		return f"Banque : {self._nom}"

	def _lire(self) -> None:
		"""Lit la banque en base, ou celle qu'elle copie, sans ses sonores ; une nouvelle banque est vide, séquentielle,
		au masquage hérité du sonore, sans détection de blanc (https://github.com/dascritch/machincast/issues/146)."""
		banque: tuple[object, ...] = (
			"",
			None,
			MODES[0][0],
			None,
			False,
			"sonore",
			timedelta(0),
			"sonore",
			timedelta(0),
			None,
			None,
			False,
		)
		repertoires: list[str] = []
		sonores: list[tuple[object, ...]] = []
		lu = self.lu()
		with self.connexion.transaction():
			if lu is not None:
				ligne = self.connexion.execute(
					"SELECT nom_interne, nom_public, mode::text, masquer_metadonnees, ne_pas_repeter,"
					" crossfade_debut_regle::text, crossfade_debut, crossfade_fin_regle::text, crossfade_fin,"
					" duree_min, duree_max, detection_blancs FROM banques WHERE id = %s",
					(lu,),
				).fetchone()
				assert ligne is not None, f"banque {lu} absente"
				banque = ligne
				repertoires = [
					str(repertoire)
					for (repertoire,) in self.connexion.execute(
						"SELECT repertoire FROM banques_repertoires WHERE banque_id = %s", (lu,)
					)
				]
			if self.identifiant is not None:
				sonores = self.connexion.execute(
					f"{SONORES_LUS} JOIN banques_sonores bs ON bs.sonore_id = s.id"
					" WHERE bs.banque_id = %s ORDER BY bs.position",
					(self.identifiant,),
				).fetchall()
		nom, nom_public, mode, masquage, ne_pas_repeter, *crossfades, duree_min, duree_max, detection = banque
		self._nom = str(nom)
		self.ui.nom_interne.setText(self._nom)
		if self.est_une_copie():
			self.ui.nom_interne.setText(self.nom_de_la_copie(self._nom))
		self.ui.nom_public.setText(str((nom_public) or ("")))
		self.ui.mode.setCurrentIndex(self.ui.mode.findData(mode))
		self.ui.masquage.setCurrentIndex(next(i for i, (valeur, _texte) in enumerate(MASQUAGES) if valeur is masquage))
		self.ui.ne_pas_repeter.setChecked(bool(ne_pas_repeter))
		self.ui.detection_blancs.setChecked(detection is True)
		for (regle, duree), (valeur, secondes) in zip(
			self._crossfades(), (crossfades[:2], crossfades[2:]), strict=True
		):
			regle.setCurrentIndex(regle.findData(valeur))
			if isinstance(secondes, timedelta):
				preferences.montrer(duree, secondes.total_seconds())
		self._actualiser_crossfades()
		for (case, champ), borne in zip(self._durees(), (duree_min, duree_max), strict=True):
			case.setChecked(isinstance(borne, timedelta))
			if isinstance(borne, timedelta):
				champ.setTime(QTime(0, 0).addSecs(int(borne.total_seconds())))
		self._montrer_repertoires(repertoires)
		self.ui.sonores.clear()
		self.ui.sonores.addTopLevelItems([self._ligne(sonore) for sonore in sonores])
		self._charges = set(self._sonores())
		self._actualiser_boutons()

	def _ecrire(self) -> int:
		nom = conformer(self.ui.nom_interne.text())
		if nom == "":
			raise Refus("Le nom interne est obligatoire.")
		pris = self.connexion.execute(
			"SELECT 1 FROM banques WHERE nom_interne = %s AND id IS DISTINCT FROM %s", (nom, self.identifiant)
		).fetchone()
		if pris is not None:
			raise Refus(f"Une autre banque s'appelle déjà « {nom} ».")
		valeurs: list[object] = [
			nom,
			(conformer(self.ui.nom_public.text())) or (None),
			self.ui.mode.currentData(),
			MASQUAGES[self.ui.masquage.currentIndex()][0],
			self.ui.ne_pas_repeter.isChecked(),
		]
		for regle, duree in self._crossfades():
			valeurs += [regle.currentData(), timedelta(seconds=duree.value())]
		minimum, maximum = self._bornes()
		if (minimum is not None) and (maximum is not None) and (minimum > maximum):
			raise Refus("La durée minimale des sonores dépasse la durée maximale.")
		valeurs += [minimum, maximum, self.ui.detection_blancs.isChecked()]
		if self.identifiant is None:
			creee = self.connexion.execute(
				"INSERT INTO banques (nom_interne, nom_public, mode, masquer_metadonnees, ne_pas_repeter,"
				" crossfade_debut_regle, crossfade_debut, crossfade_fin_regle, crossfade_fin, duree_min, duree_max,"
				" detection_blancs) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
				valeurs,
			).fetchone()
			assert creee is not None
			identifiant = int(str(creee[0]))
		else:
			identifiant = self.identifiant
			self.connexion.execute(
				"UPDATE banques SET nom_interne = %s, nom_public = %s, mode = %s, masquer_metadonnees = %s,"
				" ne_pas_repeter = %s, crossfade_debut_regle = %s, crossfade_debut = %s, crossfade_fin_regle = %s,"
				" crossfade_fin = %s, duree_min = %s, duree_max = %s, detection_blancs = %s WHERE id = %s",
				(*valeurs, identifiant),
			)
		self.connexion.execute("DELETE FROM banques_repertoires WHERE banque_id = %s", (identifiant,))
		self.connexion.execute(
			"INSERT INTO banques_repertoires (banque_id, repertoire) SELECT %s, unnest(%s::text[])",
			(identifiant, self._repertoires()),
		)
		self._ecrire_sonores(identifiant)
		self._ecrire_les_etats()
		return identifiant

	def _ecrire_les_etats(self) -> None:
		"""Les états choisis au clic droit ; un sonore passé en aperçu entre-temps y reste."""
		for ligne in self._lignes():
			choisi = ligne.data(0, ETAT_CHOISI)
			sonore = ligne.data(0, SONORE)
			if (choisi is not None) and (sonore is not None):
				self.connexion.execute(
					"UPDATE sonores SET etat = %s WHERE id = %s AND etat <> 'apercu'", (choisi, int(sonore))
				)

	def menu_des_sonores(self, ligne: QTreeWidgetItem | None) -> QMenu | None:
		"""Le menu du clic droit sur cette ligne : sur les sonores choisis si elle en fait partie, sur elle seule
		sinon ; aucun hors d'une ligne."""
		if ligne is None:
			return None
		lignes = self.ui.sonores.selectedItems()
		if ligne not in lignes:
			lignes = [ligne]
		menu = QMenu(self)
		for etat, texte in ETATS_CHOISIS:
			entree = menu.addAction(texte)
			entree.triggered.connect(lambda _coche=False, etat=etat: self._choisir_l_etat(lignes, etat))
		return menu

	def _menu_des_sonores(self, position: QPoint) -> None:
		menu = self.menu_des_sonores(self.ui.sonores.itemAt(position))
		if menu is not None:
			menu.exec(self.ui.sonores.viewport().mapToGlobal(position))
			menu.deleteLater()

	def _choisir_l_etat(self, lignes: list[QTreeWidgetItem], etat: str) -> None:
		"""L'état choisi se montre aussitôt ; un sonore en aperçu, ou pas encore en base, garde le sien."""
		for ligne in lignes:
			if ligne.data(0, ETAT) == "apercu":
				continue
			ligne.setData(0, ETAT_CHOISI, etat)
			ligne.setText(COLONNE_ETAT, ETATS[etat])
		self._modifier()

	def _crossfades(self) -> tuple[tuple[QComboBox, QDoubleSpinBox], tuple[QComboBox, QDoubleSpinBox]]:
		"""La règle et la durée du crossfade de début, puis celles du crossfade de fin."""
		ui = self.ui
		return ((ui.regle_crossfade_debut, ui.crossfade_debut), (ui.regle_crossfade_fin, ui.crossfade_fin))

	def _durees(self) -> tuple[tuple[QCheckBox, QTimeEdit], tuple[QCheckBox, QTimeEdit]]:
		"""La case et le champ de la durée minimale des sonores, puis ceux de la durée maximale."""
		ui = self.ui
		return ((ui.a_duree_min, ui.duree_min), (ui.a_duree_max, ui.duree_max))

	def _bornes(self) -> tuple[timedelta | None, timedelta | None]:
		"""Les durées minimale et maximale de la fiche ; None pour une durée décochée."""
		bornes: list[timedelta | None] = []
		for case, champ in self._durees():
			borne = None
			if case.isChecked():
				borne = timedelta(seconds=QTime(0, 0).secsTo(champ.time()))
			bornes.append(borne)
		return bornes[0], bornes[1]

	def _marquer_hors_durees(self) -> None:
		"""Les sonores hors des durées de la fiche ont l'icône d'anomalie et une infobulle qui dit pourquoi ; un sonore
		de durée inconnue, ou dans les durées, n'a ni l'une ni l'autre."""
		minimum, maximum = self._bornes()
		for ligne in self._lignes():
			ecart = affichage.hors_durees(ligne.data(0, DUREE), minimum, maximum)
			ligne.setIcon(0, QIcon())
			ligne.setToolTip(0, "")
			if ecart is not None:
				ligne.setIcon(0, affichage.icone_d_anomalie(self))
				ligne.setToolTip(0, ecart)

	def _actualiser_crossfades(self) -> None:
		"""La durée d'une banque qui garde les crossfades de ses sonores ne sert pas : elle ne se modifie pas."""
		for regle, duree in self._crossfades():
			duree.setEnabled(regle.currentData() != "sonore")

	def _ecrire_sonores(self, banque: int) -> None:
		voulus = []
		for ligne in self._lignes():
			identifiant = ligne.data(0, SONORE)
			if identifiant is None:
				identifiant = self.enregistrer_fichier(str(ligne.data(0, FICHIER)))
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

	def _ligne(self, sonore: tuple[object, ...]) -> QTreeWidgetItem:
		"""Une ligne de sonore ; un fichier déposé, pas encore en base, n'a pas d'identifiant."""
		identifiant, artiste, titre, duree, fichier, emplacement, etat = sonore
		texte_duree = ""
		if fichier is None:
			texte_duree = affichage.duree(None)
		elif isinstance(duree, timedelta):
			texte_duree = affichage.duree(duree)
		texte = affichage.artiste_et_titre(_texte(artiste), _texte(titre))
		if (artiste is None) and (titre is None) and (fichier is not None):
			# Pas encore décodé : le nom du fichier en attendant ses tags.
			texte = Path(str(fichier)).name
		ligne = QTreeWidgetItem([texte, texte_duree, ETATS.get(str(etat), str(etat)), str((emplacement) or (""))])
		ligne.setData(0, ETAT, str(etat))
		if identifiant is not None:
			ligne.setData(0, SONORE, int(str(identifiant)))
		ligne.setData(0, FICHIER, _texte(fichier))
		if isinstance(duree, timedelta):
			ligne.setData(0, DUREE, duree)
		ligne.setFlags(LIGNE)
		return ligne

	def _ouvrir_sonore(self, ligne: QTreeWidgetItem) -> None:
		"""Ouvrir un sonore demande sa fiche ; un fichier déposé n'en a pas avant l'enregistrement."""
		identifiant = ligne.data(0, SONORE)
		if identifiant is not None:
			self.ouverture_demandee.emit("sonore", int(identifiant), ligne.text(0))

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
		choisies = liste.selectedItems()
		self.ui.retirer_sonore.setEnabled(choisies != [])
		rangee = -1
		if len(choisies) == 1:
			rangee = liste.indexOfTopLevelItem(choisies[0])
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
		self.signaler_ignores([chemin for chemin in chemins if not chemin.is_dir()], "ce ne sont pas des répertoires")

	def _deposer_sonores(self, chemins: list[Path]) -> None:
		"""Les fichiers sonores déposés s'ajoutent en fin de liste, une fois chacun. Un fichier pas encore en base est
		montré par son nom, et deviendra un sonore à l'état aperçu à l'enregistrement."""
		fichiers, ignores = fichiers_sonores(chemins)
		with self.connexion.transaction():
			lus = self.connexion.execute(f"{SONORES_LUS} WHERE s.emplacement = ANY(%s)", (fichiers,)).fetchall()
		par_fichier = {str(sonore[4]): sonore for sonore in lus}
		presents: set[object] = set(self._sonores())
		presents |= {ligne.data(0, FICHIER) for ligne in self._lignes()}
		lignes = []
		for fichier in fichiers:
			sonore = par_fichier.get(fichier, (None, None, None, None, fichier, fichier, "apercu"))
			cle = sonore[0]
			if cle is None:
				cle = fichier
			if cle not in presents:
				presents.add(cle)
				lignes.append(self._ligne(sonore))
		self.ui.sonores.addTopLevelItems(lignes)
		self._actualiser_boutons()
		self.signaler_ignores(ignores, "ce ne sont pas des fichiers sonores", DOSSIER_SUR_LES_SONORES)

	def _montrer_repertoires(self, repertoires: list[str]) -> None:
		"""Dans l'ordre de leurs caractères, quelle que soit la langue du poste."""
		self.ui.repertoires.clear()
		self.ui.repertoires.addItems(sorted(repertoires))

	def _retirer_repertoire(self) -> None:
		self.ui.repertoires.takeItem(self.ui.repertoires.currentRow())
		self._modifier()

	def _ajouter_sonores(self) -> None:
		choisis = dialogues.choisir_sonores(self, self.connexion, DEJA_DANS_LA_BANQUE)
		presents = set(self._sonores())
		nouveaux = [sonore for sonore in choisis if sonore not in presents]
		with self.connexion.transaction():
			lus = self.connexion.execute(f"{SONORES_LUS} WHERE s.id = ANY(%s)", (nouveaux,)).fetchall()
		par_identifiant = {int(str(sonore[0])): sonore for sonore in lus}
		lignes = [self._ligne(par_identifiant[sonore]) for sonore in nouveaux if sonore in par_identifiant]
		self.ui.sonores.addTopLevelItems(lignes)
		self._actualiser_boutons()

	def _retirer_sonore(self) -> None:
		"""Les sonores choisis ; ceux des répertoires de la fiche y reviendront à la prochaine indexation, ce qu'un seul
		avertissement dit pour tous. « Ouvrir le dossier » ouvre celui du premier."""
		lignes = [ligne for ligne in self._lignes() if ligne.isSelected()]
		if lignes == []:
			return
		reintegres = [
			(ligne, repertoire)
			for ligne in lignes
			if (repertoire := self._repertoire_de(ligne.data(0, FICHIER))) is not None
		]
		reponse = Retrait.RETIRER
		if reintegres != []:
			sonores = [ligne.text(0) for ligne, _repertoire in reintegres]
			repertoires = list(dict.fromkeys(repertoire for _ligne, repertoire in reintegres))
			reponse = dialogues.confirmer_retrait(self, avertissement_retrait_groupe(sonores, repertoires))
		if reponse is Retrait.RETIRER:
			for ligne in lignes:
				self.ui.sonores.takeTopLevelItem(self.ui.sonores.indexOfTopLevelItem(ligne))
			# La ligne qui suit devient la ligne choisie, prête à être retirée à son tour.
			suivante = self.ui.sonores.currentItem()
			if suivante is not None:
				self.ui.sonores.setCurrentItem(suivante)
		elif reponse is Retrait.OUVRIR_DOSSIER:
			premiere, _repertoire = reintegres[0]
			dialogues.ouvrir_dossier(Path(str(premiere.data(0, FICHIER))).parent)
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
