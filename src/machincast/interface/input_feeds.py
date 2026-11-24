"""Les feeds des entrées audio (https://github.com/dascritch/machincast/issues/623, ticket enfant de
https://github.com/dascritch/machincast/issues/513).

Enregistrer les Paramètres du service donne à chaque entrée audio nouvelle (audio.inputs) son feed, d'entrée audio, et
un stream qui le suit, du nom de l'entrée ; une entrée renommée renomme son feed. Une entrée retirée garde son feed et
son stream : la fiche du feed la signale (machincast.interface.feed_card). Un feed se reconnaît à son périphérique ; un
nom déjà pris par un autre feed laisse l'entrée sans feed, ou son feed sous son ancien nom, et la barre d'état le dit.
"""

from collections.abc import Sequence

from machincast.configuration import AudioInput
from machincast.i18n import _
from machincast.interface.card import Connection
from machincast.interface.queries import feeds as queries

NAME_TAKEN = _("Audio input “{name}” has no feed: another feed already has this name.")


def synchronise(connection: Connection, inputs: Sequence[AudioInput]) -> list[str]:
	"""Crée ou renomme les feeds des entrées ; ce que la barre d'état en dira, rien quand tout va bien."""
	said: list[str] = []
	with connection.transaction():
		known: dict[str, tuple[int, str]] = {}
		for identifier, name, device in queries.input_feeds(connection):
			known[str(device)] = (int(str(identifier)), str(name))
		for audio_input in inputs:
			problem = _follow(connection, audio_input, known.get(audio_input.device))
			if problem is not None:
				said.append(problem)
	return said


def _follow(connection: Connection, audio_input: AudioInput, feed: tuple[int, str] | None) -> str | None:
	"""Le feed de l'entrée, créé ou renommé ; ce qui l'en empêche, None sinon."""
	identifier = None
	if feed is not None:
		identifier = feed[0]
		if feed[1] == audio_input.name:
			return None
	if queries.name_taken(connection, audio_input.name, identifier):
		return NAME_TAKEN.format(name=audio_input.name)
	if identifier is None:
		queries.insert_input(connection, audio_input.name, audio_input.device)
		return None
	queries.rename(connection, identifier, audio_input.name)
	return None
