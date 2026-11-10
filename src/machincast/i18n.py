"""Traduction des messages de MachinCast (https://github.com/dascritch/machincast/issues/360).

Le code écrit ses messages en anglais, la langue source ; chaque langue a son catalogue gettext,
locale/<langue>/LC_MESSAGES/machincast.po, versionné et lu tel quel : il n'y a rien à compiler. La langue est celle de
la session, lue dans LANGUAGE, LC_ALL, LC_MESSAGES puis LANG, comme le fait gettext : la première variable renseignée
décide. Une langue sans catalogue revient à l'anglais.

Un message s'écrit _("…") quand il se traduit aussitôt, N_("…") quand il se garde en anglais, dans la table log, et ne
se traduit qu'à l'affichage, par logged(). Ses valeurs sont des champs nommés, remplis par str.format après la
traduction : _("{count} files read").format(count=count), jamais une f-string, que le catalogue ne connaîtrait pas.
"""

import argparse
import gettext
import os
import re
from collections.abc import Mapping
from datetime import date, datetime
from functools import cache
from pathlib import Path

DOMAIN = "machincast"
LOCALE = Path(__file__).with_name("locale")
SOURCE = "en"
"""Langue des messages dans le code, et de repli."""
LANGUAGES = (
	SOURCE,
	*sorted(path.name for path in LOCALE.glob("*") if (path / "LC_MESSAGES" / "machincast.po").is_file()),
)
"""Les langues de MachinCast : l'anglais, et celles qui ont un catalogue ; en ajouter une, c'est ajouter son
catalogue."""
PLURALS = {"fr": lambda n: int(n > 1)}
"""La forme du pluriel selon le nombre, par langue (Plural-Forms) ; à défaut, celle de l'anglais : n != 1."""
VARIABLES = ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")
"""Variables d'environnement de la langue, de la plus forte à la plus faible, comme pour gettext."""
CONTEXT_SEPARATOR = "\x04"
"""Séparateur du contexte et du message dans une clé de catalogue gettext (msgctxt)."""
_PLACEHOLDER = re.compile(r"\{\{|\}\}|\{(?P<name>[A-Za-z_]\w*)(?:![rsa])?(?::[^{}]*)?\}")


def language(environment: Mapping[str, str] | None = None) -> str:
	"""La langue de la session : celle de la première variable renseignée, si MachinCast la parle, sinon l'anglais.

	LANGUAGE peut donner plusieurs langues, séparées par « : » ; la première parlée l'emporte. « C » et « POSIX »
	sont l'anglais."""
	values: Mapping[str, str] = os.environ
	if environment is not None:
		values = environment
	for variable in VARIABLES:
		value = values.get(variable, "")
		if not value:
			continue
		for candidate in value.split(":"):
			code = re.split(r"[_.@-]", candidate, maxsplit=1)[0].lower()
			if code in LANGUAGES:
				return code
		return SOURCE
	return SOURCE


def catalog_file(code: str) -> Path:
	"""Le catalogue d'une langue."""
	return LOCALE / code / "LC_MESSAGES" / f"{DOMAIN}.po"


def _unquote(text: str) -> str:
	"""Le contenu d'une chaîne entre guillemets d'un fichier .po."""
	body = text.strip()
	if (len(body) < 2) or (body[0] != '"') or (body[-1] != '"'):
		raise ValueError(f"malformed .po string: {text}")
	escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "r": "\r"}
	return re.sub(r"\\(.)", lambda found: escapes.get(found.group(1), found.group(0)), body[1:-1])


