# language: fr
Fonctionnalité: Les émissions en alternance : un événement méta joue, selon la semaine du mois, l'une de ses émissions
	En tant que responsable d'antenne,
	je veux identifier les émissions qui se partagent le même créneau horaire en fonction de la semaine,
	afin de donner la bonne indication sur le calendrier, sur l'affichage public et jouer le bon sonore programmé.

	https://github.com/dascritch/machincast/issues/609, ticket enfant de
	https://github.com/dascritch/machincast/issues/606. « Mercredi soir », le mercredi de 20 h à 21 h, est l'événement
	méta : il fait jouer « Sonia », « Les ahuris » ou « Zôtre », selon la semaine du mois. Son alternance est rangée
	dans sa colonne properties, sous la clé « alternation ». Décembre 2026 a cinq mercredis : le 2, le 9, le 16, le 23
	et le 30.

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
			{"note": "à relire", "alternation": {"candidates": [2, 3, 4], "rotation": {"1": 2, "2": 3, "3": 4, "4": 3, "5": 2}, "choices": {"2026-12-09": 4}}}
			"""

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

	# ─── Le plugin ─────────────────────────────────────────

	Plan du scénario: Le plugin s'accroche à la grille de chaque binaire qui la lit, et à la fiche de l'interface
		Quand le plugin des émissions en alternance s'enregistre dans « <binaire> »
		Alors il s'abonne seulement à <points>

		Exemples:
			| binaire          | points                                                  |
			| Machin_player    | « grid.substitutions »                                  |
			| Machin_intranet  | « grid.substitutions »                                  |
			| Machin_interface | « grid.substitutions », « interface.event_card »        |
