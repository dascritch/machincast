"""Préférences de l'interface (https://github.com/dascritch/machincast/issues/145, spec § 8.11).

« Préférences… », dans le menu « Fichier », ouvre FenetrePreferences. Sa page « Crossfades », la première
(https://github.com/dascritch/machincast/issues/234), règle les crossfades : leur granularité (à la seconde ou au
dixième de seconde), leur durée maximale, leurs durées par défaut, celles d'un sonore sans crossfade paramétré que sa
banque ne règle pas (machincast.lecture.diffusion.crossfade), et la position des fondus par rapport aux silences
détectés d'un sonore joué sans eux (crossfades.position_entree et position_sortie, machincast.lecture.fondus). Une frise
de démonstration (machincast.interface.frise) montre où tombent les fondus, sur un sonore inventé, et suit les réglages.
Sa page « Audio » règle les périphériques de l'antenne (audio.peripherique), que Machin lecture prend à son prochain
démarrage, et de la pré-écoute (audio.preecoute, https://github.com/dascritch/machincast/issues/116) : chacun est grisé
dans l'autre choix ; elle règle aussi le seuil de silence (silences.seuil,
https://github.com/dascritch/machincast/issues/146), que l'audit complet prend à son prochain passage, et le blanc dans
un sonore (section [blanc_antenne], https://github.com/dascritch/machincast/issues/122) : sa durée, son niveau, et le
passage au secours, que Machin lecture prend à son prochain démarrage. La page « Base »
règle la durée de péremption (base.peremption, https://github.com/dascritch/machincast/issues/268), que Machin purge
prend à son prochain passage, et que suit la fiche d'un élément supprimé. La page « Interface » règle l'accueil, et
choisit l'icône de l'application (interface.icone, https://github.com/dascritch/machincast/issues/111) : une image
lisible, ou celle de MachinCast ; la fenêtre principale la donne aussitôt à ses fenêtres et aux raccourcis déjà
installés (machincast.raccourci.reecrire).

- Les préférences s'enregistrent dans la section [crossfades] du fichier de configuration (ecrire), qui garde ses
  commentaires et ses autres sections : tomlkit le réécrit tel qu'il l'a lu, sauf les clés réglées. Une durée par
  défaut retirée en disparaît.
- Les préférences de la session (crossfades, definir) valent pour les fiches ouvertes ensuite ; Machin lecture prend
  les durées par défaut à son prochain démarrage.
- Les champs de crossfade des fiches les suivent (regler) : un pas d'une seconde ou d'un dixième, et la durée
  maximale, sauf pour une valeur déjà plus longue, qui reste telle quelle.
"""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import tomlkit
from PySide6.QtCore import QLocale
from PySide6.QtGui import QIcon, QStandardItemModel
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QVBoxLayout, QWidget

from machincast import audio as sorties_audio
from machincast.configuration import (
	PEREMPTION,
	SEUIL_DE_SILENCE,
	BlancAntenne,
	Crossfades,
	Granularite,
	SortieAudio,
)
from machincast.conversion import texte_ou_rien
from machincast.interface.application import ICONE, lisible
from machincast.interface.frise import Frise, Plan, forme_de_demonstration
from machincast.interface.ui.preferences import Ui_FenetrePreferences
from machincast.lecture.fondus import LIBELLES, POSITIONS, Position

FRANCAIS = QLocale(QLocale.Language.French, QLocale.Country.France)
"""Les durées s'écrivent avec une virgule."""
GRANULARITES: tuple[tuple[Granularite, str], ...] = (
	("dixieme", "Au dixième de seconde"),
	("seconde", "À la seconde"),
)
PAS: dict[Granularite, tuple[int, float]] = {"dixieme": (1, 0.1), "seconde": (0, 1.0)}
"""Pour chaque granularité : les décimales et le pas d'un champ de crossfade."""

