"""Ce que Machin indexer dit aux plugins de ce qu'il trouve (https://github.com/dascritch/machincast/issues/590).

Les plugins chargés (machincast.plugins.active) abonnés à ces points d'extension (machincast.plugins.points.CORE) sont
prévenus sans être attendus : notify les appelle dans le fil des plugins, et consigne l'erreur de l'un d'eux sans
arrêter ni le parcours ni la vérification. Les données sont faites pour être sérialisées telles quelles : heures en
ISO 8601, durées et positions en secondes, identifiants en entiers.

- SOUND_SPOTTED : le parcours vient d'enregistrer un nouveau fichier, à l'état aperçu (spotted).
- SOUND_DETAILED : la vérification vient d'écrire ce qu'elle a trouvé d'un sonore (detailed).
"""

from datetime import timedelta
from typing import Any

from machincast import plugins

SOUND_SPOTTED = "indexer.sound_spotted"
SOUND_DETAILED = "indexer.sound_detailed"


def _seconds(duration: object) -> float | None:
	if isinstance(duration, timedelta):
		return duration.total_seconds()
	return None


def spotted(sound: int, location: str, bank: int, bank_name: str) -> None:
	"""Un nouveau sonore, et la banque dont le répertoire l'a fait trouver."""
	plugins.active().points.notify(
		SOUND_SPOTTED, {"sound": sound, "location": location, "bank": bank, "bank_name": bank_name}
	)


def detailed(sound: int, location: str, details: dict[str, Any]) -> None:
	"""Le sonore examiné : son état avant et après, et ses champs, tels qu'écrits en base. details donne previous_state,
	state, duration, artist, title, metadata, file_type, detected_start, detected_end, audited et problem."""
	data = {"sound": sound, "location": location, **details}
	for key in ("duration", "detected_start", "detected_end"):
		data[key] = _seconds(data.get(key))
	plugins.active().points.notify(SOUND_DETAILED, data)
