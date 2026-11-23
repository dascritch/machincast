"""Étapes partagées des points d'extension des plugins (https://github.com/dascritch/machincast/issues/348).

Chargé comme greffon pytest par tests/conftest.py. Recorder imite un plugin qui garde ce qu'il reçoit ; le journal du
binaire dit l'échec d'un plugin (machincast.plugins.points.FAILED).
"""

import logging
import threading
from collections.abc import Callable, Iterable, Mapping
from typing import Any

import pytest
from pytest_bdd import parsers, then

from machincast.i18n import _
from machincast.plugins.points import CORE, FAILED, Points

FAILURE = "panne du plugin"


def core_points(prefix: str) -> list[str]:
	"""Les points du cœur qui commencent ainsi : « player. », « indexer. »…"""
	found = []
	for point in CORE:
		if point.startswith(prefix):
			found.append(point)
	return found


class Recorder:
	"""Ce qu'un plugin a reçu, dans l'ordre : le point et ses données."""

	def __init__(self) -> None:
		self.received: list[tuple[str, dict[str, Any]]] = []
		self._lock = threading.Lock()

	def subscribe(self, points: Points, plugin: str, names: Iterable[str]) -> None:
		for point in names:
			points.subscribe(plugin, point, self.receiver(point))

	def receiver(self, point: str) -> Callable[[Mapping[str, Any]], None]:
		def receive(data: Mapping[str, Any]) -> None:
			with self._lock:
				self.received.append((point, dict(data)))

		return receive

	def of(self, point: str) -> list[dict[str, Any]]:
		found = []
		for received_point, data in self.received:
			if received_point == point:
				found.append(data)
		return found


def subscribe_failing(points: Points, plugin: str, names: Iterable[str]) -> None:
	"""Un plugin qui échoue à chacun de ces points."""

	def fail(data: Mapping[str, Any]) -> None:
		raise RuntimeError(FAILURE)

	for point in names:
		points.subscribe(plugin, point, fail)


@pytest.fixture
def recorder() -> Recorder:
	return Recorder()


@then(parsers.parse("le journal du binaire dit que le plugin « {name} » a échoué au point « {point} »"))
def failure_logged(caplog: pytest.LogCaptureFixture, name: str, point: str) -> None:
	expected = _(FAILED).format(plugin=name, point=point, error=FAILURE)
	messages = []
	for record in caplog.records:
		if record.levelno == logging.ERROR:
			messages.append(record.getMessage())
	assert expected in messages, messages
