"""Mise en forme des heures et des durées à l'écran (https://github.com/dascritch/machincast/issues/23).

Les noms de jours et de mois sont écrits ici, en français : l'affichage ne dépend pas de la langue du poste.
"""

from datetime import datetime, timedelta
from pathlib import Path

from machincast.lecture.grille import JOURS

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


def date_et_heure(instant: datetime) -> str:
	"""« vendredi 16 octobre 2026, 20:00:30 », en heure du poste."""
	local = instant.astimezone()
	return f"{JOURS[local.weekday()]} {local.day} {MOIS[local.month - 1]} {local.year}, {local:%H:%M:%S}"


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
	return artiste_et_titre(_ou_rien(artiste), _ou_rien(titre))


def _ou_rien(valeur: object) -> str | None:
	if valeur is None:
		return None
	return str(valeur)


def oui_non(valeur: bool | None, inconnu: str = "") -> str:
	if valeur is None:
		return inconnu
	if valeur:
		return "oui"
	return "non"
