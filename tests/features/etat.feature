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
