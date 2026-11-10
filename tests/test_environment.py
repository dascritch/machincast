"""Étapes des scénarios de l'environnement virtuel (https://github.com/dascritch/machincast/issues/51)."""

import importlib.util
import sys
from pathlib import Path

from pytest_bdd import parsers, scenarios, then

scenarios("environment.feature")

PREFIX = Path(sys.prefix).resolve()


@then("les scénarios s'exécutent dans un environnement virtuel")
def in_venv() -> None:
	assert sys.prefix != sys.base_prefix, "lancer les tests depuis le venv : . .venv/bin/activate"


@then("cet environnement virtuel n'inclut pas les paquets Python du système")
def isolated() -> None:
	settings = (PREFIX / "pyvenv.cfg").read_text(encoding="utf-8")
	item_list = []
	line_list = []
	for line in settings.splitlines():
		line_list.append(line.partition("="))
	for key, _, value in line_list:
		item_list.append((key.strip(), value.strip()))
	options = dict(item_list)
	assert options.get("include-system-site-packages") == "false", (
		"recréer le venv sans --system-site-packages (décision : https://github.com/dascritch/machincast/issues/51)"
	)


@then(parsers.parse('le module "{module}" est chargé depuis l\'environnement virtuel'))
def venv_module(module: str) -> None:
	specification = importlib.util.find_spec(module)
	assert (specification is not None) and (specification.origin is not None), f"{module} n'est pas installé"
	assert Path(specification.origin).resolve().is_relative_to(PREFIX), specification.origin


@then("GStreamer s'initialise depuis Python")
def gstreamer() -> None:
	import gi

	gi.require_version("Gst", "1.0")
	from gi.repository import Gst

	assert Gst.init_check(None), "GStreamer manquant : installer gir1.2-gstreamer-1.0 et les plugins (voir CLAUDE.md)"
