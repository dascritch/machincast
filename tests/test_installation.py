"""Étapes des scénarios de vérification de l'installation (https://github.com/dascritch/machincast/issues/40)."""

import grp
import os
import pty
import pwd
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import dukpy
import gi
import pytest
import tomlkit
from PySide6.QtGui import QColor, QIcon, QImage
from PySide6.QtWidgets import QApplication
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import access, installation, power_save, service
from machincast import log as log_directory
from machincast.audio import Plugin
from machincast.configuration import PROJECT_DIRECTORY, AudioOutput
from machincast.installation import (
	COMPONENTS,
	ICON,
	PIPEWIRE_UNIT,
	SERVICE_ACCOUNT,
	SERVICE_RUNTIME,
	SERVICE_STATE,
	UNIT,
	WIREPLUMBER_UNIT,
	Account,
	Old,
	Shortfall,
	check_decoders,
	check_output,
	check_streams,
	check_versions,
	indexing_unit,
	polkit_rule,
	shortcut,
	systemd_unit,
	tasks_unit,
)
from machincast.interface.application import application
from machincast.intranet import __main__ as intranet_server
from machincast.protection import SOUND_EXTENSIONS
from tests.database_fixtures import (
	configuration_test,
	sample_configuration_path,
)

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

scenarios("installation.feature")

PLAYERS = Gst.ELEMENT_FACTORY_TYPE_DECODER | Gst.ELEMENT_FACTORY_TYPE_DEMUXER | Gst.ELEMENT_FACTORY_TYPE_PARSER


@given(parsers.parse("les éléments GStreamer qui lisent « {caps} » désactivés"))
def disabled_items(caps: str) -> Iterator[None]:
	"""Simule un paquet absent : decodebin, comme la vérification, ignore les éléments de rang NONE."""
	Gst.init(None)
	capabilities = Gst.Caps.from_string(caps)
	assert capabilities is not None
	factories = []
	for f in Gst.ElementFactory.list_get_elements(PLAYERS, Gst.Rank.MARGINAL):
		if f.can_sink_any_caps(capabilities):
			factories.append(f)
	assert factories, f"aucun élément ne lit {caps}"
	ranks = []
	for factory in factories:
		ranks.append((factory, factory.get_rank()))
	for factory in factories:
		factory.set_rank(Gst.Rank.NONE)
	yield
	for factory, rank in ranks:
		factory.set_rank(rank)


@given(parsers.parse("les sources GStreamer du protocole « {protocol} » désactivées"))
def disabled_sources(protocol: str) -> Iterator[None]:
	Gst.init(None)
	factories = []
	for f in Gst.ElementFactory.list_get_elements(Gst.ELEMENT_FACTORY_TYPE_SRC, Gst.Rank.MARGINAL):
		if (f.get_uri_type() == Gst.URIType.SRC) and (protocol in ((f.get_uri_protocols()) or ([]))):
			factories.append(f)
	assert factories, f"aucune source pour {protocol}"
	ranks = []
	for factory in factories:
		ranks.append((factory, factory.get_rank()))
	for factory in factories:
		factory.set_rank(Gst.Rank.NONE)
	yield
	for factory, rank in ranks:
		factory.set_rank(rank)


@given(parsers.parse("{component} en version « {version} »"))
def installed_version(monkeypatch: pytest.MonkeyPatch, component: str, version: str) -> None:
	"""Simule une autre version installée du composant ; les autres gardent la leur."""
	plugin, _package = COMPONENTS[component]
	version_true = installation.read_version

	def read(asks: str | None) -> str | None:
		if asks == plugin:
			return version
		return version_true(asks)

	monkeypatch.setattr(installation, "read_version", read)


@when("je vérifie la version de GStreamer", target_fixture="old_list")
def versions() -> list[Old]:
	return check_versions()


@then("aucune version de GStreamer n'est plus ancienne que la version vérifiée")
def no_old(old_list: list[Old]) -> None:
	assert old_list == [], old_list


@then(parsers.parse("{component} n'est pas signalé"))
def component_not_reported(old_list: list[Old], component: str) -> None:
	reported = []
	for old in old_list:
		if old.component == component:
			reported.append(old)
	assert reported == [], old_list


@then(parsers.parse("{component} est signalé en version « {version} », avec le paquet « {package} »"))
def old_reported(old_list: list[Old], component: str, version: str, package: str) -> None:
	assert Old(component, version, package) in old_list, old_list


@when("je vérifie les greffons comme la ligne de commande", target_fixture="output_code")
def check_as_command_line(caplog: pytest.LogCaptureFixture) -> int:
	caplog.set_level("INFO", logger="machincast.installation")
	return installation._check(configuration_test())


@then("la vérification réussit")
def successful_check(output_code: int) -> None:
	assert output_code == 0


@then(parsers.parse("le journal avertit « {message} »"))
def log_warns(caplog: pytest.LogCaptureFixture, message: str) -> None:
	warnings = []
	for r in caplog.records:
		if r.levelname == "WARNING":
			warnings.append(r.getMessage())
	assert message in warnings, warnings


@when("je vérifie la source des streams", target_fixture="gaps")
def streams() -> list[Shortfall]:
	return check_streams()


@then("aucun protocole de stream ne manque de source")
def no_missing_source(gaps: list[Shortfall]) -> None:
	assert gaps == [], gaps


@when("je vérifie les décodeurs GStreamer", target_fixture="gaps")
def decoders() -> list[Shortfall]:
	return check_decoders()


@then("aucun format sonore ne manque de décodeur")
def no_missing(gaps: list[Shortfall]) -> None:
	assert gaps == [], gaps


@then(parsers.parse("le format {sound_format} manque, avec le paquet « {package} »"))
def missing_format(gaps: list[Shortfall], sound_format: str, package: str) -> None:
	assert Shortfall(sound_format, package) in gaps, gaps


@when("je vérifie la sortie audio de la configuration de test", target_fixture="gaps")
def sample_output() -> list[Shortfall]:
	return check_output(configuration_test())


@when("je vérifie une sortie audio dont le greffon GStreamer n'existe pas", target_fixture="gaps")
def nonexistent_output() -> list[Shortfall]:
	plugins: dict[AudioOutput, Plugin] = {
		"dummy": Plugin(factory="elementinexistant", property_=None, package="gstreamer1.0-inexistant")
	}
	return check_output(configuration_test(), plugins)


@then("la sortie audio est disponible")
def available_output(gaps: list[Shortfall]) -> None:
	assert gaps == [], gaps


@then(parsers.parse("la sortie audio manque, avec le paquet « {package} »"))
def missing_output(gaps: list[Shortfall], package: str) -> None:
	missing_list = []
	for missing in gaps:
		missing_list.append(missing.package)
	assert missing_list == [package], gaps


