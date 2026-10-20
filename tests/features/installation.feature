# language: fr
Fonctionnalité: Vérifications de l'installation
	En tant que technicien d'antenne,
	je veux qu'un seul script installe MachinCast sur un poste Ubuntu 26.04 LTS,
	afin que l'installation soit reproductible.

	install.sh enchaîne des commandes système et n'est pas testé ici ; il s'appuie sur machincast.installation,
	dont ces scénarios vérifient les étapes : noms des bases, greffons GStreamer et sortie audio.

	# ─── Greffons GStreamer ────────────────────────────────────

	Scénario: Avec les paquets installés, chaque format de la spec a son décodeur
		Quand je vérifie les décodeurs GStreamer
		Alors aucun format sonore ne manque de décodeur

	Plan du scénario: Un format sans décodeur est signalé avec le paquet à installer
		Étant donné les éléments GStreamer qui lisent « <caps> » désactivés
		Quand je vérifie les décodeurs GStreamer
		Alors le format <format> manque, avec le paquet « <paquet> »

		Exemples:
			| caps                                       | format | paquet                    |
			| audio/x-aiff                               | aiff   | gstreamer1.0-plugins-bad  |
			| audio/mpeg, mpegversion=(int)1, layer=(int)3 | mp3    | gstreamer1.0-plugins-good |
			| audio/x-vorbis                             | ogg    | gstreamer1.0-plugins-base |
			| audio/mpeg, mpegversion=(int)4             | m4a    | gstreamer1.0-plugins-bad  |
			| audio/mpeg, mpegversion=(int)4, stream-format=(string)adts | aac | gstreamer1.0-plugins-good |

	# ─── Source des streams (https://github.com/dascritch/machincast/issues/16) ───

	Scénario: Avec les paquets installés, les streams HTTP et HTTPS ont leur source
		Quand je vérifie la source des streams
		Alors aucun protocole de stream ne manque de source

	Scénario: Un protocole de stream sans source est signalé avec le paquet à installer
		Étant donné les sources GStreamer du protocole « http » désactivées
		Quand je vérifie la source des streams
		Alors le format stream http manque, avec le paquet « gstreamer1.0-plugins-good »

	# ─── Sortie audio ──────────────────────────────────────────

	Scénario: La sortie audio configurée est créée, sans jouer de son
		Quand je vérifie la sortie audio de la configuration de test
		Alors la sortie audio est disponible

	Scénario: Une sortie audio dont le greffon manque est signalée avec le paquet à installer
		Quand je vérifie une sortie audio dont le greffon GStreamer n'existe pas
		Alors la sortie audio manque, avec le paquet « gstreamer1.0-inexistant »

	# ─── En ligne de commande ──────────────────────────────────

	Scénario: Les paramètres des bases sont lus dans la configuration, une valeur par ligne
		Quand je lance « python -m machincast.installation bases » avec la configuration de test
		Alors la commande se termine sans erreur
		Et elle affiche la socket, la base de production puis la base de test de cette configuration

	Scénario: La vérification en ligne de commande réussit quand rien ne manque
		Quand je lance « python -m machincast.installation verifier » avec la configuration de test
		Alors la commande se termine sans erreur
		Et sa sortie annonce « décodeurs, source des streams et sortie audio disponibles »

	Scénario: L'application du schéma signale une base injoignable
		Quand je lance « python -m machincast.installation migrer » avec une configuration dont la socket n'existe pas
		Alors la commande se termine avec le code 1
		Et sa sortie d'erreur mentionne « base de données injoignable »

	# ─── Service systemd (https://github.com/dascritch/machincast/issues/22) ─────
	# Facultatif, pour un ordinateur dédié à l'antenne : install.sh --service installe l'unité et la règle polkit que
	# rédige machincast.installation. Le service tourne sous le compte de MachinCast, dont la session garde PipeWire.

	Scénario: L'unité du service lance Machin lecture sous le compte de MachinCast, et la relance après un plantage
		Quand je lance « python -m machincast.installation unite » avec la configuration de test
		Alors la commande se termine sans erreur
		Et l'unité a, dans la section « Unit » :
			| clé         | valeur                                                     |
			| Description | MachinCast : diffusion de l'antenne (Machin lecture)       |
			| Wants       | network-online.target                                      |
			| After       | network-online.target postgresql.service sound.target      |
		Et l'unité a, dans la section « Service » :
			| clé              | valeur                                          |
			| Type             | simple                                          |
			| User             | <compte>                                        |
			| Group            | <groupe>                                        |
			| WorkingDirectory | <répertoire>                                    |
			| Environment      | XDG_RUNTIME_DIR=/run/user/<uid>                 |
			| ExecStart        | <répertoire>/bin/Machin lecture                 |
			| Restart          | on-failure                                      |
			| RestartSec       | 5                                               |
			| KillSignal       | SIGTERM                                         |
			| TimeoutStopSec   | 15                                              |
			| SyslogIdentifier | machincast                                      |
		Et l'unité a, dans la section « Install » :
			| clé      | valeur            |
			| WantedBy | multi-user.target |

	Scénario: L'unité et la règle suivent le compte de MachinCast, quel qu'il soit
		Quand l'unité et la règle sont rédigées pour le compte « radio », du groupe « antenne », d'uid 1001, dans « /home/radio/machincast »
		Alors l'unité a, dans la section « Service », entre autres :
			| clé              | valeur                                |
			| User             | radio                                 |
			| Group            | antenne                               |
			| WorkingDirectory | /home/radio/machincast                |
			| Environment      | XDG_RUNTIME_DIR=/run/user/1001        |
			| ExecStart        | /home/radio/machincast/bin/Machin lecture |
		Et la règle ne concerne que le compte « radio »

	Scénario: systemd accepte l'unité du service
		Étant donné l'outil « systemd-analyze » du poste
		Quand je lance « python -m machincast.installation unite » avec la configuration de test
		Et j'enregistre sa sortie en « machincast.service »
		Alors « systemd-analyze verify » accepte « machincast.service »

	Plan du scénario: La règle polkit n'autorise que démarrer, arrêter et redémarrer le service, par un administrateur, au compte de MachinCast
		Étant donné l'outil « node » du poste
		Quand je lance « python -m machincast.installation regle » avec la configuration de test
		Alors la règle polkit répond <reponse> à l'action « <action> » sur « <unite> », verbe « <verbe> », pour <qui>

		Exemples:
			| action                                 | unite              | verbe   | qui                  | reponse         |
			| org.freedesktop.systemd1.manage-units  | machincast.service | start   | le compte            | « auth_admin »  |
			| org.freedesktop.systemd1.manage-units  | machincast.service | stop    | le compte            | « auth_admin »  |
			| org.freedesktop.systemd1.manage-units  | machincast.service | restart | le compte            | « auth_admin »  |
			| org.freedesktop.systemd1.manage-units  | machincast.service | enable  | le compte            | rien            |
			| org.freedesktop.systemd1.manage-units  | ssh.service        | stop    | le compte            | rien            |
			| org.freedesktop.systemd1.manage-units  | machincast.service | stop    | un autre compte      | rien            |
			| org.freedesktop.systemd1.manage-unit-files | machincast.service | stop | le compte          | rien            |

	Scénario: L'unité porte le nom que le wrapper suit dans le journal
		Alors l'unité de machincast.installation est celle de « Machin logs »
