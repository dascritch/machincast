# language: fr
Fonctionnalité: Connexion à l'intranet, validée au pupitre par un code à 6 chiffres
	En tant que membre de l'équipe, depuis un autre poste,
	je veux me connecter à l'intranet par mon nom et mon mot de passe, puis faire valider ma connexion au pupitre par
	un code à 6 chiffres,
	afin que personne ne se connecte à distance sans que le studio le sache.

	https://github.com/dascritch/machincast/issues/539, ticket enfant de
	https://github.com/dascritch/machincast/issues/524. Les requêtes passent directement à l'application ASGI
	(tests/asgi_client.py), sur la base de test, au rôle machincast_intranet ; 30 minutes pour valider, des sessions de
	12 heures.

	Contexte:
		Étant donné les comptes de l'intranet :
			| nom       | mot de passe    | rôle      | état      |
			| regie     | tisane-au-micro | consulter | actif     |
			| stagiaire | cafe-du-matin-1 | consulter | désactivé |
		Et l'application de l'intranet sur la base de test

	Scénario: Sans session, l'accueil mène à la mire de connexion
		Quand je demande « GET / »
		Alors la réponse est 303, vers « /login »
		Quand je demande « GET /login »
		Alors la réponse est 200, une page qui demande le nom d'utilisateur et le mot de passe, sans récupération de mot de passe

	Plan du scénario: Des identifiants refusés laissent la mire, sans dire si le compte existe
		Quand je me connecte en « <nom> », mot de passe « <mot de passe> »
		Alors la réponse est 401, et dit « Nom inconnu, compte désactivé ou mot de passe faux. »
		Et aucun cookie de session n'est posé
		Et aucune session n'est ouverte

		Exemples:
			| nom       | mot de passe    |
			| regie     | mauvais-mot     |
			| inconnu   | tisane-au-micro |
			| stagiaire | cafe-du-matin-1 |

	Scénario: Des identifiants valides ouvrent une session à valider, et demandent une action au pupitre
		Quand je me connecte en « regie », mot de passe « tisane-au-micro »
		Alors la réponse est 303, vers « /validation »
		Et le cookie de session est posé, Secure, HttpOnly et SameSite=Strict
		Et la base a une session à valider de « regie », depuis « 10.0.0.31 », navigateur « Firefox/140 (scénario) », avec un code à 6 chiffres, à valider sous 30 minutes
		Et la base ne garde que l'empreinte SHA-256 du cookie
		Quand je demande « GET /validation »
		Alors la réponse est 200, et dit « Une action doit être faite au pupitre »
		Quand je demande « GET / »
		Alors la réponse est 303, vers « /validation »

	Scénario: Le code donné au pupitre valide la session, pour 12 heures, et mène à l'accueil
		Étant donné que je me suis connecté en « regie », mot de passe « tisane-au-micro »
		Quand je saisis le code donné au pupitre
		Alors la réponse est 303, vers « / »
		Et la session est valide, pour 12 heures
		Quand je demande « GET / »
		Alors la réponse est 200, et dit « Accueil — Machin intranet »

	Scénario: Le code se saisit aussi avec une espace entre ses deux moitiés, comme le pupitre le montre
		Étant donné que je me suis connecté en « regie », mot de passe « tisane-au-micro »
		Quand je saisis le code donné au pupitre, en deux groupes de trois chiffres
		Alors la session est valide, pour 12 heures

	Scénario: Un code faux se redemande ; au cinquième, la session est invalide, et il faut se reconnecter
		Étant donné que je me suis connecté en « regie », mot de passe « tisane-au-micro »
		Quand je saisis un code faux
		Alors la réponse est 400, et dit « Code faux : redemandez-le au pupitre. »
		Quand je saisis un code faux 4 fois
		Alors la réponse est 401, et dit « Connexion non validée à temps, ou trop de codes faux : reconnectez-vous. »
		Et la session est invalide
		Quand je saisis le code donné au pupitre
		Alors la session est invalide

	Scénario: Passé le délai de validation, la session est invalide
		Étant donné que je me suis connecté en « regie », mot de passe « tisane-au-micro »
		Et que le délai de validation est passé
		Quand je saisis le code donné au pupitre
		Alors la réponse est 401, et dit « Connexion non validée à temps, ou trop de codes faux : reconnectez-vous. »
		Et la session est invalide

	Scénario: Se déconnecter rend la session invalide, et efface son cookie
		Étant donné que je me suis connecté en « regie », mot de passe « tisane-au-micro »
		Et que j'ai saisi le code donné au pupitre
		Quand je demande « POST /logout »
		Alors la réponse est 303, vers « /login »
		Et le cookie de session est effacé
		Et la session est invalide

	Scénario: Le jeton de la session sert aussi en « Authorization: Bearer », pour l'API
		Étant donné que je me suis connecté en « regie », mot de passe « tisane-au-micro »
		Et que j'ai saisi le code donné au pupitre
		Quand je demande « GET / » avec le jeton en « Authorization: Bearer », sans cookie
		Alors la réponse est 200, et dit « Accueil — Machin intranet »

	Scénario: Un compte désactivé perd ses sessions valides
		Étant donné que je me suis connecté en « regie », mot de passe « tisane-au-micro »
		Et que j'ai saisi le code donné au pupitre
		Et que le compte « regie » est désactivé
		Quand je demande « GET / »
		Alors la réponse est 303, vers « /login »

	Scénario: Trop d'échecs d'une même adresse la font attendre
		Quand je me connecte 5 fois en « regie », mot de passe « mauvais-mot »
		Et je me connecte en « regie », mot de passe « tisane-au-micro »
		Alors la réponse est 429, et dit « Trop d'essais refusés : attendez un quart d'heure. »
		Et aucune session n'est ouverte

	Scénario: Un formulaire envoyé d'un autre site est refusé
		Quand je me connecte en « regie », mot de passe « tisane-au-micro », depuis l'origine « https://ailleurs.example »
		Alors la réponse est 403
		Et aucune session n'est ouverte

	Scénario: Un corps de requête trop gros est refusé
		Quand j'envoie à « /login » un formulaire de 100000 octets
		Alors la réponse est 413
