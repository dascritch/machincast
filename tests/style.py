"""Vérification de deux règles de style du code Python (https://github.com/dascritch/machincast/issues/103).

Décidées en relecture de https://github.com/dascritch/machincast/pull/100 (doc/regles/developpement.md, Style de code) :

1. dans une condition qui enchaîne `and` ou `or` (un nœud BoolOp), chaque opérande est entre parenthèses dans le
   source : `(a) and (f(b))`, jamais `a and f(b)` ;
2. une expression conditionnelle (un nœud IfExp) ne décide pas d'un appel : aucune de ses deux branches n'appelle de
   fonction, sauf les conversions d'une valeur lue, listées dans CONVERSIONS. La condition, elle, peut appeler
   (`x if isinstance(x, int) else None`).

Les parenthèses se lisent dans les jetons du source : le module ast ne les garde pas.
"""

import ast
import io
import tokenize
from dataclasses import dataclass

CONVERSIONS = frozenset({"int", "str", "bool"})
"""Fonctions qu'une branche d'expression conditionnelle peut appeler : la conversion d'une valeur lue,
`None if valeur is None else int(str(valeur))`."""

OPERANDE = "opérande sans parenthèses dans une condition enchaînée"
APPEL = "appel dans une branche d'expression conditionnelle"


@dataclass(frozen=True)
class Faute:
	ligne: int
	nature: str


def _jetons(source: str) -> list[tokenize.TokenInfo]:
	ignores = {
		tokenize.NL,
		tokenize.NEWLINE,
		tokenize.COMMENT,
		tokenize.INDENT,
		tokenize.DEDENT,
		tokenize.ENCODING,
		tokenize.ENDMARKER,
	}
	return [jeton for jeton in tokenize.generate_tokens(io.StringIO(source).readline) if jeton.type not in ignores]


def _colonne(lignes: list[str], ligne: int, octet: int) -> int:
	"""La colonne d'ast compte les octets UTF-8 ; celle des jetons, les caractères."""
	return len(lignes[ligne - 1].encode()[:octet].decode())


def _entre_parentheses(
	noeud: ast.expr, lignes: list[str], jetons: list[tokenize.TokenInfo], debuts: dict[tuple[int, int], int]
) -> bool:
	"""Le jeton qui précède l'opérande ouvre une parenthèse, et celui qui le suit la ferme."""
	assert (noeud.end_lineno is not None) and (noeud.end_col_offset is not None)
	debut = debuts.get((noeud.lineno, _colonne(lignes, noeud.lineno, noeud.col_offset)))
	fin = (noeud.end_lineno, _colonne(lignes, noeud.end_lineno, noeud.end_col_offset))
	suivants = [rang for rang, jeton in enumerate(jetons) if jeton.end == fin]
	if (debut is None) or (debut == 0) or (suivants == []):
		return False
	suivant = suivants[-1] + 1
	return (jetons[debut - 1].string == "(") and (suivant < len(jetons)) and (jetons[suivant].string == ")")


def _appel_interdit(noeud: ast.expr) -> bool:
	for appel in ast.walk(noeud):
		if not isinstance(appel, ast.Call):
			continue
		if (not isinstance(appel.func, ast.Name)) or (appel.func.id not in CONVERSIONS):
			return True
	return False


def fautes(source: str) -> list[Faute]:
	"""Les fautes de style d'un source Python, dans l'ordre des lignes."""
	jetons = _jetons(source)
	debuts = {jeton.start: rang for rang, jeton in enumerate(jetons)}
	lignes = source.splitlines()
	trouvees = []
	for noeud in ast.walk(ast.parse(source)):
		if isinstance(noeud, ast.BoolOp):
			trouvees += [
				Faute(operande.lineno, OPERANDE)
				for operande in noeud.values
				if not _entre_parentheses(operande, lignes, jetons, debuts)
			]
		elif (isinstance(noeud, ast.IfExp)) and ((_appel_interdit(noeud.body)) or (_appel_interdit(noeud.orelse))):
			trouvees.append(Faute(noeud.lineno, APPEL))
	return sorted(set(trouvees), key=lambda faute: (faute.ligne, faute.nature))
