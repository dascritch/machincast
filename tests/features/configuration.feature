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
			[database]
			socket = "/var/run/postgresql"
			production = "machincast"
			test = "machincast_test"

			[audio]
			output = "pipewire"
			device = "antenne"
			preview = "casque"

			[outputs]
			csv = "sorties/airplay.csv"
			pls = "sorties/playlist.pls"
			html = "/srv/web/airplay.html"

			[metadata]
			hide = true
			public_text = "Vous écoutez Radio FMR"
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
		Étant donné une configuration valide où la clé "audio.device" est absente
		Quand je charge la configuration
		Alors la sortie audio utilise le périphérique par défaut

	Scénario: La socket d'état de Machin player est par défaut dans le répertoire d'exécution du compte
		Étant donné le répertoire d'exécution du compte « /run/user/1000 »
		Et une configuration valide où la clé "player.state_socket" est absente
		Quand je charge la configuration
		Alors la socket d'état est "/run/user/1000/machincast/lecture.sock"

	Scénario: La clé player.state_socket choisit un autre chemin pour la socket d'état
		Étant donné une configuration valide où la clé "player.state_socket" vaut "run/lecture.sock"
		Quand je charge la configuration
		Alors la socket d'état est "run/lecture.sock" à côté du fichier de configuration

	Plan du scénario: Un chemin de sortie ne peut pas désigner un fichier sonore
		Étant donné une configuration valide où la clé "<cle>" vaut "<chemin>"
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "extension d'un fichier sonore"

		Exemples:
			| cle                 | chemin               |
			| outputs.csv         | musique/airplay.mp3  |
			| outputs.pls         | musique/liste.flac   |
			| outputs.html        | /srv/web/page.WAV    |
			| player.state_socket | run/lecture.ogg      |

	Plan du scénario: Une clé obligatoire manque
		Étant donné une configuration valide où la clé "<cle>" est absente
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "<cle>"

		Exemples:
			| cle                 |
			| database.socket         |
			| database.production     |
			| database.test           |
			| audio.output        |
			| audio.preview     |
			| outputs.csv         |
			| outputs.pls         |
			| outputs.html        |
			| metadata.hide |
			| metadata.public_text |

	Plan du scénario: Une valeur a un type invalide
		Étant donné une configuration valide où la clé "<cle>" vaut <valeur>
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "<cle>"
		Et le message mentionne "<attendu>"

		Exemples:
			| cle                 | valeur | attendu        |
			| metadata.hide | "oui"  | booléen        |
			| database.production     | 12     | texte          |
			| outputs.html        | false  | texte          |

	Scénario: Le texte public par défaut est limité à 255 caractères
		Étant donné une configuration valide où la clé "metadata.public_text" vaut "<256 caractères>"
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "metadata.public_text"
		Et le message mentionne "255 caractères"

	Scénario: La sortie audio doit être connue
		Étant donné une configuration valide où la clé "audio.output" vaut "jack"
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "audio.output"
		Et le message mentionne "alsa, pulseaudio, pipewire, dummy"

	Scénario: La sortie audio factice est acceptée
		Étant donné une configuration valide où la clé "audio.output" vaut "factice"
		Quand je charge la configuration
		Alors la configuration est chargée sans erreur

	Scénario: La base de test ne peut pas être la base de production
		Étant donné une configuration valide où la clé "database.test" vaut "machincast"
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "database.test"
		Et le message mentionne "base de production"

	Scénario: La pré-écoute ne peut pas utiliser le périphérique d'antenne
		Étant donné une configuration valide où la clé "audio.preview" vaut "antenne"
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "audio.preview"

	Plan du scénario: L'entrée « sortie factice » vaut pour l'antenne comme pour la pré-écoute (https://github.com/dascritch/machincast/issues/339)
		Étant donné une configuration valide où la clé "audio.output" vaut "pipewire"
		Et la clé "<cle>" vaut "factice"
		Quand je charge la configuration
		Alors la configuration est chargée sans erreur
		Et l'antenne joue sur la sortie « <sortie> », <peripherique>
		Et la pré-écoute est <preecoute>

		Exemples:
			| cle               | sortie   | peripherique                   | preecoute  |
			| audio.device | factice  | sans périphérique              | active     |
			| audio.preview    | pipewire | sur le périphérique « antenne » | désactivée |

	Scénario: L'antenne et la pré-écoute ne sont pas toutes deux sur la sortie factice
		Étant donné une configuration valide où la clé "audio.device" vaut "factice"
		Et la clé "audio.preview" vaut "factice"
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "audio.preview"

	# ─── Crossfades (https://github.com/dascritch/machincast/issues/145) ─────────────────────────

	Scénario: Sans section [crossfades], les crossfades se règlent au dixième de seconde, jusqu'à 10 secondes, sans défaut
		Étant donné une configuration valide sans section "crossfades"
		Quand je charge la configuration
		Alors les crossfades se règlent au dixième de seconde, jusqu'à 10 secondes
		Et les crossfades n'ont pas de durée par défaut
		Et le fade-in se termine au début détecté, et le fade-out commence à la fin détectée

	Scénario: La section [crossfades] donne la granularité, le maximum et les durées par défaut
		Étant donné une configuration valide où la clé "crossfades.granularity" vaut "seconde"
		Et la clé "crossfades.maximum" vaut 8
		Et la clé "crossfades.start" vaut 1.5
		Et la clé "crossfades.end" vaut 3
		Quand je charge la configuration
		Alors les crossfades se règlent à la seconde, jusqu'à 8 secondes
		Et les crossfades durent par défaut 1,5 seconde au début et 3 secondes à la fin

	Scénario: Les durées par défaut vont de 0 seconde jusqu'au maximum compris
		Étant donné une configuration valide où la clé "crossfades.start" vaut 0
		Et la clé "crossfades.end" vaut 5
		Quand je charge la configuration
		Alors les crossfades durent par défaut 0 seconde au début et 5 secondes à la fin

	Scénario: La section [crossfades] donne la position des fondus par rapport aux silences détectés
		https://github.com/dascritch/machincast/issues/234

		Étant donné une configuration valide où la clé "crossfades.fade_in_position" vaut "en_cours"
		Et la clé "crossfades.fade_out_position" vaut "termine"
		Quand je charge la configuration
		Alors le fade-in est en cours au début détecté, et le fade-out se termine à la fin détectée

	Plan du scénario: Des réglages de crossfade invalides sont refusés
		Étant donné une configuration valide où la clé "<cle>" vaut <valeur>
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "<cle>"
		Et le message mentionne "<attendu>"

		Exemples:
			| cle                    | valeur     | attendu                    |
			| crossfades.granularity | "centieme" | second, tenth              |
			| crossfades.maximum     | 0          | strictement positif        |
			| crossfades.maximum     | "5"        | nombre                     |
			| crossfades.start       | -1         | positif ou nul             |
			| crossfades.end         | 11         | au plus crossfades.maximum |
			| crossfades.start       | true       | nombre                     |
			| crossfades.fade_in_position | "avant" | starts, ongoing, ends       |
			| crossfades.fade_out_position | 2       | texte                       |

	# ─── Détection de silence (https://github.com/dascritch/machincast/issues/146) ─────────────────

	# ─── Péremption (https://github.com/dascritch/machincast/issues/268) ───

	Scénario: Sans clé database.retention, la durée de péremption est de 60 jours
		Étant donné une configuration valide où la clé "database.retention" est absente
		Quand je charge la configuration
		Alors la durée de péremption est de 60 jours

	Plan du scénario: La clé database.retention donne la durée de péremption, en jours entiers, d'un jour au moins
		Étant donné une configuration valide où la clé "database.retention" vaut <valeur>
		Quand je charge la configuration
		Alors la durée de péremption est de <valeur> jours

		Exemples:
			| valeur |
			| 1      |
			| 365    |

	Plan du scénario: Une durée de péremption invalide est refusée
		Étant donné une configuration valide où la clé "database.retention" vaut <valeur>
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "database.retention"
		Et le message mentionne "nombre entier de jours, 1 au moins"

		Exemples:
			| valeur |
			| 0      |
			| -5     |
			| 1.5    |
			| "60"   |
			| true   |

	Scénario: Sans section [silences], le seuil de silence est de -40 dB
		Étant donné une configuration valide sans section "silences"
		Quand je charge la configuration
		Alors le seuil de silence est de -40 dB

	Plan du scénario: La clé silences.threshold donne le seuil de silence, de -100 dB compris à 0 dB exclu
		Étant donné une configuration valide où la clé "silences.threshold" vaut <valeur>
		Quand je charge la configuration
		Alors le seuil de silence est de <seuil> dB

		Exemples:
			| valeur | seuil |
			| -60    | -60   |
			| -48.5  | -48,5 |
			| -100   | -100  |
			| -0.1   | -0,1  |

	Plan du scénario: Un seuil de silence invalide est refusé
		Étant donné une configuration valide où la clé "silences.threshold" vaut <valeur>
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "silences.threshold"
		Et le message mentionne "<attendu>"

		Exemples:
			| valeur | attendu                          |
			| 0      | de -100 dB compris à 0 dB exclu  |
			| 3      | de -100 dB compris à 0 dB exclu  |
			| -101   | de -100 dB compris à 0 dB exclu  |
			| "-40"  | nombre                           |
			| true   | nombre                           |

	Scénario: Une clé inconnue de la section [silences] est refusée
		Étant donné une configuration valide où la clé "silences.duree" vaut 1
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "silences.duree"

	Scénario: Sans section [dead_air], un blanc de 10 secondes sous -90 dB dans un sonore est noté seulement
		https://github.com/dascritch/machincast/issues/122 : un blanc dans un sonore, à l'antenne, n'est pas un silence,
		qui borne un fichier (https://github.com/dascritch/machincast/issues/291).

		Étant donné une configuration valide sans section "blanc_antenne"
		Quand je charge la configuration
		Alors un blanc dans un sonore dure au moins 10 secondes sous -90 dB, et il est noté seulement

	Scénario: La section [dead_air] donne la durée et le niveau d'un blanc, et le passage au secours
		Étant donné une configuration valide où la clé "dead_air.duration" vaut 4.5
		Et la clé "dead_air.threshold" vaut -70
		Et la clé "dead_air.fallback" vaut true
		Quand je charge la configuration
		Alors un blanc dans un sonore dure au moins 4,5 secondes sous -70 dB, et il fait passer au secours

	Plan du scénario: La durée d'un blanc va de 1 à 300 secondes comprises, son niveau de -100 dB compris à 0 dB exclu
		Étant donné une configuration valide où la clé "dead_air.duration" vaut <duree>
		Et la clé "dead_air.threshold" vaut <seuil>
		Quand je charge la configuration
		Alors un blanc dans un sonore dure au moins <secondes> secondes sous <db> dB, et il est noté seulement

		Exemples:
			| duree | seuil | secondes | db    |
			| 1     | -100  | 1        | -100  |
			| 300   | -0.1  | 300      | -0,1  |

	Plan du scénario: Une clé de la section [dead_air] invalide est refusée
		Étant donné une configuration valide où la clé "dead_air.<cle>" vaut <valeur>
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "dead_air.<cle>"
		Et le message mentionne "<attendu>"

		Exemples:
			| cle       | valeur | attendu                          |
			| duration  | 0.5    | de 1 à 300 secondes comprises    |
			| duration  | 301    | de 1 à 300 secondes comprises    |
			| duration  | "10"   | nombre                           |
			| threshold | 0      | de -100 dB compris à 0 dB exclu  |
			| threshold | -101   | de -100 dB compris à 0 dB exclu  |
			| threshold | true   | nombre                           |
			| fallback  | 1      | booléen                          |
			| volume    | 1      | dead_air.volume                  |

	Plan du scénario: Une ancienne section française est refusée, en nommant son nom anglais
		https://github.com/dascritch/machincast/issues/357 : sections et clés sont en anglais, sans compatibilité ; les
		installations se refont de zéro. [blancs] était l'ancien nom de [silences] (https://github.com/dascritch/machincast/issues/291).

		Étant donné une configuration valide où la clé "<ancienne>.<cle>" vaut 1
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "section [<ancienne>] inconnue : son nom est désormais [<nouvelle>]"

		Exemples:
			| ancienne      | cle        | nouvelle |
			| base          | peremption | database |
			| sorties       | csv        | outputs  |
			| metadonnees   | masquer    | metadata |
			| lecture       | socket     | player   |
			| blanc_antenne | duree      | dead_air |
			| blancs        | seuil      | silences |

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
			| Machin_player    |
			| Machin_indexer |
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
			| Machin_player    |
			| Machin_indexer |
			| Machin_interface  |

	Scénario: Un binaire refuse une configuration invalide
		Étant donné un chemin de configuration qui n'existe pas
		Quand je lance "Machin_player" avec ce chemin de configuration
		Alors le binaire s'arrête avec le code 2
		Et l'erreur affichée mentionne le chemin du fichier

	# ─── Interface (https://github.com/dascritch/machincast/issues/191) ─────────────────

	Scénario: Sans section [interface], le voyant « Saturation » de l'onglet Antenne est affiché
		Étant donné une configuration valide sans section "interface"
		Quand je charge la configuration
		Alors le voyant « Saturation » de l'onglet Antenne est affiché

	Plan du scénario: La clé interface.clipping affiche ou cache le voyant « Saturation » de l'onglet Antenne
		Étant donné une configuration valide où la clé "interface.clipping" vaut <valeur>
		Quand je charge la configuration
		Alors le voyant « Saturation » de l'onglet Antenne est <etat>

		Exemples:
			| valeur | etat    |
			| true   | affiché |
			| false  | caché   |

	Plan du scénario: Une valeur de interface.clipping qui n'est pas un booléen est refusée, comme une clé inconnue
		Étant donné une configuration valide où la clé "<cle>" vaut <valeur>
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "<cle>"

		Exemples:
			| cle                  | valeur |
			| interface.clipping | "oui"  |
			| interface.clipping | 1      |
			| interface.suggestions | "non" |
			| interface.blanc      | true   |

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

	Scénario: Sans clé interface.icon, l'interface a l'icône de MachinCast
		Étant donné une configuration valide sans section "interface"
		Quand je charge la configuration
		Alors l'icône de l'interface est celle de MachinCast

	Plan du scénario: La clé interface.icon désigne une image SVG, PNG ou JPEG, relative au fichier de configuration
		Étant donné une configuration valide où la clé "interface.icon" vaut "<chemin>"
		Quand je charge la configuration
		Alors l'icône de l'interface est "<chemin>" à côté du fichier de configuration

		Exemples:
			| chemin           |
			| images/logo.png  |
			| logo.SVG         |
			| photos/radio.jpg |
			| radio.jpeg       |

	Plan du scénario: Une icône qui n'est pas une image SVG, PNG ou JPEG est refusée
		Étant donné une configuration valide où la clé "interface.icon" vaut <valeur>
		Quand je charge la configuration
		Alors le chargement échoue avec un message qui mentionne "interface.icon"

		Exemples:
			| valeur                |
			| "logo.gif"            |
			| "musique/jingle.mp3"  |
			| "logo"                |
			| true                  |
