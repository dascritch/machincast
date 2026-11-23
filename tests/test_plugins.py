"""Étapes du socle des plugins (https://github.com/dascritch/machincast/issues/585)."""

import dataclasses
import json
import logging
import re
import sys
import threading
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import __version__, plugins
from machincast.configuration import Configuration, InvalidConfiguration, Plugins, load
from machincast.plugins.points import Points, UnknownPoint
from tests.database_fixtures import configuration_test, sample_configuration_path

scenarios("plugins.feature")

NAME = r"« ([^»]+) »"


@pytest.fixture
def plugin_directory(tmp_path: Path) -> Path:
	directory = tmp_path / "plugins"
	directory.mkdir()
	return directory


@pytest.fixture(autouse=True)
def forgotten_plugins() -> Iterator[None]:
	"""Les paquets des plugins de ce scénario, et leurs src/, ne restent pas pour le suivant."""
	path = list(sys.path)
	yield
	plugins.active().points.close()
	sys.path[:] = path
	for name in list(sys.modules):
		if name.startswith("machincast_"):
			del sys.modules[name]


@pytest.fixture
def settings() -> dict[str, Any]:
	return {"enabled": (), "settings": {}}


@pytest.fixture
def configuration(plugin_directory: Path, settings: dict[str, Any]) -> Configuration:
	loaded = configuration_test()
	return dataclasses.replace(
		loaded,
		plugins=Plugins(
			enabled=tuple(settings["enabled"]), directory=plugin_directory, settings=dict(settings["settings"])
		),
	)


def _manifest(directory: Path) -> dict[str, Any]:
	content: dict[str, Any] = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
	return content


