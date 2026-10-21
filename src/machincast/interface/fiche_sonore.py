"""Fiche d'un sonore (https://github.com/dascritch/machincast/issues/28, spec § 8.3).

La fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.fenetre), depuis la liste des sonores, ou vide
pour un nouveau stream (https://github.com/dascritch/machincast/issues/30), qui entre en base à l'état actif ; un
fichier s'ajoute depuis la liste (machincast.interface.ajout). Enregistrement, annulation et fermeture :
machincast.interface.fiche.

- Champs : artiste, titre, les métadonnées musicales que tient l'indexeur (année, album, artiste de l'album, genre,
  compositeur, label, piste), crossfades, maximum de lectures, masquage, période de diffusion, état, et pour un fichier
  la détection de blanc, avec le début et la fin détectés (https://github.com/dascritch/machincast/issues/146). Les
  autres clés des métadonnées musicales sont montrées, jamais modifiées. L'emplacement et la durée ne se modifient pas.
- Seuls les champs modifiés depuis la lecture de la fiche sont écrits : ce que l'indexation ou la diffusion change
  entre-temps est gardé. Chacun est ajouté à champs_edites, sauf l'état, que l'indexeur peut encore changer
  (fichier défectueux, puis de nouveau sain) : l'indexeur ne modifie plus un champ édité.
- État : l'interface pose « actif » ou « désactivé » ; un sonore expiré, erroné ou supprimé peut y revenir. Un sonore
  en aperçu attend sa première indexation.
- Stream : adresse directe ou marque-page, événement de secours parmi les événements de priorité secours, et test du
  flux à la demande (machincast.interface.essai_flux), sur l'adresse saisie, même pas encore enregistrée.
- Derniers passages : les 50 derniers, du plus récent au plus ancien, avec les alertes et incidents du log pendant
  chaque passage.
- Relations (https://github.com/dascritch/machincast/issues/125) : les séquences, banques et événements qui citent le
  sonore dans leur liste ; un double-clic ouvre leur fiche.
- Fichier : type lu par l'indexeur (https://github.com/dascritch/machincast/issues/121), encodage moyen (taille sur
  durée, pochette et tags compris), taille, dates de création et de modification lues sur le fichier, qui n'est que lu,
  et date de sa dernière vérification complète par l'indexeur. Le bouton du dossier ouvre le dossier du fichier dans
  le navigateur de fichiers du poste.
- Encarts (https://github.com/dascritch/machincast/issues/190) : « Métadonnées », « Diffusion », « Détection de
  blanc », « Relations » et « Fichier » sont repliés à l'ouverture de la fiche, et se déplient d'un clic sur leur
  titre (machincast.interface.depliable).
- « Vérification complète », pour un fichier enregistré, demande l'audit complet de ce seul sonore
  (verification_demandee) ; le bouton attend sa fin (attendre_la_verification), puis une question propose de
  rafraîchir la fiche (verification_terminee).
"""

import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from psycopg import sql
from psycopg.types.json import Jsonb
from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QCheckBox, QDateTimeEdit, QDoubleSpinBox, QLineEdit, QTableWidgetItem, QWidget

from machincast.conformation import conformer
from machincast.conversion import duree_ou_rien, texte_ou_rien
from machincast.horloge import Horloge
from machincast.interface import affichage, depliable, dialogues, icones, preferences
from machincast.interface.colonnes import Colonnes
from machincast.interface.essai_flux import EssaiDeFlux, resultat_de_l_essai
from machincast.interface.fiche import Connexion, Fiche, Refus
from machincast.interface.listes import ETATS
from machincast.interface.ui.fiche_sonore import Ui_FicheSonore

