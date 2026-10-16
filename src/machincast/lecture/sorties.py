"""Masquage des métadonnées et modules de sortie (https://github.com/dascritch/machincast/issues/19, spec § 4.8, § 5.3).

Sorties privées, qui disent tout :

- journal du binaire : chaque passage qui commence, en information sur la sortie standard ; les alertes et incidents
  du log vont sur la sortie d'erreur (machincast.lecture.enregistrement.consigner) ;
- CSV : un fichier par jour, nommé avec la date du jour (sorties.csv « airplay.csv » donne « airplay-2026-10-15.csv »),
  une ligne par passage terminé, séparateur « ; », UTF-8 avec BOM ; jamais réécrit ;
- .pls : les PLAYLIST derniers fichiers joués, streams compris, du plus ancien au plus récent ; réécrit à chaque
  passage.

Sortie publique, avec le masquage :

- HTML : page statique, réécrite à chaque passage, qui montre le sonore à l'antenne puis les PRECEDENTS précédents,
  sans JavaScript, rafraîchie toutes les RAFRAICHISSEMENT secondes. L'emplacement d'un fichier n'y paraît jamais.

Masquage : la valeur retenue est celle du premier niveau renseigné, événement, séquence, banque, sonore, puis la
configuration (metadonnees.masquer). Masqués, l'artiste et le titre laissent la place au premier nom public renseigné,
celui de l'événement, de la séquence puis de la banque (https://github.com/dascritch/machincast/issues/99), sinon au
texte public de la configuration. Les indicateurs sont lus en base au moment d'écrire la page.

Une sortie qui ne peut pas être écrite est signalée une fois dans le log (alerte « sortie inaccessible »), sans arrêter
la diffusion ; elle est de nouveau signalée si elle redevient inaccessible après avoir été écrite.
"""

import csv
import functools
import html
import io
import logging
import os
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.configuration import Configuration, Metadonnees
from machincast.configuration import Sorties as Chemins
from machincast.lecture.enregistrement import Passage, consigner
from machincast.protection import verifier_ecriture

journal = logging.getLogger(__name__)

PRECEDENTS = 20
"""Passages précédents montrés par la page publique, sous le sonore à l'antenne."""
PLAYLIST = 100
"""Fichiers de la playlist .pls."""
RAFRAICHISSEMENT = 30
"""Délai de rafraîchissement de la page publique, en secondes."""
COLONNES_CSV = (
	"debut",
	"fin",
	"duree",
	"artiste",
	"titre",
	"emplacement",
	"evenement",
	"sequence",
	"banque",
	"sans_incident",
)
SORTIE_INACCESSIBLE = "sortie inaccessible"


@dataclass(frozen=True)
class Ligne:
	"""Un passage de l'airplay, avec ce qu'il faut pour l'écrire sur chaque sortie."""

	debut: datetime
	fin: datetime | None
	duree: timedelta | None
	sans_incident: bool | None
	artiste: str | None
	titre: str | None
	emplacement: str | None
	evenement: str | None
	nom_public: str | None
	"""Premier nom public renseigné : celui de l'événement, de la séquence, puis de la banque
	(https://github.com/dascritch/machincast/issues/99)."""
	sequence: str | None
	banque: str | None
	masquages: tuple[bool | None, bool | None, bool | None, bool | None]
	"""Masquage de l'événement, de la séquence, de la banque et du sonore ; None : non renseigné."""


def masque(masquages: tuple[bool | None, ...], defaut: bool) -> bool:
	"""Premier niveau renseigné, dans l'ordre événement, séquence, banque, sonore ; sinon la valeur de la
	configuration."""
	return next((valeur for valeur in masquages if valeur is not None), defaut)


def premier_nom_public(*noms: object) -> str | None:
	"""Premier nom public renseigné, dans l'ordre donné : événement, séquence, banque."""
	return next((str(nom) for nom in noms if nom), None)


def artiste_et_titre(ligne: Ligne) -> str:
	return " – ".join(partie for partie in (ligne.artiste, ligne.titre) if partie)


def texte_public(ligne: Ligne, metadonnees: Metadonnees) -> str:
	"""Ce que la sortie publique affiche du passage : l'artiste et le titre, sauf s'ils sont masqués."""
	if not masque(ligne.masquages, metadonnees.masquer):
		visible = artiste_et_titre(ligne)
		if visible:
			return visible
	return ligne.nom_public or metadonnees.texte_public


def chemin_du_csv(modele: Path, jour: datetime) -> Path:
	"""CSV du jour : la date au format ISO 8601 entre le nom et l'extension du chemin de la configuration."""
	return modele.with_name(f"{modele.stem}-{jour:%Y-%m-%d}{modele.suffix}")


def _duree(duree: timedelta | None) -> str:
	if duree is None:
		return ""
	secondes = round(duree.total_seconds())
	return f"{secondes // 3600:02d}:{secondes % 3600 // 60:02d}:{secondes % 60:02d}"


