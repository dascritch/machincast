"""Tags d'un fichier sonore : artiste, titre et métadonnées musicales (https://github.com/dascritch/machincast/issues/8).

Les tags sont lus par GStreamer pendant le décodage complet de la vérification : ID3 (MP3, et AIFF quand le
fichier en porte), Vorbis comments (Ogg, FLAC), atomes MP4 (M4A) et INFO (WAV). Ils sont convertis en
artiste, titre (colonnes de sonores) et en clés de l'objet JSON music_metadata.
"""

from dataclasses import dataclass, field

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from machincast.conformation import conform  # noqa: E402
from machincast.database import SHORT_TEXT_LENGTH  # noqa: E402

Value = str | int

# Clé de music_metadata ← tags GStreamer, par ordre de préférence. L'année est traitée à part.
TEXTS: dict[str, tuple[str, ...]] = {
	"album": (Gst.TAG_ALBUM,),
	"album_artist": (Gst.TAG_ALBUM_ARTIST,),
	"genre": (Gst.TAG_GENRE,),
	"composer": (Gst.TAG_COMPOSER,),
	# Vorbis ORGANIZATION ; ID3 TPUB.
	"label": (Gst.TAG_ORGANIZATION, Gst.TAG_PUBLISHER),
}

KEYS: tuple[str, ...] = ("year", *TEXTS, "track")
"""Clés de music_metadata tenues par l'indexeur ; les autres clés ne sont jamais modifiées."""


@dataclass(frozen=True)
class Tags:
	artist: str | None
	title: str | None
	metadata: dict[str, Value] = field(default_factory=dict)
	"""Clés de CLES trouvées dans les tags ; une clé absente n'a pas de tag."""


def _text(list_: Gst.TagList, *names: str, length: int | None = None) -> str | None:
	"""Premier tag texte non vide parmi les noms, une fois conformé
	(https://github.com/dascritch/machincast/issues/108) ; plusieurs valeurs d'un tag sont jointes par GStreamer."""
	for name in names:
		found, value = list_.get_string(name)
		if not found:
			continue
		text = conform((value) or (""))
		if text != "":
			if length is not None:
				return text[:length]
			return text
	return None


def _year(list_: Gst.TagList) -> int | None:
	"""Année de sortie : une date (date), sinon un horodatage sans heure (datetime).

	Un horodatage avec heure est une date de création, pas de sortie : un M4A sans date de sortie annonce ainsi
	la date de création de son conteneur, qui ne doit pas devenir l'année du morceau.
	"""
	found, date = list_.get_date(Gst.TAG_DATE)
	if (found) and (date is not None) and (date.valid()):
		return int(date.get_year())
	found, timestamp = list_.get_date_time(Gst.TAG_DATE_TIME)
	if (found) and (timestamp is not None) and (timestamp.has_year()) and (not timestamp.has_time()):
		return int(timestamp.get_year())
	return None


def extract(list_: Gst.TagList) -> Tags:
	"""Artiste, titre et métadonnées musicales d'une liste de tags GStreamer ; textes vides ignorés."""
	metadata: dict[str, Value] = {}
	year = _year(list_)
	if year is not None:
		metadata["year"] = year
	for key, names in TEXTS.items():
		text = _text(list_, *names)
		if text is not None:
			metadata[key] = text
	found, track = list_.get_uint(Gst.TAG_TRACK_NUMBER)
	if (found) and (track > 0):
		metadata["track"] = int(track)
	return Tags(
		artist=_text(list_, Gst.TAG_ARTIST, length=SHORT_TEXT_LENGTH),
		title=_text(list_, Gst.TAG_TITLE, length=SHORT_TEXT_LENGTH),
		metadata=metadata,
	)


def merge(
	current_list: dict[str, object], fetched_list: dict[str, Value], edited_fields: list[str]
) -> dict[str, object]:
	"""Métadonnées musicales après lecture des tags.

	Chaque clé de CLES prend la valeur de son tag, ou disparaît si le tag est absent, sauf si elle a été
	éditée à la main (« music_metadata.<clé> » dans edited_fields). Les autres clés sont conservées.
	"""
	result = dict(current_list)
	for key in KEYS:
		if f"music_metadata.{key}" in edited_fields:
			continue
		if key in fetched_list:
			result[key] = fetched_list[key]
		else:
			result.pop(key, None)
	return result
