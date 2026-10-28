# language: fr
Fonctionnalité: Un sonore dont la lecture ne démarre pas est remplacé
	En tant que responsable d'antenne,
	je veux qu'un sonore qui ne démarre pas soit remplacé,
	afin de ne jamais laisser l'antenne en silence sur un lecteur bloqué.

	https://github.com/dascritch/machincast/issues/281. playbin se bloquait au démarrage d'un AIFF, avec GStreamer 1.24
	comme 1.28 : la voie reste « en cours », sans erreur ni son. playbin3, le lecteur des voies depuis
	https://github.com/dascritch/machincast/issues/284, ne s'est jamais bloqué ; la garde reste contre tout lecteur qui
	ne démarre pas. Passé le délai de démarrage
	(moteur.DELAI_DE_GARDE, 10 secondes), la voie est bloquée : la diffusion termine son passage en incident « lecture
	bloquée », et joue le sonore suivant, comme après un sonore fini. Un stream n'est jamais déclaré bloqué ainsi : sa
	connexion a son propre délai, et sa chute son repli (https://github.com/dascritch/machincast/issues/16). Les
	scénarios tournent sur le moteur simulé, qui suit l'horloge du binaire ; le lecteur bloqué est imité.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 20:00:00 »

	Scénario: Un sonore dont la lecture ne démarre pas est remplacé par le suivant, et l'incident est noté
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et chaque sonore dure 60 secondes
		Et le lecteur du sonore « f2 » se bloque à son premier démarrage
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 62 secondes
		Alors l'airplay montre les passages « f1 », « f2 »
		Quand la diffusion avance de 9 secondes
		Alors l'airplay montre les passages « f1 », « f2 », « f3 »
		Et le passage « f2 » a fini en incident « lecture bloquée » au « 2026-10-14 20:01:10 »
		Et le log contient 1 incident « lecture bloquée »

	Scénario: Le sonore bloqué une fois rejoue normalement à son tour suivant
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Et le lecteur du sonore « f2 » se bloque à son premier démarrage
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 64 secondes
		Et la diffusion avance de 118 secondes
		Alors l'airplay montre les passages « f1 », « f2 », « f1 », « f2 »
		Et le log contient 1 incident « lecture bloquée »

	Scénario: Un stream qui tarde à donner du son n'est pas déclaré bloqué
		Étant donné le stream « Direct studio » à une adresse factice
		Et l'émission « Direct » de 20:00:00 à 20:30:00, avec le sonore « Direct studio »
		Et le lecteur du sonore « Direct studio » se bloque à son premier démarrage
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 12 secondes
		Alors l'airplay montre les passages « Direct studio »
		Et le log contient 0 incident « lecture bloquée »
