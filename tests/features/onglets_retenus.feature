# language: fr
Fonctionnalité: Onglets ouverts retenus d'un lancement à l'autre
	En tant que technicien d'antenne,
	je veux retrouver les onglets que j'avais ouverts en relançant l'interface,
	afin de reprendre mon travail là où je l'avais laissé.

	https://github.com/dascritch/machincast/issues/321. À la fermeture, l'interface retient, dans les réglages des vues
	du compte, les onglets ouverts dans leur ordre, fiches comprises, et l'onglet actif. Au lancement, elle les rouvre.
	Une fiche dont l'élément n'est plus en base, ou est supprimé, est oubliée sans question ; une nouvelle fiche, jamais
	enregistrée, n'est pas retenue.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et les événements :
			| nom         | nom_public | priorite    | debut | fin | jours |
			| Fil de jour |            | fil_musical |       |     |       |
		Et les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement                  |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/jingles/hiver/cafe.flac |
			| Aube        | Matin clair   | fichier | actif | 200   | /srv/jingles/hiver/matin.flac |
		Et la banque « Jingles », séquentielle, sans nom public, avec « Café à minuit »

	Scénario: Les onglets ouverts, fiches comprises, se rouvrent dans leur ordre, avec l'onglet actif
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Feeds » dans le menu « Affichage »
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et j'ouvre la fiche de la banque « Jingles »
		Et je choisis « Rechercher… » dans le menu « Affichage »
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et j'ouvre l'onglet « Banque : Jingles »
		Et je ferme la fenêtre de l'interface
		Et la fenêtre de l'interface s'ouvre
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Événements », « Séquences », « Banques », « Sonores », « Feeds », « Incidents », « Sonore : Café à minuit », « Airplay », « Banque : Jingles », « Recherche », « Simulation »
		Et l'onglet ouvert est « Banque : Jingles »

	Scénario: Sans onglet ajouté, la fenêtre se rouvre comme au premier lancement, sur l'onglet actif
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Incidents »
		Et je ferme la fenêtre de l'interface
		Et la fenêtre de l'interface s'ouvre
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Événements », « Séquences », « Banques », « Incidents »
		Et l'onglet ouvert est « Incidents »

	Scénario: Une fiche dont l'élément a été supprimé, ou effacé de la base, est oubliée sans question
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et j'ouvre la fiche du sonore « Matin clair »
		Et j'ouvre la fiche de la banque « Jingles »
		Et je ferme la fenêtre de l'interface
		Et le sonore « Café à minuit » est supprimé en base, depuis un autre poste
		Et la banque « Jingles » est effacée de la base
		Et la fenêtre de l'interface s'ouvre
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Événements », « Séquences », « Banques », « Sonores », « Incidents », « Sonore : Matin clair »
		Et l'onglet ouvert est « Antenne »
		Et aucune question n'a été posée

	Scénario: Une nouvelle fiche, jamais enregistrée, n'est pas retenue
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je clique sur « Nouvelle banque »
		Et je ferme la fenêtre de l'interface
		Et la fenêtre de l'interface s'ouvre
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Événements », « Séquences », « Banques », « Incidents »
		Et l'onglet ouvert est « Antenne »
