# language: fr
Fonctionnalité: Sauter une session d'un événement récurrent, à la diffusion
	En tant que responsable d'antenne,
	je veux annuler une session d'un événement récurrent à venir,
	afin de marquer une période de vacances et de remplacer par une autre émission pendant une certaine période.

	https://github.com/dascritch/machincast/issues/273. Une session sautée se note en base par le jour où elle commence
	(evenements_sauts) ; la grille (machincast.lecture.grille) ne la joue pas, et l'antenne revient à ce qui joue sans
	elle : le fil musical, ou un autre événement. L'interface la saute depuis le calendrier, puis demande à Machin
	lecture, sur la socket d'état, de relire la grille : le prochain sonore et les sonores à venir sont recalculés
	aussitôt, sans attendre le changement de sonore. Les sonores des scénarios durent une minute, sur un moteur simulé
	qui suit l'horloge du binaire ; « Flash » revient chaque mercredi et chaque jeudi, le 14 octobre 2026 étant un
	mercredi.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 »
		Et l'émission « Flash » de 20:02:30 à 20:30:00, avec les sonores « m1 », « m2 »
		Et l'émission « Flash » revient chaque mercredi et chaque jeudi
		Et chaque sonore dure 60 secondes

	Scénario: Une session sautée ne joue pas : le fil musical garde l'antenne
		Étant donné l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et la session du 2026-10-14 de l'événement « Flash » est sautée
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors le prochain sonore réservé est « f2 »
		Et les sonores à venir sont « f3 », « f4 », « f5 », « f1 », « f2 »

	Scénario: Les autres sessions de l'événement jouent toujours
		Étant donné l'horloge du binaire au « 2026-10-15 20:00:00 »
		Et la session du 2026-10-14 de l'événement « Flash » est sautée
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « f3 », « m1 », « m2 », « m1 », « m2 »

	Scénario: Une session rétablie joue de nouveau
		Étant donné l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et la session du 2026-10-14 de l'événement « Flash » est sautée
		Et la session du 2026-10-14 de l'événement « Flash » est rétablie
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « f3 », « m1 », « m2 », « m1 », « m2 »

	Scénario: La demande de relire la grille recalcule aussitôt le prochain sonore et les sonores à venir
		Étant donné l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et la socket d'état dans un répertoire temporaire
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « f3 », « m1 », « m2 », « m1 », « m2 »
		Quand la session du 2026-10-14 de l'événement « Flash » est sautée
		Et l'interface demande à Machin lecture de relire la grille
		Et la diffusion avance de 1 seconde
		Alors le prochain sonore réservé est « f2 »
		Et les sonores à venir sont « f3 », « f4 », « f5 », « f1 », « f2 »
		Quand la diffusion avance de 300 secondes
		Alors l'airplay montre les passages « f1 », « f2 », « f3 », « f4 », « f5 », « f1 »


	Scénario: Sans demande, la session sautée vaut au prochain changement de sonore
		Étant donné l'horloge du binaire au « 2026-10-14 20:00:00 »
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Et la session du 2026-10-14 de l'événement « Flash » est sautée
		Et la diffusion avance de 60 secondes
		Alors le prochain sonore réservé est « f3 »
		Et les sonores à venir sont « f4 », « f5 », « f1 », « f2 », « f3 »
