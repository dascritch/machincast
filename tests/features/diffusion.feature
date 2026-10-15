# language: fr
Fonctionnalité: Boucle de diffusion de Machin lecture
	En tant que technicien d'antenne,
	je veux que Machin lecture diffuse la grille en continu, en assemblant l'ordonnanceur, le moteur audio et l'enregistrement,
	afin que l'antenne tourne sans intervention.

	https://github.com/dascritch/machincast/issues/88. La diffusion avance pas à pas : à chaque pas, l'horloge du
	binaire avance, et la boucle traite les voies finies, consulte l'ordonnanceur et lance le sonore suivant. Les
	sonores sont des copies du fichier de test d'une seconde, joués sur la sortie factice : au plus vite quand
	l'horloge est accélérée, en temps réel quand la superposition ou la coupure doivent s'entendre.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 19:59:50 »

	# ─── Marche continue ───────────────────────────────────────

	Scénario: Le démarrage et l'arrêt sont consignés dans le log
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors le log commence par « info » « démarrage » et finit par « info » « arrêt »

	Scénario: Le fil musical passe en continu, chaque passage écrit dans l'airplay
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 6 pas d'une seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « f2 », « f1 », « f2 », « f1 », « f2 »
		Et chaque passage a sa ligne de fin, sans incident

	Scénario: Une émission prend l'antenne à son heure, puis le fil musical reprend
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Flash » de 19:59:53 à 19:59:55, avec le sonore « m »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 6 pas d'une seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « f2 », « f1 », « m », « m », « f2 »

	Scénario: Un fichier introuvable est consigné et sauté, sans être réessayé
		Étant donné le fil musical permanent « Continue », avec les sonores « disparu », « f1 »
		Et le fichier du sonore « disparu » a été supprimé
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « f1 », « f1 »
		Et le log contient 1 incident « fichier introuvable »

	Scénario: Un fichier introuvable dans une banque est sauté de même
		Étant donné le fil musical permanent « Continue », avec la banque séquentielle « Rotation » des sonores « disparu », « f1 »
		Et le fichier du sonore « disparu » a été supprimé
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « f1 », « f1 »
		Et le log contient 1 incident « fichier introuvable »

	Scénario: Rien à diffuser : silence et alerte, puis la diffusion reprend dès qu'un sonore est jouable
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et le sonore « f1 » est à l'état « desactive »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 2 pas d'une seconde
		Et le sonore « f1 » redevient actif
		Et la diffusion tourne 1 pas d'une seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 »
		Et le log contient 1 alerte « silence »

	# ─── Enchaînements en temps réel ───────────────────────────

	Scénario: Le début d'un événement coupe net le sonore en cours, à la seconde près
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et l'émission « Flash » de 19:59:51 à 19:59:59, avec le sonore « m »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,3 seconde
		Et l'horloge du binaire passe au « 2026-10-14 19:59:51 »
		Et la diffusion tourne 1 pas de 0,1 seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « m »
		Et le passage « f1 » a été coupé net au « 2026-10-14 19:59:51 »
		Et le log contient 1 info « coupure nette »

	Scénario: Deux sonores avec leurs crossfades se superposent
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore a 0,5 seconde de crossfade de début et de fin
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1,2 seconde en temps réel
		Et la diffusion s'arrête
		Alors le passage « f2 » a commencé avant la fin du passage « f1 »

	Scénario: Sans crossfade de début, le sonore suivant attend la fin du précédent
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore a 0,5 seconde de crossfade de fin, et aucun de début
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1,5 seconde en temps réel
		Et la diffusion s'arrête
		Alors le passage « f2 » a commencé après la fin du passage « f1 »

	# ─── Arrêt ─────────────────────────────────────────────────

	Scénario: L'arrêt termine le passage en cours dans l'airplay
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,2 seconde
		Et la diffusion s'arrête
		Alors chaque passage a sa ligne de fin, sans incident
		Et le log finit par « info » « arrêt »

	Scénario: SIGTERM demande l'arrêt de la diffusion
		Étant donné l'arrêt de la diffusion branché sur les signaux
		Quand le processus reçoit SIGTERM
		Alors l'arrêt de la diffusion est demandé

	Scénario: Sans base de données joignable, Machin lecture s'arrête avec le code 1
		Quand je lance Machin_lecture avec une configuration dont la socket n'existe pas
		Alors il s'arrête avec le code 1, en signalant la base de données injoignable
