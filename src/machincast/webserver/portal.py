"""La connexion à l'intranet, validée au pupitre (https://github.com/dascritch/machincast/issues/539).

- GET /login : la mire, nom d'utilisateur et mot de passe, sans récupération de mot de passe.
- POST /login : des identifiants valides ouvrent une session à valider, son cookie posé, et mènent à /validation ;
  sinon 401, sans dire si le nom existe. Trop d'échecs d'une même adresse la font attendre (Throttle).
- GET /validation : la page qui dit qu'une action doit être faite au pupitre, et demande le code à 6 chiffres que
  l'interface y montre, une fois la connexion acceptée ; un code saisi avant n'est pas essayé
  (https://github.com/dascritch/machincast/issues/547).
- POST /validation : le code exact valide la session, et mène à l'accueil ; un code faux le redemande ; au cinquième,
  ou le délai passé, la session est invalide, et il faut se reconnecter. Les codes faux sont freinés par adresse et par
  compte, et un compte n'a que deux sessions à valider à la fois : un mot de passe volé ne suffit pas à forcer le
  code (https://github.com/dascritch/machincast/issues/547).
- POST /logout : la session devient invalide, son cookie s'efface.
- GET / : l'accueil (machincast.webserver.home), pour une session valide ; sinon la mire, ou la page de validation.

Chaque connexion, acceptée ou refusée, et chaque code, laisse une ligne au journal
(https://github.com/dascritch/machincast/issues/578) : l'adresse du client entre crochets en tête du message, que
reconnaît un analyseur de journal (fail2ban), puis le nom saisi (shown), jamais le mot de passe ni le code ; un refus en
WARNING.

Le cookie de session est Secure, HttpOnly, SameSite=Strict ; le même jeton sert l'API, en cookie ou en
« Authorization: Bearer ». Les accès à la base passent par asyncio.to_thread : une connexion par requête, au rôle
machincast_webserver.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import psycopg
from psycopg.rows import TupleRow

from machincast.clock import Clock, SystemClock
from machincast.configuration import Intranet as Settings
from machincast.i18n import _
from machincast.webserver import rendering, sessions
from machincast.webserver.app import HTML, TITLE, Request, Response, Route, redirect, text
from machincast.webserver.sessions import COOKIE, Session

Connection = psycopg.Connection[TupleRow]
Connect = Callable[[], Connection]

log = logging.getLogger(__name__)

FAILURES = 5
"""Échecs d'une même adresse, ou codes faux d'un même compte, avant d'attendre."""
PENALTY = 15 * 60
"""Secondes d'attente, après FAILURES échecs, et fenêtre où ils se comptent."""
ACCOUNT = "compte:"
"""Le préfixe des codes faux d'un compte, dans Throttle, à côté de ceux d'une adresse."""
SHOWN_NAME = 64
"""Caractères d'un nom saisi, au plus, dans le journal."""
UNPRINTABLE = "\ufffd"


def shown(name: str) -> str:
	"""Le nom saisi, pour le journal : sur une seule ligne, sans caractère de contrôle, coupé à SHOWN_NAME caractères. Il
	ne peut pas contrefaire une ligne du journal (https://github.com/dascritch/machincast/issues/578)."""
	characters = []
	for character in name[:SHOWN_NAME]:
		if character.isprintable():
			characters.append(character)
		else:
			characters.append(UNPRINTABLE)
	text = "".join(characters)
	if len(name) > SHOWN_NAME:
		text += "…"
	return text


def cookie(value: str, max_age: int) -> tuple[str, str]:
	"""L'en-tête qui pose le cookie de session : jamais en clair, jamais lu par un script, jamais envoyé d'ailleurs."""
	return ("set-cookie", f"{COOKIE}={value}; Max-Age={max_age}; Path=/; Secure; HttpOnly; SameSite=Strict")


