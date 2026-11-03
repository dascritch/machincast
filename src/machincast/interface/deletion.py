"""Suppression d'un élément depuis sa fiche (https://github.com/dascritch/machincast/issues/33, spec § 8.9).

Supprimer un sonore, une banque, une séquence ou un événement le retire des listes où il figure, et le marque
« supprimé », avec l'instant de la demande (deleted_at) : il reste en base jusqu'à sa péremption, hors des listes, de
la recherche et de la grille, et se restaure depuis sa fiche (restaurer,
https://github.com/dascritch/machincast/issues/267). Restauré, il ne revient pas dans les listes d'où il avait été
retiré. Un événement supprimé ne secourt plus aucun stream. Un feed quitte la base. Jamais un fichier sonore ni un
répertoire, qui restent à leur place, intacts (https://github.com/dascritch/machincast/issues/96). L'historique de
diffusion garde ses passages.

La question de confirmation dit où l'élément figure, et quelle liste n'aurait plus rien après son retrait.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.i18n import _, date_and_hour, pgettext, short_date
from machincast.interface import display

Connection = psycopg.Connection[TupleRow]


@dataclass(frozen=True)
class Category:
	"""Un genre d'élément, et ses phrases de suppression : chacune entière, pour que sa traduction s'accorde au genre
	de l'élément (https://github.com/dascritch/machincast/issues/360)."""

	table: str
	title: str
	"""Le titre de la question : « Supprimer le sonore »."""
	ask: str
	"""La question, à champ {name} : « Supprimer le sonore « {name} » ? »."""
	removed: str
	"""L'annonce des listes d'où il sera retiré : « Il en sera retiré : »."""
	restorable: str
	"""« Marqué « supprimé », il se restaure depuis sa fiche. »"""
	marks: str
	"""Ce que dit la fiche de l'élément supprimé, à champs {deleted} et {erased}."""
	other: str
	"""Un autre élément du même genre a son nom, à champ {name} : « une autre banque s'appelle déjà « {name} » »."""
	column: str
	"""Colonne qui désigne l'élément dans les listes qui le contiennent."""
	containers: tuple[str, ...]
	"""Genres des listes qui peuvent le contenir."""
	no: str
	"""Phrase pour un élément qui ne figure nulle part."""
	name: str = "internal_name"
	"""Colonne de son nom."""
	history: bool = True
	"""L'historique de diffusion le cite : la question rappelle qu'il garde ses passages."""
	deferred: bool = True
	"""Supprimé, il reste en base, marqué, jusqu'à sa péremption ; sinon, il quitte la base."""


CATEGORIES = {
	"sonore": Category(
		"sounds",
		_("Delete the sound"),
		_("Delete the sound “{name}”?"),
		pgettext("sound", "It will be removed from:"),
		pgettext("sound", "Marked “deleted”, it can be restored from its card."),
		pgettext(
			"sound",
			"Deleted on {deleted}, erased from the database after {erased}: “Restore” puts it back into service.",
		),
		_("another sound is already called “{name}”"),
		"sound_id",
		("banque", "séquence", "événement"),
		_("It is in no bank, no sequence and no event."),
	),
	"banque": Category(
		"banks",
		_("Delete the bank"),
		_("Delete the bank “{name}”?"),
		pgettext("bank", "It will be removed from:"),
		pgettext("bank", "Marked “deleted”, it can be restored from its card."),
		pgettext(
			"bank",
			"Deleted on {deleted}, erased from the database after {erased}: “Restore” puts it back into service.",
		),
		_("another bank is already called “{name}”"),
		"bank_id",
		("séquence", "événement"),
		_("It is in no sequence and no event."),
	),
	"séquence": Category(
		"sequences",
		_("Delete the sequence"),
		_("Delete the sequence “{name}”?"),
		pgettext("sequence", "It will be removed from:"),
		pgettext("sequence", "Marked “deleted”, it can be restored from its card."),
		pgettext(
			"sequence",
			"Deleted on {deleted}, erased from the database after {erased}: “Restore” puts it back into service.",
		),
		_("another sequence is already called “{name}”"),
		"sequence_id",
		("événement",),
		_("It is in no event."),
	),
	"événement": Category(
		"events",
		_("Delete the event"),
		_("Delete the event “{name}”?"),
		pgettext("event", "It will be removed from:"),
		pgettext("event", "Marked “deleted”, it can be restored from its card."),
		pgettext(
			"event",
			"Deleted on {deleted}, erased from the database after {erased}: “Restore” puts it back into service.",
		),
		_("another event is already called “{name}”"),
		"",
		(),
		"",
	),
	"feed": Category(
		"feeds",
		_("Delete the feed"),
		_("Delete from the database the feed “{name}”?"),
		pgettext("feed", "It will be removed from:"),
		"",
		"",
		_("another feed is already called “{name}”"),
		"",
		(),
		_("No stream follows it."),
		"name",
		False,
		False,
	),
}
CONTAINERS = {
	"banque": ("banks", "bank_sounds", "bank_id", _("of the bank"), _("which will no longer have any sound")),
	"séquence": (
		"sequences",
		"sequence_items",
		"sequence_id",
		_("of the sequence"),
		_("which will no longer have any element"),
	),
	"événement": (
		"events",
		"event_items",
		"event_id",
		_("of the event"),
		_("which will no longer have anything to play"),
	),
}
"""Pour chaque genre de liste : sa table, la table de ses éléments, la colonne qui la désigne, comment la nommer, et
ce qu'elle devient vide."""
HISTORY = _("The broadcast history keeps its plays.")


