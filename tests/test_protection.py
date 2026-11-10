"""Étapes de la protection des fichiers sonores (https://github.com/dascritch/machincast/issues/96).

Les étapes de la diffusion viennent de tests/broadcast_steps.py.
"""

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.configuration import Metadata
from machincast.configuration import Outputs as OutputPaths
from machincast.database import Role, open_connection
from machincast.indexer.indexer import index
from machincast.player.outputs import Outputs
from machincast.player.saving import Play
from machincast.player.simulation import export, simulate
from machincast.player.state import StateSocket
from machincast.protection import ProtectedSoundFile, unjustified
from tests.broadcast_steps import Connection
from tests.database_fixtures import sample_database_parameters
from tests.log_texts import shown, stored
from tests.sounds import corrupt, sample_copy

scenarios("protection.feature")

ROOT = Path(__file__).resolve().parents[1]
INSTANT = datetime.fromisoformat("2026-10-14 20:00:00").astimezone()

Reading = dict[Path, tuple[str, int, int]]


@dataclass
class Context:
	directory: Path | None = None
	bank: int | None = None
	reading: Reading = field(default_factory=dict)
	outputs: Outputs | None = None
	error: Exception | None = None
	code: str = ""


@pytest.fixture
def context() -> Context:
	return Context()


def directory(context: Context) -> Path:
	assert context.directory is not None
	return context.directory


def read_off(folder: Path) -> Reading:
	"""Octets, taille et date de modification de chaque fichier du répertoire."""
	return {
		path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size, path.stat().st_mtime_ns)
		for path in sorted(folder.rglob("*"))
		if path.is_file()
	}


def index_database(full_audit: bool) -> None:
	with open_connection(*sample_database_parameters(), Role.INDEXING) as connection:
		index(connection, full_audit=full_audit)


def sound_of(database: Connection, context: Context, name: str) -> int:
	line = database.execute("SELECT id FROM sounds WHERE location = %s", (str(directory(context) / name),)).fetchone()
	assert line is not None, f"aucun sonore pour {name}"
	return int(str(line[0]))


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("une banque « {name} » dont le répertoire contient « {healthy} », sain, et « {worn} », endommagé"))
def bank(context: Context, empty_database: Connection, tmp_path: Path, name: str, healthy: str, worn: str) -> None:
	folder = tmp_path / "musique"
	folder.mkdir()
	sample_copy("flac", folder).rename(folder / healthy)
	damaged = sample_copy("mp3", folder)
	corrupt(damaged, 1000, 1 / 3)
	damaged.rename(folder / worn)
	line = empty_database.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential') RETURNING id", (name,)
	).fetchone()
	assert line is not None
	empty_database.execute("INSERT INTO bank_directories VALUES (%s, %s)", (line[0], str(folder)))
	context.directory, context.bank = folder, int(str(line[0]))


@given(parsers.parse("les fichiers de la banque « {name} » relevés, puis la banque indexée"))
def indexed(context: Context, name: str) -> None:
	context.reading = read_off(directory(context))
	index_database(full_audit=False)


@given(parsers.parse("le fil musical permanent « {name} », avec la banque « {bank} »"))
def bank_feed(context: Context, empty_database: Connection, name: str, bank: str) -> None:
	line = empty_database.execute(
		"INSERT INTO events (internal_name, priority) VALUES (%s, 'background_programming') RETURNING id", (name,)
	).fetchone()
	assert line is not None
	empty_database.execute(
		"INSERT INTO event_items (event_id, position, bank_id) VALUES (%s, 1, %s)",
		(line[0], context.bank),
	)


@given(parsers.parse("la sortie {output} placée sur le fichier sonore « {name} »"))
def output_on_sound(context: Context, tmp_path: Path, output: str, name: str) -> None:
	target = directory(context) / name
	paths = {
		"csv": tmp_path / "sorties" / "airplay.csv",
		"pls": tmp_path / "sorties" / "playlist.pls",
		"html": tmp_path / "sorties" / "airplay.html",
	}
	# Le CSV du jour ajoute la date au nom : son modèle est placé à côté du fichier sonore, avec son extension.
	paths[output] = target
	context.outputs = Outputs(OutputPaths(**paths), Metadata(hide=False, public_text="Radio"))


@given(parsers.parse("le code « {code} »"))
def code(context: Context, code: str) -> None:
	context.code = code


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"l'entrée du sonore « (?P<name>[^»]+) » (?P<change>.+)"))
def change_entry(context: Context, empty_database: Connection, name: str, change: str) -> None:
	identifier = sound_of(empty_database, context, name)
	state = re.fullmatch(r"passe à l'état « (\w+) »", change)
	match change:
		case _ if state:
			empty_database.execute("UPDATE sounds SET state = %s WHERE id = %s", (state.group(1), identifier))
		case "change d'emplacement":
			empty_database.execute(
				"UPDATE sounds SET location = %s WHERE id = %s",
				(str(directory(context) / "ailleurs.flac"), identifier),
			)
		case "change d'artiste et de titre":
			empty_database.execute("UPDATE sounds SET artist = 'Autre', title = 'Autre' WHERE id = %s", (identifier,))
		case "est supprimée de la base":
			empty_database.execute("DELETE FROM sounds WHERE id = %s", (identifier,))
		case _:
			raise AssertionError(f"changement inconnu : {change}")


