"""Enregistrement de l'airplay et du log (https://github.com/dascritch/machincast/issues/17, spec § 3.1 et § 5.2).

Le binaire lecture n'écrit que par ce module, et seulement des insertions : ses droits PostgreSQL ne lui
permettent ni de modifier ni de supprimer une ligne d'airplay ou de log, ni de lire le log (pas de RETURNING).

- Airplay : deux lignes par passage, reliées par play_id. Chacune recopie l'emplacement (pour un stream, son
  adresse directe ou celle de son feed), l'artiste et le titre du sonore au moment du passage, et référence
  le sonore, la banque qui l'a fourni (aucune pour un sonore placé directement dans l'événement), l'événement et
  l'élément de sa liste, et, pour un sonore joué par une séquence, la séquence et son élément
  (https://github.com/dascritch/machincast/issues/99). La ligne de fin donne la durée effectivement diffusée et
  l'indicateur without_incident.
- Log : chaque opération, normale (info) ou non (alerte, incident), avec sa nature, un message et ses références.
  Une coupure nette est une opération normale ; une lecture interrompue par une erreur est un incident, que
  l'appelant peut nommer plus précisément (flux tombé d'un stream).

Les alertes et incidents du log sont aussi écrits dans le journal du binaire, sur sa sortie d'erreur
(https://github.com/dascritch/machincast/issues/19).

Les heures viennent de l'horloge du binaire (machincast.horloge), pour que la simulation et les tests soient
reproductibles.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import psycopg
from psycopg.rows import TupleRow

Niveau = Literal["info", "warning", "incident"]
NIVEAUX = {"info": "info", "warning": "alerte", "incident": "incident"}
"""Les niveaux du log à l'écran et dans les messages, par leur valeur en base
(https://github.com/dascritch/machincast/issues/358)."""

journal = logging.getLogger(__name__)


@dataclass(frozen=True)
class Passage:
	id: uuid.UUID
	sonore: int
	banque: int | None
	evenement: int | None
	element: int | None
	debut: datetime
	sequence: int | None = None
	"""Séquence qui a fait jouer le sonore (https://github.com/dascritch/machincast/issues/99)."""
	sequence_element: int | None = None
	"""Élément de cette séquence."""


def consigner(
	connexion: psycopg.Connection[TupleRow],
	niveau: str,
	nature: str,
	message: str,
	instant: datetime | None = None,
	sonore: int | None = None,
	banque: int | None = None,
	evenement: int | None = None,
) -> None:
	"""Ajoute une ligne au log ; sans instant, l'heure du serveur PostgreSQL. Jamais de RETURNING : la lecture
	n'a pas le droit de lire le log."""
	if niveau != "info":
		# Sortie privée stderr (https://github.com/dascritch/machincast/issues/19) : alertes et incidents.
		journal.warning(f"{NIVEAUX.get(niveau, niveau)} : {nature} : {message}")
	with connexion.transaction():
		connexion.execute(
			"INSERT INTO log (logged_at, level, kind, message, sound_id, bank_id, event_id)"
			" VALUES (COALESCE(%s, clock_timestamp()), %s, %s, %s, %s, %s, %s)",
			(instant, niveau, nature, message, sonore, banque, evenement),
		)


def _debut(connexion: psycopg.Connection[TupleRow], passage: Passage) -> None:
	connexion.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, bank_id, event_id, event_item_id,"
		" sequence_id, sequence_item_id, location, artist, title)"
		" SELECT %s, 'start', %s, s.id, %s, %s, %s, %s, %s, COALESCE(s.location, s.stream_url, m.url), s.artist,"
		" s.title FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = %s",
		(
			passage.id,
			passage.debut,
			passage.banque,
			passage.evenement,
			passage.element,
			passage.sequence,
			passage.sequence_element,
			passage.sonore,
		),
	)


def _fin(connexion: psycopg.Connection[TupleRow], passage: Passage, instant: datetime, sans_incident: bool) -> None:
	# La ligne de fin recopie la ligne de début : l'artiste et le titre restent ceux du moment du passage.
	connexion.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, bank_id, event_id, event_item_id,"
		" sequence_id, sequence_item_id, location, artist, title, played_duration, without_incident)"
		" SELECT play_id, 'end', %s, sound_id, bank_id, event_id, event_item_id, sequence_id,"
		" sequence_item_id, location, artist, title, %s, %s FROM airplay"
		" WHERE play_id = %s AND line_type = 'start'",
		(instant, instant - passage.debut, sans_incident, passage.id),
	)


def commencer_passage(
	connexion: psycopg.Connection[TupleRow],
	sonore: int,
	banque: int | None,
	evenement: int | None,
	element: int | None,
	instant: datetime,
	sequence: int | None = None,
	sequence_element: int | None = None,
) -> Passage:
	"""Ligne de début d'un passage ; l'artiste et le titre sont recopiés tels qu'ils sont à cet instant."""
	passage = Passage(uuid.uuid4(), sonore, banque, evenement, element, instant, sequence, sequence_element)
	with connexion.transaction():
		_debut(connexion, passage)
	return passage


def terminer_passage(
	connexion: psycopg.Connection[TupleRow],
	passage: Passage,
	instant: datetime,
	coupe: bool = False,
	erreur: str | None = None,
	nature: str = "lecture interrompue",
) -> None:
	"""Ligne de fin d'un passage, avec la durée diffusée ; une coupure ou une erreur est aussi consignée au log,
	l'erreur en incident de la nature donnée."""
	with connexion.transaction():
		_fin(connexion, passage, instant, erreur is None)
		references = {"sonore": passage.sonore, "banque": passage.banque, "evenement": passage.evenement}
		if erreur is not None:
			consigner(connexion, "incident", nature, erreur, instant, **references)
		elif coupe:
			consigner(connexion, "info", "coupure nette", "début d'un événement", instant, **references)
