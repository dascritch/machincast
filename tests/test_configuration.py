"""Étapes des scénarios du fichier de configuration."""

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import configuration as module_configuration
from machincast.cli import INVALID_CONFIGURATION_CODE
from machincast.cli import launch as launch_binary
from machincast.configuration import Configuration, InvalidConfiguration, default_file, load
from machincast.player.fades import LABELS

scenarios("configuration.feature")

ROOT = Path(__file__).resolve().parents[1]

# Configuration valide de référence, en littéraux TOML, section par section.
VALID: dict[str, dict[str, str]] = {
	"database": {"socket": '"/var/run/postgresql"', "production": '"machincast"', "test": '"machincast_test"'},
	"audio": {"output": '"pipewire"', "device": '"antenne"', "preview": '"casque"'},
	"outputs": {"csv": '"airplay.csv"', "pls": '"playlist.pls"', "html": '"airplay.html"'},
	"metadata": {"hide": "false", "public_text": '"Radio FMR"'},
}


@dataclass
class Context:
	directory: Path
	path: Path | None = None
	configuration: Configuration | None = None
	error: InvalidConfiguration | None = None
	result: subprocess.CompletedProcess[str] | None = None
	code: int | None = None
	received: Configuration | None = None
	errors: str = ""
	keys: dict[str, dict[str, str]] = field(default_factory=lambda: {s: dict(c) for s, c in VALID.items()})


@pytest.fixture
def context(tmp_path: Path) -> Context:
	return Context(directory=tmp_path)


def write(context: Context, name: str = "machincast.toml") -> Path:
	lines: list[str] = []
	for section, keys in context.keys.items():
		lines.append(f"[{section}]")
		key_list = []
		for key, value in keys.items():
			key_list.append(f"{key} = {value}")
		lines += key_list
		lines.append("")
	path = context.directory / name
	path.write_text("\n".join(lines), encoding="utf-8")
	context.path = path
	return path


def launch(executable: str, arguments: list[str], directory: Path) -> subprocess.CompletedProcess[str]:
	path = shutil.which(executable)
	assert path is not None, f"{executable} n'est pas installé"
	return subprocess.run(
		[path, *arguments], capture_output=True, text=True, timeout=30, cwd=directory, env=os.environ.copy()
	)


# ─── Étant donné ───────────────────────────────────────────


@given("le modèle de configuration du dépôt")
def model(context: Context) -> None:
	context.path = ROOT / "machincast.exemple.toml"


@given("un fichier de configuration contenant :")
def container_file(context: Context, docstring: str) -> None:
	context.path = context.directory / "machincast.toml"
	context.path.write_text(docstring, encoding="utf-8")


@given(parsers.parse('une configuration valide où la clé "{key}" est absente'))
def absent_key(context: Context, key: str) -> None:
	section, name = key.split(".")
	context.keys.setdefault(section, {}).pop(name, None)
	write(context)


@given(parsers.parse('une configuration valide où la clé "{key}" vaut {value}'))
def key_is_worth(context: Context, key: str, value: str) -> None:
	section, name = key.split(".")
	value = value.replace("<256 caractères>", "é" * 256)
	context.keys.setdefault(section, {})[name] = value
	write(context)


@given(parsers.parse('une configuration valide sans section "{section}"'))
def without_section(context: Context, section: str) -> None:
	context.keys.pop(section, None)
	write(context)


@given(parsers.parse('la clé "{key}" vaut {value}'))
def and_key_is_worth(context: Context, key: str, value: str) -> None:
	key_is_worth(context, key, value)


@given(parsers.parse("le répertoire d'exécution du compte « {directory} »"))
def execution_directory(monkeypatch: pytest.MonkeyPatch, directory: str) -> None:
	monkeypatch.setenv("XDG_RUNTIME_DIR", directory)


@given("un chemin de configuration qui n'existe pas")
def absent_path(context: Context) -> None:
	context.path = context.directory / "absent.toml"


@given(parsers.parse('une configuration valide enregistrée dans "{name}"'))
def valid_saved(context: Context, name: str) -> None:
	"""Configuration passée à un binaire : sa socket PostgreSQL n'existe pas, pour qu'il ne puisse joindre aucune
	base, et surtout pas la base de production qu'elle désigne (https://github.com/dascritch/machincast/issues/7)."""
	context.keys["database"]["socket"] = f'"{context.directory / "aucune-socket"}"'
	write(context, name)