METADONNEES: tuple[tuple[str, str], ...] = (
	("annee", "année"),
	("album", "album"),
	("artiste_album", "artiste de l'album"),
	("genre", "genre"),
	("compositeur", "compositeur"),
	("label", "label"),
	("piste", "piste"),
)
"""Clés de metadonnees_musicales tenues par l'indexeur (machincast.indexation.tags.CLES), et leur nom à l'écran."""
ENTIERS = frozenset({"annee", "piste"})
"""Clés dont la valeur est un nombre entier."""
LIBELLES: dict[str, str] = {
	"artiste": "artiste",
	"titre": "titre",
	**{f"metadonnees_musicales.{cle}": nom for cle, nom in METADONNEES},
	"crossfade_debut": "crossfade de début",
	"crossfade_fin": "crossfade de fin",
	"max_lectures": "maximum de lectures",
	"masquer_metadonnees": "artiste et titre",
	"debut_diffusion": "début de diffusion",
	"fin_diffusion": "fin de diffusion",
	"url_stream": "adresse directe",
	"marque_page_id": "marque-page",
	"secours_evenement_id": "événement de secours",
	"detection_blancs": "détection de blanc",
	"debut_detecte": "début détecté",
	"fin_detectee": "fin détectée",
	"duree": "durée",
}
"""Nom à l'écran d'un champ de champs_edites."""
CHOIX_ETATS: dict[str, tuple[str, ...]] = {
	"apercu": ("apercu",),
	"actif": ("actif", "desactive"),
	"desactive": ("desactive", "actif"),
	"expire": ("expire", "actif", "desactive"),
	"errone": ("errone", "actif", "desactive"),
	"non_supporte": ("non_supporte", "actif", "desactive"),
	"supprime": ("supprime", "actif", "desactive"),
}
"""L'état du sonore, puis ceux que l'interface peut poser."""
MASQUAGES: tuple[tuple[bool | None, str], ...] = (
	(None, "Selon la configuration"),
	(True, "Masqués"),
	(False, "Affichés"),
)
"""Valeurs de sonores.masquer_metadonnees, dans l'ordre du choix de la fiche."""
NOUVEAU_STREAM: tuple[object, ...] = (
	"stream",
	None,
	None,
	None,
	None,
	None,
	None,
	None,
	{},
	timedelta(0),
	timedelta(0),
	None,
	"actif",
	None,
	None,
	None,
	None,
	[],
	None,
	None,
	False,
	None,
	None,
)
"""Ce que montre la fiche d'un nouveau stream, dans l'ordre des colonnes lues."""
RELATION = Qt.ItemDataRole.UserRole
"""Rôle qui porte, sur la cellule du nom d'une relation, son genre et son identifiant."""
PASSAGES = 50
"""Nombre de derniers passages montrés."""
URL = Qt.ItemDataRole.UserRole + 1
"""Rôle qui porte l'adresse d'un marque-page, dans son choix."""


DELAI_DE_STAT = 5
"""Secondes laissées à stat pour lire la date de création d'un fichier, sur un partage réseau par exemple."""


