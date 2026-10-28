"""Accès à la base PostgreSQL et application des migrations yoyo.

Schéma unique (https://github.com/dascritch/machincast/issues/314) : les migrations 0002 à 0015 sont fondues dans
0001.schema-initial, qui donne exactement le même schéma. Une base qui les a toutes reçues garde ses données : avant
d'appliquer les migrations, oublier_les_migrations_fusionnees retire leurs traces de _yoyo_migration, et donne leurs
noms d'origine aux contraintes NOT NULL que PostgreSQL 18 nomme, et qu'un renommage de table ou de colonne gardait. Une
base restée à une migration intermédiaire est refusée (SchemaPerime), sans rien modifier.
"""

import logging
from enum import StrEnum
from pathlib import Path
from urllib.parse import quote

import psycopg
from psycopg import sql
from psycopg.rows import TupleRow
from yoyo import get_backend, read_migrations
from yoyo.backends.base import DatabaseBackend

journal = logging.getLogger(__name__)

LONGUEUR_TEXTE_COURT = 255
"""Longueur maximale des textes saisis à la main (noms, artiste, titre), en base comme dans l'interface."""

REPERTOIRE_MIGRATIONS = Path(__file__).parent / "migrations"
"""Migrations SQL livrées avec le paquet : 0001.nom.sql et son annulation 0001.nom.rollback.sql."""

TABLES: tuple[str, ...] = (
	"sonores",
	"feeds",
	"banques",
	"banques_repertoires",
	"banques_sonores",
	"evenements",
	"evenements_elements",
	"evenements_sauts",
	"sequences",
	"sequences_elements",
	"airplay",
	"log",
)
"""Tables créées par les migrations, dans l'ordre de doc/spec.md § 3.1."""

TYPES: tuple[str, ...] = (
	"type_sonore",
	"mode_banque",
	"priorite_evenement",
	"jour_semaine",
	"type_ligne_airplay",
	"niveau_log",
	"etat_sonore",
	"regle_crossfade",
)
"""Types énumérés créés par les migrations."""


class Role(StrEnum):
	"""Rôles de groupe PostgreSQL, un par binaire. Droits : doc/spec.md § 3.2 et migration 0001.schema-initial."""

	LECTURE = "machincast_lecture"
	INDEXATION = "machincast_indexation"
	INTERFACE = "machincast_interface"


def url_yoyo(socket: Path, base: str) -> str:
	"""URL yoyo pour une connexion psycopg 3 par socket Unix (authentification peer)."""
	return f"postgresql+psycopg:///{quote(base)}?host={quote(str(socket))}"


