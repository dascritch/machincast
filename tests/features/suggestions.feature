# language: fr
Fonctionnalité: Suggestions au lancement de l'interface
	En tant que technicien radio,
	je veux qu'au lancement de l'interface graphique, celle-ci me suggère de créer quelques éléments,
	afin d'accélérer la mise en place de l'outil pour démarrer.

	https://github.com/dascritch/machincast/issues/119. Au lancement, si les suggestions sont actives
	(interface.suggestions) et qu'il manque un fil musical, l'une des banques suggérées, ou le périphérique de l'antenne
	sur une vraie sortie, une fenêtre modale propose de les créer : chaque élément manquant est une ligne à cocher,
	cochée par défaut. Elle remplace la création automatique du fil musical au lancement
	(https://github.com/dascritch/machincast/issues/39), qui reste quand les suggestions sont éteintes. Ici, la fenêtre
	des suggestions est remplacée par les réponses du scénario ; la vraie fenêtre s'ouvre à la fin, hors de l'écran.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 10:00:00 »
		Et les suggestions au lancement sont actives

	# ─── Ce qui est proposé ────────────────────────────────────

	Scénario: Sur une base vide, tout est proposé
		Étant donné les suggestions seront refermées par « Plus tard »
		Quand la fenêtre de l'interface s'ouvre
		Alors les suggestions ont proposé :
			| élément                          |
			| Fil musical                      |
			| Banque « Identifiant station »   |
			| Banque « Musique rotation lourde » |
			| Banque « Musique rotation normale » |
			| Banque « Musique rotation rare »   |
			| Banque « Musique rotation de nuit » |
			| Banque « Partenariats »             |
			| Banque « Publicités »               |
			| Banque « Bande-annonce émissions »  |
		Et les suggestions n'ont pas proposé de périphérique d'antenne
		Et il n'y a aucun événement en base
		Et il n'y a aucune banque en base

	Scénario: Ce qui existe déjà n'est pas proposé, sans tenir compte des majuscules
		Étant donné les événements :
			| nom  | nom_public | priorite    | debut | fin | jours |
			| Fond |            | fil_musical |       |     |       |
		Et la banque « identifiant STATION », séquentielle, sans nom public, avec rien
		Et la banque « Musique rotation lourde », séquentielle, sans nom public, avec rien
		Et les suggestions seront refermées par « Plus tard »
		Quand la fenêtre de l'interface s'ouvre
		Alors les suggestions ont proposé :
			| élément                          |
			| Banque « Musique rotation normale » |
			| Banque « Musique rotation rare »   |
			| Banque « Musique rotation de nuit » |
			| Banque « Partenariats »             |
			| Banque « Publicités »               |
			| Banque « Bande-annonce émissions »  |

	Scénario: Quand rien ne manque, aucune suggestion n'est faite
		Étant donné les événements :
			| nom  | nom_public | priorite    | debut | fin | jours |
			| Fond |            | fil_musical |       |     |       |
		Et les banques suggérées existent déjà
		Quand la fenêtre de l'interface s'ouvre
		Alors aucune suggestion n'a été faite

	Scénario: Suggestions éteintes, rien n'est proposé, et le fil musical est recréé comme avant
		Étant donné les suggestions au lancement sont éteintes dans le fichier de configuration
		Quand la fenêtre de l'interface s'ouvre
		Alors aucune suggestion n'a été faite
		Et la barre d'état annonce « Aucun fil musical : « Fil musical » est créé, permanent et sans élément ; sa liste se remplit dans sa fiche. »
		Et il n'y a aucune banque en base

	# ─── Création ──────────────────────────────────────────────

	Scénario: « Créer » crée ce qui est coché, et remplit le fil musical d'une rotation type
		https://github.com/dascritch/machincast/issues/231 : les musiques durent 15 minutes au plus ; l'identifiant
		station, les partenariats, les publicités et les bandes-annonces, 2 minutes, ces trois derniers séquentiels et
		enchaînés sans crossfade, imposé à 0 seconde à tous leurs sonores ; une bande-annonce ne passe jamais deux fois
		de suite.

		Étant donné les suggestions seront acceptées par « Créer », sans « Banque « Musique rotation rare » »
		Quand la fenêtre de l'interface s'ouvre
		Alors le fil musical « Fil musical » est en base, permanent
		Et la liste de l'événement « Fil musical » est en base « Identifiant station », « Musique rotation lourde », « Musique rotation normale », « Musique rotation lourde »
		Et les banques en base sont :
			| nom                      | mode       | ne pas répéter | durée maximale | crossfade de début | crossfade de fin |
			| Bande-annonce émissions  | sequentiel | oui            | 0:02:00        | imposé, 0 s        | imposé, 0 s      |
			| Identifiant station      | aleatoire  | oui            | 0:02:00        | des sonores        | des sonores      |
			| Musique rotation de nuit | aleatoire  | non            |                | des sonores        | des sonores      |
			| Musique rotation lourde  | aleatoire  | non            | 0:15:00        | des sonores        | des sonores      |
			| Musique rotation normale | aleatoire  | non            | 0:15:00        | des sonores        | des sonores      |
			| Partenariats             | sequentiel | non            | 0:02:00        | imposé, 0 s        | imposé, 0 s      |
			| Publicités               | sequentiel | non            | 0:02:00        | imposé, 0 s        | imposé, 0 s      |
		Et la barre d'état annonce « Créés : le fil musical « Fil musical », les banques « Identifiant station », « Musique rotation lourde », « Musique rotation normale », « Musique rotation de nuit », « Partenariats », « Publicités », « Bande-annonce émissions ». »

	Scénario: La rotation rare dure aussi 15 minutes au plus
		Étant donné les suggestions seront acceptées par « Créer »
		Quand la fenêtre de l'interface s'ouvre
		Alors la banque « Musique rotation rare » en base a pour durée maximale « 0:15:00 », sans durée minimale

	Scénario: Un fil musical existant, encore vide, reçoit la rotation type ; un fil déjà rempli est gardé tel quel
		Étant donné les événements :
			| nom  | nom_public | priorite    | debut | fin | jours |
			| Fond |            | fil_musical |       |     |       |
		Et les suggestions seront acceptées par « Créer »
		Quand la fenêtre de l'interface s'ouvre
		Alors la liste de l'événement « Fond » est en base « Identifiant station », « Musique rotation lourde », « Musique rotation normale », « Musique rotation lourde », « Musique rotation rare »
		Et les fils musicaux en base sont « Fond »

	Scénario: Sans fil musical créé, « Plus tard » ne crée rien, et la suggestion revient au lancement suivant
		Étant donné les suggestions seront refermées par « Plus tard »
		Quand la fenêtre de l'interface s'ouvre
		Alors il n'y a aucun événement en base
		Et le fichier de configuration n'a pas changé
		Quand je ferme la fenêtre de l'interface
		Et la fenêtre de l'interface s'ouvre
		Alors les suggestions ont été faites 2 fois

	Scénario: « Ne plus proposer au lancement » éteint les suggestions dans le fichier de configuration
		Étant donné les suggestions seront refermées par « Plus tard », en cochant « Ne plus proposer au lancement »
		Quand la fenêtre de l'interface s'ouvre
		Alors le fichier de configuration contient la ligne « suggestions = false »
		Et le fichier de configuration contient encore « # Configuration utilisée par les tests »

	# ─── Périphérique de l'antenne ─────────────────────────────

	Scénario: Sans périphérique d'antenne sur une vraie sortie, son choix est proposé, et s'enregistre
		Étant donné les périphériques audio du poste :
			| identifiant       | nom           |
			| carte-1           | Carte 1       |
			| preecoute-factice | Haut-parleurs |
		Et la configuration audio sortie « pipewire », sans périphérique d'antenne
		Et les banques suggérées existent déjà
		Et les événements :
			| nom  | nom_public | priorite    | debut | fin | jours |
			| Fond |            | fil_musical |       |     |       |
		Et les suggestions seront acceptées par « Créer », avec l'antenne « carte-1 »
		Quand la fenêtre de l'interface s'ouvre
		Alors les suggestions ont proposé les périphériques d'antenne « carte-1 »
		Et le fichier de configuration contient la ligne « peripherique = "carte-1" »
		Et la barre d'état annonce « Périphérique de l'antenne : carte-1 ; Machin lecture le prendra à son prochain démarrage. »
		Et la barre d'état ne signale pas « Périphérique de l'antenne à renseigner »

	# ─── Vraie fenêtre ─────────────────────────────────────────

	Scénario: La fenêtre des suggestions coche tout, propose l'antenne, et donne ce qui est coché
		Étant donné les périphériques audio du poste :
			| identifiant       | nom           |
			| carte-1           | Carte 1       |
			| casque-usb        | Casque USB    |
			| preecoute-factice | Haut-parleurs |
		Quand la fenêtre des suggestions s'ouvre sur le fil musical et la banque « Identifiant station », avec l'antenne à choisir sur « pipewire »
		Alors elle s'intitule « Pour bien démarrer »
		Et elle propose, cochés, « Fil musical », « Banque « Identifiant station » »
		Et son choix de l'antenne propose « Carte 1 », « Casque USB », sans la pré-écoute
		Quand j'y décoche « Fil musical »
		Et j'y choisis l'antenne « Casque USB »
		Et j'y coche « Ne plus proposer au lancement »
		Et j'y clique sur « Créer »
		Alors elle a donné : la banque « Identifiant station », l'antenne « casque-usb », ne plus proposer
