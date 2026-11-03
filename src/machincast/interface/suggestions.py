"""Suggestions au lancement de l'interface (https://github.com/dascritch/machincast/issues/119, spec § 8.10).

Au lancement, si les suggestions sont actives (interface.suggestions), l'interface cherche ce qui manque pour démarrer
(manquants) : un événement de priorité fil musical, les banques de BANQUES (par leur nom interne, sans tenir compte des
majuscules) et, sur une vraie sortie, la carte son de l'antenne. S'il manque quelque chose, une fenêtre modale
(SuggestionsWindow, par machincast.interface.dialogs.suggest) le propose, chaque élément coché par défaut. Tant que
l'antenne n'a pas de carte son, la fenêtre propose d'abord, en tête, le bloc des cartes son des préférences
(machincast.interface.sound_cards, https://github.com/dascritch/machincast/issues/339) : le type de sortie, et les
cartes
de l'antenne et de la pré-écoute, chacune avec son bouton « Tester », selon le service de diffusion. Avec les seules
cartes son à choisir, son bouton est « Enregistrer », sinon « Créer » ; il est grisé tant que l'antenne et la
pré-écoute ont la même carte.

- « Créer » (creer) crée ce qui est coché : le fil musical, permanent, comme le fil musical garanti
  (machincast.interface.background_programming) ; les banques, sans répertoire, chacune avec ses réglages (REGLAGES) :
  l'identifiant station et les musiques, aléatoires ; les annonces (partenariats, publicités, bandes-annonces),
  séquentielles, enchaînées sans crossfade, imposé à 0 seconde à leurs sonores ; « Identifiant station » et
  « Bande-annonce émissions » marquées « ne pas répéter » ; les musiques de 15 minutes au plus, l'identifiant station
  et les annonces de 2 minutes au plus (https://github.com/dascritch/machincast/issues/231). Un fil musical encore
  vide, créé ou déjà là, reçoit la rotation type (ROTATION), avec les banques qui existent. Les cartes son choisies
  s'enregistrent dans audio.output, audio.device et audio.preview (enregistrer).
- « Plus tard » ne crée ni n'enregistre rien : la fenêtre revient au lancement suivant.
- « Ne plus proposer au lancement » écrit interface.suggestions = false dans le fichier de configuration
  (enregistrer), qui garde ses commentaires.
"""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import psycopg
import tomlkit
from psycopg.rows import TupleRow
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem, QWidget

from machincast.configuration import Audio, AudioOutput
from machincast.interface import background_programming
from machincast.interface.preferences import write_audio
from machincast.interface.sound_cards import SoundCards
from machincast.interface.ui.suggestions import Ui_SuggestionsWindow
from machincast.service import ABSENT, ServiceState

BACKGROUND_PROGRAMMING = "Fil musical"
"""La ligne du fil musical dans la fenêtre."""


@dataclass(frozen=True)
class Setting:
	"""Ce qu'une banque suggérée reçoit à sa création."""

	mode: str = "random"
	no_repeat: bool = False
	"""https://github.com/dascritch/machincast/issues/63"""
	max_duration: timedelta | None = None
	without_crossfade: bool = False
	"""Crossfades de début et de fin imposés à 0 seconde à tous ses sonores : ils s'enchaînent sans se mêler."""


MUSIC = Setting(max_duration=timedelta(minutes=15))
ANNOUNCEMENT = Setting(mode="sequential", max_duration=timedelta(minutes=2), without_crossfade=True)
SETTINGS = {
	"Identifiant station": Setting(no_repeat=True, max_duration=timedelta(minutes=2)),
	"Musique rotation lourde": MUSIC,
	"Musique rotation normale": MUSIC,
	"Musique rotation rare": MUSIC,
	"Musique rotation de nuit": Setting(),
	"Partenariats": ANNOUNCEMENT,
	"Publicités": ANNOUNCEMENT,
	"Bande-annonce émissions": Setting(
		mode="sequential", no_repeat=True, max_duration=timedelta(minutes=2), without_crossfade=True
	),
}
"""Les banques suggérées, dans l'ordre où la fenêtre les propose, et leurs réglages
(https://github.com/dascritch/machincast/issues/231)."""
BANKS = tuple(SETTINGS)
ROTATION = (
	"Identifiant station",
	"Musique rotation lourde",
	"Musique rotation normale",
	"Musique rotation lourde",
	"Musique rotation rare",
)
"""La liste d'un fil musical encore vide ; la rotation de nuit reste à placer à la main dans un événement de nuit."""


