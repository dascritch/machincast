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


def bank_properties(connection: Connection, bank: int) -> dict[str, Any]:
	found = connection.execute("SELECT properties FROM banks WHERE id = %s", (bank,)).fetchone()
	if (found is None) or (not isinstance(found[0], dict)):
		return {}
	return found[0]


def banks_of_sound(connection: Connection, sound: int) -> list[tuple[str, dict[str, Any]]]:
	"""Les banques non supprimées qui contiennent le sonore, par nom, avec leurs properties."""
	found = []
	for name, properties in connection.execute(
		"SELECT b.internal_name, b.properties FROM bank_sounds bs JOIN banks b ON b.id = bs.bank_id"
		" WHERE bs.sound_id = %s AND b.deleted_at IS NULL ORDER BY lower(b.internal_name), b.id",
		(sound,),
	).fetchall():
		if not isinstance(properties, dict):
			properties = {}
		found.append((str(name), properties))
	return found


def write_bank_values(connection: Connection, bank: int, target: float | None, ceiling: float | None) -> None:
	"""La cible et le plafond propres à la banque ; sans l'un ni l'autre, la clé du plugin en part."""
	values: dict[str, float] = {}
	if target is not None:
		values["target"] = round(target, 1)
	if ceiling is not None:
		values["ceiling"] = round(ceiling, 1)
	if values == {}:
		connection.execute("UPDATE banks SET properties = properties - %s WHERE id = %s", (KEY, bank))
		return
	connection.execute(
		"UPDATE banks SET properties = properties || jsonb_build_object(%s::text, %s::jsonb) WHERE id = %s",
		(KEY, Jsonb(values), bank),
	)


def is_stream(connection: Connection, sound: int) -> bool:
	found = connection.execute("SELECT type::text FROM sounds WHERE id = %s", (sound,)).fetchone()
	return (found is not None) and (found[0] == "stream")
