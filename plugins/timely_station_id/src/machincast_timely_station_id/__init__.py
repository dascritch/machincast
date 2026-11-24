"""Le station ID régulier : un station ID environ tous les quarts d'heure, quelle que soit la durée des morceaux, dans
les événements choisis (https://github.com/dascritch/machincast/issues/460).

- Dans Machin player, et dans la simulation de Machin interface, la réponse au point « player.before_choice »
  (machincast_timely_station_id.station, https://github.com/dascritch/machincast/issues/640) : le station ID passe
  avant un sonore choisi, à l'antenne comme dans les sonores à venir.
- Dans Machin interface, la case « Station ID régulier » de la fiche d'un événement
  (machincast_timely_station_id.section), et la fenêtre du plugin, menu « Plugins », qui règle la banque, les banques qui
  annoncent aussi la station, l'écart et le placement (machincast_timely_station_id.settings).

Ses réglages sont dans la section [plugins.timely_station_id] de machincast.toml (machincast_timely_station_id.rule) ;
refusés, ils sont consignés, et aucun station ID n'est inséré.
"""

import logging
from typing import Any

from machincast.plugins import Plugin
from machincast_timely_station_id.rule import Current, read_settings
from machincast_timely_station_id.station import Station
from machincast_timely_station_id.texts import t

log = logging.getLogger(__name__)


def register(plugin: Plugin) -> None:
	"""S'abonne aux points du binaire qui le charge ; seul Machin interface importe Qt."""
	found = read_settings(dict(plugin.context.settings))
	current = Current()
	if isinstance(found, str):
		log.error(t("timely_station_id: settings refused, no station ID inserted: {reason}").format(reason=found))
	else:
		current.settings = found
	if plugin.context.executable == "Machin_player":
		if current.settings is not None:
			plugin.on("player.before_choice", Station(current).answer)
		return
	if plugin.context.executable == "Machin_interface":
		from machincast_timely_station_id import section, settings

		configuration = plugin.context.configuration

		def card_section(data: Any) -> object:
			return section.RegularSection(data["connection"], current, data["parent"], data.get("card"))

		def window(data: Any) -> object:
			return settings.StationSettings(configuration, current, data.get("parent"))

		# Dans la simulation de l'interface, les réglages enregistrés dans la fenêtre valent aussitôt.
		plugin.on("player.before_choice", Station(current).answer)
		plugin.on("interface.event_card", card_section)
		plugin.on("interface.plugin_window", window)
