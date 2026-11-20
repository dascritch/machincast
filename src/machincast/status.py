"""L'état de la station pour le shell : Machin status (https://github.com/dascritch/machincast/issues/518).

Des réponses courtes, une par ligne sur la sortie standard, pour un script ou une barre d'état :

- ``Machin status``, ou ``Machin status player`` : « running » quand Machin player diffuse, « stopped » sinon, avec le
  code de sortie 0, ou STOPPED_CODE ; un programme en simulation n'est pas une diffusion ;
- ``Machin status summary`` : tout ce qui précède pour la bannière de ``Machin banner``, une ligne « clé, tabulation,
  valeur » par réponse : server, radio, player, et, quand Machin player diffuse, now et next, quand ils existent ;
- ``Machin status server`` : « service » quand le service de diffusion est installé, « test » sinon ;
- ``Machin status radio`` : le nom de la radio, metadata.public_text ;
- ``Machin status event --now``, ou ``Machin status event`` : l'événement actuel, « {début} → {fin} : {nom privé} » ;
- ``Machin status event --next`` : l'événement suivant, dans le même format.

Les heures sont celles du poste, au format HH:MM. Un fil musical permanent n'a ni début ni fin : celles qu'il dit sont
l'heure où il a pris l'antenne, quand l'événement d'avant s'est terminé, et l'heure où il sera interrompu, par le début
du suivant, cherchées dans la semaine d'avant et la semaine d'après ; « --:-- » dit celle qui n'y est pas. Les événements viennent de la grille de la base de production, lue sans rien y écrire : une session
sautée y est sautée, mais un événement avancé ou terminé à la main, qui n'est connu que du service de lecture, ne
l'est pas ici. Sans événement, rien n'est écrit et le code de sortie est NONE_CODE.
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import datetime, timedelta

import psycopg

from machincast import programs, service
from machincast.cli import launch
from machincast.clock import Clock, SystemClock
from machincast.configuration import Configuration
from machincast.database import Role, open_connection
from machincast.i18n import _
from machincast.shared.grid import Event, Occurrence, active_event, following_event, plan, read_grid, wall_hour

EXECUTABLE = "Machin_status"
DESCRIPTION = _("Tells the state of the station: server, radio name, current and next event.")
NONE_CODE = 1
"""Le code de sortie quand il n'y a pas d'événement à dire."""
STOPPED_CODE = 1
"""Le code de sortie quand Machin player ne diffuse pas."""
FEED_HORIZON = timedelta(days=7)
"""Jusqu'où chercher, avant et après maintenant, le début et la fin d'un fil musical."""
FAILURE_CODE = 3
"""Le code de sortie quand la base est injoignable."""
RUNNING = "running"
STOPPED = "stopped"
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


def player() -> str:
	"""« running » quand une diffusion de Machin player tourne, sous un compte quelconque, « stopped » sinon."""
	for program in programs.ongoing():
		if (program.name == "player") and ("--simulation" not in program.arguments):
			return RUNNING
	return STOPPED


def _feed_bounds(
	events: list[Event], occurrence: Occurrence, instant: datetime
) -> tuple[datetime | None, datetime | None]:
	"""Quand un fil musical permanent a pris l'antenne, et quand il la laissera ; None pour ce qui sort de la période
	cherchée : il y est depuis plus longtemps, ou y reste plus longtemps."""
	now = wall_hour(instant)
	start, end = now - FEED_HORIZON, now + FEED_HORIZON
	for planned in plan(events, start, end):
		for begins, ends in planned.plays:
			if (planned.occurrence.key == occurrence.key) and (begins <= now < ends):
				return _within(begins, start), _within(ends, end)
	return None, None


def _within(moment: datetime, limit: datetime) -> datetime | None:
	"""Le moment, sauf s'il est la limite de la période cherchée : il est alors plus loin, et inconnu."""
	if moment == limit:
		return None
	return moment


def describe(occurrence: Occurrence, bounds: tuple[datetime | None, datetime | None] | None = None) -> str:
	"""« {début} → {fin} : {nom privé} » ; les heures de l'occurrence, ou celles données pour un fil musical."""
	if bounds is None:
		bounds = (occurrence.start, occurrence.end)
	return f"{_hour(bounds[0])} → {_hour(bounds[1])} : {occurrence.event.name}"


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
	if (found.start is None) and (found.end is None):
		return describe(found, _feed_bounds(events, found, instant))
	return describe(found)


def summary(configuration: Configuration) -> list[tuple[str, str]]:
	"""Les réponses de la bannière : serveur, radio, état de Machin player, et, s'il diffuse, l'événement actuel et le
	suivant ; ceux que la base ne donne pas manquent."""
	answers = [("server", server()), ("radio", configuration.metadata.public_text), ("player", player())]
	if answers[-1][1] != RUNNING:
		return answers
	try:
		for key, following in (("now", False), ("next", True)):
			found = event(configuration, following=following)
			if found is not None:
				answers.append((key, found))
	except psycopg.Error as error:
		log.error(_("database unreachable: {error}").format(error=error))
	return answers


def run(configuration: Configuration, options: argparse.Namespace) -> int:
	"""Écrit la réponse demandée ; le code de sortie."""
	if options.question == "summary":
		for key, value in summary(configuration):
			sys.stdout.write(f"{key}\t{value}\n")
		return 0
	if options.question in (None, "player"):
		state = player()
		sys.stdout.write(f"{state}\n")
		if state == RUNNING:
			return 0
		return STOPPED_CODE
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
	questions = analyser.add_subparsers(dest="question", metavar="QUESTION")
	questions.add_parser("player", help=_("“running” if Machin player is broadcasting, “stopped” otherwise (default)"))
	questions.add_parser("summary", help=_("all the answers, one “key, tab, value” line each, for the banner"))
	questions.add_parser("server", help=_("“service” if the broadcast service is installed, “test” otherwise"))
	questions.add_parser("radio", help=_("the name of the radio (metadata.public_text)"))
	events = questions.add_parser("event", help=_("the current or the next event, “start → end : private name”"))
	which = events.add_mutually_exclusive_group()
	which.add_argument("--now", action="store_true", help=_("the current event (default)"))
	which.add_argument("--next", action="store_true", help=_("the next event"))


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run, own_options=add_options)