@when("l'indexeur fait une indexation rapide, puis un audit complet")
def indexings() -> None:
	index_database(full_audit=False)
	index_database(full_audit=True)


@when(parsers.parse("une simulation de {minutes:d} minutes tourne"))
def simulation(tmp_path: Path, minutes: int) -> None:
	"""Quelques minutes suffisent : des centaines de passages de sonores d'une seconde
	(https://github.com/dascritch/machincast/issues/280)."""
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		simulate(connection, tmp_path / "simulation", INSTANT, INSTANT + timedelta(minutes=minutes))


@when(parsers.parse("un passage de « {name} » est publié sur les sorties"))
def publish(context: Context, empty_database: Connection, name: str) -> None:
	assert context.outputs is not None
	identifier = sound_of(empty_database, context, name)
	play = Play(uuid.uuid4(), identifier, None, None, None, INSTANT)
	empty_database.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, location, title)"
		" VALUES (%s, 'start', %s, %s, %s, %s)",
		(play.id, INSTANT, identifier, str(directory(context) / name), name),
	)
	empty_database.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, location, title, played_duration,"
		" without_incident) VALUES (%s, 'end', %s, %s, %s, %s, '1 s', true)",
		(play.id, INSTANT, identifier, str(directory(context) / name), name),
	)
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		context.outputs.started_play(connection, play)
		context.outputs.finished_play(connection, play, INSTANT)


@when(parsers.parse("la socket d'état est ouverte sur le fichier sonore « {name} »"))
def open_socket(context: Context, name: str) -> None:
	try:
		StateSocket(directory(context) / name).open_()
	except OSError as error:
		context.error = error


@when(parsers.parse("une simulation est exportée sous le nom « {name} », dans le répertoire de la banque"))
def export_in_bank(context: Context, name: str) -> None:
	export([], [], directory(context), name, INSTANT, INSTANT.replace(hour=21))


# ─── Alors ─────────────────────────────────────────────────


@then("les fichiers sonores de la banque sont intacts")
def intact_list(context: Context) -> None:
	after = read_off(directory(context))
	for path, reading in context.reading.items():
		assert after.get(path) == reading, f"{path} a changé ou disparu"


@then(parsers.parse("le fichier « {name} » a de nouveau un sonore, à l'état « {state} »"))
def reindexed(context: Context, empty_database: Connection, name: str, state: str) -> None:
	line = empty_database.execute(
		"SELECT state::text FROM sounds WHERE id = %s", (sound_of(empty_database, context, name),)
	).fetchone()
	assert line == (state,)


@then(parsers.parse("le sonore de « {name} » est à l'état « {state} »"))
def sound_state(context: Context, empty_database: Connection, name: str, state: str) -> None:
	line = empty_database.execute(
		"SELECT state::text FROM sounds WHERE id = %s", (sound_of(empty_database, context, name),)
	).fetchone()
	assert line == (state,)


@then(parsers.parse("l'airplay montre {count:d} passages"))
def play_count(empty_database: Connection, count: int) -> None:
	assert empty_database.execute("SELECT count(*) FROM airplay WHERE line_type = 'start'").fetchone() == (count,)


@then(parsers.parse("le log contient 1 alerte « {kind} », qui mentionne « {mention} »"))
def warning(empty_database: Connection, kind: str, mention: str) -> None:
	lines = empty_database.execute("SELECT level::text, message FROM log WHERE kind = %s", (stored(kind),)).fetchall()
	assert (len(lines) >= 1) and (all((n == "warning") and (mention in shown(m)) for n, m in lines)), lines


@then("l'ouverture est refusée, car c'est un fichier sonore protégé")
def refused_socket(context: Context) -> None:
	assert isinstance(context.error, ProtectedSoundFile), repr(context.error)


@then(
	parsers.parse(
		"chaque suppression, renommage ou remplacement de fichier de src, bin et install.sh porte la justification"
		" « {marks} »"
	)
)
def justified_code(marks: str) -> None:
	files = [*sorted((ROOT / "src").rglob("*.py")), ROOT / "bin" / "Machin", ROOT / "install.sh"]
	faults = [
		f"{path.relative_to(ROOT)}:{number} : {line.strip()}"
		for path in files
		for number, line in unjustified(path.read_text(encoding="utf-8"), path.suffix != ".py")
	]
	assert not faults, "suppressions sans « " + marks + " » :\n" + "\n".join(faults)


@then(parsers.re(r"le garde-fou (?P<verdict>refuse|accepte) ce code"))
def keeps_crazy(context: Context, verdict: str) -> None:
	bash = context.code.startswith(("rm ", "mv "))
	found_list = unjustified(context.code, bash)
	assert bool(found_list) is (verdict == "refuse"), found_list


@then(parsers.parse("le sonore de « {name} » a un début et une fin détectés"))
def detected_silences(context: Context, empty_database: Connection, name: str) -> None:
	"""https://github.com/dascritch/machincast/issues/146"""
	line = empty_database.execute(
		"SELECT detected_start, detected_end FROM sounds WHERE id = %s", (sound_of(empty_database, context, name),)
	).fetchone()
	assert (line is not None) and (all(isinstance(value, timedelta) for value in line)), line
