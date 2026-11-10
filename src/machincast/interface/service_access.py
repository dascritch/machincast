"""La lecture des sonores par le service de diffusion, depuis l'interface (https://github.com/dascritch/machincast/issues/381).

Le service de diffusion tourne sous son propre compte (machincast.access). Quand un répertoire s'ajoute à une banque,
ou des fichiers à la liste des sonores, l'interface les passe au crible avant de les ajouter :

- ce que le service lit déjà est accepté, où que ce soit : un répertoire comme /home/musiques, que son administrateur
  a ouvert au compte machincast, s'ajoute et s'indexe ;
- illisibles dans un répertoire personnel (machincast.access.personal_home), ils sont refusés : MachinCast n'en
  changera pas les droits, et l'interface dit de les déposer dans le répertoire d'accueil des sonores,
  /home/machincast ;
- illisibles dans une autre arborescence sensible (/media, /mnt…), refusés aussi : MachinCast n'y change aucun
  droit ;
- ailleurs, s'il ne les lit pas, elle propose de lui en donner la lecture (ACL, setfacl) ; refusée, ils s'ajoutent
  quand même, et le menu Maintenance la donnera plus tard.

Sans service installé, il n'y a rien à vérifier : Machin player lit avec le compte qui le lance.
"""

from dataclasses import dataclass, field
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
PERSONAL = _(
	"Not added, unreadable by the broadcast service, in a personal directory whose rights MachinCast never changes: "
	"{list}. Put the sound files in {welcome}."
)
SENSITIVE = _(
	"Not added, unreadable by the broadcast service, in a directory where MachinCast never changes any right: {list}."
)


@dataclass
class Screening:
	"""Les chemins acceptés, et ce que l'interface en dit."""

	accepted: list[Path] = field(default_factory=list)
	messages: list[str] = field(default_factory=list)

	def text(self) -> str:
		return " ".join(self.messages)


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


def _names(paths: list[Path]) -> str:
	names = []
	for path in paths:
		names.append(str(path))
	return ", ".join(names)


def _sort(
	path: Path,
	account: access.Account,
	accepted: list[Path],
	personal: list[Path],
	sensitive: list[Path],
	missing: list[Path],
) -> None:
	"""Range un chemin : ce que le service lit déjà est toujours accepté, même dans un répertoire personnel, dont les
	droits ont été ouverts par d'autres ; illisible, il est refusé dans un répertoire personnel ou une autre
	arborescence sensible, et accepté ailleurs, à faire lire au service."""
	unread = (path.exists()) and (_missing(path, account))
	if (unread) and (access.personal_home(path) is not None):
		personal.append(path)
		return
	if (unread) and (access.sensitive_tree(path) is not None):
		sensitive.append(path)
		return
	accepted.append(path)
	if unread:
		missing.append(path)


def screen(parent: QWidget, paths: list[Path]) -> Screening:
	"""Passe les chemins au crible du service, avant de les ajouter ; sans service, tous sont acceptés."""
	account = access.service_account()
	if account is None:
		return Screening(list(paths))
	result = Screening()
	personal: list[Path] = []
	sensitive: list[Path] = []
	missing: list[Path] = []
	for path in paths:
		_sort(path, account, result.accepted, personal, sensitive, missing)
	if personal != []:
		result.messages.append(PERSONAL.format(list=_names(personal), welcome=access.welcome()))
	if sensitive != []:
		result.messages.append(SENSITIVE.format(list=_names(sensitive)))
	if missing != []:
		result.messages.append(_offer(parent, missing, account))
	return result


def _offer(parent: QWidget, missing: list[Path], account: access.Account) -> str:
	text = _(
		"The broadcast service, under its own account {account}, cannot read these files or directories, or what "
		"they contain: {list}."
	).format(account=account.name, list=_names(missing))
	if not dialogs.confirm_action(parent, TITLE, text, BUTTON):
		return REFUSED
	problems = []
	for path in missing:
		problems += access.grant(path, account).problems
	if problems != []:
		return _("Reading not given to the broadcast service: {list}").format(list=" ; ".join(problems))
	return GRANTED
