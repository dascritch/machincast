"""Scénarios de la présentation des sorties au serveur audio (https://github.com/dascritch/machincast/issues/296).

Les sorties sont de vrais éléments GStreamer, créés sans être lancés : aucun serveur audio n'est joint.
"""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import parsers, scenarios, then, when

from machincast import audio
from machincast.configuration import PROJECT_DIRECTORY, AudioOutput

scenarios("presentation_audio.feature")

PROGRAMS = {
	"Machin player": audio.ON_AIR,
	"la pré-écoute": audio.PREVIEW,
	"l'essai de la sortie": audio.TRIAL,
}
ICON_KEYS = {"pipewiresink": "application.icon-name", "pulsesink": "application.icon_name"}


@pytest.fixture
def context() -> SimpleNamespace:
	return SimpleNamespace(output=None)


@when(parsers.parse("je crée la sortie « {output} » de {program}"))
def create(context: SimpleNamespace, output: AudioOutput, program: str) -> None:
	context.output = audio.create_output(output, None, presentation=PROGRAMS[program])


def _factory(item: audio.Gst.Element) -> str:
	factory = item.get_factory()
	assert factory is not None
	return str(factory.get_name())


@then(parsers.parse("la sortie se présente comme « {name} », pour le flux « {stream} », avec l'icône « {icon} »"))
def presented(context: SimpleNamespace, name: str, stream: str, icon: str) -> None:
	output = context.output
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
		for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
			if (not isinstance(node, ast.Call)) or (ast.unparse(node.func).split(".")[-1] != "creer_sortie"):
				continue
			found = False
			for word in node.keywords:
				if word.arg == "presentation":
					found = True
					break
			if not found:
				without.append(f"{file.relative_to(PROJECT_DIRECTORY)}:{node.lineno}")
	assert without == []


@then(parsers.parse("install.sh installe l'icône de MachinCast en « {path} » du compte"))
def installed_icon(path: str) -> None:
	assert path == f"icons/hicolor/512x512/apps/{audio.ICON}.png"
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	assert f'ICONE_DU_THEME="${{XDG_DATA_HOME:-${{HOME}}/.local/share}}/{path}"' in install
	assert Path(PROJECT_DIRECTORY / "src/machincast/interface/machincast.png").is_file()
	assert 'installer_icone "${ICONE_DU_THEME}"' in install
