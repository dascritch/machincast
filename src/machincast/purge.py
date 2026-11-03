"""Purge de la base de données : Machin purge (https://github.com/dascritch/machincast/issues/268).

Efface de la base de production ce qui dépasse la durée de péremption (database.retention de la configuration, 60 jours
par défaut, réglable aussi dans Fichier → Préférences… de l'interface), comptée depuis l'heure du lancement :

- les passages de l'airplay finis avant la limite : un passage commencé avant et fini après reste entier ;
- les lignes du log d'avant la limite ;
- les sonores, banques, séquences et événements supprimés depuis l'interface avant la limite
  (https://github.com/dascritch/machincast/issues/267) ;
- les sonores dont l'indexation a constaté la disparition du fichier avant la limite.
- les sessions sautées des événements récurrents d'avant la limite (https://github.com/dascritch/machincast/issues/273),
  sans les compter dans le bilan.

Les passages plus récents d'un sonore effacé gardent l'emplacement, l'artiste et le titre recopiés lors du passage.
Tout est effacé en une seule transaction ; le bilan va au journal et, ligne « purge », au log de la base. Seules des
lignes de la base sont effacées : jamais un fichier sonore, ni un répertoire
(https://github.com/dascritch/machincast/issues/96).

Le compte de MachinCast est propriétaire de la base et de ses tables : il efface sans endosser de rôle, aucun des
trois rôles n'ayant le droit d'effacer l'airplay ou le log. install.sh --service installe un minuteur systemd qui
lance la purge chaque jour à midi. Le code de sortie est 0 si la purge s'est faite, 1 sinon.
"""

import argparse
import logging
from collections.abc import Sequence
from datetime import datetime, timedelta

import psycopg

from machincast.cli import launch
from machincast.clock import Clock, SystemClock
from machincast.configuration import Configuration

EXECUTABLE = "Machin_purge"
DESCRIPTION = "Efface de la base de données ce qui dépasse la durée de péremption."
FAILURE_CODE = 1
CLOCK: Clock = SystemClock()
"""L'heure d'où se compte la péremption ; les scénarios la fixent."""

# Nom explicite : lancé par son script, ce module garde le journal « machincast ».
log = logging.getLogger("machincast.purge")

PLAYS = """
	DELETE FROM airplay WHERE play_id IN (
		SELECT play_id FROM airplay GROUP BY play_id HAVING max(logged_at) < %s
	) RETURNING play_id
"""
ITEMS = (
	# LEAST ignore les valeurs vides : la suppression, ou la disparition du fichier, que l'indexation ne date que pour
	# un sonore à l'état supprime, et efface quand le fichier revient.
	("sonore", "sounds", "LEAST(deleted_at, missing_at)"),
	("banque", "banks", "deleted_at"),
	("séquence", "sequences", "deleted_at"),
	("événement", "events", "deleted_at"),
)
"""Le genre, sa table, et la date d'où se compte la péremption d'une ligne."""


def _count(count: int, name: str, complement: str = "") -> str:
	"""« 0 sonore », « 1 sonore », « 2 sonores » : le pluriel français commence à deux."""
	if count > 1:
		name = f"{name}s"
	return f"{count} {name}{complement}"


def purge(connection: psycopg.Connection[tuple[object, ...]], limit: datetime) -> list[str]:
	"""Efface ce qui est d'avant la limite, dans la transaction de la connexion ; le bilan, genre par genre."""
	plays = {play for (play,) in connection.execute(PLAYS, (limit,)).fetchall()}
	lines = connection.execute("DELETE FROM log WHERE logged_at < %s", (limit,)).rowcount
	report = [_count(len(plays), "passage", " de l'airplay"), _count(lines, "ligne", " du log")]
	for category, table, date in ITEMS:
		erased_list = connection.execute(f"DELETE FROM {table} WHERE {date} < %s", (limit,)).rowcount  # noqa: S608
		report.append(_count(erased_list, category))
	# Une session sautée d'avant la limite ne compte plus pour rien (https://github.com/dascritch/machincast/issues/273).
	connection.execute("DELETE FROM event_skips WHERE day < %s", (limit.date(),))
	return report


def run(configuration: Configuration, _options: argparse.Namespace) -> int:
	database = configuration.database
	limit = (CLOCK.now() - timedelta(days=database.retention)).astimezone()
	try:
		with (
			psycopg.connect(host=str(database.socket), dbname=database.production) as connection,
			connection.transaction(),
		):
			report = purge(connection, limit)
			announces = (
				f"purge de la base {database.production}, au-delà de {database.retention} jours"
				f" (avant le {limit:%d/%m/%Y %H:%M}) : {', '.join(report)} effacés"
			)
			connection.execute("INSERT INTO log (level, kind, message) VALUES ('info', 'purge', %s)", (announces,))
	except psycopg.OperationalError as error:
		log.error(f"base de données injoignable ({database.production}) : {error} ; rien n'a été effacé")
		return FAILURE_CODE
	except psycopg.Error as error:
		log.error(f"erreur de base de données : {error} ; rien n'a été effacé")
		return FAILURE_CODE
	log.info(announces)
	return 0


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run)
