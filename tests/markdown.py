"""Vérification des liens relatifs et des ancres d'un fichier Markdown du dépôt."""

import re
from pathlib import Path

LIEN_RELATIF = re.compile(r"\]\((?!https?://|mailto:|#)([^)#\s]+)(?:#[^)]*)?\)")
# Lien vers une ancre, dans le même fichier (chemin vide) ou dans un autre fichier Markdown du dépôt.
LIEN_ANCRE = re.compile(r"\]\((?!https?://)([^)#\s]*)#([^)\s]+)\)")


def ancres(chemin: Path) -> set[str]:
	"""Ancres des titres d'un fichier Markdown, calculées comme GitHub : minuscules, ponctuation retirée."""
	titres = re.findall(r"^#{1,6} (.+)$", chemin.read_text(encoding="utf-8"), flags=re.MULTILINE)
	return {re.sub(r"[^\w\- ]", "", titre.strip().lower()).replace(" ", "-") for titre in titres}


def liens_casses(chemin: Path) -> list[str]:
	"""Liens relatifs qui ne mènent à aucun fichier, résolus depuis le répertoire du fichier Markdown."""
	texte = chemin.read_text(encoding="utf-8")
	return [lien for lien in LIEN_RELATIF.findall(texte) if not (chemin.parent / lien).exists()]


def ancres_cassees(chemin: Path) -> list[str]:
	"""Liens vers une ancre qui ne correspond à aucun titre du fichier visé."""
	texte = chemin.read_text(encoding="utf-8")
	return [
		f"{fichier}#{ancre}"
		for fichier, ancre in LIEN_ANCRE.findall(texte)
		if ancre not in ancres(chemin.parent / fichier if fichier else chemin)
	]
