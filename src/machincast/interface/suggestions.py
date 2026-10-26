"""Suggestions au lancement de l'interface (https://github.com/dascritch/machincast/issues/119, spec § 8.10).

Au lancement, si les suggestions sont actives (interface.suggestions), l'interface cherche ce qui manque pour démarrer
(manquants) : un événement de priorité fil musical, les banques de BANQUES (par leur nom interne, sans tenir compte des
majuscules) et, sur une vraie sortie, le périphérique de l'antenne. S'il manque quelque chose, une fenêtre modale
(FenetreSuggestions, par machincast.interface.dialogues.suggerer) le propose, chaque élément coché par défaut.

- « Créer » (creer) crée ce qui est coché : le fil musical, permanent, comme le fil musical garanti
  (machincast.interface.fil_musical) ; les banques, aléatoires et sans répertoire, chacune avec ses réglages
  (REGLAGES) : « Identifiant station » marquée « ne pas répéter », les musiques de 15 minutes au plus, l'habillage
  et les annonces de 2 minutes au plus, ces dernières enchaînées sans crossfade, imposé à 0 seconde à leurs sonores
  (https://github.com/dascritch/machincast/issues/231). Un fil musical encore vide, créé ou déjà là, reçoit la
  rotation type (ROTATION), avec les banques qui existent. Le périphérique d'antenne choisi s'enregistre dans
  audio.peripherique (enregistrer).
- « Plus tard » ne crée rien : la fenêtre revient au lancement suivant.
- « Ne plus proposer au lancement » écrit interface.suggestions = false dans le fichier de configuration
  (enregistrer), qui garde ses commentaires.
"""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import psycopg
import tomlkit
from psycopg.rows import TupleRow
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem, QWidget

from machincast import audio as sorties_audio
from machincast.configuration import Audio
from machincast.conversion import texte_ou_rien
from machincast.interface import fil_musical
from machincast.interface.ui.suggestions import Ui_FenetreSuggestions

FIL_MUSICAL = "Fil musical"
"""La ligne du fil musical dans la fenêtre."""


@dataclass(frozen=True)
class Reglage:
	"""Ce qu'une banque suggérée reçoit à sa création."""

	ne_pas_repeter: bool = False
	"""https://github.com/dascritch/machincast/issues/63"""
	duree_max: timedelta | None = None
	sans_crossfade: bool = False
	"""Crossfades de début et de fin imposés à 0 seconde à tous ses sonores : ils s'enchaînent sans se mêler."""


MUSIQUE = Reglage(duree_max=timedelta(minutes=15))
ANNONCE = Reglage(duree_max=timedelta(minutes=2), sans_crossfade=True)
REGLAGES = {
	"Identifiant station": Reglage(ne_pas_repeter=True, duree_max=timedelta(minutes=2)),
	"Musique rotation lourde": MUSIQUE,
	"Musique rotation normale": MUSIQUE,
	"Musique rotation rare": MUSIQUE,
	"Musique rotation de nuit": Reglage(),
	"Partenariats": ANNONCE,
	"Publicités": ANNONCE,
	"Bande-annonce émissions": ANNONCE,
}
"""Les banques suggérées, dans l'ordre où la fenêtre les propose, et leurs réglages
(https://github.com/dascritch/machincast/issues/231)."""
BANQUES = tuple(REGLAGES)
ROTATION = (
	"Identifiant station",
	"Musique rotation lourde",
	"Musique rotation normale",
	"Musique rotation lourde",
	"Musique rotation rare",
)
"""La liste d'un fil musical encore vide ; la rotation de nuit reste à placer à la main dans un événement de nuit."""


def libelle(banque: str) -> str:
	"""« Banque « Identifiant station » » : la ligne d'une banque dans la fenêtre."""
	return f"Banque « {banque} »"


@dataclass(frozen=True)
class Manques:
	"""Ce qui manque pour démarrer."""

	fil_musical: bool
	banques: tuple[str, ...]
	antennes: tuple[sorties_audio.Peripherique, ...] | None = None
	"""Les périphériques que peut prendre l'antenne, quand elle n'en a pas sur une vraie sortie ; None sinon."""

	def elements(self) -> list[str]:
		"""Les lignes à cocher de la fenêtre."""
		lignes = [libelle(banque) for banque in self.banques]
		if self.fil_musical:
			lignes.insert(0, FIL_MUSICAL)
		return lignes

	def vide(self) -> bool:
		return (not self.fil_musical) and (not self.banques) and (self.antennes is None)


@dataclass(frozen=True)
class Reponse:
	"""Ce que la fenêtre a décidé : creer est faux pour « Plus tard »."""

	creer: bool
	fil_musical: bool = False
	banques: tuple[str, ...] = ()
	antenne: str | None = None
	ne_plus_proposer: bool = False


def manquants(connexion: psycopg.Connection[TupleRow], audio: Audio) -> Manques:
	"""Ce qui manque : fil musical, banques suggérées, périphérique d'antenne sur une vraie sortie."""
	with connexion.transaction():
		fil = connexion.execute("SELECT 1 FROM evenements WHERE priorite = 'fil_musical' LIMIT 1").fetchone()
		existantes = {str(nom).casefold() for (nom,) in connexion.execute("SELECT nom_interne FROM banques")}
	banques = tuple(banque for banque in BANQUES if banque.casefold() not in existantes)
	antennes = None
	if (audio.sortie != "factice") and (audio.peripherique is None):
		antennes = tuple(
			peripherique
			for peripherique in sorties_audio.peripheriques(audio.sortie)
			if peripherique.identifiant != audio.preecoute
		)
	return Manques(fil is None, banques, antennes)


