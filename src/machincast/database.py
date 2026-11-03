"""Accès à la base PostgreSQL et application des migrations yoyo.

Schéma unique, aux noms anglais (https://github.com/dascritch/machincast/issues/314,
https://github.com/dascritch/machincast/issues/358) : 0001.initial-schema. Une base créée avec l'ancien schéma, aux
noms français, est refusée (OutdatedSchema), sans rien modifier : elle se recrée.
"""

from enum import StrEnum
from pathlib import Path
from urllib.parse import quote

import psycopg
from psycopg import sql
from psycopg.rows import TupleRow
from yoyo import get_backend, read_migrations
from yoyo.backends.base import DatabaseBackend

from machincast.i18n import _

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
)
"""Types énumérés créés par les migrations."""


class Role(StrEnum):
	"""Rôles de groupe PostgreSQL, un par binaire. Droits : doc/fr/spec.md § 3.2 et migration 0001.initial-schema."""

	PLAYBACK = "machincast_player"
	INDEXING = "machincast_indexer"
	INTERFACE = "machincast_interface"


def url_yoyo(socket: Path, database: str) -> str:
	"""URL yoyo pour une connexion psycopg 3 par socket Unix (authentification peer)."""
	return f"postgresql+psycopg:///{quote(database)}?host={quote(str(socket))}"


OLD_MIGRATIONS: tuple[str, ...] = (
	"0001.schema-initial",
	"0002.evenements-nom-unique",
	"0003.sonores-type-de-fichier",
	"0004.sonores-verifie-le",
	"0005.banques-crossfades",
	"0006.banques-durees",
	"0007.sonores-crossfades-facultatifs",
	"0008.detection-blancs",
	"0009.sonores-audit-demande",
	"0010.indexation-retire-des-banques",
	"0011.sonores-dernier-audit",
	"0012.feeds",
	"0013.suppression-differee",
	"0014.sessions-sautees",
	"0015.vocabulaire-silences-blancs",
)
"""Migrations de l'ancien schéma, aux noms français, d'avant https://github.com/dascritch/machincast/issues/358 : une
base qui en a reçu une se recrée."""


class OutdatedSchema(Exception):
	"""La base a l'ancien schéma, aux noms français : le message dit quoi faire."""


def refuse_old_schema(backend: DatabaseBackend, database: str) -> None:
	"""Lève OutdatedSchema, sans rien modifier, pour une base qui a reçu une migration de l'ancien schéma. À appeler
	sous
	le verrou du backend."""
	backend.ensure_internal_schema_updated()
	lines = backend.execute(f"SELECT migration_id FROM {backend.migration_table_quoted}").fetchall()
	old_list = [migration for migration in OLD_MIGRATIONS if migration in {str(line[0]) for line in lines}]
	if old_list != []:
		raise OutdatedSchema(
			_(
				"database {database}: old schema, with French names (migration {old_list}); recreate it, "
				"after backing it up if it holds anything useful: sudo -u postgres dropdb {database}, then "
				"./install.sh"
			).format(database=database, old_list=old_list[0])
		)


# Le backend yoyo garde sa connexion ouverte jusqu'au ramasse-miettes : le « with » la ferme, même en cas
# d'erreur, pour ne pas épuiser les connexions du serveur (https://github.com/dascritch/machincast/issues/78).


def apply_migrations(url: str, database: str = "") -> int:
	"""Applique toutes les migrations pas encore appliquées, puis ferme la connexion ; rend le nombre de migrations
	appliquées. Lève OutdatedSchema, sans rien modifier, pour une base à l'ancien schéma."""
	migrations = read_migrations(str(MIGRATION_DIRECTORY))
	with get_backend(url) as backend, backend.lock():
		refuse_old_schema(backend, database)
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
