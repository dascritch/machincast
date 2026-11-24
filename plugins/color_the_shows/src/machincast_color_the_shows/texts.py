"""Les textes des couleurs des émissions, en anglais, et leur traduction, dans la langue de MachinCast
(https://github.com/dascritch/machincast/issues/628). Le catalogue de MachinCast ne relève que son propre code : le
plugin garde le sien."""

from machincast import i18n

TRANSLATIONS: dict[str, dict[str, str]] = {
	"fr": {
		"Show colours": "Couleurs des émissions",
		"Genre": "Genre",
		"&Genre": "&Genre",
		"no genre": "aucun genre",
		"The colour of the event in the calendars and the tables of airplay; without genre, the colour of its priority.": (
			"La couleur de l'événement dans les calendriers et les tableaux d'airplay ; sans genre, la couleur de sa"
			" priorité."
		),
		"The genres of the shows, and the colours of the events without genre, in the calendar of Machin interface, the"
		" one of Machin intranet and the tables of airplay.": (
			"Les genres des émissions, et les couleurs des événements sans genre, dans le calendrier de Machin interface,"
			" celui de Machin intranet et les tableaux d'airplay."
		),
		"Genres": "Genres",
		"Name": "Nom",
		"Colour": "Couleur",
		"Add": "Ajouter",
		"Remove": "Retirer",
		"Choose…": "Choisir…",
		"Click to choose the colour": "Cliquer pour choisir la couleur",
		"Colours of the events without genre": "Couleurs des événements sans genre",
		"Background programming": "Fil antenne",
		"Show": "Émission",
		"Special": "Spéciale",
		"Save": "Enregistrer",
		"new genre": "nouveau genre",
		"Saved.": "Enregistré.",
		"A genre has no name.": "Un genre n'a pas de nom.",
		"Two genres are named “{name}”.": "Deux genres s'appellent « {name} ».",
		"The genre name “{name}” is too long: {length} characters at most.": (
			"Le nom de genre « {name} » est trop long : {length} caractères au plus."
		),
		"“{colour}” is not a colour #rrggbb, for “{name}”.": "« {colour} » n'est pas une couleur #rrggbb, pour « {name} ».",
		"The colours cannot be read or saved: {error}": "Les couleurs ne peuvent être lues ni enregistrées : {error}",
	},
}


def t(text: str) -> str:
	return TRANSLATIONS.get(i18n.current(), {}).get(text, text)
