"""Fiche d'un événement (https://github.com/dascritch/machincast/issues/32, spec § 8.5).

La fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.window), depuis la liste des événements, ou vide
pour un nouvel événement. Enregistrement, annulation et fermeture : machincast.interface.card.

- Les noms sont enregistrés conformés (machincast.conformation, https://github.com/dascritch/machincast/issues/108) ; un
  nom public vide n'en est pas un (NULL). Deux événements n'ont pas le même nom interne.
- Le masquage « selon la séquence, la banque ou le sonore » (NULL) laisse décider le niveau suivant ; « masqués » et
  « affichés » l'imposent.
- Grille (spec § 3.1) : le début et la fin de la première occurrence, chacun à cocher, et les jours où elle revient.
  Sans début, ni fin ni jours : un fil musical sans début est permanent. Un événement de secours n'a ni dates ni
  jours : il ne joue qu'à la place d'un stream tombé. Une émission ou un spécial a un début ; une fin suit le début.
  Une date cochée part de l'heure de l'horloge, à la minute ; une fin, d'une heure après le début.
- Un événement ne chevauche pas un autre événement de même priorité (machincast.player.grid.overlap) ; une
  session sautée ne chevauche rien (https://github.com/dascritch/machincast/issues/273).
- Un événement de secours qu'un stream désigne reste de priorité secours : la base le refuserait aussi.
- La liste de lecture : sonores, banques et séquences (machincast.interface.items). Un événement vide
  s'enregistre, pour être complété plus tard, avec un avertissement qui dit ce qu'en fait la diffusion selon sa
  priorité ; la liste des événements le montre en anomalie (https://github.com/dascritch/machincast/issues/140).
  L'avertissement d'une banque « ne pas répéter » appelée juste après elle-même suit la boucle de la
  liste : elle boucle, sauf pour une émission ou un spécial sans fin.
- Session sautée (https://github.com/dascritch/machincast/issues/295) : la prochaine session sautée de l'événement,
  en cours ou à venir (machincast.interface.sessions.next_skipped), s'annonce en haut de la fiche, sous l'erreur,
  sur un liseret orange (skipped_session, SESSION_OUTLINE) : un avertissement, qui ne refuse rien. Le saut tient au
  jour : il suit l'heure de l'événement quand elle change. Son bouton « Rétablir » la rétablit, comme le clic droit du
  calendrier, sans toucher aux champs de la fiche ; il est inactif, avec une infobulle qui dit pourquoi, pour une
  session commencée, ou dont un événement de même priorité a pris la place. Rétablie, la session s'annonce
  (restored_session) et Machin player relit la grille.
- Sa copie (https://github.com/dascritch/machincast/issues/130) garde sa priorité, ses noms, son masquage et sa liste
  de lecture, sans dates ni jours : son créneau est à choisir, une émission ou un spécial ne s'enregistrant pas sans
  début.
"""

from datetime import date, datetime, timedelta

from PySide6.QtCore import QDateTime, Signal
from PySide6.QtWidgets import QBoxLayout, QDateTimeEdit, QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from machincast.clock import Clock
from machincast.conformation import conform
from machincast.i18n import _, date_and_hour
from machincast.interface import display
from machincast.interface.calendar import day_and_month, long_date
from machincast.interface.card import ORANGE, Card, Connection, Refusal
from machincast.interface.items import CATEGORY, FEED, ITEM, Buttons, ItemList
from machincast.interface.lists import EMPTY_EVENT
from machincast.interface.sessions import Session, next_skipped, overlapped, reinstate, started
from machincast.interface.ui.event_card import Ui_EventCard
from machincast.player.grid import DAYS, NEVER, Event, Priority, overlap, read_grid

