# language: fr
Fonctionnalité: Raccourcis des onglets
	En tant que technicien d'antenne,
	je veux passer d'un onglet à l'autre au clavier,
	afin de revenir vite à l'accueil ou à une fiche ouverte.

	https://github.com/dascritch/machincast/issues/192. Les 12 premiers onglets ont les raccourcis Maj+F1 à Maj+F12,
	selon leur rang : Maj+F1 est toujours l'accueil, et ouvrir ou fermer un onglet décale les suivants. L'infobulle de
	chaque onglet donne son raccourci. Les touches s'écrivent ici en anglais, comme les lit Qt (Shift, Ctrl, PgUp, PgDown).

	https://github.com/dascritch/machincast/issues/318 : Ctrl+PageUp et Ctrl+PageDown vont à l'onglet de gauche et de
	droite, sans boucler, Ctrl+Home au premier, l'accueil, et Ctrl+End au dernier, quel que soit le widget qui a le
	focus, champ de texte et tableau compris.

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

	# ─── Onglet précédent, suivant, premier et dernier (https://github.com/dascritch/machincast/issues/318) ───

	Scénario: Ctrl+PageUp et Ctrl+PageDown vont à l'onglet de gauche et de droite, sans boucler, même depuis un tableau
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je donne le focus au tableau de l'onglet « Banques »
		Et j'appuie sur « Ctrl+PgDown »
		Alors l'onglet ouvert est « Incidents »
		Quand j'appuie sur « Ctrl+PgDown »
		Alors l'onglet ouvert est « Incidents »
		Quand j'appuie sur « Ctrl+PgUp »
		Alors l'onglet ouvert est « Banques »
		Quand j'appuie sur « Shift+F1 »
		Et j'appuie sur « Ctrl+PgUp »
		Alors l'onglet ouvert est « Accueil »
		Quand j'appuie sur « Ctrl+PgDown »
		Alors l'onglet ouvert est « Calendrier »

	Scénario: Ctrl+End va au dernier onglet, Ctrl+Home à l'accueil, même depuis l'horloge de l'accueil ou un tableau
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Et j'appuie sur « Shift+F1 »
		Et je clique sur l'horloge de l'accueil
		Et j'appuie sur « Ctrl+End »
		Alors l'onglet ouvert est « Séquence : Un »
		Quand j'ouvre l'onglet « Banques »
		Et je donne le focus au tableau de l'onglet « Banques »
		Et j'appuie sur « Ctrl+Home »
		Alors l'onglet ouvert est « Accueil »

	Scénario: Dans un champ de texte, les quatre raccourcis changent aussi d'onglet
		Un champ d'une ligne réclame Ctrl+Home et Ctrl+End, sans rien en faire : le raccourci de la fenêtre les prend.

		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je saisis « jingles » dans le filtre de l'onglet « Banques », le curseur à la fin
		Et j'appuie sur « Ctrl+PgUp »
		Alors l'onglet ouvert est « Séquences »
		Quand j'ouvre l'onglet « Banques »
		Et je saisis « jingles » dans le filtre de l'onglet « Banques », le curseur à la fin
		Et j'appuie sur « Ctrl+PgDown »
		Alors l'onglet ouvert est « Incidents »
		Quand j'ouvre l'onglet « Banques »
		Et je saisis « jingles » dans le filtre de l'onglet « Banques », le curseur à la fin
		Et j'appuie sur « Ctrl+Home »
		Alors l'onglet ouvert est « Accueil »
		Quand j'ouvre l'onglet « Banques »
		Et je saisis « jingles » dans le filtre de l'onglet « Banques », le curseur à la fin
		Et j'appuie sur « Ctrl+End »
		Alors l'onglet ouvert est « Incidents »
