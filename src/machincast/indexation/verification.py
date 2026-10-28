"""Vérification des sonores existants (https://github.com/dascritch/machincast/issues/7, spec § 6.1).

Deux modes (https://github.com/dascritch/machincast/issues/69) :

- indexation rapide, par défaut : seuls les sonores en aperçu (fichiers nouveaux, jamais vérifiés) sont décodés ;
  pour les autres, seule la présence du fichier est contrôlée, sans décodage ;
- audit complet : chaque sonore de type fichier est décodé en entier, silences mesurés, sauf s'il a déjà été audité au
  même seuil de silence et que son fichier n'a pas changé depuis (https://github.com/dascritch/machincast/issues/206) :
  sonores.audite_le et sonores.audit_seuil gardent son dernier audit ; forcer décode tout.

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
import threading
from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

from machincast.configuration import SEUIL_DE_SILENCE
from machincast.conversion import duree_ou_rien, liste_ou_rien
from machincast.empreinte import etat_du_fichier, modifie
from machincast.indexation.audit import Anomalie
from machincast.indexation.decodage import EtatFichier, Verificateur, Verification, verifier_fichier
from machincast.indexation.tags import fusionner
from machincast.indexation.type_fichier import Nature, nature, type_mime

journal = logging.getLogger(__name__)


class EtatSonore(StrEnum):
	"""Valeurs du type etat_sonore (migration 0001.schema-initial)."""

	APERCU = "apercu"
	ACTIF = "actif"
	DESACTIVE = "desactive"
	EXPIRE = "expire"
	ERRONE = "errone"
	NON_SUPPORTE = "non_supporte"
	"""Le fichier n'est pas du son (https://github.com/dascritch/machincast/issues/121, état non_supporte)."""
	SUPPRIME = "supprime"


LIBELLES = {
	EtatSonore.APERCU: "aperçu",
	EtatSonore.ACTIF: "actif",
	EtatSonore.DESACTIVE: "désactivé",
	EtatSonore.EXPIRE: "expiré",
	EtatSonore.ERRONE: "erroné",
	EtatSonore.NON_SUPPORTE: "non supporté",
	EtatSonore.SUPPRIME: "supprimé",
}
"""Libellés accentués, pour les messages et l'interface."""


@dataclass
class Bilan:
	audit_complet: bool = False
	nouveaux: int = 0
	"""Fichiers trouvés dans les répertoires des banques et enregistrés comme nouveaux sonores."""
	rattaches: int = 0
	"""Sonores déjà connus, ajoutés à une banque dont ils n'étaient pas membres."""
	retraits: int = 0
	"""Sonores retirés d'une banque dont ils sortent des durées (https://github.com/dascritch/machincast/issues/195)."""
	verifies: int = 0
	"""Sonores décodés."""
	errones: int = 0
	non_supportes: int = 0
	"""Sonores passés non supportés : leur fichier n'est pas du son."""
	supprimes: int = 0
	retablis: int = 0
	"""Sonores erronés redevenus actifs."""
	sortis_apercu: int = 0
	deja_audites: list[int] = field(default_factory=list)
	"""Sonores dont l'audit complet est sauté : déjà audités au même seuil, fichier inchangé
	(https://github.com/dascritch/machincast/issues/206)."""
	anomalies: list[Anomalie] = field(default_factory=list)
	"""Les fichiers défectueux du passage, pour le document d'audit (https://github.com/dascritch/machincast/issues/11)."""


def _accorder(nombre: int, singulier: str, pluriel: str) -> str:
	"""Zéro et un s'accordent au singulier."""
	return f"{nombre} {pluriel if nombre > 1 else singulier}"