PRIORITIES: tuple[tuple[str, str], ...] = (
	("fallback", _("Fallback")),
	("background_programming", _("Background programming")),
	("show", _("Show")),
	("special", _("Special")),
)
"""Valeurs de events.priority, dans l'ordre du choix de la fiche : de la plus basse à la plus haute, comme le type
event_priority (https://github.com/dascritch/machincast/issues/253)."""
NEW = "show"
"""Priorité d'un nouvel événement."""
ENDLESS_DOES_NOT_LOOP = ("show", "special")
"""Priorités dont la liste ne boucle pas, sans fin : l'occurrence se termine au bout de sa liste."""
HIDINGS: tuple[tuple[bool | None, str], ...] = (
	(None, _("According to the sequence, the bank or the sound")),
	(True, _("Hidden by the public name of the event")),
	(False, _("Shown")),
)
"""Valeurs de events.hide_metadata, dans l'ordre du choix de la fiche."""
REPETITION = _("A sound, a bank or a sequence may come back several times in an event.")
"""Remarque des choix d'éléments."""
END_OF_LIST: tuple[tuple[str, str], ...] = (
	("replay", _("Replay the list")),
	("background_programming", _("Switch to the background programming")),
	("fallback", _("Switch to a fallback")),
	("lend_name", _("Lend its name to the background programming")),
)
"""Valeurs de events.end_of_list, dans l'ordre du choix de la fiche (https://github.com/dascritch/machincast/issues/350).
Le choix n'a de sens que pour une émission ou un spécial qui a une fin : sans fin, sa liste ne boucle pas ; un fil
musical et un secours rejouent toujours la leur. Prêter son nom (https://github.com/dascritch/machincast/issues/399) :
l'événement en dessous, le plus souvent le fil musical, joue sous son nom jusqu'à sa fin, dès son début si sa liste
est vide."""
LENDS_NAME = _("Empty list: the event below, most often the background programming, plays in its name during its slot.")
"""Ce que dit la fiche d'une liste vide qui prête son nom : ce n'est pas une anomalie."""
CHOOSE_FALLBACK = _("Choose a fallback…")
EACH_STREAM = _("The fallback of each stream")
"""Sans secours d'un stream tombé dans l'événement : celui de chaque stream, comme avant."""
WITHOUT_END = _("Only for a show or a special that has an end: otherwise, its list does not replay.")
WITHOUT_STREAM = _("Only for an event whose list has a stream.")
DEFAULT_DURATION = timedelta(hours=1)
"""Écart entre le début et une fin qui se coche."""
SESSION_OUTLINE = f"QFrame#session_sautee {{ border: 4px solid {ORANGE}; }}"
"""Le liseret d'une session sautée : un avertissement, de l'orange de ceux de la fiche."""
REINSTATE = _("Reinstate")
STARTED = _("It has already started: it can no longer be reinstated.")


def _show(date: QDateTimeEdit, instant: datetime) -> None:
	date.setDateTime(QDateTime.fromSecsSinceEpoch(int(instant.timestamp())))


