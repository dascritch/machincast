"""Les noms des rythmes et des rangs de la rotation des émissions en alternance
(https://github.com/dascritch/machincast/issues/609) : « 1er mercredi du mois », « 2e semaine de la quinzaine »,
« 3e semaine sur 4 », et la règle qui fait jouer une émission, « 1er et 3e mercredis du mois ».
"""

from datetime import date

from machincast.i18n import short_date
from machincast.shared import grid
from machincast_alternation import rotation
from machincast_alternation.texts import t

RANKS = ("1st", "2nd", "3rd", "4th", "5th")
MODE_LABELS = {
	rotation.MONTHLY: "Monthly, by the week of the month",
	rotation.FORTNIGHTLY: "Fortnightly, every other week",
	rotation.THREE_WEEKLY: "Every third week",
	rotation.FOUR_WEEKLY: "Every fourth week",
}


def ordinal(rank: int, *, feminine: bool = False) -> str:
	"""1er, 2e… ; 1re pour « semaine »."""
	if (rank == 1) and (feminine):
		return t("1st (feminine)")
	return t(RANKS[rank - 1])


def listed(parts: list[str]) -> str:
	"""« A », « A et B », « A, B et C »."""
	if len(parts) <= 1:
		return "".join(parts)
	return t("{first} and {last}").format(first=", ".join(parts[:-1]), last=parts[-1])


def _ordinals(ranks: list[int], *, feminine: bool) -> str:
	found = []
	for rank in ranks:
		found.append(ordinal(rank, feminine=feminine))
	return listed(found)


def rank_label(rank: int, day: int | None) -> str:
	"""« 1er mercredi du mois », ou « 1re semaine du mois » pour un événement de plusieurs jours, ou sans jour."""
	return ranks_label([rank], day)


def ranks_label(ranks: list[int], day: int | None) -> str:
	"""« 1er et 3e mercredi du mois », ou « 1re et 3e semaine du mois »."""
	if day is None:
		return t("week {rank} of the month").format(rank=_ordinals(ranks, feminine=True))
	return t("{rank} {day} of the month").format(rank=_ordinals(ranks, feminine=False), day=grid.DAY_NAMES[day].lower())


def cycle_ranks(ranks: list[int], period: int) -> str:
	"""« 1re semaine de la quinzaine », « 1re et 3e semaine sur 4 »."""
	if period == 2:
		return t("{rank} week of the fortnight").format(rank=_ordinals(ranks, feminine=True))
	return t("{rank} week of {count}").format(rank=_ordinals(ranks, feminine=True), count=period)


def cycle_label(rank: int, period: int, following: date | None) -> str:
	"""« 1re semaine de la quinzaine, dont le 16/12/2026 » : son prochain passage, s'il est connu."""
	text = cycle_ranks([rank], period)
	if following is None:
		return text
	return t("{week}, including {day}").format(week=text, day=short_date(following))


def rule(alternation: rotation.Alternation, show: int, day: int | None) -> str:
	"""Ce qui fait jouer cette émission : les rangs de la rotation où elle est, sinon un choix à la main, sinon
	rien."""
	ranks = []
	for rank in rotation.RANKS[alternation.mode]:
		if alternation.rotation.get(rank) == show:
			ranks.append(rank)
	if ranks:
		period = rotation.PERIODS.get(alternation.mode)
		if period is None:
			return ranks_label(ranks, day)
		return cycle_ranks(ranks, period)
	if show in alternation.choices.values():
		return t("Chosen by hand")
	return t("Outside the rotation")
