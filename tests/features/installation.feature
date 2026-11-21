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
			| audio/mpeg, mpegversion=(int)1, layer=(int)3 | mp3    | gstreamer1.0-plugins-good |
			| audio/x-vorbis                             | ogg    | gstreamer1.0-plugins-base |
			| audio/mpeg, mpegversion=(int)4             | m4a    | gstreamer1.0-plugins-bad  |
			| audio/mpeg, mpegversion=(int)4, stream-format=(string)adts | aac | gstreamer1.0-plugins-good |

	# ─── Version de GStreamer (https://github.com/dascritch/machincast/issues/284) ───
	# MachinCast est vérifié avec GStreamer 1.28, celui d'Ubuntu 26.04 LTS : une version plus ancienne est signalée,
	# sans bloquer l'installation, avec le paquet à mettre à jour. La suite de tests tourne sur la version vérifiée.

	Scénario: GStreamer et ses greffons sont au moins dans la version vérifiée
		Le poste qui fait tourner la suite de tests est en Ubuntu 26.04 LTS, ou plus récent : ce scénario échoue sur un
		poste plus ancien, dont les résultats ne valent pas pour la version cible.

		Quand je vérifie la version de GStreamer
		Alors aucune version de GStreamer n'est plus ancienne que la version vérifiée

	Plan du scénario: Une version plus ancienne que la version vérifiée est signalée, avec le paquet à mettre à jour
		Étant donné <composant> en version « <version> »
		Quand je vérifie la version de GStreamer
		Alors <composant> est signalé en version « <version> », avec le paquet « <paquet> »

		Exemples:
			| composant                     | version | paquet                    |
			| GStreamer                     | 1.24.2  | libgstreamer1.0-0         |
			| le greffon GStreamer playback | 1.27.90 | gstreamer1.0-plugins-base |
			| le greffon GStreamer flac     | 1.24.2  | gstreamer1.0-plugins-good |
			| le greffon GStreamer faad     | 1.20.1  | gstreamer1.0-plugins-bad  |

	Plan du scénario: Une version égale ou plus récente que la version vérifiée n'est pas signalée
		Étant donné GStreamer en version « <version> »
		Quand je vérifie la version de GStreamer
		Alors GStreamer n'est pas signalé

		Exemples:
			| version |
			| 1.28.0  |
			| 1.28.2  |
			| 1.30.1  |
			| 2.0.0   |

	Scénario: La vérification en ligne de commande signale une version plus ancienne, sans échouer
		Étant donné GStreamer en version « 1.24.2 »
		Quand je vérifie les greffons comme la ligne de commande
		Alors la vérification réussit
		Et le journal avertit « GStreamer 1.24.2 : MachinCast est vérifié avec la version 1.28 (Ubuntu 26.04 LTS) ; mettre à jour libgstreamer1.0-0 »

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
		Quand je lance « python -m machincast.installation databases » avec la configuration de test
		Alors la commande se termine sans erreur
		Et elle affiche la socket, la base de production puis la base de test de cette configuration

	Scénario: La vérification en ligne de commande réussit quand rien ne manque
		Quand je lance « python -m machincast.installation check » avec la configuration de test
		Alors la commande se termine sans erreur
		Et sa sortie annonce « décodeurs, source des streams et sortie audio disponibles »

	Scénario: L'application du schéma signale une base injoignable
		Quand je lance « python -m machincast.installation migrate » avec une configuration dont la socket n'existe pas
		Alors la commande se termine avec le code 1
		Et sa sortie d'erreur mentionne « base de données injoignable »

	# ─── Service systemd (https://github.com/dascritch/machincast/issues/22) ─────
	# Facultatif, pour un ordinateur dédié à l'antenne : install.sh --service installe les unités, la règle polkit et les
	# configurations que rédige machincast.installation. Le service tourne sous son propre compte, machincast, avec son
	# PipeWire et son WirePlumber, sans session ouverte (https://github.com/dascritch/machincast/issues/381) ; le compte
	# de MachinCast rejoint son groupe, qui lit ses logs et pré-écoute l'antenne.

	Plan du scénario: install.sh --service refuse une antenne sur la sortie factice ou PulseAudio, et recommande une autre sortie
		https://github.com/dascritch/machincast/issues/339 : l'antenne d'un poste dédié joue toujours sur une carte son,
		par le PipeWire du service (https://github.com/dascritch/machincast/issues/381). install.sh --service lance cette
		vérification avant d'installer le service, et s'arrête si elle échoue.

		Quand je lance « python -m machincast.installation on-air » avec une configuration sur la sortie « <sortie> », l'antenne <antenne>
		Alors la commande se termine avec le code <code>
		Et sa sortie <flux> « <message> »

		Exemples:
			| sortie     | antenne        | code | flux               | message |
			| pipewire   | « carte-1 »    | 0    | annonce            | antenne sur la sortie pipewire, périphérique carte-1 : le service de diffusion peut l'utiliser |
			| alsa       | « hw:1,0 »     | 0    | annonce            | antenne sur la sortie alsa, périphérique hw:1,0 : le service de diffusion peut l'utiliser |
			| pipewire   | non renseignée | 0    | d'erreur mentionne | antenne sur la sortie pipewire, à renseigner : le service de diffusion refusera de démarrer tant que audio.device ne la donne pas |
			| pipewire   | « dummy »      | 1    | d'erreur mentionne | antenne sur la sortie factice : le service de diffusion ne jouerait aucun son ; choisir une autre carte son dans Machin interface, Fichier → Paramètres du service…, page Audio, puis relancer ./install.sh --service |
			| dummy      | « carte-1 »    | 1    | d'erreur mentionne | antenne sur la sortie factice : le service de diffusion ne jouerait aucun son ; choisir une autre carte son dans Machin interface, Fichier → Paramètres du service…, page Audio, puis relancer ./install.sh --service |
			| pulseaudio | « carte-1 »    | 1    | d'erreur mentionne | antenne sur la sortie PulseAudio : le service de diffusion joue par son propre PipeWire ; choisir la sortie PipeWire dans Machin interface, Fichier → Paramètres du service…, page Audio, puis relancer ./install.sh --service |

	Plan du scénario: Sans --service, un service déjà installé se met à jour comme avec --service, ses minuteurs comme ils étaient
		https://github.com/dascritch/machincast/issues/557 : une mise à jour du poste par ./install.sh, sans
		--service, mettait à jour le reste, mais laissait le service tel quel s'il semblait à jour, ou demandait de le
		faire. Le poste est déjà dédié à l'antenne : la question n'est pas reposée. Le choix de --no-timers tient.
		Étant donné l'unité du service <unité>, et le minuteur des tâches <minuteur>
		Quand install.sh décide du service, avec les options « <options> »
		Alors install.sh <décision>

		Exemples:
			| options          | unité     | minuteur | décision                                                                   |
			|                  | installée | installé | met le service à jour, avec ses minuteurs, sans redemander le poste dédié |
			|                  | installée | absent   | met le service à jour, sans minuteurs, sans redemander le poste dédié     |
			|                  | absente   | absent   | n'installe pas le service                                                  |
			| --service        | absente   | absent   | installe le service, avec ses minuteurs, en demandant le poste dédié      |
			| --remove-service | installée | installé | retire le service                                                          |

	Scénario: install.sh reprend le service installé avant de demander le poste dédié, et dès le début
		Alors install.sh reprend le service installé avant de demander le poste dédié, seulement s'il n'est pas déjà installé

	Scénario: install.sh vérifie l'antenne avant d'installer le service
		Alors install.sh vérifie l'antenne par « installation on-air » avant la première étape du service, et s'arrête si elle échoue

	Scénario: L'unité du service lance Machin player sous le compte du service, par son PipeWire, et la relance après un plantage
		Quand je lance « python -m machincast.installation unit » avec la configuration de test
		Alors la commande se termine sans erreur
		Et l'unité a, dans la section « Unit » :
			| clé         | valeur                                                                                                       |
			| Description | MachinCast: on-air broadcast (Machin player)                                                                 |
			| Wants       | network-online.target                                                                                        |
			| Requires    | machincast-pipewire.service machincast-wireplumber.service                                                   |
			| After       | network-online.target postgresql.service sound.target machincast-pipewire.service machincast-wireplumber.service |
		Et l'unité a, dans la section « Service » :
			| clé                      | valeur                                  |
			| Type                     | simple                                  |
			| User                     | machincast                              |
			| Group                    | machincast                              |
			| SupplementaryGroups      | audio                                   |
			| UMask                    | 0007                                    |
			| Environment              | HOME=/var/lib/machincast                |
			| Environment              | XDG_RUNTIME_DIR=/run/machincast         |
			| Environment              | PIPEWIRE_RUNTIME_DIR=/run/machincast    |
			| WorkingDirectory         | <répertoire>                            |
			| ExecStart                | <répertoire>/bin/Machin player          |
			| Restart                  | on-failure                              |
			| RestartSec               | 5                                       |
			| RestartPreventExitStatus | 2                                       |
			| KillSignal               | SIGTERM                                 |
			| TimeoutStopSec           | 15                                      |
			| SyslogIdentifier         | machincast                              |
		Et l'unité a, dans la section « Install » :
			| clé      | valeur            |
			| WantedBy | multi-user.target |

	Scénario: Le PipeWire du service tourne sous son compte, sans session ouverte, sa socket au groupe du service
		Quand je lance « python -m machincast.installation pipewire-unit » avec la configuration de test
		Alors la commande se termine sans erreur
		Et l'unité a, dans la section « Unit » :
			| clé         | valeur                                              |
			| Description | MachinCast: PipeWire of the broadcast service       |
			| After       | sound.target systemd-tmpfiles-setup.service         |
		Et l'unité a, dans la section « Service » :
			| clé                 | valeur                               |
			| Type                | simple                               |
			| User                | machincast                           |
			| Group               | machincast                           |
			| SupplementaryGroups | audio                                |
			| UMask               | 0007                                 |
			| Environment         | HOME=/var/lib/machincast             |
			| Environment         | XDG_RUNTIME_DIR=/run/machincast      |
			| Environment         | PIPEWIRE_RUNTIME_DIR=/run/machincast |
			| StateDirectory      | machincast                           |
			| ExecStart           | /usr/bin/pipewire                    |
			| Restart             | on-failure                           |
			| RestartSec          | 2                                    |
			| SyslogIdentifier    | machincast-pipewire                  |
		Et l'unité a, dans la section « Install » :
			| clé      | valeur            |
			| WantedBy | multi-user.target |

	Scénario: Le WirePlumber du service suit son PipeWire, sans lire la configuration des sessions du poste
		Quand je lance « python -m machincast.installation wireplumber-unit » avec la configuration de test
		Alors la commande se termine sans erreur
		Et l'unité a, dans la section « Unit » :
			| clé         | valeur                                           |
			| Description | MachinCast: WirePlumber of the broadcast service |
			| BindsTo     | machincast-pipewire.service                      |
			| After       | machincast-pipewire.service                      |
		Et l'unité a, dans la section « Service » :
			| clé                 | valeur                                                                 |
			| Type                | simple                                                                 |
			| User                | machincast                                                             |
			| Group               | machincast                                                             |
			| SupplementaryGroups | audio                                                                  |
			| UMask               | 0007                                                                   |
			| Environment         | HOME=/var/lib/machincast                                               |
			| Environment         | XDG_RUNTIME_DIR=/run/machincast                                        |
			| Environment         | PIPEWIRE_RUNTIME_DIR=/run/machincast                                   |
			| Environment         | WIREPLUMBER_CONFIG_DIR=/etc/machincast/wireplumber:/usr/share/wireplumber |
			| StateDirectory      | machincast                                                             |
			| ExecStart           | /usr/bin/wireplumber                                                   |
			| Restart             | on-failure                                                             |
			| RestartSec          | 2                                                                      |
			| SyslogIdentifier    | machincast-wireplumber                                                 |
		Et l'unité a, dans la section « Install » :
			| clé      | valeur                      |
			| WantedBy | machincast-pipewire.service |

	Scénario: L'unité suit le répertoire de MachinCast, et la règle son compte, quels qu'ils soient
		Quand l'unité est rédigée dans « /home/radio/machincast », et la règle pour le compte « radio », du groupe « antenne », d'uid 1001
		Alors l'unité a, dans la section « Service », entre autres :
			| clé              | valeur                                   |
			| User             | machincast                               |
			| WorkingDirectory | /home/radio/machincast                   |
			| ExecStart        | /home/radio/machincast/bin/Machin player |
		Et la règle ne concerne que le compte « radio »

	Scénario: systemd accepte les unités du service, ensemble
		Étant donné l'outil « systemd-analyze » du poste
		Et l'outil « pipewire » du poste
		Et l'outil « wireplumber » du poste
		Quand je lance « python -m machincast.installation unit » avec la configuration de test
		Et j'enregistre sa sortie en « machincast.service »
		Et je lance « python -m machincast.installation pipewire-unit » avec la configuration de test
		Et j'enregistre sa sortie en « machincast-pipewire.service »
		Et je lance « python -m machincast.installation wireplumber-unit » avec la configuration de test
		Et j'enregistre sa sortie en « machincast-wireplumber.service »
		Alors « systemd-analyze verify » accepte ensemble « machincast.service », « machincast-pipewire.service » et « machincast-wireplumber.service »

	Scénario: Le serveur intranet démarre avec le poste, et s'arrête aussitôt tant qu'il est éteint
		https://github.com/dascritch/machincast/issues/538 : Machin intranet éteint s'arrête, code 4, sans que systemd le
		relance.

		Quand je lance « python -m machincast.installation intranet-unit » avec la configuration de test
		Alors la commande se termine sans erreur
		Et l'unité de la commande a, dans la section « Service », entre autres :
			| clé                      | valeur              |
			| Type                     | exec                |
			| StateDirectory           | machincast-intranet |
			| StateDirectoryMode       | 0700                |
			| SuccessExitStatus        | 4                   |
			| RestartPreventExitStatus | 4                   |
			| Restart                  | on-failure          |
			| NoNewPrivileges          | yes                 |
		Et l'unité a, dans la section « Install » :
			| clé      | valeur            |
			| WantedBy | multi-user.target |
		Et install.sh installe l'unité du serveur intranet, l'active, et la retire avec le service

	Scénario: Le serveur intranet tourne sous son propre compte, et ne peut écrire que dans son répertoire d'état
		https://github.com/dascritch/machincast/issues/549 : exposé au réseau, il n'est ni le compte de MachinCast,
		propriétaire de la base et du dépôt, ni dans le groupe du service de diffusion, qui donne son PipeWire, ses logs
		et les sonores de /home/machincast. Son rôle PostgreSQL n'endosse que machincast_intranet.

		Quand je lance « python -m machincast.installation intranet-unit » avec la configuration de test
		Alors la commande se termine sans erreur
		Et l'unité de la commande a, dans la section « Service », entre autres :
			| clé                     | valeur                                   |
			| User                    | machincast-intranet                      |
			| Group                   | machincast-intranet                      |
			| ProtectSystem           | strict                                   |
			| ProtectHome             | yes                                      |
			| PrivateTmp              | yes                                      |
			| PrivateDevices          | yes                                      |
			| CapabilityBoundingSet   |                                          |
			| RestrictAddressFamilies | AF_UNIX AF_INET AF_INET6 AF_NETLINK      |
			| MemoryDenyWriteExecute  | yes                                      |
			| UMask                   | 0077                                     |
		Et install.sh crée le compte « machincast-intranet », hors du groupe du service, et son rôle qui n'endosse que « machincast_intranet », et les retire avec le service

	Scénario: Le filtre des appels système du serveur intranet laisse ip lâcher ses capacités
		https://github.com/dascritch/machincast/issues/556 : « ~@privileged » interdit capset, que ip appelle au
		démarrage pour lâcher ses capacités (drop_cap), même sans en avoir ; tué par SIGSYS, ip laissait un core dump à
		chaque lecture des adresses du poste, devinées à la place. capset ne peut que retirer des capacités : l'unité
		n'en donne aucune (CapabilityBoundingSet vide).
		Quand je lance « python -m machincast.installation intranet-unit » avec la configuration de test
		Alors la commande se termine sans erreur
		Et les filtres des appels système de l'unité sont, dans l'ordre, « @system-service », « ~@privileged @resources », « capset »

	Scénario: systemd accepte l'unité du serveur intranet
		Étant donné l'outil « systemd-analyze » du poste
		Quand je lance « python -m machincast.installation intranet-unit » avec la configuration de test
		Et j'enregistre sa sortie en « machincast-intranet.service »
		Alors « systemd-analyze verify » accepte « machincast-intranet.service »

	Scénario: Les répertoires du service sont recréés à chaque démarrage du poste, au groupe du service
		Quand je lance « python -m machincast.installation tmpfiles » avec la configuration de test
		Alors la commande se termine sans erreur
		Et sa sortie a, hors commentaires, les lignes :
			| ligne                                                      |
			| d /run/machincast 2770 machincast machincast -             |
			| d /var/log/machincast 2770 machincast machincast -         |
			| d /var/log/machincast/crash-dump 2770 machincast machincast - |
			| d /run/machincast-intranet 2750 machincast machincast-intranet - |

	Scénario: Les logs tournent chaque semaine, sans couper les programmes qui y écrivent
		Quand je lance « python -m machincast.installation logrotate » avec la configuration de test
		Alors la commande se termine sans erreur
		Et sa sortie a, hors commentaires, les lignes :
			| ligne                        |
			| /var/log/machincast/*.log {  |
			| su machincast machincast     |
			| weekly                       |
			| rotate 8                     |
			| compress                     |
			| delaycompress                |
			| missingok                    |
			| notifempty                   |
			| copytruncate                 |
			| }                            |

	Plan du scénario: La carte de l'antenne est cachée aux sessions du poste, elle est au PipeWire du service
		Deux PipeWire n'ouvrent pas la même carte en même temps : le WirePlumber des sessions du poste désactive le nœud
		de l'antenne ; celui du service ne lit pas sa configuration.

		Quand je lance « python -m machincast.installation wireplumber-desktop » avec une configuration sur la sortie « <sortie> », l'antenne <antenne>
		Alors la commande se termine sans erreur
		Et le fragment WirePlumber désactive <nœuds>

		Exemples:
			| sortie   | antenne                                  | nœuds                                                |
			| pipewire | « alsa_output.pci-0000_00_1f.3.analog-stereo » | le nœud « alsa_output.pci-0000_00_1f.3.analog-stereo » |
			| pipewire | « dummy »                                | aucun nœud                                           |
			| pipewire | non renseignée                           | aucun nœud                                           |
			| alsa     | « hw:1,0 »                               | aucun nœud                                           |

	Scénario: Le WirePlumber du service ne cherche que les cartes son
		Quand je lance « python -m machincast.installation wireplumber-service » avec la configuration de test
		Alors la commande se termine sans erreur
		Et sa sortie annonce « monitor.bluez = disabled »
		Et sa sortie annonce « monitor.v4l2 = disabled »
		Et sa sortie annonce « monitor.libcamera = disabled »

	Plan du scénario: La règle polkit n'autorise que démarrer, arrêter et redémarrer le service et le serveur intranet, par un administrateur, au compte de MachinCast
		https://github.com/dascritch/machincast/issues/558 : un compte administrateur donne son propre mot de passe, sans
		choisir parmi les administrateurs du poste ; un autre, celui d'un administrateur.
		Quand je lance « python -m machincast.installation rule » avec la configuration de test
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
			| org.freedesktop.systemd1.manage-units  | machincast-intranet.service | start   | le compte | « auth_admin » |
			| org.freedesktop.systemd1.manage-units  | machincast-intranet.service | stop    | le compte | « auth_admin » |
			| org.freedesktop.systemd1.manage-units  | machincast-intranet.service | restart | le compte | « auth_admin » |
			| org.freedesktop.systemd1.manage-units  | machincast-intranet.service | enable  | le compte | rien           |
			| org.freedesktop.systemd1.manage-units  | machincast.service | restart | le compte, administrateur | « auth_self_keep » |
			| org.freedesktop.systemd1.manage-units  | machincast-intranet.service | restart | le compte, administrateur | « auth_self_keep » |
			| org.freedesktop.systemd1.manage-units  | machincast-intranet.service | enable  | le compte, administrateur | rien |
			| org.freedesktop.systemd1.manage-units  | machincast.service | stop    | un autre compte, administrateur | rien |

	Plan du scénario: La règle polkit demande le mot de passe d'un administrateur pour éteindre, redémarrer ou mettre en veille le poste, à tout compte, écran de connexion compris
		Un administrateur donne le sien (https://github.com/dascritch/machincast/issues/558).
		https://github.com/dascritch/machincast/issues/448 : sur un poste d'antenne, une extinction, un redémarrage ou une
		mise en veille par mégarde coupe l'antenne. Ubuntu les permet sans mot de passe à toute session active, écran de
		connexion compris (allow_active de org.freedesktop.login1.policy) ; la règle du service les soumet à
		l'authentification d'un administrateur, pour tout compte. Le retrait du service retire la règle, et rend la
		politique d'Ubuntu.
		Quand je lance « python -m machincast.installation rule » avec la configuration de test
		Alors la règle polkit répond <reponse> à l'action « <action> », pour <qui>

		Exemples:
			| action                                            | qui             | reponse        |
			| org.freedesktop.login1.power-off                  | le compte       | « auth_admin » |
			| org.freedesktop.login1.power-off                  | le compte, administrateur | « auth_self_keep » |
			| org.freedesktop.login1.reboot                     | un autre compte, administrateur | « auth_self_keep » |
			| org.freedesktop.login1.power-off                  | un autre compte | « auth_admin » |
			| org.freedesktop.login1.power-off-multiple-sessions | un autre compte | « auth_admin » |
			| org.freedesktop.login1.power-off-ignore-inhibit   | un autre compte | « auth_admin » |
			| org.freedesktop.login1.reboot                     | le compte       | « auth_admin » |
			| org.freedesktop.login1.reboot                     | un autre compte | « auth_admin » |
			| org.freedesktop.login1.reboot-multiple-sessions   | un autre compte | « auth_admin » |
			| org.freedesktop.login1.reboot-ignore-inhibit      | un autre compte | « auth_admin » |
			| org.freedesktop.login1.halt                       | un autre compte | « auth_admin » |
			| org.freedesktop.login1.halt-multiple-sessions     | un autre compte | « auth_admin » |
			| org.freedesktop.login1.halt-ignore-inhibit        | un autre compte | « auth_admin » |
			| org.freedesktop.login1.suspend                    | le compte       | « auth_admin » |
			| org.freedesktop.login1.suspend-multiple-sessions  | un autre compte | « auth_admin » |
			| org.freedesktop.login1.suspend-ignore-inhibit     | un autre compte | « auth_admin » |
			| org.freedesktop.login1.hibernate                  | un autre compte | « auth_admin » |
			| org.freedesktop.login1.hibernate-multiple-sessions | un autre compte | « auth_admin » |
			| org.freedesktop.login1.hibernate-ignore-inhibit   | un autre compte | « auth_admin » |
			| org.freedesktop.login1.inhibit-block-sleep        | le compte       | rien           |
			| org.freedesktop.login1.set-reboot-to-firmware-setup | le compte     | rien           |

	Scénario: Le service neutralise les touches d'alimentation, de redémarrage et de veille, et le capot
		https://github.com/dascritch/machincast/issues/448 : logind éteint, redémarre ou met en veille sans passer par
		polkit à l'appui d'une touche ou à la fermeture du capot. Le fragment de logind du service les ignore ; dans une
		session, le bureau garde la main sur la touche, et passe par logind, donc par la règle polkit. Un appui long sur
		le bouton d'alimentation, que le matériel traite seul, éteint toujours.
		Quand je lance « python -m machincast.installation logind » avec la configuration de test
		Alors la commande se termine sans erreur
		Et sa sortie annonce « [Login] »
		Et sa sortie règle à « ignore » « HandlePowerKey », « HandlePowerKeyLongPress », « HandleRebootKey », « HandleRebootKeyLongPress », « HandleSuspendKey », « HandleSuspendKeyLongPress », « HandleHibernateKey », « HandleHibernateKeyLongPress », « HandleLidSwitch », « HandleLidSwitchExternalPower », « HandleLidSwitchDocked »

	Scénario: Le service neutralise la rafale de Ctrl+Alt+Suppr en console
		https://github.com/dascritch/machincast/issues/448 : en console, Ctrl+Alt+Suppr redémarre (ctrl-alt-del.target,
		qu'install.sh --service masque), et sept appuis en deux secondes forcent le redémarrage, même masqué
		(CtrlAltDelBurstAction) : le fragment de systemd du service l'annule.
		Quand je lance « python -m machincast.installation system-conf » avec la configuration de test
		Alors la commande se termine sans erreur
		Et sa sortie annonce « [Manager] »
		Et sa sortie règle à « none » « CtrlAltDelBurstAction »

	Scénario: install.sh --service masque Ctrl+Alt+Suppr et recharge logind ; --remove-service rend les deux
		https://github.com/dascritch/machincast/issues/448 : logind relit son fragment sans fermer les sessions
		(systemctl reload) ; systemd relit le sien en se réexécutant (daemon-reexec), seulement quand il change. Le
		retrait démasque ctrl-alt-del.target s'il est masqué, et retire les fragments : la politique d'Ubuntu revient.
		Alors install.sh, en installant le service, recharge « systemd-logind » quand « FICHIER_LOGIND » change, et réexécute systemd quand « FICHIER_SYSTEME » change
		Et install.sh, en installant le service, masque « ctrl-alt-del.target » s'il ne l'est pas
		Et install.sh, en retirant le service, démasque « ctrl-alt-del.target » s'il est masqué, recharge « systemd-logind » et réexécute systemd

	Scénario: L'unité porte le nom que le wrapper suit dans le journal
		Alors l'unité de machincast.installation est celle de « Machin logs »

	Scénario: install.sh installe, tient à jour et retire tout ce que rédige machincast.installation pour le service
		Alors install.sh a les noms du service de machincast.installation
		Et install.sh installe, vérifie et retire chacun de ces fichiers :
			| action              | fichier                     |
			| unit                | FICHIER_UNITE               |
			| pipewire-unit       | FICHIER_UNITE_PIPEWIRE      |
			| wireplumber-unit    | FICHIER_UNITE_WIREPLUMBER   |
			| wireplumber-service | FICHIER_WIREPLUMBER_SERVICE |
			| wireplumber-desktop | FICHIER_WIREPLUMBER_BUREAU  |
			| tmpfiles            | FICHIER_TMPFILES            |
			| logrotate           | FICHIER_LOGROTATE           |
			| profile             | FICHIER_PROFIL              |
			| tasks-unit          | FICHIER_UNITE_TACHES        |
			| tasks-timer         | FICHIER_MINUTEUR_TACHES     |
			| indexing-unit       | FICHIER_UNITE_INDEXATION    |
			| indexing-timer      | FICHIER_MINUTEUR_INDEXATION |
			| rule                | FICHIER_REGLE               |
			| logind              | FICHIER_LOGIND              |
			| system-conf         | FICHIER_SYSTEME             |
			| power-save          | FICHIER_MODPROBE            |
			| usb-power           | FICHIER_USB                 |

	Scénario: install.sh --service demande d'abord de dédier le poste à l'antenne, puis de sortir MachinCast d'un répertoire personnel
		Alors install.sh, avec --service, demande de dédier le poste puis déplace MachinCast, avant toute autre étape

	Scénario: install.sh ne change jamais les droits d'un répertoire personnel
		Alors install.sh ne lance jamais setfacl, ni chmod, ni chown

	Plan du scénario: install.sh reconnaît un répertoire personnel
		Alors pour install.sh, « <chemin> » <verdict> dans un répertoire personnel

		Exemples:
			| chemin                       | verdict      |
			| /home/radio/machincast       | est          |
			| /root/machincast             | est          |
			| ~/machincast                 | est          |
			| /home/machincast/jingles     | n'est pas    |
			| /usr/local/machincast        | n'est pas    |
			| /srv/sons                    | n'est pas    |

	Scénario: Le répertoire d'accueil des sonores est au compte de MachinCast et au groupe du service
		Alors install.sh crée « /home/machincast » au compte de MachinCast, au groupe « machincast », en mode 2750

	# ─── Tâches du service (https://github.com/dascritch/machincast/issues/268, https://github.com/dascritch/machincast/issues/455) ─────
	# install.sh --service installe deux minuteurs, sous le compte de MachinCast : l'indexation rapide toutes les heures,
	# et, tous les quarts d'heure, les tâches régulières, Machin tasks, qui lance ce qui est dû : la tâche quotidienne,
	# Machin purge puis l'audit complet, à l'heure réglée (schedule.daily, 10:00 par défaut). Ce que fait chaque passage
	# est dans le wrapper (tests/wrapper/taches.bats) : l'unité ne change pas avec les tâches. --no-timers n'installe
	# pas les minuteurs, et retire ceux d'avant ; --remove-service les retire avec le service. Ils remplacent le
	# minuteur de la purge à midi, retiré à la mise à jour.

	Scénario: L'unité des tâches régulières lance Machin tasks, sous le compte de MachinCast
		Quand je lance « python -m machincast.installation tasks-unit » avec la configuration de test
		Alors la commande se termine sans erreur
		Et l'unité a, dans la section « Unit » :
			| clé         | valeur                                  |
			| Description | MachinCast: regular tasks (Machin tasks) |
			| After       | postgresql.service                      |
		Et l'unité a, dans la section « Service » :
			| clé              | valeur                        |
			| Type             | oneshot                       |
			| User             | <compte>                      |
			| Group            | <groupe>                      |
			| WorkingDirectory | <répertoire>                  |
			| StateDirectory   | machincast-tasks              |
			| ExecStart        | <répertoire>/bin/Machin tasks |
			| SyslogIdentifier | machincast-tasks              |
		Et l'unité n'a pas de section « Install »

	Scénario: Le minuteur des tâches régulières les lance tous les quarts d'heure
		Quand je lance « python -m machincast.installation tasks-timer » avec la configuration de test
		Alors la commande se termine sans erreur
		Et l'unité a, dans la section « Unit » :
			| clé         | valeur                                              |
			| Description | MachinCast: regular tasks, every quarter of an hour |
		Et l'unité a, dans la section « Timer » :
			| clé        | valeur                   |
			| OnCalendar | *:0/15                   |
			| Unit       | machincast-tasks.service |
		Et l'unité a, dans la section « Install » :
			| clé      | valeur        |
			| WantedBy | timers.target |

	Scénario: L'unité de l'indexation rapide lance Machin indexer, sous le compte de MachinCast
		Quand je lance « python -m machincast.installation indexing-unit » avec la configuration de test
		Alors la commande se termine sans erreur
		Et l'unité a, dans la section « Unit » :
			| clé         | valeur                                          |
			| Description | MachinCast: quick indexing (Machin indexer)     |
			| After       | postgresql.service                              |
		Et l'unité a, dans la section « Service » :
			| clé               | valeur                          |
			| Type              | oneshot                         |
			| User              | <compte>                        |
			| Group             | <groupe>                        |
			| WorkingDirectory  | <répertoire>                    |
			| ExecStart         | <répertoire>/bin/Machin indexer |
			| SuccessExitStatus | 3                               |
			| SyslogIdentifier  | machincast-indexing             |
		Et l'unité n'a pas de section « Install »

	Scénario: Le minuteur de l'indexation rapide la lance toutes les heures, et la rattrape si le poste était éteint
		Quand je lance « python -m machincast.installation indexing-timer » avec la configuration de test
		Alors la commande se termine sans erreur
		Et l'unité a, dans la section « Unit » :
			| clé         | valeur                                    |
			| Description | MachinCast: quick indexing, every hour    |
		Et l'unité a, dans la section « Timer » :
			| clé        | valeur                      |
			| OnCalendar | hourly                      |
			| Persistent | true                        |
			| Unit       | machincast-indexing.service |
		Et l'unité a, dans la section « Install » :
			| clé      | valeur        |
			| WantedBy | timers.target |

	Scénario: Les unités des tâches suivent le compte de MachinCast, quel qu'il soit
		Quand les unités des tâches sont rédigées pour le compte « radio », du groupe « antenne », dans « /home/radio/machincast »
		Alors l'unité des tâches régulières a, dans la section « Service », entre autres :
			| clé              | valeur                                  |
			| User             | radio                                   |
			| Group            | antenne                                 |
			| WorkingDirectory | /home/radio/machincast                  |
			| ExecStart        | /home/radio/machincast/bin/Machin tasks |
		Et l'unité de l'indexation rapide a, dans la section « Service », entre autres :
			| clé              | valeur                                  |
			| User             | radio                                   |
			| ExecStart        | /home/radio/machincast/bin/Machin indexer |

	Scénario: systemd accepte les unités et les minuteurs des tâches
		Étant donné l'outil « systemd-analyze » du poste
		Quand je lance « python -m machincast.installation tasks-unit » avec la configuration de test
		Et j'enregistre sa sortie en « machincast-tasks.service »
		Et je lance « python -m machincast.installation tasks-timer » avec la configuration de test
		Et j'enregistre sa sortie en « machincast-tasks.timer »
		Et je lance « python -m machincast.installation indexing-unit » avec la configuration de test
		Et j'enregistre sa sortie en « machincast-indexing.service »
		Et je lance « python -m machincast.installation indexing-timer » avec la configuration de test
		Et j'enregistre sa sortie en « machincast-indexing.timer »
		Alors « systemd-analyze verify » accepte ensemble « machincast-tasks.service », « machincast-tasks.timer », « machincast-indexing.service » et « machincast-indexing.timer »

	Scénario: install.sh installe les minuteurs des tâches, sauf avec --no-timers, qui retire ceux d'avant
		https://github.com/dascritch/machincast/issues/455 : un poste dont l'installation est pilotée par un outil de
		déploiement, comme Ansible, garde ses propres tâches. Sans --service, une mise à jour ne vérifie les minuteurs que
		s'ils sont installés : le choix de --no-timers tient.
		Alors install.sh a les noms des tâches du service de machincast.service
		Et install.sh, avec --no-timers, n'installe aucun minuteur et retire ceux d'avant
		Et install.sh ne vérifie les minuteurs d'un service installé que s'ils le sont
		Et install.sh retire l'ancien minuteur de la purge à midi, à l'installation comme au retrait du service

	# ─── Raccourci et icône de l'interface (https://github.com/dascritch/machincast/issues/62) ─────
	# install.sh installe le raccourci que rédige machincast.installation dans le menu des applications du compte, et,
	# sur demande, sur son bureau. Lancé depuis une icône, le programme démarre dans le répertoire de MachinCast.

	Scénario: Le raccourci lance Machin interface depuis le répertoire de MachinCast, avec son icône
		Quand je lance « python -m machincast.installation shortcut » avec la configuration de test
		Alors la commande se termine sans erreur
		Et le raccourci a, dans la section « Desktop Entry » :
			| clé            | valeur                                                 |
			| Type           | Application                                            |
			| Version        | 1.5                                                    |
			| Name           | MachinCast                                             |
			| GenericName    | Automated radio broadcasting                           |
			| GenericName[fr] | Diffusion radio automatisée                           |
			| Comment        | Program the on-air output and follow the broadcast     |
			| Comment[fr]    | Programmer l'antenne et suivre la diffusion            |
			| Exec           | <répertoire>/bin/Machin interface                      |
			| Path           | <répertoire>                                           |
			| Icon           | <répertoire>/src/machincast/interface/machincast.png   |
			| Terminal       | false                                                  |
			| Categories     | AudioVideo;Audio;                                      |
			| Keywords       | radio;on air;broadcast;programming;                    |
			| Keywords[fr]   | radio;antenne;diffusion;programmation;                 |
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
		Quand je lance « python -m machincast.installation shortcut » avec la configuration de test
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
		Quand je lance « python -m machincast.installation shortcut » avec une configuration dont l'icône est cette image
		Alors la commande se termine sans erreur
		Et le raccourci a l'icône de cette image

	Scénario: Une icône choisie introuvable laisse au raccourci l'icône de MachinCast
		Quand le raccourci est rédigé pour le répertoire « /home/radio/machincast », avec l'icône « /home/radio/disparu.png »
		Alors le raccourci a, dans la section « Desktop Entry », entre autres :
			| clé  | valeur                                                     |
			| Icon | /home/radio/machincast/src/machincast/interface/machincast.png |

	# ─── Désinstallation (https://github.com/dascritch/machincast/issues/430) ─────
	# Un répertoire qui contient des sonores n'est jamais retiré, ni le répertoire d'accueil des sonores, même vide.

	Plan du scénario: install.sh ne retire un répertoire qu'il a créé que s'il ne contient aucun sonore
		Étant donné un répertoire créé par MachinCast, qui contient <contenu>
		Quand install.sh retire ce répertoire
		Alors le répertoire <verdict>

		Exemples:
			| contenu                                  | verdict                                              |
			| « wireplumber/etat »                     | est retiré                                           |
			| « sons/jingle.flac »                     | reste, et install.sh dit qu'il contient des sonores  |
			| « a/b/c/VIEUX.MP3 »                      | reste, et install.sh dit qu'il contient des sonores  |
			| « reportage.Wav »                        | reste, et install.sh dit qu'il contient des sonores  |

	Scénario: install.sh ne retire jamais le répertoire d'accueil des sonores, même vide
		Étant donné le répertoire d'accueil des sonores, vide
		Quand install.sh retire ce répertoire
		Alors le répertoire reste, et install.sh dit que c'est celui des sonores

	Scénario: install.sh ne retire un répertoire que par retirer_repertoires
		Alors install.sh ne lance « rm --recursive » que dans retirer_repertoires
		Et les extensions des sonores d'install.sh sont celles de machincast.protection

	# ─── Réimportation d'une sauvegarde à la création de la base (https://github.com/dascritch/machincast/issues/347) ───
	# Quand install.sh vient de créer la base de production, il propose de réimporter une sauvegarde d'une installation
	# précédente, sur ce poste ou sur un autre, faite par Machin backup-db ou Machin maintenance-db : par kdialog sur un
	# poste graphique, dans le terminal sinon, comme par ssh. Il la réimporte par Machin restore-db, qui la vérifie,
	# avant d'appliquer le schéma. Une réimportation refusée repose la question. --restore FICHIER la réimporte sans
	# rien demander ; --no-restore ne la propose pas. Les scénarios lancent sa fonction, Machin restore-db et kdialog
	# remplacés par des scripts.

	Scénario: install.sh ne propose la réimportation que pour la base de production qu'il vient de créer, avant le schéma
		Alors install.sh propose de réimporter une sauvegarde après avoir créé la base de production, avant d'appliquer le schéma

	Plan du scénario: Sur un poste graphique, kdialog demande s'il faut réimporter une sauvegarde, puis laquelle
		Étant donné un poste graphique avec kdialog
		Et kdialog répond <réponse>, puis choisit « /media/cle/machincast-2026-11-01T10-00-00.dump »
		Quand install.sh propose de réimporter une sauvegarde
		Alors install.sh <résultat>

		Exemples:
			| réponse                           | résultat                                                                                    |
			| « Oui, importer une sauvegarde »  | a réimporté « /media/cle/machincast-2026-11-01T10-00-00.dump » par Machin restore-db        |
			| « Non, on repart de zéro »        | n'a rien réimporté, et dit « nouvelle base : on repart de zéro »                            |

	Scénario: kdialog pose la question du ticket, et cherche une sauvegarde de MachinCast dans le répertoire personnel
		Étant donné un poste graphique avec kdialog
		Et kdialog répond « Non, on repart de zéro », puis choisit « /media/cle/machincast-2026-11-01T10-00-00.dump »
		Quand install.sh propose de réimporter une sauvegarde
		Alors kdialog a demandé « Vous semblez faire une installation neuve de MachinCast. L'aviez-vous déjà fait tourner sur ce poste ou sur un autre ? Faut-il récupérer sa base de données ? »

	Scénario: Sans affichage graphique, comme par ssh, les questions se posent dans le terminal
		Étant donné un poste sans affichage graphique, dans un terminal
		Quand install.sh propose de réimporter une sauvegarde, et que je réponds « o » puis « ~/sauvegardes/machincast.dump »
		Alors install.sh a réimporté « <personnel>/sauvegardes/machincast.dump » par Machin restore-db

	Scénario: Une réimportation refusée repose la question
		Étant donné un poste sans affichage graphique, dans un terminal
		Et Machin restore-db qui refuse la sauvegarde
		Quand install.sh propose de réimporter une sauvegarde, et que je réponds « o » puis « /tmp/ancienne.dump » puis « n »
		Alors install.sh a tenté de réimporter « /tmp/ancienne.dump », a reposé la question, et dit « nouvelle base : on repart de zéro »

	Scénario: Sans affichage graphique ni terminal, rien n'est réimporté, et install.sh dit comment le faire
		Étant donné un poste sans affichage graphique ni terminal
		Quand install.sh propose de réimporter une sauvegarde
		Alors install.sh n'a rien réimporté, et dit « nouvelle base, sans sauvegarde réimportée : ./install.sh --restore FICHIER en réimporte une »

	Plan du scénario: --restore FICHIER réimporte sans rien demander, --no-restore ne propose rien
		Étant donné un poste graphique avec kdialog
		Et install.sh lancé avec « <options> »
		Quand install.sh propose de réimporter une sauvegarde
		Alors install.sh <résultat>
		Et kdialog n'a rien demandé

		Exemples:
			| options                       | résultat                                                       |
			| --restore /srv/base.dump      | a réimporté « /srv/base.dump » par Machin restore-db           |
			| --no-restore                  | n'a rien réimporté                                             |

	Scénario: Avec --restore, une sauvegarde refusée arrête install.sh, avant le schéma
		Étant donné un poste graphique avec kdialog
		Et install.sh lancé avec « --restore /srv/base.dump »
		Et Machin restore-db qui refuse la sauvegarde
		Quand install.sh propose de réimporter une sauvegarde
		Alors install.sh s'arrête avec le message « sauvegarde /srv/base.dump non réimportée : corriger, puis Machin restore-db FICHIER avant de relancer ./install.sh »

	# https://github.com/dascritch/machincast/issues/517 : un installateur plus simple et moins rebutant pour un technicien
	# radio qui travaille dans un environnement graphique. La bannière est celle de « Machin banner » (wrapper.bats), lancée
	# au début d'install.sh, et à chaque nouveau shell interactif quand le service est installé. Sans --verbose ni
	# --simulation, les lignes d'information techniques sont cachées ; les avertissements sont en jaune, les échecs en jaune
	# vif sur fond rouge sombre, les questions en blanc et en gras, ou dans une fenêtre kdialog sur un poste graphique local.

	Scénario: Le script de session de chaque nouveau shell lance la bannière, dans un shell interactif seulement
		Quand je lance « python -m machincast.installation profile » avec la configuration de test
		Alors la commande se termine sans erreur
		Et sa sortie a, hors commentaires, les lignes :
			| ligne                                                           |
			| case "$-" in                                                    |
			| *i*)                                                            |
			| if [ -t 1 ] && command -v Machin >/dev/null 2>&1; then         |
			| Machin banner                                                   |
			| fi                                                              |
			| ;;                                                              |
			| esac                                                            |

	Scénario: Le script de session ne montre rien hors d'un shell interactif, ni quand la sortie n'est pas un terminal
		Quand un shell non interactif lit le script de session
		Alors le script de session n'a rien montré

	Scénario: Le script de session montre la bannière dans un shell interactif sur un terminal
		Quand un shell interactif sur un terminal lit le script de session
		Alors le script de session a lancé « Machin banner »

	Plan du scénario: install.sh cache ses lignes techniques sans --verbose ni --simulation
		Étant donné install.sh avec VERBEUX=<verbeux> et SIMULATION=<simulation>
		Quand install.sh écrit une information technique, une annonce et un avertissement
		Alors install.sh montre <montré>

		Exemples:
			| verbeux | simulation | montré                                              |
			| false   | false      | l'annonce et l'avertissement, sans l'information    |
			| true    | false      | l'information, l'annonce et l'avertissement         |
			| false   | true       | l'information, l'annonce et l'avertissement         |

	Scénario: Un avertissement a son texte en jaune, sur un terminal
		Étant donné install.sh avec les couleurs forcées
		Quand install.sh écrit une information technique, une annonce et un avertissement
		Alors la ligne d'avertissement d'install.sh est entourée du code de couleur « 33 »
		Et la ligne d'annonce d'install.sh n'a aucune couleur

	Scénario: Un échec est en jaune vif sur un fond rouge sombre, sur la sortie d'erreur
		Étant donné install.sh avec les couleurs forcées
		Quand install.sh échoue avec « disque plein »
		Alors la ligne d'échec d'install.sh est entourée du code de couleur « 1;93;48;5;88 »

	Plan du scénario: Sans terminal, ou avec NO_COLOR, install.sh n'ajoute aucune couleur
		Étant donné install.sh <situation>
		Quand install.sh écrit une information technique, une annonce et un avertissement
		Et install.sh échoue avec « disque plein »
		Alors install.sh n'a écrit aucune couleur

		Exemples:
			| situation                                    |
			| sans terminal                                |
			| avec NO_COLOR et les couleurs forcées        |

	Scénario: Dans le terminal, la question est en blanc et en gras
		Étant donné un poste sans affichage graphique, dans un terminal
		Et install.sh avec les couleurs forcées
		Quand install.sh pose la question « Arrêter ? [y/N] », et que je réponds « o »
		Alors la question d'install.sh est en blanc et en gras, et sa réponse est oui

	Scénario: Sur un poste graphique local, toute question d'install.sh s'ouvre dans une fenêtre kdialog
		Étant donné un poste graphique avec kdialog
		Quand install.sh pose la question « Arrêter ? [y/N] »
		Alors kdialog a demandé « Arrêter ? » sans ses crochets

	Scénario: Par ssh, même avec un affichage, la question se pose dans le terminal
		Étant donné un poste graphique avec kdialog
		Et une connexion ssh
		Quand install.sh pose la question « Arrêter ? [y/N] », et que je réponds « o »
		Alors kdialog n'a rien demandé

	Scénario: install.sh montre la bannière avant toute étape, et a une option --verbose
		Alors install.sh lance « Machin banner » avant toute étape, et reconnaît --verbose
