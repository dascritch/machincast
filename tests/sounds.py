"""Fichiers sonores de test (https://github.com/dascritch/machincast/issues/7).

Les fichiers de tests/fichiers-sonores/ sont versionnés : une seconde de sinusoïde en mono, la plus petite
taille utile, dans chacun des formats de la spec. sain.aiff ne sert qu'aux mesures de tests.gstreamer_measures : l'AIFF
n'est pas pris en charge (https://github.com/dascritch/machincast/issues/284), et la suite de tests ne le décode pas.
muet.mp3 est une seconde de silence numérique, que le serveur de flux envoie pour un flux muet
(https://github.com/dascritch/machincast/issues/122). Les fichiers sain.* n'ont aucun tag ; les fichiers tags.* portent
TEST_TAGS
(https://github.com/dascritch/machincast/issues/8), dans les formats où GStreamer sait les écrire (pas l'AIFF). Les
scénarios en copient un dans leur répertoire temporaire, puis peuvent le tronquer ou le corrompre ; le dépôt n'est
jamais modifié.

Pour les régénérer (encodeurs GStreamer nécessaires) : python -m tests.sounds
"""

import logging
import math
import shutil
import struct
from pathlib import Path
from typing import cast

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

SOUND_FILES = Path(__file__).parent / "fichiers-sonores"
DURATION_SECONDS = 1
FREQUENCY = 44100
SAMPLES_PER_BUFFER = 1024

