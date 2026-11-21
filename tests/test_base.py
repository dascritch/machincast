"""Étapes des scénarios du socle de test (https://github.com/dascritch/machincast/issues/5)."""

import ast
import logging
import os
import random
import re
import stat
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest
from _pytest.capture import CaptureResult
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import log
from machincast.audio import Plugin, UnavailableAudioOutput, create_output, play_test_sound
from machincast.clock import FixedClock, SystemClock
from machincast.configuration import AudioOutput, InvalidConfiguration, load
from machincast.log import configure as configure_log
from machincast.randomness import create_randomness
from tests.database_fixtures import CONFIGURATION_TEST, configuration_test, purge_database, sample_configuration_path
from tests.style import faults as style_faults
from tests.timestamp import without_timestamp

ROOT = Path(__file__).resolve().parents[1]

scenarios("base.feature")


@dataclass
class Context:
	connection: psycopg.Connection[tuple[object, ...]] | None = None
	path: Path | None = None
	error: Exception | None = None
	clock: FixedClock | None = None
	random_draws: list[random.Random] = field(default_factory=list)
	item: object = None
	screenshot: "CaptureResult[str] | None" = None
	style_faults: list[str] = field(default_factory=list)


@pytest.fixture
def context() -> Context:
	return Context()


# ─── Configuration et base de test ─────────────────────────


@then(parsers.parse('la configuration de test désigne la base "{name}"'))
def designated_database(name: str) -> None:
	# La configuration du dépôt, même quand MACHINCAST_CONFIG_TEST en désigne une autre.
	assert load(CONFIGURATION_TEST).database.test == name


@then(parsers.parse('la sortie audio des tests est "{output}"'))
def sample_outputs(output: str) -> None:
	assert load(CONFIGURATION_TEST).audio.output == output


@then("la base de production de la configuration de test n'est pas celle du modèle de configuration")
def production_outside_tests() -> None:
	# Un binaire lancé avec la configuration de test ne doit pas pouvoir atteindre la vraie base de production
	# (https://github.com/dascritch/machincast/issues/7).
	model = load(ROOT / "machincast.exemple.toml")
	assert configuration_test().database.production != model.database.production


@given("une configuration de test dont la base de test porte le nom de la base de production")
def dangerous_configuration(context: Context, tmp_path: Path) -> None:
	database = configuration_test().database
	text = (
		sample_configuration_path()
		.read_text(encoding="utf-8")
		.replace(f'test = "{database.test}"', f'test = "{database.production}"')
	)
	context.path = tmp_path / "configuration-dangereuse.toml"
	context.path.write_text(text, encoding="utf-8")


@when("je charge cette configuration")
def load_configuration(context: Context) -> None:
	try:
		load(context.path)
	except InvalidConfiguration as error:
		context.error = error


@then(parsers.parse('le chargement échoue avec un message qui mentionne "{text}"'))
def failure(context: Context, text: str) -> None:
	assert context.error is not None, "le chargement aurait dû échouer"
	assert text in str(context.error)


@given("une base de test vide")
def database(context: Context, empty_database: psycopg.Connection[tuple[object, ...]]) -> None:
	context.connection = empty_database


def save_bank(context: Context, name: str) -> int:
	assert context.connection is not None
	line = context.connection.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, 'random') RETURNING id", (name,)
	).fetchone()
	assert line is not None
	return int(str(line[0]))


@when("j'enregistre deux banques")
def bank_two(context: Context) -> None:
	save_bank(context, "Jingles")
	save_bank(context, "Habillages")


@when("la base de test est purgée")
def purge(context: Context) -> None:
	assert context.connection is not None
	purge_database(context.connection)


@then("la base ne contient plus aucune banque")
def more_bank(context: Context) -> None:
	assert context.connection is not None
	assert context.connection.execute("SELECT count(*) FROM banks").fetchone() == (0,)


@then(parsers.parse("la prochaine banque enregistrée reçoit l'identifiant {identifier:d}"))
def put_back_identifier(context: Context, identifier: int) -> None:
	assert save_bank(context, "Nouvelle") == identifier


# ─── Horloge ───────────────────────────────────────────────


@given(parsers.parse('une horloge fixée au "{instant}"'))
def fixed_clock(context: Context, instant: str) -> None:
	context.clock = FixedClock(datetime.fromisoformat(instant))


