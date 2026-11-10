"""Mise à jour des catalogues de traduction (https://github.com/dascritch/machincast/issues/360).

Relève les messages du code, les appels _(), N_(), ngettext(), counted(), N_counted() et pgettext() de
src/machincast, et les textes des écrans .ui, puis met à jour chaque catalogue
locale/<langue>/LC_MESSAGES/machincast.po : un message nouveau y entre sans traduction, un message disparu en sort, une
traduction existante est gardée. Avec --check, ne modifie rien et échoue si un catalogue n'est pas à jour ou a un
message sans traduction : les tests le vérifient.

	python -m machincast.catalog          # met à jour les catalogues
	python -m machincast.catalog --check  # vérifie, sans rien écrire
	python -m machincast.catalog --new de # crée le catalogue d'une nouvelle langue
"""

import argparse
import ast
import re
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from pathlib import Path

from machincast import i18n
from machincast.log import configure as configure_log

PACKAGE = Path(__file__).parent
PROJECT = PACKAGE.parent.parent
SCRIPTS = ("bin/Machin", "bin/i18n.bash", "install.sh")
"""Les scripts bash de MachinCast, dans le dépôt : leurs messages sont relevés aussi (bin/i18n.bash)."""
BASH_MESSAGE = re.compile(r"\b(?:t|tf|etape|info|echec) '([^']+)'")
"""Un message d'un script : le premier argument, entre apostrophes, d'une fonction qui le traduit."""
SOURCE_LANGUAGE_HEADER = (
	"Project-Id-Version: MachinCast\n"
	"Report-Msgid-Bugs-To: https://github.com/dascritch/machincast/issues\n"
	"MIME-Version: 1.0\n"
	"Content-Type: text/plain; charset=UTF-8\n"
	"Content-Transfer-Encoding: 8bit\n"
)
PLURAL_FORMS = {"fr": "nplurals=2; plural=(n > 1);"}
KEYWORDS = {
	"_": "message",
	"N_": "message",
	"ngettext": "plural",
	"counted": "plural",
	"N_counted": "plural",
	"pgettext": "context",
}


@dataclass
class Message:
	"""Un message du code : son msgid, son pluriel et son contexte s'il en a, et où il apparaît."""

	msgid: str
	plural: str | None = None
	context: str | None = None
	references: list[str] = field(default_factory=list)

	@property
	def key(self) -> str:
		if self.context is None:
			return self.msgid
		return self.context + i18n.CONTEXT_SEPARATOR + self.msgid


def _constant(node: ast.expr) -> str | None:
	if (isinstance(node, ast.Constant)) and (isinstance(node.value, str)):
		return node.value
	return None


def extract(package: Path = PACKAGE) -> dict[str, Message]:
	"""Les messages du code et des écrans, dans l'ordre de leur première apparition."""
	found: dict[str, Message] = {}

	def add(message: Message, reference: str) -> None:
		known = found.setdefault(message.key, message)
		if known.plural is None:
			known.plural = message.plural
		known.references.append(reference)

	for path in sorted(package.rglob("*.py")):
		relative = path.relative_to(package.parent).as_posix()
		if "/ui/" in relative:
			continue
		for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
			if not ((isinstance(node, ast.Call)) and (isinstance(node.func, ast.Name)) and (node.func.id in KEYWORDS)):
				continue
			texts = []
			for argument in node.args:
				texts.append(_constant(argument))
			kind = KEYWORDS[node.func.id]
			# Le fichier seul, sans numéro de ligne : déplacer du code ne change pas le catalogue.
			reference = relative
			if (kind == "message") and (texts) and (texts[0]):
				add(Message(texts[0]), reference)
			else:
				if (kind == "plural") and (len(texts) >= 2) and (texts[0]) and (texts[1]):
					add(Message(texts[0], plural=texts[1]), reference)
				else:
					if (kind == "context") and (len(texts) >= 2) and (texts[0]) and (texts[1]):
						add(Message(texts[1], context=texts[0]), reference)
	for path in sorted(package.rglob("*.ui")):
		relative = path.relative_to(package.parent).as_posix()
		for element in ElementTree.parse(path).iter("string"):
			if (element.get("notr") == "true") or (not element.text):
				continue
			add(Message(element.text, context=(element.get("comment")) or (None)), relative)
	for script in scripts(package):
		text = script.read_text(encoding="utf-8")
		for found_message in BASH_MESSAGE.finditer(text):
			start = text.rfind("\n", 0, found_message.start()) + 1
			if text[start : found_message.start()].lstrip().startswith("#"):
				continue
			add(Message(found_message.group(1)), script.relative_to(package.parent.parent).as_posix())
	return found


def scripts(package: Path = PACKAGE) -> list[Path]:
	"""Les scripts bash du dépôt ; aucun pour un paquet installé hors du dépôt."""
	scripts = []
	name_list = []
	for name in SCRIPTS:
		name_list.append(package.parent.parent / name)
	for path in name_list:
		if path.is_file():
			scripts.append(path)
	return scripts


def bash_messages(messages: dict[str, Message]) -> set[str]:
	"""Les messages qui viennent d'un script bash."""
	bash_messages = set()
	for key, message in messages.items():
		found = False
		for ref in message.references:
			if not ref.startswith("machincast/"):
				found = True
				break
		if found:
			bash_messages.add(key)
	return bash_messages


def _bash(text: str) -> str:
	"""Une chaîne bash $'…'."""
	return "$'" + text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\t", "\\t") + "'"