# Encodeur et multiplexeur de chaque format, et le paquet Ubuntu qui les fournit.
# flacenc écrit seul dans le fichier : sans flacparse derrière lui, il peut réécrire l'en-tête
# STREAMINFO à la fin avec le nombre total d'échantillons, comme le font les logiciels d'encodage.
ENCODERS: dict[str, tuple[str, str]] = {
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
TAGGED_ENCODERS: dict[str, str] = {
	"wav": "wavenc name=tags",
	"flac": "flacenc name=tags",
	"ogg": "vorbisenc name=tags ! oggmux",
	"mp3": "lamemp3enc ! id3v2mux name=tags",
	"m4a": "voaacenc ! mp4mux name=tags",
}

# Noms fictifs, avec des accents pour vérifier l'UTF-8. L'année est donnée deux fois : FLAC et Ogg ne l'écrivent
# que depuis un horodatage (datetime), le M4A que depuis une date (date).
TEST_TAGS = (
	'taglist, artist=(string)"Les Gaufres Électriques", title=(string)"Café à minuit", album=(string)"Été indien",'
	' album-artist=(string)"Collectif Exemple", genre=(string)Chanson, composer=(string)"Jeanne Exemple",'
	' organization=(string)"Disques Exemple", track-number=(uint)7, date=(date)1987-06-21,'
	" datetime=(datetime)1987-06-21"
)


def sample_copy(sound_format: str, directory: Path, variant: str = "sain") -> Path:
	"""Copie le fichier sonore de test du format demandé (sain.* sans tags, tags.* tagué) dans le répertoire."""
	source = SOUND_FILES / f"{variant}.{sound_format}"
	assert source.is_file(), f"{source} absent : le régénérer avec python -m tests.sounds"
	return Path(shutil.copy(source, directory / source.name))


def truncate(path: Path, fraction: float = 0.5) -> None:
	"""Ne garde que le début du fichier, comme un téléchargement ou une copie interrompus."""
	data = path.read_bytes()
	path.write_bytes(data[: round(len(data) * fraction)])


def corrupt(path: Path, bytes_: int, position: float = 1 / 3) -> None:
	"""Altère des octets au milieu du fichier, comme un secteur de disque endommagé. Déterministe."""
	data = bytearray(path.read_bytes())
	start = round(len(data) * position)
	for index in range(start, min(start + bytes_, len(data))):
		data[index] = (data[index] * 7 + 13) & 0xFF
	path.write_bytes(bytes(data))


def generate_sound(
	sound_format: str, path: Path, seconds: float = DURATION_SECONDS, tags: str | None = None, wave: str = "sine"
) -> Path:
	"""Écrit une sinusoïde mono de la durée donnée (à un tampon près) dans le format demandé, avec les tags donnés ;
	onde : « silence » pour un silence numérique (muet.mp3, https://github.com/dascritch/machincast/issues/122)."""
	Gst.init(None)
	encoder, package = ENCODERS[sound_format]
	if tags is not None:
		encoder = TAGGED_ENCODERS[sound_format]
	buffers = max(1, round(seconds * FREQUENCY / SAMPLES_PER_BUFFER))
	try:
		pipeline = Gst.parse_launch(
			f"audiotestsrc wave={wave} num-buffers={buffers} samplesperbuffer={SAMPLES_PER_BUFFER}"
			f" ! audio/x-raw,rate={FREQUENCY},channels=1 ! audioconvert ! {encoder} ! filesink name=fichier"
		)
	except gi.repository.GLib.Error as error:
		raise RuntimeError(f"encodeur {sound_format} indisponible ({error.message}) : installer {package}") from error
	assert isinstance(pipeline, Gst.Bin)
	file = pipeline.get_by_name("fichier")
	assert file is not None
	file.set_property("location", str(path))
	if tags is not None:
		carrier = pipeline.get_by_name("tags")
		list_ = Gst.TagList.new_from_string(tags)
		assert (carrier is not None) and (list_ is not None)
		# L'élément nommé « tags » implémente l'interface GstTagSetter (voir TAGGED_ENCODERS).
		cast(Gst.TagSetter, carrier).merge_tags(list_, Gst.TagMergeMode.REPLACE)
	pipeline.set_state(Gst.State.PLAYING)
	bus = pipeline.get_bus()
	assert bus is not None
	message = bus.timed_pop_filtered(60 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
	pipeline.set_state(Gst.State.NULL)
	assert (message is not None) and (message.type == Gst.MessageType.EOS), f"génération de {path} impossible"
	return path


SILENCES: tuple[tuple[float, float], ...] = (
	(0.5, 0.0),
	(1.0, 0.5),
	(0.25, 0.003),
	(0.25, 0.0),
)
"""Le fichier silences.flac, morceau par morceau : durée en secondes et amplitude crête de la sinusoïde (1 = 0 dB) ;
détection de silence (https://github.com/dascritch/machincast/issues/146). Une demi-seconde de silence, une seconde à
-6 dB, un quart de seconde à -50,5 dB, puis un quart de seconde de silence : au seuil de -40 dB, une demi-seconde de
silence au début et à la fin ; au seuil de -60 dB, un quart de seconde à la fin."""


def generate_silences(
	path: Path, pieces: tuple[tuple[float, float], ...] = SILENCES, frequency: int = FREQUENCY
) -> Path:
	"""Écrit en FLAC un son mono fait de morceaux de sinusoïde (SILENCES par défaut), chacun aligné sur l'échantillon :
	durée en secondes et amplitude crête. frequence : d'échantillonnage, plus basse pour un long fichier vite écrit."""
	Gst.init(None)
	samples = bytearray()
	for seconds, amplitude in pieces:
		for index in range(round(seconds * frequency)):
			value = round(amplitude * 32767 * math.sin(2 * math.pi * 440 * index / frequency))
			samples += struct.pack("<h", value)
	pipeline = Gst.parse_launch(
		f"appsrc name=source format=time caps=audio/x-raw,format=S16LE,layout=interleaved,rate={frequency},channels=1"
		" ! audioconvert ! flacenc ! filesink name=fichier"
	)
	assert isinstance(pipeline, Gst.Bin)
	source, file = pipeline.get_by_name("source"), pipeline.get_by_name("fichier")
	assert (source is not None) and (file is not None)
	file.set_property("location", str(path))
	pipeline.set_state(Gst.State.PLAYING)
	buffer = Gst.Buffer.new_wrapped(bytes(samples))
	buffer.pts = 0
	buffer.duration = round(len(samples) / 2 / frequency * Gst.SECOND)
	source.emit("push-buffer", buffer)
	source.emit("end-of-stream")
	bus = pipeline.get_bus()
	assert bus is not None
	message = bus.timed_pop_filtered(60 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
	pipeline.set_state(Gst.State.NULL)
	assert (message is not None) and (message.type == Gst.MessageType.EOS), f"génération de {path} impossible"
	return path


if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO, format="{message}", style="{")
	SOUND_FILES.mkdir(exist_ok=True)
	for sound_format in ENCODERS:
		path = generate_sound(sound_format, SOUND_FILES / f"sain.{sound_format}")
		logging.info(f"{path.name} : {path.stat().st_size} octets")
	for sound_format in TAGGED_ENCODERS:
		path = generate_sound(sound_format, SOUND_FILES / f"tags.{sound_format}", tags=TEST_TAGS)
		logging.info(f"{path.name} : {path.stat().st_size} octets")
	path = generate_silences(SOUND_FILES / "silences.flac")
	logging.info(f"{path.name} : {path.stat().st_size} octets")
	path = generate_sound("mp3", SOUND_FILES / "muet.mp3", wave="silence")
	logging.info(f"{path.name} : {path.stat().st_size} octets")
