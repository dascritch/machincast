"""Étapes des scénarios de vérification de l'installation (https://github.com/dascritch/machincast/issues/40)."""

import grp
import os
import pwd
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import gi
import pytest
import tomlkit
from PySide6.QtGui import QColor, QIcon, QImage
from PySide6.QtWidgets import QApplication
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import installation
from machincast.audio import Plugin
from machincast.configuration import PROJECT_DIRECTORY, AudioOutput
from machincast.installation import (
	COMPONENTS,
	ICON,
	PURGE_TIMER,
	PURGE_UNIT,
	UNIT,
	Account,
	Old,
	Shortfall,
	check_decoders,
	check_output,
	check_streams,
	check_versions,
	polkit_rule,
	purge_unit,
	shortcut,
	systemd_unit,
)
from machincast.interface.application import application
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
	old_list_2 = []
	for old in old_list:
		if old.component == component:
			old_list_2.append(old)
	assert old_list_2 == [], old_list


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
	assert check < body.index("loginctl"), body


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


def _section(text: str, name: str) -> dict[str, str]:
	"""Les clés d'une section d'unité systemd ; une clé répétée garde sa dernière valeur."""
	keys: dict[str, str] = {}
	inside = False
	for line in text.splitlines():
		line = line.strip()
		if line.startswith("["):
			inside = line == f"[{name}]"
			continue
		if (inside) and ("=" in line) and (not line.startswith("#")):
			key, value = line.split("=", 1)
			keys[key] = value
	return keys


@then(parsers.parse("l'unité a, dans la section « {name} » :"))
def unit_section(command: subprocess.CompletedProcess[str], name: str, datatable: list[list[str]]) -> None:
	account, group, uid = _account()
	replacements = {"<compte>": account, "<groupe>": group, "<uid>": str(uid), "<répertoire>": str(PROJECT_DIRECTORY)}
	_headers, *rows = datatable
	expected_list = {}
	for key, value in rows:
		for marks, text in replacements.items():
			value = value.replace(marks, text)
		expected_list[key.strip()] = value.strip()
	assert _section(command.stdout, name) == expected_list, command.stdout


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
const polkit = {
	Result: {NO: "no", YES: "yes", AUTH_SELF: "auth_self", AUTH_SELF_KEEP: "auth_self_keep",
		AUTH_ADMIN: "auth_admin", AUTH_ADMIN_KEEP: "auth_admin_keep", NOT_HANDLED: null},
	regles: [],
	addRule(regle) { this.regles.push(regle); },
};
const [identifiant, unite, verbe, utilisateur] = process.argv.slice(2);
const action = {id: identifiant, lookup: (cle) => ({unit: unite, verb: verbe})[cle]};
const sujet = {user: utilisateur, local: true, active: true};
"""
"""Ce que polkit donne à une règle : polkit.addRule, et une action sur une unité ; la réponse s'affiche."""


@then(
	parsers.re(
		r"la règle polkit répond (?:« (?P<response>[^»]+) »|rien) à l'action « (?P<action>[^»]+) »"
		r" sur « (?P<unit>[^»]+) », verbe « (?P<verb>[^»]+) », pour (?P<who>le compte|un autre compte)"
	)
)
def polkit_response(
	tmp_path: Path,
	command: subprocess.CompletedProcess[str],
	response: str | None,
	action: str,
	unit: str,
	verb: str,
	who: str,
) -> None:
	assert command.returncode == 0, command.stderr
	program = tmp_path / "polkit.js"
	program.write_text(
		POLKIT_SIMULATOR
		+ command.stdout
		+ "\nconst reponses = polkit.regles.map((regle) => regle(action, sujet)).filter((r) => r != null);"
		+ "\nprocess.stdout.write(reponses.length ? String(reponses[0]) : 'rien');\n",
		encoding="utf-8",
	)
	user = _account()[0]
	if who == "un autre compte":
		user = f"autre-que-{user}"
	result = subprocess.run(
		["node", str(program), action, unit, verb, user], capture_output=True, text=True, timeout=60
	)
	assert result.returncode == 0, result.stderr
	assert result.stdout == ((response) or ("rien")), result.stdout


