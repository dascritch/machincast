"""Date de modification et taille d'un fichier sonore : ce qui dit qu'il a changé depuis sa dernière vérification
(https://github.com/dascritch/machincast/issues/10).

L'indexeur s'en sert pour décider de redécoder un fichier en indexation rapide, et Machin player pour savoir si le
prochain sonore doit être analysé avant d'être joué (https://github.com/dascritch/machincast/issues/181). Ce module
ne fait que lire l'état du fichier sur le disque, jamais le fichier lui-même.
"""

from datetime import UTC, datetime
from pathlib import Path


def file_state(path: Path) -> tuple[datetime, int] | None:
	"""Date de modification et taille du fichier, ou None s'il est introuvable."""
	try:
		state = path.stat()
	except OSError:
		return None
	return datetime.fromtimestamp(state.st_mtime, tz=UTC), state.st_size


def modified(path: Path, modified_at: object, size: object) -> bool:
	"""Le fichier a-t-il changé depuis sa dernière vérification (https://github.com/dascritch/machincast/issues/10) ?

	Sa date de modification ou sa taille diffère de celles enregistrées, toujours ensemble. Un sonore jamais vérifié
	n'en a pas, et un fichier introuvable n'a rien à comparer : ni l'un ni l'autre n'est dit modifié.
	"""
	if modified_at is None:
		return False
	file = file_state(path)
	return (file is not None) and (file != (modified_at, size))
