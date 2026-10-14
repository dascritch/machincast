"""Accès à la base PostgreSQL et application des migrations yoyo."""

from pathlib import Path
from urllib.parse import quote

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
