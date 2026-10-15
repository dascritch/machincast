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
			| nom      | priorité    | début | fin | jours | modifié          |
			| Continue | fil_musical |       |     |       | 2026-10-01 10:00 |
		Alors l'événement actif est « Continue » à chacune de ces heures :
			| heure            |
			| 2000-01-01 00:00 |
			| 2026-10-14 12:00 |
			| 2040-12-31 23:59 |

	Scénario: Un événement ponctuel est actif de son début, inclus, à sa fin, exclue
		Étant donné les événements :
			| nom      | priorité    | début            | fin              | jours | modifié          |
			| Continue | fil_musical |                  |                  |       | 2026-10-01 10:00 |
			| Concert  | emission    | 2026-10-14 20:00 | 2026-10-14 22:00 |       | 2026-10-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 19:59 | Continue |
			| 2026-10-14 20:00 | Concert  |
			| 2026-10-14 21:59 | Concert  |
			| 2026-10-14 22:00 | Continue |
			| 2026-10-21 20:30 | Continue |

	Scénario: Les priorités départagent les événements qui se chevauchent : spécial, puis émission, puis fil musical
		Étant donné les événements :
			| nom      | priorité    | début            | fin              | jours | modifié          |
			| Continue | fil_musical |                  |                  |       | 2026-10-01 10:00 |
			| Magazine | emission    | 2026-10-14 18:00 | 2026-10-14 20:00 |       | 2026-10-01 10:00 |
			| Flash    | special     | 2026-10-14 19:00 | 2026-10-14 19:10 |       | 2026-09-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 18:30 | Magazine |
			| 2026-10-14 19:05 | Flash    |
			| 2026-10-14 19:10 | Magazine |
			| 2026-10-14 20:00 | Continue |

	# ─── Récurrence ────────────────────────────────────────────

	Scénario: Un événement récurrent revient les jours cochés, à partir de sa première occurrence
		Étant donné les événements :
			| nom      | priorité    | début            | fin              | jours                     | modifié          |
			| Continue | fil_musical |                  |                  |                           | 2026-10-01 10:00 |
			| Magazine | emission    | 2026-10-12 21:00 | 2026-10-12 23:00 | lundi, mercredi, vendredi | 2026-10-01 10:00 |
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
			| nom      | priorité    | début            | fin              | jours | modifié          |
			| Continue | fil_musical |                  |                  |       | 2026-10-01 10:00 |
			| Nocturne | emission    | 2026-10-12 23:00 | 2026-10-13 01:00 | lundi | 2026-10-01 10:00 |
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
			| nom  | priorité    | début            | fin              | jours                                                         | modifié          |
			| Nuit | fil_musical | 2026-10-12 00:00 | 2026-10-12 06:00 | lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche     | 2026-10-01 10:00 |
			| Jour | fil_musical | 2026-10-12 06:00 | 2026-10-13 00:00 | lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche     | 2026-10-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif |
			| 2026-10-14 05:59 | Nuit  |
			| 2026-10-14 06:00 | Jour  |
			| 2026-10-14 23:59 | Jour  |
			| 2026-10-15 00:00 | Nuit  |

	# ─── Événements sans fin ───────────────────────────────────

	Scénario: Une émission sans fin reste active jusqu'à ce que sa liste soit épuisée
		Étant donné les événements :
			| nom      | priorité    | début            | fin | jours | modifié          |
			| Continue | fil_musical |                  |     |       | 2026-10-01 10:00 |
			| Direct   | emission    | 2026-10-14 20:00 |     |       | 2026-10-01 10:00 |
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 19:59 | Continue |
			| 2026-10-14 20:00 | Direct   |
			| 2026-10-15 03:00 | Direct   |
		Quand l'occurrence de « Direct » commencée le « 2026-10-14 20:00 » se termine, sa liste épuisée
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-15 03:00 | Continue |

	Scénario: Une émission récurrente sans fin reprend à sa prochaine occurrence, même si la précédente est terminée
		Étant donné les événements :
			| nom      | priorité    | début            | fin | jours | modifié          |
			| Continue | fil_musical |                  |     |       | 2026-10-01 10:00 |
			| Matinale | emission    | 2026-10-12 07:00 |     | lundi | 2026-10-01 10:00 |
		Quand l'occurrence de « Matinale » commencée le « 2026-10-12 07:00 » se termine, sa liste épuisée
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-12 09:00 | Continue |
			| 2026-10-19 06:59 | Continue |
			| 2026-10-19 07:00 | Matinale |

	# ─── Conflit ───────────────────────────────────────────────

	Scénario: Deux événements de même priorité qui se chevauchent : le dernier modifié en base l'emporte
		Étant donné les événements :
			| nom    | priorité | début            | fin              | jours | modifié          |
			| Ancien | emission | 2026-10-14 20:00 | 2026-10-14 22:00 |       | 2026-10-01 10:00 |
			| Récent | emission | 2026-10-14 21:00 | 2026-10-14 23:00 |       | 2026-10-02 10:00 |
		Alors l'événement actif est :
			| heure            | actif  |
			| 2026-10-14 20:30 | Ancien |
			| 2026-10-14 21:30 | Récent |
			| 2026-10-14 22:30 | Récent |

	# ─── Changement d'heure ────────────────────────────────────

	Scénario: Un événement quotidien garde son heure murale au changement d'heure
		Étant donné les événements :
			| nom      | priorité    | début            | fin              | jours                                                     | modifié          |
			| Continue | fil_musical |                  |                  |                                                           | 2026-10-01 10:00 |
			| Journal  | emission    | 2026-03-01 21:00 | 2026-03-01 22:00 | lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche | 2026-02-01 10:00 |
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
			| nom  | priorité    | début            | fin              | jours                                                     | modifié          |
			| Nuit | fil_musical | 2026-01-05 00:00 | 2026-01-05 06:00 | lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche | 2026-01-01 10:00 |
			| Jour | fil_musical | 2026-01-05 06:00 | 2026-01-06 00:00 | lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche | 2026-01-01 10:00 |
		Alors l'événement actif est :
			| heure                  | actif |
			| 2026-03-29 01:59+01:00 | Nuit  |
			| 2026-03-29 03:00+02:00 | Nuit  |
			| 2026-03-29 05:59+02:00 | Nuit  |
			| 2026-03-29 06:00+02:00 | Jour  |
			| 2026-10-25 02:30+02:00 | Nuit  |
			| 2026-10-25 02:30+01:00 | Nuit  |
			| 2026-10-25 06:00+01:00 | Jour  |

	# ─── Lecture de la grille en base ──────────────────────────

	Scénario: La grille est lue en base avec les droits du binaire lecture
		Étant donné les événements :
			| nom      | priorité    | début            | fin              | jours            | modifié          |
			| Continue | fil_musical |                  |                  |                  | 2026-10-01 10:00 |
			| Magazine | emission    | 2026-10-12 21:00 | 2026-10-12 23:00 | lundi, mercredi  | 2026-10-01 10:00 |
		Et ces événements enregistrés en base
		Quand le binaire lecture lit la grille en base
		Alors l'événement actif est :
			| heure            | actif    |
			| 2026-10-14 21:30 | Magazine |
			| 2026-10-15 21:30 | Continue |
