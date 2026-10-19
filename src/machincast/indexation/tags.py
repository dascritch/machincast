"""Tags d'un fichier sonore : artiste, titre et métadonnées musicales (https://github.com/dascritch/machincast/issues/8).

Les tags sont lus par GStreamer pendant le décodage complet de la vérification : ID3 (MP3, et AIFF quand le
fichier en porte), Vorbis comments (Ogg, FLAC), atomes MP4 (M4A) et INFO (WAV). Ils sont convertis en
artiste, titre (colonnes de sonores) et en clés de l'objet JSON metadonnees_musicales.
"""

from dataclasses import dataclass, field

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from machincast.base import LONGUEUR_TEXTE_COURT  # noqa: E402

Valeur = str | int

# Clé de metadonnees_musicales ← tags GStreamer, par ordre de préférence. L'année est traitée à part.
TEXTES: dict[str, tuple[str, ...]] = {
	"album": (Gst.TAG_ALBUM,),
	"artiste_album": (Gst.TAG_ALBUM_ARTIST,),
	"genre": (Gst.TAG_GENRE,),
	"compositeur": (Gst.TAG_COMPOSER,),
	# Vorbis ORGANIZATION ; ID3 TPUB.
	"label": (Gst.TAG_ORGANIZATION, Gst.TAG_PUBLISHER),
}

CLES: tuple[str, ...] = ("annee", *TEXTES, "piste")
"""Clés de metadonnees_musicales tenues par l'indexeur ; les autres clés ne sont jamais modifiées."""


@dataclass(frozen=True)
class Tags:
	artiste: str | None
	titre: str | None
	metadonnees: dict[str, Valeur] = field(default_factory=dict)
	"""Clés de CLES trouvées dans les tags ; une clé absente n'a pas de tag."""


def _texte(liste: Gst.TagList, *noms: str, longueur: int | None = None) -> str | None:
	"""Premier tag texte non vide parmi les noms ; plusieurs valeurs d'un même tag sont jointes par GStreamer."""
	for nom in noms:
		trouve, valeur = liste.get_string(nom)
		if (trouve) and (valeur) and (valeur.strip()):
			texte = valeur.strip()
			return texte[:longueur] if longueur is not None else texte
	return None


def _annee(liste: Gst.TagList) -> int | None:
	"""Année de sortie : une date (date), sinon un horodatage sans heure (datetime).

	Un horodatage avec heure est une date de création, pas de sortie : un M4A sans date de sortie annonce ainsi
	la date de création de son conteneur, qui ne doit pas devenir l'année du morceau.
	"""
	trouve, date = liste.get_date(Gst.TAG_DATE)
	if (trouve) and (date is not None) and (date.valid()):
		return int(date.get_year())
	trouve, horodatage = liste.get_date_time(Gst.TAG_DATE_TIME)
	if (trouve) and (horodatage is not None) and (horodatage.has_year()) and (not horodatage.has_time()):
		return int(horodatage.get_year())
	return None


def extraire(liste: Gst.TagList) -> Tags:
	"""Artiste, titre et métadonnées musicales d'une liste de tags GStreamer ; textes vides ignorés."""
	metadonnees: dict[str, Valeur] = {}
	annee = _annee(liste)
	if annee is not None:
		metadonnees["annee"] = annee
	for cle, noms in TEXTES.items():
		texte = _texte(liste, *noms)
		if texte is not None:
			metadonnees[cle] = texte
	trouve, piste = liste.get_uint(Gst.TAG_TRACK_NUMBER)
	if (trouve) and (piste > 0):
		metadonnees["piste"] = int(piste)
	return Tags(
		artiste=_texte(liste, Gst.TAG_ARTIST, longueur=LONGUEUR_TEXTE_COURT),
		titre=_texte(liste, Gst.TAG_TITLE, longueur=LONGUEUR_TEXTE_COURT),
		metadonnees=metadonnees,
	)


def fusionner(actuelles: dict[str, object], lues: dict[str, Valeur], champs_edites: list[str]) -> dict[str, object]:
	"""Métadonnées musicales après lecture des tags.

	Chaque clé de CLES prend la valeur de son tag, ou disparaît si le tag est absent, sauf si elle a été
	éditée à la main (« metadonnees_musicales.<clé> » dans champs_edites). Les autres clés sont conservées.
	"""
	resultat = dict(actuelles)
	for cle in CLES:
		if f"metadonnees_musicales.{cle}" in champs_edites:
			continue
		if cle in lues:
			resultat[cle] = lues[cle]
		else:
			resultat.pop(cle, None)
	return resultat