def read_catalog(text: str, plurals: dict[str, str] | None = None) -> dict[str, str | tuple[str, ...]]:
	"""Les traductions d'un fichier .po : msgid (précédé de son msgctxt et de CONTEXT_SEPARATOR, s'il en a un) vers
	msgstr, ou vers les formes de msgstr[n] pour un message au pluriel, dont la clé est le msgid singulier. Les entrées
	floues (« #, fuzzy »), non traduites ou obsolètes (« #~ ») sont ignorées, comme par msgfmt. Le msgid_plural de
	chaque message au pluriel s'ajoute à plurals, s'il est donné."""
	entries: dict[str, str | tuple[str, ...]] = {}
	fields: dict[str, str] = {}
	current = ""
	fuzzy = False

	def close() -> None:
		nonlocal fields, fuzzy
		if ("msgid" in fields) and (fields["msgid"]) and (not fuzzy):
			key = fields["msgid"]
			if "msgctxt" in fields:
				key = fields["msgctxt"] + CONTEXT_SEPARATOR + key
			forms = tuple(fields[name] for name in sorted(fields) if name.startswith("msgstr["))
			if (forms) and (all(forms)):
				entries[key] = forms
				if (plurals is not None) and ("msgid_plural" in fields):
					plurals[key] = fields["msgid_plural"]
			else:
				if fields.get("msgstr"):
					entries[key] = fields["msgstr"]
		fields = {}
		fuzzy = False

	for line in [*text.splitlines(), ""]:
		stripped = line.strip()
		if not stripped:
			close()
			continue
		if stripped.startswith("#"):
			if (stripped.startswith("#,")) and ("fuzzy" in stripped):
				fuzzy = True
			continue
		if stripped.startswith('"'):
			fields[current] += _unquote(stripped)
			continue
		keyword, _space, rest = stripped.partition(" ")
		if (keyword in fields) and (keyword in ("msgctxt", "msgid")):
			close()
		current = keyword
		fields[current] = _unquote(rest)
	return entries


class Catalog(gettext.NullTranslations):
	"""Les traductions d'une langue, lues dans son fichier .po."""

	def __init__(
		self, entries: dict[str, str | tuple[str, ...]], plurals: dict[str, str] | None = None, code: str = SOURCE
	) -> None:
		super().__init__()
		self.code = code
		self.entries = entries
		if plurals is None:
			self.plurals = {}
		else:
			self.plurals = plurals
		"""Le msgid_plural de chaque message au pluriel, par son msgid."""

	def gettext(self, message: str) -> str:
		found = self.entries.get(message)
		if isinstance(found, str):
			return found
		return message

	def ngettext_forms(self, forms: tuple[str, ...], n: int) -> str:
		"""La forme qui convient à n, selon la langue. Français : le singulier pour 0 et 1."""
		index = PLURALS.get(self.code, lambda count: int(count != 1))(n)
		return forms[min(index, len(forms) - 1)]

	def ngettext(self, msgid1: str, msgid2: str, n: int) -> str:
		found = self.entries.get(msgid1)
		if isinstance(found, tuple):
			return self.ngettext_forms(found, n)
		if n == 1:
			return msgid1
		return msgid2

	def pgettext(self, context: str, message: str) -> str:
		found = self.entries.get(context + CONTEXT_SEPARATOR + message)
		if isinstance(found, str):
			return found
		return message


def load(code: str) -> Catalog:
	"""Le catalogue d'une langue ; vide pour l'anglais, ou pour une langue sans fichier."""
	file = catalog_file(code)
	if (code == SOURCE) or (not file.is_file()):
		return Catalog({})
	plurals: dict[str, str] = {}
	return Catalog(read_catalog(file.read_text(encoding="utf-8"), plurals), plurals, code)


_catalog = load(language())
_language = language()


def current() -> str:
	"""La langue des messages."""
	return _language


def activate(code: str) -> None:
	"""Change la langue des messages, pour ceux traduits désormais ; ceux déjà traduits, comme les constantes des
	modules, gardent la leur. Sert aux tests ; les exécutables prennent la langue de leur session."""
	global _catalog, _language
	_language = SOURCE
	if code in LANGUAGES:
		_language = code
	_catalog = load(_language)
	_templates.cache_clear()


def _(message: str) -> str:
	"""Le message traduit dans la langue de la session."""
	return _catalog.gettext(message)


def ngettext(singular: str, plural: str, count: int) -> str:
	"""Le message au singulier ou au pluriel, selon count, traduit."""
	return _catalog.ngettext(singular, plural, count)


def counted(singular: str, plural: str, count: int) -> str:
	"""Le message au singulier ou au pluriel, traduit, son champ {count} rempli : counted("{count} file",
	"{count} files", 3) donne « 3 fichiers » en français."""
	return ngettext(singular, plural, count).format(count=count)


def pgettext(context: str, message: str) -> str:
	"""Le message traduit, selon son contexte : pour un même mot anglais aux traductions différentes."""
	return _catalog.pgettext(context, message)


def short_date(day: date) -> str:
	"""« 2026-10-20 » en anglais, « 20/10/2026 » en français."""
	return pgettext("date format", "{day:%Y-%m-%d}").format(day=day)


def date_and_hour(instant: datetime) -> str:
	"""« 2026-10-20 at 20:00 » en anglais, « 20/10/2026 à 20:00 » en français."""
	return pgettext("date and time format", "{instant:%Y-%m-%d at %H:%M}").format(instant=instant)


