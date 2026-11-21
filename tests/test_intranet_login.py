"""Scénarios de la connexion à l'intranet, validée au pupitre (https://github.com/dascritch/machincast/issues/539).

Les requêtes passent directement à l'application ASGI (tests.asgi_client), sur la base de test, au rôle
machincast_intranet.
"""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.configuration import Intranet as Settings
from machincast.database import Role, open_connection
from machincast.interface.queries import api_users
from machincast.intranet import sessions
from machincast.intranet.app import Intranet
from machincast.intranet.pages import Pages
from machincast.intranet.portal import Portal, Throttle
from tests.asgi_client import Answer, call
from tests.database_fixtures import sample_database_parameters
from tests.interface_steps import Connection

scenarios("intranet_login.feature")

COOKIE_PREFIX = f"{sessions.COOKIE}="


@dataclass
class Visit:
	application: Intranet
	answer: Answer | None = None
	token: str | None = None


def connect() -> psycopg.Connection[TupleRow]:
	socket, database = sample_database_parameters()
	return open_connection(socket, database, Role.INTRANET)


@given("l'application de l'intranet sur la base de test", target_fixture="visit")
def application(empty_database: Connection, tmp_path: Path) -> Visit:
	del empty_database
	portal = Portal(Settings(enabled=True), connect)
	home = Pages(portal, connect, tmp_path / "lecture.sock", "Radio Thune")
	return Visit(Intranet({**portal.routes(), **home.routes()}))


def _keep(visit: Visit, answer: Answer) -> None:
	"""La réponse, et le jeton qu'elle pose, comme le garderait le navigateur."""
	visit.answer = answer
	posed = answer.header("set-cookie")
	if (posed is not None) and (posed.startswith(COOKIE_PREFIX)):
		value = posed[len(COOKIE_PREFIX) :].split(";")[0]
		visit.token = (value) or (None)


def _cookie(visit: Visit) -> dict[str, str]:
	if visit.token is None:
		return {}
	return {"cookie": f"{sessions.COOKIE}={visit.token}"}


@when(parsers.re(r"je demande « (?P<method>[A-Z]+) (?P<path>[^»]+) »$"))
def ask(visit: Visit, method: str, path: str) -> None:
	_keep(visit, call(visit.application, method, path, headers=_cookie(visit)))


@when(parsers.re(r"je demande « GET / », la session dans le (?P<rank>premier|second) de deux en-têtes Cookie"))
def ask_split_cookies(visit: Visit, rank: str) -> None:
	"""https://github.com/dascritch/machincast/issues/551"""
	other = ("cookie", "preferences=sombre; langue=fr")
	session = ("cookie", f"{sessions.COOKIE}={visit.token}")
	repeated = [session, other]
	if rank == "second":
		repeated = [other, session]
	_keep(visit, call(visit.application, "GET", "/", repeated=repeated))


@when(parsers.parse("je demande « GET / » avec le jeton en « Authorization: Bearer », sans cookie"))
def ask_bearer(visit: Visit) -> None:
	_keep(visit, call(visit.application, "GET", "/", headers={"authorization": f"Bearer {visit.token}"}))


def _login(visit: Visit, name: str, password: str, origin: str | None = None, address: str = "10.0.0.31") -> None:
	"""Comme le navigateur : avec le cookie qu'il a déjà, s'il en a un."""
	headers = _cookie(visit)
	if origin is not None:
		headers["origin"] = origin
	answer = call(
		visit.application, "POST", "/login", form={"name": name, "password": password}, headers=headers, client=address
	)
	_keep(visit, answer)


@given(parsers.parse("je me suis connecté en « {name} », mot de passe « {password} »"))
@when(parsers.parse("je me connecte en « {name} », mot de passe « {password} »"))
def login(visit: Visit, name: str, password: str) -> None:
	_login(visit, name, password)


@when(parsers.parse("je me connecte en « {name} », mot de passe « {password} », depuis l'origine « {origin} »"))
def login_from(visit: Visit, name: str, password: str, origin: str) -> None:
	_login(visit, name, password, origin)


@when(parsers.parse("je me connecte en « {name} », mot de passe « {password} », avec les en-têtes « {given} »"))
def login_with_headers(visit: Visit, name: str, password: str, given: str) -> None:
	"""https://github.com/dascritch/machincast/issues/571"""
	headers = _cookie(visit)
	for pair in given.split("; "):
		key, value = pair.split(": ", 1)
		headers[key] = value
	answer = call(
		visit.application,
		"POST",
		"/login",
		form={"name": name, "password": password},
		headers=headers,
		client="10.0.0.31",
	)
	_keep(visit, answer)


@when(parsers.parse("je me connecte en « {name} », mot de passe « {password} », depuis l'adresse « {address} »"))
def login_from_address(visit: Visit, name: str, password: str, address: str) -> None:
	_login(visit, name, password, address=address)


