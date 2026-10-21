# language: fr
Fonctionnalité: Icônes des genres, uniformes dans toute l'interface
	En tant que programmateur de l'antenne,
	je veux qu'une même icône désigne partout un même genre d'élément,
	afin de reconnaître d'un coup d'œil un sonore, une séquence, une banque, un événement, la grille ou la simulation.

	https://github.com/dascritch/machincast/issues/215. Chaque genre a son icône monochrome, dessinée pour MachinCast
	(machincast.interface.icones) : une croche pour un sonore, une feuille et sa liste à puces pour une séquence, un
	dossier pour une banque, une montre pour un événement, un calendrier pour la grille, une boule de divination pour la
	simulation. Elle prend la couleur du texte du thème, clair ou sombre. Elle désigne le genre dans les onglets (listes,
	fiches, grille, simulation), le menu « Affichage », la colonne « Type » de la recherche et les relations de la fiche
	d'un sonore. Les autres écrans, Accueil, Incidents, Recherche et Marques-pages, n'en ont pas.

	Contexte:
		Étant donné l'horloge de l'interface au « 2026-10-21 09:00:00 »

	Plan du scénario: Chaque icône est monochrome, de la couleur du texte du thème
		Alors l'icône « <genre> », dessinée en <couleur>, n'a que cette couleur, et se voit à 16, 24, 32 et 48 pixels

		Exemples:
			| genre      | couleur |
			| sonore     | #2a2a2a |
			| séquence   | #2a2a2a |
			| banque     | #2a2a2a |
			| événement  | #2a2a2a |
			| grille     | #2a2a2a |
			| simulation | #2a2a2a |
			| sonore     | #f0f0f0 |
			| simulation | #f0f0f0 |

	Scénario: Les six icônes sont différentes les unes des autres
		Alors les icônes « sonore », « séquence », « banque », « événement », « grille » et « simulation » sont toutes différentes

	Scénario: L'icône suit la couleur du texte du thème de l'application
		Quand le thème de l'application écrit en #f0f0f0
		Alors l'icône « banque » de l'application est dessinée en #f0f0f0

	Scénario: Les onglets portent l'icône de leur genre
		Étant donné les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement            |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/musique/cafe.flac |
		Et la banque « Rotation », aléatoire, sans nom public, avec « Café à minuit »
		Et la séquence « Passage pub », sans nom public, avec le sonore « Café à minuit »
		Et les événements :
			| nom         | nom_public | priorite    | debut | fin | jours |
			| Fil de jour |            | fil_musical |       |     |       |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ouvre l'onglet « Marques-pages »
		Et j'ouvre la fiche de la banque « Rotation »
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et j'ouvre la fiche de l'événement « Fil de jour »
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et j'appuie sur « Ctrl+F »
		Alors les onglets portent les icônes :
			| onglet                   | icône      |
			| Accueil                  | aucune     |
			| Événements               | événement  |
			| Séquences                | séquence   |
			| Banques                  | banque     |
			| Sonores                  | sonore     |
			| Marques-pages            | aucune     |
			| Incidents                | aucune     |
			| Banque : Rotation        | banque     |
			| Séquence : Passage pub   | séquence   |
			| Événement : Fil de jour  | événement  |
			| Sonore : Café à minuit   | sonore     |
			| Calendrier               | grille     |
			| Simulation               | simulation |
			| Recherche                | aucune     |

	Scénario: Une nouvelle fiche porte l'icône de son genre dès son ouverture
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je clique sur « Nouvelle banque »
		Alors l'onglet « Nouvelle banque » porte l'icône « banque »

	Scénario: Le menu « Affichage » donne aux onglets à ouvrir l'icône de leur genre
		Quand la fenêtre de l'interface s'ouvre
		Alors les entrées du menu « Affichage » portent les icônes :
			| entrée                          | icône      |
			| Rafraîchir les onglets          | aucune     |
			| Rechercher…                     | aucune     |
			| Ouvrir l'onglet Sonores         | sonore     |
			| Ouvrir l'onglet Marques-pages   | aucune     |
			| Ouvrir l'onglet Grille horaire  | grille     |
			| Ouvrir l'onglet Simulation      | simulation |
			| Pré-écoute…                     | aucune     |

	Scénario: La colonne « Type » de la recherche porte l'icône de chaque genre
		Étant donné les sonores :
			| artiste | titre | type    | etat  | duree | emplacement     |
			|         | Matin | fichier | actif | 214   | /srv/matin.flac |
		Et la banque « Matin calme », aléatoire, sans nom public, avec « Matin »
		Et la séquence « Matin pub », sans nom public, avec le sonore « Matin »
		Et les événements :
			| nom         | nom_public | priorite    | debut | fin | jours |
			| Matinale    |            | fil_musical |       |     |       |
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « Ctrl+F »
		Et je tape « matin » dans le champ de recherche
		Alors les résultats de la recherche portent les icônes :
			| type      | nom         | icône     |
			| Événement | Matinale    | événement |
			| Séquence  | Matin pub   | séquence  |
			| Banque    | Matin calme | banque    |
			| Sonore    | Matin       | sonore    |

	Scénario: Les relations de la fiche d'un sonore portent l'icône de chaque genre
		Étant donné les sonores :
			| artiste | titre | type    | etat  | duree | emplacement     |
			|         | Matin | fichier | actif | 214   | /srv/matin.flac |
		Et la banque « Matin calme », aléatoire, sans nom public, avec « Matin »
		Et la séquence « Matin pub », sans nom public, avec le sonore « Matin »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Matin »
		Alors les relations de la fiche portent les icônes :
			| genre    | nom         | icône    |
			| séquence | Matin pub   | séquence |
			| banque   | Matin calme | banque   |
