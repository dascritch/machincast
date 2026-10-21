"""Écran par défaut de Machin_interface (https://github.com/dascritch/machincast/issues/23, spec § 8.1).

En un coup d'œil : l'heure, le texte public du sonore en cours entre guillemets, l'état du binaire lecture, l'événement
à l'antenne et ses heures, le sonore en cours et le temps qui lui reste, le prochain sonore, chacun avec son événement,
sa séquence, sa banque et son horaire sur une ligne, et l'airplay des 12 dernières heures
(https://github.com/dascritch/machincast/issues/144). Les boutons de chaque sonore, et un double-clic dans l'airplay,
demandent la fiche du sonore, de l'événement, de la séquence ou de la banque (ouverte). Le sonore en cours et le
prochain viennent de la socket d'état du binaire lecture (ClientEtat). L'airplay se lit en base à l'ouverture, puis à
chaque changement de sonore annoncé par la socket : jamais en boucle. La disposition est dessinée dans
ui/ecran_par_defaut.ui (CONTRIBUTION.md).
"""

import logging
import math
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QModelIndex, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from machincast.configuration import Audio
from machincast.horloge import Horloge
from machincast.interface import affichage
from machincast.interface.airplay import FENETRE, PassageAffiche, lire_airplay
from machincast.interface.calendrier import date_longue
from machincast.interface.colonnes import Colonnes
from machincast.interface.etat import ClientEtat, EtatLecture, SonoreAffiche
from machincast.interface.moniteur import Moniteur, nom_du_port
from machincast.interface.ui.ecran_par_defaut import Ui_EcranParDefaut
from machincast.interface.vumetre import VuMetre

journal = logging.getLogger(__name__)

SECONDE = 1000
"""Rafraîchissement de l'heure, en millisecondes."""
ETATS = {"diffusion": "En diffusion", "silence": "En silence", "arret": "À l'arrêt"}
ELEMENT = Qt.ItemDataRole.UserRole
"""Rôle qui porte, sur une cellule de l'airplay, le genre et l'identifiant de l'élément qu'elle désigne."""
VOYANT_ALLUME = (
	"QLabel {{ background: {teinte}; color: white; border-radius: 3px; font-weight: bold; font-size: 7pt; }}"
)
VOYANT_ETEINT = "QLabel { color: palette(mid); font-size: 7pt; }"
"""Les voyants « Silence » et « Saturation » de l'antenne, allumés de leur teinte, ou éteints, grisés."""


