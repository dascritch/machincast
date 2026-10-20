"""Airplay récent, pour l'écran par défaut (https://github.com/dascritch/machincast/issues/23, spec § 8.1).

Lu avec le rôle de l'interface, qui lit l'airplay sans pouvoir l'écrire. L'écran ne le relit qu'à chaque changement de
sonore annoncé par la socket d'état, jamais en boucle (doc/regles/interface.md). L'interface est privée : l'artiste et
le titre sont toujours affichés, même masqués.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import TupleRow

FENETRE = timedelta(hours=12)
"""Profondeur de l'airplay affiché."""


@dataclass(frozen=True)
class PassageAffiche:
	debut: datetime
	fin: datetime | None
	"""None pour le passage en cours."""
	duree: timedelta | None
	artiste: str | None
	titre: str | None
	evenement: str | None
	sequence: str | None
	banque: str | None
	sans_incident: bool | None
	sonore_id: int | None = None
	evenement_id: int | None = None
	sequence_id: int | None = None
	banque_id: int | None = None
	"""Les éléments du passage, pour ouvrir leur fiche (https://github.com/dascritch/machincast/issues/144) ; None
	pour un élément supprimé depuis."""


def _texte(valeur: object) -> str | None:
	if valeur is None:
		return None
	return str(valeur)


def _entier(valeur: object) -> int | None:
	if valeur is None:
		return None
	return int(str(valeur))


def lire_airplay(connexion: psycopg.Connection[TupleRow], depuis: datetime) -> list[PassageAffiche]:
	"""Passages commencés depuis cet instant, du plus récent au plus ancien."""
	with connexion.transaction():
		lignes = connexion.execute(
			"SELECT d.horodatage, f.horodatage, f.duree_diffusee, f.sans_incident, d.artiste, d.titre,"
			" e.nom_interne, q.nom_interne, b.nom_interne, d.sonore_id, e.id, q.id, b.id"
			" FROM airplay d"
			" LEFT JOIN airplay f ON f.passage_id = d.passage_id AND f.type_ligne = 'fin'"
			" LEFT JOIN evenements e ON e.id = d.evenement_id"
			" LEFT JOIN sequences q ON q.id = d.sequence_id"
			" LEFT JOIN banques b ON b.id = d.banque_id"
			" WHERE d.type_ligne = 'debut' AND d.horodatage >= %s"
			" ORDER BY d.horodatage DESC, d.id DESC",
			(depuis,),
		).fetchall()
	passages = []
	for ligne in lignes:
		debut, fin, duree, sans_incident, artiste, titre, evenement, sequence, banque, *identifiants = ligne
		if not isinstance(debut, datetime):
			continue
		passages.append(
			PassageAffiche(
				debut=debut,
				fin=fin if isinstance(fin, datetime) else None,
				duree=duree if isinstance(duree, timedelta) else None,
				artiste=_texte(artiste),
				titre=_texte(titre),
				evenement=_texte(evenement),
				sequence=_texte(sequence),
				banque=_texte(banque),
				sans_incident=None if sans_incident is None else bool(sans_incident),
				sonore_id=_entier(identifiants[0]),
				evenement_id=_entier(identifiants[1]),
				sequence_id=_entier(identifiants[2]),
				banque_id=_entier(identifiants[3]),
			)
		)
	return passages
