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

from machincast.interface.intents import ADD, REMOVE, label, without_intent

Connection = psycopg.Connection[TupleRow]
RECHECK = "La prochaine indexation, même rapide, les revérifiera en entier."


def count(quantity: int, singular: str, plural: str) -> str:
	"""« 1 sonore », « 2 sonores », « 0 sonore »."""
	if quantity > 1:
		return f"{quantity} {plural}"
	return f"{quantity} {singular}"


def _sounds(quantity: int) -> str:
	return count(quantity, "sonore", "sonores")


def _banks(quantity: int) -> str:
	return count(quantity, "banque", "banques")


def _names(names: list[str]) -> str:
	return ", ".join(f"« {name} »" for name in names)


def _to_banks(names: list[str]) -> str:
	if len(names) == 1:
		return f"à la banque {_names(names)}"
	return f"aux banques {_names(names)}"


def _of_banks(names: list[str]) -> str:
	if len(names) == 1:
		return f"de la banque {_names(names)}"
	return f"des banques {_names(names)}"


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


def _change_state(state: str, done: str, facts: str) -> Callable[[Connection, list[int], list[int]], str]:
	def run(connection: Connection, sounds: list[int], _banks: list[int]) -> str:
		changes = connection.execute(
			"UPDATE sounds SET state = %s WHERE id = ANY(%s) AND state NOT IN ('preview', %s) RETURNING id",
			(state, sounds, state),
		).fetchall()
		return f"{count(len(changes), done, facts)}."

	return run


def _state_question(verb: str) -> Callable[[int, list[str]], str]:
	def question(quantity: int, _bank_names: list[str]) -> str:
		return f"{verb} {_sounds(quantity)} ? Un sonore en aperçu reste en aperçu."

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
	return f"{count(len(added_list), 'sonore ajouté', 'sonores ajoutés')} {_a(len(touched_list))}."


def _a(banks: int) -> str:
	return f"à {count(banks, 'banque', 'banques')}"


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
	de = f"de {count(len(touched_list), 'banque', 'banques')}"
	return f"{count(sound_count, 'sonore retiré', 'sonores retirés')} {de}."


def _audit_announcement(marks: int) -> str:
	return f"Audit complet demandé pour {count(marks, 'sonore', 'sonores')}, à la prochaine indexation."


def _ask_audit(connection: Connection, sounds: list[int], _banks: list[int]) -> str:
	marks = connection.execute(
		"UPDATE sounds SET audit_requested = true WHERE id = ANY(%s) AND type = 'file' RETURNING id", (sounds,)
	).fetchall()
	return _audit_announcement(len(marks))


def _audit_question(quantity: int, _bank_names: list[str]) -> str:
	recheck = RECHECK
	if quantity == 1:
		recheck = "La prochaine indexation, même rapide, le revérifiera en entier."
	return f"Demander l'audit complet de {_sounds(quantity)} ? {recheck}"


SOUNDS: tuple[Action, ...] = (
	Action(
		"activer", "Activer", _state_question("Activer"), _change_state("active", "sonore activé", "sonores activés")
	),
	Action(
		"desactiver",
		"Désactiver",
		_state_question("Désactiver"),
		_change_state("disabled", "sonore désactivé", "sonores désactivés"),
	),
	Action(
		"ajouter",
		label(ADD, "Ajouter à des banques…"),
		lambda quantity, names: (
			f"Ajouter {_sounds(quantity)} {_to_banks(names)} ?"
			" Un sonore déjà dans une banque n'y est pas ajouté une seconde fois."
		),
		_add,
		"toutes",
	),
	Action(
		"retirer",
		label(REMOVE, "Retirer de banques…"),
		lambda quantity, names: (
			f"Retirer {_sounds(quantity)} {_of_banks(names)} ?"
			" Un sonore dont le fichier est dans un répertoire d'une banque y reviendra à la prochaine indexation."
		),
		_remove,
		"leurs",
	),
	Action("audit", "Demander un audit complet", _audit_question, _ask_audit),
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
		return f"Artiste et titre {state} pour {count(len(changed_list), 'banque', 'banques')}."

	return run


BANKS: tuple[Action, ...] = (
	Action(
		"audit",
		"Demander l'audit complet de leurs sonores",
		lambda quantity, _names: f"Demander l'audit complet des sonores de {_banks(quantity)} ? {RECHECK}",
		_ask_bank_audit,
	),
	Action(
		"masquer",
		"Masquer l'artiste et le titre",
		lambda quantity, _names: f"Masquer l'artiste et le titre des sonores de {_banks(quantity)} ?",
		_hide(True, "masqués"),
	),
	Action(
		"afficher",
		"Afficher l'artiste et le titre",
		lambda quantity, _names: f"Afficher l'artiste et le titre des sonores de {_banks(quantity)} ?",
		_hide(False, "affichés"),
	),
	Action(
		"heriter",
		"Artiste et titre hérités du sonore",
		lambda quantity, _names: f"Laisser au sonore le masquage de l'artiste et du titre de {_banks(quantity)} ?",
		_hide(None, "hérités du sonore"),
	),
)

ACTIONS: dict[str, tuple[Action, ...]] = {"sonore": SOUNDS, "banque": BANKS}
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
