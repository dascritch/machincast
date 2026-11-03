"""Une indexation complète : parcours des répertoires des banques, puis vérification des sonores (spec § 6).

Le parcours enregistre les nouveaux fichiers à l'état apercu (https://github.com/dascritch/machincast/issues/9) ;
la vérification qui suit les décode dans le même passage, en indexation rapide comme en audit complet
(https://github.com/dascritch/machincast/issues/69).

Une seule indexation à la fois sur une base, qu'elle vienne d'un terminal ou de l'interface : l'indexation tient un
verrou consultatif de PostgreSQL (VERROU) pendant tout son passage. Une indexation peut être arrêtée entre deux
fichiers (arret) : sa fenêtre de journal le demande quand on la ferme
(https://github.com/dascritch/machincast/issues/120).
"""

import threading

import psycopg
from psycopg.rows import TupleRow

from machincast.configuration import SILENCE_THRESHOLD
from machincast.i18n import _
from machincast.indexer.check import Report, check_sounds
from machincast.indexer.decoding import Checker, check_file
from machincast.indexer.directories import attach_in_waiting, index_directories, remove_outside_durations

LOCK = 0x4D616368_696E6478
"""Clé du verrou consultatif de l'indexation, propre à MachinCast : « Machindx »."""


class OngoingIndexing(Exception):
	"""Une autre indexation tient le verrou de la base : celle-ci ne commence pas."""


def index(
	connection: psycopg.Connection[TupleRow],
	full_audit: bool = False,
	check: Checker = check_file,
	stop: threading.Event | None = None,
	silence_threshold: float = SILENCE_THRESHOLD,
	force: bool = False,
) -> Report:
	"""Parcourt les répertoires des banques, puis vérifie les sonores ; renvoie le bilan des deux étapes.

	forcer : l'audit complet décode aussi les sonores déjà audités et inchangés
	(https://github.com/dascritch/machincast/issues/206).

	arret : une fois posé, l'indexation s'arrête après le fichier en cours ; le travail fait est gardé.
	silence_threshold : seuil de silence de l'audit complet, en dB crête (https://github.com/dascritch/machincast/issues/146).
	Lève OngoingIndexing si une autre indexation tourne sur la base, UnavailableDecoder si GStreamer ne sait
	pas décoder un format.
	"""
	with connection.transaction():
		taken = connection.execute("SELECT pg_try_advisory_lock(%s)", (LOCK,)).fetchone()
	assert taken is not None
	if not taken[0]:
		raise OngoingIndexing(_("another indexing is running on this database"))
	try:
		report = Report(full_audit=full_audit)
		scan = index_directories(connection, report, stop)
		check_sounds(connection, check, full_audit, report, stop=stop, silence_threshold=silence_threshold, force=force)
		# Les durées vérifiées, les sonores en attente n'entrent que dans les banques dont ils sont dans les durées,
		# même après un arrêt (https://github.com/dascritch/machincast/issues/210) ; puis chaque banque ne garde que les
		# sonores dans ses durées, sauf après un arrêt (https://github.com/dascritch/machincast/issues/195).
		attach_in_waiting(connection, report, scan)
		if (stop is None) or (not stop.is_set()):
			remove_outside_durations(connection, report)
	finally:
		with connection.transaction():
			connection.execute("SELECT pg_advisory_unlock(%s)", (LOCK,))
	return report


def index_sound(
	connection: psycopg.Connection[TupleRow],
	sound: int,
	full_audit: bool = False,
	silence_threshold: float = SILENCE_THRESHOLD,
	force: bool = False,
) -> Report:
	"""Machin_indexer --sound N (https://github.com/dascritch/machincast/issues/181) : vérifie ce seul sonore, sans
	parcours ni verrou, puis le retire des banques dont il sort des durées
	(https://github.com/dascritch/machincast/issues/195)."""
	report = check_sounds(
		connection, full_audit=full_audit, identifiers=[sound], silence_threshold=silence_threshold, force=force
	)
	remove_outside_durations(connection, report, [sound])
	return report
