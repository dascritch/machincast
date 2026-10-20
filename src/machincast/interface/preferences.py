"""Préférences de l'interface (https://github.com/dascritch/machincast/issues/145, spec § 8.11).

« Préférences… », dans le menu « Fichier », ouvre FenetrePreferences. Sa page « Interface » règle les crossfades : leur
granularité (à la seconde ou au dixième de seconde), leur durée maximale, et leurs durées par défaut, celles d'un
sonore sans crossfade paramétré que sa banque ne règle pas (machincast.lecture.diffusion.crossfade). Sa page « Audio »
règle les périphériques de l'antenne (audio.peripherique), que Machin lecture prend à son prochain démarrage, et de la
pré-écoute (audio.preecoute, https://github.com/dascritch/machincast/issues/116) : chacun est grisé dans l'autre choix.

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
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QWidget

from machincast.configuration import Crossfades, Granularite, SortieAudio
from machincast.interface import preecoute
from machincast.interface.ui.preferences import Ui_FenetrePreferences

FRANCAIS = QLocale(QLocale.Language.French, QLocale.Country.France)
"""Les durées s'écrivent avec une virgule."""
GRANULARITES: tuple[tuple[Granularite, str], ...] = (
	("dixieme", "Au dixième de seconde"),
	("seconde", "À la seconde"),
)
PAS: dict[Granularite, tuple[int, float]] = {"dixieme": (1, 0.1), "seconde": (0, 1.0)}
"""Pour chaque granularité : les décimales et le pas d'un champ de crossfade."""

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


_courantes = Crossfades()


def crossfades() -> Crossfades:
	"""Les préférences de la session, que suivent les fiches qui s'ouvrent."""
	return _courantes


def definir(reglages: Crossfades) -> None:
	global _courantes  # noqa: PLW0603 : les préférences de la session, une seule par interface
	_courantes = reglages


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
	secondes = duree.total_seconds()
	if secondes == int(secondes):
		return int(secondes)
	return secondes


def ecrire(chemin: Path, reglages: Reglages) -> None:
	"""Écrit les réglages dans les sections [crossfades] et [audio] du fichier de configuration, qui garde le reste
	tel quel, commentaires compris."""
	document = tomlkit.parse(chemin.read_text(encoding="utf-8"))
	if "crossfades" not in document:
		document.add("crossfades", tomlkit.table())
	section = document["crossfades"]
	assert isinstance(section, tomlkit.items.Table)
	crossfades = reglages.crossfades
	section["granularite"] = crossfades.granularite
	section["maximum"] = _secondes(crossfades.maximum)
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
		trouves = preecoute.peripheriques(sortie)
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
		ui.granularite.currentIndexChanged.connect(self._granularite)
		ui.maximum.valueChanged.connect(self._maximum)
		ui.boutons.accepted.connect(self.accept)
		ui.boutons.rejected.connect(self.reject)

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
		crossfades = Crossfades(durees[0], durees[1], timedelta(seconds=ui.maximum.value()), self._choisie())
		antenne = ui.antenne.currentData()
		return Reglages(crossfades, None if antenne is None else str(antenne), str(ui.preecoute.currentData()))


def _garnir(choix: QComboBox, actuel: str | None, trouves: list[preecoute.Peripherique]) -> None:
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
