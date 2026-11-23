# language: fr
Fonctionnalité: Validation au pupitre des connexions à distance, et sessions des comptes
	En tant que membre de l'équipe au studio,
	je veux voir chaque connexion à distance à valider, avec le code à donner, et les sessions de chaque compte,
	afin de laisser entrer qui j'attends, de refuser les autres, et de couper une session à tout moment.

	https://github.com/dascritch/machincast/issues/539, ticket enfant de
	https://github.com/dascritch/machincast/issues/524. Au-dessus des onglets, un bandeau montre chaque connexion à
	valider : le compte, l'adresse IP source, le navigateur, l'heure limite et le code à 6 chiffres à donner ; il se
	relit toutes les 3 secondes. Dans l'onglet « API », le compte choisi montre ses sessions.

	Contexte:
		Étant donné l'horloge de l'interface au « 2026-11-20 10:00:00 »
		Et les comptes de l'intranet :
			| nom   | mot de passe    | rôle      | état  |
			| regie | tisane-au-micro | consulter | actif |

	Scénario: Sans connexion à valider, pas de bandeau
		Quand la fenêtre de l'interface s'ouvre
		Et le bandeau des connexions à distance se relit
		Alors le bandeau des connexions à distance est caché

	Scénario: Une connexion demandée montre qui la demande, d'où et avec quel navigateur, mais pas encore son code
		https://github.com/dascritch/machincast/issues/547 : le pupitre accepte la connexion avant d'en donner le code.
		Étant donné une connexion à valider de « regie », depuis « 10.0.0.31 », navigateur « Firefox/140 », code « 042917 »
		Quand la fenêtre de l'interface s'ouvre
		Et le bandeau des connexions à distance se relit
		Alors le bandeau des connexions à distance montre 1 connexion demandée, qui nomme « regie », « 10.0.0.31 » et « Firefox/140 », sans code
		Et le bandeau propose d'accepter et de refuser la connexion

	Scénario: Accepter une connexion montre le code à donner
		Étant donné une connexion à valider de « regie », depuis « 10.0.0.31 », navigateur « Firefox/140 », code « 042917 »
		Quand la fenêtre de l'interface s'ouvre
		Et le bandeau des connexions à distance se relit
		Et j'accepte la connexion à distance
		Alors le bandeau des connexions à distance montre 1 connexion, qui nomme « regie », « 10.0.0.31 », « Firefox/140 » et le code « 042 917 »
		Et le bandeau ne propose plus que de refuser la connexion
		Et la dernière session de « regie » est acceptée au pupitre
		Et la barre d'état annonce « Connexion à distance de regie acceptée : donnez-lui son code. »

	Scénario: Sans code, accepter une connexion la laisse entrer d'elle-même
		https://github.com/dascritch/machincast/issues/600 : la première connexion réglée « au pupitre », sans code.
		Étant donné une connexion à valider de « regie », depuis « 10.0.0.31 », navigateur « Firefox/140 », sans code
		Quand la fenêtre de l'interface s'ouvre
		Et le bandeau des connexions à distance se relit
		Alors le bandeau des connexions à distance montre 1 connexion demandée, qui nomme « regie », « 10.0.0.31 » et « Firefox/140 », et dit « Acceptez-la pour la laisser entrer. »
		Quand j'accepte la connexion à distance
		Alors le bandeau des connexions à distance montre 1 connexion demandée, qui nomme « regie », et dit « Acceptée : elle entre d'elle-même dans quelques secondes. »
		Et le bandeau ne propose plus que de refuser la connexion
		Et la barre d'état annonce « Connexion à distance de regie acceptée : elle entre d'elle-même. »

	Scénario: Une connexion qui a reçu des codes faux le dit au pupitre
		https://github.com/dascritch/machincast/issues/547 : peut-être quelqu'un qui essaie de deviner le code.
		Étant donné une connexion à valider de « regie », depuis « 10.0.0.31 », navigateur « Firefox/140 », code « 042917 »
		Et la connexion à valider de « regie » est acceptée au pupitre
		Et la connexion à valider de « regie » a déjà reçu 3 codes faux
		Quand la fenêtre de l'interface s'ouvre
		Et le bandeau des connexions à distance se relit
		Alors le bandeau des connexions à distance montre 1 connexion, qui nomme « regie » et « 3 codes faux déjà saisis » et le code « 042 917 »

	Scénario: Refuser une connexion la rend invalide, et le bandeau disparaît
		Étant donné une connexion à valider de « regie », depuis « 10.0.0.31 », navigateur « Firefox/140 », code « 042917 »
		Quand la fenêtre de l'interface s'ouvre
		Et le bandeau des connexions à distance se relit
		Et je refuse la connexion à distance
		Alors le bandeau des connexions à distance est caché
		Et la dernière session de « regie » est invalide
		Et la barre d'état annonce « Connexion à distance de regie refusée. »

	Scénario: Une connexion dont le délai est passé ne se montre plus
		Étant donné une connexion à valider de « regie », depuis « 10.0.0.31 », navigateur « Firefox/140 », code « 042917 », délai passé
		Quand la fenêtre de l'interface s'ouvre
		Et le bandeau des connexions à distance se relit
		Alors le bandeau des connexions à distance est caché
		Et la dernière session de « regie » est invalide

	Scénario: L'onglet « API » montre les sessions du compte choisi, et en invalide une
		Étant donné une connexion à valider de « regie », depuis « 10.0.0.31 », navigateur « Firefox/140 », code « 042917 »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet API » dans le menu « Affichage »
		Et je choisis le compte « regie » dans l'onglet API
		Alors les sessions de l'onglet API sont :
			| état      | origine  | adresse   | navigateur  |
			| à valider | intranet | 10.0.0.31 | Firefox/140 |
		Quand je choisis la première session de l'onglet API
		Et je clique sur « Invalider la session »
		Alors les sessions de l'onglet API sont :
			| état     | origine  | adresse   | navigateur  |
			| invalide | intranet | 10.0.0.31 | Firefox/140 |
		Et « Invalider la session » est grisé
		Et la barre d'état annonce « Session de regie invalidée. »

	Scénario: Une session générée au pupitre, pour l'API, montre son jeton une seule fois
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet API » dans le menu « Affichage »
		Et je choisis le compte « regie » dans l'onglet API
		Et je clique sur « ➕ Nouvelle session API… »
		Alors un jeton a été montré pour « regie »
		Et la base garde de ce jeton son empreinte seulement, en session valide de « regie », générée au pupitre, pour 12 heures
		Et les sessions de l'onglet API sont :
			| état   | origine | adresse | navigateur |
			| valide | pupitre |         |            |
		Et la barre d'état annonce « Session API de regie créée, valable 12 heures. »
