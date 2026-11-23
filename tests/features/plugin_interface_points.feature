# language: fr
Fonctionnalité: Les points d'extension des fiches et des menus de l'interface
	En tant que développeur d'un plugin,
	je veux m'accrocher aux fiches et aux menus de l'interface,
	afin d'y ajouter des champs, des vérifications et des actions
	(https://github.com/dascritch/machincast/issues/591, ticket enfant de https://github.com/dascritch/machincast/issues/348).

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 15:30:42 »
		Et les sonores :
			| type | location   | artist | title  | state  | duration |
			| file | jingle.mp3 | Radio  | Jingle | active | 5        |
		Et la banque « Habillage », séquentielle, sans nom public, avec « Jingle »

	Scénario: Un plugin ajoute sa section à la fiche d'une banque, au-dessus de ses boutons, enregistrée avec elle
		Étant donné le plugin « remarque », qui ajoute sa section à la fiche d'une banque
		Et la banque « Habillage » a pour propriétés « {"remarque": "à trier"} »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Habillage »
		Alors la fiche a la section du plugin « remarque », au-dessus de ses boutons, qui montre « à trier »
		Et la fiche n'est pas modifiée
		Quand je saisis « triée » dans la section du plugin « remarque »
		Alors la fiche est modifiée
		Quand j'enregistre la fiche
		Alors la banque « Habillage » a pour propriétés « {"remarque": "triée"} »

	Scénario: Un plugin est prévenu de la lecture et de l'enregistrement d'une fiche, sans être attendu
		Étant donné un plugin abonné à « interface.load_bank » et à « interface.save_bank »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Habillage »
		Alors le plugin a été prévenu de « interface.load_bank » pour la banque « Habillage »
		Quand je saisis le nom interne « Habillage du soir »
		Et j'enregistre la fiche
		Alors le plugin a été prévenu de « interface.save_bank » pour la banque « Habillage du soir », avec sa ligne

	Scénario: Un plugin vérifie une fiche avant son enregistrement, et la refuse avec sa raison
		Étant donné un plugin qui refuse, à « interface.presave_bank », un nom interne sans majuscule : « Le nom commence par une majuscule. »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Habillage »
		Et je saisis le nom interne « habillage »
		Et j'enregistre la fiche
		Alors la fiche signale « Le nom commence par une majuscule. »
		Et la banque « Habillage » est toujours en base sous ce nom
		Quand je saisis le nom interne « Habillage bis »
		Et j'enregistre la fiche
		Alors la banque « Habillage bis » est en base

	Scénario: Un plugin ajoute son menu à la barre de menus, avant « Aide »
		Étant donné un plugin qui ajoute le menu « Outils de la radio » à la barre de menus
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre de menus a les menus « Fichier », « Affichage », « Onglets », « Tableau », « Diffusion », « Plugins », « Maintenance », « Outils de la radio », « Aide »

	Scénario: Un plugin ajoute son entrée au clic droit sur une ligne d'une liste
		Étant donné un plugin qui ajoute l'entrée « Exporter » au clic droit sur une ligne
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Exporter » au clic droit sur la ligne « Habillage » de l'onglet « Banques »
		Alors le plugin a exporté la banque « Habillage »
