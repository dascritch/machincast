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

import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import psycopg
from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
	QCheckBox,
	QDialog,
	QDialogButtonBox,
	QFrame,
	QHBoxLayout,
	QLabel,
	QMenu,
	QScrollArea,
	QToolButton,
	QVBoxLayout,
	QWidget,
)

from machincast import plugins
from machincast.configuration import Configuration
from machincast.i18n import _
from machincast.plugins.manifest import Manifest

WINDOW_POINT = "interface.plugin_window"
AVAILABLE = _("can be enabled")
UNAVAILABLE = _("cannot be enabled")
NOT_AVAILABLE = _("It cannot be enabled:")
ABSENT = _("absent from the directory of the plugins")
RESTART = _(
	"The plugins change at the next start of the broadcast, of the indexing and of the interface: restart them."
)
NONE_ENABLED = _("No plugin enabled")
NO_SETTINGS = _("This plugin brings no settings here.")
TO_INSTALL = _("Its tables will be created when the settings are validated, after a backup of the database.")
INSTALLING = _("Installation of the plugins: {names}…")
INSTALLED = _("plugin “{name}” installed")
INSTALL_FAILED = _("installation of the plugin “{name}” failed, code {code}: {output}")


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
	directory: Path | None = None
	to_install: bool = False
	"""Ses tables sont à créer : l'onglet l'installe à sa validation (https://github.com/dascritch/machincast/issues/587)."""


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
	to_install = False
	if configuration is not None:
		reasons = plugins.availability(found, manifests, configuration, _executable(manifest), installing=True)
		to_install = _to_install(configuration, found)
	return Offered(
		found.name,
		manifest.localised("name"),
		str(manifest.version),
		manifest.localised("description"),
		tuple(reasons),
		manifest,
		found.directory,
		to_install,
	)


def _to_install(configuration: Configuration, found: plugins.Found) -> bool:
	"""Ses tables sont-elles à créer ? Une base qui ne répond pas est déjà dans ses raisons."""
	try:
		return plugins.pending_migrations(configuration, found) != []
	except psycopg.Error:
		return False


class Heading(QLabel):
	"""La ligne d'un plugin, qui le déplie ou le replie d'un clic, comme sa flèche."""

	clicked = Signal()

	def mouseReleaseEvent(self, event: QMouseEvent) -> None:
		if event.button() == Qt.MouseButton.LeftButton:
			self.clicked.emit()
		super().mouseReleaseEvent(event)