class FicheSonore(Fiche):
	preecoute_demandee = Signal(int)
	"""« Pré-écoute… » : le sonore à écouter dans la fenêtre de pré-écoute
	(https://github.com/dascritch/machincast/issues/116)."""
	verification_demandee = Signal(int)
	"""« Vérification complète » : le sonore dont faire l'audit complet
	(https://github.com/dascritch/machincast/issues/190)."""
	genre = "sonore"

	def __init__(
		self, connexion: Connexion, identifiant: int | None, horloge: Horloge, parent: QWidget | None = None
	) -> None:
		super().__init__(connexion, identifiant, horloge, parent)
		self.ui = Ui_FicheSonore()
		self.ui.setupUi(self)
		self.brancher(self.ui.enregistrer, self.ui.annuler, self.ui.supprimer, self.ui.message)
		self.metadonnees: dict[str, QLineEdit] = {cle: getattr(self.ui, cle) for cle, _nom in METADONNEES}
		for cle in ENTIERS:
			self.metadonnees[cle].setValidator(QIntValidator(0, 9999, self))
		# Le pas et la durée maximale des préférences (https://github.com/dascritch/machincast/issues/145).
		for crossfade in (self.ui.crossfade_debut, self.ui.crossfade_fin):
			preferences.regler_selon_les_preferences(crossfade)
		for _valeur, texte in MASQUAGES:
			self.ui.masquage.addItem(texte)
		self.essai = EssaiDeFlux(self)
		self.ui.preecouter.clicked.connect(self._preecouter)
		self.ui.verifier.clicked.connect(self._verifier)
		self._fichier = False
		"""Le sonore lu est un fichier : seul un fichier se vérifie."""
		self._en_verification = False
		for groupe in (
			self.ui.groupe_metadonnees,
			self.ui.groupe_diffusion,
			self.ui.groupe_blancs,
			self.ui.groupe_relations,
			self.ui.groupe_fichier,
		):
			depliable.rendre_depliable(groupe)
		self.essai.termine.connect(self._essai_termine)
		self._nom = ""
		self._initiales: dict[str, object] = {}
		"""Champs tels que la fiche les a montrés à la lecture : seuls ceux qui en diffèrent sont écrits."""
		for champ in (self.ui.artiste, self.ui.titre, self.ui.url_stream, *self.metadonnees.values()):
			champ.textChanged.connect(self._modifier)
		for choix in (self.ui.etat, self.ui.masquage, self.ui.marque_page, self.ui.secours):
			choix.currentIndexChanged.connect(self._modifier)
		for nombre in (self.ui.crossfade_debut, self.ui.crossfade_fin, self.ui.max_lectures):
			nombre.valueChanged.connect(self._modifier)
		for case, nombre in (
			(self.ui.a_crossfade_debut, self.ui.crossfade_debut),
			(self.ui.a_crossfade_fin, self.ui.crossfade_fin),
		):
			case.toggled.connect(nombre.setEnabled)
			case.toggled.connect(self._modifier)
		# Détection de blanc (https://github.com/dascritch/machincast/issues/146) : un blanc décoché n'est pas détecté.
		self.ui.detection_blancs.toggled.connect(self._modifier)
		for case, nombre in (
			(self.ui.a_debut_detecte, self.ui.debut_detecte),
			(self.ui.a_fin_detectee, self.ui.fin_detectee),
		):
			nombre.setLocale(preferences.FRANCAIS)
			nombre.valueChanged.connect(self._modifier)
			case.toggled.connect(nombre.setEnabled)
			case.toggled.connect(self._modifier)
		self._duree: timedelta | None = None
		"""Durée du fichier en base, que les blancs détectés ne peuvent pas couvrir à eux deux."""
		for case, date in ((self.ui.a_debut, self.ui.debut_diffusion), (self.ui.a_fin, self.ui.fin_diffusion)):
			case.toggled.connect(date.setEnabled)
			case.toggled.connect(self._modifier)
			date.dateTimeChanged.connect(self._modifier)
		self.ui.par_adresse.toggled.connect(self._mode_stream)
		self.ui.par_adresse.toggled.connect(self._modifier)
		self.ui.tester.clicked.connect(self._tester)
		self.ui.ouvrir_dossier.clicked.connect(
			lambda: dialogues.ouvrir_dossier(Path(self.ui.emplacement.text()).parent)
		)
		self.ui.relations.itemActivated.connect(self._ouvrir_relation)
		self.colonnes_relations = Colonnes(self.ui.relations, "fiche-sonore-relations")
		self.colonnes_passages = Colonnes(self.ui.passages, "fiche-sonore-passages")
		self.charger()

	def titre(self) -> str:
		if self.identifiant is None:
			return "Nouveau stream"
		return f"Sonore : {self._nom}"

	def fermer(self) -> None:
		self.essai.arreter()

	def _preecouter(self) -> None:
		if self.identifiant is not None:
			self.preecoute_demandee.emit(self.identifiant)

	def _verifier(self) -> None:
		if self.identifiant is not None:
			self.verification_demandee.emit(self.identifiant)

	def attendre_la_verification(self) -> None:
		"""La vérification complète est lancée : le bouton attend sa fin."""
		self._en_verification = True
		self.ui.verifier.setText("Vérification…")
		self._actualiser_la_verification()
		self.message.setText("Vérification complète en cours…")

	def verification_terminee(self, texte: str) -> None:
		"""La vérification complète est finie : une question propose de rafraîchir la fiche, qui montre alors ce que
		l'indexeur a écrit."""
		self._en_verification = False
		self.ui.verifier.setText("Vérification complète")
		self._actualiser_la_verification()
		self.message.clear()
		if dialogues.proposer_rafraichissement(self, texte):
			self.rafraichir()

	def _actualiser_la_verification(self) -> None:
		"""Un fichier enregistré se vérifie, une seule fois à la fois ; un stream ne se vérifie pas."""
		self.ui.verifier.setEnabled((self.identifiant is not None) and (self._fichier) and (not self._en_verification))

	def _lire(self) -> None:
		"""Lit le sonore en base ; un nouveau stream est actif, sans adresse ni réglage."""
		# Un nouveau stream n'est pas encore en base : rien à pré-écouter avant son enregistrement.
		self.ui.preecouter.setEnabled(self.identifiant is not None)
		ligne: tuple[object, ...] | None = NOUVEAU_STREAM
		passages: list[tuple[object, ...]] = []
		relations: list[tuple[object, ...]] = []
		with self.connexion.transaction():
			if self.identifiant is not None:
				ligne = self._lire_sonore()
				passages = self._lire_passages()
				relations = self._lire_relations()
			marques = self.connexion.execute("SELECT id, nom, url FROM marques_pages_streams ORDER BY nom").fetchall()
			secours = self.connexion.execute(
				"SELECT id, nom_interne FROM evenements WHERE priorite = 'secours' ORDER BY nom_interne"
			).fetchall()
		assert ligne is not None, f"sonore {self.identifiant} absent"
		self._montrer(ligne, marques, secours, passages)
		self._montrer_relations(relations)

	def _lire_sonore(self) -> tuple[object, ...] | None:
		return self.connexion.execute(
			"SELECT s.type::text, s.emplacement, s.url_stream, s.marque_page_id, m.url, s.secours_evenement_id,"
			" s.artiste, s.titre, s.metadonnees_musicales, s.crossfade_debut, s.crossfade_fin, s.max_lectures,"
			" s.etat::text, s.masquer_metadonnees, s.duree, s.debut_diffusion, s.fin_diffusion, s.champs_edites,"
			" s.type_mime, s.verifie_le, s.detection_blancs, s.debut_detecte, s.fin_detectee"
			" FROM sonores s LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id WHERE s.id = %s",
			(self.identifiant,),
		).fetchone()

	def _montrer(
		self,
		ligne: tuple[object, ...],
		marques: list[tuple[object, ...]],
		secours: list[tuple[object, ...]],
		passages: list[tuple[object, ...]],
	) -> None:
		(
			type_sonore,
			emplacement,
			url_stream,
			marque_page,
			url_marque_page,
			evenement_secours,
			artiste,
			titre,
			metadonnees,
			crossfade_debut,
			crossfade_fin,
			max_lectures,
			etat,
			masquage,
			duree,
			debut,
			fin,
			champs_edites,
			type_mime,
			verifie_le,
			detection_blancs,
			debut_detecte,
			fin_detectee,
		) = ligne
		stream = type_sonore == "stream"
		self._nom = (texte_ou_rien(titre)) or (Path(str(emplacement)).name)
		if stream:
			self._nom = (texte_ou_rien(titre)) or (str((url_stream) or (url_marque_page)))
		self.ui.type_sonore.setText(str(type_sonore))
		self.ui.emplacement.setText(str((emplacement) or ("")))
		self.ui.formulaire_sonore.setRowVisible(self.ui.etiquette_emplacement, not stream)
		self.ui.groupe_fichier.setVisible(not stream)
		if not stream:
			self._montrer_fichier(Path(str(emplacement)), type_mime, duree, verifie_le)
		self._fichier = type_sonore == "fichier"
		self._actualiser_la_verification()
		self.ui.groupe_stream.setVisible(stream)
		# Un stream n'a pas de blancs détectés : seul un fichier est audité.
		self.ui.groupe_blancs.setVisible(not stream)
		self.ui.detection_blancs.setChecked(detection_blancs is True)
		for case, nombre, blanc in (
			(self.ui.a_debut_detecte, self.ui.debut_detecte, debut_detecte),
			(self.ui.a_fin_detectee, self.ui.fin_detectee, fin_detectee),
		):
			nombre.setValue(_secondes(blanc))
			case.setChecked(isinstance(blanc, timedelta))
		self._duree = None
		if isinstance(duree, timedelta):
			self._duree = duree
		texte_duree = ""
		if stream:
			texte_duree = affichage.duree(None)
		elif isinstance(duree, timedelta):
			texte_duree = affichage.duree(duree)
		self.ui.duree.setText(texte_duree)
		self.ui.etat.clear()
		for code in CHOIX_ETATS[str(etat)]:
			self.ui.etat.addItem(ETATS[code], code)
		self.ui.etat.setEnabled(self.ui.etat.count() > 1)
		self.ui.artiste.setText(str((artiste) or ("")))
		self.ui.titre.setText(str((titre) or ("")))
		assert isinstance(metadonnees, dict)
		musicales = dict(metadonnees)
		for cle, champ in self.metadonnees.items():
			champ.setText(str(musicales.pop(cle, "")))
		autres = [f"{cle} : {valeur}" for cle, valeur in sorted(musicales.items())]
		self.ui.autres_metadonnees.setText(", ".join(autres))
		# Un crossfade non paramétré (NULL) est décoché ; 0 seconde en est un (https://github.com/dascritch/machincast/issues/145).
		for case, nombre, crossfade in (
			(self.ui.a_crossfade_debut, self.ui.crossfade_debut, crossfade_debut),
			(self.ui.a_crossfade_fin, self.ui.crossfade_fin, crossfade_fin),
		):
			preferences.montrer(nombre, _secondes(crossfade))
			case.setChecked(isinstance(crossfade, timedelta))
		self.ui.max_lectures.setValue(int(str((max_lectures) or (0))))
		self.ui.masquage.setCurrentIndex(next(i for i, (valeur, _texte) in enumerate(MASQUAGES) if valeur is masquage))
		self._montrer_date(self.ui.a_debut, self.ui.debut_diffusion, debut)
		self._montrer_date(self.ui.a_fin, self.ui.fin_diffusion, fin)
		self.ui.marque_page.clear()
		for identifiant, nom, url in marques:
			self.ui.marque_page.addItem(str(nom), int(str(identifiant)))
			self.ui.marque_page.setItemData(self.ui.marque_page.count() - 1, str(url), URL)
		self.ui.par_marque_page.setEnabled(marques != [])
		self.ui.marque_page.setCurrentIndex(self.ui.marque_page.findData(marque_page))
		self.ui.url_stream.setText(str((url_stream) or ("")))
		self.ui.par_marque_page.setChecked(marque_page is not None)
		self.ui.par_adresse.setChecked(marque_page is None)
		self._mode_stream()
		self.ui.secours.clear()
		self.ui.secours.addItem("Aucun : le fil musical", None)
		for identifiant, nom in secours:
			self.ui.secours.addItem(str(nom), int(str(identifiant)))
		self.ui.secours.setCurrentIndex(self.ui.secours.findData(evenement_secours))
		edites = [LIBELLES.get(str(champ), str(champ)) for champ in _liste(champs_edites)]
		texte_edites = ""
		if edites != []:
			texte_edites = f"Saisis à la main, que l'indexeur ne modifie plus : {', '.join(edites)}."
		self.ui.champs_edites.setText(texte_edites)
		self._montrer_passages(passages)
		self._initiales = self._saisies()

	def _montrer_date(self, case: QCheckBox, date: QDateTimeEdit, valeur: object) -> None:
		"""Une période sans date part de l'heure de l'horloge, à la minute, quand sa case se coche."""
		instant = self.horloge.maintenant().replace(second=0, microsecond=0)
		if isinstance(valeur, datetime):
			instant = valeur
		date.setDateTime(QDateTime.fromSecsSinceEpoch(int(instant.timestamp())))
		# La case active la date quand elle change d'état (toggled).
		case.setChecked(isinstance(valeur, datetime))

	def _mode_stream(self) -> None:
		self.ui.url_stream.setEnabled(self.ui.par_adresse.isChecked())
		self.ui.marque_page.setEnabled(self.ui.par_marque_page.isChecked())

	def _saisies(self) -> dict[str, object]:
		"""Les champs modifiables, tels que la fiche les montre : colonne de sonores, ou metadonnees_musicales.<clé>."""
		saisies: dict[str, object] = {
			"artiste": (conformer(self.ui.artiste.text())) or (None),
			"titre": (conformer(self.ui.titre.text())) or (None),
		}
		for cle, champ in self.metadonnees.items():
			valeur: str | int | None = (conformer(champ.text())) or (None)
			if (cle in ENTIERS) and (valeur is not None):
				valeur = int(valeur)
			saisies[f"metadonnees_musicales.{cle}"] = valeur
		saisies["crossfade_debut"] = _crossfade(self.ui.a_crossfade_debut, self.ui.crossfade_debut)
		saisies["crossfade_fin"] = _crossfade(self.ui.a_crossfade_fin, self.ui.crossfade_fin)
		saisies["max_lectures"] = (self.ui.max_lectures.value()) or (None)
		saisies["masquer_metadonnees"] = MASQUAGES[self.ui.masquage.currentIndex()][0]
		saisies["debut_diffusion"] = affichage.date_cochee(self.ui.a_debut, self.ui.debut_diffusion)
		saisies["fin_diffusion"] = affichage.date_cochee(self.ui.a_fin, self.ui.fin_diffusion)
		if self.ui.groupe_blancs.isVisibleTo(self):
			saisies["detection_blancs"] = self.ui.detection_blancs.isChecked()
			saisies["debut_detecte"] = _crossfade(self.ui.a_debut_detecte, self.ui.debut_detecte)
			saisies["fin_detectee"] = _crossfade(self.ui.a_fin_detectee, self.ui.fin_detectee)
		if self.ui.groupe_stream.isVisibleTo(self):
			saisies["url_stream"] = None
			saisies["marque_page_id"] = None
			if self.ui.par_adresse.isChecked():
				saisies["url_stream"] = (self.ui.url_stream.text().strip()) or (None)
			else:
				saisies["marque_page_id"] = self.ui.marque_page.currentData()
			saisies["secours_evenement_id"] = self.ui.secours.currentData()
		saisies["etat"] = self.ui.etat.currentData()
		return saisies

	def _ecrire(self) -> int:
		saisies = self._saisies()
		debut, fin = saisies["debut_diffusion"], saisies["fin_diffusion"]
		if (isinstance(debut, datetime)) and (isinstance(fin, datetime)) and (fin <= debut):
			raise Refus("La fin de la diffusion doit suivre son début.")
		if ("url_stream" in saisies) and (saisies["url_stream"] is None) and (saisies["marque_page_id"] is None):
			raise Refus("L'adresse du stream est obligatoire.")
		# Seuls des blancs saisis sont refusés : l'indexeur ne mesure jamais des blancs qui couvrent tout le fichier.
		cotes = ("debut_detecte", "fin_detectee")
		saisis = any(saisies.get(cote) != self._initiales.get(cote) for cote in cotes)
		blancs = [blanc for blanc in (saisies.get(cote) for cote in cotes) if isinstance(blanc, timedelta)]
		if (saisis) and (self._duree is not None) and (sum(blancs, timedelta(0)) >= self._duree):
			raise Refus("Les blancs détectés doivent laisser du son : ensemble, plus courts que la durée du sonore.")
		identifiant = self.identifiant
		if identifiant is None:
			# Un nouveau stream entre en base avec son adresse ; ses autres champs s'écrivent comme une modification.
			cree = self.connexion.execute(
				"INSERT INTO sonores (type, url_stream, marque_page_id, etat) VALUES ('stream', %s, %s, 'actif')"
				" RETURNING id",
				(saisies["url_stream"], saisies["marque_page_id"]),
			).fetchone()
			assert cree is not None
			identifiant = int(str(cree[0]))
		modifies = [champ for champ, valeur in saisies.items() if valeur != self._initiales[champ]]
		ligne = self.connexion.execute(
			"SELECT champs_edites FROM sonores WHERE id = %s FOR UPDATE", (identifiant,)
		).fetchone()
		if ligne is None:
			raise Refus("Ce sonore n'est plus en base.")
		edites = list((ligne[0]) or ([]))
		edites += [champ for champ in modifies if (champ != "etat") and (champ not in edites)]
		colonnes = [champ for champ in modifies if not champ.startswith("metadonnees_musicales.")]
		affectations: list[sql.Composable] = [
			sql.SQL("{} = %s").format(sql.Identifier(colonne)) for colonne in colonnes
		]
		valeurs: list[object] = [saisies[colonne] for colonne in colonnes]
		prefixe = "metadonnees_musicales."
		musicales = {champ.removeprefix(prefixe): saisies[champ] for champ in modifies if champ.startswith(prefixe)}
		affectations.append(sql.SQL("metadonnees_musicales = (metadonnees_musicales - %s::text[]) || %s::jsonb"))
		valeurs += [list(musicales), Jsonb({cle: valeur for cle, valeur in musicales.items() if valeur is not None})]
		affectations.append(sql.SQL("champs_edites = %s"))
		valeurs.append(edites)
		requete = sql.SQL("UPDATE sonores SET {} WHERE id = %s").format(sql.SQL(", ").join(affectations))
		self.connexion.execute(requete, [*valeurs, identifiant])
		return identifiant

	def _lire_relations(self) -> list[tuple[object, ...]]:
		"""Les séquences, banques et événements dont la liste cite le sonore ; dans une transaction."""
		return self.connexion.execute(
			"SELECT genre, id, nom, minimum, maximum, (SELECT duree FROM sonores WHERE id = %s) FROM ("
			" SELECT 1 AS ordre, 'séquence' AS genre, q.id, q.nom_interne AS nom, NULL::interval AS minimum,"
			"  NULL::interval AS maximum FROM sequences q"
			"  WHERE EXISTS (SELECT 1 FROM sequences_elements x WHERE x.sequence_id = q.id AND x.sonore_id = %s)"
			" UNION ALL SELECT 2, 'banque', b.id, b.nom_interne, b.duree_min, b.duree_max FROM banques b"
			"  WHERE EXISTS (SELECT 1 FROM banques_sonores x WHERE x.banque_id = b.id AND x.sonore_id = %s)"
			" UNION ALL SELECT 3, 'événement', e.id, e.nom_interne, NULL, NULL FROM evenements e"
			"  WHERE EXISTS (SELECT 1 FROM evenements_elements x WHERE x.evenement_id = e.id AND x.sonore_id = %s)"
			") r ORDER BY ordre, nom, id",
			(self.identifiant, self.identifiant, self.identifiant, self.identifiant),
		).fetchall()

	def _montrer_relations(self, relations: list[tuple[object, ...]]) -> None:
		table = self.ui.relations
		table.setRowCount(0)
		for genre, identifiant, nom, minimum, maximum, duree in relations:
			rangee = table.rowCount()
			table.insertRow(rangee)
			# L'icône du genre (https://github.com/dascritch/machincast/issues/215).
			table.setItem(rangee, 0, QTableWidgetItem(icones.icone_de(str(genre)), str(genre)))
			cellule = QTableWidgetItem(str(nom))
			cellule.setData(RELATION, (str(genre), int(str(identifiant))))
			# Une banque dont le sonore sort des durées (https://github.com/dascritch/machincast/issues/147).
			ecart = affichage.hors_durees(
				duree_ou_rien(duree), duree_ou_rien(minimum), duree_ou_rien(maximum), str(nom)
			)
			if ecart is not None:
				cellule.setIcon(affichage.icone_d_anomalie(self))
				cellule.setToolTip(ecart)
			table.setItem(rangee, 1, cellule)
		self.ui.aucune_relation.setVisible(relations == [])

	def _ouvrir_relation(self, cellule: QTableWidgetItem) -> None:
		nom = self.ui.relations.item(cellule.row(), 1)
		assert nom is not None
		genre, identifiant = nom.data(RELATION)
		self.ouverture_demandee.emit(genre, identifiant, nom.text())

	def _montrer_fichier(self, chemin: Path, type_mime: object, duree: object, verifie_le: object) -> None:
		"""Ce que la base sait du fichier, et ce que le fichier dit de lui-même, sans être modifié."""
		ui = self.ui
		ui.type_mime.setText(str((type_mime) or ("inconnu")))
		ui.verifie_le.setText("jamais")
		if isinstance(verifie_le, datetime):
			ui.verifie_le.setText(affichage.date(verifie_le))
		ui.encodage.setText("inconnu")
		try:
			etat = chemin.stat()
		except OSError:
			for champ in (ui.taille, ui.cree_le, ui.modifie_le):
				champ.setText("introuvable")
			return
		ui.taille.setText(affichage.taille(etat.st_size))
		ui.modifie_le.setText(affichage.date(datetime.fromtimestamp(etat.st_mtime).astimezone()))
		ui.cree_le.setText("inconnue")
		naissance = _naissance(chemin)
		if naissance is not None:
			ui.cree_le.setText(affichage.date(naissance))
		# La base refuse une durée nulle.
		if isinstance(duree, timedelta):
			ui.encodage.setText(f"≈ {round(etat.st_size * 8 / duree.total_seconds() / 1000)} kbit/s")

	def _lire_passages(self) -> list[tuple[object, ...]]:
		"""Les derniers passages, avec les alertes et incidents du log pendant chacun ; dans une transaction."""
		return self.connexion.execute(
			"SELECT d.horodatage, f.horodatage, f.duree_diffusee, e.nom_interne, q.nom_interne,"
			" b.nom_interne, i.horodatages, i.natures, i.messages"
			" FROM airplay d"
			" LEFT JOIN airplay f ON f.passage_id = d.passage_id AND f.type_ligne = 'fin'"
			" LEFT JOIN evenements e ON e.id = d.evenement_id"
			" LEFT JOIN sequences q ON q.id = d.sequence_id"
			" LEFT JOIN banques b ON b.id = d.banque_id"
			" LEFT JOIN LATERAL ("
			"  SELECT array_agg(l.horodatage ORDER BY l.horodatage, l.id) AS horodatages,"
			"   array_agg(l.nature::text ORDER BY l.horodatage, l.id) AS natures,"
			"   array_agg(l.message ORDER BY l.horodatage, l.id) AS messages"
			"  FROM log l WHERE l.sonore_id = d.sonore_id AND l.niveau <> 'info' AND l.horodatage >= d.horodatage"
			"   AND (f.horodatage IS NULL OR l.horodatage <= f.horodatage)"
			" ) i ON true"
			" WHERE d.type_ligne = 'debut' AND d.sonore_id = %s"
			" ORDER BY d.horodatage DESC, d.id DESC LIMIT %s",
			(self.identifiant, PASSAGES),
		).fetchall()

	def _montrer_passages(self, passages: list[tuple[object, ...]]) -> None:
		table = self.ui.passages
		table.setRowCount(0)
		for debut, fin, duree, evenement, sequence, banque, horodatages, natures, messages in passages:
			assert isinstance(debut, datetime)
			texte_fin, texte_duree = "en cours", ""
			if isinstance(fin, datetime):
				texte_fin = affichage.heure(fin)
			if isinstance(duree, timedelta):
				texte_duree = affichage.duree(duree)
			incidents = list(zip(_liste(horodatages), _liste(natures), _liste(messages), strict=True))
			cellules = [f"{debut.astimezone():%Y-%m-%d %H:%M:%S}", texte_fin, texte_duree]
			cellules += [str((nom) or ("")) for nom in (evenement, sequence, banque)]
			cellules.append(", ".join(str(nature) for _h, nature, _m in incidents))
			items = [QTableWidgetItem(texte) for texte in cellules]
			details = [f"{_heure(h)} {nature} : {message}" for h, nature, message in incidents]
			items[-1].setToolTip("\n".join(details))
			rangee = table.rowCount()
			table.insertRow(rangee)
			for colonne, item in enumerate(items):
				table.setItem(rangee, colonne, item)

	def _adresse(self) -> str:
		if self.ui.par_adresse.isChecked():
			return self.ui.url_stream.text().strip()
		return str(self.ui.marque_page.currentData(URL))

	def _tester(self) -> None:
		self.ui.tester.setEnabled(False)
		self.ui.resultat_essai.setText("Test du flux en cours…")
		self.essai.lancer(self._adresse())

	def _essai_termine(self, repond: bool, detail: str) -> None:
		self.ui.resultat_essai.setText(resultat_de_l_essai(repond, detail))
		self.ui.tester.setEnabled(True)


