# language: fr
Fonctionnalité: Programmes de MachinCast en cours pendant l'installation
	En tant qu'administrateur du poste,
	je veux qu'install.sh me dise quels programmes de MachinCast tournent, les arrête si je l'accepte, et les relance
	à la fin,
	afin qu'une mise à jour, et ses migrations de la base, ne se fassent pas sous un programme qui s'en sert.

	https://github.com/dascritch/machincast/issues/254. machincast.programmes lit /proc, avec la seule bibliothèque
	standard : install.sh le lance avant de toucher au venv. Il reconnaît Machin lecture (le service de diffusion, une
	diffusion d'essai ou une simulation), Machin indexation et Machin interface, lancés par bin/Machin, par leur
	exécutable du venv ou par python -m, sous tous les comptes du poste. À la fin, il relance ceux du compte qui lance
	install.sh : la diffusion d'essai dans un terminal, l'interface dans la session, chacune avec ses arguments et
	depuis son répertoire ; il dit ce qui reste à rouvrir à la main. Le service de diffusion, install.sh le relance
	lui-même. Les scénarios lisent un /proc factice ; les comptes y sont « radio », celui qui installe, et « xavier ».

	Scénario: Les programmes de MachinCast en cours sont reconnus, quel que soit leur lancement
		Étant donné les processus :
			| pid | compte | commande                                                                                     | cgroup                                     |
			| 101 | radio  | /opt/machincast/.venv/bin/python3 /opt/machincast/.venv/bin/Machin_lecture                    | 0::/system.slice/machincast.service        |
			| 102 | radio  | /opt/machincast/.venv/bin/python3 /opt/machincast/.venv/bin/Machin_interface --config m.toml  | 0::/user.slice/user-1000.slice/session.scope |
			| 103 | radio  | /opt/machincast/.venv/bin/python3 -m machincast.lecture --simulation --repertoire /tmp/s      | 0::/user.slice/user-1000.slice/session.scope |
			| 104 | xavier | /opt/machincast/.venv/bin/python3 /opt/machincast/.venv/bin/Machin_indexation --audit-complet | 0::/user.slice/user-1001.slice/session.scope |
			| 105 | xavier | /opt/machincast/.venv/bin/Machin_lecture --config essai.toml                                  | 0::/user.slice/user-1001.slice/session.scope |
		Alors les programmes en cours sont :
			| pid | compte | programme  | nature               | arguments                       |
			| 101 | radio  | lecture    | service de diffusion |                                 |
			| 102 | radio  | interface  | interface            | --config m.toml                 |
			| 103 | radio  | lecture    | simulation           | --simulation --repertoire /tmp/s |
			| 104 | xavier | indexation | indexation           | --audit-complet                 |
			| 105 | xavier | lecture    | diffusion d'essai    | --config essai.toml             |

	Scénario: Ce qui n'est pas un programme de MachinCast est ignoré
		Étant donné les processus :
			| pid | compte | commande                                                            | cgroup |
			| 201 | radio  | vim Machin_lecture                                                  |        |
			| 202 | radio  | less /opt/machincast/.venv/bin/Machin_interface                     |        |
			| 203 | radio  | /opt/machincast/.venv/bin/python3 -m machincast.installation migrer |        |
			| 204 | radio  | /usr/bin/python3 -m machincast.programmes lister                    |        |
			| 205 | radio  | /opt/machincast/.venv/bin/Machin_maintenance-db                     |        |
			| 208 | radio  | /opt/machincast/.venv/bin/Machin_purge                              |        |
		Et le processus 206 sans ligne de commande, comme un fil du noyau
		Et le processus 207 disparu pendant la lecture
		Alors aucun programme n'est en cours

	Scénario: Un programme d'un autre compte, dont le répertoire est illisible, est reconnu quand même
		Le répertoire d'un processus (/proc/<pid>/cwd) ne se lit que pour son propre compte ; sa ligne de commande, son
		propriétaire et son groupe de contrôle se lisent pour tous.

		Étant donné les processus :
			| pid | compte | commande                                                     | cgroup |
			| 105 | xavier | /opt/machincast/.venv/bin/Machin_lecture --config essai.toml |        |
		Et le répertoire du processus 105 illisible
		Alors les programmes en cours sont :
			| pid | compte | programme | nature            | arguments           |
			| 105 | xavier | lecture   | diffusion d'essai | --config essai.toml |

	Scénario: La liste pour install.sh donne, pour chaque programme, s'il est du compte qui installe et s'il est le service
		Étant donné les processus :
			| pid | compte | commande                                                                                    | cgroup                              |
			| 101 | radio  | /opt/machincast/.venv/bin/python3 /opt/machincast/.venv/bin/Machin_lecture                   | 0::/system.slice/machincast.service |
			| 102 | radio  | /opt/machincast/.venv/bin/python3 /opt/machincast/.venv/bin/Machin_interface --config m.toml |                                     |
			| 104 | xavier | /opt/machincast/.venv/bin/python3 /opt/machincast/.venv/bin/Machin_indexation               |                                     |
		Quand install.sh demande la liste des programmes en cours, sous le compte « radio »
		Alors la liste pour install.sh est :
			| pid | du compte | service | programme                                                   |
			| 101 | oui       | oui     | Machin lecture (service de diffusion), compte radio         |
			| 102 | oui       | non     | Machin interface --config m.toml (interface), compte radio  |
			| 104 | non       | non     | Machin indexation (indexation), compte xavier               |
		Et l'état des programmes arrêtés est enregistré

	Scénario: À la fin, la diffusion d'essai et l'interface du compte se relancent, avec leurs arguments et depuis leur répertoire
		Étant donné les processus :
			| pid | compte | commande                                                                                     | cgroup                              | répertoire        |
			| 101 | radio  | /opt/machincast/.venv/bin/python3 /opt/machincast/.venv/bin/Machin_lecture                    | 0::/system.slice/machincast.service | /                 |
			| 102 | radio  | /opt/machincast/.venv/bin/python3 /opt/machincast/.venv/bin/Machin_interface --config m.toml  |                                     | /home/radio/radio |
			| 103 | radio  | /opt/machincast/.venv/bin/python3 -m machincast.lecture --simulation --repertoire /tmp/s      |                                     | /home/radio       |
			| 105 | radio  | /opt/machincast/.venv/bin/Machin_lecture --config essai.toml                                  |                                     | /home/radio/radio |
			| 106 | radio  | /opt/machincast/.venv/bin/Machin_indexation --audit-complet                                   |                                     | /home/radio       |
			| 107 | xavier | /opt/machincast/.venv/bin/Machin_interface                                                    |                                     | /home/xavier      |
		Et une session graphique, avec le terminal « konsole »
		Quand install.sh demande la liste des programmes en cours, sous le compte « radio »
		Et install.sh relance les programmes arrêtés, sous le compte « radio »
		Alors les programmes relancés sont :
			| répertoire        | commande                                              | détachée |
			| /home/radio/radio | Machin interface --config m.toml                      | oui      |
			| /home/radio/radio | konsole -e Machin lecture --config essai.toml         | oui      |
		Et la relance dit :
			| message                                                                                     |
			| relancé : Machin interface --config m.toml                                                  |
			| relancé dans un terminal : Machin lecture --config essai.toml                               |
			| simulation interrompue : la relancer depuis l'onglet Simulation de l'interface              |
			| indexation interrompue : relancer Machin indexation --audit-complet                         |
			| à rouvrir par le compte xavier : Machin interface                                           |

	Scénario: Sans session graphique, ni terminal, rien ne se relance : la relance dit quoi rouvrir à la main
		Étant donné les processus :
			| pid | compte | commande                                                     | cgroup | répertoire  |
			| 102 | radio  | /opt/machincast/.venv/bin/Machin_interface                   |        | /home/radio |
			| 105 | radio  | /opt/machincast/.venv/bin/Machin_lecture --config essai.toml |        | /home/radio |
		Et aucune session graphique, ni terminal
		Quand install.sh demande la liste des programmes en cours, sous le compte « radio »
		Et install.sh relance les programmes arrêtés, sous le compte « radio »
		Alors aucun programme n'est relancé
		Et la relance dit :
			| message                                                                                        |
			| à rouvrir dans la session graphique : Machin interface                                         |
			| à rouvrir dans un terminal : Machin lecture --config essai.toml                                |

	Scénario: En simulation, la relance dit ce qu'elle ferait, sans rien lancer
		Étant donné les processus :
			| pid | compte | commande                                   | cgroup | répertoire  |
			| 102 | radio  | /opt/machincast/.venv/bin/Machin_interface |        | /home/radio |
		Et une session graphique, avec le terminal « konsole »
		Quand install.sh demande la liste des programmes en cours, sous le compte « radio »
		Et install.sh simule la relance des programmes arrêtés, sous le compte « radio »
		Alors aucun programme n'est relancé
		Et la relance dit :
			| message                                                            |
			| [simulation] relancé : Machin interface                            |

	Scénario: Le module se lance sans le venv, avec la seule bibliothèque standard
		Alors machincast.programmes liste les programmes en cours avec un Python sans paquet installé
