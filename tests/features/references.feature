# language: fr
Fonctionnalité: Liens vers les tickets et les PR
	En tant que développeur de MachinCast,
	je veux que toute référence à un ticket ou une PR soit un lien cliquable,
	afin d'y accéder directement.

	Scénario: Aucune référence nue à un ticket ou une PR dans le dépôt
		Étant donné les fichiers Markdown, Python, TOML, SQL, shell et Gherkin du dépôt
		Alors chaque référence à un ticket ou une PR est un lien vers GitHub

	Plan du scénario: Le détecteur distingue les références nues des liens
		Étant donné la ligne « <ligne> »
		Alors le détecteur y trouve <nombre> référence(s) nue(s)

		Exemples:
			| ligne                                                                  | nombre |
			| voir #51                                                               | 1      |
			| tests du wrapper (#6), lancement (#6)                                  | 2      |
			| voir [#51](https://github.com/dascritch/machincast/issues/51)          | 0      |
			| voir [PR #56](https://github.com/dascritch/machincast/pull/56)         | 0      |
			| décision : https://github.com/dascritch/machincast/issues/51           | 0      |
			| voir [§ 4.8](#48-métadonnées-publiques-et-masquage)                    | 0      |
			| couleur "1d76db" et ancre (#airplay)                                   | 0      |
			| couleur "#1d76db"                                                      | 0      |
			| # Titre Markdown                                                       | 0      |
