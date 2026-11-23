"""Le statut coloré de la diffusion (https://github.com/dascritch/machincast/issues/495).

Le cartouche de l'état de la diffusion, sur l'onglet Antenne, a en permanence un liseré de 2 px, rouge quand le service de diffusion est
installé, vert pour une diffusion d'essai ; « En diffusion » prend aussi ce fond, et un texte blanc ou noir, celui qui
contraste le plus. Le titre de la fenêtre dit « MachinCast », le témoin de l'onglet Antenne en diffusion, ⛶ sinon, et le
nom de la radio, metadata.public_text. Pendant un blanc à l'antenne, la diffusion tourne : le titre garde le témoin.
"""

APPLICATION = "MachinCast"
SERVICE = "#c62828"
"""Le rouge du service de diffusion installé : l'antenne pour de vrai."""
TRIAL = "#2e7d32"
"""Le vert d'une installation sans service : la diffusion d'essai."""
WHITE, BLACK = "#ffffff", "#000000"
ON_AIR_STATES = frozenset({"playing", "dead_air"})
"""Les états de la diffusion où le titre de la fenêtre porte le témoin de couleur : en diffusion, et pendant un blanc."""
NOT_BROADCASTING = "⛶"
"""Le témoin du titre de la fenêtre quand rien n'est en diffusion."""
BORDER = 2
"""L'épaisseur du liseré, en pixels."""
FRAME = "state_frame"
"""Le cartouche de l'état de la diffusion, sur la page de garde : l'état, et le bouton du moniteur de l'antenne."""


def _channel(value: int) -> float:
	"""Une composante sRGB, linéarisée comme le veut le calcul de la luminance relative du WCAG 2."""
	ratio = value / 255
	if ratio <= 0.04045:
		return ratio / 12.92
	linear: float = ((ratio + 0.055) / 1.055) ** 2.4
	return linear


def luminance(colour: str) -> float:
	"""La luminance relative d'une couleur #rrggbb."""
	red, green, blue = int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)
	return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast(first: str, second: str) -> float:
	"""Le rapport de contraste du WCAG 2 entre deux couleurs, de 1 à 21."""
	lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
	return (lighter + 0.05) / (darker + 0.05)


def contrasting_text(background: str) -> str:
	"""Le blanc ou le noir, celui qui contraste le plus avec le fond."""
	if contrast(background, WHITE) >= contrast(background, BLACK):
		return WHITE
	return BLACK


def colour(*, installed: bool) -> str:
	"""La couleur du statut : rouge pour le service installé, vert pour l'essai."""
	if installed:
		return SERVICE
	return TRIAL


def style(*, installed: bool, broadcasting: bool) -> str:
	"""La feuille de style du cartouche de l'état de la diffusion, FRAME : le liseré toujours, le fond en diffusion
	seulement, et le texte de son état qui contraste avec lui ; le bouton du moniteur de l'antenne y garde son icône
	(https://github.com/dascritch/machincast/issues/604)."""
	border = colour(installed=installed)
	if not broadcasting:
		return f"#{FRAME} {{ border: {BORDER}px solid {border}; }}"
	text = contrasting_text(border)
	return (
		f"#{FRAME} {{ background-color: {border}; border: {BORDER}px solid {border}; }} "
		f"#{FRAME} QLabel {{ color: {text}; }} "
		# Le bouton du moniteur garde les couleurs des autres boutons, pas celles du fond.
		f"#{FRAME} QToolButton {{ background-color: palette(button); color: palette(button-text);"
		" border: 1px solid palette(mid); border-radius: 3px; padding: 2px; }"
	)


def window_title(indicator: str, station: str) -> str:
	"""« MachinCast », le témoin, et le nom de la radio s'il y en a un."""
	words = [APPLICATION, indicator]
	if station.strip():
		words.append(station.strip())
	return " ".join(words)
