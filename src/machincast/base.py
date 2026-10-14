"""Accès à la base PostgreSQL et application des migrations yoyo."""

from collections.abc import Iterable
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
	"marques_pages_streams",
	"banques",
	"banques_repertoires",
	"banques_sonores",
	"evenements",
	"evenements_elements",
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
)
"""Types énumérés créés par les migrations."""


class Role(StrEnum):
	"""Rôles de groupe PostgreSQL, un par binaire. Droits : doc/spec.md § 3.2 et migration 0002.droits."""

	LECTURE = "machincast_lecture"
	INDEXATION = "machincast_indexation"
	INTERFACE = "machincast_interface"


def url_yoyo(socket: Path, base: str) -> str:
	"""URL yoyo pour une connexion psycopg 3 par socket Unix (authentification peer)."""
	return f"postgresql+psycopg:///{quote(base)}?host={quote(str(socket))}"


def appliquer_migrations(url: str) -> None:
	"""Applique toutes les migrations pas encore appliquées."""
	backend = get_backend(url)
	migrations = read_migrations(str(REPERTOIRE_MIGRATIONS))
	with backend.lock():
		backend.apply_migrations(backend.to_apply(migrations))


def annuler_migrations(url: str) -> None:
	"""Annule toutes les migrations appliquées, dans l'ordre inverse."""
	backend = get_backend(url)
	migrations = read_migrations(str(REPERTOIRE_MIGRATIONS))
	with backend.lock():
		backend.rollback_migrations(backend.to_rollback(migrations))


def connecter(socket: Path, base: str, role: Role) -> psycopg.Connection[TupleRow]:
	"""Ouvre une connexion par socket Unix (authentification peer) et endosse le rôle du binaire.

	L'utilisateur système doit avoir été autorisé par autoriser_utilisateur : il n'hérite pas des droits
	de ses rôles, il doit les endosser. Chaque binaire n'agit ainsi qu'avec ses propres droits.
	"""
	connexion = psycopg.connect(host=str(socket), dbname=base)
	try:
		connexion.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
		connexion.commit()
	except BaseException:
		connexion.close()
		raise
	return connexion


def autoriser_utilisateur(
	connexion_admin: psycopg.Connection[TupleRow], utilisateur: str, roles: Iterable[Role]
) -> None:
	"""Crée si besoin le rôle de connexion d'un utilisateur système et l'autorise à endosser des rôles.

	L'autorisation est donnée sans héritage (INHERIT FALSE) : l'utilisateur n'a aucun droit tant qu'il
	n'a pas endossé un rôle par SET ROLE. Idempotent ; à exécuter par un administrateur PostgreSQL,
	par exemple depuis install.sh.
	"""
	if not utilisateur.strip():
		raise ValueError("le nom d'utilisateur ne peut pas être vide")
	identifiant = sql.Identifier(utilisateur)
	with connexion_admin.transaction():
		existe = connexion_admin.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (utilisateur,)).fetchone()
		if existe is None:
			connexion_admin.execute(sql.SQL("CREATE ROLE {} LOGIN").format(identifiant))
		for role in roles:
			connexion_admin.execute(
				sql.SQL("GRANT {} TO {} WITH INHERIT FALSE, SET TRUE").format(sql.Identifier(role), identifiant)
			)