ICONE_PAR_DEFAUT = "Icône de MachinCast"
"""Ce que montre la page « Interface » quand aucune image n'est choisie."""
TAILLE_DE_L_APERCU = 48
A_RENSEIGNER = "(à renseigner)"
"""Le périphérique de l'antenne, quand la configuration ne le donne pas : Machin lecture refuse alors de diffuser."""


@dataclass(frozen=True)
class Reglages:
	"""Ce que règle la fenêtre des préférences."""

	crossfades: Crossfades
	antenne: str | None
	"""audio.peripherique ; None tant qu'il n'est pas renseigné."""
	preecoute: str
	"""audio.preecoute."""
	seuil_silences: float = SEUIL_DE_SILENCE
	"""silences.seuil, en dB crête (https://github.com/dascritch/machincast/issues/146)."""
	saturation: bool = True
	"""interface.saturation : le voyant « Saturation » de l'accueil est affiché
	(https://github.com/dascritch/machincast/issues/191)."""
	suggestions: bool = True
	"""interface.suggestions : au lancement, l'interface propose ce qui manque pour démarrer
	(https://github.com/dascritch/machincast/issues/119)."""
	icone: Path | None = None
	"""interface.icone : l'image choisie pour icône de l'application ; None : celle de MachinCast
	(https://github.com/dascritch/machincast/issues/111)."""
	peremption: int = PEREMPTION
	"""base.peremption, en jours : au-delà, Machin purge efface de la base
	(https://github.com/dascritch/machincast/issues/268)."""
	blanc_antenne: BlancAntenne = BlancAntenne()
	"""La section [blanc_antenne] : blanc dans un sonore, à l'antenne
	(https://github.com/dascritch/machincast/issues/122)."""


_courantes = Crossfades()
_peremption = PEREMPTION


DEMONSTRATION = (30.0, 3.0, 4.0)
"""Le sonore de la frise de démonstration (https://github.com/dascritch/machincast/issues/234) : sa durée, et ses
silences détectés au début et à la fin, en secondes ; il est joué sans eux."""


def crossfades() -> Crossfades:
	"""Les préférences de la session, que suivent les fiches qui s'ouvrent."""
	return _courantes


def definir(reglages: Crossfades) -> None:
	global _courantes  # noqa: PLW0603 : les préférences de la session, une seule par interface
	_courantes = reglages


def peremption() -> int:
	"""La durée de péremption de la session, en jours : la fiche d'un élément supprimé dit quand il sera effacé."""
	return _peremption


def definir_peremption(jours: int) -> None:
	global _peremption  # noqa: PLW0603 : les préférences de la session, une seule par interface
	_peremption = jours


def regler(champ: QDoubleSpinBox, granularite: Granularite, maximum: timedelta) -> None:
	"""Le pas, les décimales et la durée maximale d'un champ de crossfade."""
	decimales, pas = PAS[granularite]
	champ.setLocale(FRANCAIS)
	champ.setDecimals(decimales)
	champ.setSingleStep(pas)
	champ.setMaximum(maximum.total_seconds())


def regler_selon_les_preferences(champ: QDoubleSpinBox) -> None:
	reglages = crossfades()
	regler(champ, reglages.granularite, reglages.maximum)


def montrer(champ: QDoubleSpinBox, secondes: float) -> None:
	"""Une valeur plus longue que la durée maximale reste telle quelle : le champ s'allonge pour elle."""
	champ.setMaximum(max(champ.maximum(), secondes))
	champ.setValue(secondes)


def _secondes(duree: timedelta) -> int | float:
	"""Un nombre entier de secondes s'écrit sans décimale dans le fichier."""
	return _nombre(duree.total_seconds())


def _nombre(valeur: float) -> int | float:
	"""Un nombre entier s'écrit sans décimale dans le fichier."""
	if valeur == int(valeur):
		return int(valeur)
	return valeur


