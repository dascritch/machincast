"""Le station ID régulier : un station ID environ tous les quarts d'heure, quelle que soit la durée des morceaux, dans
les événements choisis (https://github.com/dascritch/machincast/issues/460).

- Dans Machin player, et dans la simulation de Machin interface, la réponse au point « player.before_choice »
  (machincast_timely_station_id.station, https://github.com/dascritch/machincast/issues/640) : le station ID passe
  avant un sonore choisi, à l'antenne comme dans les sonores à venir.
- Dans Machin interface, la case « Station ID régulier » de la fiche d'un événement
  (machincast_timely_station_id.section).

Ses réglages sont dans la section [plugins.timely_station_id] de machincast.toml (machincast_timely_station_id.rule) ;
refusés, ils sont consignés, et aucun station ID n'est inséré.
"""

import logging
from typing import Any

from machincast.plugins import Plugin
from machincast_timely_station_id.rule import Settings, read_settings
from machincast_timely_station_id.station import Station
from machincast_timely_station_id.texts import t

log = logging.getLogger(__name__)


def register(plugin: Plugin) -> None:
	"""S'abonne aux points du binaire qui le charge ; seul Machin interface importe Qt."""
	found = read_settings(dict(plugin.context.settings))
	settings: Settings | None = None
	if isinstance(found, str):
		log.error(t("timely_station_id: settings refused, no station ID inserted: {reason}").format(reason=found))
	else:
		settings = found
		plugin.on("player.before_choice", Station(settings).answer)
	if plugin.context.executable == "Machin_interface":
		from machincast_timely_station_id import section

		def card_section(data: Any) -> object:
			return section.RegularSection(data["connection"], settings, data["parent"], data.get("card"))

		plugin.on("interface.event_card", card_section)
