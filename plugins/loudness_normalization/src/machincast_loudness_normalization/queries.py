"""Les requêtes de la normalisation du niveau (https://github.com/dascritch/machincast/issues/43).

L'ajustement manuel d'un sonore est dans sa colonne properties, sous la clé du plugin ; sans ajustement, la clé en est
retirée, sans toucher aux autres, ni à la mesure du cœur, sous la clé « loudness ».
"""

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from machincast_loudness_normalization.rule import KEY

Connection = psycopg.Connection[Any]


def properties(connection: Connection, sound: int) -> dict[str, Any]:
	found = connection.execute("SELECT properties FROM sounds WHERE id = %s", (sound,)).fetchone()
	if (found is None) or (not isinstance(found[0], dict)):
		return {}
	return found[0]


def write_manual(connection: Connection, sound: int, gain: float) -> None:
	"""L'ajustement manuel du sonore, en dB ; 0 retire la clé du plugin."""
	if gain == 0:
		connection.execute("UPDATE sounds SET properties = properties - %s WHERE id = %s", (KEY, sound))
		return
	connection.execute(
		"UPDATE sounds SET properties = properties || jsonb_build_object(%s::text, %s::jsonb) WHERE id = %s",
		(KEY, Jsonb({"gain": round(gain, 1)}), sound),
	)


def record_incident(connection: Connection, kind: str, message: str, sound: int) -> None:
	"""Une ligne « incident » du log, au nom du sonore."""
	connection.execute(
		"INSERT INTO log (level, kind, message, sound_id) VALUES ('incident', %s, %s, %s)", (kind, message, sound)
	)
