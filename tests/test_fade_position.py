"""Scénarios de la position des fondus par rapport aux silences détectés
(https://github.com/dascritch/machincast/issues/234).

Le placement s'essaie seul (machincast.player.fades.put) ; la diffusion, par les paramètres de lecture qu'elle lit
en base de test (machincast.player.broadcast.read_parameters), avec le rôle de Machin player.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from types import SimpleNamespace
from typing import cast

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.configuration import Crossfades
from machincast.database import Role, open_connection
from machincast.player.broadcast import Parameters, read_parameters
from machincast.player.fades import LABELS, POSITIONS, Placement, Position, put
from machincast.player.rundown import Choice
from tests.categories import inverted
from tests.database_fixtures import sample_database_parameters

scenarios("fade_position.feature")

Connection = psycopg.Connection[tuple[object, ...]]
POSITION = inverted(LABELS)
"""Chaque position par ce qu'elle dit, « est en cours »."""


@dataclass
class Trial:
	duration: timedelta = timedelta(0)
	start: timedelta | None = None
	end: timedelta | None = None
	without_silences: bool = True
	crossfades: tuple[timedelta, timedelta] = (timedelta(0), timedelta(0))
	placement: Placement | None = None
	sounds: dict[str, int] = field(default_factory=dict)
	banks: dict[str, int] = field(default_factory=dict)
	defects: Crossfades = field(default_factory=Crossfades)
	parameters: Parameters | None = None


@pytest.fixture
def trial() -> Trial:
	return Trial()


def seconds(text: str) -> float:
	return float(text.replace(",", ".").removesuffix(" s"))


def silence(text: str) -> timedelta | None:
	if text == "aucun":
		return None
	return timedelta(seconds=seconds(text))


# ─── Placement ─────────────────────────────────────────────


@given(
	parsers.re(
		r"un fichier de (?P<duration>\d+) secondes, aux silences détectés de (?P<start>[\d,]+ s|aucun) au début et"
		r" (?P<end>[\d,]+ s|aucun) à la fin, (?P<plays>sans|avec) ses silences"
	)
)
def file(trial: Trial, duration: str, start: str, end: str, plays: str) -> None:
	trial.duration = timedelta(seconds=int(duration))
	trial.start, trial.end = silence(start), silence(end)
	trial.without_silences = plays == "sans"


@given(parsers.parse("des crossfades de {start:d} secondes au début et {end:d} à la fin"))
def crossfades(trial: Trial, start: int, end: int) -> None:
	trial.crossfades = (timedelta(seconds=start), timedelta(seconds=end))


@when(
	parsers.re(
		r"le fade-in (?P<entry>commence|est en cours|se termine) au début détecté, et le fade-out"
		r" (?P<output>commence|est en cours|se termine) à la fin détectée"
	)
)
def put_fades(trial: Trial, entry: str, output: str) -> None:
	trial.placement = put(
		trial.duration,
		trial.start,
		trial.end,
		trial.without_silences,
		*trial.crossfades,
		POSITION[entry],
		POSITION[output],
	)


def _placement(trial: Trial) -> Placement:
	assert trial.placement is not None
	return trial.placement


@then(parsers.parse("la lecture va de {de} à {a} secondes du fichier"))
def playback(trial: Trial, de: str, a: str) -> None:
	placement = _placement(trial)
	assert placement.start.total_seconds() == pytest.approx(seconds(de))
	assert (placement.start + placement.duration).total_seconds() == pytest.approx(seconds(a))
	# Le fichier entier se joue sans décalage : la voie n'a rien à borner.
	integer = (seconds(de) == 0) and (seconds(a) == trial.duration.total_seconds())
	assert (placement.offset is None) == integer, placement


@then(parsers.parse("le fade-in dure {duration} secondes, depuis le volume {volume}"))
def fade_in(trial: Trial, duration: str, volume: str) -> None:
	placement = _placement(trial)
	assert placement.entry_fade.total_seconds() == pytest.approx(seconds(duration))
	assert placement.departure == pytest.approx(seconds(volume))


@then(parsers.parse("le fade-out dure {duration} secondes, jusqu'au volume {volume}"))
def fade_out(trial: Trial, duration: str, volume: str) -> None:
	placement = _placement(trial)
	assert placement.output_fade.total_seconds() == pytest.approx(seconds(duration))
	assert placement.arrival == pytest.approx(seconds(volume))