def _names(lines: list[TupleRow]) -> str:
	return ", ".join(_("“{line}”").format(line=line[0]) for line in lines)


def _name(connection: Connection, category: str, identifier: int) -> str | None:
	"""Le nom de l'élément ; None s'il n'est plus en base. Un sonore : artiste et titre, ou le nom de son fichier, ou
	l'adresse de son stream."""
	if category != "sonore":
		line = connection.execute(
			f"SELECT {CATEGORIES[category].name} FROM {CATEGORIES[category].table} WHERE id = %s",  # noqa: S608
			(identifier,),
		).fetchone()
		if line is None:
			return None
		return str(line[0])
	sound = connection.execute(
		"SELECT artist, title, location, stream_url FROM sounds WHERE id = %s", (identifier,)
	).fetchone()
	if sound is None:
		return None
	return display.sound_name(*sound)


def _removals(connection: Connection, category: str, identifier: int) -> list[str]:
	"""Une ligne par liste qui contient l'élément : les banques, puis les séquences, puis les événements, par nom."""
	column = CATEGORIES[category].column
	lines = []
	for container in CATEGORIES[category].containers:
		table, items, parent, give_name, empty = CONTAINERS[container]
		found_list = connection.execute(
			f"SELECT c.internal_name, NOT EXISTS (SELECT 1 FROM {items} x WHERE x.{parent} = c.id"  # noqa: S608
			f" AND x.{column} IS DISTINCT FROM %s) FROM {table} c WHERE EXISTS (SELECT 1 FROM {items} x"
			f" WHERE x.{parent} = c.id AND x.{column} = %s) ORDER BY c.internal_name, c.id",
			(identifier, identifier),
		).fetchall()
		for name, emptied in found_list:
			line = _("• {give_name} “{name}”").format(give_name=give_name, name=name)
			if emptied:
				line = _("{line}, {empty}").format(line=line, empty=empty)
			lines.append(line)
	return lines


def _file(connection: Connection, identifier: int) -> list[str]:
	"""Ce que devient le fichier d'un sonore : rien, il reste à sa place ; l'indexation le reprendra s'il est sous
	un répertoire de banque."""
	line = connection.execute("SELECT location FROM sounds WHERE id = %s", (identifier,)).fetchone()
	if (line is None) or (line[0] is None):
		return []
	file = Path(str(line[0]))
	text = _("Its file stays in place, intact: {file}.").format(file=file)
	directories = connection.execute(
		"SELECT b.internal_name, r.directory FROM bank_directories r JOIN banks b ON b.id = r.bank_id"
		" ORDER BY b.internal_name, r.directory"
	).fetchall()
	banks = list(dict.fromkeys(str(name) for name, directory in directories if file.is_relative_to(str(directory))))
	if banks != []:
		which = _("of bank “{banks}”").format(banks=banks[0])
		if len(banks) > 1:
			which = _("of banks {list}").format(list=", ".join(_("“{bank}”").format(bank=bank) for bank in banks))
		text = _("{text} It is in a directory {which}: the next indexing will record it again, as a new sound.").format(
			text=text, which=which
		)
	return [text]


def _remainders(connection: Connection, category: str, identifier: int) -> list[str]:
	"""Ce qui reste après la suppression, propre à chaque genre."""
	if category == "sonore":
		return _file(connection, identifier)
	if category == "banque":
		directories = connection.execute(
			"SELECT directory FROM bank_directories WHERE bank_id = %s ORDER BY directory", (identifier,)
		).fetchall()
		if directories == []:
			return [_("Its sounds stay in the database.")]
		paths = ", ".join(str(directory) for (directory,) in directories)
		return [
			_(
				"Its directories stay in place, with their files, intact: {paths}. Its sounds stay in the database."
			).format(paths=paths)
		]
	if category == "séquence":
		return [_("Its sounds and its banks stay in the database.")]
	if category == "feed":
		return []
	streams = connection.execute(
		"SELECT COALESCE(title, stream_url) FROM sounds WHERE fallback_event_id = %s ORDER BY 1", (identifier,)
	).fetchall()
	lines = []
	if len(streams) == 1:
		lines.append(
			_("It is the fallback event of stream {names}, which will have none any more.").format(
				names=_names(streams)
			)
		)
	elif streams != []:
		lines.append(
			_("It is the fallback event of streams {names}, which will have none any more.").format(
				names=_names(streams)
			)
		)
	lines.append(
		_("It no longer plays; its play list stays with it. Its sounds, banks and sequences stay in the database.")
	)
	return lines


