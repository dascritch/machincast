"""Parcours récursif des répertoires des banques (https://github.com/dascritch/machincast/issues/9, spec § 6.2).

Chaque fichier sonore trouvé dans l'un des répertoires d'une banque (table banques_repertoires) est enregistré
dans sonores s'il ne l'est pas encore, à l'état apercu et sans être décodé
(https://github.com/dascritch/machincast/issues/69), puis rattaché à la banque en fin de liste. La vérification
qui suit le décode dans le même passage.

- Formats de la spec : mp3, m4a et aac, ogg, flac, wav, aiff (et .aif), quelle que soit la casse de l'extension.
- Les fichiers et répertoires cachés (nom commençant par un point) sont ignorés : ce sont des fichiers de
  service, comme les « ._*.mp3 » qu'écrit macOS sur un disque partagé.
- Les sous-répertoires sont parcourus dans l'ordre de leur nom, sans suivre les liens symboliques vers d'autres
  répertoires, qui pourraient former une boucle ; un répertoire de banque qui est lui-même un lien est suivi.
- Un fichier déjà indexé n'est jamais dupliqué, même trouvé par plusieurs banques : l'emplacement est unique.
- Un sonore trouvé dans le répertoire d'une banque y est rattaché s'il n'y est pas, même retiré à la main, sauf si sa
  durée est connue et sort des durées de la banque (https://github.com/dascritch/machincast/issues/195).
- Un sonore de durée encore inconnue, trouvé dans le répertoire d'une banque qui a des durées, attend la vérification :
  rattacher_en_attente ne l'y rattache qu'ensuite, s'il est dans ses durées ou que sa durée reste inconnue. Un sonore
  qui sort des durées d'une banque ne passe donc jamais par elle, et rien ne le dit, ni ligne ni compte : seule la
  fiche de la banque signale ses durées (https://github.com/dascritch/machincast/issues/210). Un nouveau sonore est
  annoncé avec la première banque qui le garde, ou seul s'il n'en a aucune.
- Après la vérification, retirer_hors_durees retire de chaque banque les sonores de durée connue qui sortent de ses
  durées, qu'ils viennent de ses répertoires ou qu'ils aient été ajoutés à la main.
- Un répertoire introuvable ou illisible est signalé en anomalie ; les autres banques sont indexées.

Chaque fichier est enregistré dans sa propre transaction, pour qu'une interruption garde le travail fait.
"""

import logging
import os
import threading
from collections.abc import Collection, Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import liste_ou_rien
from machincast.indexation.verification import Bilan, EtatSonore
from machincast.protection import EXTENSIONS_SONORES

journal = logging.getLogger(__name__)

EXTENSIONS = EXTENSIONS_SONORES
"""Extensions des formats de la spec § 6.2, en minuscules (machincast.protection)."""


def _cache(nom: str) -> bool:
	return nom.startswith(".")


HORS_DUREES = (
	"s.duree IS NOT NULL AND ((b.duree_min IS NOT NULL AND s.duree < b.duree_min)"
	" OR (b.duree_max IS NOT NULL AND s.duree > b.duree_max))"
)
"""Condition SQL : le sonore s, de durée connue, sort des durées de la banque b, bornes comprises dans les durées
(https://github.com/dascritch/machincast/issues/147, https://github.com/dascritch/machincast/issues/195)."""


def fichiers_sonores(repertoire: Path) -> Iterator[Path]:
	"""Fichiers sonores du répertoire et de ses sous-répertoires, dans l'ordre de leur chemin."""

	def signaler(erreur: OSError) -> None:
		journal.warning(f"{erreur.filename} : répertoire illisible ({erreur.strerror}) ; ignoré")

	for courant, sous_repertoires, fichiers in os.walk(repertoire, onerror=signaler):
		# Trié en place : os.walk descend ensuite dans cet ordre, et saute les répertoires cachés retirés.
		sous_repertoires[:] = sorted(nom for nom in sous_repertoires if not _cache(nom))
		for nom in sorted(fichiers):
			chemin = Path(courant) / nom
			if (not _cache(nom)) and (chemin.suffix.lower() in EXTENSIONS) and (chemin.is_file()):
				yield chemin


@dataclass(frozen=True)
class Attente:
	"""Un sonore de durée encore inconnue, trouvé dans le répertoire d'une banque qui a des durées."""

	banque: int
	nom: str
	sonore: int
	emplacement: str