class EventCard(Card):
	category = "event"
	restored_session = Signal(str)
	"""Une session sautée a été rétablie depuis la fiche : ce que la barre d'état en annonce. Machin player doit
	relire la grille (https://github.com/dascritch/machincast/issues/295)."""

	def __init__(
		self, connection: Connection, identifier: int | None, clock: Clock, parent: QWidget | None = None
	) -> None:
		super().__init__(connection, identifier, clock, parent)
		self.ui = Ui_EventCard()
		self.ui.setupUi(self)
		ui = self.ui
		self.plug(ui.save, ui.cancel, ui.delete, ui.message, ui.duplicate)
		self._build_session_announcement()
		for _value, text in PRIORITIES:
			ui.priority.addItem(text)
		for _mask, text in HIDINGS:
			ui.hiding.addItem(text)
		self.days = [getattr(ui, day) for day in DAYS]
		self._name = ""
		buttons = Buttons(
			{
				"sound": ui.add_sounds,
				"bank": ui.add_banks,
				"sequence": ui.add_sequences,
				"feed": ui.add_feeds,
			},
			ui.remove_item,
			ui.raise_,
			ui.go_down,
		)
		self.items = ItemList(self, ui.items, buttons, "event_items", "event_id", REPETITION, ui.item_group)
		self.items.changed.connect(self._modify)
		self.items.changed.connect(self._warn)
		self.items.loaded.connect(self._warn)
		ui.internal_name.textChanged.connect(self._modify)
		ui.public_name.textChanged.connect(self._modify)
		ui.hiding.currentIndexChanged.connect(self._modify)
		ui.priority.currentIndexChanged.connect(self._grid)
		ui.priority.currentIndexChanged.connect(self._modify)
		ui.priority.currentIndexChanged.connect(self._warn)
		ui.has_start.toggled.connect(self._grid)
		ui.has_start.toggled.connect(self._modify)
		ui.has_end.toggled.connect(self._tick_end)
		ui.has_end.toggled.connect(self._grid)
		ui.has_end.toggled.connect(self._modify)
		ui.has_end.toggled.connect(self._warn)
		for value, text in END_OF_LIST:
			ui.end_of_list.addItem(text, value)
		ui.end_of_list.currentIndexChanged.connect(self._end_of_list)
		ui.end_of_list.currentIndexChanged.connect(self._modify)
		ui.end_of_list.currentIndexChanged.connect(self._warn)
		ui.end_fallback.currentIndexChanged.connect(self._modify)
		ui.stream_fallback.currentIndexChanged.connect(self._modify)
		ui.priority.currentIndexChanged.connect(self._end_of_list)
		ui.has_end.toggled.connect(self._end_of_list)
		self.items.changed.connect(self._end_of_list)
		self.items.loaded.connect(self._end_of_list)
		for field in (ui.start, ui.end):
			field.dateTimeChanged.connect(self._modify)
		for day in self.days:
			day.toggled.connect(self._modify)
		self.load()

	def title(self) -> str:
		if self.is_copy():
			return _("New event, copy of {name}").format(name=self._name)
		if self.identifier is None:
			return _("New event")
		return _("Event: {name}").format(name=self._name)

	def _priority(self) -> str:
		return PRIORITIES[self.ui.priority.currentIndex()][0]

	def _read(self) -> None:
		"""Lit l'événement en base, ou celui qu'il copie, sans ses dates ni ses jours ; un nouvel événement est une
		émission, sans dates, au masquage hérité."""
		event: tuple[object, ...] = ("", None, NEW, None, None, [], None, "replay", None, None)
		lu = self.lu()
		with self.connection.transaction():
			if lu is not None:
				line = self.connection.execute(
					"SELECT internal_name, public_name, priority::text, starts_at, ends_at, recurrence_days::text[],"
					" hide_metadata, end_of_list::text, end_fallback_event_id, stream_fallback_event_id"
					" FROM events WHERE id = %s",
					(lu,),
				).fetchone()
				assert line is not None, f"événement {lu} absent"
				event = line
			fallbacks = self.connection.execute(
				"SELECT id, internal_name FROM events WHERE priority = 'fallback' AND deleted_at IS NULL"
				" AND id IS DISTINCT FROM %s ORDER BY internal_name",
				(lu,),
			).fetchall()
			self.items.load(lu, self.is_copy())
		name, public_name, priority, start, end, days, hiding, end_of_list, end_fallback, stream_fallback = event
		if self.is_copy():
			start, end, days = None, None, []
		ui = self.ui
		self._name = str(name)
		ui.internal_name.setText(self._name)
		if self.is_copy():
			ui.internal_name.setText(self.name_of_copy(self._name))
		ui.public_name.setText(str((public_name) or ("")))
		ui.priority.setCurrentIndex(next(i for i, (value, _text) in enumerate(PRIORITIES) if value == priority))
		ui.hiding.setCurrentIndex(next(i for i, (value, _text) in enumerate(HIDINGS) if value is hiding))
		now = self.clock.now().replace(second=0, microsecond=0)
		departure = now
		if isinstance(start, datetime):
			departure = start
		# Une fin qui se coche part d'une heure après le début (_cocher_fin).
		arrival = departure
		if isinstance(end, datetime):
			arrival = end
		_show(ui.start, departure)
		_show(ui.end, arrival)
		# Chaque case met la grille à jour quand elle change d'état (toggled) : le début d'abord, qui permet le reste.
		ui.has_start.setChecked(isinstance(start, datetime))
		ui.has_end.setChecked(isinstance(end, datetime))
		ticked_list = set()
		if isinstance(days, list):
			ticked_list = {str(day) for day in days}
		for day_name, day in zip(DAYS, self.days, strict=True):
			day.setChecked(day_name in ticked_list)
		self._fill_fallbacks(fallbacks, end_of_list, end_fallback, stream_fallback)
		# Une priorité déjà choisie ne change pas l'index : l'avertissement ne suit pas de lui-même.
		self._grid()
		self._warn()
		self._end_of_list()
		self._announce_session()

	# ─── Session sautée (https://github.com/dascritch/machincast/issues/295) ───

	def _build_session_announcement(self) -> None:
		"""L'annonce, sous l'erreur de la fiche, cachée sans session sautée."""
		self.skipped_session = QFrame(self)
		self.skipped_session.setObjectName("skipped_session")
		self.skipped_session.setStyleSheet(SESSION_OUTLINE)
		self.skipped_session.setAccessibleName(_("Skipped session"))
		self.session_text = QLabel(self.skipped_session)
		self.session_text.setWordWrap(True)
		self.reinstate_session = QPushButton(REINSTATE, self.skipped_session)
		self.reinstate_session.clicked.connect(self._reinstate_session)
		line = QHBoxLayout(self.skipped_session)
		line.setContentsMargins(10, 6, 6, 6)
		line.addWidget(self.session_text, 1)
		line.addWidget(self.reinstate_session)
		self.skipped_session.hide()
		arrangement = self.layout()
		assert isinstance(arrangement, QBoxLayout)
		arrangement.insertWidget(arrangement.indexOf(self.error) + 1, self.skipped_session)
		self._session: Session | None = None

	def _next_skipped(self) -> Session | None:
		"""Celle de l'événement en base ; aucune pour une fiche nouvelle, une copie, qui n'est pas en base, ou un
		événement supprimé."""
		if self.identifier is None:
			return None
		event = next((lu for lu in read_grid(self.connection) if lu.id == self.identifier), None)
		if event is None:
			return None
		return next_skipped(event, self.clock.now())

	def _announce_session(self) -> None:
		"""Montre la prochaine session sautée, et si elle se rétablit ; cache l'annonce sans session sautée."""
		now = self.clock.now()
		hindrance = None
		with self.connection.transaction():
			self._session = self._next_skipped()
			if self._session is not None:
				hindrance = self._hindrance(self._session, now)
		session = self._session
		if session is None:
			self.skipped_session.hide()
			return
		will_play = _("will not play")
		if started(session, now):
			will_play = _("does not play")
		self.session_text.setText(
			_("The session of {long_date} at {start:%H:%M} is skipped: it {will_play}.").format(
				long_date=long_date(session.start.date()), start=session.start, will_play=will_play
			)
		)
		self.reinstate_session.setEnabled(hindrance is None)
		self.reinstate_session.setToolTip(
			(hindrance) or (_("Reinstate the session: it will play again, without touching the fields of the form."))
		)
		self.skipped_session.show()

	def _hindrance(self, session: Session, now: datetime) -> str | None:
		"""Pourquoi la session ne se rétablit pas, comme au calendrier ; None si elle le peut. Dans une transaction."""
		if started(session, now):
			return STARTED
		found = overlapped(self.connection, session, now)
		if found is None:
			return None
		other, instant = found
		return _("“{name}”, of the same priority, took its place on {day_and_month} at {instant:%H:%M}.").format(
			name=other.name, day_and_month=day_and_month(instant.date()), instant=instant
		)

	def _reinstate_session(self) -> None:
		"""Rétablit la session annoncée, relue en base, sans toucher aux champs de la fiche ; ce qui l'empêche, apparu
		depuis l'annonce, s'affiche en erreur."""
		now = self.clock.now()
		with self.connection.transaction():
			session = self._next_skipped()
			if session is None:
				hindrance = None
			else:
				hindrance = self._hindrance(session, now)
				if hindrance is None:
					reinstate(self.connection, session)
		self._announce_session()
		if session is None:
			return
		if hindrance is not None:
			self.flag_error(_("Session not reinstated: {hindrance}").format(hindrance=hindrance))
			return
		name, day = session.event.name, session.start.date()
		self.restored_session.emit(
			_("Session of “{name}” of {day_and_month} at {start:%H:%M} reinstated.").format(
				name=name, day_and_month=day_and_month(day), start=session.start
			)
		)

	def plan(self, start: datetime, end: datetime) -> None:
		"""Les dates d'un nouvel événement demandé depuis le calendrier
		(https://github.com/dascritch/machincast/issues/36) : la fiche est modifiée, rien n'est enregistré avant
		« Enregistrer »."""
		ui = self.ui
		_show(ui.start, start.astimezone())
		_show(ui.end, end.astimezone())
		ui.has_start.setChecked(True)
		# Cocher les dates modifie la fiche (_modifier).
		ui.has_end.setChecked(True)

	def _grid(self) -> None:
		"""Ce qui se saisit de la grille : rien pour un événement de secours ; ni fin ni jours sans début."""
		ui = self.ui
		fallback = self._priority() == "fallback"
		if fallback:
			ui.has_start.setChecked(False)
		with_start = ui.has_start.isChecked()
		if not with_start:
			ui.has_end.setChecked(False)
			for day in self.days:
				day.setChecked(False)
		ui.has_start.setEnabled(not fallback)
		ui.start.setEnabled(with_start)
		ui.has_end.setEnabled(with_start)
		ui.end.setEnabled(ui.has_end.isChecked())
		for day in self.days:
			day.setEnabled(with_start)

	# ─── Fin de liste et secours (https://github.com/dascritch/machincast/issues/350) ───

	def _fill_fallbacks(
		self, fallbacks: list[tuple[object, ...]], end_of_list: object, end_fallback: object, stream_fallback: object
	) -> None:
		"""Les secours proposés, ceux de priorité secours qui ne sont pas supprimés, et les choix de l'événement."""
		ui = self.ui
		for combo, first in ((ui.end_fallback, CHOOSE_FALLBACK), (ui.stream_fallback, EACH_STREAM)):
			combo.blockSignals(True)
			combo.clear()
			combo.addItem(first, None)
			for identifier, fallback_name in fallbacks:
				combo.addItem(str(fallback_name), int(str(identifier)))
			combo.blockSignals(False)
		ui.end_of_list.setCurrentIndex(max(ui.end_of_list.findData(str(end_of_list)), 0))
		ui.end_fallback.setCurrentIndex(max(ui.end_fallback.findData(end_fallback), 0))
		ui.stream_fallback.setCurrentIndex(max(ui.stream_fallback.findData(stream_fallback), 0))

	def _end_of_list(self) -> None:
		"""La fin de liste ne se choisit que pour une émission ou un spécial qui a une fin, grisée sinon sur
		« Rejouer la liste » ; son secours, que pour « Basculer vers un secours ». Le secours d'un stream tombé, que
		pour une liste qui a un stream."""
		ui = self.ui
		with_end = (self._priority() in ENDLESS_DOES_NOT_LOOP) and (ui.has_end.isChecked())
		if not with_end:
			ui.end_of_list.setCurrentIndex(0)
		ui.end_of_list.setEnabled(with_end)
		tooltip = WITHOUT_END
		if with_end:
			tooltip = ""
		ui.end_of_list.setToolTip(tooltip)
		ui.end_fallback.setEnabled((with_end) and (ui.end_of_list.currentData() == "fallback"))
		stream = self._has_stream()
		ui.stream_fallback.setEnabled(stream)
		tooltip = WITHOUT_STREAM
		if stream:
			tooltip = ""
		ui.stream_fallback.setToolTip(tooltip)

	def _has_stream(self) -> bool:
		"""Un stream dans la liste : un feed ajouté, ou un sonore de type stream, parmi les éléments pas encore lus
		compris (https://github.com/dascritch/machincast/issues/383)."""
		if self.items.tail_stream:
			return True
		sounds = []
		for line in self.items.lines():
			if line.data(0, CATEGORY) != "sound":
				continue
			if line.data(0, FEED) is not None:
				return True
			if line.data(0, ITEM) is not None:
				sounds.append(int(line.data(0, ITEM)))
		if sounds == []:
			return False
		with self.connection.transaction():
			found = self.connection.execute(
				"SELECT 1 FROM sounds WHERE type = 'stream' AND id = ANY(%s) LIMIT 1", (sounds,)
			).fetchone()
		return found is not None

	def _tick_end(self) -> None:
		"""Une fin cochée qui ne suit pas le début part d'une heure après lui."""
		ui = self.ui
		if ui.end.dateTime() <= ui.start.dateTime():
			ui.end.setDateTime(ui.start.dateTime().addSecs(int(DEFAULT_DURATION.total_seconds())))

	def _warn(self) -> None:
		"""Un événement vide, selon sa priorité, ou une banque « ne pas répéter » appelée juste après elle-même : cet
		appel sera sauté. La liste boucle, sauf pour une émission ou un spécial sans fin."""
		loop = (self._priority() not in ENDLESS_DOES_NOT_LOOP) or (self.ui.has_end.isChecked())
		self.ui.warning.setText("\n".join(self.items.warnings(loop)))
		empty = ""
		if self.items.lines() == []:
			empty = EMPTY_EVENT[self._priority()]
			if self.ui.end_of_list.currentData() == "lend_name":
				empty = LENDS_NAME
		self.warn(empty)

	def _write(self) -> int:
		ui = self.ui
		name = conform(ui.internal_name.text())
		if name == "":
			raise Refusal(_("The internal name is required."), ui.internal_name)
		taken = self.connection.execute(
			"SELECT 1 FROM events WHERE internal_name = %s AND id IS DISTINCT FROM %s AND deleted_at IS NULL",
			(name, self.identifier),
		).fetchone()
		if taken is not None:
			raise Refusal(_("Another event is already called “{name}”.").format(name=name), ui.internal_name)
		priority = self._priority()
		start, end = display.ticked_date(ui.has_start, ui.start), display.ticked_date(ui.has_end, ui.end)
		if (priority in ENDLESS_DOES_NOT_LOOP) and (start is None):
			raise Refusal(_("A show or a special has a start."), ui.priority, ui.has_start)
		if (start is not None) and (end is not None) and (end <= start):
			raise Refusal(_("The end must follow the start."), ui.has_start, ui.has_end)
		days = [day_name for day_name, day in zip(DAYS, self.days, strict=True) if day.isChecked()]
		self._refuse_overlap(name, priority, start, end, days)
		self._refuse_designated_fallback(priority)
		end_of_list = str(ui.end_of_list.currentData())
		end_fallback = None
		if end_of_list == "fallback":
			end_fallback = ui.end_fallback.currentData()
			if end_fallback is None:
				raise Refusal(_("Choose the fallback that follows the end of the list."), ui.end_of_list_caption)
		stream_fallback = None
		if ui.stream_fallback.isEnabled():
			stream_fallback = ui.stream_fallback.currentData()
		values = (
			name,
			(conform(ui.public_name.text())) or (None),
			priority,
			start,
			end,
			days,
			HIDINGS[ui.hiding.currentIndex()][0],
			end_of_list,
			end_fallback,
			stream_fallback,
		)
		if self.identifier is None:
			created = self.connection.execute(
				"INSERT INTO events"
				" (internal_name, public_name, priority, starts_at, ends_at, recurrence_days, hide_metadata,"
				" end_of_list, end_fallback_event_id, stream_fallback_event_id)"
				" VALUES (%s, %s, %s, %s, %s, %s::weekday[], %s, %s, %s, %s) RETURNING id",
				values,
			).fetchone()
			assert created is not None
			identifier = int(str(created[0]))
		else:
			identifier = self.identifier
			self.connection.execute(
				"UPDATE events SET internal_name = %s, public_name = %s, priority = %s, starts_at = %s, ends_at = %s,"
				" recurrence_days = %s::weekday[], hide_metadata = %s, end_of_list = %s, end_fallback_event_id = %s,"
				" stream_fallback_event_id = %s WHERE id = %s",
				(*values, identifier),
			)
		self.items.write(identifier)
		return identifier

	def _refuse_overlap(
		self, name: str, priority: str, start: datetime | None, end: datetime | None, days: list[str]
	) -> None:
		place = Event(
			id=-1,
			name=name,
			priority=Priority(priority),
			start=start,
			end=end,
			days=frozenset(DAYS.index(day) for day in days),
			modified_at=NEVER,
			skipped_list=self._skipped_list(),
		)
		others = [other for other in read_grid(self.connection) if other.id != self.identifier]
		found = overlap(place, others, since=self.clock.now())
		if found is not None:
			other, instant = found
			raise Refusal(
				_("Overlaps the event “{name}”, of the same priority, on {date}.").format(
					name=other.name, date=date_and_hour(instant)
				),
				self.ui.priority,
				self.ui.has_start,
				self.ui.has_end,
			)

	def _skipped_list(self) -> frozenset[date]:
		"""Les jours de ses sessions sautées, qui ne chevauchent rien (https://github.com/dascritch/machincast/issues/273)."""
		if self.identifier is None:
			return frozenset()
		lines = self.connection.execute(
			"SELECT day FROM event_skips WHERE event_id = %s", (self.identifier,)
		).fetchall()
		return frozenset(day for (day,) in lines if isinstance(day, date))

	def _refuse_designated_fallback(self, priority: str) -> None:
		"""Un événement de secours qu'un stream désigne garde sa priorité."""
		if (self.identifier is None) or (priority == "fallback"):
			return
		streams = self.connection.execute(
			"SELECT COALESCE(title, stream_url) FROM sounds WHERE fallback_event_id = %s ORDER BY 1",
			(self.identifier,),
		).fetchall()
		events = self.connection.execute(
			"SELECT internal_name FROM events WHERE (end_fallback_event_id = %s OR stream_fallback_event_id = %s)"
			" AND deleted_at IS NULL ORDER BY 1",
			(self.identifier, self.identifier),
		).fetchall()
		if events != []:
			names = ", ".join(_("“{event}”").format(event=event) for (event,) in events)
			raise Refusal(
				_("Events have this event as fallback: {names}. It stays of priority “Fallback”.").format(names=names),
				self.ui.priority,
			)
		if streams != []:
			names = ", ".join(_("“{stream}”").format(stream=stream) for (stream,) in streams)
			raise Refusal(
				_("Streams have this event as fallback: {names}. It stays of priority “Fallback”.").format(names=names),
				self.ui.priority,
			)