def label(bank: str) -> str:
	"""« Banque « Identifiant station » » : la ligne d'une banque dans la fenêtre."""
	return f"Banque « {bank} »"


@dataclass(frozen=True)
class Shortfalls:
	"""Ce qui manque pour démarrer."""

	background_programming: bool
	banks: tuple[str, ...]
	audio: Audio | None = None
	"""La configuration audio, que montrent les cartes son, quand l'antenne n'a pas de carte sur une vraie sortie ; None
	sinon (https://github.com/dascritch/machincast/issues/339)."""

	def items(self) -> list[str]:
		"""Les lignes à cocher de la fenêtre."""
		lines = [label(bank) for bank in self.banks]
		if self.background_programming:
			lines.insert(0, BACKGROUND_PROGRAMMING)
		return lines

	def empty(self) -> bool:
		return (not self.background_programming) and (not self.banks) and (self.audio is None)


@dataclass(frozen=True)
class Response:
	"""Ce que la fenêtre a décidé : creer est faux pour « Plus tard »."""

	create: bool
	background_programming: bool = False
	banks: tuple[str, ...] = ()
	output: AudioOutput | None = None
	"""Le type de sortie choisi ; None sans cartes son à choisir."""
	on_air: str | None = None
	preview: str | None = None
	more_offer: bool = False


def missing_list(connection: psycopg.Connection[TupleRow], audio: Audio) -> Shortfalls:
	"""Ce qui manque : fil musical, banques suggérées, carte son d'antenne sur une vraie sortie."""
	with connection.transaction():
		feed = connection.execute(
			"SELECT 1 FROM events WHERE priority = 'background_programming' AND deleted_at IS NULL LIMIT 1"
		).fetchone()
		existing_list = {
			str(name).casefold()
			for (name,) in connection.execute("SELECT internal_name FROM banks WHERE deleted_at IS NULL")
		}
	banks = tuple(bank for bank in BANKS if bank.casefold() not in existing_list)
	to_choose = None
	if audio.to_fill_in_on_air():
		to_choose = audio
	return Shortfalls(feed is None, banks, to_choose)


def create(connection: psycopg.Connection[TupleRow], response: Response) -> str | None:
	"""Crée ce que la réponse demande, puis remplit un fil musical encore vide ; ce que dit la barre d'état, ou None
	si rien n'est créé."""
	created_list: list[str] = []
	with connection.transaction():
		if response.background_programming:
			name = background_programming.guarantee(connection)
			if name is not None:
				created_list.append(f"le fil musical « {name} »")
		new_list = []
		for bank in response.banks:
			setting = SETTINGS[bank]
			rule = "sound"
			if setting.without_crossfade:
				rule = "forced"
			connection.execute(
				"INSERT INTO banks (internal_name, mode, no_repeat, max_duration, crossfade_start_rule,"
				" crossfade_start, crossfade_end_rule, crossfade_end)"
				" VALUES (%s, %s, %s, %s, %s, '0 s', %s, '0 s')",
				(bank, setting.mode, setting.no_repeat, setting.max_duration, rule, rule),
			)
			new_list.append(f"« {bank} »")
		if len(new_list) == 1:
			created_list.append(f"la banque {new_list[0]}")
		elif new_list:
			created_list.append(f"les banques {', '.join(new_list)}")
		_fill_empty_feed(connection)
	if not created_list:
		return None
	return f"Créés : {', '.join(created_list)}."