class PluginEntry(QFrame):
	"""Un plugin, élément dépliable de l'onglet : sa case, s'il en a une, et sa ligne, « nom version · état », qui le
	déplie ou le replie ; déplié, sa description, puis ce qui l'empêche d'être activé, une raison par ligne."""

	changed = Signal()
	"""Sa case, cochée ou décochée."""

	def __init__(self, plugin: Offered, *, enabled: bool, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.plugin = plugin
		self.setObjectName(f"plugin-{plugin.name}")
		self.setFrameShape(QFrame.Shape.StyledPanel)
		layout = QVBoxLayout(self)
		heading = QHBoxLayout()
		self.fold = QToolButton(self)
		self.fold.setObjectName("fold")
		self.fold.setAutoRaise(True)
		self.fold.setAccessibleName(plugin.label)
		self.fold.clicked.connect(lambda: self._fold(unfolded=not self.unfolded()))
		heading.addWidget(self.fold)
		# Un plugin activé se décoche toujours ; un autre n'a de case que s'il peut être activé. Il n'est jamais grisé :
		# ses raisons doivent se lire.
		self.box: QCheckBox | None = None
		if (enabled) or (plugin.reasons == ()):
			self.box = QCheckBox(self)
			self.box.setChecked(enabled)
			self.box.setAccessibleName(plugin.label)
			self.box.toggled.connect(lambda _checked: self.changed.emit())
			heading.addWidget(self.box)
		self.heading = Heading(" · ".join(_heading(plugin)), self)
		self.heading.clicked.connect(lambda: self._fold(unfolded=not self.unfolded()))
		heading.addWidget(self.heading, 1)
		layout.addLayout(heading)
		self.details = QWidget(self)
		details = QVBoxLayout(self.details)
		details.setContentsMargins(24, 0, 0, 0)
		self.lines: list[QLabel] = []
		for line in _lines(plugin):
			label = QLabel(line, self.details)
			label.setWordWrap(True)
			label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
			if line == NOT_AVAILABLE:
				font = label.font()
				font.setBold(True)
				label.setFont(font)
			details.addWidget(label)
			self.lines.append(label)
		layout.addWidget(self.details)
		self._unfolded = False
		self._fold(unfolded=plugin.reasons != ())

	def _fold(self, *, unfolded: bool) -> None:
		"""Déplie ou replie : la flèche, vers le bas ou vers la droite, et les lignes du plugin."""
		self._unfolded = unfolded
		self.fold.setArrowType(Qt.ArrowType.RightArrow)
		if unfolded:
			self.fold.setArrowType(Qt.ArrowType.DownArrow)
		self.details.setVisible(unfolded)

	def unfolded(self) -> bool:
		return self._unfolded

	def checked(self) -> bool:
		return (self.box is not None) and (self.box.isChecked())


class PluginsPage(QWidget):
	"""L'onglet « Plugins » : un élément dépliable par plugin (PluginEntry), les uns sous les autres, sans tableau. Un
	plugin qui ne peut pas être activé est déplié d'emblée."""

	def __init__(self, offered_list: Sequence[Offered], enabled: Sequence[str], parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.offered_list = list(offered_list)
		self.initial = tuple(enabled)
		layout = QVBoxLayout(self)
		scroll = QScrollArea(self)
		scroll.setObjectName("plugins")
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)
		inside = QWidget(scroll)
		entries = QVBoxLayout(inside)
		self.entries: list[PluginEntry] = []
		for plugin in self.offered_list:
			entry = PluginEntry(plugin, enabled=plugin.name in self.initial, parent=inside)
			entry.changed.connect(self._changed)
			entries.addWidget(entry)
			self.entries.append(entry)
		entries.addStretch(1)
		scroll.setWidget(inside)
		layout.addWidget(scroll)
		self.restart = QLabel(RESTART, self)
		self.restart.setObjectName("restart")
		self.restart.setWordWrap(True)
		layout.addWidget(self.restart)
		self._changed()

	def enabled(self) -> tuple[str, ...]:
		"""Les plugins cochés : ceux qui l'étaient, dans leur ordre, puis les nouveaux, dans celui de l'onglet."""
		checked = []
		for entry in self.entries:
			if entry.checked():
				checked.append(entry.plugin.name)
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


def _heading(plugin: Offered) -> list[str]:
	parts = [plugin.label]
	if plugin.version != "":
		parts = [f"{plugin.label} {plugin.version}"]
	parts.append(_state(plugin))
	return parts


def _lines(plugin: Offered) -> list[str]:
	"""Ce que le plugin déplié dit : sa description, ses tables à créer, ou ses raisons."""
	lines = []
	if plugin.description != "":
		lines.append(plugin.description)
	if (plugin.to_install) and (plugin.reasons == ()):
		lines.append(TO_INSTALL)
	if plugin.reasons != ():
		lines.append(NOT_AVAILABLE)
	for reason in plugin.reasons:
		lines.append(f"• {reason}")
	return lines


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


TIMESTAMP = re.compile(r"^\S+[+-]\d\d:\d\d\s+")
"""L'horodatage d'une ligne du journal, retiré de la raison d'un échec."""


def installation_command(plugin: Offered, configuration: Path | None, backups: Path) -> list[str]:
	"""Son install.sh, ou, sans lui, l'installation commune de MachinCast, sur la base de la configuration, avec sa
	sauvegarde dans backups (machincast.plugins.installation, https://github.com/dascritch/machincast/issues/586)."""
	assert plugin.directory is not None
	options = ["--backups", str(backups)]
	if configuration is not None:
		options += ["--config", str(configuration)]
	script = plugin.directory / "install.sh"
	if script.is_file():
		return [str(script), *options]
	return [sys.executable, "-m", "machincast.plugins.installation", str(plugin.directory), *options]


def newly_enabled(offered_list: Sequence[Offered], before: Sequence[str], after: Sequence[str]) -> list[Offered]:
	"""Les plugins que la validation active, dans l'ordre de [plugins] enabled : chacun s'installe, ses tables créées
	s'il en a ; un plugin désactivé ne perd rien."""
	found: dict[str, Offered] = {}
	for plugin in offered_list:
		if plugin.directory is not None:
			found[plugin.name] = plugin
	chosen = []
	for name in after:
		candidate = found.get(name)
		if (candidate is not None) and (name not in before):
			chosen.append(candidate)
	return chosen


class Installer(QObject):
	"""L'installation des plugins activés à la validation des paramètres du service, l'un après l'autre, chacun dans son
	propre processus, sans terminal (https://github.com/dascritch/machincast/issues/587). Sa fin émet finished, avec ce
	qu'en dit la barre d'état."""

	finished = Signal(str)

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.process: QProcess | None = None
		self.queue: list[tuple[str, list[str]]] = []
		self.outcomes: list[str] = []

	def running(self) -> bool:
		return self.process is not None

	def start(self, plugins_: Sequence[Offered], configuration: Path | None, backups: Path) -> str:
		"""Lance l'installation de chaque plugin ; ce qu'en dit la barre d'état."""
		names = []
		for plugin in plugins_:
			self.queue.append((plugin.name, installation_command(plugin, configuration, backups)))
			names.append(plugin.label)
		self.outcomes = []
		self._next()
		return INSTALLING.format(names=", ".join(names))

	def _next(self) -> None:
		if self.queue == []:
			self.finished.emit(" ; ".join(self.outcomes))
			return
		name, command = self.queue.pop(0)
		process = QProcess(self)
		environment = QProcessEnvironment.systemEnvironment()
		# Le Python de l'interface, celui du venv de MachinCast, pour l'install.sh du plugin.
		environment.insert("MACHINCAST_PYTHON", sys.executable)
		process.setProcessEnvironment(environment)
		process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
		process.finished.connect(lambda code, status: self._finished(name, code, status))
		self.process = process
		process.start(command[0], command[1:])

	def _finished(self, name: str, code: int, status: QProcess.ExitStatus) -> None:
		process = self.process
		assert process is not None
		self.process = None
		output = bytes(process.readAll().data()).decode(errors="replace")
		process.deleteLater()
		if (code == 0) and (status == QProcess.ExitStatus.NormalExit):
			self.outcomes.append(INSTALLED.format(name=name))
		else:
			last = ""
			for line in output.splitlines():
				if line.strip():
					last = TIMESTAMP.sub("", line.strip())
			self.outcomes.append(INSTALL_FAILED.format(name=name, code=code, output=last))
		# Le suivant, ou la fin, après le retour de ce signal : le processus fini n'est plus sur la pile.
		QTimer.singleShot(0, self._next)
