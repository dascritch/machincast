# language: fr
Fonctionnalité: Pilotage de la diffusion depuis l'interface
	En tant que technicien d'antenne,
	je veux démarrer et arrêter la diffusion depuis l'interface,
	afin de ne pas avoir besoin d'un terminal.

	https://github.com/dascritch/machincast/issues/25, spec § 8.11. Le menu « Diffusion » appelle systemctl sur le
	service machincast.service, que la règle polkit d'install.sh --service autorise avec l'authentification d'un
	administrateur (https://github.com/dascritch/machincast/issues/22) : jamais sudo. Sans service, l'interface dit que
	l'installation n'est pas définitive, et comment la terminer ; le menu pilote alors une diffusion d'essai : Machin
	lecture lancé dans une fenêtre de terminal, qu'arrêter arrête par SIGTERM, comme Ctrl-C. Son processus
	est celui qui répond sur la socket d'état. Redémarrer n'est plus proposé (https://github.com/dascritch/machincast/issues/223) :
	arrêter puis démarrer fait de même. Ce n'est pas « Machin player --simulation », qui ne joue rien. Les commandes systemctl et konsole du scénario sont des imitations, en tête du PATH :
	elles notent leurs arguments, et répondent ce que dit le scénario ; systemctl
	change l'état du service qu'il imite.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-20 16:40:00 »
		Et les événements :
			| name     | public_name | priority               | starts_at | ends_at | days |
			| Continue |             | background_programming |           |         |      |

	# ─── Avec le service ───────────────────────────────────────

	Plan du scénario: Le menu « Diffusion » ne montre que l'entrée que permet l'état du service
		Étant donné le service de diffusion installé, <etat>
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre de menus a les menus « Fichier », « Affichage », « Onglets », « Tableau », « Diffusion », « Maintenance », « Aide »
		Et le menu « Diffusion » a les entrées :
			| entrée                                | état       | raccourci | infobulle                                               |
			| Moniteur de l'antenne               | active     | Alt+P     | Écouter l'antenne sur la sortie de pré-écoute, aussitôt |
			| —                                     |            |           |                                                         |
			| <entree>                              | active     |           |                                                         |
			| —                                     |            |           |                                                         |
			| Recommencer                           | active   |           |                                                         |
			| Sauter                                | active   |           |                                                         |
			| Insérer après ce sonore               | active   |           |                                                         |
			| Couper                                | active   |           |                                                         |
		Et la barre d'état ne signale pas d'installation à terminer

		Exemples:
			| etat      | entree                |
			| arrêté    | Démarrer la diffusion |
			| en marche | Arrêter la diffusion  |
			| en échec  | Démarrer la diffusion |

	Plan du scénario: Chaque entrée appelle systemctl sur le service, sans sudo, et la barre d'état dit ce qu'il en est
		Étant donné le service de diffusion installé, <etat>
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « <entree> » dans le menu « Diffusion »
		Alors systemctl a reçu bientôt « <verbe> machincast.service »
		Et la barre d'état annonce bientôt « <annonce> »

		Exemples:
			| etat      | entree                  | verbe   | annonce               |
			| arrêté    | Démarrer la diffusion   | start   | Diffusion démarrée.   |
			| en marche | Arrêter la diffusion    | stop    | Diffusion arrêtée.    |

	Plan du scénario: Un service démarré dont Machin player s'arrête aussitôt : une alerte le dit, avec ce que veut dire son code et le journal du service
		https://github.com/dascritch/machincast/issues/376 : systemctl réussit dès que Machin player est lancé ; après une
		mise à jour, le service d'avant appelait « Machin lecture », que Machin refuse, avec le code 2.
		Étant donné le service de diffusion installé, arrêté
		Et Machin player qui s'arrête aussitôt lancé par le service, avec le code <code>, le service <état>
		Et le journal du service qui finit par « <ligne> »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion » dans le menu « Diffusion »
		Alors une alerte dit bientôt « Diffusion non démarrée : Machin player s'est arrêté, code de sortie <code>. <sens> Machin logs, dans un terminal, en dit plus. »
		Et elle montre en détails les lignes du journal « Started machincast.service » et « <ligne> »
		Et la barre d'état annonce bientôt « Diffusion non démarrée : Machin player s'est arrêté, code de sortie <code>. <sens> »

		Exemples:
			| code | état                | ligne                         | sens                                                                                                                  |
			| 2    | en échec            | Machin: unknown binary: lecture | Sa configuration ou son appel est invalide : après une mise à jour de MachinCast, relancer ./install.sh, qui met le service à jour. |
			| 1    | relancé par systemd | base de données injoignable   | La base de données est injoignable, la sortie audio indisponible, ou un autre Machin player diffuse déjà.             |

	Scénario: Un service démarré dont Machin player tient ne fait pas d'alerte
		Étant donné le service de diffusion installé, arrêté
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion » dans le menu « Diffusion »
		Alors la barre d'état annonce bientôt « Diffusion démarrée. »
		Et aucune alerte ne dit que la diffusion n'a pas démarré

	Scénario: Une authentification refusée laisse la diffusion telle quelle, et la barre d'état le dit
		Étant donné le service de diffusion installé, arrêté
		Et systemctl refuse en disant « Access denied »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion » dans le menu « Diffusion »
		Alors la barre d'état annonce bientôt « Diffusion non démarrée : Access denied »

	Scénario: Le menu suit l'état du service quand il s'ouvre
		Étant donné le service de diffusion installé, arrêté
		Quand la fenêtre de l'interface s'ouvre
		Et le service de diffusion passe en marche
		Et j'ouvre le menu « Diffusion »
		Alors le menu « Diffusion » a les entrées :
			| entrée                                | état     | raccourci | infobulle                                               |
			| Moniteur de l'antenne               | active   | Alt+P     | Écouter l'antenne sur la sortie de pré-écoute, aussitôt |
			| —                                     |          |           |                                                         |
			| Arrêter la diffusion | active |           |                                                         |
			| —                                     |          |           |                                                         |
			| Recommencer                           | active   |           |                                                         |
			| Sauter                                | active   |           |                                                         |
			| Insérer après ce sonore               | active   |           |                                                         |
			| Couper                                | active   |           |                                                         |

	Scénario: Après une commande, le menu suit le nouvel état du service
		Étant donné le service de diffusion installé, arrêté
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion » dans le menu « Diffusion »
		Alors la barre d'état annonce bientôt « Diffusion démarrée. »
		Et le menu « Diffusion » a les entrées :
			| entrée                                | état     | raccourci | infobulle                                               |
			| Moniteur de l'antenne               | active   | Alt+P     | Écouter l'antenne sur la sortie de pré-écoute, aussitôt |
			| —                                     |          |           |                                                         |
			| Arrêter la diffusion | active |           |                                                         |
			| —                                     |          |           |                                                         |
			| Recommencer                           | active   |           |                                                         |
			| Sauter                                | active   |           |                                                         |
			| Insérer après ce sonore               | active   |           |                                                         |
			| Couper                                | active   |           |                                                         |

	Scénario: Le service installé pendant que l'interface est ouverte se pilote dès l'ouverture du menu
		Étant donné le service de diffusion non installé
		Quand la fenêtre de l'interface s'ouvre
		Et le service de diffusion s'installe, arrêté
		Et j'ouvre le menu « Diffusion »
		Alors le menu « Diffusion » a les entrées :
			| entrée                                | état     | raccourci | infobulle                                               |
			| Moniteur de l'antenne               | active   | Alt+P     | Écouter l'antenne sur la sortie de pré-écoute, aussitôt |
			| —                                     |          |           |                                                         |
			| Démarrer la diffusion | active |           |                                                         |
			| —                                     |          |           |                                                         |
			| Recommencer                           | active   |           |                                                         |
			| Sauter                                | active   |           |                                                         |
			| Insérer après ce sonore               | active   |           |                                                         |
			| Couper                                | active   |           |                                                         |
		Et la barre d'état ne signale pas d'installation à terminer

	# ─── Sans le service ───────────────────────────────────────

	Scénario: Sans service, la barre d'état dit que l'installation n'est pas définitive, et le menu pilote une diffusion d'essai
		Étant donné le service de diffusion non installé
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre d'état signale « Installation non définitive : diffusion sans service », avec l'infobulle « La diffusion ne démarre pas avec le poste, et ne redémarre pas seule après un plantage. Sur un ordinateur dédié à l'antenne, installer le service : ./install.sh --service (INSTALL.md, Service de diffusion). »
		Et la barre de menus a les menus « Fichier », « Affichage », « Onglets », « Tableau », « Diffusion », « Maintenance », « Aide »
		Et le menu « Diffusion » a les entrées :
			| entrée                                | état     | raccourci | infobulle                                                  |
			| Moniteur de l'antenne               | active   | Alt+P     | Écouter l'antenne sur la sortie de pré-écoute, aussitôt    |
			| —                                     |          |           |                                                            |
			| Démarrer la diffusion d'essai | active |           | Sans service : Machin player dans une fenêtre de terminal |
			| —                                     |          |           |                                                            |
			| Recommencer                           | active   |           |                                                         |
			| Sauter                                | active   |           |                                                         |
			| Insérer après ce sonore               | active   |           |                                                         |
			| Couper                                | active   |           |                                                         |

	Scénario: Sans service, « Démarrer la diffusion d'essai » lance Machin player comme le service, dans une fenêtre de terminal
		Étant donné le service de diffusion non installé
		Et le terminal « konsole » du poste
		Et l'interface lancée sur la configuration du service
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion d'essai » dans le menu « Diffusion »
		Alors le terminal a lancé bientôt Machin player, comme le service
		Et la barre d'état annonce « Diffusion d'essai lancée dans un terminal : Ctrl-C l'y arrête. »
		Et systemctl n'a reçu que des demandes d'état

	Scénario: Une interface sur une autre configuration que le service lance quand même la diffusion d'essai comme lui, et le dit
		Étant donné le service de diffusion non installé
		Et le terminal « konsole » du poste
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion d'essai » dans le menu « Diffusion »
		Alors le terminal a lancé bientôt Machin player, comme le service
		Et la barre d'état annonce que la diffusion d'essai lit la configuration du service, et non celle de l'interface

	Scénario: Sans service, une diffusion d'essai qui tourne s'arrête, mais ne se relance pas
		Étant donné le service de diffusion non installé
		Et une diffusion d'essai qui tourne, lancée à la main
		Quand la fenêtre de l'interface s'ouvre
		Et l'état du binaire lecture est bientôt « En diffusion » sur l'onglet Antenne
		Et j'ouvre le menu « Diffusion »
		Alors le menu « Diffusion » a les entrées :
			| entrée                                | état     | raccourci | infobulle                                                             |
			| Moniteur de l'antenne               | active   | Alt+P     | Écouter l'antenne sur la sortie de pré-écoute, aussitôt               |
			| —                                     |          |           |                                                                       |
			| Arrêter la diffusion d'essai | active |           | Sans service : arrête le Machin player lancé à la main, comme Ctrl-C |
			| —                                     |          |           |                                                                       |
			| Recommencer                           | active   |           |                                                         |
			| Sauter                                | active   |           |                                                         |
			| Insérer après ce sonore               | active   |           |                                                         |
			| Couper                                | active   |           |                                                         |

	Scénario: Sans service, « Arrêter la diffusion d'essai » arrête Machin player comme Ctrl-C
		Étant donné le service de diffusion non installé
		Et une diffusion d'essai qui tourne, lancée à la main
		Quand la fenêtre de l'interface s'ouvre
		Et l'état du binaire lecture est bientôt « En diffusion » sur l'onglet Antenne
		Et je choisis « Arrêter la diffusion d'essai » dans le menu « Diffusion »
		Alors la barre d'état annonce « Arrêt de la diffusion d'essai demandé… »
		Et la barre d'état annonce bientôt « Diffusion d'essai arrêtée. »
		Et la diffusion d'essai s'est arrêtée par SIGTERM
		Et systemctl n'a reçu que des demandes d'état

	Scénario: Sans terminal sur le poste, la barre d'état dit comment lancer la diffusion d'essai
		Étant donné le service de diffusion non installé
		Et aucun terminal sur le poste
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion d'essai » dans le menu « Diffusion »
		Alors la barre d'état annonce « Aucun terminal trouvé (konsole, x-terminal-emulator) : lancer Machin player à la main. »

	# ─── Témoins de la diffusion (https://github.com/dascritch/machincast/issues/322) ───

	Scénario: Le titre de l'onglet Antenne porte 🟩 tant que le service n'est pas installé, 🟥 dès qu'il l'est
		Étant donné le service de diffusion non installé
		Quand la fenêtre de l'interface s'ouvre
		Alors le titre de l'onglet Antenne est « 🟩 Antenne »
		Quand le service de diffusion s'installe, arrêté
		Et j'ouvre le menu « Diffusion »
		Alors le titre de l'onglet Antenne est « 🟥 Antenne »

	Plan du scénario: Avec le service installé, le titre de l'onglet Antenne porte 🟥, que la diffusion tourne ou non
		Étant donné le service de diffusion installé, <etat>
		Quand la fenêtre de l'interface s'ouvre
		Alors le titre de l'onglet Antenne est « 🟥 Antenne »

		Exemples:
			| etat      |
			| arrêté    |
			| en marche |
			| en échec  |

	# ─── Statut coloré de la diffusion (https://github.com/dascritch/machincast/issues/495) ───

	Plan du scénario: « En diffusion » est sur fond rouge en service, vert en essai, et le titre de la fenêtre porte le témoin et la radio
		Étant donné le service de diffusion <service>
		Et une diffusion d'essai qui tourne, lancée à la main
		Quand la fenêtre de l'interface s'ouvre
		Et l'état du binaire lecture est bientôt « En diffusion » sur l'onglet Antenne
		Alors l'état de la diffusion est sur fond <fond>, en texte <texte>, avec un liseré <fond> de 2 px
		Et le titre de la fenêtre est « MachinCast <témoin> Radio de test »

		Exemples:
			| service              | fond    | texte   | témoin |
			| non installé         | #2e7d32 | #ffffff | 🟩     |
			| installé, en marche  | #c62828 | #ffffff | 🟥     |

	Plan du scénario: Pendant un blanc à l'antenne, le titre de la fenêtre garde le témoin de couleur, et l'état son liseré sans fond
		Étant donné le service de diffusion <service>
		Et une diffusion d'essai qui laisse un blanc, lancée à la main
		Quand la fenêtre de l'interface s'ouvre
		Alors l'état de la diffusion devient bientôt « Blanc à l'antenne », sans fond coloré, avec un liseré <fond> de 2 px
		Et le titre de la fenêtre est « MachinCast <témoin> Radio de test »

		Exemples:
			| service              | fond    | témoin |
			| non installé         | #2e7d32 | 🟩     |
			| installé, en marche  | #c62828 | 🟥     |

	Scénario: Hors diffusion, l'état garde son liseré sans fond coloré, et le titre de la fenêtre porte ⛶
		Étant donné le service de diffusion non installé
		Et une diffusion d'essai qui tourne, lancée à la main
		Quand la fenêtre de l'interface s'ouvre
		Et l'état du binaire lecture est bientôt « En diffusion » sur l'onglet Antenne
		Et je choisis « Arrêter la diffusion d'essai » dans le menu « Diffusion »
		Alors l'état de la diffusion devient bientôt « À l'arrêt », sans fond coloré, avec un liseré #2e7d32 de 2 px
		Et le titre de la fenêtre est « MachinCast ⛶ Radio de test »

	Scénario: Le service installé, arrêté : liseré rouge, et ⛶ dans le titre de la fenêtre
		Étant donné le service de diffusion installé, arrêté
		Quand la fenêtre de l'interface s'ouvre
		Alors l'état de la diffusion devient bientôt « À l'arrêt », sans fond coloré, avec un liseré #c62828 de 2 px
		Et le titre de la fenêtre est « MachinCast ⛶ Radio de test »

	Plan du scénario: Le texte prend, du blanc ou du noir, celui qui contraste le plus avec le fond
		Alors sur le fond <fond>, le texte de l'état de la diffusion est <texte>

		Exemples:
			| fond    | texte   |
			| #c62828 | #ffffff |
			| #2e7d32 | #ffffff |
			| #ffeb3b | #000000 |
			| #66bb6a | #000000 |

	Scénario: La dernière ligne de la fenêtre dit « 🔇 Diffusion arrêtée » tant que la diffusion ne tourne pas
		Étant donné le service de diffusion non installé
		Et une diffusion d'essai qui tourne, lancée à la main
		Quand la fenêtre de l'interface s'ouvre
		Et l'état du binaire lecture est bientôt « En diffusion » sur l'onglet Antenne
		Alors la dernière ligne de la fenêtre ne dit pas « 🔇 Diffusion arrêtée »
		Quand je choisis « Arrêter la diffusion d'essai » dans le menu « Diffusion »
		Alors la dernière ligne de la fenêtre dit bientôt « 🔇 Diffusion arrêtée »

	Scénario: Sans diffusion, la dernière ligne de la fenêtre dit « 🔇 Diffusion arrêtée » dès l'ouverture
		Étant donné le service de diffusion installé, arrêté
		Quand la fenêtre de l'interface s'ouvre
		Alors la dernière ligne de la fenêtre dit bientôt « 🔇 Diffusion arrêtée »

	# ─── Maintenance de la base de données (https://github.com/dascritch/machincast/issues/127) ───

	Scénario: « Maintenance de la base de données… » lance Machin maintenance-db dans un terminal, sur la configuration de l'interface
		Étant donné le service de diffusion non installé
		Et le terminal « konsole » du poste
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Maintenance de la base de données… » dans le menu « Maintenance »
		Alors l'interface a demandé confirmation, avec l'emplacement des sauvegardes : le répertoire des sauvegardes de sa configuration
		Et le terminal a lancé bientôt Machin maintenance-db, sur la configuration de l'interface, avec les sauvegardes dans le répertoire des sauvegardes de sa configuration, le terminal restant ouvert
		Et la barre d'état annonce « Maintenance de la base de données lancée dans un terminal : sauvegarde, vérification du schéma, optimisation. »

	Scénario: Les sauvegardes vont à l'emplacement choisi dans la confirmation
		Étant donné le service de diffusion non installé
		Et le terminal « konsole » du poste
		Et l'emplacement « /media/cle/sauvegardes » choisi pour les sauvegardes de la maintenance
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Maintenance de la base de données… » dans le menu « Maintenance »
		Alors le terminal a lancé bientôt Machin maintenance-db, sur la configuration de l'interface, avec les sauvegardes dans « /media/cle/sauvegardes », le terminal restant ouvert

	# ─── Export de la base (https://github.com/dascritch/machincast/issues/347) ───

	Scénario: « Exporter la base… » sauvegarde la base de l'interface dans son répertoire des sauvegardes, sans terminal
		Étant donné le service de diffusion non installé
		Et l'export de la base qui réussit
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Exporter la base… » dans le menu « Maintenance »
		Alors l'entrée « Exporter la base… » du menu « Maintenance » est inactive
		Et la barre d'état annonce bientôt la base exportée dans le répertoire des sauvegardes de sa configuration
		Et l'export a lancé Machin backup-db sur la configuration de l'interface, dans le répertoire des sauvegardes de sa configuration
		Et l'entrée « Exporter la base… » du menu « Maintenance » est active

	Scénario: Un export impossible dit pourquoi, sans l'horodatage de la ligne
		Étant donné le service de diffusion non installé
		Et l'export de la base qui échoue avec « sauvegarde impossible : pg_dump introuvable, installer postgresql-client »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Exporter la base… » dans le menu « Maintenance »
		Alors la barre d'état annonce bientôt « Export de la base impossible : sauvegarde impossible : pg_dump introuvable, installer postgresql-client »

	Scénario: Une maintenance de la base non confirmée n'est pas lancée
		Étant donné le service de diffusion non installé
		Et le terminal « konsole » du poste
		Et la maintenance de la base non confirmée
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Maintenance de la base de données… » dans le menu « Maintenance »
		Alors la barre d'état annonce « Maintenance de la base de données abandonnée : rien n'a été lancé. »
		Et le terminal n'a rien lancé

	Scénario: Sans terminal, la barre d'état dit comment lancer la maintenance à la main
		Étant donné le service de diffusion non installé
		Et aucun terminal sur le poste
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Maintenance de la base de données… » dans le menu « Maintenance »
		Alors la barre d'état annonce « Aucun terminal trouvé (konsole, x-terminal-emulator) : lancer Machin maintenance-db à la main. »

	# ─── Paramètres du service (https://github.com/dascritch/machincast/issues/389) ───
	# Les préférences de l'interface valent aussitôt ; les paramètres du service redémarrent la diffusion, et
	# reviennent si elle ne redémarre pas.

	Scénario: Des paramètres du service changés redémarrent le service de diffusion, qui les prend
		Étant donné le service de diffusion installé, en marche
		Et le fichier de configuration de l'interface noté tel qu'il est
		Et les préférences régleront l'antenne « carte-2 » et la pré-écoute « preecoute-factice »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors la fenêtre ouverte est celle des paramètres du service
		Et systemctl a reçu bientôt « restart machincast.service »
		Et la barre d'état annonce bientôt « Diffusion démarrée. »
		Et le fichier de configuration donne l'antenne « carte-2 »

	Scénario: Un redémarrage refusé ramène les paramètres du service précédents, dans le fichier et dans l'interface
		Étant donné le service de diffusion installé, en marche
		Et systemctl refuse en disant « Interactive authentication required. »
		Et le fichier de configuration de l'interface noté tel qu'il est
		Et les préférences régleront l'antenne « carte-2 » et la pré-écoute « preecoute-factice »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors systemctl a reçu bientôt « restart machincast.service »
		Et la barre d'état annonce bientôt « Diffusion non redémarrée : les paramètres du service précédents sont revenus, dans le fichier de configuration et dans l'interface. »
		Et le fichier de configuration est revenu tel qu'il était
		Et l'interface n'a pas d'antenne réglée

	Scénario: Des paramètres du service changés, service arrêté, valent au prochain démarrage, sans redémarrage
		Étant donné le service de diffusion installé, arrêté
		Et les préférences régleront l'antenne « carte-2 » et la pré-écoute « preecoute-factice »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors systemctl n'a reçu que des demandes d'état
		Et le fichier de configuration donne l'antenne « carte-2 »

	Scénario: Les préférences de l'interface ne redémarrent jamais la diffusion
		Étant donné le service de diffusion installé, en marche
		Et les préférences régleront seulement la pré-écoute « casque-usb »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors la fenêtre ouverte est celle des préférences de l'interface
		Et systemctl n'a reçu que des demandes d'état
		Et le fichier de configuration donne la pré-écoute « casque-usb »
