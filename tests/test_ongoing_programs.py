"""Scénarios des programmes de MachinCast en cours pendant l'installation
(https://github.com/dascritch/machincast/issues/254).

Le /proc factice du scénario a, pour chaque processus, sa ligne de commande (les mots de la colonne « commande »),
son propriétaire, son groupe de contrôle et son répertoire. Les comptes « radio » et « xavier » y ont les uid 5001 et
5002. La relance n'ouvre rien : elle note ce qu'elle lancerait.
"""

import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import programs
from machincast.programs import Program
from tests.categories import inverted

scenarios("ongoing_programs.feature")

COUNTS = {"radio": 5001, "xavier": 5002}
NAMES = inverted(COUNTS)
SRC = Path(__file__).parent.parent / "src"


@dataclass
class Station:
	proc: Path
	state: Path
	environment: dict[str, str] = field(default_factory=dict)
	terminals: tuple[str, ...] = ()
	list_: str = ""
	launched_list: list[tuple[str, str]] = field(default_factory=list)
	"""Les commandes relancées, et leur répertoire."""
	messages: list[str] = field(default_factory=list)


@pytest.fixture
def station(tmp_path: Path) -> Station:
	proc = tmp_path / "proc"
	proc.mkdir()
	return Station(proc, tmp_path / "programmes.json")


def account(uid: int) -> str:
	return NAMES[uid]


def table(datatable: list[list[str]]) -> list[dict[str, str]]:
	headers, *rows = datatable
	table = []
	for row in rows:
		keys = []
		for header in headers:
			keys.append(header.strip())
		cells = []
		for v in row:
			cells.append(v.strip())
		table.append(dict(zip(keys, cells, strict=True)))
	return table


def readable(command: list[str]) -> str:
	"""bin/Machin s'écrit « Machin »."""
	word_list = []
	for word in command:
		shown = word
		if word == str(programs.MACHIN):
			shown = "Machin"
		word_list.append(shown)
	return " ".join(word_list)


# ─── Étant donné ───────────────────────────────────────────


@given("les processus :")
def process(station: Station, datatable: list[list[str]]) -> None:
	for row in table(datatable):
		folder = station.proc / row["pid"]
		folder.mkdir()
		word_list = []
		for word in row["commande"].split():
			word_list.append(f"{word}\0")
		folder.joinpath("cmdline").write_bytes("".join(word_list).encode())
		uid = COUNTS[row["compte"]]
		folder.joinpath("status").write_text(f"Name:\tpython3\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n")
		folder.joinpath("cgroup").write_text(f"{row['cgroup']}\n")
		folder.joinpath("cwd").symlink_to((row.get("répertoire")) or ("/"))


@given(parsers.parse("le processus {pid:d} sans ligne de commande, comme un fil du noyau"))
def kernel_feed(station: Station, pid: int) -> None:
	folder = station.proc / str(pid)
	folder.mkdir()
	folder.joinpath("cmdline").write_bytes(b"")
	folder.joinpath("status").write_text("Name:\tkthreadd\nUid:\t0\t0\t0\t0\n")


@given(parsers.parse("le processus {pid:d} disparu pendant la lecture"))
def disappeared(station: Station, pid: int) -> None:
	"""Son dossier est là, mais plus ses fichiers."""
	(station.proc / str(pid)).mkdir()


@given(parsers.parse("le répertoire du processus {pid:d} illisible"))
def unreadable_directory(station: Station, pid: int) -> Iterator[None]:
	"""Comme pour un autre compte : le lien cwd ne se lit pas. Ses droits reviennent à la fin du scénario : sans eux,
	pytest ne peut pas effacer le répertoire temporaire d'un compte qui n'est pas root."""
	link = station.proc / str(pid) / "cwd"
	link.unlink()
	link.mkdir(mode=0)
	yield
	link.chmod(0o700)


@given(parsers.parse("une session graphique, avec le terminal « {terminal} »"))
def graphic_session(station: Station, terminal: str) -> None:
	station.environment = {"DISPLAY": ":0"}
	station.terminals = (terminal,)


@given("aucune session graphique, ni terminal")
def without_session(station: Station) -> None:
	station.environment = {}
	station.terminals = ()


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("install.sh demande la liste des programmes en cours, sous le compte « {name} »"))
def ask_list(station: Station, name: str) -> None:
	found_list = programs.ongoing(station.proc, account)
	programs.save(found_list, station.state)
	station.list_ = programs.list_items(found_list, name)


@when(
	parsers.re(
		r"install\.sh (?P<simulated>relance les|simule la relance des) programmes arrêtés,"
		r" sous le compte « (?P<name>[^»]+) »"
	)
)
def restart(station: Station, simulated: str, name: str) -> None:
	def launch(command: list[str], directory: str) -> None:
		station.launched_list.append((readable(command), directory))

	def find(terminal: str) -> str | None:
		if terminal in station.terminals:
			return terminal
		return None

	station.messages = programs.restart(
		programs.reread(station.state),
		name,
		station.environment,
		launch=launch,
		find=find,
		simulation=simulated != "relance les",
	)


# ─── Alors ─────────────────────────────────────────────────


def describe(program: Program) -> dict[str, str]:
	return {
		"pid": str(program.pid),
		"compte": program.account,
		"programme": program.name,
		"nature": program.kind,
		"arguments": " ".join(program.arguments),
	}


@then("les programmes en cours sont :")
def ongoing(station: Station, datatable: list[list[str]]) -> None:
	found_list = []
	for program in programs.ongoing(station.proc, account):
		found_list.append(describe(program))
	assert found_list == table(datatable)


@then("aucun programme n'est en cours")
def no(station: Station) -> None:
	assert programs.ongoing(station.proc, account) == []


@then("la liste pour install.sh est :")
def list_for_install(station: Station, datatable: list[list[str]]) -> None:
	expected_list = []
	for row in table(datatable):
		expected_list.append("\t".join(row.values()))
	assert station.list_.splitlines() == expected_list


@then("l'état des programmes arrêtés est enregistré")
def saved_state(station: Station) -> None:
	assert programs.reread(station.state) == programs.ongoing(station.proc, account)


@then("les programmes relancés sont :")
def restarted_list(station: Station, datatable: list[list[str]]) -> None:
	expected_list = []
	for row in table(datatable):
		expected_list.append((row["commande"], row["répertoire"]))
	assert station.launched_list == expected_list


@then("aucun programme n'est relancé")
def no_restarted(station: Station) -> None:
	assert station.launched_list == []


@then("la relance dit :")
def restarts_says(station: Station, datatable: list[list[str]]) -> None:
	row_list = []
	for row in table(datatable):
		row_list.append(row["message"])
	assert station.messages == row_list


@then("machincast.programs liste les programmes en cours avec un Python sans paquet installé")
def without_venv(tmp_path: Path) -> None:
	"""-S : sans site-packages, ni ceux du venv ; seules les sources de MachinCast sont sur le chemin."""
	result = subprocess.run(
		[sys.executable, "-S", "-m", "machincast.programs", "list", "--state", str(tmp_path / "etat.json")],
		env={**os.environ, "PYTHONPATH": str(SRC)},
		capture_output=True,
		text=True,
		check=False,
	)
	assert result.returncode == 0, result.stderr
	assert (tmp_path / "etat.json").exists()