@given(parsers.parse("je me suis connecté depuis un autre navigateur en « {name} », mot de passe « {password} »"))
@when(parsers.parse("je me connecte depuis un autre navigateur en « {name} », mot de passe « {password} »"))
def login_elsewhere(visit: Visit, name: str, password: str) -> None:
	"""Un autre navigateur, sans le cookie de celui d'avant."""
	visit.token = None
	_login(visit, name, password)


@when("je me déconnecte")
def logout(visit: Visit) -> None:
	_keep(visit, call(visit.application, "POST", "/logout", headers=_cookie(visit)))


@when(parsers.parse("je me connecte {count:d} fois en « {name} », mot de passe « {password} »"))
def login_again(visit: Visit, count: int, name: str, password: str) -> None:
	for _time in range(count):
		_login(visit, name, password)


def _row(empty_database: Connection) -> tuple[object, ...]:
	row = empty_database.execute(
		"SELECT s.state::text, s.code, host(s.source_ip), s.user_agent, s.validate_before - s.created_at,"
		" s.expires_at - s.validated_at, s.token_hash, u.name, s.id FROM api_sessions s"
		" JOIN api_users u ON u.id = s.user_id ORDER BY s.id DESC LIMIT 1"
	).fetchone()
	assert row is not None
	return row


def _code(visit: Visit, empty_database: Connection, grouped: bool = False) -> None:
	code = _row(empty_database)[1]
	given = str((code) or ("000000"))
	if grouped:
		given = f"{given[:3]} {given[3:]}"
	_keep(visit, call(visit.application, "POST", "/validation", form={"code": given}, headers=_cookie(visit)))


@given("j'ai saisi le code donné au pupitre")
@when("je saisis le code donné au pupitre")
def enter_code(visit: Visit, empty_database: Connection) -> None:
	_code(visit, empty_database)


@when("je saisis le code donné au pupitre, en deux groupes de trois chiffres")
def enter_grouped_code(visit: Visit, empty_database: Connection) -> None:
	_code(visit, empty_database, grouped=True)


def _wrong(visit: Visit, empty_database: Connection) -> None:
	code = str(_row(empty_database)[1])
	wrong = f"{(int(code) + 1) % 1_000_000:06d}"
	_keep(visit, call(visit.application, "POST", "/validation", form={"code": wrong}, headers=_cookie(visit)))


@given("j'ai saisi un code faux")
@when("je saisis un code faux")
def enter_wrong(visit: Visit, empty_database: Connection) -> None:
	_wrong(visit, empty_database)


@given(parsers.parse("j'ai saisi un code faux {count:d} fois"))
@when(parsers.parse("je saisis un code faux {count:d} fois"))
def enter_wrong_again(visit: Visit, empty_database: Connection, count: int) -> None:
	for _time in range(count):
		_wrong(visit, empty_database)


@given("le délai de validation est passé")
def validation_late(empty_database: Connection) -> None:
	empty_database.execute("UPDATE api_sessions SET validate_before = clock_timestamp() - interval '1 second'")


@given(parsers.parse("le compte « {name} » est désactivé"))
def disabled(empty_database: Connection, name: str) -> None:
	empty_database.execute("UPDATE api_users SET disabled_at = clock_timestamp() WHERE name = %s", (name,))


@when(parsers.parse("j'envoie à « {path} » un formulaire de {size:d} octets"))
def huge(visit: Visit, path: str, size: int) -> None:
	_keep(visit, call(visit.application, "POST", path, form={"name": "x" * size, "password": ""}))


def _answer(visit: Visit) -> Answer:
	assert visit.answer is not None
	return visit.answer


@then(parsers.parse("la réponse est {status:d}, vers « {location} »"))
def redirected(visit: Visit, status: int, location: str) -> None:
	assert (_answer(visit).status, _answer(visit).header("location")) == (status, location)


@then(parsers.re(r"la réponse est (?P<status>\d+)$"))
def status_only(visit: Visit, status: str) -> None:
	assert _answer(visit).status == int(status), _answer(visit).text()


@then(parsers.parse("la réponse est {status:d}, et dit « {text} »"))
def says(visit: Visit, status: int, text: str) -> None:
	assert _answer(visit).status == status, _answer(visit).text()
	assert text in _answer(visit).text().replace("&#x27;", "'"), _answer(visit).text()


@then(
	"la réponse est 200, une page qui demande le nom d'utilisateur et le mot de passe, sans récupération de mot de passe"
)
def login_form(visit: Visit) -> None:
	page = _answer(visit).text()
	assert _answer(visit).status == 200
	assert 'name="name"' in page
	assert 'type="password"' in page
	assert 'action="/login"' in page
	assert "oubli" not in page.lower()


@then("aucun cookie de session n'est posé")
def no_cookie(visit: Visit) -> None:
	assert _answer(visit).header("set-cookie") is None


@then("aucune session n'est ouverte")
def no_session(empty_database: Connection) -> None:
	assert empty_database.execute("SELECT count(*) FROM api_sessions").fetchone() == (0,)


