"""Installer, mettre à jour ou désinstaller un plugin : python -m machincast.plugins.installation PLUGIN
(https://github.com/dascritch/machincast/issues/586), que lance le install.sh de chaque plugin.

- sans option : applique ses migrations qui manquent, sur la base de production, après une sauvegarde (pg_dump, comme
  Machin maintenance-db) ;
- --remove : annule ses migrations, après une sauvegarde ; aucune table du cœur ni d'un autre plugin n'est touchée,
  aucun fichier non plus ;
- --simulation : dit ce qui serait fait, sans rien faire.

Un manifest invalide, ou des migrations mal nommées, sans annulation, ou qui donnent des droits au rôle d'un binaire où
le plugin ne s'accroche pas (machincast.plugins.schema.problems), refusent l'installation, code INVALID ; une
sauvegarde ou une base en échec, code FAILURE. L'activation, elle, se règle dans machincast.toml, [plugins].
"""

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

import psycopg

from machincast.cli import launch
from machincast.configuration import Configuration
from machincast.database import url_yoyo
from machincast.i18n import _, ngettext
from machincast.maintenance import BackupFailure, back_up
from machincast.plugins import schema
from machincast.plugins.manifest import InvalidManifest, read

log = logging.getLogger(__name__)

EXECUTABLE = "Machin_plugin-install"
DESCRIPTION = _("Installs, updates or removes a plugin: its tables, after a backup of the database")
FAILURE = 1
INVALID = 2


def own_options(analyser: argparse.ArgumentParser) -> None:
	analyser.add_argument("plugin", type=Path, help=_("directory of the plugin, in plugins/"))
	analyser.add_argument("--remove", action="store_true", help=_("cancels its migrations, after a backup"))
	analyser.add_argument("--simulation", action="store_true", help=_("says what would be done, without doing it"))
	analyser.add_argument(
		"--backups",
		type=Path,
		metavar="REPERTOIRE",
		help=_("directory of the backup; by default backup.directory of the configuration"),
	)


def _plan(url: str, plugin: Path, *, remove: bool) -> list[str]:
	if remove:
		return list(reversed(schema.applied(url, plugin)))
	return schema.pending(url, plugin)


def _change(configuration: Configuration, plugin: Path, options: argparse.Namespace, plan: list[str]) -> None:
	"""Sauvegarde, puis applique ou annule ; lève BackupFailure, psycopg.Error."""
	database = configuration.database
	url = url_yoyo(database.socket, database.production)
	back_up(configuration, Path((options.backups) or (configuration.backup.directory)).expanduser())
	if options.remove:
		count = schema.cancel(url, plugin)
		log.info(
			ngettext(
				"plugin “{name}”: {count} migration cancelled", "plugin “{name}”: {count} migrations cancelled", count
			).format(name=plugin.name, count=count)
		)
		return
	count = schema.apply(url, plugin)
	log.info(
		ngettext(
			"plugin “{name}”: {count} migration applied", "plugin “{name}”: {count} migrations applied", count
		).format(name=plugin.name, count=count)
	)


def run(configuration: Configuration, options: argparse.Namespace) -> int:
	"""Vérifie le plugin, puis applique ou annule ses migrations, après une sauvegarde ; ou dit ce qui serait fait.
	Le code de sortie : 0, FAILURE ou INVALID."""
	plugin = Path(options.plugin).expanduser().absolute()
	try:
		manifest = read(plugin)
	except InvalidManifest as error:
		log.error(_("plugin {plugin}: {error}").format(plugin=plugin, error=error))
		return INVALID
	found = schema.problems(plugin, manifest)
	if found != []:
		for problem in found:
			log.error(_("plugin “{name}”: {problem}").format(name=manifest.name, problem=problem))
		return INVALID
	database = configuration.database
	try:
		plan = _plan(url_yoyo(database.socket, database.production), plugin, remove=options.remove)
		if plan == []:
			log.info(_("plugin “{name}”: nothing to do").format(name=manifest.name))
			return 0
		if options.simulation:
			log.info(
				_("plugin “{name}”, simulation: backup, then {action} {migrations}").format(
					name=manifest.name, action=_action(remove=options.remove), migrations=", ".join(plan)
				)
			)
			return 0
		_change(configuration, plugin, options, plan)
	except BackupFailure as error:
		log.error(_("backup impossible: {error}; nothing was changed").format(error=error))
		return FAILURE
	except psycopg.Error as error:
		log.error(_("database error: {error}").format(error=error))
		return FAILURE
	return 0


def _action(*, remove: bool) -> str:
	if remove:
		return _("cancellation of")
	return _("application of")


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run, own_options)


if __name__ == "__main__":
	raise SystemExit(main())
