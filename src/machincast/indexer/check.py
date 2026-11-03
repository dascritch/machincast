"""Vérification des sonores existants (https://github.com/dascritch/machincast/issues/7, spec § 6.1).

Deux modes (https://github.com/dascritch/machincast/issues/69) :

- indexation rapide, par défaut : seuls les sonores en aperçu (fichiers nouveaux, jamais vérifiés) sont décodés ;
  pour les autres, seule la présence du fichier est contrôlée, sans décodage ;
- audit complet : chaque sonore de type fichier est décodé en entier, silences mesurés, sauf s'il a déjà été audité au
  même seuil de silence et que son fichier n'a pas changé depuis (https://github.com/dascritch/machincast/issues/206) :
  sounds.audited_at et sounds.audit_threshold gardent son dernier audit ; forcer décode tout.

Les streams ne sont jamais vérifiés. Un fichier sain enregistre sa durée, la date de modification et la taille
du fichier. L'état du sonore suit le verdict (https://github.com/dascritch/machincast/issues/66) :

	apercu    + sain         →  actif
	apercu, actif + défectueux  →  errone, ou supprime si le fichier est introuvable
	errone    + sain         →  actif : l'indexeur rétablit ce qu'il a lui-même posé
	errone    + introuvable  →  supprime
	desactive, expire, supprime : jamais modifiés par l'indexeur, qui signale quand même le fichier défectueux

Un fichier sain met aussi à jour l'artiste, le titre et les clés de music_metadata tenues par l'indexeur,
depuis ses tags (https://github.com/dascritch/machincast/issues/8) ; un tag absent vide le champ correspondant.

Chaque fichier défectueux est signalé par son chemin, en anomalie (logging, niveau WARNING, sur la sortie
d'erreur). L'indexeur n'écrit jamais dans le log, et ne modifie jamais un champ listé dans edited_fields
(« music_metadata.<clé> » pour une clé des métadonnées musicales).
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

from machincast.configuration import SILENCE_THRESHOLD
from machincast.conversion import duration_or_none, list_or_none
from machincast.fingerprint import file_state, modified
from machincast.indexer.audit import Anomaly
from machincast.indexer.decoding import Check, Checker, FileState, check_file
from machincast.indexer.file_type import Kind, kind, type_mime
from machincast.indexer.tags import merge

log = logging.getLogger(__name__)


class SoundState(StrEnum):
	"""Valeurs du type sound_state (migration 0001.initial-schema)."""

	PREVIEW = "preview"
	ACTIVE = "active"
	DISABLED = "disabled"
	EXPIRED = "expired"
	CORRUPT = "corrupt"
	UNSUPPORTED = "unsupported"
	"""Le fichier n'est pas du son (https://github.com/dascritch/machincast/issues/121, état non_supporte)."""
	DELETED = "missing"


LABELS = {
	SoundState.PREVIEW: "aperçu",
	SoundState.ACTIVE: "actif",
	SoundState.DISABLED: "désactivé",
	SoundState.EXPIRED: "expiré",
	SoundState.CORRUPT: "erroné",
	SoundState.UNSUPPORTED: "non supporté",
	SoundState.DELETED: "supprimé",
}
"""Libellés accentués, pour les messages et l'interface."""


@dataclass
class Report:
	full_audit: bool = False
	new_list: int = 0
	"""Fichiers trouvés dans les répertoires des banques et enregistrés comme nouveaux sonores."""
	attached_list: int = 0
	"""Sonores déjà connus, ajoutés à une banque dont ils n'étaient pas membres."""
	removals: int = 0
	"""Sonores retirés d'une banque dont ils sortent des durées (https://github.com/dascritch/machincast/issues/195)."""
	checked_list: int = 0
	"""Sonores décodés."""
	corrupt_list: int = 0
	not_supported: int = 0
	"""Sonores passés non supportés : leur fichier n'est pas du son."""
	deleted_list: int = 0
	restored: int = 0
	"""Sonores erronés redevenus actifs."""
	exited_preview: int = 0
	already_audited: list[int] = field(default_factory=list)
	"""Sonores dont l'audit complet est sauté : déjà audités au même seuil, fichier inchangé
	(https://github.com/dascritch/machincast/issues/206)."""
	anomalies: list[Anomaly] = field(default_factory=list)
	"""Les fichiers défectueux du passage, pour le document d'audit (https://github.com/dascritch/machincast/issues/11)."""