class Prevented(Exception):
	"""L'élément ne peut pas être supprimé : le message dit pourquoi, et ce qu'il faut faire d'abord."""


def _prevent(connection: Connection, category: str, identifier: int) -> None:
	"""Un feed qu'un stream suit ne se supprime pas (feed_id ON DELETE RESTRICT)."""
	if category != "feed":
		return
	streams = connection.execute(
		"SELECT COALESCE(s.title, m.url) FROM sounds s JOIN feeds m ON m.id = s.feed_id WHERE m.id = %s ORDER BY 1",
		(identifier,),
	).fetchall()
	if streams != []:
		raise Prevented(
			_("Streams {names} follow this feed: choose another address for them before deleting it.").format(
				names=_names(streams)
			)
		)


def question(connection: Connection, category: str, identifier: int) -> tuple[str, str] | None:
	"""Le titre et le texte de la question de suppression ; None si l'élément n'est plus en base. Lève Empechee pour
	un élément qui ne peut pas être supprimé. À appeler dans une transaction."""
	name = _name(connection, category, identifier)
	if name is None:
		return None
	_prevent(connection, category, identifier)
	describes = CATEGORIES[category]
	lines = [describes.ask.format(name=name)]
	removals = _removals(connection, category, identifier)
	if removals != []:
		lines.append(describes.removed)
		lines += [_("{removal};").format(removal=removal) for removal in removals[:-1]]
		lines.append(_("{removal}.").format(removal=removals[-1]))
	elif describes.no != "":
		lines.append(describes.no)
	lines += _remainders(connection, category, identifier)
	if describes.history:
		lines.append(HISTORY)
	if describes.deferred:
		lines.append(describes.restorable)
	return describes.title, "\n".join(lines)


def delete(connection: Connection, category: str, identifier: int, instant: datetime) -> None:
	"""Dans la transaction en cours : retire l'élément des listes qui le contiennent, et le marque « supprimé » à cet
	instant ; un événement ne secourt plus aucun stream. Un feed quitte la base."""
	describes = CATEGORIES[category]
	if not describes.deferred:
		connection.execute(f"DELETE FROM {describes.table} WHERE id = %s", (identifier,))  # noqa: S608
		return
	for container in describes.containers:
		_table, items, _parent, _give_name, _empty = CONTAINERS[container]
		connection.execute(f"DELETE FROM {items} WHERE {describes.column} = %s", (identifier,))  # noqa: S608
	if category == "événement":
		connection.execute("UPDATE sounds SET fallback_event_id = NULL WHERE fallback_event_id = %s", (identifier,))
	connection.execute(
		f"UPDATE {describes.table} SET deleted_at = %s WHERE id = %s",  # noqa: S608
		(instant, identifier),
	)


def deleted_at(connection: Connection, category: str, identifier: int) -> datetime | None:
	"""L'instant de la demande de suppression ; None pour un élément qui n'est pas supprimé, ou qui ne l'est jamais
	qu'en quittant la base."""
	describes = CATEGORIES[category]
	if not describes.deferred:
		return None
	line = connection.execute(
		f"SELECT deleted_at FROM {describes.table} WHERE id = %s",  # noqa: S608
		(identifier,),
	).fetchone()
	if (line is None) or (not isinstance(line[0], datetime)):
		return None
	return line[0]


def marks(category: str, instant: datetime, retention: int) -> str:
	"""Ce que dit la fiche d'un élément supprimé : quand il l'a été, et après quel jour Machin purge l'efface de la
	base, peremption jours plus tard (https://github.com/dascritch/machincast/issues/268)."""
	describes = CATEGORIES[category]
	erased = (instant + timedelta(days=retention)).astimezone()
	return describes.marks.format(deleted=date_and_hour(instant.astimezone()), erased=short_date(erased))


def restore(connection: Connection, category: str, identifier: int) -> None:
	"""Dans la transaction en cours : l'élément n'est plus supprimé, sans revenir dans les listes d'où il avait été
	retiré. Lève Empechee si un autre élément a repris son nom, ou son emplacement."""
	describes = CATEGORIES[category]
	column = "location"
	if category != "sonore":
		column = describes.name
	taken = connection.execute(
		f"SELECT o.{column} FROM {describes.table} s JOIN {describes.table} o ON o.{column} = s.{column}"  # noqa: S608
		" AND o.id <> s.id AND o.deleted_at IS NULL WHERE s.id = %s",
		(identifier,),
	).fetchone()
	if taken is not None:
		who = describes.other.format(name=taken[0])
		if category == "sonore":
			who = _("another sound already has this file, {taken}").format(taken=taken[0])
		raise Prevented(_("Restoring impossible: {who}.").format(who=who))
	connection.execute(f"UPDATE {describes.table} SET deleted_at = NULL WHERE id = %s", (identifier,))  # noqa: S608
