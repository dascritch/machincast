"""Accès à la base PostgreSQL et application des migrations yoyo."""

from enum import StrEnum
from pathlib import Path
from urllib.parse import quote

import psycopg
from psycopg import sql
from psycopg.rows import TupleRow
from yoyo import get_backend, read_migrations

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


# Le backend yoyo garde sa connexion ouverte jusqu'au ramasse-miettes : le « with » la ferme, même en cas
# d'erreur, pour ne pas épuiser les connexions du serveur (https://github.com/dascritch/machincast/issues/78).


def appliquer_migrations(url: str) -> None:
	"""Applique toutes les migrations pas encore appliquées, puis ferme la connexion."""
	migrations = read_migrations(str(REPERTOIRE_MIGRATIONS))
	with get_backend(url) as backend, backend.lock():
		backend.apply_migrations(backend.to_apply(migrations))


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
