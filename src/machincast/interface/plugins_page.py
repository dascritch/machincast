"""Les plugins dans l'interface (https://github.com/dascritch/machincast/issues/587, ticket enfant de
https://github.com/dascritch/machincast/issues/348).

- L'onglet « Plugins » des « Paramètres du service de diffusion… » (PluginsPage) : chaque plugin du répertoire des
  plugins, avec son nom, sa version, sa description et, s'il n'est pas activable, pourquoi
  (machincast.plugins.availability) ; une case l'active ou le désactive. La liste s'enregistre dans [plugins] enabled
  du fichier de configuration (machincast.interface.preferences.write), et l'onglet dit qu'il faut relancer la
  diffusion, l'indexation et l'interface : chaque binaire ne charge ses plugins qu'à son démarrage.
- Le menu « Plugins » de la fenêtre principale (fill_menu) : une entrée par plugin activé, qui ouvre sa fenêtre
  (PluginWindow), son nom, sa version, sa description et les réglages qu'il apporte, au point d'extension
  « interface.plugin_window ».
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QDialog,
	QDialogButtonBox,
	QHeaderView,
	QLabel,
	QMenu,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from machincast import plugins
from machincast.configuration import Configuration
from machincast.i18n import _
from machincast.plugins.manifest import Manifest

WINDOW_POINT = "interface.plugin_window"
COLUMNS = (_("Active"), _("Plugin"), _("Version"), _("Description"), _("State"))
AVAILABLE = _("can be enabled")
ABSENT = _("absent from the directory of the plugins")
RESTART = _(
	"The plugins change at the next start of the broadcast, of the indexing and of the interface: restart them."
)
NONE_ENABLED = _("No plugin enabled")
NO_SETTINGS = _("This plugin brings no settings here.")


@dataclass(frozen=True)
class Offered:
	"""Un plugin, tel que l'onglet le propose."""

	name: str
	label: str
	version: str
	description: str
	reasons: tuple[str, ...]
	"""Pourquoi il ne peut pas être activé ; vide s'il le peut."""
	manifest: Manifest | None = None


def _executable(manifest: Manifest) -> str:
	"""Le binaire au rôle duquel vérifier ses tables : le premier où il s'accroche."""
	return sorted(manifest.binaries)[0]


def offered(configuration: Configuration) -> list[Offered]:
	"""Les plugins du répertoire, puis ceux de [plugins] enabled qui n'y sont pas, pour qu'ils se désactivent."""
	found_list = plugins.discover(plugins.directory(configuration))
	manifests: dict[str, Manifest] = {}
	for found in found_list:
		if found.manifest is not None:
			manifests[found.name] = found.manifest
	offered_list = []
	names = []
	for found in found_list:
		names.append(found.name)
		offered_list.append(_offered(found, manifests, configuration))
	for name in configuration.plugins.enabled:
		if name not in names:
			offered_list.append(Offered(name, name, "", "", (ABSENT,)))
	return offered_list


def _offered(found: plugins.Found, manifests: dict[str, Manifest], configuration: Configuration | None) -> Offered:
	"""Le plugin, et ce qui l'empêche d'être activé, sauf sans configuration : pour le menu, qui ne vérifie rien."""
	manifest = found.manifest
	if manifest is None:
		return Offered(found.name, found.name, "", "", (str(found.problem),))
	reasons: list[str] = []
	if configuration is not None:
		reasons = plugins.availability(found, manifests, configuration, _executable(manifest))
	return Offered(
		found.name,
		manifest.localised("name"),
		str(manifest.version),
		manifest.localised("description"),
		tuple(reasons),
		manifest,
	)


