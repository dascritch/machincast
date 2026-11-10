# language: fr
Fonctionnalité: Interruption manuelle de l'antenne
	En tant que responsable d'antenne,
	je veux sauter au sonore suivant, sauter après la séquence en cours, ou couper l'événement par le fil musical,
	afin de corriger l'antenne sans attendre.

	https://github.com/dascritch/machincast/issues/104 et https://github.com/dascritch/machincast/issues/228,
	spec § 4.9. L'interface envoie la demande sur la socket d'état ; Machin player la traite à son pas suivant. Le
	sonore en cours s'éteint aussitôt pendant le crossfade de fin par défaut de la configuration, ou s'arrête net
	sans lui, et le suivant monte pendant le crossfade de début par défaut ; son passage se termine sans incident :
	c'est une opération normale. Le log note « interruption manuelle », avec ce qui est interrompu. Les sonores des
	scénarios durent une minute, sur un moteur simulé qui suit l'horloge du binaire.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 20:00:00 »

	# ─── Sonore ────────────────────────────────────────────────

	Scénario: Sauter au sonore suivant passe au prochain sonore annoncé
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je saute au sonore suivant
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre :
			| sonore | début    | fin      | sans incident |
			| f1     | 20:00:00 | 20:00:10 | oui           |
			| f2     | 20:00:10 | 20:00:15 | oui           |
		Et le log note l'interruption manuelle « du sonore « f1 » »

	Scénario: Le sonore sauté s'éteint pendant le crossfade de fin par défaut, sous le suivant qui monte
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Et les crossfades par défaut de la configuration sont de 2 seconde au début et de 3 à la fin
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je saute au sonore suivant
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre :
			| sonore | début    | fin      | sans incident |
			| f1     | 20:00:00 | 20:00:13 | oui           |
			| f2     | 20:00:10 | 20:00:15 | oui           |
		Et le sonore « f2 » a démarré avec une montée de 2 secondes

	Scénario: Sans crossfade par défaut, le sonore sauté est coupé net, même avec ses propres crossfades
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Et chaque sonore a 5 seconde de crossfade de début et de fin
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je saute au sonore suivant
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre :
			| sonore | début    | fin      | sans incident |
			| f1     | 20:00:00 | 20:00:10 | oui           |
			| f2     | 20:00:10 | 20:00:15 | oui           |
		Et le sonore « f2 » a démarré sans montée

	Scénario: Sauter un sonore d'une séquence passe à l'élément suivant de la séquence
		Étant donné la séquence « Pub » des sonores « p1 », « p2 », jouée par le fil musical permanent « Continue », avant le sonore « f »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je saute au sonore suivant
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « p1 », « p2 »

	# ─── Séquence ──────────────────────────────────────────────

	Scénario: Sauter après la séquence passe au sonore prévu après elle
		Étant donné la séquence « Pub » des sonores « p1 », « p2 », jouée par le fil musical permanent « Continue », avant le sonore « f »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je saute après la séquence
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « p1 », « f »
		Et le log note l'interruption manuelle « de la séquence « Pub », dans « Continue » »

	Scénario: Sauter après la séquence garde les sonores à venir qui la suivent
		Étant donné le fil musical permanent « Continue » joue les séquences « Pub » des sonores « p1 », « p2 », « p3 », puis « Jingles » des sonores « j1 », « j2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Alors les sonores à venir sont « p3 », « j1 », « j2 », « p1 », « p2 »
		Quand la diffusion avance de 9 secondes
		Et je saute après la séquence
		Alors l'airplay montre les passages « p1 », « j1 »
		Et le prochain sonore réservé est « j2 »
		Et les sonores à venir sont « p1 », « p2 », « p3 », « j1 », « j2 »

	Scénario: Le sonore prévu après la séquence passe, même tiré au hasard
		Étant donné le fil musical permanent « Continue » joue la séquence « Pub » des sonores « p1 », « p2 », puis la banque aléatoire « Rotation » des sonores « a », « b », « c », « d », « e », « g », « h », « i »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 1 seconde
		Et je note les sonores annoncés
		Et la diffusion avance de 9 secondes
		Et je saute après la séquence
		Alors le passage n°2 est le sonore noté n°2
		Et le prochain sonore et les sonores à venir reprennent les sonores notés à partir du n°3

	Scénario: Hors d'une séquence, sauter après la séquence ne fait rien
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je saute après la séquence
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 »
		Et le log ne note aucune interruption manuelle
		Et le journal du binaire a signalé « interruption manuelle ignorée : aucune séquence à l'antenne »

	# ─── Événement ─────────────────────────────────────────────

	Scénario: Couper une émission par le fil musical rend aussitôt l'antenne au fil musical
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Flash » de 20:00:00 à 20:30:00, avec le sonore « m »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je coupe l'événement par le fil musical
		Et la diffusion avance de 120 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « m », « f1 », « f2 »
		Et le log note l'interruption manuelle « de l'événement « Flash » »

	Scénario: Couper un spécial par le fil musical saute aussi l'émission qu'il recouvre
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Journal » de 20:00:00 à 20:30:00, avec le sonore « j »
		Et le spécial « Flash » de 20:00:00 à 20:10:00, avec le sonore « s »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je coupe l'événement par le fil musical
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « s », « f1 »

	Scénario: Dans le fil musical, couper l'événement par le fil musical ne fait rien
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je coupe l'événement par le fil musical
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 »
		Et le log ne note aucune interruption manuelle
		Et le journal du binaire a signalé « interruption manuelle ignorée : le fil musical est déjà à l'antenne »

	# ─── Couper par le secours ou par un feed (https://github.com/dascritch/machincast/issues/323) ───
	# Comme pour le fil musical, chaque événement au-dessus du fil musical est terminé ; le secours, ou le stream qui
	# suit le feed, tient l'antenne jusqu'à la fin prévue de l'événement coupé, ou, sous le fil musical, jusqu'au
	# début de l'événement suivant. Le log note l'interruption manuelle, avec ce qui est coupé et par quoi.

	Scénario: Couper une émission par le secours le fait jouer jusqu'à la fin prévue de l'émission
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Flash » de 20:00:00 à 20:02:00, avec le sonore « m »
		Et l'événement de secours « Secours », avec les sonores « s1 », « s2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je coupe l'antenne par le secours « Secours »
		Et la diffusion avance de 150 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre :
			| sonore | début    | fin      | sans incident |
			| m      | 20:00:00 | 20:00:10 | oui           |
			| s1     | 20:00:10 | 20:01:10 | oui           |
			| s2     | 20:01:10 | 20:02:10 | oui           |
			| f1     | 20:02:10 | 20:02:40 | oui           |
		Et le log note l'interruption manuelle « de l'événement « Flash » par le secours « Secours » »

	Scénario: Sous le fil musical, le secours tient l'antenne jusqu'à l'événement suivant
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Journal » de 20:01:30 à 20:30:00, avec le sonore « j »
		Et l'événement de secours « Secours », avec les sonores « s1 », « s2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je coupe l'antenne par le secours « Secours »
		Et la diffusion avance de 120 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre :
			| sonore | début    | fin      | sans incident |
			| f1     | 20:00:00 | 20:00:10 | oui           |
			| s1     | 20:00:10 | 20:01:10 | oui           |
			| s2     | 20:01:10 | 20:01:30 | oui           |
			| j      | 20:01:30 | 20:02:10 | oui           |
		Et le log note l'interruption manuelle « du fil musical « Continue » par le secours « Secours » »

	Scénario: Un secours sans rien de jouable rend l'antenne à la grille : le fil musical, l'émission coupée ne revient pas
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Flash » de 20:00:00 à 20:30:00, avec le sonore « m »
		Et l'événement de secours « Secours », avec les sonores « s1 »
		Et le sonore « s1 » est à l'état « disabled »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je coupe l'antenne par le secours « Secours »
		Et la diffusion avance de 20 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « m », « f1 »

	Scénario: Un événement qui n'est pas un secours ne coupe rien
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Flash » de 20:00:00 à 20:30:00, avec le sonore « m »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je coupe l'antenne par le secours « Flash »
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « m »
		Et le log ne note aucune interruption manuelle
		Et le journal du binaire a signalé « n'est pas un secours »

	Scénario: Couper une émission par un feed fait passer le stream qui le suit, jusqu'à la fin prévue de l'émission
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Flash » de 20:00:00 à 20:02:00, avec le sonore « m »
		Et chaque sonore dure 60 secondes
		Et le stream « Relais » sur le feed « Studio mobile », à une adresse factice
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je coupe l'antenne par le feed « Studio mobile »
		Et la diffusion avance de 130 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre :
			| sonore | début    | fin      | sans incident |
			| m      | 20:00:00 | 20:00:10 | oui           |
			| Relais | 20:00:10 | 20:02:00 | oui           |
			| f1     | 20:02:01 | 20:02:20 | oui           |
		Et le passage « Relais » est au nom de l'événement « Flash », sans élément de liste
		Et le log note l'interruption manuelle « de l'événement « Flash » par le feed « Studio mobile » »

	Scénario: Un feed qu'aucun stream actif ne suit ne coupe rien
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Et le stream « Relais » sur le feed « Studio mobile », à une adresse factice
		Et le sonore « Relais » est à l'état « disabled »
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je coupe l'antenne par le feed « Studio mobile »
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 »
		Et le log ne note aucune interruption manuelle
		Et le journal du binaire a signalé « aucun stream actif ne suit le feed « Studio mobile » »

	Scénario: Une demande de coupure par le secours arrive par la socket d'état
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'événement de secours « Secours », avec les sonores « s1 »
		Et chaque sonore dure 60 secondes
		Et la socket d'état dans un répertoire temporaire
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et un client de la socket d'état demande de couper l'antenne par le secours « Secours »
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « s1 »
		Et le log note l'interruption manuelle « du fil musical « Continue » par le secours « Secours » »

	# ─── Avancer l'événement suivant (https://github.com/dascritch/machincast/issues/257) ───
	# L'événement suivant, la première occurrence à venir qui prendra l'antenne, commence aussitôt, au-dessus de tout,
	# jusqu'à sa fin prévue : à son début prévu, rien ne change. La demande nomme l'événement attendu, celui que
	# Machin player a annoncé ; un autre événement suivant, depuis, la fait ignorer.

	Scénario: Avancer l'événement suivant le met aussitôt à l'antenne, jusqu'à sa fin prévue
		Une émission qui a une fin boucle sa liste jusqu'à elle.

		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et l'émission « Journal » de 20:30:00 à 20:45:00, avec les sonores « j1 », « j2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et j'avance l'événement suivant « Journal »
		Et la diffusion avance de 130 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre :
			| sonore | début    | fin      | sans incident |
			| f1     | 20:00:00 | 20:00:10 | oui           |
			| j1     | 20:00:10 | 20:01:10 | oui           |
			| j2     | 20:01:10 | 20:02:10 | oui           |
			| j1     | 20:02:10 | 20:02:20 | oui           |
		Et le log note l'avance « de l'événement « Journal », prévu le 14/10/2026 à 20:30 »

	Scénario: À son début prévu, l'événement avancé continue, sans coupure
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Journal » de 20:01:00 à 20:30:00, avec les sonores « j1 », « j2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 30 secondes
		Et j'avance l'événement suivant « Journal »
		Et la diffusion avance de 100 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre :
			| sonore | début    | fin      | sans incident |
			| f1     | 20:00:00 | 20:00:30 | oui           |
			| j1     | 20:00:30 | 20:01:30 | oui           |
			| j2     | 20:01:30 | 20:02:10 | oui           |

	Scénario: Un spécial en cours cède aussi la place à l'événement avancé
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et le spécial « Flash » de 20:00:00 à 20:20:00, avec les sonores « s1 », « s2 »
		Et l'émission « Journal » de 20:30:00 à 20:45:00, avec le sonore « j »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et j'avance l'événement suivant « Journal »
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « s1 », « j »

	Scénario: Une séquence en cours ne continue pas après l'avance
		Étant donné la séquence « Pub » des sonores « p1 », « p2 », jouée par le fil musical permanent « Continue », avant le sonore « f »
		Et l'émission « Journal » de 20:30:00 à 20:45:00, avec le sonore « j »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et j'avance l'événement suivant « Journal »
		Et la diffusion avance de 70 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « p1 », « j », « j »

	Scénario: Sans événement suivant, avancer ne fait rien
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et j'avance l'événement suivant « Journal »
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 »
		Et le log ne note aucune avance
		Et le journal du binaire a signalé « avance ignorée : aucun événement suivant »

	Scénario: Un autre événement suivant que celui demandé fait ignorer l'avance
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Journal » de 20:30:00 à 20:45:00, avec le sonore « j »
		Et l'émission « Concert » de 21:00:00 à 22:00:00, avec le sonore « c »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et j'avance l'événement suivant « Concert »
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 »
		Et le log ne note aucune avance
		Et le journal du binaire a signalé « avance ignorée : l'événement suivant est « Journal », pas « Concert » »

	Scénario: Machin player annonce l'événement suivant, puis le suivant une fois avancé
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Journal » de 20:30:00 à 20:45:00, avec le sonore « j »
		Et l'émission « Concert » de 21:00:00 à 22:00:00, avec le sonore « c »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 2 secondes
		Alors Machin player annonce l'événement suivant « Journal », du « 2026-10-14T20:30:00 » au « 2026-10-14T20:45:00 »
		Quand j'avance l'événement suivant « Journal »
		Et la diffusion avance de 2 secondes
		Alors Machin player annonce l'événement suivant « Concert », du « 2026-10-14T21:00:00 » au « 2026-10-14T22:00:00 »

	Scénario: Une demande d'avance arrive par la socket d'état
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Journal » de 20:30:00 à 20:45:00, avec le sonore « j »
		Et chaque sonore dure 60 secondes
		Et la socket d'état dans un répertoire temporaire
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et un client de la socket d'état demande d'avancer l'événement « Journal »
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « j »

	# ─── Revenir au début (https://github.com/dascritch/machincast/issues/366) ───
	# Pour un début d'émission raté : le sonore en cours, ou l'événement à l'antenne, repart de son début, dans un
	# nouveau passage, avec les crossfades par défaut, comme un saut.

	Scénario: Revenir au début du sonore le rejoue aussitôt, dans un nouveau passage
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je reviens au début du sonore
		Et la diffusion avance de 70 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre :
			| sonore | début    | fin      | sans incident |
			| f1     | 20:00:00 | 20:00:10 | oui           |
			| f1     | 20:00:10 | 20:01:10 | oui           |
			| f2     | 20:01:10 | 20:01:20 | oui           |
		Et le log note l'interruption manuelle « retour au début du sonore « f1 » »

	Scénario: Le sonore repris s'éteint pendant le crossfade de fin par défaut, sous son nouveau passage qui monte
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Et les crossfades par défaut de la configuration sont de 2 seconde au début et de 3 à la fin
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je reviens au début du sonore
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre :
			| sonore | début    | fin      | sans incident |
			| f1     | 20:00:00 | 20:00:13 | oui           |
			| f1     | 20:00:10 | 20:00:15 | oui           |

	Scénario: Revenir au début d'un sonore d'une séquence garde la séquence, qui continue après lui
		Étant donné la séquence « Pub » des sonores « p1 », « p2 », jouée par le fil musical permanent « Continue », avant le sonore « f »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et je reviens au début du sonore
		Et la diffusion avance de 70 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « p1 », « p1 », « p2 »

	Scénario: Recommencer une émission rejoue sa liste depuis son premier élément
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Matinale » de 20:00:00 à 20:30:00, avec les sonores « m1 », « m2 », « m3 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 70 secondes
		Et je recommence l'événement
		Et la diffusion avance de 70 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « m1 », « m2 », « m1 », « m2 »
		Et le log note l'interruption manuelle « retour au début de l'événement « Matinale » »

	Scénario: Recommencer le fil musical reprend sa liste à son premier élément
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 70 secondes
		Et je recommence l'événement
		Et la diffusion avance de 70 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « f2 », « f1 », « f2 »

	Scénario: Recommencer l'événement abandonne la séquence en cours, et rejoue la liste depuis son début
		Étant donné la séquence « Pub » des sonores « p1 », « p2 », jouée par le fil musical permanent « Continue », avant le sonore « f »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 70 secondes
		Et je recommence l'événement
		Et la diffusion avance de 70 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « p1 », « p2 », « p1 », « p2 »

	Scénario: Recommencer l'événement qui prête son nom lui rend l'antenne, depuis le début de sa liste
		https://github.com/dascritch/machincast/issues/399 : l'émission prête son nom au fil musical à la fin de sa
		liste ; recommencée, elle cesse de le prêter et rejoue sa liste, puis le prête de nouveau.

		Étant donné le fil musical permanent « Continue », avec les sonores « f »
		Et l'émission « Matinale » de 20:00:00 à 20:30:00, avec le sonore « g »
		Et l'événement « Matinale » prête, à la fin de sa liste, son nom au fil musical
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 70 secondes
		Et je recommence l'événement
		Et la diffusion avance de 70 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « g », « f », « g », « f »
		Et le log note l'interruption manuelle « retour au début de l'événement « Matinale » »

	Scénario: Une demande de retour au début arrive par la socket d'état
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Et la socket d'état dans un répertoire temporaire
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et un client de la socket d'état demande « {"command": "interrupt", "item": "restart_sound"} »
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « f1 »

	# ─── Rien à interrompre ────────────────────────────────────

	Scénario: Pendant un blanc, une interruption ne fait rien
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et le sonore « f1 » est à l'état « disabled »
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 5 secondes
		Et je saute au sonore suivant
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay ne montre aucun passage
		Et le log ne note aucune interruption manuelle
		Et le journal du binaire a signalé « interruption manuelle ignorée : rien à l'antenne »

	Scénario: Pendant un blanc, recommencer l'événement ne fait rien
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et le sonore « f1 » est à l'état « disabled »
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 5 secondes
		Et je recommence l'événement
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay ne montre aucun passage
		Et le journal du binaire a signalé « interruption manuelle ignorée : rien à l'antenne »

	# ─── Socket d'état ─────────────────────────────────────────

	Scénario: Une demande d'interruption arrive par la socket d'état
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Et la socket d'état dans un répertoire temporaire
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et un client de la socket d'état demande « {"command": "interrupt", "item": "sound"} »
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « f2 »
		Et le log note l'interruption manuelle « du sonore « f1 » »

	Plan du scénario: Une demande illisible ou inconnue est ignorée, et signalée dans le journal du binaire
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Et la socket d'état dans un répertoire temporaire
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et un client de la socket d'état demande « <demande> »
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 »
		Et le journal du binaire a signalé « demande ignorée sur la socket d'état »

		Exemples:
			| demande                                          |
			| pas du JSON                                      |
			| {"command": "stop"}                          |
			| {"command": "stop", "item": "sound"}     |
			| {"command": "interrupt", "item": "bank"} |
			| [1, 2]                                           |
			| {"command": "reread_grid", "item": "x"} |
			| {"command": "advance"}                          |
			| {"command": "advance", "event": "Journal"}  |
			| {"command": "advance", "event": true}       |
