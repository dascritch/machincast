"""Les plugins de MachinCast (https://github.com/dascritch/machincast/issues/348, socle :
https://github.com/dascritch/machincast/issues/585).

Un plugin est un répertoire de plugins/, à la racine du dépôt (ou de [plugins] directory) :

	plugins/<nom>/
		README.md
		manifest.json      son nom, sa version, ce qu'il demande, ses binaires (machincast.plugins.manifest)
		check.py           facultatif : check(context) rend les raisons qui l'empêchent d'être activé
		install.sh         son installation (https://github.com/dascritch/machincast/issues/586)
		src/machincast_<nom>/__init__.py    register(plugin), appelé à son chargement
		tests/  bin/  doc/

Il est activé dans machincast.toml, section [plugins], enabled = ["nom"] ; ses réglages sont dans [plugins.<nom>].
Au démarrage, chaque binaire (cli.launch) charge les plugins activés qui s'accrochent à lui (load) : il vérifie que
chacun est activable (availability : sa version de MachinCast, ses plugins demandés, ses modules Python, ses
programmes, ses tables, puis son check.py), les ordonne après ceux qu'ils demandent, puis appelle leur register. Un
plugin écarté l'est avec ses raisons, au journal ; le binaire démarre quand même. active() rend ce qui est chargé :
les plugins, et le registre des points d'extension (machincast.plugins.points).
"""

import importlib
import importlib.util
import logging
import shutil
import sys
import threading
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import psycopg

from machincast import __version__, database
from machincast.configuration import PROJECT_DIRECTORY, Configuration
from machincast.i18n import _
from machincast.plugins import queries
from machincast.plugins.manifest import InvalidManifest, Manifest, read
from machincast.plugins.points import Points, Subscriber

log = logging.getLogger(__name__)

DIRECTORY = PROJECT_DIRECTORY / "plugins"
"""Le répertoire des plugins, sans [plugins] directory."""
CHECK = "check.py"
ROLES = {
	"Machin_player": database.Role.PLAYBACK,
	"Machin_indexer": database.Role.INDEXING,
	"Machin_interface": database.Role.INTERFACE,
	"Machin_intranet": database.Role.INTRANET,
}
"""Le rôle sous lequel chaque binaire vérifie les tables d'un plugin."""


class Live:
	"""Ce qui se joue, tel que le binaire le sait : le dernier état publié par Machin player, ou None."""

	def __init__(self) -> None:
		self._lock = threading.Lock()
		self._state: dict[str, Any] | None = None

	def set(self, state: Mapping[str, Any] | None) -> None:
		with self._lock:
			self._state = None
			if state is not None:
				self._state = dict(state)

	def get(self) -> dict[str, Any] | None:
		with self._lock:
			if self._state is None:
				return None
			return dict(self._state)


@dataclass(frozen=True)
class Context:
	"""Ce que les fonctions d'un plugin reçoivent du binaire : de quoi dialoguer avec lui."""

	version: str
	"""La version de MachinCast."""
	executable: str
	"""Le binaire qui l'a chargé."""
	configuration: Configuration
	plugins: Mapping[str, str]
	"""Les plugins chargés dans ce binaire, et leurs versions."""
	settings: Mapping[str, Any]
	"""Ses réglages, la section [plugins.<nom>] de machincast.toml."""
	live: Live

	@property
	def playing(self) -> dict[str, Any] | None:
		"""Le dernier état de l'antenne, s'il est connu du binaire."""
		return self.live.get()


@dataclass
class Plugin:
	"""Un plugin chargé, tel que son register le reçoit."""

	manifest: Manifest
	directory: Path
	context: Context
	points: Points
	module: ModuleType | None = None

	@property
	def name(self) -> str:
		return self.manifest.name

	def on(self, point: str, function: Subscriber) -> None:
		"""S'abonne à un point d'extension, du cœur ou d'un plugin demandé."""
		self.points.subscribe(self.name, point, function)

	def declare(self, point: str, description: str) -> None:
		"""Déclare un point d'extension du plugin, « <nom>.… », pour les plugins qui le demandent."""
		self.points.declare(self.name, point, description)


@dataclass(frozen=True)
class Found:
	"""Un répertoire de plugins/ : son manifest, ou pourquoi il n'est pas lisible."""

	name: str
	directory: Path
	manifest: Manifest | None
	problem: str | None = None


@dataclass
class Loaded:
	"""Les plugins d'un binaire : ceux qui sont chargés, dans l'ordre, et ceux qui sont écartés, avec leurs raisons."""

	points: Points = field(default_factory=Points)
	plugins: list[Plugin] = field(default_factory=list)
	refused: dict[str, list[str]] = field(default_factory=dict)
	live: Live = field(default_factory=Live)

	def names(self) -> list[str]:
		names = []
		for plugin in self.plugins:
			names.append(plugin.name)
		return names


_active = Loaded()


def active() -> Loaded:
	"""Les plugins du binaire, chargés par load ; aucun avant."""
	return _active


def directory(configuration: Configuration) -> Path:
	return (configuration.plugins.directory) or (DIRECTORY)


