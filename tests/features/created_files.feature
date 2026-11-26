# language: fr
Fonctionnalité: La liste des fichiers créés par MachinCast, les seuls qu'il touche
	En tant qu'administrateur du poste de diffusion,
	je veux la liste des fichiers que MachinCast a créés, un par ligne, à côté de sa configuration,
	afin de savoir quoi sauvegarder pour une reprise d'activité, et d'être sûr qu'il ne modifie ni n'efface aucun autre fichier.

	https://github.com/dascritch/machincast/issues/652. La liste, fichiers-machincast.txt, est dans le répertoire du
	fichier de configuration (machincast.created_files) : un chemin absolu par ligne, triés, sans doublon. Y sont la
	configuration et les réglages, et les données à sauvegarder ; pas les logs, les fichiers d'exécution ni les
	dépendances. Les scénarios posent leur liste dans leur répertoire temporaire.

	# ─── La liste ──────────────────────────────────────────

	Scénario: Un fichier créé s'inscrit dans la liste, un chemin absolu par ligne, triés, sans doublon
		Étant donné la liste des fichiers créés de la configuration « machincast.toml »
		Quand MachinCast écrit « sorties/b.pls », puis « sorties/a.html », puis de nouveau « sorties/b.pls »
		Alors la liste a pour lignes les chemins absolus de « sorties/a.html » et « sorties/b.pls », dans cet ordre
		Et la liste est « fichiers-machincast.txt », à côté de « machincast.toml »

	Scénario: Un fichier qui existe hors de la liste n'est ni réécrit ni effacé
		Étant donné la liste des fichiers créés de la configuration « machincast.toml »
		Et le fichier « notes.txt », écrit par quelqu'un d'autre
		Quand MachinCast écrit « notes.txt »
		Alors il est refusé : « notes.txt : pas créé par MachinCast, il n'est pas dans fichiers-machincast.txt : MachinCast n'y touche pas »
		Et « notes.txt » est intact

	Scénario: Un fichier inscrit se réécrit ; effacé par MachinCast, il quitte la liste
		Étant donné la liste des fichiers créés de la configuration « machincast.toml »
		Quand MachinCast écrit « sorties/a.html », puis de nouveau « sorties/a.html »
		Et MachinCast efface « sorties/a.html »
		Alors la liste est vide

	Scénario: La liste se réécrit en place : elle garde son inode, donc son groupe et son mode
		Étant donné la liste des fichiers créés de la configuration « machincast.toml »
		Et la liste existe déjà, au mode 0660
		Quand MachinCast écrit « sorties/a.html »
		Alors la liste a gardé son inode et son mode 0660

	Scénario: Un binaire lancé avec une configuration tient la liste à côté d'elle ; la configuration, sienne, s'y inscrit à sa première écriture
		Étant donné le fichier de configuration valide « station.toml », sans liste imposée par les tests
		Quand un binaire se lance avec « station.toml »
		Alors la liste en cours est « fichiers-machincast.txt », à côté de « station.toml »
		Quand MachinCast écrit « station.toml »
		Alors la liste a pour lignes le chemin absolu de « station.toml »

	# ─── install.sh ────────────────────────────────────────

	Scénario: install.sh inscrit et retire des fichiers, et adopte ceux qui existent déjà
		Étant donné la liste des fichiers créés de la configuration « machincast.toml »
		Et le fichier « sorties/ancien.pls », écrit par une version d'avant la liste
		Quand install.sh lance « adopt » sur « sorties/ancien.pls » et « sorties/absent.pls »
		Alors la commande écrit le chemin absolu de « sorties/ancien.pls », et se termine par le code 0
		Et la liste a pour lignes le chemin absolu de « sorties/ancien.pls »
		Quand install.sh lance « check » sur « notes.txt », écrit par quelqu'un d'autre
		Alors la commande se termine par le code 1
		Quand install.sh lance « add » sur « unite.service »
		Et install.sh lance « forget » sur « sorties/ancien.pls »
		Alors la liste a pour lignes le chemin absolu de « unite.service »

	# ─── Ceux qui écrivent ─────────────────────────────────

	Plan du scénario: <écrivain> inscrit les fichiers qu'il crée
		Étant donné la liste des fichiers créés de la configuration « machincast.toml »
		Quand <écrivain> écrit ses fichiers
		Alors chacun de ses fichiers est dans la liste

		Exemples:
			| écrivain                                |
			| la page HTML de Machin player           |
			| la simulation de Machin player          |
			| le rapport de l'audit complet           |
			| la pré-écoute choisie dans l'interface  |
			| les réglages des vues de l'interface    |

	Plan du scénario: <écrivain> ne touche pas à un fichier qui existe hors de la liste
		Étant donné la liste des fichiers créés de la configuration « machincast.toml »
		Et les fichiers de <écrivain> existent déjà, écrits par quelqu'un d'autre
		Quand <écrivain> écrit ses fichiers
		Alors il est refusé, et ses fichiers sont intacts

		Exemples:
			| écrivain                                       |
			| la page HTML de Machin player                  |
			| la simulation de Machin player                 |
			| le rapport de l'audit complet                  |
			| le retrait des réglages d'économie d'énergie   |

	Scénario: Des réglages des vues qui ne sont pas de MachinCast restent intacts : les vues se règlent le temps de la session
		Étant donné la liste des fichiers créés de la configuration « machincast.toml »
		Et le fichier des vues existe déjà, écrit par quelqu'un d'autre
		Quand l'interface règle ses vues
		Alors le fichier des vues est intact, et les vues sont réglées dans un fichier d'exécution
