# language: fr
Fonctionnalité: Onglets déplaçables, ouverts à droite de leur onglet d'origine
	En tant que technicien d'antenne,
	je veux ranger les onglets à ma façon, et qu'un onglet s'ouvre à côté de celui d'où je l'ouvre,
	afin de garder ensemble ce sur quoi je travaille.

	https://github.com/dascritch/machincast/issues/405. Tout onglet se déplace à la souris, sauf l'onglet Antenne, qui
	reste le premier : Maj+F1 et Ctrl+Home y mènent toujours. Les raccourcis, les infobulles et le menu « Onglets »
	suivent le nouvel ordre. Un onglet s'ouvre directement à droite de l'onglet ouvert, celui d'où il est ouvert : une
	fiche à droite de sa liste, une liste à la demande ou la recherche à droite de l'onglet où l'on était. L'ordre, onglets
	fixes compris, est retenu d'un lancement à l'autre (retained_tabs.feature). Les scénarios déplacent un onglet comme le
	ferait la souris, par la barre des onglets.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et les événements :
			| name        | public_name | priority               | starts_at | ends_at | days |
			| Fil de jour |             | background_programming |           |         |      |
		Et la séquence « Un », sans nom public, avec rien

	Scénario: Un onglet déplacé change de raccourci
		Quand la fenêtre de l'interface s'ouvre
		Et je déplace l'onglet « Banques » à la place 2
		Alors la fenêtre a les onglets « Antenne », « Banques », « Calendrier », « Événements », « Séquences », « Incidents »
		Et l'onglet « Banques » a pour infobulle « Maj+F2 »
		Quand j'appuie sur « Shift+F2 »
		Alors l'onglet ouvert est « Banques »

	Scénario: L'onglet Antenne reste le premier
		Quand la fenêtre de l'interface s'ouvre
		Et je déplace l'onglet « Antenne » à la place 4
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Événements », « Séquences », « Banques », « Incidents »
		Quand je déplace l'onglet « Incidents » à la place 1
		Alors la fenêtre a les onglets « Antenne », « Incidents », « Calendrier », « Événements », « Séquences », « Banques »

	Scénario: Un onglet s'ouvre directement à droite de l'onglet ouvert
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Calendrier »
		Et je choisis « Rechercher… » dans le menu « Affichage »
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Recherche », « Événements », « Séquences », « Banques », « Incidents »
		Quand j'ouvre l'onglet « Banques »
		Et je choisis « Ouvrir l'onglet Sonores » dans le menu « Affichage »
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Recherche », « Événements », « Séquences », « Banques », « Sonores », « Incidents »

	Scénario: Une fiche s'ouvre directement à droite de sa liste
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Événements », « Séquences », « Séquence : Un », « Banques », « Incidents »

	Scénario: Un onglet déjà ouvert revient au premier plan sans changer de place
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Sonores » dans le menu « Affichage »
		Et j'ouvre l'onglet « Incidents »
		Et je choisis « Ouvrir l'onglet Sonores » dans le menu « Affichage »
		Alors l'onglet ouvert est « Sonores »
		Et la fenêtre a les onglets « Antenne », « Sonores », « Calendrier », « Événements », « Séquences », « Banques », « Incidents »

	Scénario: L'ordre des onglets déplacés, fixes compris, est retenu d'un lancement à l'autre
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Un »
		Et je déplace l'onglet « Incidents » à la place 2
		Et je déplace l'onglet « Calendrier » à la place 7
		Et je ferme la fenêtre de l'interface
		Et la fenêtre de l'interface s'ouvre
		Alors la fenêtre a les onglets « Antenne », « Incidents », « Événements », « Séquences », « Séquence : Un », « Banques », « Calendrier »

	Scénario: Les onglets se déplacent à la souris
		Quand la fenêtre de l'interface s'ouvre
		Alors les onglets sont déplaçables
