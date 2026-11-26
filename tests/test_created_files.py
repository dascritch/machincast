"""Étapes de la liste des fichiers créés par MachinCast (https://github.com/dascritch/machincast/issues/652).

Chaque scénario pose sa liste dans son répertoire temporaire : la fixture created_files_list (tests/conftest.py) y
impose aussi celle des binaires qu'il lance.
"""

import io
import shutil
from collections.abc import Callable
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import cli, created_files, power_save
from machincast.created_files import NotCreatedByMachinCast
from machincast.indexer import audit as audit_module
from machincast.interface import columns, preview
from machincast.player import outputs, simulation

scenarios("created_files.feature")

ROOT = Path(__file__).resolve().parents[1]
FOREIGN = "écrit par quelqu'un d'autre\n"


@dataclass
class Context:
	directory: Path
	listing: Path | None = None
	error: Exception | None = None
	inode: int = 0
	code: int = 0
	output: str = ""
	written: list[str] = field(default_factory=list)
	writer: str = ""


@pytest.fixture
def context(tmp_path: Path) -> Context:
	return Context(tmp_path / "poste")


def _listing(context: Context) -> Path:
	assert context.listing is not None
	return context.listing


def _shown(context: Context, text: str) -> str:
	return text.replace(f"{context.directory}/", "")