def _grant(count: int, singular: str, plural: str) -> str:
	"""Zéro et un s'accordent au singulier."""
	return f"{count} {plural if count > 1 else singular}"


def report_text(report: Report) -> str:
	"""« indexation rapide : 2 nouveaux sonores, 0 rattachement, 0 retrait ; 2 sonores vérifiés ; … ».

	Les nouveaux sonores et les rattachements viennent du parcours des répertoires des banques, les retraits des durées
	des banques (https://github.com/dascritch/machincast/issues/195) ; le nombre de
	sonores vérifiés est celui des sonores décodés ; les autres nombres comptent les changements d'état.
	"""
	mode = "audit complet" if report.full_audit else "indexation rapide"
	return (
		f"{mode} : {_grant(report.new_list, 'nouveau sonore', 'nouveaux sonores')}, "
		f"{_grant(report.attached_list, 'rattachement', 'rattachements')}, "
		f"{_grant(report.removals, 'retrait', 'retraits')} ; "
		f"{_grant(report.checked_list, 'sonore vérifié', 'sonores vérifiés')} ; "
		f"{_grant(report.corrupt_list, 'erroné', 'erronés')}, "
		f"{_grant(report.not_supported, 'non supporté', 'non supportés')}, "
		f"{_grant(report.deleted_list, 'supprimé', 'supprimés')}, "
		f"{_grant(report.restored, 'rétabli', 'rétablis')}, "
		f"{_grant(report.exited_preview, 'sorti', 'sortis')} d'aperçu"
	)


def new_state(state: SoundState, verdict: FileState) -> SoundState:
	"""État du sonore après la vérification de son fichier."""
	if state not in (SoundState.PREVIEW, SoundState.ACTIVE, SoundState.CORRUPT, SoundState.UNSUPPORTED):
		return state
	if verdict is FileState.HEALTHY:
		return SoundState.ACTIVE
	if verdict is FileState.NOT_FOUND:
		return SoundState.DELETED
	if verdict is FileState.UNSUPPORTED:
		return SoundState.UNSUPPORTED
	return SoundState.CORRUPT


def _consequence(before: SoundState, after: SoundState) -> str:
	if before == after:
		if before in (SoundState.CORRUPT, SoundState.UNSUPPORTED):
			return f"sonore toujours {LABELS[before]}"
		return f"état {LABELS[before]} conservé"
	return f"sonore passé {LABELS[after]}"