@when(parsers.parse("l'horloge avance de {seconds:d} secondes"))
def advance(context: Context, seconds: int) -> None:
	assert context.clock is not None
	context.clock.advance(timedelta(seconds=seconds))


@then(parsers.parse('l\'horloge indique "{instant}"'))
def indicates(context: Context, instant: str) -> None:
	assert context.clock is not None
	assert context.clock.now() == datetime.fromisoformat(instant)


@then(parsers.parse('une horloge fixée au "{instant}" est refusée'))
def without_zone(instant: str) -> None:
	with pytest.raises(ValueError, match="fuseau"):
		FixedClock(datetime.fromisoformat(instant))


@then("l'horloge système donne une heure avec fuseau, proche de l'heure réelle")
def system_clock() -> None:
	instant = SystemClock().now()
	assert instant.tzinfo is not None
	assert abs(instant - datetime.now().astimezone()) < timedelta(seconds=5)


# ─── Hasard ────────────────────────────────────────────────


@given(parsers.parse("deux générateurs de hasard créés avec la graine {seed:d}"))
def generators_two(context: Context, seed: int) -> None:
	context.random_draws = [create_randomness(seed), create_randomness(seed)]


@given(parsers.parse("un générateur créé avec la graine {first:d} et un autre avec la graine {second:d}"))
def different_generators(context: Context, first: int, second: int) -> None:
	context.random_draws = [create_randomness(first), create_randomness(second)]


def draws(randomness: random.Random, count: int, among: int) -> list[int]:
	draws = []
	for _ in range(count):
		draws.append(randomness.choice(range(among)))
	return draws


@then(parsers.parse("ils tirent les mêmes {count:d} sonores parmi {among:d}"))
def same_draws(context: Context, count: int, among: int) -> None:
	first, second = context.random_draws
	assert draws(first, count, among) == draws(second, count, among)


@then(parsers.parse("leurs {count:d} tirages parmi {among:d} diffèrent"))
def different_draws(context: Context, count: int, among: int) -> None:
	first, second = context.random_draws
	assert draws(first, count, among) != draws(second, count, among)


# ─── Sortie audio ──────────────────────────────────────────


@when(parsers.parse('je crée la sortie audio "{output}" sur le périphérique "{device}"'))
def create_with_device(context: Context, output: str, device: str) -> None:
	context.item = create_output(output, device)  # type: ignore[arg-type]


@when(parsers.parse('je crée la sortie audio "{output}" sans périphérique'))
def create_without_device(context: Context, output: str) -> None:
	context.item = create_output(output, None)  # type: ignore[arg-type]


@then(parsers.parse('l\'élément GStreamer est un "{factory}"'))
def created_item(context: Context, factory: str) -> None:
	assert context.item.get_factory().get_name() == factory  # type: ignore[attr-defined]


@then(parsers.parse('son périphérique est "{device}"'))
def rule_device(context: Context, device: str) -> None:
	item = context.item
	name = "device"
	if item.get_factory().get_name() == "pipewiresink":
		name = "target-object"
	assert item.get_property(name) == device  # type: ignore[attr-defined]


@when("je joue un son de test d'une demi-seconde sur la sortie factice", target_fixture="result")
def play() -> bool:
	return play_test_sound(create_output("dummy", None), duration=timedelta(milliseconds=500))


@then("la lecture se termine sans erreur")
def finished_playback(result: bool) -> None:
	assert result is True


@when(parsers.parse("je crée une sortie dont le greffon GStreamer « {factory} » n'est pas installé"))
def missing_plugin(context: Context, factory: str) -> None:
	plugins: dict[AudioOutput, Plugin] = {
		"dummy": Plugin(factory=factory, property_=None, package="gstreamer1.0-inexistant")
	}
	try:
		create_output("dummy", None, plugins)
	except UnavailableAudioOutput as error:
		context.error = error


@then("la création échoue en nommant le paquet à installer")
def named_package(context: Context) -> None:
	assert context.error is not None, "la création aurait dû échouer"
	assert "gstreamer1.0-inexistant" in str(context.error)


# ─── Garde-fous ────────────────────────────────────────────

