"""La lecture des sonores par le service de diffusion, depuis l'interface (https://github.com/dascritch/machincast/issues/381).

Le service de diffusion tourne sous son propre compte (machincast.access). Quand un répertoire s'ajoute à une banque,
ou des fichiers à la liste des sonores, l'interface vérifie que le service les lit, eux et ce qu'ils contiennent ; s'il
ne les lit pas, elle propose de lui en donner la lecture (ACL, setfacl), et dit ce qu'elle n'a pas pu faire. Sans
service installé, il n'y a rien à vérifier : Machin player lit avec le compte qui le lance.
"""

from pathlib import Path

from PySide6.QtWidgets import QWidget

from machincast import access
from machincast.i18n import _
from machincast.interface import dialogs

TITLE = _("Reading by the broadcast service")
BUTTON = _("Let it read them")
GRANTED = _("The broadcast service can now read them.")
REFUSED = _(
	"The broadcast service cannot read them: Maintenance → Let the broadcast service read the sound files… gives "
	"it access later."
)


def _missing(path: Path, account: access.Account) -> bool:
	if path.is_dir():
		return access.unreadable_inside(path, account) != []
	return not access.readable(path, account)


def unreadable(paths: list[Path], account: access.Account | None = None) -> list[Path]:
	"""Les chemins que le service ne lit pas, eux ou ce qu'ils contiennent ; aucun sans service installé."""
	if account is None:
		account = access.service_account()
	if account is None:
		return []
	found = []
	for path in paths:
		if (path.exists()) and (_missing(path, account)):
			found.append(path)
	return found


def offer(parent: QWidget, paths: list[Path]) -> str:
	"""Propose de donner au service la lecture des chemins qu'il ne lit pas ; ce qu'il en est, rien s'il les lit
	tous."""
	account = access.service_account()
	if account is None:
		return ""
	missing = unreadable(paths, account)
	if missing == []:
		return ""
	names = []
	for path in missing:
		names.append(str(path))
	text = _(
		"The broadcast service, under its own account {account}, cannot read these files or directories, or what "
		"they contain: {list}."
	).format(account=account.name, list=", ".join(names))
	if not dialogs.confirm_action(parent, TITLE, text, BUTTON):
		return REFUSED
	problems = []
	for path in missing:
		problems += access.grant(path, account).problems
	if problems != []:
		return _("Reading not given to the broadcast service: {list}").format(list=" ; ".join(problems))
	return GRANTED
