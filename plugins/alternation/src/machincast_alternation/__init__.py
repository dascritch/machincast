"""Les émissions en alternance : un événement « méta » qui fait jouer, selon la semaine du mois, l'une des émissions
qui se partagent son créneau (https://github.com/dascritch/machincast/issues/609, ticket enfant de
https://github.com/dascritch/machincast/issues/606).

- Dans chaque binaire qui lit la grille, Machin player, Machin interface et Machin webserver, l'émission qui joue
  chaque occurrence (machincast_alternation.rotation) : l'antenne, le calendrier, l'intranet et l'affichage public la
  jouent et la montrent.
- Dans Machin interface, la fiche de l'événement méta choisit ses émissions, leur rotation, et les passages des
  semaines à venir (machincast_alternation.section).
"""

from typing import Any

from machincast.plugins import Plugin
from machincast_alternation import rotation


def register(plugin: Plugin) -> None:
	"""S'abonne aux points du binaire qui le charge ; seul Machin interface importe Qt."""
	plugin.on("grid.substitutions", lambda data: rotation.substitution())
	if plugin.context.executable == "Machin_interface":
		from machincast_alternation import section

		def card_section(data: Any) -> object:
			return section.AlternationSection(data["connection"], data["card"].clock, data["parent"])

		plugin.on("interface.event_card", card_section)
