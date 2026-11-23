# language: fr
Fonctionnalité: Calendrier de l'intranet, en API, en hCalendar et en page, et lien vers la documentation
	En tant que membre de l'équipe connecté à l'intranet,
	je veux voir le calendrier de la semaine, et le lire par l'API, y compris en hCalendar,
	afin de préparer l'antenne à distance, et de retrouver la documentation.

	https://github.com/dascritch/machincast/issues/542, ticket enfant de
	https://github.com/dascritch/machincast/issues/524. Le calendrier vient de la grille, passé comme à venir, même
	les occurrences qu'un événement de priorité plus haute couvre. Les requêtes passent directement à l'application
	ASGI (tests/asgi_client.py), sur la base de test ; le jeton de la session en « Authorization: Bearer ».
	La page montre la semaine en grille horaire, comme le calendrier de l'interface
	(https://github.com/dascritch/machincast/issues/580), en SVG : la politique de sécurité du contenu refuse tout
	attribut style.

	Contexte:
		Étant donné les comptes de l'intranet :
			| nom   | mot de passe    | rôle      | état  |
			| regie | tisane-au-micro | consulter | actif |
		Et une session valide de « regie », de jeton « jeton-de-regie »
		Et l'API de l'intranet sur la base de test, à « 2026-11-20 10:00:00 »
		Et les événements :
			| name        | public_name | priority               | starts_at        | ends_at          | days |
			| Fil de jour |             | background_programming |                  |                  |      |
			| Matinale    |             | show                   | 2026-11-18 07:00 | 2026-11-18 09:00 |      |
			| Chronique   |             | show                   | 2026-11-18 07:45 | 2026-11-18 08:00 |      |
			| Spécial     |             | special                | 2026-11-18 07:30 | 2026-11-18 08:30 |      |

	Scénario: L'API donne le calendrier d'une période passée, même les occurrences couvertes par un autre événement
		Quand je demande à l'API « GET /api/v1/calendar?from=2026-11-18&to=2026-11-19 »
		Alors l'API répond 200, avec le calendrier du « 2026-11-18 » au « 2026-11-19 » : « Fil de jour », « Matinale », « Spécial », « Chronique »
		Et « Matinale » est à l'antenne de « 2026-11-18 07:00 » à « 2026-11-18 07:30 », et de « 2026-11-18 08:30 » à « 2026-11-18 09:00 »
		Et « Spécial » est à l'antenne de « 2026-11-18 07:30 » à « 2026-11-18 08:30 »
		Et « Chronique », de « 2026-11-18 07:45 » à « 2026-11-18 08:00 », est couverte, sans moment à l'antenne

	Scénario: Sans période, l'API donne la semaine en cours
		Quand je demande à l'API « GET /api/v1/calendar »
		Alors l'API répond 200, avec le calendrier du « 2026-11-16 » au « 2026-11-23 » : « Fil de jour », « Matinale », « Spécial », « Chronique »

	Plan du scénario: Une période illisible, à l'envers ou trop longue est refusée
		Quand je demande à l'API « GET /api/v1/calendar?<période> »
		Alors l'API répond 400, avec l'erreur « from et to sont des dates, from avant to, à 62 jours au plus l'une de l'autre. »

		Exemples:
			| période                       |
			| from=2026-11-20&to=2026-11-19 |
			| from=2026-11-20&to=2026-11-20 |
			| from=demain                   |
			| from=2026-01-01&to=2026-06-01 |

	Scénario: L'API donne aussi le calendrier en HTML hCalendar
		Quand je demande à l'API « GET /api/v1/calendar?from=2026-11-18&to=2026-11-19&format=html »
		Alors l'API répond 200, une page hCalendar de 4 occurrences
		Et l'occurrence hCalendar « Chronique » est de « 2026-11-18 07:45 » à « 2026-11-18 08:00 », « émission », couverte

	Scénario: La page du calendrier montre une semaine en grille horaire, avec la précédente et la suivante
		Quand je demande à l'API « GET /calendar?week=2026-11-18 »
		Alors l'API répond 200, une page « Calendrier » du gabarit de « Radio Thune », « À l'arrêt », pour « regie »
		Et le bandeau mène à « /calendar » « Calendrier », la page en cours, et permet de se déconnecter
		Et la page est titrée « Semaine du 16/11 au 22/11/2026 »
		Et la page mène à la semaine précédente « /calendar?week=2026-11-09 » et à la suivante « /calendar?week=2026-11-23 »
		Et la grille a pour jours « lundi 16/11 », « mardi 17/11 », « mercredi 18/11 », « jeudi 19/11 », « vendredi 20/11 », « samedi 21/11 », « dimanche 22/11 »
		Et la grille a pour heures « 00:00 » à « 23:00 », et s'ouvre à 07:00
		Et le « vendredi 20/11 » est aujourd'hui, l'heure actuelle à 10:00
		Et la page n'a aucun attribut style

	# ─── L'agenda : une seule couche d'événements à venir (https://github.com/dascritch/machincast/issues/599) ───

	Scénario: L'agenda ne montre que ce qui passera à l'antenne, une seule couche, en morceaux
		Étant donné les événements :
			| name      | public_name | priority | starts_at        | ends_at          | days |
			| Journal   |             | show     | 2026-11-23 07:00 | 2026-11-23 09:00 |      |
			| Flash     |             | special  | 2026-11-23 07:30 | 2026-11-23 08:30 |      |
			| Revue     |             | show     | 2026-11-23 07:45 | 2026-11-23 08:00 |      |
			| Nuit      |             | show     | 2026-11-24 22:00 |                  |      |
		Et l'événement de secours « Attente »
		Quand je demande à l'API « GET /calendar?week=2026-11-23 »
		Alors les heures du « lundi 23/11 » ont pour blocs :
			| nom     | priorité | heures        | colonne | à l'antenne   | estompé |
			| Journal | show     | 07:00 – 07:30 | 1 sur 1 | 07:00 – 07:30 | non     |
			| Flash   | special  | 07:30 – 08:30 | 1 sur 1 | 07:30 – 08:30 | non     |
			| Journal | show     | 08:30 – 09:00 | 1 sur 1 | 08:30 – 09:00 | non     |
		Et les heures du « mardi 24/11 » ne montrent rien
		Et la bande de la journée entière du « lundi 23/11 » ne montre rien

	Scénario: L'agenda ne montre pas ce qui est passé, mais montre l'en cours
		Étant donné les événements :
			| name     | public_name | priority | starts_at        | ends_at          | days |
			| Réveil   |             | show     | 2026-11-20 06:00 | 2026-11-20 08:00 |      |
			| Débat    |             | show     | 2026-11-20 09:30 | 2026-11-20 11:00 |      |
			| Soirée   |             | show     | 2026-11-20 20:00 | 2026-11-20 22:00 |      |
		Quand je demande à l'API « GET /calendar?week=2026-11-20 »
		Alors les heures du « vendredi 20/11 » montrent « Débat », « Soirée »
		Et les heures du « mercredi 18/11 » ne montrent rien

	Scénario: Une session sautée n'est pas dans l'agenda
		Étant donné les événements :
			| name     | public_name | priority | starts_at        | ends_at          | days                                     |
			| Magazine |             | show     | 2026-11-23 18:00 | 2026-11-23 19:00 | monday,tuesday,wednesday,thursday,friday |
		Et la session du 2026-11-24 de l'événement « Magazine » est sautée
		Quand je demande à l'API « GET /calendar?week=2026-11-23 »
		Alors les heures du « lundi 23/11 » montrent « Magazine »
		Et les heures du « mardi 24/11 » ne montrent rien
		Et les heures du « mercredi 25/11 » montrent « Magazine »

	Scénario: L'API garde le calendrier entier, toutes les couches, passées comme à venir
		Quand je demande à l'API « GET /api/v1/calendar?from=2026-11-18&to=2026-11-19 »
		Alors l'API répond 200, avec le calendrier du « 2026-11-18 » au « 2026-11-19 » : « Fil de jour », « Matinale », « Spécial », « Chronique »

	Scénario: Un plugin reprend l'agenda à un autre usage
		Étant donné les événements :
			| name    | public_name | priority | starts_at        | ends_at          | days |
			| Journal |             | show     | 2026-11-23 07:00 | 2026-11-23 09:00 |      |
		Alors l'agenda de la semaine du « 2026-11-23 », pour un plugin, est « Journal » de « 2026-11-23 07:00 » à « 2026-11-23 09:00 »
		Et son HTML est une section « agenda », en grille horaire

	Scénario: La page de la documentation mène au guide de l'antenne et à la spécification de l'intranet, à la version installée
		Quand je demande à l'API « GET /documentation »
		Alors l'API répond 200, une page « Documentation » du gabarit de « Radio Thune », « À l'arrêt », pour « regie »
		Et la page mène au guide de l'antenne et à la spécification de l'intranet, à la version installée

	Plan du scénario: Sans session valide, les pages mènent à la connexion
		Quand je demande à l'API « GET <page> », sans jeton
		Alors l'API répond 303, vers « /login »

		Exemples:
			| page           |
			| /calendar      |
			| /documentation |
