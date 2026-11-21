"""Les blocs d'un jour qui se chevauchent, côte à côte (https://github.com/dascritch/machincast/issues/580).

Le calendrier de l'interface et celui de l'intranet placent leurs blocs de la même façon : chacun à la première colonne
libre de son groupe, un groupe réunissant les blocs qui se chevauchent, de proche en proche ; toutes les colonnes d'un
groupe ont la même largeur. Sans Qt : l'intranet ne l'importe pas.
"""

from datetime import datetime
from typing import Protocol


class Timed(Protocol):
	"""Un bloc, de son début à sa fin."""

	@property
	def start(self) -> datetime: ...

	@property
	def end(self) -> datetime: ...


def columns[Block: Timed](blocks: list[Block]) -> dict[Block, tuple[int, int]]:
	"""La colonne de chaque bloc d'un jour, et le nombre de colonnes de son groupe : ceux qui se chevauchent se
	placent côte à côte, à la première colonne libre."""
	places: dict[Block, tuple[int, int]] = {}
	group: list[tuple[Block, int]] = []
	group_end: datetime | None = None
	for block in sorted(blocks, key=lambda b: (b.start, b.end)):
		if (group_end is not None) and (block.start >= group_end):
			_put(group, places)
			group, group_end = [], None
		busy = set()
		for other, taken in group:
			if other.end > block.start:
				busy.add(taken)
		# La première colonne libre.
		column = 0
		while column in busy:
			column += 1
		group.append((block, column))
		group_end = max((group_end) or (block.end), block.end)
	_put(group, places)
	return places


def _put[Block: Timed](group: list[tuple[Block, int]], places: dict[Block, tuple[int, int]]) -> None:
	block_list = []
	for _block, column in group:
		block_list.append(column)
	count = max(block_list, default=-1) + 1
	for block, column in group:
		places[block] = (column, count)
