# language: fr
Fonctionnalité: Socket d'état du binaire lecture
	En tant que technicien d'antenne,
	je veux que le binaire lecture publie son état sur une socket Unix,
	afin que l'interface affiche en temps réel ce qui passe à l'antenne.

	https://github.com/dascritch/machincast/issues/20, spec § 5.4 et § 4.6. Le binaire envoie une ligne JSON, de
	version 1, à chaque client qui se connecte, puis à chaque changement, et au moins chaque seconde pour la
	progression. Le prochain sonore est réservé dès le début du sonore en cours : c'est lui qui sera joué, sauf si un
	événement coupe la diffusion ou s'il n'est plus jouable. La socket est créée dans un répertoire temporaire.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et la socket d'état dans un répertoire temporaire

	# ─── Sonore en cours ───────────────────────────────────────

	Scénario: À la connexion, la socket donne l'état de la diffusion, en JSON versionné
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et la diffusion tourne 1 pas de 0,1 seconde
		Et un client lit la socket d'état
		Alors le message est en version 1, à l'état « diffusion »
		Et le sonore en cours est « f1 », un fichier de l'événement « Continue »
		Et il a commencé au « 2026-10-14 19:59:50 », dure 1 seconde et finira au « 2026-10-14 19:59:51 »
		Et sa progression est entre 0 et 1
		Et l'emplacement du sonore en cours est le fichier de « f1 »

	Scénario: Un stream en cours a une durée inconnue
		Étant donné un serveur de flux local, avec le flux « studio » en ligne
		Et le stream « Direct studio » à l'adresse du flux « studio »
		Et l'émission « Direct » de 19:59:50 à 20:30:00, avec le sonore « Direct studio »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1 seconde en temps réel
		Et un client lit la socket d'état
		Alors le sonore en cours est « Direct studio », un stream de l'événement « Direct »
		Et sa durée, sa fin estimée et sa progression sont inconnues
		Et l'emplacement du sonore en cours est l'adresse du flux « studio »

	Scénario: Rien à diffuser : la socket annonce le silence
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et le sonore « f1 » est à l'état « desactive »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Et un client lit la socket d'état
		Alors le message est en version 1, à l'état « silence »
		Et il n'y a ni sonore en cours ni prochain sonore

	# ─── Contexte du sonore (https://github.com/dascritch/machincast/issues/144) ─────

	Scénario: Le sonore en cours et le prochain disent leur banque, et l'événement qui les joue
		Étant donné le fil musical permanent « Continue », avec la banque séquentielle « Titres » des sonores « f1 », « f2 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et un client lit la socket d'état
		Alors le sonore en cours vient de la banque « Titres », sans séquence, de l'événement « Continue », permanent
		Et le prochain sonore vient de la banque « Titres », sans séquence, de l'événement « Continue », permanent
		Et le texte public du sonore en cours est « f1 »
		Et le prochain sonore n'a pas de texte public

	Scénario: Un sonore joué par une séquence dit sa séquence
		Étant donné la séquence « Pub » des sonores « s1 », « s2 », jouée par le fil musical permanent « Continue », avant le sonore « f3 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et un client lit la socket d'état
		Alors le sonore en cours vient de la séquence « Pub », sans banque, de l'événement « Continue », permanent

	Scénario: Le sonore d'une émission donne les heures de début et de fin de l'événement
		Étant donné l'émission « Journal » de 19:59:50 à 20:30:00, avec le sonore « f1 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et un client lit la socket d'état
		Alors l'événement du sonore en cours va du « 2026-10-14 19:59:50 » au « 2026-10-14 20:30:00 »

	Scénario: Le texte public applique le masquage, comme la page publique
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et l'événement « Continue » a pour nom public « Radio Machin », et masque ses sonores
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et un client lit la socket d'état
		Alors le texte public du sonore en cours est « Radio Machin »

	# ─── Prochain sonore ───────────────────────────────────────

	Scénario: Le prochain sonore est annoncé avec son début et sa fin estimés
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et un client lit la socket d'état
		Alors le prochain sonore est « f2 », sain
		Et il commencera au « 2026-10-14 19:59:51 », dure 1 seconde et finira au « 2026-10-14 19:59:52 »
		Et l'emplacement du prochain sonore est le fichier de « f2 »

	Scénario: Avec superposition, le prochain sonore commence au début du crossfade de fin
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore a 0,5 seconde de crossfade de début et de fin
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,2 seconde
		Et un client lit la socket d'état
		Alors le prochain sonore commencera au « 2026-10-14 19:59:50.500 » et finira au « 2026-10-14 19:59:51.500 »

	Plan du scénario: Une banque garde les crossfades de ses sonores, les applique à défaut, ou les impose
		https://github.com/dascritch/machincast/issues/143 : chaque côté, début et fin, a sa règle. « À défaut » ne
		vaut que pour un sonore dont le crossfade n'est pas paramétré : 0 seconde en est un (https://github.com/dascritch/machincast/issues/145).
		Deux sonores ne se superposent que si le sortant a un crossfade de fin et l'entrant un crossfade de début ; le
		prochain commence alors au début du crossfade de fin du sortant.

		Étant donné le fil musical permanent « Continue », avec la banque séquentielle « Titres » des sonores « f1 », « f2 »
		Et les crossfades de chaque sonore sont <sonores>
		Et la banque « Titres » <debut> seconde de crossfade de début
		Et la banque « Titres » <fin> seconde de crossfade de fin
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,2 seconde
		Et un client lit la socket d'état
		Alors le prochain sonore commencera au « <prochain> » et finira au « <fin_prochain> »

		Exemples:
			| sonores         | debut                                   | fin                                     | prochain                | fin_prochain            |
			| non paramétrés  | laisse ses sonores décider, malgré 0,25 | laisse ses sonores décider, malgré 0,25 | 2026-10-14 19:59:51     | 2026-10-14 19:59:52     |
			| de 0,5 seconde  | laisse ses sonores décider, malgré 0,25 | laisse ses sonores décider, malgré 0,25 | 2026-10-14 19:59:50.500 | 2026-10-14 19:59:51.500 |
			| non paramétrés  | applique à défaut 0,25                  | applique à défaut 0,25                  | 2026-10-14 19:59:50.750 | 2026-10-14 19:59:51.750 |
			| de 0 seconde    | applique à défaut 0,25                  | applique à défaut 0,25                  | 2026-10-14 19:59:51     | 2026-10-14 19:59:52     |
			| de 0,5 seconde  | applique à défaut 0,25                  | applique à défaut 0,25                  | 2026-10-14 19:59:50.500 | 2026-10-14 19:59:51.500 |
			| de 0,5 seconde  | impose 0,25                             | impose 0,25                             | 2026-10-14 19:59:50.750 | 2026-10-14 19:59:51.750 |
			| de 0,5 seconde  | impose 0                                | impose 0,25                             | 2026-10-14 19:59:51     | 2026-10-14 19:59:52     |
			| de 0,5 seconde  | impose 0,25                             | laisse ses sonores décider, malgré 0,25 | 2026-10-14 19:59:50.500 | 2026-10-14 19:59:51.500 |
			| de 0 seconde    | impose 0,25                             | laisse ses sonores décider, malgré 0,25 | 2026-10-14 19:59:51     | 2026-10-14 19:59:52     |

	Plan du scénario: Un sonore sans crossfade paramétré, que sa banque ne règle pas, prend celui de la configuration
		https://github.com/dascritch/machincast/issues/145 : « crossfades.debut » et « crossfades.fin » valent pour un sonore sans
		crossfade paramétré, qu'aucune banque n'impose ni n'applique à défaut.

		Étant donné le fil musical permanent « Continue », avec la banque séquentielle « Titres » des sonores « f1 », « f2 »
		Et les crossfades de chaque sonore sont <sonores>
		Et la banque « Titres » <banque> seconde de crossfade de début
		Et la banque « Titres » <banque> seconde de crossfade de fin
		Et les crossfades par défaut de la configuration sont <defauts>
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,2 seconde
		Et un client lit la socket d'état
		Alors le prochain sonore commencera au « <prochain> » et finira au « <fin_prochain> »

		Exemples:
			| sonores        | banque                                 | defauts                                       | prochain                | fin_prochain            |
			| non paramétrés | laisse ses sonores décider, malgré 0,5 | de 0,25 seconde au début et de 0,25 à la fin  | 2026-10-14 19:59:50.750 | 2026-10-14 19:59:51.750 |
			| de 0 seconde   | laisse ses sonores décider, malgré 0,5 | de 0,25 seconde au début et de 0,25 à la fin  | 2026-10-14 19:59:51     | 2026-10-14 19:59:52     |
			| non paramétrés | applique à défaut 0,5                  | de 0,25 seconde au début et de 0,25 à la fin  | 2026-10-14 19:59:50.500 | 2026-10-14 19:59:51.500 |
			| non paramétrés | laisse ses sonores décider, malgré 0,5 | de 0,25 seconde au début et de 0,5 à la fin   | 2026-10-14 19:59:50.500 | 2026-10-14 19:59:51.500 |
			| non paramétrés | laisse ses sonores décider, malgré 0,5 | de 0,25 seconde au début, et absent à la fin  | 2026-10-14 19:59:51     | 2026-10-14 19:59:52     |
			| non paramétrés | laisse ses sonores décider, malgré 0,5 | absent au début, et de 0,5 à la fin           | 2026-10-14 19:59:51     | 2026-10-14 19:59:52     |
			| non paramétrés | laisse ses sonores décider, malgré 0,5 | absents                                       | 2026-10-14 19:59:51     | 2026-10-14 19:59:52     |

	Scénario: Un sonore placé directement dans l'événement, sans crossfade paramétré, prend aussi celui de la configuration
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et les crossfades par défaut de la configuration sont de 0,25 seconde au début et de 0,25 à la fin
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,2 seconde
		Et un client lit la socket d'état
		Alors le prochain sonore commencera au « 2026-10-14 19:59:50.750 » et finira au « 2026-10-14 19:59:51.750 »

	Scénario: Un sonore placé directement dans l'événement garde ses crossfades, même dans une banque qui les impose
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et la banque « Titres », séquentielle, avec les sonores « f1 », « f2 »
		Et la banque « Titres » impose 0,25 seconde de crossfade de début
		Et la banque « Titres » impose 0,25 seconde de crossfade de fin
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,2 seconde
		Et un client lit la socket d'état
		Alors le prochain sonore commencera au « 2026-10-14 19:59:51 » et finira au « 2026-10-14 19:59:52 »

	Plan du scénario: Un prochain sonore n'est pas sain si son fichier pose problème
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et <probleme>
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,3 seconde
		Et un client lit la socket d'état
		Alors le prochain sonore est « f2 », pas sain

		Exemples:
			| probleme                                                |
			| le fichier du sonore « f2 » a été supprimé              |
			| la dernière lecture du sonore « f2 » a fini en incident |

	Scénario: Le prochain sonore d'un stream a un état sain inconnu
		Étant donné un serveur de flux local, avec le flux « studio » en ligne
		Et le stream « Direct studio » à l'adresse du flux « studio »
		Et le fil musical permanent « Continue », avec les sonores « f1 », « Direct studio »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,3 seconde
		Et un client lit la socket d'état
		Alors le prochain sonore est « Direct studio », à l'état sain inconnu

	# ─── Coupure par un événement à venir (https://github.com/dascritch/machincast/issues/169) ─────

	Scénario: Un événement qui commencera pendant le sonore en cours : la socket annonce la coupure et le sonore suivant
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et le sonore « f1 » dure 600 secondes en base
		Et l'émission « Journal » de 20:00:00 à 20:30:00, avec le sonore « j1 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et un client lit la socket d'état
		Alors le sonore en cours finira au « 2026-10-14 20:00:00 », coupé par l'événement « Journal »
		Et le prochain sonore est « j1 », sain
		Et il commencera au « 2026-10-14 20:00:00 », dure 1 seconde et finira au « 2026-10-14 20:00:01 »
		Et le prochain sonore est joué par l'événement « Journal »

	Plan du scénario: Un événement qui commencera après le sonore en cours, ou pendant son crossfade de fin, ne le coupe pas
		Le sonore suivant est demandé au début du crossfade de fin : c'est lui que l'événement coupera.

		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et le sonore « f1 » dure 600 secondes en base
		Et le sonore « f1 » a 20 seconde de crossfade de fin
		Et l'émission « Journal » de <debut> à 20:30:00, avec le sonore « j1 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et un client lit la socket d'état
		Alors le sonore en cours finira au « 2026-10-14 20:09:50 », sans être coupé
		Et le prochain sonore est « f2 », sain
		Et le prochain sonore est joué par l'événement « Continue »

		Exemples:
			| debut    |
			| 20:09:50 |
			| 20:09:40 |

	Scénario: Le premier changement de la grille qui ne coupe pas n'empêche pas de trouver le suivant, qui coupe
		Étant donné le fil musical permanent « Continue », avec les sonores « f2 »
		Et l'émission « Magazine » de 19:59:50 à 20:00:05, avec le sonore « f1 »
		Et le sonore « f1 » dure 600 secondes en base
		Et l'émission « Journal » de 20:01:00 à 20:30:00, avec le sonore « j1 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et un client lit la socket d'état
		Alors le sonore en cours finira au « 2026-10-14 20:01:00 », coupé par l'événement « Journal »

	Scénario: Un stream s'éteint à la fin de son événement : un événement qui commence ensuite ne le coupe pas
		Étant donné un serveur de flux local, avec le flux « studio » en ligne
		Et le stream « Direct studio » à l'adresse du flux « studio »
		Et l'émission « Direct » de 19:59:50 à 20:00:00, avec le sonore « Direct studio »
		Et le spécial « Flash » de 20:00:30 à 20:05:00, avec le sonore « j1 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1 seconde en temps réel
		Et un client lit la socket d'état
		Alors le sonore en cours n'a pas de fin estimée, sans être coupé

	Scénario: Un stream en cours, de durée inconnue, annonce aussi sa coupure
		Étant donné un serveur de flux local, avec le flux « studio » en ligne
		Et le stream « Direct studio » à l'adresse du flux « studio »
		Et l'émission « Direct » de 19:59:50 à 20:30:00, avec le sonore « Direct studio »
		Et le spécial « Flash » de 20:00:00 à 20:05:00, avec le sonore « j1 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1 seconde en temps réel
		Et un client lit la socket d'état
		Alors le sonore en cours finira au « 2026-10-14 20:00:00 », coupé par l'événement « Flash »
		Et le prochain sonore est « j1 », sain
		Et il commencera au « 2026-10-14 20:00:00 », dure 1 seconde et finira au « 2026-10-14 20:00:01 »

	Scénario: Le sonore annoncé après la coupure est celui qui est joué, même tiré au hasard
		Sept sonores : avec la graine des tests, les deux premiers tirages diffèrent, et un hasard que l'anticipation
		aurait fait avancer donnerait un autre sonore.

		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et le sonore « f1 » dure 600 secondes en base
		Et l'émission « Journal » de 20:00:00 à 20:30:00, avec la banque aléatoire « Rotation » des sonores « a », « b », « c », « d », « e », « g », « h »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Et un client lit la socket d'état
		Et l'horloge du binaire passe au « 2026-10-14 20:00:00 »
		Et la diffusion tourne 1 pas d'une seconde
		Alors le deuxième passage est le prochain sonore annoncé

	Scénario: Anticiper le sonore qui suivra la coupure ne laisse aucune trace dans le log
		Le saut d'une banque « ne pas répéter » est noté quand la coupure a lieu, pas quand elle est annoncée.

		Étant donné le fil musical permanent « Continue », avec la banque séquentielle « Titres » des sonores « f1 », « f2 »
		Et le sonore « f1 » dure 600 secondes en base
		Et la banque « Titres » est marquée « ne pas répéter »
		Et l'émission « Journal » de 20:00:00 à 20:30:00, qui joue la banque « Titres », puis le sonore « j1 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Et un client lit la socket d'état
		Alors le prochain sonore est « j1 », sain
		Et le log contient 0 info « élément sauté »
		Quand l'horloge du binaire passe au « 2026-10-14 20:00:00 »
		Et la diffusion tourne 1 pas d'une seconde
		Alors l'airplay montre les passages « f1 », « j1 »
		Et le log contient 1 info « élément sauté »

	# ─── Playlist immédiate (https://github.com/dascritch/machincast/issues/228) ─────

	Scénario: La socket annonce les cinq sonores qui suivront le prochain, avec leurs heures estimées
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 », « f4 », « f5 », « f6 », « f7 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et un client lit la socket d'état
		Alors la socket annonce les sonores à venir « f3 », « f4 », « f5 », « f6 », « f7 », sains
		Et le premier sonore à venir commencera au « 2026-10-14 19:59:52 » et finira au « 2026-10-14 19:59:53 »
		Et le dernier sonore à venir commencera au « 2026-10-14 19:59:56 » et finira au « 2026-10-14 19:59:57 »
		Et le premier sonore à venir vient de l'événement « Continue », permanent

	Scénario: Les sonores à venir se chevauchent comme le prochain, chacun pendant son crossfade
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et chaque sonore a 0,5 seconde de crossfade de début et de fin
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,1 seconde
		Et un client lit la socket d'état
		Alors le premier sonore à venir commencera au « 2026-10-14 19:59:51 » et finira au « 2026-10-14 19:59:52 »

	Scénario: Un sonore à venir qu'un événement coupera finit à la coupure, et le sonore de l'événement le suit
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et le sonore « f3 » dure 600 secondes en base
		Et l'émission « Journal » de 20:00:00 à 20:30:00, avec le sonore « j1 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et un client lit la socket d'état
		Alors la socket annonce les sonores à venir « f3 », « j1 », « j1 », « j1 », « j1 », sains
		Et le premier sonore à venir commencera au « 2026-10-14 19:59:52 » et finira au « 2026-10-14 20:00:00 »

	Scénario: Après un stream qui s'éteint à la fin de son événement, le suivant attend la fin de son fondu
		Étant donné un serveur de flux local, avec le flux « studio » en ligne
		Et le stream « Direct studio » à l'adresse du flux « studio »
		Et l'émission « Direct » de 19:59:50 à 20:00:00, avec le sonore « Direct studio »
		Et le sonore « Direct studio » a 3 seconde de crossfade de fin
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne pendant 1 seconde en temps réel
		Et un client lit la socket d'état
		Alors le prochain sonore commencera au « 2026-10-14 20:00:03 »

	Scénario: Rien à diffuser après le prochain : aucun sonore à venir
		Étant donné l'émission « Journal » de 19:59:50 à 19:59:51, avec le sonore « j1 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et un client lit la socket d'état
		Alors il n'y a aucun sonore à venir

	Scénario: Le sonore en cours dit la priorité de son événement
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,4 seconde
		Et un client lit la socket d'état
		Alors le sonore en cours est joué par un événement de priorité « fil_musical »

	# ─── Réservation ───────────────────────────────────────────

	Scénario: Le sonore réservé est celui qui est joué, même tiré au hasard
		Étant donné le fil musical permanent « Continue », avec la banque aléatoire « Rotation » des sonores « a », « b », « c », « d »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Et un client lit la socket d'état
		Et la diffusion tourne 1 pas d'une seconde
		Alors le deuxième passage est le prochain sonore annoncé

	Scénario: Un sonore réservé qui n'est plus jouable est remplacé
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Et le sonore « f2 » est désactivé
		Et la diffusion tourne 1 pas d'une seconde
		Alors l'airplay montre les passages « f1 », « f3 »

	Scénario: Le sonore réservé d'un événement terminé n'est pas joué
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et l'émission « Flash » de 19:59:50 à 19:59:51, avec le sonore « m »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 2 pas d'une seconde
		Alors l'airplay montre les passages « m », « f1 »

	# ─── Publication ───────────────────────────────────────────

	Scénario: Un client connecté reçoit chaque changement
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Quand la diffusion démarre au plus vite
		Et un client reste connecté à la socket d'état
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors le client a vu passer en cours « f1 », « f2 », « f1 »
		Et son dernier message est à l'état « arret »
		Et la socket d'état n'existe plus

	Scénario: Un client qui se déconnecte n'interrompt pas la diffusion
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Quand la diffusion démarre au plus vite
		Et un client se connecte puis se déconnecte aussitôt
		Et la diffusion tourne 3 pas d'une seconde
		Alors l'airplay montre les passages « f1 », « f1 », « f1 »

	Scénario: La socket d'état est réservée au compte qui diffuse
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Quand la diffusion démarre au plus vite
		Alors le répertoire de la socket d'état n'est accessible qu'à son propriétaire
		Et la socket d'état n'est lisible et modifiable que par son propriétaire

	Scénario: Un second Machin lecture est refusé tant que la socket d'état est occupée
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Quand la diffusion démarre au plus vite
		Alors une seconde diffusion sur la même socket d'état est refusée, car un autre Machin lecture diffuse déjà

	Scénario: Chaque champ du message est décrit dans la spécification
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Quand la diffusion démarre en temps réel
		Et la diffusion tourne 1 pas de 0,3 seconde
		Et un client lit la socket d'état
		Alors chaque champ du message figure dans la spécification, § 5.4