@dataclass
class Parcours:
	"""Ce que le parcours laisse à rattacher_en_attente, une fois les sonores vérifiés."""

	attentes: list[Attente] = field(default_factory=list)
	inannonces: dict[int, str] = field(default_factory=dict)
	"""Les nouveaux sonores qu'aucune banque n'a encore gardés, avec leur emplacement."""


def _rattacher(connexion: psycopg.Connection[TupleRow], banque: int, sonore: int) -> bool:
	"""Rattache le sonore à la fin de la banque, s'il n'y est pas et qu'il ne sort pas de ses durées."""
	return (
		connexion.execute(
			"INSERT INTO banques_sonores (banque_id, sonore_id, position)"
			" SELECT %s, %s, (SELECT COALESCE(MAX(position), 0) + 1 FROM banques_sonores WHERE banque_id = %s)"
			f" WHERE NOT EXISTS (SELECT 1 FROM sonores s, banques b WHERE s.id = %s AND b.id = %s AND {HORS_DUREES})"
			" ON CONFLICT (banque_id, sonore_id) DO NOTHING",
			(banque, sonore, banque, sonore, banque),
		).rowcount
		> 0
	)


def _annoncer(bilan: Bilan, parcours: Parcours, sonore: int, nom: str, emplacement: str) -> None:
	"""Une ligne par rattachement ; la première banque d'un nouveau sonore l'annonce avec lui, sans compter de
	rattachement."""
	if parcours.inannonces.pop(sonore, None) is not None:
		journal.info(f"{emplacement} : nouveau sonore, ajouté à la banque {nom}")
		return
	bilan.rattaches += 1
	journal.info(f"{emplacement} : rattaché à la banque {nom}")


def _enregistrer(
	connexion: psycopg.Connection[TupleRow], banque: int, nom: str, emplacement: str, bilan: Bilan, parcours: Parcours
) -> None:
	"""Enregistre le fichier comme nouveau sonore s'il ne l'est pas, et le rattache à la banque, ou le met en attente
	de sa vérification ; une ligne dit chaque rattachement."""
	with connexion.transaction():
		ligne = connexion.execute(
			"SELECT s.id, s.duree IS NULL AND (b.duree_min IS NOT NULL OR b.duree_max IS NOT NULL)"
			" FROM sonores s, banques b WHERE s.emplacement = %s AND b.id = %s",
			(emplacement, banque),
		).fetchone()
		if ligne is None:
			ligne = connexion.execute(
				"INSERT INTO sonores (type, emplacement, etat, indexe_le)"
				" VALUES ('fichier', %s, %s, clock_timestamp())"
				" RETURNING id, EXISTS (SELECT 1 FROM banques WHERE id = %s"
				" AND (duree_min IS NOT NULL OR duree_max IS NOT NULL))",
				(emplacement, EtatSonore.APERCU.value, banque),
			).fetchone()
			assert ligne is not None
			bilan.nouveaux += 1
			parcours.inannonces[int(str(ligne[0]))] = emplacement
		sonore, en_attente = int(str(ligne[0])), ligne[1] is True
		# Un sonore de durée connue, hors des durées de la banque, n'y est pas rattaché ; un sonore de durée encore
		# inconnue attend sa vérification, si la banque a des durées
		# (https://github.com/dascritch/machincast/issues/195, https://github.com/dascritch/machincast/issues/210).
		rattache = False
		if en_attente:
			parcours.attentes.append(Attente(banque, nom, sonore, emplacement))
		else:
			rattache = _rattacher(connexion, banque, sonore)
	if rattache:
		_annoncer(bilan, parcours, sonore, nom, emplacement)


def rattacher_en_attente(connexion: psycopg.Connection[TupleRow], bilan: Bilan, parcours: Parcours) -> None:
	"""Après la vérification, rattache les sonores en attente aux banques dont ils sont dans les durées, ou dont leur
	durée reste inconnue ; annonce les nouveaux sonores qu'aucune banque n'a gardés. Un sonore hors des durées d'une
	banque n'y entre pas, sans ligne ni compte (https://github.com/dascritch/machincast/issues/210)."""
	for attente in parcours.attentes:
		with connexion.transaction():
			rattache = _rattacher(connexion, attente.banque, attente.sonore)
		if rattache:
			_annoncer(bilan, parcours, attente.sonore, attente.nom, attente.emplacement)
	for emplacement in parcours.inannonces.values():
		journal.info(f"{emplacement} : nouveau sonore")