def check_sounds(
	connection: psycopg.Connection[TupleRow],
	check: Checker = check_file,
	full_audit: bool = False,
	report: Report | None = None,
	identifiers: Collection[int] | None = None,
	stop: threading.Event | None = None,
	silence_threshold: float = SILENCE_THRESHOLD,
	force: bool = False,
) -> Report:
	"""Vérifie les sonores de type fichier ; chaque sonore est enregistré dans sa propre transaction.

	Le bilan reçu, celui du parcours des répertoires (machincast.indexer.indexer), est complété ; sans bilan,
	un nouveau est créé.

	En indexation rapide, seuls les sonores en aperçu, et ceux dont le fichier a changé depuis sa dernière
	vérification (date de modification ou taille), sont décodés ; pour les autres, un fichier disparu est quand même
	repéré. En audit complet, tous sont décodés. Un sonore dont l'interface a demandé l'audit complet
	(sounds.audit_requested, https://github.com/dascritch/machincast/issues/114) est audité en entier, silences compris,
	même en indexation rapide ; sa marque s'efface dès que son fichier est trouvé et vérifié.

	identifiants : seuls ces sonores, pour la vérification immédiate des fichiers que l'interface ajoute
	(https://github.com/dascritch/machincast/issues/30) ; tous les sonores sans eux.

	arret : une fois posé, la vérification s'arrête avant le sonore suivant.

	silence_threshold : en audit complet, le décodage d'un fichier sain mesure ses silences à ce seuil, en dB crête,
	et les
	enregistre, sauf ceux saisis à la main (https://github.com/dascritch/machincast/issues/146). L'indexation rapide ne
	les mesure que pour les sonores dont l'audit complet est demandé.

	Un audit complet, général, demandé ou d'un seul sonore, saute un sonore déjà audité au même seuil dont le fichier
	n'a pas changé depuis (already_audited, https://github.com/dascritch/machincast/issues/206) ; sa demande tombe. Une
	ligne compte les sonores sautés. forcer : tous sont audités.

	La connexion doit avoir endossé le rôle de l'indexation (machincast.database.open_connection). Lève
	UnavailableDecoder si GStreamer ne sait pas décoder un format : les sonores déjà vérifiés le restent.
	"""
	with connection.transaction():
		sounds = connection.execute(
			"SELECT id, location, state::text, edited_fields, artist, title, music_metadata,"
			" file_modified_at, file_size, detected_start, detected_end, audit_requested, audited_at, audit_threshold"
			" FROM sounds WHERE type = 'file' AND deleted_at IS NULL AND (%s::bigint[] IS NULL OR id = ANY(%s))"
			" ORDER BY id",
			(list_or_none(identifiers), list_or_none(identifiers)),
		).fetchall()

	if report is None:
		report = Report(full_audit=full_audit)
	for line in sounds:
		if (stop is not None) and (stop.is_set()):
			break
		(
			identifier,
			location,
			text_state,
			edited_fields,
			artist,
			title,
			metadata,
			modified_before,
			size_before,
			detected_start,
			detected_end,
			asks,
			audited_at,
			threshold_audit,
		) = line
		path = Path(str(location))
		before = SoundState(str(text_state))
		audited = (full_audit) or (asks is True)
		if (
			(audited)
			and (not force)
			and (already_audited(path, modified_before, size_before, audited_at, threshold_audit, silence_threshold))
		):
			audited = False
			report.already_audited.append(int(str(identifier)))
		decode = (audited) or (before is SoundState.PREVIEW) or (modified(path, modified_before, size_before))
		if (not decode) and (path.exists()):
			if asks is True:
				# La demande est faite : le dernier audit vaut toujours.
				with connection.transaction():
					connection.execute("UPDATE sounds SET audit_requested = false WHERE id = %s", (identifier,))
			continue
		# Un fichier introuvable est déclaré tel sans décodage : l'indexation rapide repère donc les disparus.
		# Un fichier dont le type n'est pas sonore n'est pas décodé non plus.
		file_type = type_mime(path)
		if (file_type is not None) and (kind(file_type) is Kind.NON_SOUND):
			result = Check.defective(FileState.UNSUPPORTED, f"de type {file_type}, ce n'est pas un fichier sonore")
		elif audited:
			result = check(path, silence_threshold=silence_threshold)
		else:
			result = check(path)
		after = new_state(before, result.state)
		file = file_state(path)
		modified_at, size = file if file is not None else (None, None)
		# La durée n'est enregistrée que pour un fichier sain, et jamais à la place d'une durée saisie à la main.
		healthy = result.state is FileState.HEALTHY
		duration = result.duration if (healthy) and ("duration" not in edited_fields) else None
		# Les tags d'un fichier défectueux ne sont pas lus : artiste, titre et métadonnées restent tels quels.
		if healthy:
			artist = artist if "artist" in edited_fields else result.tags.artist
			title = title if "title" in edited_fields else result.tags.title
			metadata = merge(dict(metadata), result.tags.metadata, list(edited_fields))
		# Les silences mesurés remplacent ceux en base, sauf ceux saisis à la main ; sans mesure, rien ne change.
		if (healthy) and (result.silences is not None):
			if "detected_start" not in edited_fields:
				detected_start = result.silences.start
			if "detected_end" not in edited_fields:
				detected_end = result.silences.end
		with connection.transaction():
			# Un fichier introuvable garde la date et la taille de son dernier passage.
			connection.execute(
				"UPDATE sounds SET state = %s, duration = COALESCE(%s, duration),"
				" file_modified_at = COALESCE(%s, file_modified_at), file_size = COALESCE(%s, file_size),"
				" artist = %s, title = %s, music_metadata = %s, mime_type = COALESCE(%s, mime_type),"
				" checked_at = CASE WHEN %s THEN clock_timestamp() ELSE checked_at END,"
				" detected_start = %s, detected_end = %s, audit_requested = audit_requested AND NOT %s,"
				" audited_at = CASE WHEN %s THEN clock_timestamp() ELSE audited_at END,"
				" audit_threshold = CASE WHEN %s THEN %s ELSE audit_threshold END,"
				# La disparition du fichier est datée une fois ; un fichier revenu ne l'est plus
				# (https://github.com/dascritch/machincast/issues/267).
				" missing_at = CASE WHEN %s THEN COALESCE(missing_at, clock_timestamp()) END"
				" WHERE id = %s",
				(
					after.value,
					duration,
					modified_at,
					size,
					artist,
					title,
					Jsonb(metadata),
					file_type,
					# Un fichier trouvé arrive ici vérifié en entier ; un fichier disparu garde la date de sa dernière
					# vérification.
					file is not None,
					duration_or_none(detected_start),
					duration_or_none(detected_end),
					# La marque d'un audit demandé tombe avec la vérification du fichier, pas avant.
					file is not None,
					# Un audit complet d'un fichier trouvé est retenu, avec son seuil, quel que soit le verdict.
					(audited) and (file is not None),
					(audited) and (file is not None),
					silence_threshold,
					after is SoundState.DELETED,
					identifier,
				),
			)
		if decode:
			report.checked_list += 1
		if (before is SoundState.PREVIEW) and (after is not SoundState.PREVIEW):
			report.exited_preview += 1
		if after != before:
			if after is SoundState.CORRUPT:
				report.corrupt_list += 1
			elif after is SoundState.UNSUPPORTED:
				report.not_supported += 1
			elif after is SoundState.DELETED:
				report.deleted_list += 1
			elif (after is SoundState.ACTIVE) and (before in (SoundState.CORRUPT, SoundState.UNSUPPORTED)):
				report.restored += 1
		if result.state is not FileState.HEALTHY:
			consequence = _consequence(before, after)
			log.warning(f"{location} : {result.problem} ; {consequence}")
			detail = str(result.problem).removeprefix(f"{result.state} : ")
			report.anomalies.append(Anomaly(str(location), str(result.state), detail, consequence))
		else:
			log.info(f"{location} : {_healthy(artist, title)} ; {_consequence(before, after)}")
	if report.already_audited:
		log.info(_already_audited(len(report.already_audited), silence_threshold))
	return report


