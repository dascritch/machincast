"""Étapes des scénarios de vérification des fichiers (https://github.com/dascritch/machincast/issues/7)."""

import os
import resource
import shutil
import subprocess
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import gi
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.indexer import decoding
from machincast.indexer.decoding import Check, FileState, UnavailableDecoder, check_file
from tests.database_fixtures import sample_configuration_path
from tests.indexing_steps import DECIMAL, count
from tests.sounds import corrupt, sample_copy, truncate

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

scenarios("check.feature")

# ─── Fichiers ──────────────────────────────────────────────


@given(parsers.parse('un fichier "{name}" qui contient du texte'), target_fixture="file")
def text_file(tmp_path: Path, name: str) -> Path:
	path = tmp_path / name
	path.write_text("Ceci n'est pas un son.\n" * 200, encoding="utf-8")
	return path


@given(parsers.parse('un fichier "{name}" vide'), target_fixture="file")
def empty_file(tmp_path: Path, name: str) -> Path:
	path = tmp_path / name
	path.touch()
	return path


@given("ce fichier tronqué de moitié")
def truncated_file(file: Path) -> None:
	truncate(file, 0.5)


@given(parsers.parse("{bytes_:d} octets corrompus au tiers de ce fichier"))
def corrupt_file(file: Path, bytes_: int) -> None:
	corrupt(file, bytes_, 1 / 3)


