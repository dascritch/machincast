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
from collections.abc import Callable
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.indexation.decodage import Verification, verifier_fichier
from machincast.indexation.repertoires import indexer_repertoires
from machincast.indexation.verification import Bilan, verifier_sonores

VERROU = 0x4D616368_696E6478
"""Clé du verrou consultatif de l'indexation, propre à MachinCast : « Machindx »."""


class IndexationEnCours(Exception):
	"""Une autre indexation tient le verrou de la base : celle-ci ne commence pas."""


def indexer(
	connexion: psycopg.Connection[TupleRow],
	audit_complet: bool = False,
	verifier: Callable[[Path], Verification] = verifier_fichier,
	arret: threading.Event | None = None,
) -> Bilan:
	"""Parcourt les répertoires des banques, puis vérifie les sonores ; renvoie le bilan des deux étapes.

	arret : une fois posé, l'indexation s'arrête après le fichier en cours ; le travail fait est gardé.
	Lève IndexationEnCours si une autre indexation tourne sur la base, DecodeurIndisponible si GStreamer ne sait
	pas décoder un format.
	"""
	with connexion.transaction():
		pris = connexion.execute("SELECT pg_try_advisory_lock(%s)", (VERROU,)).fetchone()
	assert pris is not None
	if not pris[0]:
		raise IndexationEnCours("une autre indexation est en cours sur cette base")
	try:
		bilan = Bilan(audit_complet=audit_complet)
		indexer_repertoires(connexion, bilan, arret)
		verifier_sonores(connexion, verifier, audit_complet, bilan, arret=arret)
	finally:
		with connexion.transaction():
			connexion.execute("SELECT pg_advisory_unlock(%s)", (VERROU,))
	return bilan
