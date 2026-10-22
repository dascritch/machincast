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

	Plan du scénario: Un chemin de sortie ne peut pas désigner un fichier sonore
		Étant donné une configuration valide où la clé "<cle>" vaut "<chemin>"
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "extension d'un fichier sonore"

		Exemples:
			| cle                 | chemin               |
			| sorties.csv         | musique/airplay.mp3  |
			| sorties.pls         | musique/liste.flac   |
			| sorties.html        | /srv/web/page.WAV    |
			| lecture.socket_etat | run/lecture.ogg      |

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

	# ─── Crossfades (https://github.com/dascritch/machincast/issues/145) ─────────────────────────

	Scénario: Sans section [crossfades], les crossfades se règlent au dixième de seconde, jusqu'à 10 secondes, sans défaut
		Étant donné une configuration valide sans section "crossfades"
		Quand je charge la configuration
		Alors les crossfades se règlent au dixième de seconde, jusqu'à 10 secondes
		Et les crossfades n'ont pas de durée par défaut
		Et le fade-in se termine au début détecté, et le fade-out commence à la fin détectée

	Scénario: La section [crossfades] donne la granularité, le maximum et les durées par défaut
		Étant donné une configuration valide où la clé "crossfades.granularite" vaut "seconde"
		Et la clé "crossfades.maximum" vaut 8
		Et la clé "crossfades.debut" vaut 1.5
		Et la clé "crossfades.fin" vaut 3
		Quand je charge la configuration
		Alors les crossfades se règlent à la seconde, jusqu'à 8 secondes
		Et les crossfades durent par défaut 1,5 seconde au début et 3 secondes à la fin

	Scénario: Les durées par défaut vont de 0 seconde jusqu'au maximum compris
		Étant donné une configuration valide où la clé "crossfades.debut" vaut 0
		Et la clé "crossfades.fin" vaut 5
		Quand je charge la configuration
		Alors les crossfades durent par défaut 0 seconde au début et 5 secondes à la fin

	Scénario: La section [crossfades] donne la position des fondus par rapport aux blancs détectés
		https://github.com/dascritch/machincast/issues/234

		Étant donné une configuration valide où la clé "crossfades.position_entree" vaut "en_cours"
		Et la clé "crossfades.position_sortie" vaut "termine"
		Quand je charge la configuration
		Alors le fade-in est en cours au début détecté, et le fade-out se termine à la fin détectée

	Plan du scénario: Des réglages de crossfade invalides sont refusés
		Étant donné une configuration valide où la clé "<cle>" vaut <valeur>
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "<cle>"
		Et le message mentionne "<attendu>"

		Exemples:
			| cle                    | valeur     | attendu                    |
			| crossfades.granularite | "centieme" | seconde, dixieme           |
			| crossfades.maximum     | 0          | strictement positif        |
			| crossfades.maximum     | "5"        | nombre                     |
			| crossfades.debut       | -1         | positif ou nul             |
			| crossfades.fin         | 11         | au plus crossfades.maximum |
			| crossfades.debut       | true       | nombre                     |
			| crossfades.position_entree | "avant" | commence, en_cours, termine |
			| crossfades.position_sortie | 2       | texte                       |

	# ─── Détection de blanc (https://github.com/dascritch/machincast/issues/146) ─────────────────

	Scénario: Sans section [blancs], le seuil de blanc est de -40 dB
		Étant donné une configuration valide sans section "blancs"
		Quand je charge la configuration
		Alors le seuil de blanc est de -40 dB

	Plan du scénario: La clé blancs.seuil donne le seuil de blanc, de -100 dB compris à 0 dB exclu
		Étant donné une configuration valide où la clé "blancs.seuil" vaut <valeur>
		Quand je charge la configuration
		Alors le seuil de blanc est de <seuil> dB

		Exemples:
			| valeur | seuil |
			| -60    | -60   |
			| -48.5  | -48,5 |
			| -100   | -100  |
			| -0.1   | -0,1  |

	Plan du scénario: Un seuil de blanc invalide est refusé
		Étant donné une configuration valide où la clé "blancs.seuil" vaut <valeur>
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "blancs.seuil"
		Et le message mentionne "<attendu>"

		Exemples:
			| valeur | attendu                          |
			| 0      | de -100 dB compris à 0 dB exclu  |
			| 3      | de -100 dB compris à 0 dB exclu  |
			| -101   | de -100 dB compris à 0 dB exclu  |
			| "-40"  | nombre                           |
			| true   | nombre                           |

	Scénario: Une clé inconnue de la section [blancs] est refusée
		Étant donné une configuration valide où la clé "blancs.duree" vaut 1
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "blancs.duree"

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

	# ─── Interface (https://github.com/dascritch/machincast/issues/191) ─────────────────

	Scénario: Sans section [interface], le voyant « Saturation » de l'accueil est affiché
		Étant donné une configuration valide sans section "interface"
		Quand je charge la configuration
		Alors le voyant « Saturation » de l'accueil est affiché

	Plan du scénario: La clé interface.saturation affiche ou cache le voyant « Saturation » de l'accueil
		Étant donné une configuration valide où la clé "interface.saturation" vaut <valeur>
		Quand je charge la configuration
		Alors le voyant « Saturation » de l'accueil est <etat>

		Exemples:
			| valeur | etat    |
			| true   | affiché |
			| false  | caché   |

	Plan du scénario: Une valeur de interface.saturation qui n'est pas un booléen est refusée, comme une clé inconnue
		Étant donné une configuration valide où la clé "<cle>" vaut <valeur>
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "<cle>"

		Exemples:
			| cle                  | valeur |
			| interface.saturation | "oui"  |
			| interface.saturation | 1      |
			| interface.suggestions | "non" |
			| interface.silence    | true   |

	Plan du scénario: La clé interface.suggestions active ou éteint les suggestions au lancement, actives par défaut
		https://github.com/dascritch/machincast/issues/119

		Étant donné <configuration>
		Quand je charge la configuration
		Alors les suggestions au lancement sont <etat>

		Exemples:
			| configuration                                                     | etat     |
			| une configuration valide sans section "interface"                 | actives  |
			| une configuration valide où la clé "interface.suggestions" vaut true  | actives  |
			| une configuration valide où la clé "interface.suggestions" vaut false | éteintes |

	# ─── Icône de l'interface (https://github.com/dascritch/machincast/issues/111) ───────

	Scénario: Sans clé interface.icone, l'interface a l'icône de MachinCast
		Étant donné une configuration valide sans section "interface"
		Quand je charge la configuration
		Alors l'icône de l'interface est celle de MachinCast

	Plan du scénario: La clé interface.icone désigne une image SVG, PNG ou JPEG, relative au fichier de configuration
		Étant donné une configuration valide où la clé "interface.icone" vaut "<chemin>"
		Quand je charge la configuration
		Alors l'icône de l'interface est "<chemin>" à côté du fichier de configuration

		Exemples:
			| chemin           |
			| images/logo.png  |
			| logo.SVG         |
			| photos/radio.jpg |
			| radio.jpeg       |

	Plan du scénario: Une icône qui n'est pas une image SVG, PNG ou JPEG est refusée
		Étant donné une configuration valide où la clé "interface.icone" vaut <valeur>
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "interface.icone"

		Exemples:
			| valeur                |
			| "logo.gif"            |
			| "musique/jingle.mp3"  |
			| "logo"                |
			| true                  |
