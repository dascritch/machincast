"""Le manifest d'un plugin, plugins/<nom>/manifest.json (https://github.com/dascritch/machincast/issues/585).

{
	"name": "cartwall",
	"version": "0.1.0",
	"description": "Touch buttons to drive the antenna from the intranet",
	"machincast": ">=0.9",
	"binaries": ["Machin_intranet", "Machin_interface"],
	"requires": {"plugins": {"autre": ">=1.0"}, "python": ["requests"], "programs": ["ffmpeg"], "tables": ["sounds"]},
	"l10n": {"fr": {"name": "Cartouchier", "description": "Des boutons tactiles pour piloter l'antenne"}}
}

- name : le nom du répertoire, qui valide NAME ; version : une version PEP 440 ; description : 200 caractères au plus.
- machincast : les versions de MachinCast acceptées, un spécificateur PEP 440 (« >=0.9,<2 ») ; sans lui, toutes.
- binaries : les binaires où le plugin s'accroche (BINARIES) ; il n'est chargé que dans ceux-là.
- requires : les plugins demandés et leurs versions acceptées, les modules Python, les programmes, les tables ; tout
  est facultatif.
- l10n : le nom et la description, par langue, comme le reste de MachinCast (machincast.i18n).

Une clé inconnue est refusée, comme dans machincast.toml : une faute de frappe ne passe pas inaperçue.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from machincast import i18n
from machincast.i18n import _

FILE = "manifest.json"
NAME = re.compile(r"^[_\-a-zA-Z0-9]+$")
"""Le nom d'un plugin, celui de son répertoire."""
DESCRIPTION = 200
"""Caractères d'une description courte, au plus."""
BINARIES = frozenset({"Machin_player", "Machin_indexer", "Machin_interface", "Machin_intranet"})
"""Les binaires où un plugin peut s'accrocher."""
KEYS = frozenset({"name", "version", "description", "machincast", "binaries", "requires", "l10n"})
REQUIREMENTS = frozenset({"plugins", "python", "programs", "tables"})
LOCALISED = frozenset({"name", "description"})


class InvalidManifest(Exception):
	"""Un manifest illisible, ou qui ne dit pas ce qu'il faut : sa raison, lisible par un humain."""


@dataclass(frozen=True)
class Requirements:
	plugins: dict[str, SpecifierSet] = field(default_factory=dict)
	"""Les plugins demandés, et les versions acceptées de chacun."""
	python: tuple[str, ...] = ()
	"""Les modules Python, importables."""
	programs: tuple[str, ...] = ()
	"""Les programmes, dans le PATH."""
	tables: tuple[str, ...] = ()
	"""Les tables, en base."""


@dataclass(frozen=True)
class Manifest:
	name: str
	version: Version
	description: str
	machincast: SpecifierSet
	binaries: frozenset[str]
	requires: Requirements
	l10n: dict[str, dict[str, str]]

	def localised(self, key: str) -> str:
		"""Le nom ou la description, dans la langue de MachinCast, sinon en anglais."""
		value = self.l10n.get(i18n.current(), {}).get(key)
		if value is not None:
			return value
		if key == "name":
			return self.name
		return self.description


def _text(document: dict[str, Any], key: str) -> str:
	value = document.get(key)
	if (not isinstance(value, str)) or (value.strip() == ""):
		raise InvalidManifest(_("{key}: a text is expected").format(key=key))
	return value


def _names(value: object, key: str) -> tuple[str, ...]:
	if not isinstance(value, list):
		raise InvalidManifest(_("{key}: a list of texts is expected").format(key=key))
	names = []
	for item in value:
		if not isinstance(item, str):
			raise InvalidManifest(_("{key}: a list of texts is expected").format(key=key))
		names.append(item)
	return tuple(names)


def _specifier(value: object, key: str) -> SpecifierSet:
	if not isinstance(value, str):
		raise InvalidManifest(_("{key}: versions such as “>=1.0,<2” are expected").format(key=key))
	try:
		return SpecifierSet(value)
	except InvalidSpecifier:
		raise InvalidManifest(
			_("{key}: “{value}” is not a version specifier, such as “>=1.0,<2”").format(key=key, value=value)
		) from None


