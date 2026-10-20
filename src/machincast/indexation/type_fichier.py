"""Type réel du fichier d'un sonore, lu par libmagic (https://github.com/dascritch/machincast/issues/121, spec § 6.1).

L'extension dit ce qu'un fichier prétend être, son contenu ce qu'il est : un texte ou une image renommés en .mp3 ne
sont pas du son. libmagic lit les premiers octets du fichier, sans le décoder ni le modifier
(https://github.com/dascritch/machincast/issues/96).

- Un type audio/…, ou un conteneur sonore (video/mp4 d'un .m4a, application/ogg), est sonore.
- Un type indéterminé (données brutes, fichier vide) ne dit rien : le décodage tranche.
- Tout autre type (texte, image, PDF, archive…) n'est pas supporté.
"""

from enum import Enum
from pathlib import Path

import magic

CONTENEURS_SONORES = frozenset({"video/mp4", "application/ogg"})
"""Types de conteneurs qui portent du son : un .m4a est un MP4, un Ogg peut se dire application/ogg."""
INDETERMINES = frozenset({"application/octet-stream", "inode/x-empty"})
"""Ce que libmagic répond quand il ne reconnaît rien : le décodage dira si c'est du son."""


class Nature(Enum):
	SONORE = "sonore"
	INDETERMINEE = "indéterminée"
	NON_SONORE = "non sonore"


def type_mime(chemin: Path) -> str | None:
	"""Le type MIME du fichier, comme le donne libmagic ; None s'il est introuvable ou illisible, ce que le décodage
	dira."""
	try:
		return str(magic.from_file(str(chemin), mime=True))
	except (OSError, magic.MagicException):
		return None


def nature(type_du_fichier: str) -> Nature:
	if (type_du_fichier.startswith("audio/")) or (type_du_fichier in CONTENEURS_SONORES):
		return Nature.SONORE
	if type_du_fichier in INDETERMINES:
		return Nature.INDETERMINEE
	return Nature.NON_SONORE
