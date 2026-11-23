"""Les gabarits Jinja2 de « Machin intranet » (https://github.com/dascritch/machincast/issues/597, ticket enfant de
https://github.com/dascritch/machincast/issues/596).

Les pages de l'intranet viennent des fichiers de machincast/intranet/templates/, en Jinja2, le moteur Python le plus
proche de Twig : page.html.jinja, la page HTML, que layout.html.jinja étend du bandeau (banner.html.jinja) ; puis
chaque page, qui étend layout.html.jinja.

Un plugin activé surcharge un gabarit en fournissant, dans son répertoire templates/, un fichier du même nom : le
premier plugin chargé, dans l'ordre de [plugins] enabled, l'emporte, puis viennent ceux de MachinCast. Un gabarit qui en
remplace un peut étendre l'original sous le nom « machincast/<nom> ».

- L'échappement HTML est automatique ; un fragment déjà écrit en HTML passe par html(), qui le marque sûr.
- Les textes passent par _() et ngettext(), ceux de MachinCast (machincast.i18n) ; machincast.catalog les relève dans
  les gabarits, comme dans le code.
- Une variable absente est une erreur (StrictUndefined) : un gabarit surchargé qui en attend une le dit aussitôt.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader, PrefixLoader, StrictUndefined
from jinja2.loaders import BaseLoader
from markupsafe import Markup

from machincast.i18n import _, ngettext

DIRECTORY = "templates"
"""Le répertoire des gabarits, dans machincast/intranet/ comme dans chaque plugin."""
ORIGINAL = "machincast"
"""Le préfixe sous lequel un gabarit de MachinCast reste joignable, pour un plugin qui le surcharge en l'étendant."""

_overrides: tuple[Path, ...] = ()
_environment: Environment | None = None


def configure(directories: Sequence[Path]) -> None:
	"""Les répertoires templates/ des plugins, dans l'ordre où ils l'emportent ; ceux qui n'existent pas sont laissés."""
	global _overrides, _environment
	found = []
	for directory in directories:
		if directory.is_dir():
			found.append(directory)
	_overrides = tuple(found)
	_environment = None


def plugin_directories(plugin_paths: Sequence[Path]) -> list[Path]:
	"""Le répertoire templates/ de chaque plugin chargé, dans l'ordre de chargement."""
	found = []
	for path in plugin_paths:
		found.append(path / DIRECTORY)
	return found


def _loader() -> BaseLoader:
	machincast = PackageLoader("machincast.intranet", DIRECTORY)
	loaders: list[BaseLoader] = []
	for directory in _overrides:
		loaders.append(FileSystemLoader(str(directory)))
	loaders.append(machincast)
	loaders.append(PrefixLoader({ORIGINAL: machincast}))
	return ChoiceLoader(loaders)


def environment() -> Environment:
	"""L'environnement Jinja2 de l'intranet, construit au premier usage, de nouveau après configure."""
	global _environment
	if _environment is None:
		built = Environment(
			loader=_loader(),
			autoescape=True,
			undefined=StrictUndefined,
			trim_blocks=True,
			lstrip_blocks=True,
			keep_trailing_newline=True,
			extensions=["jinja2.ext.i18n"],
		)
		built.install_gettext_callables(gettext=_, ngettext=ngettext, newstyle=True)  # type: ignore[attr-defined]
		_environment = built
	return _environment


def render(template: str, /, **context: Any) -> str:
	"""Le gabarit, rendu avec context."""
	return environment().get_template(template).render(**context)


def html(text: str) -> Markup:
	"""Un fragment déjà écrit en HTML, et échappé là où il le faut : Jinja2 le garde tel quel."""
	return Markup(text)
