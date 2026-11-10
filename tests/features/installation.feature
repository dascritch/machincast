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
			| pipewire   | « dummy »      | 1    | d'erreur mentionne | antenne sur la sortie factice : le service de diffusion ne jouerait aucun son ; choisir une autre carte son dans Machin interface, Fichier → Préférences…, page Audio, puis relancer ./install.sh --service |
			| dummy      | « carte-1 »    | 1    | d'erreur mentionne | antenne sur la sortie factice : le service de diffusion ne jouerait aucun son ; choisir une autre carte son dans Machin interface, Fichier → Préférences…, page Audio, puis relancer ./install.sh --service |
			| pulseaudio | « carte-1 »    | 1    | d'erreur mentionne | antenne sur la sortie PulseAudio : le service de diffusion joue par son propre PipeWire ; choisir la sortie PipeWire dans Machin interface, Fichier → Préférences…, page Audio, puis relancer ./install.sh --service |

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

	Scénario: Les répertoires du service sont recréés à chaque démarrage du poste, au groupe du service
		Quand je lance « python -m machincast.installation tmpfiles » avec la configuration de test
		Alors la commande se termine sans erreur
		Et sa sortie a, hors commentaires, les lignes :
			| ligne                                                      |
			| d /run/machincast 2770 machincast machincast -             |
			| d /var/log/machincast 2770 machincast machincast -         |
			| d /var/log/machincast/crash-dump 2770 machincast machincast - |

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

	Plan du scénario: La règle polkit n'autorise que démarrer, arrêter et redémarrer le service, par un administrateur, au compte de MachinCast
		Étant donné l'outil « node » du poste
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
			| purge-unit          | FICHIER_UNITE_PURGE         |
			| purge-timer         | FICHIER_MINUTEUR_PURGE      |
			| rule                | FICHIER_REGLE               |

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

	# ─── Purge quotidienne (https://github.com/dascritch/machincast/issues/268) ─────
	# install.sh --service installe aussi le minuteur de la purge : chaque jour à midi, Machin purge efface de la base
	# ce qui dépasse la durée de péremption, sous le compte de MachinCast. --remove-service le retire avec le service.

	Scénario: L'unité de la purge lance Machin purge une fois, sous le compte de MachinCast
		Quand je lance « python -m machincast.installation purge-unit » avec la configuration de test
		Alors la commande se termine sans erreur
		Et l'unité a, dans la section « Unit » :
			| clé         | valeur                                                          |
			| Description | MachinCast: database purge (Machin purge)                       |
			| After       | postgresql.service                                              |
		Et l'unité a, dans la section « Service » :
			| clé              | valeur                          |
			| Type             | oneshot                         |
			| User             | <compte>                        |
			| Group            | <groupe>                        |
			| WorkingDirectory | <répertoire>                    |
			| ExecStart        | <répertoire>/bin/Machin purge   |
			| SyslogIdentifier | machincast-purge                |
		Et l'unité n'a pas de section « Install »

	Scénario: Le minuteur de la purge la lance chaque jour à midi, et la rattrape si le poste était éteint
		Quand je lance « python -m machincast.installation purge-timer » avec la configuration de test
		Alors la commande se termine sans erreur
		Et l'unité a, dans la section « Unit » :
			| clé         | valeur                                                 |
			| Description | MachinCast: daily database purge, at noon              |
		Et l'unité a, dans la section « Timer » :
			| clé        | valeur                   |
			| OnCalendar | *-*-* 12:00:00           |
			| Persistent | true                     |
			| Unit       | machincast-purge.service |
		Et l'unité a, dans la section « Install » :
			| clé      | valeur        |
			| WantedBy | timers.target |

	Scénario: L'unité de la purge suit le compte de MachinCast, quel qu'il soit
		Quand l'unité de la purge est rédigée pour le compte « radio », du groupe « antenne », dans « /home/radio/machincast »
		Alors l'unité de la purge a, dans la section « Service », entre autres :
			| clé              | valeur                                  |
			| User             | radio                                   |
			| Group            | antenne                                 |
			| WorkingDirectory | /home/radio/machincast                  |
			| ExecStart        | /home/radio/machincast/bin/Machin purge |

	Scénario: systemd accepte l'unité et le minuteur de la purge
		Étant donné l'outil « systemd-analyze » du poste
		Quand je lance « python -m machincast.installation purge-unit » avec la configuration de test
		Et j'enregistre sa sortie en « machincast-purge.service »
		Et je lance « python -m machincast.installation purge-timer » avec la configuration de test
		Et j'enregistre sa sortie en « machincast-purge.timer »
		Alors « systemd-analyze verify » accepte « machincast-purge.service »
		Et « systemd-analyze verify » accepte « machincast-purge.timer »

	Scénario: Les noms de l'unité et du minuteur de la purge sont ceux qu'installe install.sh
		Alors install.sh installe et retire l'unité et le minuteur de la purge de machincast.installation

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
