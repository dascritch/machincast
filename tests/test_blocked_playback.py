"""Scénarios d'une lecture qui ne démarre pas (https://github.com/dascritch/machincast/issues/281).

La diffusion tourne sur le moteur simulé, qui suit l'horloge du binaire. Un lecteur bloqué est imité par une voie
simulée dont la position n'avance pas, et qui se dit bloquée passé le délai de démarrage, comme la voie GStreamer
(machincast.player.engine.Track.blocked). Les étapes partagées de la diffusion sont dans tests/broadcast_steps.py.
"""

from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios

from machincast.clock import FixedClock
from machincast.player.engine import GUARD_DELAY, PlaybackTrack
from machincast.player.simulation import SimulatedEngine, SimulatedTrack

scenarios("blocked_playback.feature")

Connection = psycopg.Connection[tuple[object, ...]]


class BlockedTrack(SimulatedTrack):
	"""Un lecteur qui ne démarre jamais : ni son, ni erreur, ni fin."""

	def position(self) -> timedelta:
		return timedelta(0)

	def handle(self) -> None:
		pass

	def blocked(self) -> bool:
		return (self.state == "en cours") and (self.clock.now() - self.start >= GUARD_DELAY)


@given(parsers.parse("le lecteur du sonore « {name} » se bloque à son premier démarrage"))
def blocked_player(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
	"""Les fichiers des sonores sont dans un répertoire à leur nom (broadcast_steps.create_sound) ; l'adresse d'un
	stream factice finit par son nom."""
	true_play = SimulatedEngine.play
	blocked_list: list[str] = []

	def play(
		self: SimulatedEngine, path: Path | str, duration: timedelta | None, *args: object, **options: object
	) -> PlaybackTrack:
		targeted = (Path(str(path)).parent.name == name) or (str(path).endswith(f"/{name}"))
		if (targeted) and (blocked_list == []):
			blocked_list.append(name)
			assert isinstance(self.clock, FixedClock)
			track = BlockedTrack(self.clock, duration)
			self._tracks.append(track)
			return track
		return true_play(self, path, duration, *args, **options)  # type: ignore[arg-type]

	monkeypatch.setattr(SimulatedEngine, "play", play)
