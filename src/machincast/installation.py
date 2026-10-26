"""Étapes d'installation appelées par install.sh (https://github.com/dascritch/machincast/issues/40).

	python -m machincast.installation bases     --config machincast.toml   socket, base de production, base de test
	python -m machincast.installation migrer    --config machincast.toml   schéma appliqué aux deux bases
	python -m machincast.installation verifier  --config machincast.toml   décodeurs GStreamer et sortie audio
	python -m machincast.installation unite     --config machincast.toml   unité systemd du service de lecture
	python -m machincast.installation regle     --config machincast.toml   règle polkit qui le pilote
	python -m machincast.installation unite-purge    --config machincast.toml   unité systemd de la purge
	python -m machincast.installation minuteur-purge --config machincast.toml   son minuteur, chaque jour à midi
	python -m machincast.installation raccourci --config machincast.toml   raccourci de l'interface (.desktop)
	python -m machincast.installation peripheriques --config machincast.toml   périphériques de sortie du poste

peripheriques n'est pas appelé par install.sh : il aide à trouver les identifiants à recopier dans audio.peripherique
et audio.preecoute (https://github.com/dascritch/machincast/issues/116).

install.sh enchaîne les commandes système (apt, sudo, psql, liens) ; ce module porte ce qui se teste : la lecture
de la configuration, les migrations, la vérification des greffons GStreamer, et le texte de l'unité systemd et de la
règle polkit du service de lecture (https://github.com/dascritch/machincast/issues/22), et ceux de l'unité et du
minuteur de la purge quotidienne (https://github.com/dascritch/machincast/issues/268), qu'install.sh --service
installe, et celui du raccourci de l'interface, qu'install.sh met dans le menu des applications du compte et, sur
demande, sur son bureau (https://github.com/dascritch/machincast/issues/62).
"""

import argparse
import grp
import logging
import os
import pwd
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import gi
import psycopg

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from machincast import audio as sorties_audio  # noqa: E402
from machincast import raccourci as rediger_le_raccourci  # noqa: E402
from machincast.audio import GREFFONS, Greffon, SortieAudioIndisponible, creer_sortie  # noqa: E402
from machincast.base import appliquer_migrations, url_yoyo  # noqa: E402
from machincast.cli import lancer  # noqa: E402
from machincast.configuration import REPERTOIRE_PROJET, Configuration, SortieAudio  # noqa: E402
from machincast.service import UNITE  # noqa: E402

EXECUTABLE = "machincast.installation"
DESCRIPTION = "Étapes d'installation de MachinCast, appelées par install.sh."
CODE_ECHEC = 1
UNITE_PURGE = "machincast-purge.service"
"""L'unité de la purge, Machin purge : les mêmes noms dans install.sh."""
MINUTEUR_PURGE = "machincast-purge.timer"
HEURE_PURGE = "*-*-* 12:00:00"
"""Chaque jour à midi : en journée, quand le poste de l'antenne est allumé."""

# Nom explicite : lancé par python -m, ce module s'appelle __main__, hors du journal « machincast ».
journal = logging.getLogger("machincast.installation")


@dataclass(frozen=True)
class Exigence:
	"""Un élément GStreamer d'un type donné doit savoir lire ces capacités."""

	type_element: int
	capacites: str
	paquet: str | None = None
	"""Paquet qui fournit l'élément, quand ce n'est pas celui du format."""


@dataclass(frozen=True)
class FormatSonore:
	exigences: tuple[Exigence, ...]
	paquet: str
	"""Paquet Ubuntu qui fournit les éléments, parmi les prérequis de CLAUDE.md."""


_DECODEUR = Gst.ELEMENT_FACTORY_TYPE_DECODER
_DEMULTIPLEXEUR = Gst.ELEMENT_FACTORY_TYPE_DEMUXER
_ANALYSEUR = Gst.ELEMENT_FACTORY_TYPE_PARSER