def indexer_repertoires(
	connexion: psycopg.Connection[TupleRow], bilan: Bilan, arret: threading.Event | None = None
) -> Parcours:
	"""Enregistre et rattache à leurs banques les fichiers sonores de leurs répertoires ; complète le bilan. Renvoie les
	rattachements qui attendent la vérification, pour rattacher_en_attente.

	arret : une fois posé, le parcours s'arrête avant le fichier suivant.

	La connexion doit avoir endossé le rôle de l'indexation (machincast.base.connecter).
	"""
	parcours = Parcours()
	with connexion.transaction():
		repertoires = connexion.execute(
			"SELECT b.id, b.nom_interne, r.repertoire FROM banques_repertoires r JOIN banques b ON b.id = r.banque_id"
			" ORDER BY b.id, r.repertoire"
		).fetchall()
	for banque, nom, repertoire in repertoires:
		chemin = Path(os.path.normpath(str(repertoire)))
		if not chemin.is_absolute():
			journal.warning(f"{repertoire} : répertoire relatif, ignoré pour la banque {nom}")
			continue
		if not chemin.is_dir():
			journal.warning(f"{chemin} : répertoire introuvable, ignoré pour la banque {nom}")
			continue
		for fichier in fichiers_sonores(chemin):
			if (arret is not None) and (arret.is_set()):
				return parcours
			_enregistrer(connexion, int(str(banque)), str(nom), str(fichier), bilan, parcours)
	return parcours


def retirer_hors_durees(
	connexion: psycopg.Connection[TupleRow], bilan: Bilan, identifiants: Collection[int] | None = None
) -> None:
	"""Retire de chaque banque les sonores dont la durée en base est connue et sort de ses durées ; complète le bilan
	(https://github.com/dascritch/machincast/issues/195).

	Seule la ligne de banques_sonores disparaît : le sonore reste en base, dans ses autres banques, séquences et
	événements, et son fichier n'est jamais touché. La durée comparée est la durée complète, même saisie à la main.
	identifiants : seuls ces sonores ; tous sans eux. Chaque retrait a sa ligne, désignée par le chemin du fichier.
	"""
	with connexion.transaction():
		hors = connexion.execute(
			"SELECT bs.banque_id, bs.sonore_id, b.nom_interne, s.emplacement, s.duree, b.duree_min, b.duree_max"
			" FROM banques_sonores bs JOIN banques b ON b.id = bs.banque_id JOIN sonores s ON s.id = bs.sonore_id"
			f" WHERE (%s::bigint[] IS NULL OR s.id = ANY(%s)) AND {HORS_DUREES} ORDER BY b.id, bs.position",
			(liste_ou_rien(identifiants), liste_ou_rien(identifiants)),
		).fetchall()
		for banque, sonore, nom, emplacement, duree, minimum, maximum in hors:
			connexion.execute("DELETE FROM banques_sonores WHERE banque_id = %s AND sonore_id = %s", (banque, sonore))
			bilan.retraits += 1
			journal.info(f"{emplacement} : retiré de la banque {nom}, {_hors_durees(duree, minimum, maximum)}")


def _duree(valeur: object) -> str:
	"""« 3:34 », ou « 1:02:05 » au-delà d'une heure, à la seconde la plus proche : un fichier d'une seconde décodé en
	0,998 seconde dure « 0:01 »."""
	assert isinstance(valeur, timedelta), valeur
	heures, reste = divmod(round(valeur.total_seconds()), 3600)
	minutes, secondes = divmod(reste, 60)
	if heures > 0:
		return f"{heures}:{minutes:02d}:{secondes:02d}"
	return f"{minutes}:{secondes:02d}"


def _hors_durees(duree: object, minimum: object, maximum: object) -> str:
	"""« durée 0:30 plus courte que son minimum, 1:00 », ou « … plus longue que son maximum, 2:00 »."""
	if (isinstance(minimum, timedelta)) and (isinstance(duree, timedelta)) and (duree < minimum):
		return f"durée {_duree(duree)} plus courte que son minimum, {_duree(minimum)}"
	return f"durée {_duree(duree)} plus longue que son maximum, {_duree(maximum)}"
