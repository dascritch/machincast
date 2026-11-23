"""Les requêtes SQL du cartouchier (https://github.com/dascritch/machincast/issues/512) : les boutons d'un compte, au
rôle machincast_intranet, pour la page et l'API ; leur réglage, au rôle machincast_interface."""

from dataclasses import dataclass
from typing import Any

import psycopg

from machincast_cartwall.buttons import Button
from machincast_cartwall.texts import t

Connection = psycopg.Connection[Any]

_BUTTONS = """
SELECT b.id, b.label, b.colour, b.action, COALESCE(b.sequence_id, b.bank_id, b.event_id, b.feed_id), b.blank,
	COALESCE(s.internal_name, k.internal_name, e.internal_name, f.name),
	COALESCE(s.deleted_at, k.deleted_at, e.deleted_at) IS NOT NULL,
	COALESCE(k.no_repeat AND k.id = (
		SELECT a.bank_id FROM airplay a WHERE a.line_type = 'start' ORDER BY a.id DESC LIMIT 1
	), false)
FROM cartwall__buttons b
JOIN api_users u ON u.id = b.api_user_id
LEFT JOIN sequences s ON s.id = b.sequence_id
LEFT JOIN banks k ON k.id = b.bank_id
LEFT JOIN events e ON e.id = b.event_id
LEFT JOIN feeds f ON f.id = b.feed_id
"""


@dataclass(frozen=True)
class Fields:
	"""Ce qu'on règle d'un bouton dans l'interface."""

	label: str
	colour: str
	action: str
	target: int | None = None
	blank: str | None = None


def _button(line: tuple[Any, ...]) -> Button:
	identifier, label, colour, action, target, blank, name, deleted, repeated = line
	unusable = None
	if deleted:
		unusable = t("“{name}” is deleted").format(name=name)
	if repeated:
		unusable = t("the bank “{name}” does not repeat: it gave the sound on air").format(name=name)
	return Button(int(identifier), str(label), str(colour), str(action), target, blank, name, unusable)


def _buttons(connection: Connection, condition: str, value: object) -> list[Button]:
	with connection.transaction():
		lines = connection.execute(_BUTTONS + condition + " ORDER BY b.position", (value,)).fetchall()
	buttons = []
	for line in lines:
		buttons.append(_button(line))
	return buttons


def buttons_of(connection: Connection, user: str) -> list[Button]:
	"""Les boutons du compte nommé, dans l'ordre, et pourquoi chacun ne peut pas servir maintenant."""
	return _buttons(connection, "WHERE u.name = %s", user)


def buttons_of_account(connection: Connection, account: int) -> list[Button]:
	return _buttons(connection, "WHERE u.id = %s", account)


def button_of(connection: Connection, user: str, button: int) -> Button | None:
	"""Le bouton, s'il est à ce compte : un compte ne demande que ses propres actions."""
	found = []
	for each in buttons_of(connection, user):
		if each.id == button:
			found.append(each)
	if found == []:
		return None
	return found[0]


def accounts(connection: Connection) -> list[tuple[int, str]]:
	"""Les comptes de l'API, par nom."""
	with connection.transaction():
		lines = connection.execute("SELECT id, name FROM api_users ORDER BY name").fetchall()
	found = []
	for identifier, name in lines:
		found.append((int(identifier), str(name)))
	return found


_TARGETS = {
	"sequence": "SELECT id, internal_name FROM sequences WHERE deleted_at IS NULL ORDER BY internal_name",
	"bank": "SELECT id, internal_name FROM banks WHERE deleted_at IS NULL ORDER BY internal_name",
	"fallback": (
		"SELECT id, internal_name FROM events WHERE priority = 'fallback' AND deleted_at IS NULL ORDER BY internal_name"
	),
	"feed": "SELECT id, name FROM feeds ORDER BY name",
}


def targets(connection: Connection, kind: str) -> list[tuple[int, str]]:
	"""Ce qu'une action peut viser : les séquences, les banques, les secours ou les feeds, par nom."""
	with connection.transaction():
		lines = connection.execute(_TARGETS[kind]).fetchall()
	found = []
	for identifier, name in lines:
		found.append((int(identifier), str(name)))
	return found


def _columns(fields: Fields) -> dict[str, object]:
	columns: dict[str, object] = {
		"label": fields.label,
		"colour": fields.colour,
		"action": fields.action,
		"sequence_id": None,
		"bank_id": None,
		"event_id": None,
		"feed_id": None,
		"blank": fields.blank,
	}
	column = {
		"insert_sequence": "sequence_id",
		"insert_bank": "bank_id",
		"cut_by_fallback": "event_id",
		"cut_by_feed": "feed_id",
	}.get(fields.action)
	if column is not None:
		columns[column] = fields.target
	return columns


def add(connection: Connection, account: int, fields: Fields) -> int:
	"""Un bouton de plus, au bout de ceux du compte ; son identifiant."""
	columns = _columns(fields)
	with connection.transaction():
		line = connection.execute(
			"INSERT INTO cartwall__buttons (api_user_id, position, label, colour, action, sequence_id, bank_id, event_id,"
			" feed_id, blank) SELECT %(account)s, COALESCE(max(position), 0) + 1, %(label)s, %(colour)s, %(action)s,"
			" %(sequence_id)s, %(bank_id)s, %(event_id)s, %(feed_id)s, %(blank)s FROM cartwall__buttons"
			" WHERE api_user_id = %(account)s RETURNING id",
			{**columns, "account": account},
		).fetchone()
	assert line is not None
	return int(line[0])


def replace(connection: Connection, button: int, fields: Fields) -> None:
	with connection.transaction():
		connection.execute(
			"UPDATE cartwall__buttons SET label = %(label)s, colour = %(colour)s, action = %(action)s,"
			" sequence_id = %(sequence_id)s, bank_id = %(bank_id)s, event_id = %(event_id)s, feed_id = %(feed_id)s,"
			" blank = %(blank)s WHERE id = %(button)s",
			{**_columns(fields), "button": button},
		)


def remove(connection: Connection, button: int) -> None:
	"""Retire le bouton ; ceux qui le suivent remontent d'un rang."""
	with connection.transaction():
		connection.execute("SET CONSTRAINTS cartwall__buttons_position DEFERRED")
		line = connection.execute(
			"DELETE FROM cartwall__buttons WHERE id = %s RETURNING api_user_id, position", (button,)
		).fetchone()
		if line is not None:
			connection.execute(
				"UPDATE cartwall__buttons SET position = position - 1 WHERE api_user_id = %s AND position > %s", line
			)


def move(connection: Connection, button: int, offset: int) -> None:
	"""Échange le bouton avec son voisin, offset -1 avant lui, 1 après ; rien au bord."""
	with connection.transaction():
		connection.execute("SET CONSTRAINTS cartwall__buttons_position DEFERRED")
		connection.execute(
			"UPDATE cartwall__buttons AS b SET position = CASE WHEN b.id = m.id THEN m.position + %(offset)s"
			" ELSE m.position END FROM cartwall__buttons AS m WHERE m.id = %(button)s AND b.api_user_id = m.api_user_id"
			" AND b.position IN (m.position, m.position + %(offset)s)"
			" AND EXISTS (SELECT 1 FROM cartwall__buttons o WHERE o.api_user_id = m.api_user_id"
			" AND o.position = m.position + %(offset)s)",
			{"button": button, "offset": offset},
		)
