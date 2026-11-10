"""Scénarios de la présentation des sorties au serveur audio (https://github.com/dascritch/machincast/issues/296,
https://github.com/dascritch/machincast/issues/343).

Les sorties sont de vrais éléments GStreamer, créés sans être lancés : aucun serveur audio n'est joint.
"""

import ast
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import parsers, scenarios, then, when

from machincast import audio
from machincast.configuration import PROJECT_DIRECTORY, Audio, AudioOutput
from machincast.interface import monitor

scenarios("presentation_audio.feature")

PROGRAMS = {
	"Machin player": audio.ON_AIR,
	"la pré-écoute": audio.PREVIEW,
	"l'essai de la sortie": audio.TRIAL,
}
ICON_KEYS = {
	"pipewiresink": "application.icon-name",
	"pulsesink": "application.icon_name",
	"pipewiresrc": "application.icon-name",
	"pulsesrc": "application.icon_name",
}
SOURCES = frozenset({"pipewiresrc", "pulsesrc"})
BINARIES = {"Machin_player": "ON_AIR", "Machin_interface": "PREVIEW"}
MAINS = {
	"Machin_player": "src/machincast/player/__main__.py",
	"Machin_interface": "src/machincast/interface/__main__.py",
}


@pytest.fixture
def context() -> SimpleNamespace:
	return SimpleNamespace(output=None, source=None)


@when(parsers.parse("je crée la sortie « {output} » de {program}"))
def create(context: SimpleNamespace, output: AudioOutput, program: str) -> None:
	context.output = audio.create_output(output, None, presentation=PROGRAMS[program])


def _factory(item: audio.Gst.Element) -> str:
	factory = item.get_factory()
	assert factory is not None
	return str(factory.get_name())


@when(parsers.parse("je crée l'écoute de l'antenne « {output} »"))
def create_monitoring(context: SimpleNamespace, output: AudioOutput) -> None:
	block = monitor.monitor_source(Audio(output=output, device="casque", preview="casque"))
	elements = block.iterate_elements()
	result, item = elements.next()
	while result == audio.Gst.IteratorResult.OK:
		if _factory(item) in SOURCES:
			context.source = item
		result, item = elements.next()
	assert context.source is not None


@then(parsers.parse("la sortie se présente comme « {name} », pour le flux « {stream} », avec l'icône « {icon} »"))
def presented(context: SimpleNamespace, name: str, stream: str, icon: str) -> None:
	_presented(context.output, name, stream, icon)


@then(parsers.parse("la source se présente comme « {name} », pour le flux « {stream} », avec l'icône « {icon} »"))
def source_presented(context: SimpleNamespace, name: str, stream: str, icon: str) -> None:
	_presented(context.source, name, stream, icon)


@then("la source écoute la sortie de son périphérique (stream.capture.sink)")
def capture_kept(context: SimpleNamespace) -> None:
	properties = context.source.get_property("stream-properties")
	assert properties.get_value("stream.capture.sink") is True


@when(parsers.parse("{binary} se nomme"), target_fixture="names")
def named(binary: str) -> list[str]:
	"""Dans un processus à part : GLib ne retient que le premier nom d'application d'un processus."""
	code = (
		"from machincast import audio\n"
		f"audio.identify(audio.{BINARIES[binary]}, {binary!r})\n"
		"print(audio.GLib.get_application_name())\n"
		"print(audio.GLib.get_prgname())\n"
	)
	completed = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
	return completed.stdout.splitlines()


@then(parsers.parse("GLib le nomme « {name} », du programme « {binary} »"))
def named_by_glib(names: list[str], name: str, binary: str) -> None:
	assert names == [name, binary]


@then("la fonction run de Machin_player et de Machin_interface commence par se nommer")
def named_at_launch() -> None:
	for binary, file in MAINS.items():
		module = ast.parse((PROJECT_DIRECTORY / file).read_text(encoding="utf-8"))
		run = None
		for node in module.body:
			if (isinstance(node, ast.FunctionDef)) and (node.name == "run"):
				run = node
		assert run is not None, file
		first = ast.unparse(run.body[0])
		assert first.startswith("audio.identify("), (binary, first)


def _presented(output: audio.Gst.Element, name: str, stream: str, icon: str) -> None:
	properties = output.get_property("stream-properties")
	assert properties is not None
	assert output.get_property("client-name") == name
	assert properties.get_string("application.name") == name
	assert properties.get_string("media.name") == stream
	assert properties.get_string(ICON_KEYS[_factory(output)]) == icon


@then("la sortie est créée, sans présentation")
def without_presentation(context: SimpleNamespace) -> None:
	assert context.output is not None
	assert context.output.find_property("client-name") is None


@then(parsers.parse("les propriétés du client PipeWire de la sortie nomment « {name} », avec l'icône « {icon} »"))
def client_pipewire(context: SimpleNamespace, name: str, icon: str) -> None:
	properties = context.output.get_property("client-properties")
	assert properties is not None
	assert (properties.get_string("application.name"), properties.get_string("application.icon-name")) == (name, icon)


@then("chaque appel à create_output, hors des tests, passe une présentation")
def present_calls() -> None:
	without = []
	for file in sorted((PROJECT_DIRECTORY / "src").rglob("*.py")):

		def present_node(node, file) -> None:
			if (not isinstance(node, ast.Call)) or (ast.unparse(node.func).split(".")[-1] != "create_output"):
				return
			found = False
			for word in node.keywords:
				if word.arg == "presentation":
					found = True
					break
			if not found:
				without.append(f"{file.relative_to(PROJECT_DIRECTORY)}:{node.lineno}")

		for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
			present_node(node, file)
	assert without == []


@then(parsers.parse("install.sh installe l'icône de MachinCast en « {path} » du compte"))
def installed_icon(path: str) -> None:
	assert path == f"icons/hicolor/512x512/apps/{audio.ICON}.png"
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	assert f'ICONE_DU_THEME="${{XDG_DATA_HOME:-${{HOME}}/.local/share}}/{path}"' in install
	assert Path(PROJECT_DIRECTORY / "src/machincast/interface/machincast.png").is_file()
	assert 'installer_icone "${ICONE_DU_THEME}"' in install
