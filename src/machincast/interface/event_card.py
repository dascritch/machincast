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
from machincast.interface import display
from machincast.interface.calendar import day_and_month, long_date
from machincast.interface.card import ORANGE, Card, Connection, Refusal
from machincast.interface.items import Buttons, ItemList
from machincast.interface.lists import EMPTY_EVENT
from machincast.interface.sessions import Session, next_skipped, overlapped, reinstate, started
from machincast.interface.ui.event_card import Ui_EventCard
from machincast.player.grid import DAYS, NEVER, Event, Priority, overlap, read_grid

PRIORITIES: tuple[tuple[str, str], ...] = (
	("fallback", "Secours"),
	("background_programming", "Fil musical"),
	("show", "Émission"),
	("special", "Spécial"),
)
"""Valeurs de events.priority, dans l'ordre du choix de la fiche : de la plus basse à la plus haute, comme le type
event_priority (https://github.com/dascritch/machincast/issues/253)."""
NEW = "show"
"""Priorité d'un nouvel événement."""
ENDLESS_DOES_NOT_LOOP = ("show", "special")
"""Priorités dont la liste ne boucle pas, sans fin : l'occurrence se termine au bout de sa liste."""
HIDINGS: tuple[tuple[bool | None, str], ...] = (
	(None, "Selon la séquence, la banque ou le sonore"),
	(True, "Masqué par le nom public de l'événement"),
	(False, "Affichés"),
)
"""Valeurs de events.hide_metadata, dans l'ordre du choix de la fiche."""
REPETITION = "Un sonore, une banque ou une séquence peut revenir plusieurs fois dans un événement."
"""Remarque des choix d'éléments."""
DEFAULT_DURATION = timedelta(hours=1)
"""Écart entre le début et une fin qui se coche."""
SESSION_OUTLINE = f"QFrame#session_sautee {{ border: 4px solid {ORANGE}; }}"
"""Le liseret d'une session sautée : un avertissement, de l'orange de ceux de la fiche."""
REINSTATE = "Rétablir"
STARTED = "Elle a déjà commencé : elle ne se rétablit plus."


def _show(date: QDateTimeEdit, instant: datetime) -> None:
	date.setDateTime(QDateTime.fromSecsSinceEpoch(int(instant.timestamp())))


