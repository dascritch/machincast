"""Choix d'un sonore dans une banque (https://github.com/dascritch/machincast/issues/13, spec § 4.4 et § 4.5).

Le choix ne garde aucun état en mémoire : il se déduit de l'airplay, où chaque passage note la banque qui l'a
fourni. Un redémarrage du binaire, ou un sonore ajouté à une banque, ne perturbe donc rien.

- Séquentiel : le premier sonore jouable qui suit, dans l'ordre des positions, le dernier joué via cette banque ;
  après le dernier, la liste reprend au début. Sans passage via la banque, le premier sonore jouable.
- Aléatoire contrôlé : un sonore joué via cette banque n'est plus tiré tant que tous les sonores jouables de la
  banque ne l'ont pas été. Les cycles se lisent dans les passages via la banque, du plus ancien au plus récent :
  un cycle se clôt quand tous les sonores jouables y sont passés. Le dernier sonore joué n'ouvre jamais le cycle
  suivant (sauf s'il est seul) : pas deux fois de suite le même sonore.
- Chaque banque a son propre cycle : seuls comptent les passages fournis par elle, même pour un sonore présent
  dans plusieurs banques.
- Sonore jouable (§ 4.5) : à l'état actif, dans sa période de diffusion quand elle est renseignée (fin exclue),
  sous son maximum de lectures, compté sur tout l'airplay, quelle que soit la banque.
- Aucun sonore jouable : la banque ne fournit rien ; l'élément de l'événement est traité comme une banque vide.
- Ne pas répéter (https://github.com/dascritch/machincast/issues/63) : une banque marquée ne passe jamais deux fois
  de suite ; le déroulé (machincast.player.rundown) saute l'élément qui la rappellerait (has_no_repeat).

Le tirage passe par un Hasard reçu en paramètre (machincast.randomness) : reproductible avec une graine. Les passages et
les états se lisent par un Historique (machincast.player.history) : la base, ou la mémoire en simulation.
"""

from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import integer_or_none
from machincast.player.history import IN_DATABASE, History
from machincast.randomness import Randomness

PLAYABLE_STATE = "active"


@dataclass(frozen=True)
class Candidate:
	"""Un sonore de la banque, dans l'ordre de sa position, avec ce qui décide s'il est jouable."""

	sound: int
	state: str
	broadcast_start: datetime | None
	broadcast_end: datetime | None
	playback_max: int | None
	plays: int
	"""Passages du sonore dans tout l'airplay, quelle que soit la banque."""


def playable(candidate: Candidate, instant: datetime) -> bool:
	if candidate.state != PLAYABLE_STATE:
		return False
	if (candidate.broadcast_start is not None) and (instant < candidate.broadcast_start):
		return False
	if (candidate.broadcast_end is not None) and (instant >= candidate.broadcast_end):
		return False
	return (candidate.playback_max is None) or (candidate.plays < candidate.playback_max)


def following_sequential(order: list[int], playable_list: set[int], last: int | None) -> int | None:
	"""Premier sonore jouable après le dernier joué, en reprenant au début ; None si aucun n'est jouable."""
	if not playable_list:
		return None
	departure = 0
	if last in order:
		departure = order.index(last) + 1
	for offset in range(len(order)):
		sound = order[(departure + offset) % len(order)]
		if sound in playable_list:
			return sound
	return None


def cycle_rest(playable_list: set[int], history: list[int]) -> set[int]:
	"""Sonores jouables pas encore joués dans le cycle en cours.

	historique : sonores joués via la banque, du passage le plus récent au plus ancien. Les cycles se suivent
	depuis le premier passage : un cycle se clôt quand tous les sonores jouables y ont été joués. Au début d'un
	nouveau cycle, le dernier sonore joué est écarté, pour ne pas passer deux fois de suite.
	"""
	seen_list: set[int] = set()
	for sound in reversed(history):
		if sound in playable_list:
			seen_list.add(sound)
			if seen_list == playable_list:
				seen_list = set()
	rest = playable_list - seen_list
	if (rest == playable_list) and (len(rest) > 1) and (history):
		rest.discard(history[0])
	return rest


