"""Les textes de la banque en emoji, en anglais, et leur traduction, dans la langue de MachinCast
(https://github.com/dascritch/machincast/issues/505). Le catalogue de MachinCast ne relève que son propre code : le
plugin garde le sien."""

from machincast import i18n

TRANSLATIONS: dict[str, dict[str, str]] = {
	"fr": {
		"Emoji of the bank": "Emoji de la banque",
		"The emoji at the start of the internal name, shown in the tables of airplay and of the coming sounds:"
		" choose it in the emoji selector, which copies it": (
			"L'emoji au début du nom interne, montré dans les tableaux d'airplay et des sonores à venir : le choisir dans"
			" le sélecteur d'emojis, qui le copie"
		),
		"Remove the emoji": "Retirer l'emoji",
		"Emoji…": "Emoji…",
		"Paste another emoji, then Enter": "Coller un autre emoji, puis Entrée",
		"Internal name, without its emoji": "Nom interne, sans son emoji",
	},
}


def t(text: str) -> str:
	return TRANSLATIONS.get(i18n.current(), {}).get(text, text)
