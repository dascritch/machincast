# language: fr
Fonctionnalité: Un plugin choisit l'événement qui joue une occurrence de la grille
	En tant que développeur d'un plugin,
	je veux qu'une occurrence de la grille puisse être jouée par un autre événement que le sien, choisi par le plugin,
	afin que l'antenne, le calendrier, l'intranet et l'affichage public jouent et montrent l'émission effectivement
	diffusée.

	https://github.com/dascritch/machincast/issues/608, ticket enfant de
	https://github.com/dascritch/machincast/issues/606. Chaque lecture de la grille (machincast.shared.grid.read_grid)
	demande aux plugins abonnés au point « grid.substitutions » leur Substitution : les événements qu'un événement fait
	jouer, hors grille, et celui qui joue chacune de ses occurrences. Ici, « Mercredi soir » fait jouer « Sonia » le
	premier mercredi du mois, « Les ahuris » les autres ; « Sonia » et « Les ahuris » ont aussi leurs propres dates.

	Contexte:
		Étant donné les événements de la grille :
			| nom           | priorité | début            | fin              | jours     |
			| Mercredi soir | show     | 2026-12-02 20:00 | 2026-12-02 21:00 | wednesday |
			| Sonia         | show     | 2026-11-30 10:00 | 2026-11-30 11:00 | monday    |
			| Les ahuris    | show     | 2026-12-01 10:00 | 2026-12-01 11:00 |           |
		Et le plugin « alternance » qui fait jouer « Mercredi soir » par « Sonia » le premier mercredi du mois, par « Les ahuris » sinon

	Scénario: L'occurrence est jouée par l'événement choisi, sur le créneau et avec la priorité de l'événement qui le fait jouer
		Quand la grille est lue
		Alors à « 2026-12-02 20:30 », l'événement actif est « Sonia », de « 2026-12-02 20:00 » à « 2026-12-02 21:00 », de priorité « show »
		Et à « 2026-12-09 20:30 », l'événement actif est « Les ahuris », de « 2026-12-09 20:00 » à « 2026-12-09 21:00 », de priorité « show »

	Scénario: Un événement qu'un autre fait jouer est hors grille : ses propres dates ne jouent pas
		Quand la grille est lue
		Alors à « 2026-12-07 10:30 », aucun événement n'est actif
		Et à « 2026-12-01 10:30 », aucun événement n'est actif
		Et la grille lue n'a que « Mercredi soir »

	Scénario: Le calendrier montre, chaque semaine, l'événement qui joue
		Quand la grille est lue
		Alors le calendrier du « 2026-11-30 » au « 2026-12-14 » montre « Sonia » le « 2026-12-02 20:00 », « Les ahuris » le « 2026-12-09 20:00 »

	Scénario: Sans choix du plugin, l'événement joue lui-même
		Étant donné le plugin « alternance » qui ne choisit rien
		Quand la grille est lue
		Alors à « 2026-12-02 20:30 », l'événement actif est « Mercredi soir », de « 2026-12-02 20:00 » à « 2026-12-02 21:00 », de priorité « show »
		Et à « 2026-12-07 10:30 », l'événement actif est « Sonia », de « 2026-12-07 10:00 » à « 2026-12-07 11:00 », de priorité « show »

	Scénario: Un plugin qui ne répond pas une Substitution est ignoré, et consigné
		Étant donné le plugin « bavard » qui répond « bonjour » au point « grid.substitutions »
		Quand la grille est lue
		Alors le journal dit « plugin « bavard » : une substitution de la grille est attendue »
		Et à « 2026-12-02 20:30 », l'événement actif est « Sonia », de « 2026-12-02 20:00 » à « 2026-12-02 21:00 », de priorité « show »

	Scénario: Le point « grid.substitutions » est un point du cœur, décrit
		Alors le point « grid.substitutions » est un point du cœur