class PluginsPage(QWidget):
	"""L'onglet « Plugins » : une ligne par plugin, sa case cochée s'il est activé."""

	def __init__(self, offered_list: Sequence[Offered], enabled: Sequence[str], parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.offered_list = list(offered_list)
		self.initial = tuple(enabled)
		layout = QVBoxLayout(self)
		self.table = QTableWidget(len(self.offered_list), len(COLUMNS), self)
		self.table.setObjectName("plugins")
		self.table.setHorizontalHeaderLabels(list(COLUMNS))
		self.table.verticalHeader().setVisible(False)
		self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
		for row, plugin in enumerate(self.offered_list):
			self._show(row, plugin)
		layout.addWidget(self.table)
		self.restart = QLabel(RESTART, self)
		self.restart.setObjectName("restart")
		self.restart.setWordWrap(True)
		layout.addWidget(self.restart)
		self.table.itemChanged.connect(self._changed)
		self._changed()

	def _show(self, row: int, plugin: Offered) -> None:
		box = QTableWidgetItem()
		flags = Qt.ItemFlag.ItemIsUserCheckable
		enabled = plugin.name in self.initial
		# Un plugin activé se désactive toujours ; un autre ne s'active que s'il le peut.
		if (enabled) or (plugin.reasons == ()):
			flags |= Qt.ItemFlag.ItemIsEnabled
		box.setFlags(flags)
		box.setCheckState(Qt.CheckState.Unchecked)
		if enabled:
			box.setCheckState(Qt.CheckState.Checked)
		self.table.setItem(row, 0, box)
		state = AVAILABLE
		if plugin.reasons != ():
			state = "; ".join(plugin.reasons)
		for column, text in enumerate((plugin.label, plugin.version, plugin.description, state), start=1):
			item = QTableWidgetItem(text)
			item.setToolTip(text)
			self.table.setItem(row, column, item)

	def enabled(self) -> tuple[str, ...]:
		"""Les plugins cochés : ceux qui l'étaient, dans leur ordre, puis les nouveaux, dans celui de l'onglet."""
		checked = []
		for row, plugin in enumerate(self.offered_list):
			item = self.table.item(row, 0)
			if (item is not None) and (item.checkState() == Qt.CheckState.Checked):
				checked.append(plugin.name)
		kept = []
		for name in self.initial:
			if name in checked:
				kept.append(name)
		for name in checked:
			if name not in kept:
				kept.append(name)
		return tuple(kept)

	def _changed(self) -> None:
		"""L'avertissement de la relance, dès que la liste diffère de celle du fichier."""
		self.restart.setVisible(self.enabled() != self.initial)


class PluginWindow(QDialog):
	"""La fenêtre d'un plugin activé : son nom, sa version, sa description, et les réglages qu'il apporte."""

	def __init__(self, plugin: Offered, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setWindowTitle(plugin.label)
		layout = QVBoxLayout(self)
		for name, text in (("name", plugin.label), ("version", plugin.version), ("description", plugin.description)):
			label = QLabel(text, self)
			label.setObjectName(name)
			label.setWordWrap(True)
			layout.addWidget(label)
		self.settings: list[QWidget] = []
		for answer in plugins.active().points.collect_from(plugin.name, WINDOW_POINT, {"parent": self}):
			if isinstance(answer, QWidget):
				self.settings.append(answer)
				layout.addWidget(answer)
		if self.settings == []:
			none = QLabel(NO_SETTINGS, self)
			none.setObjectName("no_settings")
			layout.addWidget(none)
		buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)


def fill_menu(menu: QMenu, configuration: Configuration, open_window: Callable[[Offered], None]) -> None:
	"""Le menu « Plugins » : une entrée par plugin activé, dans l'ordre de [plugins] enabled ; sans plugin activé, une
	entrée grisée le dit."""
	menu.clear()
	found: dict[str, Offered] = {}
	for each in plugins.discover(plugins.directory(configuration)):
		found[each.name] = _offered(each, {}, None)
	entries = 0
	for name in configuration.plugins.enabled:
		plugin = found.get(name)
		if (plugin is None) or (plugin.manifest is None):
			plugin = Offered(name, name, "", "", (ABSENT,))
		action = menu.addAction(plugin.label + "…")
		action.triggered.connect(lambda _ticked=False, chosen=plugin: open_window(chosen))
		entries += 1
	if entries == 0:
		menu.addAction(NONE_ENABLED).setEnabled(False)
