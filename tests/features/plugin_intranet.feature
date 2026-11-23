# language: fr
Fonctionnalité: Les pages et les routes des plugins dans Machin intranet
	En tant que développeur d'un plugin,
	je veux ajouter mes pages, mes routes d'API et mes fichiers statiques à Machin intranet,
	afin de donner à l'équipe un outil sur mesure, derrière la même connexion et les mêmes rôles.

	https://github.com/dascritch/machincast/issues/588, ticket enfant de
	https://github.com/dascritch/machincast/issues/348. Au démarrage, Machin intranet demande à chaque plugin abonné
	au point « intranet.extensions » son Extension : des pages sous /plugins/<nom>/, des routes sous
	/api/v1/plugins/<nom>/, des fichiers statiques sous /plugins/<nom>/static/. Ici, le plugin « horloge » a une page
	« Horloge », dans le bandeau, une page « Réglages », sans entrée au bandeau, pour les comptes « actions API », et une
	route POST « sonner », pour les comptes « actions API » aussi ; sous l'antenne en direct de l'accueil, la section
	« cadran », pour tout compte, et la section « alarmes », pour les comptes « actions API ».

	Contexte:
		Étant donné les comptes de l'intranet :
			| nom    | mot de passe    | rôle        | état  |
			| regie  | tisane-au-micro | actions API | actif |
			| invite | cafe-sans-sucre | consulter   | actif |
		Et une session valide de « regie », de jeton « jeton-de-regie »
		Et une session valide de « invite », de jeton « jeton-d-invite »
		Et l'intranet sur la base de test, avec le plugin « horloge »

	Scénario: La page d'un plugin, dans le gabarit, avec son entrée au bandeau
		Quand je demande à l'API « GET /plugins/horloge », avec le jeton « jeton-d-invite »
		Alors l'API répond 200, une page « Horloge » du gabarit de « Radio Thune », « À l'arrêt », pour « invite »
		Et le bandeau mène à « /plugins/horloge » « Horloge », la page en cours, et permet de se déconnecter
		Et la page contient « <p id="horloge">pour invite</p> »
		Et la page charge la feuille de style « /plugins/horloge/static/horloge.css » et le script « /plugins/horloge/static/horloge.js »

	Scénario: Les sections d'un plugin s'ajoutent sous l'antenne en direct de l'accueil, avec leurs fichiers
		Quand je demande à l'API « GET / », avec le jeton « jeton-de-regie »
		Alors l'API répond 200, une page « MachinCast - Radio Thune » du gabarit de « Radio Thune », « À l'arrêt », pour « regie »
		Et l'accueil a, sous l'antenne en direct, les sections « cadran », « alarmes »
		Et la page contient « <p>pour regie</p> »
		Et la page contient « <link rel="stylesheet" href="/plugins/horloge/static/cadran.css"> »

	Scénario: Une section de l'accueil réservée aux comptes « actions API » n'est pas montrée aux autres
		Quand je demande à l'API « GET / », avec le jeton « jeton-d-invite »
		Alors l'accueil a, sous l'antenne en direct, les sections « cadran »

	Scénario: Une section de l'accueil en échec est consignée, et l'accueil s'affiche sans elle
		Étant donné le plugin « bancal » qui ajoute à l'accueil une section en échec
		Et l'intranet, de nouveau, avec ses plugins
		Quand je demande à l'API « GET / », avec le jeton « jeton-de-regie »
		Alors l'API répond 200, une page « MachinCast - Radio Thune » du gabarit de « Radio Thune », « À l'arrêt », pour « regie »
		Et l'accueil a, sous l'antenne en direct, les sections « cadran », « alarmes »
		Et le journal dit « plugin « bancal » : sa section de l'accueil a échoué : cadran cassé »

	Scénario: Les pages de l'intranet ont l'entrée du plugin au bandeau
		Quand je demande à l'API « GET /calendar », avec le jeton « jeton-d-invite »
		Alors la page contient « <a href="/plugins/horloge">Horloge</a> »
		Et la page ne contient pas « Réglages »

	Scénario: Sans session, la page d'un plugin mène à la connexion
		Quand je demande à l'API « GET /plugins/horloge », sans jeton
		Alors l'API répond 303, vers « /login »

	Scénario: Une page réservée aux comptes « actions API »
		Quand je demande à l'API « GET /plugins/horloge/reglages », avec le jeton « jeton-d-invite »
		Alors l'API répond 403, de type « text/html; charset=utf-8 »
		Et la page contient « Cette page est réservée aux comptes qui peuvent agir sur l'antenne. »
		Quand je demande à l'API « GET /plugins/horloge/reglages », avec le jeton « jeton-de-regie »
		Alors l'API répond 200, une page « Réglages » du gabarit de « Radio Thune », « À l'arrêt », pour « regie »

	Scénario: La route d'un plugin répond en JSON, au compte de la session
		Quand je demande à l'API « POST /api/v1/plugins/horloge/sonner », avec le jeton « jeton-de-regie »
		Alors l'API répond 202, avec le JSON « {"sonne": "regie"} »

	Scénario: La route d'un plugin refuse un compte sans le rôle, ou sans session
		Quand je demande à l'API « POST /api/v1/plugins/horloge/sonner », avec le jeton « jeton-d-invite »
		Alors l'API répond 403, avec l'erreur « Ce compte ne peut pas agir sur l'antenne. »
		Quand je demande à l'API « POST /api/v1/plugins/horloge/sonner », sans jeton
		Alors l'API répond 401, avec l'erreur « Une session valide est nécessaire. »

	Scénario: La route d'un plugin refuse un formulaire d'un autre site
		Quand le compte « regie » envoie « POST /api/v1/plugins/horloge/sonner » depuis « https://ailleurs.example »
		Alors l'API répond 403

	Plan du Scénario: Les fichiers statiques d'un plugin, par type
		Quand je demande à l'API « GET /plugins/horloge/static/<fichier> », sans jeton
		Alors l'API répond 200, de type « <type> »

		Exemples:
			| fichier     | type                            |
			| horloge.css | text/css; charset=utf-8         |
			| horloge.js  | text/javascript; charset=utf-8  |
			| cadran.svg  | image/svg+xml                   |

	Plan du Scénario: Un fichier statique inconnu, d'un type refusé, ou hors du répertoire, n'est pas servi
		Quand je demande à l'API « GET /plugins/horloge/static/<fichier> », sans jeton
		Alors l'API répond 404

		Exemples:
			| fichier              |
			| absent.css           |
			| notes.txt            |
			| ../secret.css        |
			| sous/horloge.css     |
			| .cache.css           |

	Scénario: Un plugin qui ne répond pas une Extension est ignoré, et consigné
		Étant donné le plugin « bavard » qui répond « bonjour » au point « intranet.extensions »
		Quand Machin intranet rassemble les extensions des plugins
		Alors le journal dit « plugin « bavard » : une extension de l'intranet est attendue »
		Et seules les routes du plugin « horloge » sont ajoutées

	Scénario: Une page au chemin invalide n'est pas ajoutée
		Étant donné le plugin « bancal » qui ajoute une page « ../evasion »
		Quand Machin intranet rassemble les extensions des plugins
		Alors le journal dit « plugin « bancal » : « /plugins/bancal/../evasion » n'est pas un chemin de l'intranet »
		Et seules les routes du plugin « horloge » sont ajoutées