MIGRATIONS_FUSIONNEES: tuple[str, ...] = (
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
"""Migrations fondues dans 0001.schema-initial (https://github.com/dascritch/machincast/issues/314)."""
DERNIERE_VERSION_A_MIGRATIONS = "cd2e564"
"""Le dernier commit de MachinCast qui les livre encore, pour mettre à jour une base restée en chemin."""
CONTRAINTES_RENOMMEES: tuple[tuple[str, str, str], ...] = (
	("feeds", "marques_pages_streams_id_not_null", "feeds_id_not_null"),
	("feeds", "marques_pages_streams_nom_not_null", "feeds_nom_not_null"),
	("feeds", "marques_pages_streams_url_not_null", "feeds_url_not_null"),
	("sonores", "sonores_detection_blancs_not_null", "sonores_detection_silences_not_null"),
	("banques", "banques_detection_blancs_not_null", "banques_detection_silences_not_null"),
)
"""Contraintes NOT NULL nommées par PostgreSQL 18 avant un renommage, et leur nom dans le schéma unique : table,
ancien nom, nouveau nom."""


class SchemaPerime(Exception):
	"""La base a reçu une partie seulement des migrations fondues dans le schéma unique : le message dit quoi faire."""


def oublier_les_migrations_fusionnees(backend: DatabaseBackend, base: str) -> bool:
	"""Une base qui a reçu toutes les migrations fondues dans 0001.schema-initial a déjà son schéma : leurs traces
	sont retirées, et ses contraintes renommées comme dans le schéma unique ; vrai si c'est fait. Une base qui n'en a
	reçu qu'une partie lève SchemaPerime, sans rien modifier. À appeler sous le verrou du backend."""
	backend.ensure_internal_schema_updated()
	lignes = backend.execute(f"SELECT migration_id FROM {backend.migration_table_quoted}").fetchall()
	trouvees = {str(ligne[0]) for ligne in lignes} & set(MIGRATIONS_FUSIONNEES)
	if trouvees == set():
		return False
	manquantes = [migration for migration in MIGRATIONS_FUSIONNEES if migration not in trouvees]
	if manquantes != []:
		raise SchemaPerime(
			f"base {base} : ancien schéma, sans la migration {manquantes[0]} ; la mettre à jour avec MachinCast"
			f" {DERNIERE_VERSION_A_MIGRATIONS} (git checkout {DERNIERE_VERSION_A_MIGRATIONS}, puis ./install.sh), puis"
			" revenir à la version actuelle, ou la recréer si elle ne contient rien d'utile"
		)
	with backend.transaction():
		backend.execute(
			f"DELETE FROM {backend.migration_table_quoted} WHERE migration_id = ANY(:ids)",
			{"ids": list(MIGRATIONS_FUSIONNEES)},
		)
		for table, ancien, nouveau in CONTRAINTES_RENOMMEES:
			existe = backend.execute(
				"SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = :nom AND conrelid = to_regclass(:table))",
				{"nom": ancien, "table": table},
			).fetchone()
			if (existe is not None) and (existe[0] is True):
				# Des noms constants, de CONTRAINTES_RENOMMEES.
				backend.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{ancien}" TO "{nouveau}"')
	journal.info(
		f"base {base} : les migrations {MIGRATIONS_FUSIONNEES[0]} à {MIGRATIONS_FUSIONNEES[-1]}, fondues dans"
		" 0001.schema-initial, sont oubliées ; ses données ne changent pas"
	)
	return True


# Le backend yoyo garde sa connexion ouverte jusqu'au ramasse-miettes : le « with » la ferme, même en cas
# d'erreur, pour ne pas épuiser les connexions du serveur (https://github.com/dascritch/machincast/issues/78).


def appliquer_migrations(url: str, base: str = "") -> int:
	"""Oublie les migrations fondues dans le schéma unique, si la base les a toutes reçues, applique toutes les
	migrations pas encore appliquées, puis ferme la connexion ; rend le nombre de migrations appliquées. Lève
	SchemaPerime pour une base restée en chemin."""
	migrations = read_migrations(str(REPERTOIRE_MIGRATIONS))
	with get_backend(url) as backend, backend.lock():
		oublier_les_migrations_fusionnees(backend, base)
		manquantes = backend.to_apply(migrations)
		backend.apply_migrations(manquantes)
	return len(manquantes)


def annuler_migrations(url: str) -> None:
	"""Annule toutes les migrations appliquées, dans l'ordre inverse, puis ferme la connexion."""
	migrations = read_migrations(str(REPERTOIRE_MIGRATIONS))
	with get_backend(url) as backend, backend.lock():
		backend.rollback_migrations(backend.to_rollback(migrations))


def connecter(socket: Path, base: str, role: Role) -> psycopg.Connection[TupleRow]:
	"""Ouvre une connexion par socket Unix (authentification peer) et endosse le rôle du binaire.

	L'utilisateur système doit avoir été autorisé par l'utilisateur postgres (doc/spec.md § 3.2) : il n'hérite pas
	des droits de ses rôles, il doit les endosser. Chaque binaire n'agit ainsi qu'avec ses propres droits.
	"""
	connexion = psycopg.connect(host=str(socket), dbname=base)
	try:
		connexion.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
		connexion.commit()
	except BaseException:
		connexion.close()
		raise
	return connexion
