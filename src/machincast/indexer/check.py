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
d'erreur).

Chaque sonore est vérifié à part (https://github.com/dascritch/machincast/issues/401) : une erreur imprévue pendant sa
vérification est un incident (logging, niveau ERROR), désigné par son chemin, qui laisse le sonore tel quel et
n'empêche pas de vérifier les suivants ; seuls un décodeur absent et une base injoignable arrêtent tout. L'examen de
chaque fichier (type, puis décodage) tourne dans un fil à part, que la vérification attend au plus AUDIT_LIMIT : au-delà,
il est abandonné en incident. Le module signal ne convient pas : il n'interrompt pas un appel bloqué dans GStreamer,
libmagic ou le système de fichiers, seulement l'interpréteur Python ; le fil abandonné, lui, n'empêche pas la suite. L'indexeur n'écrit jamais dans le log, et ne modifie jamais un champ listé dans edited_fields
(« music_metadata.<clé> » pour une clé des métadonnées musicales).
"""

import logging
import threading
from collections.abc import Callable, Collection, Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

from machincast import crash
from machincast.configuration import SILENCE_THRESHOLD
from machincast.conversion import duration_or_none, list_or_none
from machincast.fingerprint import audited_since_modification, file_state, modified
from machincast.i18n import _, decimal, ngettext
from machincast.indexer.audit import Anomaly
from machincast.indexer.decoding import Check, Checker, FileState, UnavailableDecoder, check_file
from machincast.indexer.file_type import Kind, kind, type_mime
from machincast.indexer.tags import merge

log = logging.getLogger(__name__)

ANALYSED = _("File being analysed")
"""La rubrique des rapports de crash de Machin indexer (https://github.com/dascritch/machincast/issues/342)."""
AUDIT_LIMIT = timedelta(minutes=10)
"""Durée maximale de l'examen d'un fichier : au-delà, quelque chose est bloqué, et l'examen est abandonné en incident
(https://github.com/dascritch/machincast/issues/401)."""
INCIDENT = _("incident")
"""Le verdict d'un incident, dans le document d'audit."""


class Expired(Exception):
	"""L'examen d'un fichier a dépassé AUDIT_LIMIT."""


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
	SoundState.PREVIEW: _("preview"),
	SoundState.ACTIVE: "actif",
	SoundState.DISABLED: _("disabled"),
	SoundState.EXPIRED: _("expired"),
	SoundState.CORRUPT: _("corrupt"),
	SoundState.UNSUPPORTED: _("unsupported"),
	SoundState.DELETED: _("missing"),
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
	incidents: int = 0
	"""Sonores dont la vérification a été interrompue par une erreur imprévue ou par AUDIT_LIMIT
	(https://github.com/dascritch/machincast/issues/401)."""
	anomalies: list[Anomaly] = field(default_factory=list)
	"""Les fichiers défectueux du passage, et ses incidents, pour le document d'audit
	(https://github.com/dascritch/machincast/issues/11)."""


def _grant(text: str, count: int) -> str:
	"""Un nombre dans son texte, déjà accordé par ngettext : zéro et un s'accordent au singulier en français."""
	return text.format(count=count)


def report_text(report: Report) -> str:
	"""« indexation rapide : 2 nouveaux sonores, 0 rattachement, 0 retrait ; 2 sonores vérifiés ; … ».

	Les nouveaux sonores et les rattachements viennent du parcours des répertoires des banques, les retraits des durées
	des banques (https://github.com/dascritch/machincast/issues/195) ; le nombre de
	sonores vérifiés est celui des sonores décodés ; les autres nombres comptent les changements d'état.
	"""
	mode = _("quick indexing")
	if report.full_audit:
		mode = _("full audit")
	return _("{mode}: {detail}").format(mode=mode, detail=report_detail(report))


def report_detail(report: Report) -> str:
	"""Le bilan sans son mode : « 2 nouveaux sonores, 0 rattachement, 0 retrait ; 2 sonores vérifiés ; … », suivi
	des incidents s'il y en a eu (« ; 1 incident »)."""
	detail = _(
		"{new}, {attached}, {removed}; {checked}; {corrupt}, {unsupported}, {deleted}, {restored}, {exited}"
	).format(
		new=_grant(ngettext("{count} new sound", "{count} new sounds", report.new_list), report.new_list),
		attached=_grant(
			ngettext("{count} attachment", "{count} attachments", report.attached_list), report.attached_list
		),
		removed=_grant(ngettext("{count} removal", "{count} removals", report.removals), report.removals),
		checked=_grant(
			ngettext("{count} sound checked", "{count} sounds checked", report.checked_list), report.checked_list
		),
		corrupt=_grant(ngettext("{count} corrupt", "{count} corrupt", report.corrupt_list), report.corrupt_list),
		unsupported=_grant(
			ngettext("{count} unsupported", "{count} unsupported", report.not_supported), report.not_supported
		),
		deleted=_grant(ngettext("{count} deleted", "{count} deleted", report.deleted_list), report.deleted_list),
		restored=_grant(ngettext("{count} restored", "{count} restored", report.restored), report.restored),
		exited=_grant(
			ngettext("{count} out of preview", "{count} out of preview", report.exited_preview), report.exited_preview
		),
	)
	if report.incidents == 0:
		return detail
	return _("{detail}; {incidents}").format(
		detail=detail,
		incidents=_grant(ngettext("{count} incident", "{count} incidents", report.incidents), report.incidents),
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
			return _("sound still {labels}").format(labels=LABELS[before])
		return _("state {labels} kept").format(labels=LABELS[before])
	return _("sound now {labels}").format(labels=LABELS[after])


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
	if report is None:
		report = Report(full_audit=full_audit)
	for line in _sounds(connection, identifiers):
		if (stop is not None) and (stop.is_set()):
			break
		try:
			_check_sound(connection, line, check, full_audit, report, silence_threshold, force)
		except (UnavailableDecoder, psycopg.OperationalError):
			# Un décodeur absent n'est la faute d'aucun fichier, et une base injoignable arrête tout.
			raise
		except Exception as error:  # noqa: BLE001 : un incident sur un sonore n'arrête pas les autres
			_incident(report, str(line[1]), error)
	if report.already_audited:
		log.info(_already_audited(len(report.already_audited), silence_threshold))
	return report


BATCH = 500
"""Les sonores que la vérification lit à la fois : la mémoire ne croît pas avec leur nombre
(https://github.com/dascritch/machincast/issues/390)."""


def _sounds(connection: psycopg.Connection[TupleRow], identifiers: Collection[int] | None) -> Iterator[TupleRow]:
	"""Les sonores à vérifier, par identifiant croissant, lus par lots de BATCH, chacun dans sa transaction : la
	vérification d'un sonore a la sienne. Un sonore ajouté pendant la vérification, d'identifiant plus grand, est
	vérifié aussi."""
	last = 0
	while True:
		with connection.transaction():
			lines = connection.execute(
				"SELECT id, location, state::text, edited_fields, artist, title, music_metadata,"
				" file_modified_at, file_size, detected_start, detected_end, audit_requested, audited_at,"
				" audit_threshold FROM sounds WHERE type = 'file' AND deleted_at IS NULL"
				" AND (%s::bigint[] IS NULL OR id = ANY(%s)) AND id > %s ORDER BY id LIMIT %s",
				(list_or_none(identifiers), list_or_none(identifiers), last, BATCH),
			).fetchall()
		yield from lines
		if len(lines) < BATCH:
			return
		last = int(str(lines[-1][0]))


def _check_sound(
	connection: psycopg.Connection[TupleRow],
	line: TupleRow,
	check: Checker,
	full_audit: bool,
	report: Report,
	silence_threshold: float,
	force: bool,
) -> None:
	"""Vérifie un sonore, dans sa propre transaction, et complète le bilan. Lève Expired si l'examen de son fichier
	dépasse AUDIT_LIMIT, UnavailableDecoder si GStreamer ne sait pas décoder son format."""
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
	# Pour le rapport de crash d'une exception (https://github.com/dascritch/machincast/issues/342) ; après un signal
	# fatal, la dernière ligne du journal qui ouvre une analyse nomme le fichier
	# (https://github.com/dascritch/machincast/issues/413). Le résultat suit, sans le nom.
	crash.note(ANALYSED, str(path))
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
		return
	log.info(_("{location}: analysis…").format(location=location))
	# Un fichier introuvable est déclaré tel sans décodage : l'indexation rapide repère donc les disparus.
	# Un fichier dont le type n'est pas sonore n'est pas décodé non plus.
	file_type, result = watched(lambda: _examine(path, check, audited, silence_threshold), AUDIT_LIMIT)
	after = new_state(before, result.state)
	file = file_state(path)
	if file is not None:
		modified_at, size = file
	else:
		modified_at, size = (None, None)
	# La durée n'est enregistrée que pour un fichier sain, et jamais à la place d'une durée saisie à la main.
	healthy = result.state is FileState.HEALTHY
	if (healthy) and ("duration" not in edited_fields):
		duration = result.duration
	else:
		duration = None
	# Les tags d'un fichier défectueux ne sont pas lus : artiste, titre et métadonnées restent tels quels.
	if healthy:
		if "artist" in edited_fields:
			artist = artist
		else:
			artist = result.tags.artist
		if "title" in edited_fields:
			title = title
		else:
			title = result.tags.title
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
		else:
			if after is SoundState.UNSUPPORTED:
				report.not_supported += 1
			else:
				if after is SoundState.DELETED:
					report.deleted_list += 1
				else:
					if (after is SoundState.ACTIVE) and (before in (SoundState.CORRUPT, SoundState.UNSUPPORTED)):
						report.restored += 1
	if result.state is not FileState.HEALTHY:
		consequence = _consequence(before, after)
		log.warning(_("  {problem}; {consequence}").format(problem=result.problem, consequence=consequence))
		report.anomalies.append(Anomaly(str(location), _(result.state), str(result.detail), consequence))
	else:
		log.info(
			_("  {healthy}; {consequence}").format(
				healthy=_healthy(artist, title), consequence=_consequence(before, after)
			)
		)


def _examine(path: Path, check: Checker, audited: bool, silence_threshold: float) -> tuple[str | None, Check]:
	"""Le type du fichier, puis son décodage, sauf s'il n'est pas du son ; un fichier introuvable est déclaré tel
	par le décodage."""
	file_type = type_mime(path)
	if (file_type is not None) and (kind(file_type) is Kind.NON_SOUND):
		return file_type, Check.defective(
			FileState.UNSUPPORTED, _("of type {file_type}, this is not a sound file").format(file_type=file_type)
		)
	if audited:
		return file_type, check(path, silence_threshold=silence_threshold)
	return file_type, check(path)


def watched[T](function: Callable[[], T], limit: timedelta) -> T:
	"""Le résultat de la fonction, lancée dans un fil à part, ou ce qu'elle lève ; Expired si elle dure plus que la
	limite. Le fil n'est pas interrompu, Python ne le permet pas : il est abandonné, et se termine seul s'il le peut,
	sans rien écrire en base (https://github.com/dascritch/machincast/issues/401)."""
	outcome: list[T] = []
	failure: list[BaseException] = []

	def run() -> None:
		try:
			outcome.append(function())
		except BaseException as error:  # noqa: BLE001 : rendue à l'appelant
			failure.append(error)

	feed = threading.Thread(target=run, name="examination", daemon=True)
	feed.start()
	feed.join(limit.total_seconds())
	if feed.is_alive():
		raise Expired
	if failure:
		raise failure[0]
	return outcome[0]


def _limit_text(limit: timedelta) -> str:
	"""« 10 minutes », ou « 2 secondes » pour une limite de moins d'une minute."""
	seconds = round(limit.total_seconds())
	if seconds < 60:
		return ngettext("{count} second", "{count} seconds", seconds).format(count=seconds)
	minutes = seconds // 60
	return ngettext("{count} minute", "{count} minutes", minutes).format(count=minutes)


def _incident(report: Report, location: str, error: Exception) -> None:
	"""Un sonore dont la vérification s'est interrompue : il reste tel quel, et la vérification passe au suivant."""
	problem = _("check abandoned after {limit}").format(limit=_limit_text(AUDIT_LIMIT))
	if not isinstance(error, Expired):
		problem = _("unexpected error during the check: {error}").format(error=f"{type(error).__name__}: {error}")
	consequence = _("sound left unchanged")
	report.incidents += 1
	log.error(_("  incident, {problem}; {consequence}").format(problem=problem, consequence=consequence))
	report.anomalies.append(Anomaly(location, INCIDENT, problem, consequence))


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
	return (threshold_audit == threshold) and (
		audited_since_modification(path, modified_before, size_before, audited_at)
	)


def threshold_text(threshold: float) -> str:
	"""« -40 », « -55,5 » : un seuil de silence, en dB, à la décimale de la langue : virgule en français."""
	return decimal(f"{threshold:g}")


def _already_audited(count: int, threshold: float) -> str:
	"""« 2 sonores déjà audités au seuil de -40 dB, aux fichiers inchangés : non décodés ; … »."""
	threshold_string = threshold_text(threshold)
	start = ngettext(
		"{count} sound already audited at the threshold of {threshold} dB, unchanged file: not decoded",
		"{count} sounds already audited at the threshold of {threshold} dB, unchanged files: not decoded",
		count,
	).format(count=count, threshold=threshold_string)
	return _("{start}; --force decodes all sounds").format(start=start)


def _healthy(artist: object, title: object) -> str:
	"""« sain », suivi du nom du sonore quand il en a un : « sain, Les Gaufres – Café à minuit »."""
	name = " – ".join(str(part) for part in (artist, title) if part is not None)
	if name == "":
		return _("healthy")
	return _("healthy, {name}").format(name=name)
