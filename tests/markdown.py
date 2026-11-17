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


SENTENCE_END = ".!?…"
"""Ce qui finit une phrase, suivi d'une espace et du début de la phrase suivante."""
SENTENCE_START = re.compile(r"[A-ZÀÂÉÈÊËÎÏÔÛÙÇŒÆ«`\[]|\*\S")
"""Le début d'une phrase : une majuscule, un guillemet, du code, un lien ou une mise en valeur, jamais « * » suivi
d'une espace, qui ferait une liste."""
ABBREVIATIONS = ("p", "ex", "cf", "M", "n°", "c.-à-d")
"""Les abréviations dont le point ne finit pas la phrase."""
OPENING = {"[": "]", "(": ")", "«": "»"}
"""Ce qui s'ouvre et se ferme dans une phrase : une fin de phrase à l'intérieur ne compte pas."""


def sentence_ends(line: str) -> list[int]:
	"""Les positions des espaces qui séparent deux phrases d'une ligne de prose
	(https://github.com/dascritch/machincast/issues/445) : après un point, un point d'exclamation ou d'interrogation, ou
	des points de suspension, hors du code, d'un lien, de parenthèses ou de guillemets, et avant le début d'une phrase."""
	ends = []
	in_code = False
	closing: list[str] = []
	for position, character in enumerate(line):
		if character == "`":
			in_code = not in_code
		if not in_code:
			_follow_nesting(closing, character)
			if (not closing) and (_ends_sentence(line, position)):
				ends.append(position + 1)
	return ends


def _follow_nesting(closing: list[str], character: str) -> None:
	"""Tient la pile de ce qui est ouvert : crochets, parenthèses, guillemets."""
	if (closing) and (character == closing[-1]):
		closing.pop()
		return
	if character in OPENING:
		closing.append(OPENING[character])


def _ends_sentence(line: str, position: int) -> bool:
	"""Vrai si le caractère finit une phrase suivie d'une autre sur la même ligne."""
	if line[position] not in SENTENCE_END:
		return False
	if line[position + 1 : position + 2] != " ":
		return False
	if SENTENCE_START.match(line, position + 2) is None:
		return False
	word = re.search(r"([\w°.-]+)$", line[:position])
	# Un nombre avant le point est le numéro d'une liste numérotée, ou une version : pas une fin de phrase.
	return (word is None) or ((word.group(1) not in ABBREVIATIONS) and (not word.group(1).isdigit()))


def prose_lines(path: Path) -> list[tuple[int, str]]:
	"""Les lignes de prose d'un fichier Markdown, avec leur numéro : ni titre, ni tableau, ni bloc de code."""
	lines = []
	in_block = False
	for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
		if line.startswith("```"):
			in_block = not in_block
		prose = (not in_block) and (not line.startswith(("#", "```"))) and (not line.lstrip().startswith("|"))
		if prose:
			lines.append((number, line))
	return lines