@given(parsers.parse("la liste des fichiers créés de la configuration « {name} »"))
def listing(context: Context, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
	context.directory.mkdir()
	context.listing = created_files.beside(context.directory / name)
	monkeypatch.setattr(created_files, "LIST", context.listing)


@given(parsers.re(r"le fichier « (?P<name>[^»]+) », écrit par (?:quelqu'un d'autre|une version d'avant la liste)"))
def foreign(context: Context, name: str) -> None:
	path = context.directory / name
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(FOREIGN, encoding="utf-8")


@given("la liste existe déjà, au mode 0660")
def existing_list(context: Context) -> None:
	path = _listing(context)
	path.write_text("", encoding="utf-8")
	path.chmod(0o660)
	context.inode = path.stat().st_ino


def _write(context: Context, name: str) -> None:
	path = context.directory / name
	path.parent.mkdir(parents=True, exist_ok=True)
	try:
		created_files.write_text(path, f"{name}\n")
	except NotCreatedByMachinCast as error:
		context.error = error


@when(
	parsers.re(
		r"MachinCast écrit « (?P<first>[^»]+) »(?:, puis « (?P<second>[^»]+) »)?(?:, puis de nouveau « (?P<third>[^»]+) »)?$"
	)
)
def write(context: Context, first: str, second: str | None, third: str | None) -> None:
	for name in (first, second, third):
		if name is not None:
			_write(context, name)


@when(parsers.parse("MachinCast efface « {name} »"))
def delete(context: Context, name: str) -> None:
	created_files.delete(context.directory / name)
	assert not (context.directory / name).exists()


def _lines(context: Context) -> list[str]:
	return _listing(context).read_text(encoding="utf-8").splitlines()


@then(
	parsers.re(
		r"la liste a pour lignes les chemins absolus de « (?P<first>[^»]+) » et « (?P<second>[^»]+) », dans cet ordre"
	)
)
def two_lines(context: Context, first: str, second: str) -> None:
	assert _lines(context) == [str(context.directory / first), str(context.directory / second)]


@then(parsers.parse("la liste a pour lignes le chemin absolu de « {name} »"))
def one_line(context: Context, name: str) -> None:
	assert _lines(context) == [str(context.directory / name)]


@then("la liste est vide")
def empty(context: Context) -> None:
	assert _lines(context) == []


@then(parsers.parse("la liste est « {name} », à côté de « {configuration} »"))
def beside(context: Context, name: str, configuration: str) -> None:
	assert _listing(context) == context.directory / name
	assert created_files.beside(context.directory / configuration) == context.directory / name


@then(parsers.parse("il est refusé : « {message} »"))
def refused(context: Context, message: str) -> None:
	assert context.error is not None
	assert _shown(context, str(context.error)) == message


@then(parsers.parse("« {name} » est intact"))
def intact(context: Context, name: str) -> None:
	assert (context.directory / name).read_text(encoding="utf-8") == FOREIGN


@then("la liste a gardé son inode et son mode 0660")
def same_inode(context: Context) -> None:
	status = _listing(context).stat()
	assert (status.st_ino, status.st_mode & 0o777) == (context.inode, 0o660)


@given(parsers.parse("le fichier de configuration valide « {name} », sans liste imposée par les tests"))
def configuration(context: Context, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
	context.directory.mkdir()
	shutil.copy(ROOT / "tests" / "configuration-test.toml", context.directory / name)
	monkeypatch.delenv(created_files.ENVIRONMENT)


@when(parsers.parse("un binaire se lance avec « {name} »"))
def launched(context: Context, name: str) -> None:
	def action(_configuration: object, _options: object) -> int:
		context.listing = created_files.LIST
		return 0

	assert cli.launch("Machin_test", "", ["--config", str(context.directory / name)], action) == 0


@then(parsers.parse("la liste en cours est « {name} », à côté de « {configuration} »"))
def current(context: Context, name: str, configuration: str) -> None:
	assert context.directory / name == created_files.LIST
	beside(context, name, configuration)


def _command(context: Context, action: str, names: list[str]) -> None:
	output = io.StringIO()
	arguments = ["--list", str(_listing(context)), action]
	for name in names:
		arguments.append(str(context.directory / name))
	with redirect_stdout(output):
		context.code = created_files.main(arguments)
	context.output = output.getvalue()


@when(parsers.re(r"install.sh lance « (?P<action>\w+) » sur « (?P<first>[^»]+) »(?: et « (?P<second>[^»]+) »)?$"))
def command(context: Context, action: str, first: str, second: str | None) -> None:
	names = [first]
	if second is not None:
		names.append(second)
	_command(context, action, names)


@when(parsers.parse("install.sh lance « {action} » sur « {name} », écrit par quelqu'un d'autre"))
def command_foreign(context: Context, action: str, name: str) -> None:
	foreign(context, name)
	_command(context, action, [name])


@then(parsers.parse("la commande écrit le chemin absolu de « {name} », et se termine par le code 0"))
def wrote(context: Context, name: str) -> None:
	assert (context.output, context.code) == (f"{context.directory / name}\n", 0)


@then(parsers.parse("la commande se termine par le code {code:d}"))
def ended(context: Context, code: int) -> None:
	assert context.code == code


# ─── Ceux qui écrivent ─────────────────────────────────

START = datetime.fromisoformat("2026-11-26 20:00:00").astimezone()


def _writers(context: Context) -> dict[str, tuple[list[Path], Callable[[], object]]]:
	"""Les fichiers de chaque écrivain, et ce qui les écrit."""
	directory = context.directory
	configuration = directory / "machincast.toml"
	audit = directory / "audits" / f"machincast-audit-{START:%Y-%m-%dT%H:%M:%S}"
	return {
		"la page HTML de Machin player": (
			[directory / "sorties" / "airplay.html"],
			lambda: outputs._write(directory / "sorties" / "airplay.html", "<p>page</p>\n"),
		),
		"la simulation de Machin player": (
			[directory / "simulation" / f"essai{extension}" for extension in (".csv", ".pls", ".html")],
			lambda: simulation.export([], [], directory / "simulation", "essai", START, START + timedelta(hours=1)),
		),
		"le rapport de l'audit complet": (
			[audit.with_suffix(".csv"), audit.with_suffix(".html")],
			lambda: audit_module.write([], "rapport", START, directory / "audits"),
		),
		"la pré-écoute choisie dans l'interface": (
			[configuration],
			lambda: preview.write_preview(configuration, "dummy"),
		),
		"les réglages des vues de l'interface": (
			[directory / "vues.ini"],
			lambda: _views(directory / "vues.ini"),
		),
		"le retrait des réglages d'économie d'énergie": (
			[directory / path.relative_to("/") for path, _text in power_save.SETTINGS],
			lambda: power_save.disable(directory),
		),
	}


def _views(path: Path) -> None:
	views = columns.settings()
	views.setValue("essai/colonnes", "titre")
	views.sync()
	assert Path(views.fileName()).is_file()


@pytest.fixture(autouse=True)
def quiet_udevadm(monkeypatch: pytest.MonkeyPatch) -> None:
	"""Le retrait des réglages d'économie d'énergie relance udevadm : jamais sur le poste des tests."""
	monkeypatch.setattr(power_save, "_udevadm", lambda *_arguments: None)


@pytest.fixture(autouse=True)
def views_here(context: Context, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
	monkeypatch.setattr(columns, "FILE", context.directory / "vues.ini")
	monkeypatch.setattr(columns, "FALLBACK", tmp_path / "execution" / "vues.ini")
	monkeypatch.setattr(columns, "_KEPT", set())


def _prepare(context: Context, writer: str) -> None:
	"""Le répertoire des rapports de l'audit ; la configuration, que la pré-écoute réécrit, est celle de MachinCast."""
	(context.directory / "audits").mkdir(exist_ok=True)
	configuration = context.directory / "machincast.toml"
	if (writer == "la pré-écoute choisie dans l'interface") and (not configuration.exists()):
		shutil.copy(ROOT / "tests" / "configuration-test.toml", configuration)
		created_files.record([configuration])


@given(parsers.parse("les fichiers de {writer} existent déjà, écrits par quelqu'un d'autre"))
def foreign_files(context: Context, writer: str) -> None:
	for path in _writers(context)[writer][0]:
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(FOREIGN, encoding="utf-8")


@given("le fichier des vues existe déjà, écrit par quelqu'un d'autre")
def foreign_views(context: Context) -> None:
	foreign_files(context, "les réglages des vues de l'interface")


@when(parsers.parse("{writer} écrit ses fichiers"))
def writes(context: Context, writer: str) -> None:
	context.writer = writer
	_prepare(context, writer)
	try:
		_writers(context)[writer][1]()
	except NotCreatedByMachinCast as error:
		context.error = error


@when("l'interface règle ses vues")
def views(context: Context) -> None:
	writes(context, "les réglages des vues de l'interface")


@then("chacun de ses fichiers est dans la liste")
def all_listed(context: Context) -> None:
	assert context.error is None
	for path in _writers(context)[context.writer][0]:
		assert path.is_file(), path
		assert created_files.listed(path), path


@then("il est refusé, et ses fichiers sont intacts")
def all_refused(context: Context) -> None:
	assert isinstance(context.error, NotCreatedByMachinCast)
	for path in _writers(context)[context.writer][0]:
		assert path.read_text(encoding="utf-8") == FOREIGN, path


@then("le fichier des vues est intact, et les vues sont réglées dans un fichier d'exécution")
def views_aside(context: Context) -> None:
	assert context.error is None
	assert (context.directory / "vues.ini").read_text(encoding="utf-8") == FOREIGN
	assert "colonnes=titre" in columns.FALLBACK.read_text(encoding="utf-8")
	assert not created_files.listed(context.directory / "vues.ini")
