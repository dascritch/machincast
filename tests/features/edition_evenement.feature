# language: fr
Fonctionnalité: Un événement modifié vaut aussitôt à l'antenne
	En tant que technicien radio,
	je veux que l'édition d'un événement impacte immédiatement l'antenne,
	afin de corriger la diffusion qui est en cours.

	https://github.com/dascritch/machincast/issues/266. Après l'enregistrement, la suppression ou la restauration d'une
	fiche, l'interface demande à Machin lecture, sur la socket d'état, de relire la grille, comme après une session
	sautée (https://github.com/dascritch/machincast/issues/273). Si ce qui règle l'antenne a changé (dates, jours,
	priorité, suppression, listes des événements et des séquences, sessions sautées : EMPREINTE_DE_LA_GRILLE), la durée
	de lecture du sonore en cours, le prochain sonore et les sonores à venir sont recalculés aussitôt. Sinon, rien ne
	change : les sonores à venir, déjà tirés, restent ceux qui passeront. Les sonores durent une minute, sur un moteur
	simulé qui suit l'horloge du binaire.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et la socket d'état dans un répertoire temporaire

	Scénario: Une émission déplacée change aussitôt les sonores à venir
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 », « f6 »
		Et l'émission « Flash » de 20:02:30 à 20:30:00, avec les sonores « m1 », « m2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « f3 », « m1 », « m2 », « m1 », « m2 »
		Quand l'émission « Flash » est déplacée de 20:04:30 à 20:30:00
		Et l'interface demande à Machin lecture de relire la grille
		Et la diffusion avance de 1 seconde
		Alors le prochain sonore réservé est « f2 »
		Et les sonores à venir sont « f3 », « f4 », « f5 », « m1 », « m2 »

	Scénario: Une émission avancée raccourcit aussitôt le sonore en cours
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et l'émission « Flash » de 20:02:30 à 20:30:00, avec les sonores « m1 », « m2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Et l'émission « Flash » est déplacée de 20:00:40 à 20:30:00
		Et l'interface demande à Machin lecture de relire la grille
		Et la diffusion avance de 1 seconde
		Alors le prochain sonore réservé est « m1 »
		Et les sonores à venir sont « m2 », « m1 », « m2 », « m1 », « m2 »
		Quand la diffusion avance de 40 secondes
		Alors l'airplay montre les passages « f1 », « m1 »
		Et le passage « f1 » a été coupé net au « 2026-10-14 20:00:40 »

	Scénario: Une émission retirée de la grille rend aussitôt la suite au fil musical
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 », « f6 »
		Et l'émission « Flash » de 20:02:30 à 20:30:00, avec les sonores « m1 », « m2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Et l'événement « Flash » est supprimé depuis l'interface
		Et l'interface demande à Machin lecture de relire la grille
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « f3 », « f4 », « f5 », « f6 », « f1 »

	Scénario: Une modification sans effet sur l'antenne ne retire pas les sonores à venir, déjà tirés
		Étant donné le fil musical permanent « Continue », avec la banque aléatoire « Rotation » des sonores « a », « b », « c », « d », « e », « g », « h », « i »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Et je note les sonores annoncés
		Et l'événement « Continue » est renommé « Rotation de jour », avec un nom public et un masquage
		Et l'interface demande à Machin lecture de relire la grille
		Et la diffusion avance de 61 secondes
		Alors le prochain sonore et les sonores à venir reprennent les sonores notés à partir du n°2

	Scénario: Une émission qui finit plus tôt rend aussitôt la suite au fil musical
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 », « f6 »
		Et l'émission « Flash » de 20:02:30 à 20:30:00, avec les sonores « m1 », « m2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Et l'émission « Flash » finit à 20:02:40
		Et l'interface demande à Machin lecture de relire la grille
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « f3 », « m1 », « f4 », « f5 », « f6 »

	Scénario: Un événement qui change de priorité change aussitôt les sonores à venir
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et l'émission « Magazine » de 20:01:30 à 20:30:00, avec les sonores « n1 », « n2 »
		Et le spécial « Flash » de 20:02:30 à 20:30:00, avec les sonores « m1 », « m2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « n1 », « m1 », « m2 », « m1 », « m2 »
		Quand l'événement « Flash » passe en fil musical
		Et l'interface demande à Machin lecture de relire la grille
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « n1 », « n2 », « n1 », « n2 », « n1 »

	Scénario: Un événement qui revient un jour de plus change aussitôt les sonores à venir
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 », « f6 »
		Et l'émission « Flash » de 20:02:30 à 20:30:00, avec les sonores « m1 », « m2 »
		Et l'émission « Flash » a eu lieu la veille
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « f3 », « f4 », « f5 », « f6 », « f1 »
		Quand l'événement « Flash » revient aussi le mercredi
		Et l'interface demande à Machin lecture de relire la grille
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « f3 », « m1 », « m2 », « m1 », « m2 »
