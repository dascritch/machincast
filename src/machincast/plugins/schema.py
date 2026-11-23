"""Le schéma SQL d'un plugin : ses migrations, ses droits (https://github.com/dascritch/machincast/issues/586).

Les migrations d'un plugin sont dans plugins/<nom>/migrations/, au format de celles du cœur (yoyo-migrations) :
<nom>.NNNN.<sujet>.sql et son annulation <nom>.NNNN.<sujet>.rollback.sql. Préfixés du nom du plugin, leurs
identifiants ne croisent jamais ceux du cœur, ni ceux d'un autre plugin, dans la table _yoyo_migration ; appliquer ou
annuler celles d'un plugin ne touche à aucune autre.

- Une table d'un plugin ne désigne que les tables du cœur, jamais l'inverse : le cœur ignore ses plugins.
- Ses GRANT ne donnent qu'aux rôles des binaires où il s'accroche (machincast.plugins.ROLES) ; problems le vérifie, et
  install refuse un plugin qui donne à un autre.
"""

import re
from pathlib import Path

from yoyo import get_backend, read_migrations

from machincast.i18n import _
from machincast.plugins import ROLES
from machincast.plugins.manifest import Manifest

DIRECTORY = "migrations"
ROLLBACK = ".rollback.sql"
GRANT = re.compile(r"\bGRANT\b[^;]*?\bTO\b\s+([^;]+);", re.IGNORECASE | re.DOTALL)
"""Un GRANT, et ses bénéficiaires, jusqu'au point-virgule."""


def directory(plugin: Path) -> Path:
	return plugin / DIRECTORY


def files(plugin: Path) -> list[Path]:
	"""Les migrations du plugin, sans leurs annulations, dans l'ordre."""
	found: list[Path] = []
	if not directory(plugin).is_dir():
		return found
	for path in sorted(directory(plugin).glob("*.sql")):
		if not path.name.endswith(ROLLBACK):
			found.append(path)
	return found


def _roles(manifest: Manifest) -> set[str]:
	roles = set()
	for binary in manifest.binaries:
		roles.add(str(ROLES[binary]))
	return roles


def _granted(text: str) -> list[str]:
	"""Les rôles à qui un script donne des droits."""
	roles = []
	for found in GRANT.finditer(text):
		for role in found.group(1).split(","):
			name = role.strip().split()[0].strip('"').lower()
			if name.startswith("machincast_"):
				roles.append(name)
	return roles


def problems(plugin: Path, manifest: Manifest) -> list[str]:
	"""Ce qui empêche d'appliquer les migrations du plugin : un nom sans son préfixe, une annulation qui manque, un
	droit donné au rôle d'un binaire où il ne s'accroche pas."""
	found = []
	allowed = _roles(manifest)
	for path in files(plugin):
		if not path.name.startswith(f"{manifest.name}."):
			found.append(
				_("migration {file}: its name starts with “{name}.”").format(file=path.name, name=manifest.name)
			)
		rollback = path.with_name(path.name.removesuffix(".sql") + ROLLBACK)
		if not rollback.is_file():
			found.append(
				_("migration {file}: its cancellation {rollback} is missing").format(
					file=path.name, rollback=rollback.name
				)
			)
		for role in _granted(path.read_text(encoding="utf-8")):
			if role not in allowed:
				found.append(
					_(
						"migration {file}: it grants rights to {role}, the role of a binary it does not hook into"
					).format(file=path.name, role=role)
				)
	return found


def _migrations(plugin: Path) -> object:
	return read_migrations(str(directory(plugin)))


def pending(url: str, plugin: Path) -> list[str]:
	"""Les identifiants des migrations du plugin pas encore appliquées."""
	if files(plugin) == []:
		return []
	with get_backend(url) as backend:
		missing = backend.to_apply(_migrations(plugin))
	identifiers = []
	for migration in missing:
		identifiers.append(str(migration.id))
	return identifiers


def applied(url: str, plugin: Path) -> list[str]:
	"""Les identifiants des migrations du plugin appliquées."""
	if files(plugin) == []:
		return []
	with get_backend(url) as backend:
		present = backend.to_rollback(_migrations(plugin))
	identifiers = []
	for migration in present:
		identifiers.append(str(migration.id))
	return identifiers


def apply(url: str, plugin: Path) -> int:
	"""Applique les migrations du plugin qui manquent ; leur nombre."""
	if files(plugin) == []:
		return 0
	with get_backend(url) as backend, backend.lock():
		missing = backend.to_apply(_migrations(plugin))
		backend.apply_migrations(missing)
	return len(missing)


def cancel(url: str, plugin: Path) -> int:
	"""Annule les migrations du plugin, dans l'ordre inverse ; leur nombre. Celles du cœur et des autres plugins
	restent."""
	if files(plugin) == []:
		return 0
	with get_backend(url) as backend, backend.lock():
		present = backend.to_rollback(_migrations(plugin))
		backend.rollback_migrations(present)
	return len(present)
