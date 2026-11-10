# language: fr
Fonctionnalité: Détermination de l'événement actif
	En tant que programmateur de l'antenne,
	je veux que le binaire sache à tout instant quel événement doit être diffusé,
	afin que la grille programmée soit respectée.

	https://github.com/dascritch/machincast/issues/12 — spec § 4.1. Le poste travaille en heure locale, celle de
	Paris : un événement garde son heure d'un jour à l'autre, même au changement d'heure. Les heures sans décalage
	sont en heure de Paris. Le 12 octobre 2026 est un lundi.

	Contexte:
		Étant donné le poste à l'heure de Paris

	# ─── Bases ─────────────────────────────────────────────────

	Scénario: Sans événement, rien n'est actif
		Étant donné aucun événement
		Et l'heure « 2026-10-14 12:00 »
		Alors aucun événement n'est actif

	Scénario: Un fil musical sans dates est permanent
		Étant donné les événements :
			| nom      | priorité               | début | fin | jours | modifié          |
			| Continue | background_programming |       |     |       | 2026-10-01 10:00 |
		Alors l'événement actif est « Continue » à chacune de ces heures :
			| heure            |
			| 2000-01-01 00:00 |
			| 2026-10-14 12:00 |
			| 2040-12-31 23:59 |

	Scénario: Un événement ponctuel est actif de son début, inclus, à sa fin, exclue
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours | modifié          |
			| Continue | background_programming |                  |                  |       | 2026-10-01 10:00 |
			| Concert  | show                   | 2026-10-14 20:00 | 2026-10-14 22:00 |       | 2026-10-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 19:59 | Continue |
			| 2026-10-14 20:00 | Concert  |
			| 2026-10-14 21:59 | Concert  |
			| 2026-10-14 22:00 | Continue |
			| 2026-10-21 20:30 | Continue |

	Scénario: Les priorités départagent les événements qui se chevauchent : spécial, puis émission, puis fil musical
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours | modifié          |
			| Continue | background_programming |                  |                  |       | 2026-10-01 10:00 |
			| Magazine | show                   | 2026-10-14 18:00 | 2026-10-14 20:00 |       | 2026-10-01 10:00 |
			| Flash    | special                | 2026-10-14 19:00 | 2026-10-14 19:10 |       | 2026-09-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 18:30 | Magazine |
			| 2026-10-14 19:05 | Flash    |
			| 2026-10-14 19:10 | Magazine |
			| 2026-10-14 20:00 | Continue |

	Scénario: Un imprévu passe avant tout autre événement, même un spécial
		https://github.com/dascritch/machincast/issues/402 : imprévu, spécial, émission, fil musical, secours.

		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours | modifié          |
			| Continue | background_programming |                  |                  |       | 2026-10-01 10:00 |
			| Magazine | show                   | 2026-10-14 18:00 | 2026-10-14 20:00 |       | 2026-10-01 10:00 |
			| Flash    | special                | 2026-10-14 19:00 | 2026-10-14 19:10 |       | 2026-11-01 10:00 |
			| Alerte   | breaking               | 2026-10-14 19:02 | 2026-10-14 19:05 |       | 2026-09-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 19:01 | Flash    |
			| 2026-10-14 19:02 | Alerte   |
			| 2026-10-14 19:04 | Alerte   |
			| 2026-10-14 19:05 | Flash    |

	# ─── Récurrence ────────────────────────────────────────────

	Scénario: Un événement récurrent revient les jours cochés, à partir de sa première occurrence
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours                     | modifié          |
			| Continue | background_programming |                  |                  |                           | 2026-10-01 10:00 |
			| Magazine | show                   | 2026-10-12 21:00 | 2026-10-12 23:00 | monday, wednesday, friday | 2026-10-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-09 21:30 | Continue |
			| 2026-10-12 21:30 | Magazine |
			| 2026-10-13 21:30 | Continue |
			| 2026-10-14 21:30 | Magazine |
			| 2026-10-16 22:59 | Magazine |
			| 2026-10-16 23:00 | Continue |
			| 2027-03-01 21:00 | Magazine |

	Scénario: Un événement qui passe minuit couvre la fin de sa nuit
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours  | modifié          |
			| Continue | background_programming |                  |                  |        | 2026-10-01 10:00 |
			| Nocturne | show                   | 2026-10-12 23:00 | 2026-10-13 01:00 | monday | 2026-10-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-12 23:30 | Nocturne |
			| 2026-10-13 00:30 | Nocturne |
			| 2026-10-13 01:00 | Continue |
			| 2026-10-14 00:30 | Continue |
			| 2026-10-19 23:00 | Nocturne |
			| 2026-10-20 00:59 | Nocturne |

	Scénario: Plusieurs fils musicaux se relaient selon l'heure
		Étant donné les événements :
			| nom  | priorité               | début            | fin              | jours                                                          | modifié          |
			| Nuit | background_programming | 2026-10-12 00:00 | 2026-10-12 06:00 | monday, tuesday, wednesday, thursday, friday, saturday, sunday | 2026-10-01 10:00 |
			| Jour | background_programming | 2026-10-12 06:00 | 2026-10-13 00:00 | monday, tuesday, wednesday, thursday, friday, saturday, sunday | 2026-10-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif |
			| 2026-10-14 05:59 | Nuit  |
			| 2026-10-14 06:00 | Jour  |
			| 2026-10-14 23:59 | Jour  |
			| 2026-10-15 00:00 | Nuit  |

	Scénario: Un fil musical permanent sert de fond, là où aucun autre fil musical ne couvre l'heure
		# https://github.com/dascritch/machincast/issues/32 : modifié en dernier, il ne l'emporte pas pour autant.
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours                                                          | modifié          |
			| Nuit     | background_programming | 2026-10-12 00:00 | 2026-10-12 06:00 | monday, tuesday, wednesday, thursday, friday, saturday, sunday | 2026-10-01 10:00 |
			| Continue | background_programming |                  |                  |                                                                | 2026-10-02 10:00 |
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-11 23:59 | Continue |
			| 2026-10-14 05:59 | Nuit     |
			| 2026-10-14 06:00 | Continue |
			| 2026-10-15 00:00 | Nuit     |

	# ─── Événements sans fin ───────────────────────────────────

	Scénario: Une émission sans fin reste active jusqu'à ce que sa liste soit épuisée
		Étant donné les événements :
			| nom      | priorité               | début            | fin | jours | modifié          |
			| Continue | background_programming |                  |     |       | 2026-10-01 10:00 |
			| Direct   | show                   | 2026-10-14 20:00 |     |       | 2026-10-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 19:59 | Continue |
			| 2026-10-14 20:00 | Direct   |
			| 2026-10-15 03:00 | Direct   |
		Quand l'occurrence de « Direct » commencée le « 2026-10-14 20:00 » se termine, sa liste épuisée
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-15 03:00 | Continue |

	Scénario: Une émission sans fin laisse la place à une émission qui commence après elle, puis reprend
		# https://github.com/dascritch/machincast/issues/32 : modifiée en dernier, elle ne l'emporte pas pour autant.
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours | modifié          |
			| Continue | background_programming |                  |                  |       | 2026-10-01 10:00 |
			| Magazine | show                   | 2026-10-14 21:00 | 2026-10-14 22:00 |       | 2026-10-01 10:00 |
			| Direct   | show                   | 2026-10-14 20:00 |                  |       | 2026-10-02 10:00 |
			| Tardif   | show                   | 2026-10-14 23:00 |                  |       | 2026-10-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 20:30 | Direct   |
			| 2026-10-14 21:30 | Magazine |
			| 2026-10-14 22:30 | Direct   |
			| 2026-10-14 23:30 | Tardif   |

	Scénario: Une émission récurrente sans fin reprend à sa prochaine occurrence, même si la précédente est terminée
		Étant donné les événements :
			| nom      | priorité               | début            | fin | jours  | modifié          |
			| Continue | background_programming |                  |     |        | 2026-10-01 10:00 |
			| Matinale | show                   | 2026-10-12 07:00 |     | monday | 2026-10-01 10:00 |
		Quand l'occurrence de « Matinale » commencée le « 2026-10-12 07:00 » se termine, sa liste épuisée
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-12 09:00 | Continue |
			| 2026-10-19 06:59 | Continue |
			| 2026-10-19 07:00 | Matinale |

	# ─── Conflit ───────────────────────────────────────────────

	Scénario: Deux événements de même priorité qui se chevauchent : le dernier modifié en base l'emporte
		Étant donné les événements :
			| nom     | priorité | début            | fin              | jours | modifié          |
			| Premier | show     | 2026-10-14 20:00 | 2026-10-14 22:00 |       | 2026-10-02 10:00 |
			| Second  | show     | 2026-10-14 21:00 | 2026-10-14 23:00 |       | 2026-10-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif   |
			| 2026-10-14 20:30 | Premier |
			| 2026-10-14 21:30 | Premier |
			| 2026-10-14 22:30 | Second  |

	# ─── Changement d'heure ────────────────────────────────────

	Scénario: Un événement quotidien garde son heure murale au changement d'heure
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours                                                          | modifié          |
			| Continue | background_programming |                  |                  |                                                                | 2026-10-01 10:00 |
			| Journal  | show                   | 2026-03-01 21:00 | 2026-03-01 22:00 | monday, tuesday, wednesday, thursday, friday, saturday, sunday | 2026-02-01 10:00 |
		Alors l'événement actif est :
			| heure                  | actif    |
			| 2026-03-28 21:30+01:00 | Journal  |
			| 2026-03-29 21:30+02:00 | Journal  |
			| 2026-03-29 22:30+02:00 | Continue |
			| 2026-10-24 21:30+02:00 | Journal  |
			| 2026-10-25 21:30+01:00 | Journal  |
			| 2026-10-25 20:30+01:00 | Continue |

	Scénario: Le fil de nuit couvre l'heure sautée et l'heure répétée
		Étant donné les événements :
			| nom  | priorité               | début            | fin              | jours                                                          | modifié          |
			| Nuit | background_programming | 2026-01-05 00:00 | 2026-01-05 06:00 | monday, tuesday, wednesday, thursday, friday, saturday, sunday | 2026-01-01 10:00 |
			| Jour | background_programming | 2026-01-05 06:00 | 2026-01-06 00:00 | monday, tuesday, wednesday, thursday, friday, saturday, sunday | 2026-01-01 10:00 |
		Alors l'événement actif est :
			| heure                  | actif |
			| 2026-03-29 01:59+01:00 | Nuit  |
			| 2026-03-29 03:00+02:00 | Nuit  |
			| 2026-03-29 05:59+02:00 | Nuit  |
			| 2026-03-29 06:00+02:00 | Jour  |
			| 2026-10-25 02:30+02:00 | Nuit  |
			| 2026-10-25 02:30+01:00 | Nuit  |
			| 2026-10-25 06:00+01:00 | Jour  |

	# ─── Sessions sautées (https://github.com/dascritch/machincast/issues/273) ───

	Scénario: Une session sautée n'est jamais active : le fil musical, ou ce qui joue sans elle, l'est
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours             | modifié          |
			| Continue | background_programming |                  |                  |                   | 2026-10-01 10:00 |
			| Magazine | show                   | 2026-10-12 21:00 | 2026-10-12 23:00 | monday, wednesday | 2026-10-01 10:00 |
			| Concert  | special                | 2026-10-14 22:00 | 2026-10-14 23:30 |                   | 2026-10-01 10:00 |
		Et la session du « 2026-10-14 » de « Magazine » est sautée
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-12 21:30 | Magazine |
			| 2026-10-14 21:30 | Continue |
			| 2026-10-14 22:30 | Concert  |
			| 2026-10-19 21:30 | Magazine |

	Scénario: Même sans récurrence, un événement dont la session est sautée n'est pas actif
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours | modifié          |
			| Continue | background_programming |                  |                  |       | 2026-10-01 10:00 |
			| Concert  | special                | 2026-10-14 22:00 | 2026-10-14 23:30 |       | 2026-10-01 10:00 |
		Et la session du « 2026-10-14 » de « Concert » est sautée
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 22:30 | Continue |

	Scénario: Une session sautée n'est pas un changement de la grille
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours             | modifié          |
			| Continue | background_programming |                  |                  |                   | 2026-10-01 10:00 |
			| Magazine | show                   | 2026-10-12 21:00 | 2026-10-12 23:00 | monday, wednesday | 2026-10-01 10:00 |
			| Concert  | special                | 2026-10-16 22:00 | 2026-10-16 23:30 |                   | 2026-10-01 10:00 |
		Et la session du « 2026-10-14 » de « Magazine » est sautée
		Et la session du « 2026-10-16 » de « Concert » est sautée
		Alors le prochain changement de la grille après le « 2026-10-13 12:00 » est le « 2026-10-19 21:00 »

	Scénario: Les sessions sautées se lisent en base avec les droits du binaire lecture
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours             | modifié          |
			| Continue | background_programming |                  |                  |                   | 2026-10-01 10:00 |
			| Magazine | show                   | 2026-10-12 21:00 | 2026-10-12 23:00 | monday, wednesday | 2026-10-01 10:00 |
		Et ces événements enregistrés en base
		Et la session du 2026-10-14 de l'événement « Magazine » est sautée
		Quand le binaire lecture lit la grille en base
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-12 21:30 | Magazine |
			| 2026-10-14 21:30 | Continue |

	# ─── Événement suivant, avancé (https://github.com/dascritch/machincast/issues/257) ───
	# L'événement suivant est la première occurrence qui commencera après l'instant et prendra l'antenne, en sept jours
	# au plus : un fil musical qui reprend, ou une occurrence déjà commencée qui réapparaît, n'en est pas un. Avancée,
	# cette occurrence est active dès maintenant, au-dessus de tout, jusqu'à son début prévu, où la grille la retrouve.

	Plan du scénario: L'événement suivant est la première occurrence à venir qui prendra l'antenne
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours  | modifié          |
			| Continue | background_programming |                  |                  |        | 2026-10-01 10:00 |
			| Journal  | show                   | 2026-10-14 12:00 | 2026-10-14 13:00 |        | 2026-10-01 10:00 |
			| Flash    | special                | 2026-10-14 11:30 | 2026-10-14 12:30 |        | 2026-10-01 10:00 |
			| Concert  | show                   | 2026-10-12 20:00 | 2026-10-12 22:00 | monday | 2026-10-01 10:00 |
		Alors après le « <instant> », l'événement suivant est <suivant>

		Exemples:
			| instant          | suivant                             |
			| 2026-10-14 10:00 | « Flash » du « 2026-10-14 11:30 »   |
			| 2026-10-14 11:45 | « Journal » du « 2026-10-14 12:00 » |
			| 2026-10-14 12:15 | « Concert » du « 2026-10-19 20:00 » |
			| 2026-10-14 12:45 | « Concert » du « 2026-10-19 20:00 » |
			| 2026-10-19 20:30 | « Concert » du « 2026-10-26 20:00 » |

	Scénario: Au-delà de sept jours, ou sans occurrence à venir, il n'y a pas d'événement suivant
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours | modifié          |
			| Continue | background_programming |                  |                  |       | 2026-10-01 10:00 |
			| Concert  | show                   | 2026-10-14 20:00 | 2026-10-14 22:00 |       | 2026-10-01 10:00 |
			| Gala     | special                | 2026-10-25 20:00 | 2026-10-25 22:00 |       | 2026-10-01 10:00 |
		Alors après le « 2026-10-14 21:00 », il n'y a pas d'événement suivant
		Et après le « 2026-10-18 20:00 », l'événement suivant est « Gala » du « 2026-10-25 20:00 »

	Scénario: Une session sautée n'est pas l'événement suivant
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours             | modifié          |
			| Continue | background_programming |                  |                  |                   | 2026-10-01 10:00 |
			| Concert  | show                   | 2026-10-12 20:00 | 2026-10-12 22:00 | monday, wednesday | 2026-10-01 10:00 |
		Et la session du « 2026-10-14 » de « Concert » est sautée
		Alors après le « 2026-10-13 12:00 », l'événement suivant est « Concert » du « 2026-10-19 20:00 »

	Scénario: Une occurrence avancée est active aussitôt, jusqu'à son début prévu, puis comme prévu
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours | modifié          |
			| Continue | background_programming |                  |                  |       | 2026-10-01 10:00 |
			| Flash    | special                | 2026-10-14 18:00 | 2026-10-14 19:30 |       | 2026-10-01 10:00 |
			| Concert  | show                   | 2026-10-14 20:00 | 2026-10-14 22:00 |       | 2026-10-01 10:00 |
		Et l'occurrence de « Concert » du « 2026-10-14 20:00 » avancée
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 19:00 | Concert  |
			| 2026-10-14 19:45 | Concert  |
			| 2026-10-14 20:00 | Concert  |
			| 2026-10-14 21:59 | Concert  |
			| 2026-10-14 22:00 | Continue |

	Scénario: Une occurrence avancée puis terminée plus tôt rend l'antenne à la grille
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours | modifié          |
			| Continue | background_programming |                  |                  |       | 2026-10-01 10:00 |
			| Concert  | show                   | 2026-10-14 20:00 | 2026-10-14 22:00 |       | 2026-10-01 10:00 |
		Et l'occurrence de « Concert » du « 2026-10-14 20:00 » avancée
		Quand l'occurrence de « Concert » commencée le « 2026-10-14 20:00 » se termine, sa liste épuisée
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 19:00 | Continue |
			| 2026-10-14 20:30 | Continue |

	# ─── Lecture de la grille en base ──────────────────────────

	Scénario: La grille est lue en base avec les droits du binaire lecture
		Étant donné les événements :
			| nom      | priorité               | début            | fin              | jours             | modifié          |
			| Continue | background_programming |                  |                  |                   | 2026-10-01 10:00 |
			| Magazine | show                   | 2026-10-12 21:00 | 2026-10-12 23:00 | monday, wednesday | 2026-10-01 10:00 |
		Et ces événements enregistrés en base
		Quand le binaire lecture lit la grille en base
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 21:30 | Magazine |
			| 2026-10-15 21:30 | Continue |
