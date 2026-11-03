"""Mise en forme des heures et des durées à l'écran (https://github.com/dascritch/machincast/issues/23).

Les noms de jours et de mois sont écrits ici, en français : l'affichage ne dépend pas de la langue du poste.
"""

from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QAbstractButton, QCheckBox, QDateTimeEdit, QMenu, QStyle, QWidget

from machincast.conversion import text_or_none
from machincast.interface import icons

MONTH = (
	"janvier",
	"février",
	"mars",
	"avril",
	"mai",
	"juin",
	"juillet",
	"août",
	"septembre",
	"octobre",
	"novembre",
	"décembre",
)
EMPTY = "—"
"""Ce que montre un champ sans valeur : aucun sonore, par exemple."""


def hour(instant: datetime | None, unknown: str = "inconnue") -> str:
	"""« 20:03:34 », en heure du poste, à la seconde près ; inconnue sans instant."""
	if instant is None:
		return unknown
	return f"{instant.astimezone():%H:%M:%S}"


def duration(seconds: float | timedelta | None) -> str:
	"""« 3:34 », ou « 1:02:05 » au-delà d'une heure, à la seconde entamée près ; « inconnue » sans durée."""
	if seconds is None:
		return "inconnue"
	if isinstance(seconds, timedelta):
		seconds = seconds.total_seconds()
	hours, rest = divmod(int(seconds), 3600)
	minutes, seconds_remaining = divmod(rest, 60)
	if hours > 0:
		return f"{hours}:{minutes:02d}:{seconds_remaining:02d}"
	return f"{minutes}:{seconds_remaining:02d}"


def artist_and_title(artist: str | None, title: str | None) -> str:
	"""« Les Gaufres – Café à minuit », ou ce qui est connu des deux."""
	text = " – ".join(part for part in (artist, title) if part)
	return (text) or ("(sans titre)")


def sound_name(artist: object, title: object, location: object, address: object) -> str:
	"""Artiste et titre ; sans eux, le nom du fichier, ou l'adresse du stream."""
	if (artist is None) and (title is None):
		if location is not None:
			return Path(str(location)).name
		return str((address) or (""))
	return artist_and_title(text_or_none(artist), text_or_none(title))


def yes_no(value: bool | None, unknown: str = "") -> str:
	if value is None:
		return unknown
	if value:
		return "oui"
	return "non"


def outside_durations(
	sound_duration: timedelta | None,
	minimum: timedelta | None,
	maximum: timedelta | None,
	bank: str | None = None,
) -> str | None:
	"""« 3:20 : plus court que le minimum de la banque « Jingles », 3:30. » : un sonore hors des durées d'une banque
	(https://github.com/dascritch/machincast/issues/147), nommée si on la donne. None pour un sonore dans ses durées,
	ou de durée inconnue."""
	name = "la banque"
	if bank is not None:
		name = f"la banque « {bank} »"
	if sound_duration is None:
		return None
	if (minimum is not None) and (sound_duration < minimum):
		return f"{duration(sound_duration)} : plus court que le minimum de {name}, {duration(minimum)}."
	if (maximum is not None) and (sound_duration > maximum):
		return f"{duration(sound_duration)} : plus long que le maximum de {name}, {duration(maximum)}."
	return None


def anomaly_icon(widget: QWidget) -> QIcon:
	"""L'icône d'avertissement du style du poste, qui marque ce qui est en anomalie."""
	return widget.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)


SIZE_UNITS = ("ko", "Mo", "Go", "To")


def size(bytes_: int) -> str:
	"""« 1,2 Mo », en unités décimales, à un chiffre après la virgule ; « 512 o » en deçà d'un kilo-octet."""
	if bytes_ < 1000:
		return f"{bytes_} o"
	value = bytes_ / 1000
	rank = 0
	while (value >= 1000) and (rank < len(SIZE_UNITS) - 1):
		value /= 1000
		rank += 1
	return f"{value:.1f} {SIZE_UNITS[rank]}".replace(".", ",")


def date(instant: datetime) -> str:
	"""« 2026-10-14 07:30:00 », en heure du poste."""
	return f"{instant.astimezone():%Y-%m-%d %H:%M:%S}"


def ticked_date(box: QCheckBox, date: QDateTimeEdit) -> datetime | None:
	"""La date saisie, à l'heure du poste ; None si sa case n'est pas cochée."""
	if not box.isChecked():
		return None
	return datetime.fromtimestamp(date.dateTime().toSecsSinceEpoch()).astimezone()


PREVIEW = "Pré-écoute…"
"""L'entrée des menus contextuels qui pré-écoute le sonore de la ligne, comme le bouton de sa fiche
(https://github.com/dascritch/machincast/issues/226)."""


DISABLED_PREVIEW = "Pré-écoute désactivée : sa carte son est la sortie factice (Fichier → Préférences…, page Audio)."
"""L'infobulle des boutons et des entrées de menu de la pré-écoute, sur l'entrée « Sortie factice »
(https://github.com/dascritch/machincast/issues/339)."""
_disabled_preview = False


def disable_preview(disabled: bool) -> None:
	"""La pré-écoute de la session, désactivée sur l'entrée « Sortie factice » (audio.preview) : la fenêtre
	principale la règle à son ouverture, et après les préférences ou les suggestions."""
	global _disabled_preview  # noqa: PLW0603 : la pré-écoute de la session, une seule par interface
	_disabled_preview = disabled


def disabled_preview() -> bool:
	return _disabled_preview


def set_preview(item: QAction | QAbstractButton, active: bool, tooltip: str) -> None:
	"""Un bouton ou une entrée de menu qui lance une pré-écoute : grisé, avec l'infobulle qui dit pourquoi, quand la
	pré-écoute est désactivée ; sinon actif selon ce qu'il pré-écoute, avec son infobulle."""
	if _disabled_preview:
		item.setEnabled(False)
		item.setToolTip(DISABLED_PREVIEW)
		return
	item.setEnabled(active)
	item.setToolTip(tooltip)


def offer_preview(menu: QMenu, sound: int, ask: Callable[[int], None]) -> None:
	"""« Pré-écoute… » en tête du menu d'une ligne de sonore, avec l'icône du bouton de la fiche, séparée des entrées
	qui suivent ; grisée, avec son infobulle, quand la pré-écoute est désactivée."""
	first = None
	if menu.actions():
		first = menu.actions()[0]
	entry = menu.addAction(icons.icon("pré-écoute"), PREVIEW)
	entry.triggered.connect(lambda _ticked=False: ask(sound))
	set_preview(entry, True, PREVIEW)
	menu.setToolTipsVisible(True)
	if first is not None:
		menu.removeAction(entry)
		menu.insertAction(first, entry)
		menu.insertSeparator(first)