@given("un fichier WAV dont la lecture se bloque après son début", target_fixture="file")
def blocked_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
	"""Tube nommé : un écrivain y verse la première moitié d'un WAV, puis le garde ouvert, sans rien y écrire, jusqu'à
	ce que la vérification abandonne le décodage. Fermé après un délai fixe, la fin du fichier pourrait arriver avant
	que le blocage ne soit constaté, sur un poste chargé (https://github.com/dascritch/machincast/issues/280). Le
	décodage abandonné arrête son pipeline, dont la lecture du tube attend : le tube se ferme juste avant."""
	data = sample_copy("wav", tmp_path).read_bytes()
	start = data[: len(data) // 2]
	pipe = tmp_path / "bloque.wav"
	os.mkfifo(pipe)
	abandoned = threading.Event()
	release_true = decoding._Decoding.release

	def release(ongoing_decoding: decoding._Decoding) -> None:
		abandoned.set()
		writer.join(timeout=10)
		release_true(ongoing_decoding)

	monkeypatch.setattr(decoding._Decoding, "release", release)

	def feed() -> None:
		with pipe.open("wb") as opened_pipe:  # attend que le décodeur ouvre le tube
			opened_pipe.write(start)
			opened_pipe.flush()
			abandoned.wait(timeout=60)

	writer = threading.Thread(target=feed, daemon=True)
	writer.start()
	yield pipe
	abandoned.set()
	writer.join(timeout=10)


@dataclass
class Attempts:
	count: int = 0


@given(
	parsers.re(r"un décodage qui ne démarre (?:pas aux (?P<failures>\d+) premières tentatives|jamais)"),
	target_fixture="attempts",
)
def blocked_startup(monkeypatch: pytest.MonkeyPatch, failures: str | None) -> Attempts:
	"""Simule un démarrage bloqué : un disque réseau en veille, ou le blocage de decodebin qui a fait écarter l'AIFF
	(https://github.com/dascritch/machincast/issues/280, https://github.com/dascritch/machincast/issues/284)."""
	attempts = Attempts()
	attempt_true = decoding._attempt

	def attempt(
		path: Path, startup_delay: timedelta, delay_without_progress: timedelta, silence_threshold: float | None = None
	) -> Check | None:
		attempts.count += 1
		if (failures is None) or (attempts.count <= int(failures)):
			return None
		return attempt_true(path, startup_delay, delay_without_progress)

	monkeypatch.setattr(decoding, "_attempt", attempt)
	return attempts


@then(parsers.parse("le décodage a été tenté {count:d} fois"))
def tries(attempts: Attempts, count: int) -> None:
	assert attempts.count == count


@given("le décodeur GStreamer du Vorbis désactivé")
def disabled_vorbis() -> Iterator[None]:
	"""Simule un paquet absent : decodebin ignore les éléments de rang NONE.

	Plusieurs paquets savent décoder le Vorbis (vorbisdec de plugins-base, avdec_vorbis de libav) : tous sont écartés.
	"""
	Gst.init(None)
	vorbis = Gst.Caps.from_string("audio/x-vorbis")
	assert vorbis is not None
	factories = [
		factory
		for factory in Gst.ElementFactory.list_get_elements(Gst.ELEMENT_FACTORY_TYPE_DECODER, Gst.Rank.MARGINAL)
		if factory.can_sink_any_caps(vorbis)
	]
	assert factories, "aucun décodeur Vorbis : installer gstreamer1.0-plugins-base"
	ranks = [(factory, factory.get_rank()) for factory in factories]
	for factory in factories:
		factory.set_rank(Gst.Rank.NONE)
	yield
	for factory, rank in ranks:
		factory.set_rank(rank)


def opened_descriptors() -> int:
	return len(os.listdir("/proc/self/fd"))


@dataclass
class Limit:
	"""Descripteurs ouverts avant les vérifications."""

	opened_list: int = 0


@pytest.fixture
def limit() -> Iterator[Limit]:
	"""La limite de descripteurs du processus, rétablie en fin de scénario."""
	flexible, lasting = resource.getrlimit(resource.RLIMIT_NOFILE)
	yield Limit()
	resource.setrlimit(resource.RLIMIT_NOFILE, (flexible, lasting))


@given(parsers.parse("un processus limité à {margin:d} descripteurs de fichier de plus que ceux déjà ouverts"))
def cap(limit: Limit, file: Path, margin: int) -> None:
	# Un premier décodage ouvre ce que GStreamer garde pour toute la durée du processus (registre, horloge).
	assert check_file(file).state == FileState.HEALTHY
	limit.opened_list = opened_descriptors()
	_flexible, lasting = resource.getrlimit(resource.RLIMIT_NOFILE)
	resource.setrlimit(resource.RLIMIT_NOFILE, (limit.opened_list + margin, lasting))


@when(parsers.parse("je vérifie ce fichier {times:d} fois de suite"), target_fixture="results")
def check_several_times(file: Path, times: int) -> list[Check]:
	return [check_file(file) for _ in range(times)]


@then("le fichier est sain à chaque vérification")
def always_healthy(results: list[Check]) -> None:
	assert [result.problem for result in results if result.state != FileState.HEALTHY] == []


@then("autant de descripteurs de fichier sont ouverts qu'avant les vérifications")
def without_leak(limit: Limit) -> None:
	assert opened_descriptors() == limit.opened_list


@when(
	parsers.parse("je vérifie ce fichier en abandonnant après {seconds:d} seconde sans progression"),
	target_fixture="result",
)
def check_with_delay(file: Path, seconds: int) -> Check:
	return check_file(file, delay_without_progress=timedelta(seconds=seconds))


@then("le fichier est sain")
def is_healthy(result: Check) -> None:
	assert isinstance(result, Check), result
	assert result.state is FileState.HEALTHY, result.problem


@then(parsers.re(rf"sa durée mesurée est de (?P<expected>{DECIMAL}) secondes? à (?P<margin>{DECIMAL}) seconde près"))
def measured_duration(result: Check, expected: str, margin: str) -> None:
	assert result.duration is not None
	assert abs(result.duration.total_seconds() - count(expected)) <= count(margin), result.duration


@then(parsers.parse("le fichier est déclaré {verdict}"))
def is_declared(result: Check, verdict: str) -> None:
	assert isinstance(result, Check), result
	assert result.state == verdict, f"{result.state} : {result.problem}"
	assert (result.problem is not None) and (result.problem.startswith(verdict))


@then(parsers.parse("le problème signalé mentionne « {text} »"))
def mentioned_problem(result: Check, text: str) -> None:
	assert (result.problem is not None) and (text in result.problem), result.problem


@then("la vérification s'arrête en signalant un décodeur absent et le paquet à installer")
def absent_decoder(result: Check | UnavailableDecoder) -> None:
	assert isinstance(result, UnavailableDecoder), result
	assert "gstreamer1.0-plugins-bad" in str(result)


# ─── Exécutable ────────────────────────────────────────────


@when(
	parsers.parse('je lance "{executable}" avec une configuration dont la socket PostgreSQL n\'existe pas'),
	target_fixture="command",
)
def launch_without_database(tmp_path: Path, executable: str) -> subprocess.CompletedProcess[str]:
	configuration = tmp_path / "sans-base.toml"
	text = sample_configuration_path().read_text(encoding="utf-8")
	configuration.write_text(
		text.replace('socket = "/var/run/postgresql"', f'socket = "{tmp_path / "aucune-socket"}"'), encoding="utf-8"
	)
	path = shutil.which(executable)
	assert path is not None, f'{executable} n\'est pas installé : lancer pip install -e ".[dev]"'
	return subprocess.run([path, "--config", str(configuration)], capture_output=True, text=True, timeout=60)


@then(parsers.parse("la commande se termine avec le code {code:d}"))
def output_code(command: subprocess.CompletedProcess[str], code: int) -> None:
	assert command.returncode == code, command.stderr


@then(parsers.parse("la sortie d'erreur de la commande mentionne « {text} »"))
def command_error(command: subprocess.CompletedProcess[str], text: str) -> None:
	assert text in command.stderr, command.stderr


@pytest.fixture(autouse=True)
def gstreamer() -> None:
	Gst.init(None)
