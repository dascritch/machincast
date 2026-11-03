"""Étapes des scénarios de la langue des messages (https://github.com/dascritch/machincast/issues/360)."""

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

from pytest_bdd import given, parsers, scenarios, then, when

from machincast import catalog, i18n

scenarios("language.feature")

LANGUAGE_VARIABLES = ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")


@dataclass
class Context:
	variables: dict[str, str] = field(default_factory=dict)
	process: subprocess.CompletedProcess[str] | None = None


def _variables(text: str) -> dict[str, str]:
	"""« LC_ALL=fr_CA.UTF-8 LANG=en_US.UTF-8 » : les variables de langue d'une session."""
	return dict(pair.split("=", 1) for pair in text.split())


def _session(text: str) -> dict[str, str]:
	"""L'environnement d'un programme lancé dans cette session : celui des scénarios, sans leurs variables de langue."""
	environment = {key: value for key, value in os.environ.items() if key not in LANGUAGE_VARIABLES}
	environment.update(_variables(text))
	return environment


@given(parsers.re("les variables de langue « (?P<variables>.*) »"), target_fixture="context")
def language_variables(variables: str) -> Context:
	return Context(variables=_variables(variables))


@then(parsers.parse("la langue des messages est « {code} »"))
def language_is(context: Context, code: str) -> None:
	assert i18n.language(context.variables) == code, context.variables


@when(parsers.parse("je demande l'aide de Machin_player dans une session « {variables} »"), target_fixture="context")
def player_help(variables: str) -> Context:
	process = subprocess.run(
		[sys.executable, "-m", "machincast.player", "--help"],
		capture_output=True,
		text=True,
		timeout=60,
		env=_session(variables),
	)
	return Context(process=process)


@then(parsers.parse("l'aide commence par « {start} »"))
def help_starts(context: Context, start: str) -> None:
	assert context.process is not None
	assert context.process.returncode == 0, context.process.stderr
	description = context.process.stdout.split("\n\n", 1)[1]
	assert " ".join(description.split()).startswith(start), context.process.stdout


@when(
	parsers.parse("j'ouvre les préférences de l'interface dans une session « {variables} »"),
	target_fixture="context",
)
def open_preferences(variables: str) -> Context:
	program = (
		"from PySide6.QtWidgets import QDialog\n"
		"from machincast.interface.application import application\n"
		"from machincast.interface.ui.preferences import Ui_PreferencesWindow\n"
		"application('essai')\n"
		"window = QDialog()\n"
		"Ui_PreferencesWindow().setupUi(window)\n"
		"print(window.windowTitle())\n"
	)
	environment = _session(variables) | {"QT_QPA_PLATFORM": "offscreen"}
	process = subprocess.run(
		[sys.executable, "-c", program], capture_output=True, text=True, timeout=60, env=environment
	)
	return Context(process=process)


@then(parsers.parse("leur titre est « {title} »"))
def preferences_title(context: Context, title: str) -> None:
	assert context.process is not None
	assert context.process.stdout.strip() == title, (context.process.stdout, context.process.stderr)


@then(parsers.re("le message « (?P<message>.*) » du log s'affiche « (?P<shown>.*) »"))
def logged_message(message: str, shown: str) -> None:
	assert i18n.current() == "fr"
	assert i18n.logged(message) == shown


@when("je vérifie les catalogues de traduction", target_fixture="context")
def check_catalogues() -> Context:
	process = subprocess.run(
		[sys.executable, "-m", "machincast.catalog", "--check"], capture_output=True, text=True, timeout=120
	)
	return Context(process=process)


@then("la vérification réussit")
def check_succeeds(context: Context) -> None:
	assert context.process is not None
	assert context.process.returncode == 0, context.process.stderr


@then("chaque traduction garde les champs de son message")
def same_fields() -> None:
	"""Une traduction qui perdrait, ajouterait ou renommerait un champ {nom} ferait échouer son str.format."""
	fields = re.compile(r"(?<!\{)\{([A-Za-z_]\w*)")
	messages = catalog.extract()
	for code in i18n.LANGUAGES:
		if code == i18n.SOURCE:
			continue
		translations = i18n.read_catalog(i18n.catalog_file(code).read_text(encoding="utf-8"))
		for key, message in messages.items():
			translated = translations[key]
			forms = translated if isinstance(translated, tuple) else (translated,)
			for form in forms:
				assert set(fields.findall(form)) == set(fields.findall(message.msgid)), (code, message.msgid, form)
