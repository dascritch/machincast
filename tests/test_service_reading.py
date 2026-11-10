"""Scénarios de la lecture des sonores par le service de diffusion (https://github.com/dascritch/machincast/issues/381).

Le compte du service est celui de MACHINCAST_SERVICE_ACCOUNT, « nobody » ici : un compte qui existe sur tout poste,
sans aucun fichier. Les chemins « …/ » sont dans un répertoire temporaire que tout compte traverse, à part de celui du
scénario, privé. Les droits reviennent à la fin, pour que le répertoire s'efface.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast import access, personal, service
from machincast.interface import dialogs, service_access
from tests.database_fixtures import sample_configuration_path

scenarios("service_reading.feature")


@pytest.fixture
def root() -> Iterator[Path]:
	if shutil.which(access.TOOL) is None:
		pytest.skip("setfacl absent du poste")
	directory = Path(tempfile.mkdtemp(prefix="machincast-lecture-"))
	directory.chmod(0o755)
	yield directory
	for folder, _directories, _files in os.walk(directory):
		os.chmod(folder, 0o700)
	shutil.rmtree(directory)


@pytest.fixture
def context() -> SimpleNamespace:
	return SimpleNamespace(before={}, result=None, command=None, asked=[], said="", accepted=[], setfacl=[])


def _path(root: Path, text: str) -> Path:
	if text.startswith("/"):
		return Path(text)
	return root / text.removeprefix("…/")


def _account() -> access.Account:
	account = access.service_account()
	assert account is not None
	return account


@given(parsers.parse("le compte du service « {name} »"))
def service_account(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
	monkeypatch.setenv(service.ACCOUNT_ENVIRONMENT, name)


@given(parsers.parse("le répertoire « {path} » en mode {mode}"))
def directory(root: Path, path: str, mode: str) -> None:
	folder = _path(root, path)
	folder.mkdir()
	folder.chmod(int(mode, 8))


@when(parsers.parse("le fichier « {path} » s'ajoute, en mode {mode}"))
def added(root: Path, path: str, mode: str) -> None:
	"""Comme une copie : le fichier se crée avec son mode, que l'ACL par défaut de son répertoire complète, sans
	chmod, qui changerait le masque de son ACL."""
	descriptor = os.open(_path(root, path), os.O_CREAT | os.O_WRONLY, int(mode, 8))
	os.write(descriptor, b"son")
	os.close(descriptor)


@given(parsers.parse("le fichier « {path} » en mode {mode}"))
def file(root: Path, path: str, mode: str) -> None:
	item = _path(root, path)
	item.write_bytes(b"son " + path.encode())
	item.chmod(int(mode, 8))


@given("aucune ACL")
def without_acl() -> None:
	pass


@given(parsers.parse("l'ACL « {entry} » sur « {path} »"))
def acl(root: Path, entry: str, path: str) -> None:
	subprocess.run([access.TOOL, f"--modify={entry}", str(_path(root, path))], check=True)


@then(parsers.re(r"le service (?P<verdict>lit|ne lit pas) « (?P<path>[^»]+) »"))
def reads(root: Path, verdict: str, path: str) -> None:
	assert access.readable(_path(root, path), _account()) is (verdict == "lit")


@when(parsers.parse("la lecture de « {path} » est donnée au service"))
def granted(root: Path, context: SimpleNamespace, path: str) -> None:
	for folder, _directories, files in os.walk(root):
		for name in files:
			item = Path(folder) / name
			state = item.stat()
			context.before[item] = (state.st_uid, state.st_gid, state.st_mtime_ns, _hash(item), state.st_mode & 0o77)
	context.result = access.grant(_path(root, path), _account())
	assert context.result.problems == []


def _hash(path: Path) -> str:
	path.chmod(path.stat().st_mode | 0o400)
	return hashlib.sha256(path.read_bytes()).hexdigest()


@then(parsers.parse("le service lit tout « {path} »"))
def reads_all(root: Path, path: str) -> None:
	assert access.unreadable_inside(_path(root, path), _account()) == []


@then(parsers.parse("le service traverse « {path} » sans le lire"))
def crosses(root: Path, path: str) -> None:
	rights = access._rights(_path(root, path), _account())
	assert (rights & access.EXECUTE, rights & access.READ) == (access.EXECUTE, 0)


@then("les modes, les dates et le contenu des fichiers sont inchangés")
def unchanged(context: SimpleNamespace) -> None:
	"""Propriétaire, groupe, date, contenu ; ni le groupe du fichier ni les autres n'y gagnent de droit : avec une ACL,
	les bits du groupe du mode sont son masque, et les droits du groupe sont dans son entrée GROUP_OBJ."""
	for item, (uid, gid, modified, content, rights) in context.before.items():
		state = item.stat()
		group = (rights >> 3) & 7
		for tag, perm, _identifier in access._acl(item):
			if tag == access.GROUP_OBJ:
				group = perm
		assert (state.st_uid, state.st_gid, state.st_mtime_ns, _hash(item)) == (uid, gid, modified, content), item
		assert (group, state.st_mode & 7) == ((rights >> 3) & 7, rights & 7), item


@given(parsers.parse("un compte qui n'est pas le propriétaire de « {path} »"))
def not_owner(root: Path, monkeypatch: pytest.MonkeyPatch, path: str) -> None:
	monkeypatch.setattr(access.os, "getuid", lambda: _path(root, path).stat().st_uid + 1)


@then(parsers.parse("la lecture n'est pas donnée, et le problème dit « {text} »"))
def problem(context: SimpleNamespace, text: str) -> None:
	assert context.result.problems != []
	assert text in " ".join(context.result.problems), context.result.problems


@when(parsers.parse("je lance « Machin grant-read » sur « {path} »"))
def command(root: Path, context: SimpleNamespace, path: str) -> None:
	target = _path(root, path)
	context.command = subprocess.run(
		[sys.executable, "-m", "machincast.access", "--config", str(sample_configuration_path()), str(target)],
		capture_output=True,
		text=True,
		timeout=60,
		check=False,
	)


@then(parsers.parse("la commande se termine avec le code {code:d}"))
def code(context: SimpleNamespace, code: int) -> None:
	assert context.command.returncode == code, context.command.stderr


@then(parsers.parse("sa sortie d'erreur mentionne « {text} »"))
def mentions(context: SimpleNamespace, text: str) -> None:
	assert text in context.command.stderr, context.command.stderr


@when(parsers.parse("l'interface ajoute « {path} », et que j'accepte de les faire lire au service"))
def interface_adds(
	root: Path, context: SimpleNamespace, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
	def confirm(_parent: QWidget, _title: str, text: str, _button: str | None = None) -> bool:
		context.asked.append(text)
		return True

	monkeypatch.setattr(dialogs, "confirm_action", confirm)
	parent = QWidget()
	qtbot.addWidget(parent)
	screening = service_access.screen(parent, [_path(root, path)])
	context.said = screening.text()
	context.accepted = screening.accepted


@then(parsers.parse("l'interface a demandé si le service peut lire « {path} »"))
def asked(root: Path, context: SimpleNamespace, path: str) -> None:
	assert len(context.asked) == 1, context.asked
	assert str(_path(root, path)) in context.asked[0], context.asked


@then(parsers.parse("elle annonce « {text} »"))
def said(context: SimpleNamespace, text: str) -> None:
	assert context.said == text


@then("l'interface n'a rien demandé")
def nothing_asked(context: SimpleNamespace) -> None:
	assert (context.asked, context.said) == ([], "")


@given(parsers.parse("le répertoire personnel « {path} »"))
def personal_home(root: Path, monkeypatch: pytest.MonkeyPatch, path: str) -> None:
	monkeypatch.setenv(access.PERSONAL_ENVIRONMENT, str(_path(root, path)))


@given(parsers.parse("le lien « {link} » vers « {target} »"))
def link(root: Path, link: str, target: str) -> None:
	_path(root, link).symlink_to(_path(root, target))


@given(parsers.parse("le fichier « {path} » lisible par tous"))
def readable_by_all(path: str) -> None:
	assert Path(path).stat().st_mode & 0o004


@then(
	parsers.re(
		r"« (?P<path>[^»]+) » est dans le répertoire personnel (?P<home>« [^»]+ »|aucun), et dans l'arborescence sensible (?P<tree>« [^»]+ »|aucune)"
	)
)
def trees(path: str, home: str, tree: str) -> None:
	expected_home = None
	if home != "aucun":
		expected_home = Path(home.strip("« »"))
	expected_tree = None
	if tree != "aucune":
		expected_tree = Path(tree.strip("« »"))
	assert (access.personal_home(Path(path)), access.sensitive_tree(Path(path))) == (expected_home, expected_tree)


@then(parsers.parse("« {path} » est dans un répertoire personnel"))
def in_personal(root: Path, path: str) -> None:
	assert access.personal_home(_path(root, path)) is not None


@when(parsers.parse("la lecture de « {path} » est demandée pour le service"))
def asked_grant(root: Path, context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, path: str) -> None:
	def recorded(arguments: list[str]) -> None:
		context.setfacl.append(arguments)

	monkeypatch.setattr(access, "_setfacl", recorded)
	context.result = access.grant(_path(root, path), _account())


@then("setfacl n'a pas été lancé")
def no_setfacl(context: SimpleNamespace) -> None:
	assert context.setfacl == []


@then(parsers.re(r"l'interface n'a rien demandé, et (?P<verdict>refuse|accepte) « (?P<path>[^»]+) »"))
def screened(root: Path, context: SimpleNamespace, verdict: str, path: str) -> None:
	assert context.asked == []
	assert (_path(root, path) in context.accepted) is (verdict == "accepte")


@then(parsers.parse("elle annonce, entre autres, « {text} »"))
def said_among(context: SimpleNamespace, text: str) -> None:
	assert text in context.said, context.said


@then(parsers.parse("setfacl n'a été lancé que pour « {path} »"))
def setfacl_only(root: Path, context: SimpleNamespace, path: str) -> None:
	targets = []
	for arguments in context.setfacl:
		targets.append(arguments[-1])
	assert targets == [str(_path(root, path))]


@given(
	parsers.re(
		r"le répertoire d'accueil « (?P<path>[^»]+) » en mode (?P<mode>\d+), que le service (?:ne )?traverse(?: pas)?"
	)
)
def welcome_directory(
	root: Path, monkeypatch: pytest.MonkeyPatch, context: SimpleNamespace, path: str, mode: str
) -> None:
	"""Sur le poste, il est au groupe du service, en 2750 ; ici, le service, un autre compte, le traverse par les
	droits des autres."""
	folder = _path(root, path)
	folder.mkdir()
	folder.chmod(int(mode, 8))
	monkeypatch.setenv(access.WELCOME_ENVIRONMENT, str(folder))
	context.before[folder] = folder.stat().st_mode


@then(parsers.parse("les droits de « {path} » sont inchangés"))
def rights_unchanged(root: Path, context: SimpleNamespace, path: str) -> None:
	folder = _path(root, path)
	assert folder.stat().st_mode == context.before[folder]
	assert access._acl(folder) == []


@given(parsers.parse("l'ACL « {entry} » sur tout « {path} »"))
def acl_all(root: Path, entry: str, path: str) -> None:
	subprocess.run([access.TOOL, "--recursive", f"--modify={entry}", str(_path(root, path))], check=True)


@then(parsers.parse("install.sh ne propose pas de déplacer « {path} »"))
def not_proposed(root: Path, path: str) -> None:
	assert not personal._closed(_path(root, path), _account())
