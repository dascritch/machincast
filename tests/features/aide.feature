# language: fr
Fonctionnalité: Aide des exécutables
	En tant que technicien d'antenne,
	je veux que chaque exécutable de MachinCast affiche son aide,
	afin de savoir comment l'utiliser.

	Plan du scénario: Un exécutable affiche son aide
		Quand je lance "<executable>" avec l'option "--help"
		Alors la commande se termine sans erreur
		Et la sortie mentionne "<executable>"

		Exemples:
			| executable        |
			| Machin_lecture    |
			| Machin_indexation |
			| Machin_interface  |
			| Machin_purge      |

	Plan du scénario: Un exécutable affiche sa version
		Quand je lance "<executable>" avec l'option "--version"
		Alors la commande se termine sans erreur
		Et la sortie mentionne la version de MachinCast

		Exemples:
			| executable        |
			| Machin_lecture    |
			| Machin_indexation |
			| Machin_interface  |
			| Machin_purge      |
