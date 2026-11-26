# language: fr
Fonctionnalité: Serveur intranet en HTTPS, éteint par défaut, et son certificat
	En tant que responsable de l'antenne,
	je veux allumer, depuis les paramètres du service, un serveur intranet qui n'écoute qu'en HTTPS, même sur une
	simple adresse IP de sous-réseau,
	afin d'ouvrir l'accès à distance à la demande, sans jamais l'exposer en clair.

	https://github.com/dascritch/machincast/issues/538, ticket enfant de
	https://github.com/dascritch/machincast/issues/524. Machin webserver (machincast.webserver) sert une application
	ASGI par Hypercorn, en TLS seulement. Sans certificat donné, il en génère un auto-signé, par openssl, au nom du
	poste et de chacune de ses adresses IP ; il le refait quand il ne couvre plus une adresse du poste.

	# ─── Configuration ─────────────────────────────────────

	Scénario: Sans section [intranet], le serveur est éteint, sur le port 8443, avec 30 minutes pour valider une connexion
		Quand je charge la configuration de test, sans section [intranet]
		Alors l'intranet est éteint, écoute « 0.0.0.0 » sur le port 8443, et laisse 30 minutes pour valider une connexion
		Et l'intranet n'a pas de certificat donné
		Et la première connexion se valide « au pupitre, avec un code »
		Et le second facteur est « aucun »

	Plan du scénario: Une section [intranet] incohérente est refusée, en nommant la clé
		Quand je charge la configuration de test, avec dans [intranet] : <valeurs>
		Alors la configuration est refusée en nommant « <clé> »

		Exemples:
			| valeurs                                    | clé                  |
			| port = 80                                  | intranet.port        |
			| port = 70000                               | intranet.port        |
			| port = "8443"                              | intranet.port        |
			| validation = 0                             | intranet.validation  |
			| validation = 2000                          | intranet.validation  |
			| address = "studio"                         | intranet.address     |
			| enabled = "oui"                            | intranet.enabled     |
			| certificate = "certificat.pem"             | intranet.certificate |
			| first_login = "personne"                   | intranet.first_login |
			| first_login = 1                            | intranet.first_login |
			| second_factor = "sms"                      | intranet.second_factor |
			| sans_https = true                          | sans_https           |

	Plan du scénario: La sécurité de la première connexion se règle
		https://github.com/dascritch/machincast/issues/600 : aucune, au pupitre, ou au pupitre avec un code.
		Quand je charge la configuration de test, avec dans [intranet] : first_login = "<valeur>"
		Alors la première connexion se valide « <validation> »

		Exemples:
			| valeur    | validation                  |
			| none      | sans validation             |
			| desk      | au pupitre                  |
			| desk_code | au pupitre, avec un code    |

	Plan du scénario: Le second facteur se règle
		https://github.com/dascritch/machincast/issues/601 : aucun, l'application d'authentification de chaque compte, ou le
		pupitre, à chaque connexion.
		Quand je charge la configuration de test, avec dans [intranet] : second_factor = "<valeur>"
		Alors le second facteur est « <facteur> »

		Exemples:
			| valeur | facteur                          |
			| none   | aucun                            |
			| totp   | application d'authentification   |
			| desk   | au pupitre                       |

	Plan du scénario: En production, aucune validation n'est pas possible : Machin webserver demande le pupitre et son code
		https://github.com/dascritch/machincast/issues/600 : la production, c'est le serveur intranet installé en service.
		Quand je charge la configuration de test, avec dans [intranet] : first_login = "<valeur>"
		Et Machin webserver prend ses réglages, <installation>
		Alors la première connexion se valide « <validation> »
		Et son journal <dit>

		Exemples:
			| valeur | installation           | validation               | dit                                                                                                                      |
			| none   | installé en service     | au pupitre, avec un code | dit « la première connexion sans validation est impossible en production : elle se valide au pupitre, avec un code »     |
			| none   | sans le service         | sans validation          | ne dit rien                                                                                                              |
			| desk   | installé en service     | au pupitre               | ne dit rien                                                                                                              |

	Scénario: Un certificat se donne avec sa clé, chemins relatifs au fichier de configuration
		Quand je charge la configuration de test, avec dans [intranet] : enabled = true, certificate = "tls/cert.pem", key = "tls/cle.pem"
		Alors l'intranet est allumé, avec le certificat « tls/cert.pem » et la clé « tls/cle.pem », à côté du fichier de configuration

	# ─── Certificat ────────────────────────────────────────

	Scénario: Sans certificat, Machin webserver en génère un, au nom du poste et de chacune de ses adresses
		Quand le certificat de l'intranet est assuré pour les noms « studio », « studio.radio.lan » et les adresses « 10.0.0.12 », « 127.0.0.1 »
		Alors un certificat a été généré
		Et le certificat nomme « DNS:studio », « DNS:studio.radio.lan », « IP Address:10.0.0.12 » et « IP Address:127.0.0.1 »
		Et le certificat est un certificat de serveur, auto-signé, valable 825 jours
		Et seule le compte peut lire la clé du certificat

	Scénario: Un certificat qui couvre encore le poste est gardé
		Quand le certificat de l'intranet est assuré pour les noms « studio » et les adresses « 10.0.0.12 », « 127.0.0.1 »
		Et le certificat de l'intranet est assuré pour les noms « studio » et les adresses « 10.0.0.12 », « 127.0.0.1 »
		Alors un seul certificat a été généré

	Scénario: Une nouvelle adresse du poste, en DHCP, fait refaire le certificat
		Quand le certificat de l'intranet est assuré pour les noms « studio » et les adresses « 10.0.0.12 », « 127.0.0.1 »
		Et le certificat de l'intranet est assuré pour les noms « studio » et les adresses « 10.0.0.31 », « 127.0.0.1 »
		Alors deux certificats ont été générés
		Et le certificat nomme « IP Address:10.0.0.31 »

	Scénario: Un certificat donné dans la configuration n'est jamais touché
		Étant donné un certificat donné dans la configuration de l'intranet
		Quand Machin webserver choisit son certificat
		Alors il prend le certificat donné, sans en générer

	Scénario: L'adresse à donner est celle d'écoute, ou, sur toutes les adresses, le nom de domaine interne et chaque adresse du poste
		Étant donné le poste « studio.radio.lan », aux adresses « 10.0.0.12 » et « fd00::12 »
		Alors les adresses à donner pour « 0.0.0.0 », port 8443, sont « https://studio.radio.lan:8443/ », « https://10.0.0.12:8443/ » et « https://[fd00::12]:8443/ »
		Et les adresses à donner pour « 10.0.0.12 », port 9443, sont « https://10.0.0.12:9443/ »

	Scénario: Sans nom de domaine interne, même en DHCP, l'intranet se joint par l'adresse IP de sous-réseau
		Étant donné le poste « studio », aux adresses « 10.0.0.12 »
		Alors les adresses à donner pour « 0.0.0.0 », port 8443, sont « https://10.0.0.12:8443/ »

	# ─── Le PID de Machin webserver (https://github.com/dascritch/machincast/issues/550) ───

	Plan du scénario: Machin webserver se reconnaît à ses arguments, élément par élément, jamais par sous-chaîne
		Alors des arguments « <arguments> » <verdict> ceux de Machin webserver

		Exemples:
			| arguments                                                                   | verdict     |
			| /opt/machincast/.venv/bin/python /opt/machincast/.venv/bin/Machin_webserver  | sont        |
			| /usr/bin/python3 -m machincast.webserver --config machincast.toml            | sont        |
			| vim src/machincast/webserver/app.py                                          | ne sont pas |
			| /usr/bin/python3 -m machincast.webserver.process                             | ne sont pas |
			| less /var/log/Machin_webserver.log                                           | ne sont pas |
			| grep -r intranet .                                                          | ne sont pas |

	Scénario: Un Machin webserver d'un autre compte ne compte pas
		Étant donné un Machin webserver qui tourne, son PID noté
		Quand l'interface le cherche sous un autre compte
		Alors elle ne le trouve pas

	# ─── Mode test, sans le service (https://github.com/dascritch/machincast/issues/549) ───

	Scénario: En mode test, Machin player et Machin webserver, sous le même compte, s'accordent sur la socket de l'intranet
		Sans le service, Machin webserver tourne sous le compte qui le lance, et lit la socket que lui ouvre le Machin
		player de ce compte, à côté de sa socket d'état, privée au compte.
		Étant donné un poste sans le service de diffusion, le répertoire d'exécution du compte dans un répertoire temporaire
		Quand je charge la configuration de test, sans section [player]
		Alors la socket de l'intranet est « intranet.sock », à côté de la socket d'état « lecture.sock »
		Et un Machin player qui diffuse sur ces sockets donne son état à Machin webserver, par la socket de l'intranet

	# ─── Serveur ───────────────────────────────────────────

	Scénario: Éteint, Machin webserver refuse de démarrer, et le dit
		Quand je lance Machin webserver avec l'intranet éteint
		Alors Machin webserver s'arrête avec le code 4
		Et son journal dit « l'intranet est éteint : intranet.enabled, ou la page « Intranet » des paramètres du service »

	Plan du scénario: Une connexion TLS que le navigateur a déjà fermée ne laisse pas de traceback au journal
		https://github.com/dascritch/machincast/issues/572 : le navigateur envoie encore des données après sa
		fermeture TLS ; Hypercorn ne rattrape pas l'erreur de wait_closed, qu'asyncio écrivait en exception non gérée.
		Quand la boucle de Machin webserver rencontre l'exception « <exception> »
		Alors le journal de la boucle <verdict>

		Exemples:
			| exception                                                                                          | verdict          |
			| SSLError: [SSL: APPLICATION_DATA_AFTER_CLOSE_NOTIFY] application data after close notify (_ssl.c:2839) | ne dit rien      |
			| SSLError: [SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1029)                           | dit l'exception  |
			| RuntimeError: panne imitée                                                                         | dit l'exception  |

	Scénario: Une page qui plante répond 500, et le journal donne le traceback de son erreur
		https://github.com/dascritch/machincast/issues/574 : le journal ne disait que « intranet: request … failed ».
		Étant donné une page « /panne » de l'intranet qui plante sur « base injoignable »
		Quand je demande la page « /panne », le journal de Machin webserver configuré
		Alors la réponse est 500, « Erreur interne. »
		Et la sortie d'erreur dit « intranet : la requête /panne a échoué », puis le traceback de « RuntimeError: base injoignable »

	Scénario: Allumé, Machin webserver répond en HTTPS, avec ses en-têtes de sécurité
		Quand je lance Machin webserver avec l'intranet allumé
		Alors une requête HTTPS « GET /login » reçoit 200, une page « Machin webserver »
		Et la réponse a les en-têtes :
			| en-tête                   | valeur                                                          |
			| strict-transport-security | max-age=31536000                                                |
			| x-content-type-options    | nosniff                                                         |
			| x-frame-options           | DENY                                                            |
			| referrer-policy           | same-origin                                                     |
			| content-security-policy   | default-src 'self'; frame-ancestors 'none'; form-action 'self' |
			| cache-control             | no-store                                                        |
		Et la réponse ne nomme pas son serveur
		Et une requête HTTPS « GET /introuvable » reçoit 404
		Et une requête HTTPS « POST / » reçoit 405
		Et une requête en HTTP clair ne reçoit aucune réponse HTTP
		Et son journal donne l'adresse à donner et l'empreinte du certificat

	Scénario: Machin webserver s'arrête proprement à SIGTERM, son PID noté le temps qu'il sert
		https://github.com/dascritch/machincast/issues/544 : l'interface le retrouve par ce PID pour l'arrêter.
		Quand je lance Machin webserver avec l'intranet allumé
		Alors son PID est noté dans son répertoire d'état
		Quand Machin webserver reçoit SIGTERM
		Alors Machin webserver s'arrête avec le code 0
		Et son PID n'est plus noté
