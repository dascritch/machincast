"""Fichiers sonores de test (https://github.com/dascritch/machincast/issues/7).

Les fichiers de tests/fichiers-sonores/ sont versionnés : une seconde de sinusoïde en mono, la plus petite
taille utile, dans chacun des formats de la spec. Les scénarios en copient un dans leur répertoire temporaire,
puis peuvent le tronquer ou le corrompre ; le dépôt n'est jamais modifié.

Pour les régénérer (encodeurs GStreamer nécessaires) : python -m tests.sons
"""

import logging
import shutil
from pathlib import Path

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
	"aiff": ("aiffmux", "gstreamer1.0-plugins-bad"),
}


def copie_de_test(format_sonore: str, repertoire: Path) -> Path:
	"""Copie le fichier sonore de test sain du format demandé dans le répertoire donné."""
	source = FICHIERS_SONORES / f"sain.{format_sonore}"
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


def generer_son(format_sonore: str, chemin: Path, secondes: float = DUREE_SECONDES) -> Path:
	"""Écrit une sinusoïde mono de la durée donnée (à un tampon près) dans le format demandé."""
	Gst.init(None)
	encodeur, paquet = ENCODEURS[format_sonore]
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
	pipeline.set_state(Gst.State.PLAYING)
	bus = pipeline.get_bus()
	assert bus is not None
	message = bus.timed_pop_filtered(60 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
	pipeline.set_state(Gst.State.NULL)
	assert message is not None and message.type == Gst.MessageType.EOS, f"génération de {chemin} impossible"
	return chemin


if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO, format="%(message)s")
	FICHIERS_SONORES.mkdir(exist_ok=True)
	for format_sonore in ENCODEURS:
		chemin = generer_son(format_sonore, FICHIERS_SONORES / f"sain.{format_sonore}")
		logging.info("%s : %d octets", chemin.name, chemin.stat().st_size)
