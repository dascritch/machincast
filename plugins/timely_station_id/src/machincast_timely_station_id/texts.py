"""Les textes du station ID régulier, en anglais, et leur traduction, dans la langue de MachinCast
(https://github.com/dascritch/machincast/issues/460). Le catalogue de MachinCast ne relève que son propre code : le
plugin garde le sien."""

from machincast import i18n

TRANSLATIONS: dict[str, dict[str, str]] = {
	"fr": {
		'the bank of the station IDs is missing: bank = "…"': 'la banque des station ID manque : bank = "…"',
		"watched is a list of names of banks": "watched est une liste de noms de banques",
		"minimum and maximum are minutes, the minimum not above the maximum": (
			"minimum et maximum sont des minutes, le minimum pas au-dessus du maximum"
		),
		"placement is “before” or “after”": "placement vaut « before » ou « after »",
		"timely_station_id: settings refused, no station ID inserted: {reason}": (
			"timely_station_id : réglages refusés, aucun station ID inséré : {reason}"
		),
		"timely_station_id: no bank “{name}”": "timely_station_id : aucune banque « {name} »",
		"Regular station ID": "Station ID régulier",
		"A station ID of the bank “{bank}”, every {minimum} to {maximum} minutes, whatever the length of the songs": (
			"Un station ID de la banque « {bank} », toutes les {minimum} à {maximum} minutes, quelle que soit la durée"
			" des morceaux"
		),
		"A station ID at regular intervals, once its settings are in machincast.toml": (
			"Un station ID à intervalles réguliers, une fois ses réglages dans machincast.toml"
		),
		"A station ID at regular intervals, in the events whose box “Regular station ID” is ticked. Machin player"
		" takes these settings at its next start.": (
			"Un station ID à intervalles réguliers, dans les événements dont la case « Station ID régulier » est"
			" cochée. Machin player prend ces réglages à son prochain démarrage."
		),
		"These banks also say the name of the radio, for instance a seasonal jingle: a play of one of them counts as a"
		" station ID": (
			"Ces banques disent aussi le nom de la radio, par exemple un jingle saisonnier : un passage de l'une d'elles"
			" compte comme un station ID"
		),
		"Before the song that would exceed the maximum, once the minimum is past": (
			"Avant le morceau qui ferait dépasser le maximum, une fois le minimum passé"
		),
		"After the maximum, without moving any song forward": "Après le maximum, sans avancer aucun morceau",
		"Save": "Enregistrer",
		" min": " min",
		"Bank of the station IDs": "Banque des station ID",
		"Banks that also announce the station": "Banques qui annoncent aussi la station",
		"Minimum between two station IDs": "Minimum entre deux station ID",
		"Maximum between two station IDs": "Maximum entre deux station ID",
		"Placement": "Placement",
		"The banks cannot be read: {error}": "Les banques ne peuvent être lues : {error}",
		"— choose a bank —": "— choisir une banque —",
		"The settings cannot be saved: {error}": "Les réglages ne peuvent être enregistrés : {error}",
		"Saved. Restart the broadcast for Machin player to take them.": (
			"Enregistré. Relancez la diffusion pour que Machin player les prenne."
		),
	},
}


def t(text: str) -> str:
	return TRANSLATIONS.get(i18n.current(), {}).get(text, text)
