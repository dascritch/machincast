"""Vérification des sonores existants (https://github.com/dascritch/machincast/issues/7, spec § 6.1).

Chaque sonore de type fichier est décodé en entier. Un fichier sain met à jour la durée, la date de
modification et la taille du fichier ; un fichier endommagé, illisible ou introuvable désactive le
sonore et est signalé comme anomalie, par son chemin (logging, niveau WARNING, sur la sortie d'erreur).
Les streams ne sont jamais vérifiés.

L'indexeur n'écrit jamais dans le log et ne modifie pas un champ listé dans champs_edites, à une
exception près : un fichier défectueux désactive son sonore même si « actif » a été édité à la main,
pour qu'un fichier endommagé ne passe jamais à l'antenne.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.indexation.decodage import EtatFichier, Verification, verifier_fichier

journal = logging.getLogger(__name__)


@dataclass
class Bilan:
	verifies: int = 0
	desactives: int = 0


def texte_bilan(bilan: Bilan) -> str:
	"""« 2 sonores vérifiés, 1 désactivé » ; zéro et un s'accordent au singulier."""
	verifies = "sonores vérifiés" if bilan.verifies > 1 else "sonore vérifié"
	desactives = "désactivés" if bilan.desactives > 1 else "désactivé"
	return f"{bilan.verifies} {verifies}, {bilan.desactives} {desactives}"


def _etat_du_fichier(chemin: Path) -> tuple[datetime, int] | None:
	"""Date de modification et taille du fichier, ou None s'il est introuvable."""
	try:
		etat = chemin.stat()
	except OSError:
		return None
	return datetime.fromtimestamp(etat.st_mtime, tz=UTC), etat.st_size


def verifier_sonores(
	connexion: psycopg.Connection[TupleRow],
	verifier: Callable[[Path], Verification] = verifier_fichier,
) -> Bilan:
	"""Vérifie tous les sonores de type fichier ; chaque sonore est enregistré dans sa propre transaction.

	La connexion doit avoir endossé le rôle de l'indexation (machincast.base.connecter). Lève
	DecodeurIndisponible si GStreamer ne sait pas décoder un format : les sonores déjà vérifiés le restent.
	"""
	with connexion.transaction():
		sonores = connexion.execute(
			"SELECT id, emplacement, actif, champs_edites FROM sonores WHERE type = 'fichier' ORDER BY id"
		).fetchall()

	bilan = Bilan()
	for identifiant, emplacement, actif, champs_edites in sonores:
		chemin = Path(str(emplacement))
		resultat = verifier(chemin)
		fichier = _etat_du_fichier(chemin)
		modifie_le, taille = fichier if fichier is not None else (None, None)
		with connexion.transaction():
			if resultat.etat is EtatFichier.SAIN:
				duree = None if "duree" in champs_edites else resultat.duree
				connexion.execute(
					"UPDATE sonores SET duree = COALESCE(%s, duree), fichier_modifie_le = %s, fichier_taille = %s"
					" WHERE id = %s",
					(duree, modifie_le, taille, identifiant),
				)
			else:
				# Un fichier introuvable garde la date et la taille de son dernier passage.
				connexion.execute(
					"UPDATE sonores SET actif = false, fichier_modifie_le = COALESCE(%s, fichier_modifie_le),"
					" fichier_taille = COALESCE(%s, fichier_taille) WHERE id = %s",
					(modifie_le, taille, identifiant),
				)
		bilan.verifies += 1
		if resultat.etat is not EtatFichier.SAIN:
			consequence = "sonore désactivé" if actif else "sonore déjà inactif"
			journal.warning("%s : %s ; %s", emplacement, resultat.probleme, consequence)
			if actif:
				bilan.desactives += 1
	return bilan
