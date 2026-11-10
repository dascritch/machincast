"""Accès à la base PostgreSQL et application des migrations yoyo.

Schéma initial, aux noms anglais (https://github.com/dascritch/machincast/issues/314,
https://github.com/dascritch/machincast/issues/358) : 0001.initial-schema, seule migration, que les suivantes ont
rejointe en alpha (https://github.com/dascritch/machincast/issues/381). Une base de l'ancien schéma, aux noms français,
n'est plus reconnue (https://github.com/dascritch/machincast/issues/384) : aucune ne sera mise à jour avant la 1.0.0,
elles se recréent.
"""

from enum import StrEnum
from pathlib import Path
from urllib.parse import quote

import psycopg
from psycopg import sql
from psycopg.rows import TupleRow
from yoyo import get_backend, read_migrations

SHORT_TEXT_LENGTH = 255
"""Longueur maximale des textes saisis à la main (noms, artiste, titre), en base comme dans l'interface."""

MIGRATION_DIRECTORY = Path(__file__).parent / "migrations"
"""Migrations SQL livrées avec le paquet : 0001.nom.sql et son annulation 0001.nom.rollback.sql."""

TABLES: tuple[str, ...] = (
	"sounds",
	"feeds",
	"banks",
	"bank_directories",
	"bank_sounds",
	"events",
	"event_items",
	"event_skips",
	"sequences",
	"sequence_items",
	"airplay",
	"log",
)
"""Tables créées par les migrations, dans l'ordre de doc/fr/spec.md § 3.1."""

TYPES: tuple[str, ...] = (
	"sound_type",
	"bank_mode",
	"event_priority",
	"weekday",
	"airplay_line_type",
	"log_level",
	"sound_state",
	"crossfade_rule",
	"end_of_list",
)
"""Types énumérés créés par la migration ; end_of_list depuis https://github.com/dascritch/machincast/issues/350."""


class Role(StrEnum):
	"""Rôles de groupe PostgreSQL, un par binaire. Droits : doc/fr/spec.md § 3.2 et migrations."""

	PLAYBACK = "machincast_player"
	INDEXING = "machincast_indexer"
	INTERFACE = "machincast_interface"


def url_yoyo(socket: Path, database: str) -> str:
	"""URL yoyo pour une connexion psycopg 3 par socket Unix (authentification peer)."""
	return f"postgresql+psycopg:///{quote(database)}?host={quote(str(socket))}"


# Le backend yoyo garde sa connexion ouverte jusqu'au ramasse-miettes : le « with » la ferme, même en cas
# d'erreur, pour ne pas épuiser les connexions du serveur (https://github.com/dascritch/machincast/issues/78).


def apply_migrations(url: str) -> int:
	"""Applique toutes les migrations pas encore appliquées, puis ferme la connexion ; rend le nombre de migrations
	appliquées."""
	migrations = read_migrations(str(MIGRATION_DIRECTORY))
	with get_backend(url) as backend, backend.lock():
		missing_list = backend.to_apply(migrations)
		backend.apply_migrations(missing_list)
	return len(missing_list)


def cancel_migrations(url: str) -> None:
	"""Annule toutes les migrations appliquées, dans l'ordre inverse, puis ferme la connexion."""
	migrations = read_migrations(str(MIGRATION_DIRECTORY))
	with get_backend(url) as backend, backend.lock():
		backend.rollback_migrations(backend.to_rollback(migrations))


def open_connection(socket: Path, database: str, role: Role) -> psycopg.Connection[TupleRow]:
	"""Ouvre une connexion par socket Unix (authentification peer) et endosse le rôle du binaire.

	L'utilisateur système doit avoir été autorisé par l'utilisateur postgres (doc/fr/spec.md § 3.2) : il n'hérite pas
	des droits de ses rôles, il doit les endosser. Chaque binaire n'agit ainsi qu'avec ses propres droits.
	"""
	connection = psycopg.connect(host=str(socket), dbname=database)
	try:
		connection.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
		connection.commit()
	except BaseException:
		connection.close()
		raise
	return connection
