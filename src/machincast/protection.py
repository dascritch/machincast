"""Protection des fichiers sonores (https://github.com/dascritch/machincast/issues/96).

Directive très importante : MachinCast ne supprime jamais un fichier sonore, quels que soient les changements de son
entrée dans la table sonores. Il ne le renomme, ne le déplace, ne le remplace ni ne l'écrit jamais non plus.

- Les sorties (CSV, .pls, HTML) et la socket d'état n'écrivent jamais un chemin qui porte l'extension d'un fichier
  sonore : la configuration le refuse, et verifier_ecriture le refuse à l'écriture. Les fichiers de la simulation
  finissent toujours par .csv, .pls ou .html.
- Dans le code, toute suppression, tout renommage ou tout remplacement de fichier porte, sur sa ligne ou celle du
  dessus, la justification MARQUE suivie du fichier concerné, créé par MachinCast. Un scénario de protection.feature
  refuse toute autre suppression dans src, bin et install.sh (injustifiees).
"""

import re
from pathlib import Path

EXTENSIONS_SONORES = frozenset({".mp3", ".m4a", ".aac", ".ogg", ".flac", ".wav", ".aiff", ".aif"})
"""Extensions des formats de la spec § 6.2, en minuscules : celles des fichiers que l'indexeur enregistre."""

MARQUE = "fichier de MachinCast :"
"""Justification d'une suppression, d'un renommage ou d'un remplacement de fichier dans le code."""

_PYTHON = re.compile(
	r"\.(?:unlink|rmdir|rename)\(|\b(?:os\.(?:remove|unlink|rmdir|removedirs|rename|renames|replace)|shutil\.(?:rmtree|move))\("
)
_BASH = re.compile(r"(?:^|[\s;&|(`'\"])(?:rm|rmdir|mv|unlink|shred)\s")


class FichierSonoreProtege(PermissionError):
	"""MachinCast n'écrit jamais dans un fichier sonore, et ne le remplace jamais."""


def est_fichier_sonore(chemin: Path) -> bool:
	return chemin.suffix.lower() in EXTENSIONS_SONORES


def verifier_ecriture(chemin: Path) -> None:
	"""À appeler avant d'écrire, de remplacer ou d'effacer un fichier : refuse un fichier sonore."""
	if est_fichier_sonore(chemin):
		raise FichierSonoreProtege(f"{chemin} : fichier sonore protégé, MachinCast n'y écrit jamais")


def injustifiees(texte: str, bash: bool = False) -> list[tuple[int, str]]:
	"""Lignes qui suppriment, renomment ou remplacent un fichier sans la justification MARQUE (numérotées dès 1)."""
	motif = _BASH if bash else _PYTHON
	fautes = []
	precedente = ""
	for numero, ligne in enumerate(texte.splitlines(), start=1):
		if motif.search(ligne) and MARQUE not in ligne and MARQUE not in precedente:
			fautes.append((numero, ligne))
		precedente = ligne
	return fautes
