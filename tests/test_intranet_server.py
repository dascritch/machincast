"""Scénarios du serveur intranet, de sa configuration et de son certificat
(https://github.com/dascritch/machincast/issues/538)."""

import http.client
import os
import re
import signal
import socket
import ssl
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import service
from machincast.configuration import Configuration, InvalidConfiguration, load
from machincast.intranet import __main__ as server
from machincast.intranet import certificate, live, network, process
from machincast.player.state import StateSocket
from tests.database_fixtures import sample_configuration_path

scenarios("intranet_server.feature")

NAME_MARKS = r"« ([^»]*) »"
EXECUTABLE = Path(sys.executable).with_name("Machin_intranet")
STARTUP = 20.0


@dataclass
class Context:
	directory: Path
	configuration: Configuration | None = None
	error: str = ""
	generated: list[bool] = field(default_factory=list)
	pair: certificate.Pair | None = None
	process: subprocess.Popen[str] | None = None
	port: int = 0
	response: http.client.HTTPResponse | None = None
	body: bytes = b""
	journal: str = ""


@pytest.fixture
def context(tmp_path: Path) -> Iterator[Context]:
	found = Context(tmp_path)
	yield found
	if (found.process is not None) and (found.process.poll() is None):
		found.process.kill()
		found.process.wait()


def _marks(text: str) -> list[str]:
	return re.findall(NAME_MARKS, text)


def _write(context: Context, section: str) -> Path:
	path = context.directory / "machincast.toml"
	text = sample_configuration_path().read_text(encoding="utf-8")
	path.write_text(f"{text}\n{section}", encoding="utf-8")
	return path


# ─── Configuration ─────────────────────────────────────────


@when("je charge la configuration de test, sans section [intranet]")
def load_without(context: Context) -> None:
	context.configuration = load(_write(context, ""))


@when(parsers.parse("je charge la configuration de test, avec dans [intranet] : {values}"))
def load_with(context: Context, values: str) -> None:
	lines = []
	for value in values.split(", "):
		lines.append(value)
	path = _write(context, "[intranet]\n" + "\n".join(lines) + "\n")
	try:
		context.configuration = load(path)
	except InvalidConfiguration as error:
		context.error = str(error)


@then(
	parsers.parse(
		"l'intranet est éteint, écoute « {address} » sur le port {port:d}, et laisse {minutes:d} minutes pour valider"
		" une connexion"
	)
)
def defaults(context: Context, address: str, port: int, minutes: int) -> None:
	assert context.configuration is not None
	intranet = context.configuration.intranet
	assert (intranet.enabled, intranet.address, intranet.port, intranet.validation) == (False, address, port, minutes)


@then("l'intranet n'a pas de certificat donné")
def no_certificate(context: Context) -> None:
	assert context.configuration is not None
	assert (context.configuration.intranet.certificate, context.configuration.intranet.key) == (None, None)


@then(parsers.parse("la configuration est refusée en nommant « {key} »"))
def refused(context: Context, key: str) -> None:
	assert context.configuration is None
	assert key in context.error, context.error


@then(
	parsers.parse(
		"l'intranet est allumé, avec le certificat « {certificate_} » et la clé « {key} », à côté du fichier de"
		" configuration"
	)
)
def given_certificate(context: Context, certificate_: str, key: str) -> None:
	assert context.configuration is not None
	intranet = context.configuration.intranet
	assert intranet.enabled
	assert intranet.certificate == context.directory / certificate_
	assert intranet.key == context.directory / key


# ─── Certificat ────────────────────────────────────────────


@when(
	parsers.re(r"le certificat de l'intranet est assuré pour les noms (?P<names>.+) et les adresses (?P<addresses>.+)")
)
def ensure(context: Context, names: str, addresses: str) -> None:
	context.pair = certificate.default(context.directory / "etat")
	context.generated.append(certificate.ensure(context.pair, _marks(names), _marks(addresses)))


@then("un certificat a été généré")
def generated_one(context: Context) -> None:
	assert context.generated == [True]


@then("un seul certificat a été généré")
def generated_once(context: Context) -> None:
	assert context.generated == [True, False]


@then("deux certificats ont été générés")
def generated_twice(context: Context) -> None:
	assert context.generated == [True, True]


def _text(context: Context) -> str:
	assert context.pair is not None
	return subprocess.run(
		["openssl", "x509", "-in", str(context.pair.certificate), "-noout", "-text"],
		capture_output=True,
		text=True,
		check=True,
	).stdout


@then(parsers.re(r"le certificat nomme (?P<entries>.+)"))
def names_listed(context: Context, entries: str) -> None:
	text = _text(context)
	for entry in _marks(entries):
		assert entry in text, (entry, text)


