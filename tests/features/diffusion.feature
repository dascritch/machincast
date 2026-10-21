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

	Scénario: Une séquence passe à l'antenne, et l'airplay note sa séquence et son élément
		Étant donné la séquence « Pub » des sonores « p1 », « p2 », jouée par le fil musical permanent « Continue », avant le sonore « f »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 4 pas d'une seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « p1 », « p2 », « f », « p1 »
		Et chaque passage de « p1 » et de « p2 » note la séquence « Pub » et son élément, au début comme à la fin

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

	Scénario: Un sonore qui active la détection de blanc passe à l'antenne entre son début et sa fin détectés
		https://github.com/dascritch/machincast/issues/146 : le fichier d'une seconde est joué de 0,25 à 0,75 seconde.

		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et le sonore « f1 » active la détection de blanc, avec 0,25 seconde de blanc détecté au début et 0,25 à la fin
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1,2 seconde en temps réel
		Et la diffusion s'arrête
		Alors le passage « f1 » a duré 0,5 seconde, à 0,15 seconde près
		Et la voie de « f1 » a joué son fichier de 0,25 à 0,75 seconde, à 0,05 seconde près

	Scénario: Sans crossfade de début, le sonore suivant attend la fin du précédent
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore a 0,5 seconde de crossfade de fin, et aucun de début
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1,5 seconde en temps réel
		Et la diffusion s'arrête
		Alors le passage « f2 » a commencé après la fin du passage « f1 »

	# ─── Événements et séquences dans le log (https://github.com/dascritch/machincast/issues/153) ─────────────
	# Les heures sont celles de l'antenne : un événement commence avec son premier passage, et finit quand un passage
	# d'un autre événement commence, ou à l'arrêt ; de même pour une séquence.

	Scénario: Le log note le début et la fin de chaque événement à l'antenne
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Flash » de 19:59:51 à 19:59:53, avec le sonore « m »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 4 pas d'une seconde
		Et la diffusion s'arrête
		Alors le log note pour les événements et les séquences :
			| horodatage          | nature            | message                                  | événement |
			| 2026-10-14 19:59:50 | début d'événement | « Continue », fil musical, permanent     | Continue  |
			| 2026-10-14 19:59:51 | fin d'événement   | « Continue »                             | Continue  |
			| 2026-10-14 19:59:51 | début d'événement | « Flash », émission, de 19:59:51 à 19:59:53 | Flash  |
			| 2026-10-14 19:59:53 | fin d'événement   | « Flash »                                | Flash     |
			| 2026-10-14 19:59:53 | début d'événement | « Continue », fil musical, permanent     | Continue  |
			| 2026-10-14 19:59:54 | fin d'événement   | « Continue »                             | Continue  |

	Scénario: Le log note le début et la fin de chaque séquence, même quand elle revient aussitôt
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et la séquence « Pub » des sonores « s1 », « s2 », jouée par le fil musical permanent « Continue », avant le sonore « f3 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 4 pas d'une seconde
		Et la diffusion s'arrête
		Alors le log note pour les événements et les séquences :
			| horodatage          | nature             | message                          | événement |
			| 2026-10-14 19:59:50 | début d'événement  | « Continue », fil musical, permanent | Continue |
			| 2026-10-14 19:59:50 | début de séquence  | « Pub », dans « Continue »       | Continue  |
			| 2026-10-14 19:59:52 | fin de séquence    | « Pub », dans « Continue »       | Continue  |
			| 2026-10-14 19:59:53 | début de séquence  | « Pub », dans « Continue »       | Continue  |
			| 2026-10-14 19:59:54 | fin de séquence    | « Pub », dans « Continue »       | Continue  |
			| 2026-10-14 19:59:54 | fin d'événement    | « Continue »                     | Continue  |

	Scénario: Un événement qui coupe une séquence la termine, avant de commencer
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et la séquence « Pub » des sonores « s1 », « s2 », jouée par le fil musical permanent « Continue », avant le sonore « f3 »
		Et l'émission « Flash » de 19:59:51 à 19:59:52, avec le sonore « m »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors le log note pour les événements et les séquences :
			| horodatage          | nature             | message                          | événement |
			| 2026-10-14 19:59:50 | début d'événement  | « Continue », fil musical, permanent | Continue |
			| 2026-10-14 19:59:50 | début de séquence  | « Pub », dans « Continue »       | Continue  |
			| 2026-10-14 19:59:51 | fin de séquence    | « Pub », dans « Continue »       | Continue  |
			| 2026-10-14 19:59:51 | fin d'événement    | « Continue »                     | Continue  |
			| 2026-10-14 19:59:51 | début d'événement  | « Flash », émission, de 19:59:51 à 19:59:52 | Flash |
			| 2026-10-14 19:59:52 | fin d'événement    | « Flash »                        | Flash     |
			| 2026-10-14 19:59:52 | début d'événement  | « Continue », fil musical, permanent | Continue |
			| 2026-10-14 19:59:53 | fin d'événement    | « Continue »                     | Continue  |

	Scénario: Une séquence qui revient aussitôt, et une autre qui commence à son deuxième élément, commencent chacune
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le fil musical permanent « Continue » joue les séquences « A » des sonores « a1 », puis « B » des sonores « b1 », « b2 »
		Et le sonore « b1 » est à l'état « desactive »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors le log note pour les événements et les séquences :
			| horodatage          | nature             | message                              | événement |
			| 2026-10-14 19:59:50 | début d'événement  | « Continue », fil musical, permanent | Continue  |
			| 2026-10-14 19:59:50 | début de séquence  | « A », dans « Continue »             | Continue  |
			| 2026-10-14 19:59:51 | fin de séquence    | « A », dans « Continue »             | Continue  |
			| 2026-10-14 19:59:51 | début de séquence  | « B », dans « Continue »             | Continue  |
			| 2026-10-14 19:59:52 | fin de séquence    | « B », dans « Continue »             | Continue  |
			| 2026-10-14 19:59:52 | début de séquence  | « A », dans « Continue »             | Continue  |
			| 2026-10-14 19:59:53 | fin de séquence    | « A », dans « Continue »             | Continue  |
			| 2026-10-14 19:59:53 | fin d'événement    | « Continue »                         | Continue  |

	Scénario: Une même séquence seule dans la liste recommence à chaque tour
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le fil musical permanent « Continue » joue les séquences « Pub » des sonores « s1 », « s2 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors le log note pour les événements et les séquences :
			| horodatage          | nature             | message                              | événement |
			| 2026-10-14 19:59:50 | début d'événement  | « Continue », fil musical, permanent | Continue  |
			| 2026-10-14 19:59:50 | début de séquence  | « Pub », dans « Continue »           | Continue  |
			| 2026-10-14 19:59:52 | fin de séquence    | « Pub », dans « Continue »           | Continue  |
			| 2026-10-14 19:59:52 | début de séquence  | « Pub », dans « Continue »           | Continue  |
			| 2026-10-14 19:59:53 | fin de séquence    | « Pub », dans « Continue »           | Continue  |
			| 2026-10-14 19:59:53 | fin d'événement    | « Continue »                         | Continue  |

	Scénario: Les heures d'un événement s'écrivent à la minute, à la seconde quand elle compte, et sans fin « depuis »
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:59 »
		Et le fil musical permanent « Continue », avec les sonores « f1 »
		Et l'émission « Flash » de 20:00:00 à 20:00:01, avec le sonore « m »
		Et le spécial « Élections » à partir de 20:00:01, sans fin, avec le sonore « e »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors le log note pour les événements et les séquences :
			| horodatage          | nature            | message                                     | événement |
			| 2026-10-14 19:59:59 | début d'événement | « Continue », fil musical, permanent        | Continue  |
			| 2026-10-14 20:00:00 | fin d'événement   | « Continue »                                | Continue  |
			| 2026-10-14 20:00:00 | début d'événement | « Flash », émission, de 20:00 à 20:00:01    | Flash     |
			| 2026-10-14 20:00:01 | fin d'événement   | « Flash »                                   | Flash     |
			| 2026-10-14 20:00:01 | début d'événement | « Élections », spécial, depuis 20:00:01     | Élections |
			| 2026-10-14 20:00:02 | fin d'événement   | « Élections »                               | Élections |

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

	Scénario: Sans périphérique d'antenne, Machin lecture refuse de diffuser sur une vraie sortie
		Quand je lance Machin_lecture sur la sortie « pipewire », sans périphérique d'antenne
		Alors il s'arrête avec le code 2, en signalant « périphérique de l'antenne non renseigné »

	Scénario: Sans base de données joignable, Machin lecture s'arrête avec le code 1
		Quand je lance Machin_lecture avec une configuration dont la socket n'existe pas
		Alors il s'arrête avec le code 1, en signalant la base de données injoignable
