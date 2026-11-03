"""Scénarios de la fiche d'un sonore (https://github.com/dascritch/machincast/issues/28).

Les étapes de la fenêtre, des listes et des fiches sont dans tests/interface_steps.py ; le serveur de flux local, dans
tests/broadcast_steps.py. Celles-ci manipulent la fiche d'un sonore et lisent la base de test.
"""

import json
import os
import re
import socket
import subprocess
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from PySide6.QtCore import QDateTime, QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QAbstractButton, QApplication, QComboBox, QMenu, QRadioButton
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import sound_card, stream_trial
from machincast.interface.sound_card import SoundCard
from tests.interface_steps import NAME, Connection, Context, identifier, open_in, type_, window
from tests.stream import StreamServer

scenarios("sound_card.feature")

SPACE = "⎵"
"""Une espace dans une cellule de tableau, que Gherkin rognerait."""
RETURN = "⏎"
"""Un retour à la ligne dans un texte attendu."""
DATE = "dd/MM/yyyy HH:mm"


def card(interface: Context) -> SoundCard:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, SoundCard), opened
	return opened


def id_sound(database: Connection, name: str) -> int:
	"""Un sonore par son titre ; sans titre, par le nom de son fichier, ou l'adresse de son stream ou de son
	feed."""
	lines = database.execute(
		"SELECT s.id FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.title = %s"
		" OR (s.title IS NULL AND (s.location LIKE '%%/' || %s OR s.stream_url = %s OR m.url = %s))",
		(name, name, name, name),
	).fetchall()
	assert len(lines) == 1, f"« {name} » : {lines}"
	return int(str(lines[0][0]))


def paris_hour(text: str) -> datetime:
	return datetime.fromisoformat(text).astimezone()


def choose_text(choice: QComboBox, text: str) -> None:
	index = choice.findText(text, Qt.MatchFlag.MatchFixedString)
	assert index >= 0, f"« {text} » absent : {[choice.itemText(i) for i in range(choice.count())]}"
	choice.setCurrentIndex(index)


def texts(choice: QComboBox) -> list[str]:
	return [choice.itemText(index).casefold() for index in range(choice.count())]


def if_ticked(box: QAbstractButton, read: Callable[[], str]) -> Callable[[], str]:
	"""Ce que montre un champ qui ne compte que si sa case est cochée : rien sinon."""

	def playback() -> str:
		if not box.isChecked():
			return ""
		return read()

	return playback


def shows(sound: SoundCard) -> dict[str, Callable[[], str]]:
	"""Ce que la fiche montre, par nom de champ à l'écran."""
	ui = sound.ui

	return {
		"Type": ui.sound_type.text,
		"Emplacement": ui.location.text,
		"Durée": ui.duration.text,
		"État": lambda: ui.state.currentText().casefold(),
		"Artiste": ui.artist.text,
		"Titre": ui.title.text,
		"Année": ui.year.text,
		"Album": ui.album.text,
		"Artiste de l'album": ui.album_artist.text,
		"Genre": ui.genre.text,
		"Compositeur": ui.composer.text,
		"Label": ui.label.text,
		"Piste": ui.track.text,
		"Crossfade de début": if_ticked(ui.has_start_crossfade, ui.start_crossfade.text),
		"Crossfade de fin": if_ticked(ui.has_end_crossfade, ui.end_crossfade.text),
		"Maximum de lectures": ui.playback_max.text,
		"Détection de silence": lambda: "oui" if ui.detection_silences.isChecked() else "non",
		"Début détecté": if_ticked(ui.has_detected_start, ui.detected_start.text),
		"Fin détectée": if_ticked(ui.has_detected_end, ui.detected_end.text),
		# Saisis à la main, ils s'appellent « Début » et « Fin » (https://github.com/dascritch/machincast/issues/330).
		"Début": if_ticked(ui.has_detected_start, ui.detected_start.text),
		"Fin": if_ticked(ui.has_detected_end, ui.detected_end.text),
		"Artiste et titre": lambda: ui.hiding.currentText().casefold(),
		"Diffusion à partir du": if_ticked(ui.has_start, ui.broadcast_start.text),
		"Diffusion jusqu'au": if_ticked(ui.has_end, ui.broadcast_end.text),
		"Adresse directe": if_ticked(ui.by_address, ui.url_stream.text),
		"Feed": if_ticked(ui.by_feed, ui.feed.currentText),
		"Événement de secours": lambda: ui.fallback.currentText().casefold(),
	}


