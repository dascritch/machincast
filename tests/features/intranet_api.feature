# language: fr
Fonctionnalité: API REST v1 de l'intranet, en lecture
	En tant qu'outil de la radio, authentifié par une session valide,
	je veux lire l'antenne et les éléments de MachinCast par une API REST versionnée, /api/v1, en GET seulement,
	afin d'afficher ou de suivre l'antenne ailleurs que dans l'interface.

	https://github.com/dascritch/machincast/issues/540, ticket enfant de
	https://github.com/dascritch/machincast/issues/524. Les requêtes passent directement à l'application ASGI
	(tests/asgi_client.py), sur la base de test, au rôle machincast_intranet ; le jeton de la session en
	« Authorization: Bearer ». Les réponses sont en JSON : dates en ISO 8601, durées en secondes.

	Contexte:
		Étant donné les comptes de l'intranet :
			| nom   | mot de passe    | rôle      | état  |
			| regie | tisane-au-micro | consulter | actif |
		Et une session valide de « regie », de jeton « jeton-de-regie »
		Et l'API de l'intranet sur la base de test, à « 2026-11-20 10:00:00 »

	Scénario: Sans session valide, l'API répond 401, et dit pourquoi
		Quand je demande à l'API « GET /api/v1/sounds », sans jeton
		Alors l'API répond 401, avec l'erreur « Une session valide est nécessaire. »
		Et la réponse demande un jeton « Bearer »

	Scénario: Une session à valider ne sert pas l'API
		Étant donné une session à valider de « regie », de jeton « jeton-en-attente »
		Quand je demande à l'API « GET /api/v1/sounds », avec le jeton « jeton-en-attente »
		Alors l'API répond 401, avec l'erreur « Une session valide est nécessaire. »

	Plan du scénario: L'API ne répond qu'en GET, et à ses seuls chemins
		Quand je demande à l'API « <requête> »
		Alors l'API répond <statut>

		Exemples:
			| requête                | statut |
			| POST /api/v1/live      | 405    |
			| DELETE /api/v1/sounds  | 405    |
			| GET /api/v1/inconnu    | 404    |
			| GET /api/v1/sounds/999 | 404    |
			| GET /api/v2/sounds     | 404    |

	Scénario: La liste des sonores, par pages, sans les sonores supprimés
		Étant donné les sonores :
			| artist      | title         | type | state    | duration | location               |
			| Les Gaufres | Café à minuit | file | active   | 214      | /srv/musique/cafe.flac |
			| Aube        | Matin clair   | file | disabled | 180      | /srv/musique/matin.flac |
			| Ancien      | Effacé        | file | active   | 60       | /srv/musique/efface.flac |
		Et le sonore « Effacé » est supprimé
		Quand je demande à l'API « GET /api/v1/sounds?limit=1 »
		Alors l'API répond 200, avec les « sounds » de titres « Café à minuit »
		Et la page suivante commence après le sonore « Café à minuit »
		Quand je demande à l'API la page suivante des « sounds »
		Alors l'API répond 200, avec les « sounds » de titres « Matin clair »
		Et la réponse n'a pas de page suivante
		Quand je demande à l'API « GET /api/v1/sounds?limit=5000 »
		Alors l'API répond 400

	Plan du scénario: Un paramètre de page illisible est refusé, 400, jamais une erreur interne
		https://github.com/dascritch/machincast/issues/553 : « ² » (%C2%B2) passe isdigit, mais pas int ; « ٣ » (%D9%A3), un
		chiffre arabe-indien, passe les deux, mais n'est pas un identifiant de l'API.
		Quand je demande à l'API « GET /api/v1/sounds?<paramètre> »
		Alors l'API répond 400

		Exemples:
			| paramètre      |
			| limit=%C2%B2   |
			| after=%C2%B2   |
			| limit=%D9%A3   |
			| limit=-1       |

	Scénario: La fiche d'une banque donne ses sonores, dans l'ordre, et ses répertoires
		Étant donné les sonores :
			| artist      | title         | type | state  | duration | location               |
			| Les Gaufres | Café à minuit | file | active | 214      | /srv/musique/cafe.flac |
			| Aube        | Matin clair   | file | active | 180      | /srv/musique/matin.flac |
		Et la banque « Rotation », aléatoire, sans nom public, avec « Matin clair », « Café à minuit »
		Quand je demande à l'API la fiche de la banque « Rotation »
		Alors l'API répond 200, avec la fiche « internal_name » « Rotation », « mode » « random »
		Et ses éléments sont « Aube – Matin clair », « Les Gaufres – Café à minuit »

	Scénario: La fiche d'un événement donne ses éléments, dans l'ordre
		Étant donné les sonores :
			| artist      | title         | type | state  | duration | location               |
			| Les Gaufres | Café à minuit | file | active | 214      | /srv/musique/cafe.flac |
		Et la séquence « Passage pub », sans nom public, avec le sonore « Café à minuit »
		Et les événements :
			| name        | public_name | priority               | starts_at | ends_at | days |
			| Fil de jour |             | background_programming |           |         |      |
		Et l'événement « Fil de jour » joue la séquence « Passage pub »
		Quand je demande à l'API la fiche de l'événement « Fil de jour »
		Alors l'API répond 200, avec la fiche « internal_name » « Fil de jour », « priority » « background_programming »
		Et ses éléments sont « Passage pub »
		Quand je demande à l'API la fiche de la séquence « Passage pub »
		Alors ses éléments sont « Les Gaufres – Café à minuit »

	Scénario: Les incidents seulement, les plus récents en tête
		Étant donné les entrées du log :
			| level    | kind        | message              |
			| info     | start       | Machin player démarre |
			| incident | dead air    | blanc de 4 s         |
			| warning  | late stream | stream lent          |
			| incident | dropped stream | stream tombé      |
		Quand je demande à l'API « GET /api/v1/incidents »
		Alors l'API répond 200, avec les incidents « dropped stream », « dead air »

	Scénario: L'antenne en direct : sonore en cours, 5 suivants, 5 derniers, et les événements autour
		Étant donné les événements :
			| name        | public_name | priority               | starts_at        | ends_at          | days |
			| Fil de jour |             | background_programming |                  |                  |      |
			| Matinale    |             | show                   | 2026-11-20 06:00 | 2026-11-20 09:00 |      |
			| Journal     |             | special                | 2026-11-20 09:30 | 2026-11-20 10:30 |      |
			| Midi        |             | show                   | 2026-11-20 12:00 | 2026-11-20 13:00 |      |
		Et les passages dans l'airplay :
			| starts_at           | ends_at             | artist | title   | event       | sequence | bank | without_incident |
			| 2026-11-20 09:00:00 | 2026-11-20 09:03:00 | A      | Un      | Fil de jour |          |      | oui              |
			| 2026-11-20 09:03:00 | 2026-11-20 09:06:00 | B      | Deux    | Fil de jour |          |      | oui              |
			| 2026-11-20 09:06:00 | 2026-11-20 09:09:00 | C      | Trois   | Fil de jour |          |      | oui              |
			| 2026-11-20 09:09:00 | 2026-11-20 09:12:00 | D      | Quatre  | Fil de jour |          |      | oui              |
			| 2026-11-20 09:12:00 | 2026-11-20 09:15:00 | E      | Cinq    | Fil de jour |          |      | oui              |
			| 2026-11-20 09:15:00 | 2026-11-20 09:18:00 | F      | Six     | Fil de jour |          |      | oui              |
		Et Machin player qui publie « Le journal » en cours, puis « Spot », « S1 », « S2 », « S3 », « S4 », « S5 »
		Quand je demande à l'API « GET /api/v1/live »
		Alors l'API répond 200, en direct « playing », texte public « Radio Thune — Le journal »
		Et le sonore en cours est « Le journal »
		Et les sonores suivants sont « Spot », « S1 », « S2 », « S3 », « S4 »
		Et les derniers sonores sont « Six », « Cinq », « Quatre », « Trois », « Deux »
		Et l'événement précédent est « Fil de jour », de « 2026-11-20T09:00:00 » à « 2026-11-20T09:30:00 »
		Et l'événement en cours est « Journal », de « 2026-11-20T09:30:00 » à « 2026-11-20T10:30:00 »
		Et l'événement suivant est « Fil de jour », de « 2026-11-20T10:30:00 » à « 2026-11-20T12:00:00 »

	Scénario: Sans Machin player, l'antenne est arrêtée, sans sonore
		Quand je demande à l'API « GET /api/v1/live »
		Alors l'API répond 200, en direct « stopped », sans sonore en cours ni à venir
