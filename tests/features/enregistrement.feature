# language: fr
Fonctionnalité: Enregistrement de l'airplay et du log
	En tant que technicien d'antenne,
	je veux que chaque passage et chaque opération soient enregistrés en base,
	afin que l'historique serve aux déclarations, aux reprises et au diagnostic.

	https://github.com/dascritch/machincast/issues/17 — spec § 3.1 et § 5.2. Tout passe par la connexion du binaire
	lecture, qui ne peut qu'ajouter des lignes à l'airplay et au log. Les heures viennent de l'horloge du binaire.

	Contexte:
		Étant donné le sonore « /musique/cafe.flac », de l'artiste « Les Gaufres » et du titre « Café à minuit »
		Et la banque « Titres » qui le contient
		Et l'émission « Magazine », dont il est le 2e élément, via la banque « Titres »

	# ─── Airplay ───────────────────────────────────────────────

	Scénario: Un passage donne deux lignes d'airplay, reliées, au début et à la fin
		Quand le binaire lecture commence ce passage à « 2026-10-15 20:00:00 »
		Et le termine à « 2026-10-15 20:03:30 », joué en entier
		Alors l'airplay contient 2 lignes, de début et de fin, avec le même identifiant de passage
		Et la ligne de début est datée de « 2026-10-15 20:00:00 », celle de fin de « 2026-10-15 20:03:30 »

	Scénario: Les deux lignes recopient le sonore et référencent sa banque, son événement et son élément
		Quand le binaire lecture commence ce passage à « 2026-10-15 20:00:00 »
		Et le termine à « 2026-10-15 20:03:30 », joué en entier
		Alors chaque ligne d'airplay recopie l'emplacement « /musique/cafe.flac », l'artiste « Les Gaufres » et le titre « Café à minuit »
		Et chaque ligne d'airplay référence le sonore, la banque « Titres », l'émission « Magazine » et son 2e élément

	Scénario: L'airplay garde l'artiste et le titre du moment du passage
		Quand le binaire lecture commence ce passage à « 2026-10-15 20:00:00 »
		Et le titre du sonore devient « Thé à midi »
		Et le binaire lecture termine le passage à « 2026-10-15 20:03:30 », joué en entier
		Alors chaque ligne d'airplay recopie l'emplacement « /musique/cafe.flac », l'artiste « Les Gaufres » et le titre « Café à minuit »

	Scénario: Un sonore placé directement dans l'événement n'a pas de banque
		Étant donné l'émission « Journal », dont le sonore est le 1er élément, sans banque
		Quand le binaire lecture commence le passage de l'émission « Journal » à « 2026-10-15 21:00:00 »
		Alors la ligne de début ne référence aucune banque

	Scénario: La ligne de fin donne la durée effectivement diffusée, sans incident
		Quand le binaire lecture commence ce passage à « 2026-10-15 20:00:00 »
		Et le termine à « 2026-10-15 20:03:30 », joué en entier
		Alors la ligne de fin indique 210 secondes diffusées, sans incident
		Et le log ne contient rien

	Scénario: Un passage coupé net donne sa durée réelle, sans incident, et la coupure est consignée
		Quand le binaire lecture commence ce passage à « 2026-10-15 20:00:00 »
		Et le termine à « 2026-10-15 20:01:00 », coupé net
		Alors la ligne de fin indique 60 secondes diffusées, sans incident
		Et le log contient une ligne « info » « coupure nette » pour ce sonore, la banque et l'émission

	Scénario: Un passage interrompu par une erreur de lecture est marqué comme incident
		Quand le binaire lecture commence ce passage à « 2026-10-15 20:00:00 »
		Et le termine à « 2026-10-15 20:00:12 », sur l'erreur « Could not decode stream »
		Alors la ligne de fin indique 12 secondes diffusées, avec incident
		Et le log contient une ligne « incident » « lecture interrompue » pour ce sonore, la banque et l'émission
		Et cette ligne du log mentionne « Could not decode stream »

	# ─── Log ───────────────────────────────────────────────────

	Plan du scénario: Chaque opération est consignée avec son niveau, sa nature et ses références
		Quand le binaire lecture consigne « <niveau> » « <nature> » : « <message> », à « 2026-10-15 20:00:00 »
		Alors le log contient une ligne « <niveau> » « <nature> » datée de « 2026-10-15 20:00:00 », qui mentionne « <message> »

		Exemples:
			| niveau   | nature              | message                    |
			| info     | démarrage           | Machin_lecture 0.1.0       |
			| alerte   | silence             | rien à diffuser            |
			| incident | fichier introuvable | /musique/disparu.flac      |

	Scénario: Les écritures existantes du binaire lecture passent par le même journal
		Alors aucun module du binaire lecture n'écrit dans le log autrement que par machincast.lecture.enregistrement