@then(parsers.parse("la position « {label} » s'écrit « {key} » dans la configuration"))
def configuration_key(label: str, key: str) -> None:
	assert key in POSITIONS
	assert LABELS[cast(Position, key)] == label


# ─── Diffusion ─────────────────────────────────────────────


@given(
	parsers.re(
		r"le sonore « (?P<title>[^»]+) », de (?P<duration>\d+) secondes, aux silences détectés de (?P<start>[\d,]+) s"
		r" au"
		r" début et (?P<end>[\d,]+) s à la fin, qui active la détection de silence, avec des crossfades de"
		r" (?P<cd>\d+) secondes au début et (?P<cf>\d+) à la fin"
	)
)
def sound(
	trial: Trial, empty_database: Connection, title: str, duration: str, start: str, end: str, cd: str, cf: str
) -> None:
	line = empty_database.execute(
		"INSERT INTO sounds (type, location, title, state, duration, detected_start, detected_end, silence_detection,"
		" crossfade_start, crossfade_end) VALUES ('file', %s, %s, 'active', %s, %s, %s, true, %s, %s) RETURNING id",
		(
			f"/srv/musique/{title}.flac",
			title,
			timedelta(seconds=int(duration)),
			timedelta(seconds=seconds(start)),
			timedelta(seconds=seconds(end)),
			timedelta(seconds=int(cd)),
			timedelta(seconds=int(cf)),
		),
	).fetchone()
	assert line is not None
	trial.sounds[title] = int(str(line[0]))


@given(
	parsers.re(
		r"les positions des fondus de la configuration : fade-in « (?P<entry>[^»]+) », fade-out « (?P<output>[^»]+) »"
	)
)
def configuration_positions(trial: Trial, entry: str, output: str) -> None:
	trial.defects = Crossfades(entry=POSITION[entry], output=POSITION[output])


@given(
	parsers.re(
		r"la banque « (?P<name>[^»]+) », avec « (?P<title>[^»]+) », qui impose un crossfade de fin de"
		r" (?P<duration>[\d,]+) secondes"
	)
)
def bank(trial: Trial, empty_database: Connection, name: str, title: str, duration: str) -> None:
	line = empty_database.execute(
		"INSERT INTO banks (internal_name, mode, crossfade_end_rule, crossfade_end)"
		" VALUES (%s, 'random', 'forced', %s) RETURNING id",
		(name, timedelta(seconds=seconds(duration))),
	).fetchone()
	assert line is not None
	trial.banks[name] = int(str(line[0]))
	empty_database.execute(
		"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, 1)",
		(line[0], trial.sounds[title]),
	)


@when(
	parsers.re(
		r"la diffusion lit les paramètres de « (?P<title>[^»]+) », (?:de la banque « (?P<name>[^»]+) »|sans banque)"
	)
)
def read(trial: Trial, title: str, name: str | None) -> None:
	id_bank = None
	if name is not None:
		id_bank = trial.banks[name]
	# read_parameters ne lit du choix que le sonore et sa banque.
	choice = cast(Choice, SimpleNamespace(sound=trial.sounds[title], bank=id_bank))
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		trial.parameters = read_parameters(connection, choice, trial.defects)


@then(
	parsers.re(
		r"ses paramètres de lecture : à partir de (?P<offset>[\d,]+) s du fichier, pendant (?P<duration>[\d,]+) s,"
		r" fade-in de (?P<cd>[\d,]+) s depuis (?P<departure>[\d,]+), fade-out de (?P<cf>[\d,]+) s jusqu'à"
		r" (?P<arrival>[\d,]+)"
	)
)
def parameters(trial: Trial, offset: str, duration: str, cd: str, departure: str, cf: str, arrival: str) -> None:
	fetched_list = trial.parameters
	assert fetched_list is not None
	assert (fetched_list.offset is not None) and (fetched_list.duration is not None)
	fetched_rows = (
		fetched_list.offset.total_seconds(),
		fetched_list.duration.total_seconds(),
		fetched_list.start_crossfade.total_seconds(),
		fetched_list.departure_volume,
		fetched_list.end_crossfade.total_seconds(),
		fetched_list.arrival_volume,
	)
	value_list = []
	for value in (offset, duration, cd, departure, cf, arrival):
		value_list.append(seconds(value))
	expected_list = tuple(value_list)
	assert fetched_rows == pytest.approx(expected_list), fetched_rows
