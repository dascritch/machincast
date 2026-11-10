"""Tableaux en zebra (https://github.com/dascritch/machincast/issues/412).

Les lignes des tableaux, des arbres et des listes de l'interface alternent deux fonds : celui du thème (QPalette.Base)
et un fond alterné (QPalette.AlternateBase), que chaque vue dessine dès qu'elle a alternatingRowColors. Le fond
alterné du thème est souvent trop proche du fond pour se voir (#f7f7f7 sur blanc dans Fusion), ou lui est égal : il
est recalculé ici, à partir du fond et du texte du thème, clair comme sombre.

Le fond alterné est le fond, mêlé d'un peu de la couleur du texte, juste assez pour que le contraste entre les deux
fonds atteigne VISIBLE (1,12:1) : les lignes se distinguent, sans que l'écart attire l'œil. Il ne s'éloigne jamais du
fond au point que le texte, sur lui, descende sous READABLE (4,5:1), le contraste minimal d'un texte de taille
courante du RGAA (critère 3.2, celui des WCAG 1.4.3) : le mélange s'arrête avant, et un thème dont le texte n'atteint
déjà pas ce contraste sur le fond garde un seul fond.

install pose le fond alterné dans la palette de l'application, rôle par rôle : les autres couleurs suivent toujours le
thème, et chaque changement de la palette de l'application (passage du thème clair au sombre, autre thème) recalcule
le fond alterné (QGuiApplication.paletteChanged) ; poser celui qu'elle a déjà ne change rien, ce qui arrête là.
"""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPalette

VISIBLE = 1.12
"""Le contraste visé entre le fond et le fond alterné : visible, sans être fort."""
READABLE = 4.5
"""Le contraste minimal du texte sur un fond, pour un texte de taille courante (RGAA 3.2)."""
STEP = 0.005
"""Le pas du mélange du texte dans le fond."""
GROUPS = (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled)


def _channel(value: int) -> float:
	share = value / 255
	if share <= 0.04045:
		return share / 12.92
	return float(((share + 0.055) / 1.055) ** 2.4)


def luminance(colour: QColor) -> float:
	"""La luminance relative des WCAG, de 0 (noir) à 1 (blanc)."""
	return 0.2126 * _channel(colour.red()) + 0.7152 * _channel(colour.green()) + 0.0722 * _channel(colour.blue())


def contrast(first: QColor, second: QColor) -> float:
	"""Le rapport de contraste des WCAG, de 1 à 21."""
	light = max(luminance(first), luminance(second))
	dark = min(luminance(first), luminance(second))
	return (light + 0.05) / (dark + 0.05)


def _mix(base: QColor, text: QColor, share: float) -> QColor:
	return QColor(
		round(base.red() + (text.red() - base.red()) * share),
		round(base.green() + (text.green() - base.green()) * share),
		round(base.blue() + (text.blue() - base.blue()) * share),
	)


def alternate(base: QColor, text: QColor) -> QColor:
	"""Le fond alterné : le fond, mêlé du texte jusqu'au contraste VISIBLE avec lui, sans que le texte y descende
	sous READABLE ; le fond lui-même si le texte n'y atteint déjà pas READABLE."""
	found = QColor(base)
	share = STEP
	while share < 1:
		candidate = _mix(base, text, share)
		if contrast(candidate, text) < READABLE:
			return found
		found = candidate
		if contrast(candidate, base) >= VISIBLE:
			return found
		share += STEP
	return found


def zebra(palette: QPalette) -> QPalette:
	"""Une palette qui ne fixe que le fond alterné de chaque groupe, d'après le fond et le texte de celle donnée."""
	result = QPalette()
	for group in GROUPS:
		colour = alternate(palette.color(group, QPalette.ColorRole.Base), palette.color(group, QPalette.ColorRole.Text))
		result.setColor(group, QPalette.ColorRole.AlternateBase, colour)
	return result


def apply(application: QGuiApplication) -> bool:
	"""Pose le fond alterné dans la palette de l'application ; False s'il y était déjà."""
	current = application.palette()
	wanted = zebra(current)
	same = True
	for group in GROUPS:
		role = QPalette.ColorRole.AlternateBase
		if current.color(group, role) != wanted.color(group, role):
			same = False
	if same:
		return False
	palette = QPalette(current)
	for group in GROUPS:
		palette.setColor(group, QPalette.ColorRole.AlternateBase, wanted.color(group, QPalette.ColorRole.AlternateBase))
	application.setPalette(palette)
	return True


INSTALLED = "machincast_zebra"
"""La propriété de l'application qui note que le fond alterné la suit déjà."""


def install(application: QGuiApplication) -> None:
	"""Le fond alterné, maintenant et à chaque changement de la palette ; une seule fois par application."""
	apply(application)
	if application.property(INSTALLED):
		return
	application.setProperty(INSTALLED, True)
	application.paletteChanged.connect(lambda _palette: QTimer.singleShot(0, application, lambda: apply(application)))
