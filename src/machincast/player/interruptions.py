"""Les interruptions de l'antenne demandées à Machin player (https://github.com/dascritch/machincast/issues/440).

Interruptions traite ce que l'interface demande sur la socket d'état, au début du pas suivant de la diffusion : avancer
l'événement suivant (https://github.com/dascritch/machincast/issues/257), interrompre le sonore, la séquence ou
l'événement en cours (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228), couper l'antenne par un secours ou par un feed
(https://github.com/dascritch/machincast/issues/323). Elle agit sur la diffusion qui la crée (broadcast), dont elle
partage l'état : le sonore en cours, ceux prévus, l'ordonnanceur et l'historique.
"""

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from machincast.i18n import N_, _, logged
from machincast.player.broadcast_plan import (
	_continues_sequence,
)
from machincast.player.broadcast_types import (
	Planned,
	Playback,
)
from machincast.player.rundown import Choice
from machincast.shared.fades import NO_CROSSFADE
from machincast.shared.grid import Event, Occurrence, Priority, read_event, wall_hour

if TYPE_CHECKING:
	from machincast.player.broadcast import Broadcast

log = logging.getLogger(__name__)

MANUAL_INTERRUPTION = N_("manual interruption")
IGNORED = N_("{manual_interruption} ignored").format(manual_interruption=MANUAL_INTERRUPTION)
ADVANCED_EVENT = N_("advanced event")
"""Nature de la ligne du log d'une avance de l'événement suivant (https://github.com/dascritch/machincast/issues/257)."""
IGNORED_ADVANCE = N_("advance ignored")
FOLLOWING_EVENT_SEARCH = timedelta(minutes=1)
"""L'événement suivant publié se cherche de nouveau au plus tard après ce délai, même si rien n'a changé."""


