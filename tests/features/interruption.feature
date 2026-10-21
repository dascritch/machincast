# language: fr
Fonctionnalité: Interruption manuelle de l'antenne
	En tant que responsable d'antenne,
	je veux interrompre le sonore, la séquence ou l'événement en cours,
	afin de passer au suivant.

	https://github.com/dascritch/machincast/issues/104, spec § 4.9. L'interface envoie la demande sur la socket
	d'état ; Machin lecture la traite à son pas suivant. Le sonore en cours s'éteint pendant son crossfade de fin,
	ou s'arrête net sans crossfade, et son passage se termine sans incident : c'est une opération normale. Le log
	note « interruption manuelle », avec ce qui est interrompu. Les sonores des scénarios durent une minute, sur un
	moteur simulé qui suit l'horloge du binaire.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 20:00:00 »

	# ─── Sonore ────────────────────────────────────────────────

	Scénario: Interrompre le sonore passe au suivant de la liste
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et j'interromps le sonore
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre :
			| sonore | début    | fin      | sans incident |
			| f1     | 20:00:00 | 20:00:10 | oui           |
			| f2     | 20:00:10 | 20:00:15 | oui           |
		Et le log note l'interruption manuelle « du sonore « f1 » »

	Scénario: Le sonore interrompu s'éteint pendant son crossfade de fin, sous le suivant
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Et chaque sonore a 2 seconde de crossfade de début et de fin
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et j'interromps le sonore
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre :
			| sonore | début    | fin      | sans incident |
			| f1     | 20:00:00 | 20:00:12 | oui           |
			| f2     | 20:00:10 | 20:00:15 | oui           |

	Scénario: Interrompre un sonore d'une séquence passe à l'élément suivant de la séquence
		Étant donné la séquence « Pub » des sonores « p1 », « p2 », jouée par le fil musical permanent « Continue », avant le sonore « f »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et j'interromps le sonore
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « p1 », « p2 »

	# ─── Séquence ──────────────────────────────────────────────

	Scénario: Interrompre la séquence passe à l'élément qui la suit
		Étant donné la séquence « Pub » des sonores « p1 », « p2 », jouée par le fil musical permanent « Continue », avant le sonore « f »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et j'interromps la séquence
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « p1 », « f »
		Et le log note l'interruption manuelle « de la séquence « Pub », dans « Continue » »

	Scénario: Hors d'une séquence, interrompre la séquence ne fait rien
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et j'interromps la séquence
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 »
		Et le log ne note aucune interruption manuelle
		Et le journal du binaire a signalé « interruption manuelle ignorée : aucune séquence à l'antenne »

	# ─── Événement ─────────────────────────────────────────────

	Scénario: Interrompre une émission rend l'antenne à l'événement de priorité inférieure jusqu'à sa fin prévue
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et l'émission « Flash » de 20:00:00 à 20:30:00, avec le sonore « m »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et j'interromps l'événement
		Et la diffusion avance de 120 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « m », « f1 », « f2 »
		Et le log note l'interruption manuelle « de l'événement « Flash » »

	Scénario: Interrompre le fil musical pendant une séquence la quitte, et le fil reprend au début de sa liste
		Étant donné la séquence « Pub » des sonores « p1 », « p2 », jouée par le fil musical permanent « Continue », avant le sonore « f »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 10 secondes
		Et j'interromps l'événement
		Et la diffusion avance de 5 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « p1 », « p1 »

	Scénario: Interrompre le fil musical arrête son élément, et le fait reprendre au début de sa liste
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et chaque sonore dure 60 secondes
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 70 secondes
		Et j'interromps l'événement
		Et la diffusion avance de 65 secondes
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « f2 », « f1 », « f2 »
		Et le log note l'interruption manuelle « de l'événement « Continue » »

	# ─── Rien à interrompre ────────────────────────────────────

	Scénario: Pendant un silence, une interruption ne fait rien
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et le sonore « f1 » est à l'état « desactive »
		Quand la diffusion démarre sur un moteur simulé
		Et la diffusion avance de 5 secondes
		Et j'interromps le sonore
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
			| demande                                             |
			| pas du JSON                                         |
			| {"commande": "arreter"}                             |
			| {"commande": "arreter", "element": "sonore"}        |
			| {"commande": "interrompre", "element": "banque"}    |
			| [1, 2]                                              |
