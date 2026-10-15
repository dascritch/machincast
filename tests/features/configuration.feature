# language: fr
Fonctionnalité: Fichier de configuration
	En tant que développeur de MachinCast,
	je veux que chaque binaire lise sa configuration dans machincast.toml, ou dans un fichier passé avec --config,
	afin que les tests et les installations utilisent des réglages différents sans toucher au code.

	Scénario: Le modèle versionné est une configuration valide
		Étant donné le modèle de configuration du dépôt
		Quand je charge la configuration
		Alors la configuration est chargée sans erreur

	Scénario: Une configuration complète est lue
		Étant donné un fichier de configuration contenant :
			"""
			[base]
			socket = "/var/run/postgresql"
			production = "machincast"
			test = "machincast_test"

			[audio]
			sortie = "pipewire"
			peripherique = "antenne"
			preecoute = "casque"

			[sorties]
			csv = "sorties/airplay.csv"
			pls = "sorties/playlist.pls"
			html = "/srv/web/airplay.html"

			[metadonnees]
			masquer = true
			texte_public = "Vous écoutez Radio FMR"
			"""
		Quand je charge la configuration
		Alors la base de production est "machincast"
		Et la base de test est "machincast_test"
		Et la sortie audio est "pipewire" sur le périphérique "antenne"
		Et la pré-écoute utilise le périphérique "casque"
		Et la sortie CSV est "sorties/airplay.csv" à côté du fichier de configuration
		Et la sortie HTML est "/srv/web/airplay.html"
		Et les métadonnées sont masquées par défaut
		Et le texte public par défaut est "Vous écoutez Radio FMR"

	Scénario: Le périphérique d'antenne est facultatif
		Étant donné une configuration valide où la clé "audio.peripherique" est absente
		Quand je charge la configuration
		Alors la sortie audio utilise le périphérique par défaut

	Scénario: La socket d'état de Machin lecture est par défaut dans le répertoire d'exécution du compte
		Étant donné le répertoire d'exécution du compte « /run/user/1000 »
		Et une configuration valide où la clé "lecture.socket_etat" est absente
		Quand je charge la configuration
		Alors la socket d'état est "/run/user/1000/machincast/lecture.sock"

	Scénario: La clé lecture.socket_etat choisit un autre chemin pour la socket d'état
		Étant donné une configuration valide où la clé "lecture.socket_etat" vaut "run/lecture.sock"
		Quand je charge la configuration
		Alors la socket d'état est "run/lecture.sock" à côté du fichier de configuration

	Plan du scénario: Une clé obligatoire manque
		Étant donné une configuration valide où la clé "<cle>" est absente
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "<cle>"

		Exemples:
			| cle                 |
			| base.socket         |
			| base.production     |
			| base.test           |
			| audio.sortie        |
			| audio.preecoute     |
			| sorties.csv         |
			| sorties.pls         |
			| sorties.html        |
			| metadonnees.masquer |
			| metadonnees.texte_public |

	Plan du scénario: Une valeur a un type invalide
		Étant donné une configuration valide où la clé "<cle>" vaut <valeur>
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "<cle>"
		Et le message mentionne "<attendu>"

		Exemples:
			| cle                 | valeur | attendu        |
			| metadonnees.masquer | "oui"  | booléen        |
			| base.production     | 12     | texte          |
			| sorties.html        | false  | texte          |

	Scénario: Le texte public par défaut est limité à 255 caractères
		Étant donné une configuration valide où la clé "metadonnees.texte_public" vaut "<256 caractères>"
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "metadonnees.texte_public"
		Et le message mentionne "255 caractères"

	Scénario: La sortie audio doit être connue
		Étant donné une configuration valide où la clé "audio.sortie" vaut "jack"
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "audio.sortie"
		Et le message mentionne "alsa, pulseaudio, pipewire, factice"

	Scénario: La sortie audio factice est acceptée
		Étant donné une configuration valide où la clé "audio.sortie" vaut "factice"
		Quand je charge la configuration
		Alors la configuration est chargée sans erreur

	Scénario: La base de test ne peut pas être la base de production
		Étant donné une configuration valide où la clé "base.test" vaut "machincast"
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "base.test"
		Et le message mentionne "base de production"

	Scénario: La pré-écoute ne peut pas utiliser le périphérique d'antenne
		Étant donné une configuration valide où la clé "audio.preecoute" vaut "antenne"
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "audio.preecoute"

	Scénario: Une clé inconnue est refusée
		Étant donné une configuration valide où la clé "audio.volume" vaut 80
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "audio.volume"

	Scénario: Un fichier mal formé est refusé
		Étant donné un fichier de configuration contenant :
			"""
			[base
			production = "machincast"
			"""
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "TOML"

	Scénario: Un fichier absent est signalé
		Étant donné un chemin de configuration qui n'existe pas
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne le chemin du fichier

	Plan du scénario: Un binaire utilise le fichier passé avec --config
		Étant donné une configuration valide enregistrée dans "reglages-test.toml"
		Quand je lance "<executable>" avec la configuration "reglages-test.toml"
		Alors la configuration est acceptée par le binaire

		Exemples:
			| executable        |
			| Machin_lecture    |
			| Machin_indexation |
			| Machin_interface  |

	# ─── Fichier par défaut (https://github.com/dascritch/machincast/issues/76) ───
	# Les tests ne lisent jamais le machincast.toml du dépôt : un répertoire temporaire en tient lieu.

	Scénario: Le fichier par défaut est le machincast.toml du répertoire de MachinCast
		Alors le fichier de configuration par défaut est "machincast.toml" à la racine du dépôt

	Scénario: Sans --config, un binaire lit le machincast.toml du répertoire de MachinCast, quel que soit le répertoire courant
		Étant donné une configuration valide enregistrée dans "machincast.toml"
		Et ce répertoire tient lieu de répertoire de MachinCast
		Et le répertoire courant est un autre répertoire
		Quand un binaire démarre sans option
		Alors il reçoit la configuration de ce répertoire

	Scénario: Sans --config, un machincast.toml absent est signalé avec son chemin complet
		Étant donné un répertoire de MachinCast sans machincast.toml
		Et le répertoire courant est un autre répertoire
		Quand un binaire démarre sans option
		Alors il s'arrête avec le code 2
		Et son erreur mentionne le chemin complet du machincast.toml de ce répertoire

	Plan du scénario: L'aide d'un binaire indique le fichier par défaut
		Quand je lance "<executable>" avec l'option "--help"
		Alors la sortie mentionne le machincast.toml à la racine du dépôt

		Exemples:
			| executable        |
			| Machin_lecture    |
			| Machin_indexation |
			| Machin_interface  |

	Scénario: Un binaire refuse une configuration invalide
		Étant donné un chemin de configuration qui n'existe pas
		Quand je lance "Machin_lecture" avec ce chemin de configuration
		Alors le binaire s'arrête avec le code 2
		Et l'erreur affichée mentionne le chemin du fichier