class Interruptions:
	"""Les demandes d'interruption de l'antenne, traitées pour une diffusion."""

	def __init__(self, broadcast: "Broadcast") -> None:
		self.broadcast = broadcast

	def advance(self, event: int | None) -> bool:
		"""L'événement suivant commence aussitôt (https://github.com/dascritch/machincast/issues/257), s'il est bien
		celui que la demande attend : l'interface nomme celui que Machin player a publié. Le sonore en cours
		s'éteint comme pour une interruption manuelle, une séquence en cours ne continue pas, et les sonores à venir
		sont recalculés. False si la demande est ignorée."""
		instant = self.broadcast.clock.now()
		following = self.broadcast.scheduler.following_event(instant)
		if following is None:
			log.warning(_("{ignored_advance}: no next event").format(ignored_advance=logged(IGNORED_ADVANCE)))
			return False
		if following.event.id != event:
			expected = self._expected_name(event)
			log.warning(
				_("{ignored_advance}: the next event is “{name}”, not {expected}").format(
					ignored_advance=logged(IGNORED_ADVANCE), name=following.event.name, expected=expected
				)
			)
			return False
		self.broadcast.scheduler.advance(instant)
		assert following.start is not None
		message = N_("of the event “{name}”, planned on {start:%Y-%m-%d %H:%M}").format(
			name=following.event.name, start=following.start
		)
		current = self.broadcast.current
		if current is None:
			sound = None
		else:
			sound = current.choice.sound
		self.broadcast.history.record(
			self.broadcast.connection, "info", ADVANCED_EVENT, message, instant, sound=sound, event=following.event.id
		)
		if self.broadcast.outputs is not None:
			self.broadcast.outputs.announce(ADVANCED_EVENT, message)
		self.broadcast._following = None
		if current is not None:
			# Une séquence en cours ne continue pas : l'occurrence avancée a commencé après son dernier passage.
			self.broadcast.upcoming = []
			self.broadcast._expected = None
			play = self.broadcast._decide(instant, None).play
			fade = (self.broadcast.crossfades.end) or (NO_CROSSFADE)
			self.broadcast._switch_off(
				current, play, instant, fade, (self.broadcast.crossfades.start) or (NO_CROSSFADE)
			)
		self.broadcast._publish(instant)
		return True

	def _expected_name(self, event: int | None) -> str:
		"""L'événement qu'attendait une demande d'avance, pour le journal."""
		if event is None:
			return _("none")
		with self.broadcast.connection.transaction():
			line = self.broadcast.connection.execute(
				"SELECT internal_name FROM events WHERE id = %s", (event,)
			).fetchone()
		if line is None:
			return _("event no. {event}, unknown").format(event=event)
		return _("“{line}”").format(line=line[0])

	def the_following_event(self, instant: datetime) -> Occurrence | None:
		"""L'événement suivant à publier, cherché de nouveau quand il a pu changer : au début d'un sonore, après une
		demande, quand il commence, et au moins chaque minute."""
		following = self.broadcast._following
		if (
			(following is None)
			or (instant - following[0] >= FOLLOWING_EVENT_SEARCH)
			or (
				(following[1] is not None)
				and (following[1].start is not None)
				and (wall_hour(instant) >= following[1].start)
			)
		):
			following = (instant, self.broadcast.scheduler.following_event(instant))
			self.broadcast._following = following
		return following[1]

	def interrupt(self, item: str) -> bool:
		"""Interruption manuelle (https://github.com/dascritch/machincast/issues/228) : sauter au sonore suivant
		(« sound »), sauter après la séquence (« sequence »), ou couper l'événement par le fil musical
		(« event ») ; revenir au début du sonore (« restart_sound ») ou de l'événement à l'antenne (« restart_event »,
		https://github.com/dascritch/machincast/issues/366). False si elle est ignorée, faute de rien à interrompre."""
		instant = self.broadcast.clock.now()
		current = self.broadcast.current
		if current is None:
			log.warning(_("{ignored}: nothing on air").format(ignored=logged(IGNORED)))
			return False
		choice = current.choice
		# L'événement à l'antenne : celui qui prête son nom, s'il y en a un (https://github.com/dascritch/machincast/issues/399).
		event = ((choice.lender) or (choice.occurrence)).event
		if (item == "sequence") and (choice.line is None):
			log.warning(_("{ignored}: no sequence on air").format(ignored=logged(IGNORED)))
			return False
		if (item == "event") and (event.priority is Priority.BACKGROUND_PROGRAMMING):
			log.warning(_("{ignored}: the background programming is already on air").format(ignored=logged(IGNORED)))
			return False
		if (item == "restart_sound") and (current.parameters.stream):
			log.warning(_("{ignored}: a stream has no beginning").format(ignored=logged(IGNORED)))
			return False
		self.broadcast._following = None
		message = self._interrupted(item, choice, event)
		self.broadcast.history.record(
			self.broadcast.connection,
			"info",
			MANUAL_INTERRUPTION,
			message,
			instant,
			sound=choice.sound,
			event=event.id,
		)
		if self.broadcast.outputs is not None:
			self.broadcast.outputs.announce(MANUAL_INTERRUPTION, message)
		if item not in ("sound", "restart_sound"):
			self.broadcast.scheduler.abandon_sequence(current.play.id)
		following = None
		match item:
			case "event":
				self.broadcast.scheduler.return_to_background_programming(instant)
				self.broadcast.upcoming = []
			case "restart_sound":
				# Le même sonore, du même élément : les sonores à venir le suivent toujours.
				following = choice
			case "restart_event":
				self.broadcast.scheduler.restart((choice.lender) or (choice.occurrence), instant)
				self.broadcast.upcoming = []
			case _:
				following = self._skip(current, after_sequence=item == "sequence", instant=instant)
		if following is None:
			following = self.broadcast._decide(instant, None).play
		fade = (self.broadcast.crossfades.end) or (NO_CROSSFADE)
		self.broadcast._switch_off(
			current, following, instant, fade, (self.broadcast.crossfades.start) or (NO_CROSSFADE)
		)
		self.broadcast._publish(instant)
		return True

	def _interrupted(self, item: str, choice: Choice, event: Event) -> str:
		"""Ce que l'interruption manuelle interrompt, pour le log et les sorties."""
		match item:
			case "sequence":
				return N_("of the sequence {on_air_sequence}").format(on_air_sequence=self.broadcast._on_air_sequence)
			case "event":
				return N_("of the event “{name}”").format(name=event.name)
			case "restart_sound":
				return N_("back to the start of the sound “{sound_name}”").format(
					sound_name=self._sound_name(choice.sound)
				)
			case "restart_event":
				return N_("back to the start of the event “{name}”").format(name=event.name)
		return N_("of the sound “{sound_name}”").format(sound_name=self._sound_name(choice.sound))

	def cut_by_fallback(self, event: int | None) -> bool:
		"""Coupe l'antenne par cet événement de secours (https://github.com/dascritch/machincast/issues/323) ; False si
		la demande est ignorée : rien à l'antenne, ou pas un secours en base."""
		fallback = None
		if event is not None:
			with self.broadcast.connection.transaction():
				fallback = read_event(self.broadcast.connection, event)
		if (fallback is None) or (fallback.priority is not Priority.FALLBACK) or (fallback.deleted_at is not None):
			log.warning(
				_("{ignored}: event no. {event} is not a fallback").format(ignored=logged(IGNORED), event=event)
			)
			return False
		return self._cut_by(fallback, None, fallback.name)

	def cut_by_feed(self, feed: int | None) -> bool:
		"""Coupe l'antenne par le stream actif qui suit ce feed, le plus ancien
		(https://github.com/dascritch/machincast/issues/323) ; False si la demande est ignorée."""
		with self.broadcast.connection.transaction():
			line = self.broadcast.connection.execute(
				"SELECT m.name, (SELECT s.id FROM sounds s WHERE s.feed_id = m.id AND s.type = 'stream'"
				" AND s.state = 'active' AND s.deleted_at IS NULL ORDER BY s.id LIMIT 1) FROM feeds m WHERE m.id = %s",
				(feed,),
			).fetchone()
		if line is None:
			log.warning(_("{ignored}: feed no. {feed} does not exist").format(ignored=logged(IGNORED), feed=feed))
			return False
		name, stream = line
		if stream is None:
			log.warning(
				_("{ignored}: no active stream follows the feed “{name}”").format(ignored=logged(IGNORED), name=name)
			)
			return False
		return self._cut_by(None, int(str(stream)), str(name))

	def _cut_by(self, fallback: Event | None, stream: int | None, by: str) -> bool:
		"""Comme une interruption de l'événement, mais le secours ou le stream remplace la grille jusqu'à la fin de
		l'événement coupé ; by : le nom du secours, ou celui du feed du stream."""
		instant = self.broadcast.clock.now()
		current = self.broadcast.current
		if current is None:
			log.warning(_("{ignored}: nothing on air").format(ignored=logged(IGNORED)))
			return False
		event = current.choice.occurrence.event
		# Une phrase entière par cas, que le log traduit d'un seul gabarit.
		if event.priority is Priority.BACKGROUND_PROGRAMMING:
			message = N_("of the background programming “{name}” by the fallback “{by}”")
			if fallback is None:
				message = N_("of the background programming “{name}” by the feed “{by}”")
		else:
			message = N_("of the event “{name}” by the fallback “{by}”")
			if fallback is None:
				message = N_("of the event “{name}” by the feed “{by}”")
		message = message.format(name=event.name, by=by)
		self.broadcast.history.record(
			self.broadcast.connection,
			"info",
			MANUAL_INTERRUPTION,
			message,
			instant,
			sound=current.choice.sound,
			event=event.id,
		)
		if self.broadcast.outputs is not None:
			self.broadcast.outputs.announce(MANUAL_INTERRUPTION, message)
		self.broadcast._following = None
		self.broadcast.scheduler.abandon_sequence(current.play.id)
		self.broadcast.scheduler.cut_by(instant, fallback, stream)
		self.broadcast.upcoming = []
		self.broadcast._expected = None
		following = self.broadcast._decide(instant, None).play
		fade = (self.broadcast.crossfades.end) or (NO_CROSSFADE)
		self.broadcast._switch_off(
			current, following, instant, fade, (self.broadcast.crossfades.start) or (NO_CROSSFADE)
		)
		self.broadcast._publish(instant)
		return True

	def _skip(self, current: Playback, *, after_sequence: bool, instant: datetime) -> Choice | None:
		"""Le sonore où sauter : le prochain, ou, après la séquence, le premier sonore prévu qui ne la continue pas ;
		les sonores à venir qui le suivent sont gardés. None s'il n'est pas prévu, ou plus jouable : l'ordonnanceur
		décide alors, et la liste sera recalculée."""
		reserve = self.broadcast.reserve
		if (reserve is None) or (reserve.early):
			return None
		candidates: list[tuple[Choice, Planned | None]] = [(reserve.choice, None)]
		for upcoming in self.broadcast.upcoming:
			candidates.append((upcoming.choice, upcoming))
		previous = current.choice
		for rank, (choice, planned) in enumerate(candidates):
			same_occurrence = previous.occurrence.key == choice.occurrence.key
			if (after_sequence) and (same_occurrence) and (_continues_sequence(previous, choice)):
				# Un sonore de la séquence est passé avec elle.
				previous = choice
			else:
				if not self.broadcast.scheduler.validate(choice, instant):
					return None
				if planned is not None:
					self.broadcast._engage(planned, instant)
				self.broadcast.upcoming = self.broadcast.upcoming[rank:]
				self.broadcast._expected = choice
				return choice
		return None

	def _sound_name(self, sound: int) -> str:
		with self.broadcast.connection.transaction():
			line = self.broadcast.connection.execute(
				"SELECT COALESCE(title, location, stream_url) FROM sounds WHERE id = %s", (sound,)
			).fetchone()
		if (line is None) or (line[0] is None):
			return str(sound)
		return str(line[0])
