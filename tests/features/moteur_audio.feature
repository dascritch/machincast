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

	Plan du scénario: Le sonore suivant démarre au point d'enchaînement
		Alors un sonore de <duree> secondes, avec <fin> secondes de crossfade de fin, laisse démarrer le suivant après <enchainement> secondes

		Exemples:
			| duree | fin | enchainement |
			| 60    | 0   | 60           |
			| 60    | 4   | 56           |
			| 3     | 5   | 0            |

	# ─── Lecture ───────────────────────────────────────────────

	Scénario: Un sonore joue sur la sortie de la configuration jusqu'au bout
		Étant donné un moteur audio sur la sortie de la configuration de test, au plus vite
		Quand il joue le fichier de test « sain.flac »
		Et j'attends la fin de ses voies
		Alors la voie de « sain.flac » est finie
		Et elle a joué sur l'élément GStreamer « fakesink »

	Plan du scénario: Chaque format de la spécification est joué
		Étant donné un moteur audio sur la sortie de la configuration de test, au plus vite
		Quand il joue le fichier de test « sain.<format> »
		Et j'attends la fin de ses voies
		Alors la voie de « sain.<format> » est finie

		Exemples:
			| format |
			| mp3    |
			| m4a    |
			| aac    |
			| ogg    |
			| wav    |
			| aiff   |

	Scénario: Deux sonores se superposent pendant un crossfade
		Étant donné un moteur audio sur la sortie de la configuration de test, en temps réel
		Quand il joue le fichier de test « sain.flac »
		Et il joue le fichier de test « sain.ogg »
		Alors 2 voies sont en cours
		Quand j'attends la fin de ses voies
		Alors la voie de « sain.flac » est finie
		Et la voie de « sain.ogg » est finie

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
