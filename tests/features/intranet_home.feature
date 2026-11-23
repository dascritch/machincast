# language: fr
Fonctionnalité: Gabarit « Machin intranet » et accueil en direct
	En tant que membre de l'équipe connecté à l'intranet,
	je veux une page d'accueil qui suit l'antenne en direct,
	afin de savoir ce qui passe sans être au studio.

	https://github.com/dascritch/machincast/issues/541, ticket enfant de
	https://github.com/dascritch/machincast/issues/524. Le serveur écrit l'accueil tel qu'est l'antenne à son
	chargement ; son script le relit sur /api/v1/live et tient les décomptes, à la seconde. Durées et décomptes
	s'écrivent HH:MM:SS (https://github.com/dascritch/machincast/issues/579). Les requêtes passent directement à
	l'application ASGI (tests/asgi_client.py), sur la base de test.

	Contexte:
		Étant donné les comptes de l'intranet :
			| nom   | mot de passe    | rôle      | état  |
			| regie | tisane-au-micro | consulter | actif |
		Et une session valide de « regie », de jeton « jeton-de-regie »
		Et l'API de l'intranet sur la base de test, à « 2026-11-20 10:00:00 »

	Scénario: L'accueil suit l'antenne, dans le gabarit « Machin intranet »
		Étant donné les événements :
			| name        | public_name | priority               | starts_at        | ends_at          | days |
			| Fil de jour |             | background_programming |                  |                  |      |
			| Journal     |             | special                | 2026-11-20 09:30 | 2026-11-20 10:30 |      |
			| Midi        |             | show                   | 2026-11-20 12:00 | 2026-11-20 13:00 |      |
		Et les passages dans l'airplay :
			| starts_at           | ends_at             | artist | title | event       | sequence | bank | without_incident |
			| 2026-11-20 09:00:00 | 2026-11-20 09:03:00 | A      | Un    | Fil de jour |          |      | oui              |
			| 2026-11-20 09:03:00 | 2026-11-20 09:06:00 | B      | Deux  | Fil de jour |          |      | oui              |
		Et Machin player qui publie « Le journal » en cours, puis « Spot », « S1 »
		Quand je demande à l'API « GET / »
		Alors l'API répond 200, une page « MachinCast - Radio Thune » du gabarit de « Radio Thune », « En diffusion », pour « regie »
		Et le bandeau mène à « / » « Accueil », la page en cours, et permet de se déconnecter
		Et la page charge /static/intranet.css et /static/intranet.js, sans script dans la page
		Et les sections de l'accueil sont, dans l'ordre, « heure », « texte-public », « evenement », « suivant », « sonore », « prochain », « airplay »
		Et l'accueil met côte à côte « evenement » et « suivant », puis « sonore » et « prochain »
		Et l'accueil montre :
			| élément          | texte                     |
			| heure            | 10:00:00                  |
			| texte-public     | Radio Thune — Le journal  |
			| evenement-nom    | Journal                   |
			| evenement-debut  | 09:30                     |
			| evenement-fin    | 10:30                     |
			| evenement-reste  | 00:30:00                  |
			| suivant-nom      | Fil de jour               |
			| suivant-debut    | 10:30                     |
			| suivant-fin      | 12:00                     |
			| sonore-nom       | Le journal                |
			| sonore-duree     | 00:03:00                  |
			| sonore-reste     | 00:02:47                  |
			| prochain-nom     | Spot                      |
			| prochain-duree   | 00:03:00                  |
			| prochain-attente | 00:02:47                  |
		Et les décomptes « evenement-reste », « sonore-reste », « prochain-attente » ont leur limite, pour le script
		Et l'airplay de l'accueil est « 09:03 B – Deux », « 09:00 A – Un »

	Scénario: Sans Machin player, l'accueil montre l'antenne arrêtée
		Quand je demande à l'API « GET / »
		Alors l'API répond 200, une page « MachinCast - Radio Thune » du gabarit de « Radio Thune », « À l'arrêt », pour « regie »
		Et l'accueil montre :
			| élément      | texte |
			| texte-public | —     |
			| sonore-nom   | —     |
			| sonore-reste | —     |
			| prochain-nom | —     |

	Plan du scénario: Une durée de l'accueil s'écrit HH:MM:SS, à la seconde
		Quand l'accueil écrit la durée <durée>
		Alors il écrit « <texte> »

		Exemples:
			| durée    | texte    |
			| 0        | 00:00:00 |
			| 59.99    | 00:00:59 |
			| 167.5    | 00:02:47 |
			| 3600     | 01:00:00 |
			| 93784    | 26:03:04 |
			| -5       | 00:00:00 |
			| inconnue | —        |

	Plan du scénario: Sans session valide, l'accueil mène à la connexion
		Étant donné une session à valider de « regie », de jeton « jeton-en-attente »
		Quand je demande à l'API « GET / », <jeton>
		Alors l'API répond 303, vers « <page> »

		Exemples:
			| jeton                           | page        |
			| sans jeton                      | /login      |
			| avec le jeton « jeton-en-attente » | /validation |
			| avec le jeton « inconnu »       | /login      |

	Plan du scénario: L'intranet sert sa feuille de style et son script, et rien d'autre sous /static/
		Quand je demande à l'API « GET /static/<fichier> », sans jeton
		Alors l'API répond <statut>, de type « <type> »

		Exemples:
			| fichier             | statut | type                            |
			| intranet.css        | 200    | text/css; charset=utf-8         |
			| intranet.js         | 200    | text/javascript; charset=utf-8  |
			| ../home.py          | 404    | text/plain; charset=utf-8       |
			| autre.js            | 404    | text/plain; charset=utf-8       |

	# ─── Lisible de loin (https://github.com/dascritch/machincast/issues/598) ───

	Scénario: Le titre public à droite de l'horloge, et les décomptes des sonores aussi grands qu'elle
		Quand je demande à l'API « GET / », avec le jeton « jeton-de-regie »
		Alors l'API répond 200, une page « MachinCast - Radio Thune » du gabarit de « Radio Thune », « À l'arrêt », pour « regie »
		Et l'horloge et le titre public sont sur la même ligne, le titre à droite
		Et la feuille de style écrit le temps restant des sonores aussi grand que l'horloge

	Scénario: L'icône de l'intranet est celle de l'application, choisie dans l'interface
		Étant donné l'icône de l'application « logo.svg »
		Quand je demande à l'API « GET / », avec le jeton « jeton-de-regie »
		Alors la page déclare l'icône « /favicon »
		Quand je demande à l'API « GET /favicon », sans jeton
		Alors l'API répond 200, de type « image/svg+xml »
		Et l'icône servie est « logo.svg »

	Scénario: Sans icône choisie, ou illisible, l'intranet prend celle de MachinCast
		Étant donné l'icône de l'application « absente.png », qui n'existe pas
		Quand je demande à l'API « GET /favicon », sans jeton
		Alors l'API répond 200, de type « image/png »
		Et l'icône servie est celle de MachinCast