def ecrire(chemin: Path, reglages: Reglages) -> None:
	"""Écrit les réglages dans les sections [crossfades], [audio], [silences], [blanc_antenne], [interface] et [base] du
	fichier de configuration, qui garde le reste tel quel, commentaires compris. Une section [blancs], l'ancien nom de
	[silences], est renommée."""
	document = tomlkit.parse(chemin.read_text(encoding="utf-8"))
	base = document["base"]
	assert isinstance(base, tomlkit.items.Table)
	# La durée par défaut ne s'écrit pas dans une section qui ne la donne pas : [base] reste telle quelle.
	if ("peremption" in base) or (reglages.peremption != PEREMPTION):
		base["peremption"] = reglages.peremption
	if "crossfades" not in document:
		document.add("crossfades", tomlkit.table())
	section = document["crossfades"]
	assert isinstance(section, tomlkit.items.Table)
	crossfades = reglages.crossfades
	section["granularite"] = crossfades.granularite
	section["maximum"] = _secondes(crossfades.maximum)
	section["position_entree"] = crossfades.entree
	section["position_sortie"] = crossfades.sortie
	audio = document["audio"]
	assert isinstance(audio, tomlkit.items.Table)
	if reglages.antenne is not None:
		audio["peripherique"] = reglages.antenne
	audio["preecoute"] = reglages.preecoute
	for cle, duree in (("debut", crossfades.debut), ("fin", crossfades.fin)):
		if duree is None:
			if cle in section:
				del section[cle]
			continue
		section[cle] = _secondes(duree)
	# L'ancienne section [blancs] devient [silences], commentaires compris
	# (https://github.com/dascritch/machincast/issues/291).
	if ("blancs" in document) and ("silences" not in document):
		document.add("silences", document.pop("blancs"))
	if "silences" not in document:
		document.add("silences", tomlkit.table())
	silences = document["silences"]
	assert isinstance(silences, tomlkit.items.Table)
	silences["seuil"] = _nombre(reglages.seuil_silences)
	if "blanc_antenne" not in document:
		document.add("blanc_antenne", tomlkit.table())
	blanc_antenne = document["blanc_antenne"]
	assert isinstance(blanc_antenne, tomlkit.items.Table)
	blanc_antenne["duree"] = _secondes(reglages.blanc_antenne.duree)
	blanc_antenne["seuil"] = _nombre(reglages.blanc_antenne.seuil)
	blanc_antenne["secours"] = reglages.blanc_antenne.secours
	if "interface" not in document:
		document.add("interface", tomlkit.table())
	section_interface = document["interface"]
	assert isinstance(section_interface, tomlkit.items.Table)
	section_interface["saturation"] = reglages.saturation
	section_interface["suggestions"] = reglages.suggestions
	if reglages.icone is not None:
		section_interface["icone"] = str(reglages.icone)
	elif "icone" in section_interface:
		del section_interface["icone"]
	chemin.write_text(tomlkit.dumps(document), encoding="utf-8")