class EventCard(Card):
	category = "événement"
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
				"sonore": ui.add_sounds,
				"banque": ui.add_banks,
				"séquence": ui.add_sequences,
				"feed": ui.add_feeds,
			},
			ui.remove_item,
			ui.raise_,
			ui.go_down,
		)
		self.items = ItemList(self, ui.items, buttons, "event_items", "event_id", REPETITION)
		self.items.changed.connect(self._modify)
		self.items.changed.connect(self._warn)
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
		for field in (ui.start, ui.end):
			field.dateTimeChanged.connect(self._modify)
		for day in self.days:
			day.toggled.connect(self._modify)
		self.load()

	def title(self) -> str:
		if self.is_copy():
			return f"Nouvel événement, copie de {self._name}"
		if self.identifier is None:
			return "Nouvel événement"
		return f"Événement : {self._name}"

	def _priority(self) -> str:
		return PRIORITIES[self.ui.priority.currentIndex()][0]

	def _read(self) -> None:
		"""Lit l'événement en base, ou celui qu'il copie, sans ses dates ni ses jours ; un nouvel événement est une
		émission, sans dates, au masquage hérité."""
		event: tuple[object, ...] = ("", None, NEW, None, None, [], None)
		lu = self.lu()
		with self.connection.transaction():
			if lu is not None:
				line = self.connection.execute(
					"SELECT internal_name, public_name, priority::text, starts_at, ends_at, recurrence_days::text[],"
					" hide_metadata FROM events WHERE id = %s",
					(lu,),
				).fetchone()
				assert line is not None, f"événement {lu} absent"
				event = line
			self.items.load(lu, self.is_copy())
		name, public_name, priority, start, end, days, hiding = event
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
		# Une priorité déjà choisie ne change pas l'index : l'avertissement ne suit pas de lui-même.
		self._grid()
		self._warn()
		self._announce_session()

	# ─── Session sautée (https://github.com/dascritch/machincast/issues/295) ───

	def _build_session_announcement(self) -> None:
		"""L'annonce, sous l'erreur de la fiche, cachée sans session sautée."""
		self.skipped_session = QFrame(self)
		self.skipped_session.setObjectName("skipped_session")
		self.skipped_session.setStyleSheet(SESSION_OUTLINE)
		self.skipped_session.setAccessibleName("Session sautée")
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
		will_play = "ne joue pas" if started(session, now) else "ne jouera pas"
		self.session_text.setText(
			f"La session du {long_date(session.start.date())} à {session.start:%H:%M} est sautée : elle {will_play}."
		)
		self.reinstate_session.setEnabled(hindrance is None)
		self.reinstate_session.setToolTip(
			(hindrance) or ("Rétablir la session : elle jouera de nouveau, sans toucher aux champs de la fiche.")
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
		return (
			f"« {other.name} », de même priorité, a pris sa place le {day_and_month(instant.date())} à {instant:%H:%M}."
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
			self.flag_error(f"Session non rétablie : {hindrance}")
			return
		name, day = session.event.name, session.start.date()
		self.restored_session.emit(f"Session de « {name} » du {day_and_month(day)} à {session.start:%H:%M} rétablie.")

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
		self.warn(empty)

	def _write(self) -> int:
		ui = self.ui
		name = conform(ui.internal_name.text())
		if name == "":
			raise Refusal("Le nom interne est obligatoire.", ui.internal_name)
		taken = self.connection.execute(
			"SELECT 1 FROM events WHERE internal_name = %s AND id IS DISTINCT FROM %s AND deleted_at IS NULL",
			(name, self.identifier),
		).fetchone()
		if taken is not None:
			raise Refusal(f"Un autre événement s'appelle déjà « {name} ».", ui.internal_name)
		priority = self._priority()
		start, end = display.ticked_date(ui.has_start, ui.start), display.ticked_date(ui.has_end, ui.end)
		if (priority in ENDLESS_DOES_NOT_LOOP) and (start is None):
			raise Refusal("Une émission ou un spécial a un début.", ui.priority, ui.has_start)
		if (start is not None) and (end is not None) and (end <= start):
			raise Refusal("La fin doit suivre le début.", ui.has_start, ui.has_end)
		days = [day_name for day_name, day in zip(DAYS, self.days, strict=True) if day.isChecked()]
		self._refuse_overlap(name, priority, start, end, days)
		self._refuse_designated_fallback(priority)
		values = (
			name,
			(conform(ui.public_name.text())) or (None),
			priority,
			start,
			end,
			days,
			HIDINGS[ui.hiding.currentIndex()][0],
		)
		if self.identifier is None:
			created = self.connection.execute(
				"INSERT INTO events"
				" (internal_name, public_name, priority, starts_at, ends_at, recurrence_days, hide_metadata)"
				" VALUES (%s, %s, %s, %s, %s, %s::weekday[], %s) RETURNING id",
				values,
			).fetchone()
			assert created is not None
			identifier = int(str(created[0]))
		else:
			identifier = self.identifier
			self.connection.execute(
				"UPDATE events SET internal_name = %s, public_name = %s, priority = %s, starts_at = %s, ends_at = %s,"
				" recurrence_days = %s::weekday[], hide_metadata = %s WHERE id = %s",
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
				f"Chevauche l'événement « {other.name} », de même priorité, le {instant:%d/%m/%Y à %H:%M}.",
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
		if streams != []:
			names = ", ".join(f"« {stream} »" for (stream,) in streams)
			raise Refusal(
				f"Des streams ont cet événement pour secours : {names}. Il reste de priorité « Secours ».",
				self.ui.priority,
			)
