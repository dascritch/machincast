# language: fr
Fonctionnalité: Pilotage de la diffusion depuis l'interface
	En tant que technicien d'antenne,
	je veux démarrer, arrêter et redémarrer la diffusion depuis l'interface,
	afin de ne pas avoir besoin d'un terminal.

	https://github.com/dascritch/machincast/issues/25, spec § 8.11. Le menu « Diffusion » appelle systemctl sur le
	service machincast.service, que la règle polkit d'install.sh --service autorise avec l'authentification d'un
	administrateur (https://github.com/dascritch/machincast/issues/22) : jamais sudo. Sans service, l'interface dit que
	l'installation n'est pas définitive, et comment la terminer ; le menu pilote alors une diffusion d'essai : Machin
	lecture lancé dans une fenêtre de terminal, qu'arrêter ou redémarrer arrête par SIGTERM, comme Ctrl-C. Son processus
	est celui qui répond sur la socket d'état. Ce n'est pas « Machin lecture --simulation », qui ne joue rien. Les commandes systemctl et konsole du scénario sont des imitations, en tête du PATH :
	elles notent leurs arguments, et répondent ce que dit le scénario ; systemctl
	change l'état du service qu'il imite.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-20 16:40:00 »
		Et les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |

	# ─── Avec le service ───────────────────────────────────────

	Plan du scénario: Le menu « Diffusion » propose ce que permet l'état du service
		Étant donné le service de diffusion installé, <etat>
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre de menus a les menus « Fichier », « Affichage », « Diffusion », « Maintenance », « Aide »
		Et le menu « Diffusion » a les entrées :
			| entrée                                | état         | raccourci | infobulle        |
			| Démarrer la diffusion                 | <demarrer>   |           |                  |
			| Arrêter la diffusion                  | <arreter>    |           |                  |
			| Redémarrer la diffusion               | <redemarrer> |           |                  |
			| —                                     |              |           |                  |
			| Sauter au sonore suivant              | inactive     |           | Rien à l'antenne |
			| Sauter après la séquence              | inactive     |           | Rien à l'antenne |
			| Couper l'événement par le fil musical | inactive     |           | Rien à l'antenne |
		Et la barre d'état ne signale pas d'installation à terminer

		Exemples:
			| etat      | demarrer | arreter  | redemarrer |
			| arrêté    | active   | inactive | inactive   |
			| en marche | inactive | active   | active     |
			| en échec  | active   | inactive | active     |

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
			| en marche | Redémarrer la diffusion | restart | Diffusion redémarrée. |

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
			| entrée                                | état     | raccourci | infobulle        |
			| Démarrer la diffusion                 | inactive |           |                  |
			| Arrêter la diffusion                  | active   |           |                  |
			| Redémarrer la diffusion               | active   |           |                  |
			| —                                     |          |           |                  |
			| Sauter au sonore suivant              | inactive |           | Rien à l'antenne |
			| Sauter après la séquence              | inactive |           | Rien à l'antenne |
			| Couper l'événement par le fil musical | inactive |           | Rien à l'antenne |

	Scénario: Après une commande, le menu suit le nouvel état du service
		Étant donné le service de diffusion installé, arrêté
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion » dans le menu « Diffusion »
		Alors la barre d'état annonce bientôt « Diffusion démarrée. »
		Et le menu « Diffusion » a les entrées :
			| entrée                                | état     | raccourci | infobulle        |
			| Démarrer la diffusion                 | inactive |           |                  |
			| Arrêter la diffusion                  | active   |           |                  |
			| Redémarrer la diffusion               | active   |           |                  |
			| —                                     |          |           |                  |
			| Sauter au sonore suivant              | inactive |           | Rien à l'antenne |
			| Sauter après la séquence              | inactive |           | Rien à l'antenne |
			| Couper l'événement par le fil musical | inactive |           | Rien à l'antenne |

	Scénario: Le service installé pendant que l'interface est ouverte se pilote dès l'ouverture du menu
		Étant donné le service de diffusion non installé
		Quand la fenêtre de l'interface s'ouvre
		Et le service de diffusion s'installe, arrêté
		Et j'ouvre le menu « Diffusion »
		Alors le menu « Diffusion » a les entrées :
			| entrée                                | état     | raccourci | infobulle        |
			| Démarrer la diffusion                 | active   |           |                  |
			| Arrêter la diffusion                  | inactive |           |                  |
			| Redémarrer la diffusion               | inactive |           |                  |
			| —                                     |          |           |                  |
			| Sauter au sonore suivant              | inactive |           | Rien à l'antenne |
			| Sauter après la séquence              | inactive |           | Rien à l'antenne |
			| Couper l'événement par le fil musical | inactive |           | Rien à l'antenne |
		Et la barre d'état ne signale pas d'installation à terminer

	# ─── Sans le service ───────────────────────────────────────

	Scénario: Sans service, la barre d'état dit que l'installation n'est pas définitive, et le menu pilote une diffusion d'essai
		Étant donné le service de diffusion non installé
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre d'état signale « Installation non définitive : diffusion sans service », avec l'infobulle « La diffusion ne démarre pas avec le poste, et ne redémarre pas seule après un plantage. Sur un ordinateur dédié à l'antenne, installer le service : ./install.sh --service (INSTALL.md, Service de diffusion). »
		Et la barre de menus a les menus « Fichier », « Affichage », « Diffusion », « Maintenance », « Aide »
		Et le menu « Diffusion » a les entrées :
			| entrée                                | état     | raccourci | infobulle                                                  |
			| Démarrer la diffusion d'essai         | active   |           | Sans service : Machin lecture dans une fenêtre de terminal |
			| Arrêter la diffusion d'essai          | inactive |           | Aucune diffusion d'essai en cours                          |
			| Redémarrer la diffusion d'essai       | inactive |           | Aucune diffusion d'essai en cours                          |
			| —                                     |          |           |                                                            |
			| Sauter au sonore suivant              | inactive |           | Rien à l'antenne                                           |
			| Sauter après la séquence              | inactive |           | Rien à l'antenne                                           |
			| Couper l'événement par le fil musical | inactive |           | Rien à l'antenne                                           |

	Scénario: Sans service, « Démarrer la diffusion d'essai » lance Machin lecture comme le service, dans une fenêtre de terminal
		Étant donné le service de diffusion non installé
		Et le terminal « konsole » du poste
		Et l'interface lancée sur la configuration du service
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion d'essai » dans le menu « Diffusion »
		Alors le terminal a lancé bientôt Machin lecture, comme le service
		Et la barre d'état annonce « Diffusion d'essai lancée dans un terminal : Ctrl-C l'y arrête. »
		Et systemctl n'a reçu que des demandes d'état

	Scénario: Une interface sur une autre configuration que le service lance quand même la diffusion d'essai comme lui, et le dit
		Étant donné le service de diffusion non installé
		Et le terminal « konsole » du poste
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion d'essai » dans le menu « Diffusion »
		Alors le terminal a lancé bientôt Machin lecture, comme le service
		Et la barre d'état annonce que la diffusion d'essai lit la configuration du service, et non celle de l'interface

	Scénario: Sans service, une diffusion d'essai qui tourne s'arrête ou se redémarre, mais ne se relance pas
		Étant donné le service de diffusion non installé
		Et une diffusion d'essai qui tourne, lancée à la main
		Quand la fenêtre de l'interface s'ouvre
		Et l'état du binaire lecture est bientôt « En diffusion » sur l'accueil
		Et j'ouvre le menu « Diffusion »
		Alors le menu « Diffusion » a les entrées :
			| entrée                                | état     | raccourci | infobulle                                                             |
			| Démarrer la diffusion d'essai         | inactive |           | La diffusion d'essai tourne déjà                                      |
			| Arrêter la diffusion d'essai          | active   |           | Sans service : arrête le Machin lecture lancé à la main, comme Ctrl-C |
			| Redémarrer la diffusion d'essai       | active   |           | Sans service : l'arrête, puis le relance dans une fenêtre de terminal |
			| —                                     |          |           |                                                                       |
			| Sauter au sonore suivant              | inactive |           | Rien à l'antenne                                                      |
			| Sauter après la séquence              | inactive |           | Rien à l'antenne                                                      |
			| Couper l'événement par le fil musical | inactive |           | Rien à l'antenne                                                      |

	Scénario: Sans service, « Arrêter la diffusion d'essai » arrête Machin lecture comme Ctrl-C
		Étant donné le service de diffusion non installé
		Et une diffusion d'essai qui tourne, lancée à la main
		Quand la fenêtre de l'interface s'ouvre
		Et l'état du binaire lecture est bientôt « En diffusion » sur l'accueil
		Et je choisis « Arrêter la diffusion d'essai » dans le menu « Diffusion »
		Alors la barre d'état annonce « Arrêt de la diffusion d'essai demandé… »
		Et la barre d'état annonce bientôt « Diffusion d'essai arrêtée. »
		Et la diffusion d'essai s'est arrêtée par SIGTERM
		Et systemctl n'a reçu que des demandes d'état

	Scénario: Sans service, « Redémarrer la diffusion d'essai » l'arrête, puis la relance dans une fenêtre de terminal
		Étant donné le service de diffusion non installé
		Et le terminal « konsole » du poste
		Et une diffusion d'essai qui tourne, lancée à la main
		Et l'interface lancée sur la configuration du service
		Quand la fenêtre de l'interface s'ouvre
		Et l'état du binaire lecture est bientôt « En diffusion » sur l'accueil
		Et je choisis « Redémarrer la diffusion d'essai » dans le menu « Diffusion »
		Alors la barre d'état annonce bientôt « Diffusion d'essai relancée dans un terminal : Ctrl-C l'y arrête. »
		Et la diffusion d'essai s'est arrêtée par SIGTERM
		Et le terminal a lancé bientôt Machin lecture, comme le service
		Et le terminal a été lancé après l'arrêt de la diffusion d'essai

	Scénario: Sans terminal sur le poste, la barre d'état dit comment lancer la diffusion d'essai
		Étant donné le service de diffusion non installé
		Et aucun terminal sur le poste
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion d'essai » dans le menu « Diffusion »
		Alors la barre d'état annonce « Aucun terminal trouvé (konsole, x-terminal-emulator) : lancer Machin lecture à la main. »

	# ─── Maintenance de la base de données (https://github.com/dascritch/machincast/issues/127) ───

	Scénario: « Maintenance de la base de données… » lance Machin maintenance-db dans un terminal, sur la configuration de l'interface
		Étant donné le service de diffusion non installé
		Et le terminal « konsole » du poste
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Maintenance de la base de données… » dans le menu « Maintenance »
		Alors l'interface a demandé confirmation, avec l'emplacement des sauvegardes : le répertoire « sauvegardes » de sa configuration
		Et le terminal a lancé bientôt Machin maintenance-db, sur la configuration de l'interface, avec les sauvegardes dans « sauvegardes » à côté d'elle, le terminal restant ouvert
		Et la barre d'état annonce « Maintenance de la base de données lancée dans un terminal : sauvegarde, vérification du schéma, optimisation. »

	Scénario: Les sauvegardes vont à l'emplacement choisi dans la confirmation
		Étant donné le service de diffusion non installé
		Et le terminal « konsole » du poste
		Et l'emplacement « /media/cle/sauvegardes » choisi pour les sauvegardes de la maintenance
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Maintenance de la base de données… » dans le menu « Maintenance »
		Alors le terminal a lancé bientôt Machin maintenance-db, sur la configuration de l'interface, avec les sauvegardes dans « /media/cle/sauvegardes », le terminal restant ouvert

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