def texte_bilan(bilan: Bilan) -> str:
	"""« indexation rapide : 2 nouveaux sonores, 0 rattachement, 0 retrait ; 2 sonores vérifiés ; … ».

	Les nouveaux sonores et les rattachements viennent du parcours des répertoires des banques, les retraits des durées
	des banques (https://github.com/dascritch/machincast/issues/195) ; le nombre de
	sonores vérifiés est celui des sonores décodés ; les autres nombres comptent les changements d'état.
	"""
	mode = "audit complet" if bilan.audit_complet else "indexation rapide"
	return (
		f"{mode} : {_accorder(bilan.nouveaux, 'nouveau sonore', 'nouveaux sonores')}, "
		f"{_accorder(bilan.rattaches, 'rattachement', 'rattachements')}, "
		f"{_accorder(bilan.retraits, 'retrait', 'retraits')} ; "
		f"{_accorder(bilan.verifies, 'sonore vérifié', 'sonores vérifiés')} ; "
		f"{_accorder(bilan.errones, 'erroné', 'erronés')}, "
		f"{_accorder(bilan.non_supportes, 'non supporté', 'non supportés')}, "
		f"{_accorder(bilan.supprimes, 'supprimé', 'supprimés')}, "
		f"{_accorder(bilan.retablis, 'rétabli', 'rétablis')}, "
		f"{_accorder(bilan.sortis_apercu, 'sorti', 'sortis')} d'aperçu"
	)


def nouvel_etat(etat: EtatSonore, verdict: EtatFichier) -> EtatSonore:
	"""État du sonore après la vérification de son fichier."""
	if etat not in (EtatSonore.APERCU, EtatSonore.ACTIF, EtatSonore.ERRONE, EtatSonore.NON_SUPPORTE):
		return etat
	if verdict is EtatFichier.SAIN:
		return EtatSonore.ACTIF
	if verdict is EtatFichier.INTROUVABLE:
		return EtatSonore.SUPPRIME
	if verdict is EtatFichier.NON_SUPPORTE:
		return EtatSonore.NON_SUPPORTE
	return EtatSonore.ERRONE


def _consequence(avant: EtatSonore, apres: EtatSonore) -> str:
	if avant == apres:
		if avant in (EtatSonore.ERRONE, EtatSonore.NON_SUPPORTE):
			return f"sonore toujours {LIBELLES[avant]}"
		return f"état {LIBELLES[avant]} conservé"
	return f"sonore passé {LIBELLES[apres]}"


