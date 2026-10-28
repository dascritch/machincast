# language: fr
Fonctionnalité: Un blanc dans un sonore à l'antenne est noté, et peut faire passer au secours
	En tant que responsable d'antenne,
	je veux qu'un sonore qui ne donne plus de son pendant qu'il joue soit noté, et remplacé si je le demande,
	afin de ne pas laisser l'antenne sur un blanc : un fichier mal monté, un stream qui ne transmet plus que du vide.

	https://github.com/dascritch/machincast/issues/122. Le sonore qui reste blanc_antenne.duree (10 secondes par défaut)
	sous blanc_antenne.seuil (-90 dB crête par défaut) présente un blanc. Le niveau se mesure dans la voie, avant son
	volume : les fondus et une voie muette n'en font pas. Le log note un incident « blanc dans un sonore », avec la
	position du blanc dans le fichier et son niveau moyen. Avec blanc_antenne.secours, un fichier laisse aussitôt
	l'antenne au sonore suivant ; un stream la laisse à son secours, comme un flux tombé, et la reprend dès que son son
	revient, sa voie gardée ouverte. Sans, le blanc est seulement noté. Un blanc dans un sonore n'est ni un silence, au
	début ou à la fin d'un fichier, ni l'alerte « blanc », rien à diffuser
	(https://github.com/dascritch/machincast/issues/291). Les premiers scénarios jouent de vrais fichiers sur la sortie
	factice, au plus vite ; les suivants tournent sur le moteur simulé, qui imite le blanc. Le scénario d'un vrai stream
	muet est dans streams.feature.

	# ─── Mesure, dans la voie ──────────────────────────────────

	Plan du scénario: Un sonore ne présente un blanc que s'il reste sous le seuil au moins la durée d'un blanc
		Étant donné un blanc dans un sonore réglé à <duree> secondes sous <seuil> dB, qui est noté seulement
		Et le fichier « parole » : 1 seconde à -20 dB, 3 secondes à -80 dB, puis 1 seconde à -20 dB
		Quand une voie joue le fichier « parole » jusqu'au bout, au plus vite
		Alors la voie a présenté <blancs> blanc

		Exemples:
			| duree | seuil | blancs |
			| 2     | -70   | 1      |
			| 2,8   | -70   | 1      |
			| 3,5   | -70   | 0      |
			| 2     | -90   | 0      |
			| 2     | -82   | 0      |

	Scénario: Chaque blanc donne sa position dans le fichier et son niveau moyen, un silence numérique n'en a pas
		Étant donné un blanc dans un sonore réglé à 2 secondes sous -70 dB, qui est noté seulement
		Et le fichier « parole » : 1 seconde à -20 dB, 3 secondes à -80 dB, 1 seconde à -20 dB, 3 secondes de silence numérique, puis 1 seconde à -20 dB
		Quand une voie joue le fichier « parole » jusqu'au bout, au plus vite
		Alors la voie a présenté 2 blancs
		Et le blanc n°1 commence à 1 seconde du fichier, au niveau moyen de -83 dB
		Et le blanc n°2 commence à 5 secondes du fichier, en silence numérique

	Scénario: Un long blanc n'est signalé qu'une fois
		Étant donné un blanc dans un sonore réglé à 2 secondes sous -70 dB, qui est noté seulement
		Et le fichier « parole » : 1 seconde à -20 dB, 9 secondes de silence numérique, puis 1 seconde à -20 dB
		Quand une voie joue le fichier « parole » jusqu'au bout, au plus vite
		Alors la voie a présenté 1 blanc
		Et le blanc n°1 commence à 1 seconde du fichier, en silence numérique

	Scénario: Un sonore rogné donne la position de son blanc dans le fichier
		Étant donné un blanc dans un sonore réglé à 2 secondes sous -70 dB, qui est noté seulement
		Et le fichier « parole » : 1 seconde à -20 dB, 3 secondes de silence numérique, puis 1 seconde à -20 dB
		Quand une voie joue le fichier « parole » à partir de 0,5 seconde du fichier, jusqu'au bout, au plus vite
		Alors la voie a présenté 1 blanc
		Et le blanc n°1 commence à 1 seconde du fichier, en silence numérique

	Scénario: Le niveau se mesure avant le volume : une voie muette ne présente pas de blanc, et elle est entendue
		Étant donné un blanc dans un sonore réglé à 2 secondes sous -70 dB, qui est noté seulement
		Et le fichier « parole » : 5 secondes à -20 dB
		Quand une voie muette joue le fichier « parole » jusqu'au bout, au plus vite
		Alors la voie a présenté 0 blanc
		Et la voie a été entendue

	Scénario: Une voie qui finit sur un blanc n'est plus entendue
		Étant donné un blanc dans un sonore réglé à 2 secondes sous -70 dB, qui est noté seulement
		Et le fichier « parole » : 1 seconde à -20 dB, puis 1 seconde de silence numérique
		Quand une voie joue le fichier « parole » jusqu'au bout, au plus vite
		Alors la voie a présenté 0 blanc
		Et la voie n'est plus entendue

	# ─── Diffusion ─────────────────────────────────────────────

	Scénario: Sans passage au secours, le blanc est noté, et le sonore continue
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et un blanc dans un sonore réglé à 10 secondes sous -90 dB, qui est noté seulement
		Et le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et chaque sonore dure 60 secondes
		Et le sonore « f2 » présente un blanc à 20 secondes de son début, au niveau moyen de -95 dB
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 125 secondes
		Alors l'airplay montre les passages « f1 », « f2 », « f3 »
		Et le passage « f2 » a fini sans incident
		Et le log contient 1 incident « blanc dans un sonore »
		Et l'incident « blanc dans un sonore » dit « f2/sain.flac : blanc de 10 s à 0:20,0 du sonore, niveau moyen -95,0 dB »
		Et l'incident « blanc dans un sonore » a été noté au « 2026-10-14 20:01:30 », pour le sonore « f2 » de « Continue »

	Scénario: Avec passage au secours, un fichier en blanc laisse aussitôt l'antenne au sonore suivant
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et un blanc dans un sonore réglé à 10 secondes sous -90 dB, qui fait passer au secours
		Et le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et chaque sonore dure 60 secondes
		Et le sonore « f2 » présente un blanc à 20 secondes de son début, au niveau moyen de -95 dB
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 91 secondes
		Alors l'airplay montre les passages « f1 », « f2 », « f3 »
		Et le passage « f2 » a fini en incident « blanc dans un sonore » au « 2026-10-14 20:01:30 »
		Et l'incident « blanc dans un sonore » dit « blanc de 10 s à 0:20,0 du sonore, niveau moyen -95,0 dB, le sonore suivant est joué »
		Et le log contient 1 incident « blanc dans un sonore »

	Scénario: Avec passage au secours, un stream en blanc laisse l'antenne à son secours, et la reprend quand son son revient
		La voie du stream reste ouverte, muette : elle sert de sonde, sans nouvelle connexion, et le stream reprend dès
		que son niveau repasse le seuil, comme un flux tombé qui revient.

		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et un blanc dans un sonore réglé à 10 secondes sous -90 dB, qui fait passer au secours
		Et l'événement de secours « Secours direct », avec les sonores « s1 », « s2 »
		Et chaque sonore dure 60 secondes
		Et le stream « Direct studio » à une adresse factice
		Et le stream « Direct studio » est secouru par « Secours direct »
		Et l'émission « Direct » de 20:00:00 à 20:30:00, avec le sonore « Direct studio »
		Et le sonore « Direct studio » présente un blanc à 20 secondes de son début, au niveau moyen de -95 dB, et son son revient à 50 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 45 secondes
		Alors l'airplay montre les passages « Direct studio », « s1 »
		Et le passage « Direct studio » a fini en incident « blanc dans un sonore » au « 2026-10-14 20:00:30 »
		Et l'incident « blanc dans un sonore » dit « blanc de 10 s à 0:20,0 de sa lecture, niveau moyen -95,0 dB, le stream laisse l'antenne jusqu'au retour de son son »
		Et le log contient 0 incident « reprise du flux »
		Quand la diffusion avance de 10 secondes
		Alors l'airplay montre les passages « Direct studio », « s1 », « Direct studio »
		Et le log contient 1 incident « reprise du flux »
		Et le log contient 0 incident « flux tombé »
		Et le moteur n'a ouvert qu'une voie pour « Direct studio »

	Scénario: Sans passage au secours, un stream en blanc garde l'antenne
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et un blanc dans un sonore réglé à 10 secondes sous -90 dB, qui est noté seulement
		Et le stream « Direct studio » à une adresse factice
		Et l'événement de secours « Secours direct », avec les sonores « s1 »
		Et le stream « Direct studio » est secouru par « Secours direct »
		Et l'émission « Direct » de 20:00:00 à 20:30:00, avec le sonore « Direct studio »
		Et le sonore « Direct studio » présente un blanc à 20 secondes de son début, au niveau moyen de -95 dB, et son son revient à 50 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 60 secondes
		Alors l'airplay montre les passages « Direct studio »
		Et le log contient 1 incident « blanc dans un sonore »

	Scénario: Un stream qui s'éteint à la fin de son événement n'est pas concerné par un blanc
		Il laisse déjà l'antenne : son blanc n'est ni noté, ni secouru.

		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et un blanc dans un sonore réglé à 10 secondes sous -90 dB, qui fait passer au secours
		Et le fil musical permanent « Continue », avec les sonores « f1 »
		Et l'événement de secours « Secours direct », avec les sonores « s1 »
		Et chaque sonore dure 60 secondes
		Et le stream « Direct studio » à une adresse factice
		Et le stream « Direct studio » est secouru par « Secours direct »
		Et le sonore « Direct studio » a 15 seconde de crossfade de fin
		Et l'émission « Direct » de 20:00:00 à 20:00:25, avec le sonore « Direct studio »
		Et le sonore « Direct studio » présente un blanc à 20 secondes de son début, au niveau moyen de -95 dB
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 45 secondes
		Alors l'airplay montre les passages « Direct studio », « f1 »
		Et le log contient 0 incident « blanc dans un sonore »

	Plan du scénario: La position d'un blanc s'écrit en minutes, secondes et dixièmes, et en heures au-delà
		Alors un blanc à <secondes> secondes s'écrit « <position> »

		Exemples:
			| secondes | position  |
			| 0        | 0:00,0    |
			| 20       | 0:20,0    |
			| 83,44    | 1:23,4    |
			| 3599,96  | 1:00:00,0 |
			| 3723,4   | 1:02:03,4 |

	Scénario: Machin lecture prend le blanc dans un sonore de sa configuration
		Le moteur le mesure, la diffusion décide du passage au secours. Ni la base ni la sortie audio ne sont jointes :
		le scénario remplace la connexion, le moteur et la boucle de diffusion.

		Étant donné la configuration des tests, avec un blanc dans un sonore de 4,5 secondes sous -70 dB, qui fait passer au secours
		Quand Machin lecture diffuse avec cette configuration, sans base ni sortie audio
		Alors son moteur mesure un blanc de 4,5 secondes sous -70 dB, et sa diffusion fait passer au secours
