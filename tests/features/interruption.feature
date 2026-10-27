# language: fr
Fonctionnalité: Interruption manuelle de l'antenne
	En tant que responsable d'antenne,
	je veux sauter au sonore suivant, sauter après la séquence en cours, ou couper l'événement par le fil musical,
	afin de corriger l'antenne sans attendre.

	https://github.com/dascritch/machincast/issues/104 et https://github.com/dascritch/machincast/issues/228,
	spec § 4.9. L'interface envoie la demande sur la socket d'état ; Machin lecture la traite à son pas suivant. Le
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

	# ─── Rien à interrompre ────────────────────────────────────

	Scénario: Pendant un silence, une interruption ne fait rien
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et le sonore « f1 » est à l'état « desactive »
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 5 secondes
		Et je saute au sonore suivant
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay ne montre aucun passage
		Et le log ne note aucune interruption manuelle
		Et le journal du binaire a signalé « interruption manuelle ignorée : rien à l'antenne »

	# ─── Socket d'état ─────────────────────────────────────────

	Scénario: Une demande d'interruption arrive par la socket d'état
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Et la socket d'état dans un répertoire temporaire
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et un client de la socket d'état demande « {"commande": "interrompre", "element": "sonore"} »
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
			| {"commande": "arreter"}                          |
			| {"commande": "arreter", "element": "sonore"}     |
			| {"commande": "interrompre", "element": "banque"} |
			| [1, 2]                                           |
			| {"commande": "relire_la_grille", "element": "x"} |
