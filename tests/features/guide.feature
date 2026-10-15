# language: fr
Fonctionnalité: Guide d'utilisation des fonctions livrées
	En tant qu'utilisateur ou administrateur de MachinCast,
	je veux un guide d'utilisation de ce qui est déjà livré, écrit pour les humains,
	afin de m'en servir sans lire la spécification ni le code.

	Le guide est doc/utilisation.md (https://github.com/dascritch/machincast/issues/74). Ces scénarios vérifient
	qu'il couvre ce que les programmes exposent : un ajout au code sans documentation les fait échouer.

	Scénario: README.md et INSTALL.md mènent au guide d'utilisation
		Alors README.md contient un lien vers doc/utilisation.md
		Et INSTALL.md contient un lien vers doc/utilisation.md

	Scénario: Le wrapper est entièrement documenté
		Alors chaque binaire du wrapper est documenté dans le guide
		Et chaque option du wrapper est documentée dans le guide
		Et la commande « Machin logs » est documentée dans le guide

	Plan du scénario: Chaque option d'un binaire est documentée
		Alors chaque option de l'aide de « <executable> » est documentée dans le guide

		Exemples:
			| executable        |
			| Machin_lecture    |
			| Machin_indexation |
			| Machin_interface  |

	Scénario: Les états des sonores et les verdicts de la vérification sont documentés
		Alors chaque état d'un sonore est documenté dans le guide
		Et chaque verdict de la vérification d'un fichier est documenté dans le guide

	Scénario: Les métadonnées lues dans les tags sont documentées
		Alors chaque clé de métadonnées musicales tenue par l'indexeur est documentée dans le guide

	Scénario: Les liens relatifs et les ancres du guide mènent quelque part
		Alors chaque lien relatif du guide mène à un fichier du dépôt
		Et chaque ancre citée par le guide mène à un titre du fichier visé
