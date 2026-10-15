"""Grille des événements et choix de l'événement actif (https://github.com/dascritch/machincast/issues/12, spec § 4.1).

À tout instant, l'événement actif est celui de plus haute priorité (spécial > émission > fil musical) dont une
occurrence couvre l'instant, sauf si cette occurrence s'est terminée plus tôt (liste épuisée d'un événement sans
fin). Deux événements de même priorité qui se chevauchent sont départagés par leur date de modification : le
dernier modifié en base l'emporte.

Dates d'un événement (spec § 3.1) : debut et fin sont ceux de sa première occurrence.

- Un fil musical sans debut ni fin est permanent.
- Sans jours de récurrence, l'événement a une seule occurrence, [debut, fin[, ou [debut, ∞[ sans fin.
- Avec des jours de récurrence, il revient chacun de ces jours à partir de sa première occurrence, à la même
  heure que debut, et dure jusqu'à l'heure de fin, autant de jours plus tard que la première occurrence : un
  événement peut passer minuit, et c'est le jour de son début qui compte.
- Sans fin, une occurrence couvre l'instant à partir de son début, jusqu'à ce que sa liste soit épuisée : le
  binaire la déclare alors terminée (Occurrence.cle).

Un événement de secours (https://github.com/dascritch/machincast/issues/16) n'est jamais actif par la grille :
sans date ni jour, sa liste ne joue qu'à la place d'un stream tombé (machincast.lecture.deroule).

Le poste travaille en heure locale, celle de Paris : la grille calcule en heure murale, sans fuseau à manier.
Au changement d'heure, un événement garde donc son heure (spec § 4.1 : aucune règle particulière).
"""

from collections.abc import Iterable, Set
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import psycopg
from psycopg.rows import TupleRow


class Priorite(StrEnum):
	"""Valeurs du type priorite_evenement, de la plus basse à la plus haute."""

	SECOURS = "secours"
	"""Hors grille : remplace un stream tombé, jamais actif à une heure donnée."""
	FIL_MUSICAL = "fil_musical"
	EMISSION = "emission"
	SPECIAL = "special"


RANGS = {priorite: rang for rang, priorite in enumerate(Priorite)}

JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
"""Valeurs du type jour_semaine, dans l'ordre de datetime.weekday()."""


@dataclass(frozen=True)
class Evenement:
	id: int
	nom: str
	priorite: Priorite
	debut: datetime | None
	"""Début de la première occurrence ; None pour un fil musical permanent."""
	fin: datetime | None
	jours: frozenset[int]
	"""Jours de récurrence, 0 pour lundi ; vide si l'événement n'a qu'une occurrence."""
	modifie_le: datetime


@dataclass(frozen=True)
class Occurrence:
	evenement: Evenement
	debut: datetime | None
	"""Début de l'occurrence, en heure murale du poste ; None pour un fil musical permanent."""
	fin: datetime | None
	"""None pour une occurrence sans fin, qui dure jusqu'à l'épuisement de sa liste."""

	@property
	def cle(self) -> tuple[int, datetime | None]:
		"""Identifie l'occurrence, pour la déclarer terminée plus tôt."""
		return self.evenement.id, self.debut


def heure_murale(moment: datetime) -> datetime:
	"""Heure du poste, sans fuseau : la machine travaille en heure locale, celle de Paris."""
	return moment.astimezone().replace(tzinfo=None) if moment.tzinfo is not None else moment


def _couvre(debut: datetime, fin: datetime | None, moment: datetime) -> bool:
	return debut <= moment and (fin is None or moment < fin)


def occurrence(evenement: Evenement, instant: datetime) -> Occurrence | None:
	"""Occurrence de l'événement qui couvre l'instant, ou None. Ses dates sont en heure murale du poste."""
	if evenement.debut is None:
		return Occurrence(evenement, None, None)
	debut = heure_murale(evenement.debut)
	fin = None if evenement.fin is None else heure_murale(evenement.fin)
	moment = heure_murale(instant)
	if not evenement.jours:
		return Occurrence(evenement, debut, fin) if _couvre(debut, fin, moment) else None

	premier_jour = debut.date()
	duree_en_jours = None if fin is None else (fin.date() - premier_jour).days
	# Une occurrence avec fin a commencé au plus tôt autant de jours avant que dure la première ; une occurrence
	# sans fin, dans la semaine qui précède.
	recul = 7 if duree_en_jours is None else duree_en_jours
	for ecart in range(recul + 1):
		jour = moment.date() - timedelta(days=ecart)
		if jour < premier_jour or (jour != premier_jour and jour.weekday() not in evenement.jours):
			continue
		depart = datetime.combine(jour, debut.time())
		arrivee = None
		if fin is not None and duree_en_jours is not None:
			arrivee = datetime.combine(jour + timedelta(days=duree_en_jours), fin.time())
		if _couvre(depart, arrivee, moment):
			return Occurrence(evenement, depart, arrivee)
	return None


def evenement_actif(
	evenements: Iterable[Evenement],
	instant: datetime,
	terminees: Set[tuple[int, datetime | None]] = frozenset(),
) -> Occurrence | None:
	"""Occurrence de l'événement actif à l'instant, ou None si aucun ne le couvre.

	terminees contient les clés (Occurrence.cle) des occurrences terminées plus tôt, liste épuisée.
	"""
	candidates = [
		o
		for e in evenements
		if e.priorite is not Priorite.SECOURS and (o := occurrence(e, instant)) is not None and o.cle not in terminees
	]
	if not candidates:
		return None
	return max(candidates, key=lambda o: (RANGS[o.evenement.priorite], o.evenement.modifie_le, o.evenement.id))


COLONNES = "id, nom_interne, priorite::text, debut, fin, jours_recurrence::text[], modifie_le"


def lire_grille(connexion: psycopg.Connection[TupleRow]) -> list[Evenement]:
	"""Événements de la grille, sans les événements de secours ; la connexion a endossé le rôle de la lecture
	(machincast.base.connecter)."""
	lignes = connexion.execute(f"SELECT {COLONNES} FROM evenements WHERE priorite <> 'secours' ORDER BY id").fetchall()
	return _evenements(lignes)


def lire_evenement(connexion: psycopg.Connection[TupleRow], identifiant: int) -> Evenement | None:
	"""Un événement, quelle que soit sa priorité : par exemple l'événement de secours d'un stream."""
	lignes = connexion.execute(
		f"SELECT {COLONNES} FROM evenements WHERE id = %s",
		(identifiant,),
	).fetchall()
	return next(iter(_evenements(lignes)), None)


def _evenements(lignes: list[TupleRow]) -> list[Evenement]:
	return [
		Evenement(
			id=int(str(identifiant)),
			nom=str(nom),
			priorite=Priorite(str(priorite)),
			debut=debut if isinstance(debut, datetime) else None,
			fin=fin if isinstance(fin, datetime) else None,
			jours=frozenset(JOURS.index(str(jour)) for jour in (jours if isinstance(jours, list) else [])),
			modifie_le=modifie_le if isinstance(modifie_le, datetime) else datetime.min.replace(tzinfo=UTC),
		)
		for identifiant, nom, priorite, debut, fin, jours, modifie_le in lignes
	]
