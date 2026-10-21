"""Recherche globale (https://github.com/dascritch/machincast/issues/27,
https://github.com/dascritch/machincast/issues/105, spec § 8.2).

L'onglet « Recherche » (EcranRecherche), qui se ferme, s'ouvre par « Affichage → Rechercher… » ou Ctrl+F
(machincast.interface.fenetre). Dès MINIMUM caractères, le texte tapé est cherché, sans tenir compte des majuscules ni
des accents, dans le nom interne et le nom public des événements, des séquences et des banques, et dans l'artiste et
le titre des sonores (chercher). Les résultats vont dans l'ordre : événements, séquences, banques, sonores, chacun par
nom. La table les donne au fil de la frappe, jusqu'à LIMITE, avec le compte ; le champ ne propose pas de suggestions.
Ouvrir une ligne de la table (double-clic, Entrée) demande la fiche de l'élément (signal ouverte), sans toucher au texte
cherché. La recherche se relance à l'ouverture de l'onglet et au
rafraîchissement des onglets : jamais en boucle.

Les accents sont retirés des deux côtés : en base par translate(), pour les lettres de ACCENTUEES ; dans le texte tapé
par listes.sans_accents. Les caractères % et _ de LIKE sont cherchés tels quels.
"""

import logging
from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QModelIndex, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
	QAbstractItemView,
	QLabel,
	QLineEdit,
	QTableView,
	QVBoxLayout,
	QWidget,
)

from machincast.interface.colonnes import Colonnes
from machincast.interface.listes import ETATS, sans_accents

journal = logging.getLogger(__name__)

Connexion = psycopg.Connection[TupleRow]
MINIMUM = 2
"""Caractères à taper avant de chercher."""
LIMITE = 500
"""Lignes de la table des résultats, au plus."""
COLONNES = ("Type", "Nom interne", "Nom public", "Statut")
TYPES = {"événement": "Événement", "séquence": "Séquence", "banque": "Banque", "sonore": "Sonore"}
ACCENTUEES = "àâäáãåçéèêëíìîïñóòôöõúùûüýÿÀÂÄÁÃÅÇÉÈÊËÍÌÎÏÑÓÒÔÖÕÚÙÛÜÝ"
SANS_ACCENT = "aaaaaaceeeeiiiinooooouuuuyyaaaaaaceeeeiiiinooooouuuuy"
"""Les lettres accentuées, minuscules et majuscules, que la base ramène à leur lettre de base, dans le même ordre :
avant lower(), qui ne sait pas toujours abaisser une majuscule accentuée, selon la locale de la base."""
TROP_COURT = f"Tapez au moins {MINIMUM} caractères."


@dataclass(frozen=True)
class Resultat:
	genre: str
	"""« événement », « séquence », « banque » ou « sonore », comme les fiches."""
	identifiant: int
	nom: str
	"""Le nom interne ; pour un sonore, son artiste et son titre."""
	nom_public: str
	statut: str
	"""L'état d'un sonore ; rien pour les autres."""


def _normalise(colonne: str) -> str:
	return f"lower(translate(COALESCE({colonne}, ''), '{ACCENTUEES}', '{SANS_ACCENT}'))"


def _motif(texte: str) -> str:
	"""Le texte, sans accents ni majuscules, entre deux % de LIKE ; ses \\, % et _ sont cherchés tels quels."""
	echappe = sans_accents(texte).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	return f"%{echappe}%"


def _trouve(*colonnes: str) -> str:
	return " OR ".join(f"{_normalise(colonne)} LIKE recherche.motif" for colonne in colonnes)


TROUVES = f"""
	WITH recherche AS (SELECT %s::text AS motif)
	SELECT 1 AS rang, 'événement' AS genre, id, nom_interne AS nom, nom_public, NULL AS etat FROM evenements, recherche
		WHERE {_trouve("nom_interne", "nom_public")}
	UNION ALL
	SELECT 2, 'séquence', id, nom_interne, nom_public, NULL FROM sequences, recherche
		WHERE {_trouve("nom_interne", "nom_public")}
	UNION ALL
	SELECT 3, 'banque', id, nom_interne, nom_public, NULL FROM banques, recherche
		WHERE {_trouve("nom_interne", "nom_public")}
	UNION ALL
	SELECT 4, 'sonore', id, concat_ws(' – ', artiste, titre), NULL, etat::text FROM sonores, recherche
		WHERE {_trouve("artiste", "titre")}
"""
"""Les éléments où se trouve le motif, lié une seule fois (recherche.motif), avec le rang de leur type."""


