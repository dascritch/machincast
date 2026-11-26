"""Les couleurs des émissions : chaque événement prend la couleur de son genre, talk, jazz, metal, reggae…, ou celle de
sa priorité, dans le calendrier de Machin interface, celui de Machin webserver et les tableaux d'airplay
(https://github.com/dascritch/machincast/issues/628).

- Dans Machin interface et Machin webserver, la réponse au point « grid.event_colour »
  (machincast_color_the_shows.palette, https://github.com/dascritch/machincast/issues/635).
- Dans Machin interface, la section « Genre » de la fiche d'un événement (machincast_color_the_shows.section), et la
  fenêtre du plugin, menu « Plugins », qui règle les genres et les couleurs (machincast_color_the_shows.settings).
"""

from typing import Any

from machincast.database import Role, open_connection
from machincast.plugins import Plugin
from machincast_color_the_shows import queries
from machincast_color_the_shows.palette import Palette

ROLES = {"Machin_interface": Role.INTERFACE, "Machin_webserver": Role.INTRANET}


def register(plugin: Plugin) -> None:
	"""S'abonne aux points du binaire qui le charge ; seul Machin interface importe Qt."""
	role = ROLES.get(plugin.context.executable)
	if role is None:
		return
	configuration = plugin.context.configuration

	def connect() -> queries.Connection:
		settings = configuration.database
		return open_connection(settings.socket, settings.production, role)

	palette = Palette(connect)
	plugin.on("grid.event_colour", palette.answer)
	if plugin.context.executable == "Machin_interface":
		from machincast_color_the_shows import section, settings

		def card_section(data: Any) -> object:
			return section.GenreSection(data["connection"], data["parent"], palette.forget, data.get("card"))

		def window(data: Any) -> object:
			return settings.ColoursSettings(configuration, data.get("parent"), saved=palette.forget)

		plugin.on("interface.event_card", card_section)
		plugin.on("interface.plugin_window", window)
