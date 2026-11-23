# language: fr
Fonctionnalité: Les émissions en alternance : un événement méta joue, selon la semaine du mois, l'une de ses émissions
	En tant que responsable d'antenne,
	je veux identifier les émissions qui se partagent le même créneau horaire en fonction de la semaine,
	afin de donner la bonne indication sur le calendrier, sur l'affichage public et jouer le bon sonore programmé.

	https://github.com/dascritch/machincast/issues/609, ticket enfant de
	https://github.com/dascritch/machincast/issues/606. « Mercredi soir », le mercredi de 20 h à 21 h, est l'événement
	méta : il fait jouer « Sonia », « Les ahuris » ou « Zôtre », selon la semaine du mois, ou une semaine sur deux, par
	quinzaine, comptée depuis sa première occurrence, le 2 décembre. Son alternance est rangée dans sa colonne
	properties, sous la clé « alternation ». Décembre 2026 a cinq mercredis : le 2, le 9, le 16, le 23 et le 30.

	Contexte:
		Étant donné les événements :
			| nom           | priorité | début            | fin              | jours     |
			| Mercredi soir | show     | 2026-12-02 20:00 | 2026-12-02 21:00 | wednesday |
			| Sonia         | show     | 2026-11-30 10:00 | 2026-11-30 11:00 | monday    |
			| Les ahuris    | show     | 2026-12-01 10:00 | 2026-12-01 11:00 |           |
			| Zôtre         | show     | 2026-12-01 14:00 | 2026-12-01 15:00 |           |
			| Matinale      | show     | 2026-12-01 07:00 | 2026-12-01 09:00 |           |
			| Panne         | fallback |                  |                  |           |
		Et le plugin des émissions en alternance, chargé

	# ─── La grille ─────────────────────────────────────────

	Scénario: Chaque mercredi joue l'émission de sa semaine dans le mois, sous son nom
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Quand la grille est lue
		Alors le calendrier de décembre 2026 montre « Sonia » le 2, « Les ahuris » le 9, « Zôtre » le 16, « Les ahuris » le 23, « Sonia » le 30

	Scénario: Un passage choisi à la main l'emporte sur la rotation
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Et le passage du « 2026-12-16 » de « Mercredi soir » choisi : « Sonia »
		Quand la grille est lue
		Alors le calendrier de décembre 2026 montre « Sonia » le 2, « Les ahuris » le 9, « Sonia » le 16, « Les ahuris » le 23, « Sonia » le 30

	Scénario: Par quinzaine, deux émissions alternent une semaine sur deux, depuis la première occurrence, même d'un mois à l'autre
		Étant donné l'alternance par quinzaine de « Mercredi soir » : « Sonia », « Zôtre »
		Quand la grille est lue
		Alors le calendrier de décembre 2026 montre « Sonia » le 2, « Zôtre » le 9, « Sonia » le 16, « Zôtre » le 23, « Sonia » le 30
		Et le calendrier de janvier 2027 montre « Zôtre » le 6, « Sonia » le 13, « Zôtre » le 20, « Sonia » le 27

	Scénario: Par quinzaine aussi, un passage choisi à la main l'emporte
		Étant donné l'alternance par quinzaine de « Mercredi soir » : « Sonia », « Zôtre »
		Et le passage du « 2026-12-16 » de « Mercredi soir » choisi : « Zôtre »
		Quand la grille est lue
		Alors le calendrier de décembre 2026 montre « Sonia » le 2, « Zôtre » le 9, « Zôtre » le 16, « Zôtre » le 23, « Sonia » le 30

	Plan du scénario: Le rang d'un jour dans sa quinzaine, depuis la première occurrence
		Alors depuis le « 2026-12-02 », le « <jour> » est la <rang> semaine de sa quinzaine

		Exemples:
			| jour       | rang |
			| 2026-12-02 | 1    |
			| 2026-12-08 | 1    |
			| 2026-12-09 | 2    |
			| 2026-12-16 | 1    |
			| 2027-01-06 | 2    |

	Scénario: Une semaine sans émission dans la rotation joue l'événement méta lui-même
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », —
		Quand la grille est lue
		Alors le calendrier de décembre 2026 montre « Sonia » le 2, « Les ahuris » le 9, « Zôtre » le 16, « Les ahuris » le 23, « Mercredi soir » le 30

	Scénario: Les émissions de l'alternance sont hors grille : leurs propres dates ne jouent pas
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Quand la grille est lue
		Alors la grille lue a « Mercredi soir », « Matinale »

	Scénario: Une émission choisie qui n'est pas parmi celles de l'alternance est ignorée
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Et le passage du « 2026-12-16 » de « Mercredi soir » choisi : « Matinale »
		Quand la grille est lue
		Alors le calendrier de décembre 2026 montre « Sonia » le 2, « Les ahuris » le 9, « Zôtre » le 16, « Les ahuris » le 23, « Sonia » le 30

	Plan du scénario: Le rang d'un jour parmi les mêmes jours de son mois
		Alors le « <jour> » est le <rang> de son mois

		Exemples:
			| jour       | rang |
			| 2026-12-02 | 1    |
			| 2026-12-07 | 1    |
			| 2026-12-08 | 2    |
			| 2026-12-28 | 4    |
			| 2026-12-29 | 5    |
			| 2026-12-31 | 5    |

	# ─── La fiche de l'événement méta ──────────────────────

	Scénario: La fiche de l'événement méta montre ses émissions, leur rotation et ses prochains passages
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », —
		Et le passage du « 2026-12-16 » de « Mercredi soir » choisi : « Sonia »
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Alors la section est cochée, et remplace la liste de lecture
		Et son rythme est « Par mois, selon la semaine du mois », parmi « Par mois, selon la semaine du mois », « Par quinzaine, une semaine sur deux »
		Et elle propose les émissions « Les ahuris », « Matinale », « Sonia », « Zôtre », dont « Les ahuris », « Sonia », « Zôtre » sont cochées
		Et sa rotation est :
			| rang                  | émission                |
			| 1er mercredi du mois  | Sonia                   |
			| 2e mercredi du mois   | Les ahuris              |
			| 3e mercredi du mois   | Zôtre                   |
			| 4e mercredi du mois   | Les ahuris              |
			| 5e mercredi du mois   | — l'événement lui-même  |
		Et ses 8 prochains passages commencent par :
			| passage                       | émission                            |
			| mercredi 02/12/2026 à 20:00   | Selon la rotation : Sonia           |
			| mercredi 09/12/2026 à 20:00   | Selon la rotation : Les ahuris      |
			| mercredi 16/12/2026 à 20:00   | Sonia                               |
			| mercredi 23/12/2026 à 20:00   | Selon la rotation : Les ahuris      |
			| mercredi 30/12/2026 à 20:00   | Selon la rotation : — l'événement lui-même |
		Et la section ne signale aucun changement

	Scénario: Choisir un passage, puis enregistrer, range l'alternance sous la clé du plugin, sans toucher au reste
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Et la propriété « note » de « Mercredi soir » : « à relire »
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Et je choisis « Zôtre » pour le passage du « 2026-12-09 »
		Alors la section signale un changement
		Quand la section s'enregistre
		Alors « Mercredi soir » a pour propriétés :
			"""
			{"note": "à relire", "alternation": {"mode": "monthly", "candidates": [2, 3, 4], "rotation": {"1": 2, "2": 3, "3": 4, "4": 3, "5": 2}, "choices": {"2026-12-09": 4}}}
			"""

	Scénario: Par quinzaine, la fiche ne montre que deux semaines, chacune avec son prochain passage
		Étant donné l'alternance par quinzaine de « Mercredi soir » : « Sonia », « Zôtre »
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-12-05 10:00 »
		Alors son rythme est « Par quinzaine, une semaine sur deux »
		Et sa rotation est :
			| rang                                         | émission |
			| 1re semaine de la quinzaine, dont le 16/12/2026 | Sonia    |
			| 2e semaine de la quinzaine, dont le 09/12/2026  | Zôtre    |
		Et ses 8 prochains passages commencent par :
			| passage                       | émission                    |
			| mercredi 09/12/2026 à 20:00   | Selon la rotation : Zôtre   |
			| mercredi 16/12/2026 à 20:00   | Selon la rotation : Sonia   |

	Scénario: Passer du mois à la quinzaine change la rotation, et s'enregistre
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Et je choisis le rythme « Par quinzaine, une semaine sur deux »
		Alors la section signale un changement
		Et la rotation montre 2 semaines
		Et le passage du « 2026-12-09 » est « Selon la rotation : Les ahuris »
		Quand la section s'enregistre
		Alors « Mercredi soir » a pour propriétés :
			"""
			{"alternation": {"mode": "fortnightly", "candidates": [2, 3, 4], "rotation": {"1": 2, "2": 3}, "choices": {}}}
			"""

	Scénario: Créer une émission sur le créneau partagé l'ajoute, cochée, et l'enregistre avec l'événement méta
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Alors le bouton « Créer une émission sur ce créneau partagé » est à côté de « Émissions qui se partagent le créneau »
		Quand je crée l'émission « Clara » sur ce créneau partagé
		Alors elle propose les émissions « Les ahuris », « Matinale », « Sonia », « Zôtre », « Clara (à créer) », dont « Les ahuris », « Sonia », « Zôtre », « Clara (à créer) » sont cochées
		Et la section signale un changement
		Et l'événement « Clara » n'existe pas encore
		Quand je choisis « Clara (à créer) » pour le 5e rang de la rotation
		Et la section s'enregistre
		Alors l'événement « Clara » est une émission, de « 2026-12-02 20:00 » à « 2026-12-02 21:00 », sans jour de récurrence
		Et l'alternance de « Mercredi soir » a « Clara » parmi ses émissions, et au 5e rang de sa rotation
		Quand la grille est lue
		Alors le calendrier de décembre 2026 montre « Sonia » le 2, « Les ahuris » le 9, « Zôtre » le 16, « Les ahuris » le 23, « Clara » le 30

	Scénario: L'émission créée sur le créneau partagé prend son nom pour nom public, et hérite de l'événement méta
		Étant donné « Mercredi soir » masque ses sonores, passe en fin de liste au secours « Panne », et a pour secours de stream tombé « Panne »
		Et l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Et je crée l'émission « Clara » sur ce créneau partagé
		Et la section s'enregistre
		Alors l'événement « Clara » a pour nom public « Clara »
		Et « Clara » masque ses sonores, passe en fin de liste au secours « Panne », et a pour secours de stream tombé « Panne »

	Scénario: Sans masquage, fin de liste ni secours, l'émission créée n'en a pas non plus
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Et je crée l'émission « Clara » sur ce créneau partagé
		Et la section s'enregistre
		Alors « Clara » laisse décider le masquage, rejoue sa liste, sans secours
		Et « Clara » a pour propriétés :
			"""
			{}
			"""

	Scénario: Une émission à créer au nom déjà pris n'est pas ajoutée, et la section dit pourquoi
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Et je crée l'émission « Matinale » sur ce créneau partagé
		Alors elle propose les émissions « Les ahuris », « Matinale », « Sonia », « Zôtre », dont aucune n'est cochée
		Et elle dit, sous ses émissions, « Un autre événement s'appelle déjà « Matinale ». »

	Scénario: La même émission à créer n'est ajoutée qu'une fois
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Et je crée l'émission « Clara » sur ce créneau partagé
		Et je crée l'émission « Clara » sur ce créneau partagé
		Alors elle propose les émissions « Les ahuris », « Matinale », « Sonia », « Zôtre », « Clara (à créer) », dont « Clara (à créer) » sont cochées
		Et elle dit, sous ses émissions, « Un autre événement s'appelle déjà « Clara ». »

	Scénario: Abandonner la création ne change rien
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Et j'abandonne la création d'une émission sur ce créneau partagé
		Alors elle propose les émissions « Les ahuris », « Matinale », « Sonia », « Zôtre », dont aucune n'est cochée
		Et la section ne signale aucun changement

	Scénario: Retirer une émission la retire de la rotation, qui revient à l'événement lui-même
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Et je décoche l'émission « Sonia »
		Alors la rotation est « — l'événement lui-même », « Les ahuris », « Zôtre », « Les ahuris », « — l'événement lui-même »

	Scénario: Sans émission cochée, l'enregistrement est refusé
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Et je coche « Émissions en alternance »
		Alors la section remplace la liste de lecture
		Et la section refuse l'enregistrement : « Choisissez au moins une émission qui partage le créneau. »

	Scénario: Décocher les émissions en alternance retire l'alternance, et rend la liste de lecture
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Et je décoche « Émissions en alternance »
		Alors la section ne remplace plus la liste de lecture
		Quand la section s'enregistre
		Alors « Mercredi soir » a pour propriétés :
			"""
			{}
			"""

	Scénario: Pour un nouvel événement, les passages à venir attendent son enregistrement
		Quand j'ouvre la section des émissions en alternance d'un nouvel événement, le « 2026-11-23 10:00 »
		Alors la section n'est pas cochée
		Et elle dit « Enregistrez l'événement pour voir ses passages à venir. »
		Et sa rotation est par « 1re semaine du mois », « 2e semaine du mois », « 3e semaine du mois », « 4e semaine du mois », « 5e semaine du mois »

	# ─── La fiche d'une émission de l'alternance ───────────

	Scénario: La fiche d'une émission de l'alternance dit le créneau qu'elle partage, à la place de l'encadré de sa grille
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Et le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-11-23 10:00:00 »
		Et la section des émissions en alternance, dans la fiche d'un événement
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Les ahuris »
		Alors la fiche montre, à la place de l'encadré de la grille, « Cette émission partage le créneau « Mercredi soir », le mercredi de 20h à 21h, avec les émissions « Sonia » et « Zôtre ». »
		Quand j'ouvre la fiche de l'événement « Matinale »
		Alors la fiche montre l'encadré de la grille

	Scénario: Avec une seule autre émission, la fiche la nomme
		Étant donné l'alternance par quinzaine de « Mercredi soir » : « Sonia », « Zôtre »
		Quand j'ouvre la section des émissions en alternance de « Sonia », le « 2026-11-23 10:00 »
		Alors la section remplace l'encadré de la grille par « Cette émission partage le créneau « Mercredi soir », le mercredi de 20h à 21h, avec l'émission « Zôtre ». »

	Scénario: Un événement méta qui revient deux jours par semaine, à la demi-heure, les dit
		Étant donné « Mercredi soir » revient le lundi et le mercredi, de 20:30 à 21:00
		Et l'alternance par quinzaine de « Mercredi soir » : « Sonia », « Zôtre »
		Quand j'ouvre la section des émissions en alternance de « Zôtre », le « 2026-11-23 10:00 »
		Alors la section remplace l'encadré de la grille par « Cette émission partage le créneau « Mercredi soir », le lundi et le mercredi de 20h30 à 21h, avec l'émission « Sonia ». »

	Scénario: La fiche de l'événement méta, ou d'un événement hors de toute alternance, garde l'encadré de sa grille
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Les ahuris », « Zôtre », « Les ahuris », « Sonia »
		Quand j'ouvre la section des émissions en alternance de « Mercredi soir », le « 2026-11-23 10:00 »
		Alors la section laisse l'encadré de la grille
		Quand j'ouvre la section des émissions en alternance de « Matinale », le « 2026-11-23 10:00 »
		Alors la section laisse l'encadré de la grille

	Scénario: Une émission retirée de l'alternance retrouve l'encadré de sa grille
		Étant donné l'alternance de « Mercredi soir » : « Sonia », « Sonia », « Zôtre », « Sonia », « Sonia »
		Quand j'ouvre la section des émissions en alternance de « Les ahuris », le « 2026-11-23 10:00 »
		Alors la section laisse l'encadré de la grille

	# ─── Le plugin ─────────────────────────────────────────

	Plan du scénario: Le plugin s'accroche à la grille de chaque binaire qui la lit, et à la fiche de l'interface
		Quand le plugin des émissions en alternance s'enregistre dans « <binaire> »
		Alors il s'abonne seulement à <points>

		Exemples:
			| binaire          | points                                                  |
			| Machin_player    | « grid.substitutions »                                  |
			| Machin_intranet  | « grid.substitutions »                                  |
			| Machin_interface | « grid.substitutions », « interface.event_card »        |
