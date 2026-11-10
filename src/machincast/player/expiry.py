"""Expiration automatique des sonores (https://github.com/dascritch/machincast/issues/18, spec § 4.5).

Le binaire lecture passe un sonore de l'état actif à l'état expire :

- quand il atteint son maximum de lectures, compté sur tout l'airplay (lignes de début), quels que soient
  l'événement et la banque ;
- quand sa période de diffusion est terminée : broadcast_end atteinte, fin comprise (la période s'entend fin exclue).

Seule la colonne etat change, et seulement d'actif à expire : les droits PostgreSQL du binaire lecture ne lui
permettent pas d'en modifier d'autres. Chaque expiration est consignée dans le log (info, « sonore expiré »), avec
sa cause. Le sonore ne revient à l'état actif que par l'interface.
"""

from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import integer_or_none
from machincast.i18n import N_, N_counted
from machincast.player.saving import record

KIND = N_("expired sound")


@dataclass(frozen=True)
class Expiry:
	sound: int
	cause: str


def _cause(maximum: int | None, plays: int, end: datetime | None, instant: datetime) -> str:
	causes = []
	if (maximum is not None) and (plays >= maximum):
		causes.append(N_counted("maximum of {count} play reached", "maximum of {count} plays reached", maximum))
	if (end is not None) and (end <= instant):
		causes.append(N_("broadcast period ended on {end:%Y-%m-%d %H:%M:%S}").format(end=end.astimezone()))
	return "; ".join(causes)


def expire(connection: psycopg.Connection[TupleRow], instant: datetime, sound: int | None = None) -> list[Expiry]:
	"""Passe à l'état expire les sonores actifs arrivés au bout, et le consigne ; sonore limite la vérification à un
	seul sonore, par exemple celui dont un passage vient de commencer.

	La connexion a endossé le rôle de la lecture (machincast.database.open_connection).
	"""
	with connection.transaction():
		lines = connection.execute(
			"WITH candidats AS ("
			" SELECT s.id, s.max_plays, s.broadcast_end,"
			" (SELECT count(*) FROM airplay a WHERE a.sound_id = s.id AND a.line_type = 'start') AS lectures"
			" FROM sounds s WHERE s.state = 'active' AND s.deleted_at IS NULL"
			" AND (%s::bigint IS NULL OR s.id = %s::bigint)"
			" AND (s.broadcast_end <= %s OR s.max_plays IS NOT NULL))"
			" UPDATE sounds s SET state = 'expired' FROM candidats c"
			" WHERE s.id = c.id AND (c.broadcast_end <= %s OR c.lectures >= c.max_plays)"
			" RETURNING s.id, COALESCE(s.title, s.location, s.stream_url), c.max_plays, c.lectures,"
			" c.broadcast_end",
			(sound, sound, instant, instant),
		).fetchall()
		expiries = []
		for identifier, name, maximum, plays, end in lines:
			if isinstance(end, datetime):
				known_end = end
			else:
				known_end = None
			expiry = Expiry(
				int(str(identifier)),
				_cause(
					integer_or_none(maximum),
					int(str(plays)),
					known_end,
					instant,
				),
			)
			record(
				connection,
				"info",
				KIND,
				N_("{name}: {cause}").format(
					name=(name) or (N_("sound {sound}").format(sound=expiry.sound)), cause=expiry.cause
				),
				instant,
				sound=expiry.sound,
			)
			expiries.append(expiry)
	return expiries
