"""Les textes de la normalisation du niveau, en anglais, et leur traduction, dans la langue de MachinCast
(https://github.com/dascritch/machincast/issues/43). Le catalogue de MachinCast ne relève que son propre code : le
plugin garde le sien."""

from machincast import i18n

TRANSLATIONS: dict[str, dict[str, str]] = {
	"fr": {
		"target is a loudness in LUFS, from -40 to -5": "target est une sonie en LUFS, de -40 à -5",
		"ceiling is a peak in dBFS, from -12 to 0": "ceiling est une crête en dBFS, de -12 à 0",
		"loudness_normalization: settings refused, no gain applied: {reason}": (
			"loudness_normalization : réglages refusés, aucun gain appliqué : {reason}"
		),
		"Level": "Niveau",
		"Not measured yet: the full audit of Machin indexer measures it.": (
			"Pas encore mesuré : l'audit complet de Machin indexer le mesure."
		),
		"Loudness {integrated} LUFS, peak {peak} dBFS": "Sonie {integrated} LUFS, crête {peak} dBFS",
		"unknown": "inconnue",
		"Manual adjustment": "Ajustement manuel",
		"Added to the automatic gain, which brings the loudness to the target; bounded so that the peak never exceeds"
		" the ceiling.": (
			"Ajouté au gain automatique, qui porte la sonie à la cible ; borné pour que la crête ne dépasse jamais le"
			" plafond."
		),
		" dB": " dB",
		"Gain applied: {gain} dB (automatic {automatic} dB, target {target} LUFS, ceiling {ceiling} dBFS)": (
			"Gain appliqué : {gain} dB (automatique {automatic} dB, cible {target} LUFS, plafond {ceiling} dBFS)"
		),
		"Gain applied: {gain} dB": "Gain appliqué : {gain} dB",
		"The loudness normalisation is not set: its settings are refused.": (
			"La normalisation du niveau n'est pas réglée : ses réglages sont refusés."
		),
		"level adjusted": "niveau ajusté",
		"“{location}”: its peak of {peak} dBFS would exceed the ceiling of {ceiling} dBFS with a gain of {gain} dB:"
		" manual adjustment brought from {before} to {after} dB": (
			"« {location} » : sa crête de {peak} dBFS dépasserait le plafond de {ceiling} dBFS avec un gain de {gain} dB"
			" : ajustement manuel ramené de {before} à {after} dB"
		),
		"loudness_normalization: {error}": "loudness_normalization : {error}",
		"The loudness of each sound is brought to the target by the gain of Machin player, never beyond the peak"
		" ceiling. Machin player and Machin indexer take these settings at their next start.": (
			"La sonie de chaque sonore est portée à la cible par le gain de Machin player, jamais au-delà du plafond de"
			" crête. Machin player et Machin indexer prennent ces réglages à leur prochain démarrage."
		),
		"Target loudness": "Sonie visée",
		"Peak ceiling": "Plafond de crête",
		" LUFS": " LUFS",
		" dBFS": " dBFS",
		"Save": "Enregistrer",
		"In the bank “{name}”: {gain}": "Dans la banque « {name} » : {gain}",
		"Target loudness of its own": "Sonie visée propre à la banque",
		"Peak ceiling of its own": "Plafond de crête propre à la banque",
		"Ticked, it replaces the setting of the plugin for the sounds that this bank provides": (
			"Cochée, elle remplace le réglage du plugin pour les sonores que fournit cette banque"
		),
		"The settings cannot be saved: {error}": "Les réglages ne peuvent être enregistrés : {error}",
		"Saved. Restart the broadcast and the indexing for them to take these settings.": (
			"Enregistré. Relancez la diffusion et l'indexation pour qu'elles prennent ces réglages."
		),
	},
}


def t(text: str) -> str:
	return TRANSLATIONS.get(i18n.current(), {}).get(text, text)