def verifier_sonores(
	connexion: psycopg.Connection[TupleRow],
	verifier: Verificateur = verifier_fichier,
	audit_complet: bool = False,
	bilan: Bilan | None = None,
	identifiants: Collection[int] | None = None,
	arret: threading.Event | None = None,
	seuil_silences: float = SEUIL_DE_SILENCE,
	forcer: bool = False,
) -> Bilan:
	"""Vérifie les sonores de type fichier ; chaque sonore est enregistré dans sa propre transaction.

	Le bilan reçu, celui du parcours des répertoires (machincast.indexation.indexeur), est complété ; sans bilan,
	un nouveau est créé.

	En indexation rapide, seuls les sonores en aperçu, et ceux dont le fichier a changé depuis sa dernière
	vérification (date de modification ou taille), sont décodés ; pour les autres, un fichier disparu est quand même
	repéré. En audit complet, tous sont décodés. Un sonore dont l'interface a demandé l'audit complet
	(sonores.audit_demande, https://github.com/dascritch/machincast/issues/114) est audité en entier, silences compris,
	même en indexation rapide ; sa marque s'efface dès que son fichier est trouvé et vérifié.

	identifiants : seuls ces sonores, pour la vérification immédiate des fichiers que l'interface ajoute
	(https://github.com/dascritch/machincast/issues/30) ; tous les sonores sans eux.

	arret : une fois posé, la vérification s'arrête avant le sonore suivant.

	seuil_silences : en audit complet, le décodage d'un fichier sain mesure ses silences à ce seuil, en dB crête, et les
	enregistre, sauf ceux saisis à la main (https://github.com/dascritch/machincast/issues/146). L'indexation rapide ne
	les mesure que pour les sonores dont l'audit complet est demandé.

	Un audit complet, général, demandé ou d'un seul sonore, saute un sonore déjà audité au même seuil dont le fichier
	n'a pas changé depuis (deja_audite, https://github.com/dascritch/machincast/issues/206) ; sa demande tombe. Une
	ligne compte les sonores sautés. forcer : tous sont audités.

	La connexion doit avoir endossé le rôle de l'indexation (machincast.base.connecter). Lève
	DecodeurIndisponible si GStreamer ne sait pas décoder un format : les sonores déjà vérifiés le restent.
	"""
	with connexion.transaction():
		sonores = connexion.execute(
			"SELECT id, emplacement, etat::text, champs_edites, artiste, titre, metadonnees_musicales,"
			" fichier_modifie_le, fichier_taille, debut_detecte, fin_detectee, audit_demande, audite_le, audit_seuil"
			" FROM sonores WHERE type = 'fichier' AND supprime_le IS NULL AND (%s::bigint[] IS NULL OR id = ANY(%s))"
			" ORDER BY id",
			(liste_ou_rien(identifiants), liste_ou_rien(identifiants)),
		).fetchall()

	if bilan is None:
		bilan = Bilan(audit_complet=audit_complet)
	for ligne in sonores:
		if (arret is not None) and (arret.is_set()):
			break
		(
			identifiant,
			emplacement,
			etat_texte,
			champs_edites,
			artiste,
			titre,
			metadonnees,
			modifie_avant,
			taille_avant,
			debut_detecte,
			fin_detectee,
			demande,
			audite_le,
			audit_seuil,
		) = ligne
		chemin = Path(str(emplacement))
		avant = EtatSonore(str(etat_texte))
		audite = (audit_complet) or (demande is True)
		if (
			(audite)
			and (not forcer)
			and (deja_audite(chemin, modifie_avant, taille_avant, audite_le, audit_seuil, seuil_silences))
		):
			audite = False
			bilan.deja_audites.append(int(str(identifiant)))
		decoder = (audite) or (avant is EtatSonore.APERCU) or (modifie(chemin, modifie_avant, taille_avant))
		if (not decoder) and (chemin.exists()):
			if demande is True:
				# La demande est faite : le dernier audit vaut toujours.
				with connexion.transaction():
					connexion.execute("UPDATE sonores SET audit_demande = false WHERE id = %s", (identifiant,))
			continue
		# Un fichier introuvable est déclaré tel sans décodage : l'indexation rapide repère donc les disparus.
		# Un fichier dont le type n'est pas sonore n'est pas décodé non plus.
		type_du_fichier = type_mime(chemin)
		if (type_du_fichier is not None) and (nature(type_du_fichier) is Nature.NON_SONORE):
			resultat = Verification.defectueux(
				EtatFichier.NON_SUPPORTE, f"de type {type_du_fichier}, ce n'est pas un fichier sonore"
			)
		elif audite:
			resultat = verifier(chemin, seuil_silences=seuil_silences)
		else:
			resultat = verifier(chemin)
		apres = nouvel_etat(avant, resultat.etat)
		fichier = etat_du_fichier(chemin)
		modifie_le, taille = fichier if fichier is not None else (None, None)
		# La durée n'est enregistrée que pour un fichier sain, et jamais à la place d'une durée saisie à la main.
		sain = resultat.etat is EtatFichier.SAIN
		duree = resultat.duree if (sain) and ("duree" not in champs_edites) else None
		# Les tags d'un fichier défectueux ne sont pas lus : artiste, titre et métadonnées restent tels quels.
		if sain:
			artiste = artiste if "artiste" in champs_edites else resultat.tags.artiste
			titre = titre if "titre" in champs_edites else resultat.tags.titre
			metadonnees = fusionner(dict(metadonnees), resultat.tags.metadonnees, list(champs_edites))
		# Les silences mesurés remplacent ceux en base, sauf ceux saisis à la main ; sans mesure, rien ne change.
		if (sain) and (resultat.silences is not None):
			if "debut_detecte" not in champs_edites:
				debut_detecte = resultat.silences.debut
			if "fin_detectee" not in champs_edites:
				fin_detectee = resultat.silences.fin
		with connexion.transaction():
			# Un fichier introuvable garde la date et la taille de son dernier passage.
			connexion.execute(
				"UPDATE sonores SET etat = %s, duree = COALESCE(%s, duree),"
				" fichier_modifie_le = COALESCE(%s, fichier_modifie_le), fichier_taille = COALESCE(%s, fichier_taille),"
				" artiste = %s, titre = %s, metadonnees_musicales = %s, type_mime = COALESCE(%s, type_mime),"
				" verifie_le = CASE WHEN %s THEN clock_timestamp() ELSE verifie_le END,"
				" debut_detecte = %s, fin_detectee = %s, audit_demande = audit_demande AND NOT %s,"
				" audite_le = CASE WHEN %s THEN clock_timestamp() ELSE audite_le END,"
				" audit_seuil = CASE WHEN %s THEN %s ELSE audit_seuil END,"
				# La disparition du fichier est datée une fois ; un fichier revenu ne l'est plus
				# (https://github.com/dascritch/machincast/issues/267).
				" disparu_le = CASE WHEN %s THEN COALESCE(disparu_le, clock_timestamp()) END"
				" WHERE id = %s",
				(
					apres.value,
					duree,
					modifie_le,
					taille,
					artiste,
					titre,
					Jsonb(metadonnees),
					type_du_fichier,
					# Un fichier trouvé arrive ici vérifié en entier ; un fichier disparu garde la date de sa dernière
					# vérification.
					fichier is not None,
					duree_ou_rien(debut_detecte),
					duree_ou_rien(fin_detectee),
					# La marque d'un audit demandé tombe avec la vérification du fichier, pas avant.
					fichier is not None,
					# Un audit complet d'un fichier trouvé est retenu, avec son seuil, quel que soit le verdict.
					(audite) and (fichier is not None),
					(audite) and (fichier is not None),
					seuil_silences,
					apres is EtatSonore.SUPPRIME,
					identifiant,
				),
			)
		if decoder:
			bilan.verifies += 1
		if (avant is EtatSonore.APERCU) and (apres is not EtatSonore.APERCU):
			bilan.sortis_apercu += 1
		if apres != avant:
			if apres is EtatSonore.ERRONE:
				bilan.errones += 1
			elif apres is EtatSonore.NON_SUPPORTE:
				bilan.non_supportes += 1
			elif apres is EtatSonore.SUPPRIME:
				bilan.supprimes += 1
			elif (apres is EtatSonore.ACTIF) and (avant in (EtatSonore.ERRONE, EtatSonore.NON_SUPPORTE)):
				bilan.retablis += 1
		if resultat.etat is not EtatFichier.SAIN:
			consequence = _consequence(avant, apres)
			journal.warning(f"{emplacement} : {resultat.probleme} ; {consequence}")
			detail = str(resultat.probleme).removeprefix(f"{resultat.etat} : ")
			bilan.anomalies.append(Anomalie(str(emplacement), str(resultat.etat), detail, consequence))
		else:
			journal.info(f"{emplacement} : {_sain(artiste, titre)} ; {_consequence(avant, apres)}")
	if bilan.deja_audites:
		journal.info(_deja_audites(len(bilan.deja_audites), seuil_silences))
	return bilan


