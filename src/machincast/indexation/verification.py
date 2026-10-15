"""Vérification des sonores existants (https://github.com/dascritch/machincast/issues/7, spec § 6.1).

Chaque sonore de type fichier est décodé en entier ; les streams ne sont jamais vérifiés. Un fichier sain
enregistre sa durée, la date de modification et la taille du fichier. L'état du sonore suit le verdict
(https://github.com/dascritch/machincast/issues/66) :

	actif     + défectueux   →  errone, ou supprime si le fichier est introuvable
	errone    + sain         →  actif : l'indexeur rétablit ce qu'il a lui-même posé
	errone    + introuvable  →  supprime
	desactive, expire, supprime : jamais modifiés par l'indexeur, qui signale quand même le fichier défectueux

Chaque fichier défectueux est signalé par son chemin, en anomalie (logging, niveau WARNING, sur la sortie
d'erreur). L'indexeur n'écrit jamais dans le log, et ne remplace pas une durée saisie à la main.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.indexation.decodage import EtatFichier, Verification, verifier_fichier

journal = logging.getLogger(__name__)


class EtatSonore(StrEnum):
	"""Valeurs du type etat_sonore (migration 0003.etat-sonores)."""

	ACTIF = "actif"
	DESACTIVE = "desactive"
	EXPIRE = "expire"
	ERRONE = "errone"
	SUPPRIME = "supprime"


LIBELLES = {
	EtatSonore.ACTIF: "actif",
	EtatSonore.DESACTIVE: "désactivé",
	EtatSonore.EXPIRE: "expiré",
	EtatSonore.ERRONE: "erroné",
	EtatSonore.SUPPRIME: "supprimé",
}
"""Libellés accentués, pour les messages et l'interface."""


@dataclass
class Bilan:
	verifies: int = 0
	errones: int = 0
	supprimes: int = 0
	retablis: int = 0


def _accorder(nombre: int, singulier: str, pluriel: str) -> str:
	"""Zéro et un s'accordent au singulier."""
	return f"{nombre} {pluriel if nombre > 1 else singulier}"


def texte_bilan(bilan: Bilan) -> str:
	"""« 2 sonores vérifiés : 1 erroné, 0 supprimé, 1 rétabli » ; compte les changements d'état du passage."""
	return (
		f"{_accorder(bilan.verifies, 'sonore vérifié', 'sonores vérifiés')} : "
		f"{_accorder(bilan.errones, 'erroné', 'erronés')}, "
		f"{_accorder(bilan.supprimes, 'supprimé', 'supprimés')}, "
		f"{_accorder(bilan.retablis, 'rétabli', 'rétablis')}"
	)


def nouvel_etat(etat: EtatSonore, verdict: EtatFichier) -> EtatSonore:
	"""État du sonore après la vérification de son fichier."""
	if etat not in (EtatSonore.ACTIF, EtatSonore.ERRONE):
		return etat
	if verdict is EtatFichier.SAIN:
		return EtatSonore.ACTIF
	if verdict is EtatFichier.INTROUVABLE:
		return EtatSonore.SUPPRIME
	return EtatSonore.ERRONE


def _consequence(avant: EtatSonore, apres: EtatSonore) -> str:
	if avant == apres:
		if avant is EtatSonore.ERRONE:
			return "sonore toujours erroné"
		return f"état {LIBELLES[avant]} conservé"
	return f"sonore passé {LIBELLES[apres]}"


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
			"SELECT id, emplacement, etat::text, champs_edites FROM sonores WHERE type = 'fichier' ORDER BY id"
		).fetchall()

	bilan = Bilan()
	for identifiant, emplacement, etat_texte, champs_edites in sonores:
		chemin = Path(str(emplacement))
		resultat = verifier(chemin)
		avant = EtatSonore(str(etat_texte))
		apres = nouvel_etat(avant, resultat.etat)
		fichier = _etat_du_fichier(chemin)
		modifie_le, taille = fichier if fichier is not None else (None, None)
		# La durée n'est enregistrée que pour un fichier sain, et jamais à la place d'une durée saisie à la main.
		duree = resultat.duree if resultat.etat is EtatFichier.SAIN and "duree" not in champs_edites else None
		with connexion.transaction():
			# Un fichier introuvable garde la date et la taille de son dernier passage.
			connexion.execute(
				"UPDATE sonores SET etat = %s, duree = COALESCE(%s, duree),"
				" fichier_modifie_le = COALESCE(%s, fichier_modifie_le), fichier_taille = COALESCE(%s, fichier_taille)"
				" WHERE id = %s",
				(apres.value, duree, modifie_le, taille, identifiant),
			)
		bilan.verifies += 1
		if apres != avant:
			if apres is EtatSonore.ERRONE:
				bilan.errones += 1
			elif apres is EtatSonore.SUPPRIME:
				bilan.supprimes += 1
			elif apres is EtatSonore.ACTIF:
				bilan.retablis += 1
		if resultat.etat is not EtatFichier.SAIN:
			journal.warning("%s : %s ; %s", emplacement, resultat.probleme, _consequence(avant, apres))
	return bilan
