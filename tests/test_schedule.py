"""Scénarios des tâches quotidiennes à l'heure réglée (https://github.com/dascritch/machincast/issues/455)."""

import os
import subprocess
import sys
from datetime import datetime, time
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import schedule
from machincast.configuration import PROJECT_DIRECTORY

scenarios("schedule.feature")

TEST_CONFIGURATION = PROJECT_DIRECTORY / "tests" / "configuration-test.toml"


@pytest.fixture
def context(tmp_path: Path) -> SimpleNamespace:
	return SimpleNamespace(daily=time(10, 0), last=None, state=tmp_path / "state", configuration=None, result=None)


def _local(text: str) -> datetime:
	"""Une heure du poste, écrite « AAAA-MM-JJ HH:MM »."""
	return datetime.fromisoformat(text).astimezone()


@given(parsers.parse("les tâches quotidiennes réglées à « {hour} »"))
def set_daily(context: SimpleNamespace, hour: str) -> None:
	context.daily = time.fromisoformat(hour)


@given("leur dernier passage jamais")
def never_done(context: SimpleNamespace) -> None:
	context.last = None


@given(parsers.parse("leur dernier passage le « {when} »"))
def last_done(context: SimpleNamespace, when: str) -> None:
	context.last = _local(when)


@then(parsers.re(r"le « (?P<now>[^»]+) », la tâche quotidienne (?P<verdict>est due|n'est pas due)"))
def verdict(context: SimpleNamespace, now: str, verdict: str) -> None:
	assert schedule.due(_local(now), context.daily, context.last) == (verdict == "est due")


@given("un répertoire d'état vide")
def empty_state(context: SimpleNamespace) -> None:
	context.state.mkdir()


@given(parsers.parse("une configuration de test où les tâches quotidiennes passent à « {hour} »"))
def configuration_at(context: SimpleNamespace, tmp_path: Path, hour: str) -> None:
	text = TEST_CONFIGURATION.read_text(encoding="utf-8")
	context.configuration = tmp_path / "machincast.toml"
	context.configuration.write_text(f'{text}\n[schedule]\ndaily = "{hour}"\n', encoding="utf-8")


def _claim(context: SimpleNamespace, *, with_state: bool) -> None:
	environment = dict(os.environ)
	environment.pop("STATE_DIRECTORY", None)
	if with_state:
		environment["STATE_DIRECTORY"] = str(context.state)
	context.result = subprocess.run(
		[sys.executable, "-m", "machincast.schedule", "claim", "--config", str(context.configuration)],
		env=environment,
		capture_output=True,
		text=True,
		timeout=60,
		check=False,
	)


@when("je lance « python -m machincast.schedule claim »")
def claim(context: SimpleNamespace) -> None:
	_claim(context, with_state=True)


@when("je lance « python -m machincast.schedule claim » sans répertoire d'état")
def claim_without_state(context: SimpleNamespace) -> None:
	_claim(context, with_state=False)


@then(parsers.parse("la réserve se termine par le code {code:d}"))
def claim_code(context: SimpleNamespace, code: int) -> None:
	assert context.result.returncode == code, context.result.stdout + context.result.stderr


@then("le répertoire d'état garde l'heure de ce passage")
def stamped(context: SimpleNamespace) -> None:
	stamp = datetime.fromisoformat((context.state / schedule.STAMP).read_text(encoding="utf-8").strip())
	assert abs((datetime.now().astimezone() - stamp).total_seconds()) < 60, stamp


@then(parsers.parse("sa sortie d'erreur mentionne « {text} »"))
def error_mentions(context: SimpleNamespace, text: str) -> None:
	assert text in context.result.stderr, context.result.stderr