def _read_candidates(
	connection: psycopg.Connection[TupleRow], query: str, value: int, history: History
) -> list[Candidate]:
	lines = connection.execute(query, (value,)).fetchall()
	line_list = []
	for line in lines:
		line_list.append(int(str(line[0])))
	plays = history.plays(connection, line_list)
	candidates = []
	for sound, state, start, end, maximum in lines:
		if isinstance(start, datetime):
			known_start = start
		else:
			known_start = None
		if isinstance(end, datetime):
			known_end = end
		else:
			known_end = None
		candidates.append(
			Candidate(
				sound=int(str(sound)),
				state=str(state),
				broadcast_start=known_start,
				broadcast_end=known_end,
				playback_max=integer_or_none(maximum),
				plays=plays[int(str(sound))],
			)
		)
	return candidates


def _candidates(connection: psycopg.Connection[TupleRow], bank: int, history: History) -> list[Candidate]:
	return _read_candidates(
		connection,
		"SELECT s.id, s.state::text, s.broadcast_start, s.broadcast_end, s.max_plays"
		" FROM bank_sounds bs JOIN sounds s ON s.id = bs.sound_id"
		" WHERE bs.bank_id = %s ORDER BY bs.position",
		bank,
		history,
	)


def playable_sound(
	connection: psycopg.Connection[TupleRow], sound: int, instant: datetime, history: History = IN_DATABASE
) -> bool:
	"""Le sonore est-il jouable à l'instant (§ 4.5) : pour un sonore placé directement dans un événement."""
	candidates = _read_candidates(
		connection,
		"SELECT s.id, s.state::text, s.broadcast_start, s.broadcast_end, s.max_plays FROM sounds s WHERE s.id = %s",
		sound,
		history,
	)
	return (bool(candidates)) and (playable(candidates[0], instant))


def _playable_list(
	connection: psycopg.Connection[TupleRow], bank: int, instant: datetime, history: History
) -> tuple[list[int], set[int]]:
	candidates = _candidates(connection, bank, history)
	sounds = []
	for c in candidates:
		sounds.append(c.sound)
	playable_sounds = set()
	for c in candidates:
		if playable(c, instant):
			playable_sounds.add(c.sound)
	return sounds, playable_sounds


def remaining_list(
	connection: psycopg.Connection[TupleRow], bank: int, instant: datetime, history: History = IN_DATABASE
) -> set[int]:
	"""Sonores jouables d'une banque aléatoire pas encore joués dans son cycle en cours."""
	_, playable_list = _playable_list(connection, bank, instant, history)
	return cycle_rest(playable_list, history.played_via_bank(connection, bank))


def has_no_repeat(connection: psycopg.Connection[TupleRow], bank: int) -> str | None:
	"""Nom de la banque si elle est marquée « ne pas répéter », sinon None."""
	line = connection.execute("SELECT internal_name FROM banks WHERE id = %s AND no_repeat", (bank,)).fetchone()
	if line is None:
		return None
	return str(line[0])


def choose_sound(
	connection: psycopg.Connection[TupleRow],
	bank: int,
	instant: datetime,
	randomness: Randomness,
	excluded_list: frozenset[int] = frozenset(),
	history: History = IN_DATABASE,
) -> int | None:
	"""Sonore que la banque fournit à l'instant, selon son mode ; None si aucun n'est jouable (banque vide).

	exclus : sonores écartés par le binaire lecture, comme un fichier introuvable, traités comme non jouables.
	La connexion a endossé le rôle de la lecture (machincast.database.open_connection) : tout est lu, rien n'est écrit.
	"""
	line = connection.execute("SELECT mode::text FROM banks WHERE id = %s", (bank,)).fetchone()
	if line is None:
		return None
	order, playable_list = _playable_list(connection, bank, instant, history)
	playable_list -= excluded_list
	played_list = history.played_via_bank(connection, bank)
	if line[0] == "sequential":
		last_played = None
		if played_list:
			last_played = played_list[0]
		return following_sequential(order, playable_list, last_played)
	rest = cycle_rest(playable_list, played_list)
	if not rest:
		return None
	return randomness.choice(sorted(rest))
