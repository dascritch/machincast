"""Export de l'onglet Airplay (https://github.com/dascritch/machincast/issues/244, spec § 8.1).

Trois formats, tous privés : chacun donne l'artiste, le titre et l'emplacement du passage, et aussi son texte public,
tel que la page publique de la diffusion l'affiche, masquage appliqué (machincast.lecture.sorties.texte_public) :

- CSV : une ligne par passage, du plus récent au plus ancien, avec les colonnes COLONNES, comme le CSV de la diffusion
  (séparateur « ; », heures « AAAA-MM-JJ HH:MM:SS », durée « HH:MM:SS »), le texte public après le titre ;
- HTML : une page autonome, sans JavaScript, avec un tableau des passages, du plus récent au plus ancien ;
- M3U : une liste de lecture étendue, du plus ancien au plus récent comme le .pls de la diffusion, chaque fichier
  précédé de sa durée et de son artiste et titre (#EXTINF), et de son texte public en commentaire. Un passage sans
  emplacement n'y figure pas.

Le CSV et le M3U s'écrivent en UTF-8, le CSV avec BOM pour les tableurs.
"""

import csv
import html
import io
from datetime import datetime, timedelta

from machincast.configuration import Metadonnees
from machincast.lecture.sorties import Ligne, artiste_et_titre, texte_public

COLONNES = (
	"debut",
	"fin",
	"duree",
	"artiste",
	"titre",
	"texte_public",
	"emplacement",
	"evenement",
	"sequence",
	"banque",
	"sans_incident",
)
FORMATS = {
	"Tableur CSV (*.csv)": ".csv",
	"Page HTML (*.html)": ".html",
	"Liste de lecture M3U (*.m3u)": ".m3u",
}
"""Filtres du sélecteur d'export, et l'extension de chacun."""
ENTETES_HTML = (
	"Début",
	"Fin",
	"Durée",
	"Artiste",
	"Titre",
	"Texte public",
	"Emplacement",
	"Événement",
	"Séquence",
	"Banque",
	"Incident",
)


def _heure(instant: datetime | None) -> str:
	if instant is None:
		return ""
	return f"{instant.astimezone():%Y-%m-%d %H:%M:%S}"


def _duree(duree: timedelta | None) -> str:
	if duree is None:
		return ""
	secondes = round(duree.total_seconds())
	return f"{secondes // 3600:02d}:{secondes % 3600 // 60:02d}:{secondes % 60:02d}"


def _incident(ligne: Ligne) -> str:
	"""Comme la colonne « Incident » de l'airplay de l'interface : « oui » pour un passage qui en a eu un."""
	if ligne.sans_incident is False:
		return "oui"
	return ""


def _sans_incident(ligne: Ligne) -> str:
	if ligne.sans_incident is None:
		return ""
	if ligne.sans_incident:
		return "oui"
	return "non"


def _valeurs(ligne: Ligne, metadonnees: Metadonnees) -> list[str]:
	return [
		_heure(ligne.debut),
		_heure(ligne.fin),
		_duree(ligne.duree),
		(ligne.artiste) or (""),
		(ligne.titre) or (""),
		texte_public(ligne, metadonnees),
		(ligne.emplacement) or (""),
		(ligne.evenement) or (""),
		(ligne.sequence) or (""),
		(ligne.banque) or (""),
	]


def en_csv(lignes: list[Ligne], metadonnees: Metadonnees) -> str:
	tampon = io.StringIO()
	ecrivain = csv.writer(tampon, delimiter=";", lineterminator="\r\n")
	ecrivain.writerow(COLONNES)
	for ligne in lignes:
		ecrivain.writerow([*_valeurs(ligne, metadonnees), _sans_incident(ligne)])
	return tampon.getvalue()


def en_html(lignes: list[Ligne], metadonnees: Metadonnees, titre: str, instant: datetime) -> str:
	entetes = "".join(f"<th>{html.escape(entete)}</th>" for entete in ENTETES_HTML)
	rangees = "\n".join(
		'\t\t\t<tr class="passage">'
		+ "".join(f"<td>{html.escape(valeur)}</td>" for valeur in [*_valeurs(ligne, metadonnees), _incident(ligne)])
		+ "</tr>"
		for ligne in lignes
	)
	return f"""<!DOCTYPE html>
<html lang="fr">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>{html.escape(titre)}</title>
	<style>
		body {{ font-family: system-ui, sans-serif; margin: 1rem; }}
		table {{ border-collapse: collapse; }}
		th, td {{ border-bottom: 1px solid #ccc; padding: 0.2rem 0.5rem; text-align: left; vertical-align: top; }}
		td:nth-child(-n+3) {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
	</style>
</head>
<body>
	<h1>{html.escape(titre)}</h1>
	<table>
		<thead><tr>{entetes}</tr></thead>
		<tbody>
{rangees}
		</tbody>
	</table>
	<footer><p>Exporté le <time datetime="{instant.isoformat()}">{_heure(instant)}</time></p></footer>
</body>
</html>
"""


def en_m3u(lignes: list[Ligne], metadonnees: Metadonnees) -> str:
	entrees = ["#EXTM3U"]
	for ligne in reversed(lignes):
		if not ligne.emplacement:
			continue
		duree = -1
		if ligne.duree is not None:
			duree = round(ligne.duree.total_seconds())
		entrees.append(f"#EXTINF:{duree},{(artiste_et_titre(ligne)) or (ligne.emplacement)}")
		entrees.append(f"# texte public : {texte_public(ligne, metadonnees)}")
		entrees.append(ligne.emplacement)
	return "\n".join([*entrees, ""])
