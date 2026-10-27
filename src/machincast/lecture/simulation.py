"""Mode simulation de Machin lecture (https://github.com/dascritch/machincast/issues/21, spec § 5.5).

La simulation rejoue la diffusion entre deux instants, avec la même logique que la diffusion réelle
(machincast.lecture.diffusion), pour vérifier une grille avant sa mise à l'antenne :

- aucune écriture en base : toute la simulation se fait dans une seule transaction en lecture seule et en lecture
  répétable (lecture_seule) ; PostgreSQL refuse donc toute écriture, et l'état de départ est figé à son ouverture ;
- l'état de départ (positions dans les listes, cycles aléatoires, compteurs de lectures) est lu dans l'airplay, puis
  tenu en mémoire avec les passages, le log et les expirations simulés (HistoriqueSimule) ;
- aucune sortie sonore : les voies sont simulées (MoteurSimule), et la diffusion avance d'échéance en échéance à
  l'horloge de la simulation (fin d'un sonore, début de son crossfade de fin, début ou fin d'un événement) ;
- un stream n'est pas contacté : on suppose qu'il tient jusqu'à la fin de son événement, ou jusqu'à une coupure ;
- une graine rend le hasard reproductible ;
- seules des sorties .csv, .pls et .html sont produites, pour toute la période, nommées par défaut « simulation »
  suivi des dates de début et de fin (nom_par_defaut), dans le répertoire des sorties de la configuration. L'artiste
  et le titre y sont masqués comme sur la page publique ; l'emplacement de chaque fichier permet de vérifier ce qui
  est joué.
"""

import html
import logging
import uuid
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.configuration import Crossfades, Metadonnees
from machincast.conversion import booleen_ou_rien, entier_ou_rien, texte_ou_rien
from machincast.hasard import creer_hasard
from machincast.horloge import HorlogeFixe
from machincast.lecture.diffusion import Diffusion
from machincast.lecture.enregistrement import Passage
from machincast.lecture.expiration import NATURE as SONORE_EXPIRE
from machincast.lecture.expiration import Expiration, _cause
from machincast.lecture.grille import lire_grille, prochain_changement
from machincast.lecture.historique import EN_BASE, DernierPassage
from machincast.lecture.moteur import EtatVoie, VoieLecture
from machincast.lecture.sorties import COLONNES_CSV, Ligne, ligne_csv, masque, playlist, premier_nom_public

journal = logging.getLogger(__name__)

Connexion = psycopg.Connection[TupleRow]

ATTENTE_EN_SILENCE = timedelta(minutes=1)
"""Pendant un silence, la simulation réessaie à cet intervalle : un sonore peut redevenir jouable."""


class PeriodeInvalide(ValueError):
	"""La fin de la simulation ne suit pas son début."""


def nom_par_defaut(debut: datetime, fin: datetime) -> str:
	"""« simulation » suivi des dates de début et de fin, à la minute, en heure du poste."""
	return f"simulation-{debut.astimezone():%Y-%m-%dT%H%M}-{fin.astimezone():%Y-%m-%dT%H%M}"


@contextmanager
def lecture_seule(connexion: Connexion) -> Iterator[None]:
	"""Une seule transaction, en lecture seule et en lecture répétable, toujours annulée à la fin.

	Les transactions ouvertes à l'intérieur deviennent des points de sauvegarde de celle-ci : PostgreSQL y refuse toute
	écriture (ReadOnlySqlTransaction).
	"""
	with connexion.transaction() as transaction:
		connexion.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
		yield
		raise psycopg.Rollback(transaction)


# ─── Voies simulées ────────────────────────────────────────