def discover(root: Path) -> list[Found]:
	"""Chaque répertoire de root, par nom, avec son manifest ou sa raison ; les fichiers et les répertoires cachés
	sont ignorés."""
	found_list: list[Found] = []
	if not root.is_dir():
		return found_list
	for path in sorted(root.iterdir()):
		if (path.is_dir()) and (not path.name.startswith(".")):
			found_list.append(_found(path))
	return found_list


def _found(path: Path) -> Found:
	try:
		return Found(path.name, path, read(path))
	except InvalidManifest as error:
		return Found(path.name, path, None, str(error))


def _requirements(manifest: Manifest, manifests: Mapping[str, Manifest], enabled: frozenset[str]) -> list[str]:
	"""Ce qui manque au plugin, sans base ni check.py."""
	reasons = []
	if __version__ not in manifest.machincast:
		reasons.append(
			_("MachinCast {version} is not one of its versions, {versions}").format(
				version=__version__, versions=manifest.machincast
			)
		)
	for name, versions in manifest.requires.plugins.items():
		other = manifests.get(name)
		if (other is None) or (name not in enabled):
			reasons.append(_("it requires the plugin “{name}”, which is not enabled").format(name=name))
		if (other is not None) and (other.version not in versions):
			reasons.append(
				_("it requires the plugin “{name}” {versions}, {version} found").format(
					name=name, versions=versions, version=other.version
				)
			)
	for module in manifest.requires.python:
		if importlib.util.find_spec(module) is None:
			reasons.append(_("the Python module “{module}” is missing").format(module=module))
	for program in manifest.requires.programs:
		if shutil.which(program) is None:
			reasons.append(_("the program “{program}” is missing").format(program=program))
	return reasons


def _missing_tables(configuration: Configuration, executable: str, found: Found, tables: tuple[str, ...]) -> list[str]:
	"""Les tables du plugin qui manquent à la base de production, et comment les créer : son install.sh
	(https://github.com/dascritch/machincast/issues/586)."""
	if tables == ():
		return []
	role = ROLES.get(executable, database.Role.INTERFACE)
	settings = configuration.database
	try:
		with database.open_connection(settings.socket, settings.production, role) as connection:
			missing = queries.missing_tables(connection, list(tables))
	except psycopg.Error as error:
		return [_("its tables cannot be checked: {error}").format(error=error)]
	reasons = []
	for table in missing:
		reasons.append(
			_("the table “{table}” is missing: install the plugin with {script}").format(
				table=table, script=found.directory / "install.sh"
			)
		)
	return reasons


def _module(path: Path, name: str) -> ModuleType:
	"""Le module d'un fichier, sous ce nom."""
	specification = importlib.util.spec_from_file_location(name, path)
	assert (specification is not None) and (specification.loader is not None)
	module = importlib.util.module_from_spec(specification)
	specification.loader.exec_module(module)
	return module


def module_name(name: str) -> str:
	"""Le paquet Python d'un plugin, dans son src/ : « machincast_<nom> », les « - » en « _ »."""
	return "machincast_" + name.replace("-", "_")


def _checked(found: Found, context: Context) -> list[str]:
	"""Les raisons que donne son check.py, s'il en a un."""
	path = found.directory / CHECK
	if not path.is_file():
		return []
	try:
		module = _module(path, f"{module_name(found.name)}_check")
		reasons = module.check(context)
	except Exception as error:
		return [_("its check.py failed: {error}").format(error=error)]
	if not isinstance(reasons, list):
		return [_("its check.py returns a list of reasons")]
	given = []
	for reason in reasons:
		given.append(str(reason))
	return given


def install_script(found: Found) -> Path:
	return found.directory / "install.sh"


def pending_migrations(configuration: Configuration, found: Found) -> list[str]:
	"""Les migrations du plugin pas encore appliquées à la base de production : ses tables, que MachinCast crée à son
	installation (https://github.com/dascritch/machincast/issues/586). Lève psycopg.Error."""
	from machincast.plugins import schema

	if schema.files(found.directory) == []:
		return []
	settings = configuration.database
	return schema.pending(database.url_yoyo(settings.socket, settings.production), found.directory)


def _uninstalled(configuration: Configuration, found: Found, *, installing: bool) -> list[str]:
	"""Ses tables pas encore créées, sauf pour l'onglet « Plugins », qui l'installe à sa validation (installing)."""
	try:
		pending = pending_migrations(configuration, found)
	except psycopg.Error as error:
		return [_("its tables cannot be checked: {error}").format(error=error)]
	if (pending == []) or (installing):
		return []
	return [
		_(
			"its tables are not created: enable it in the settings of the broadcast service of Machin interface, "
			"which installs it, or run {script}"
		).format(script=install_script(found))
	]


