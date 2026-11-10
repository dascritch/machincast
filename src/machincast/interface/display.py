"""Mise en forme des heures et des durées à l'écran (https://github.com/dascritch/machincast/issues/23).

Les noms de jours et de mois sont écrits ici, traduits par le catalogue de MachinCast
(https://github.com/dascritch/machincast/issues/360) : l'affichage suit la langue de la session, pas les formats du
poste.
"""

from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtGui import QAction, QGuiApplication, QIcon
from PySide6.QtWidgets import QAbstractButton, QCheckBox, QDateTimeEdit, QMenu, QStyle, QWidget

from machincast.conversion import text_or_none
from machincast.i18n import _, decimal
from machincast.interface import icons

MONTH = (
	_("January"),
	_("February"),
	_("March"),
	_("April"),
	_("May"),
	_("June"),
	_("July"),
	_("August"),
	_("September"),
	_("October"),
	_("November"),
	_("December"),
)
CATEGORIES = {
	"sound": _("sound"),
	"bank": _("bank"),
	"sequence": _("sequence"),
	"event": _("event"),
	"feed": _("feed"),
}
"""Le nom montré de chaque genre d'élément, dont le code ne garde que la clé anglaise
(https://github.com/dascritch/machincast/issues/368)."""
EMPTY = "—"
"""Ce que montre un champ sans valeur : aucun sonore, par exemple."""


def hour(instant: datetime | None, unknown: str | None = None) -> str:
	"""« 20:03:34 », en heure du poste, à la seconde près ; inconnue sans instant."""
	if instant is None:
		if unknown is None:
			return _("unknown")
		return unknown
	return f"{instant.astimezone():%H:%M:%S}"


def duration(seconds: float | timedelta | None) -> str:
	"""« 3:34 », ou « 1:02:05 » au-delà d'une heure, à la seconde entamée près ; « inconnue » sans durée."""
	if seconds is None:
		return _("unknown")
	if isinstance(seconds, timedelta):
		seconds = seconds.total_seconds()
	hours, rest = divmod(int(seconds), 3600)
	minutes, seconds_remaining = divmod(rest, 60)
	if hours > 0:
		return f"{hours}:{minutes:02d}:{seconds_remaining:02d}"
	return f"{minutes}:{seconds_remaining:02d}"


def artist_and_title(artist: str | None, title: str | None) -> str:
	"""« Les Gaufres – Café à minuit », ou ce qui est connu des deux."""
	part_list = []
	for part in (artist, title):
		if part:
			part_list.append(part)
	text = " – ".join(part_list)
	return (text) or (_("(untitled)"))


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
		return _("yes")
	return _("no")


def outside_durations(
	sound_duration: timedelta | None,
	minimum: timedelta | None,
	maximum: timedelta | None,
	bank: str | None = None,
) -> str | None:
	"""« 3:20 : plus court que le minimum de la banque « Jingles », 3:30. » : un sonore hors des durées d'une banque
	(https://github.com/dascritch/machincast/issues/147), nommée si on la donne. None pour un sonore dans ses durées,
	ou de durée inconnue."""
	name = _("the bank")
	if bank is not None:
		name = _("the bank “{bank}”").format(bank=bank)
	if sound_duration is None:
		return None
	if (minimum is not None) and (sound_duration < minimum):
		return _("{duration}: shorter than the minimum of {name}, {duration2}.").format(
			duration=duration(sound_duration), name=name, duration2=duration(minimum)
		)
	if (maximum is not None) and (sound_duration > maximum):
		return _("{duration}: longer than the maximum of {name}, {duration2}.").format(
			duration=duration(sound_duration), name=name, duration2=duration(maximum)
		)
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
	return decimal(f"{value:.1f} {SIZE_UNITS[rank]}")


def date(instant: datetime) -> str:
	"""« 2026-10-14 07:30:00 », en heure du poste."""
	return f"{instant.astimezone():%Y-%m-%d %H:%M:%S}"


def ticked_date(box: QCheckBox, date: QDateTimeEdit) -> datetime | None:
	"""La date saisie, à l'heure du poste ; None si sa case n'est pas cochée."""
	if not box.isChecked():
		return None
	return datetime.fromtimestamp(date.dateTime().toSecsSinceEpoch()).astimezone()


PREVIEW = _("Pre-listen…")
"""L'entrée des menus contextuels qui pré-écoute le sonore de la ligne, comme le bouton de sa fiche
(https://github.com/dascritch/machincast/issues/226)."""


DISABLED_PREVIEW = _(
	"Pre-listen disabled: its sound card is the dummy output (File → Interface preferences…, Audio page)."
)
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
	entry = menu.addAction(icons.icon("preview"), PREVIEW)
	entry.triggered.connect(lambda _ticked=False: ask(sound))
	set_preview(entry, True, PREVIEW)
	menu.setToolTipsVisible(True)
	if first is not None:
		menu.removeAction(entry)
		menu.insertAction(first, entry)
		menu.insertSeparator(first)


# ─── Emplacement d'un sonore (https://github.com/dascritch/machincast/issues/344) ───

COPY_LOCATION = _("Copy the location")
COPY_FEED_URL = _("Copy the URL of the feed")
OPEN_FOLDER = _("Open the folder")


def is_stream_location(location: str) -> bool:
	"""Un emplacement de l'airplay est l'adresse d'un stream, ou le chemin, absolu, d'un fichier."""
	return not location.startswith("/")


def copy_text(text: str) -> None:
	"""Dans le presse-papiers du bureau."""
	clipboard = QGuiApplication.clipboard()
	if clipboard is not None:
		clipboard.setText(text)


def offer_location(menu: QMenu, location: str | None, stream: bool, open_folder: Callable[[Path], None]) -> None:
	"""À la fin du menu d'un sonore, ce que l'onglet Antenne ne montre plus de son emplacement : « Copier
	l'emplacement » et « Ouvrir le dossier » d'un fichier, « Copier l'URL du feed » d'un stream. Rien pour un sonore
	à l'emplacement inconnu. Ouvrir le dossier ne fait que le montrer : jamais un fichier modifié."""
	if location is None:
		return
	if menu.actions():
		menu.addSeparator()
	if stream:
		copy = menu.addAction(COPY_FEED_URL)
	else:
		copy = menu.addAction(COPY_LOCATION)
	copy.triggered.connect(lambda _ticked=False: copy_text(location))
	if not stream:
		folder = menu.addAction(OPEN_FOLDER)
		folder.triggered.connect(lambda _ticked=False: open_folder(Path(location).parent))
