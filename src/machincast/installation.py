"""Étapes d'installation appelées par install.sh (https://github.com/dascritch/machincast/issues/40).

	python -m machincast.installation bases     --config machincast.toml   socket, base de production, base de test
	python -m machincast.installation migrer    --config machincast.toml   schéma appliqué aux deux bases
	python -m machincast.installation verifier  --config machincast.toml   décodeurs GStreamer et sortie audio

install.sh enchaîne les commandes système (apt, sudo, psql, liens) ; ce module porte ce qui se teste : la lecture
de la configuration, les migrations et la vérification des greffons GStreamer.
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass

import gi
import psycopg

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from machincast.audio import GREFFONS, Greffon, SortieAudioIndisponible, creer_sortie  # noqa: E402
from machincast.base import appliquer_migrations, url_yoyo  # noqa: E402
from machincast.cli import lancer  # noqa: E402
from machincast.configuration import Configuration, SortieAudio  # noqa: E402

EXECUTABLE = "machincast.installation"
DESCRIPTION = "Étapes d'installation de MachinCast, appelées par install.sh."
CODE_ECHEC = 1

# Nom explicite : lancé par python -m, ce module s'appelle __main__, hors du journal « machincast ».
journal = logging.getLogger("machincast.installation")


@dataclass(frozen=True)
class Exigence:
	"""Un élément GStreamer d'un type donné doit savoir lire ces capacités."""

	type_element: int
	capacites: str


@dataclass(frozen=True)
class FormatSonore:
	exigences: tuple[Exigence, ...]
	paquet: str
	"""Paquet Ubuntu qui fournit les éléments, parmi les prérequis de CLAUDE.md."""


_DECODEUR = Gst.ELEMENT_FACTORY_TYPE_DECODER
_DEMULTIPLEXEUR = Gst.ELEMENT_FACTORY_TYPE_DEMUXER

FORMATS: dict[str, FormatSonore] = {
	"mp3": FormatSonore(
		(Exigence(_DECODEUR, "audio/mpeg, mpegversion=(int)1, layer=(int)3"),), "gstreamer1.0-plugins-good"
	),
	"m4a": FormatSonore(
		(Exigence(_DEMULTIPLEXEUR, "audio/x-m4a"), Exigence(_DECODEUR, "audio/mpeg, mpegversion=(int)4")),
		"gstreamer1.0-plugins-bad",
	),
	"ogg": FormatSonore(
		(Exigence(_DEMULTIPLEXEUR, "application/ogg"), Exigence(_DECODEUR, "audio/x-vorbis")),
		"gstreamer1.0-plugins-base",
	),
	"flac": FormatSonore((Exigence(_DECODEUR, "audio/x-flac"),), "gstreamer1.0-plugins-good"),
	"wav": FormatSonore((Exigence(_DEMULTIPLEXEUR, "audio/x-wav"),), "gstreamer1.0-plugins-good"),
	"aiff": FormatSonore((Exigence(_DEMULTIPLEXEUR, "audio/x-aiff"),), "gstreamer1.0-plugins-bad"),
}
"""Formats de la spec § 6.2, et ce que decodebin doit trouver pour les décoder."""


@dataclass(frozen=True)
class Manque:
	element: str
	"""Format sonore ou sortie audio qui ne peut pas fonctionner."""
	paquet: str


def _satisfaite(exigence: Exigence) -> bool:
	"""Vrai si un élément utilisable par decodebin (rang au moins MARGINAL) lit ces capacités."""
	capacites = Gst.Caps.from_string(exigence.capacites)
	assert capacites is not None
	fabriques = Gst.ElementFactory.list_get_elements(exigence.type_element, Gst.Rank.MARGINAL)
	return any(fabrique.can_sink_any_caps(capacites) for fabrique in fabriques)


def verifier_decodeurs() -> list[Manque]:
	"""Formats de la spec qu'aucun décodeur GStreamer installé ne sait lire, avec le paquet à installer."""
	Gst.init(None)
	return [
		Manque(nom, format_sonore.paquet)
		for nom, format_sonore in FORMATS.items()
		if not all(_satisfaite(exigence) for exigence in format_sonore.exigences)
	]


def verifier_sortie(configuration: Configuration, greffons: dict[SortieAudio, Greffon] = GREFFONS) -> list[Manque]:
	"""Crée l'élément de la sortie audio configurée, sans jouer de son : aucun son ne part à l'antenne."""
	audio = configuration.audio
	try:
		creer_sortie(audio.sortie, audio.peripherique, greffons)
	except SortieAudioIndisponible:
		return [Manque(f"sortie audio {audio.sortie}", greffons[audio.sortie].paquet)]
	return []


def _bases(configuration: Configuration) -> int:
	# Données lues par install.sh, une valeur par ligne : ce n'est pas un message, d'où l'écriture directe.
	base = configuration.base
	sys.stdout.write(f"{base.socket}\n{base.production}\n{base.test}\n")
	return 0


def _migrer(configuration: Configuration) -> int:
	base = configuration.base
	for nom in (base.production, base.test):
		try:
			appliquer_migrations(url_yoyo(base.socket, nom))
		except psycopg.OperationalError as erreur:
			journal.error(f"base de données injoignable ({nom} par {base.socket}) : {erreur}")
			return CODE_ECHEC
		except psycopg.errors.InsufficientPrivilege as erreur:
			journal.error(
				f"droits insuffisants pour appliquer le schéma dans la base {nom}, qui appartient sans doute à un autre"
				f" rôle PostgreSQL : {erreur}"
			)
			return CODE_ECHEC
		journal.info(f"schéma à jour dans la base {nom}")
	return 0


def _verifier(configuration: Configuration) -> int:
	manques = verifier_decodeurs() + verifier_sortie(configuration)
	for manque in manques:
		journal.error(f"{manque.element} : greffon GStreamer absent, installer {manque.paquet}")
	if manques:
		return CODE_ECHEC
	journal.info("décodeurs et sortie audio disponibles")
	return 0


ACTIONS = {"bases": _bases, "migrer": _migrer, "verifier": _verifier}


def _options(analyseur: argparse.ArgumentParser) -> None:
	analyseur.add_argument("action", choices=sorted(ACTIONS), help="étape d'installation à exécuter")


def _executer(configuration: Configuration, options: argparse.Namespace) -> int:
	return ACTIONS[options.action](configuration)


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, _executer, _options)


if __name__ == "__main__":
	raise SystemExit(main())