def availability(
	found: Found,
	manifests: Mapping[str, Manifest],
	configuration: Configuration,
	executable: str,
	*,
	installing: bool = False,
) -> list[str]:
	"""Les raisons qui empêchent le plugin d'être activé : aucune s'il est activable. installing : l'onglet « Plugins »
	des paramètres du service, qui crée ses tables à sa validation (https://github.com/dascritch/machincast/issues/587) ;
	ses tables à créer ne l'empêchent pas."""
	if found.manifest is None:
		return [str(found.problem)]
	reasons = _requirements(found.manifest, manifests, frozenset(configuration.plugins.enabled))
	reasons += _uninstalled(configuration, found, installing=installing)
	reasons += _missing_tables(configuration, executable, found, found.manifest.requires.tables)
	if reasons != []:
		return reasons
	return _checked(found, _context(found.manifest, configuration, executable, {}, Live()))


def _context(
	manifest: Manifest, configuration: Configuration, executable: str, loaded: Mapping[str, str], live: Live
) -> Context:
	return Context(
		version=__version__,
		executable=executable,
		configuration=configuration,
		plugins=loaded,
		settings=configuration.plugins.settings.get(manifest.name, {}),
		live=live,
	)


def _ordered(manifests: dict[str, Manifest]) -> tuple[list[str], list[str]]:
	"""Les plugins, chacun après ceux qu'il demande, et ceux qui se demandent en cercle."""
	ordered: list[str] = []
	visiting: set[str] = set()
	circular: list[str] = []

	def visit(name: str) -> bool:
		if name in ordered:
			return True
		if name in visiting:
			return False
		visiting.add(name)
		success = True
		for wanted in sorted(manifests[name].requires.plugins):
			if (wanted in manifests) and (not visit(wanted)):
				success = False
		visiting.discard(name)
		if success:
			ordered.append(name)
		if (not success) and (name not in circular):
			circular.append(name)
		return success

	for name in sorted(manifests):
		visit(name)
	return ordered, circular


def _register(found: Found, manifest: Manifest, context: Context, points: Points) -> Plugin:
	"""Importe le paquet du plugin, depuis son src/, et appelle son register."""
	source = found.directory / "src"
	if str(source) not in sys.path:
		sys.path.insert(0, str(source))
	module = importlib.import_module(module_name(found.name))
	plugin = Plugin(manifest, found.directory, context, points, module)
	register = getattr(module, "register", None)
	if not callable(register):
		raise TypeError(_("{module} has no register(plugin) function").format(module=module.__name__))
	register(plugin)
	return plugin


def _refuse(loaded: Loaded, name: str, reasons: list[str]) -> None:
	loaded.refused[name] = reasons
	log.warning(_("plugin “{name}” not loaded: {reasons}").format(name=name, reasons="; ".join(reasons)))


def _candidates(configuration: Configuration, executable: str, loaded: Loaded) -> dict[str, Found]:
	"""Les plugins activés qui s'accrochent au binaire ; les introuvables sont écartés."""
	found_list = {}
	for found in discover(directory(configuration)):
		found_list[found.name] = found
	candidates = {}
	for name in configuration.plugins.enabled:
		candidate = found_list.get(name)
		if candidate is None:
			_refuse(loaded, name, [_("no such plugin in {directory}").format(directory=directory(configuration))])
		if (candidate is not None) and ((candidate.manifest is None) or (executable in candidate.manifest.binaries)):
			candidates[name] = candidate
	return candidates


def load(configuration: Configuration, executable: str) -> Loaded:
	"""Charge les plugins activés qui s'accrochent au binaire, et les rend actifs (active)."""
	global _active
	loaded = Loaded()
	_active = loaded
	candidates = _candidates(configuration, executable, loaded)
	manifests: dict[str, Manifest] = {}
	for name, found in candidates.items():
		reasons = availability(found, _all_manifests(configuration), configuration, executable)
		if reasons != []:
			_refuse(loaded, name, reasons)
		if (reasons == []) and (found.manifest is not None):
			manifests[name] = found.manifest
	ordered, circular = _ordered(manifests)
	for name in circular:
		_refuse(loaded, name, [_("it requires itself, through the plugins it requires")])
	versions: dict[str, str] = {}
	for name in ordered:
		_load_one(loaded, candidates[name], manifests[name], configuration, executable, versions)
	return loaded


def _all_manifests(configuration: Configuration) -> dict[str, Manifest]:
	manifests = {}
	for found in discover(directory(configuration)):
		if found.manifest is not None:
			manifests[found.name] = found.manifest
	return manifests


def _load_one(
	loaded: Loaded,
	found: Found,
	manifest: Manifest,
	configuration: Configuration,
	executable: str,
	versions: dict[str, str],
) -> None:
	missing = []
	for wanted in manifest.requires.plugins:
		if wanted not in versions:
			missing.append(_("it requires the plugin “{name}”, which is not loaded").format(name=wanted))
	if missing != []:
		_refuse(loaded, found.name, missing)
		return
	context = _context(manifest, configuration, executable, versions, loaded.live)
	try:
		plugin = _register(found, manifest, context, loaded.points)
	except Exception as error:
		log.error(_("plugin “{name}” failed to load: {error}").format(name=found.name, error=error), exc_info=error)
		loaded.refused[found.name] = [str(error)]
		return
	versions[found.name] = str(manifest.version)
	loaded.plugins.append(plugin)
	log.info(_("plugin “{name}” {version} loaded").format(name=found.name, version=manifest.version))
