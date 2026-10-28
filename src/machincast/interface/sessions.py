"""Sessions sautées d'un événement (https://github.com/dascritch/machincast/issues/273), communes au calendrier et à la
fiche d'un événement (https://github.com/dascritch/machincast/issues/295).

Une session sautée se note en base par le jour où elle commence (evenements_sauts). Elle se rétablit tant qu'elle n'a
pas commencé, et qu'aucun événement de même priorité n'a pris sa place (chevauchee). Le jour seul compte : une session
sautée le reste quand l'heure de l'événement change, et la fiche de l'événement l'annonce (prochaine_sautee).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import TupleRow

from machincast.lecture.grille import JAMAIS, Evenement, chevauchement, heure_murale, lire_grille, sessions

Connexion = psycopg.Connection[TupleRow]
UN_JOUR = timedelta(days=1)


@dataclass(frozen=True)
class Session:
	"""Une session d'un événement, en heure murale du poste ; sans fin, elle dure jusqu'au bout de sa liste."""

	evenement: Evenement
	debut: datetime
	fin: datetime | None


def passee(session: Session, maintenant: datetime) -> bool:
	"""Finie ; une session sans fin l'est le lendemain de son début."""
	moment = heure_murale(maintenant)
	if session.fin is None:
		return session.debut.date() < moment.date()
	return session.fin <= moment


def commencee(session: Session, maintenant: datetime) -> bool:
	return session.debut <= heure_murale(maintenant)


def prochaine_sautee(evenement: Evenement, maintenant: datetime) -> Session | None:
	"""La première session sautée de l'événement qui n'est pas encore passée : en cours, ou à venir. Un saut dont le
	jour n'a plus de session, après un changement des jours de l'événement, ne compte pas."""
	for jour in sorted(evenement.sautees):
		for debut, fin in sessions(evenement, jour, jour + UN_JOUR):
			session = Session(evenement, debut, fin)
			if not passee(session, maintenant):
				return session
	return None


def chevauchee(connexion: Connexion, session: Session, maintenant: datetime) -> tuple[Evenement, datetime] | None:
	"""L'événement de même priorité qui a pris la place de la session, et le premier instant commun ; None si elle
	peut revenir. À appeler dans une transaction."""
	seule = Evenement(
		id=session.evenement.id,
		nom=session.evenement.nom,
		priorite=session.evenement.priorite,
		debut=session.debut,
		fin=session.fin,
		jours=frozenset(),
		modifie_le=JAMAIS,
	)
	autres = [autre for autre in lire_grille(connexion) if autre.id != session.evenement.id]
	return chevauchement(seule, autres, depuis=heure_murale(maintenant))


def retablir(connexion: Connexion, session: Session) -> None:
	"""La session joue de nouveau. À appeler dans une transaction."""
	connexion.execute(
		"DELETE FROM evenements_sauts WHERE evenement_id = %s AND jour = %s",
		(session.evenement.id, session.debut.date()),
	)
