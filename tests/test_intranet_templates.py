"""Scénarios des gabarits Jinja2 de l'intranet, surchargeables par un plugin
(https://github.com/dascritch/machincast/issues/597).

Les répertoires templates/ des plugins sont imités dans le répertoire temporaire du scénario ;
machincast.webserver.rendering.configure les donne à l'intranet, comme son démarrage le fait pour les plugins chargés.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import catalog
from machincast.webserver import rendering
from tests.test_intranet_api import Api, _page, application, ask_with, valid_session

scenarios("intranet_templates.feature")

given(parsers.parse("l'API de l'intranet sur la base de test, à « {moment} »"), target_fixture="api")(application)
given(parsers.parse("une session valide de « {name} », de jeton « {value} »"), target_fixture="token")(valid_session)
when(parsers.parse("je demande à l'API « {request} », avec le jeton « {value} »"))(ask_with)


@pytest.fixture
def socket_path(tmp_path: Path) -> Path:
	directory = tmp_path / "lecture"
	directory.mkdir(mode=0o700)
	return directory / "lecture.sock"


@pytest.fixture
def plugin_templates(tmp_path: Path) -> Iterator[list[Path]]:
	"""Les répertoires templates/ des plugins du scénario, dans l'ordre de leur chargement."""
	directories: list[Path] = []
	yield directories
	rendering.configure([])


@given(parsers.parse("le plugin « {name} » qui fournit le gabarit « {file} » : « {content} »"))
def provided(tmp_path: Path, plugin_templates: list[Path], name: str, file: str, content: str) -> None:
	directory = tmp_path / "plugins" / name / rendering.DIRECTORY
	directory.mkdir(parents=True, exist_ok=True)
	(directory / file).write_text(content, encoding="utf-8")
	if directory not in plugin_templates:
		plugin_templates.append(directory)
	rendering.configure(plugin_templates)


@then(parsers.re(r"les gabarits de l'intranet sont (?P<names>« .+)$"))
def own_templates(names: str) -> None:
	found = []
	for template in sorted(rendering.environment().list_templates()):
		if (template.endswith(".html.jinja")) and (not template.startswith(rendering.ORIGINAL)):
			found.append(template.removesuffix(".html.jinja"))
	expected = []
	for name in names.split(", "):
		expected.append(name.strip("« »"))
	assert found == expected


@then(parsers.parse("la page contient « {text} »"))
def contains(api: Api, text: str) -> None:
	assert text in _page(api), _page(api)


@then(parsers.parse("la page ne contient pas « {text} »"))
def lacks(api: Api, text: str) -> None:
	assert text not in _page(api)


@then(parsers.parse("le catalogue relève « {message} » dans « {path} »"))
def extracted(message: str, path: str) -> None:
	found = catalog.extract()
	assert path in found[message].references, found[message].references


@then(parsers.parse("un plugin rend « {template} » avec « {key} » valant « {value} » : « {expected} »"))
def plugin_renders(template: str, key: str, value: str, expected: str) -> None:
	context = {key: value}
	assert rendering.render(template, **context).strip() == expected