def launch(action: str, configuration: Path) -> subprocess.CompletedProcess[str]:
	return subprocess.run(
		[sys.executable, "-m", "machincast.installation", action, "--config", str(configuration)],
		capture_output=True,
		text=True,
		timeout=60,
	)


@when(
	parsers.parse("je lance « python -m machincast.installation {action} » avec la configuration de test"),
	target_fixture="command",
)
def launch_with_test_configuration(action: str) -> subprocess.CompletedProcess[str]:
	return launch(action, sample_configuration_path())


@when(
	parsers.parse(
		"je lance « python -m machincast.installation {action} » avec une configuration dont la socket n'existe pas"
	),
	target_fixture="command",
)
def launch_without_database(tmp_path: Path, action: str) -> subprocess.CompletedProcess[str]:
	# Une configuration jetable, dans le répertoire temporaire du scénario, qui ne peut joindre aucune base.
	configuration = tmp_path / "sans-base.toml"
	text = sample_configuration_path().read_text(encoding="utf-8")
	configuration.write_text(
		text.replace('socket = "/var/run/postgresql"', f'socket = "{tmp_path / "aucune-socket"}"'), encoding="utf-8"
	)
	return launch(action, configuration)


@when(
	parsers.re(
		r"je lance « python -m machincast.installation (?P<action>[a-z-]+) » avec une configuration sur la sortie"
		r" « (?P<output>[^»]+) », l'antenne (?:« (?P<on_air>[^»]+) »|non renseignée)"
	),
	target_fixture="command",
)
def launch_on_on_air(tmp_path: Path, action: str, output: str, on_air: str | None) -> subprocess.CompletedProcess[str]:
	"""https://github.com/dascritch/machincast/issues/339"""
	document = tomlkit.parse(sample_configuration_path().read_text(encoding="utf-8"))
	audio = document["audio"]
	assert isinstance(audio, tomlkit.items.Table)
	audio["output"] = output
	if on_air is not None:
		audio["device"] = on_air
	configuration = tmp_path / "antenne.toml"
	configuration.write_text(tomlkit.dumps(document), encoding="utf-8")
	return launch(action, configuration)


@then(
	parsers.parse(
		"install.sh vérifie l'antenne par « installation on-air » avant la première étape du service, et s'arrête si"
		" elle échoue"
	)
)
def checked_on_air_install() -> None:
	text = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	start = text.index("installer_service() {")
	body = text[start : text.index("\n}\n", start)]
	check = body.index("installation on-air || echec ")
	assert check < body.index("creer_le_compte_du_service"), body


@then("la commande se termine sans erreur")
def without_error(command: subprocess.CompletedProcess[str]) -> None:
	assert command.returncode == 0, command.stderr


@then(parsers.parse("la commande se termine avec le code {code:d}"))
def code(command: subprocess.CompletedProcess[str], code: int) -> None:
	assert command.returncode == code, command.stderr


@then("elle affiche la socket, la base de production puis la base de test de cette configuration")
def parameters(command: subprocess.CompletedProcess[str]) -> None:
	database = configuration_test().database
	assert command.stdout.splitlines() == [str(database.socket), database.production, database.test]


@then(parsers.parse("sa sortie annonce « {text} »"))
def announced_output(command: subprocess.CompletedProcess[str], text: str) -> None:
	assert text in command.stdout, command.stdout + command.stderr


@then(parsers.re(r"sa sortie règle à « (?P<value>[^»]+) » (?P<keys>«.+»)$"))
def output_settings(command: subprocess.CompletedProcess[str], value: str, keys: str) -> None:
	"""Chaque clé, sur sa ligne, à cette valeur (https://github.com/dascritch/machincast/issues/448)."""
	lines = command.stdout.splitlines()
	for key in re.findall(r"« ([^»]+) »", keys):
		assert f"{key}={value}" in lines, (key, command.stdout)


@then(parsers.parse("sa sortie d'erreur mentionne « {text} »"))
def mentioned_error(command: subprocess.CompletedProcess[str], text: str) -> None:
	assert text in command.stderr, command.stderr


@pytest.fixture(autouse=True)
def gstreamer() -> None:
	Gst.init(None)


# ─── Service systemd (https://github.com/dascritch/machincast/issues/22) ─────


def _account() -> tuple[str, str, int]:
	entry = pwd.getpwuid(os.getuid())
	return entry.pw_name, grp.getgrgid(entry.pw_gid).gr_name, entry.pw_uid


def _section(text: str, name: str) -> dict[str, list[str]]:
	"""Les clés d'une section d'unité systemd, avec leurs valeurs dans l'ordre : Environment se répète."""
	keys: dict[str, list[str]] = {}
	inside = False
	for line in text.splitlines():
		line = line.strip()
		if line.startswith("["):
			inside = line == f"[{name}]"
		if (inside) and ("=" in line) and (not line.startswith(("#", "["))):
			key, value = line.split("=", 1)
			keys.setdefault(key, []).append(value)
	return keys


def _expected(rows: list[list[str]], replacements: dict[str, str] | None = None) -> dict[str, list[str]]:
	"""Les clés attendues d'un tableau « clé | valeur », une ligne par valeur."""
	expected: dict[str, list[str]] = {}
	for key, value in rows:
		for marks, text in ((replacements) or ({})).items():
			value = value.replace(marks, text)
		expected.setdefault(key.strip(), []).append(value.strip())
	return expected


def _among(section: dict[str, list[str]], expected: dict[str, list[str]]) -> None:
	found = {}
	for key in expected:
		found[key] = section.get(key)
	assert found == expected


@then(parsers.parse("l'unité a, dans la section « {name} » :"))
def unit_section(command: subprocess.CompletedProcess[str], name: str, datatable: list[list[str]]) -> None:
	account, group, uid = _account()
	replacements = {"<compte>": account, "<groupe>": group, "<uid>": str(uid), "<répertoire>": str(PROJECT_DIRECTORY)}
	_headers, *rows = datatable
	assert _section(command.stdout, name) == _expected(rows, replacements), command.stdout


@then(parsers.re(r"« systemd-analyze verify » accepte (?:ensemble )?(?P<names>« [^»]+ »(?:(?:, | et )« [^»]+ »)*)"))
def accepted_units(tmp_path: Path, names: str) -> None:
	"""Des unités qui se nomment l'une l'autre se vérifient ensemble."""
	files = []
	for name in re.findall(r"« ([^»]+) »", names):
		files.append(str(tmp_path / name))
	check = subprocess.run(
		["systemd-analyze", "verify", "--man=no", *files], capture_output=True, text=True, timeout=60
	)
	assert check.returncode == 0, check.stderr


@given(parsers.parse("l'outil « {tool} » du poste"))
def tool(tool: str) -> None:
	if shutil.which(tool) is None:
		pytest.skip(f"{tool} absent du poste")