def _requirements(value: object) -> Requirements:
	if value is None:
		return Requirements()
	if not isinstance(value, dict):
		raise InvalidManifest(_("requires: an object is expected"))
	for key in value:
		if key not in REQUIREMENTS:
			raise InvalidManifest(_("unknown key requires.{key}").format(key=key))
	plugins = value.get("plugins", {})
	if not isinstance(plugins, dict):
		raise InvalidManifest(_("requires.plugins: an object of plugin names and versions is expected"))
	wanted = {}
	for name, versions in plugins.items():
		if not NAME.match(name):
			raise InvalidManifest(_("requires.plugins: “{name}” is not a plugin name").format(name=name))
		wanted[name] = _specifier(versions, f"requires.plugins.{name}")
	return Requirements(
		plugins=wanted,
		python=_names(value.get("python", []), "requires.python"),
		programs=_names(value.get("programs", []), "requires.programs"),
		tables=_names(value.get("tables", []), "requires.tables"),
	)


def _l10n(value: object) -> dict[str, dict[str, str]]:
	if value is None:
		return {}
	if not isinstance(value, dict):
		raise InvalidManifest(_("l10n: an object of languages is expected"))
	texts: dict[str, dict[str, str]] = {}
	for language, content in value.items():
		if language not in i18n.LANGUAGES:
			raise InvalidManifest(_("l10n: unknown language “{language}”").format(language=language))
		if (not isinstance(content, dict)) or (not set(content) <= LOCALISED):
			raise InvalidManifest(_("l10n.{language}: a name and a description are expected").format(language=language))
		for key, text in content.items():
			if not isinstance(text, str):
				raise InvalidManifest(_("l10n.{language}.{key}: a text is expected").format(language=language, key=key))
		if len(content.get("description", "")) > DESCRIPTION:
			raise InvalidManifest(
				_("l10n.{language}.description: {maximum} characters at most").format(
					language=language, maximum=DESCRIPTION
				)
			)
		texts[language] = dict(content)
	return texts


def parse(document: object, directory_name: str) -> Manifest:
	"""Le manifest d'un plugin, du répertoire directory_name ; lève InvalidManifest avec sa raison."""
	if not isinstance(document, dict):
		raise InvalidManifest(_("a manifest is a JSON object"))
	for key in document:
		if key not in KEYS:
			raise InvalidManifest(_("unknown key {key}").format(key=key))
	name = _text(document, "name")
	if name != directory_name:
		raise InvalidManifest(
			_("name: “{name}”, but the directory is “{directory}”").format(name=name, directory=directory_name)
		)
	try:
		version = Version(_text(document, "version"))
	except InvalidVersion:
		raise InvalidManifest(
			_("version: “{version}” is not a version, such as 1.0.2").format(version=document["version"])
		) from None
	description = _text(document, "description")
	if len(description) > DESCRIPTION:
		raise InvalidManifest(_("description: {maximum} characters at most").format(maximum=DESCRIPTION))
	binaries = frozenset(_names(document.get("binaries"), "binaries"))
	if binaries == frozenset():
		raise InvalidManifest(_("binaries: at least one binary is expected"))
	unknown = sorted(binaries - BINARIES)
	if unknown:
		raise InvalidManifest(_("binaries: unknown {names}").format(names=", ".join(unknown)))
	return Manifest(
		name=name,
		version=version,
		description=description,
		machincast=_specifier(document.get("machincast", ""), "machincast"),
		binaries=binaries,
		requires=_requirements(document.get("requires")),
		l10n=_l10n(document.get("l10n")),
	)


def read(directory: Path) -> Manifest:
	"""Le manifest du plugin de ce répertoire ; lève InvalidManifest avec sa raison."""
	if not NAME.match(directory.name):
		raise InvalidManifest(
			_("“{name}” is not a plugin name: letters, digits, “_” and “-” only").format(name=directory.name)
		)
	path = directory / FILE
	try:
		document = json.loads(path.read_text(encoding="utf-8"))
	except FileNotFoundError:
		raise InvalidManifest(_("no {file}").format(file=FILE)) from None
	except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
		raise InvalidManifest(_("unreadable {file}: {error}").format(file=FILE, error=error)) from None
	return parse(document, directory.name)
