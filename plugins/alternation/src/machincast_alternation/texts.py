"""Les textes des émissions en alternance, en anglais, et leur traduction, dans la langue de MachinCast
(https://github.com/dascritch/machincast/issues/609). Le catalogue de MachinCast ne relève que son propre code : le
plugin garde le sien."""

from machincast import i18n

TRANSLATIONS: dict[str, dict[str, str]] = {
	"fr": {
		"Shows in alternation": "Émissions en alternance",
		"This event plays, each week, one of the shows below, instead of a play list": (
			"Cet événement joue, chaque semaine, l'une des émissions ci-dessous, à la place d'une liste de lecture"
		),
		"Shows that share the slot": "Émissions qui se partagent le créneau",
		"Rhythm": "Rythme",
		"Rotation": "Rotation",
		"Monthly, by the week of the month": "Par mois, selon la semaine du mois",
		"Fortnightly, every other week": "Par quinzaine, une semaine sur deux",
		"{rank} week of the fortnight": "{rank} semaine de la quinzaine",
		"{week}, including {day}": "{week}, dont le {day}",
		"Coming broadcasts": "Passages à venir",
		"{rank} {day} of the month": "{rank} {day} du mois",
		"week {rank} of the month": "{rank} semaine du mois",
		"1st": "1er",
		"2nd": "2e",
		"3rd": "3e",
		"4th": "4e",
		"5th": "5e",
		"1st (feminine)": "1re",
		"— the event itself": "— l'événement lui-même",
		"According to the rotation: {name}": "Selon la rotation : {name}",
		"Save the event to see its coming broadcasts.": "Enregistrez l'événement pour voir ses passages à venir.",
		"Choose at least one show that shares the slot.": "Choisissez au moins une émission qui partage le créneau.",
		"No show or special to share the slot: create them first.": (
			"Aucune émission ni spécial pour partager le créneau : créez-les d'abord."
		),
	},
}


def t(text: str) -> str:
	"""Le texte dans la langue de MachinCast, s'il est traduit ; sinon en anglais."""
	return TRANSLATIONS.get(i18n.current(), {}).get(text, text)
