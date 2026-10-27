# language: fr
Fonctionnalité: Moteur audio GStreamer avec crossfade
	En tant que technicien d'antenne,
	je veux que le binaire joue les sonores sur la sortie configurée, avec les crossfades de chaque sonore,
	afin que les enchaînements soient propres à l'antenne.

	https://github.com/dascritch/machincast/issues/15 — spec § 5.1. Chaque sonore joue dans sa propre voie, sur la
	sortie de la configuration : deux voies se superposent pendant un crossfade. Les scénarios utilisent la sortie
	factice, qui ne joue aucun son : en temps réel quand le temps compte, le plus vite possible sinon.
	Crossfade de fin : le sonore suivant démarre autant avant la fin, et celui-ci s'éteint pendant ce temps.
	Crossfade de début : le sonore monte progressivement pendant ce temps.
	Les deux sonores ne se superposent que si le sortant a un crossfade de fin et l'entrant un crossfade de début :
	sinon le sortant joue jusqu'au bout à plein volume, et l'entrant démarre ensuite à plein volume.

	# ─── Enveloppe et enchaînement ─────────────────────────────

	Plan du scénario: Le volume d'un sonore suit ses crossfades de début et de fin
		Étant donné une voie pour un sonore de 60 secondes, avec <debut> secondes de crossfade de début et <fin> de fin
		Alors à <instant> secondes, son volume est de <volume>

		Exemples:
			| debut | fin | instant | volume |
			| 0     | 0   | 0       | 1      |
			| 0     | 0   | 60      | 1      |
			| 2     | 0   | 0       | 0      |
			| 2     | 0   | 1       | 0,5    |
			| 2     | 0   | 2       | 1      |
			| 2     | 0   | 59      | 1      |
			| 0     | 4   | 56      | 1      |
			| 0     | 4   | 58      | 0,5    |
			| 0     | 4   | 60      | 0      |
			| 2     | 4   | 30      | 1      |

	Plan du scénario: Deux sonores ne se superposent que si le sortant a un crossfade de fin et l'entrant un crossfade de début
		Alors après un sonore de <duree> secondes avec <fin> secondes de crossfade de fin, un sonore avec <debut> secondes de crossfade de début démarre après <enchainement> secondes, <fondu>

		Exemples:
			| duree | fin | debut | enchainement | fondu                  |
			| 60    | 4   | 2     | 56           | avec fondu d'entrée    |
			| 60    | 4   | 0     | 60           | sans fondu d'entrée    |
			| 60    | 0   | 2     | 60           | sans fondu d'entrée    |
			| 60    | 0   | 0     | 60           | sans fondu d'entrée    |
			| 3     | 5   | 2     | 0            | avec fondu d'entrée    |

	Scénario: Sans superposition, le sonore sortant joue jusqu'au bout à plein volume
		Étant donné une voie pour un sonore de 60 secondes, avec 0 secondes de crossfade de début et 4 de fin
		Quand le sonore suivant n'a pas de crossfade de début
		Alors à 58 secondes, son volume est de 1
		Et à 60 secondes, son volume est de 1

	# ─── Sonore rogné par la détection de blanc (https://github.com/dascritch/machincast/issues/146) ───
	# Les instants et la position d'une voie se comptent depuis son début détecté, pas depuis le début du fichier.

	Plan du scénario: Le volume d'un sonore rogné suit ses crossfades à partir de son début détecté
		Étant donné une voie pour un sonore de 60 secondes commencé à 5 secondes du début du fichier, avec <debut> secondes de crossfade de début et <fin> de fin
		Alors à <instant> secondes, son volume est de <volume>

		Exemples:
			| debut | fin | instant | volume |
			| 2     | 0   | 0       | 0      |
			| 2     | 0   | 1       | 0,5    |
			| 2     | 0   | 2       | 1      |
			| 0     | 4   | 58      | 0,5    |
			| 0     | 4   | 60      | 0      |

	Scénario: Un sonore rogné joue de son début détecté à sa fin détectée
		Étant donné un moteur audio sur la sortie de la configuration de test, au plus vite
		Quand il joue le fichier de test « blancs.flac » de 0,5 à 1,5 seconde du fichier
		Et j'attends la fin de ses voies
		Alors la voie de « blancs.flac » est finie
		Et elle s'est arrêtée à 1,5 seconde du fichier, à 0,05 seconde près, après avoir joué 1 seconde

	# ─── Fondus qui débordent du fichier (https://github.com/dascritch/machincast/issues/234) ───
	# Un fondu placé par rapport aux blancs détectés peut commencer avant le début du fichier, ou finir après sa fin :
	# la voie part du volume où en est le fade-in, et s'arrête au volume où en est le fade-out.

	Plan du scénario: Un fondu qui déborde du fichier part, ou s'arrête, au volume où il en est
		Étant donné une voie pour un sonore de 10 secondes, avec 1 seconde de fade-in depuis le volume 0,75 et 6 de fade-out jusqu'au volume 0,25
		Alors à <instant> secondes, son volume est de <volume>

		Exemples:
			| instant | volume |
			| 0       | 0,75   |
			| 0,5     | 0,875  |
			| 1       | 1      |
			| 4       | 1      |
			| 7       | 0,625  |
			| 10      | 0,25   |

	Scénario: Sans superposition, un sonore qui part d'un fade-in entamé joue jusqu'au bout à plein volume, sans s'éteindre
		Étant donné une voie pour un sonore de 10 secondes, avec 1 seconde de fade-in depuis le volume 0,75 et 6 de fade-out jusqu'au volume 0,25
		Quand le sonore suivant n'a pas de crossfade de début
		Alors à 0 secondes, son volume est de 0,75
		Et à 10 secondes, son volume est de 1

	# ─── Fondus d'un stream (https://github.com/dascritch/machincast/issues/16) ───

	Scénario: Une voie muette reste silencieuse, puis monte en fondu
		Étant donné une voie muette, pour un stream
		Alors à 30 secondes, son volume est de 0
		Quand elle monte à plein volume en 2 secondes
		Alors à 0 secondes, son volume est de 0
		Et à 1 secondes, son volume est de 0,5
		Et à 2 secondes, son volume est de 1
		Et à 30 secondes, son volume est de 1

	Scénario: Une voie s'éteint en fondu à partir de maintenant
		Étant donné une voie pour un sonore de 60 secondes, avec 0 secondes de crossfade de début et 0 de fin
		Quand elle s'éteint en 4 secondes
		Alors à 2 secondes, son volume est de 0,5
		Et à 4 secondes, son volume est de 0
		Et elle s'arrêtera d'elle-même à 4 secondes

	# ─── Lecture ───────────────────────────────────────────────

	Scénario: Un sonore joue sur la sortie de la configuration jusqu'au bout
		Étant donné un moteur audio sur la sortie de la configuration de test, au plus vite
		Quand il joue le fichier de test « sain.flac »
		Et j'attends la fin de ses voies
		Alors la voie de « sain.flac » est finie
		Et elle a joué sur l'élément GStreamer « fakesink »
		Et elle a été lue par l'élément GStreamer « playbin3 »

	Plan du scénario: Chaque format de la spécification est joué
		Étant donné un moteur audio sur la sortie de la configuration de test, au plus vite
		Quand il joue le fichier de test « sain.<format> »
		Et j'attends la fin de ses voies
		Alors la voie de « sain.<format> » est finie

		# L'AIFF n'est plus un format de la spécification : GStreamer en bloque parfois le démarrage
		# (https://github.com/dascritch/machincast/issues/284).
		Exemples:
			| format |
			| mp3    |
			| m4a    |
			| aac    |
			| ogg    |
			| wav    |

	Scénario: Une voie qui ne démarre pas est bloquée passé le délai de démarrage ; une voie qui joue ne l'est jamais
		https://github.com/dascritch/machincast/issues/281 : playbin se bloquait parfois au démarrage
		d'un AIFF, sans erreur ni son. Le blocage est imité : la sortie de la voie de « sain.flac » ne reçoit jamais de
		son. L'horloge du moteur est celle du scénario.

		Étant donné un moteur audio sur la sortie de la configuration de test, en temps réel, à l'horloge du scénario
		Quand il joue le fichier de test « sain.flac », dont la sortie ne reçoit jamais de son
		Et il joue le fichier de test « sain.mp3 »
		Et le son de « sain.mp3 » avance
		Et 2,9 secondes passent à l'horloge du moteur
		Alors aucune voie n'est bloquée
		Quand 0,2 seconde passent à l'horloge du moteur
		Alors seule la voie de « sain.flac » est bloquée

	Scénario: Deux sonores se superposent pendant un crossfade
		Étant donné un moteur audio sur la sortie de la configuration de test, en temps réel
		Quand il joue le fichier de test « sain.flac »
		Et il joue le fichier de test « sain.ogg »
		Alors 2 voies sont en cours
		Quand j'attends la fin de ses voies
		Alors la voie de « sain.flac » est finie
		Et la voie de « sain.ogg » est finie

	Scénario: Une voie éteinte en fondu s'arrête d'elle-même à la fin du fondu
		Étant donné un moteur audio sur la sortie de la configuration de test, en temps réel
		Quand il joue le fichier de test « sain.flac »
		Et 200 millisecondes passent
		Et la voie de « sain.flac » s'éteint en 300 millisecondes
		Et j'attends la fin de ses voies
		Alors la voie de « sain.flac » est finie
		Et elle a fini moins de 800 millisecondes après son démarrage

	Scénario: La coupure nette arrête aussitôt tous les sonores en cours
		Étant donné un moteur audio sur la sortie de la configuration de test, en temps réel
		Quand il joue le fichier de test « sain.flac »
		Et il joue le fichier de test « sain.ogg »
		Et 200 millisecondes passent
		Et il coupe net
		Alors aucune voie n'est en cours
		Et la voie de « sain.flac » est coupée avant 500 millisecondes
		Et la voie de « sain.ogg » est coupée avant 500 millisecondes

	Scénario: Un fichier illisible est signalé, sans empêcher la lecture des suivants
		Étant donné un moteur audio sur la sortie de la configuration de test, au plus vite
		Quand il joue un fichier qui contient du texte
		Et il joue le fichier de test « sain.flac »
		Et j'attends la fin de ses voies
		Alors la voie du fichier texte est en erreur, avec le motif de GStreamer
		Et la voie de « sain.flac » est finie

	# ─── Vérification avant lecture ────────────────────────────

	Scénario: Un fichier inchangé depuis l'indexation est joué sans rien consigner
		Étant donné un sonore indexé pour le fichier de test « sain.flac »
		Quand le binaire lecture vérifie ce fichier avant de le jouer
		Alors le fichier est prêt à être joué
		Et le log ne contient rien

	Plan du scénario: Un fichier modifié depuis l'indexation est joué, et l'écart consigné dans le log
		Étant donné un sonore indexé pour le fichier de test « sain.flac »
		Et <changement>
		Quand le binaire lecture vérifie ce fichier avant de le jouer
		Alors le fichier est prêt à être joué
		Et le log contient une alerte « fichier modifié » pour ce sonore, qui mentionne « <mention> »

		Exemples:
			| changement                                             | mention |
			| la date de modification du fichier a changé            | date    |
			| la taille du fichier a changé                          | taille  |

	Scénario: Un fichier disparu n'est pas joué, et l'incident est consigné dans le log
		Étant donné un sonore indexé pour le fichier de test « sain.flac »
		Et le fichier a été supprimé
		Quand le binaire lecture vérifie ce fichier avant de le jouer
		Alors le fichier n'est pas joué
		Et le log contient un incident « fichier introuvable » pour ce sonore
