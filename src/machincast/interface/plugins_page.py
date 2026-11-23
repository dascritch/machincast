"""Les plugins dans l'interface (https://github.com/dascritch/machincast/issues/587, ticket enfant de
https://github.com/dascritch/machincast/issues/348).

- L'onglet « Plugins » des « Paramètres du service… » (PluginsPage) : un élément dépliable par plugin du répertoire
  des plugins, son nom, sa version et s'il peut être activé ; déplié, sa description et, s'il ne peut pas l'être,
  chacune de ses raisons (machincast.plugins.availability), déplié d'emblée ; une case l'active ou le désactive. La liste s'enregistre dans [plugins] enabled
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
	QTreeWidget,
	QTreeWidgetItem,
	QVBoxLayout,
	QWidget,
)

from machincast import plugins
from machincast.configuration import Configuration
from machincast.i18n import _
from machincast.plugins.manifest import Manifest

WINDOW_POINT = "interface.plugin_window"
COLUMNS = (_("Plugin"), _("Version"), _("State"))
AVAILABLE = _("can be enabled")
UNAVAILABLE = _("cannot be enabled")
NOT_AVAILABLE = _("It cannot be enabled:")
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
	"""L'onglet « Plugins » : un élément dépliable par plugin, sa case cochée s'il est activé ; déplié, sa
	description, puis ce qui l'empêche d'être activé, une raison par ligne. Un plugin qui ne peut pas l'être est
	déplié d'emblée."""

	def __init__(self, offered_list: Sequence[Offered], enabled: Sequence[str], parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.offered_list = list(offered_list)
		self.initial = tuple(enabled)
		layout = QVBoxLayout(self)
		self.tree = QTreeWidget(self)
		self.tree.setObjectName("plugins")
		self.tree.setColumnCount(len(COLUMNS))
		self.tree.setHeaderLabels(list(COLUMNS))
		self.tree.setWordWrap(True)
		self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
		for column in (1, 2):
			self.tree.header().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
		self.tree.header().setStretchLastSection(False)
		self.items: list[QTreeWidgetItem] = []
		for plugin in self.offered_list:
			self.items.append(self._show(plugin))
		layout.addWidget(self.tree)
		self.restart = QLabel(RESTART, self)
		self.restart.setObjectName("restart")
		self.restart.setWordWrap(True)
		layout.addWidget(self.restart)
		self.tree.itemChanged.connect(self._changed)
		self._changed()

	def _show(self, plugin: Offered) -> QTreeWidgetItem:
		item = QTreeWidgetItem(self.tree, [plugin.label, plugin.version, _state(plugin)])
		enabled = plugin.name in self.initial
		# Un plugin activé se décoche toujours ; un autre n'a de case que s'il peut être activé. Il n'est jamais grisé :
		# ses raisons doivent se lire.
		item.setFlags(Qt.ItemFlag.ItemIsEnabled)
		if (enabled) or (plugin.reasons == ()):
			item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
			item.setCheckState(0, Qt.CheckState.Unchecked)
		if enabled:
			item.setCheckState(0, Qt.CheckState.Checked)
		lines = []
		if plugin.description != "":
			lines.append(plugin.description)
		if plugin.reasons != ():
			lines.append(NOT_AVAILABLE)
		for reason in plugin.reasons:
			lines.append(f"• {reason}")
		for line in lines:
			child = QTreeWidgetItem(item, [line])
			child.setFirstColumnSpanned(True)
			child.setToolTip(0, line)
			child.setFlags(Qt.ItemFlag.ItemIsEnabled)
			if line == NOT_AVAILABLE:
				font = child.font(0)
				font.setBold(True)
				child.setFont(0, font)
		item.setExpanded(plugin.reasons != ())
		return item

	def enabled(self) -> tuple[str, ...]:
		"""Les plugins cochés : ceux qui l'étaient, dans leur ordre, puis les nouveaux, dans celui de l'onglet."""
		checked = []
		for plugin, item in zip(self.offered_list, self.items, strict=True):
			if (_checkable(item)) and (item.checkState(0) == Qt.CheckState.Checked):
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


def _checkable(item: QTreeWidgetItem) -> bool:
	return bool(item.flags() & Qt.ItemFlag.ItemIsUserCheckable)


def _state(plugin: Offered) -> str:
	if plugin.reasons == ():
		return AVAILABLE
	return UNAVAILABLE


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