FORMATS: dict[str, FormatSonore] = {
	"mp3": FormatSonore(
		(Exigence(_DECODEUR, "audio/mpeg, mpegversion=(int)1, layer=(int)3"),), "gstreamer1.0-plugins-good"
	),
	"m4a": FormatSonore(
		(Exigence(_DEMULTIPLEXEUR, "audio/x-m4a"), Exigence(_DECODEUR, "audio/mpeg, mpegversion=(int)4")),
		"gstreamer1.0-plugins-bad",
	),
	# AAC brut en trames ADTS (.aac) : aacparse (plugins-good) découpe les trames, le décodeur est celui du M4A.
	"aac": FormatSonore(
		(
			Exigence(
				_ANALYSEUR, "audio/mpeg, mpegversion=(int)4, stream-format=(string)adts", "gstreamer1.0-plugins-good"
			),
			Exigence(_DECODEUR, "audio/mpeg, mpegversion=(int)4"),
		),
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
	"""Format sonore, protocole de stream ou sortie audio qui ne peut pas fonctionner."""
	paquet: str


def _satisfaite(exigence: Exigence) -> bool:
	"""Vrai si un élément utilisable par decodebin (rang au moins MARGINAL) lit ces capacités."""
	capacites = Gst.Caps.from_string(exigence.capacites)
	assert capacites is not None
	fabriques = Gst.ElementFactory.list_get_elements(exigence.type_element, Gst.Rank.MARGINAL)
	return any(fabrique.can_sink_any_caps(capacites) for fabrique in fabriques)


def verifier_decodeurs() -> list[Manque]:
	"""Formats de la spec qu'aucun décodeur GStreamer installé ne sait lire, avec le paquet à installer.

	Le paquet nommé est celui du premier élément manquant.
	"""
	Gst.init(None)
	manques = []
	for nom, format_sonore in FORMATS.items():
		absente = next((e for e in format_sonore.exigences if not _satisfaite(e)), None)
		if absente is not None:
			manques.append(Manque(nom, (absente.paquet) or (format_sonore.paquet)))
	return manques


PROTOCOLES_STREAMS = {"http": "gstreamer1.0-plugins-good", "https": "gstreamer1.0-plugins-good"}
"""Protocoles des streams (https://github.com/dascritch/machincast/issues/16), et le paquet de leur source
(souphttpsrc)."""


def verifier_streams() -> list[Manque]:
	"""Protocoles de stream qu'aucune source GStreamer installée ne sait lire, avec le paquet à installer."""
	Gst.init(None)
	sources = [
		f
		for f in Gst.ElementFactory.list_get_elements(Gst.ELEMENT_FACTORY_TYPE_SRC, Gst.Rank.MARGINAL)
		if f.get_uri_type() == Gst.URIType.SRC
	]
	lus = {protocole for f in sources for protocole in ((f.get_uri_protocols()) or ([]))}
	return [Manque(f"stream {p}", paquet) for p, paquet in PROTOCOLES_STREAMS.items() if p not in lus]


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
	manques = verifier_decodeurs() + verifier_streams() + verifier_sortie(configuration)
	for manque in manques:
		journal.error(f"{manque.element} : greffon GStreamer absent, installer {manque.paquet}")
	if manques:
		return CODE_ECHEC
	journal.info("décodeurs, source des streams et sortie audio disponibles")
	return 0


@dataclass(frozen=True)
class Compte:
	"""Le compte de MachinCast, celui qui l'installe : le service tourne sous lui, avec sa session audio."""

	nom: str
	groupe: str
	uid: int

	@classmethod
	def courant(cls) -> "Compte":
		entree = pwd.getpwuid(os.getuid())
		return cls(entree.pw_name, grp.getgrgid(entree.pw_gid).gr_name, entree.pw_uid)


def unite_systemd(compte: Compte, repertoire: Path = REPERTOIRE_PROJET) -> str:
	"""L'unité du service de lecture : Machin lecture, sous le compte de MachinCast, relancé après un plantage. Son
	répertoire d'exécution est celui de la session du compte, gardée active au démarrage (loginctl enable-linger) :
	PipeWire ou PulseAudio, et la socket d'état que lit l'interface. Ses messages vont dans journald."""
	return f"""# Service de diffusion de MachinCast (https://github.com/dascritch/machincast/issues/22).
# Installé par install.sh --service ; ne pas modifier ici, relancer install.sh --service.

[Unit]
Description=MachinCast : diffusion de l'antenne (Machin lecture)
Wants=network-online.target
After=network-online.target postgresql.service sound.target

[Service]
Type=simple
User={compte.nom}
Group={compte.groupe}
WorkingDirectory={repertoire}
Environment=XDG_RUNTIME_DIR=/run/user/{compte.uid}
ExecStart={repertoire}/bin/Machin lecture
Restart=on-failure
RestartSec=5
KillSignal=SIGTERM
TimeoutStopSec=15
SyslogIdentifier=machincast

[Install]
WantedBy=multi-user.target
"""


def unite_purge(compte: Compte, repertoire: Path = REPERTOIRE_PROJET) -> str:
	"""L'unité de la purge : Machin purge, une fois, sous le compte de MachinCast, propriétaire de la base. Son
	minuteur la lance ; elle n'a pas de section Install. Ses messages vont dans journald."""
	return f"""# Purge de la base de MachinCast (https://github.com/dascritch/machincast/issues/268).
# Installé par install.sh --service ; ne pas modifier ici, relancer install.sh --service.

[Unit]
Description=MachinCast : purge de la base de données (Machin purge)
After=postgresql.service

[Service]
Type=oneshot
User={compte.nom}
Group={compte.groupe}
WorkingDirectory={repertoire}
ExecStart={repertoire}/bin/Machin purge
SyslogIdentifier=machincast-purge
"""


def minuteur_purge() -> str:
	"""Le minuteur de la purge : chaque jour à midi ; une purge manquée, poste éteint, se fait à son démarrage."""
	return f"""# Purge quotidienne de la base de MachinCast (https://github.com/dascritch/machincast/issues/268).
# Installé par install.sh --service ; ne pas modifier ici, relancer install.sh --service.

[Unit]
Description=MachinCast : purge quotidienne de la base, à midi

[Timer]
OnCalendar={HEURE_PURGE}
Persistent=true
Unit={UNITE_PURGE}

[Install]
WantedBy=timers.target
"""


def regle_polkit(compte: Compte) -> str:
	"""La règle polkit du service de lecture : son compte le démarre, l'arrête ou le redémarre, avec
	l'authentification d'un administrateur ; rien d'autre, ni sur une autre unité."""
	return f"""// Pilotage du service de diffusion de MachinCast (https://github.com/dascritch/machincast/issues/22).
// Installé par install.sh --service ; ne pas modifier ici, relancer install.sh --service.
polkit.addRule(function (action, subject) {{
	if ((action.id == "org.freedesktop.systemd1.manage-units") && (action.lookup("unit") == "{UNITE}")
		&& (["start", "stop", "restart"].indexOf(action.lookup("verb")) >= 0) && (subject.user == "{compte.nom}")) {{
		return polkit.Result.AUTH_ADMIN;
	}}
	return polkit.Result.NOT_HANDLED;
}});
"""


ICONE = rediger_le_raccourci.ICONE


def raccourci(repertoire: Path = REPERTOIRE_PROJET, icone: Path | None = None) -> str:
	"""Le raccourci de l'interface (machincast.raccourci), avec l'icône choisie s'il y en a une qui existe
	(https://github.com/dascritch/machincast/issues/111)."""
	return rediger_le_raccourci.rediger(repertoire, icone)


def _unite(_configuration: Configuration) -> int:
	# Le texte de l'unité, qu'install.sh installe : ce n'est pas un message, d'où l'écriture directe.
	sys.stdout.write(unite_systemd(Compte.courant()))
	return 0


def _unite_purge(_configuration: Configuration) -> int:
	sys.stdout.write(unite_purge(Compte.courant()))
	return 0


def _minuteur_purge(_configuration: Configuration) -> int:
	sys.stdout.write(minuteur_purge())
	return 0


def _regle(_configuration: Configuration) -> int:
	sys.stdout.write(regle_polkit(Compte.courant()))
	return 0


def _raccourci(configuration: Configuration) -> int:
	sys.stdout.write(raccourci(icone=configuration.interface.icone))
	return 0


def lister_peripheriques(configuration: Configuration) -> str:
	"""Les périphériques de sortie de la sortie configurée, un par ligne : identifiant, nom, et leur rôle dans la
	configuration (https://github.com/dascritch/machincast/issues/116). Sans aucun, tout ce que voit GStreamer, pour
	comprendre pourquoi."""
	audio = configuration.audio
	roles = {audio.peripherique: "antenne", audio.preecoute: "pré-écoute"}
	trouves = sorties_audio.peripheriques(audio.sortie)
	lignes = [f"{p.identifiant}\t{p.nom}\t{roles.get(p.identifiant, '')}".rstrip("\t") for p in trouves]
	if trouves:
		return "\n".join(lignes) + "\n"
	lignes = [f"aucun périphérique de sortie « {audio.sortie} » ; périphériques de sortie vus par GStreamer :"]
	for appareil in sorties_audio.appareils():
		nom = sorties_audio.identifiant(appareil)
		lignes.append(
			f"{sorties_audio.type_d_appareil(appareil)}\t{appareil.get_display_name()}\t{(nom) or ('sans identifiant')}"
		)
	return "\n".join(lignes) + "\n"


def _peripheriques(configuration: Configuration) -> int:
	# Une liste à lire, ou à recopier dans audio.peripherique et audio.preecoute : écrite telle quelle.
	sys.stdout.write(lister_peripheriques(configuration))
	return 0


ACTIONS = {
	"bases": _bases,
	"migrer": _migrer,
	"minuteur-purge": _minuteur_purge,
	"peripheriques": _peripheriques,
	"raccourci": _raccourci,
	"regle": _regle,
	"unite": _unite,
	"unite-purge": _unite_purge,
	"verifier": _verifier,
}


def _options(analyseur: argparse.ArgumentParser) -> None:
	analyseur.add_argument("action", choices=sorted(ACTIONS), help="étape d'installation à exécuter")


def _executer(configuration: Configuration, options: argparse.Namespace) -> int:
	return ACTIONS[options.action](configuration)


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, _executer, _options)


if __name__ == "__main__":
	raise SystemExit(main())