def _heure(instant: datetime | None) -> str:
	return "" if instant is None else f"{instant.astimezone():%Y-%m-%d %H:%M:%S}"


def lire_passages(
	connexion: psycopg.Connection[TupleRow], nombre: int, passage: uuid.UUID | None = None
) -> list[Ligne]:
	"""Les derniers passages, du plus récent au plus ancien, ou un seul ; la connexion a le rôle de la lecture."""
	with connexion.transaction():
		lignes = connexion.execute(
			"SELECT d.horodatage, f.horodatage, f.duree_diffusee, f.sans_incident, d.artiste, d.titre, d.emplacement,"
			" e.nom_interne, e.nom_public, q.nom_public, b.nom_public, q.nom_interne, b.nom_interne,"
			" e.masquer_metadonnees, q.masquer_metadonnees, b.masquer_metadonnees, s.masquer_metadonnees"
			" FROM airplay d"
			" LEFT JOIN airplay f ON f.passage_id = d.passage_id AND f.type_ligne = 'fin'"
			" LEFT JOIN evenements e ON e.id = d.evenement_id"
			" LEFT JOIN sequences q ON q.id = d.sequence_id"
			" LEFT JOIN banques b ON b.id = d.banque_id"
			" LEFT JOIN sonores s ON s.id = d.sonore_id"
			" WHERE d.type_ligne = 'debut' AND (%s::uuid IS NULL OR d.passage_id = %s::uuid)"
			" ORDER BY d.horodatage DESC, d.id DESC LIMIT %s",
			(passage, passage, nombre),
		).fetchall()
	return [
		Ligne(
			debut=debut,
			fin=fin if isinstance(fin, datetime) else None,
			duree=duree if isinstance(duree, timedelta) else None,
			sans_incident=None if sans_incident is None else bool(sans_incident),
			artiste=None if artiste is None else str(artiste),
			titre=None if titre is None else str(titre),
			emplacement=None if emplacement is None else str(emplacement),
			evenement=None if evenement is None else str(evenement),
			nom_public=premier_nom_public(nom_public_e, nom_public_q, nom_public_b),
			sequence=None if sequence is None else str(sequence),
			banque=None if banque is None else str(banque),
			masquages=(_booleen(masque_e), _booleen(masque_q), _booleen(masque_b), _booleen(masque_s)),
		)
		for (
			debut,
			fin,
			duree,
			sans_incident,
			artiste,
			titre,
			emplacement,
			evenement,
			nom_public_e,
			nom_public_q,
			nom_public_b,
			sequence,
			banque,
			masque_e,
			masque_q,
			masque_b,
			masque_s,
		) in lignes
	]


def _booleen(valeur: object) -> bool | None:
	return None if valeur is None else bool(valeur)


def page_publique(lignes: list[Ligne], metadonnees: Metadonnees, instant: datetime) -> str:
	"""Page HTML publique : le sonore à l'antenne, puis les précédents, masquage appliqué."""
	en_cours = lignes[0] if lignes and lignes[0].fin is None else None
	precedents = lignes[1:] if en_cours is not None else lignes
	nom = html.escape(metadonnees.texte_public)

	def element(ligne: Ligne) -> str:
		texte = html.escape(texte_public(ligne, metadonnees))
		return f'<li><time datetime="{ligne.debut.isoformat()}">{ligne.debut.astimezone():%H:%M}</time> {texte}</li>'

	antenne = (
		f'<time datetime="{en_cours.debut.isoformat()}">{en_cours.debut.astimezone():%H:%M}</time> '
		f"{html.escape(texte_public(en_cours, metadonnees))}"
		if en_cours is not None
		else nom
	)
	elements = "\n".join(f"\t\t\t{element(ligne)}" for ligne in precedents[:PRECEDENTS])
	return f"""<!DOCTYPE html>
<html lang="fr">
<head>
	<meta charset="utf-8">
	<meta http-equiv="refresh" content="{RAFRAICHISSEMENT}">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>{nom} : à l'antenne</title>
	<style>
		body {{ font-family: system-ui, sans-serif; margin: 1rem auto; max-width: 40rem; padding: 0 1rem; }}
		.en-cours p {{ font-size: 1.4rem; }}
		ol {{ list-style: none; padding: 0; }}
		time {{ font-variant-numeric: tabular-nums; margin-right: 0.5rem; opacity: 0.7; }}
	</style>
</head>
<body>
	<h1>{nom}</h1>
	<section class="en-cours">
		<h2>À l'antenne</h2>
		<p>{antenne}</p>
	</section>
	<section>
		<h2>Précédemment</h2>
		<ol class="precedents">
{elements}
		</ol>
	</section>
	<footer><p>Mis à jour à <time datetime="{instant.isoformat()}">{instant.astimezone():%H:%M:%S}</time></p></footer>
</body>
</html>
"""