def _statut(etat: object) -> str:
	"""L'état d'un sonore, en clair ; rien pour un autre élément."""
	if etat is None:
		return ""
	return ETATS.get(str(etat), str(etat))


def chercher(connexion: Connexion, texte: str, limite: int) -> tuple[list[Resultat], int]:
	"""Les premiers résultats, jusqu'à la limite, et leur nombre total ; rien en dessous de MINIMUM caractères."""
	if len(texte.strip()) < MINIMUM:
		return [], 0
	motif = _motif(texte.strip())
	with connexion.transaction():
		lignes = connexion.execute(
			f"SELECT genre, id, nom, nom_public, etat FROM ({TROUVES}) t ORDER BY rang, lower(nom), id"  # noqa: S608
			" LIMIT %s",
			(motif, limite),
		).fetchall()
		ligne = connexion.execute(f"SELECT count(*) FROM ({TROUVES}) t", (motif,)).fetchone()  # noqa: S608
	assert ligne is not None
	resultats = [
		Resultat(
			str(genre),
			int(str(identifiant)),
			str(nom),
			str((nom_public) or ("")),
			_statut(etat),
		)
		for genre, identifiant, nom, nom_public, etat in lignes
	]
	return resultats, int(str(ligne[0]))


class EcranRecherche(QWidget):
	ouverte = Signal(str, int, str)
	"""Ligne ouverte : genre, identifiant et nom de l'élément."""

	def __init__(self, connexion: Connexion, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.connexion = connexion
		self.resultats: list[Resultat] = []
		disposition = QVBoxLayout(self)
		self.champ = QLineEdit(self)
		self.champ.setPlaceholderText("Rechercher un événement, une séquence, une banque ou un sonore…")
		self.champ.setClearButtonEnabled(True)
		self.champ.setToolTip(
			"Nom interne et nom public des événements, des séquences et des banques ; artiste et titre des sonores"
		)
		disposition.addWidget(self.champ)
		self.compte = QLabel(TROP_COURT, self)
		disposition.addWidget(self.compte)
		self.modele = QStandardItemModel(0, len(COLONNES), self)
		self.modele.setHorizontalHeaderLabels(list(COLONNES))
		self.table = QTableView(self)
		self.table.setModel(self.modele)
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.verticalHeader().hide()
		self.table.horizontalHeader().setStretchLastSection(True)
		self.colonnes = Colonnes(self.table, "recherche")
		disposition.addWidget(self.table)
		self.champ.textChanged.connect(self._chercher)
		self.table.activated.connect(self._ligne_ouverte)

	def focaliser(self) -> None:
		"""Le curseur dans le champ, son texte sélectionné : une nouvelle frappe le remplace."""
		self.champ.setFocus()
		self.champ.selectAll()

	def actualiser(self) -> None:
		"""Relance la recherche du texte tapé."""
		self._chercher(self.champ.text())

	def _chercher(self, texte: str) -> None:
		try:
			self.resultats, total = chercher(self.connexion, texte, LIMITE)
		except psycopg.Error as erreur:
			journal.error(f"recherche impossible : {erreur}")
			self.compte.setText(f"Recherche impossible : {erreur}")
			return
		self._montrer(total, len(texte.strip()) >= MINIMUM)

	def _montrer(self, total: int, cherche: bool) -> None:
		self.modele.setRowCount(0)
		for resultat in self.resultats:
			cellules = [QStandardItem(texte) for texte in (TYPES[resultat.genre], resultat.nom, resultat.nom_public)]
			cellules.append(QStandardItem(resultat.statut))
			self.modele.appendRow(cellules)
		texte = TROP_COURT
		if (cherche) and (total == 0):
			texte = "aucun résultat"
		elif total == 1:
			texte = "1 résultat"
		elif total > len(self.resultats):
			texte = f"{len(self.resultats)} premiers résultats sur {total}"
		elif cherche:
			texte = f"{total} résultats"
		self.compte.setText(texte)

	def _ligne_ouverte(self, index: QModelIndex) -> None:
		self._ouvrir(index.row())

	def _ouvrir(self, rangee: int) -> None:
		if 0 <= rangee < len(self.resultats):
			resultat = self.resultats[rangee]
			self.ouverte.emit(resultat.genre, resultat.identifiant, resultat.nom)