@then("l'unité de machincast.installation est celle de « Machin logs »")
def wrapper_unit() -> None:
	wrapper = (PROJECT_DIRECTORY / "bin" / "Machin").read_text(encoding="utf-8")
	assert f'UNITE_LECTURE="{UNIT}"' in wrapper


@when(
	parsers.re(
		r"l'unité et la règle sont rédigées pour le compte « (?P<name>[^»]+) », du groupe « (?P<group>[^»]+) »,"
		r" d'uid (?P<uid>\d+), dans « (?P<directory>[^»]+) »"
	),
	target_fixture="written_list",
)
def write(name: str, group: str, uid: str, directory: str) -> tuple[str, str]:
	account = Account(name, group, int(uid))
	return systemd_unit(account, Path(directory)), polkit_rule(account)


@then(parsers.parse("l'unité n'a pas de section « {name} »"))
def without_section(command: subprocess.CompletedProcess[str], name: str) -> None:
	assert f"[{name}]" not in command.stdout, command.stdout


@when(
	parsers.re(
		r"l'unité de la purge est rédigée pour le compte « (?P<name>[^»]+) », du groupe « (?P<group>[^»]+) »,"
		r" dans « (?P<directory>[^»]+) »"
	),
	target_fixture="written_purge",
)
def write_purge(name: str, group: str, directory: str) -> str:
	return purge_unit(Account(name, group, 1001), Path(directory))


@then(parsers.parse("l'unité de la purge a, dans la section « {name} », entre autres :"))
def purge_section(written_purge: str, name: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	section = _section(written_purge, name)
	value_dict = {}
	for key, _value in rows:
		value_dict[key.strip()] = section.get(key.strip())
	assert value_dict == {key.strip(): value.strip() for key, value in rows}


@then("install.sh installe et retire l'unité et le minuteur de la purge de machincast.installation")
def sh_install_purge() -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	assert f'UNITE_PURGE="{PURGE_UNIT}"' in install
	assert f'MINUTEUR_PURGE="{PURGE_TIMER}"' in install
	for expected in (
		'installer_fichier purge-unit "${FICHIER_UNITE_PURGE}"',
		'installer_fichier purge-timer "${FICHIER_MINUTEUR_PURGE}"',
		'executer sudo systemctl enable --now "${MINUTEUR_PURGE}"',
		'executer sudo systemctl disable --now "${MINUTEUR_PURGE}"',
	):
		assert expected in install, expected


@then(parsers.parse("l'unité a, dans la section « {name} », entre autres :"))
def written_section(written_list: tuple[str, str], name: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	section = _section(written_list[0], name)
	value_dict = {}
	for key, _value in rows:
		value_dict[key.strip()] = section.get(key.strip())
	assert value_dict == {key.strip(): value.strip() for key, value in rows}


@then(parsers.parse("la règle ne concerne que le compte « {name} »"))
def count_rule(written_list: tuple[str, str], name: str) -> None:
	assert re.findall(r'subject\.user == "([^"]+)"', written_list[1]) == [name]


# ─── Raccourci et icône de l'interface (https://github.com/dascritch/machincast/issues/62) ─────


@then(parsers.parse("le raccourci a, dans la section « {name} » :"))
def shortcut_section(command: subprocess.CompletedProcess[str], name: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	expected_list = {}
	for key, value in rows:
		expected_list[key.strip()] = value.strip().replace("<répertoire>", str(PROJECT_DIRECTORY))
	assert _section(command.stdout, name) == expected_list, command.stdout


@when(parsers.parse("le raccourci est rédigé pour le répertoire « {directory} »"), target_fixture="written")
def write_shortcut(directory: str) -> str:
	return shortcut(Path(directory))


@then(parsers.parse("le raccourci a, dans la section « {name} », entre autres :"))
def written_shortcut_section(written: str, name: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	section = _section(written, name)
	value_dict = {}
	for key, _value in rows:
		value_dict[key.strip()] = section.get(key.strip())
	assert value_dict == {key.strip(): value.strip() for key, value in rows}, written


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
	assert _section(command.stdout, "Desktop Entry")["Icon"] == str(image), command.stdout


@when(
	parsers.parse("le raccourci est rédigé pour le répertoire « {directory} », avec l'icône « {icon} »"),
	target_fixture="written",
)
def write_with_icon(directory: str, icon: str) -> str:
	return shortcut(Path(directory), Path(icon))
