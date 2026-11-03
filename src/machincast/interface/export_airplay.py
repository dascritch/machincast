"""Export de l'onglet Airplay (https://github.com/dascritch/machincast/issues/244, spec § 8.1).

Trois formats, tous privés : chacun donne l'artiste, le titre et l'emplacement du passage, et aussi son texte public,
tel que la page publique de la diffusion l'affiche, masquage appliqué (machincast.player.outputs.public_text) :

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

from machincast.configuration import Metadata
from machincast.i18n import _, current
from machincast.player.outputs import Line, artist_and_title, public_text

COLUMNS = (
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
	_("CSV spreadsheet (*.csv)"): ".csv",
	_("HTML page (*.html)"): ".html",
	_("M3U playlist (*.m3u)"): ".m3u",
}
"""Filtres du sélecteur d'export, et l'extension de chacun."""
HTML_HEADERS = (
	_("Start"),
	_("End"),
	_("Duration"),
	_("Artist"),
	_("Title"),
	_("Public text"),
	_("Location"),
	_("Event"),
	_("Sequence"),
	_("Bank"),
	_("Incident"),
)


def _hour(instant: datetime | None) -> str:
	if instant is None:
		return ""
	return f"{instant.astimezone():%Y-%m-%d %H:%M:%S}"


def _duration(duration: timedelta | None) -> str:
	if duration is None:
		return ""
	seconds = round(duration.total_seconds())
	return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _incident(line: Line) -> str:
	"""Comme la colonne « Incident » de l'airplay de l'interface : « oui » pour un passage qui en a eu un."""
	if line.without_incident is False:
		return _("yes")
	return ""


def _without_incident(line: Line) -> str:
	if line.without_incident is None:
		return ""
	if line.without_incident:
		return "oui"
	return "non"


def _values(line: Line, metadata: Metadata) -> list[str]:
	return [
		_hour(line.start),
		_hour(line.end),
		_duration(line.duration),
		(line.artist) or (""),
		(line.title) or (""),
		public_text(line, metadata),
		(line.location) or (""),
		(line.event) or (""),
		(line.sequence) or (""),
		(line.bank) or (""),
	]


def in_csv(lines: list[Line], metadata: Metadata) -> str:
	buffer = io.StringIO()
	writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
	writer.writerow(COLUMNS)
	for line in lines:
		writer.writerow([*_values(line, metadata), _without_incident(line)])
	return buffer.getvalue()


def in_html(lines: list[Line], metadata: Metadata, title: str, instant: datetime) -> str:
	headers = "".join(f"<th>{html.escape(header)}</th>" for header in HTML_HEADERS)
	rows = "\n".join(
		'\t\t\t<tr class="passage">'
		+ "".join(f"<td>{html.escape(value)}</td>" for value in [*_values(line, metadata), _incident(line)])
		+ "</tr>"
		for line in lines
	)
	exported = _("Exported on {time}").format(
		time=f'<time datetime="{instant.isoformat()}">{html.escape(_hour(instant))}</time>'
	)
	return f"""<!DOCTYPE html>
<html lang="{current()}">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>{html.escape(title)}</title>
	<style>
		body {{ font-family: system-ui, sans-serif; margin: 1rem; }}
		table {{ border-collapse: collapse; }}
		th, td {{ border-bottom: 1px solid #ccc; padding: 0.2rem 0.5rem; text-align: left; vertical-align: top; }}
		td:nth-child(-n+3) {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
	</style>
</head>
<body>
	<h1>{html.escape(title)}</h1>
	<table>
		<thead><tr>{headers}</tr></thead>
		<tbody>
{rows}
		</tbody>
	</table>
	<footer><p>{exported}</p></footer>
</body>
</html>
"""


def in_m3u(lines: list[Line], metadata: Metadata) -> str:
	entries = ["#EXTM3U"]
	for line in reversed(lines):
		if not line.location:
			continue
		duration = -1
		if line.duration is not None:
			duration = round(line.duration.total_seconds())
		entries.append(f"#EXTINF:{duration},{(artist_and_title(line)) or (line.location)}")
		entries.append(_("# public text: {public_text}").format(public_text=public_text(line, metadata)))
		entries.append(line.location)
	return "\n".join([*entries, ""])
