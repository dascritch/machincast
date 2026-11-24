"""La normalisation du niveau : chaque sonore porté à une sonie visée, EBU R128, sans que sa crête dépasse un plafond,
avec un ajustement manuel par sonore (https://github.com/dascritch/machincast/issues/43).

- Dans Machin player, la réponse au point « player.sound_gain » (machincast_loudness_normalization.gain,
  https://github.com/dascritch/machincast/issues/643) ; sans le plugin, Machin player joue les sonores tels quels.
- Dans Machin indexer, au point « indexer.sound_detailed » : un ajustement manuel qui ferait dépasser le plafond, après
  une mise à jour du fichier, est ramené, et le log le dit.
- Dans Machin interface, le niveau d'un sonore dans sa fiche (machincast_loudness_normalization.section), la cible et
  le plafond propres à une banque dans la sienne (machincast_loudness_normalization.bank_section), et la fenêtre du
  plugin, menu « Plugins », qui règle la cible et le plafond (machincast_loudness_normalization.settings).

La mesure, crête et sonie, est celle de l'audit complet du cœur (https://github.com/dascritch/machincast/issues/642).
"""

import logging
from typing import Any

from machincast.database import Role, open_connection
from machincast.plugins import Plugin
from machincast_loudness_normalization import gain, queries
from machincast_loudness_normalization.rule import Current, read_settings
from machincast_loudness_normalization.texts import t

log = logging.getLogger(__name__)


def register(plugin: Plugin) -> None:
	"""S'abonne aux points du binaire qui le charge ; seul Machin interface importe Qt."""
	found = read_settings(dict(plugin.context.settings))
	current = Current()
	if isinstance(found, str):
		log.error(t("loudness_normalization: settings refused, no gain applied: {reason}").format(reason=found))
	else:
		current.settings = found
	configuration = plugin.context.configuration
	executable = plugin.context.executable
	if executable == "Machin_player":
		plugin.on("player.sound_gain", gain.sound_gain(current))
	if executable == "Machin_indexer":

		def connect() -> queries.Connection:
			settings = configuration.database
			return open_connection(settings.socket, settings.production, Role.INDEXING)

		plugin.on("indexer.sound_detailed", gain.detailed(current, connect))
	if executable == "Machin_interface":
		from machincast_loudness_normalization import bank_section, section, settings

		def card_section(data: Any) -> object:
			return section.LevelSection(data["connection"], current, data["parent"], data.get("card"))

		def bank_card_section(data: Any) -> object:
			return bank_section.BankLevelSection(data["connection"], current, data["parent"])

		def window(data: Any) -> object:
			return settings.LevelSettings(configuration, current, data.get("parent"))

		plugin.on("interface.sound_card", card_section)
		plugin.on("interface.bank_card", bank_card_section)
		plugin.on("interface.plugin_window", window)
