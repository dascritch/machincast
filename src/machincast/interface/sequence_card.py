"""Fiche d'une séquence (https://github.com/dascritch/machincast/issues/112, spec § 8.12).

La fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.window), depuis la liste des séquences, ou vide
pour une nouvelle séquence. Enregistrement, annulation et fermeture : machincast.interface.card.

- Les noms sont enregistrés conformés (machincast.conformation, https://github.com/dascritch/machincast/issues/108) ; un
  nom public vide n'en est pas un (NULL).
- Le masquage « selon la banque ou le sonore » (NULL) laisse décider le niveau suivant ; « masqués » et « affichés »
  l'imposent.
- Les éléments sont des sonores et des banques, jamais une autre séquence (machincast.interface.items). Une
  séquence vide s'enregistre, pour être complétée plus tard, avec un avertissement : elle ne joue rien, la diffusion
  la saute, et la liste des séquences la montre en anomalie (https://github.com/dascritch/machincast/issues/138).
  L'avertissement d'une banque « ne pas répéter » appelée deux fois de suite ne boucle pas : la séquence ne reprend
  pas à son début.
- Les événements où la séquence figure sont montrés ; ouvrir un événement ouvre sa fiche.
- Sa copie (https://github.com/dascritch/machincast/issues/130) garde tout : nom public, masquage et éléments ; elle
  ne figure encore dans aucun événement.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QWidget

from machincast.clock import Clock
from machincast.conformation import conform
from machincast.i18n import _
from machincast.interface.card import Card, Connection, Refusal
from machincast.interface.items import Buttons, ItemList
from machincast.interface.lists import EMPTY_SEQUENCE
from machincast.interface.ui.sequence_card import Ui_SequenceCard

HIDINGS: tuple[tuple[bool | None, str], ...] = (
	(None, _("According to the bank or the sound")),
	(True, _("Hidden by the public name of the sequence")),
	(False, _("Shown")),
)
"""Valeurs de sequences.hide_metadata, dans l'ordre du choix de la fiche."""
EVENT = Qt.ItemDataRole.UserRole
"""Rôle qui porte l'identifiant d'un événement, dans la liste des événements."""
REPETITION = _("A sound or a bank may come back several times in a sequence.")
"""Remarque des choix de sonores et de banques."""


class SequenceCard(Card):
	category = "sequence"

	def __init__(
		self, connection: Connection, identifier: int | None, clock: Clock, parent: QWidget | None = None
	) -> None:
		super().__init__(connection, identifier, clock, parent)
		self.ui = Ui_SequenceCard()
		self.ui.setupUi(self)
		self.plug(self.ui.save, self.ui.cancel, self.ui.delete, self.ui.message, self.ui.duplicate)
		for _value, text in HIDINGS:
			self.ui.hiding.addItem(text)
		self._name = ""
		ui = self.ui
		buttons = Buttons({"sound": ui.add_sounds, "bank": ui.add_banks}, ui.remove_item, ui.raise_, ui.go_down)
		self.items = ItemList(self, ui.items, buttons, "sequence_items", "sequence_id", REPETITION)
		self.items.changed.connect(self._modify)
		self.items.changed.connect(self._warn)
		ui.internal_name.textChanged.connect(self._modify)
		ui.public_name.textChanged.connect(self._modify)
		ui.hiding.currentIndexChanged.connect(self._modify)
		ui.events.itemActivated.connect(self._open_event)
		self.load()

	def title(self) -> str:
		if self.is_copy():
			return _("New sequence, copy of {name}").format(name=self._name)
		if self.identifier is None:
			return _("New sequence")
		return _("Sequence: {name}").format(name=self._name)

	def _read(self) -> None:
		"""Lit la séquence en base, ou celle qu'elle copie ; une nouvelle séquence est vide, au masquage hérité de la
		banque ou du sonore."""
		sequence: tuple[object, ...] = ("", None, None)
		events: list[tuple[object, ...]] = []
		lu = self.lu()
		with self.connection.transaction():
			if lu is not None:
				line = self.connection.execute(
					"SELECT internal_name, public_name, hide_metadata FROM sequences WHERE id = %s", (lu,)
				).fetchone()
				assert line is not None, f"séquence {lu} absente"
				sequence = line
			if self.identifier is not None:
				events = self.connection.execute(
					"SELECT DISTINCT ev.id, ev.internal_name FROM events ev"
					" JOIN event_items ee ON ee.event_id = ev.id"
					" WHERE ee.sequence_id = %s AND ev.deleted_at IS NULL ORDER BY ev.internal_name, ev.id",
					(self.identifier,),
				).fetchall()
			self.items.load(lu, self.is_copy())
		name, public_name, hiding = sequence
		self._name = str(name)
		self.ui.internal_name.setText(self._name)
		if self.is_copy():
			self.ui.internal_name.setText(self.name_of_copy(self._name))
		self.ui.public_name.setText(str((public_name) or ("")))
		self.ui.hiding.setCurrentIndex(next(i for i, (value, _text) in enumerate(HIDINGS) if value is hiding))
		self.ui.events.clear()
		for identifier, event_name in events:
			item = QListWidgetItem(str(event_name))
			item.setData(EVENT, int(str(identifier)))
			self.ui.events.addItem(item)
		# Une liste lue vide ne change pas : l'avertissement d'une séquence vide se pose ici.
		self._warn()

	def _write(self) -> int:
		name = conform(self.ui.internal_name.text())
		if name == "":
			raise Refusal(_("The internal name is required."), self.ui.internal_name)
		taken = self.connection.execute(
			"SELECT 1 FROM sequences WHERE internal_name = %s AND id IS DISTINCT FROM %s AND deleted_at IS NULL",
			(name, self.identifier),
		).fetchone()
		if taken is not None:
			raise Refusal(_("Another sequence is already called “{name}”.").format(name=name), self.ui.internal_name)
		values = (
			name,
			(conform(self.ui.public_name.text())) or (None),
			HIDINGS[self.ui.hiding.currentIndex()][0],
		)
		if self.identifier is None:
			created = self.connection.execute(
				"INSERT INTO sequences (internal_name, public_name, hide_metadata) VALUES (%s, %s, %s) RETURNING id",
				values,
			).fetchone()
			assert created is not None
			identifier = int(str(created[0]))
		else:
			identifier = self.identifier
			self.connection.execute(
				"UPDATE sequences SET internal_name = %s, public_name = %s, hide_metadata = %s WHERE id = %s",
				(*values, identifier),
			)
		self.items.write(identifier)
		return identifier

	def _warn(self) -> None:
		"""Une séquence vide, ou une banque « ne pas répéter » appelée juste après elle-même : cet appel sera sauté."""
		self.ui.warning.setText("\n".join(self.items.warnings(False)))
		empty = ""
		if self.items.lines() == []:
			empty = EMPTY_SEQUENCE
		self.warn(empty)

	def _open_event(self, item: QListWidgetItem) -> None:
		self.requested_opening.emit("event", int(item.data(EVENT)), item.text())
