"""Scénarios de l'ajout de fichiers sonores depuis la liste des sonores
(https://github.com/dascritch/machincast/issues/30).

Les étapes de la fenêtre, des listes et des fenêtres de dialogue sont dans tests/interface_steps.py. La vérification
des fichiers ajoutés décode vraiment les fichiers de test ; ses scénarios peuvent la faire attendre, ou lui retirer ses
décodeurs, en remplaçant le décodage de l'indexeur.
"""

import re
import threading
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.indexer.decoding import Check, UnavailableDecoder, check_file
from machincast.interface import check
from machincast.interface.lists import List
from tests.interface_steps import (
	WAITING,
	Connection,
	Context,
	list_,
	slide,
	tab_title,
	wait_check,
	window,
)

scenarios("adding_files.feature")


@pytest.fixture
def resumption() -> threading.Event:
	"""Ce qu'attend une vérification qui attend."""
	return threading.Event()


@dataclass
class Decodings:
	"""Décodages en cours, et le plus grand nombre qui l'ont été à la fois."""

	ongoing: int = 0
	maximum: int = 0
	lock: threading.Lock = field(default_factory=threading.Lock)


@pytest.fixture
def decodings() -> Decodings:
	return Decodings()


# ─── Étant donné ───────────────────────────────────────────


@given("une vérification des fichiers ajoutés qui attend")
def check_who_waiting(monkeypatch: pytest.MonkeyPatch, resumption: threading.Event, decodings: Decodings) -> None:
	def decode(path: Path) -> Check:
		with decodings.lock:
			decodings.ongoing += 1
			decodings.maximum = max(decodings.maximum, decodings.ongoing)
		try:
			assert resumption.wait(WAITING / 1000), "la vérification attendue n'a jamais repris"
			return check_file(path)
		finally:
			with decodings.lock:
				decodings.ongoing -= 1

	monkeypatch.setattr(check, "check_file", decode)


@given("un indexeur qui ne sait pas décoder les fichiers")
def without_decoder(monkeypatch: pytest.MonkeyPatch) -> None:
	def decode(_path: Path) -> Check:
		raise UnavailableDecoder("aucun décodeur pour ce format")

	monkeypatch.setattr(check, "check_file", decode)


# ─── Quand ─────────────────────────────────────────────────


@when(
	parsers.re(r"je dépose sur la liste des sonores (?P<what>.+?)(?P<relocation>, en ne proposant que le déplacement)?")
)
def drop_in(interface: Context, what: str, relocation: str | None) -> None:
	slide(interface, list_(interface).table, what, True, relocation is not None)


@when("la vérification attendue reprend, et se termine")
def resume(interface: Context, qtbot: QtBot, resumption: threading.Event) -> None:
	resumption.set()
	wait_check(interface, qtbot)


@when("je ferme la fenêtre de l'interface, pendant que la vérification attendue reprend")
def close_during(interface: Context, resumption: threading.Event) -> None:
	assert window(interface).checker.ongoing()
	threading.Timer(0.3, resumption.set).start()
	window(interface).close()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"la barre d'état a annoncé, dans l'ordre, (?P<texts>.+)"))
def ordinates_announcements(interface: Context, texts: str) -> None:
	expected_list = re.findall(r"« (.+?) »(?:, |$)", texts)
	final_list = []
	for announces in interface.announcements:
		if announces.startswith("Vérification"):
			final_list.append(announces)
	assert final_list == expected_list


@then("les vérifications ont décodé un fichier à la fois")
def a_has_times(decodings: Decodings) -> None:
	assert decodings.maximum == 1


@then("la vérification des fichiers ajoutés est terminée")
def finished(interface: Context) -> None:
	assert not window(interface).checker.ongoing()


@then("les sonores ajoutés sont en base :")
def in_database(interface: Context, empty_database: Connection, datatable: list[list[str]]) -> None:
	"""Les sonores dont le fichier est dans le répertoire du scénario, par emplacement ; la durée à la seconde."""
	headers, *rows = datatable
	expected_list = [dict(zip(headers, (interface.path(v.strip()) for v in values), strict=True)) for values in rows]
	fetched_list = empty_database.execute(
		"SELECT location, type::text, state::text, artist, title, duration FROM sounds"
		" WHERE location LIKE %s || '/%%' ORDER BY location",
		(str(interface.directory),),
	).fetchall()
	found_list = []
	for location, sound_type, state, artist, title, duration in fetched_list:
		if isinstance(duration, timedelta):
			duration = timedelta(seconds=round(duration.total_seconds()))
		values = (location, sound_type, state, artist, title, duration)
		header_list = []
		for header in headers:
			header_list.append(header.strip())
		v_list = []
		for v in values:
			v_list.append(str(v))
		found_list.append(dict(zip(header_list, v_list, strict=True)))
	assert found_list == sorted(expected_list, key=lambda line: line["location"])


@then(parsers.parse("seule la liste « {title} » propose « ➕ Ajouter des fichiers… » et accepte les dépôts"))
def only_list(interface: Context, title: str) -> None:
	tabs = window(interface).ui.tabs
	with_ = []
	for index in range(tabs.count()):
		opened = tabs.widget(index)
		if isinstance(opened, List):
			button = opened.ui.add_files
			if (not button.isHidden()) or (opened.table.acceptDrops()):
				assert (button.text(), opened.table.acceptDrops()) == ("➕ Ajouter des fichiers…", True)
				with_.append(tab_title(tabs, index))
	assert with_ == [title]
