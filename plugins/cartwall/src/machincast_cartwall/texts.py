"""Les textes du cartouchier, en anglais, et leur traduction, dans la langue de MachinCast
(https://github.com/dascritch/machincast/issues/512). Le catalogue de MachinCast ne relève que son propre code : le
plugin garde le sien."""

from machincast import i18n

TRANSLATIONS: dict[str, dict[str, str]] = {
	"fr": {
		"Cartwall": "Cartouchier",
		"Skip to the next sound": "Sauter au sonore suivant",
		"Skip after the sequence": "Sauter après la séquence",
		"Cut the event by the background programming": "Couper l'événement par le fil musical",
		"Back to the start of the sound": "Revenir au début du sonore",
		"Back to the start of the event": "Recommencer l'événement",
		"Restart the sequence": "Recommencer la séquence",
		"Advance the next event": "Avancer l'événement suivant",
		"Cut the antenna by a fallback": "Couper l'antenne par un secours",
		"Cut the antenna by a feed": "Couper l'antenne par un feed",
		"Insert a sequence after this sound": "Insérer une séquence après ce sonore",
		"Insert a sound of a bank after this sound": "Insérer un sonore d'une banque après ce sonore",
		"no blank": "sans blanc",
		"a blank of 5 seconds before": "un blanc de 5 secondes avant",
		"a blank of 5 seconds after": "un blanc de 5 secondes après",
		"a blank of 5 seconds before and after": "un blanc de 5 secondes avant et après",
		"Buttons": "Boutons",
		"No button for this account: they are set in Machin interface, menu “Plugins”, “Cartouchier”.": (
			"Aucun bouton pour ce compte : ils se règlent dans Machin interface, menu « Plugins », « Cartouchier »."
		),
		"This account only consults: its buttons are for the accounts that can act on the antenna.": (
			"Ce compte ne fait que consulter : les boutons sont pour les comptes qui peuvent agir sur l'antenne."
		),
		"the bank “{name}” does not repeat: it gave the sound on air": (
			"la banque « {name} » ne se répète pas : elle a donné le sonore à l'antenne"
		),
		"“{name}” is deleted": "« {name} » est supprimé",
		"no next event": "aucun événement suivant",
		"Unknown button.": "Bouton inconnu.",
		'A button is asked: {"button": <identifier>}.': 'Un bouton est demandé : {"button": <identifiant>}.',
		"Done: {label}": "Fait : {label}",
		"Refused: {reason}": "Refusé : {reason}",
		"Account": "Compte",
		"Label": "Intitulé",
		"Colour": "Couleur",
		"Action": "Action",
		"Target": "Cible",
		"Blank": "Blanc",
		"Add": "Ajouter",
		"Replace": "Remplacer",
		"Remove": "Retirer",
		"Up": "Monter",
		"Down": "Descendre",
		"No account of the API: create one in the tab “API”.": "Aucun compte de l'API : créez-en un dans l'onglet « API ».",
		"The buttons of each account of the API, in the cartwall of Machin intranet.": (
			"Les boutons de chaque compte de l'API, dans le cartouchier de Machin intranet."
		),
		"A label is required.": "Un intitulé est demandé.",
		"A colour is written #rrggbb.": "Une couleur s'écrit #rrggbb.",
		"This action needs a target.": "Cette action demande une cible.",
		"The buttons cannot be read or saved: {error}": "Les boutons ne se lisent ni ne s'enregistrent : {error}",
	},
}


def t(text: str) -> str:
	"""Le texte dans la langue de MachinCast, s'il est traduit ; sinon en anglais."""
	return TRANSLATIONS.get(i18n.current(), {}).get(text, text)