def deja_audite(
	chemin: Path, modifie_avant: object, taille_avant: object, audite_le: object, audit_seuil: object, seuil: float
) -> bool:
	"""Le sonore a déjà eu un audit complet à ce seuil, et son fichier n'a pas changé depuis : ni sa date de
	modification, plus ancienne que l'audit, ni sa date et sa taille, celles enregistrées
	(https://github.com/dascritch/machincast/issues/206)."""
	if (not isinstance(audite_le, datetime)) or (audit_seuil != seuil):
		return False
	fichier = etat_du_fichier(chemin)
	return (fichier is not None) and (fichier == (modifie_avant, taille_avant)) and (fichier[0] <= audite_le)


def texte_du_seuil(seuil: float) -> str:
	"""« -40 », « -55,5 » : un seuil de silence, en dB, à la française."""
	return f"{seuil:g}".replace(".", ",")


def _deja_audites(nombre: int, seuil: float) -> str:
	"""« 2 sonores déjà audités au seuil de -40 dB, aux fichiers inchangés : non décodés ; … »."""
	texte_seuil = texte_du_seuil(seuil)
	if nombre > 1:
		debut = f"{nombre} sonores déjà audités au seuil de {texte_seuil} dB, aux fichiers inchangés : non décodés"
	else:
		debut = f"{nombre} sonore déjà audité au seuil de {texte_seuil} dB, au fichier inchangé : non décodé"
	return f"{debut} ; --forcer décode tous les sonores"


def _sain(artiste: object, titre: object) -> str:
	"""« sain », suivi du nom du sonore quand il en a un : « sain, Les Gaufres – Café à minuit »."""
	nom = " – ".join(str(partie) for partie in (artiste, titre) if partie is not None)
	if nom == "":
		return "sain"
	return f"sain, {nom}"
