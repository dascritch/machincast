"""Machin_intranet : le serveur intranet et son API, en HTTPS seulement (https://github.com/dascritch/machincast/issues/538).

Éteint par défaut : il refuse de démarrer tant que intranet.enabled n'est pas vrai, ce que règle la page « Intranet »
des paramètres du service. Il écoute sur intranet.address et intranet.port, en TLS ; une connexion en clair n'obtient
aucune réponse HTTP. Sans certificat donné, il utilise celui qu'il génère dans son répertoire d'état
(machincast.intranet.certificate) : STATE_DIRECTORY sous systemd, ~/.local/state/machincast/intranet sinon.

Il s'arrête proprement sur SIGTERM ou SIGINT. Tant qu'il sert, son PID est noté dans son répertoire d'état
(machincast.intranet.process), où l'interface le retrouve pour l'arrêter. Avec --keep-open, pour le terminal que
lance l'interface sans le service (https://github.com/dascritch/machincast/issues/544), un arrêt sur une erreur garde
la fenêtre ouverte sur sa raison.
"""

import argparse
import asyncio
import ipaddress
import logging
import signal
from collections.abc import Sequence

import psycopg
from hypercorn.asyncio import serve
from hypercorn.config import Config
from psycopg.rows import TupleRow

from machincast.cli import launch
from machincast.configuration import Configuration, Intranet
from machincast.database import Role, open_connection
from machincast.i18n import _
from machincast.intranet import certificate, network, process
from machincast.intranet.api import ApiV1
from machincast.intranet.app import Intranet as Application
from machincast.intranet.pages import Pages
from machincast.intranet.portal import Portal
from machincast.maintenance import stay_open

log = logging.getLogger(__name__)

EXECUTABLE = "Machin_intranet"
DESCRIPTION = _("Serves the intranet and its API of MachinCast, in HTTPS only, when it is switched on.")
DISABLED_CODE = 4
"""Éteint dans la configuration : un autre code que celui d'une configuration invalide, 2, que systemd ne doit pas
prendre pour un arrêt voulu."""
FAILURE_CODE = 1
STOPPED_ON_ERROR = _("Machin intranet stopped on an error: this window stays open, close it whenever you want.")


def pair(settings: Intranet) -> certificate.Pair:
	"""Le certificat donné, ou celui que Machin intranet génère, refait s'il ne couvre plus le poste."""
	if (settings.certificate is not None) and (settings.key is not None):
		return certificate.Pair(settings.certificate, settings.key)
	generated = certificate.default(process.state_directory())
	certificate.ensure(generated, network.names(), network.addresses())
	return generated


def bind(settings: Intranet) -> str:
	"""« adresse:port », une adresse IPv6 entre crochets."""
	if ipaddress.ip_address(settings.address).version == 6:
		return f"[{settings.address}]:{settings.port}"
	return f"{settings.address}:{settings.port}"


def server_configuration(settings: Intranet, chosen: certificate.Pair) -> Config:
	"""Hypercorn en TLS seulement : aucune adresse en clair."""
	config = Config()
	config.bind = [bind(settings)]
	config.insecure_bind = []
	config.certfile = str(chosen.certificate)
	config.keyfile = str(chosen.key)
	config.accesslog = None
	config.errorlog = logging.getLogger("machincast.intranet.server")
	config.server_names = []
	config.include_server_header = False
	return config


def application(configuration: Configuration) -> Application:
	"""L'application de l'intranet, sur la base de production, au rôle machincast_intranet."""
	database = configuration.database

	def connect() -> psycopg.Connection[TupleRow]:
		return open_connection(database.socket, database.production, Role.INTRANET)

	portal = Portal(configuration.intranet, connect)
	api = ApiV1(portal, connect, configuration.player.state_socket)
	pages = Pages(portal, connect, configuration.player.state_socket, configuration.metadata.public_text)
	return Application({**portal.routes(), **api.routes(), **pages.routes()})


def own_options(analyser: argparse.ArgumentParser) -> None:
	analyser.add_argument(
		"--keep-open",
		action="store_true",
		help=_("keeps the terminal open after an error, until it is closed: for the window that the interface opens"),
	)


def run(configuration: Configuration, options: argparse.Namespace) -> int:
	"""serve, et, avec --keep-open, le terminal gardé ouvert sur l'erreur qui l'arrête."""
	code = serve_intranet(configuration)
	if (code != 0) and (options.keep_open):
		stay_open(STOPPED_ON_ERROR)
	return code


def serve_intranet(configuration: Configuration) -> int:
	"""Éteint, s'arrête aussitôt ; allumé, prend son certificat, dit l'adresse à donner et l'empreinte du certificat,
	puis sert jusqu'à SIGTERM ou SIGINT, son PID noté. Le code de sortie."""
	settings = configuration.intranet
	if not settings.enabled:
		log.error(_("the intranet is switched off: intranet.enabled, or the « Intranet » page of the service settings"))
		return DISABLED_CODE
	try:
		chosen = pair(settings)
	except (OSError, ValueError) as error:
		log.error(_("no TLS certificate for the intranet: {error}").format(error=error))
		return FAILURE_CODE
	log.info(
		_("intranet on {addresses}, certificate {fingerprint}").format(
			addresses=", ".join(network.to_give(settings.address, settings.port)),
			fingerprint=certificate.fingerprint(chosen.certificate),
		)
	)
	with process.recorded():
		asyncio.run(_serve(application(configuration), server_configuration(settings, chosen)))
	return 0


async def _serve(application: Application, config: Config) -> None:
	stopped = asyncio.Event()
	loop = asyncio.get_running_loop()
	for received in (signal.SIGTERM, signal.SIGINT):
		loop.add_signal_handler(received, stopped.set)
	await serve(application, config, shutdown_trigger=stopped.wait)  # type: ignore[arg-type]


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run, own_options)


if __name__ == "__main__":
	raise SystemExit(main())