class VoieSimulee:
	"""Une voie sans son : sa position suit l'horloge de la simulation."""

	def __init__(self, horloge: HorlogeFixe, duree: timedelta | None) -> None:
		self.horloge = horloge
		self.debut = horloge.maintenant()
		self.duree = duree
		self.etat: EtatVoie = "en cours"
		self.erreur: str | None = None
		self.arret_prevu: timedelta | None = None

	def position(self) -> timedelta:
		ecoule = self.horloge.maintenant() - self.debut
		if self.duree is None:
			return ecoule
		return min(ecoule, self.duree)

	def bloquee(self) -> bool:
		"""Une voie simulée démarre toujours."""
		return False

	def gelee(self) -> bool:
		"""Une voie simulée avance toujours."""
		return False

	def fin_prevue(self) -> datetime | None:
		if self.arret_prevu is not None:
			return self.debut + self.arret_prevu
		return None if self.duree is None else self.debut + self.duree

	def traiter(self) -> None:
		fin = self.fin_prevue()
		if (self.etat == "en cours") and (fin is not None) and (self.horloge.maintenant() >= fin):
			self.etat = "finie"

	def couper(self) -> None:
		if self.etat == "en cours":
			self.etat = "coupée"

	def fermer(self) -> None:
		pass

	def fondu(self, cible: float, duree: timedelta) -> None:
		pass

	def eteindre(self, duree: timedelta) -> None:
		self.arret_prevu = self.position() + max(duree, timedelta(0))
		self.traiter()

	def supprimer_fondu_de_sortie(self) -> None:
		pass

	def volume_a(self, instant: timedelta) -> float:
		return 1.0


class MoteurSimule:
	"""Moteur sans sortie audio : aucune voie GStreamer n'est créée."""

	def __init__(self, horloge: HorlogeFixe) -> None:
		self.horloge = horloge
		self._voies: list[VoieSimulee] = []

	def jouer(
		self,
		chemin: Path | str,
		duree: timedelta | None,
		crossfade_debut: timedelta = timedelta(0),
		crossfade_fin: timedelta = timedelta(0),
		muette: bool = False,
		decalage: timedelta | None = None,
		depart: float = 0.0,
		arrivee: float = 0.0,
	) -> VoieLecture:
		"""La durée d'un sonore rogné est déjà sans ses blancs : le décalage ne change rien à la voie simulée."""
		voie = VoieSimulee(self.horloge, duree)
		self._voies.append(voie)
		return voie

	def traiter_messages(self) -> None:
		for voie in self._voies:
			voie.traiter()
		self._voies = [voie for voie in self._voies if voie.etat == "en cours"]

	def couper(self) -> None:
		for voie in self._voies:
			voie.couper()
		self._voies = []

	def fermer(self) -> None:
		self._voies = []

	def echeances(self) -> list[datetime]:
		"""Fins prévues des voies en cours."""
		return [fin for voie in self._voies if (fin := voie.fin_prevue()) is not None]


# ─── Historique en mémoire ─────────────────────────────────


@dataclass
class PassageSimule:
	passage: Passage
	artiste: str | None
	titre: str | None
	emplacement: str | None
	fin: datetime | None = None
	sans_incident: bool | None = None