@then("le certificat est un certificat de serveur, auto-signé, valable 825 jours")
def server_certificate(context: Context) -> None:
	text = _text(context)
	assert "TLS Web Server Authentication" in text
	assert "CA:FALSE" in text
	assert context.pair is not None
	dates = subprocess.run(
		["openssl", "x509", "-in", str(context.pair.certificate), "-noout", "-startdate", "-enddate"],
		capture_output=True,
		text=True,
		check=True,
	).stdout
	start, end = dates.splitlines()
	parsed = []
	for line in (start, end):
		parsed.append(ssl.cert_time_to_seconds(line.partition("=")[2]))
	assert round((parsed[1] - parsed[0]) / 86400) == certificate.DAYS
	issuer = subprocess.run(
		["openssl", "verify", "-CAfile", str(context.pair.certificate), str(context.pair.certificate)],
		capture_output=True,
		text=True,
		check=False,
	)
	assert issuer.returncode == 0, issuer.stdout + issuer.stderr


@then("seule le compte peut lire la clé du certificat")
def private_key(context: Context) -> None:
	assert context.pair is not None
	assert context.pair.key.stat().st_mode & 0o777 == 0o600


@given("un certificat donné dans la configuration de l'intranet")
def certificate_given(context: Context) -> None:
	path = _write(context, '[intranet]\nenabled = true\ncertificate = "donne/cert.pem"\nkey = "donne/cle.pem"\n')
	given_pair = certificate.Pair(context.directory / "donne" / "cert.pem", context.directory / "donne" / "cle.pem")
	certificate.generate(given_pair, ["ailleurs"], ["192.0.2.1"])
	context.configuration = load(path)
	context.pair = given_pair


