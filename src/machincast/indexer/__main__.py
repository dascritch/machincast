"""Point d'entrée de Machin_indexer.

Parcours des répertoires des banques (https://github.com/dascritch/machincast/issues/9), puis vérification
des sonores (https://github.com/dascritch/machincast/issues/7), en indexation rapide par défaut ou en audit
complet (https://github.com/dascritch/machincast/issues/69). Avec --window, l'indexation montre son journal dans une
fenêtre, ligne par ligne : c'est ainsi que l'interface la lance, dans un processus à part
(https://github.com/dascritch/machincast/issues/120). Avec --sound, seul ce sonore est vérifié, sans parcours des
répertoires, sans verrou et sans document d'audit : c'est ainsi que Machin player fait analyser le prochain sonore
qu'il va jouer (https://github.com/dascritch/machincast/issues/181).
"""

import argparse
import logging
from collections.abc import Sequence

import psycopg

from machincast.cli import INVALID_CONFIGURATION_CODE, launch
from machincast.configuration import Configuration
from machincast.database import Role, open_connection
from machincast.indexer import audit
from machincast.indexer.check import report_text
from machincast.indexer.decoding import UnavailableDecoder
from machincast.indexer.indexer import OngoingIndexing, index, index_sound
from machincast.interface.__main__ import available_display

EXECUTABLE = "Machin_indexer"
DESCRIPTION = "Vérifie les sonores et indexe les répertoires des banques."

FAILURE_CODE = 1

# Nom explicite : lancé par python -m, ce module s'appelle __main__, hors du journal « machincast ».
log = logging.getLogger("machincast.indexer")


def own_options(analyser: argparse.ArgumentParser) -> None:
	analyser.add_argument(
		"--full-audit",
		action="store_true",
		help="décode tous les sonores ; par défaut, l'indexation rapide ne décode que les sonores en aperçu",
	)
	analyser.add_argument(
		"--force",
		action="store_true",
		help="avec --full-audit, décode aussi les sonores déjà audités au même seuil de silence, dont le fichier n'a"
		" pas changé depuis ; sans lui, l'audit complet les saute",
	)
	analyser.add_argument(
		"--window",
		action="store_true",
		help="montre le journal de l'indexation dans une fenêtre, ligne par ligne, comme le lance l'interface",
	)
	analyser.add_argument(
		"--sound",
		type=int,
		metavar="N",
		help="ne vérifie que le sonore N, sans parcourir les répertoires ni écrire de document d'audit ;"
		" avec --full-audit, son fichier est décodé s'il n'a pas déjà été audité, inchangé, au même seuil",
	)


def run(configuration: Configuration, options: argparse.Namespace) -> int:
	database = configuration.database
	if (options.sound is not None) and (options.window):
		log.error("--sound ne s'emploie pas avec --window")
		return INVALID_CONFIGURATION_CODE
	if (options.force) and (not options.full_audit):
		log.error("--force ne s'emploie qu'avec --full-audit")
		return INVALID_CONFIGURATION_CODE
	if options.sound is not None:
		return check_sound(configuration, options.sound, options.full_audit, options.force)
	if options.window:
		if not available_display():
			log.error("--window demande un affichage graphique : sans lui, lancer Machin indexer sans --window")
			return FAILURE_CODE
		# PySide6 n'est importé qu'ici : sans --window, l'indexation ne demande aucun affichage graphique.
		from machincast.interface.indexing_log import launch_window

		return launch_window(
			database.socket, database.production, options.full_audit, configuration.silences.threshold, options.force
		)
	start = audit.CLOCK.now()
	try:
		with open_connection(database.socket, database.production, Role.INDEXING) as connection:
			report = index(
				connection,
				full_audit=options.full_audit,
				silence_threshold=configuration.silences.threshold,
				force=options.force,
			)
	except psycopg.OperationalError as error:
		log.error(f"base de données injoignable ({database.production} par {database.socket}) : {error}")
		return FAILURE_CODE
	except psycopg.Error as error:
		log.error(f"erreur de base de données : {error}")
		return FAILURE_CODE
	except UnavailableDecoder as error:
		log.error(f"vérification interrompue : {error}")
		return FAILURE_CODE
	except OngoingIndexing as error:
		log.error(f"indexation refusée : {error}")
		return FAILURE_CODE
	log.info(report_text(report))
	audit.produce(report.anomalies, report_text(report), start)
	return 0


def check_sound(configuration: Configuration, sound: int, full_audit: bool, force: bool = False) -> int:
	"""Ce sonore seulement, s'il est un fichier : sans verrou, comme la vérification des fichiers ajoutés depuis
	l'interface, car une indexation en cours peut le vérifier aussi sans dommage."""
	database = configuration.database
	try:
		with open_connection(database.socket, database.production, Role.INDEXING) as connection:
			with connection.transaction():
				file = connection.execute("SELECT 1 FROM sounds WHERE id = %s AND type = 'file'", (sound,)).fetchone()
			if file is None:
				log.error(f"sonore {sound} : inconnu, ou pas un fichier")
				return FAILURE_CODE
			report = index_sound(connection, sound, full_audit, configuration.silences.threshold, force)
	except psycopg.OperationalError as error:
		log.error(f"base de données injoignable ({database.production} par {database.socket}) : {error}")
		return FAILURE_CODE
	except psycopg.Error as error:
		log.error(f"erreur de base de données : {error}")
		return FAILURE_CODE
	except UnavailableDecoder as error:
		log.error(f"vérification interrompue : {error}")
		return FAILURE_CODE
	log.info(report_text(report))
	return 0


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run, own_options)


if __name__ == "__main__":
	raise SystemExit(main())