def _fill_empty_feed(connection: psycopg.Connection[TupleRow]) -> None:
	"""Le premier fil musical sans élément, par nom, reçoit la rotation type, avec les banques qui existent."""
	empty = connection.execute(
		"SELECT e.id FROM events e WHERE e.priority = 'background_programming' AND e.deleted_at IS NULL"
		" AND NOT EXISTS (SELECT 1 FROM event_items x WHERE x.event_id = e.id)"
		" ORDER BY e.internal_name LIMIT 1"
	).fetchone()
	if empty is None:
		return
	banks = {
		str(name).casefold(): int(str(identifier))
		for identifier, name in connection.execute(
			"SELECT id, internal_name FROM banks WHERE deleted_at IS NULL ORDER BY id"
		)
	}
	position = 0
	for bank in ROTATION:
		identifier = banks.get(bank.casefold())
		if identifier is None:
			continue
		position += 1
		connection.execute(
			"INSERT INTO event_items (event_id, position, bank_id) VALUES (%s, %s, %s)",
			(empty[0], position, identifier),
		)


def save(path: Path, response: Response) -> None:
	"""Écrit dans le fichier de configuration les cartes son choisies, et l'arrêt des suggestions ; le reste du fichier
	reste tel quel, commentaires compris. « Plus tard » n'enregistre pas les cartes son."""
	cards = (response.create) and (response.output is not None)
	if (not cards) and (not response.more_offer):
		return
	document = tomlkit.parse(path.read_text(encoding="utf-8"))
	if cards:
		write_audio(document, response.output, response.on_air, response.preview)
	if response.more_offer:
		if "interface" not in document:
			document.add("interface", tomlkit.table())
		section_interface = document["interface"]
		assert isinstance(section_interface, tomlkit.items.Table)
		section_interface["suggestions"] = False
	path.write_text(tomlkit.dumps(document), encoding="utf-8")


class SuggestionsWindow(QDialog):
	"""La fenêtre des suggestions : les cartes son en tête, tant que l'antenne n'en a pas ; puis une ligne cochée par
	élément manquant."""

	def __init__(self, gaps: Shortfalls, parent: QWidget | None = None, service: ServiceState = ABSENT) -> None:
		super().__init__(parent)
		self.ui = Ui_SuggestionsWindow()
		self.ui.setupUi(self)
		self.gaps = gaps
		for text in gaps.items():
			line = QListWidgetItem(text, self.ui.items)
			line.setFlags(line.flags() | Qt.ItemFlag.ItemIsUserCheckable)
			line.setCheckState(Qt.CheckState.Checked)
		to_create = bool(gaps.items())
		self.ui.items.setVisible(to_create)
		self.ui.explanation.setVisible(to_create)
		self.cards: SoundCards | None = None
		self.ui.sound_cards_group.setVisible(gaps.audio is not None)
		if gaps.audio is not None:
			audio = gaps.audio
			self.cards = SoundCards(audio.output, audio.device, audio.preview, service, self.ui.sound_cards_group)
			self.ui.sound_cards_layout.addWidget(self.cards)
			self.cards.changed.connect(self._validate)
		buttons = self.ui.buttons
		text = "Enregistrer"
		if to_create:
			text = "Créer"
		buttons.button(QDialogButtonBox.StandardButton.Ok).setText(text)
		buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Plus tard")
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		self._validate()

	def _validate(self) -> None:
		"""Jamais la même carte à l'antenne et à la pré-écoute."""
		valid = (self.cards is None) or (self.cards.valid())
		self.ui.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(valid)

	def _ticked_list(self) -> set[str]:
		list_ = self.ui.items
		lines = [list_.item(rank) for rank in range(list_.count())]
		return {line.text() for line in lines if line.checkState() == Qt.CheckState.Checked}

	def response(self) -> Response:
		"""Ce qui est décidé : tout ce qui est coché sur « Créer », rien sur « Plus tard »."""
		more = self.ui.more_offer.isChecked()
		if self.result() != QDialog.DialogCode.Accepted:
			return Response(create=False, more_offer=more)
		ticked_list = self._ticked_list()
		output, on_air, preview = None, None, None
		if self.cards is not None:
			output = self.cards.chosen_output()
			on_air = self.cards.chosen_on_air()
			preview = self.cards.chosen_preview()
		return Response(
			create=True,
			background_programming=BACKGROUND_PROGRAMMING in ticked_list,
			banks=tuple(bank for bank in self.gaps.banks if label(bank) in ticked_list),
			output=output,
			on_air=on_air,
			preview=preview,
			more_offer=more,
		)