class EcranParDefaut(QWidget):
	ecoute_demandee = Signal()
	"""Clic sur le VU-mètre de l'antenne, disponible : l'écouter en pré-écoute
	(https://github.com/dascritch/machincast/issues/24)."""
	ouverte = Signal(str, int, str)
	"""Fiche demandée : genre, identifiant et nom de l'élément."""
	COLONNES_AIRPLAY = (
		("debut", "Début"),
		("fin", "Fin"),
		("duree", "Durée"),
		("artiste", "Artiste"),
		("titre", "Titre"),
		("evenement", "Événement"),
		("sequence", "Séquence"),
		("banque", "Banque"),
		("incident", "Incident"),
	)

	def __init__(
		self,
		connexion: psycopg.Connection[TupleRow],
		socket_etat: Path,
		horloge: Horloge,
		parent: QWidget | None = None,
		audio: Audio | None = None,
	) -> None:
		"""audio : la sortie et le périphérique de l'antenne, dont le VU-mètre lit le port de monitoring
		(https://github.com/dascritch/machincast/issues/24) ; sans elle, il est indisponible."""
		super().__init__(parent)
		self.connexion = connexion
		self.horloge = horloge
		self.ui = Ui_EcranParDefaut()
		self.ui.setupUi(self)
		self.modele_airplay = QStandardItemModel(0, len(self.COLONNES_AIRPLAY), self)
		self.modele_airplay.setHorizontalHeaderLabels([titre for _, titre in self.COLONNES_AIRPLAY])
		self.ui.table_airplay.setModel(self.modele_airplay)
		self.colonnes_airplay = Colonnes(self.ui.table_airplay, "accueil-airplay")
		self.ui.table_airplay.activated.connect(self._ouvrir_cellule)
		self._en_cours: SonoreAffiche | None = None
		self._prochain: SonoreAffiche | None = None
		ui = self.ui
		ui.ouvrir_sonore_en_cours.clicked.connect(lambda: self._ouvrir_sonore(self._en_cours))
		ui.ouvrir_sonore_prochain.clicked.connect(lambda: self._ouvrir_sonore(self._prochain))
		ui.ouvrir_evenement_en_cours.clicked.connect(lambda: self._ouvrir_evenement(self._en_cours))
		ui.ouvrir_evenement_prochain.clicked.connect(lambda: self._ouvrir_evenement(self._prochain))
		ui.ouvrir_sequence_en_cours.clicked.connect(lambda: self._ouvrir_sequence(self._en_cours))
		ui.ouvrir_sequence_prochain.clicked.connect(lambda: self._ouvrir_sequence(self._prochain))
		ui.ouvrir_banque_en_cours.clicked.connect(lambda: self._ouvrir_banque(self._en_cours))
		ui.ouvrir_banque_prochain.clicked.connect(lambda: self._ouvrir_banque(self._prochain))
		self._passage_connu: datetime | None = None
		"""Début du sonore en cours que l'airplay affiché connaît : il n'est relu que si un autre est annoncé."""
		self._afficher_heure()
		self._horloge = QTimer(self)
		self._horloge.setInterval(SECONDE)
		self._horloge.timeout.connect(self._afficher_heure)
		self._horloge.start()
		self.afficher(EtatLecture("arret"), relire=False)
		passages = self.actualiser_airplay()
		if (len(passages) > 0) and (passages[0].fin is None):
			self._passage_connu = passages[0].debut
		self.client = ClientEtat(socket_etat, self)
		self.client.etat_recu.connect(self.afficher)
		self.client.connecter()
		self.vumetre = VuMetre(ui.place_vumetre, vertical=True)
		disposition = QVBoxLayout(ui.place_vumetre)
		disposition.setContentsMargins(0, 0, 0, 0)
		disposition.addWidget(self.vumetre)
		self.vumetre.clique.connect(self._ecouter)
		self.moniteur = Moniteur(audio, self)
		self.moniteur.change.connect(self._montrer_l_antenne)
		self.changer_d_antenne(audio)

	def changer_d_antenne(self, audio: Audio | None) -> None:
		"""Le VU-mètre lit le port de monitoring de cette antenne, par exemple après les préférences."""
		self.moniteur.audio = audio
		infobulle = "Port de monitoring inconnu."
		if audio is not None:
			infobulle = f"Port de monitoring : {nom_du_port(audio)}. Clic : écouter l'antenne en pré-écoute."
		self.vumetre.setToolTip(infobulle)
		self.moniteur.demarrer()

	def montrer_la_saturation(self, affiche: bool) -> None:
		"""Le voyant « Saturation » de la colonne Antenne, affiché ou caché selon les préférences
		(https://github.com/dascritch/machincast/issues/191) ; le VU-mètre montre toujours les crêtes."""
		self.ui.voyant_saturation.setVisible(affiche)

	def _ecouter(self) -> None:
		if self.moniteur.indisponible is None:
			self.ecoute_demandee.emit()

	def _montrer_l_antenne(self) -> None:
		ui, moniteur = self.ui, self.moniteur
		self.vumetre.montrer(moniteur.niveaux, moniteur.cretes)
		ui.etat_moniteur.setText((moniteur.indisponible) or (""))
		ui.etat_moniteur.setVisible(moniteur.indisponible is not None)
		for voyant, allume, teinte in (
			(ui.voyant_silence, moniteur.silence, "#e0a020"),
			(ui.voyant_saturation, moniteur.saturation, "#d03030"),
		):
			if voyant.property("allume") != allume:
				voyant.setProperty("allume", allume)
				style = VOYANT_ETEINT
				if allume:
					style = VOYANT_ALLUME.format(teinte=teinte)
				voyant.setStyleSheet(style)

	def closeEvent(self, evenement: QCloseEvent) -> None:
		self._horloge.stop()
		self.client.fermer()
		self.moniteur.arreter()
		super().closeEvent(evenement)

	def _afficher_heure(self) -> None:
		"""L'heure seule, à la seconde ; la date du jour en infobulle (demandé avec
		https://github.com/dascritch/machincast/issues/191)."""
		maintenant = self.horloge.maintenant()
		self.ui.heure.setText(affichage.heure(maintenant))
		self.ui.heure.setToolTip(date_longue(maintenant.astimezone().date()))

	# ─── État du binaire lecture ───────────────────────────

	def afficher(self, etat: EtatLecture, relire: bool = True) -> None:
		self.ui.etat_lecture.setText(ETATS.get(etat.etat, etat.etat))
		self._en_cours, self._prochain = etat.en_cours, etat.prochain
		self._afficher_sonore("en_cours", etat.en_cours)
		self._afficher_sonore("prochain", etat.prochain)
		self._afficher_progression(etat.en_cours)
		self._afficher_antenne(etat.en_cours)
		prochain = etat.prochain
		self.ui.prochain_sain.setText(affichage.VIDE)
		if prochain is not None:
			self.ui.prochain_sain.setText(affichage.oui_non(prochain.sain, "non testé"))
		debut = None
		if etat.en_cours is not None:
			debut = etat.en_cours.debut
		if (relire) and (debut != self._passage_connu):
			self._passage_connu = debut
			self.actualiser_airplay()

	def _afficher_sonore(self, lequel: str, sonore: SonoreAffiche | None) -> None:
		"""Titre, événement, séquence, banque, horaire sur une ligne et emplacement d'un des deux sonores."""
		ui = self.ui
		champs = [getattr(ui, f"{lequel}_{nom}") for nom in ("titre", "evenement", "sequence", "banque", "horaire")]
		titre, evenement, sequence, banque, horaire = champs
		_afficher_emplacement(getattr(ui, f"{lequel}_emplacement"), sonore)
		getattr(ui, f"ouvrir_sonore_{lequel}").setEnabled(sonore is not None)
		getattr(ui, f"ouvrir_evenement_{lequel}").setEnabled((sonore is not None) and (sonore.evenement_id is not None))
		getattr(ui, f"ouvrir_sequence_{lequel}").setEnabled((sonore is not None) and (sonore.sequence_id is not None))
		getattr(ui, f"ouvrir_banque_{lequel}").setEnabled((sonore is not None) and (sonore.banque_id is not None))
		if sonore is None:
			for champ in champs:
				champ.setText(affichage.VIDE)
			return
		titre.setText(affichage.artiste_et_titre(sonore.artiste, sonore.titre))
		evenement.setText((sonore.evenement) or (affichage.VIDE))
		sequence.setText((sonore.sequence) or (affichage.VIDE))
		banque.setText((sonore.banque) or (affichage.VIDE))
		horaire.setText(_horaire(sonore))

	def _afficher_progression(self, sonore: SonoreAffiche | None) -> None:
		"""Le temps qui reste au sonore en cours, plutôt qu'un pourcentage."""
		barre = self.ui.en_cours_progression
		barre.setValue(0)
		if sonore is None:
			barre.setFormat(affichage.VIDE)
			return
		longueur = _longueur(sonore)
		if (longueur is None) or (sonore.position is None):
			barre.setFormat("durée inconnue")
			return
		# Une barre hors de ses bornes garde son ancienne valeur : un sonore qui dépasse sa durée la remplit.
		barre.setValue(100)
		if longueur > 0:
			barre.setValue(min(100, round(sonore.position / longueur * 100)))
		# Le temps qui reste se compte à la seconde entamée : « reste 0:01 » jusqu'à la fin, puis « reste 0:00 ».
		reste = math.ceil(max(0.0, longueur - sonore.position))
		# Texte composé ici : les codes de format de Qt s'écrivent avec la notation %, que refuse socle.feature.
		texte = f"reste {affichage.duree(reste)}"
		if sonore.coupe_par is not None:
			texte = f"{texte} avant « {sonore.coupe_par} »"
		barre.setFormat(texte)

	def _afficher_antenne(self, sonore: SonoreAffiche | None) -> None:
		"""Le texte public entre guillemets, et l'événement à l'antenne avec ses heures."""
		ui = self.ui
		ui.texte_public.setText(affichage.VIDE)
		ui.evenement_antenne.setText(affichage.VIDE)
		if sonore is None:
			return
		if sonore.texte_public:
			ui.texte_public.setText(f"« {sonore.texte_public} »")
		if sonore.evenement is not None:
			ui.evenement_antenne.setText(f"{sonore.evenement}, {_heures_de_l_evenement(sonore)}")

	def _ouvrir_sonore(self, sonore: SonoreAffiche | None) -> None:
		if sonore is not None:
			self.ouverte.emit("sonore", sonore.sonore, affichage.artiste_et_titre(sonore.artiste, sonore.titre))

	def _ouvrir_evenement(self, sonore: SonoreAffiche | None) -> None:
		if (sonore is not None) and (sonore.evenement_id is not None):
			self.ouverte.emit("événement", sonore.evenement_id, str(sonore.evenement))

	def _ouvrir_sequence(self, sonore: SonoreAffiche | None) -> None:
		if (sonore is not None) and (sonore.sequence_id is not None):
			self.ouverte.emit("séquence", sonore.sequence_id, str(sonore.sequence))

	def _ouvrir_banque(self, sonore: SonoreAffiche | None) -> None:
		if (sonore is not None) and (sonore.banque_id is not None):
			self.ouverte.emit("banque", sonore.banque_id, str(sonore.banque))

	def _ouvrir_cellule(self, index: QModelIndex) -> None:
		"""Un double-clic sur une cellule qui désigne un élément demande sa fiche ; ailleurs, il ne fait rien."""
		element = index.data(ELEMENT)
		if element is not None:
			genre, identifiant, nom = element
			self.ouverte.emit(genre, identifiant, nom)

	# ─── Airplay ───────────────────────────────────────────

	def actualiser_airplay(self) -> list[PassageAffiche]:
		"""Relit l'airplay des 12 dernières heures ; une base injoignable laisse la table telle qu'elle était."""
		try:
			passages = lire_airplay(self.connexion, self.horloge.maintenant() - FENETRE)
		except psycopg.Error as erreur:
			journal.error(f"airplay illisible : {erreur}")
			return []
		self.modele_airplay.setRowCount(0)
		for passage in passages:
			cellules = [QStandardItem(texte) for texte in _cellules(passage)]
			for colonne, element in _elements(passage).items():
				cellules[colonne].setData(element, ELEMENT)
			self.modele_airplay.appendRow(cellules)
		return passages