def write_bash(messages: dict[str, Message], translations: dict[str, str | tuple[str, ...]]) -> str:
	"""Le catalogue bash d'une langue : les traductions des messages des scripts, que bin/i18n.bash charge."""
	lines = [
		"# shellcheck shell=bash",
		"# Écrit par python -m machincast.catalog d'après machincast.po : ne pas modifier ici.",
		"MACHINCAST_MESSAGES+=(",
	]
	for key in sorted(bash_messages(messages)):
		translated = translations.get(key)
		if (isinstance(translated, str)) and (translated):
			lines.append(f"\t[{_bash(key)}]={_bash(translated)}")
	lines.append(")")
	return "\n".join(lines) + "\n"


def _quote(text: str, width: int = 76) -> str:
	"""Une chaîne de fichier .po, entre guillemets ; une longue, ou à plusieurs lignes, sur plusieurs lignes du
	fichier, coupée après ses retours à la ligne et ses espaces, comme le fait msgmerge."""
	escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\t", "\\t").replace("\r", "\\r")
	lines = escaped.split("\n")
	chosen = []
	if lines[-1]:
		chosen = [lines[-1]]
	line_list = []
	for line in lines[:-1]:
		line_list.append(line + "\\n")
	pieces = line_list + chosen
	if (len(pieces) <= 1) and (len(escaped) <= width - 8):
		return f'"{"".join(pieces)}"'
	parts = []
	for piece in pieces:
		while len(piece) > width:
			cut = piece.rfind(" ", 0, width)
			if cut <= 0:
				break
			parts.append(piece[: cut + 1])
			piece = piece[cut + 1 :]
		parts.append(piece)
	part_list = []
	for part in parts:
		part_list.append(f'"{part}"')
	return '""\n' + "\n".join(part_list)


def write_catalog(code: str, messages: dict[str, Message], translations: dict[str, str | tuple[str, ...]]) -> str:
	"""Le contenu du catalogue d'une langue : les messages du code, avec les traductions connues."""
	header = SOURCE_LANGUAGE_HEADER + f"Language: {code}\n"
	if code in PLURAL_FORMS:
		header += f"Plural-Forms: {PLURAL_FORMS[code]}\n"
	blocks = [f'msgid ""\nmsgstr {_quote(header)}\n']
	for key, message in messages.items():
		lines = []
		for reference in dict.fromkeys(message.references):
			lines.append(f"#: {reference}")
		if i18n._PLACEHOLDER.search(message.msgid):
			lines.append("#, python-brace-format")
		if message.context is not None:
			lines.append(f"msgctxt {_quote(message.context)}")
		lines.append(f"msgid {_quote(message.msgid)}")
		known = translations.get(key)
		if message.plural is not None:
			lines.append(f"msgid_plural {_quote(message.plural)}")
			if isinstance(known, tuple):
				forms = known
			else:
				forms = ("", "")
			form_list = []
			for index, form in enumerate(forms):
				form_list.append(f"msgstr[{index}] {_quote(form)}")
			lines.extend(form_list)
		else:
			lines.append(f"msgstr {_quote(known if isinstance(known, str) else '')}")
		blocks.append("\n".join(lines) + "\n")
	return "\n".join(blocks)


def untranslated(messages: dict[str, Message], translations: dict[str, str | tuple[str, ...]]) -> list[str]:
	"""Les messages sans traduction dans un catalogue."""
	untranslated = []
	for key, message in messages.items():
		if not translations.get(key):
			untranslated.append(message.msgid)
	return untranslated


def main(arguments: list[str] | None = None) -> int:
	analyser = argparse.ArgumentParser(prog="python -m machincast.catalog", description=__doc__.splitlines()[0])
	analyser.add_argument("--check", action="store_true", help="checks the catalogues, without writing anything")
	analyser.add_argument("--new", metavar="LANGUAGE", help="creates the catalogue of a new language, such as de")
	options = analyser.parse_args(arguments)
	log = configure_log("catalog")
	messages = extract()
	code_returned = 0
	languages = list(i18n.LANGUAGES)
	if options.new is not None:
		languages.append(options.new)
	for code in dict.fromkeys(languages):
		if code == i18n.SOURCE:
			continue
		file = i18n.catalog_file(code)
		before = ""
		if file.is_file():
			before = file.read_text(encoding="utf-8")
		translations = i18n.read_catalog(before)
		after = write_catalog(code, messages, translations)
		missing = untranslated(messages, translations)
		bash_file = file.with_suffix(".bash")
		bash_after = None
		if scripts():
			bash_after = write_bash(messages, translations)
		if options.check:
			bash_before = ""
			if bash_file.is_file():
				bash_before = bash_file.read_text(encoding="utf-8")
			if (after != before) or ((bash_after is not None) and (bash_after != bash_before)):
				log.error(f"{file}: not up to date, run python -m machincast.catalog")
				code_returned = 1
			for msgid in missing:
				log.error(f"{file}: untranslated: {msgid!r}")
				code_returned = 1
			continue
		file.parent.mkdir(parents=True, exist_ok=True)
		file.write_text(after, encoding="utf-8")
		if bash_after is not None:
			bash_file.write_text(bash_after, encoding="utf-8")
		log.info(f"{file}: {len(messages)} messages, {len(missing)} untranslated")
	return code_returned


if __name__ == "__main__":
	sys.exit(main())