def creer(connexion: psycopg.Connection[TupleRow], reponse: Reponse) -> str | None:
	"""Crée ce que la réponse demande, puis remplit un fil musical encore vide ; ce que dit la barre d'état, ou None
	si rien n'est créé."""
	crees: list[str] = []
	with connexion.transaction():
		if reponse.fil_musical:
			nom = fil_musical.garantir(connexion)
			if nom is not None:
				crees.append(f"le fil musical « {nom} »")
		nouvelles = []
		for banque in reponse.banques:
			reglage = REGLAGES[banque]
			regle = "sonore"
			if reglage.sans_crossfade:
				regle = "impose"
			connexion.execute(
				"INSERT INTO banques (nom_interne, mode, ne_pas_repeter, duree_max, crossfade_debut_regle,"
				" crossfade_debut, crossfade_fin_regle, crossfade_fin)"
				" VALUES (%s, 'aleatoire', %s, %s, %s, '0 s', %s, '0 s')",
				(banque, reglage.ne_pas_repeter, reglage.duree_max, regle, regle),
			)
			nouvelles.append(f"« {banque} »")
		if len(nouvelles) == 1:
			crees.append(f"la banque {nouvelles[0]}")
		elif nouvelles:
			crees.append(f"les banques {', '.join(nouvelles)}")
		_remplir_un_fil_vide(connexion)
	if not crees:
		return None
	return f"Créés : {', '.join(crees)}."


def _remplir_un_fil_vide(connexion: psycopg.Connection[TupleRow]) -> None:
	"""Le premier fil musical sans élément, par nom, reçoit la rotation type, avec les banques qui existent."""
	vide = connexion.execute(
		"SELECT e.id FROM evenements e WHERE e.priorite = 'fil_musical'"
		" AND NOT EXISTS (SELECT 1 FROM evenements_elements x WHERE x.evenement_id = e.id)"
		" ORDER BY e.nom_interne LIMIT 1"
	).fetchone()
	if vide is None:
		return
	banques = {
		str(nom).casefold(): int(str(identifiant))
		for identifiant, nom in connexion.execute("SELECT id, nom_interne FROM banques ORDER BY id")
	}
	position = 0
	for banque in ROTATION:
		identifiant = banques.get(banque.casefold())
		if identifiant is None:
			continue
		position += 1
		connexion.execute(
			"INSERT INTO evenements_elements (evenement_id, position, banque_id) VALUES (%s, %s, %s)",
			(vide[0], position, identifiant),
		)


def enregistrer(chemin: Path, antenne: str | None, ne_plus_proposer: bool) -> None:
	"""Écrit dans le fichier de configuration le périphérique d'antenne choisi, et l'arrêt des suggestions ; le reste
	du fichier reste tel quel, commentaires compris."""
	if (antenne is None) and (not ne_plus_proposer):
		return
	document = tomlkit.parse(chemin.read_text(encoding="utf-8"))
	if antenne is not None:
		section_audio = document["audio"]
		assert isinstance(section_audio, tomlkit.items.Table)
		section_audio["peripherique"] = antenne
	if ne_plus_proposer:
		if "interface" not in document:
			document.add("interface", tomlkit.table())
		section_interface = document["interface"]
		assert isinstance(section_interface, tomlkit.items.Table)
		section_interface["suggestions"] = False
	chemin.write_text(tomlkit.dumps(document), encoding="utf-8")


class FenetreSuggestions(QDialog):
	"""La fenêtre des suggestions : une ligne cochée par élément manquant, le choix de l'antenne s'il manque."""

	def __init__(self, manques: Manques, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.ui = Ui_FenetreSuggestions()
		self.ui.setupUi(self)
		self.manques = manques
		for texte in manques.elements():
			ligne = QListWidgetItem(texte, self.ui.elements)
			ligne.setFlags(ligne.flags() | Qt.ItemFlag.ItemIsUserCheckable)
			ligne.setCheckState(Qt.CheckState.Checked)
		self.ui.elements.setVisible(bool(manques.elements()))
		self.ui.groupe_antenne.setVisible(manques.antennes is not None)
		for peripherique in (manques.antennes) or (()):
			self.ui.antenne.addItem(peripherique.nom, peripherique.identifiant)
		boutons = self.ui.boutons
		boutons.button(QDialogButtonBox.StandardButton.Ok).setText("Créer")
		boutons.button(QDialogButtonBox.StandardButton.Cancel).setText("Plus tard")
		boutons.accepted.connect(self.accept)
		boutons.rejected.connect(self.reject)

	def _cochees(self) -> set[str]:
		liste = self.ui.elements
		lignes = [liste.item(rang) for rang in range(liste.count())]
		return {ligne.text() for ligne in lignes if ligne.checkState() == Qt.CheckState.Checked}

	def reponse(self) -> Reponse:
		"""Ce qui est décidé : tout ce qui est coché sur « Créer », rien sur « Plus tard »."""
		ne_plus = self.ui.ne_plus_proposer.isChecked()
		if self.result() != QDialog.DialogCode.Accepted:
			return Reponse(creer=False, ne_plus_proposer=ne_plus)
		cochees = self._cochees()
		antenne = None
		if self.manques.antennes is not None:
			donnee = self.ui.antenne.currentData()
			antenne = texte_ou_rien(donnee)
		return Reponse(
			creer=True,
			fil_musical=FIL_MUSICAL in cochees,
			banques=tuple(banque for banque in self.manques.banques if libelle(banque) in cochees),
			antenne=antenne,
			ne_plus_proposer=ne_plus,
		)