# ─── Quand ─────────────────────────────────────────────────


@when("je charge la configuration")
def load_configuration(context: Context) -> None:
	try:
		context.configuration = load(context.path)
	except InvalidConfiguration as error:
		context.error = error


@when(parsers.parse('je lance "{executable}" avec la configuration "{name}"'))
def launch_with_configuration(context: Context, executable: str, name: str) -> None:
	context.result = launch(executable, ["--config", name], context.directory)


@given("ce répertoire tient lieu de répertoire de MachinCast")
def machincast_directory(context: Context, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(module_configuration, "PROJECT_DIRECTORY", context.directory)


@given("un répertoire de MachinCast sans machincast.toml")
def directory_without_file(context: Context, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(module_configuration, "PROJECT_DIRECTORY", context.directory)


@given("le répertoire courant est un autre répertoire")
def other_directory(context: Context, monkeypatch: pytest.MonkeyPatch) -> None:
	elsewhere = context.directory / "ailleurs"
	elsewhere.mkdir()
	monkeypatch.chdir(elsewhere)


@when("un binaire démarre sans option")
def start_without_option(context: Context, capsys: pytest.CaptureFixture[str]) -> None:
	def action(configuration: Configuration, _options: object) -> int:
		context.received = configuration
		return 0

	context.code = launch_binary("Machin_essai", "Binaire d'essai.", [], action)
	context.errors = capsys.readouterr().err


@when(parsers.parse('je lance "{executable}" avec l\'option "{option}"'))
def launch_option(context: Context, executable: str, option: str) -> None:
	context.result = launch(executable, [option], context.directory)


@when(parsers.parse('je lance "{executable}" avec ce chemin de configuration'))
def launch_with_path(context: Context, executable: str) -> None:
	assert context.path is not None
	context.result = launch(executable, ["--config", str(context.path)], context.directory)


# ─── Alors ─────────────────────────────────────────────────


def configuration(context: Context) -> Configuration:
	assert context.error is None, str(context.error)
	assert context.configuration is not None
	return context.configuration


@then(parsers.parse('le fichier de configuration par défaut est "{name}" à la racine du dépôt'))
def default_in_drop(name: str) -> None:
	assert default_file() == ROOT / name


@then("il reçoit la configuration de ce répertoire")
def receives_configuration(context: Context) -> None:
	assert context.code == 0, context.errors
	assert context.received is not None
	# Les chemins relatifs sont résolus depuis le fichier lu : c'est bien celui de ce répertoire.
	assert context.received.outputs.csv == context.directory / "airplay.csv"


@then(parsers.parse("il s'arrête avec le code {code:d}"))
def code_stop(context: Context, code: int) -> None:
	assert context.code == code


@then("son erreur mentionne le chemin complet du machincast.toml de ce répertoire")
def full_path_error(context: Context) -> None:
	assert str(context.directory / "machincast.toml") in context.errors, context.errors


@then("la sortie mentionne le machincast.toml à la racine du dépôt")
def default_help(context: Context) -> None:
	assert context.result is not None
	assert str(ROOT / "machincast.toml") in context.result.stdout, context.result.stdout


@then("la configuration est chargée sans erreur")
def loaded(context: Context) -> None:
	configuration(context)


@then(parsers.parse('la base de production est "{name}"'))
def production_database(context: Context, name: str) -> None:
	assert configuration(context).database.production == name


@then(parsers.parse('la base de test est "{name}"'))
def sample_database(context: Context, name: str) -> None:
	assert configuration(context).database.test == name


@then(parsers.parse('la sortie audio est "{output}" sur le périphérique "{device}"'))
def audio_output(context: Context, output: str, device: str) -> None:
	audio = configuration(context).audio
	assert (audio.output, audio.device) == (output, device)


@then("la sortie audio utilise le périphérique par défaut")
def default_device(context: Context) -> None:
	assert configuration(context).audio.device is None


@then(parsers.parse('la pré-écoute utilise le périphérique "{device}"'))
def preview(context: Context, device: str) -> None:
	assert configuration(context).audio.preview == device


@then(parsers.parse('la sortie CSV est "{relative}" à côté du fichier de configuration'))
def csv_output(context: Context, relative: str) -> None:
	assert configuration(context).outputs.csv == context.directory / relative


@then(parsers.re(r'la socket d\'état est "(?P<path>[^"]+)"(?P<relative> à côté du fichier de configuration)?$'))
def state_socket(context: Context, path: str, relative: str | None) -> None:
	assert context.configuration is not None
	expected = Path(path)
	if relative:
		expected = context.directory / path
	assert context.configuration.player.state_socket == expected


@then(parsers.parse('la sortie HTML est "{absolute}"'))
def html_output(context: Context, absolute: str) -> None:
	assert configuration(context).outputs.html == Path(absolute)


@then(parsers.parse('le texte public par défaut est "{text}"'))
def public_text(context: Context, text: str) -> None:
	assert configuration(context).metadata.public_text == text


@then("les métadonnées sont masquées par défaut")
def hidden_list(context: Context) -> None:
	assert configuration(context).metadata.hide is True


@then(parsers.parse('le chargement échoue avec un message qui mentionne "{text}"'))
def mentioned_failure(context: Context, text: str) -> None:
	assert context.error is not None, "le chargement aurait dû échouer"
	assert text in str(context.error)


@then(parsers.parse('le message mentionne "{text}"'))
def mentioned_message(context: Context, text: str) -> None:
	assert text in str(context.error)


@then("le chargement échoue avec un message qui mentionne le chemin du fichier")
def path_failure(context: Context) -> None:
	assert context.error is not None, "le chargement aurait dû échouer"
	assert str(context.path) in str(context.error)


@then("la configuration est acceptée par le binaire")
def accepted(context: Context) -> None:
	# Après une configuration acceptée, le binaire va plus loin : il signale un ticket à venir, ou ne joint pas la base.
	assert context.result is not None
	assert context.result.returncode != INVALID_CONFIGURATION_CODE, context.result.stderr
	assert "configuration invalide" not in context.result.stderr, context.result.stderr


@then(parsers.parse("le binaire s'arrête avec le code {code:d}"))
def returned_code(context: Context, code: int) -> None:
	assert context.result is not None
	assert context.result.returncode == code


@then("l'erreur affichée mentionne le chemin du fichier")
def path_error(context: Context) -> None:
	assert context.result is not None
	assert str(context.path) in context.result.stderr


# ─── Crossfades (https://github.com/dascritch/machincast/issues/145) ─────


@then(
	parsers.re(
		r"les crossfades se règlent (?P<granularity>au dixième de seconde|à la seconde),"
		r" jusqu'à (?P<maximum>\d+) secondes"
	)
)
def granularity_and_maximum(context: Context, granularity: str, maximum: str) -> None:
	assert context.configuration is not None, context.error
	crossfades = context.configuration.crossfades
	expected = {"au dixième de seconde": "tenth", "à la seconde": "second"}[granularity]
	assert (crossfades.granularity, crossfades.maximum) == (expected, timedelta(seconds=int(maximum)))


@then("les crossfades n'ont pas de durée par défaut")
def without_default(context: Context) -> None:
	assert context.configuration is not None, context.error
	assert (context.configuration.crossfades.start, context.configuration.crossfades.end) == (None, None)


@then(
	parsers.re(
		r"les crossfades durent par défaut (?P<start>[\d,]+) secondes? au début et (?P<end>[\d,]+) secondes? à la fin"
	)
)
def defects(context: Context, start: str, end: str) -> None:
	assert context.configuration is not None, context.error
	crossfades = context.configuration.crossfades
	value_list = []
	for value in (start, end):
		value_list.append(timedelta(seconds=float(value.replace(",", "."))))
	expected_list = tuple(value_list)
	assert (crossfades.start, crossfades.end) == expected_list


@then(parsers.parse("les fiches chargent {rows:d} lignes à la fois"))
def table_rows(context: Context, rows: int) -> None:
	assert context.configuration is not None
	assert context.configuration.interface.table_rows == rows


@then(parsers.parse("la durée de péremption est de {days:d} jours"))
def retention(context: Context, days: int) -> None:
	"""https://github.com/dascritch/machincast/issues/268"""
	assert context.configuration is not None, context.error
	assert context.configuration.database.retention == days


@then(parsers.re(r"le seuil de silence est de (?P<threshold>-?[\d,]+) dB"))
def silence_threshold(context: Context, threshold: str) -> None:
	"""https://github.com/dascritch/machincast/issues/146"""
	assert context.configuration is not None, context.error
	assert context.configuration.silences.threshold == float(threshold.replace(",", "."))


@then(
	parsers.re(
		r"un blanc dans un sonore dure au moins (?P<duration>[\d,]+) secondes sous (?P<threshold>-?[\d,]+) dB, et il"
		r" (?P<remainder>est noté seulement|fait passer au secours)"
	)
)
def dead_air(context: Context, duration: str, threshold: str, remainder: str) -> None:
	"""https://github.com/dascritch/machincast/issues/122"""
	assert context.configuration is not None, context.error
	dead_air_found = context.configuration.dead_air
	expected = (timedelta(seconds=float(duration.replace(",", "."))), float(threshold.replace(",", ".")))
	assert (dead_air_found.duration, dead_air_found.threshold) == expected
	assert dead_air_found.fallback is (remainder == "fait passer au secours")


@then("le journal avertit que la section [blancs] s'appelle désormais [silences]")
def warns_dead_airs(caplog: pytest.LogCaptureFixture) -> None:
	"""https://github.com/dascritch/machincast/issues/291"""
	warnings = []
	for r in caplog.records:
		if r.levelno == logging.WARNING:
			warnings.append(r.getMessage())
	found = False
	for m in warnings:
		if "la section [blancs] s'appelle désormais [silences]" in m:
			found = True
			break
	assert found, warnings


@then(parsers.re(r"le voyant « Saturation » de l'onglet Antenne est (?P<state>affiché|caché)"))
def clipping_light(context: Context, state: str) -> None:
	"""https://github.com/dascritch/machincast/issues/191"""
	assert context.configuration is not None, context.error
	assert context.configuration.interface.clipping is (state == "affiché")


@then(parsers.re(r"les suggestions au lancement sont (?P<state>actives|éteintes)"))
def suggestions_to_launching(context: Context, state: str) -> None:
	"""https://github.com/dascritch/machincast/issues/119"""
	assert context.configuration is not None, context.error
	assert context.configuration.interface.suggestions is (state == "actives")


# ─── Icône de l'interface (https://github.com/dascritch/machincast/issues/111) ───


@then("l'icône de l'interface est celle de MachinCast")
def default_icon(context: Context) -> None:
	assert context.configuration is not None
	assert context.configuration.interface.icon is None


@then(parsers.parse("l'icône de l'interface est \"{relative}\" à côté du fichier de configuration"))
def relative_icon(context: Context, relative: str) -> None:
	assert context.configuration is not None
	assert context.path is not None
	assert context.configuration.interface.icon == context.path.parent / relative


@then(
	parsers.re(
		r"le fade-in (?P<entry>commence|est en cours|se termine) au début détecté, et le fade-out"
		r" (?P<output>commence|est en cours|se termine) à la fin détectée"
	)
)
def fade_positions(context: Context, entry: str, output: str) -> None:
	"""https://github.com/dascritch/machincast/issues/234"""
	assert context.configuration is not None, context.error
	crossfades = context.configuration.crossfades
	assert (LABELS[crossfades.entry], LABELS[crossfades.output]) == (entry, output)


@then(
	parsers.re(
		r"l'antenne joue sur la sortie « (?P<output>[^»]+) »,"
		r" (?:sans périphérique|sur le périphérique « (?P<device>[^»]+) »)"
	)
)
def on_air_output(context: Context, output: str, device: str | None) -> None:
	"""L'entrée « sortie factice » (https://github.com/dascritch/machincast/issues/339)."""
	assert context.configuration is not None, context.error
	assert context.configuration.audio.on_air() == (output, device)


@then(parsers.re(r"la pré-écoute est (?P<state>active|désactivée)"))
def active_preview(context: Context, state: str) -> None:
	assert context.configuration is not None, context.error
	assert context.configuration.audio.disabled_preview() == (state == "désactivée")