def playlist(lignes: list[Ligne]) -> str:
	"""Playlist .pls : du plus ancien au plus récent, sans masquage."""
	jouees = [ligne for ligne in reversed(lignes) if ligne.emplacement]
	entrees = []
	for numero, ligne in enumerate(jouees, start=1):
		duree = -1 if ligne.duree is None else round(ligne.duree.total_seconds())
		entrees.append(f"File{numero}={ligne.emplacement}")
		entrees.append(f"Title{numero}={artiste_et_titre(ligne) or ligne.emplacement}")
		entrees.append(f"Length{numero}={duree}")
	return "\n".join(["[playlist]", *entrees, f"NumberOfEntries={len(jouees)}", "Version=2", ""])


def ligne_csv(ligne: Ligne) -> str:
	tampon = io.StringIO()
	sans_incident = "" if ligne.sans_incident is None else ("oui" if ligne.sans_incident else "non")
	csv.writer(tampon, delimiter=";", lineterminator="\r\n").writerow(
		[
			_heure(ligne.debut),
			_heure(ligne.fin),
			_duree(ligne.duree),
			ligne.artiste or "",
			ligne.titre or "",
			ligne.emplacement or "",
			ligne.evenement or "",
			ligne.sequence or "",
			ligne.banque or "",
			sans_incident,
		]
	)
	return tampon.getvalue()


def _ecrire(chemin: Path, contenu: str) -> None:
	"""Remplace le fichier d'un coup : un lecteur ne voit jamais de page à moitié écrite."""
	verifier_ecriture(chemin)
	chemin.parent.mkdir(parents=True, exist_ok=True)
	descripteur, temporaire = tempfile.mkstemp(dir=chemin.parent, prefix=f".{chemin.name}.")
	try:
		with os.fdopen(descripteur, "w", encoding="utf-8") as fichier:
			fichier.write(contenu)
		os.chmod(temporaire, 0o644)
		os.replace(temporaire, chemin)  # fichier de MachinCast : sortie, jamais un fichier sonore (verifier_ecriture)
	except BaseException:
		Path(temporaire).unlink(missing_ok=True)  # fichier de MachinCast : fichier temporaire de la sortie
		raise


@dataclass
class Sorties:
	"""Modules de sortie du binaire lecture."""

	chemins: Chemins
	metadonnees: Metadonnees
	_inaccessibles: set[Path] = field(default_factory=set, init=False, repr=False)

	@classmethod
	def depuis(cls, configuration: Configuration) -> "Sorties":
		return cls(configuration.sorties, configuration.metadonnees)

	def passage_commence(self, connexion: psycopg.Connection[TupleRow], passage: Passage) -> None:
		"""Annonce le passage dans le journal du binaire, puis met à jour la page publique et la playlist."""
		for ligne in lire_passages(connexion, 1, passage.id):
			lieu = f" ({ligne.evenement})" if ligne.evenement else ""
			journal.info(f"à l'antenne : {artiste_et_titre(ligne) or ligne.emplacement}{lieu}")
		self.mettre_a_jour(connexion, passage.debut)

	def passage_termine(self, connexion: psycopg.Connection[TupleRow], passage: Passage, instant: datetime) -> None:
		"""Ajoute le passage au CSV de son jour, puis met à jour la page publique et la playlist."""
		for ligne in lire_passages(connexion, 1, passage.id):
			chemin = chemin_du_csv(self.chemins.csv, ligne.debut.astimezone())
			self._sortie(connexion, chemin, instant, functools.partial(self._ajouter, chemin, ligne))
		self.mettre_a_jour(connexion, instant)

	def mettre_a_jour(self, connexion: psycopg.Connection[TupleRow], instant: datetime) -> None:
		"""Réécrit la page publique et la playlist depuis l'airplay."""
		lignes = lire_passages(connexion, max(PRECEDENTS + 1, PLAYLIST))
		page = page_publique(lignes[: PRECEDENTS + 1], self.metadonnees, instant)
		liste = playlist(lignes[:PLAYLIST])
		self._sortie(connexion, self.chemins.html, instant, lambda: _ecrire(self.chemins.html, page))
		self._sortie(connexion, self.chemins.pls, instant, lambda: _ecrire(self.chemins.pls, liste))

	@staticmethod
	def _ajouter(chemin: Path, ligne: Ligne) -> None:
		verifier_ecriture(chemin)
		chemin.parent.mkdir(parents=True, exist_ok=True)
		nouveau = not chemin.exists()
		with chemin.open("a", encoding="utf-8-sig" if nouveau else "utf-8", newline="") as fichier:
			if nouveau:
				fichier.write(";".join(COLONNES_CSV) + "\r\n")
			fichier.write(ligne_csv(ligne))

	def _sortie(
		self, connexion: psycopg.Connection[TupleRow], chemin: Path, instant: datetime, ecrire: Callable[[], None]
	) -> None:
		try:
			ecrire()
		except OSError as erreur:
			if chemin not in self._inaccessibles:
				self._inaccessibles.add(chemin)
				consigner(connexion, "alerte", SORTIE_INACCESSIBLE, f"{chemin} : {erreur}", instant)
		else:
			self._inaccessibles.discard(chemin)