@dataclass
class HistoriqueSimule:
	"""L'airplay et le log de la base, lus sans y écrire, plus les passages, le log et les expirations simulés."""

	passages: list[PassageSimule] = field(default_factory=list)
	log: list[tuple[str, str, str]] = field(default_factory=list)
	"""Lignes de log simulées : niveau, nature, message."""
	expires: set[int] = field(default_factory=set)
	"""Sonores expirés pendant la simulation, consignés une seule fois. Ils ne sont déjà plus jouables : leur maximum
	de lectures, compté avec les passages simulés, ou leur fin de période est atteint."""

	def lectures(self, connexion: Connexion, sonores: Collection[int]) -> dict[int, int]:
		comptes = EN_BASE.lectures(connexion, sonores)
		for simule in self.passages:
			if simule.passage.sonore in comptes:
				comptes[simule.passage.sonore] += 1
		return comptes

	def joues_via_banque(self, connexion: Connexion, banque: int) -> list[int]:
		simules = [s.passage.sonore for s in reversed(self.passages) if s.passage.banque == banque]
		return simules + EN_BASE.joues_via_banque(connexion, banque)

	def dernier_element(self, connexion: Connexion, evenement: int, depuis: datetime | None) -> int | None:
		for simule in reversed(self.passages):
			passage = simule.passage
			if (passage.evenement == evenement) and ((depuis is None) or (passage.debut >= depuis)):
				return passage.element
		return EN_BASE.dernier_element(connexion, evenement, depuis)

	def dernier_passage(self, connexion: Connexion) -> DernierPassage | None:
		if self.passages:
			passage = self.passages[-1].passage
			return DernierPassage(
				passage.id, passage.banque, passage.debut, passage.evenement, passage.element, passage.sequence_element
			)
		return EN_BASE.dernier_passage(connexion)

	def commencer_passage(
		self,
		connexion: Connexion,
		sonore: int,
		banque: int | None,
		evenement: int | None,
		element: int | None,
		instant: datetime,
		sequence: int | None = None,
		sequence_element: int | None = None,
	) -> Passage:
		ligne = connexion.execute(
			"SELECT s.artiste, s.titre, COALESCE(s.emplacement, s.url_stream, m.url) FROM sonores s"
			" LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = %s",
			(sonore,),
		).fetchone()
		artiste, titre, emplacement = ligne if ligne is not None else (None, None, None)
		passage = Passage(uuid.uuid4(), sonore, banque, evenement, element, instant, sequence, sequence_element)
		self.passages.append(
			PassageSimule(
				passage,
				texte_ou_rien(artiste),
				texte_ou_rien(titre),
				texte_ou_rien(emplacement),
			)
		)
		return passage

	def terminer_passage(
		self,
		connexion: Connexion,
		passage: Passage,
		instant: datetime,
		coupe: bool = False,
		erreur: str | None = None,
		nature: str = "lecture interrompue",
	) -> None:
		for simule in self.passages:
			if simule.passage.id == passage.id:
				simule.fin, simule.sans_incident = instant, erreur is None
		references = {"sonore": passage.sonore, "banque": passage.banque, "evenement": passage.evenement}
		if erreur is not None:
			self.consigner(connexion, "incident", nature, erreur, instant, **references)
		elif coupe:
			self.consigner(connexion, "info", "coupure nette", "début d'un événement", instant, **references)

	def consigner(
		self,
		connexion: Connexion,
		niveau: str,
		nature: str,
		message: str,
		instant: datetime | None = None,
		sonore: int | None = None,
		banque: int | None = None,
		evenement: int | None = None,
	) -> None:
		if niveau != "info":
			moment = ""
			if instant is not None:
				moment = f"{instant.astimezone():%Y-%m-%d %H:%M:%S} : "
			journal.warning(f"simulation : {moment}{niveau} : {nature} : {message}")
		self.log.append((niveau, nature, message))

	def expirer(self, connexion: Connexion, instant: datetime, sonore: int | None = None) -> list[Expiration]:
		lignes = connexion.execute(
			"SELECT id, max_lectures, fin_diffusion, COALESCE(titre, emplacement, url_stream) FROM sonores"
			" WHERE etat = 'actif' AND (%s::bigint IS NULL OR id = %s::bigint)"
			" AND (fin_diffusion <= %s OR max_lectures IS NOT NULL)",
			(sonore, sonore, instant),
		).fetchall()
		candidats = {int(str(i)): (m, f, n) for i, m, f, n in lignes if int(str(i)) not in self.expires}
		lectures = self.lectures(connexion, list(candidats))
		expirations = []
		for identifiant, (maximum, fin, nom) in candidats.items():
			limite = entier_ou_rien(maximum)
			fin_diffusion = fin if isinstance(fin, datetime) else None
			if ((limite is not None) and (lectures[identifiant] >= limite)) or (
				(fin_diffusion is not None) and (fin_diffusion <= instant)
			):
				expiration = Expiration(identifiant, _cause(limite, lectures[identifiant], fin_diffusion, instant))
				self.expires.add(identifiant)
				self.consigner(connexion, "info", SONORE_EXPIRE, f"{nom} : {expiration.cause}", instant, identifiant)
				expirations.append(expiration)
		return expirations

	def lignes(self, connexion: Connexion) -> list[Ligne]:
		"""Passages simulés, dans l'ordre où ils commencent, avec leur événement, leur banque et le masquage de chaque
		niveau, comme machincast.lecture.sorties.lire_passages pour l'airplay."""
		evenements = {
			identifiant: (nom, nom_public, masque)
			for identifiant, nom, nom_public, masque in connexion.execute(
				"SELECT id, nom_interne, nom_public, masquer_metadonnees FROM evenements WHERE id = ANY(%s)",
				([s.passage.evenement for s in self.passages],),
			).fetchall()
		}
		sequences = {
			identifiant: (nom, nom_public, masque)
			for identifiant, nom, nom_public, masque in connexion.execute(
				"SELECT id, nom_interne, nom_public, masquer_metadonnees FROM sequences WHERE id = ANY(%s)",
				([s.passage.sequence for s in self.passages],),
			).fetchall()
		}
		banques = {
			identifiant: (nom, nom_public, masque)
			for identifiant, nom, nom_public, masque in connexion.execute(
				"SELECT id, nom_interne, nom_public, masquer_metadonnees FROM banques WHERE id = ANY(%s)",
				([s.passage.banque for s in self.passages],),
			).fetchall()
		}
		sonores: dict[object, object] = dict(
			connexion.execute(
				"SELECT id, masquer_metadonnees FROM sonores WHERE id = ANY(%s)",
				([s.passage.sonore for s in self.passages],),
			).fetchall()
		)
		resultat = []
		for simule in sorted(self.passages, key=lambda s: s.passage.debut):
			passage = simule.passage
			evenement = evenements.get(passage.evenement, (None, None, None))
			sequence = sequences.get(passage.sequence, (None, None, None))
			banque = banques.get(passage.banque, (None, None, None))
			resultat.append(
				Ligne(
					debut=passage.debut,
					fin=simule.fin,
					duree=None if simule.fin is None else simule.fin - passage.debut,
					sans_incident=simule.sans_incident,
					artiste=simule.artiste,
					titre=simule.titre,
					emplacement=simule.emplacement,
					evenement=texte_ou_rien(evenement[0]),
					nom_public=premier_nom_public(evenement[1], sequence[1], banque[1]),
					sequence=texte_ou_rien(sequence[0]),
					banque=texte_ou_rien(banque[0]),
					masquages=(
						booleen_ou_rien(evenement[2]),
						booleen_ou_rien(sequence[2]),
						booleen_ou_rien(banque[2]),
						booleen_ou_rien(sonores.get(passage.sonore)),
					),
				)
			)
		return resultat