def decimal(number: str) -> str:
	"""Un nombre écrit à la décimale de la langue : « 0,5 » en français, « 0.5 » en anglais."""
	if _language == "fr":
		return number.replace(".", ",")
	return number


def known(message: str, context: str | None = None) -> str | None:
	"""La traduction d'un message que le catalogue de la langue connaît, même identique ; None sinon."""
	if context is None:
		key = message
	else:
		key = context + CONTEXT_SEPARATOR + message
	found = _catalog.entries.get(key)
	if isinstance(found, str):
		return found
	return None


def N_(message: str) -> str:
	"""Marque un message pour le catalogue, sans le traduire : il se garde en anglais, et se traduit à l'affichage."""
	return message


def N_counted(singular: str, plural: str, count: int) -> str:
	"""Comme counted, mais en anglais, pour la table log ; le catalogue le connaît, logged() le traduira."""
	chosen = plural
	if count == 1:
		chosen = singular
	return chosen.format(count=count)


def _pattern(msgid: str) -> tuple[int, re.Pattern[str]]:
	"""Un gabarit en expression rationnelle, ses champs capturés ; avec la longueur de son texte hors champs."""
	pattern = []
	seen = set()
	position = 0
	for field in _PLACEHOLDER.finditer(msgid):
		before = msgid[position : field.start()]
		pattern.append(re.escape(before))
		name = field.group("name")
		if name is None:
			pattern.append(re.escape(field.group(0)[0]))
		else:
			if name in seen:
				pattern.append(f"(?P={name})")
			else:
				seen.add(name)
				# Un nombre accordé (counted) n'est fait que de chiffres : « 2 sounds, 1 bank » n'est pas un seul nombre.
				value = r".+?"
				if name == "count":
					value = r"-?\d+"
				else:
					if (before.endswith("“")) and (msgid[field.end() :].startswith("”")):
						# Un nom entre guillemets n'en contient pas : « of “{a}” by “{b}” » se coupe aux guillemets.
						value = r"[^“”]+?"
				pattern.append(f"(?P<{name}>{value})")
		position = field.end()
	pattern.append(re.escape(msgid[position:]))
	return len(_PLACEHOLDER.sub("", msgid)), re.compile("".join(pattern), re.DOTALL)


def _order(entry: tuple[int, re.Pattern[str], object, bool | None, frozenset[str]]) -> tuple[int, int]:
	"""L'ordre d'essai d'un gabarit : les forts, du plus précis au moins précis ; les faibles, du moins de champs au
	plus, « {path}: {error} » avant « {level}: {kind}: {message} », dont le découpage tomberait au milieu d'un
	message."""
	literal, pattern, _msgstr, weak, _quoted = entry
	if weak is False:
		return (-literal, 0)
	return (len(pattern.groupindex), -literal)


@cache
def _templates() -> list[tuple[re.Pattern[str], str | tuple[str, ...], bool | None, frozenset[str]]]:
	"""Les gabarits du catalogue, à champs nommés, en expressions rationnelles : du plus précis au moins précis. Un
	message au pluriel en donne deux, son singulier et son pluriel anglais. Un gabarit sans un mot hors de ses champs,
	« {line}, {empty} », est faible : il ne vient qu'après le découpage d'une énumération ; un gabarit sans rien que des
	espaces hors de ses champs n'en est pas un."""
	found = []
	for msgid, msgstr in _catalog.entries.items():
		if CONTEXT_SEPARATOR in msgid:
			continue
		sources = [msgid]
		if (isinstance(msgstr, tuple)) and (msgid in _catalog.plurals):
			sources.append(_catalog.plurals[msgid])
		for source in sources:
			# Un gabarit de champs séparés par des espaces, « {day} {month} », reconnaîtrait toute phrase.
			if (_PLACEHOLDER.search(source)) and (_PLACEHOLDER.sub("", source).strip()):
				literal, pattern = _pattern(source)
				between = _PLACEHOLDER.sub("", source)
				weak: bool | None = False
				if re.search(r"[^\W\d_]", between) is None:
					weak = True
				if between.strip(" ,;") == "":
					weak = None
				# Un champ entre guillemets, « “{name}” », est un nom, gardé tel quel : un événement peut s'appeler
				# Continue.
				quoted = frozenset(re.findall(r"“\{(\w+)[^{}]*\}”", source))
				found.append((literal, pattern, msgstr, weak, quoted))
	found.sort(key=_order)
	return [(pattern, msgstr, weak, quoted) for _literal, pattern, msgstr, weak, quoted in found]


