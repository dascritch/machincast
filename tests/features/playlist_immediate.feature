# language: fr
Fonctionnalité: Playlist immédiate
	En tant que responsable d'antenne,
	je veux voir les cinq sonores qui passeront après le prochain,
	afin de savoir ce que l'antenne diffusera dans les minutes qui viennent.

	https://github.com/dascritch/machincast/issues/228, spec § 4.10. Les sonores à venir sont engagés : c'est eux qui
	passent, dans cet ordre, même tirés au hasard. À chaque changement de sonore, la liste avance d'un cran et Machin
	lecture calcule le cinquième ; sur un imprévu (saut manuel, coupure qu'elle n'avait pas prévue, grille modifiée,
	sonore qui n'est plus jouable), elle est recalculée. Les sonores des scénarios durent une minute, sur un moteur
	simulé qui suit l'horloge du binaire.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 20:00:00 »

	Scénario: Les cinq sonores qui suivront le prochain sont annoncés dès le démarrage
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 », « f6 », « f7 », « f8 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors le prochain sonore réservé est « f2 »
		Et les sonores à venir sont « f3 », « f4 », « f5 », « f6 », « f7 »

	Scénario: À chaque changement de sonore, la liste avance d'un cran
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 », « f6 », « f7 », « f8 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 61 secondes
		Alors le prochain sonore réservé est « f3 »
		Et les sonores à venir sont « f4 », « f5 », « f6 », « f7 », « f8 »

	Scénario: Une liste qui boucle annonce son retour au début
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « f3 », « f1 », « f2 », « f3 », « f1 »

	Scénario: Les sonores à venir sont ceux qui passent, même tirés au hasard
		Étant donné le fil musical permanent « Continue », avec la banque aléatoire « Rotation » des sonores « a », « b », « c », « d », « e », « g », « h », « i »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Et je note les sonores annoncés
		Et la diffusion avance de 420 secondes
		Alors les passages, à partir du deuxième, sont les sonores notés

	Scénario: L'événement qui coupera un sonore à venir est prévu
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 »
		Et l'émission « Flash » de 20:02:30 à 20:30:00, avec les sonores « m1 », « m2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors le prochain sonore réservé est « f2 »
		Et les sonores à venir sont « f3 », « m1 », « m2 », « m1 », « m2 »

	Scénario: Après une émission qui finit, le fil musical reprend dans les sonores à venir
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 »
		Et l'émission « Flash » de 20:00:00 à 20:02:30, avec les sonores « m1 », « m2 », « m3 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors le prochain sonore réservé est « m2 »
		Et les sonores à venir sont « m3 », « f1 », « f2 », « f3 », « f4 »

	Scénario: Le dernier sonore d'un spécial sans fin rend l'antenne au fil musical
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 »
		Et le spécial « Nuit » à partir de 20:00:00, sans fin, avec les sonores « n1 », « n2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors le prochain sonore réservé est « n2 »
		Et les sonores à venir sont « f1 », « f2 », « f3 », « f4 », « f5 »
		Quand la diffusion avance de 240 secondes
		Alors l'airplay montre les passages « n1 », « n2 », « f1 », « f2 », « f3 »

	Scénario: La liste ne va pas au-delà d'un blanc
		Étant donné l'émission « Flash » de 20:00:00 à 20:02:30, avec les sonores « m1 », « m2 », « m3 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors le prochain sonore réservé est « m2 »
		Et les sonores à venir sont « m3 »

	Scénario: Une émission ajoutée à la grille fait recalculer la liste au changement de sonore
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 », « f6 », « f7 », « f8 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 30 secondes
		Et l'émission « Flash » de 20:04:00 à 20:30:00, avec les sonores « m1 », « m2 », est ajoutée à la grille
		Alors les sonores à venir sont « f3 », « f4 », « f5 », « f6 », « f7 »
		Quand la diffusion avance de 31 secondes
		Alors le prochain sonore réservé est « f3 »
		Et les sonores à venir sont « f4 », « m1 », « m2 », « m1 », « m2 »

	Scénario: Un sonore à venir qui n'est plus jouable est remplacé, et la liste recalculée
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 », « f6 », « f7 », « f8 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Et le sonore « f2 » est désactivé
		Et la diffusion avance de 60 secondes
		Alors l'airplay montre les passages « f1 », « f3 »
		Et le prochain sonore réservé est « f4 »
		Et les sonores à venir sont « f5 », « f6 », « f7 », « f8 », « f1 »

	Scénario: Sauter au sonore suivant fait avancer la liste d'un cran
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 », « f6 », « f7 », « f8 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je saute au sonore suivant
		Alors le prochain sonore réservé est « f3 »
		Et les sonores à venir sont « f4 », « f5 », « f6 », « f7 », « f8 »

	Scénario: Sauter au sonore suivant avance les heures : une coupure qui n'est plus prévue fait recalculer la liste
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 », « f6 », « f7 », « f8 »
		Et l'émission « Flash » de 20:01:30 à 20:30:00, avec les sonores « m1 », « m2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « m1 », « m2 », « m1 », « m2 », « m1 »
		Quand la diffusion avance de 9 secondes
		Et je saute au sonore suivant
		Alors le prochain sonore réservé est « f3 »
		Et les sonores à venir sont « m1 », « m2 », « m1 », « m2 », « m1 »

	Scénario: Le fil musical qui suit un spécial sans fin passe comme il était annoncé, même tiré au hasard
		Étant donné le fil musical permanent « Continue », avec la banque aléatoire « Rotation » des sonores « a », « b », « c », « d », « e », « g », « h », « i »
		Et le spécial « Nuit » à partir de 20:00:00, sans fin, avec les sonores « n1 », « n2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Et je note les sonores annoncés
		Et la diffusion avance de 420 secondes
		Alors les passages, à partir du deuxième, sont les sonores notés

	Scénario: Un sonore annoncé dont le fichier a disparu est remplacé, et la liste recalculée
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 », « f6 », « f7 », « f8 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Et le fichier de test du sonore « f2 » disparaît
		Et la diffusion avance de 60 secondes
		Alors l'airplay montre les passages « f1 », « f3 »
		Et le prochain sonore réservé est « f4 »
		Et les sonores à venir sont « f5 », « f6 », « f7 », « f8 », « f1 »

	Scénario: Le sonore qui suit est choisi au début du crossfade de fin du précédent
		Une émission qui commence pendant ce crossfade ne coupe pas le sonore choisi juste avant elle.

		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 »
		Et l'émission « Flash » de 20:01:50 à 20:30:00, avec les sonores « m1 », « m2 »
		Et chaque sonore dure 60 secondes
		Et le sonore « f2 » a 20 seconde de crossfade de fin
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors le prochain sonore réservé est « f2 »
		Et les sonores à venir sont « f3 », « m1 », « m2 », « m1 », « m2 »
