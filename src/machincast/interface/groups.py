"""Actions sur plusieurs sonores ou plusieurs banques à la fois (https://github.com/dascritch/machincast/issues/114,
spec § 8.2).

Les listes des sonores et des banques (machincast.interface.lists) proposent ces actions au clic droit sur leur
sélection ; la fenêtre (machincast.interface.window) fait choisir des banques s'il le faut, demande confirmation
(dialogs.confirm_action), puis exécute l'action dans une transaction, avec le rôle de l'interface.

- Activer, désactiver : l'état des sonores choisis, comme dans leur fiche ; un sonore en aperçu reste en aperçu,
  jusqu'à sa vérification.
- Ajouter à des banques : chaque sonore à la fin de chaque banque choisie, sauf s'il y est déjà.
- Retirer de banques : parmi les banques où figure l'un des sonores ; les positions restantes se resserrent. Un
  sonore dont le fichier est dans un répertoire de la banque y reviendra à la prochaine indexation.
- Audit complet demandé (sounds.audit_requested) : la prochaine indexation, même rapide, revérifie en entier les
  fichiers marqués (machincast.indexer.check) ; un stream n'est jamais vérifié.
- Masquage de l'artiste et du titre des banques choisies : masqués, affichés, ou hérités du sonore.

Chaque action rend la phrase qu'annonce la barre d'état : ce qui a réellement changé.
"""

from collections.abc import Callable
from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow

from machincast.i18n import _, counted
from machincast.interface.intents import ADD, REMOVE, label, without_intent

Connection = psycopg.Connection[TupleRow]
RECHECK = _("The next indexing, even quick, will check them again in full.")


def _sounds(quantity: int) -> str:
	"""« 1 sonore », « 2 sonores », « 0 sonore »."""
	return counted("{count} sound", "{count} sounds", quantity)


def _banks(quantity: int) -> str:
	return counted("{count} bank", "{count} banks", quantity)


def _names(names: list[str]) -> str:
	return ", ".join(_("“{name}”").format(name=name) for name in names)


def _to_banks(names: list[str]) -> str:
	if len(names) == 1:
		return _("to bank {names}").format(names=_names(names))
	return _("to banks {names}").format(names=_names(names))


def _of_banks(names: list[str]) -> str:
	if len(names) == 1:
		return _("from bank {names}").format(names=_names(names))
	return _("from banks {names}").format(names=_names(names))


def _identifiers(rows: list[TupleRow]) -> set[int]:
	return {int(str(row[0])) for row in rows}


@dataclass(frozen=True)
class Action:
	key: str
	text: str
	"""L'entrée du menu ; « … » quand un choix de banques la suit."""
	question: Callable[[int, list[str]], str]
	"""Le texte de la confirmation, selon le nombre d'éléments choisis et les noms des banques choisies."""
	run: Callable[[Connection, list[int], list[int]], str]
	"""Dans une transaction : l'action sur les éléments et les banques choisies ; l'annonce de la barre d'état."""
	choice: str = ""
	"""« toutes » : choisir parmi toutes les banques ; « leurs » : parmi celles des sonores ; « » : aucun choix."""

	@property
	def title(self) -> str:
		"""Le titre de la confirmation : l'entrée du menu, sans son emoji ni « … »
		(https://github.com/dascritch/machincast/issues/294)."""
		return without_intent(self.text).removesuffix("…")

	@property
	def button(self) -> str:
		"""Le bouton qui confirme : l'entrée du menu, avec son emoji, sans « … »."""
		return self.text.removesuffix("…")


# ─── Sonores ───────────────────────────────────────────────


def _change_state(state: str, done: Callable[[int], str]) -> Callable[[Connection, list[int], list[int]], str]:
	def run(connection: Connection, sounds: list[int], _banks: list[int]) -> str:
		changes = connection.execute(
			"UPDATE sounds SET state = %s WHERE id = ANY(%s) AND state NOT IN ('preview', %s) RETURNING id",
			(state, sounds, state),
		).fetchall()
		return done(len(changes))

	return run


