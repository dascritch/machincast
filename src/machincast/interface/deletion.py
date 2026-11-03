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

from machincast.interface import display

Connection = psycopg.Connection[TupleRow]


@dataclass(frozen=True)
class Category:
	table: str
	item: str
	"""« le sonore », « la banque »…"""
	pronoun: str
	"""« Il » ou « Elle »."""
	agreement: str
	"""« » ou « e » : retiré, retirée."""
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

	@property
	def object_(self) -> str:
		"""« le » ou « la » : le pronom qui le reprend."""
		if self.agreement == "e":
			return "la"
		return "le"


CATEGORIES = {
	"sonore": Category(
		"sounds",
		"le sonore",
		"Il",
		"",
		"sound_id",
		("banque", "séquence", "événement"),
		"Il ne figure dans aucune banque, aucune séquence ni aucun événement.",
	),
	"banque": Category(
		"banks",
		"la banque",
		"Elle",
		"e",
		"bank_id",
		("séquence", "événement"),
		"Elle ne figure dans aucune séquence ni aucun événement.",
	),
	"séquence": Category(
		"sequences", "la séquence", "Elle", "e", "sequence_id", ("événement",), "Elle ne figure dans aucun événement."
	),
	"événement": Category("events", "l'événement", "Il", "", "", (), ""),
	"feed": Category("feeds", "le feed", "Il", "", "", (), "Aucun stream ne le suit.", "name", False, False),
}
CONTAINERS = {
	"banque": ("banks", "bank_sounds", "bank_id", "de la banque", "qui n'aura plus aucun sonore"),
	"séquence": ("sequences", "sequence_items", "sequence_id", "de la séquence", "qui n'aura plus aucun élément"),
	"événement": (
		"events",
		"event_items",
		"event_id",
		"de l'événement",
		"qui n'aura plus rien à jouer",
	),
}
"""Pour chaque genre de liste : sa table, la table de ses éléments, la colonne qui la désigne, comment la nommer, et
ce qu'elle devient vide."""
HISTORY = "L'historique de diffusion garde ses passages."


def _names(lines: list[TupleRow]) -> str:
	return ", ".join(f"« {line[0]} »" for line in lines)


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
			line = f"• {give_name} « {name} »"
			if emptied:
				line = f"{line}, {empty}"
			lines.append(line)
	return lines


def _file(connection: Connection, identifier: int) -> list[str]:
	"""Ce que devient le fichier d'un sonore : rien, il reste à sa place ; l'indexation le reprendra s'il est sous
	un répertoire de banque."""
	line = connection.execute("SELECT location FROM sounds WHERE id = %s", (identifier,)).fetchone()
	if (line is None) or (line[0] is None):
		return []
	file = Path(str(line[0]))
	text = f"Son fichier reste à sa place, intact : {file}."
	directories = connection.execute(
		"SELECT b.internal_name, r.directory FROM bank_directories r JOIN banks b ON b.id = r.bank_id"
		" ORDER BY b.internal_name, r.directory"
	).fetchall()
	banks = list(dict.fromkeys(str(name) for name, directory in directories if file.is_relative_to(str(directory))))
	if banks != []:
		which = f"de la banque « {banks[0]} »"
		if len(banks) > 1:
			which = f"des banques {', '.join(f'« {bank} »' for bank in banks)}"
		text = (
			f"{text} Il est dans un répertoire {which} : la prochaine indexation l'enregistrera de nouveau, comme un"
			" nouveau sonore."
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
			return ["Ses sonores restent en base."]
		paths = ", ".join(str(directory) for (directory,) in directories)
		return [
			f"Ses répertoires restent à leur place, avec leurs fichiers, intacts : {paths}."
			" Ses sonores restent en base."
		]
	if category == "séquence":
		return ["Ses sonores et ses banques restent en base."]
	if category == "feed":
		return []
	streams = connection.execute(
		"SELECT COALESCE(title, stream_url) FROM sounds WHERE fallback_event_id = %s ORDER BY 1", (identifier,)
	).fetchall()
	lines = []
	if len(streams) == 1:
		lines.append(f"Il est l'événement de secours du stream {_names(streams)}, qui n'en aura plus.")
	elif streams != []:
		lines.append(f"Il est l'événement de secours des streams {_names(streams)}, qui n'en auront plus.")
	lines.append(
		"Il ne joue plus ; sa liste de lecture reste avec lui. Ses sonores, banques et séquences restent en base."
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
			f"Les streams {_names(streams)} suivent ce feed : choisir pour eux une autre adresse avant de le supprimer."
		)


def question(connection: Connection, category: str, identifier: int) -> tuple[str, str] | None:
	"""Le titre et le texte de la question de suppression ; None si l'élément n'est plus en base. Lève Empechee pour
	un élément qui ne peut pas être supprimé. À appeler dans une transaction."""
	name = _name(connection, category, identifier)
	if name is None:
		return None
	_prevent(connection, category, identifier)
	describes = CATEGORIES[category]
	lines = [f"Supprimer {describes.item} « {name} » ?"]
	if not describes.deferred:
		lines = [f"Supprimer de la base {describes.item} « {name} » ?"]
	removals = _removals(connection, category, identifier)
	if removals != []:
		lines.append(f"{describes.pronoun} en sera retiré{describes.agreement} :")
		lines += [f"{removal} ;" for removal in removals[:-1]]
		lines.append(f"{removals[-1]}.")
	elif describes.no != "":
		lines.append(describes.no)
	lines += _remainders(connection, category, identifier)
	if describes.history:
		lines.append(HISTORY)
	if describes.deferred:
		lines.append(
			f"Marqué{describes.agreement} « supprimé{describes.agreement} », {describes.pronoun.lower()} se restaure"
			f" depuis sa fiche."
		)
	return f"Supprimer {describes.item}", "\n".join(lines)


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
	return (
		f"Supprimé{describes.agreement} le {instant.astimezone():%d/%m/%Y à %H:%M}, effacé{describes.agreement} de la"
		f" base après le"
		f" {erased:%d/%m/%Y} : « Restaurer » {describes.object_} remet en service."
	)


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
		who = f"{_a_other(describes)} s'appelle déjà « {taken[0]} »"
		if category == "sonore":
			who = f"un autre sonore a déjà ce fichier, {taken[0]}"
		raise Prevented(f"Restauration impossible : {who}.")
	connection.execute(f"UPDATE {describes.table} SET deleted_at = NULL WHERE id = %s", (identifier,))  # noqa: S608


def _a_other(describes: Category) -> str:
	"""« une autre banque », « un autre événement »…"""
	name = describes.item.split(" ", 1)[-1].removeprefix("l'")
	if describes.agreement == "e":
		return f"une autre {name}"
	return f"un autre {name}"
