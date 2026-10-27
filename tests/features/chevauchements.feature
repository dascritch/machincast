# language: fr
Fonctionnalité: Chevauchement de deux événements de même priorité
	En tant que programmateur de l'antenne,
	je veux qu'un événement ne puisse pas en chevaucher un autre de même priorité,
	afin que la grille dise sans ambiguïté ce qui passe à l'antenne.

	https://github.com/dascritch/machincast/issues/32, spec § 4.1. La fiche d'un événement refuse de l'enregistrer s'il
	chevauche un autre événement de même priorité (fiche_evenement.feature) : la grille donne le premier instant
	commun. Une occurrence sans fin ne compte que par son début. Un fil musical permanent sert de fond, et ne chevauche
	rien ; un événement de secours est hors grille. Les heures sont en heure de Paris. Le 12 octobre 2026 est un lundi.

	Contexte:
		Étant donné le poste à l'heure de Paris

	Plan du scénario: Deux événements de même priorité se chevauchent dès qu'un instant leur est commun
		Étant donné les événements à comparer :
			| nom   | priorité   | début   | fin   | jours   |
			| Placé | <priorité> | <début> | <fin> | <jours> |
			| Autre | <autre>    | <début autre> | <fin autre> | <jours autre> |
		Alors « Placé » chevauche <verdict>

		Exemples: ponctuels
			| priorité | début            | fin              | jours | autre    | début autre      | fin autre        | jours autre | verdict                                 |
			| emission | 2026-10-14 20:00 | 2026-10-14 22:00 |       | emission | 2026-10-14 21:00 | 2026-10-14 23:00 |             | « Autre » le « 2026-10-14 21:00 »       |
			| emission | 2026-10-14 21:00 | 2026-10-14 23:00 |       | emission | 2026-10-14 20:00 | 2026-10-14 22:00 |             | « Autre » le « 2026-10-14 21:00 »       |
			| emission | 2026-10-14 20:00 | 2026-10-14 22:00 |       | emission | 2026-10-14 20:30 | 2026-10-14 21:00 |             | « Autre » le « 2026-10-14 20:30 »       |
			| emission | 2026-10-14 20:00 | 2026-10-14 22:00 |       | emission | 2026-10-14 22:00 | 2026-10-14 23:00 |             | rien                                    |
			| emission | 2026-10-14 22:00 | 2026-10-14 23:00 |       | emission | 2026-10-14 20:00 | 2026-10-14 22:00 |             | rien                                    |
			| emission | 2026-10-14 20:00 | 2026-10-14 22:00 |       | special  | 2026-10-14 21:00 | 2026-10-14 23:00 |             | rien                                    |
			| special  | 2026-10-14 20:00 | 2026-10-14 22:00 |       | special  | 2026-10-14 21:00 | 2026-10-14 23:00 |             | « Autre » le « 2026-10-14 21:00 »       |

		Exemples: récurrents
			| priorité    | début            | fin              | jours            | autre       | début autre      | fin autre        | jours autre                                               | verdict                            |
			| emission    | 2026-10-12 21:00 | 2026-10-12 23:00 | lundi, mercredi  | emission    | 2026-10-16 22:00 | 2026-10-16 22:30 |                                                           | rien                               |
			| emission    | 2026-10-12 21:00 | 2026-10-12 23:00 | lundi, mercredi  | emission    | 2026-11-04 22:00 | 2026-11-04 22:30 |                                                           | « Autre » le « 2026-11-04 22:00 »  |
			| emission    | 2026-10-12 21:00 | 2026-10-12 23:00 | lundi            | emission    | 2026-10-05 21:30 | 2026-10-05 22:00 |                                                           | rien                               |
			| emission    | 2026-10-12 21:00 | 2026-10-12 23:00 | mardi            | emission    | 2026-10-12 22:00 | 2026-10-12 22:30 |                                                           | « Autre » le « 2026-10-12 22:00 »  |
			| emission    | 2026-10-12 21:00 | 2026-10-12 23:00 | lundi            | emission    | 2026-10-13 22:00 | 2026-10-13 23:00 | mardi, jeudi                                              | rien                               |
			| emission    | 2026-10-12 21:00 | 2026-10-12 23:00 | lundi            | emission    | 2026-10-13 22:00 | 2026-10-13 23:00 | lundi, jeudi                                              | « Autre » le « 2026-10-19 22:00 »  |
			| emission    | 2026-10-12 23:00 | 2026-10-13 01:00 | lundi            | emission    | 2026-10-13 00:30 | 2026-10-13 02:00 | mardi                                                     | « Autre » le « 2026-10-13 00:30 »  |
			| emission    | 2026-10-12 10:00 | 2026-10-15 10:00 | lundi            | emission    | 2026-10-21 12:00 | 2026-10-21 13:00 |                                                           | « Autre » le « 2026-10-21 12:00 »  |
			| fil_musical | 2026-10-12 00:00 | 2026-10-12 06:00 | lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche | fil_musical | 2026-10-12 06:00 | 2026-10-13 00:00 | lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche | rien |
			| fil_musical | 2026-10-12 00:00 | 2026-10-12 07:00 | lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche | fil_musical | 2026-10-17 06:00 | 2026-10-18 00:00 | samedi                                                    | « Autre » le « 2026-10-17 06:00 »  |

		Exemples: sans fin
			| priorité    | début            | fin              | jours | autre       | début autre      | fin autre        | jours autre | verdict                            |
			| emission    | 2026-10-14 20:00 |                  |       | emission    | 2026-10-14 21:00 | 2026-10-14 22:00 |             | rien                               |
			| emission    | 2026-10-14 21:30 |                  |       | emission    | 2026-10-14 21:00 | 2026-10-14 22:00 |             | « Autre » le « 2026-10-14 21:30 »  |
			| emission    | 2026-10-14 21:00 | 2026-10-14 22:00 |       | emission    | 2026-10-14 21:30 |                  |             | « Autre » le « 2026-10-14 21:30 »  |
			| emission    | 2026-10-14 20:00 | 2026-10-14 21:00 |       | emission    | 2026-10-14 21:30 |                  |             | rien                               |
			| emission    | 2026-10-14 22:00 |                  |       | emission    | 2026-10-14 21:00 | 2026-10-14 22:00 |             | rien                               |
			| emission    | 2026-10-14 21:00 |                  |       | emission    | 2026-10-14 21:00 |                  |             | « Autre » le « 2026-10-14 21:00 »  |
			| emission    | 2026-10-14 21:00 |                  |       | emission    | 2026-10-14 21:01 |                  |             | rien                               |
			| emission    | 2026-10-12 07:00 |                  | lundi | emission    | 2026-10-19 06:30 | 2026-10-19 08:00 |             | « Autre » le « 2026-10-19 07:00 »  |
			| fil_musical | 2026-10-12 06:00 |                  |       | fil_musical | 2026-10-14 05:00 | 2026-10-14 07:00 | mercredi    | rien                               |

		Exemples: fil permanent
			| priorité    | début            | fin              | jours | autre       | début autre      | fin autre        | jours autre | verdict |
			| fil_musical |                  |                  |       | fil_musical | 2026-10-12 00:00 | 2026-10-12 06:00 | lundi       | rien    |
			| fil_musical | 2026-10-12 00:00 | 2026-10-12 06:00 | lundi | fil_musical |                  |                  |             | rien    |
			| fil_musical |                  |                  |       | fil_musical |                  |                  |             | rien    |

	Scénario: Le premier événement chevauché est donné, au plus tôt
		Étant donné les événements à comparer :
			| nom      | priorité | début            | fin              | jours  |
			| Placé    | emission | 2026-10-12 20:00 | 2026-10-12 22:00 | lundi  |
			| Lointain | emission | 2026-12-07 21:00 | 2026-12-07 21:30 |        |
			| Proche   | emission | 2026-10-26 21:00 | 2026-10-26 23:00 |        |
			| Ailleurs | special  | 2026-10-12 20:00 | 2026-10-12 22:00 |        |
		Alors « Placé » chevauche « Proche » le « 2026-10-26 21:00 »

	Plan du scénario: Ce qui chevauche avant un instant donné ne compte pas
		https://github.com/dascritch/machincast/issues/271 : la fiche d'un événement ne compte que les chevauchements à
		partir de maintenant ; ceux de la grille déjà diffusée ne bloquent pas l'enregistrement. Un chevauchement en
		cours à cet instant compte, à partir de lui.

		Étant donné les événements à comparer :
			| nom   | priorité | début   | fin   | jours   |
			| Placé | emission | <début> | <fin> | <jours> |
			| Autre | emission | <début autre> | <fin autre> | <jours autre> |
		Alors à partir du « <depuis> », « Placé » chevauche <verdict>

		Exemples:
			| début            | fin              | jours  | début autre      | fin autre        | jours autre  | depuis           | verdict                           |
			| 2026-10-14 20:00 | 2026-10-14 22:00 |        | 2026-10-14 21:00 | 2026-10-14 23:00 |              | 2026-10-14 20:00 | « Autre » le « 2026-10-14 21:00 » |
			| 2026-10-14 20:00 | 2026-10-14 22:00 |        | 2026-10-14 21:00 | 2026-10-14 23:00 |              | 2026-10-14 21:30 | « Autre » le « 2026-10-14 21:30 » |
			| 2026-10-14 20:00 | 2026-10-14 22:00 |        | 2026-10-14 21:00 | 2026-10-14 23:00 |              | 2026-10-14 22:00 | rien                              |
			| 2026-10-14 20:00 | 2026-10-14 22:00 |        | 2026-10-14 21:00 | 2026-10-14 23:00 |              | 2026-10-20 00:00 | rien                              |
			| 2026-10-12 21:00 | 2026-10-12 23:00 | lundi  | 2026-10-12 22:00 | 2026-10-12 22:30 |              | 2026-10-13 00:00 | rien                              |
			| 2026-10-12 21:00 | 2026-10-12 23:00 | lundi  | 2026-10-13 22:00 | 2026-10-13 23:00 | lundi, jeudi | 2026-11-01 00:00 | « Autre » le « 2026-11-02 22:00 » |
			| 2026-10-12 21:00 | 2026-10-12 23:00 | lundi  | 2026-10-30 22:00 | 2026-10-30 22:30 |              | 2026-10-20 00:00 | rien                              |
			| 2026-10-12 21:00 | 2026-10-12 23:00 | lundi  | 2026-11-09 22:00 | 2026-11-09 22:30 |              | 2026-10-20 00:00 | « Autre » le « 2026-11-09 22:00 » |
			| 2026-10-14 21:00 |                  |        | 2026-10-14 21:00 |                  |              | 2026-10-14 21:00 | « Autre » le « 2026-10-14 21:00 » |
			| 2026-10-14 21:00 |                  |        | 2026-10-14 21:00 |                  |              | 2026-10-14 21:01 | rien                              |