def masquer(ligne: Ligne, metadonnees: Metadonnees) -> Ligne:
	"""Le passage tel que la page publique le montre : artiste et titre masqués selon les cinq niveaux, remplacés
	par le premier nom public renseigné ou le texte public (machincast.lecture.sorties). L'emplacement reste : il permet
	de vérifier ce qui est joué."""
	if not masque(ligne.masquages, metadonnees.masquer):
		return ligne
	return replace(ligne, artiste=None, titre=(ligne.nom_public) or (metadonnees.texte_public))


# ─── Simulation ────────────────────────────────────────────


@dataclass
class Resultat:
	passages: list[Ligne] = field(default_factory=list)
	log: list[tuple[str, str, str]] = field(default_factory=list)
	"""Log simulé : niveau, nature, message."""
	fichiers: tuple[Path, Path, Path] | None = None
	"""Sorties écrites : .csv, .pls, .html."""


def _prochaine_echeance(
	connexion: Connexion, diffusion: Diffusion, moteur: MoteurSimule, instant: datetime, fin: datetime
) -> datetime:
	"""Le prochain instant où la diffusion peut changer : fin de voie, début de crossfade de fin, grille, silence."""
	candidats = [fin, *moteur.echeances()]
	courant = diffusion.courant
	if (courant is not None) and (not courant.suivant_demande) and (courant.parametres.duree is not None):
		candidats.append(courant.passage.debut + courant.parametres.duree - courant.parametres.crossfade_fin)
	changement = prochain_changement(lire_grille(connexion), instant)
	if changement is not None:
		candidats.append(changement)
	if (courant is None) and (not diffusion.sortants):
		candidats.append(instant + ATTENTE_EN_SILENCE)
	apres = [candidat for candidat in candidats if candidat > instant]
	if not apres:
		return fin
	return min(apres)


def simuler(
	connexion: Connexion,
	repertoire: Path,
	debut: datetime,
	fin: datetime,
	graine: int | None = None,
	nom: str | None = None,
	metadonnees: Metadonnees | None = None,
	crossfades: Crossfades | None = None,
) -> Resultat:
	"""Simule la diffusion de debut à fin, puis écrit les sorties de la simulation dans le répertoire.

	La connexion a endossé le rôle de la lecture (machincast.base.connecter) ; rien n'est écrit en base.
	"""
	if fin <= debut:
		raise PeriodeInvalide("la fin doit suivre le début")
	historique = HistoriqueSimule()
	horloge = HorlogeFixe(debut)
	moteur = MoteurSimule(horloge)
	with lecture_seule(connexion):
		diffusion = Diffusion(
			connexion,
			moteur,
			horloge,
			creer_hasard(graine),
			historique=historique,
			crossfades=(crossfades) or (Crossfades()),
		)
		diffusion.demarrer()
		while horloge.maintenant() < fin:
			instant = horloge.maintenant()
			diffusion.pas()
			if (diffusion.courant is None) and (not diffusion.sortants) and (diffusion.en_attente is not None):
				# Le sonore en attente démarre au même instant, sans laisser de silence.
				diffusion.pas()
			horloge.avancer(_prochaine_echeance(connexion, diffusion, moteur, instant, fin) - instant)
		diffusion.arreter()
		lignes = historique.lignes(connexion)
	masquees = [masquer(ligne, (metadonnees) or (Metadonnees(masquer=False, texte_public=""))) for ligne in lignes]
	fichiers = exporter(masquees, historique.log, repertoire, (nom) or (nom_par_defaut(debut, fin)), debut, fin)
	return Resultat(lignes, historique.log, fichiers)


