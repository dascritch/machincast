"""Icônes des genres d'éléments, uniformes dans toute l'interface (https://github.com/dascritch/machincast/issues/215).

Chaque genre a son icône monochrome, dessinée pour MachinCast, en SVG dans le dossier icones/ du paquet : une croche
pour un sonore, une feuille et sa liste à puces pour une séquence, un dossier pour une banque, une montre pour un
événement, un calendrier pour la grille, une boule de divination pour la simulation, et un casque pour la pré-écoute.
Chaque SVG ne dessine qu'en « currentColor », que icone remplace par la couleur du texte du thème (QPalette.WindowText),
clair ou sombre : l'icône se lit sur le fond de la fenêtre.

L'icône d'un genre désigne ce genre partout où il apparaît : onglets des listes, des fiches, de la grille et de la
simulation, menu « Affichage », colonne « Type » de la recherche, relations de la fiche d'un sonore. Un genre sans
icône (feed) n'en montre aucune : icon_of rend alors une icône nulle.
"""

from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer

FOLDER = Path(__file__).with_name("icons")
FILES = {
	"sound": "sound.svg",
	"sequence": "sequence.svg",
	"bank": "bank.svg",
	"event": "event.svg",
	"grid": "grid.svg",
	"simulation": "simulation.svg",
	"preview": "preview.svg",
	"airplay": "airplay.svg",
}
"""Le dessin de chaque genre ; les fiches et la recherche nomment les genres ainsi. « preview », un casque, n'est pas
un genre : il marque chaque bouton et chaque entrée de menu qui lance une pré-écoute
(https://github.com/dascritch/machincast/issues/223). « airplay » marque l'onglet de l'historique de diffusion
(https://github.com/dascritch/machincast/issues/244)."""
SIZES = (16, 24, 32, 48, 64)
"""Les tailles dessinées : Qt prend la plus proche de celle demandée."""
COLOUR = "currentColor"
"""Le mot que chaque SVG emploie pour sa seule couleur."""

_drawn_list: dict[tuple[str, str], QIcon] = {}


def text_colour() -> QColor:
	"""La couleur du texte des fenêtres, celle du thème en cours."""
	return QGuiApplication.palette().color(QPalette.ColorRole.WindowText)


def icon(category: str, colour: QColor | None = None) -> QIcon:
	"""L'icône du genre, dans la couleur donnée, ou dans celle du texte du thème. Lève KeyError pour un genre sans
	icône."""
	tint = (colour) or (text_colour())
	key = (category, tint.name(QColor.NameFormat.HexArgb))
	if key not in _drawn_list:
		source = (FOLDER / FILES[category]).read_text(encoding="utf-8").replace(COLOUR, tint.name())
		rendering = QSvgRenderer(QByteArray(source.encode("utf-8")))
		drawn = QIcon()
		for size in SIZES:
			image = QPixmap(size, size)
			image.fill(Qt.GlobalColor.transparent)
			with QPainter(image) as painter:
				rendering.render(painter)
			drawn.addPixmap(image)
		_drawn_list[key] = drawn
	return _drawn_list[key]


def icon_of(category: str) -> QIcon:
	"""L'icône du genre, ou une icône nulle pour un genre qui n'en a pas."""
	if category not in FILES:
		return QIcon()
	return icon(category)
