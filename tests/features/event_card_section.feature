# language: fr
Fonctionnalité: Un plugin ajoute sa section à la fiche d'un événement
	En tant que développeur d'un plugin,
	je veux ajouter ma section à la fiche d'un événement dans Machin interface, enregistrée avec elle, et pouvoir y
	remplacer sa liste, afin de régler ce que mon plugin ajoute à un événement là où on règle l'événement.

	https://github.com/dascritch/machincast/issues/611, ticket enfant de
	https://github.com/dascritch/machincast/issues/606. À l'ouverture de la fiche, Machin interface demande aux plugins
	abonnés au point « interface.event_card » leur section, une machincast.interface.event_card.CardSection. Ici, le
	plugin « note » range une note dans les propriétés de l'événement, sous son nom, et remplace la liste de
	l'événement quand sa case « Sans liste » est cochée.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 15:30:42 »
		Et les événements :
			| name     | public_name | priority | starts_at        | ends_at          | days |
			| Journal  |             | show     | 2026-10-21 09:00 | 2026-10-21 09:30 |      |
		Et l'événement « Journal » a pour propriétés « {"note": {"text": "à relire"}} »
		Et le plugin « note », qui ajoute sa section à la fiche d'un événement

	Scénario: La section du plugin s'ajoute à la fiche, et lit les propriétés de l'événement
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Journal »
		Alors la fiche de l'événement a la section du plugin « note », qui montre « à relire »
		Et la fiche de l'événement montre sa liste
		Et la fiche n'est pas modifiée

	Scénario: Un changement dans la section modifie la fiche, et s'enregistre avec elle, sans toucher aux autres propriétés
		Étant donné l'événement « Journal » a pour propriétés « {"note": {"text": "à relire"}, "autre": 1} »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Journal »
		Et je saisis « relu » dans la section du plugin « note »
		Alors la fiche est modifiée
		Quand j'enregistre la fiche
		Alors l'événement « Journal » a pour propriétés « {"note": {"text": "relu"}, "autre": 1} »

	Scénario: La section peut remplacer la liste de l'événement
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Journal »
		Et je coche « Sans liste » dans la section du plugin « note »
		Alors la fiche de l'événement ne montre plus sa liste

	Scénario: La section peut placer sa case sous les jours de la récurrence
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Journal »
		Alors la case « Sans liste » du plugin « note » est sous les jours de la récurrence, au-dessus de l'explication des dates

	Scénario: La section peut refuser l'enregistrement, et la fiche le dit, sans rien écrire
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Journal »
		Et je saisis « » dans la section du plugin « note »
		Et j'enregistre la fiche
		Alors la fiche signale « Une note est demandée. »
		Et l'événement « Journal » a pour propriétés « {"note": {"text": "à relire"}} »

	Scénario: Le point « interface.event_card » est un point du cœur, décrit
		Alors le point « interface.event_card » est un point du cœur, qui mène à la CardSection
