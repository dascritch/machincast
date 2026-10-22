"""Airplay récent, pour l'écran par défaut (https://github.com/dascritch/machincast/issues/23, spec § 8.1) et l'onglet
Airplay (https://github.com/dascritch/machincast/issues/244).

Lu avec le rôle de l'interface, qui lit l'airplay sans pouvoir l'écrire. L'écran ne le relit qu'à chaque changement de
sonore annoncé par la socket d'état, jamais en boucle (doc/regles/interface.md). L'interface est privée : l'artiste et
le titre sont toujours affichés, même masqués.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import booleen_ou_rien, entier_ou_rien, texte_ou_rien

HEURES = 12
"""Heures de l'airplay que montre l'onglet Airplay, sans réglage du compte."""
DERNIERS = 10
"""Passages de l'airplay que montre l'accueil."""


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


def lire_airplay(
	connexion: psycopg.Connection[TupleRow], depuis: datetime | None = None, nombre: int | None = None
) -> list[PassageAffiche]:
	"""Passages commencés depuis cet instant, ou les derniers, du plus récent au plus ancien ; nombre au plus."""
	with connexion.transaction():
		lignes = connexion.execute(
			"SELECT d.horodatage, f.horodatage, f.duree_diffusee, f.sans_incident, d.artiste, d.titre,"
			" e.nom_interne, q.nom_interne, b.nom_interne, d.sonore_id, e.id, q.id, b.id"
			" FROM airplay d"
			" LEFT JOIN airplay f ON f.passage_id = d.passage_id AND f.type_ligne = 'fin'"
			" LEFT JOIN evenements e ON e.id = d.evenement_id"
			" LEFT JOIN sequences q ON q.id = d.sequence_id"
			" LEFT JOIN banques b ON b.id = d.banque_id"
			" WHERE d.type_ligne = 'debut' AND (%s::timestamptz IS NULL OR d.horodatage >= %s::timestamptz)"
			" ORDER BY d.horodatage DESC, d.id DESC LIMIT %s",
			(depuis, depuis, nombre),
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
				artiste=texte_ou_rien(artiste),
				titre=texte_ou_rien(titre),
				evenement=texte_ou_rien(evenement),
				sequence=texte_ou_rien(sequence),
				banque=texte_ou_rien(banque),
				sans_incident=booleen_ou_rien(sans_incident),
				sonore_id=entier_ou_rien(identifiants[0]),
				evenement_id=entier_ou_rien(identifiants[1]),
				sequence_id=entier_ou_rien(identifiants[2]),
				banque_id=entier_ou_rien(identifiants[3]),
			)
		)
	return passages
