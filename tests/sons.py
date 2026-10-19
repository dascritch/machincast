"""Fichiers sonores de test (https://github.com/dascritch/machincast/issues/7).

Les fichiers de tests/fichiers-sonores/ sont versionnés : une seconde de sinusoïde en mono, la plus petite
taille utile, dans chacun des formats de la spec. Les fichiers sain.* n'ont aucun tag ; les fichiers tags.*
portent TAGS_DE_TEST (https://github.com/dascritch/machincast/issues/8), dans les formats où GStreamer sait les
écrire (pas l'AIFF). Les scénarios en copient un dans leur répertoire temporaire, puis peuvent le tronquer ou
le corrompre ; le dépôt n'est jamais modifié.

Pour les régénérer (encodeurs GStreamer nécessaires) : python -m tests.sons
"""

import logging
import shutil
from pathlib import Path
from typing import cast

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

FICHIERS_SONORES = Path(__file__).parent / "fichiers-sonores"
DUREE_SECONDES = 1
FREQUENCE = 44100
ECHANTILLONS_PAR_TAMPON = 1024

# Encodeur et multiplexeur de chaque format, et le paquet Ubuntu qui les fournit.
# flacenc écrit seul dans le fichier : sans flacparse derrière lui, il peut réécrire l'en-tête
# STREAMINFO à la fin avec le nombre total d'échantillons, comme le font les logiciels d'encodage.
ENCODEURS: dict[str, tuple[str, str]] = {
	"wav": ("wavenc", "gstreamer1.0-plugins-good"),
	"flac": ("flacenc", "gstreamer1.0-plugins-good"),
	"ogg": ("vorbisenc ! oggmux", "gstreamer1.0-plugins-base"),
	"mp3": ("lamemp3enc", "gstreamer1.0-plugins-good"),
	"m4a": ("voaacenc ! mp4mux", "gstreamer1.0-plugins-bad"),
	# AAC brut, en trames ADTS, sans conteneur MP4.
	"aac": ("voaacenc ! aacparse ! audio/mpeg,mpegversion=4,stream-format=adts", "gstreamer1.0-plugins-bad"),
	"aiff": ("aiffmux", "gstreamer1.0-plugins-bad"),
}

# Chaîne d'encodage des fichiers tagués : l'élément nommé « tags » reçoit les tags (interface GstTagSetter).
# Le MP3 a besoin d'id3v2mux pour porter des tags ID3.
ENCODEURS_TAGUES: dict[str, str] = {
	"wav": "wavenc name=tags",
	"flac": "flacenc name=tags",
	"ogg": "vorbisenc name=tags ! oggmux",
	"mp3": "lamemp3enc ! id3v2mux name=tags",
	"m4a": "voaacenc ! mp4mux name=tags",
}

# Noms fictifs, avec des accents pour vérifier l'UTF-8. L'année est donnée deux fois : FLAC et Ogg ne l'écrivent
# que depuis un horodatage (datetime), le M4A que depuis une date (date).
TAGS_DE_TEST = (
	'taglist, artist=(string)"Les Gaufres Électriques", title=(string)"Café à minuit", album=(string)"Été indien",'
	' album-artist=(string)"Collectif Exemple", genre=(string)Chanson, composer=(string)"Jeanne Exemple",'
	' organization=(string)"Disques Exemple", track-number=(uint)7, date=(date)1987-06-21,'
	" datetime=(datetime)1987-06-21"
)


def copie_de_test(format_sonore: str, repertoire: Path, variante: str = "sain") -> Path:
	"""Copie le fichier sonore de test du format demandé (sain.* sans tags, tags.* tagué) dans le répertoire."""
	source = FICHIERS_SONORES / f"{variante}.{format_sonore}"
	assert source.is_file(), f"{source} absent : le régénérer avec python -m tests.sons"
	return Path(shutil.copy(source, repertoire / source.name))


def tronquer(chemin: Path, fraction: float = 0.5) -> None:
	"""Ne garde que le début du fichier, comme un téléchargement ou une copie interrompus."""
	donnees = chemin.read_bytes()
	chemin.write_bytes(donnees[: round(len(donnees) * fraction)])


def corrompre(chemin: Path, octets: int, position: float = 1 / 3) -> None:
	"""Altère des octets au milieu du fichier, comme un secteur de disque endommagé. Déterministe."""
	donnees = bytearray(chemin.read_bytes())
	debut = round(len(donnees) * position)
	for indice in range(debut, min(debut + octets, len(donnees))):
		donnees[indice] = (donnees[indice] * 7 + 13) & 0xFF
	chemin.write_bytes(bytes(donnees))


def generer_son(format_sonore: str, chemin: Path, secondes: float = DUREE_SECONDES, tags: str | None = None) -> Path:
	"""Écrit une sinusoïde mono de la durée donnée (à un tampon près) dans le format demandé, avec les tags donnés."""
	Gst.init(None)
	encodeur, paquet = ENCODEURS[format_sonore]
	if tags is not None:
		encodeur = ENCODEURS_TAGUES[format_sonore]
	tampons = max(1, round(secondes * FREQUENCE / ECHANTILLONS_PAR_TAMPON))
	try:
		pipeline = Gst.parse_launch(
			f"audiotestsrc wave=sine num-buffers={tampons} samplesperbuffer={ECHANTILLONS_PAR_TAMPON}"
			f" ! audio/x-raw,rate={FREQUENCE},channels=1 ! audioconvert ! {encodeur} ! filesink name=fichier"
		)
	except gi.repository.GLib.Error as erreur:
		raise RuntimeError(f"encodeur {format_sonore} indisponible ({erreur.message}) : installer {paquet}") from erreur
	assert isinstance(pipeline, Gst.Bin)
	fichier = pipeline.get_by_name("fichier")
	assert fichier is not None
	fichier.set_property("location", str(chemin))
	if tags is not None:
		porteur = pipeline.get_by_name("tags")
		liste = Gst.TagList.new_from_string(tags)
		assert (porteur is not None) and (liste is not None)
		# L'élément nommé « tags » implémente l'interface GstTagSetter (voir ENCODEURS_TAGUES).
		cast(Gst.TagSetter, porteur).merge_tags(liste, Gst.TagMergeMode.REPLACE)
	pipeline.set_state(Gst.State.PLAYING)
	bus = pipeline.get_bus()
	assert bus is not None
	message = bus.timed_pop_filtered(60 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
	pipeline.set_state(Gst.State.NULL)
	assert (message is not None) and (message.type == Gst.MessageType.EOS), f"génération de {chemin} impossible"
	return chemin


if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO, format="{message}", style="{")
	FICHIERS_SONORES.mkdir(exist_ok=True)
	for format_sonore in ENCODEURS:
		chemin = generer_son(format_sonore, FICHIERS_SONORES / f"sain.{format_sonore}")
		logging.info(f"{chemin.name} : {chemin.stat().st_size} octets")
	for format_sonore in ENCODEURS_TAGUES:
		chemin = generer_son(format_sonore, FICHIERS_SONORES / f"tags.{format_sonore}", tags=TAGS_DE_TEST)
		logging.info(f"{chemin.name} : {chemin.stat().st_size} octets")
