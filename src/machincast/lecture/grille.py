"""Grille des événements et choix de l'événement actif (https://github.com/dascritch/machincast/issues/12, spec § 4.1).

À tout instant, l'événement actif est celui de plus haute priorité (spécial > émission > fil musical) dont une
occurrence couvre l'instant, sauf si cette occurrence s'est terminée plus tôt (liste épuisée d'un événement sans
fin). Deux événements de même priorité qui se chevauchent sont départagés par leur date de modification : le
dernier modifié en base l'emporte.

Dates d'un événement (spec § 3.1) : debut et fin sont ceux de sa première occurrence.

- Un fil musical sans debut ni fin est permanent.
- Sans jours de récurrence, l'événement a une seule occurrence, [debut, fin[, ou [debut, ∞[ sans fin.
- Avec des jours de récurrence, il revient chacun de ces jours à partir de sa première occurrence, à la même
  heure murale que debut, et dure jusqu'à l'heure murale de fin, autant de jours plus tard que la première
  occurrence : un événement peut passer minuit. Ce calcul se fait dans le fuseau local, si bien qu'au changement
  d'heure un événement garde son heure murale (spec § 4.1 : aucune règle particulière).
- Sans fin, une occurrence couvre l'instant à partir de son début, jusqu'à ce que sa liste soit épuisée : le
  binaire la déclare alors terminée (Occurrence.cle).

Les comparaisons se font en UTC : deux heures du même fuseau se comparent sinon sur leur heure murale, sans
tenir compte de l'heure répétée au changement d'heure d'automne.
"""

from collections.abc import Iterable, Set
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from enum import StrEnum

import psycopg
from psycopg.rows import TupleRow


class Priorite(StrEnum):
	"""Valeurs du type priorite_evenement, de la plus basse à la plus haute."""

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
	fin: datetime | None
	"""None pour une occurrence sans fin, qui dure jusqu'à l'épuisement de sa liste."""

	@property
	def cle(self) -> tuple[int, datetime | None]:
		"""Identifie l'occurrence, pour la déclarer terminée plus tôt."""
		return self.evenement.id, None if self.debut is None else self.debut.astimezone(UTC)


def _couvre(debut: datetime, fin: datetime | None, instant: datetime) -> bool:
	return debut.astimezone(UTC) <= instant.astimezone(UTC) and (
		fin is None or instant.astimezone(UTC) < fin.astimezone(UTC)
	)


def _a_heure(jour: date, modele: datetime, fuseau: tzinfo) -> datetime:
	"""Le jour donné, à l'heure murale de modele dans le fuseau."""
	return datetime.combine(jour, modele.astimezone(fuseau).time(), tzinfo=fuseau)


def occurrence(evenement: Evenement, instant: datetime, fuseau: tzinfo) -> Occurrence | None:
	"""Occurrence de l'événement qui couvre l'instant, ou None."""
	debut, fin = evenement.debut, evenement.fin
	if debut is None:
		return Occurrence(evenement, None, None)
	if not evenement.jours:
		return Occurrence(evenement, debut, fin) if _couvre(debut, fin, instant) else None

	premier_jour = debut.astimezone(fuseau).date()
	duree_en_jours = None if fin is None else (fin.astimezone(fuseau).date() - premier_jour).days
	aujourd_hui = instant.astimezone(fuseau).date()
	# Une occurrence avec fin a commencé au plus tard ce jour-là, la veille près, pour un éventuel changement
	# d'heure ; une occurrence sans fin a commencé dans la semaine qui précède.
	recul = 7 if duree_en_jours is None else duree_en_jours + 1
	for ecart in range(recul + 1):
		jour = aujourd_hui - timedelta(days=ecart)
		if jour < premier_jour or (jour != premier_jour and jour.weekday() not in evenement.jours):
			continue
		depart = _a_heure(jour, debut, fuseau)
		arrivee = (
			None
			if fin is None or duree_en_jours is None
			else _a_heure(jour + timedelta(days=duree_en_jours), fin, fuseau)
		)
		if _couvre(depart, arrivee, instant):
			return Occurrence(evenement, depart, arrivee)
	return None


def evenement_actif(
	evenements: Iterable[Evenement],
	instant: datetime,
	fuseau: tzinfo,
	terminees: Set[tuple[int, datetime | None]] = frozenset(),
) -> Occurrence | None:
	"""Occurrence de l'événement actif à l'instant, ou None si aucun ne le couvre.

	terminees contient les clés (Occurrence.cle) des occurrences terminées plus tôt, liste épuisée.
	"""
	candidates = [o for e in evenements if (o := occurrence(e, instant, fuseau)) is not None and o.cle not in terminees]
	if not candidates:
		return None
	return max(candidates, key=lambda o: (RANGS[o.evenement.priorite], o.evenement.modifie_le, o.evenement.id))


def lire_grille(connexion: psycopg.Connection[TupleRow]) -> list[Evenement]:
	"""Événements enregistrés en base ; la connexion a endossé le rôle de la lecture (machincast.base.connecter)."""
	lignes = connexion.execute(
		"SELECT id, nom_interne, priorite::text, debut, fin, jours_recurrence::text[], modifie_le"
		" FROM evenements ORDER BY id"
	).fetchall()
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
