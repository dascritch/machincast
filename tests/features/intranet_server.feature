# language: fr
Fonctionnalité: Serveur intranet en HTTPS, éteint par défaut, et son certificat
	En tant que responsable de l'antenne,
	je veux allumer, depuis les paramètres du service, un serveur intranet qui n'écoute qu'en HTTPS, même sur une
	simple adresse IP de sous-réseau,
	afin d'ouvrir l'accès à distance à la demande, sans jamais l'exposer en clair.

	https://github.com/dascritch/machincast/issues/538, ticket enfant de
	https://github.com/dascritch/machincast/issues/524. Machin intranet (machincast.intranet) sert une application
	ASGI par Hypercorn, en TLS seulement. Sans certificat donné, il en génère un auto-signé, par openssl, au nom du
	poste et de chacune de ses adresses IP ; il le refait quand il ne couvre plus une adresse du poste.

	# ─── Configuration ─────────────────────────────────────

	Scénario: Sans section [intranet], le serveur est éteint, sur le port 8443, avec 30 minutes pour valider une connexion
		Quand je charge la configuration de test, sans section [intranet]
		Alors l'intranet est éteint, écoute « 0.0.0.0 » sur le port 8443, et laisse 30 minutes pour valider une connexion
		Et l'intranet n'a pas de certificat donné

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
			| sans_https = true                          | sans_https           |

	Scénario: Un certificat se donne avec sa clé, chemins relatifs au fichier de configuration
		Quand je charge la configuration de test, avec dans [intranet] : enabled = true, certificate = "tls/cert.pem", key = "tls/cle.pem"
		Alors l'intranet est allumé, avec le certificat « tls/cert.pem » et la clé « tls/cle.pem », à côté du fichier de configuration

	# ─── Certificat ────────────────────────────────────────

	Scénario: Sans certificat, Machin intranet en génère un, au nom du poste et de chacune de ses adresses
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
		Quand Machin intranet choisit son certificat
		Alors il prend le certificat donné, sans en générer

	Scénario: L'adresse à donner est celle d'écoute, ou, sur toutes les adresses, le nom de domaine interne et chaque adresse du poste
		Étant donné le poste « studio.radio.lan », aux adresses « 10.0.0.12 » et « fd00::12 »
		Alors les adresses à donner pour « 0.0.0.0 », port 8443, sont « https://studio.radio.lan:8443/ », « https://10.0.0.12:8443/ » et « https://[fd00::12]:8443/ »
		Et les adresses à donner pour « 10.0.0.12 », port 9443, sont « https://10.0.0.12:9443/ »

	Scénario: Sans nom de domaine interne, même en DHCP, l'intranet se joint par l'adresse IP de sous-réseau
		Étant donné le poste « studio », aux adresses « 10.0.0.12 »
		Alors les adresses à donner pour « 0.0.0.0 », port 8443, sont « https://10.0.0.12:8443/ »

	# ─── Serveur ───────────────────────────────────────────

	Scénario: Éteint, Machin intranet refuse de démarrer, et le dit
		Quand je lance Machin intranet avec l'intranet éteint
		Alors Machin intranet s'arrête avec le code 4
		Et son journal dit « l'intranet est éteint : intranet.enabled, ou la page « Intranet » des paramètres du service »

	Scénario: Allumé, Machin intranet répond en HTTPS, avec ses en-têtes de sécurité
		Quand je lance Machin intranet avec l'intranet allumé
		Alors une requête HTTPS « GET /login » reçoit 200, une page « Machin intranet »
		Et la réponse a les en-têtes :
			| en-tête                   | valeur                                                          |
			| strict-transport-security | max-age=31536000                                                |
			| x-content-type-options    | nosniff                                                         |
			| x-frame-options           | DENY                                                            |
			| referrer-policy           | no-referrer                                                     |
			| content-security-policy   | default-src 'self'; frame-ancestors 'none'; form-action 'self' |
			| cache-control             | no-store                                                        |
		Et la réponse ne nomme pas son serveur
		Et une requête HTTPS « GET /introuvable » reçoit 404
		Et une requête HTTPS « POST / » reçoit 405
		Et une requête en HTTP clair ne reçoit aucune réponse HTTP
		Et son journal donne l'adresse à donner et l'empreinte du certificat

	Scénario: Machin intranet s'arrête proprement à SIGTERM
		Quand je lance Machin intranet avec l'intranet allumé
		Et Machin intranet reçoit SIGTERM
		Alors Machin intranet s'arrête avec le code 0
