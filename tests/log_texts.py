"""Les textes du log dans les scénarios (https://github.com/dascritch/machincast/issues/360).

La base garde kind et message en anglais ; les scénarios les écrivent en français, comme l'écran des incidents les
montre. shown traduit ce que lit un scénario, stored retrouve ce qu'il cherche en base.
"""

from machincast import i18n

_FRENCH = i18n.load("fr")


def shown(text: object) -> str:
	"""Le texte du log tel que l'interface le montre, en français."""
	return i18n.logged(str(text))


def stored(text: str) -> str:
	"""Le texte anglais gardé en base pour ce texte français : un kind, comme « flux tombé »."""
	for msgid, msgstr in _FRENCH.entries.items():
		if (msgstr == text) and (i18n.CONTEXT_SEPARATOR not in msgid):
			return msgid
	return text
