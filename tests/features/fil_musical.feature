# language: fr
Fonctionnalité: Un fil musical existe toujours
	En tant que technicien d'antenne,
	je veux que l'interface recrée un fil musical s'il n'en existe aucun,
	afin que l'antenne ne reste jamais sans programmation par défaut.

	https://github.com/dascritch/machincast/issues/39, spec § 8.10. L'interface vérifie qu'un événement de priorité
	fil musical existe : au lancement, après la suppression d'un événement, et après l'enregistrement d'un événement.
	Sinon, elle crée « Fil musical », permanent et sans élément, et la barre d'état le dit : sa liste se remplit dans
	sa fiche.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 20:30:00 »
		Et les sonores :
			| artiste | titre  | type    | etat  | duree | emplacement       |
			|         | Jingle | fichier | actif | 5     | /srv/jingle.flac  |

	Scénario: Au lancement, sans fil musical, l'interface en crée un, permanent et sans élément
		Étant donné les événements :
			| nom      | nom_public | priorite | debut            | fin              | jours |
			| Matinale |            | emission | 2026-10-19 07:00 | 2026-10-19 09:00 | lundi |
			| Panne    |            | secours  |                  |                  |       |
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre d'état annonce « Aucun fil musical : « Fil musical » est créé, permanent et sans élément ; sa liste se remplit dans sa fiche. »
		Et le fil musical « Fil musical » est en base, permanent et sans élément
		Quand j'ouvre l'onglet « Événements »
		Alors la liste montre :
			| Nom         | Nom public | Priorité    | Début            | Fin              | Récurrence |
			| Matinale    |            | émission    | 2026-10-19 07:00 | 2026-10-19 09:00 | lundi      |
			| Fil musical |            | fil musical |                  |                  |            |
			| Panne       |            | secours     |                  |                  |            |

	Scénario: Au lancement, un fil musical existant suffit, même daté
		Étant donné les événements :
			| nom  | nom_public | priorite    | debut            | fin              | jours |
			| Nuit |            | fil_musical | 2026-10-19 00:00 | 2026-10-19 06:00 | lundi |
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre d'état n'a rien annoncé
		Et les fils musicaux en base sont « Nuit »

	Plan du scénario: Le nom « Fil musical » déjà pris par un autre événement, le fil créé prend le premier libre
		Étant donné les événements :
			| nom     | nom_public | priorite | debut            | fin              | jours |
			| <un>    |            | emission | 2026-10-19 07:00 | 2026-10-19 09:00 | lundi |
			| <autre> |            | special  | 2026-10-20 07:00 | 2026-10-20 09:00 |       |
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre d'état annonce « Aucun fil musical : « <cree> » est créé, permanent et sans élément ; sa liste se remplit dans sa fiche. »
		Et les fils musicaux en base sont « <cree> »

		Exemples:
			| un          | autre          | cree          |
			| Fil musical | Matinale       | Fil musical 2 |
			| Fil musical | Fil musical 2  | Fil musical 3 |
			| Fil musical | Fil musical 3  | Fil musical 2 |

	Scénario: Supprimer le dernier fil musical en crée un autre
		Étant donné les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Et l'événement « Continue » joue le sonore « Jingle »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Continue »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors l'événement « Continue » n'est plus en base
		Et la barre d'état annonce « Aucun fil musical : « Fil musical » est créé, permanent et sans élément ; sa liste se remplit dans sa fiche. »
		Et le fil musical « Fil musical » est en base, permanent et sans élément

	Scénario: Supprimer un fil musical quand il en reste un autre ne crée rien
		Étant donné les événements :
			| nom  | nom_public | priorite    | debut            | fin              | jours |
			| Jour |            | fil_musical | 2026-10-19 06:00 | 2026-10-20 00:00 | lundi |
			| Nuit |            | fil_musical | 2026-10-19 00:00 | 2026-10-19 06:00 | lundi |
		Et l'événement « Nuit » joue le sonore « Jingle »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Nuit »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la barre d'état n'a rien annoncé
		Et les fils musicaux en base sont « Jour »

	Scénario: Supprimer un autre élément que le dernier fil musical ne crée rien
		Étant donné les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Quand la fenêtre de l'interface s'ouvre
		Et la base perd son dernier fil musical
		Et j'ouvre la fiche du sonore « Jingle »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la barre d'état n'a rien annoncé
		Et les fils musicaux en base sont aucun

	Scénario: Le dernier fil musical enregistré sous une autre priorité en crée un autre
		Étant donné les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Et l'événement « Continue » joue le sonore « Jingle »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Continue »
		Et je choisis la priorité « secours »
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et la barre d'état annonce « Aucun fil musical : « Fil musical » est créé, permanent et sans élément ; sa liste se remplit dans sa fiche. »
		Et les fils musicaux en base sont « Fil musical »
		Quand j'ouvre l'onglet « Événements »
		Alors la liste montre :
			| Nom         | Nom public | Priorité    | Début | Fin | Récurrence |
			| Fil musical |            | fil musical |       |     |            |
			| Continue    |            | secours     |       |     |            |

	Scénario: Enregistrer un autre événement ne crée rien tant qu'un fil musical existe
		Étant donné les événements :
			| nom      | nom_public | priorite    | debut            | fin              | jours |
			| Continue |            | fil_musical |                  |                  |       |
			| Matinale |            | emission    | 2026-10-19 07:00 | 2026-10-19 09:00 | lundi |
		Et l'événement « Matinale » joue le sonore « Jingle »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je saisis le nom public « Bonjour »
		Et j'enregistre la fiche
		Alors la barre d'état n'a rien annoncé
		Et les fils musicaux en base sont « Continue »