def browser_cookie(value: str) -> tuple[str, str]:
	"""L'en-tête qui pose le cookie d'un navigateur connu (https://github.com/dascritch/machincast/issues/601), comme
	celui de la session : jamais en clair, jamais lu par un script, jamais envoyé d'ailleurs."""
	max_age = sessions.BROWSER_DAYS * 86400
	return (
		"set-cookie",
		f"{sessions.BROWSER_COOKIE}={value}; Max-Age={max_age}; Path=/; Secure; HttpOnly; SameSite=Strict",
	)


def bearer(request: Request) -> str | None:
	"""Le jeton de la requête : son cookie de session, ou « Authorization: Bearer »."""
	given = request.cookie(COOKIE)
	if given:
		return given
	authorization = request.headers.get("authorization", "")
	scheme, _separator, value = authorization.partition(" ")
	if (scheme.lower() == "bearer") and (value.strip() != ""):
		return value.strip()
	return None


@dataclass
class Throttle:
	"""Des échecs par clé, une adresse ou un compte, en mémoire : au-delà de FAILURES dans PENALTY secondes, elle
	attend."""

	failures: dict[str, list[float]] = field(default_factory=dict)
	clock: Callable[[], float] = time.monotonic

	def _recent(self, address: str) -> list[float]:
		now = self.clock()
		kept = []
		for moment in self.failures.get(address, []):
			if now - moment < PENALTY:
				kept.append(moment)
		self.failures[address] = kept
		return kept

	def blocked(self, address: str) -> bool:
		return len(self._recent(address)) >= FAILURES

	def failed(self, address: str) -> None:
		self._purge()
		self._recent(address).append(self.clock())

	def _purge(self) -> None:
		"""Oublie les clés sans échec récent : la mémoire ne grossit pas avec les adresses qui changent
		(https://github.com/dascritch/machincast/issues/553)."""
		now = self.clock()
		forgotten = []
		for key, moments in self.failures.items():
			if (moments == []) or (now - moments[-1] >= PENALTY):
				forgotten.append(key)
		for key in forgotten:
			del self.failures[key]

	def succeeded(self, address: str) -> None:
		self.failures.pop(address, None)


def _page(template: str, status: int, /, **context: Any) -> Response:
	text_ = rendering.render(template, machin=TITLE, head=rendering.html(""), **context)
	return Response(status, text_.encode("utf-8"), HTML)


def login_page(message: str = "", name: str = "", status: int = 200) -> Response:
	"""La mire (login.html.jinja) : le nom gardé après un refus, et ce qui l'a refusé."""
	return _page("login.html.jinja", status, title=_("Connection"), name=name, message=message)


def validation_page(message: str = "", status: int = 200, *, stage: str = "code") -> Response:
	"""La page de la validation (validation.html.jinja), et ce qui a refusé le code précédent, selon ce que la session
	attend : « code », le code donné au pupitre ; « waiting », l'acceptation au pupitre, sans code, la page se relisant
	toutes les 5 secondes (https://github.com/dascritch/machincast/issues/600) ; « totp », le code de l'application
	d'authentification (https://github.com/dascritch/machincast/issues/601)."""
	explanation = _(
		"An action must be done at the studio desk: MachinCast shows there your name, your browser and your "
		"address. Once your connection is accepted there, the studio gives you a 6-digit code: enter it "
		"here."
	)
	field = _("6-digit code")
	title = _("Validation at the desk")
	if stage == "waiting":
		explanation = _(
			"An action must be done at the studio desk: MachinCast shows there your name, your browser and your "
			"address. Once your connection is accepted there, this page goes on by itself."
		)
		field = ""
	if stage == "totp":
		title = _("Second factor")
		explanation = _("Enter the code that your authentication app shows for this account.")
		field = _("The 6-digit code of your authentication app")
	return _page(
		"validation.html.jinja",
		status,
		title=title,
		explanation=explanation,
		message=message,
		field=field,
	)


