"""Protection des fichiers sonores (https://github.com/dascritch/machincast/issues/96).

Directive très importante : MachinCast ne supprime jamais un fichier sonore, quels que soient les changements de son
entrée dans la table sonores. Il ne le renomme, ne le déplace, ne le remplace ni ne l'écrit jamais non plus.

- Les sorties (CSV, .pls, HTML) et la socket d'état n'écrivent jamais un chemin qui porte l'extension d'un fichier
  sonore : la configuration le refuse, et check_writing le refuse à l'écriture. Les fichiers de la simulation
  finissent toujours par .csv, .pls ou .html.
- Dans le code, toute suppression, tout renommage ou tout remplacement de fichier porte, sur sa ligne ou celle du
  dessus, la justification MARQUE suivie du fichier concerné, créé par MachinCast. Un scénario de protection.feature
  refuse toute autre suppression dans src, bin et install.sh (injustifiees).
"""

import re
from pathlib import Path

from machincast.i18n import _

INDEXED_EXTENSIONS = frozenset({".mp3", ".m4a", ".aac", ".ogg", ".flac", ".wav"})
"""Extensions des formats de la spec § 6.2, en minuscules : celles des fichiers que l'indexeur enregistre."""

SOUND_EXTENSIONS = INDEXED_EXTENSIONS | {".aiff", ".aif"}
"""Extensions des fichiers sonores protégés, en minuscules : les formats de la spec, et l'AIFF, que l'indexeur ignore
depuis https://github.com/dascritch/machincast/issues/284, mais qui reste un fichier sonore, jamais écrit."""

MARK = "fichier de MachinCast :"
"""Justification d'une suppression, d'un renommage ou d'un remplacement de fichier dans le code."""
CONSENT_MARK = "sonore déplacé avec accord :"
"""La seule exception à https://github.com/dascritch/machincast/issues/96 : le déplacement d'un sonore hors d'un
répertoire personnel, accepté explicitement à install.sh --service (https://github.com/dascritch/machincast/issues/381,
machincast.personal)."""

_PYTHON = re.compile(
	r"\.(?:unlink|rmdir|rename)\(|\b(?:os\.(?:remove|unlink|rmdir|removedirs|rename|renames|replace)|shutil\.(?:rmtree|move))\("
)
_BASH = re.compile(r"(?:^|[\s;&|(`'\"])(?:rm|rmdir|mv|unlink|shred)\s")


class ProtectedSoundFile(PermissionError):
	"""MachinCast n'écrit jamais dans un fichier sonore, et ne le remplace jamais."""


def is_sound_file(path: Path) -> bool:
	return path.suffix.lower() in SOUND_EXTENSIONS


def check_writing(path: Path) -> None:
	"""À appeler avant d'écrire, de remplacer ou d'effacer un fichier : refuse un fichier sonore."""
	if is_sound_file(path):
		raise ProtectedSoundFile(_("{path}: protected sound file, MachinCast never writes to it").format(path=path))


def unjustified(text: str, bash: bool = False) -> list[tuple[int, str]]:
	"""Lignes qui suppriment, renomment ou remplacent un fichier sans la justification MARQUE (numérotées dès 1)."""
	pattern = _PYTHON
	if bash:
		pattern = _BASH
	faults = []
	previous = ""
	for number, line in enumerate(text.splitlines(), start=1):
		justified = (MARK in line) or (MARK in previous) or (CONSENT_MARK in line) or (CONSENT_MARK in previous)
		if (pattern.search(line)) and (not justified):
			faults.append((number, line))
		previous = line
	return faults
