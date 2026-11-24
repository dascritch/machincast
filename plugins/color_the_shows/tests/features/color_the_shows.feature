# language: fr
Fonctionnalité: Les couleurs des émissions, par genre, dans les calendriers et les tableaux d'airplay
	En tant que responsable d'antenne,
	je veux colorer les émissions selon leur genre, talk, jazz, metal, reggae…,
	afin de lire d'un coup d'œil le calendrier interne, celui de l'intranet et les tableaux d'airplay.

	https://github.com/dascritch/machincast/issues/628, par le point du cœur « grid.event_colour »
	(https://github.com/dascritch/machincast/issues/635). Un événement a un genre au plus, rangé dans sa colonne
	properties, sous la clé « color_the_shows » ; sans genre, il prend la couleur de sa priorité. Les genres et les
	couleurs se règlent dans la fenêtre du plugin, menu « Plugins » de Machin interface.

	Contexte:
		Étant donné les tables du plugin des couleurs des émissions
		Et les événements :
			| nom         | priorité               |
			| Jazz à FIP  | show                   |
			| Le débat    | show                   |
			| Nuit blanche | special                |
			| Musiques    | background_programming |
			| Imprévu     | breaking               |
			| Panne       | fallback               |

	# ─── Les valeurs par défaut ────────────────────────────

	Scénario: À l'installation, quatre genres, et gris, vert et rouge pour le fil antenne, les émissions et les spéciales
		Alors les genres sont :
			| nom    | couleur |
			| jazz   | #5b8def |
			| metal  | #3d3d3d |
			| reggae | #e07b39 |
			| talk   | #f2c14e |
		Et les couleurs des priorités sont :
			| priorité               | couleur |
			| background_programming | #b4b4b4 |
			| show                   | #8fd19e |
			| special                | #f08c8c |

	# ─── La palette ────────────────────────────────────────

	Scénario: Un événement prend la couleur de son genre, sinon celle de sa priorité
		Étant donné le genre « jazz » de « Jazz à FIP »
		Et le plugin des couleurs des émissions, chargé dans « Machin_interface »
		Alors la couleur de « Jazz à FIP » est « #5b8def »
		Et la couleur de « Le débat » est « #8fd19e »
		Et la couleur de « Nuit blanche » est « #f08c8c »
		Et la couleur de « Musiques » est « #b4b4b4 »
		Et « Imprévu » et « Panne » gardent la couleur du cœur
		Et le bloc de « Jazz à FIP » du calendrier est « #5b8def », son nom en noir à l'antenne

	Scénario: Dans un tableau d'airplay, seul un événement qui a un genre a un trait
		Étant donné le genre « reggae » de « Jazz à FIP »
		Et le plugin des couleurs des émissions, chargé dans « Machin_interface »
		Alors sans sa priorité, la couleur de « Jazz à FIP » est « #e07b39 »
		Et sans sa priorité, « Le débat » n'a pas de couleur

	Scénario: La palette répond de mémoire, et relit la base après 30 secondes ou un enregistrement
		Étant donné une palette lue
		Quand le genre « jazz » est donné à « Le débat », directement en base
		Alors la palette donne encore « #8fd19e » à « Le débat »
		Quand 30 secondes passent
		Alors la palette donne « #5b8def » à « Le débat »
		Quand le genre « talk » est donné à « Le débat », directement en base
		Et la palette apprend un enregistrement
		Alors la palette donne « #f2c14e » à « Le débat »

	Scénario: Une base injoignable laisse la palette telle qu'elle était
		Étant donné une palette lue
		Quand la base devient injoignable et que 30 secondes passent
		Alors la palette donne encore « #8fd19e » à « Le débat »

	Plan du scénario: Le plugin s'abonne aux points du binaire qui le charge
		Quand le plugin des couleurs des émissions s'enregistre dans « <binaire> »
		Alors il s'abonne seulement à <points>

		Exemples:
			| binaire          | points                                                                         |
			| Machin_interface | « grid.event_colour », « interface.event_card », « interface.plugin_window » |
			| Machin_intranet  | « grid.event_colour »                                                          |
			| Machin_player    | aucun point                                                                    |

	# ─── La section de la fiche ────────────────────────────

	Scénario: La section de la fiche propose aucun genre, puis les genres par nom, chacun avec sa couleur
		Quand la section « Genre » de « Jazz à FIP » s'ouvre
		Alors elle propose « aucun genre », « jazz », « metal », « reggae », « talk »
		Et elle montre « aucun genre »
		Et « jazz » a un carré « #5b8def »

	Scénario: Choisir un genre le range dans les propriétés de l'événement, sans toucher aux autres clés
		Étant donné les propriétés de « Jazz à FIP » : {"alternation": {"mode": "monthly"}}
		Quand la section « Genre » de « Jazz à FIP » s'ouvre
		Et je choisis le genre « jazz »
		Alors la fiche est modifiée
		Quand la section s'enregistre
		Alors les propriétés de « Jazz à FIP » ont « alternation », et le genre « jazz »

	Scénario: Choisir « aucun genre » retire la clé du plugin
		Étant donné le genre « jazz » de « Jazz à FIP »
		Quand la section « Genre » de « Jazz à FIP » s'ouvre
		Alors elle montre « jazz »
		Quand je choisis le genre « aucun genre »
		Et la section s'enregistre
		Alors les propriétés de « Jazz à FIP » sont {}

	Scénario: Le genre enregistré par la fiche fait relire la palette
		Étant donné le plugin des couleurs des émissions, chargé dans « Machin_interface »
		Et la couleur de « Le débat » est « #8fd19e »
		Quand la section « Genre » de « Le débat » du plugin chargé s'ouvre
		Et je choisis le genre « jazz »
		Et la section s'enregistre
		Alors la couleur de « Le débat » est « #5b8def »

	# ─── La fenêtre du plugin ──────────────────────────────

	Scénario: La fenêtre montre les genres et les couleurs des priorités
		Quand j'ouvre les réglages des couleurs
		Alors le tableau des genres est « jazz #5b8def », « metal #3d3d3d », « reggae #e07b39 », « talk #f2c14e »
		Et la cellule de « metal » est sur « #3d3d3d », en texte blanc
		Et la couleur « Émission » est « #8fd19e »

	Scénario: Ajouter un genre, changer une couleur de priorité, et enregistrer
		Quand j'ouvre les réglages des couleurs
		Et j'ajoute le genre « rock », « #AA0000 »
		Et j'écris « #ffcc00 » pour « Spéciale »
		Et j'enregistre les couleurs
		Alors le message dit « Enregistré. »
		Et les genres sont :
			| nom    | couleur |
			| jazz   | #5b8def |
			| metal  | #3d3d3d |
			| reggae | #e07b39 |
			| rock   | #aa0000 |
			| talk   | #f2c14e |
		Et la couleur de la priorité « special » est « #ffcc00 »

	Scénario: Choisir une couleur dans le sélecteur
		Quand j'ouvre les réglages des couleurs
		Et je choisis la ligne « talk »
		Et je choisis « #123456 » dans le sélecteur de couleur
		Et j'enregistre les couleurs
		Alors le genre « talk » est « #123456 »

	Scénario: Deux genres peuvent échanger leurs noms
		Quand j'ouvre les réglages des couleurs
		Et je renomme « jazz » en « metal », et « metal » en « jazz »
		Et j'enregistre les couleurs
		Alors le genre « jazz » est « #3d3d3d »
		Et le genre « metal » est « #5b8def »

	Plan du scénario: Un réglage invalide est refusé, et rien n'est enregistré
		Quand j'ouvre les réglages des couleurs
		Et <réglage>
		Et j'enregistre les couleurs
		Alors le message dit « <message> »
		Et les genres sont toujours les quatre de l'installation

		Exemples:
			| réglage                                    | message                                              |
			| j'ajoute le genre « jazz », « #000000 »    | Deux genres s'appellent « jazz ».                    |
			| j'ajoute le genre « Jazz », « #000000 »    | Deux genres s'appellent « Jazz ».                    |
			| j'ajoute le genre « ska », « vert »        | « vert » n'est pas une couleur #rrggbb, pour « ska ». |
			| j'ajoute le genre « », « #000000 »         | Un genre n'a pas de nom.                             |
			| j'écris « #12345 » pour « Fil antenne »    | « #12345 » n'est pas une couleur #rrggbb, pour « Fil antenne ». |

	Scénario: Retirer un genre le retire des événements qui l'avaient
		Étant donné le genre « jazz » de « Jazz à FIP »
		Et le genre « talk » de « Le débat »
		Quand j'ouvre les réglages des couleurs
		Et je choisis la ligne « jazz »
		Et j'appuie sur « Retirer »
		Et j'enregistre les couleurs
		Alors les propriétés de « Jazz à FIP » sont {}
		Et « Le débat » a toujours le genre « talk »

	Scénario: L'enregistrement des réglages fait relire la palette
		Étant donné le plugin des couleurs des émissions, chargé dans « Machin_interface »
		Et la couleur de « Le débat » est « #8fd19e »
		Quand j'ouvre les réglages des couleurs du plugin chargé
		Et j'écris « #00aa00 » pour « Émission »
		Et j'enregistre les couleurs
		Alors la couleur de « Le débat » est « #00aa00 »

	Scénario: Sans base, la fenêtre le dit
		Quand j'ouvre les réglages des couleurs, sans base
		Alors le message dit, entre autres, « Les couleurs ne peuvent être lues ni enregistrées »