SOURCES = ROOT / "src" / "machincast"
DEDICATED_MODULES = {"clock.py", "randomness.py"}
# Appels qui lisent l'heure réelle ou un hasard non injecté.
FORBIDDEN_LIST = re.compile(
	r"\b(datetime\.now|datetime\.today|datetime\.utcnow|date\.today|time\.time|time\.monotonic|random\.(?!Random\b)\w+)\s*\("
	r"|^\s*(from random import|import random)\b",
	re.MULTILINE,
)


@then("aucun fichier de src/ ne lit l'heure ni le hasard en dehors de machincast.clock et machincast.randomness")
def keeps_crazy() -> None:
	faults = []
	for path in sorted(SOURCES.rglob("*.py")):
		if path.name not in DEDICATED_MODULES:
			for m in FORBIDDEN_LIST.finditer(path.read_text(encoding="utf-8")):
				faults.append(f"{path.relative_to(SOURCES)} : {m.group(0).strip()}")
	assert not faults, "utiliser machincast.clock ou machincast.randomness :\n" + "\n".join(faults)


# Un QPainter s'ouvre par with : il se ferme même quand le dessin lève une exception
# (https://github.com/dascritch/machincast/issues/413).
PAINTER = re.compile(r"QPainter\(")
PAINTER_IN_WITH = re.compile(r"^\s*with QPainter\(.*\) as \w+:")


@then("aucun fichier de src/ ne crée de QPainter hors d'un bloc with")
def painter_in_with() -> None:
	faults = []
	for path in sorted(SOURCES.rglob("*.py")):
		if path.parent.name != "ui":
			for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
				if (PAINTER.search(line.split("#", 1)[0])) and (not PAINTER_IN_WITH.match(line)):
					faults.append(f"{path.relative_to(SOURCES)}:{number}")
	assert not faults, "ouvrir le QPainter par « with QPainter(…) as painter: » :\n" + "\n".join(faults)


# Les messages des exécutables passent par logging et machincast.log, jamais par print
# (revue de https://github.com/dascritch/machincast/pull/65).
PRINT = re.compile(r"(?<![\w.])print\s*\(")


@then("aucun fichier de src/ n'appelle print")
def without_print() -> None:
	faults = []
	for path in sorted(SOURCES.rglob("*.py")):
		for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
			if PRINT.search(line.split("#", 1)[0]):
				faults.append(f"{path.relative_to(SOURCES)}:{number}")
	assert not faults, "utiliser logging (machincast.log) au lieu de print :\n" + "\n".join(faults)


@given("le répertoire des logs créé")
def created_log_directory(log_directory: Path) -> None:
	"""https://github.com/dascritch/machincast/issues/381 : celui du scénario (conftest.log_directory)."""
	log_directory.mkdir()


def _without_writing(monkeypatch: pytest.MonkeyPatch, forbidden: Path) -> None:
	"""Le répertoire des logs, que l'exécutable ne peut pas écrire : comme le compte du serveur intranet. Les tests
	tournent parfois en root, que os.access ne refuse jamais."""
	access = os.access

	def refused(path: Any, mode: int, **options: Any) -> bool:
		if (Path(path) == forbidden) and (mode & os.W_OK):
			return False
		return access(path, mode, **options)

	monkeypatch.setattr(log.os, "access", refused)


