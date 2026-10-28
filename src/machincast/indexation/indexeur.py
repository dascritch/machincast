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

from machincast.configuration import SEUIL_DE_SILENCE
from machincast.indexation.decodage import Verificateur, verifier_fichier
from machincast.indexation.repertoires import indexer_repertoires, rattacher_en_attente, retirer_hors_durees
from machincast.indexation.verification import Bilan, verifier_sonores

VERROU = 0x4D616368_696E6478
"""Clé du verrou consultatif de l'indexation, propre à MachinCast : « Machindx »."""


class IndexationEnCours(Exception):
	"""Une autre indexation tient le verrou de la base : celle-ci ne commence pas."""


def indexer(
	connexion: psycopg.Connection[TupleRow],
	audit_complet: bool = False,
	verifier: Verificateur = verifier_fichier,
	arret: threading.Event | None = None,
	seuil_silences: float = SEUIL_DE_SILENCE,
	forcer: bool = False,
) -> Bilan:
	"""Parcourt les répertoires des banques, puis vérifie les sonores ; renvoie le bilan des deux étapes.

	forcer : l'audit complet décode aussi les sonores déjà audités et inchangés
	(https://github.com/dascritch/machincast/issues/206).

	arret : une fois posé, l'indexation s'arrête après le fichier en cours ; le travail fait est gardé.
	seuil_silences : seuil de silence de l'audit complet, en dB crête (https://github.com/dascritch/machincast/issues/146).
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
		parcours = indexer_repertoires(connexion, bilan, arret)
		verifier_sonores(
			connexion, verifier, audit_complet, bilan, arret=arret, seuil_silences=seuil_silences, forcer=forcer
		)
		# Les durées vérifiées, les sonores en attente n'entrent que dans les banques dont ils sont dans les durées,
		# même après un arrêt (https://github.com/dascritch/machincast/issues/210) ; puis chaque banque ne garde que les
		# sonores dans ses durées, sauf après un arrêt (https://github.com/dascritch/machincast/issues/195).
		rattacher_en_attente(connexion, bilan, parcours)
		if (arret is None) or (not arret.is_set()):
			retirer_hors_durees(connexion, bilan)
	finally:
		with connexion.transaction():
			connexion.execute("SELECT pg_advisory_unlock(%s)", (VERROU,))
	return bilan


def indexer_un_sonore(
	connexion: psycopg.Connection[TupleRow],
	sonore: int,
	audit_complet: bool = False,
	seuil_silences: float = SEUIL_DE_SILENCE,
	forcer: bool = False,
) -> Bilan:
	"""Machin_indexation --sonore N (https://github.com/dascritch/machincast/issues/181) : vérifie ce seul sonore, sans
	parcours ni verrou, puis le retire des banques dont il sort des durées
	(https://github.com/dascritch/machincast/issues/195)."""
	bilan = verifier_sonores(
		connexion, audit_complet=audit_complet, identifiants=[sonore], seuil_silences=seuil_silences, forcer=forcer
	)
	retirer_hors_durees(connexion, bilan, [sonore])
	return bilan