@when(parsers.parse("j'enregistre sa sortie en « {name} »"))
def save_output(tmp_path: Path, command: subprocess.CompletedProcess[str], name: str) -> None:
	(tmp_path / name).write_text(command.stdout, encoding="utf-8")


@then(parsers.parse("« systemd-analyze verify » accepte « {name} »"))
def accepted_unit(tmp_path: Path, name: str) -> None:
	check = subprocess.run(
		["systemd-analyze", "verify", "--man=no", str(tmp_path / name)], capture_output=True, text=True, timeout=60
	)
	assert check.returncode == 0, check.stderr


POLKIT_SIMULATOR = """
var polkit = {
	Result: {NO: "no", YES: "yes", AUTH_SELF: "auth_self", AUTH_SELF_KEEP: "auth_self_keep",
		AUTH_ADMIN: "auth_admin", AUTH_ADMIN_KEEP: "auth_admin_keep", NOT_HANDLED: null},
	rules: [],
	addRule: function (rule) { this.rules.push(rule); }
};
var action = {id: dukpy.action, lookup: function (key) { return {unit: dukpy.unit, verb: dukpy.verb}[key]; }};
var subject = {user: dukpy.user, local: true, active: true};
"""
"""Ce que polkit donne à une règle : polkit.addRule, et une action sur une unité. En ES5, comme le moteur de polkitd,
Duktape, que dukpy embarque (https://github.com/dascritch/machincast/issues/470)."""

POLKIT_ANSWER = """
var answer = "rien";
for (var index = 0; index < polkit.rules.length; index++) {
	var response = polkit.rules[index](action, subject);
	if ((response !== null) && (response !== undefined) && (answer === "rien")) {
		answer = String(response);
	}
}
answer;
"""
"""La réponse de la première règle qui en donne une, comme polkitd ; « rien » si aucune ne répond."""


@then(
	parsers.re(
		r"la règle polkit répond (?:« (?P<response>[^»]+) »|rien) à l'action « (?P<action>[^»]+) »"
		r"(?: sur « (?P<unit>[^»]+) », verbe « (?P<verb>[^»]+) »)?, pour (?P<who>le compte|un autre compte)"
	)
)
def polkit_response(
	command: subprocess.CompletedProcess[str],
	response: str | None,
	action: str,
	unit: str | None,
	verb: str | None,
	who: str,
) -> None:
	"""Une action sur une unité (systemd1), ou sans unité (login1, https://github.com/dascritch/machincast/issues/448)."""
	assert command.returncode == 0, command.stderr
	user = _account()[0]
	if who == "un autre compte":
		user = f"autre-que-{user}"
	answer = dukpy.evaljs(
		[POLKIT_SIMULATOR, command.stdout, POLKIT_ANSWER],
		action=action,
		unit=(unit) or (""),
		verb=(verb) or (""),
		user=user,
	)
	assert answer == ((response) or ("rien")), answer


@then("l'unité de machincast.installation est celle de « Machin logs »")
def wrapper_unit() -> None:
	wrapper = (PROJECT_DIRECTORY / "bin" / "Machin").read_text(encoding="utf-8")
	assert f'UNITE_LECTURE="{UNIT}"' in wrapper


@when(
	parsers.re(
		r"l'unité est rédigée dans « (?P<directory>[^»]+) », et la règle pour le compte « (?P<name>[^»]+) »,"
		r" du groupe « (?P<group>[^»]+) », d'uid (?P<uid>\d+)"
	),
	target_fixture="written_list",
)
def write(directory: str, name: str, group: str, uid: str) -> tuple[str, str]:
	return systemd_unit(Path(directory)), polkit_rule(Account(name, group, int(uid)))


@then(parsers.parse("l'unité n'a pas de section « {name} »"))
def without_section(command: subprocess.CompletedProcess[str], name: str) -> None:
	assert f"[{name}]" not in command.stdout, command.stdout


@when(
	parsers.re(
		r"les unités des tâches sont rédigées pour le compte « (?P<name>[^»]+) », du groupe « (?P<group>[^»]+) »,"
		r" dans « (?P<directory>[^»]+) »"
	),
	target_fixture="written_tasks",
)
def write_tasks(name: str, group: str, directory: str) -> dict[str, str]:
	"""https://github.com/dascritch/machincast/issues/455"""
	account = Account(name, group, 1001)
	return {
		"des tâches régulières": tasks_unit(account, Path(directory)),
		"de l'indexation rapide": indexing_unit(account, Path(directory)),
	}


