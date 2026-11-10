"""Vérification des liens relatifs et des ancres d'un fichier Markdown du dépôt."""

import re
from pathlib import Path

RELATIVE_LINK = re.compile(r"\]\((?!https?://|mailto:|#)([^)#\s]+)(?:#[^)]*)?\)")
# Lien vers une ancre, dans le même fichier (chemin vide) ou dans un autre fichier Markdown du dépôt.
ANCHOR_LINK = re.compile(r"\]\((?!https?://)([^)#\s]*)#([^)\s]+)\)")


def anchors(path: Path) -> set[str]:
	"""Ancres des titres d'un fichier Markdown, calculées comme GitHub : minuscules, ponctuation retirée."""
	titles = re.findall(r"^#{1,6} (.+)$", path.read_text(encoding="utf-8"), flags=re.MULTILINE)
	anchors = set()
	for title in titles:
		anchors.add(re.sub(r"[^\w\- ]", "", title.strip().lower()).replace(" ", "-"))
	return anchors


def broken_links(path: Path) -> list[str]:
	"""Liens relatifs qui ne mènent à aucun fichier, résolus depuis le répertoire du fichier Markdown."""
	text = path.read_text(encoding="utf-8")
	broken_links = []
	for link in RELATIVE_LINK.findall(text):
		if not (path.parent / link).exists():
			broken_links.append(link)
	return broken_links


def broken_anchors(path: Path) -> list[str]:
	"""Liens vers une ancre qui ne correspond à aucun titre du fichier visé."""
	text = path.read_text(encoding="utf-8")
	broken_anchors = []
	for file, anchor in ANCHOR_LINK.findall(text):
		target = path
		if file:
			target = path.parent / file
		if anchor not in anchors(target):
			broken_anchors.append(f"{file}#{anchor}")
	return broken_anchors
