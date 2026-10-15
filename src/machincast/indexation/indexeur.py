"""Une indexation complète : parcours des répertoires des banques, puis vérification des sonores (spec § 6).

Le parcours enregistre les nouveaux fichiers à l'état apercu (https://github.com/dascritch/machincast/issues/9) ;
la vérification qui suit les décode dans le même passage, en indexation rapide comme en audit complet
(https://github.com/dascritch/machincast/issues/69).
"""

from collections.abc import Callable
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.indexation.decodage import Verification, verifier_fichier
from machincast.indexation.repertoires import indexer_repertoires
from machincast.indexation.verification import Bilan, verifier_sonores


def indexer(
	connexion: psycopg.Connection[TupleRow],
	audit_complet: bool = False,
	verifier: Callable[[Path], Verification] = verifier_fichier,
) -> Bilan:
	"""Parcourt les répertoires des banques, puis vérifie les sonores ; renvoie le bilan des deux étapes.

	Lève DecodeurIndisponible si GStreamer ne sait pas décoder un format.
	"""
	bilan = Bilan(audit_complet=audit_complet)
	indexer_repertoires(connexion, bilan)
	verifier_sonores(connexion, verifier, audit_complet, bilan)
	return bilan
