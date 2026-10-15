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
			| audio/x-aiff                               | aiff   | gstreamer1.0-plugins-bad  |
			| audio/mpeg, mpegversion=(int)1, layer=(int)3 | mp3    | gstreamer1.0-plugins-good |
			| audio/x-vorbis                             | ogg    | gstreamer1.0-plugins-base |
			| audio/mpeg, mpegversion=(int)4             | m4a    | gstreamer1.0-plugins-bad  |
			| audio/mpeg, mpegversion=(int)4, stream-format=(string)adts | aac | gstreamer1.0-plugins-good |

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
		Quand je lance « python -m machincast.installation bases » avec la configuration de test
		Alors la commande se termine sans erreur
		Et elle affiche la socket, la base de production puis la base de test de cette configuration

	Scénario: La vérification en ligne de commande réussit quand rien ne manque
		Quand je lance « python -m machincast.installation verifier » avec la configuration de test
		Alors la commande se termine sans erreur
		Et sa sortie annonce « décodeurs, source des streams et sortie audio disponibles »

	Scénario: L'application du schéma signale une base injoignable
		Quand je lance « python -m machincast.installation migrer » avec une configuration dont la socket n'existe pas
		Alors la commande se termine avec le code 1
		Et sa sortie d'erreur mentionne « base de données injoignable »