@pytest.fixture
def silent_server() -> Iterator[str]:
	"""Un serveur qui accepte les connexions sans jamais rien répondre ; son adresse."""
	listening = socket.socket()
	listening.bind(("127.0.0.1", 0))
	listening.listen()
	yield f"http://127.0.0.1:{listening.getsockname()[1]}/muet"
	listening.close()


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le sonore « {name} » a en base :"))
def sound_in_database(empty_database: Connection, name: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	sound_identifier = id_sound(empty_database, name)
	for field, text in ((field.strip(), text.strip()) for field, text in rows):
		value: object = text
		if field in ("broadcast_start", "broadcast_end", "checked_at"):
			value = paris_hour(text)
		query = f"UPDATE sounds SET {field} = %s WHERE id = %s"
		empty_database.execute(query, (value, sound_identifier))


@given(parsers.parse("le feed « {name} » à l'adresse du flux « {stream} » du serveur local"))
def feed_local(server: StreamServer, empty_database: Connection, name: str, stream: str) -> None:
	empty_database.execute("INSERT INTO feeds (name, url) VALUES (%s, %s)", (name, server.address(stream)))


@given(parsers.parse("le stream « {name} » est sur le feed « {marks} »"))
def on_feed(empty_database: Connection, name: str, marks: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET stream_url = NULL, feed_id = %s WHERE id = %s",
		(identifier(empty_database, "feeds", "name", marks), id_sound(empty_database, name)),
	)


@given("un serveur qui accepte les connexions sans jamais répondre")
def silent(silent_server: str) -> None:
	"""Le serveur est ouvert par le fixture."""


@given(parsers.parse("un test de flux limité à {seconds:d} seconde"))
def short_delay(monkeypatch: pytest.MonkeyPatch, seconds: int) -> None:
	monkeypatch.setattr(stream_trial, "DELAY", timedelta(seconds=seconds))


def play(
	database: Connection,
	sound: int,
	start: datetime,
	end: datetime | None,
	references: tuple[int | None, int | None, int | None] = (None, None, None),
	without_incident: bool | None = None,
) -> None:
	event, sequence, bank = references
	number = uuid.uuid4()
	columns = "play_id, line_type, logged_at, sound_id, event_id, sequence_id, bank_id"
	database.execute(
		f"INSERT INTO airplay ({columns}) VALUES (%s, 'start', %s, %s, %s, %s, %s)",  # noqa: S608
		(number, start, sound, event, sequence, bank),
	)
	if end is not None:
		database.execute(
			f"INSERT INTO airplay ({columns}, played_duration, without_incident)"  # noqa: S608
			" VALUES (%s, 'end', %s, %s, %s, %s, %s, %s, %s)",
			(number, end, sound, event, sequence, bank, end - start, without_incident),
		)


def reference(database: Connection, table: str, name: str) -> int | None:
	if name == "":
		return None
	return identifier(database, table, "internal_name", name)


@given("les passages de sonores :")
def plays(empty_database: Connection, datatable: list[list[str]]) -> None:
	headers, *rows = datatable
	for values in rows:
		line = dict(zip(headers, (value.strip() for value in values), strict=True))
		end = None
		if line["ends_at"] != "":
			end = paris_hour(line["ends_at"])
		without_incident = {"oui": True, "non": False, "": None}[line["without_incident"]]
		references = (
			reference(empty_database, "events", line["event"]),
			reference(empty_database, "sequences", line["sequence"]),
			reference(empty_database, "banks", line["bank"]),
		)
		start = paris_hour(line["starts_at"])
		play(empty_database, id_sound(empty_database, line["sound"]), start, end, references, without_incident)


@given("le log :")
def log(empty_database: Connection, datatable: list[list[str]]) -> None:
	headers, *rows = datatable
	for values in rows:
		line = dict(zip(headers, (value.strip() for value in values), strict=True))
		empty_database.execute(
			"INSERT INTO log (logged_at, level, kind, message, sound_id) VALUES (%s, %s, %s, %s, %s)",
			(
				paris_hour(line["logged_at"]),
				line["level"],
				line["kind"],
				line["message"],
				id_sound(empty_database, line["sound"]),
			),
		)


@given(
	parsers.parse("le sonore « {name} » est passé {times:d} fois, toutes les {minutes:d} minutes depuis « {start} »")
)
def regular_plays(empty_database: Connection, name: str, times: int, minutes: int, start: str) -> None:
	sound = id_sound(empty_database, name)
	for rank in range(times):
		begins = paris_hour(start) + timedelta(minutes=minutes * rank)
		play(empty_database, sound, begins, begins + timedelta(minutes=1), without_incident=True)


def click_choice(qtbot: QtBot, choice: QRadioButton) -> None:
	"""Clique sur le rond du choix : au-delà de son libellé, la largeur de sa colonne ne répond pas au clic."""
	qtbot.mouseClick(choice, Qt.MouseButton.LeftButton, pos=QPoint(choice.height() // 2, choice.height() // 2))


# ─── Quand ─────────────────────────────────────────────────


@when("je saisis dans la fiche du sonore :")
def enter(interface: Context, qtbot: QtBot, datatable: list[list[str]]) -> None:
	ui = card(interface).ui
	free_texts = {
		"Artiste": ui.artist,
		"Titre": ui.title,
		"Année": ui.year,
		"Album": ui.album,
		"Artiste de l'album": ui.album_artist,
		"Genre": ui.genre,
		"Compositeur": ui.composer,
		"Label": ui.label,
		"Piste": ui.track,
	}
	lists = {"Artiste et titre": ui.hiding, "État": ui.state, "Événement de secours": ui.fallback}
	dates = {
		"Diffusion à partir du": (ui.has_start, ui.broadcast_start),
		"Diffusion jusqu'au": (ui.has_end, ui.broadcast_end),
	}
	_headers, *rows = datatable
	for field, raw in ((field.strip(), raw.strip().replace(SPACE, " ")) for field, raw in rows):
		if field in free_texts:
			type_(qtbot, free_texts[field], raw)
		elif field in lists:
			choose_text(lists[field], raw)
		elif field in dates:
			box, date = dates[field]
			box.setChecked(raw != "")
			if raw != "":
				date.setDateTime(QDateTime.fromString(raw, DATE))
		elif field in ("Crossfade de début", "Crossfade de fin"):
			# Un crossfade vide n'est pas paramétré (https://github.com/dascritch/machincast/issues/145).
			box, count = {
				"Crossfade de début": (ui.has_start_crossfade, ui.start_crossfade),
				"Crossfade de fin": (ui.has_end_crossfade, ui.end_crossfade),
			}[field]
			box.setChecked(raw != "")
			if raw != "":
				count.setValue(float(raw.replace(",", ".")))
		elif field == "Maximum de lectures":
			ui.playback_max.setValue(int(raw))
		elif field == "Détection de silence":
			ui.detection_silences.setChecked(raw == "oui")
		elif field in ("Début détecté", "Fin détectée"):
			# Un silence vide n'est pas détecté (https://github.com/dascritch/machincast/issues/146).
			box, count = {
				"Début détecté": (ui.has_detected_start, ui.detected_start),
				"Fin détectée": (ui.has_detected_end, ui.detected_end),
			}[field]
			box.setChecked(raw != "")
			if raw != "":
				count.setValue(float(raw.replace(",", ".")))
		elif field == "Adresse directe":
			click_choice(qtbot, ui.by_address)
			type_(qtbot, ui.url_stream, raw)
		else:
			assert field == "Feed", field
			click_choice(qtbot, ui.by_feed)
			choose_text(ui.feed, raw)


@when(parsers.parse("je coche « {box} » dans la fiche du sonore"))
def tick(interface: Context, qtbot: QtBot, box: str) -> None:
	ui = card(interface).ui
	boxes = {ui.has_start.text(): ui.has_start, ui.has_end.text(): ui.has_end}
	qtbot.mouseClick(boxes[box], Qt.MouseButton.LeftButton)


@when(parsers.parse("l'indexation change le titre de « {name} » en « {title} », et son album en « {album} »"))
def indexer(empty_database: Connection, name: str, title: str, album: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET title = %s, music_metadata = music_metadata || %s::jsonb WHERE id = %s",
		(title, json.dumps({"album": album}), id_sound(empty_database, name)),
	)


@when(parsers.parse("la diffusion passe « {name} » à l'état « {state} »"))
def broadcast(empty_database: Connection, name: str, state: str) -> None:
	empty_database.execute("UPDATE sounds SET state = %s WHERE id = %s", (state, id_sound(empty_database, name)))


@when(parsers.parse("je saisis l'adresse du flux « {stream} » du serveur local dans la fiche du sonore"))
def local_address(interface: Context, qtbot: QtBot, server: StreamServer, stream: str) -> None:
	ui = card(interface).ui
	click_choice(qtbot, ui.by_address)
	type_(qtbot, ui.url_stream, server.address(stream))


@when("je saisis l'adresse du serveur muet dans la fiche du sonore")
def silent_address(interface: Context, qtbot: QtBot, silent_server: str) -> None:
	type_(qtbot, card(interface).ui.url_stream, silent_server)


@when("je choisis l'adresse directe dans la fiche du sonore")
def choose_address(interface: Context, qtbot: QtBot) -> None:
	click_choice(qtbot, card(interface).ui.by_address)


@when(parsers.parse("le flux « {stream} » du serveur local est avare"))
def sparing(server: StreamServer, stream: str) -> None:
	server.sparing_list.add(stream)
	server.in_line[stream] = True


@when(parsers.parse("le serveur de flux local a bientôt {count:d} connexion"))
@then(parsers.parse("le serveur de flux local a bientôt {count:d} connexion"))
def connections(server: StreamServer, qtbot: QtBot, count: int) -> None:
	qtbot.waitUntil(lambda: server.connections == count, timeout=5000)


@then("le serveur de flux local n'a bientôt plus de connexion")
def more_connection(server: StreamServer, qtbot: QtBot) -> None:
	# Moins que le délai du test d'un flux, qui fermerait de lui-même sa connexion.
	qtbot.waitUntil(lambda: server.connections == 0, timeout=5000)


@when("je teste le flux")
def launch_trial(interface: Context, qtbot: QtBot) -> None:
	qtbot.mouseClick(card(interface).ui.test, Qt.MouseButton.LeftButton)


# ─── Alors ─────────────────────────────────────────────────


@then("la fiche du sonore montre :")
def shown_list(interface: Context, datatable: list[list[str]]) -> None:
	playback = shows(card(interface))
	_headers, *rows = datatable
	expected_list = [(field.strip(), value.strip()) for field, value in rows]
	assert [(field, playback[field]()) for field, _value in expected_list] == expected_list


@then(parsers.parse("la fiche du sonore montre les autres métadonnées « {text} »"))
def others(interface: Context, text: str) -> None:
	assert card(interface).ui.other_metadata.text() == text


@then(parsers.re(r"la fiche du sonore montre les champs saisis à la main (?P<fields>.+)"))
def shown_fields(interface: Context, fields: str) -> None:
	expected = f"Saisis à la main, que l'indexeur ne modifie plus : {', '.join(NAME.findall(fields))}."
	assert card(interface).ui.edited_fields.text() == expected


@then("l'emplacement de la fiche du sonore ne se modifie pas")
def fixed_location(interface: Context) -> None:
	assert card(interface).ui.location.isReadOnly()


@then("la fiche du sonore n'a pas de réglages de stream")
def without_stream(interface: Context) -> None:
	ui = card(interface).ui
	assert (ui.stream_group.isHidden(), ui.location.isHidden()) == (True, False)


@then("la fiche du sonore n'a pas de détection de silence")
def without_detection(interface: Context) -> None:
	"""Un stream n'a pas de silences détectés (https://github.com/dascritch/machincast/issues/146)."""
	assert card(interface).ui.silence_group.isHidden()


@then("la fiche du sonore n'a pas d'emplacement")
def without_location(interface: Context) -> None:
	ui = card(interface).ui
	assert (ui.stream_group.isHidden(), ui.location.isHidden()) == (False, True)


@then(
	parsers.re(
		r"le sonore « (?P<name>[^»]+) » est en base, (?P<what>d'artiste « [^»]+ »|sans artiste|sans artiste ni titre)"
	)
)
def artist_in_database(empty_database: Connection, name: str, what: str) -> None:
	line = empty_database.execute(
		"SELECT artist, title FROM sounds WHERE id = %s", (id_sound(empty_database, name),)
	).fetchone()
	assert line is not None
	artist, title = line
	expected = (None, name)
	if what.startswith("d'artiste"):
		expected = (NAME.findall(what)[0], name)
	if what == "sans artiste ni titre":
		expected = (None, None)
	assert (artist, title) == expected


@then(parsers.re(r"les métadonnées musicales de « (?P<name>[^»]+) » sont (?P<text>\{.*\})"))
def metadata(empty_database: Connection, name: str, text: str) -> None:
	line = empty_database.execute(
		"SELECT music_metadata FROM sounds WHERE id = %s", (id_sound(empty_database, name),)
	).fetchone()
	assert line is not None
	assert line[0] == json.loads(text)


@then(parsers.re(r"les champs saisis à la main de « (?P<name>[^»]+) » sont (?P<fields>.+)"))
def fields_in_database(empty_database: Connection, name: str, fields: str) -> None:
	line = empty_database.execute(
		"SELECT edited_fields FROM sounds WHERE id = %s", (id_sound(empty_database, name),)
	).fetchone()
	assert line is not None
	assert line[0] == NAME.findall(fields)


@then(parsers.parse("le sonore « {name} » a en base :"))
def columns_in_database(empty_database: Connection, name: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	expected_list = [(field.strip(), value.strip()) for field, value in rows]
	sound_identifier = id_sound(empty_database, name)
	fetched_list = []
	for field, _value in expected_list:
		line = empty_database.execute(f"SELECT {field} FROM sounds WHERE id = %s", (sound_identifier,)).fetchone()
		assert line is not None
		value = line[0]
		if isinstance(value, datetime):
			value = value.astimezone()
		fetched_list.append((field, str(value)))
	assert fetched_list == expected_list


@then(parsers.re(r"l'état de la fiche du sonore se choisit parmi (?P<states>.+)"))
def states(interface: Context, states: str) -> None:
	"""L'état du sonore, puis ceux que l'interface peut poser : les autres sont grisés
	(https://github.com/dascritch/machincast/issues/223)."""
	choice = card(interface).ui.state
	model = choice.model()
	possible = [
		choice.itemText(rank).casefold()
		for rank in range(choice.count())
		if (rank != choice.currentIndex()) and (model.flags(model.index(rank, 0)) & Qt.ItemFlag.ItemIsEnabled)
	]
	expected_list = NAME.findall(states)
	obtained_list = [choice.currentText().casefold(), *possible]
	assert (obtained_list, choice.isEnabled()) == (expected_list, len(expected_list) > 1)


@then(parsers.re(r"les feeds proposés sont (?P<names>.+)"))
def offered_marks(interface: Context, names: str) -> None:
	assert texts(card(interface).ui.feed) == [name.casefold() for name in NAME.findall(names)]


@then(parsers.re(r"les événements de secours proposés sont (?P<names>.+)"))
def offered_fallback(interface: Context, names: str) -> None:
	assert texts(card(interface).ui.fallback) == [name.casefold() for name in NAME.findall(names)]


@then(
	parsers.re(
		r"le stream « (?P<name>[^»]+) » est en base,"
		r" (?:sur le feed « (?P<marks>[^»]+) »|à l'adresse « (?P<url>[^»]+) »),"
		r" (?:sans adresse directe|sans feed),"
		r" (?:secouru par « (?P<fallback>[^»]+) »|sans événement de secours)"
	)
)
def stream_in_database(
	empty_database: Connection, name: str, marks: str | None, url: str | None, fallback: str | None
) -> None:
	line = empty_database.execute(
		"SELECT s.stream_url, m.name, e.internal_name FROM sounds s"
		" LEFT JOIN feeds m ON m.id = s.feed_id"
		" LEFT JOIN events e ON e.id = s.fallback_event_id WHERE s.id = %s",
		(id_sound(empty_database, name),),
	).fetchone()
	assert line == (url, marks, fallback)


@then("le choix d'un feed est inactif")
def inactive_feed(interface: Context) -> None:
	assert not card(interface).ui.by_feed.isEnabled()


@then("le test du flux est en cours")
def ongoing_trial(interface: Context) -> None:
	ui = card(interface).ui
	assert (ui.trial_result.text(), ui.test.isEnabled()) == ("Test du flux en cours…", False)


@then(parsers.parse("le test du flux dit bientôt « {verdict} »"))
def verdict_soon(interface: Context, qtbot: QtBot, verdict: str) -> None:
	ui = card(interface).ui
	qtbot.waitUntil(lambda: ui.trial_result.text() == verdict, timeout=15000)


@then("le test du flux dit bientôt qu'il ne répond pas, avec l'erreur du serveur")
def error_soon(interface: Context, qtbot: QtBot) -> None:
	ui = card(interface).ui
	start = "Le flux ne répond pas : "

	def error() -> bool:
		text = ui.trial_result.text()
		end = (text.endswith(".")) and (not text.endswith(".."))
		return (text.startswith(start)) and (len(text) > len(start) + 1) and ("n'arrive pas" not in text) and (end)

	qtbot.waitUntil(error, timeout=15000)


@then(parsers.parse("le test du flux dit « {verdict} »"))
def verdict(interface: Context, verdict: str) -> None:
	assert card(interface).ui.trial_result.text() == verdict


@then(parsers.parse("après {seconds:d} secondes, le test du flux dit toujours « {verdict} »"))
def always(interface: Context, qtbot: QtBot, seconds: int, verdict: str) -> None:
	qtbot.wait(seconds * 1000)
	assert card(interface).ui.trial_result.text() == verdict


@then(parsers.re(r"les dates de diffusion qui se saisissent sont (?P<dates>.+)"))
def active_dates(interface: Context, dates: str) -> None:
	ui = card(interface).ui
	fields = {"Diffusion à partir du": ui.broadcast_start, "Diffusion jusqu'au": ui.broadcast_end}
	assert [name for name, field in fields.items() if field.isEnabled()] == NAME.findall(dates)


@then(parsers.parse("seul le champ « {name} » du stream se saisit"))
def stream_field(interface: Context, name: str) -> None:
	ui = card(interface).ui
	fields = {"Adresse directe": ui.url_stream, "Feed": ui.feed}
	assert [key for key, field in fields.items() if field.isEnabled()] == [name]


@then("la fiche du sonore ne montre aucun champ saisi à la main")
def no_field(interface: Context) -> None:
	assert card(interface).ui.edited_fields.text() == ""


@then("le flux peut de nouveau être testé")
def rerunnable_trial(interface: Context) -> None:
	ui = card(interface).ui
	assert (ui.test.isEnabled(), card(interface).trial.ongoing()) == (True, False)


@then("les derniers passages du sonore sont :")
def last_plays(interface: Context, datatable: list[list[str]]) -> None:
	table = card(interface).ui.plays
	headers, *rows = datatable
	titles = [table.horizontalHeaderItem(column).text() for column in range(table.columnCount())]
	assert titles == [header.strip() for header in headers]
	shown_list = [
		[table.item(row, column).text() for column in range(table.columnCount())] for row in range(table.rowCount())
	]
	assert shown_list == [[value.strip() for value in values] for values in rows]


@then(parsers.parse("l'infobulle des incidents du passage de « {start} » est « {text} »"))
def tooltip(interface: Context, start: str, text: str) -> None:
	table = card(interface).ui.plays
	rows = [row for row in range(table.rowCount()) if table.item(row, 0).text() == start]
	assert len(rows) == 1
	assert table.item(rows[0], table.columnCount() - 1).toolTip() == text.replace(RETURN, "\n")


@then(parsers.parse("la fiche du sonore montre {count:d} passages, du « {first} » au « {last} »"))
def play_count(interface: Context, count: int, first: str, last: str) -> None:
	table = card(interface).ui.plays
	starts = [table.item(row, 0).text() for row in range(table.rowCount())]
	assert (len(starts), starts[0], starts[-1]) == (count, first, last)


# ─── Améliorations (https://github.com/dascritch/machincast/issues/125) ─────


@given(parsers.parse("le fichier « {path} », de {bytes_:d} octets, modifié le « {instant} »"))
def date_file(interface: Context, path: str, bytes_: int, instant: str) -> None:
	file = Path(interface.path(path))
	file.parent.mkdir(parents=True, exist_ok=True)
	file.write_bytes(b"\0" * bytes_)
	timestamp = paris_hour(instant).timestamp()
	os.utime(file, (timestamp, timestamp))


@when("je clique sur le bouton du dossier du fichier")
def open_folder(interface: Context, qtbot: QtBot) -> None:
	qtbot.mouseClick(card(interface).ui.open_folder, Qt.MouseButton.LeftButton)


@when(parsers.parse("j'ouvre la relation « {name} » du sonore"))
def open_relation(interface: Context, qtbot: QtBot, name: str) -> None:
	open_in(qtbot, card(interface).ui.relations, name)


@then("les relations du sonore sont :")
def relations(interface: Context, datatable: list[list[str]]) -> None:
	table = card(interface).ui.relations
	headers, *rows = datatable
	columns = [table.horizontalHeaderItem(column).text() for column in range(table.columnCount())]
	assert columns == [header.strip() for header in headers]
	fetched_list = [
		[table.item(row, column).text() for column in range(table.columnCount())] for row in range(table.rowCount())
	]
	assert fetched_list == [[value.strip() for value in row] for row in rows]


@then(parsers.parse("la fiche du sonore dit « {text} »"))
def says(interface: Context, text: str) -> None:
	# Ce que la fiche montre, que l'encart Relations soit déplié ou non (https://github.com/dascritch/machincast/issues/190).
	assert not card(interface).ui.no_relation.isHidden()
	assert card(interface).ui.no_relation.text() == text


@then("l'encart « Fichier » de la fiche du sonore montre :")
def file_panel(interface: Context, datatable: list[list[str]]) -> None:
	"""« <création du fichier> » : la date de naissance que donne stat (format W), ou « inconnue » si le système n'en a
	pas."""
	ui = card(interface).ui
	assert ui.file_group.isVisible()
	fields = {
		"Type": ui.type_mime,
		"Encodage moyen": ui.encoding,
		"Taille": ui.size,
		"Créé le": ui.created_at,
		"Modifié le": ui.modified_at,
		"Dernière vérification complète": ui.checks_at,
	}
	_headers, *rows = datatable
	location = Path(ui.location.text())
	for field, value in ((field.strip(), value.strip()) for field, value in rows):
		if value == "<création du fichier>":
			birth = int(subprocess.run(["stat", "--format=%W", str(location)], capture_output=True, text=True).stdout)
			value = "inconnue"
			if birth > 0:
				value = f"{datetime.fromtimestamp(birth).astimezone():%Y-%m-%d %H:%M:%S}"
		assert (field, fields[field].text()) == (field, value)


@then("la fiche du sonore n'a ni encart « Fichier », ni bouton du dossier")
def without_file(interface: Context) -> None:
	ui = card(interface).ui
	assert not ui.file_group.isVisible()
	assert ui.open_folder.isHidden()


@then("la fiche du sonore ne dit pas qu'aucun élément ne le cite")
def says_not(interface: Context) -> None:
	assert card(interface).ui.no_relation.isHidden()


@given("un système de fichiers qui ne garde pas la date de création")
def without_creation_date(monkeypatch: pytest.MonkeyPatch) -> None:
	"""stat répond 0 quand le système de fichiers ne garde pas la date de naissance d'un fichier."""
	run = subprocess.run

	def stat(command: list[str], **options: object) -> subprocess.CompletedProcess[str]:
		if command[:2] == ["stat", "--format=%W"]:
			return subprocess.CompletedProcess(command, 0, "0\n", "")
		return run(command, **options)  # type: ignore[call-overload,no-any-return]

	monkeypatch.setattr(sound_card.subprocess, "run", stat)


@then("la fiche du sonore marque hors des durées les banques :")
def banks_outside_durations(interface: Context, datatable: list[list[str]]) -> None:
	"""Les banques de ses relations dont le sonore sort des durées : icône et infobulle sur leur nom
	(https://github.com/dascritch/machincast/issues/147)."""
	table = card(interface).ui.relations
	marked_list = []
	for row in range(table.rowCount()):
		name = table.item(row, 1)
		assert name is not None
		if not name.icon().isNull():
			marked_list.append([name.text(), name.toolTip()])
	_headers, *rows = datatable
	assert marked_list == [[bank.strip(), tooltip.strip()] for bank, tooltip in rows]


@then("le champ du crossfade de début de la fiche du sonore est inactif, celui de fin actif")
def crossfade_fields(interface: Context) -> None:
	ui = card(interface).ui
	assert (ui.start_crossfade.isEnabled(), ui.end_crossfade.isEnabled()) == (False, True)


# ─── Retirer une relation (https://github.com/dascritch/machincast/issues/331) ───

LISTS = {
	"la séquence": ("sequences", "sequence_items", "sequence_id"),
	"la banque": ("banks", "bank_sounds", "bank_id"),
	"l'événement": ("events", "event_items", "event_id"),
}
ITEM_OF = r"(?P<item>la séquence|la banque|l'événement) « (?P<name>[^»]+) »"


def _relation_row(interface: Context, name: str) -> int:
	table = card(interface).ui.relations
	(row,) = [row for row in range(table.rowCount()) if table.item(row, 1).text() == name]
	return row


def _relation_menu(interface: Context, name: str) -> QMenu:
	table = card(interface).ui.relations
	row = _relation_row(interface, name)
	position = table.visualItemRect(table.item(row, 1)).center()
	return card(interface).relation_columns.table_menu(position)


@when(parsers.re(r"je choisis « (?P<entry>.+) » au clic droit sur la relation « (?P<name>[^»]+) » du sonore$"))
def remove_relation(interface: Context, entry: str, name: str) -> None:
	(action,) = [action for action in _relation_menu(interface, name).actions() if action.text() == entry]
	action.trigger()


@then(parsers.re(r"le clic droit sur la relation « (?P<name>[^»]+) » du sonore propose (?P<entries>«.+)$"))
def relation_menu(interface: Context, name: str, entries: str) -> None:
	texts = []
	for action in _relation_menu(interface, name).actions():
		text = action.text()
		if action.isSeparator():
			text = "—"
		texts.append(text)
	expected_list = [entry.strip() for entry in entries.strip("« »").split(" », « ")]
	assert texts == expected_list, texts


def _quotations(database: Connection, item: str, name: str, sound: str) -> tuple[int, int]:
	"""Les places du sonore dans la liste de l'élément, et le nombre d'éléments de cette liste."""
	table, list_, column = LISTS[item]
	parent = identifier(database, table, "internal_name", name)
	cites = identifier(database, "sounds", "title", sound)
	line = database.execute(
		f"SELECT count(*) FILTER (WHERE sound_id = %s), count(*) FROM {list_} WHERE {column} = %s",  # noqa: S608
		(cites, parent),
	).fetchone()
	assert line is not None
	return int(line[0]), int(line[1])


@then(parsers.re(rf"en base, {ITEM_OF} cite encore le sonore « (?P<sound>[^»]+) »"))
def cites_still(empty_database: Connection, item: str, name: str, sound: str) -> None:
	assert _quotations(empty_database, item, name, sound)[0] > 0


@then(
	parsers.re(rf"en base, {ITEM_OF} ne cite plus le sonore « (?P<sound>[^»]+) », mais garde (?P<count>\d+) éléments?")
)
def cites_more(empty_database: Connection, item: str, name: str, sound: str, count: str) -> None:
	assert _quotations(empty_database, item, name, sound) == (0, int(count))


# ─── Début et fin sur la frise (https://github.com/dascritch/machincast/issues/330) ───


def _seconds_fetched(text: str) -> float:
	return float(text.replace(",", "."))


@when("je décoche le début détecté de la fiche")
def untick_start(interface: Context) -> None:
	card(interface).ui.has_detected_start.setChecked(False)


@when(parsers.parse("je glisse le curseur « {name} » de la frise de la fiche à {seconds} s"))
def slide_slider(interface: Context, name: str, seconds: str) -> None:
	"""Prise sur le curseur, glissement, puis relâche à l'instant voulu, en points non arrondis."""
	timeline = card(interface).timeline
	key = {"Début": "debut", "Fin": "fin"}[name]
	departure = QPointF(timeline.seconds_to_x(timeline.sliders[key]), timeline.height() / 2)
	arrival = QPointF(timeline.seconds_to_x(_seconds_fetched(seconds)), timeline.height() / 2)
	left = Qt.MouseButton.LeftButton
	no = Qt.KeyboardModifier.NoModifier
	for category, point, buttons in (
		(QEvent.Type.MouseButtonPress, departure, left),
		(QEvent.Type.MouseMove, arrival, left),
		(QEvent.Type.MouseButtonRelease, arrival, Qt.MouseButton.NoButton),
	):
		event = QMouseEvent(category, point, timeline.mapToGlobal(point), left, buttons, no)
		QApplication.sendEvent(timeline, event)


@then(parsers.parse("les silences détectés de la fiche s'appellent « {start} » et « {end} »"))
def silence_names(interface: Context, start: str, end: str) -> None:
	ui = card(interface).ui
	assert (ui.has_detected_start.text(), ui.has_detected_end.text()) == (start, end)


@then(parsers.parse("le début détecté de la fiche va au plus à {start} s, et la fin détectée à {end} s"))
def silence_bounds(interface: Context, start: str, end: str) -> None:
	ui = card(interface).ui
	bounds = (round(ui.detected_start.maximum(), 2), round(ui.detected_end.maximum(), 2))
	assert bounds == (_seconds_fetched(start), _seconds_fetched(end)), bounds


@then(parsers.re(r"la frise de la fiche a (?:les curseurs|le seul curseur) (?P<sliders>«.+)"))
def timeline_sliders(interface: Context, sliders: str) -> None:
	expected_list = {
		{"Début": "debut", "Fin": "fin"}[name]: _seconds_fetched(value)
		for name, value in re.findall(r"« ([^»]+) » à ([\d,]+) s", sliders)
	}
	fetched_list = {name: round(position, 2) for name, position in card(interface).timeline.sliders.items()}
	assert fetched_list == expected_list, fetched_list
