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
			| aac    |
			| aiff   |

	# https://github.com/dascritch/machincast/issues/149 : chaque décodage gardait deux descripteurs ouverts. Passé la
	# limite du système (1024 par défaut), GStreamer ne pouvait plus attendre ses messages, et tous les fichiers qui
	# suivaient, sains compris, étaient déclarés illisibles.
	Plan du scénario: Une longue vérification ne garde aucun descripteur de fichier ouvert
		Étant donné un fichier <format> sain
		Et un processus limité à 40 descripteurs de fichier de plus que ceux déjà ouverts
		Quand je vérifie ce fichier 60 fois de suite
		Alors le fichier est sain à chaque vérification
		Et autant de descripteurs de fichier sont ouverts qu'avant les vérifications

		Exemples:
			| format |
			| ogg    |
			| flac   |

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
			| aac    | endommagé |

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
		Et un sonore à l'état « actif » pour ce fichier
		Quand l'indexeur fait un audit complet
		Alors le sonore est à l'état « actif »
		Et sa durée en base est de 1 seconde à 0,05 seconde près
		Et la date de modification et la taille du fichier sont enregistrées
		Et rien n'est signalé sur la sortie d'erreur
		Et le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Plan du scénario: L'indexeur ne change l'état que des sonores en aperçu, actifs ou erronés
		Étant donné un fichier <fichier>
		Et un sonore à l'état « <avant> » pour ce fichier
		Quand l'indexeur fait un audit complet
		Alors le sonore est à l'état « <apres> »

		Exemples:
			| fichier       | avant     | apres     |
			| mp3 sain      | apercu    | actif     |
			| mp3 endommagé | apercu    | errone    |
			| introuvable   | apercu    | supprime  |
			| mp3 sain      | actif     | actif     |
			| mp3 endommagé | actif     | errone    |
			| introuvable   | actif     | supprime  |
			| mp3 sain      | errone    | actif     |
			| mp3 endommagé | errone    | errone    |
			| introuvable   | errone    | supprime  |
			| mp3 sain      | supprime  | supprime  |
			| mp3 sain      | desactive | desactive |
			| mp3 endommagé | desactive | desactive |
			| introuvable   | desactive | desactive |
			| mp3 sain      | expire    | expire    |
			| mp3 endommagé | expire    | expire    |

	Plan du scénario: Un fichier défectueux est signalé par son chemin, avec la conséquence pour son sonore
		Étant donné un fichier <fichier>
		Et un sonore à l'état « <avant> » pour ce fichier
		Quand l'indexeur fait un audit complet
		Alors la sortie d'erreur signale ce fichier comme « <verdict> », avec « <consequence> »

		Exemples:
			| fichier       | avant     | verdict     | consequence             |
			| mp3 endommagé | actif     | endommagé   | sonore passé erroné     |
			| introuvable   | actif     | introuvable | sonore passé supprimé   |
			| mp3 endommagé | errone    | endommagé   | sonore toujours erroné  |
			| mp3 endommagé | desactive | endommagé   | état désactivé conservé |
			| mp3 endommagé | expire    | endommagé   | état expiré conservé    |

	Scénario: Le bilan compte les sonores passés erronés, supprimés et rétablis
		Étant donné un fichier mp3 endommagé
		Et un sonore à l'état « actif » pour ce fichier
		Et un deuxième fichier wav sain, dont le sonore est à l'état « errone »
		Quand l'indexeur fait un audit complet
		Alors le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement, 0 retrait ; 2 sonores vérifiés ; 1 erroné, 0 non supporté, 0 supprimé, 1 rétabli, 0 sorti d'aperçu »

	Scénario: Une durée saisie à la main n'est pas remplacée
		Étant donné un fichier wav sain
		Et un sonore à l'état « actif » pour ce fichier, dont la durée a été saisie à la main à 99 secondes
		Quand l'indexeur fait un audit complet
		Alors sa durée en base est de 99 secondes à 0,1 seconde près
		Et la date de modification et la taille du fichier sont enregistrées

	# ─── Détection de blanc (https://github.com/dascritch/machincast/issues/146) ───
	# blancs.flac : une demi-seconde de silence, une seconde à -6 dB, un quart de seconde à -50,5 dB, puis un quart de
	# seconde de silence (tests.sons.BLANCS). La fin détectée se compte depuis la fin du fichier.

	Plan du scénario: Le décodage mesure les blancs au début et à la fin d'un fichier, d'après le seuil en crête
		Étant donné un fichier flac avec des blancs
		Quand je vérifie ce fichier en détectant les blancs au seuil de <seuil> dB
		Alors le fichier est sain
		Et son début détecté est de <debut> seconde à 0,01 seconde près
		Et sa fin détectée est de <fin> seconde à 0,01 seconde près

		Exemples:
			| seuil | debut | fin  |
			| -40   | 0,5   | 0,5  |
			| -60   | 0,5   | 0,25 |
			| -10   | 0,5   | 0,5  |

	Scénario: Un fichier qui n'atteint jamais le seuil n'a aucun blanc détecté
		Étant donné un fichier flac sain
		Quand je vérifie ce fichier en détectant les blancs au seuil de -1 dB
		Alors le fichier est sain
		Et aucun blanc n'est détecté

	Scénario: Sans seuil, le décodage ne mesure pas les blancs
		Étant donné un fichier flac avec des blancs
		Quand je vérifie ce fichier
		Alors le fichier est sain
		Et les blancs n'ont pas été mesurés

	Scénario: L'audit complet enregistre les blancs détectés au seuil de la configuration
		Étant donné un fichier flac avec des blancs
		Et un sonore à l'état « actif » pour ce fichier
		Et un seuil de blanc de -60 dB dans la configuration
		Quand l'indexeur fait un audit complet
		Alors en base, le début détecté du sonore est de 0,5 seconde et sa fin détectée de 0,25 seconde, à 0,01 seconde près

	Scénario: L'audit complet d'un seul sonore enregistre ses blancs, au seuil de -40 dB par défaut
		Étant donné un fichier flac avec des blancs
		Et un sonore à l'état « actif » pour ce fichier
		Quand l'indexeur fait l'audit complet de ce seul sonore
		Alors en base, le début détecté du sonore est de 0,5 seconde et sa fin détectée de 0,5 seconde, à 0,01 seconde près

	Scénario: L'indexation rapide ne détecte pas les blancs
		Étant donné un fichier flac avec des blancs
		Et un sonore à l'état « apercu » pour ce fichier
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « actif »
		Et en base, le sonore n'a ni début ni fin détectés

	Scénario: Un audit complet efface les blancs d'un fichier qui n'atteint plus le seuil
		Étant donné un fichier flac sain
		Et un sonore à l'état « actif » pour ce fichier, avec 1 seconde de début et de fin détectés
		Et un seuil de blanc de -1 dB dans la configuration
		Quand l'indexeur fait un audit complet
		Alors en base, le sonore n'a ni début ni fin détectés

	Scénario: Un début et une fin détectés saisis à la main ne sont pas remplacés
		Étant donné un fichier flac avec des blancs
		Et un sonore à l'état « actif » pour ce fichier, dont le début et la fin détectés ont été saisis à la main à 0,1 seconde
		Quand l'indexeur fait un audit complet
		Alors en base, le début détecté du sonore est de 0,1 seconde et sa fin détectée de 0,1 seconde, à 0,01 seconde près

	Scénario: Les blancs d'un fichier défectueux ne sont pas touchés
		Étant donné un fichier mp3 endommagé
		Et un sonore à l'état « actif » pour ce fichier, avec 1 seconde de début et de fin détectés
		Quand l'indexeur fait un audit complet
		Alors en base, le début détecté du sonore est de 1 seconde et sa fin détectée de 1 seconde, à 0,01 seconde près

	Scénario: Les streams ne sont jamais vérifiés
		Étant donné un stream enregistré
		Quand l'indexeur fait un audit complet
		Alors le stream n'a pas été modifié
		Et le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement, 0 retrait ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	# ─── Exécutable ────────────────────────────────────────────

	Scénario: Machin_indexation signale une base injoignable
		Quand je lance "Machin_indexation" avec une configuration dont la socket PostgreSQL n'existe pas
		Alors la commande se termine avec le code 1
		Et la sortie d'erreur de la commande mentionne « base de données injoignable »
