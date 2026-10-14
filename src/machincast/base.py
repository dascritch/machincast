"""Accès à la base PostgreSQL et application des migrations yoyo."""

from pathlib import Path
from urllib.parse import quote

from yoyo import get_backend, read_migrations

REPERTOIRE_MIGRATIONS = Path(__file__).parent / "migrations"
"""Migrations SQL livrées avec le paquet : 0001.nom.sql et son annulation 0001.nom.rollback.sql."""

TABLES: tuple[str, ...] = (
	"sonores",
	"marques_pages_streams",
	"banques",
	"banques_sonores",
	"evenements",
	"evenements_elements",
	"airplay",
	"log",
)
"""Tables créées par les migrations, dans l'ordre de doc/spec.md § 3.1."""


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
