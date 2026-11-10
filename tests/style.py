"""Vérification des règles de style du code Python (https://github.com/dascritch/machincast/issues/103,
https://github.com/dascritch/machincast/issues/340).

Décidées en relecture de https://github.com/dascritch/machincast/pull/100 (doc/fr/regles/developpement.md, Style de
code) :

1. dans une condition qui enchaîne `and` ou `or` (un nœud BoolOp), chaque opérande est entre parenthèses dans le
   source : `(a) and (f(b))`, jamais `a and f(b)` ;
2. pas d'expression conditionnelle (un nœud IfExp), `a if b else c` : une valeur par défaut puis un `if`, ou un
   `if`/`else` développé (https://github.com/dascritch/machincast/issues/340) ;
3. pas de `elif` : un `match`/`case`, un `return`, ou une conditionnelle développée ;
4. pas de compréhension, de liste, d'ensemble, de dictionnaire, ni d'expression génératrice : une boucle `for`
   développée, au besoin dans une fonction nommée ;
5. pas de `continue` : une sous-fonction dont on sort par un simple `return` dit de quelle boucle on s'échappe.

Les parenthèses se lisent dans les jetons du source : le module ast ne les garde pas.
"""

import ast
import io
import tokenize
from dataclasses import dataclass

OPERAND = "opérande sans parenthèses dans une condition enchaînée"
TERNARY = "expression conditionnelle"
ELIF = "elif"
COMPREHENSION = "compréhension"
CONTINUE = "continue"
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


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
	tokens = []
	for token in tokenize.generate_tokens(io.StringIO(source).readline):
		if token.type not in ignored:
			tokens.append(token)
	return tokens


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
	following_list = []
	for rank, token in enumerate(tokens):
		if token.end == end:
			following_list.append(rank)
	if (start is None) or (start == 0) or (following_list == []):
		return False
	following = following_list[-1] + 1
	return (tokens[start - 1].string == "(") and (following < len(tokens)) and (tokens[following].string == ")")


def _elif(node: ast.If, lines: list[str]) -> bool:
	"""Le sinon du if est un if écrit elif : un seul if, sur une ligne qui commence par elif."""
	if (len(node.orelse) != 1) or (not isinstance(node.orelse[0], ast.If)):
		return False
	return lines[node.orelse[0].lineno - 1].lstrip().startswith("elif")


def faults(source: str) -> list[Fault]:
	"""Les fautes de style d'un source Python, dans l'ordre des lignes."""
	tokens = _tokens(source)
	starts = {}
	for rank, token in enumerate(tokens):
		starts[token.start] = rank
	lines = source.splitlines()
	found_list = []
	for node in ast.walk(ast.parse(source)):
		found_list += _node_faults(node, lines, tokens, starts)
	return sorted(set(found_list), key=_line_then_kind)


def _line_then_kind(fault: Fault) -> tuple[int, str]:
	return (fault.line, fault.kind)


def _node_faults(
	node: ast.AST, lines: list[str], tokens: list[tokenize.TokenInfo], starts: dict[tuple[int, int], int]
) -> list[Fault]:
	"""Les fautes d'un nœud, sans ses enfants."""
	found_list: list[Fault] = []
	if isinstance(node, ast.BoolOp):
		for operand in node.values:
			if not _between_parentheses(operand, lines, tokens, starts):
				found_list.append(Fault(operand.lineno, OPERAND))
		return found_list
	if isinstance(node, ast.IfExp):
		return [Fault(node.lineno, TERNARY)]
	if isinstance(node, COMPREHENSIONS):
		return [Fault(node.lineno, COMPREHENSION)]
	if isinstance(node, ast.Continue):
		return [Fault(node.lineno, CONTINUE)]
	if (isinstance(node, ast.If)) and (_elif(node, lines)):
		return [Fault(node.orelse[0].lineno, ELIF)]
	return found_list