def _state_question(verb: str) -> Callable[[int, list[str]], str]:
	def question(quantity: int, _bank_names: list[str]) -> str:
		return _("{verb} {sounds}? A sound in preview stays in preview.").format(verb=verb, sounds=_sounds(quantity))

	return question


def _add(connection: Connection, sounds: list[int], banks: list[int]) -> str:
	added_list: set[int] = set()
	touched_list: set[int] = set()
	for bank in banks:
		present_list = _identifiers(
			connection.execute("SELECT sound_id FROM bank_sounds WHERE bank_id = %s FOR UPDATE", (bank,)).fetchall()
		)
		new_list = [sound for sound in sounds if sound not in present_list]
		if new_list == []:
			continue
		line = connection.execute(
			"SELECT COALESCE(MAX(position), 0) FROM bank_sounds WHERE bank_id = %s", (bank,)
		).fetchone()
		assert line is not None
		end = int(str(line[0]))
		with connection.cursor() as slider:
			slider.executemany(
				"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)",
				[(bank, sound, end + rank) for rank, sound in enumerate(new_list, start=1)],
			)
		added_list |= set(new_list)
		touched_list.add(bank)
	return _("{sounds} {banks}.").format(
		sounds=counted("{count} sound added", "{count} sounds added", len(added_list)),
		banks=counted("to {count} bank", "to {count} banks", len(touched_list)),
	)


def _remove(connection: Connection, sounds: list[int], banks: list[int]) -> str:
	removed_list = connection.execute(
		"DELETE FROM bank_sounds WHERE sound_id = ANY(%s) AND bank_id = ANY(%s) RETURNING sound_id, bank_id",
		(sounds, banks),
	).fetchall()
	touched_list = sorted({int(str(bank)) for _sound, bank in removed_list})
	# Les positions restantes se resserrent ; leur unicité n'est vérifiée qu'en fin de transaction.
	connection.execute(
		"UPDATE bank_sounds bs SET position = r.rang FROM ("
		" SELECT bank_id, sound_id, row_number() OVER (PARTITION BY bank_id ORDER BY position) AS rang"
		" FROM bank_sounds WHERE bank_id = ANY(%s)) r"
		" WHERE bs.bank_id = r.bank_id AND bs.sound_id = r.sound_id",
		(touched_list,),
	)
	sound_count = len(_identifiers(removed_list))
	return _("{sounds} {banks}.").format(
		sounds=counted("{count} sound removed", "{count} sounds removed", sound_count),
		banks=counted("from {count} bank", "from {count} banks", len(touched_list)),
	)


def _audit_announcement(marks: int) -> str:
	return counted(
		"Full audit requested for {count} sound, at the next indexing.",
		"Full audit requested for {count} sounds, at the next indexing.",
		marks,
	)


def _ask_audit(connection: Connection, sounds: list[int], _banks: list[int]) -> str:
	marks = connection.execute(
		"UPDATE sounds SET audit_requested = true WHERE id = ANY(%s) AND type = 'file' RETURNING id", (sounds,)
	).fetchall()
	return _audit_announcement(len(marks))


def _audit_question(quantity: int, _bank_names: list[str]) -> str:
	recheck = RECHECK
	if quantity == 1:
		recheck = _("The next indexing, even quick, will check it again in full.")
	return _("Request the full audit of {sounds}? {recheck}").format(sounds=_sounds(quantity), recheck=recheck)


