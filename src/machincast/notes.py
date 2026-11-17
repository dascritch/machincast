"""« Votre installation » : le document éditable de l'équipe (https://github.com/dascritch/machincast/issues/451).

	python -m machincast.notes create --config machincast.toml

Un document Markdown, que l'équipe complète : qui appeler, la programmation, les partenariats, les publicités… Il est
sur le Bureau du compte (xdg-user-dir DESKTOP ; sans Bureau, le répertoire personnel), sous un nom dans la langue de la
session, ou à l'emplacement de interface.notes. Il se crée depuis un modèle de la langue de la session
(templates/installation.<langue>.md, installation.md en anglais à défaut) : par install.sh à l'installation, et par
l'interface, Aide → « Votre installation… », s'il manque. Un document qui existe n'est jamais remplacé.

Codes de sortie : 0 si le document est là, créé ou déjà présent ; 1 s'il n'a pas pu être créé ; 2 pour une
configuration invalide.
"""

import argparse
import logging
import subprocess
from collections.abc import Sequence
from pathlib import Path

from machincast.cli import launch
from machincast.configuration import Configuration
from machincast.i18n import _, language
from machincast.protection import check_writing

EXECUTABLE = "machincast.notes"
DESCRIPTION = _("Creates the “Your installation” document from its template, if it does not exist.")
FAILURE_CODE = 1
TEMPLATES = Path(__file__).with_name("templates")
TEMPLATE = TEMPLATES / "installation.md"
"""Le modèle en anglais ; celui d'une autre langue est à côté, installation.<langue>.md."""
XDG_DELAY = 5
"""Secondes laissées à xdg-user-dir pour répondre."""

# Nom explicite : lancé par son script, ce module garde le journal « machincast ».
log = logging.getLogger("machincast.notes")


def name() -> str:
	"""Le nom du document, dans la langue de la session."""
	return _("Your MachinCast installation.md")


def template_file(code: str | None = None) -> Path:
	"""Le modèle de cette langue, celle de la session par défaut ; celui en anglais à défaut."""
	if code is None:
		code = language()
	localised = TEMPLATES / f"installation.{code}.md"
	if localised.exists():
		return localised
	return TEMPLATE


def desktop() -> Path:
	"""Le Bureau du compte, que donne xdg-user-dir ; le répertoire personnel sans lui."""
	try:
		result = subprocess.run(
			["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, timeout=XDG_DELAY, check=False
		)
	except (OSError, subprocess.SubprocessError):
		return Path.home()
	folder = result.stdout.strip()
	if (result.returncode != 0) or (not folder):
		return Path.home()
	return Path(folder)


def document(configured: Path | None) -> Path:
	"""Le document : celui de interface.notes, sinon celui du Bureau."""
	if configured is not None:
		return configured
	return desktop() / name()


def create(path: Path) -> bool:
	"""Crée le document depuis le modèle, s'il n'existe pas : vrai s'il vient d'être créé. Jamais par-dessus un
	fichier ; lève OSError."""
	if path.exists():
		return False
	check_writing(path)
	path.parent.mkdir(parents=True, exist_ok=True)
	with path.open("x", encoding="utf-8") as written:
		written.write(template_file().read_text(encoding="utf-8"))
	return True


def run(configuration: Configuration, _options: argparse.Namespace) -> int:
	path = document(configuration.interface.notes)
	try:
		created = create(path)
	except OSError as error:
		log.error(_("installation document not created: {path}: {error}").format(path=path, error=error))
		return FAILURE_CODE
	if created:
		log.info(_("installation document created from its template: {path}").format(path=path))
		return 0
	log.info(_("installation document already there: {path}").format(path=path))
	return 0


def _options(analyser: argparse.ArgumentParser) -> None:
	analyser.add_argument("action", choices=["create"], help=_("create the document if it does not exist"))


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run, _options)


if __name__ == "__main__":
	raise SystemExit(main())