class Portal:
	"""Les routes de la connexion, et la session de chaque requête."""

	def __init__(
		self,
		settings: Settings,
		connect: Connect,
		throttle: Throttle | None = None,
		codes: Throttle | None = None,
		*,
		clock: Clock | None = None,
	) -> None:
		self.settings = settings
		self.connect = connect
		self.clock: Clock = (clock) or (SystemClock())
		"""L'heure des codes de l'application d'authentification (https://github.com/dascritch/machincast/issues/601)."""
		self.used: dict[int, int] = {}
		"""Le dernier pas accepté de l'application d'authentification de chaque compte : un code ne sert qu'une fois."""
		self.throttle = (throttle) or (Throttle())
		"""Les mots de passe refusés, par adresse ; une connexion réussie les efface."""
		self.codes = (codes) or (Throttle())
		"""Les codes faux, par adresse et par compte (https://github.com/dascritch/machincast/issues/547) : une connexion
		réussie ne les efface pas, seule une session validée au pupitre."""

	def routes(self) -> dict[tuple[str, str], Route]:
		return {
			("GET", "/login"): self.login_form,
			("POST", "/login"): self.login,
			("GET", "/validation"): self.validation_form,
			("POST", "/validation"): self.validation,
			("POST", "/logout"): self.logout,
		}

	async def _database[T](self, action: Callable[[Connection], T]) -> T:
		def run() -> T:
			with self.connect() as connection:
				return action(connection)

		return await asyncio.to_thread(run)

	async def session(self, request: Request) -> Session | None:
		"""La session de la requête, quel que soit son état ; None sans jeton connu."""
		value = bearer(request)
		if value is None:
			return None
		return await self._database(lambda connection: sessions.find(connection, value))

	async def valid(self, request: Request) -> Session | None:
		"""La session valide de la requête ; None sinon."""
		found = await self.session(request)
		if (found is None) or (found.state != "valid"):
			return None
		return found

	async def login_form(self, _request: Request) -> Response:
		return login_page()

	def _codes_blocked(self, address: str, name: str) -> bool:
		return (self.codes.blocked(address)) or (self.codes.blocked(f"{ACCOUNT}{name}"))

	async def login(self, request: Request) -> Response:
		"""Des identifiants valides ouvrent une session à valider ; sinon la mire, 401. Trop de mots de passe refusés
		d'une adresse, ou de codes faux d'une adresse ou d'un compte, font attendre, avant même de lire le mot de passe :
		la réponse ne dit pas s'il était bon."""
		address = request.client
		form = request.form()
		name = form.get("name", "").strip()
		password = form.get("password", "")
		if (self.throttle.blocked(address)) or (self._codes_blocked(address, name)):
			log.warning(
				_(
					"[{address}] intranet connection refused, user “{name}”: too many failed attempts, waiting a quarter "
					"of an hour"
				).format(address=address, name=shown(name))
			)
			return login_page(_("Too many failed attempts: wait a quarter of an hour."), status=429)
		user = await self._database(lambda connection: sessions.authenticate(connection, name, password))
		if user is None:
			self.throttle.failed(address)
			log.warning(
				_(
					"[{address}] intranet connection refused, user “{name}”: unknown user, disabled account or wrong "
					"password"
				).format(address=address, name=shown(name))
			)
			return login_page(_("Unknown user, disabled account or wrong password."), name, 401)
		self.throttle.succeeded(address)
		previous = bearer(request)
		if previous is not None:
			# Se reconnecter du même navigateur abandonne sa session d'avant, à valider ou valide.
			await self._database(lambda connection: sessions.end(connection, previous))
		browser = request.cookie(sessions.BROWSER_COOKIE)
		known = await self._database(lambda connection: sessions.known_browser(connection, user, browser))
		desk, with_code, totp = self._steps(known=known)
		if totp:
			secret = await self._database(lambda connection: sessions.totp_secret(connection, user))
			if secret is None:
				log.warning(
					_("[{address}] intranet connection refused, user “{name}”: no authentication app").format(
						address=address, name=shown(name)
					)
				)
				return login_page(
					_("This account has no authentication app: have it set up at the studio, in the API tab."),
					name,
					403,
				)
		client = (request.headers.get("user-agent", ""), address)
		if (not desk) and (not totp):
			return await self._without_validation(user, client, name, known=known)
		return await self._pending(user, client, name, (desk, with_code, totp))

	def _steps(self, *, known: bool) -> tuple[bool, bool, bool]:
		"""Ce que la connexion passe : le pupitre, son code, l'application d'authentification. Un navigateur inconnu
		passe la première connexion (https://github.com/dascritch/machincast/issues/600), puis le second facteur ; un
		navigateur connu, le second facteur seul (https://github.com/dascritch/machincast/issues/601)."""
		factor = self.settings.second_factor
		desk = factor == "desk"
		with_code = False
		if not known:
			desk = (desk) or (self.settings.first_login != "none")
			with_code = self.settings.first_login == "desk_code"
		return desk, with_code, factor == "totp"

	async def _pending(self, user: int, client: tuple[str, str], name: str, steps: tuple[bool, bool, bool]) -> Response:
		"""Une session à valider, et la page de la validation ; 429 si le compte en a déjà MAXIMUM_PENDING."""
		address = client[1]
		desk, with_code, totp = steps
		value = sessions.token()
		minutes = self.settings.validation
		given = await self._database(
			lambda connection: sessions.open_pending(
				connection, user, value, minutes, client, with_code=with_code, steps=(desk, totp)
			)
		)
		if given is None:
			log.info(
				_(
					"[{address}] intranet connection refused, user “{name}”: too many connections waiting for validation"
				).format(address=address, name=shown(name))
			)
			return login_page(
				_(
					"This account already has {count} connections waiting for validation: have them validated or "
					"refused at the desk, or wait for their delay."
				).format(count=sessions.MAXIMUM_PENDING),
				name,
				429,
			)
		max_age = (minutes * 60) + (self.settings.session * 3600)
		said = _("[{address}] intranet connection of “{name}”, to validate at the desk")
		if not desk:
			said = _("[{address}] intranet connection of “{name}”, waiting for the code of its authentication app")
		log.info(said.format(address=address, name=shown(name)))
		return redirect("/validation", [cookie(value, max_age)])

	async def _without_validation(self, user: int, client: tuple[str, str], name: str, *, known: bool) -> Response:
		"""Ni pupitre ni application d'authentification : une session valide aussitôt, et l'accueil. Un navigateur
		inconnu, sans validation de la première connexion, le journal le dit, en WARNING
		(https://github.com/dascritch/machincast/issues/600) ; un navigateur connu, sans second facteur, en INFO
		(https://github.com/dascritch/machincast/issues/601)."""
		hours = self.settings.session
		value = sessions.token()
		await self._database(lambda connection: sessions.open_valid(connection, user, value, hours, client))
		if known:
			log.info(
				_("[{address}] intranet connection of “{name}”, from a known browser").format(
					address=client[1], name=shown(name)
				)
			)
			return redirect("/", [cookie(value, hours * 3600)])
		log.warning(
			_("[{address}] intranet connection of “{name}”, without validation at the desk").format(
				address=client[1], name=shown(name)
			)
		)
		return redirect("/", [cookie(value, hours * 3600), await self._remember(value)])

	async def _remember(self, value: str) -> tuple[str, str]:
		"""Le navigateur de cette session valide, retenu pour son compte (https://github.com/dascritch/machincast/issues/601) :
		le cookie qui le dit."""
		browser = await self._database(lambda connection: sessions.remember_browser(connection, value))
		return browser_cookie(browser)

	async def validation_form(self, request: Request) -> Response:
		"""Ce que la session attend : le code du pupitre, celui de l'application d'authentification, ou l'acceptation
		au pupitre, sans code, la page se relisant ; une session qui n'attend plus rien entre
		(https://github.com/dascritch/machincast/issues/600, https://github.com/dascritch/machincast/issues/601)."""
		found = await self.session(request)
		value = bearer(request)
		if (found is None) or (found.state == "invalid") or (value is None):
			return redirect("/login")
		if found.state == "valid":
			return redirect("/")
		chosen = await self._database(lambda connection: sessions.stage(connection, value))
		if chosen == "invalid":
			return redirect("/login")
		if chosen != "ready":
			return validation_page(stage=chosen)
		outcome = await self._database(lambda connection: sessions.validate(connection, self._validation(value, None)))
		if outcome == "valid":
			return await self._validated(request.client, found.user, value)
		return redirect("/login")

	def _validation(self, value: str, given: str | None) -> sessions.Validation:
		return sessions.Validation(value, given, self.settings.session, self.clock.now(), self.used)

	async def _validated(self, address: str, user: str, value: str, *, by_app: bool = False) -> Response:
		"""La session validée, au pupitre ou par l'application d'authentification : les codes faux de l'adresse et du
		compte effacés, le navigateur retenu, et l'accueil."""
		self.codes.succeeded(address)
		self.codes.succeeded(f"{ACCOUNT}{user}")
		said = _("[{address}] intranet connection of “{name}” validated at the desk")
		if by_app:
			said = _("[{address}] intranet connection of “{name}” validated by its authentication app")
		log.info(said.format(address=address, name=shown(user)))
		return redirect("/", [await self._remember(value)])

	async def validation(self, request: Request) -> Response:
		"""Le code saisi : valide, l'accueil ; faux, la page le redemande ; invalide, la mire. Chaque code faux compte
		pour l'adresse et pour le compte ; au-delà de FAILURES, aucun code n'est essayé avant un quart d'heure."""
		value = bearer(request)
		found = await self.session(request)
		if (value is None) or (found is None):
			return redirect("/login")
		address = request.client
		name = shown(found.user)
		chosen = await self._database(lambda connection: sessions.stage(connection, value))
		if self._codes_blocked(address, found.user):
			log.warning(
				_(
					"[{address}] validation code refused, user “{name}”: too many wrong codes, waiting a quarter of an "
					"hour"
				).format(address=address, name=name)
			)
			return validation_page(_("Too many wrong codes: wait a quarter of an hour."), 429, stage=chosen)
		given = request.form().get("code", "")
		outcome = await self._database(lambda connection: sessions.validate(connection, self._validation(value, given)))
		if outcome == "waiting":
			return validation_page(
				_(
					"Your connection is not accepted at the desk yet: once the studio accepts it, it gives you the "
					"code."
				),
				409,
				stage=chosen,
			)
		if outcome == "valid":
			return await self._validated(address, found.user, value, by_app=chosen == "totp")
		if outcome == "totp":
			return redirect("/validation")
		return self._refused(outcome, address, found.user)

	def _refused(self, outcome: str, address: str, user: str) -> Response:
		"""Un code faux, compté pour l'adresse et le compte, ou la session devenue invalide."""
		name = shown(user)
		if outcome in ("wrong", "wrong_totp", "exhausted"):
			self.codes.failed(address)
			self.codes.failed(f"{ACCOUNT}{user}")
		if outcome == "wrong":
			log.warning(_("[{address}] wrong validation code, user “{name}”").format(address=address, name=name))
			return validation_page(_("Wrong code: ask again at the desk."), 400)
		if outcome == "wrong_totp":
			log.warning(
				_("[{address}] wrong code of the authentication app, user “{name}”").format(address=address, name=name)
			)
			return validation_page(
				_("Wrong code: enter the one that your authentication app shows."), 400, stage="totp"
			)
		log.warning(
			_(
				"[{address}] intranet connection of “{name}” invalid: not validated in time, or too many wrong codes"
			).format(address=address, name=name)
		)
		return login_page(_("Connection not validated in time, or too many wrong codes: connect again."), status=401)

	async def logout(self, request: Request) -> Response:
		value = bearer(request)
		if value is not None:
			await self._database(lambda connection: sessions.end(connection, value))
		return redirect("/login", [cookie("", 0)])


async def unauthorised(_request: Request) -> Response:
	"""Pour l'API : 401, sans session valide."""
	return text(401, _("A valid session is required."))
