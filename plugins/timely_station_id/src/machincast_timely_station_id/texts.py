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
	},
}


def t(text: str) -> str:
	return TRANSLATIONS.get(i18n.current(), {}).get(text, text)