class FenetrePreferences(QDialog):
	"""La fenêtre des préférences : une page « Interface », avec les crossfades, et une page « Audio », avec les
	périphériques."""

	def __init__(self, tous: Reglages, sortie: SortieAudio, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.ui = Ui_FenetrePreferences()
		self.ui.setupUi(self)
		ui = self.ui
		reglages = tous.crossfades
		trouves = sorties_audio.peripheriques(sortie)
		_garnir(ui.antenne, tous.antenne, trouves)
		_garnir(ui.preecoute, tous.preecoute, trouves)
		ui.antenne.currentIndexChanged.connect(self._exclure)
		ui.preecoute.currentIndexChanged.connect(self._exclure)
		self._exclure()
		for valeur, texte in GRANULARITES:
			ui.granularite.addItem(texte, valeur)
		ui.granularite.setCurrentIndex(ui.granularite.findData(reglages.granularite))
		self._granularite()
		ui.maximum.setValue(reglages.maximum.total_seconds())
		self._maximum()
		for case, champ, duree in ((ui.a_debut, ui.debut, reglages.debut), (ui.a_fin, ui.fin, reglages.fin)):
			case.toggled.connect(champ.setEnabled)
			case.setChecked(duree is not None)
			if duree is not None:
				champ.setValue(duree.total_seconds())
		ui.seuil_silences.setLocale(FRANCAIS)
		ui.seuil_silences.setValue(tous.seuil_silences)
		ui.secours_blanc.setChecked(tous.blanc_antenne.secours)
		ui.duree_blanc.setLocale(FRANCAIS)
		ui.duree_blanc.setValue(tous.blanc_antenne.duree.total_seconds())
		ui.seuil_blanc.setLocale(FRANCAIS)
		ui.seuil_blanc.setValue(tous.blanc_antenne.seuil)
		ui.peremption.setValue(tous.peremption)
		ui.saturation.setChecked(tous.saturation)
		ui.suggestions.setChecked(tous.suggestions)
		self.icone = tous.icone
		self._montrer_l_icone()
		self._signaler("")
		ui.choisir_icone.clicked.connect(self._choisir_l_icone)
		ui.icone_par_defaut.clicked.connect(self._revenir_a_l_icone_par_defaut)
		ui.granularite.currentIndexChanged.connect(self._granularite)
		ui.maximum.valueChanged.connect(self._maximum)
		# Les positions des fondus, et leur frise de démonstration (https://github.com/dascritch/machincast/issues/234).
		for choix, actuelle in ((ui.position_entree, reglages.entree), (ui.position_sortie, reglages.sortie)):
			for position in POSITIONS:
				choix.addItem(LIBELLES[position], position)
			choix.setCurrentIndex(choix.findData(actuelle))
			choix.currentIndexChanged.connect(self._demontrer)
		self.demonstration = Frise(ui.place_demonstration, interactive=False)
		disposition = QVBoxLayout(ui.place_demonstration)
		disposition.setContentsMargins(0, 0, 0, 0)
		disposition.addWidget(self.demonstration)
		longueur, silence_debut, silence_fin = DEMONSTRATION
		self.demonstration.montrer_la_forme(forme_de_demonstration(longueur, silence_debut, silence_fin))
		for champ in (ui.debut, ui.fin):
			champ.valueChanged.connect(self._demontrer)
		self._demontrer()
		ui.boutons.accepted.connect(self.accept)
		ui.boutons.rejected.connect(self.reject)

	def _montrer_l_icone(self) -> None:
		"""L'aperçu et le chemin de l'icône ; « Icône de MachinCast » ne sert que pour une autre icône."""
		ui = self.ui
		image = ICONE
		texte = ICONE_PAR_DEFAUT
		if self.icone is not None:
			image = self.icone
			texte = str(self.icone)
		ui.icone_apercu.setPixmap(QIcon(str(image)).pixmap(TAILLE_DE_L_APERCU))
		ui.icone_chemin.setText(texte)
		ui.icone_par_defaut.setEnabled(self.icone is not None)

	def _choisir_l_icone(self) -> None:
		"""Une image que Qt ne sait pas lire n'est pas prise : la page le dit."""
		# Importé ici : dialogues ouvre cette fenêtre, et importe donc ce module.
		from machincast.interface import dialogues

		choisie = dialogues.choisir_icone(self)
		if choisie is None:
			return
		if not lisible(choisie):
			self._signaler(f"Image illisible : {choisie}")
			return
		self._signaler("")
		self.icone = choisie
		self._montrer_l_icone()

	def _revenir_a_l_icone_par_defaut(self) -> None:
		self._signaler("")
		self.icone = None
		self._montrer_l_icone()

	def _signaler(self, texte: str) -> None:
		"""Ce qui ne va pas avec l'image choisie ; rien, sans place prise sur la page."""
		self.ui.icone_erreur.setText(texte)
		self.ui.icone_erreur.setVisible(texte != "")

	def _choisie(self) -> Granularite:
		granularite: Granularite = self.ui.granularite.currentData()
		return granularite

	def _granularite(self) -> None:
		"""Les champs suivent la granularité choisie ; la durée maximale fait au moins un pas."""
		ui = self.ui
		decimales, pas = PAS[self._choisie()]
		ui.maximum.setLocale(FRANCAIS)
		ui.maximum.setDecimals(decimales)
		ui.maximum.setSingleStep(pas)
		ui.maximum.setMinimum(pas)
		for champ in (ui.debut, ui.fin):
			regler(champ, self._choisie(), timedelta(seconds=ui.maximum.value()))

	def _maximum(self) -> None:
		"""Une durée par défaut ne dépasse pas la durée maximale."""
		for champ in (self.ui.debut, self.ui.fin):
			regler(champ, self._choisie(), timedelta(seconds=self.ui.maximum.value()))

	def _positions(self) -> tuple[Position, Position]:
		entree: Position = self.ui.position_entree.currentData()
		sortie: Position = self.ui.position_sortie.currentData()
		return entree, sortie

	def _demontrer(self) -> None:
		"""La frise de démonstration : le sonore inventé, avec les durées par défaut saisies, même décochées, et les
		positions choisies."""
		duree, silence_debut, silence_fin = DEMONSTRATION
		entree, sortie = self._positions()
		plan = Plan(
			duree,
			silence_debut,
			silence_fin,
			silences_retires=True,
			crossfade_debut=self.ui.debut.value(),
			crossfade_fin=self.ui.fin.value(),
			position_entree=entree,
			position_sortie=sortie,
		)
		self.demonstration.montrer(plan, duree)
		self.ui.legende_demonstration.setText(
			f"Démonstration : un sonore de 30 s, aux silences de 3 s et 4 s. {plan.resume()}"
		)

	def _exclure(self) -> None:
		"""Le périphérique choisi pour l'un est grisé dans l'autre ; « OK » ne donne jamais le même aux deux."""
		ui = self.ui
		antenne, preecoute_choisie = ui.antenne.currentData(), ui.preecoute.currentData()
		_griser(ui.antenne, preecoute_choisie)
		_griser(ui.preecoute, antenne)
		ui.boutons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(antenne != preecoute_choisie)

	def reglages(self) -> Reglages:
		ui = self.ui
		durees: list[timedelta | None] = []
		for case, champ in ((ui.a_debut, ui.debut), (ui.a_fin, ui.fin)):
			duree = None
			if case.isChecked():
				duree = timedelta(seconds=champ.value())
			durees.append(duree)
		entree, sortie = self._positions()
		crossfades = Crossfades(
			durees[0], durees[1], timedelta(seconds=ui.maximum.value()), self._choisie(), entree, sortie
		)
		antenne = ui.antenne.currentData()
		return Reglages(
			crossfades,
			texte_ou_rien(antenne),
			str(ui.preecoute.currentData()),
			round(ui.seuil_silences.value(), 1),
			ui.saturation.isChecked(),
			ui.suggestions.isChecked(),
			self.icone,
			ui.peremption.value(),
			BlancAntenne(
				timedelta(seconds=round(ui.duree_blanc.value(), 1)),
				round(ui.seuil_blanc.value(), 1),
				ui.secours_blanc.isChecked(),
			),
		)


def _garnir(choix: QComboBox, actuel: str | None, trouves: list[sorties_audio.Peripherique]) -> None:
	"""Le périphérique configuré d'abord, « (introuvable) » s'il n'est pas sur le poste, puis les autres."""
	if actuel is None:
		choix.addItem(A_RENSEIGNER, None)
	else:
		nom = next((p.nom for p in trouves if p.identifiant == actuel), f"{actuel} (introuvable)")
		choix.addItem(nom, actuel)
	for peripherique in trouves:
		if peripherique.identifiant != actuel:
			choix.addItem(peripherique.nom, peripherique.identifiant)


def _griser(choix: QComboBox, exclu: object) -> None:
	modele = choix.model()
	assert isinstance(modele, QStandardItemModel)
	for indice in range(choix.count()):
		modele.item(indice).setEnabled(choix.itemData(indice) != exclu)
