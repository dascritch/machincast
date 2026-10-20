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

CATEGORIES_SUPPRIMEES = frozenset({"Cc", "Cs", "Co", "Cn"})
"""Contrôle, demi-codet, usage privé, non attribué."""
PLAGES_SUPPRIMEES = (
	(0xFE00, 0xFE0F),
	(0xE0100, 0xE01EF),
	(0x180B, 0x180F),
	(0xFFF0, 0xFFFF),
)
"""Sélecteurs de variante, dont ceux du mongol, et caractères spéciaux."""
SANS_LARGEUR = frozenset({"​", "﻿"})
"""Espace sans largeur, et espace insécable sans largeur (l'indicateur d'ordre des octets en tête de texte)."""


def _supprime(caractere: str) -> bool:
	code = ord(caractere)
	if (caractere in SANS_LARGEUR) or (unicodedata.category(caractere) in CATEGORIES_SUPPRIMEES):
		return True
	return any(debut <= code <= fin for debut, fin in PLAGES_SUPPRIMEES)


def conformer(texte: str) -> str:
	"""Le texte filtré : espaces simples, uniques, sans espace au début ni à la fin ; sans caractère indésirable."""
	gardes = []
	for caractere in texte:
		if caractere.isspace():
			gardes.append(" ")
		elif not _supprime(caractere):
			gardes.append(caractere)
	return " ".join(mot for mot in "".join(gardes).split(" ") if mot != "")
