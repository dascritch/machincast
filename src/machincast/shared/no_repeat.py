"""Les lignes qui rappellent une banque « ne pas répéter », sans base ni diffusion (https://github.com/dascritch/machincast/issues/442).

Partagé par l'avertissement de l'interface à l'édition d'une liste (https://github.com/dascritch/machincast/issues/112) et par
la diffusion."""

from collections.abc import Collection, Sequence


def ignored_calls(banks: Sequence[int | None], no_repeat: Collection[int], *, loop: bool) -> list[int]:
	"""Lignes de la liste d'un événement, numérotées dès 1, qui rappellent la banque « ne pas répéter » de la ligne
	précédente : elles seront toujours sautées à la diffusion. Pour un événement qui boucle, la première ligne suit la
	dernière.

	banques : la banque de chaque ligne, None pour un sonore. Pour l'avertissement de l'interface à l'édition d'une
	séquence (https://github.com/dascritch/machincast/issues/112), qui n'empêche pas d'enregistrer.
	"""
	bank_list = []
	for bank in banks:
		bank_list.append((bank, bank))
	return ignored_calls_to_edges(bank_list, no_repeat, loop=loop)


def ignored_calls_to_edges(
	edges: Sequence[tuple[int | None, int | None]], no_repeat: Collection[int], *, loop: bool
) -> list[int]:
	"""Comme ignored_calls, quand une ligne commence et finit par des banques différentes : une séquence
	(https://github.com/dascritch/machincast/issues/32). Chaque ligne donne sa première banque, celle que la ligne
	précédente peut avoir déjà fait passer, et sa dernière, que la ligne suivante peut rappeler ; None pour un
	sonore.
	"""
	reported_list = []

	def ignored_last(_last: int | None, first: int | None, index: int) -> None:
		if (first not in no_repeat) or ((index == 0) and (not loop)):
			return
		if edges[index - 1][1] == first:
			reported_list.append(index + 1)

	for index, (first, _last) in enumerate(edges):
		ignored_last(_last, first, index)
	return reported_list
