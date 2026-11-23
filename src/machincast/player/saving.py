"""Enregistrement de l'airplay et du log (https://github.com/dascritch/machincast/issues/17, spec § 3.1 et § 5.2).

Le binaire lecture n'écrit que par ce module, et seulement des insertions : ses droits PostgreSQL ne lui
permettent ni de modifier ni de supprimer une ligne d'airplay ou de log, ni de lire le log (pas de RETURNING).

- Airplay : deux lignes par passage, reliées par play_id. Chacune recopie l'emplacement (pour un stream, son
  adresse directe ou celle de son feed), l'artiste et le titre du sonore au moment du passage, et référence
  le sonore, la banque qui l'a fourni (aucune pour un sonore placé directement dans l'événement), l'événement et
  l'élément de sa liste, et, pour un sonore joué par une séquence, la séquence et son élément
  (https://github.com/dascritch/machincast/issues/99). La ligne de fin donne la durée effectivement diffusée et
  l'indicateur without_incident.
- Log : chaque opération, normale (info) ou non (alerte, incident), avec sa nature, un message et ses références.
  Une coupure nette est une opération normale ; une lecture interrompue par une erreur est un incident, que
  l'appelant peut nommer plus précisément (flux tombé d'un stream).

Les alertes et incidents du log sont aussi écrits dans le journal du binaire, sur sa sortie d'erreur
(https://github.com/dascritch/machincast/issues/19).

Les heures viennent de l'horloge du binaire (machincast.clock), pour que la simulation et les tests soient
reproductibles.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import psycopg
from psycopg.rows import TupleRow

from machincast.i18n import N_, _, logged
from machincast.player import queries
from machincast.plugins import incidents

Level = Literal["info", "warning", "incident"]
LEVELS = {"info": _("info"), "warning": _("warning"), "incident": _("incident")}
"""Les niveaux du log à l'écran et dans les messages, par leur valeur en base
(https://github.com/dascritch/machincast/issues/358)."""

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Play:
	id: uuid.UUID
	sound: int
	bank: int | None
	event: int | None
	item: int | None
	start: datetime
	sequence: int | None = None
	"""Séquence qui a fait jouer le sonore (https://github.com/dascritch/machincast/issues/99)."""
	item_sequence: int | None = None
	"""Élément de cette séquence."""
	lender: int | None = None
	"""L'événement au nom de qui le passage est joué (https://github.com/dascritch/machincast/issues/399)."""

	@classmethod
	def of(cls, start: "PlayStart") -> "Play":
		"""Le passage qui commence ainsi, sous un identifiant neuf."""
		return cls(
			uuid.uuid4(),
			start.sound,
			start.bank,
			start.event,
			start.item,
			start.instant,
			start.sequence,
			start.item_sequence,
			start.lender,
		)


@dataclass(frozen=True)
class PlayStart:
	"""Ce qui fait commencer un passage (https://github.com/dascritch/machincast/issues/441)."""

	sound: int
	bank: int | None
	event: int | None
	item: int | None
	instant: datetime
	sequence: int | None = None
	item_sequence: int | None = None
	lender: int | None = None


def record(
	connection: psycopg.Connection[TupleRow],
	level: str,
	kind: str,
	message: str,
	instant: datetime | None = None,
	sound: int | None = None,
	bank: int | None = None,
	event: int | None = None,
	*,
	origin: str | None = None,
	api_user: str | None = None,
) -> None:
	"""Ajoute une ligne au log ; sans instant, l'heure du serveur PostgreSQL. Jamais de RETURNING : la lecture
	n'a pas le droit de lire le log. Pour une demande d'un client de la socket d'état, origin dit d'où elle vient,
	et api_user, le compte de l'API qui l'a faite depuis l'intranet (https://github.com/dascritch/machincast/issues/549)."""
	if level != "info":
		# Sortie privée stderr (https://github.com/dascritch/machincast/issues/19) : alertes et incidents.
		log.warning(
			_("{level}: {kind}: {message}").format(
				level=LEVELS.get(level, level), kind=logged(kind), message=logged(message)
			)
		)
	with connection.transaction():
		queries.insert_log(connection, (instant, level, kind, message), (sound, bank, event), origin, api_user)
	if level == "incident":
		# Les plugins abonnés à log_incident (https://github.com/dascritch/machincast/issues/592).
		incidents.tell(
			level, logged(kind), logged(message), instant, {"sound": sound, "bank": bank, "event": event}, origin
		)


def _start(connection: psycopg.Connection[TupleRow], play: Play) -> None:
	queries.insert_play_start(
		connection,
		play.id,
		play.start,
		(play.bank, play.event, play.item, play.sequence, play.item_sequence, play.lender),
		play.sound,
	)


def _end(connection: psycopg.Connection[TupleRow], play: Play, instant: datetime, *, without_incident: bool) -> None:
	queries.insert_play_end(connection, play.id, instant, instant - play.start, without_incident=without_incident)


def begin_play(connection: psycopg.Connection[TupleRow], start: PlayStart) -> Play:
	"""Ligne de début d'un passage ; l'artiste et le titre sont recopiés tels qu'ils sont à cet instant."""
	play = Play.of(start)
	with connection.transaction():
		_start(connection, play)
	return play


def finish_play(
	connection: psycopg.Connection[TupleRow],
	play: Play,
	instant: datetime,
	*,
	cut: bool = False,
	error: str | None = None,
	kind: str = N_("interrupted playback"),
) -> None:
	"""Ligne de fin d'un passage, avec la durée diffusée ; une coupure ou une erreur est aussi consignée au log,
	l'erreur en incident de la nature donnée."""
	with connection.transaction():
		_end(connection, play, instant, without_incident=error is None)
		if error is not None:
			record(connection, "incident", kind, error, instant, play.sound, play.bank, play.event)
		else:
			if cut:
				record(
					connection,
					"info",
					N_("clean cut"),
					N_("start of an event"),
					instant,
					play.sound,
					play.bank,
					play.event,
				)
