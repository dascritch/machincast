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
- GET / : l'accueil (machincast.intranet.home), pour une session valide ; sinon la mire, ou la page de validation.

Le cookie de session est Secure, HttpOnly, SameSite=Strict ; le même jeton sert l'API, en cookie ou en
« Authorization: Bearer ». Les accès à la base passent par asyncio.to_thread : une connexion par requête, au rôle
machincast_intranet.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from html import escape

import psycopg
from psycopg.rows import TupleRow

from machincast.configuration import Intranet as Settings
from machincast.i18n import _
from machincast.intranet import sessions
from machincast.intranet.app import TITLE, Request, Response, Route, page, redirect, text
from machincast.intranet.sessions import COOKIE, Session

Connection = psycopg.Connection[TupleRow]
Connect = Callable[[], Connection]

FAILURES = 5
"""Échecs d'une même adresse, ou codes faux d'un même compte, avant d'attendre."""
PENALTY = 15 * 60
"""Secondes d'attente, après FAILURES échecs, et fenêtre où ils se comptent."""
ACCOUNT = "compte:"
"""Le préfixe des codes faux d'un compte, dans Throttle, à côté de ceux d'une adresse."""


def cookie(value: str, max_age: int) -> tuple[str, str]:
	"""L'en-tête qui pose le cookie de session : jamais en clair, jamais lu par un script, jamais envoyé d'ailleurs."""
	return ("set-cookie", f"{COOKIE}={value}; Max-Age={max_age}; Path=/; Secure; HttpOnly; SameSite=Strict")


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
		self._recent(address).append(self.clock())

	def succeeded(self, address: str) -> None:
		self.failures.pop(address, None)


LOGIN_FORM = """<h1>{title}</h1>
<form method="post" action="/login">
<p><label>{name_label}<br><input name="name" autocomplete="username" required autofocus value="{name}"></label></p>
<p><label>{password_label}<br><input name="password" type="password" autocomplete="current-password" required></label></p>
<p><button type="submit">{submit}</button></p>
</form>
{message}"""
VALIDATION_FORM = """<h1>{title}</h1>
<p>{explanation}</p>
<form method="post" action="/validation">
<p><label>{code_label}<br><input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9 ]{{6,7}}" maxlength="7" required autofocus></label></p>
<p><button type="submit">{submit}</button></p>
</form>
{message}
<form method="post" action="/logout"><p><button type="submit">{logout}</button></p></form>"""


def login_page(message: str = "", name: str = "", status: int = 200) -> Response:
	"""La mire : le nom gardé après un refus, et ce qui l'a refusé."""
	shown = ""
	if message != "":
		shown = f'<p role="alert">{escape(message)}</p>'
	return page(
		_("Connection"),
		LOGIN_FORM.format(
			title=TITLE,
			name_label=escape(_("User name")),
			name=escape(name),
			password_label=escape(_("Password")),
			submit=escape(_("Connect")),
			message=shown,
		),
		status,
	)


def validation_page(message: str = "", status: int = 200) -> Response:
	"""La page qui demande le code donné au pupitre, et ce qui a refusé le précédent."""
	shown = ""
	if message != "":
		shown = f'<p role="alert">{escape(message)}</p>'
	return page(
		_("Validation at the desk"),
		VALIDATION_FORM.format(
			title=escape(_("Validation at the desk")),
			explanation=escape(
				_(
					"An action must be done at the studio desk: MachinCast shows there your name, your browser and your "
					"address. Once your connection is accepted there, the studio gives you a 6-digit code: enter it "
					"here."
				)
			),
			code_label=escape(_("6-digit code")),
			submit=escape(_("Validate")),
			message=shown,
			logout=escape(_("Disconnect")),
		),
		status,
	)


class Portal:
	"""Les routes de la connexion, et la session de chaque requête."""

	def __init__(
		self, settings: Settings, connect: Connect, throttle: Throttle | None = None, codes: Throttle | None = None
	) -> None:
		self.settings = settings
		self.connect = connect
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
			return login_page(_("Too many failed attempts: wait a quarter of an hour."), status=429)
		user = await self._database(lambda connection: sessions.authenticate(connection, name, password))
		if user is None:
			self.throttle.failed(address)
			return login_page(_("Unknown user, disabled account or wrong password."), name, 401)
		self.throttle.succeeded(address)
		previous = bearer(request)
		if previous is not None:
			# Se reconnecter du même navigateur abandonne sa session d'avant, à valider ou valide.
			await self._database(lambda connection: sessions.end(connection, previous))
		value = sessions.token()
		agent = request.headers.get("user-agent", "")
		minutes = self.settings.validation
		given = await self._database(
			lambda connection: sessions.open_pending(connection, user, value, minutes, agent, address)
		)
		if given is None:
			return login_page(
				_(
					"This account already has {count} connections waiting for validation: have them validated or "
					"refused at the desk, or wait for their delay."
				).format(count=sessions.MAXIMUM_PENDING),
				name,
				429,
			)
		max_age = (minutes * 60) + (self.settings.session * 3600)
		return redirect("/validation", [cookie(value, max_age)])

	async def validation_form(self, request: Request) -> Response:
		found = await self.session(request)
		if (found is None) or (found.state == "invalid"):
			return redirect("/login")
		if found.state == "valid":
			return redirect("/")
		return validation_page()

	async def validation(self, request: Request) -> Response:
		"""Le code saisi : valide, l'accueil ; faux, la page le redemande ; invalide, la mire. Chaque code faux compte
		pour l'adresse et pour le compte ; au-delà de FAILURES, aucun code n'est essayé avant un quart d'heure."""
		value = bearer(request)
		if value is None:
			return redirect("/login")
		found = await self.session(request)
		if found is None:
			return redirect("/login")
		address = request.client
		if self._codes_blocked(address, found.user):
			return validation_page(_("Too many wrong codes: wait a quarter of an hour."), 429)
		given = request.form().get("code", "")
		hours = self.settings.session
		outcome = await self._database(lambda connection: sessions.validate(connection, value, given, hours))
		if outcome == "waiting":
			return validation_page(
				_(
					"Your connection is not accepted at the desk yet: once the studio accepts it, it gives you the "
					"code."
				),
				409,
			)
		if outcome == "valid":
			self.codes.succeeded(address)
			self.codes.succeeded(f"{ACCOUNT}{found.user}")
			return redirect("/")
		if outcome in ("wrong", "exhausted"):
			self.codes.failed(address)
			self.codes.failed(f"{ACCOUNT}{found.user}")
		if outcome == "wrong":
			return validation_page(_("Wrong code: ask again at the desk."), 400)
		return login_page(_("Connection not validated in time, or too many wrong codes: connect again."), status=401)

	async def logout(self, request: Request) -> Response:
		value = bearer(request)
		if value is not None:
			await self._database(lambda connection: sessions.end(connection, value))
		return redirect("/login", [cookie("", 0)])


async def unauthorised(_request: Request) -> Response:
	"""Pour l'API : 401, sans session valide."""
	return text(401, _("A valid session is required."))
