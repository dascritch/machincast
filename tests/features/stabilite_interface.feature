# language: fr
Fonctionnalité: L'interface reste réactive et libère ce qu'elle ferme
	En tant qu'équipe de l'antenne,
	je veux que l'interface reste réactive et stable à l'usage, même après une session verrouillée ou des écrans en veille,
	afin que les VU-mètres ne saccadent pas et que l'interface ne tombe pas.

	https://github.com/dascritch/machincast/issues/305. Une fiche qui s'ouvre se lit une seule fois : passer au
	premier plan ne la relit pas aussitôt. Une fiche fermée est libérée, avec ses lignes, même nombreuses. La base se
	lit par l'implémentation compilée de psycopg, bien plus rapide que l'implémentation en Python pour les fiches de
	milliers de lignes. La liste des périphériques audio garde un seul moniteur, jamais arrêté
	(peripheriques_liste.feature).

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-28 12:00:00 »
		Et la banque « Grosse », de 3000 sonores

	Scénario: Une fiche qui s'ouvre ne lit son élément qu'une fois
		Étant donné que les lectures des fiches de banque sont comptées
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Grosse »
		Alors la fiche de la banque a été lue 1 fois
		Et la fiche montre 3000 sonores
		Quand j'ouvre l'onglet « Accueil »
		Et j'ouvre l'onglet « Banque : Grosse »
		Alors la fiche de la banque a été lue 2 fois

	Scénario: Une fiche fermée est libérée, avec ses lignes
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre puis ferme 3 fois la fiche de la banque « Grosse »
		Alors aucune des fiches fermées ne survit

	Scénario: La base se lit par l'implémentation compilée de psycopg
		Alors psycopg n'utilise pas son implémentation en Python
