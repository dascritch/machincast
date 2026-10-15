# language: fr
Fonctionnalité: Expiration automatique des sonores
	En tant que programmateur de l'antenne,
	je veux qu'un sonore passe automatiquement à l'état « expiré » quand il atteint son maximum de lectures ou la fin de sa période de diffusion,
	afin qu'une annonce limitée dans le temps ne passe plus une fois expirée.

	https://github.com/dascritch/machincast/issues/18, spec § 4.5. Le binaire lecture, avec ses propres droits, passe
	un sonore de l'état actif à l'état expiré, et le consigne dans le log avec la cause. Seule la colonne etat change.

	Contexte:
		Étant donné le poste à l'heure de Paris

	# ─── Maximum de lectures ───────────────────────────────────

	Scénario: Un sonore qui atteint son maximum de lectures expire, avec la cause dans le log
		Étant donné le sonore actif « Annonce concert » avec un maximum de 2 lectures
		Et « Annonce concert » a été joué 2 fois
		Quand le binaire lecture vérifie les expirations au « 2026-10-14 20:00:00 »
		Alors le sonore « Annonce concert » est à l'état « expire »
		Et le log contient 1 info « sonore expiré », pour ce sonore, qui mentionne « maximum de 2 lectures atteint »

	Scénario: Un sonore sous son maximum de lectures reste actif
		Étant donné le sonore actif « Annonce concert » avec un maximum de 2 lectures
		Et « Annonce concert » a été joué 1 fois
		Quand le binaire lecture vérifie les expirations au « 2026-10-14 20:00:00 »
		Alors le sonore « Annonce concert » est à l'état « actif »
		Et le log est vide

	Scénario: Le maximum se compte sur tout l'historique, quels que soient l'événement et la banque
		Étant donné le sonore actif « Annonce concert » avec un maximum de 3 lectures
		Et « Annonce concert » a été joué 1 fois dans l'émission « Matin »
		Et « Annonce concert » a été joué 1 fois via la banque « Annonces »
		Et « Annonce concert » a été joué 1 fois sans événement ni banque
		Quand le binaire lecture vérifie les expirations au « 2026-10-14 20:00:00 »
		Alors le sonore « Annonce concert » est à l'état « expire »

	# ─── Période de diffusion ──────────────────────────────────

	Plan du scénario: Un sonore expire dès la fin de sa période de diffusion, fin comprise
		Étant donné le sonore actif « Promo salon » diffusable jusqu'au « 2026-10-14 20:00:00 »
		Quand le binaire lecture vérifie les expirations au « <instant> »
		Alors le sonore « Promo salon » est à l'état « <etat> »

		Exemples:
			| instant             | etat   |
			| 2026-10-14 19:59:59 | actif  |
			| 2026-10-14 20:00:00 | expire |
			| 2026-10-15 08:00:00 | expire |

	Scénario: La fin de la période de diffusion est consignée avec sa date
		Étant donné le sonore actif « Promo salon » diffusable jusqu'au « 2026-10-14 20:00:00 »
		Quand le binaire lecture vérifie les expirations au « 2026-10-14 20:00:30 »
		Alors le log contient 1 info « sonore expiré », pour ce sonore, qui mentionne « période de diffusion terminée le 2026-10-14 20:00:00 »

	# ─── Ce qui ne change pas ──────────────────────────────────

	Plan du scénario: Seul un sonore actif expire ; un sonore à un autre état garde le sien
		Étant donné le sonore actif « Promo salon » diffusable jusqu'au « 2026-10-14 20:00:00 »
		Et le sonore « Promo salon » est à l'état « <etat> »
		Quand le binaire lecture vérifie les expirations au « 2026-10-15 08:00:00 »
		Alors le sonore « Promo salon » est à l'état « <etat> »
		Et le log est vide

		Exemples:
			| etat      |
			| apercu    |
			| desactive |
			| errone    |
			| supprime  |
			| expire    |

	Scénario: L'expiration ne change que l'état du sonore
		Étant donné le sonore actif « Promo salon » diffusable jusqu'au « 2026-10-14 20:00:00 »
		Quand le binaire lecture vérifie les expirations au « 2026-10-15 08:00:00 »
		Alors seules les colonnes etat et modifie_le du sonore « Promo salon » ont changé

	Scénario: Un sonore expiré ne l'est qu'une fois dans le log
		Étant donné le sonore actif « Promo salon » diffusable jusqu'au « 2026-10-14 20:00:00 »
		Quand le binaire lecture vérifie les expirations au « 2026-10-15 08:00:00 »
		Et le binaire lecture vérifie les expirations au « 2026-10-15 08:01:00 »
		Alors le log contient 1 info « sonore expiré », pour ce sonore, qui mentionne « période de diffusion »

	# ─── Pendant la diffusion ──────────────────────────────────

	Scénario: Pendant la diffusion, un sonore expire au passage qui atteint son maximum
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le fil musical permanent « Continue », avec les sonores « annonce », « f1 »
		Et le sonore « annonce » a un maximum de 1 lecture
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « annonce », « f1 », « f1 »
		Et le sonore « annonce » est à l'état « expire »
		Et le log contient 1 info « sonore expiré »

	Scénario: Pendant la diffusion, la fin d'une période de diffusion est vérifiée chaque minute
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le fil musical permanent « Continue », avec les sonores « f1 »
		Et le sonore actif « Promo salon » diffusable jusqu'au « 2026-10-14 20:00:00 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Alors le sonore « Promo salon » est à l'état « actif »
		Quand l'horloge du binaire passe au « 2026-10-14 20:00:30 »
		Et la diffusion tourne 1 pas d'une seconde
		Alors le sonore « Promo salon » est à l'état « actif »
		Quand l'horloge du binaire passe au « 2026-10-14 20:00:52 »
		Et la diffusion tourne 1 pas d'une seconde
		Alors le sonore « Promo salon » est à l'état « expire »
