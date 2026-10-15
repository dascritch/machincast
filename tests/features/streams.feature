# language: fr
Fonctionnalité: Diffusion des streams
	En tant que programmateur de l'antenne,
	je veux qu'un stream programmé soit relayé, interrompu au bon moment et remplacé s'il tombe,
	afin qu'un direct extérieur puisse passer à l'antenne sans intervention.

	https://github.com/dascritch/machincast/issues/16, spec § 4.7. Un serveur HTTP local envoie le flux au rythme du
	temps réel, comme un serveur Icecast, en commençant par un MP3 tagué : ses tags ne doivent jamais remplacer les
	métadonnées de la base. La diffusion tourne en temps réel sur la sortie factice ; l'horloge du binaire suit le
	temps réel, et les scénarios la font sauter à l'heure d'un événement. Les tentatives de reconnexion sont espacées
	de 0,2 seconde.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et un serveur de flux local, avec le flux « studio » en ligne
		Et le fil musical permanent « Continue », avec les sonores « f1 », « f2 »

	# ─── Relais ────────────────────────────────────────────────

	Scénario: Un stream à adresse directe est relayé, avec les métadonnées de la base
		Étant donné le stream « Direct studio » à l'adresse du flux « studio »
		Et l'émission « Direct » de 19:59:50 à 20:30:00, avec le sonore « Direct studio »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1,5 seconde en temps réel
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « Direct studio »
		Et le passage « Direct studio » a pour emplacement l'adresse du flux « studio »
		Et aucun passage ne porte l'artiste ou le titre des tags du flux
		Et chaque passage a sa ligne de fin, sans incident

	Scénario: Un stream sur un marque-page est relayé à l'adresse du marque-page
		Étant donné le stream « Direct mobile » sur le marque-page « Studio mobile » du flux « studio »
		Et l'émission « Direct » de 19:59:50 à 20:30:00, avec le sonore « Direct mobile »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1,5 seconde en temps réel
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « Direct mobile »
		Et le passage « Direct mobile » a pour emplacement l'adresse du flux « studio »

	# ─── Arrêt du stream ───────────────────────────────────────

	Scénario: Le début d'un événement de priorité supérieure coupe net le stream
		Étant donné le stream « Direct studio » à l'adresse du flux « studio »
		Et l'émission « Direct » de 19:59:50 à 20:30:00, avec le sonore « Direct studio »
		Et le spécial « Flash » de 19:59:52 à 19:59:59, avec le sonore « m »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1 seconde en temps réel
		Et l'horloge du binaire passe au « 2026-10-14 19:59:52 »
		Et la diffusion tourne 1 pas de 0,3 seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « Direct studio », « m »
		Et le passage « Direct studio » a été coupé net au « 2026-10-14 19:59:52 »
		Et le log contient 1 info « coupure nette »

	Scénario: À la fin de son événement, le stream s'éteint pendant son crossfade de fin, sous le sonore suivant
		Étant donné le stream « Direct studio » à l'adresse du flux « studio »
		Et l'émission « Direct » de 19:59:50 à 19:59:52, avec le sonore « Direct studio »
		Et le sonore « Direct studio » a 0,5 seconde de crossfade de fin
		Et le sonore « f1 » a 0,5 seconde de crossfade de début
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1 seconde en temps réel
		Et l'horloge du binaire passe au « 2026-10-14 19:59:52 »
		Et la diffusion tourne pendant 1 seconde en temps réel
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « Direct studio », « f1 »
		Et le passage « f1 » a commencé avant la fin du passage « Direct studio »
		Et chaque passage a sa ligne de fin, sans incident
		Et le log contient 0 info « coupure nette »

	Scénario: Sans crossfade de début du sonore suivant, il attend la fin du fondu du stream
		Étant donné le stream « Direct studio » à l'adresse du flux « studio »
		Et l'émission « Direct » de 19:59:50 à 19:59:52, avec le sonore « Direct studio »
		Et le sonore « Direct studio » a 0,5 seconde de crossfade de fin
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1 seconde en temps réel
		Et l'horloge du binaire passe au « 2026-10-14 19:59:52 »
		Et la diffusion tourne pendant 1 seconde en temps réel
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « Direct studio », « f1 »
		Et le passage « f1 » a commencé après la fin du passage « Direct studio »
		Et chaque passage a sa ligne de fin, sans incident

	# ─── Flux tombé ────────────────────────────────────────────

	Scénario: Un flux qui s'arrête est un flux tombé : le fil musical joue en attendant, puis le stream reprend
		Étant donné le stream « Direct studio » à l'adresse du flux « studio »
		Et l'émission « Direct » de 19:59:50 à 20:30:00, avec le sonore « Direct studio »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1 seconde en temps réel
		Et le flux « studio » tombe
		Et la diffusion tourne pendant 3 seconde en temps réel
		Et le flux « studio » revient
		Et la diffusion tourne pendant 1,5 seconde en temps réel
		Alors le stream repris joue à plein volume
		Quand la diffusion s'arrête
		Alors l'airplay montre « Direct studio », puis des sonores de « Continue », puis « Direct studio »
		Et le premier passage « Direct studio » a fini en incident
		Et le log contient 1 incident « flux tombé », qui donne l'adresse du flux « studio »
		Et le log contient 1 incident « reprise du flux », qui donne l'adresse du flux « studio »
		Et le log contient 0 incident « lecture interrompue »
		Et l'incident « reprise du flux » suit l'incident « flux tombé »
		Et le sonore joué avant la reprise a fini au début de la reprise

	Scénario: Un stream secouru joue la liste de son événement de secours en attendant, puis reprend en fondu
		Étant donné le stream « Direct studio » à l'adresse du flux « studio »
		Et l'événement de secours « Secours direct », avec les sonores « s1 », « s2 »
		Et le stream « Direct studio » est secouru par « Secours direct »
		Et le sonore « Direct studio » a 0,5 seconde de crossfade de début
		Et l'émission « Direct » de 19:59:50 à 20:30:00, avec le sonore « Direct studio »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1 seconde en temps réel
		Et le flux « studio » tombe
		Et la diffusion tourne pendant 3 seconde en temps réel
		Et le flux « studio » revient
		Et la diffusion tourne pendant 1,5 seconde en temps réel
		Alors le stream repris joue à plein volume
		Quand la diffusion s'arrête
		Alors l'airplay montre « Direct studio », puis des sonores de « Secours direct », puis « Direct studio »
		Et le sonore joué avant la reprise a fini après le début de la reprise
		Et le log contient 1 incident « flux tombé », qui donne l'adresse du flux « studio »
		Et le log contient 1 incident « reprise du flux », qui donne l'adresse du flux « studio »

	Scénario: Un flux injoignable dès le début de son événement est remplacé de même
		Étant donné le stream « Direct studio » à l'adresse du flux « studio »
		Et l'événement de secours « Secours direct », avec les sonores « s1 »
		Et le stream « Direct studio » est secouru par « Secours direct »
		Et l'émission « Direct » de 19:59:50 à 20:30:00, avec le sonore « Direct studio »
		Et le flux « studio » est hors ligne
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1,5 seconde en temps réel
		Et le flux « studio » revient
		Et la diffusion tourne pendant 1,5 seconde en temps réel
		Et la diffusion s'arrête
		Alors l'airplay montre « Direct studio », puis des sonores de « Secours direct », puis « Direct studio »
		Et le premier passage « Direct studio » a fini en incident
		Et le log contient 1 incident « flux tombé », qui donne l'adresse du flux « studio »
		Et le log contient 1 incident « reprise du flux », qui donne l'adresse du flux « studio »

	Scénario: À la fin de l'événement du stream, la reconnexion est abandonnée
		Étant donné le stream « Direct studio » à l'adresse du flux « studio »
		Et l'événement de secours « Secours direct », avec les sonores « s1 »
		Et le stream « Direct studio » est secouru par « Secours direct »
		Et l'émission « Direct » de 19:59:50 à 19:59:53, avec le sonore « Direct studio »
		Et le flux « studio » est hors ligne
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1 seconde en temps réel
		Et l'horloge du binaire passe au « 2026-10-14 19:59:53 »
		Et le flux « studio » revient
		Et la diffusion tourne pendant 2 seconde en temps réel
		Et la diffusion s'arrête
		Alors l'airplay montre 1 passage « Direct studio »
		Et le log contient 1 incident « flux tombé », qui donne l'adresse du flux « studio »
		Et le log contient 0 incident « reprise du flux »
		Et le log contient 1 info « reconnexion abandonnée »

	Scénario: Un événement de secours n'est jamais à l'antenne par la grille
		Étant donné l'événement de secours « Secours direct », avec les sonores « s1 »
		Et le fil musical « Continue » est supprimé
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 2 pas d'une seconde
		Et la diffusion s'arrête
		Alors l'airplay ne montre aucun passage
		Et le log contient 1 alerte « silence »
