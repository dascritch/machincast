"""Document d'audit d'une indexation, en CSV et en HTML (https://github.com/dascritch/machincast/issues/11, spec § 6.3).

Chaque passage de l'indexation, rapide ou complet, en terminal ou dans sa fenêtre, écrit un document d'audit : un
.csv et un .html dans REPERTOIRE, nommés avec l'horodatage du lancement en heure locale, par exemple
/tmp/machincast-audit-2026-10-15T08:15:00.csv. Il ne liste que les anomalies des fichiers, une par ligne : date du
passage, chemin du fichier (jamais l'identifiant du sonore), verdict, problème et conséquence pour le sonore ; puis le
bilan du passage. Sans anomalie, il ne porte que le bilan. Ses chemins sont annoncés sur la sortie standard.

L'heure vient de HORLOGE, que les scénarios fixent. Rien n'est écrit dans la table log. Un document qui ne peut pas
être écrit est signalé, sans arrêter l'indexation.
"""

import csv
import html
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from machincast.clock import Clock, SystemClock
from machincast.i18n import _, current

log = logging.getLogger(__name__)

DIRECTORY = Path("/tmp")
CLOCK: Clock = SystemClock()
COLUMNS = ("date", "chemin", "verdict", _("problem"), _("consequence"))
REPORT = "bilan"
"""Verdict de la dernière ligne du CSV, qui porte le bilan du passage dans la colonne du problème."""


@dataclass(frozen=True)
class Anomaly:
	"""Un fichier défectueux, relevé par la vérification (machincast.indexer.check)."""

	path: str
	verdict: str
	problem: str
	consequence: str


def _date(start: datetime) -> str:
	return f"{start.astimezone():%Y-%m-%d %H:%M:%S}"


def write(anomalies: list[Anomaly], report: str, start: datetime, directory: Path) -> tuple[Path, Path]:
	"""Écrit le .csv et le .html du passage lancé à debut ; un document du même instant est remplacé."""
	name = f"machincast-audit-{start.astimezone():%Y-%m-%dT%H:%M:%S}"
	csv_path, html_path = directory / f"{name}.csv", directory / f"{name}.html"
	date = _date(start)
	with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
		writing = csv.writer(file, delimiter=";", lineterminator="\r\n")
		writing.writerow(COLUMNS)
		for anomaly in anomalies:
			writing.writerow((date, anomaly.path, anomaly.verdict, anomaly.problem, anomaly.consequence))
		writing.writerow((date, "", REPORT, report, ""))
	html_path.write_text(page(anomalies, report, start), encoding="utf-8")
	return csv_path, html_path


def page(anomalies: list[Anomaly], report: str, start: datetime) -> str:
	def cell(text: str) -> str:
		return f"<td>{html.escape(text)}</td>"

	rows = "\n".join(
		"\t\t\t<tr>"
		+ cell(anomaly.path)
		+ cell(anomaly.verdict)
		+ cell(anomaly.problem)
		+ cell(anomaly.consequence)
		+ "</tr>"
		for anomaly in anomalies
	)
	content = _(
		"\t<table>\n\t\t<thead><tr><th>Path</th><th>Verdict</th><th>Problem</th><th>Consequence</th></tr></thead>\n\t\t<tbody>\n{rows}\n\t\t</tbody>\n\t</table>"
	).format(rows=rows)
	if anomalies == []:
		content = _("\t<p>No anomaly.</p>")
	title = _("Indexing audit of {date}").format(date=_date(start))
	return f"""<!DOCTYPE html>
<html lang="{current()}">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>{html.escape(title)}</title>
	<style>
		body {{ font-family: system-ui, sans-serif; margin: 1rem; }}
		table {{ border-collapse: collapse; }}
		th, td {{ border-bottom: 1px solid #ccc; padding: 0.2rem 0.6rem; text-align: left; }}
	</style>
</head>
<body>
	<h1>{html.escape(title)}</h1>
	<p>{html.escape(report)}</p>
{content}
</body>
</html>
"""


def produce(anomalies: list[Anomaly], report: str, start: datetime) -> None:
	"""Écrit le document d'audit du passage dans REPERTOIRE, et annonce ses chemins."""
	try:
		csv_path, html_path = write(anomalies, report, start, DIRECTORY)
	except OSError as error:
		log.warning(
			_("audit document cannot be written in {directory}: {error}").format(directory=DIRECTORY, error=error)
		)
		return
	log.info(_("audit document: {csv_path}, {html_path}").format(csv_path=csv_path, html_path=html_path))
