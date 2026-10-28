# language: fr
Fonctionnalité: Raccourcis des onglets
	En tant que technicien d'antenne,
	je veux passer d'un onglet à l'autre au clavier,
	afin de revenir vite à l'accueil ou à une fiche ouverte.

	https://github.com/dascritch/machincast/issues/192. Les 12 premiers onglets ont les raccourcis Maj+F1 à Maj+F12,
	selon leur rang : Maj+F1 est toujours l'accueil, et ouvrir ou fermer un onglet décale les suivants. L'infobulle de
	chaque onglet donne son raccourci. Les touches s'écrivent ici en anglais, comme les lit Qt (Shift).

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et les événements :
			| nom         | nom_public | priorite    | debut | fin | jours |
			| Fil de jour |            | fil_musical |       |     |       |
		Et la séquence « Un », sans nom public, avec rien
		Et la séquence « Deux », sans nom public, avec rien
		Et la séquence « Trois », sans nom public, avec rien
		Et la séquence « Quatre », sans nom public, avec rien
		Et la séquence « Cinq », sans nom public, avec rien
		Et la séquence « Six », sans nom public, avec rien

	Scénario: Maj+F1 ramène à l'accueil, Maj+F2 au calendrier, Maj+F6 aux incidents
		Les onglets « Sonores » et « Feeds » ne s'ouvrent qu'à la demande
		(https://github.com/dascritch/machincast/issues/180), et le calendrier suit l'accueil
		(https://github.com/dascritch/machincast/issues/307) : au lancement, les incidents sont le sixième onglet.

		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et j'appuie sur « Shift+F1 »
		Alors l'onglet ouvert est « Accueil »
		Quand j'appuie sur « Shift+F2 »
		Alors l'onglet ouvert est « Calendrier »
		Quand j'appuie sur « Shift+F6 »
		Alors l'onglet ouvert est « Incidents »
		Et les onglets ont pour infobulles « Maj+F1 », « Maj+F2 », « Maj+F3 », « Maj+F4 », « Maj+F5 », « Maj+F6 »

	Scénario: Seuls les 12 premiers onglets ont un raccourci
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ouvre l'onglet « Feeds »
		Et j'ouvre la fiche de la séquence « Un »
		Et j'ouvre la fiche de la séquence « Deux »
		Et j'ouvre la fiche de la séquence « Trois »
		Et j'ouvre la fiche de la séquence « Quatre »
		Et j'ouvre la fiche de la séquence « Cinq »
		Et j'ouvre la fiche de la séquence « Six »
		Alors l'onglet « Séquence : Quatre » a pour infobulle « Maj+F12 »
		Et l'onglet « Séquence : Cinq » n'a pas d'infobulle
		Quand j'appuie sur « Shift+F1 »
		Et j'appuie sur « Shift+F12 »
		Alors l'onglet ouvert est « Séquence : Quatre »

	Scénario: Fermer un onglet décale les raccourcis des suivants
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Et j'ouvre la fiche de la séquence « Deux »
		Alors l'onglet « Séquence : Deux » a pour infobulle « Maj+F8 »
		Quand je ferme l'onglet « Séquence : Un »
		Alors l'onglet « Séquence : Deux » a pour infobulle « Maj+F7 »
		Quand j'appuie sur « Shift+F1 »
		Et j'appuie sur « Shift+F7 »
		Alors l'onglet ouvert est « Séquence : Deux »
		Quand j'appuie sur « Shift+F8 »
		Alors l'onglet ouvert est « Séquence : Deux »
