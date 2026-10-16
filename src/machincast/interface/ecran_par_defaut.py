"""Écran par défaut de Machin_interface (https://github.com/dascritch/machincast/issues/23, spec § 8.1).

En un coup d'œil : l'heure, l'état du binaire lecture, le sonore en cours et sa progression, le prochain sonore, et
l'airplay des 12 dernières heures. Le sonore en cours et le prochain viennent de la socket d'état du binaire lecture
(ClientEtat). L'airplay se lit en base à l'ouverture, puis à chaque changement de sonore annoncé par la socket : jamais
en boucle. La disposition est dessinée dans ui/ecran_par_defaut.ui (CONTRIBUTION.md).
"""

import logging
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QHeaderView, QLineEdit, QWidget

from machincast.horloge import Horloge
from machincast.interface import affichage
from machincast.interface.airplay import FENETRE, PassageAffiche, lire_airplay
from machincast.interface.etat import ClientEtat, EtatLecture, SonoreAffiche
from machincast.interface.ui.ecran_par_defaut import Ui_EcranParDefaut

journal = logging.getLogger(__name__)

SECONDE = 1000
"""Rafraîchissement de l'heure, en millisecondes."""
ETATS = {"diffusion": "En diffusion", "silence": "En silence", "arret": "À l'arrêt"}


class EcranParDefaut(QWidget):
	COLONNES_AIRPLAY = (
		("debut", "Début"),
		("fin", "Fin"),
		("duree", "Durée"),
		("artiste", "Artiste"),
		("titre", "Titre"),
		("evenement", "Événement"),
		("sequence", "Séquence"),
		("banque", "Banque"),
		("sans_incident", "Sans incident"),
	)

	def __init__(
		self,
		connexion: psycopg.Connection[TupleRow],
		socket_etat: Path,
		horloge: Horloge,
		parent: QWidget | None = None,
	) -> None:
		super().__init__(parent)
		self.connexion = connexion
		self.horloge = horloge
		self.ui = Ui_EcranParDefaut()
		self.ui.setupUi(self)
		self.modele_airplay = QStandardItemModel(0, len(self.COLONNES_AIRPLAY), self)
		self.modele_airplay.setHorizontalHeaderLabels([titre for _, titre in self.COLONNES_AIRPLAY])
		self.ui.table_airplay.setModel(self.modele_airplay)
		self.ui.table_airplay.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
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

	def closeEvent(self, evenement: QCloseEvent) -> None:
		self._horloge.stop()
		self.client.fermer()
		super().closeEvent(evenement)

	def _afficher_heure(self) -> None:
		self.ui.heure.setText(affichage.date_et_heure(self.horloge.maintenant()))

	# ─── État du binaire lecture ───────────────────────────

	def afficher(self, etat: EtatLecture, relire: bool = True) -> None:
		self.ui.etat_lecture.setText(ETATS.get(etat.etat, etat.etat))
		self._afficher_en_cours(etat.en_cours)
		self._afficher_prochain(etat.prochain)
		debut = None
		if etat.en_cours is not None:
			debut = etat.en_cours.debut
		if (relire) and (debut != self._passage_connu):
			self._passage_connu = debut
			self.actualiser_airplay()

	def _afficher_en_cours(self, sonore: SonoreAffiche | None) -> None:
		ui = self.ui
		barre = ui.en_cours_progression
		champs = (ui.en_cours_titre, ui.en_cours_evenement, ui.en_cours_debut, ui.en_cours_duree, ui.en_cours_fin)
		_afficher_emplacement(ui.en_cours_emplacement, sonore)
		if sonore is None:
			for champ in champs:
				champ.setText(affichage.VIDE)
			barre.setValue(0)
			barre.setFormat(affichage.VIDE)
			return
		ui.en_cours_titre.setText(affichage.artiste_et_titre(sonore.artiste, sonore.titre))
		ui.en_cours_evenement.setText(sonore.evenement or affichage.VIDE)
		ui.en_cours_debut.setText(affichage.heure(sonore.debut, "inconnu"))
		ui.en_cours_duree.setText(affichage.duree(sonore.duree))
		ui.en_cours_fin.setText(affichage.heure(sonore.fin_estimee))
		if sonore.progression is None:
			barre.setValue(0)
			barre.setFormat("durée inconnue")
		else:
			pourcentage = round(sonore.progression * 100)
			barre.setValue(pourcentage)
			# Texte composé ici : les codes de format de Qt s'écrivent avec la notation %, que refuse socle.feature.
			barre.setFormat(f"{pourcentage} %")

	def _afficher_prochain(self, sonore: SonoreAffiche | None) -> None:
		ui = self.ui
		champs = (ui.prochain_titre, ui.prochain_evenement, ui.prochain_debut, ui.prochain_fin, ui.prochain_duree)
		_afficher_emplacement(ui.prochain_emplacement, sonore)
		if sonore is None:
			for champ in (*champs, ui.prochain_sain):
				champ.setText(affichage.VIDE)
			return
		ui.prochain_titre.setText(affichage.artiste_et_titre(sonore.artiste, sonore.titre))
		ui.prochain_evenement.setText(sonore.evenement or affichage.VIDE)
		ui.prochain_debut.setText(affichage.heure(sonore.debut, "inconnu"))
		ui.prochain_fin.setText(affichage.heure(sonore.fin_estimee))
		ui.prochain_duree.setText(affichage.duree(sonore.duree))
		ui.prochain_sain.setText(affichage.oui_non(sonore.sain, "non testé"))

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
			self.modele_airplay.appendRow([QStandardItem(texte) for texte in _cellules(passage)])
		return passages


def _afficher_emplacement(champ: QLineEdit, sonore: SonoreAffiche | None) -> None:
	"""Chemin du fichier ou adresse du stream, dans un champ en lecture seule : un long chemin ne pousse pas la mise
	en page, sa fin (le nom du fichier) reste visible, et l'infobulle le donne en entier."""
	emplacement = None
	if sonore is not None:
		emplacement = sonore.emplacement or "inconnu"
	champ.setText(emplacement or affichage.VIDE)
	champ.setToolTip(emplacement or "")


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
		passage.artiste or "",
		passage.titre or "",
		passage.evenement or "",
		passage.sequence or "",
		passage.banque or "",
		affichage.oui_non(passage.sans_incident),
	]