def _fill(text: str, weak: bool | None) -> str | None:
	"""Le message traduit par le premier gabarit qui lui correspond, parmi les forts (False), les faibles (True) ou
	ceux d'une énumération (None) ; None sans gabarit."""
	for pattern, msgstr, weak_template, quoted in _templates():
		if weak_template != weak:
			continue
		found = pattern.fullmatch(text)
		if found is None:
			continue
		values = {}
		for name, value in found.groupdict().items():
			values[name] = value
			if name not in quoted:
				values[name] = _local(logged(value))
		form = msgstr
		if isinstance(form, tuple):
			count = found.groupdict().get("count", "")
			chosen = 1
			if count.lstrip("-").isdigit():
				chosen = int(count)
			form = _catalog.ngettext_forms(form, chosen)

		def fill(field: re.Match[str], values: dict[str, str] = values) -> str:
			name = field.group("name")
			if name is None:
				return field.group(0)[0]
			return values.get(name, field.group(0))

		return _PLACEHOLDER.sub(fill, form)
	return None


_DECIMAL = re.compile(r"(?<![\d.])\d+\.\d+(?![\d.])")
"""Un nombre décimal d'un message du log, « 10.5 » ou les secondes de « 1:23.4 », écrit à la décimale de la langue
à l'affichage ; pas une adresse IP ni une version, « 127.0.0.1 », « 0.9.0 »."""
_DATE_AND_HOUR = re.compile(r"(?<![\d-])\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?![\d:])")
"""Une date et une heure d'un message du log, en ISO 8601, « 2026-10-20 20:00 »."""


def _local(value: str) -> str:
	"""Une valeur d'un message du log, ses dates et ses nombres décimaux à la façon de la langue :
	« 2026-10-20 20:00 » devient « 20/10/2026 à 20:00 », « 10.5 » devient « 10,5 », en français."""
	value = _DATE_AND_HOUR.sub(lambda found: date_and_hour(datetime.fromisoformat(found.group(0))), value)
	return _DECIMAL.sub(lambda number: decimal(number.group(0)), value)


_SEPARATORS = (N_("; "), N_(", "))
"""Les séparateurs d'une énumération, du plus fort au plus faible, à traduire : « ; » s'écrit « ; » en français."""


def logged(text: str) -> str:
	"""Un message gardé en anglais, dans la table log, traduit pour l'affichage : par le catalogue s'il y figure
	tel quel, sinon par le premier gabarit qui lui correspond, ses valeurs traduites à leur tour ; une énumération,
	séparée par des points-virgules ou des virgules, se traduit élément par élément. Les dates et les nombres décimaux
	de ses valeurs prennent la façon de la langue : « 20/10/2026 à 20:00 », « 10,5 s » en français. Un message sans
	traduction reste en anglais."""
	if (not text) or (not _catalog.entries):
		return text
	exact = _catalog.gettext(text)
	if exact != text:
		return exact
	strong = _fill(text, weak=False)
	if strong is not None:
		return strong
	weak = _fill(text, weak=True)
	if weak is not None:
		return weak
	for separator in _SEPARATORS:
		parts = text.split(separator)
		if len(parts) > 1:
			translated = [logged(part) for part in parts]
			if translated != parts:
				return _(separator).join(translated)
	listed = _fill(text, weak=None)
	if listed is not None:
		return listed
	return text


ARGPARSE = (
	N_("usage: "),
	N_("options"),
	N_("positional arguments"),
	N_("show this help message and exit"),
	N_("show program's version number and exit"),
	N_("the following arguments are required: %s"),
	N_("unrecognized arguments: %s"),
	N_("%(prog)s: error: %(message)s\n"),
	N_("expected one argument"),
	N_("invalid choice: %(value)r (choose from %(choices)s)"),
	N_("invalid %(type)s value: %(value)r"),
	N_("argument %(argument_name)s: %(message)s"),
	N_("not allowed with argument %s"),
	N_("ambiguous option: %(option)s could match %(matches)s"),
	N_("one of the arguments %s is required"),
)
"""Les textes d'argparse, que Python ne traduit pas sans catalogue installé : l'aide des binaires les montre."""
# argparse les traduit par ses propres _ et ngettext, lus à chaque appel : ceux de MachinCast les remplacent.
argparse._ = _  # type: ignore[attr-defined]
argparse.ngettext = ngettext  # type: ignore[attr-defined]
