"""Vérification de deux règles de style du code Python (https://github.com/dascritch/machincast/issues/103).

Décidées en relecture de https://github.com/dascritch/machincast/pull/100 (doc/fr/regles/developpement.md, Style de
code) :

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

OPERAND = "opérande sans parenthèses dans une condition enchaînée"
CALL = "appel dans une branche d'expression conditionnelle"


@dataclass(frozen=True)
class Fault:
	line: int
	kind: str


def _tokens(source: str) -> list[tokenize.TokenInfo]:
	ignored = {
		tokenize.NL,
		tokenize.NEWLINE,
		tokenize.COMMENT,
		tokenize.INDENT,
		tokenize.DEDENT,
		tokenize.ENCODING,
		tokenize.ENDMARKER,
	}
	return [token for token in tokenize.generate_tokens(io.StringIO(source).readline) if token.type not in ignored]


def _column(lines: list[str], line: int, byte: int) -> int:
	"""La colonne d'ast compte les octets UTF-8 ; celle des jetons, les caractères."""
	return len(lines[line - 1].encode()[:byte].decode())


def _between_parentheses(
	node: ast.expr, lines: list[str], tokens: list[tokenize.TokenInfo], starts: dict[tuple[int, int], int]
) -> bool:
	"""Le jeton qui précède l'opérande ouvre une parenthèse, et celui qui le suit la ferme."""
	assert (node.end_lineno is not None) and (node.end_col_offset is not None)
	start = starts.get((node.lineno, _column(lines, node.lineno, node.col_offset)))
	end = (node.end_lineno, _column(lines, node.end_lineno, node.end_col_offset))
	following_list = [rank for rank, token in enumerate(tokens) if token.end == end]
	if (start is None) or (start == 0) or (following_list == []):
		return False
	following = following_list[-1] + 1
	return (tokens[start - 1].string == "(") and (following < len(tokens)) and (tokens[following].string == ")")


def _forbidden_call(node: ast.expr) -> bool:
	for call in ast.walk(node):
		if not isinstance(call, ast.Call):
			continue
		if (not isinstance(call.func, ast.Name)) or (call.func.id not in CONVERSIONS):
			return True
	return False


def faults(source: str) -> list[Fault]:
	"""Les fautes de style d'un source Python, dans l'ordre des lignes."""
	tokens = _tokens(source)
	starts = {token.start: rank for rank, token in enumerate(tokens)}
	lines = source.splitlines()
	found_list = []
	for node in ast.walk(ast.parse(source)):
		if isinstance(node, ast.BoolOp):
			found_list += [
				Fault(operand.lineno, OPERAND)
				for operand in node.values
				if not _between_parentheses(operand, lines, tokens, starts)
			]
		elif (isinstance(node, ast.IfExp)) and ((_forbidden_call(node.body)) or (_forbidden_call(node.orelse))):
			found_list.append(Fault(node.lineno, CALL))
	return sorted(set(found_list), key=lambda fault: (fault.line, fault.kind))
