"""Scénarios des conversions partagées (https://github.com/dascritch/machincast/issues/187)."""

import re
from datetime import timedelta

from pytest_bdd import parsers, scenarios, then

from machincast import conversion

scenarios("conversion.feature")


def value(text: str) -> object:
	"""La valeur que décrit le scénario : « rien », « le texte « … » », « le nombre 12 »…"""
	if text == "rien":
		return None
	if text in ("vrai", "faux"):
		return text == "vrai"
	if (found := re.fullmatch(r"le texte « ?(.*?) ?»", text)) is not None:
		return found.group(1)
	if (found := re.fullmatch(r"(?:le nombre|l'entier) (\d+)", text)) is not None:
		return int(found.group(1))
	if (found := re.fullmatch(r"la durée de (\d+) s", text)) is not None:
		return timedelta(seconds=int(found.group(1)))
	if (found := re.fullmatch(r"(?:l'ensemble|la liste) (.+)", text)) is not None:
		counts = []
		for count in found.group(1).split(", "):
			counts.append(int(count))
		if text.startswith("l'ensemble"):
			return set(counts)
		return counts
	raise AssertionError(text)


@then(parsers.re(r"(?P<name>\w+) de (?P<entry>.+) donne (?P<output>.+)"))
def convert(name: str, entry: str, output: str) -> None:
	result = getattr(conversion, name)(value(entry))
	if isinstance(result, list):
		result = sorted(result)
	expected = value(output)
	assert (result, type(result)) == (expected, type(expected))
