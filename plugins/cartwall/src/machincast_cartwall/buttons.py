"""Les boutons du cartouchier, et la demande que chacun envoie à Machin player
(https://github.com/dascritch/machincast/issues/512).

Les actions sont celles du menu « Diffusion » de l'interface qui agissent sur l'antenne, sauf démarrer et arrêter la
diffusion : sauter, recommencer, couper, avancer et insérer (spec § 4.9, socket d'état § 5.4). Une insertion peut
demander un blanc de 5 secondes avant, après, ou les deux (https://github.com/dascritch/machincast/issues/594).
"""

from dataclasses import dataclass
from typing import Any

from machincast_cartwall.texts import t

ACTIONS: dict[str, tuple[str, str | None]] = {
	"skip_sound": ("Skip to the next sound", None),
	"skip_sequence": ("Skip after the sequence", None),
	"cut_to_background": ("Cut the event by the background programming", None),
	"restart_sound": ("Back to the start of the sound", None),
	"restart_event": ("Back to the start of the event", None),
	"restart_sequence": ("Restart the sequence", None),
	"advance": ("Advance the next event", None),
	"cut_by_fallback": ("Cut the antenna by a fallback", "fallback"),
	"cut_by_feed": ("Cut the antenna by a feed", "feed"),
	"insert_sequence": ("Insert a sequence after this sound", "sequence"),
	"insert_bank": ("Insert a sound of a bank after this sound", "bank"),
}
"""Chaque action, son libellé, et ce qu'elle vise : un secours, un feed, une séquence, une banque, ou rien."""
INTERRUPTIONS = {
	"skip_sound": "sound",
	"skip_sequence": "sequence",
	"cut_to_background": "event",
	"restart_sound": "restart_sound",
	"restart_event": "restart_event",
	"restart_sequence": "restart_sequence",
}
"""Les actions qui sont une interruption de Machin player, et ce qu'elles interrompent."""
BLANKS = {
	None: "no blank",
	"before": "a blank of 5 seconds before",
	"after": "a blank of 5 seconds after",
	"both": "a blank of 5 seconds before and after",
}
INSERTIONS = ("insert_sequence", "insert_bank")
DEFAULT_COLOUR = "#3a6ea5"


@dataclass(frozen=True)
class Button:
	"""Un bouton d'un compte : son intitulé, sa couleur, son action, et ce qu'elle vise."""

	id: int
	label: str
	colour: str
	action: str
	target: int | None = None
	"""La séquence, la banque, le secours ou le feed visé ; None pour une action qui ne vise rien."""
	blank: str | None = None
	target_name: str | None = None
	unusable: str | None = None
	"""Pourquoi il ne peut pas servir maintenant ; None s'il le peut."""


def action_label(action: str) -> str:
	return t(ACTIONS[action][0])


def target_kind(action: str) -> str | None:
	return ACTIONS[action][1]


def request(button: Button, state: dict[str, Any]) -> dict[str, Any] | None:
	"""La demande à Machin player, sans le compte, que le serveur intranet ajoute ; None si elle n'a pas de sens
	maintenant : avancer sans événement suivant publié."""
	interruption = INTERRUPTIONS.get(button.action)
	if interruption is not None:
		return {"command": "interrupt", "item": interruption}
	if button.action == "advance":
		following = state.get("next_event")
		if not isinstance(following, dict):
			return None
		return {"command": "advance", "event": following.get("id")}
	if button.action == "cut_by_fallback":
		return {"command": "cut_by_fallback", "event": button.target}
	if button.action == "cut_by_feed":
		return {"command": "cut_by_feed", "feed": button.target}
	key = "bank"
	if button.action == "insert_sequence":
		key = "sequence"
	asked: dict[str, Any] = {"command": "insert", key: button.target}
	if button.blank is not None:
		asked["blank"] = button.blank
	return asked


def as_json(button: Button) -> dict[str, Any]:
	"""Le bouton, tel que la page et l'API le donnent."""
	return {
		"id": button.id,
		"label": button.label,
		"colour": button.colour,
		"action": button.action,
		"target": button.target_name,
		"blank": button.blank,
		"usable": button.unusable is None,
		"reason": button.unusable,
	}