@given("le répertoire des logs créé, que l'exécutable ne peut pas écrire")
def read_only_log_directory(log_directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	log_directory.mkdir()
	_without_writing(monkeypatch, log_directory)


@given(
	parsers.parse(
		"le répertoire des logs créé, que l'exécutable ne peut pas écrire, avec « {name} », qu'il peut écrire"
	)
)
def prepared_log_file(log_directory: Path, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
	log_directory.mkdir()
	(log_directory / name).touch()
	_without_writing(monkeypatch, log_directory)


@then("le répertoire des logs est vide")
def empty_log_directory(log_directory: Path) -> None:
	assert list(log_directory.iterdir()) == []


@then(parsers.re(r"le fichier « (?P<name>[^»]+) » du répertoire des logs contient (?P<lines>«.+»)$"))
def log_file_lines(log_directory: Path, name: str, lines: str) -> None:
	expected = []
	for text in re.findall(r"« ((?:[^«»]|«[^»]*»)*) »", lines):
		expected.append(text)
	for handler in logging.getLogger("machincast").handlers:
		handler.flush()
	content = (log_directory / name).read_text(encoding="utf-8")
	assert without_timestamp(content).splitlines() == expected, content


@then(parsers.parse("le fichier « {name} » du répertoire des logs se lit et s'écrit par le groupe, pas par les autres"))
def log_file_mode(log_directory: Path, name: str) -> None:
	assert stat.S_IMODE((log_directory / name).stat().st_mode) == 0o660


@then("le répertoire des logs n'existe pas")
def no_log_directory(log_directory: Path) -> None:
	assert not log_directory.exists()


@given(parsers.parse('les messages configurés pour l\'exécutable "{executable}"'))
def configured_messages(executable: str, capsys: pytest.CaptureFixture[str]) -> None:
	# capsys est demandé dès ici : sa capture doit commencer avant l'émission des messages.
	capsys.readouterr()
	configure_log(executable)


@when(parsers.parse("le code émet une information « {information} » et une anomalie « {anomaly} »"))
def emit(information: str, anomaly: str) -> None:
	log = logging.getLogger("machincast.trial")
	log.info(information)
	log.warning(anomaly)


@when(parsers.parse("le code journalise l'erreur « {text} » d'une division par zéro"))
def logged_exception(text: str) -> None:
	"""https://github.com/dascritch/machincast/issues/574"""
	try:
		_ = 1 / 0
	except ZeroDivisionError:
		logging.getLogger("machincast.trial").exception(text)


def _with_traceback(content: str, first: str) -> None:
	"""La ligne horodatée, puis le traceback de l'exception, jusqu'à sa dernière ligne."""
	lines = without_timestamp(content.splitlines()[0] + "\n").splitlines() + content.splitlines()[1:]
	assert lines[0] == first, content
	assert lines[1] == "Traceback (most recent call last):", content
	assert "_ = 1 / 0" in content, content
	assert lines[-1] == "ZeroDivisionError: division by zero", content


@then(parsers.parse("la sortie d'erreur commence par « {first} », puis donne le traceback de la division par zéro"))
def error_with_traceback(capsys: pytest.CaptureFixture[str], first: str) -> None:
	_with_traceback(capsys.readouterr().err, first)


@then(
	parsers.parse(
		"le fichier « {name} » du répertoire des logs commence par « {first} », puis donne le traceback de la division"
		" par zéro"
	)
)
def file_with_traceback(log_directory: Path, name: str, first: str) -> None:
	for handler in logging.getLogger("machincast").handlers:
		handler.flush()
	_with_traceback((log_directory / name).read_text(encoding="utf-8"), first)


@then(parsers.parse("la sortie standard contient seulement « {text} »"))
def standard_output(capsys: pytest.CaptureFixture[str], context: Context, text: str) -> None:
	screenshot = capsys.readouterr()
	context.screenshot = screenshot
	assert without_timestamp(screenshot.out) == text + "\n", screenshot.out


@then(parsers.parse("la sortie d'erreur contient seulement « {text} »"))
def error_output(context: Context, text: str) -> None:
	assert context.screenshot is not None
	assert without_timestamp(context.screenshot.err) == text + "\n", context.screenshot.err


# Notation des chaînes (https://github.com/dascritch/machincast/issues/73). Les %s des requêtes SQL sont des
# valeurs liées par psycopg, pas du formatage de chaîne : ils ne sont pas visés.
FORMATTING_PERCENT = re.compile(
	# Message de journal composé par logging à partir d'arguments : log.info("… %s", valeur).
	r"""\b(?:log|logging|logger)\.(?:debug|info|warning|error|critical|exception)\(\s*f?["'][^"']*%[-\d.]*[sdrif(]"""
	# Format %(message)s de logging.Formatter ou de logging.basicConfig.
	r"|%\(\w+\)[sd]"
	# Opérateur % appliqué à une chaîne : "…" % valeur.
	r"""|["']\s*%\s*[\w(]"""
)
SCRIPTS_BASH = [
	ROOT / "install.sh",
	ROOT / "bin" / "Machin",
	ROOT / "bash-completion" / "Machin",
	*sorted((ROOT / "tests" / "wrapper").glob("*.bash")),
	*sorted((ROOT / "tests" / "wrapper").glob("*.bats")),
]
# $NOM sans accolades ; $1, $@, $#, $? et les substitutions $( … ) ne sont pas des noms de variables.
VARIABLE_WITHOUT_BRACES = re.compile(r"(?<!\\)\$[A-Za-z_]")


@then("aucun fichier Python du dépôt ne compose une chaîne ou un message de journal avec la notation %")
def without_percent() -> None:
	files = sorted(SOURCES.rglob("*.py")) + sorted((ROOT / "tests").glob("*.py"))
	faults = []
	for path in files:
		if path.name != "test_base.py":
			for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
				if (FORMATTING_PERCENT.search(line)) and ("N_(" not in line):
					faults.append(f"{path.relative_to(ROOT)}:{number}")
	assert not faults, "utiliser une f-string, jamais la notation % :\n" + "\n".join(faults)


# Style des conditions (revue de https://github.com/dascritch/machincast/pull/100,
# https://github.com/dascritch/machincast/issues/103), vérifié par tests/style.py. Les écrans compilés par pyside6-uic
# n'y sont pas soumis : ils ne se modifient jamais à la main.


@when(parsers.parse("je vérifie le style de l'extrait « {code} »"))
def check_extract(context: Context, code: str) -> None:
	"""\\n dans l'extrait est une fin de ligne."""
	context.style_faults = []
	for fault in style_faults(code.replace("\\n", "\n")):
		context.style_faults.append(fault.kind)


@then(parsers.re(r"l'extrait est (?P<verdict>accepté|refusé : .+)"))
def extract_verdict(context: Context, verdict: str) -> None:
	expected_list = []
	if verdict != "accepté":
		expected_list = [verdict.removeprefix("refusé : ")]
	assert sorted(set(context.style_faults)) == expected_list


@then("aucun fichier Python de src/ ni de tests/ n'enfreint le style des conditions")
def condition_style() -> None:
	files = []
	for path in sorted(SOURCES.rglob("*.py")):
		if path.parent.name != "ui":
			files.append(path)
	files += sorted((ROOT / "tests").rglob("*.py"))
	faults = []
	for path in files:
		for fault in style_faults(path.read_text(encoding="utf-8")):
			faults.append(f"{path.relative_to(ROOT)}:{fault.line} : {fault.kind}")
	assert not faults, "doc/fr/regles/developpement.md, Style de code :\n" + "\n".join(faults[:40])


@then("aucun script bash du dépôt n'écrit une variable sans accolades")
def braces() -> None:
	faults = []
	for path in SCRIPTS_BASH:
		for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
			if VARIABLE_WITHOUT_BRACES.search(line):
				faults.append(f"{path.relative_to(ROOT)}:{number} : {line.strip()}")
	assert not faults, "écrire ${VARIABLE}, jamais $VARIABLE :\n" + "\n".join(faults[:20])


def _package(requirement: str) -> str:
	name = re.split(r"[\[<>=!~; ]", requirement, maxsplit=1)[0]
	return re.sub(r"[-_.]+", "-", name).lower()


def _pyproject() -> dict[str, Any]:
	return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


@then("chaque dépendance de pyproject.toml, de développement comprise, a une version exacte dans constraints.txt")
def constraints_exact() -> None:
	project = _pyproject()["project"]
	declared = list(project["dependencies"]) + list(project["optional-dependencies"]["dev"])
	pinned = {}
	for line in (ROOT / "constraints.txt").read_text(encoding="utf-8").splitlines():
		found = re.fullmatch(r"([A-Za-z0-9_.-]+)==([0-9][^ ;]*)", line.strip())
		if found is not None:
			pinned[_package(found.group(1))] = found.group(2)
	missing = []
	for requirement in declared:
		if _package(requirement) not in pinned:
			missing.append(_package(requirement))
	assert missing == [], f"à ajouter à constraints.txt : {missing}"


@then("install.sh passe constraints.txt à pip")
def constraints_installed() -> None:
	lines = []
	for line in (ROOT / "install.sh").read_text(encoding="utf-8").splitlines():
		if ("pip" in line) and ("install" in line) and ("--editable" in line):
			lines.append(line)
	assert len(lines) == 2, lines
	for line in lines:
		assert "--constraint" in line, line
		assert "constraints.txt" in line, line


@then("la configuration de ruff active la règle RUF100")
def ruff_unused_noqa() -> None:
	assert "RUF100" in _pyproject()["tool"]["ruff"]["lint"]["select"]


@then("la configuration de coverage mesure les sous-processus")
def coverage_subprocess() -> None:
	run = _pyproject()["tool"]["coverage"]["run"]
	assert "subprocess" in run["patch"]
	assert run["parallel"] is True
	dev = _pyproject()["project"]["optional-dependencies"]["dev"]
	packages = []
	for requirement in dev:
		packages.append(_package(requirement))
	assert "coverage" in packages


@then("la configuration de ruff active la règle C901, avec une complexité d'au plus 15")
def ruff_complexity() -> None:
	ruff = _pyproject()["tool"]["ruff"]["lint"]
	assert "C901" in ruff["select"]
	assert ruff["mccabe"]["max-complexity"] <= 15


@then("la configuration de ruff active les règles FBT001 et FBT002 sur le code de src")
def ruff_keyword_booleans() -> None:
	"""Un booléen positionnel est refusé dans src (https://github.com/dascritch/machincast/issues/441) ; les tests,
	dont les étapes reçoivent leurs paramètres par leur nom, en sont dispensés."""
	ruff = _pyproject()["tool"]["ruff"]["lint"]
	assert {"FBT001", "FBT002"} <= set(ruff["select"])
	assert "tests/**" in ruff["per-file-ignores"]
	assert "src/**" not in ruff["per-file-ignores"]


def _imports(directory: Path) -> dict[str, set[str]]:
	"""Les modules de MachinCast que chaque fichier du répertoire importe, et ceux des autres bibliothèques."""
	found: dict[str, set[str]] = {}
	for path in sorted(directory.glob("*.py")):
		modules = set()
		for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
			if (isinstance(node, ast.ImportFrom)) and (node.module is not None):
				modules.add(node.module)
			if isinstance(node, ast.Import):
				for name in node.names:
					modules.add(name.name)
		found[path.name] = modules
	return found


@then("l'interface n'importe ni la diffusion, ni son moteur, ni ses plans")
def interface_without_broadcast() -> None:
	"""https://github.com/dascritch/machincast/issues/442 : ce que l'interface partage avec la diffusion est dans
	machincast.shared."""
	forbidden = {
		"machincast.player.broadcast",
		"machincast.player.broadcast_types",
		"machincast.player.broadcast_plan",
		"machincast.player.broadcast_text",
		"machincast.player.engine",
		"machincast.player.interruptions",
		"machincast.player.rundown",
	}
	faults = []
	for name, modules in _imports(ROOT / "src" / "machincast" / "interface").items():
		for module in sorted(modules & forbidden):
			faults.append(f"{name} importe {module}")
	assert not faults, faults


@then("le paquet partagé n'importe ni Qt, ni GStreamer, ni le player, ni l'interface")
def shared_without_dependencies() -> None:
	faults = []
	for name, modules in _imports(ROOT / "src" / "machincast" / "shared").items():
		for module in sorted(modules):
			library = module.split(".")[0] in ("PySide6", "gi")
			own = module.startswith(("machincast.player", "machincast.interface"))
			if (library) or (own):
				faults.append(f"{name} importe {module}")
	assert not faults, faults


@then("aucun module de l'interface qui importe Qt n'exécute de requête")
def interface_without_queries() -> None:
	"""https://github.com/dascritch/machincast/issues/442 : les requêtes sont dans machincast.interface.queries, ou dans
	les modules sans Qt (deletion, groups, sessions…) ; une classe Qt les appelle."""
	faults = []
	for path in sorted((ROOT / "src" / "machincast" / "interface").glob("*.py")):
		tree = ast.parse(path.read_text(encoding="utf-8"))
		qt = False
		executed = []
		for node in ast.walk(tree):
			if (isinstance(node, ast.ImportFrom)) and (node.module is not None) and (node.module.startswith("PySide6")):
				qt = True
			if (
				(isinstance(node, ast.Call))
				and (isinstance(node.func, ast.Attribute))
				and (node.func.attr == "execute")
			):
				executed.append(node.lineno)
		if (qt) and (executed):
			faults.append(f"{path.name}:{executed[0]}")
	assert not faults, faults


@then("la configuration de ruff active les règles PLW0127 et PLW1510 sur le code de src")
def ruff_cleanups() -> None:
	"""https://github.com/dascritch/machincast/issues/443 : pas d'affectation à soi-même, un subprocess.run avec son
	check ; les tests en sont dispensés pour PLW1510. G004 reste inactive : le style du dépôt impose les f-strings."""
	ruff = _pyproject()["tool"]["ruff"]["lint"]
	assert {"PLW0127", "PLW1510"} <= set(ruff["select"])
	assert "PLW0127" not in ruff["per-file-ignores"]["tests/**"]
	assert "src/**" not in ruff["per-file-ignores"]


@then("chaque fonction publique de plus de 15 lignes a une docstring")
def long_public_functions_documented() -> None:
	"""https://github.com/dascritch/machincast/issues/443 : une fonction ou une méthode publique, sans « _ » initial,
	de plus de 15 lignes explique ce qu'elle fait ; le code généré (interface/ui), les fonctions imbriquées et les classes privées en sont dispensées."""
	limit = 15
	faults = []
	generated = ROOT / "src" / "machincast" / "interface" / "ui"
	for path in sorted((ROOT / "src" / "machincast").rglob("*.py")):
		tree = ast.parse(path.read_text(encoding="utf-8"))
		scopes = [tree.body]
		for node in tree.body:
			if (isinstance(node, ast.ClassDef)) and (not node.name.startswith("_")):
				scopes.append(node.body)
		for body in scopes:
			for node in body:
				if (isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)) and (not node.name.startswith("_")):
					length = ((node.end_lineno) or (node.lineno)) - node.lineno + 1
					undocumented = (length > limit) and ((ast.get_docstring(node)) is None)
					if (undocumented) and (generated not in path.parents):
						faults.append(f"{path.relative_to(ROOT)}:{node.lineno} {node.name}")
	assert not faults, faults


@then("aucun test n'appelle qtbot.wait ni time.sleep hors d'une boucle d'attente, sauf par tests/waiting.py")
def no_fixed_waiting() -> None:
	"""https://github.com/dascritch/machincast/issues/444 : une attente à durée fixe passe par `quiet` (l'absence d'un
	événement) ou `settle` (une condition) de tests/waiting.py ; un sondage dans une boucle, qui lit une condition à
	chaque tour, est une attente sur condition."""
	faults = []
	for path in sorted((ROOT / "tests").glob("*.py")):
		tree = ast.parse(path.read_text(encoding="utf-8"))
		in_loop = set()
		for node in ast.walk(tree):
			if isinstance(node, ast.While | ast.For):
				for inner in ast.walk(node):
					in_loop.add(id(inner))
		for node in ast.walk(tree):
			waiting = (isinstance(node, ast.Call)) and (ast.unparse(node.func) in ("qtbot.wait", "time.sleep"))
			if (waiting) and (id(node) not in in_loop) and (path.name != "waiting.py"):
				faults.append(f"{path.name}:{node.lineno}")
	assert not faults, faults


@then("aucun fichier d'étapes partagées de tests/ ne dépasse 1500 lignes")
def steps_size() -> None:
	"""https://github.com/dascritch/machincast/issues/444 : les étapes d'un domaine ont leur greffon, au lieu d'un
	seul fichier qui grossit."""
	faults = []
	for path in sorted((ROOT / "tests").glob("*_steps.py")):
		lines = len(path.read_text(encoding="utf-8").splitlines())
		if lines > 1500:
			faults.append(f"{path.name} : {lines} lignes")
	assert not faults, faults


@then("chaque variable globale d'un module de l'interface est remise après chaque scénario par tests/conftest.py")
def interface_session_state() -> None:
	"""https://github.com/dascritch/machincast/issues/346 : une variable qu'un module de l'interface déclare `global`
	pour la changer est un état de la session ; tests.conftest.SESSION_STATE la nomme, pour la remettre."""
	from tests.conftest import SESSION_STATE

	found = set()
	for path in sorted((ROOT / "src" / "machincast" / "interface").rglob("*.py")):
		module = ".".join(path.relative_to(ROOT / "src").with_suffix("").parts)
		for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
			if isinstance(node, ast.Global):
				for name in node.names:
					found.add((module, name))
	assert found == set(SESSION_STATE), sorted(found ^ set(SESSION_STATE))
