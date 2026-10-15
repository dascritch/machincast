# language: fr
Fonctionnalité: Vérification d'un fichier par décodage complet
	En tant que technicien d'antenne,
	je veux que chaque fichier soit entièrement décodé avant d'être déclaré jouable,
	afin qu'un fichier endommagé ne passe jamais à l'antenne.

	Les fichiers sonores de test durent une seconde (tests/fichiers-sonores) ; chaque scénario en modifie une copie.

	# ─── Décodage d'un fichier ─────────────────────────────────

	Plan du scénario: Un fichier sain est décodé en entier et sa durée mesurée
		Étant donné un fichier <format> sain
		Quand je vérifie ce fichier
		Alors le fichier est sain
		Et sa durée mesurée est de 1 seconde à 0,05 seconde près

		Exemples:
			| format |
			| wav    |
			| flac   |
			| ogg    |
			| mp3    |
			| m4a    |
			| aiff   |

	Scénario: Un fichier qui n'est pas du son est illisible
		Étant donné un fichier "faux.mp3" qui contient du texte
		Quand je vérifie ce fichier
		Alors le fichier est déclaré illisible

	Scénario: Un fichier vide est illisible
		Étant donné un fichier "vide.flac" vide
		Quand je vérifie ce fichier
		Alors le fichier est déclaré illisible

	Plan du scénario: Un fichier tronqué est détecté quand son format le permet
		Étant donné un fichier <format> sain
		Et ce fichier tronqué de moitié
		Quand je vérifie ce fichier
		Alors le fichier est déclaré <verdict>

		Exemples:
			| format | verdict   |
			| flac   | endommagé |
			| aiff   | endommagé |
			| ogg    | illisible |
			| m4a    | illisible |

	Plan du scénario: Des données corrompues en cours de fichier sont détectées quand son format le permet
		Étant donné un fichier <format> sain
		Et 1000 octets corrompus au tiers de ce fichier
		Quand je vérifie ce fichier
		Alors le fichier est déclaré <verdict>

		Exemples:
			| format | verdict   |
			| flac   | endommagé |
			| ogg    | illisible |
			| mp3    | endommagé |
			| m4a    | endommagé |

	Scénario: Un décodage qui n'avance plus est abandonné
		Étant donné un fichier WAV dont la lecture se bloque après son début
		Quand je vérifie ce fichier en abandonnant après 1 seconde sans progression
		Alors le fichier est déclaré illisible
		Et le problème signalé mentionne « bloqué »

	Scénario: Un décodage qui ne démarre pas est repris avant d'être déclaré bloqué
		Étant donné un fichier wav sain
		Et un décodage qui ne démarre pas aux 2 premières tentatives
		Quand je vérifie ce fichier
		Alors le fichier est sain
		Et le décodage a été tenté 3 fois

	Scénario: Un décodage qui ne démarre jamais est déclaré bloqué après trois tentatives
		Étant donné un fichier wav sain
		Et un décodage qui ne démarre jamais
		Quand je vérifie ce fichier
		Alors le fichier est déclaré illisible
		Et le problème signalé mentionne « bloqué au démarrage »
		Et le décodage a été tenté 3 fois

	Scénario: Un décodeur absent arrête la vérification au lieu de déclarer le fichier illisible
		Étant donné un fichier aiff sain
		Et le décodeur GStreamer de l'AIFF désactivé
		Quand je vérifie ce fichier
		Alors la vérification s'arrête en signalant un décodeur absent et le paquet à installer

	# ─── Vérification des sonores en base ──────────────────────

	Scénario: Un sonore sain reçoit sa durée, la date et la taille de son fichier
		Étant donné un fichier flac sain
		Et un sonore actif pour ce fichier
		Quand l'indexeur vérifie les sonores
		Alors le sonore est actif
		Et sa durée en base est de 1 seconde à 0,05 seconde près
		Et la date de modification et la taille du fichier sont enregistrées
		Et rien n'est signalé sur la sortie d'erreur
		Et le bilan indique « 1 sonore vérifié, 0 désactivé »

	Scénario: Un sonore dont le fichier est endommagé est désactivé et signalé
		Étant donné un fichier mp3 sain
		Et 1000 octets corrompus au tiers de ce fichier
		Et un sonore actif pour ce fichier
		Quand l'indexeur vérifie les sonores
		Alors le sonore est inactif
		Et la sortie d'erreur signale ce fichier comme « endommagé »
		Et le bilan indique « 1 sonore vérifié, 1 désactivé »

	Scénario: Un sonore dont le fichier est introuvable est désactivé et signalé
		Étant donné un fichier introuvable
		Et un sonore actif pour ce fichier
		Quand l'indexeur vérifie les sonores
		Alors le sonore est inactif
		Et la sortie d'erreur signale ce fichier comme « introuvable »

	Scénario: Un fichier endommagé désactive son sonore même si « actif » a été édité à la main
		Étant donné un fichier ogg sain
		Et 1000 octets corrompus au tiers de ce fichier
		Et un sonore actif pour ce fichier, dont le champ « actif » a été édité à la main
		Quand l'indexeur vérifie les sonores
		Alors le sonore est inactif

	Scénario: Une durée saisie à la main n'est pas remplacée
		Étant donné un fichier wav sain
		Et un sonore actif pour ce fichier, dont le champ « duree » a été édité à la main à 99 secondes
		Quand l'indexeur vérifie les sonores
		Alors sa durée en base est de 99 secondes à 0,1 seconde près
		Et la date de modification et la taille du fichier sont enregistrées

	Scénario: Un sonore inactif dont le fichier est sain reste inactif
		Étant donné un fichier wav sain
		Et un sonore inactif pour ce fichier
		Quand l'indexeur vérifie les sonores
		Alors le sonore est inactif
		Et sa durée en base est de 1 seconde à 0,05 seconde près

	Scénario: Les streams ne sont jamais vérifiés
		Étant donné un stream enregistré
		Quand l'indexeur vérifie les sonores
		Alors le stream n'a pas été modifié
		Et le bilan indique « 0 sonore vérifié, 0 désactivé »

	# ─── Exécutable ────────────────────────────────────────────

	Scénario: Machin_indexation signale une base injoignable
		Quand je lance "Machin_indexation" avec une configuration dont la socket PostgreSQL n'existe pas
		Alors la commande se termine avec le code 1
		Et la sortie d'erreur de la commande mentionne « base de données injoignable »