# ─── Sorties de la simulation ──────────────────────────────


def _heure_de_fin(fin: datetime | None) -> str:
	if fin is None:
		return ""
	return f"{fin.astimezone():%H:%M:%S}"


def page_de_simulation(lignes: list[Ligne], log: list[tuple[str, str, str]], debut: datetime, fin: datetime) -> str:
	periode = f"du {debut.astimezone():%Y-%m-%d %H:%M} au {fin.astimezone():%Y-%m-%d %H:%M}"

	def cellule(texte: str | None) -> str:
		return f"<td>{html.escape((texte) or (''))}</td>"

	rangees = "\n".join(
		"\t\t\t<tr>"
		+ cellule(f"{ligne.debut.astimezone():%Y-%m-%d %H:%M:%S}")
		+ cellule(_heure_de_fin(ligne.fin))
		+ cellule(ligne.artiste)
		+ cellule(ligne.titre)
		+ cellule(ligne.emplacement)
		+ cellule(ligne.evenement)
		+ cellule(ligne.sequence)
		+ cellule(ligne.banque)
		+ "</tr>"
		for ligne in lignes
	)
	anomalies = "\n".join(
		f'\t\t<li class="{html.escape(niveau)}">'
		f"{html.escape(niveau)} : {html.escape(nature)} : {html.escape(message)}</li>"
		for niveau, nature, message in log
		if niveau != "info"
	)
	return f"""<!DOCTYPE html>
<html lang="fr">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>Simulation {html.escape(periode)}</title>
	<style>
		body {{ font-family: system-ui, sans-serif; margin: 1rem; }}
		table {{ border-collapse: collapse; }}
		th, td {{ border-bottom: 1px solid #ccc; padding: 0.2rem 0.6rem; text-align: left; }}
		.incident {{ color: #a00; }}
	</style>
</head>
<body>
	<h1>Simulation {html.escape(periode)}</h1>
	<p>{len(lignes)} passage{"s" if len(lignes) > 1 else ""}. Rien n'a été écrit en base.</p>
	<h2>Alertes et incidents</h2>
	<ul>
{anomalies}
	</ul>
	<h2>Passages</h2>
	<table>
		<thead><tr><th>Début</th><th>Fin</th><th>Artiste</th><th>Titre</th><th>Emplacement</th><th>Événement</th><th>Séquence</th><th>Banque</th></tr></thead>
		<tbody>
{rangees}
		</tbody>
	</table>
</body>
</html>
"""


def exporter(
	lignes: list[Ligne],
	log: list[tuple[str, str, str]],
	repertoire: Path,
	nom: str,
	debut: datetime,
	fin: datetime,
) -> tuple[Path, Path, Path]:
	"""CSV, .pls et .html de la simulation, pour toute la période ; un fichier existant est remplacé."""
	repertoire.mkdir(parents=True, exist_ok=True)
	chemin_csv, chemin_pls, chemin_html = (repertoire / f"{nom}{extension}" for extension in (".csv", ".pls", ".html"))
	with chemin_csv.open("w", encoding="utf-8-sig", newline="") as fichier:
		fichier.write(";".join(COLONNES_CSV) + "\r\n")
		for ligne in lignes:
			fichier.write(ligne_csv(ligne))
	chemin_pls.write_text(playlist(list(reversed(lignes))), encoding="utf-8")
	chemin_html.write_text(page_de_simulation(lignes, log, debut, fin), encoding="utf-8")
	return chemin_csv, chemin_pls, chemin_html
