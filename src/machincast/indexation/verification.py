"""Vérification des sonores existants (https://github.com/dascritch/machincast/issues/7, spec § 6.1).

Deux modes (https://github.com/dascritch/machincast/issues/69) :

- indexation rapide, par défaut : seuls les sonores en aperçu (fichiers nouveaux, jamais vérifiés) sont décodés ;
  pour les autres, seule la présence du fichier est contrôlée, sans décodage ;
- audit complet : chaque sonore de type fichier est décodé en entier.

Les streams ne sont jamais vérifiés. Un fichier sain enregistre sa durée, la date de modification et la taille
du fichier. L'état du sonore suit le verdict (https://github.com/dascritch/machincast/issues/66) :

	apercu    + sain         →  actif
	apercu, actif + défectueux  →  errone, ou supprime si le fichier est introuvable
	errone    + sain         →  actif : l'indexeur rétablit ce qu'il a lui-même posé
	errone    + introuvable  →  supprime
	desactive, expire, supprime : jamais modifiés par l'indexeur, qui signale quand même le fichier défectueux

Un fichier sain met aussi à jour l'artiste, le titre et les clés de metadonnees_musicales tenues par l'indexeur,
depuis ses tags (https://github.com/dascritch/machincast/issues/8) ; un tag absent vide le champ correspondant.

Chaque fichier défectueux est signalé par son chemin, en anomalie (logging, niveau WARNING, sur la sortie
d'erreur). L'indexeur n'écrit jamais dans le log, et ne modifie jamais un champ listé dans champs_edites
(« metadonnees_musicales.<clé> » pour une clé des métadonnées musicales).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

from machincast.indexation.decodage import EtatFichier, Verification, verifier_fichier
from machincast.indexation.tags import fusionner

journal = logging.getLogger(__name__)


class EtatSonore(StrEnum):
	"""Valeurs du type etat_sonore (migration 0001.schema-initial)."""

	APERCU = "apercu"
	ACTIF = "actif"
	DESACTIVE = "desactive"
	EXPIRE = "expire"
	ERRONE = "errone"
	SUPPRIME = "supprime"


LIBELLES = {
	EtatSonore.APERCU: "aperçu",
	EtatSonore.ACTIF: "actif",
	EtatSonore.DESACTIVE: "désactivé",
	EtatSonore.EXPIRE: "expiré",
	EtatSonore.ERRONE: "erroné",
	EtatSonore.SUPPRIME: "supprimé",
}
"""Libellés accentués, pour les messages et l'interface."""


@dataclass
class Bilan:
	audit_complet: bool = False
	verifies: int = 0
	"""Sonores décodés."""
	errones: int = 0
	supprimes: int = 0
	retablis: int = 0
	"""Sonores erronés redevenus actifs."""
	sortis_apercu: int = 0


def _accorder(nombre: int, singulier: str, pluriel: str) -> str:
	"""Zéro et un s'accordent au singulier."""
	return f"{nombre} {pluriel if nombre > 1 else singulier}"


def texte_bilan(bilan: Bilan) -> str:
	"""« indexation rapide : 2 sonores vérifiés ; 1 erroné, 0 supprimé, 0 rétabli, 2 sortis d'aperçu ».

	Le nombre de sonores vérifiés est celui des sonores décodés ; les autres nombres comptent les changements d'état.
	"""
	mode = "audit complet" if bilan.audit_complet else "indexation rapide"
	return (
		f"{mode} : {_accorder(bilan.verifies, 'sonore vérifié', 'sonores vérifiés')} ; "
		f"{_accorder(bilan.errones, 'erroné', 'erronés')}, "
		f"{_accorder(bilan.supprimes, 'supprimé', 'supprimés')}, "
		f"{_accorder(bilan.retablis, 'rétabli', 'rétablis')}, "
		f"{_accorder(bilan.sortis_apercu, 'sorti', 'sortis')} d'aperçu"
	)


def nouvel_etat(etat: EtatSonore, verdict: EtatFichier) -> EtatSonore:
	"""État du sonore après la vérification de son fichier."""
	if etat not in (EtatSonore.APERCU, EtatSonore.ACTIF, EtatSonore.ERRONE):
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
	audit_complet: bool = False,
) -> Bilan:
	"""Vérifie les sonores de type fichier ; chaque sonore est enregistré dans sa propre transaction.

	En indexation rapide, seuls les sonores en aperçu sont décodés ; pour les autres, un fichier disparu est
	quand même repéré. En audit complet, tous sont décodés.

	La connexion doit avoir endossé le rôle de l'indexation (machincast.base.connecter). Lève
	DecodeurIndisponible si GStreamer ne sait pas décoder un format : les sonores déjà vérifiés le restent.
	"""
	with connexion.transaction():
		sonores = connexion.execute(
			"SELECT id, emplacement, etat::text, champs_edites, artiste, titre, metadonnees_musicales"
			" FROM sonores WHERE type = 'fichier' ORDER BY id"
		).fetchall()

	bilan = Bilan(audit_complet=audit_complet)
	for identifiant, emplacement, etat_texte, champs_edites, artiste, titre, metadonnees in sonores:
		chemin = Path(str(emplacement))
		avant = EtatSonore(str(etat_texte))
		decoder = audit_complet or avant is EtatSonore.APERCU
		if not decoder and chemin.exists():
			continue
		# Un fichier introuvable est déclaré tel sans décodage : l'indexation rapide repère donc les disparus.
		resultat = verifier(chemin)
		apres = nouvel_etat(avant, resultat.etat)
		fichier = _etat_du_fichier(chemin)
		modifie_le, taille = fichier if fichier is not None else (None, None)
		# La durée n'est enregistrée que pour un fichier sain, et jamais à la place d'une durée saisie à la main.
		sain = resultat.etat is EtatFichier.SAIN
		duree = resultat.duree if sain and "duree" not in champs_edites else None
		# Les tags d'un fichier défectueux ne sont pas lus : artiste, titre et métadonnées restent tels quels.
		if sain:
			artiste = artiste if "artiste" in champs_edites else resultat.tags.artiste
			titre = titre if "titre" in champs_edites else resultat.tags.titre
			metadonnees = fusionner(dict(metadonnees), resultat.tags.metadonnees, list(champs_edites))
		with connexion.transaction():
			# Un fichier introuvable garde la date et la taille de son dernier passage.
			connexion.execute(
				"UPDATE sonores SET etat = %s, duree = COALESCE(%s, duree),"
				" fichier_modifie_le = COALESCE(%s, fichier_modifie_le), fichier_taille = COALESCE(%s, fichier_taille),"
				" artiste = %s, titre = %s, metadonnees_musicales = %s"
				" WHERE id = %s",
				(apres.value, duree, modifie_le, taille, artiste, titre, Jsonb(metadonnees), identifiant),
			)
		if decoder:
			bilan.verifies += 1
		if avant is EtatSonore.APERCU and apres is not EtatSonore.APERCU:
			bilan.sortis_apercu += 1
		if apres != avant:
			if apres is EtatSonore.ERRONE:
				bilan.errones += 1
			elif apres is EtatSonore.SUPPRIME:
				bilan.supprimes += 1
			elif apres is EtatSonore.ACTIF and avant is EtatSonore.ERRONE:
				bilan.retablis += 1
		if resultat.etat is not EtatFichier.SAIN:
			journal.warning(f"{emplacement} : {resultat.probleme} ; {_consequence(avant, apres)}")
	return bilan
