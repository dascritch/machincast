"""Airplay récent, pour l'écran par défaut (https://github.com/dascritch/machincast/issues/23, spec § 8.1) et l'onglet
Airplay (https://github.com/dascritch/machincast/issues/244).

Lu avec le rôle de l'interface, qui lit l'airplay sans pouvoir l'écrire. L'écran ne le relit qu'à chaque changement de
sonore annoncé par la socket d'état, jamais en boucle (doc/fr/regles/interface.md). L'interface est privée : l'artiste
et le titre sont toujours affichés, même masqués.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import boolean_or_none, integer_or_none, text_or_none

HOURS = 12
"""Heures de l'airplay que montre l'onglet Airplay, sans réglage du compte."""
LAST_LIST = 10
"""Passages de l'airplay que montre l'onglet Antenne."""


@dataclass(frozen=True)
class DisplayedPlay:
	start: datetime
	end: datetime | None
	"""None pour le passage en cours."""
	duration: timedelta | None
	artist: str | None
	title: str | None
	event: str | None
	sequence: str | None
	bank: str | None
	without_incident: bool | None
	id_sound: int | None = None
	id_event: int | None = None
	sequence_id: int | None = None
	id_bank: int | None = None
	"""Les éléments du passage, pour ouvrir leur fiche (https://github.com/dascritch/machincast/issues/144) ; None
	pour un élément supprimé depuis."""


def read_airplay(
	connection: psycopg.Connection[TupleRow], since: datetime | None = None, count: int | None = None
) -> list[DisplayedPlay]:
	"""Passages commencés depuis cet instant, ou les derniers, du plus récent au plus ancien ; nombre au plus."""
	with connection.transaction():
		lines = connection.execute(
			"SELECT d.logged_at, f.logged_at, f.played_duration, f.without_incident, d.artist, d.title,"
			" e.internal_name, q.internal_name, b.internal_name, d.sound_id, e.id, q.id, b.id"
			" FROM airplay d"
			" LEFT JOIN airplay f ON f.play_id = d.play_id AND f.line_type = 'end'"
			" LEFT JOIN events e ON e.id = d.event_id"
			" LEFT JOIN sequences q ON q.id = d.sequence_id"
			" LEFT JOIN banks b ON b.id = d.bank_id"
			" WHERE d.line_type = 'start' AND (%s::timestamptz IS NULL OR d.logged_at >= %s::timestamptz)"
			" ORDER BY d.logged_at DESC, d.id DESC LIMIT %s",
			(since, since, count),
		).fetchall()
	plays = []
	for line in lines:
		start, end, duration, without_incident, artist, title, event, sequence, bank, *identifiers = line
		if not isinstance(start, datetime):
			continue
		plays.append(
			DisplayedPlay(
				start=start,
				end=end if isinstance(end, datetime) else None,
				duration=duration if isinstance(duration, timedelta) else None,
				artist=text_or_none(artist),
				title=text_or_none(title),
				event=text_or_none(event),
				sequence=text_or_none(sequence),
				bank=text_or_none(bank),
				without_incident=boolean_or_none(without_incident),
				id_sound=integer_or_none(identifiers[0]),
				id_event=integer_or_none(identifiers[1]),
				sequence_id=integer_or_none(identifiers[2]),
				id_bank=integer_or_none(identifiers[3]),
			)
		)
	return plays