@then(
	parsers.re(
		r"l'unité (?P<task>des tâches régulières|de l'indexation rapide) a, dans la section « (?P<name>[^»]+) »,"
		r" entre autres :"
	)
)
def task_section(written_tasks: dict[str, str], task: str, name: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	_among(_section(written_tasks[task], name), _expected(rows))


@then("install.sh a les noms des tâches du service de machincast.service")
def sh_task_names() -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	for expected in (
		f'UNITE_TACHES="{service.TASKS_UNIT}"',
		f'MINUTEUR_TACHES="{service.TASKS_TIMER}"',
		f'UNITE_INDEXATION="{service.INDEXING_UNIT}"',
		f'MINUTEUR_INDEXATION="{service.INDEXING_TIMER}"',
		f'FICHIER_MINUTEUR_TACHES="{service.TASKS_TIMER_FILE}"',
	):
		assert expected in install, expected


@then("install.sh installe l'unité du serveur intranet, l'active, et la retire avec le service")
def sh_intranet() -> None:
	"""https://github.com/dascritch/machincast/issues/538 : l'unité tient Machin intranet éteint pour un arrêt voulu."""
	assert installation.INTRANET_DISABLED == intranet_server.DISABLED_CODE
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	for expected in (
		f'UNITE_INTRANET="{service.INTRANET_UNIT}"',
		'"intranet-unit:${FICHIER_UNITE_INTRANET}"',
		'executer sudo systemctl enable "${UNITE_INTRANET}"',
		'for unite in "${UNITE_INTRANET}" "${UNITE}"',
		'"${FICHIER_UNITE}" "${FICHIER_UNITE_INTRANET}"',
	):
		assert expected in install, expected


@then("install.sh, avec --no-timers, n'installe aucun minuteur et retire ceux d'avant")
def sh_no_timers() -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	assert "--no-timers) MINUTEURS=false ;;" in install
	installing = _function(install, "installer_service")
	assert 'if "${MINUTEURS}"; then\n\t\tinstaller_minuteurs\n\telse\n\t\tretirer_minuteurs\n\tfi' in installing, (
		installing
	)
	tasks = _function(install, "installer_minuteurs")
	for expected in (
		'executer sudo systemctl enable --now "${MINUTEUR_TACHES}" "${MINUTEUR_INDEXATION}"',
		'installer_fichier tasks-unit "${FICHIER_UNITE_TACHES}"',
		'installer_fichier indexing-timer "${FICHIER_MINUTEUR_INDEXATION}"',
	):
		assert expected in tasks, expected
	removing = _function(install, "retirer_minuteurs")
	assert 'executer sudo systemctl disable --now "${minuteur}"' in removing, removing
	assert "retirer_minuteurs" in _function(install, "retirer_service")


@then("install.sh ne vérifie les minuteurs d'un service installé que s'ils le sont")
def sh_checks_installed_timers() -> None:
	checking = _function((PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8"), "fichiers_du_service_perimes")
	assert 'if [[ -e "${FICHIER_MINUTEUR_TACHES}" ]]; then' in checking, checking


@then("install.sh retire l'ancien minuteur de la purge à midi, à l'installation comme au retrait du service")
def sh_old_purge() -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	assert 'ANCIEN_MINUTEUR_PURGE="machincast-purge.timer"' in install
	old = _function(install, "retirer_ancienne_purge")
	assert 'executer sudo systemctl disable --now "${ANCIEN_MINUTEUR_PURGE}"' in old, old
	assert "retirer_ancienne_purge" in _function(install, "installer_service")
	assert "retirer_ancienne_purge" in _function(install, "retirer_service")


@then(parsers.parse("l'unité de la commande a, dans la section « {name} », entre autres :"))
def command_section(command: subprocess.CompletedProcess[str], name: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	_among(_section(command.stdout, name), _expected(rows))


@then(parsers.parse("l'unité a, dans la section « {name} », entre autres :"))
def written_section(written_list: tuple[str, str], name: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	_among(_section(written_list[0], name), _expected(rows))


@then("sa sortie a, hors commentaires, les lignes :")
def lines_without_comments(command: subprocess.CompletedProcess[str], datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	found = []
	for line in command.stdout.splitlines():
		if (line.strip()) and (not line.lstrip().startswith("#")):
			found.append(line.strip())
	expected = []
	for (row,) in rows:
		expected.append(row.strip())
	assert found == expected, command.stdout


@then(parsers.re(r"le fragment WirePlumber désactive (?:le nœud « (?P<node>[^»]+) »|aucun nœud)"))
def disabled_nodes(command: subprocess.CompletedProcess[str], node: str | None) -> None:
	"""https://github.com/dascritch/machincast/issues/381"""
	names = re.findall(r'node\.name = "([^"]*)"', command.stdout)
	expected = []
	if node is not None:
		expected.append(node)
	assert names == expected, command.stdout
	assert ("node.disabled = true" in command.stdout) == (node is not None), command.stdout


def _function(text: str, name: str) -> str:
	start = text.index(f"\n{name}() {{")
	return text[start : text.index("\n}\n", start)]


@then("install.sh a les noms du service de machincast.installation")
def sh_service_names() -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	for expected in (
		f'COMPTE_SERVICE="{SERVICE_ACCOUNT}"',
		f'DOSSIER_DU_COMPTE_SERVICE="{SERVICE_STATE}"',
		f'DOSSIER_D_EXECUTION_SERVICE="{SERVICE_RUNTIME}"',
		f'DOSSIER_DES_LOGS="{log_directory.DIRECTORY}"',
		f'UNITE="{UNIT}"',
		f'UNITE_PIPEWIRE="{PIPEWIRE_UNIT}"',
		f'UNITE_WIREPLUMBER="{WIREPLUMBER_UNIT}"',
		f'DOSSIER_WIREPLUMBER_SERVICE="{installation.SERVICE_WIREPLUMBER.parent}"',
		f'/{installation.WIREPLUMBER_FRAGMENT}"',
		f'FICHIER_MODPROBE="{power_save.MODPROBE}"',
		f'FICHIER_USB="{power_save.USB_RULE}"',
	):
		assert expected in install, expected


@then("install.sh installe, vérifie et retire chacun de ces fichiers :")
def sh_service_files(datatable: list[list[str]]) -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	# La protection du poste (https://github.com/dascritch/machincast/issues/448) est une étape de l'installation.
	installing = (
		_function(install, "installer_service")
		+ _function(install, "proteger_le_poste")
		+ _function(install, "garder_les_cartes_eveillees")
		+ _function(install, "installer_minuteurs")
	)
	checking = _function(install, "fichiers_du_service_perimes")
	# Les minuteurs des tâches (https://github.com/dascritch/machincast/issues/455) se retirent à part.
	removing = _function(install, "retirer_service") + _function(install, "retirer_minuteurs")
	_headers, *rows = datatable
	for action, variable in rows:
		assert action.strip() in installation.ACTIONS, action
		file = "${" + variable.strip() + "}"
		pair = f'"{action.strip()}:{file}"'
		assert (pair in installing) or (f'installer_fichier {action.strip()} "{file}"' in installing), action
		assert pair in checking, action
		assert f'"{file}"' in removing, action


@then("install.sh, avec --service, demande de dédier le poste puis déplace MachinCast, avant toute autre étape")
def sh_dedicated_first() -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	body = _function(install, "principal")
	dedication = body.index("confirmer_le_poste_dedie")
	assert dedication < body.index("relocaliser_machincast") < body.index("verifier_systeme"), body


@then("install.sh ne lance jamais setfacl, ni chmod, ni chown")
def sh_no_rights() -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	for line in install.splitlines():
		if not line.lstrip().startswith("#"):
			for tool in ("setfacl", "chmod", "chown"):
				assert re.search(rf"\b{tool}\b", line) is None, line


@then(parsers.re(r"pour install.sh, « (?P<path>[^»]+) » (?P<verdict>est|n'est pas) dans un répertoire personnel"))
def sh_personal(path: str, verdict: str) -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	program = "\n".join(
		[
			'ACCUEIL="/home/machincast"',
			_function(install, "dans_un_repertoire_personnel") + "\n}",
			f'dans_un_repertoire_personnel "{path.replace("~", "$HOME")}"',
		]
	)
	result = subprocess.run(["bash", "-c", program], capture_output=True, text=True, timeout=10, check=False)
	assert (result.returncode == 0) is (verdict == "est"), result.stderr


@then(parsers.parse("install.sh crée « {directory} » au compte de MachinCast, au groupe « {group} », en mode {mode}"))
def sh_welcome(directory: str, group: str, mode: str) -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	assert f'ACCUEIL="{directory}"' in install
	assert str(access.WELCOME) == directory
	assert group == installation.SERVICE_ACCOUNT
	expected = (
		f'install --directory --owner="${{UTILISATEUR}}" --group="${{COMPTE_SERVICE}}" --mode={mode} "${{ACCUEIL}}"'
	)
	assert expected in _function(install, "creer_l_accueil")


@then(parsers.parse("la règle ne concerne que le compte « {name} »"))
def count_rule(written_list: tuple[str, str], name: str) -> None:
	assert re.findall(r'subject\.user == "([^"]+)"', written_list[1]) == [name]


# ─── Raccourci et icône de l'interface (https://github.com/dascritch/machincast/issues/62) ─────


@then(parsers.parse("le raccourci a, dans la section « {name} » :"))
def shortcut_section(command: subprocess.CompletedProcess[str], name: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	assert _section(command.stdout, name) == _expected(rows, {"<répertoire>": str(PROJECT_DIRECTORY)}), command.stdout


@when(parsers.parse("le raccourci est rédigé pour le répertoire « {directory} »"), target_fixture="written")
def write_shortcut(directory: str) -> str:
	return shortcut(Path(directory))


@then(parsers.parse("le raccourci a, dans la section « {name} », entre autres :"))
def written_shortcut_section(written: str, name: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	_among(_section(written, name), _expected(rows))


@then(parsers.parse("« desktop-file-validate » accepte « {name} »"))
def accepted_shortcut(tmp_path: Path, name: str) -> None:
	check = subprocess.run(["desktop-file-validate", str(tmp_path / name)], capture_output=True, text=True)
	# desktop-file-validate ne signale les erreurs et les avertissements que sur sa sortie : rien n'est attendu.
	assert (check.returncode == 0) and (check.stdout == ""), check.stdout


@then(parsers.parse("l'icône de MachinCast est une image PNG carrée de {side:d} pixels, aux coins transparents"))
def png_icon(side: int) -> None:
	assert ICON.suffix == ".png"
	image = QImage(str(ICON))
	assert (image.width(), image.height()) == (side, side)
	for x, y in ((0, 0), (side - 1, 0), (0, side - 1), (side - 1, side - 1)):
		assert image.pixelColor(x, y).alpha() == 0, (x, y)


ICON_COLOURS = {"losange orange": QColor("#fe4300"), "casque noir": QColor(0, 0, 0)}
"""Les couleurs du logo des équipes techniques de la radio (https://github.com/dascritch/machincast/issues/213)."""


def _near(colour: QColor, expected: QColor) -> bool:
	return (
		max(
			abs(colour.red() - expected.red()),
			abs(colour.green() - expected.green()),
			abs(colour.blue() - expected.blue()),
		)
		<= 80
	)


@then(parsers.re(r"rendue en (?P<sizes>[\d, et]+) pixels, l'icône montre son losange orange et son casque noir"))
def readable_icon(qapp: QApplication, sizes: str) -> None:
	"""À chaque taille, chacune des couleurs couvre au moins un pixel sur quarante : rien ne disparaît. Le casque, au
	trait fin, n'a que quelques pixels à 16 pixels ; les bords lissés s'écartent du noir pur."""
	icon = QIcon(str(ICON))
	count_list = []
	for count in re.findall(r"\d+", sizes):
		count_list.append(int(count))
	for size in count_list:
		image = icon.pixmap(size).toImage()
		assert (image.width(), image.height()) == (size, size)
		pixels = []
		for x in range(size):
			for y in range(size):
				pixels.append(image.pixelColor(x, y))
		for name, colour in ICON_COLOURS.items():
			total = 0
			for pixel in pixels:
				if (pixel.alpha() > 200) and (_near(pixel, colour)):
					total += 1
			share = total / len(pixels)
			assert share >= 1 / 40, f"{name} à {size} pixels : {share:.3f}"


@when("l'application Qt de l'interface est créée", target_fixture="application_qt")
def application_qt(qapp: QApplication) -> QApplication:
	return application("Machin_interface")


@then("sa fenêtre a l'icône de MachinCast")
def application_icon(application_qt: QApplication) -> None:
	icon = application_qt.windowIcon()
	assert not icon.isNull()
	assert icon.pixmap(32).toImage() == QIcon(str(ICON)).pixmap(32).toImage()


@then(parsers.parse("l'application se réclame du raccourci « {name} »"))
def shortcut_name(application_qt: QApplication, name: str) -> None:
	assert application_qt.desktopFileName() == name


# ─── Icône choisie (https://github.com/dascritch/machincast/issues/111) ─────


@given(parsers.parse("une image PNG « {name} »"), target_fixture="image")
def image_png(tmp_path: Path, name: str) -> Path:
	path = tmp_path / name
	image = QImage(32, 32, QImage.Format.Format_ARGB32)
	image.fill(QColor("#c0392b"))
	assert image.save(str(path), "PNG")
	return path


@when(
	parsers.parse(
		"je lance « python -m machincast.installation {action} » avec une configuration dont l'icône est cette image"
	),
	target_fixture="command",
)
def launch_with_icon(tmp_path: Path, image: Path, action: str) -> subprocess.CompletedProcess[str]:
	configuration = tmp_path / "icone.toml"
	document = tomlkit.parse(sample_configuration_path().read_text(encoding="utf-8"))
	if "interface" not in document:
		document.add("interface", tomlkit.table())
	section = document["interface"]
	assert isinstance(section, tomlkit.items.Table)
	section["icon"] = str(image)
	configuration.write_text(tomlkit.dumps(document), encoding="utf-8")
	return launch(action, configuration)


@then("le raccourci a l'icône de cette image")
def image_icon(command: subprocess.CompletedProcess[str], image: Path) -> None:
	assert _section(command.stdout, "Desktop Entry")["Icon"] == [str(image)], command.stdout


@when(
	parsers.parse("le raccourci est rédigé pour le répertoire « {directory} », avec l'icône « {icon} »"),
	target_fixture="written",
)
def write_with_icon(directory: str, icon: str) -> str:
	return shortcut(Path(directory), Path(icon))


# ─── Désinstallation (https://github.com/dascritch/machincast/issues/430) ───


@pytest.fixture
def removal() -> SimpleNamespace:
	return SimpleNamespace(directory=None, welcome=None, result=None)


@given(parsers.parse("un répertoire créé par MachinCast, qui contient « {content} »"))
def created_directory(tmp_path: Path, removal: SimpleNamespace, content: str) -> None:
	directory = tmp_path / "machincast-cree"
	(directory / content).parent.mkdir(parents=True)
	(directory / content).write_bytes(b"contenu")
	removal.directory = directory
	removal.welcome = tmp_path / "accueil"


@given("le répertoire d'accueil des sonores, vide")
def empty_welcome(tmp_path: Path, removal: SimpleNamespace) -> None:
	removal.welcome = tmp_path / "accueil"
	removal.welcome.mkdir()
	removal.directory = removal.welcome


@when("install.sh retire ce répertoire")
def removed(removal: SimpleNamespace) -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	line = re.search(r"^EXTENSIONS_SONORES=.*$", install, re.MULTILINE)
	assert line is not None
	program = "\n".join(
		[
			"set -euo pipefail",
			"SIMULATION=false",
			f'ACCUEIL="{removal.welcome}"',
			line.group(0),
			'executer() { "$@"; }',
			'avertissement() { local format="$1"; shift; printf -- "${format}\\n" "$@"; }',
			_function(install, "premier_sonore") + "\n}",
			_function(install, "retirer_repertoires") + "\n}",
			f'retirer_repertoires "{removal.directory}"',
		]
	)
	removal.result = subprocess.run(["bash", "-c", program], capture_output=True, text=True, timeout=10, check=False)
	assert removal.result.returncode == 0, removal.result.stderr


@then(
	parsers.re(
		r"le répertoire (?P<verdict>est retiré|reste, et install.sh dit qu'il contient des sonores|reste, et install.sh dit que c'est celui des sonores)"
	)
)
def removal_verdict(removal: SimpleNamespace, verdict: str) -> None:
	if verdict == "est retiré":
		assert not removal.directory.exists()
		return
	assert removal.directory.is_dir()
	expected = "it contains sound files, such as"
	if "celui des sonores" in verdict:
		expected = "it is the directory of the sound files"
	assert expected in removal.result.stdout, removal.result.stdout


@then("install.sh ne lance « rm --recursive » que dans retirer_repertoires")
def only_guarded_removal() -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	guarded = _function(install, "retirer_repertoires")
	outside = install.replace(guarded, "")
	for line in outside.splitlines():
		if not line.lstrip().startswith("#"):
			assert "rm --recursive" not in line, line


@then("les extensions des sonores d'install.sh sont celles de machincast.protection")
def same_extensions() -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	line = re.search(r"^EXTENSIONS_SONORES=\((?P<list>[^)]*)\)$", install, re.MULTILINE)
	assert line is not None
	expected = set()
	for extension in SOUND_EXTENSIONS:
		expected.add(extension.removeprefix("."))
	assert set(line.group("list").split()) == expected


@then(
	parsers.re(
		r"install.sh, en installant le service, recharge « (?P<unit>[^»]+) » quand « (?P<logind>[^»]+) » change, et"
		r" réexécute systemd quand « (?P<manager>[^»]+) » change"
	)
)
def sh_reloads(unit: str, logind: str, manager: str) -> None:
	"""https://github.com/dascritch/machincast/issues/448 : un fragment ne vaut qu'une fois relu."""
	installing = _protection()
	assert re.search(
		rf'if installer_fichier logind "\$\{{{logind}\}}"; then\s+executer sudo systemctl reload {unit}\n', installing
	), installing
	assert re.search(
		rf'if installer_fichier system-conf "\$\{{{manager}\}}"; then\s+executer sudo systemctl daemon-reexec\n',
		installing,
	), installing


@then(parsers.parse("install.sh, en installant le service, masque « {unit} » s'il ne l'est pas"))
def sh_masks(unit: str) -> None:
	installing = _protection()
	assert f"executer sudo systemctl mask {unit}" in installing, installing
	assert f'"$(systemctl is-enabled {unit} 2>/dev/null || true)" != "masked"' in installing, installing


@then(
	parsers.parse(
		"install.sh, en retirant le service, démasque « {unit} » s'il est masqué, recharge « {logind} » et réexécute"
		" systemd"
	)
)
def sh_unmasks(unit: str, logind: str) -> None:
	removing = _function((PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8"), "retirer_service")
	assert f'"$(systemctl is-enabled {unit} 2>/dev/null || true)" == "masked"' in removing, removing
	assert f"executer sudo systemctl unmask {unit}" in removing, removing
	assert f"executer sudo systemctl reload {logind}" in removing, removing
	assert "executer sudo systemctl daemon-reexec" in removing, removing


def _protection() -> str:
	"""La protection du poste d'install.sh, appelée à l'installation du service
	(https://github.com/dascritch/machincast/issues/448)."""
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	assert "\n\tproteger_le_poste\n" in _function(install, "installer_service")
	return _function(install, "proteger_le_poste")


# ─── Réimportation d'une sauvegarde à la création de la base (https://github.com/dascritch/machincast/issues/347) ───

REIMPORT_FUNCTIONS = (
	"choisir_couleurs",
	"info",
	"annonce",
	"avertissement",
	"echec",
	"executer",
	"graphique",
	"peut_demander",
	"interroger",
	"en_terminal",
	"demander_reimportation",
	"choisir_sauvegarde",
	"restaurer",
	"reimporter_une_sauvegarde",
)
"""Les fonctions d'install.sh qu'enchaîne la réimportation, lancées seules, en français."""


@pytest.fixture
def reimport(tmp_path: Path) -> SimpleNamespace:
	"""Le poste du scénario : kdialog et Machin restore-db remplacés par des scripts qui notent leurs arguments."""
	bin_ = tmp_path / "bin"
	venv = tmp_path / "venv"
	home = tmp_path / "personnel"
	for directory in (bin_, venv / "bin", home):
		directory.mkdir(parents=True)
	journal = tmp_path / "appels"
	kdialog = bin_ / "kdialog"
	kdialog.write_text(
		"#!/bin/bash\n"
		f'echo "kdialog	$*" >>"{journal}"\n'
		'if [[ " $* " == *" --yesno "* ]]; then exit "${KDIALOG_REPONSE:-1}"; fi\n'
		'echo "${KDIALOG_FICHIER:-}"\n',
		encoding="utf-8",
	)
	restore = venv / "bin" / "Machin_restore-db"
	restore.write_text(
		f'#!/bin/bash\necho "restore	$*" >>"{journal}"\nexit "${{RESTORE_CODE:-0}}"\n', encoding="utf-8"
	)
	for program in (kdialog, restore):
		program.chmod(0o755)
	return SimpleNamespace(
		tmp=tmp_path,
		bin=bin_,
		venv=venv,
		home=home,
		journal=journal,
		environment={"LANGUAGE": "fr", "HOME": str(home), "PATH": f"{bin_}:/usr/bin:/bin"},
		terminal="false",
		variables={"REIMPORTER": "demander", "SAUVEGARDE": ""},
		answers="",
		result=None,
	)


@given("un poste graphique avec kdialog")
def graphical(reimport: SimpleNamespace) -> None:
	reimport.environment["DISPLAY"] = ":0"


@given(parsers.re(r"un poste sans affichage graphique, (?P<terminal>dans un terminal|ni terminal)"))
@given(parsers.re(r"un poste sans affichage graphique (?P<terminal>ni terminal)"))
def without_graphics(reimport: SimpleNamespace, terminal: str) -> None:
	(reimport.bin / "kdialog").unlink()
	reimport.terminal = str(terminal == "dans un terminal").lower()


@given(parsers.parse("kdialog répond « {answer} », puis choisit « {file} »"))
def kdialog_answers(reimport: SimpleNamespace, answer: str, file: str) -> None:
	reimport.environment["KDIALOG_REPONSE"] = str(int(answer != "Oui, importer une sauvegarde"))
	reimport.environment["KDIALOG_FICHIER"] = file


@given("Machin restore-db qui refuse la sauvegarde")
def refused_restore(reimport: SimpleNamespace) -> None:
	reimport.environment["RESTORE_CODE"] = "1"


@given(parsers.parse("install.sh lancé avec « {options} »"))
def launched_with(reimport: SimpleNamespace, options: str) -> None:
	"""Les variables que donne l'analyse des options de principal(), vérifiée par le scénario du texte d'install.sh."""
	words = options.split()
	if words[0] == "--restore":
		reimport.variables = {"REIMPORTER": "oui", "SAUVEGARDE": words[1]}
	if words[0] == "--no-restore":
		reimport.variables = {"REIMPORTER": "non", "SAUVEGARDE": ""}


def _propose(reimport: SimpleNamespace) -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	lines = [
		"set -euo pipefail",
		f'. "{PROJECT_DIRECTORY / "bin" / "i18n.bash"}"',
		f'charger_messages "{PROJECT_DIRECTORY}"',
		"SIMULATION=false",
		"VERBEUX=false",
		f'VENV="{reimport.venv}"',
		f'CONFIGURATION="{reimport.tmp / "machincast.toml"}"',
	]
	for name, value in reimport.variables.items():
		lines.append(f'{name}="{value}"')
	for function in REIMPORT_FUNCTIONS:
		lines.append(_function(install, function) + "\n}")
	lines.append("choisir_couleurs")
	lines.append(f"en_terminal() {{ {reimport.terminal}; }}")
	lines.append("reimporter_une_sauvegarde")
	reimport.result = subprocess.run(
		["bash", "-c", "\n".join(lines)],
		input=reimport.answers,
		capture_output=True,
		text=True,
		timeout=10,
		env=reimport.environment,
		check=False,
	)


@when("install.sh propose de réimporter une sauvegarde")
def propose(reimport: SimpleNamespace) -> None:
	_propose(reimport)


@when(parsers.re(r"install.sh propose de réimporter une sauvegarde, et que je réponds (?P<answers>«.+»)$"))
def propose_answering(reimport: SimpleNamespace, answers: str) -> None:
	lines = []
	for answer in re.findall(r"« ([^»]*) »", answers):
		lines.append(answer + "\n")
	reimport.answers = "".join(lines)
	_propose(reimport)


def _calls(reimport: SimpleNamespace, program: str) -> list[str]:
	if not reimport.journal.exists():
		return []
	calls = []
	for line in reimport.journal.read_text(encoding="utf-8").splitlines():
		name, _tab, arguments = line.partition("\t")
		if name == program:
			calls.append(arguments)
	return calls


def _restored(reimport: SimpleNamespace, file: str) -> str:
	return f"--config {reimport.tmp / 'machincast.toml'} {file.replace('<personnel>', str(reimport.home))}"


@then(parsers.parse("install.sh a réimporté « {file} » par Machin restore-db"))
def restored(reimport: SimpleNamespace, file: str) -> None:
	assert reimport.result.returncode == 0, reimport.result.stderr
	assert _calls(reimport, "restore") == [_restored(reimport, file)]


@then(parsers.re(r"install.sh n'a rien réimporté(?:, et dit « (?P<text>[^»]+) »)?$"))
def nothing_restored(reimport: SimpleNamespace, text: str | None) -> None:
	assert reimport.result.returncode == 0, reimport.result.stderr
	assert _calls(reimport, "restore") == []
	if text is not None:
		assert text in reimport.result.stdout, reimport.result.stdout


@then(parsers.parse("install.sh a tenté de réimporter « {file} », a reposé la question, et dit « {text} »"))
def restore_attempted(reimport: SimpleNamespace, file: str, text: str) -> None:
	assert reimport.result.returncode == 0, reimport.result.stderr
	assert _calls(reimport, "restore") == [_restored(reimport, file)]
	assert "sauvegarde non réimportée : en choisir une autre, ou repartir de zéro" in reimport.result.stdout
	assert text in reimport.result.stdout, reimport.result.stdout


@then(parsers.parse("kdialog a demandé « {question} »"))
def kdialog_asked(reimport: SimpleNamespace, question: str) -> None:
	(asked, *_others) = _calls(reimport, "kdialog")
	assert question in asked, asked
	assert "--yes-label Oui, importer une sauvegarde --no-label Non, on repart de zéro" in asked, asked


@then("kdialog n'a rien demandé")
def kdialog_silent(reimport: SimpleNamespace) -> None:
	assert _calls(reimport, "kdialog") == []


@then(parsers.parse("install.sh s'arrête avec le message « {text} »"))
def stops_with(reimport: SimpleNamespace, text: str) -> None:
	assert reimport.result.returncode == 1
	assert text in reimport.result.stderr, reimport.result.stderr


@then(
	"install.sh propose de réimporter une sauvegarde après avoir créé la base de production, avant d'appliquer le schéma"
)
def sh_reimport_place() -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	preparation = _function(install, "preparer_postgresql")
	creation = preparation.index('createdb --host="${socket}"')
	marked = preparation.index("nouvelle_production=true")
	reimport = preparation.index("reimporter_une_sauvegarde")
	schema = preparation.index("machincast.installation migrate")
	assert creation < marked < reimport < schema
	assert 'if [[ "${base}" == "${production}" ]]; then\n\t\t\t\tnouvelle_production=true' in preparation
	analysis = _function(install, "principal")
	assert "--restore)" in analysis
	assert "--no-restore) REIMPORTER=non ;;" in analysis


def _run_shell(reimport: SimpleNamespace, *calls: str) -> None:
	"""Les fonctions d'install.sh, lancées seules, avec les variables et l'environnement du scénario."""
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	lines = [
		"set -uo pipefail",
		f'. "{PROJECT_DIRECTORY / "bin" / "i18n.bash"}"',
		f'charger_messages "{PROJECT_DIRECTORY}"',
		"SIMULATION=false",
		"VERBEUX=false",
	]
	for name, value in reimport.variables.items():
		lines.append(f'{name}="{value}"')
	for function in REIMPORT_FUNCTIONS:
		lines.append(_function(install, function) + "\n}")
	lines.append("choisir_couleurs")
	lines.append(f"en_terminal() {{ {reimport.terminal}; }}")
	lines.extend(calls)
	reimport.result = subprocess.run(
		["bash", "-c", "\n".join(lines)],
		input=reimport.answers,
		capture_output=True,
		text=True,
		timeout=10,
		env=reimport.environment,
		check=False,
	)


@given(parsers.parse("install.sh avec VERBEUX={verbose} et SIMULATION={simulation}"))
def with_verbosity(reimport: SimpleNamespace, verbose: str, simulation: str) -> None:
	reimport.variables["VERBEUX"] = verbose
	reimport.variables["SIMULATION"] = simulation


@given("install.sh avec les couleurs forcées")
def forced_colors(reimport: SimpleNamespace) -> None:
	reimport.environment["FORCE_COLOR"] = "1"


@given("install.sh sans terminal")
def without_terminal(reimport: SimpleNamespace) -> None:
	reimport.environment.pop("FORCE_COLOR", None)


@given("install.sh avec NO_COLOR et les couleurs forcées")
def no_color(reimport: SimpleNamespace) -> None:
	reimport.environment["FORCE_COLOR"] = "1"
	reimport.environment["NO_COLOR"] = "1"


@given("une connexion ssh")
def over_ssh(reimport: SimpleNamespace) -> None:
	reimport.environment["SSH_CONNECTION"] = "192.0.2.1 50000 192.0.2.2 22"


@when("install.sh écrit une information technique, une annonce et un avertissement")
def writes_levels(reimport: SimpleNamespace) -> None:
	_run_shell(reimport, "info 'technical line'", "annonce 'plain line'", "avertissement 'warning line'")


@when(parsers.parse("install.sh échoue avec « {text} »"))
def fails_with(reimport: SimpleNamespace, text: str) -> None:
	previous = reimport.result
	_run_shell(reimport, f"echec '{text}'")
	if previous is not None:
		reimport.result = subprocess.CompletedProcess(
			reimport.result.args,
			reimport.result.returncode,
			previous.stdout + reimport.result.stdout,
			previous.stderr + reimport.result.stderr,
		)


@when(parsers.re(r"install.sh pose la question « (?P<question>[^»]+) », et que je réponds « (?P<answer>[^»]*) »$"))
def asks_answered(reimport: SimpleNamespace, question: str, answer: str) -> None:
	reimport.answers = answer + "\n"
	_run_shell(reimport, f"if interroger '{question}' n; then echo oui; else echo non; fi")


@when(parsers.re(r"install.sh pose la question « (?P<question>[^»]+) »$"))
def asks(reimport: SimpleNamespace, question: str) -> None:
	_run_shell(reimport, f"if interroger '{question}' n; then echo oui; else echo non; fi")


@then(parsers.parse("install.sh montre {shown}"))
def shows(reimport: SimpleNamespace, shown: str) -> None:
	output = reimport.result.stdout
	assert "plain line" in output, output
	assert "warning line" in output, output
	assert ("technical line" in output) == (not shown.endswith("sans l'information")), output


def _line_with(reimport: SimpleNamespace, text: str) -> str:
	for line in reimport.result.stdout.splitlines():
		if text in line:
			return line
	raise AssertionError(reimport.result.stdout)


@then(parsers.parse("la ligne d'avertissement d'install.sh est entourée du code de couleur « {code} »"))
def warning_colored(reimport: SimpleNamespace, code: str) -> None:
	assert _line_with(reimport, "warning line") == f"\x1b[{code}m  ! warning line\x1b[0m"


@then("la ligne d'annonce d'install.sh n'a aucune couleur")
def announcement_plain(reimport: SimpleNamespace) -> None:
	assert _line_with(reimport, "plain line") == "    plain line"


@then(parsers.parse("la ligne d'échec d'install.sh est entourée du code de couleur « {code} »"))
def failure_colored(reimport: SimpleNamespace, code: str) -> None:
	assert reimport.result.returncode == 1
	assert reimport.result.stderr == f"\x1b[{code}minstall.sh : disque plein\x1b[0m\n", reimport.result.stderr


@then("install.sh n'a écrit aucune couleur")
def no_colors_written(reimport: SimpleNamespace) -> None:
	assert "\x1b" not in reimport.result.stdout + reimport.result.stderr, reimport.result


@then("la question d'install.sh est en blanc et en gras, et sa réponse est oui")
def question_bold(reimport: SimpleNamespace) -> None:
	assert reimport.result.stdout == "    \x1b[1;97mArrêter ? [y/N]\x1b[0m oui\n", reimport.result.stdout


@then(parsers.parse("kdialog a demandé « {question} » sans ses crochets"))
def kdialog_asked_plain(reimport: SimpleNamespace, question: str) -> None:
	(asked, *_others) = _calls(reimport, "kdialog")
	assert asked == f"--title MachinCast --yesno {question}", asked


@then("install.sh lance « Machin banner » avant toute étape, et reconnaît --verbose")
def sh_banner_first() -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	body = _function(install, "principal")
	assert body.index('"${RACINE}/bin/Machin" banner') < body.index("confirmer_le_poste_dedie"), body
	assert "--verbose) VERBEUX=true ;;" in body


@pytest.fixture
def session(tmp_path: Path) -> SimpleNamespace:
	"""Le script de session, écrit tel que le rédige machincast.installation, et un Machin qui dit son appel."""
	bin_ = tmp_path / "bin"
	bin_.mkdir()
	machin = bin_ / "Machin"
	machin.write_text('#!/bin/bash\necho "appel: Machin $*"\n', encoding="utf-8")
	machin.chmod(0o755)
	script = tmp_path / "machincast.sh"
	script.write_text(installation.profile(), encoding="utf-8")
	return SimpleNamespace(script=script, environment={"PATH": f"{bin_}:/usr/bin:/bin"}, shown="")


@when("un shell non interactif lit le script de session")
def non_interactive_session(session: SimpleNamespace) -> None:
	result = subprocess.run(
		["bash", "--norc", "--noprofile", "-c", f'. "{session.script}"'],
		capture_output=True,
		text=True,
		timeout=10,
		env=session.environment,
		check=False,
	)
	session.shown = result.stdout


@when("un shell interactif sur un terminal lit le script de session")
def interactive_session(session: SimpleNamespace) -> None:
	master, slave = pty.openpty()
	try:
		subprocess.run(
			["bash", "--norc", "--noprofile", "-i", "-c", f'. "{session.script}"'],
			stdin=subprocess.DEVNULL,
			stdout=slave,
			stderr=subprocess.DEVNULL,
			timeout=10,
			env=session.environment,
			check=False,
		)
		os.close(slave)
		session.shown = os.read(master, 4096).decode()
	finally:
		os.close(master)


@then("le script de session n'a rien montré")
def session_silent(session: SimpleNamespace) -> None:
	assert session.shown == ""


@then(parsers.parse("le script de session a lancé « {command} »"))
def session_launched(session: SimpleNamespace, command: str) -> None:
	assert session.shown.strip() == f"appel: {command}", session.shown
