# language: fr
Fonctionnalité: Tableaux en zebra
	En tant que programmateur de l'antenne,
	je veux que les lignes des tableaux alternent deux fonds,
	afin de suivre une ligne d'un bout à l'autre sans me tromper de ligne.

	https://github.com/dascritch/machincast/issues/412. Chaque tableau, arbre ou liste de l'interface alterne le fond
	du thème et un fond alterné (machincast.interface.zebra). Le fond alterné est le fond, mêlé d'un peu du texte, juste
	assez pour un contraste de 1,12:1 entre les deux fonds : visible, sans être fort. Le texte garde sur lui au moins
	4,5:1, le contraste minimal du RGAA (critère 3.2) : le mélange s'arrête avant, et un thème dont le texte n'y atteint
	déjà pas garde un seul fond. Il suit le thème, clair ou sombre.

	Plan du scénario: Le fond alterné se distingue à peine du fond, et le texte y reste lisible
		Alors le fond alterné de <fond> et <texte> contraste de 1,12 à 1,2 avec le fond
		Et le texte contraste d'au moins 4,5 avec le fond alterné de <fond> et <texte>

		Exemples: thèmes clairs et sombres
			| fond    | texte   |
			| #ffffff | #000000 |
			| #ffffff | #1f1f1f |
			| #fcfcfc | #232629 |
			| #2d2d2d | #ffffff |
			| #1e1e1e | #e0e0e0 |
			| #232629 | #fcfcfc |

	Scénario: Un thème au texte déjà sous 4,5:1 garde un seul fond, plutôt qu'un texte moins lisible encore
		Alors le fond alterné de #ffffff et #777777 est #ffffff

	Scénario: Un thème à la limite de la lisibilité n'alterne que ce que le texte permet
		Alors le fond alterné de #ffffff et #767676 est #fefefe
		Et le texte contraste d'au moins 4,5 avec le fond alterné de #ffffff et #767676

	Scénario: L'interface pose le fond alterné dans la palette de l'application, d'après son thème
		Étant donné le thème de l'application, au fond #ffffff, au texte #000000 et au fond alterné #f7f7f7
		Quand l'application de l'interface se crée
		Alors le fond alterné de l'application est celui de #ffffff et #000000
		Quand le thème de l'application passe au fond #2d2d2d et au texte #ffffff
		Alors le fond alterné de l'application est celui de #2d2d2d et #ffffff

	Scénario: Chaque tableau de la fenêtre alterne ses lignes
		Étant donné l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et les sonores :
			| artist      | title         | type | state  | duration | location               |
			| Les Gaufres | Café à minuit | file | active | 214      | /srv/musique/cafe.flac |
		Et la banque « Rotation », aléatoire, sans nom public, avec « Café à minuit »
		Et la séquence « Passage pub », sans nom public, avec le sonore « Café à minuit »
		Et les événements :
			| name        | public_name | priority               | starts_at | ends_at | days |
			| Fil de jour |             | background_programming |           |         |      |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ouvre l'onglet « Feeds »
		Et j'ouvre la fiche de la banque « Rotation »
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et j'ouvre la fiche de l'événement « Fil de jour »
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et j'appuie sur « Ctrl+F »
		Alors chaque tableau de la fenêtre alterne ses lignes

	Scénario: Chaque tableau des écrans .ui alterne ses lignes, même ceux des fenêtres à part
		Alors chaque tableau des écrans .ui alterne ses lignes
