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
lance la purge chaque jour à midi. Le code de sortie est 0 si la purge s'est faite, 1 sinon. Le démarrage et la fin de
chaque purge sont notés au journal et au log de la base (machincast.runs).
"""

import argparse
import logging
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta

import psycopg

from machincast.cli import launch
from machincast.clock import Clock, SystemClock
from machincast.configuration import Configuration
from machincast.i18n import N_, N_counted, _, logged
from machincast.runs import Recording

EXECUTABLE = "Machin_purge"
DESCRIPTION = _("Erases from the database what exceeds the expiry duration.")
FAILURE_CODE = 1
RECORDING = Recording(role=None)
"""Le démarrage et la fin de la purge, dans le log, par le compte propriétaire de la base
(https://github.com/dascritch/machincast/issues/341)."""
CLOCK: Clock = SystemClock()
"""L'heure d'où se compte la péremption ; les scénarios la fixent."""

# Nom explicite : lancé par son script, ce module garde le journal « machincast ».
log = logging.getLogger("machincast.purge")

PLAYS = """
	WITH erased AS (
		DELETE FROM airplay WHERE play_id IN (
			SELECT play_id FROM airplay GROUP BY play_id HAVING max(logged_at) < %s
		) RETURNING play_id
	) SELECT count(DISTINCT play_id) FROM erased
"""
"""Efface les passages d'avant la limite et les compte, dans la base : ni leurs identifiants, ni leurs lignes ne
viennent jusqu'ici (https://github.com/dascritch/machincast/issues/390)."""
ITEMS: tuple[tuple[Callable[[int], str], str, str], ...] = (
	# LEAST ignore les valeurs vides : la suppression, ou la disparition du fichier, que l'indexation ne date que pour
	# un sonore à l'état supprime, et efface quand le fichier revient.
	(lambda n: N_counted("{count} sound", "{count} sounds", n), "sounds", "LEAST(deleted_at, missing_at)"),
	(lambda n: N_counted("{count} bank", "{count} banks", n), "banks", "deleted_at"),
	(lambda n: N_counted("{count} sequence", "{count} sequences", n), "sequences", "deleted_at"),
	(lambda n: N_counted("{count} event", "{count} events", n), "events", "deleted_at"),
)
"""Le décompte de chaque genre, en anglais pour le log, sa table, et la date d'où se compte la péremption d'une
ligne."""


def purge(connection: psycopg.Connection[tuple[object, ...]], limit: datetime) -> list[str]:
	"""Efface ce qui est d'avant la limite, dans la transaction de la connexion ; le bilan, genre par genre."""
	counted = connection.execute(PLAYS, (limit,)).fetchone()
	assert counted is not None
	plays = int(str(counted[0]))
	lines = connection.execute("DELETE FROM log WHERE logged_at < %s", (limit,)).rowcount
	report = [
		N_counted("{count} play of the airplay", "{count} plays of the airplay", plays),
		N_counted("{count} line of the log", "{count} lines of the log", lines),
	]
	for counting, table, date in ITEMS:
		erased_list = connection.execute(f"DELETE FROM {table} WHERE {date} < %s", (limit,)).rowcount  # noqa: S608
		report.append(counting(erased_list))
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
			announces = N_(
				"purge of database {production}, beyond {retention} days (before {limit}): {report} erased"
			).format(
				production=database.production,
				retention=database.retention,
				limit=f"{limit:%Y-%m-%d %H:%M}",
				report=", ".join(report),
			)
			connection.execute("INSERT INTO log (level, kind, message) VALUES ('info', 'purge', %s)", (announces,))
	except psycopg.OperationalError as error:
		log.error(
			_("database unreachable ({production}): {error}; nothing was erased").format(
				production=database.production, error=error
			)
		)
		return FAILURE_CODE
	except psycopg.Error as error:
		log.error(_("database error: {error}; nothing was erased").format(error=error))
		return FAILURE_CODE
	log.info(logged(announces))
	return 0


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run, recording=RECORDING)
