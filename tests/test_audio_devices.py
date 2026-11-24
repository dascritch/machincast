"""Scénarios des périphériques de sortie du poste (https://github.com/dascritch/machincast/issues/116).

Les périphériques que voit GStreamer sont remplacés par des imitations de Gst.Device : leur type GStreamer, leur nom,
leurs propriétés et leur propriété internal-name.
"""

import dataclasses
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import audio
from machincast.configuration import Configuration
from machincast.installation import list_items_devices
from tests.database_fixtures import configuration_test
from tests.interface_steps import NAME

scenarios("audio_devices.feature")


class Properties:
	def __init__(self, values: dict[str, str]) -> None:
		self.values = values

	def get_string(self, key: str) -> str | None:
		return self.values.get(key)


class FakeAppliance:
	"""Ce qu'une imitation de Gst.Device doit répondre."""

	def __init__(self, type_gstreamer: str, name: str, node: str, internal: str, kind: str = "Audio/Sink") -> None:
		self.__gtype__ = SimpleNamespace(name=type_gstreamer)
		self.kind = kind
		self.name = name
		properties = {}
		if node:
			properties = {"node.name": node}
		self.properties = Properties(properties)
		self.internal = internal

	def get_display_name(self) -> str:
		return self.name

	def has_classes(self, kind: str) -> bool:
		return self.kind == kind

	def get_properties(self) -> Properties:
		return self.properties

	def get_property(self, name: str) -> str:
		# Comme PyGObject pour une propriété que l'objet n'a pas.
		if (name != "internal-name") or (self.internal == ""):
			raise TypeError(f"l'objet n'a pas de propriété « {name} »")
		return self.internal.replace("(vide)", "")


@pytest.fixture
def context() -> SimpleNamespace:
	return SimpleNamespace(configuration=None, list_="")


@given("les périphériques vus par GStreamer :")
@given("les entrées et les sorties vues par GStreamer :")
def seen_list(monkeypatch: pytest.MonkeyPatch, datatable: list[list[str]]) -> None:
	appliances = []
	for row in datatable[1:]:
		cell_list = []
		for cell in row:
			cell_list.append(cell.strip())
		appliances.append(FakeAppliance(*cell_list))
	monkeypatch.setattr(audio, "appliances", lambda: appliances)


@given(
	parsers.parse(
		"une configuration sur la sortie « {output} », avec l'antenne « {on_air} » et la pré-écoute « {preview} »"
	)
)
def configuration(context: SimpleNamespace, output: str, on_air: str, preview: str) -> None:
	source = configuration_test()
	adjusted = dataclasses.replace(source.audio, output=output, device=on_air, preview=preview)
	context.configuration = dataclasses.replace(source, audio=adjusted)


@when("je liste les périphériques de la configuration")
def list_items(context: SimpleNamespace) -> None:
	assert isinstance(context.configuration, Configuration)
	context.list_ = list_items_devices(context.configuration)


@then(parsers.re(r"les périphériques de la sortie « (?P<output>[^»]+) » sont (?P<list_>aucun|«.+)"))
def found_list(output: str, list_: str) -> None:
	names = NAME.findall(list_)
	expected_list = list(zip(names[::2], names[1::2], strict=True))
	fetched_list = []
	for p in audio.devices(output):
		fetched_list.append((p.identifier, p.name))
	assert fetched_list == expected_list


@then("la liste est :")
def list_(context: SimpleNamespace, docstring: str) -> None:
	assert context.list_ == f"{docstring}\n"


@then(parsers.re(r"les entrées de la sortie « (?P<output>[^»]+) » sont (?P<list_>aucune|«.+)"))
def found_inputs(monkeypatch: pytest.MonkeyPatch, output: str, list_: str) -> None:
	"""https://github.com/dascritch/machincast/issues/622 ; sans PipeWire du service joignable."""
	monkeypatch.setattr(audio, "service_appliances", lambda _kind=audio.OUTPUT_CLASS: None)
	names = NAME.findall(list_)
	expected_list = list(zip(names[::2], names[1::2], strict=True))
	fetched_list = []
	for device in audio.input_devices(output):
		fetched_list.append((device.identifier, device.name))
	assert fetched_list == expected_list
