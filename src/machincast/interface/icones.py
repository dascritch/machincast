"""Icônes des genres d'éléments, uniformes dans toute l'interface (https://github.com/dascritch/machincast/issues/215).

Chaque genre a son icône monochrome, dessinée pour MachinCast, en SVG dans le dossier icones/ du paquet : une croche
pour un sonore, une feuille et sa liste à puces pour une séquence, un dossier pour une banque, une montre pour un
événement, un calendrier pour la grille, une boule de divination pour la simulation. Chaque SVG ne dessine qu'en
« currentColor », que icone remplace par la couleur du texte du thème (QPalette.WindowText), clair ou sombre : l'icône
se lit sur le fond de la fenêtre.

L'icône d'un genre désigne ce genre partout où il apparaît : onglets des listes, des fiches, de la grille et de la
simulation, menu « Affichage », colonne « Type » de la recherche, relations de la fiche d'un sonore. Un genre sans
icône (marque-page) n'en montre aucune : icone_de rend alors une icône nulle.
"""

from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer

DOSSIER = Path(__file__).with_name("icones")
FICHIERS = {
	"sonore": "sonore.svg",
	"séquence": "sequence.svg",
	"banque": "banque.svg",
	"événement": "evenement.svg",
	"grille": "grille.svg",
	"simulation": "simulation.svg",
}
"""Le dessin de chaque genre ; les fiches et la recherche nomment les genres ainsi."""
TAILLES = (16, 24, 32, 48, 64)
"""Les tailles dessinées : Qt prend la plus proche de celle demandée."""
COULEUR = "currentColor"
"""Le mot que chaque SVG emploie pour sa seule couleur."""

_dessinees: dict[tuple[str, str], QIcon] = {}


def couleur_du_texte() -> QColor:
	"""La couleur du texte des fenêtres, celle du thème en cours."""
	return QGuiApplication.palette().color(QPalette.ColorRole.WindowText)


def icone(genre: str, couleur: QColor | None = None) -> QIcon:
	"""L'icône du genre, dans la couleur donnée, ou dans celle du texte du thème. Lève KeyError pour un genre sans
	icône."""
	teinte = (couleur) or (couleur_du_texte())
	cle = (genre, teinte.name(QColor.NameFormat.HexArgb))
	if cle not in _dessinees:
		source = (DOSSIER / FICHIERS[genre]).read_text(encoding="utf-8").replace(COULEUR, teinte.name())
		rendu = QSvgRenderer(QByteArray(source.encode("utf-8")))
		dessinee = QIcon()
		for taille in TAILLES:
			image = QPixmap(taille, taille)
			image.fill(Qt.GlobalColor.transparent)
			peintre = QPainter(image)
			rendu.render(peintre)
			peintre.end()
			dessinee.addPixmap(image)
		_dessinees[cle] = dessinee
	return _dessinees[cle]


def icone_de(genre: str) -> QIcon:
	"""L'icône du genre, ou une icône nulle pour un genre qui n'en a pas."""
	if genre not in FICHIERS:
		return QIcon()
	return icone(genre)
