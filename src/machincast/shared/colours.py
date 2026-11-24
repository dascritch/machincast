"""La couleur d'un événement, qu'un plugin peut donner (https://github.com/dascritch/machincast/issues/635).

Le point du cœur « grid.event_colour » est demandé, avec « event », l'identifiant de l'événement, ou None pour la
couleur d'une priorité, et « priority », sa priorité, ou None quand l'appelant ne la connaît pas : un tableau d'airplay
n'a que l'événement. Le plugin répond une couleur « #rrggbb », ou None pour laisser celle du cœur ; la première
couleur valide l'emporte. Le calendrier de l'interface, celui de l'intranet et les tableaux d'airplay la lisent.

readable_text donne le texte, noir ou blanc, le plus contrasté sur une couleur de fond, selon le contraste de WCAG 2
(https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio).
"""

import re

from machincast import plugins

EVENT_COLOUR = "grid.event_colour"
"""Le point d'extension de la couleur d'un événement (machincast.plugins.points.CORE)."""
HEX = re.compile(r"#[0-9a-fA-F]{6}")
BLACK = "#000000"
WHITE = "#ffffff"


def event_colour(event: int | None, priority: str | None) -> str | None:
	"""La couleur que donne un plugin à l'événement, ou à la priorité sans événement ; None sans plugin qui réponde."""
	for _plugin, answer in plugins.active().points.collect(EVENT_COLOUR, {"event": event, "priority": priority}):
		if (isinstance(answer, str)) and (HEX.fullmatch(answer) is not None):
			return answer.lower()
	return None


def _channel(value: int) -> float:
	share = value / 255
	if share <= 0.03928:
		return share / 12.92
	return float(((share + 0.055) / 1.055) ** 2.4)


def luminance(colour: str) -> float:
	"""La luminance relative de WCAG 2, de 0 (noir) à 1 (blanc)."""
	red, green, blue = int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)
	return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast(first: str, second: str) -> float:
	"""Le rapport de contraste de WCAG 2, de 1 à 21."""
	lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
	return (lighter + 0.05) / (darker + 0.05)


def readable_text(background: str) -> str:
	"""Le texte, noir ou blanc, le plus contrasté sur ce fond."""
	if contrast(background, BLACK) >= contrast(background, WHITE):
		return BLACK
	return WHITE


def mixed(colour: str, share: float, other: str = WHITE) -> str:
	"""La couleur mêlée à une autre, blanc par défaut : share, de 0 à 1, est la part de la couleur."""
	parts = []
	for start in (1, 3, 5):
		value = share * int(colour[start : start + 2], 16) + (1 - share) * int(other[start : start + 2], 16)
		parts.append(f"{round(value):02x}")
	return "#" + "".join(parts)
