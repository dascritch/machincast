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

	Scénario: L'écran affiche l'heure actuelle, sans la date, et la suit
		Seule l'heure compte sur cet écran (demandé avec https://github.com/dascritch/machincast/issues/191) : la date du
		jour n'est plus qu'en infobulle.

		Quand l'écran par défaut s'ouvre
		Alors l'écran affiche l'heure « 20:00:30 »
		Et l'heure a pour infobulle « vendredi 16 octobre 2026 »
		Quand l'horloge de l'interface avance de 5 secondes
		Alors l'écran affiche bientôt l'heure « 20:00:35 »

	Scénario: Sans socket d'état, le binaire lecture est à l'arrêt
		Quand l'écran par défaut s'ouvre
		Alors l'état du binaire lecture est « À l'arrêt »
		Et le sonore en cours est « — »
		Et le prochain sonore est « — »

	Plan du scénario: Le sonore en cours et le prochain sonore se partagent la largeur, de part et d'autre de la colonne de l'antenne
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « <titre> » de « Les Gaufres » dans « <evenement> », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « <prochain> » dans « <evenement> », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Quand l'écran par défaut s'ouvre, large de <largeur> pixels
		Et le sonore en cours est bientôt « Les Gaufres – <titre> »
		Alors le sonore en cours et le prochain sonore ont la même largeur, de part et d'autre de la colonne de l'antenne

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
		Et le sonore en cours a pour événement « Fil de jour » et pour horaire « 20:00:00 – 20:03:34 (3:34) »
		Et le sonore en cours a pour emplacement « /srv/musique/Café_à_minuit.flac »
		Et l'avancement du sonore en cours est à « reste 3:05 », à 14 %
		Et le sonore en cours n'a pas d'intitulé « Progression »

	Scénario: Un sonore qui dépasse sa durée annoncée n'a plus de temps qui reste
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 220 secondes
		Quand l'écran par défaut s'ouvre
		Alors l'avancement du sonore en cours est bientôt à « reste 0:00 », à 100 %

	Scénario: La progression suit les états publiés
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Quand l'écran par défaut s'ouvre
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 107,25 secondes
		Alors l'avancement du sonore en cours est bientôt à « reste 1:48 »

	Scénario: Un sonore de durée nulle est au bout de son avancement
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Bip » de « Radio » dans « Fil de jour », commencé à 20:00:00, de 0 secondes, joué depuis 0 secondes
		Quand l'écran par défaut s'ouvre
		Alors l'avancement du sonore en cours est bientôt à « reste 0:00 », à 100 %

	Scénario: Un sonore qu'un événement coupera montre la coupure, et le temps qui lui reste jusqu'à elle
		https://github.com/dascritch/machincast/issues/169 : le binaire lecture annonce la coupure et le sonore que jouera l'événement.

		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le sonore en cours sera coupé à 20:02:00 par l'événement « Journal »
		Et le prochain sonore est « Flash info » dans « Journal », estimé de 20:02:00 à 20:02:30, de 30 secondes, sain : oui
		Quand l'écran par défaut s'ouvre
		Alors le prochain sonore est bientôt « Flash info »
		Et le sonore en cours a pour événement « Fil de jour » et pour horaire « 20:00:00 – 20:02:00 (coupé par « Journal », sur 3:34) »
		Et l'avancement du sonore en cours est à « reste 1:30 avant « Journal » », à 25 %
		Et le prochain sonore a pour événement « Journal » et pour horaire « 20:02:00 – 20:02:30 (0:30) »

	Scénario: Un stream qu'un événement coupera a une fin, et un temps qui reste
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse le stream « Direct studio » dans « Direct », commencé à 20:00:00, joué depuis 30 secondes
		Et le sonore en cours sera coupé à 20:05:00 par l'événement « Flash »
		Quand l'écran par défaut s'ouvre
		Alors le sonore en cours est bientôt « Direct studio »
		Et le sonore en cours a pour événement « Direct » et pour horaire « 20:00:00 – 20:05:00 (coupé par « Flash », durée inconnue) »
		Et l'avancement du sonore en cours est à « reste 4:30 avant « Flash » », à 10 %

	# ─── Frises (https://github.com/dascritch/machincast/issues/230) ───

	Scénario: Un fichier en cours a une frise à la place de la barre de progression, et le temps qui reste dessous
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Quand l'écran par défaut s'ouvre
		Alors le sonore en cours a une frise, sans barre de progression
		Et le prochain sonore a une frise, sans tête de lecture
		Et l'avancement du sonore en cours est bientôt à « reste 3:05 », à 14 %

	Scénario: Les deux frises sont en tête de leur sonore, au-dessus du titre, au même niveau
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Quand l'écran par défaut s'ouvre, large de 1100 pixels
		Et le sonore en cours est bientôt « Les Gaufres – Café à minuit »
		Alors les frises du sonore en cours et du prochain sonore sont au-dessus de leur titre, à la même hauteur
		Et le temps qui reste au sonore en cours est écrit au milieu de sa frise, sans autre ligne sous elle

	Scénario: Le VU-mètre de l'antenne prend toute la hauteur que lui laissent les frises
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Quand l'écran par défaut s'ouvre, large de 1100 pixels
		Et le sonore en cours est bientôt « Les Gaufres – Café à minuit »
		Et la colonne de l'antenne est plus haute qu'il ne lui faut
		Alors le VU-mètre de l'antenne occupe sa colonne : ses voyants gardent leur hauteur, il prend le reste

	Scénario: Un stream garde sa barre de progression, et n'a pas de frise
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse le stream « Direct studio » dans « Direct », commencé à 20:00:00, joué depuis 30 secondes
		Et le prochain sonore est le stream « Relais » dans « Direct », de début inconnu
		Quand l'écran par défaut s'ouvre
		Alors le sonore en cours est bientôt « Direct studio »
		Et le sonore en cours a une barre de progression, sans frise
		Et le prochain sonore n'a pas de frise

	Scénario: La frise du sonore en cours montre ce que la diffusion en fait, règles de sa banque comprises
		Étant donné le sonore « Respiration » en base, pour une copie du fichier de test « blancs.flac », de 2 secondes, aux blancs de 0,5 s au début et 0,5 s à la fin, sans détection de blanc, aux crossfades de 0,2 s au début et 0,3 s à la fin
		Et la banque « Nuit » en base, qui retire les blancs et impose un crossfade de fin de 0,4 s, avec « Respiration »
		Et la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Respiration », de la banque « Nuit », commencé à 20:00:00, joué depuis 0,4 seconde
		Quand l'écran par défaut s'ouvre
		Alors la frise du sonore en cours montre bientôt les zones :
			| zone            | de   | à    | hachures | infobulle                                                                                               |
			| blanc de début  | 0,00 | 0,50 | pleines  | Blanc de début : 0,50 s, retiré à l'antenne                                                             |
			| fondu d'entrée  | 0,30 | 0,50 | aucune   | Crossfade de début : 0,20 s, se termine au début détecté, montée si le sonore précédent a un crossfade de fin |
			| fondu de sortie | 1,50 | 1,90 | aucune   | Crossfade de fin : 0,40 s (imposé par la banque), commence à la fin détectée                            |
			| blanc de fin    | 1,50 | 2,00 | pleines  | Blanc de fin : 0,50 s, retiré à l'antenne                                                               |
		Et la tête de lecture de la frise du sonore en cours est à 0,7 seconde, la position jouée comptée depuis le début de la lecture
		Et la forme d'onde de la frise du sonore en cours est bientôt complète

	Scénario: La frise du prochain sonore, sans banque, montre ses propres réglages
		Étant donné le sonore « Respiration » en base, pour une copie du fichier de test « blancs.flac », de 2 secondes, aux blancs de 0,5 s au début et 0,5 s à la fin, sans détection de blanc, aux crossfades de 0,2 s au début et 0,3 s à la fin
		Et la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « Respiration » en base, sans banque
		Quand l'écran par défaut s'ouvre
		Alors la frise du prochain sonore montre bientôt les zones « blanc de début », « fondu d'entrée », « fondu de sortie », « blanc de fin », ses blancs joués à l'antenne

	Scénario: La forme d'onde du prochain sonore sert encore quand il passe à l'antenne, sans être recalculée
		Étant donné le sonore « Respiration » en base, pour une copie du fichier de test « blancs.flac », de 2 secondes, aux blancs de 0,5 s au début et 0,5 s à la fin, sans détection de blanc, aux crossfades de 0,2 s au début et 0,3 s à la fin
		Et la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « Respiration » en base, sans banque
		Quand l'écran par défaut s'ouvre
		Et la forme d'onde de la frise du prochain sonore est bientôt complète
		Et le binaire lecture diffuse « Respiration », sans banque, commencé à 20:03:34, joué depuis 0,2 seconde
		Alors la frise du sonore en cours dessine bientôt la forme d'onde qu'avait le prochain sonore

	Scénario: Le plan d'un sonore se lit une fois en base, pas à chaque état publié
		Étant donné le sonore « Respiration » en base, pour une copie du fichier de test « blancs.flac », de 2 secondes, aux blancs de 0,5 s au début et 0,5 s à la fin, sans détection de blanc, aux crossfades de 0,2 s au début et 0,3 s à la fin
		Et la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Respiration », sans banque, commencé à 20:00:00, joué depuis 0,2 seconde
		Quand l'écran par défaut s'ouvre
		Et le binaire lecture diffuse « Respiration », sans banque, commencé à 20:00:00, joué depuis 0,6 seconde
		Alors la tête de lecture de la frise du sonore en cours est à 0,6 seconde, la position jouée comptée depuis le début de la lecture
		Et le plan du sonore « Respiration » n'a été lu qu'une fois en base

	Scénario: Sur l'accueil, la frise ne déplace aucune lecture
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Quand l'écran par défaut s'ouvre
		Et je clique au milieu de la frise du sonore en cours
		Alors la frise du sonore en cours n'a demandé aucune position

	Plan du scénario: Le prochain sonore montre ses heures estimées, sa durée et l'indicateur « sain »
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : <sain>
		Quand l'écran par défaut s'ouvre
		Alors le prochain sonore est bientôt « Jingle »
		Et le prochain sonore a pour événement « Fil de jour » et pour horaire « 20:03:30 – 20:03:38 (0:08) »
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
		Et le sonore en cours a pour événement « Direct » et pour horaire « 20:00:00, durée inconnue »
		Et l'avancement du sonore en cours est à « durée inconnue »
		Et le sonore en cours a pour emplacement « https://flux.exemple/Direct_studio »
		Et le prochain sonore a pour événement « Direct » et pour horaire « inconnu, durée inconnue »
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
		Et l'avancement du sonore en cours est à « — »

	Scénario: Le dernier état du binaire lecture qui s'arrête met l'écran à l'arrêt
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Quand l'écran par défaut s'ouvre
		Et le binaire lecture s'arrête
		Alors l'état du binaire lecture est bientôt « À l'arrêt »
		Et le sonore en cours est « — »

	Scénario: Le binaire lecture qui s'arrête efface tout ce que l'écran disait du sonore en cours
		https://github.com/dascritch/machincast/issues/144

		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le sonore en cours a pour contexte :
			| champ           | valeur              |
			| evenement_id    | 3                   |
			| evenement_debut | 2026-10-16 20:00:00 |
			| evenement_fin   | 2026-10-16 22:00:00 |
			| sequence        | Pub                 |
			| banque          | Spots               |
			| texte_public    | Radio Machin        |
		Quand l'écran par défaut s'ouvre
		Et le sonore en cours est bientôt « Les Gaufres – Café à minuit »
		Et le binaire lecture s'arrête
		Alors l'état du binaire lecture est bientôt « À l'arrêt »
		Et le sonore en cours a pour événement « — » et pour horaire « — »
		Et le sonore en cours a pour séquence « — » et pour banque « — »
		Et l'avancement du sonore en cours est à « — », à 0 %
		Et le bandeau montre le texte public « — »
		Et l'événement à l'antenne est « — »
		Et les boutons de fiche de l'accueil sont inactifs

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

	# ─── Contexte du sonore (https://github.com/dascritch/machincast/issues/144) ─────

	Scénario: Le bandeau montre le texte public entre guillemets, et l'événement à l'antenne avec ses heures
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le sonore en cours a pour contexte :
			| champ           | valeur              |
			| evenement_id    | 3                   |
			| evenement_debut | 2026-10-16 20:00:00 |
			| evenement_fin   | 2026-10-16 22:00:00 |
			| sequence        | Pub                 |
			| sequence_id     | 4                   |
			| banque          | Spots               |
			| banque_id       | 5                   |
			| texte_public    | Radio Machin        |
		Quand l'écran par défaut s'ouvre
		Alors le bandeau montre bientôt le texte public « « Radio Machin » »
		Et l'événement à l'antenne est « Fil de jour, de 20:00 à 22:00 »
		Et le sonore en cours a pour séquence « Pub » et pour banque « Spots »

	Scénario: Le bandeau ne montre que des valeurs : l'état et l'événement à l'antenne se disent en infobulle
		Demandé avec https://github.com/dascritch/machincast/issues/191 : « Binaire lecture : » est implicite, et « Événement à
		l'antenne : » double l'événement du sonore en cours.

		Quand l'écran par défaut s'ouvre
		Alors l'écran n'a aucun intitulé « Binaire lecture : » ni « Événement à l'antenne : »
		Et l'état du binaire lecture a pour infobulle « État de Machin lecture »
		Et l'événement à l'antenne a pour infobulle « Événement à l'antenne »

	Plan du scénario: L'événement à l'antenne dit s'il est permanent, ou sans fin prévue
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le sonore en cours a pour contexte :
			| champ           | valeur  |
			| evenement_debut | <debut> |
			| evenement_fin   | <fin>   |
		Quand l'écran par défaut s'ouvre
		Alors l'événement à l'antenne est bientôt « <texte> »

		Exemples:
			| debut               | fin | texte                      |
			|                     |     | Fil de jour, permanent     |
			| 2026-10-16 19:00:00 |     | Fil de jour, depuis 19:00  |

	Scénario: Hors d'une séquence ou d'une banque, le sonore le montre
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Et le prochain sonore a pour contexte :
			| champ     | valeur  |
			| banque    | Jingles |
			| banque_id | 6       |
		Quand l'écran par défaut s'ouvre
		Alors le prochain sonore est bientôt « Jingle »
		Et le sonore en cours a pour séquence « — » et pour banque « — »
		Et le prochain sonore a pour séquence « — » et pour banque « Jingles »
		Et le bandeau montre le texte public « — »

	Scénario: Les boutons de l'accueil ouvrent la fiche du sonore et celle de l'événement
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le sonore en cours a pour contexte :
			| champ        | valeur |
			| evenement_id | 3      |
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Et le prochain sonore a pour contexte :
			| champ        | valeur |
			| evenement_id | 8      |
		Quand l'écran par défaut s'ouvre
		Et le sonore en cours est bientôt « Les Gaufres – Café à minuit »
		Et je clique sur le bouton « ouvrir_sonore_en_cours » de l'accueil
		Et je clique sur le bouton « ouvrir_evenement_en_cours » de l'accueil
		Et je clique sur le bouton « ouvrir_sonore_prochain » de l'accueil
		Et je clique sur le bouton « ouvrir_evenement_prochain » de l'accueil
		Alors l'accueil a demandé les fiches :
			| genre     | identifiant | nom                         |
			| sonore    | 12          | Les Gaufres – Café à minuit |
			| événement | 3           | Fil de jour                 |
			| sonore    | 31          | Jingle                      |
			| événement | 8           | Fil de jour                 |

	Scénario: Les boutons de l'accueil ouvrent la fiche de la séquence et celle de la banque
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le sonore en cours a pour contexte :
			| champ       | valeur  |
			| sequence    | Pub     |
			| sequence_id | 5       |
			| banque      | Jingles |
			| banque_id   | 7       |
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Et le prochain sonore a pour contexte :
			| champ       | valeur   |
			| sequence    | Météo    |
			| sequence_id | 6        |
			| banque      | Rotation |
			| banque_id   | 9        |
		Quand l'écran par défaut s'ouvre
		Et le sonore en cours est bientôt « Les Gaufres – Café à minuit »
		Et je clique sur le bouton « ouvrir_sequence_en_cours » de l'accueil
		Et je clique sur le bouton « ouvrir_banque_en_cours » de l'accueil
		Et je clique sur le bouton « ouvrir_sequence_prochain » de l'accueil
		Et je clique sur le bouton « ouvrir_banque_prochain » de l'accueil
		Alors l'accueil a demandé les fiches :
			| genre    | identifiant | nom      |
			| séquence | 5           | Pub      |
			| banque   | 7           | Jingles  |
			| séquence | 6           | Météo    |
			| banque   | 9           | Rotation |

	Scénario: Sans séquence ni banque, l'accueil ne propose pas leur fiche
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le sonore en cours a pour contexte :
			| champ       | valeur  |
			| sequence    | Pub     |
			| banque      | Jingles |
			| banque_id   | 7       |
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Quand l'écran par défaut s'ouvre
		Alors le prochain sonore est bientôt « Jingle »
		Et les boutons de séquence et de banque de l'accueil sont, pour le sonore en cours puis le prochain : inactif, actif, inactif, inactif

	Scénario: Sans événement connu, l'accueil ne propose pas sa fiche
		https://github.com/dascritch/machincast/issues/144 : un binaire lecture d'avant ce ticket ne dit pas
		l'identifiant de l'événement ; un état peut ne pas dire l'événement du tout.

		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le sonore en cours a pour contexte :
			| champ     | valeur |
			| evenement |        |
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Quand l'écran par défaut s'ouvre
		Alors le prochain sonore est bientôt « Jingle »
		Et le sonore en cours a pour événement « — » et pour horaire « 20:00:00 – 20:03:34 (3:34) »
		Et l'événement à l'antenne est « — »
		Et le prochain sonore a pour événement « Fil de jour » et pour horaire « 20:03:30 – 20:03:38 (0:08) »
		Et les boutons de fiche de l'accueil sont, dans l'ordre sonore en cours, son événement, prochain sonore, son événement : actif, inactif, actif, inactif

	Scénario: Sans sonore, les boutons de fiche de l'accueil sont inactifs
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture est en silence
		Quand l'écran par défaut s'ouvre
		Alors l'état du binaire lecture est bientôt « En silence »
		Et les boutons de fiche de l'accueil sont inactifs

	# ─── Écouter le prochain sonore (https://github.com/dascritch/machincast/issues/223) ─────

	Scénario: Pour un fichier, la ligne « Sain » du prochain sonore propose sa pré-écoute
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Quand l'écran par défaut s'ouvre
		Et le prochain sonore est bientôt « Jingle »
		Alors l'accueil propose pour le prochain sonore : pré-écoute active, test du flux caché
		Quand je clique sur le bouton « preecouter_prochain » de l'accueil
		Alors la pré-écoute du sonore 31 a été demandée

	Scénario: Un clic sur la frise du prochain sonore ouvre aussi sa pré-écoute
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Quand l'écran par défaut s'ouvre
		Et le prochain sonore est bientôt « Jingle »
		Et je clique sur la frise du prochain sonore
		Alors la pré-écoute du sonore 31 a été demandée

	Scénario: Sans prochain sonore, l'accueil ne propose ni pré-écoute ni test du flux
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Quand l'écran par défaut s'ouvre
		Et le sonore en cours est bientôt « Les Gaufres – Café à minuit »
		Alors l'accueil propose pour le prochain sonore : pré-écoute inactive, test du flux caché

	Scénario: Pour un stream, l'accueil propose de tester la connexion de son flux, qui dit son type et son débit
		Étant donné un serveur de flux local, avec le flux « studio » en ligne
		Et la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est le stream du flux « studio » dans « Direct »
		Quand l'écran par défaut s'ouvre
		Et le prochain sonore est bientôt « Direct studio »
		Alors l'accueil propose pour le prochain sonore : pré-écoute active, test du flux actif
		Quand je clique sur le bouton « tester_le_flux_prochain » de l'accueil
		Alors le test du flux du prochain sonore dit bientôt « Le flux répond : du son arrive, en MPEG-1 Layer 3 (MP3) à 224 kbit/s. »

	# ─── Sonores à venir (https://github.com/dascritch/machincast/issues/228) ─────

	Scénario: Au-dessus de l'airplay, les sonores à venir après le prochain, le plus lointain en haut
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et le prochain sonore est « Jingle » dans « Fil de jour », estimé de 20:03:30 à 20:03:38, de 8 secondes, sain : oui
		Et les sonores à venir après le prochain sont :
			| debut    | fin      | duree | artiste     | titre      | evenement   | sequence | banque | sain |
			| 20:03:38 | 20:06:38 | 180   | Les Gaufres | Le matin   | Fil de jour |          | Titres | oui  |
			| 20:06:38 | 20:07:08 | 30    |             | Spot       | Fil de jour | Pub      | Spots  | non  |
			| 20:07:08 | 20:30:00 | 1800  |             | Le journal | Journal     |          |        | oui  |
		Quand l'écran par défaut s'ouvre
		Et le sonore en cours est bientôt « Les Gaufres – Café à minuit »
		Alors la table des sonores à venir montre :
			| debut    | fin      | duree | artiste     | titre      | evenement   | sequence | banque | incident |
			| 20:07:08 | 20:30:00 | 30:00 |             | Le journal | Journal     |          |        |          |
			| 20:06:38 | 20:07:08 | 0:30  |             | Spot       | Fil de jour | Pub      | Spots  | pas sain |
			| 20:03:38 | 20:06:38 | 3:00  | Les Gaufres | Le matin   | Fil de jour |          | Titres |          |
		Et la table des sonores à venir a les colonnes de l'airplay, dans le même ordre
		Et la table des sonores à venir est au-dessus de celle de l'airplay

	Scénario: Les sonores à venir suivent les états publiés, et disparaissent à l'arrêt
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et les sonores à venir après le prochain sont :
			| debut    | fin      | duree | artiste | titre    | evenement   | sequence | banque | sain |
			| 20:03:38 | 20:06:38 | 180   |         | Le matin | Fil de jour |          |        | oui  |
		Quand l'écran par défaut s'ouvre
		Alors la table des sonores à venir a bientôt 1 ligne
		Quand le binaire lecture s'arrête
		Alors la table des sonores à venir a bientôt 0 ligne

	Scénario: Un double-clic sur un sonore à venir ouvre sa fiche, celle de son événement, de sa séquence ou de sa banque
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et les sonores à venir après le prochain sont :
			| debut    | fin      | duree | artiste | titre | evenement   | sequence | banque | sain |
			| 20:06:38 | 20:07:08 | 30    | Radio   | Spot  | Fil de jour | Pub      | Spots  | oui  |
		Quand l'écran par défaut s'ouvre
		Et la table des sonores à venir a bientôt 1 ligne
		Et j'ouvre dans les sonores à venir la cellule « Radio »
		Et j'ouvre dans les sonores à venir la cellule « Fil de jour »
		Et j'ouvre dans les sonores à venir la cellule « Pub »
		Et j'ouvre dans les sonores à venir la cellule « Spots »
		Et j'ouvre dans les sonores à venir la cellule « 20:06:38 »
		Alors l'accueil a demandé les fiches :
			| genre     | identifiant | nom         |
			| sonore    | 41          | Spot        |
			| événement | 51          | Fil de jour |
			| séquence  | 61          | Pub         |
			| banque    | 71          | Spots       |

	Scénario: Une ligne des sonores à venir propose la pré-écoute de son sonore
		Étant donné la socket d'état du binaire lecture ouverte
		Et le binaire lecture diffuse « Café à minuit » de « Les Gaufres » dans « Fil de jour », commencé à 20:00:00, de 214,5 secondes, joué depuis 30 secondes
		Et les sonores à venir après le prochain sont :
			| debut    | fin      | duree | artiste | titre | evenement   | sequence | banque | sain |
			| 20:06:38 | 20:07:08 | 30    | Radio   | Spot  | Fil de jour |          |        | oui  |
		Quand l'écran par défaut s'ouvre
		Et la table des sonores à venir a bientôt 1 ligne
		Et je choisis « Pré-écoute… » au clic droit sur la ligne « Spot » des sonores à venir
		Alors la pré-écoute du sonore 41 a été demandée

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
			| debut    | fin      | duree | artiste     | titre         | evenement   | sequence | banque | incident |
			| 20:00:00 | en cours |       | Les Gaufres | Café à minuit | Fil de jour |          | Titres |  |
			| 19:50:00 | 19:51:00 | 1:00  |             | Spot          | Fil de jour | Pub      | Spots  | oui |
			| 18:00:00 | 19:02:05 | 1:02:05 |           | Le journal    | Journal     |          |        |  |
			| 08:01:00 | 08:04:00 | 3:00  | Les Gaufres | Le matin      | Fil de jour |          | Titres |  |

	Scénario: L'interface est privée : l'airplay montre l'artiste et le titre, même masqués
		Étant donné les passages dans l'airplay :
			| debut               | fin                 | artiste     | titre         | evenement   | sequence | banque | sans_incident |
			| 2026-10-16 19:50:00 | 2026-10-16 19:53:00 | Les Gaufres | Café à minuit | Fil de jour |          |        | oui           |
		Et le masquage de tous les sonores et de tous les événements
		Quand l'écran par défaut s'ouvre
		Alors la table de l'airplay montre :
			| debut    | fin      | duree | artiste     | titre         | evenement   | sequence | banque | incident |
			| 19:50:00 | 19:53:00 | 3:00  | Les Gaufres | Café à minuit | Fil de jour |          |        |  |

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

	Scénario: Un double-clic sur un élément absent, ou effacé de la base depuis, ne demande aucune fiche
		Étant donné les passages dans l'airplay :
			| debut               | fin                 | artiste | titre | evenement   | sequence | banque | sans_incident |
			| 2026-10-16 19:50:00 | 2026-10-16 19:51:00 | Radio   | Spot  | Fil de jour |          |        | non           |
		Et le sonore « Spot » est effacé de la base
		Quand l'écran par défaut s'ouvre
		Et j'ouvre dans l'airplay la cellule « Spot »
		Et j'ouvre dans l'airplay la cellule de la colonne « Séquence »
		Et j'ouvre dans l'airplay la cellule de la colonne « Banque »
		Alors l'accueil n'a demandé aucune fiche

	Scénario: Un double-clic sur l'airplay ouvre la fiche du sonore, de l'événement, de la séquence ou de la banque
		Étant donné les passages dans l'airplay :
			| debut               | fin                 | artiste | titre | evenement   | sequence | banque | sans_incident |
			| 2026-10-16 19:50:00 | 2026-10-16 19:51:00 | Radio   | Spot  | Fil de jour | Pub      | Spots  | non           |
		Quand l'écran par défaut s'ouvre
		Et j'ouvre dans l'airplay la cellule « Radio »
		Et j'ouvre dans l'airplay la cellule « Spot »
		Et j'ouvre dans l'airplay la cellule « Fil de jour »
		Et j'ouvre dans l'airplay la cellule « Pub »
		Et j'ouvre dans l'airplay la cellule « Spots »
		Et j'ouvre dans l'airplay la cellule « 19:50:00 »
		Et j'ouvre dans l'airplay la cellule « oui »
		Alors l'accueil a demandé les fiches de l'airplay :
			| genre     | nom         |
			| sonore    | Spot        |
			| sonore    | Spot        |
			| événement | Fil de jour |
			| séquence  | Pub         |
			| banque    | Spots       |

