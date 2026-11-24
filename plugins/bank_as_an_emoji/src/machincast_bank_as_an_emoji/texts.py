"""Les textes de la banque en emoji, en anglais, et leur traduction, dans la langue de MachinCast
(https://github.com/dascritch/machincast/issues/505). Le catalogue de MachinCast ne relève que son propre code : le
plugin garde le sien."""

from machincast import i18n

TRANSLATIONS: dict[str, dict[str, str]] = {
	"fr": {
		"Emoji of the bank": "Emoji de la banque",
		"The emoji at the start of the internal name, shown in the tables of airplay and of the coming sounds; choose"
		" one, write or paste another, or leave it empty.": (
			"L'emoji au début du nom interne, montré dans les tableaux d'airplay et des sonores à venir ; en choisir un,"
			" en écrire ou en coller un autre, ou le laisser vide."
		),
		"Internal name, without its emoji": "Nom interne, sans son emoji",
		"“{emoji}” is not an emoji.": "« {emoji} » n'est pas un emoji.",
	},
}


def t(text: str) -> str:
	return TRANSLATIONS.get(i18n.current(), {}).get(text, text)
