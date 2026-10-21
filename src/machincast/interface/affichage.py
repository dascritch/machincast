"""Mise en forme des heures et des durées à l'écran (https://github.com/dascritch/machincast/issues/23).

Les noms de jours et de mois sont écrits ici, en français : l'affichage ne dépend pas de la langue du poste.
"""

from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QCheckBox, QDateTimeEdit, QStyle, QWidget

from machincast.conversion import texte_ou_rien

MOIS = (
	"janvier",
	"février",
	"mars",
	"avril",
	"mai",
	"juin",
	"juillet",
	"août",
	"septembre",
	"octobre",
	"novembre",
	"décembre",
)
VIDE = "—"
"""Ce que montre un champ sans valeur : aucun sonore, par exemple."""


def heure(instant: datetime | None, inconnue: str = "inconnue") -> str:
	"""« 20:03:34 », en heure du poste, à la seconde près ; inconnue sans instant."""
	if instant is None:
		return inconnue
	return f"{instant.astimezone():%H:%M:%S}"


def duree(secondes: float | timedelta | None) -> str:
	"""« 3:34 », ou « 1:02:05 » au-delà d'une heure, à la seconde entamée près ; « inconnue » sans durée."""
	if secondes is None:
		return "inconnue"
	if isinstance(secondes, timedelta):
		secondes = secondes.total_seconds()
	heures, reste = divmod(int(secondes), 3600)
	minutes, secondes_restantes = divmod(reste, 60)
	if heures > 0:
		return f"{heures}:{minutes:02d}:{secondes_restantes:02d}"
	return f"{minutes}:{secondes_restantes:02d}"


def artiste_et_titre(artiste: str | None, titre: str | None) -> str:
	"""« Les Gaufres – Café à minuit », ou ce qui est connu des deux."""
	texte = " – ".join(partie for partie in (artiste, titre) if partie)
	return (texte) or ("(sans titre)")


def nom_du_sonore(artiste: object, titre: object, emplacement: object, adresse: object) -> str:
	"""Artiste et titre ; sans eux, le nom du fichier, ou l'adresse du stream."""
	if (artiste is None) and (titre is None):
		if emplacement is not None:
			return Path(str(emplacement)).name
		return str((adresse) or (""))
	return artiste_et_titre(texte_ou_rien(artiste), texte_ou_rien(titre))


def oui_non(valeur: bool | None, inconnu: str = "") -> str:
	if valeur is None:
		return inconnu
	if valeur:
		return "oui"
	return "non"


def hors_durees(
	duree_du_sonore: timedelta | None,
	minimum: timedelta | None,
	maximum: timedelta | None,
	banque: str | None = None,
) -> str | None:
	"""« 3:20 : plus court que le minimum de la banque « Jingles », 3:30. » : un sonore hors des durées d'une banque
	(https://github.com/dascritch/machincast/issues/147), nommée si on la donne. None pour un sonore dans ses durées,
	ou de durée inconnue."""
	nom = "la banque"
	if banque is not None:
		nom = f"la banque « {banque} »"
	if duree_du_sonore is None:
		return None
	if (minimum is not None) and (duree_du_sonore < minimum):
		return f"{duree(duree_du_sonore)} : plus court que le minimum de {nom}, {duree(minimum)}."
	if (maximum is not None) and (duree_du_sonore > maximum):
		return f"{duree(duree_du_sonore)} : plus long que le maximum de {nom}, {duree(maximum)}."
	return None


def icone_d_anomalie(widget: QWidget) -> QIcon:
	"""L'icône d'avertissement du style du poste, qui marque ce qui est en anomalie."""
	return widget.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)


UNITES_DE_TAILLE = ("ko", "Mo", "Go", "To")


def taille(octets: int) -> str:
	"""« 1,2 Mo », en unités décimales, à un chiffre après la virgule ; « 512 o » en deçà d'un kilo-octet."""
	if octets < 1000:
		return f"{octets} o"
	valeur = octets / 1000
	rang = 0
	while (valeur >= 1000) and (rang < len(UNITES_DE_TAILLE) - 1):
		valeur /= 1000
		rang += 1
	return f"{valeur:.1f} {UNITES_DE_TAILLE[rang]}".replace(".", ",")


def date(instant: datetime) -> str:
	"""« 2026-10-14 07:30:00 », en heure du poste."""
	return f"{instant.astimezone():%Y-%m-%d %H:%M:%S}"


def date_cochee(case: QCheckBox, date: QDateTimeEdit) -> datetime | None:
	"""La date saisie, à l'heure du poste ; None si sa case n'est pas cochée."""
	if not case.isChecked():
		return None
	return datetime.fromtimestamp(date.dateTime().toSecsSinceEpoch()).astimezone()