def _crossfade(case: QCheckBox, nombre: QDoubleSpinBox) -> timedelta | None:
	"""Le crossfade, ou le blanc détecté, saisi ; None s'il n'est pas paramétré, ou pas détecté."""
	if not case.isChecked():
		return None
	return timedelta(seconds=nombre.value())


def _secondes(valeur: object) -> float:
	if isinstance(valeur, timedelta):
		return valeur.total_seconds()
	return 0.0


def _liste(valeur: object) -> list[object]:
	"""Un tableau lu en base, vide pour NULL."""
	if isinstance(valeur, list):
		return valeur
	return []


def _heure(valeur: object) -> str:
	if isinstance(valeur, datetime):
		return affichage.heure(valeur)
	return str(valeur)


def _naissance(chemin: Path) -> datetime | None:
	"""La date de création du fichier, que stat lit dans le système de fichiers ; None si le système n'en garde pas.

	Python ne la donne pas sous Linux : stat (coreutils) la demande à statx.
	"""
	try:
		sortie = subprocess.run(
			["stat", "--format=%W", str(chemin)], capture_output=True, text=True, check=True, timeout=DELAI_DE_STAT
		).stdout
		secondes = int((sortie.strip()) or ("0"))
	# Un partage réseau qui ne répond plus, ou une réponse inattendue, laisse la date inconnue, sans figer ni faire
	# planter la fiche (https://github.com/dascritch/machincast/issues/187).
	except (OSError, subprocess.SubprocessError, ValueError):
		return None
	if secondes <= 0:
		return None
	return datetime.fromtimestamp(secondes).astimezone()
