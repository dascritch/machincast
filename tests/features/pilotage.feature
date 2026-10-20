# language: fr
Fonctionnalité: Pilotage de la diffusion depuis l'interface
	En tant que technicien d'antenne,
	je veux démarrer, arrêter et redémarrer la diffusion depuis l'interface,
	afin de ne pas avoir besoin d'un terminal.

	https://github.com/dascritch/machincast/issues/25, spec § 8.11. Le menu « Diffusion » appelle systemctl sur le
	service machincast.service, que la règle polkit d'install.sh --service autorise avec l'authentification d'un
	administrateur (https://github.com/dascritch/machincast/issues/22) : jamais sudo. Sans service, l'interface dit que
	l'installation n'est pas définitive, et comment la terminer ; « Démarrer la diffusion » lance alors Machin lecture
	dans une fenêtre de terminal. Les commandes systemctl et konsole du scénario sont des imitations, en tête du PATH :
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
			| entrée                    | état         | raccourci | infobulle |
			| Démarrer la diffusion     | <demarrer>   |           |           |
			| Arrêter la diffusion      | <arreter>    |           |           |
			| Redémarrer la diffusion   | <redemarrer> |           |           |
		Et la barre d'état ne signale pas d'installation à terminer

		Exemples:
			| etat       | demarrer | arreter  | redemarrer |
			| arrêté     | active   | inactive | inactive   |
			| en marche  | inactive | active   | active     |
			| en échec   | active   | inactive | active     |

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
			| entrée                    | état     | raccourci | infobulle |
			| Démarrer la diffusion     | inactive |           |           |
			| Arrêter la diffusion      | active   |           |           |
			| Redémarrer la diffusion   | active   |           |           |

	Scénario: Après une commande, le menu suit le nouvel état du service
		Étant donné le service de diffusion installé, arrêté
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion » dans le menu « Diffusion »
		Alors la barre d'état annonce bientôt « Diffusion démarrée. »
		Et le menu « Diffusion » a les entrées :
			| entrée                    | état     | raccourci | infobulle |
			| Démarrer la diffusion     | inactive |           |           |
			| Arrêter la diffusion      | active   |           |           |
			| Redémarrer la diffusion   | active   |           |           |

	Scénario: Le service installé pendant que l'interface est ouverte se pilote dès l'ouverture du menu
		Étant donné le service de diffusion non installé
		Quand la fenêtre de l'interface s'ouvre
		Et le service de diffusion s'installe, arrêté
		Et j'ouvre le menu « Diffusion »
		Alors le menu « Diffusion » a les entrées :
			| entrée                    | état     | raccourci | infobulle |
			| Démarrer la diffusion     | active   |           |           |
			| Arrêter la diffusion      | inactive |           |           |
			| Redémarrer la diffusion   | inactive |           |           |
		Et la barre d'état ne signale pas d'installation à terminer

	# ─── Sans le service ───────────────────────────────────────

	Scénario: Sans service, la barre d'état dit que l'installation n'est pas définitive, et comment la terminer
		Étant donné le service de diffusion non installé
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre d'état signale « Installation non définitive : diffusion sans service », avec l'infobulle « La diffusion ne démarre pas avec le poste, et ne redémarre pas seule après un plantage. Sur un ordinateur dédié à l'antenne, installer le service : ./install.sh --service (INSTALL.md, Service de diffusion). »
		Et le menu « Diffusion » a les entrées :
			| entrée                    | état     | raccourci | infobulle                                                     |
			| Démarrer la diffusion     | active   |           | Sans service : Machin lecture dans une fenêtre de terminal    |
			| Arrêter la diffusion      | inactive |           | Sans service : Ctrl-C dans le terminal de Machin lecture      |
			| Redémarrer la diffusion   | inactive |           | Sans service : Ctrl-C dans le terminal de Machin lecture      |

	Scénario: Sans service, « Démarrer la diffusion » lance Machin lecture dans une fenêtre de terminal
		Étant donné le service de diffusion non installé
		Et le terminal « konsole » du poste
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion » dans le menu « Diffusion »
		Alors le terminal a lancé bientôt Machin lecture, avec la configuration de l'interface
		Et la barre d'état annonce « Machin lecture lancé dans un terminal : Ctrl-C l'y arrête. »
		Et systemctl n'a reçu que des demandes d'état

	Scénario: Sans service, une diffusion qui tourne déjà n'est pas relancée
		Étant donné le service de diffusion non installé
		Et le terminal « konsole » du poste
		Et une diffusion qui tourne déjà, hors service
		Quand la fenêtre de l'interface s'ouvre
		Et l'état du binaire lecture est bientôt « En diffusion » sur l'accueil
		Et j'ouvre le menu « Diffusion »
		Alors le menu « Diffusion » a les entrées :
			| entrée                    | état     | raccourci | infobulle                                                     |
			| Démarrer la diffusion     | inactive |           | La diffusion tourne déjà                                      |
			| Arrêter la diffusion      | inactive |           | Sans service : Ctrl-C dans le terminal de Machin lecture      |
			| Redémarrer la diffusion   | inactive |           | Sans service : Ctrl-C dans le terminal de Machin lecture      |

	Scénario: Sans terminal sur le poste, la barre d'état dit comment lancer la diffusion
		Étant donné le service de diffusion non installé
		Et aucun terminal sur le poste
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Démarrer la diffusion » dans le menu « Diffusion »
		Alors la barre d'état annonce « Aucun terminal trouvé (konsole, x-terminal-emulator) : lancer Machin lecture à la main. »
