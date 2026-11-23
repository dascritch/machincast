# language: fr
Fonctionnalité: Les points d'extension de Machin player
	En tant que développeur d'un plugin,
	je veux être prévenu de ce que joue Machin player,
	afin de réagir à l'antenne : publier un titre, avertir, enregistrer
	(https://github.com/dascritch/machincast/issues/589, ticket enfant de https://github.com/dascritch/machincast/issues/348).

	Contexte:
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le fil musical permanent « Continue » joue les séquences « Intro » des sonores « i1 », « i2 »
		Et le sonore « i1 » dure 60 secondes en base
		Et le sonore « i2 » dure 60 secondes en base
		Et l'émission « Matinale » de 20:00:00 à 20:30:00, avec le sonore « m1 »
		Et le sonore « m1 » dure 600 secondes en base
		Et l'événement « Matinale » a pour nom public « La matinale », et masque ses sonores

	Scénario: Un plugin est prévenu du démarrage, des événements, des séquences, des sonores et de l'arrêt
		Étant donné un plugin abonné à chaque point de Machin player
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 15 secondes
		Et la diffusion s'arrête
		Alors le plugin a été prévenu, dans l'ordre :
			| point                 | de        |
			| player.service_start  |           |
			| player.event_start    | Continue  |
			| player.sequence_start | Intro     |
			| player.sound_start    | i1        |
			| player.sound_stop     | i1        |
			| player.sequence_stop  | Intro     |
			| player.event_stop     | Continue  |
			| player.event_start    | Matinale  |
			| player.sound_start    | m1        |
			| player.sound_stop     | m1        |
			| player.event_stop     | Matinale  |
			| player.service_stop   |           |
		Et « player.event_start » de « Matinale » dit : nom public « La matinale », priorité « show », de « 2026-10-14 20:00 » à « 2026-10-14 20:30 »
		Et « player.event_start » de « Continue » dit : sans nom public, priorité « background_programming », sans début ni fin
		Et « player.sequence_start » de « Intro » dit l'événement « Continue »
		Et « player.sound_stop » de « i1 » dit : coupé, 10 secondes jouées, de la position 0 à la position 10, sans erreur
		Et « player.sound_start » de « m1 » dit : 600 secondes, de la position 0, dans l'événement « Matinale »
		Et « player.sound_stop » de « m1 » dit : terminé, 5 secondes jouées, de la position 0 à la position 5, sans erreur
		Et « player.service_stop » dit : sans erreur

	Scénario: Un plugin lent ou en erreur ne retarde ni n'arrête l'antenne, et son erreur est consignée
		Étant donné un plugin « lent », bloqué à chaque point de Machin player jusqu'à la fin du scénario
		Et un plugin « fautif », qui échoue à chaque point de Machin player
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 15 secondes
		Alors la diffusion a avancé sans attendre les plugins
		Et l'airplay montre les passages « i1 », « m1 »
		Quand les plugins ont fini
		Alors le journal du binaire dit que le plugin « fautif » a échoué au point « player.sound_start »
		Et le plugin « lent » a été prévenu de « player.sound_start » 2 fois

	Scénario: En simulation, aucun point n'est appelé
		Étant donné un plugin chargé, abonné à chaque point de Machin player
		Quand la diffusion de 19:59:50 à 20:00:30 est simulée
		Alors le plugin chargé n'a été prévenu de rien
