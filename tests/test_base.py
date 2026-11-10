"""Étapes des scénarios du socle de test (https://github.com/dascritch/machincast/issues/5)."""

import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from _pytest.capture import CaptureResult
from pytest_bdd import given, parsers, scenarios, then, when

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
