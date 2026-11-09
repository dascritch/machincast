"""Une indexation complète : parcours des répertoires des banques, puis vérification des sonores (spec § 6).

Le parcours enregistre les nouveaux fichiers à l'état apercu (https://github.com/dascritch/machincast/issues/9) ;
la vérification qui suit les décode dans le même passage, en indexation rapide comme en audit complet
(https://github.com/dascritch/machincast/issues/69).

Une seule indexation rapide et un seul audit complet à la fois sur une base, qu'ils viennent d'un terminal ou de
l'interface : chacun tient le verrou consultatif de PostgreSQL de son mode (LOCKS) pendant tout son passage
(https://github.com/dascritch/machincast/issues/120). Une indexation rapide et un audit complet tournent donc en même
temps, et l'audit d'un sonore nommé (index_sound, Machin indexer --sound) ne prend aucun verrou : Machin player le
demande pour le prochain sonore qu'il va jouer, même pendant une indexation générale
(https://github.com/dascritch/machincast/issues/401). Deux parcours qui trouvent le même nouveau fichier ne
l'enregistrent qu'une fois (machincast.indexer.directories.DIRECTORIES_LOCK). Une indexation peut être arrêtée entre
deux fichiers (arret) : sa fenêtre de journal le demande quand on la ferme.
"""

import threading

import psycopg
from psycopg.rows import TupleRow

from machincast.configuration import SILENCE_THRESHOLD
from machincast.i18n import _
from machincast.indexer.check import Report, check_sounds
from machincast.indexer.decoding import Checker, check_file
from machincast.indexer.directories import attach_in_waiting, index_directories, remove_outside_durations

QUICK_LOCK = 0x4D616368_696E6478
"""Clé du verrou consultatif de l'indexation rapide, propre à MachinCast : « Machindx »."""
FULL_LOCK = 0x4D616368_61756474
"""Clé du verrou consultatif de l'audit complet : « Machaudt » (https://github.com/dascritch/machincast/issues/401)."""
LOCKS = {False: QUICK_LOCK, True: FULL_LOCK}
"""Le verrou de chaque mode, selon full_audit."""
ONGOING = {
	False: _("another quick indexing is running on this database"),
	True: _("another full audit is running on this database"),
}


class OngoingIndexing(Exception):
	"""Une autre indexation du même mode tient son verrou sur la base : celle-ci ne commence pas."""


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
	Lève OngoingIndexing si une autre indexation du même mode tourne sur la base, UnavailableDecoder si GStreamer ne
	sait pas décoder un format.
	"""
	lock = LOCKS[full_audit]
	with connection.transaction():
		taken = connection.execute("SELECT pg_try_advisory_lock(%s)", (lock,)).fetchone()
	assert taken is not None
	if not taken[0]:
		raise OngoingIndexing(ONGOING[full_audit])
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
			connection.execute("SELECT pg_advisory_unlock(%s)", (lock,))
	return report


def index_sound(
	connection: psycopg.Connection[TupleRow],
	sound: int,
	full_audit: bool = False,
	silence_threshold: float = SILENCE_THRESHOLD,
	force: bool = False,
) -> Report:
	"""Machin_indexer --sound N (https://github.com/dascritch/machincast/issues/181) : vérifie ce seul sonore, sans
	parcours ni verrou, même pendant une indexation rapide ou un audit complet
	(https://github.com/dascritch/machincast/issues/401), puis le retire des banques dont il sort des durées
	(https://github.com/dascritch/machincast/issues/195)."""
	report = check_sounds(
		connection, full_audit=full_audit, identifiers=[sound], silence_threshold=silence_threshold, force=force
	)
	remove_outside_durations(connection, report, [sound])
	return report
