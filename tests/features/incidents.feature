# language: fr
Fonctionnalité: Écran des incidents
	En tant que technicien d'antenne,
	je veux que les incidents du log s'affichent en table avec des liens vers les éléments concernés,
	afin de diagnostiquer rapidement un problème d'antenne.

	https://github.com/dascritch/machincast/issues/35, spec § 8.6. L'onglet « Incidents » montre les alertes et les
	incidents que Machin lecture a notés dans le log, du plus récent au plus ancien ; les informations, sur demande.
	Un double-clic sur le sonore, la banque ou l'événement d'une entrée ouvre sa fiche. Les heures sont celles du poste.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 21:00:00 »
		Et les sonores :
			| artiste     | titre | type    | etat  | duree | emplacement         |
			| Les Gaufres | Spot  | fichier | actif | 30    | /srv/pubs/spot.flac |
		Et la banque « Publicité », aléatoire, sans nom public, avec « Spot »
		Et les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Et le log :
			| horodatage          | niveau   | nature              | message                           | sonore | banque    | evenement |
			| 2026-10-19 20:10:00 | info     | démarrage           | Machin lecture démarre            |        |           |           |
			| 2026-10-19 20:20:00 | alerte   | fichier modifié     | taille changée depuis l'indexation | Spot   | Publicité | Continue  |
			| 2026-10-19 20:30:00 | incident | fichier introuvable | /srv/pubs/spot.flac               | Spot   |           | Continue  |
			| 2026-10-19 20:40:00 | alerte   | silence             | rien à diffuser                   |        |           | Continue  |

	Scénario: Les alertes et les incidents, du plus récent au plus ancien, avec ce qu'ils concernent
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Incidents »
		Alors la liste des incidents montre :
			| Horaire             | Niveau   | Nature              | Message                            | Sonore             | Banque    | Événement |
			| 2026-10-19 20:40:00 | alerte   | silence             | rien à diffuser                    |                    |           | Continue  |
			| 2026-10-19 20:30:00 | incident | fichier introuvable | /srv/pubs/spot.flac                | Les Gaufres – Spot |           | Continue  |
			| 2026-10-19 20:20:00 | alerte   | fichier modifié     | taille changée depuis l'indexation | Les Gaufres – Spot | Publicité | Continue  |
		Et le compte des incidents est « 3 entrées »

	Scénario: Les informations se montrent sur demande
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Incidents »
		Et je coche « Montrer aussi les informations »
		Alors la liste des incidents montre les natures « silence », « fichier introuvable », « fichier modifié », « démarrage »
		Et le compte des incidents est « 4 entrées »
		Quand je décoche « Montrer aussi les informations »
		Alors la liste des incidents montre les natures « silence », « fichier introuvable », « fichier modifié »

	Scénario: Le filtre garde les entrées dont une colonne contient le texte, sans tenir compte des accents
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Incidents »
		Et je tape « fichier modifie » dans le filtre des incidents
		Alors la liste des incidents montre les natures « fichier modifié »
		Et le compte des incidents est « 1 entrée sur 3 »

	Plan du scénario: Un double-clic sur ce qu'une entrée concerne ouvre sa fiche
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Incidents »
		Et j'ouvre la cellule « <cellule> » de l'entrée « fichier modifié »
		Alors l'onglet ouvert est « <onglet> »

		Exemples:
			| cellule            | onglet                |
			| Les Gaufres – Spot | Sonore : Spot         |
			| Publicité          | Banque : Publicité    |
			| Continue           | Événement : Continue   |

	Scénario: Un double-clic ailleurs dans une entrée n'ouvre rien
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Incidents »
		Et j'ouvre la cellule « taille changée depuis l'indexation » de l'entrée « fichier modifié »
		Alors l'onglet ouvert est « Incidents »

	Scénario: Une entrée garde son message quand ce qu'elle concerne est supprimé
		Étant donné le sonore « Spot » est effacé de la base
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Incidents »
		Alors la liste des incidents montre :
			| Horaire             | Niveau   | Nature              | Message                            | Sonore | Banque    | Événement |
			| 2026-10-19 20:40:00 | alerte   | silence             | rien à diffuser                    |        |           | Continue  |
			| 2026-10-19 20:30:00 | incident | fichier introuvable | /srv/pubs/spot.flac                |        |           | Continue  |
			| 2026-10-19 20:20:00 | alerte   | fichier modifié     | taille changée depuis l'indexation |        | Publicité | Continue  |
		Quand j'ouvre la cellule « /srv/pubs/spot.flac » de l'entrée « fichier introuvable »
		Alors l'onglet ouvert est « Incidents »

	Scénario: La liste se relit à chaque ouverture de son onglet
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Incidents »
		Et Machin lecture note l'incident « flux tombé » à « 2026-10-19 20:50:00 »
		Et j'ouvre l'onglet « Accueil »
		Et j'ouvre l'onglet « Incidents »
		Alors la liste des incidents montre les natures « flux tombé », « silence », « fichier introuvable », « fichier modifié »

	Scénario: Sans alerte ni incident, l'écran le dit
		Étant donné le log est vide
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Incidents »
		Alors le compte des incidents est « aucune entrée »

	Scénario: Seules les 500 entrées les plus récentes sont montrées
		Étant donné 501 alertes « élément sauté » dans le log, une par minute depuis « 2026-10-18 08:00:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Incidents »
		Alors le compte des incidents est « 500 entrées, les plus récentes »
		Et la liste des incidents commence par la nature « silence »
