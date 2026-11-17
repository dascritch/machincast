# language: fr
Fonctionnalité: Raccourcis des onglets
	En tant que technicien d'antenne,
	je veux passer d'un onglet à l'autre au clavier,
	afin de revenir vite à l'onglet Antenne ou à une fiche ouverte.

	https://github.com/dascritch/machincast/issues/192. Les 12 premiers onglets ont les raccourcis Maj+F1 à Maj+F12,
	selon leur rang : Maj+F1 est toujours l'onglet Antenne, et ouvrir ou fermer un onglet décale les suivants. L'infobulle de
	chaque onglet donne son raccourci. Les touches s'écrivent ici en anglais, comme les lit Qt (Shift, Ctrl, PgUp, PgDown).

	https://github.com/dascritch/machincast/issues/318 : Ctrl+PageUp et Ctrl+PageDown vont à l'onglet de gauche et de
	droite, sans boucler, Ctrl+Home au premier, l'onglet Antenne, et Ctrl+End au dernier, quel que soit le widget qui a le
	focus, champ de texte et tableau compris.

	Un onglet s'ouvre à droite de l'onglet ouvert, une fiche à droite de sa liste, après celles déjà ouvertes depuis elle
	(https://github.com/dascritch/machincast/issues/405, movable_tabs.feature).

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et les événements :
			| name        | public_name | priority               | starts_at | ends_at | days |
			| Fil de jour |             | background_programming |           |         |      |
		Et la séquence « Un », sans nom public, avec rien
		Et la séquence « Deux », sans nom public, avec rien
		Et la séquence « Trois », sans nom public, avec rien
		Et la séquence « Quatre », sans nom public, avec rien
		Et la séquence « Cinq », sans nom public, avec rien
		Et la séquence « Six », sans nom public, avec rien

	Scénario: Maj+F1 ramène à l'onglet Antenne, Maj+F2 au calendrier, Maj+F6 aux incidents
		Les onglets « Sonores » et « Feeds » ne s'ouvrent qu'à la demande
		(https://github.com/dascritch/machincast/issues/180), et le calendrier suit l'onglet Antenne
		(https://github.com/dascritch/machincast/issues/307) : au lancement, les incidents sont le sixième onglet.

		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et j'appuie sur « Shift+F1 »
		Alors l'onglet ouvert est « Antenne »
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
		Alors l'onglet « Séquence : Six » a pour infobulle « Maj+F12 »
		Et l'onglet « Banques » n'a pas d'infobulle
		Quand j'appuie sur « Shift+F1 »
		Et j'appuie sur « Shift+F12 »
		Alors l'onglet ouvert est « Séquence : Six »

	Scénario: Fermer un onglet décale les raccourcis des suivants
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Et j'ouvre la fiche de la séquence « Deux »
		Alors l'onglet « Séquence : Deux » a pour infobulle « Maj+F6 »
		Quand je ferme l'onglet « Séquence : Un »
		Alors l'onglet « Séquence : Deux » a pour infobulle « Maj+F5 »
		Quand j'appuie sur « Shift+F1 »
		Et j'appuie sur « Shift+F5 »
		Alors l'onglet ouvert est « Séquence : Deux »
		Quand j'appuie sur « Shift+F6 »
		Alors l'onglet ouvert est « Banques »

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
		Alors l'onglet ouvert est « Antenne »
		Quand j'appuie sur « Ctrl+PgDown »
		Alors l'onglet ouvert est « Calendrier »

	Scénario: Ctrl+End va au dernier onglet, Ctrl+Home à l'onglet Antenne, même depuis l'horloge de l'onglet Antenne ou un tableau
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Et j'appuie sur « Shift+F1 »
		Et je clique sur l'horloge de l'onglet Antenne
		Et j'appuie sur « Ctrl+End »
		Alors l'onglet ouvert est « Incidents »
		Quand j'ouvre l'onglet « Banques »
		Et je donne le focus au tableau de l'onglet « Banques »
		Et j'appuie sur « Ctrl+Home »
		Alors l'onglet ouvert est « Antenne »

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
		Alors l'onglet ouvert est « Antenne »
		Quand j'ouvre l'onglet « Banques »
		Et je saisis « jingles » dans le filtre de l'onglet « Banques », le curseur à la fin
		Et j'appuie sur « Ctrl+End »
		Alors l'onglet ouvert est « Incidents »

	# ─── Fermer, enregistrer et rouvrir un onglet (https://github.com/dascritch/machincast/issues/428) ───

	Scénario: Ctrl+W ferme l'onglet ouvert, s'il se ferme
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Et j'appuie sur « Ctrl+W »
		Alors aucune question n'a été posée
		Et la fenêtre a les onglets « Antenne », « Calendrier », « Événements », « Séquences », « Banques », « Incidents »
		Quand j'appuie sur « Shift+F4 »
		Et j'appuie sur « Ctrl+W »
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Événements », « Séquences », « Banques », « Incidents »
		Et l'onglet ouvert est « Séquences »

	Scénario: Ctrl+W sur une fiche modifiée demande quoi faire de ses modifications
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Et je saisis le nom interne « Un bis »
		Et je réponds « Annuler » à la question de fermeture
		Et j'appuie sur « Ctrl+W »
		Alors la question de fermeture a nommé « Séquence : Un »
		Et l'onglet ouvert est « Séquence : Un »

	Scénario: Ctrl+W ferme aussi une liste ouverte à la demande, la recherche, la simulation ou l'airplay
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Feeds » dans le menu « Affichage »
		Et j'appuie sur « Ctrl+W »
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et j'appuie sur « Ctrl+W »
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Événements », « Séquences », « Banques », « Incidents »

	Scénario: Ctrl+S enregistre la fiche ouverte, qui reste ouverte
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Et je saisis le nom interne « Un bis »
		Et j'appuie sur « Ctrl+S »
		Alors l'onglet ouvert est « Séquence : Un bis »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs
		Et aucune question n'a été posée

	Plan du scénario: Ctrl+Entrée enregistre la fiche ouverte, puis la ferme
		Les deux touches Entrée, celle du clavier principal (Return) et celle du pavé numérique (Enter).

		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Et je saisis le nom interne « Un bis »
		Et j'appuie sur « <touches> »
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Événements », « Séquences », « Banques », « Incidents »
		Quand j'ouvre la fiche de la séquence « Un bis »
		Alors l'onglet ouvert est « Séquence : Un bis »

		Exemples:
			| touches     |
			| Ctrl+Return |
			| Ctrl+Enter  |

	Scénario: Ctrl+Entrée ferme une fiche sans modification, et une fiche refusée reste ouverte
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Et j'appuie sur « Ctrl+Return »
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Événements », « Séquences », « Banques », « Incidents »
		Quand j'ouvre la fiche de la séquence « Deux »
		Et je saisis le nom interne «  »
		Et j'appuie sur « Ctrl+Return »
		Alors l'onglet ouvert est « Séquence : Deux »
		Et la fiche signale « Le nom interne est obligatoire. »

	Scénario: Ctrl+S et Ctrl+Entrée ne font rien sur une fiche sans modification, ni sur un onglet qui ne s'enregistre pas
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Et j'appuie sur « Ctrl+S »
		Alors l'onglet ouvert est « Séquence : Un »
		Quand j'appuie sur « Shift+F1 »
		Et j'appuie sur « Ctrl+S »
		Et j'appuie sur « Ctrl+Return »
		Alors l'onglet ouvert est « Antenne »
		Et aucune question n'a été posée

	Scénario: Ctrl+Maj+T rouvre le dernier onglet fermé, puis celui d'avant
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Et j'ouvre l'onglet « Séquences »
		Et j'ouvre la fiche de la séquence « Deux »
		Et je ferme l'onglet « Séquence : Un »
		Et je ferme l'onglet « Séquence : Deux »
		Et j'appuie sur « Ctrl+Shift+T »
		Alors l'onglet ouvert est « Séquence : Deux »
		Quand j'appuie sur « Ctrl+Shift+T »
		Alors l'onglet ouvert est « Séquence : Un »
		Quand j'appuie sur « Ctrl+Shift+T »
		Alors l'onglet ouvert est « Séquence : Un »
		Et l'entrée « Rouvrir l'onglet fermé » du menu « Affichage » est inactive

	Scénario: Le sous-menu des onglets fermés propose les 5 derniers, le plus récent en tête
		Une fiche supprimée, ou pas encore enregistrée, ne se rouvre pas : elle n'y est pas.

		Quand la fenêtre de l'interface s'ouvre
		Alors le sous-menu « Onglets fermés récemment » du menu « Affichage » est inactif
		Quand j'ouvre la fiche de la séquence « Un »
		Et j'ouvre la fiche de la séquence « Deux »
		Et j'ouvre la fiche de la séquence « Trois »
		Et j'ouvre la fiche de la séquence « Quatre »
		Et j'ouvre la fiche de la séquence « Cinq »
		Et j'ouvre la fiche de la séquence « Six »
		Et je choisis « Ouvrir l'onglet Feeds » dans le menu « Affichage »
		Et je ferme l'onglet « Séquence : Un »
		Et je ferme l'onglet « Séquence : Deux »
		Et je ferme l'onglet « Séquence : Trois »
		Et je ferme l'onglet « Séquence : Quatre »
		Et je ferme l'onglet « Feeds »
		Et je ferme l'onglet « Séquence : Cinq »
		Alors le sous-menu « Onglets fermés récemment » du menu « Affichage » propose « Séquence : Cinq », « Feeds », « Séquence : Quatre », « Séquence : Trois », « Séquence : Deux »
		Quand je choisis « Feeds » dans le sous-menu « Onglets fermés récemment » du menu « Affichage »
		Alors l'onglet ouvert est « Feeds »
		Et le sous-menu « Onglets fermés récemment » du menu « Affichage » propose « Séquence : Cinq », « Séquence : Quatre », « Séquence : Trois », « Séquence : Deux »
