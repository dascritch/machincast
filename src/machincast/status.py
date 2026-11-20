"""L'état de la station pour le shell : Machin status (https://github.com/dascritch/machincast/issues/518).

Quatre réponses courtes, une par ligne sur la sortie standard, pour un script ou une barre d'état :

- ``Machin status server`` : « service » quand le service de diffusion est installé, « test » sinon ;
- ``Machin status radio`` : le nom de la radio, metadata.public_text ;
- ``Machin status event --now`` : l'événement actuel, « {début} → {fin} : {nom privé} » ;
- ``Machin status event --next`` : l'événement suivant, dans le même format.

Les heures sont celles du poste, au format HH:MM ; « --:-- » dit un événement sans début ou sans fin, comme un fil
musical permanent. Les événements viennent de la grille de la base de production, lue sans rien y écrire : une session
sautée y est sautée, mais un événement avancé ou terminé à la main, qui n'est connu que du service de lecture, ne
l'est pas ici. Sans événement, rien n'est écrit et le code de sortie est NONE_CODE.
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import datetime

import psycopg

from machincast import service
from machincast.cli import launch
from machincast.clock import Clock, SystemClock
from machincast.configuration import Configuration
from machincast.database import Role, open_connection
from machincast.i18n import _
from machincast.shared.grid import Occurrence, active_event, following_event, read_grid

EXECUTABLE = "Machin_status"
DESCRIPTION = _("Tells the state of the station: server, radio name, current and next event.")
NONE_CODE = 1
"""Le code de sortie quand il n'y a pas d'événement à dire."""
FAILURE_CODE = 3
"""Le code de sortie quand la base est injoignable."""
SERVICE = "service"
TEST = "test"
NO_TIME = "--:--"
CLOCK: Clock = SystemClock()
"""L'heure de « maintenant » ; les scénarios la fixent."""

# Nom explicite : lancé par son script, ce module garde le journal « machincast ».
log = logging.getLogger("machincast.status")


def server() -> str:
	"""« service » quand le service de diffusion est installé, « test » sinon."""
	if service.read_state().installed:
		return SERVICE
	return TEST


def _hour(moment: datetime | None) -> str:
	if moment is None:
		return NO_TIME
	return f"{moment:%H:%M}"


def describe(occurrence: Occurrence) -> str:
	"""« {début} → {fin} : {nom privé} »."""
	return f"{_hour(occurrence.start)} → {_hour(occurrence.end)} : {occurrence.event.name}"


def event(configuration: Configuration, *, following: bool) -> str | None:
	"""L'événement actuel, ou le suivant, décrit ; None s'il n'y en a pas."""
	database = configuration.database
	with open_connection(database.socket, database.production, Role.INTERFACE) as connection:
		events = read_grid(connection)
	instant = CLOCK.now()
	if following:
		found = following_event(events, instant)
	else:
		found = active_event(events, instant)
	if found is None:
		return None
	return describe(found)


def run(configuration: Configuration, options: argparse.Namespace) -> int:
	"""Écrit la réponse demandée ; le code de sortie."""
	if options.question == "server":
		sys.stdout.write(f"{server()}\n")
		return 0
	if options.question == "radio":
		sys.stdout.write(f"{configuration.metadata.public_text}\n")
		return 0
	try:
		answer = event(configuration, following=options.next)
	except psycopg.Error as error:
		log.error(_("database unreachable: {error}").format(error=error))
		return FAILURE_CODE
	if answer is None:
		return NONE_CODE
	sys.stdout.write(f"{answer}\n")
	return 0


def add_options(analyser: argparse.ArgumentParser) -> None:
	questions = analyser.add_subparsers(dest="question", required=True, metavar="QUESTION")
	questions.add_parser("server", help=_("“service” if the broadcast service is installed, “test” otherwise"))
	questions.add_parser("radio", help=_("the name of the radio (metadata.public_text)"))
	events = questions.add_parser("event", help=_("the current or the next event, “start → end : private name”"))
	which = events.add_mutually_exclusive_group(required=True)
	which.add_argument("--now", action="store_true", help=_("the current event"))
	which.add_argument("--next", action="store_true", help=_("the next event"))


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run, own_options=add_options)