def already_audited(
	path: Path,
	modified_before: object,
	size_before: object,
	audited_at: object,
	threshold_audit: object,
	threshold: float,
) -> bool:
	"""Le sonore a déjà eu un audit complet à ce seuil, et son fichier n'a pas changé depuis : ni sa date de
	modification, plus ancienne que l'audit, ni sa date et sa taille, celles enregistrées
	(https://github.com/dascritch/machincast/issues/206)."""
	if (not isinstance(audited_at, datetime)) or (threshold_audit != threshold):
		return False
	file = file_state(path)
	return (file is not None) and (file == (modified_before, size_before)) and (file[0] <= audited_at)


def threshold_text(threshold: float) -> str:
	"""« -40 », « -55,5 » : un seuil de silence, en dB, à la française."""
	return f"{threshold:g}".replace(".", ",")


def _already_audited(count: int, threshold: float) -> str:
	"""« 2 sonores déjà audités au seuil de -40 dB, aux fichiers inchangés : non décodés ; … »."""
	threshold_string = threshold_text(threshold)
	if count > 1:
		start = f"{count} sonores déjà audités au seuil de {threshold_string} dB, aux fichiers inchangés : non décodés"
	else:
		start = f"{count} sonore déjà audité au seuil de {threshold_string} dB, au fichier inchangé : non décodé"
	return f"{start} ; --force décode tous les sonores"


def _healthy(artist: object, title: object) -> str:
	"""« sain », suivi du nom du sonore quand il en a un : « sain, Les Gaufres – Café à minuit »."""
	name = " – ".join(str(part) for part in (artist, title) if part is not None)
	if name == "":
		return "sain"
	return f"sain, {name}"
