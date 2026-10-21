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

	# ─── Raccourci et icône de l'interface (https://github.com/dascritch/machincast/issues/62) ─────
	# install.sh installe le raccourci que rédige machincast.installation dans le menu des applications du compte, et,
	# sur demande, sur son bureau. Lancé depuis une icône, le programme démarre dans le répertoire de MachinCast.

	Scénario: Le raccourci lance Machin interface depuis le répertoire de MachinCast, avec son icône
		Quand je lance « python -m machincast.installation raccourci » avec la configuration de test
		Alors la commande se termine sans erreur
		Et le raccourci a, dans la section « Desktop Entry » :
			| clé            | valeur                                                 |
			| Type           | Application                                            |
			| Version        | 1.5                                                    |
			| Name           | MachinCast                                             |
			| GenericName    | Diffusion radio automatisée                            |
			| Comment        | Programmer l'antenne et suivre la diffusion            |
			| Exec           | <répertoire>/bin/Machin interface                      |
			| Path           | <répertoire>                                           |
			| Icon           | <répertoire>/src/machincast/interface/machincast.png   |
			| Terminal       | false                                                  |
			| Categories     | AudioVideo;Audio;                                      |
			| Keywords       | radio;antenne;diffusion;programmation;                 |
			| StartupNotify  | true                                                   |
			| StartupWMClass | MachinCast                                             |

	Plan du scénario: Le raccourci suit le répertoire de MachinCast, quel qu'il soit
		Quand le raccourci est rédigé pour le répertoire « <répertoire> »
		Alors le raccourci a, dans la section « Desktop Entry », entre autres :
			| clé  | valeur      |
			| Exec | <exec>      |
			| Path | <répertoire> |
			| Icon | <répertoire>/src/machincast/interface/machincast.png |

		Exemples:
			| répertoire                    | exec                                                |
			| /home/radio/machincast        | /home/radio/machincast/bin/Machin interface         |
			| /home/radio/Ma radio/machincast | "/home/radio/Ma radio/machincast/bin/Machin" interface |
			| /home/radio/l'antenne         | "/home/radio/l'antenne/bin/Machin" interface        |
			| /home/radio/100%              | /home/radio/100%%/bin/Machin interface              |
			| /home/radio/$HOME             | "/home/radio/\\\\$HOME/bin/Machin" interface        |

	Scénario: desktop-file-validate accepte le raccourci
		Étant donné l'outil « desktop-file-validate » du poste
		Quand je lance « python -m machincast.installation raccourci » avec la configuration de test
		Et j'enregistre sa sortie en « machincast.desktop »
		Alors « desktop-file-validate » accepte « machincast.desktop »

	Scénario: L'icône de MachinCast, le logo des équipes techniques de la radio, se lit de 16 à 256 pixels
		[#213](https://github.com/dascritch/machincast/issues/213) : un panneau de chantier orange en losange, avec un casque audio.

		Alors l'icône de MachinCast est une image PNG carrée de 512 pixels, aux coins transparents
		Et rendue en 16, 24, 32, 48, 64, 128 et 256 pixels, l'icône montre son losange orange et son casque noir

	Scénario: L'interface porte l'icône de MachinCast et le nom de son raccourci
		Quand l'application Qt de l'interface est créée
		Alors sa fenêtre a l'icône de MachinCast
		Et l'application se réclame du raccourci « machincast »

	# ─── Icône choisie (https://github.com/dascritch/machincast/issues/111) ─────

	Scénario: Le raccourci prend l'icône choisie dans la configuration
		Étant donné une image PNG « logo.png »
		Quand je lance « python -m machincast.installation raccourci » avec une configuration dont l'icône est cette image
		Alors la commande se termine sans erreur
		Et le raccourci a l'icône de cette image

	Scénario: Une icône choisie introuvable laisse au raccourci l'icône de MachinCast
		Quand le raccourci est rédigé pour le répertoire « /home/radio/machincast », avec l'icône « /home/radio/disparu.png »
		Alors le raccourci a, dans la section « Desktop Entry », entre autres :
			| clé  | valeur                                                     |
			| Icon | /home/radio/machincast/src/machincast/interface/machincast.png |
