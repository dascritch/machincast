# language: fr
Fonctionnalité: Écran par défaut de l'interface
	En tant que technicien d'antenne,
	je veux que l'écran d'accueil montre en un coup d'œil ce qui passe et ce qui va passer,
	afin que je surveille l'antenne sans effort.

	https://github.com/dascritch/machincast/issues/23, spec § 8.1. L'écran s'affiche hors de l'écran du poste (Qt
	offscreen). La socket d'état est celle du binaire lecture (machincast.lecture.etat, spec § 5.4), ouverte dans un
	répertoire temporaire : le scénario y publie les états, comme le ferait la diffusion. L'airplay se lit dans la base
	de test, avec le rôle de l'interface.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-16 20:00:30 »

	# ─── Heure et état du binaire lecture ─────────────────────

	Scénario: L'écran affiche l'heure actuelle, et la suit
		Quand l'écran par défaut s'ouvre
		Alors l'écran affiche l'heure « vendredi 16 octobre 2026, 20:00:30 »
		Quand l'horloge de l'interface avance de 5 secondes
		Alors l'écran affiche bientôt l'heure « vendredi 16 octobre 2026, 20:00:35 »

	Scénario: Sans socket d'état, le binaire lecture est à l'arrêt
		Quand l'écran par défaut s'ouvre
		Alors l'état du binaire lecture est « À l'arrêt »
		Et le sonore en cours est « — »
		Et le prochain sonore est « — »

	Plan du scénario: Le sonore en cours et le prochain sonore occupent chacun la moitié de la largeur
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « <titre> » de « Les Gaufres » dans « <evenement> », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « <prochain> » dans « <evenement> », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Quand l'écran par défaut s'ouvre, large de <largeur> pixels
		Et le sonore en cours est bientôt « Les Gaufres – <titre> »
		Alors le sonore en cours et le prochain sonore ont la même largeur, la moitié de l'écran

		Exemples:
			| largeur | titre         | prochain | evenement   |
			| 1100    | Café à minuit | Jingle   | Fil de jour |
			| 1600    | Café à minuit | Jingle   | Fil de jour |
			| 900     | Un titre très long, bien plus long que la moitié de la largeur de l'écran, qui doit passer à la ligne | Jingle | Fil de jour |
			| 900     | Café à minuit | Un titre très long, bien plus long que la moitié de la largeur de l'écran, qui doit passer à la ligne | Fil de jour |
			| 900     | Café à minuit | Jingle | Une émission au nom très long, bien plus long que la moitié de la largeur de l'écran, sur plusieurs lignes |

	Scénario: En diffusion, l'écran montre le sonore en cours et sa progression
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Quand l'écran par défaut s'ouvre
		Alors l'état du binaire lecture est bientôt « En diffusion »
		Et le sonore en cours est « Les Gaufres – Café à minuit »
		Et le sonore en cours a pour événement « Fil de jour », début « 20:00:00 », durée « 3:34 » et fin estimée « 20:03:34 »
		Et le sonore en cours a pour emplacement « /srv/musique/Café_à_minuit.flac »
		Et la barre de progression du sonore en cours est à « 14 % »

	Scénario: La progression suit les états publiés
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Quand l'écran par défaut s'ouvre
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 107,25 secondes
		Alors la barre de progression du sonore en cours est bientôt à « 50 % »

	Plan du scénario: Le prochain sonore montre ses heures estimées, sa durée et l'indicateur « sain »
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : <sain>
		Quand l'écran par défaut s'ouvre
		Alors le prochain sonore est bientôt « Jingle »
		Et le prochain sonore a pour événement « Fil de jour », début estimé « 20:03:30 », fin estimée « 20:03:38 » et durée « 0:08 »
		Et le prochain sonore a pour emplacement « /srv/musique/Jingle.flac »
		Et le prochain sonore est sain : « <affiche> »

		Exemples:
			| sain | affiche |
			| oui  | oui     |
			| non  | non     |

	Scénario: Pour un stream, la durée et la fin sont inconnues
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse le stream « Direct studio » dans « Direct », commencé à 20:00:00, joué depuis 30 secondes
		Et le prochain sonore est le stream « Relais » dans « Direct », de début inconnu
		Quand l'écran par défaut s'ouvre
		Alors le sonore en cours est bientôt « Direct studio »
		Et le sonore en cours a pour événement « Direct », début « 20:00:00 », durée « inconnue » et fin estimée « inconnue »
		Et la barre de progression du sonore en cours est à « durée inconnue »
		Et le sonore en cours a pour emplacement « https://flux.exemple/Direct_studio »
		Et le prochain sonore a pour événement « Direct », début estimé « inconnu », fin estimée « inconnue » et durée « inconnue »
		Et le prochain sonore a pour emplacement « https://flux.exemple/Relais »
		Et le prochain sonore est sain : « non testé »

	Scénario: En silence, l'écran le dit, sans sonore en cours
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture est en silence
		Quand l'écran par défaut s'ouvre
		Alors l'état du binaire lecture est bientôt « En silence »
		Et le sonore en cours est « — »
		Et le sonore en cours a pour emplacement « — »
		Et le prochain sonore a pour emplacement « — »
		Et la barre de progression du sonore en cours est à « — »

	Scénario: Le dernier état du binaire lecture qui s'arrête met l'écran à l'arrêt
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Quand l'écran par défaut s'ouvre
		Et le binaire lecture s'arrête
		Alors l'état du binaire lecture est bientôt « À l'arrêt »
		Et le sonore en cours est « — »

	Scénario: Un binaire lecture arrêté brutalement, sans dernier état, met aussi l'écran à l'arrêt
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Quand l'écran par défaut s'ouvre
		Et l'état du binaire lecture est bientôt « En diffusion »
		Et la socket d'état se ferme sans dernier état
		Alors l'état du binaire lecture est bientôt « À l'arrêt »

	Scénario: L'écran retrouve le binaire lecture quand il démarre après lui
		Quand l'écran par défaut s'ouvre
		Et la socket d'état du binaire lecture s'ouvre ensuite
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Alors l'état du binaire lecture est bientôt « En diffusion »
		Et le sonore en cours est « Les Gaufres – Café à minuit »

	Scénario: Un message illisible sur la socket est ignoré, et le suivant est lu
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Quand l'écran par défaut s'ouvre
		Et l'état du binaire lecture est bientôt « En diffusion »
		Et un message illisible arrive sur la socket d'état, suivi dans le même envoi d'un état de silence
		Alors l'état du binaire lecture est bientôt « En silence »

	Scénario: Un état coupé en deux envois sur la socket est lu en entier
		Étant donné la socket d'état du binaire lecture ouverte
		Quand l'écran par défaut s'ouvre
		Et un état de silence arrive sur la socket d'état en deux envois
		Alors l'état du binaire lecture est bientôt « En silence »

	Scénario: Un sonore sans artiste ni titre est affiché comme tel
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse un sonore sans artiste ni titre dans « Fil de jour », commencé à 20:00:00, de 60 secondes
		Quand l'écran par défaut s'ouvre
		Alors le sonore en cours est bientôt « (sans titre) »
		Et le sonore en cours a pour emplacement « inconnu »

	# ─── Airplay des 12 dernières heures ───────────────────────

	Scénario: L'airplay des 12 dernières heures, du plus récent au plus ancien
		Étant donné les passages dans l'airplay :
			| debut               | fin                 | artiste     | titre         | evenement   | sequence | banque  | sans_incident |
			| 2026-10-16 08:00:00 | 2026-10-16 08:03:00 | Ancien      | Trop ancien   | Fil de nuit |          |         | oui           |
			| 2026-10-16 08:01:00 | 2026-10-16 08:04:00 | Les Gaufres | Le matin      | Fil de jour |          | Titres  | oui           |
			| 2026-10-16 18:00:00 | 2026-10-16 19:02:05 |             | Le journal    | Journal     |          |         | oui           |
			| 2026-10-16 19:50:00 | 2026-10-16 19:51:00 |             | Spot          | Fil de jour | Pub      | Spots   | non           |
			| 2026-10-16 20:00:00 |                     | Les Gaufres | Café à minuit | Fil de jour |          | Titres  |               |
		Quand l'écran par défaut s'ouvre
		Alors la table de l'airplay montre :
			| debut    | fin      | duree | artiste     | titre         | evenement   | sequence | banque | sans_incident |
			| 20:00:00 | en cours |       | Les Gaufres | Café à minuit | Fil de jour |          | Titres |               |
			| 19:50:00 | 19:51:00 | 1:00  |             | Spot          | Fil de jour | Pub      | Spots  | non           |
			| 18:00:00 | 19:02:05 | 1:02:05 |           | Le journal    | Journal     |          |        | oui           |
			| 08:01:00 | 08:04:00 | 3:00  | Les Gaufres | Le matin      | Fil de jour |          | Titres | oui           |

	Scénario: L'interface est privée : l'airplay montre l'artiste et le titre, même masqués
		Étant donné les passages dans l'airplay :
			| debut               | fin                 | artiste     | titre         | evenement   | sequence | banque | sans_incident |
			| 2026-10-16 19:50:00 | 2026-10-16 19:53:00 | Les Gaufres | Café à minuit | Fil de jour |          |        | oui           |
		Et le masquage de tous les sonores et de tous les événements
		Quand l'écran par défaut s'ouvre
		Alors la table de l'airplay montre :
			| debut    | fin      | duree | artiste     | titre         | evenement   | sequence | banque | sans_incident |
			| 19:50:00 | 19:53:00 | 3:00  | Les Gaufres | Café à minuit | Fil de jour |          |        | oui           |

	Scénario: L'airplay se relit à chaque nouveau sonore, jamais en boucle
		Étant donné les passages dans l'airplay :
			| debut               | fin | artiste     | titre         | evenement   | sequence | banque | sans_incident |
			| 2026-10-16 20:00:00 |     | Les Gaufres | Café à minuit | Fil de jour |          |        |               |
		Et la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Quand l'écran par défaut s'ouvre
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 31 secondes
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 32 secondes
		Alors l'airplay a été lu 1 fois
		Quand le passage de « Jingle » commence dans l'airplay à 20:03:34
		Et le binaire lecture diffuse « Jingle » de « Radio » dans « Fil de jour », commencé à 20:03:34, de 8 secondes, joué depuis 0 secondes
		Alors l'airplay a bientôt été lu 2 fois
		Et la première ligne de la table de l'airplay est « Jingle »
		Quand le binaire lecture diffuse « Jingle » de « Radio » dans « Fil de jour », commencé à 20:03:34, de 8 secondes, joué depuis 1 secondes
		Alors l'airplay a été lu 2 fois

	# ─── Lancement ─────────────────────────────────────────────

	Scénario: Sans base de données joignable, une fenêtre explique pourquoi l'interface n'est pas utilisable
		Étant donné un affichage graphique disponible
		Quand Machin interface démarre avec une socket PostgreSQL inexistante
		Alors il s'arrête avec le code 1, après une fenêtre d'erreur « MachinCast : base de données injoignable »
		Et la fenêtre d'erreur explique que l'interface n'est pas utilisable sans sa base de données
		Et la fenêtre d'erreur invite à lire le document INSTALL.md du répertoire de MachinCast
		Et la fenêtre d'erreur détaille l'erreur de PostgreSQL
		Et le message « base de données injoignable » est aussi sur la sortie d'erreur

	Scénario: Un compte sans droit sur la base reçoit la même fenêtre
		Étant donné un affichage graphique disponible
		Et un compte qui ne peut pas endosser le rôle de l'interface
		Quand Machin interface démarre avec une socket PostgreSQL inexistante
		Alors il s'arrête avec le code 1, après une fenêtre d'erreur « MachinCast : base de données injoignable »
		Et la fenêtre d'erreur invite à lire le document INSTALL.md du répertoire de MachinCast
		Et le message « erreur de base de données » est aussi sur la sortie d'erreur

	Scénario: La fenêtre d'erreur parle français, boutons de Qt compris
		Étant donné un affichage graphique disponible
		Et la traduction française de Qt chargée
		Quand Machin interface démarre avec une socket PostgreSQL inexistante
		Alors la fenêtre d'erreur a les boutons « Montrer les détails… », « Ouvrir INSTALL.md » et « Fermer »

	Scénario: L'application Qt de l'interface est créée en français
		Quand l'application Qt de l'interface est créée dans un processus neuf
		Alors Qt y traduit « Show Details... » par « Montrer les détails… »

	Scénario: Le bouton de la fenêtre d'erreur ouvre INSTALL.md
		Étant donné un affichage graphique disponible
		Quand Machin interface démarre avec une socket PostgreSQL inexistante
		Et je clique sur « Ouvrir INSTALL.md » dans la fenêtre d'erreur
		Alors le document INSTALL.md du répertoire de MachinCast est ouvert

	Scénario: Sans affichage graphique, Machin interface s'arrête avec le code 1, sans fenêtre
		Quand je lance Machin_interface avec une socket PostgreSQL inexistante
		Alors Machin_interface s'arrête avec le code 1, en signalant « base de données injoignable »

	Plan du scénario: Une fenêtre ne s'ouvre que si un affichage graphique peut la montrer
		Quand l'environnement graphique est <environnement>
		Alors une fenêtre d'erreur <verdict> s'ouvrir

		Exemples:
			| environnement                         | verdict    |
			| DISPLAY=:0                            | peut       |
			| WAYLAND_DISPLAY=wayland-0             | peut       |
			| QT_QPA_PLATFORM=xcb                   | peut       |
			| DISPLAY=:0, QT_QPA_PLATFORM=offscreen | ne peut pas |
			| QT_QPA_PLATFORM=minimal               | ne peut pas |
			| vide                                  | ne peut pas |