SOUNDS: tuple[Action, ...] = (
	Action(
		"activer",
		_("Enable"),
		_state_question(_("Enable")),
		_change_state("active", lambda n: counted("{count} sound enabled.", "{count} sounds enabled.", n)),
	),
	Action(
		"desactiver",
		_("Disable"),
		_state_question(_("Disable")),
		_change_state("disabled", lambda n: counted("{count} sound disabled.", "{count} sounds disabled.", n)),
	),
	Action(
		"ajouter",
		label(ADD, _("Add to banks…")),
		lambda quantity, names: _(
			"Add {sounds} {to_banks}? A sound already in a bank is not added a second time."
		).format(sounds=_sounds(quantity), to_banks=_to_banks(names)),
		_add,
		"toutes",
	),
	Action(
		"retirer",
		label(REMOVE, _("Remove from banks…")),
		lambda quantity, names: _(
			"Remove {sounds} {of_banks}? A sound whose file is in a directory of a bank will come back "
			"at the next indexing."
		).format(sounds=_sounds(quantity), of_banks=_of_banks(names)),
		_remove,
		"leurs",
	),
	Action("audit", _("Request a full audit"), _audit_question, _ask_audit),
)


# ─── Banques ───────────────────────────────────────────────


def _ask_bank_audit(connection: Connection, banks: list[int], _chosen_list: list[int]) -> str:
	marks = connection.execute(
		"UPDATE sounds SET audit_requested = true WHERE type = 'file'"
		" AND id IN (SELECT sound_id FROM bank_sounds WHERE bank_id = ANY(%s)) RETURNING id",
		(banks,),
	).fetchall()
	return _audit_announcement(len(marks))


def _hide(value: bool | None, state: str) -> Callable[[Connection, list[int], list[int]], str]:
	def run(connection: Connection, banks: list[int], _chosen_list: list[int]) -> str:
		changed_list = connection.execute(
			"UPDATE banks SET hide_metadata = %s WHERE id = ANY(%s) RETURNING id", (value, banks)
		).fetchall()
		return _("Artist and title {state} for {banks}.").format(state=state, banks=_banks(len(changed_list)))

	return run


BANKS: tuple[Action, ...] = (
	Action(
		"audit",
		_("Request the full audit of their sounds"),
		lambda quantity, _names: _("Request the full audit of the sounds of {banks}? {recheck}").format(
			banks=_banks(quantity), recheck=RECHECK
		),
		_ask_bank_audit,
	),
	Action(
		"masquer",
		_("Hide the artist and the title"),
		lambda quantity, _names: _("Hide the artist and the title of the sounds of {banks}?").format(
			banks=_banks(quantity)
		),
		_hide(True, _("hidden")),
	),
	Action(
		"afficher",
		_("Show the artist and the title"),
		lambda quantity, _names: _("Show the artist and the title of the sounds of {banks}?").format(
			banks=_banks(quantity)
		),
		_hide(False, _("shown")),
	),
	Action(
		"heriter",
		_("Artist and title inherited from the sound"),
		lambda quantity, _names: _("Leave to the sound the hiding of the artist and the title of {banks}?").format(
			banks=_banks(quantity)
		),
		_hide(None, _("inherited from the sound")),
	),
)

ACTIONS: dict[str, tuple[Action, ...]] = {"sound": SOUNDS, "bank": BANKS}
"""Les actions sur la sélection de chaque liste ; les autres listes ne sélectionnent qu'une ligne."""


def action(category: str, key: str) -> Action:
	(found,) = [action for action in ACTIONS[category] if action.key == key]
	return found


def sound_banks(connection: Connection, sounds: list[int]) -> list[int]:
	"""Les banques où figure l'un des sonores, par nom. À appeler dans une transaction."""
	return [
		int(str(bank))
		for (bank,) in connection.execute(
			"SELECT b.id FROM banks b WHERE b.id IN (SELECT bank_id FROM bank_sounds WHERE sound_id = ANY(%s))"
			" ORDER BY b.internal_name, b.id",
			(sounds,),
		)
	]


def bank_names(connection: Connection, banks: list[int]) -> list[str]:
	"""Les noms des banques, dans l'ordre donné. À appeler dans une transaction."""
	names = {
		int(str(bank)): str(name)
		for bank, name in connection.execute("SELECT id, internal_name FROM banks WHERE id = ANY(%s)", (banks,))
	}
	return [names[bank] for bank in banks if bank in names]
