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

from machincast.horloge import Horloge, HorlogeSysteme

journal = logging.getLogger(__name__)

REPERTOIRE = Path("/tmp")
HORLOGE: Horloge = HorlogeSysteme()
COLONNES = ("date", "chemin", "verdict", "problème", "conséquence")
BILAN = "bilan"
"""Verdict de la dernière ligne du CSV, qui porte le bilan du passage dans la colonne du problème."""


@dataclass(frozen=True)
class Anomalie:
	"""Un fichier défectueux, relevé par la vérification (machincast.indexation.verification)."""

	chemin: str
	verdict: str
	probleme: str
	consequence: str


def _date(debut: datetime) -> str:
	return f"{debut.astimezone():%Y-%m-%d %H:%M:%S}"


def ecrire(anomalies: list[Anomalie], bilan: str, debut: datetime, repertoire: Path) -> tuple[Path, Path]:
	"""Écrit le .csv et le .html du passage lancé à debut ; un document du même instant est remplacé."""
	nom = f"machincast-audit-{debut.astimezone():%Y-%m-%dT%H:%M:%S}"
	chemin_csv, chemin_html = repertoire / f"{nom}.csv", repertoire / f"{nom}.html"
	date = _date(debut)
	with chemin_csv.open("w", encoding="utf-8-sig", newline="") as fichier:
		ecriture = csv.writer(fichier, delimiter=";", lineterminator="\r\n")
		ecriture.writerow(COLONNES)
		for anomalie in anomalies:
			ecriture.writerow((date, anomalie.chemin, anomalie.verdict, anomalie.probleme, anomalie.consequence))
		ecriture.writerow((date, "", BILAN, bilan, ""))
	chemin_html.write_text(page(anomalies, bilan, debut), encoding="utf-8")
	return chemin_csv, chemin_html


def page(anomalies: list[Anomalie], bilan: str, debut: datetime) -> str:
	def cellule(texte: str) -> str:
		return f"<td>{html.escape(texte)}</td>"

	rangees = "\n".join(
		"\t\t\t<tr>"
		+ cellule(anomalie.chemin)
		+ cellule(anomalie.verdict)
		+ cellule(anomalie.probleme)
		+ cellule(anomalie.consequence)
		+ "</tr>"
		for anomalie in anomalies
	)
	contenu = f"""	<table>
		<thead><tr><th>Chemin</th><th>Verdict</th><th>Problème</th><th>Conséquence</th></tr></thead>
		<tbody>
{rangees}
		</tbody>
	</table>"""
	if anomalies == []:
		contenu = "	<p>Aucune anomalie.</p>"
	titre = f"Audit de l'indexation du {_date(debut)}"
	return f"""<!DOCTYPE html>
<html lang="fr">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>{html.escape(titre)}</title>
	<style>
		body {{ font-family: system-ui, sans-serif; margin: 1rem; }}
		table {{ border-collapse: collapse; }}
		th, td {{ border-bottom: 1px solid #ccc; padding: 0.2rem 0.6rem; text-align: left; }}
	</style>
</head>
<body>
	<h1>{html.escape(titre)}</h1>
	<p>{html.escape(bilan)}</p>
{contenu}
</body>
</html>
"""


def produire(anomalies: list[Anomalie], bilan: str, debut: datetime) -> None:
	"""Écrit le document d'audit du passage dans REPERTOIRE, et annonce ses chemins."""
	try:
		chemin_csv, chemin_html = ecrire(anomalies, bilan, debut, REPERTOIRE)
	except OSError as erreur:
		journal.warning(f"document d'audit impossible à écrire dans {REPERTOIRE} : {erreur}")
		return
	journal.info(f"document d'audit : {chemin_csv}, {chemin_html}")