@when("Machin intranet choisit son certificat")
def choose(context: Context, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setenv("STATE_DIRECTORY", str(context.directory / "etat"))
	before = context.pair.certificate.read_bytes()  # type: ignore[union-attr]
	assert context.configuration is not None
	chosen = server.pair(context.configuration.intranet)
	assert context.pair is not None
	assert chosen == context.pair
	assert context.pair.certificate.read_bytes() == before


@then("il prend le certificat donné, sans en générer")
def none_generated(context: Context) -> None:
	assert not (context.directory / "etat").exists()


@given(parsers.re(r"le poste « (?P<name>[^»]+) », aux adresses (?P<addresses>.+)"))
def computer(monkeypatch: pytest.MonkeyPatch, name: str, addresses: str) -> None:
	found = [*_marks(addresses), network.LOOPBACK]
	monkeypatch.setattr(network, "addresses", lambda: found)
	monkeypatch.setattr(network, "names", lambda: [name, "localhost"])


@then(parsers.re(r"les adresses à donner pour « (?P<address>[^»]+) », port (?P<port>\d+), sont (?P<expected>.+)"))
def to_give(address: str, port: str, expected: str) -> None:
	assert network.to_give(address, int(port)) == _marks(expected)


# ─── Serveur ───────────────────────────────────────────────


def _free_port() -> int:
	with socket.socket() as probe:
		probe.bind(("127.0.0.1", 0))
		return int(probe.getsockname()[1])


@when(parsers.re(r"je lance Machin intranet avec l'intranet (?P<state>allumé|éteint)"))
def launch(context: Context, state: str) -> None:
	context.port = _free_port()
	enabled = "true"
	if state == "éteint":
		enabled = "false"
	path = _write(context, f'[intranet]\nenabled = {enabled}\naddress = "127.0.0.1"\nport = {context.port}\n')
	environment = dict(os.environ, STATE_DIRECTORY=str(context.directory / "etat"))
	context.process = subprocess.Popen(
		[str(EXECUTABLE), "--config", str(path)],
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
		env=environment,
	)
	if state == "éteint":
		return
	deadline = time.monotonic() + STARTUP
	while time.monotonic() < deadline:
		assert context.process.poll() is None, context.process.communicate()[0]
		try:
			with socket.create_connection(("127.0.0.1", context.port), timeout=0.5):
				return
		except OSError:
			time.sleep(0.1)
	raise AssertionError("Machin intranet n'écoute pas")


def _request(context: Context, method: str, path: str) -> None:
	secured = ssl.create_default_context(cafile=str(certificate.default(context.directory / "etat").certificate))
	secured.check_hostname = False
	connection = http.client.HTTPSConnection("127.0.0.1", context.port, context=secured, timeout=10)
	connection.request(method, path)
	context.response = connection.getresponse()
	context.body = context.response.read()
	connection.close()


@then(
	parsers.re(
		r"une requête HTTPS « (?P<method>[A-Z]+) (?P<path>[^»]+) » reçoit (?P<status>\d+)(?:, une page « (?P<title>[^»]+) »)?"
	)
)
def https_request(context: Context, method: str, path: str, status: str, title: str | None) -> None:
	_request(context, method, path)
	assert context.response is not None
	assert context.response.status == int(status), context.body
	if title is not None:
		assert title.encode() in context.body


@then("la réponse a les en-têtes :")
def headers(context: Context, datatable: list[list[str]]) -> None:
	assert context.response is not None
	for name, value in datatable[1:]:
		assert context.response.getheader(name.strip()) == value.strip(), name


@then("la réponse ne nomme pas son serveur")
def no_server(context: Context) -> None:
	assert context.response is not None
	assert context.response.getheader("server") is None


@then("une requête en HTTP clair ne reçoit aucune réponse HTTP")
def plain(context: Context) -> None:
	connection = http.client.HTTPConnection("127.0.0.1", context.port, timeout=5)
	with pytest.raises((http.client.HTTPException, OSError)):
		connection.request("GET", "/")
		connection.getresponse()
	connection.close()


def _stop(context: Context) -> int:
	assert context.process is not None
	if context.process.poll() is None:
		context.process.send_signal(signal.SIGTERM)
	output, _error = context.process.communicate(timeout=STARTUP)
	context.journal = output
	return context.process.returncode


@when("Machin intranet reçoit SIGTERM")
def terminate(context: Context) -> None:
	assert context.process is not None
	context.process.send_signal(signal.SIGTERM)


@then(parsers.parse("Machin intranet s'arrête avec le code {code:d}"))
def stopped(context: Context, code: int) -> None:
	assert context.process is not None
	output, _error = context.process.communicate(timeout=STARTUP)
	context.journal = output
	assert context.process.returncode == code, output


@then(parsers.parse("son journal dit « {text} »"))
def journal_says(context: Context, text: str) -> None:
	assert text in context.journal, context.journal


@then("son journal donne l'adresse à donner et l'empreinte du certificat")
def journal_address(context: Context) -> None:
	_stop(context)
	assert f"https://127.0.0.1:{context.port}/" in context.journal, context.journal
	fingerprint = certificate.fingerprint(certificate.default(context.directory / "etat").certificate)
	assert fingerprint in context.journal, context.journal


@then("son PID est noté dans son répertoire d'état")
def pid_recorded(context: Context) -> None:
	assert context.process is not None
	assert process.running_pid(context.directory / "etat") == context.process.pid


@then("son PID n'est plus noté")
def pid_removed(context: Context) -> None:
	assert not (context.directory / "etat" / process.PID_FILE).exists()


# ─── Mode test (https://github.com/dascritch/machincast/issues/549) ───


@given("un poste sans le service de diffusion, le répertoire d'exécution du compte dans un répertoire temporaire")
def without_service(context: Context, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setenv("XDG_RUNTIME_DIR", str(context.directory / "run"))
	monkeypatch.setenv(service.RUNTIME_ENVIRONMENT, str(context.directory / "absent" / "machincast"))
	monkeypatch.setenv(service.INTRANET_RUNTIME_ENVIRONMENT, str(context.directory / "absent" / "intranet"))


@when("je charge la configuration de test, sans section [player]")
def without_player(context: Context) -> None:
	kept = []
	skipping = False
	for line in sample_configuration_path().read_text(encoding="utf-8").splitlines():
		if line.startswith("["):
			skipping = line.strip() == "[player]"
		if not skipping:
			kept.append(line)
	path = context.directory / "machincast.toml"
	path.write_text("\n".join(kept) + "\n", encoding="utf-8")
	context.configuration = load(path)


@then(parsers.parse("la socket de l'intranet est « {intranet} », à côté de la socket d'état « {state} »"))
def sockets_side_by_side(context: Context, intranet: str, state: str) -> None:
	assert context.configuration is not None
	player = context.configuration.player
	assert player.state_socket == context.directory / "run" / "machincast" / state
	assert player.intranet_socket == player.state_socket.with_name(intranet)


@then("un Machin player qui diffuse sur ces sockets donne son état à Machin intranet, par la socket de l'intranet")
def shared_state(context: Context) -> None:
	assert context.configuration is not None
	player = context.configuration.player
	sockets = StateSocket(player.state_socket, player.intranet_socket)
	sockets.open_()
	try:
		sockets.publish({"state": "playing", "current": None, "next": None, "upcoming": []})
		assert live.read_state(player.intranet_socket)["state"] == "playing"
	finally:
		sockets.shut_down()