def _write(directory: Path, manifest: Mapping[str, Any]) -> None:
	(directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _package(directory: Path, body: str = "") -> None:
	package = directory / "src" / plugins.module_name(directory.name)
	package.mkdir(parents=True, exist_ok=True)
	(package / "__init__.py").write_text(f"def register(plugin):\n\tplugin.registered = True\n{body}", encoding="utf-8")


@given(
	parsers.parse(
		"le plugin « {name} » {version}, pour « {binary} », décrit « {description} » et en français « {french} »"
	)
)
def plugin(plugin_directory: Path, name: str, version: str, binary: str, description: str, french: str) -> None:
	directory = plugin_directory / name
	directory.mkdir()
	_write(
		directory,
		{
			"name": name,
			"version": version,
			"description": description,
			"binaries": [binary],
			"l10n": {"fr": {"description": french}},
		},
	)
	_package(directory)


DEFECTS = {
	"un JSON illisible": None,
	"le nom « pendule »": ("name", "pendule"),
	"la version « un »": ("version", "un"),
	"une description de 201 caractères": ("description", "x" * 201),
	"le binaire « Machin_cafetiere »": ("binaries", ["Machin_cafetiere"]),
	"aucun binaire": ("binaries", []),
	"la clé « auteur »": ("auteur", "moi"),
	"les versions de MachinCast « bientôt »": ("machincast", "bientôt"),
	"la langue « tlh »": ("l10n", {"tlh": {"name": "tlhIngan"}}),
}


@given(parsers.parse("le plugin « {name} » dont le manifest a {defect}"))
def faulty_plugin(plugin_directory: Path, name: str, defect: str) -> None:
	directory = plugin_directory / name
	directory.mkdir()
	if defect == "aucun fichier":
		return
	if defect == "un JSON illisible":
		(directory / "manifest.json").write_text("{ pas du JSON", encoding="utf-8")
		return
	manifest: dict[str, Any] = {"name": name, "version": "1.0", "description": "A clock", "binaries": ["Machin_player"]}
	change = DEFECTS[defect]
	assert change is not None
	key, value = change
	manifest[key] = value
	_write(directory, manifest)


@given(parsers.parse("le répertoire de plugin « {name} »"))
def odd_directory(plugin_directory: Path, name: str) -> None:
	(plugin_directory / name).mkdir()


def _require(plugin_directory: Path, name: str, kind: str, value: object) -> None:
	directory = plugin_directory / name
	manifest = _manifest(directory)
	requires = manifest.setdefault("requires", {})
	if kind == "plugins":
		wanted, versions = str(value).split(" ")
		requires.setdefault("plugins", {})[wanted] = versions
	if kind in ("python", "programs"):
		requires.setdefault(kind, []).append(value)
	if kind == "machincast":
		manifest["machincast"] = value
	_write(directory, manifest)


@given(parsers.parse("le plugin « {name} » demande le programme « {program} »"))
def requires_program(plugin_directory: Path, name: str, program: str) -> None:
	_require(plugin_directory, name, "programs", program)


@given(parsers.parse("le plugin « {name} » demande le module Python « {module} »"))
def requires_module(plugin_directory: Path, name: str, module: str) -> None:
	_require(plugin_directory, name, "python", module)


@given(parsers.parse("le plugin « {name} » demande le plugin « {other} » {versions}"))
def requires_plugin(plugin_directory: Path, name: str, other: str, versions: str) -> None:
	_require(plugin_directory, name, "plugins", f"{other} {versions}")


@given(parsers.parse("le plugin « {name} » demande MachinCast {versions}"))
def requires_machincast(plugin_directory: Path, name: str, versions: str) -> None:
	_require(plugin_directory, name, "machincast", versions)


@given(parsers.parse("le plugin « {name} » demande un check.py qui répond « {reason} »"))
def check_refuses(plugin_directory: Path, name: str, reason: str) -> None:
	(plugin_directory / name / "check.py").write_text(f"def check(context):\n\treturn [{reason!r}]\n", encoding="utf-8")


@given(parsers.parse("le plugin « {name} » demande un check.py qui plante"))
def check_fails(plugin_directory: Path, name: str) -> None:
	(plugin_directory / name / "check.py").write_text(
		"def check(context):\n\traise RuntimeError('boum')\n", encoding="utf-8"
	)


@given(parsers.parse("le register du plugin « {name} » plante"))
def register_fails(plugin_directory: Path, name: str) -> None:
	package = plugin_directory / name / "src" / plugins.module_name(name)
	(package / "__init__.py").write_text("def register(plugin):\n\traise RuntimeError('boum')\n", encoding="utf-8")


@given(parsers.re(rf"les plugins activés (?P<names>{NAME}(?:, {NAME})*)$"))
def enabled(settings: dict[str, Any], names: str) -> None:
	settings["enabled"] = _names(names)


@given(parsers.re(rf"les plugins activés {NAME}, réglé par « (?P<line>[^»]+) »$"))
def enabled_with_settings(settings: dict[str, Any], line: str) -> None:
	name = "horloge"
	key, value = line.split(" = ")
	settings["enabled"] = [name]
	settings["settings"] = {name: {key: json.loads(value)}}


def _names(text: str) -> list[str]:
	return re.findall(NAME, text)


@when("MachinCast cherche ses plugins", target_fixture="found")
def search(plugin_directory: Path) -> list[plugins.Found]:
	return plugins.discover(plugin_directory)


@then(parsers.parse("il trouve « {name} » {version}, « {shown} », « {description} »"))
def found_valid(found: list[plugins.Found], name: str, version: str, shown: str, description: str) -> None:
	assert len(found) == 1
	manifest = found[0].manifest
	assert manifest is not None, found[0].problem
	assert (found[0].name, str(manifest.version)) == (name, version)
	assert (manifest.localised("name"), manifest.localised("description")) == (shown, description)


@then(parsers.parse("il trouve « {name} », refusé parce que « {reason} »"))
def found_invalid(found: list[plugins.Found], name: str, reason: str) -> None:
	assert len(found) == 1
	assert (found[0].name, found[0].manifest) == (name, None)
	assert str(found[0].problem).startswith(reason), found[0].problem


@when(parsers.parse("« {binary} » charge ses plugins"), target_fixture="loaded")
def load_plugins(configuration: Configuration, binary: str, caplog: pytest.LogCaptureFixture) -> plugins.Loaded:
	caplog.set_level(logging.INFO, logger="machincast.plugins")
	return plugins.load(configuration, binary)


@then(parsers.re(rf"les plugins chargés sont (?P<names>{NAME}(?:, {NAME})*)$"))
def loaded_names(loaded: plugins.Loaded, names: str) -> None:
	assert loaded.names() == _names(names), loaded.refused
	for each in loaded.plugins:
		assert each.module is not None
		assert getattr(each, "registered", False) is True


@then("aucun plugin n'est chargé")
def none_loaded(loaded: plugins.Loaded) -> None:
	assert loaded.names() == []
	assert plugins.active() is loaded


@then(parsers.parse("« {name} » est écarté parce que « {reason} »"))
def refused(loaded: plugins.Loaded, name: str, reason: str) -> None:
	assert reason.replace("{machincast}", __version__) in loaded.refused[name], loaded.refused


@then(parsers.parse("le journal dit « {message} »"))
def journal_says(caplog: pytest.LogCaptureFixture, message: str) -> None:
	messages = []
	for record in caplog.records:
		messages.append(record.getMessage())
	assert message in messages, messages


def _plugin(loaded: plugins.Loaded, name: str) -> plugins.Plugin:
	for each in loaded.plugins:
		if each.name == name:
			return each
	raise AssertionError(name)


@then(
	parsers.parse(
		"le contexte de « {name} » connaît les plugins « {first} » {first_version}, « {second} » {second_version}, "
		"et la version de MachinCast"
	)
)
def context_knows(
	loaded: plugins.Loaded, name: str, first: str, first_version: str, second: str, second_version: str
) -> None:
	context = _plugin(loaded, name).context
	assert dict(context.plugins) == {first: first_version, second: second_version}
	assert (context.version, context.executable) == (__version__, "Machin_player")


@then(parsers.parse("le contexte de « {name} » a pour réglages « {key} » = « {value} »"))
def context_settings(loaded: plugins.Loaded, name: str, key: str, value: str) -> None:
	assert dict(_plugin(loaded, name).context.settings) == {key: value}


# ─── Configuration ───


@given(parsers.parse("une configuration dont la section [plugins] contient « {content} »"), target_fixture="toml")
def plugins_section(tmp_path: Path, content: str) -> Path:
	path = tmp_path / "machincast.toml"
	path.write_text(
		sample_configuration_path().read_text(encoding="utf-8") + f"\n[plugins]\n{content}\n", encoding="utf-8"
	)
	return path


@when("la configuration est chargée", target_fixture="refusal")
def load_configuration(toml: Path) -> str:
	try:
		load(toml)
	except InvalidConfiguration as error:
		return str(error)
	return ""


@then(parsers.parse("elle est refusée parce que « {reason} »"))
def configuration_refused(refusal: str, reason: str) -> None:
	assert refusal.endswith(reason), refusal


# ─── Points d'extension ───


@pytest.fixture
def received() -> dict[str, Any]:
	return {}


@given(parsers.parse("un registre où « {plugin_name} » déclare le point « {point} »"), target_fixture="points")
def registry(plugin_name: str, point: str) -> Iterator[Points]:
	points = Points()
	points.declare(plugin_name, point, "A tick")
	yield points
	points.close()


def _failing(data: Mapping[str, Any]) -> object:
	raise RuntimeError("boum")


@given(parsers.parse("« {plugin_name} » s'abonne à « {point} » en plantant"))
def subscribe_failing(points: Points, plugin_name: str, point: str) -> None:
	points.subscribe(plugin_name, point, _failing)


@given(parsers.parse("« {plugin_name} » s'abonne à « {point} » en notant ce qu'il reçoit"))
def subscribe_noting(points: Points, plugin_name: str, point: str, received: dict[str, Any]) -> None:
	done = threading.Event()
	returned = threading.Event()
	received["done"] = done
	received["returned"] = returned

	def noting(data: Mapping[str, Any]) -> object:
		# L'abonné attend que la notification soit rendue : elle ne peut pas l'avoir attendu.
		received["after"] = returned.wait(10)
		received["data"] = dict(data)
		done.set()
		return None

	points.subscribe(plugin_name, point, noting)


@given(parsers.parse("« {plugin_name} » s'abonne à « {point} » en répondant « {answer} »"))
def subscribe_answering(points: Points, plugin_name: str, point: str, answer: str) -> None:
	points.subscribe(plugin_name, point, lambda data: answer)


@when(parsers.parse("le point « {point} » est notifié avec « {key} » = « {value} »"))
def notify(
	points: Points, point: str, key: str, value: str, received: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
	caplog.set_level(logging.INFO, logger="machincast.plugins.points")
	points.notify(point, {key: value})
	received["returned"].set()


@then("la notification est rendue avant la fin des abonnés")
def returned_first(received: dict[str, Any]) -> None:
	assert received["done"].wait(10)
	assert received["after"] is True


@then(parsers.parse("« {plugin_name} » reçoit « {key} » = « {value} »"))
def got(received: dict[str, Any], plugin_name: str, key: str, value: str, points: Points) -> None:
	assert received["data"] == {key: value}
	points.close()


@when(parsers.parse("le point « {point} » est demandé"), target_fixture="answers")
def ask(points: Points, point: str) -> list[tuple[str, object]]:
	return points.collect(point)


@then(parsers.re(r"les réponses sont (?P<pairs>.+)$"))
def answers_are(answers: list[tuple[str, object]], pairs: str) -> None:
	expected = re.findall(r"« ([^»]+) » « ([^»]+) »", pairs)
	assert answers == expected


@then(parsers.parse("s'abonner au point « {point} » est refusé parce que « {reason} »"))
def unknown(points: Points, point: str, reason: str) -> None:
	with pytest.raises(UnknownPoint) as caught:
		points.subscribe("horloge", point, lambda data: None)
	assert str(caught.value) == reason


@then(parsers.parse("« {plugin_name} » ne peut pas déclarer le point « {point} »"))
def foreign(points: Points, plugin_name: str, point: str) -> None:
	with pytest.raises(ValueError):
		points.declare(plugin_name, point, "A toc")
