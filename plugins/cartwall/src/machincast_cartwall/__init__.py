"""Le cartouchier : des boutons tactiles dans Machin webserver, qui agissent sur l'antenne, réglés par compte de l'API
dans Machin interface (https://github.com/dascritch/machincast/issues/512, plugin de
https://github.com/dascritch/machincast/issues/348).

- Dans Machin webserver, la page du cartouchier et ses routes d'API (machincast_cartwall.intranet).
- Dans Machin interface, les boutons de chaque compte, dans la fenêtre du plugin, menu « Plugins »
  (machincast_cartwall.settings).
"""

from typing import Any

from machincast.plugins import Plugin


def register(plugin: Plugin) -> None:
	"""S'abonne aux points du binaire qui le charge ; chacun n'importe que ce qui lui sert : l'intranet n'a pas Qt."""
	if plugin.context.executable == "Machin_webserver":
		from machincast_cartwall import intranet

		plugin.on("intranet.extensions", lambda data: intranet.extension())
	if plugin.context.executable == "Machin_interface":
		from machincast_cartwall import settings

		def window(data: Any) -> object:
			return settings.ButtonsSettings(plugin.context.configuration, data.get("parent"))

		plugin.on("interface.plugin_window", window)
