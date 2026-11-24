# language: fr
Fonctionnalité: La couleur d'un événement, qu'un plugin donne au calendrier et à l'airplay
	En tant que développeur d'un plugin,
	je veux un point d'extension qui donne la couleur d'un événement,
	afin de colorer le calendrier de l'interface, celui de l'intranet et les tableaux d'airplay.

	https://github.com/dascritch/machincast/issues/635, pour le plugin de https://github.com/dascritch/machincast/issues/628.
	Le point du cœur « grid.event_colour » est demandé avec « event », l'identifiant de l'événement, ou rien pour une
	priorité, et « priority », ou rien quand l'appelant ne la connaît pas. Le plugin des scénarios, « palette », répond
	la couleur de la table « couleurs » ; rien pour le reste.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et les événements :
			| name     | public_name | priority | starts_at        | ends_at          | days   |
			| Débat    |             | show     | 2026-11-23 18:00 | 2026-11-23 19:00 | monday |
			| Comptine |             | show     | 2026-11-23 09:00 | 2026-11-23 10:00 | monday |

	Scénario: Sans plugin, l'événement garde la couleur de sa priorité
		Alors la couleur de « Débat » est celle de la priorité « show » du cœur
		Et la cellule de l'événement « Débat » d'un tableau d'airplay n'a pas de trait

	Scénario: Le plugin colore un événement, et une priorité
		Étant donné le plugin « palette » qui colore :
			| quoi     | couleur |
			| Débat    | #202060 |
			| show     | #8fd19e |
		Alors la couleur de « Débat » est « #202060 »
		Et la couleur de « Comptine » est « #8fd19e »
		Et la case « Émissions » du calendrier montre « #8fd19e », sans nom de couleur dans son infobulle
		Et la cellule de l'événement « Débat » d'un tableau d'airplay a un trait « #202060 »
		Et la cellule de l'événement « Comptine » d'un tableau d'airplay n'a pas de trait

	Scénario: Une réponse qui n'est pas une couleur « #rrggbb » est ignorée
		Étant donné le plugin « palette » qui colore :
			| quoi  | couleur |
			| Débat | rouge   |
		Alors la couleur de « Débat » est celle de la priorité « show » du cœur

	Plan du scénario: Le texte passe du noir au blanc selon la couleur du fond, pour un contraste suffisant
		Alors sur « <fond> », le texte est « <texte> »

		Exemples:
			| fond    | texte   |
			| #8fd19e | #000000 |
			| #f08c8c | #000000 |
			| #202060 | #ffffff |
			| #4a4a4a | #ffffff |

	Scénario: Dans le calendrier de l'interface, le nom d'un bloc coloré se lit en blanc sur un moment sombre à l'antenne
		Étant donné le plugin « palette » qui colore :
			| quoi  | couleur |
			| Débat | #202060 |
		Alors le nom du bloc « Débat », à l'antenne, s'écrit en « #ffffff »
		Et le nom du bloc « Débat », estompé, s'écrit en « #000000 »

	Scénario: L'intranet donne la couleur dans son JSON, et la met dans les attributs de sa grille
		Étant donné le plugin « palette » qui colore :
			| quoi  | couleur |
			| Débat | #202060 |
		Alors le calendrier de l'intranet du 23/11/2026 donne à « Débat » la couleur « #202060 », et à « Comptine » aucune
		Et la grille de l'intranet du 23/11/2026 dessine « Débat » en « #202060 », sur un fond « #bcbccf », cadré de « #161643 »
		Et la grille de l'intranet du 23/11/2026 dessine « Comptine » aux couleurs de sa priorité, par la feuille de style