@then("le cookie de session est posé, Secure, HttpOnly et SameSite=Strict")
def cookie_posed(visit: Visit) -> None:
	posed = _answer(visit).header("set-cookie")
	assert posed is not None
	for attribute in ("Secure", "HttpOnly", "SameSite=Strict", "Path=/"):
		assert attribute in posed.split("; "), posed
	assert visit.token is not None


@then("le cookie de session est effacé")
def cookie_cleared(visit: Visit) -> None:
	posed = _answer(visit).header("set-cookie")
	assert posed is not None
	assert posed.startswith(f"{COOKIE_PREFIX};")
	assert "Max-Age=0" in posed


@then(
	parsers.parse(
		"la base a une session à valider de « {name} », depuis « {address} », navigateur « {agent} », avec un code"
		" à 6 chiffres, à valider sous {minutes:d} minutes"
	)
)
def pending_session(empty_database: Connection, name: str, address: str, agent: str, minutes: int) -> None:
	state, code, source, user_agent, delay, _validity, _token, user, _identifier = _row(empty_database)
	assert (state, source, user_agent, user) == ("pending", address, agent, name)
	assert str(code).isdigit()
	assert len(str(code)) == 6
	assert isinstance(delay, timedelta)
	assert abs(delay - timedelta(minutes=minutes)) < timedelta(seconds=5)


@then("la base ne garde que l'empreinte SHA-256 du cookie")
def fingerprint_only(visit: Visit, empty_database: Connection) -> None:
	token_hash = _row(empty_database)[6]
	assert visit.token is not None
	assert token_hash == sessions.fingerprint(visit.token)
	assert visit.token not in str(token_hash)


@then(parsers.parse("la session est valide, pour {hours:d} heures"))
def valid(empty_database: Connection, hours: int) -> None:
	state, code, *_rest = _row(empty_database)
	validity = _row(empty_database)[5]
	assert (state, code) == ("valid", None)
	assert validity == timedelta(hours=hours)


@then("la session est invalide")
def invalid(empty_database: Connection) -> None:
	assert _row(empty_database)[0] == "invalid"


@given("le pupitre a accepté la connexion")
@when("le pupitre accepte la connexion")
def desk_accepts(empty_database: Connection) -> None:
	"""Comme « Accepter » dans le bandeau du pupitre, au rôle de l'interface."""
	api_users.accept(empty_database, int(str(_row(empty_database)[8])))


@then("la session est à valider, sans code faux compté")
def pending_untried(empty_database: Connection) -> None:
	found = empty_database.execute("SELECT state::text, attempts FROM api_sessions ORDER BY id DESC LIMIT 1").fetchone()
	assert found == ("pending", 0)


@then("aucune nouvelle session n'est ouverte")
def no_new_session(empty_database: Connection) -> None:
	assert empty_database.execute("SELECT count(*) FROM api_sessions").fetchone() == (1,)


@then("la session est à valider")
def still_pending(empty_database: Connection) -> None:
	assert _row(empty_database)[0] == "pending"


@then(parsers.re(r"« (?P<name>[^»]+) » a (?P<count>\d+) sessions? à valider"))
def pending_count(empty_database: Connection, name: str, count: str) -> None:
	found = empty_database.execute(
		"SELECT count(*) FROM api_sessions s JOIN api_users u ON u.id = s.user_id"
		" WHERE u.name = %s AND s.state = 'pending'",
		(name,),
	).fetchone()
	assert found == (int(count),)


@given("la session valide a expiré")
def expired(empty_database: Connection) -> None:
	empty_database.execute(
		"UPDATE api_sessions SET expires_at = clock_timestamp() - interval '1 second' WHERE id = %s",
		(int(str(_row(empty_database)[8])),),
	)


@then(parsers.parse("la base garde la session à l'état « {state} », sans l'avoir écrite"))
def unwritten(empty_database: Connection, state: str) -> None:
	assert (_row(empty_database)[0], _row(empty_database)[1]) == (state, None)
	row = empty_database.execute("SELECT ended_at FROM api_sessions ORDER BY id DESC LIMIT 1").fetchone()
	assert row == (None,)


@dataclass
class Moments:
	now: float = 1000.0


@given("un freinage à l'horloge imitée", target_fixture="throttle")
def imitated_throttle() -> tuple[Throttle, Moments]:
	moments = Moments()
	return Throttle(clock=lambda: moments.now), moments


@when(parsers.parse("l'adresse « {first} » échoue, puis, {minutes:d} minutes plus tard, l'adresse « {second} »"))
def two_failures(throttle: tuple[Throttle, Moments], first: str, minutes: int, second: str) -> None:
	held, moments = throttle
	held.failed(first)
	moments.now += minutes * 60
	held.failed(second)


@then(parsers.parse("le freinage ne se souvient que de « {address} »"))
def remembers_only(throttle: tuple[Throttle, Moments], address: str) -> None:
	assert list(throttle[0].failures) == [address]