def _afficher_emplacement(champ: QLineEdit, sonore: SonoreAffiche | None) -> None:
	"""Chemin du fichier ou adresse du stream, dans un champ en lecture seule : un long chemin ne pousse pas la mise
	en page, sa fin (le nom du fichier) reste visible, et l'infobulle le donne en entier."""
	emplacement = None
	if sonore is not None:
		emplacement = (sonore.emplacement) or ("inconnu")
	champ.setText((emplacement) or (affichage.VIDE))
	champ.setToolTip((emplacement) or (""))


def _cellules(passage: PassageAffiche) -> list[str]:
	fin = "en cours"
	duree = ""
	if passage.fin is not None:
		fin = affichage.heure(passage.fin)
		duree = affichage.duree(passage.duree)
	return [
		affichage.heure(passage.debut),
		fin,
		duree,
		(passage.artiste) or (""),
		(passage.titre) or (""),
		(passage.evenement) or (""),
		(passage.sequence) or (""),
		(passage.banque) or (""),
		"oui" if passage.sans_incident is False else "",
	]


def _elements(passage: PassageAffiche) -> dict[int, tuple[str, int, str]]:
	"""Les cellules qui désignent un élément, par colonne : artiste et titre le sonore, puis événement, séquence et
	banque ; un élément supprimé depuis n'en désigne plus."""
	elements: dict[int, tuple[str, int, str]] = {}
	if passage.sonore_id is not None:
		titre = (passage.titre) or (affichage.artiste_et_titre(passage.artiste, passage.titre))
		elements[3] = elements[4] = ("sonore", passage.sonore_id, titre)
	for colonne, genre, identifiant, nom in (
		(5, "événement", passage.evenement_id, passage.evenement),
		(6, "séquence", passage.sequence_id, passage.sequence),
		(7, "banque", passage.banque_id, passage.banque),
	):
		if identifiant is not None:
			elements[colonne] = (genre, identifiant, str(nom))
	return elements


