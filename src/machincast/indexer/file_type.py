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

SOUND_CONTAINERS = frozenset({"video/mp4", "application/ogg"})
"""Types de conteneurs qui portent du son : un .m4a est un MP4, un Ogg peut se dire application/ogg."""
UNDETERMINED = frozenset({"application/octet-stream", "inode/x-empty"})
"""Ce que libmagic répond quand il ne reconnaît rien : le décodage dira si c'est du son."""


class Kind(Enum):
	SOUND = "sonore"
	UNDETERMINED = "indéterminée"
	NON_SOUND = "non sonore"


def type_mime(path: Path) -> str | None:
	"""Le type MIME du fichier, comme le donne libmagic ; None s'il est introuvable ou illisible, ce que le décodage
	dira."""
	try:
		return str(magic.from_file(str(path), mime=True))
	except (OSError, magic.MagicException):
		return None


def kind(file_type: str) -> Kind:
	if (file_type.startswith("audio/")) or (file_type in SOUND_CONTAINERS):
		return Kind.SOUND
	if file_type in UNDETERMINED:
		return Kind.UNDETERMINED
	return Kind.NON_SOUND
