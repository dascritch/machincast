"""Préférences de l'interface (https://github.com/dascritch/machincast/issues/145, spec § 8.11).

« Préférences… », dans le menu « Fichier », ouvre FenetrePreferences. Sa page « Interface » règle les crossfades : leur
granularité (à la seconde ou au dixième de seconde), leur durée maximale, et leurs durées par défaut, celles d'un
sonore sans crossfade paramétré que sa banque ne règle pas (machincast.lecture.diffusion.crossfade).

- Les préférences s'enregistrent dans la section [crossfades] du fichier de configuration (ecrire), qui garde ses
  commentaires et ses autres sections : tomlkit le réécrit tel qu'il l'a lu, sauf les clés réglées. Une durée par
  défaut retirée en disparaît.
- Les préférences de la session (crossfades, definir) valent pour les fiches ouvertes ensuite ; Machin lecture prend
  les durées par défaut à son prochain démarrage.
- Les champs de crossfade des fiches les suivent (regler) : un pas d'une seconde ou d'un dixième, et la durée
  maximale, sauf pour une valeur déjà plus longue, qui reste telle quelle.
"""

from datetime import timedelta
from pathlib import Path

import tomlkit
from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QDialog, QDoubleSpinBox, QWidget

from machincast.configuration import Crossfades, Granularite
from machincast.interface.ui.preferences import Ui_FenetrePreferences

FRANCAIS = QLocale(QLocale.Language.French, QLocale.Country.France)
"""Les durées s'écrivent avec une virgule."""
GRANULARITES: tuple[tuple[Granularite, str], ...] = (
	("dixieme", "Au dixième de seconde"),
	("seconde", "À la seconde"),
)
PAS: dict[Granularite, tuple[int, float]] = {"dixieme": (1, 0.1), "seconde": (0, 1.0)}
"""Pour chaque granularité : les décimales et le pas d'un champ de crossfade."""

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


def ecrire(chemin: Path, reglages: Crossfades) -> None:
	"""Écrit les réglages dans la section [crossfades] du fichier de configuration, qui garde le reste tel quel."""
	document = tomlkit.parse(chemin.read_text(encoding="utf-8"))
	if "crossfades" not in document:
		document.add("crossfades", tomlkit.table())
	section = document["crossfades"]
	assert isinstance(section, tomlkit.items.Table)
	section["granularite"] = reglages.granularite
	section["maximum"] = _secondes(reglages.maximum)
	for cle, duree in (("debut", reglages.debut), ("fin", reglages.fin)):
		if duree is None:
			if cle in section:
				del section[cle]
			continue
		section[cle] = _secondes(duree)
	chemin.write_text(tomlkit.dumps(document), encoding="utf-8")


class FenetrePreferences(QDialog):
	"""La fenêtre des préférences : une page « Interface », avec les crossfades."""

	def __init__(self, reglages: Crossfades, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.ui = Ui_FenetrePreferences()
		self.ui.setupUi(self)
		ui = self.ui
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

	def reglages(self) -> Crossfades:
		ui = self.ui
		durees: list[timedelta | None] = []
		for case, champ in ((ui.a_debut, ui.debut), (ui.a_fin, ui.fin)):
			duree = None
			if case.isChecked():
				duree = timedelta(seconds=champ.value())
			durees.append(duree)
		return Crossfades(durees[0], durees[1], timedelta(seconds=ui.maximum.value()), self._choisie())