def _horaire(sonore: SonoreAffiche) -> str:
	"""« 20:00:00 – 20:03:34 (3:34) » : début, fin et durée sur une ligne ; « 20:00:00, durée inconnue » sans durée.
	Un sonore qu'un événement coupera finit à la coupure : « 20:00:00 – 20:02:00 (coupé par « Journal », sur 3:34) »
	(https://github.com/dascritch/machincast/issues/169)."""
	debut = affichage.heure(sonore.debut, "inconnu")
	if sonore.coupe_par is not None:
		duree = "durée inconnue"
		if sonore.duree is not None:
			duree = f"sur {affichage.duree(sonore.duree)}"
		return f"{debut} – {affichage.heure(sonore.fin_estimee)} (coupé par « {sonore.coupe_par} », {duree})"
	if sonore.duree is None:
		return f"{debut}, durée inconnue"
	return f"{debut} – {affichage.heure(sonore.fin_estimee)} ({affichage.duree(sonore.duree)})"


def _longueur(sonore: SonoreAffiche) -> float | None:
	"""Combien de secondes le sonore passera, de son début à sa fin estimée : sa durée, ou jusqu'à la coupure annoncée ;
	None sans fin estimée, pour un stream que rien ne coupera."""
	if (sonore.debut is None) or (sonore.fin_estimee is None):
		return None
	return (sonore.fin_estimee - sonore.debut).total_seconds()


def _heures_de_l_evenement(sonore: SonoreAffiche) -> str:
	"""« de 20:00 à 22:00 », « depuis 19:00 » pour une occurrence sans fin, « permanent » pour un fil musical."""
	debut, fin = sonore.evenement_debut, sonore.evenement_fin
	if debut is None:
		return "permanent"
	if fin is None:
		return f"depuis {debut:%H:%M}"
	return f"de {debut:%H:%M} à {fin:%H:%M}"
