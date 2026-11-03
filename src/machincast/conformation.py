"""Conformation des textes (https://github.com/dascritch/machincast/issues/108).

Les textes saisis dans l'interface (noms, artiste, titre, métadonnées musicales) et ceux lus dans les tags des
fichiers par l'indexeur passent par conformer avant d'entrer en base, pour qu'aucun caractère ne gêne le reste de
la chaîne de diffusion : sorties, flux, afficheurs RDS. La conformation ne fait que filtrer :

- tout espace Unicode (str.isspace : tabulation, retour à la ligne, espace insécable, espace fine…) devient une
  espace simple, 0x20 ;
- les espaces de début et de fin sont retirées, et jamais deux espaces ne se suivent ;
- sont supprimés : les caractères de contrôle (Cc, dont 0x00 à 0x1F et 0x7F à 0x9F), les sélecteurs de variante
  (U+FE00 à U+FE0F, U+E0100 à U+E01EF, U+180B à U+180F), les caractères spéciaux (U+FFF0 à U+FFFF), les caractères
  à usage privé (Co), les demi-codets isolés (Cs), les caractères non attribués (Cn) et les espaces sans largeur
  (U+200B, U+FEFF), qu'une espace simple changerait en séparation de mots.

Rien n'est normalisé ni remplacé autrement : les lettres accentuées, les écritures non latines et les emoji restent
tels quels. Les chemins et les adresses ne sont jamais conformés : ce sont ceux des fichiers et des flux.
"""

import unicodedata

DELETED_CATEGORIES = frozenset({"Cc", "Cs", "Co", "Cn"})
"""Contrôle, demi-codet, usage privé, non attribué."""
DELETED_RANGES = (
	(0xFE00, 0xFE0F),
	(0xE0100, 0xE01EF),
	(0x180B, 0x180F),
	(0xFFF0, 0xFFFF),
)
"""Sélecteurs de variante, dont ceux du mongol, et caractères spéciaux."""
WITHOUT_WIDTH = frozenset({"​", "﻿"})
"""Espace sans largeur, et espace insécable sans largeur (l'indicateur d'ordre des octets en tête de texte)."""


def _deleted(character: str) -> bool:
	code = ord(character)
	if (character in WITHOUT_WIDTH) or (unicodedata.category(character) in DELETED_CATEGORIES):
		return True
	return any(start <= code <= end for start, end in DELETED_RANGES)


def conform(text: str) -> str:
	"""Le texte filtré : espaces simples, uniques, sans espace au début ni à la fin ; sans caractère indésirable."""
	kept_list = []
	for character in text:
		if character.isspace():
			kept_list.append(" ")
		elif not _deleted(character):
			kept_list.append(character)
	return " ".join(word for word in "".join(kept_list).split(" ") if word != "")
