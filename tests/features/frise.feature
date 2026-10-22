# language: fr
Fonctionnalité: Frise de la pré-écoute d'un fichier
	En tant que technicien radio,
	je veux voir dans la pré-écoute d'un fichier sa forme d'onde, ses blancs, ses crossfades et la partie jouée à
	l'antenne,
	afin de vérifier ses réglages et ses enchaînements sans le passer à l'antenne.

	https://github.com/dascritch/machincast/issues/224. La frise remplace la barre de position de la pré-écoute d'un
	fichier. Elle s'étend sur toute la durée du fichier : sa forme d'onde, ses blancs détectés (hachures pleines s'ils
	sont retirés à l'antenne, pâles s'ils y sont joués), ses crossfades (rampes posées sur la partie jouée) et la tête
	de lecture. La partie jouée suit la règle de la diffusion (https://github.com/dascritch/machincast/issues/146) : un
	côté sans blanc détecté n'est pas rogné, et des blancs qui ne laissent rien du sonore sont ignorés. Un crossfade non
	paramétré est celui des préférences, marqué « (défaut) ». La pré-écoute ne connaît pas la banque par laquelle
	passera le sonore : ses règles n'y figurent pas.

	Ces scénarios essaient la frise seule, sans base ni fichier ; ceux de preecoute.feature, dans la fenêtre.

	# ─── Partie jouée ──────────────────────────────────────────

	Plan du scénario: La partie jouée à l'antenne suit les blancs retirés, comme la diffusion
		Étant donné un fichier de <duree> s, aux blancs de <debut> au début et <fin> à la fin, <retires> à l'antenne, sans crossfade
		Alors la frise joue le fichier de <de> à <a> seconde

		Exemples:
			| duree | debut | fin   | retires | de  | a   |
			| 2     | 0,5 s | 0,5 s | retirés | 0,5 | 1,5 |
			| 2     | 0,5 s | 0,5 s | joués   | 0   | 2   |
			| 2     | 0,5 s | aucun | retirés | 0,5 | 2   |
			| 2     | aucun | aucun | retirés | 0   | 2   |
			| 2     | 1,2 s | 0,8 s | retirés | 0   | 2   |

	Scénario: Sous la frise, la partie jouée à l'antenne et sa durée
		Étant donné un fichier de 2 s, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, sans crossfade
		Alors la frise résume « Joué à l'antenne : 0:00,50 → 0:01,50 (0:01,00) »

	Scénario: Un fichier jamais audité le dit : ses blancs n'ont pas été mesurés
		Étant donné un fichier de 2 s jamais audité, sans crossfade
		Alors la frise résume « Joué à l'antenne : 0:00,00 → 0:02,00 (0:02,00) · blancs jamais mesurés »
		Et la frise ne montre aucune zone

	# ─── Zones ─────────────────────────────────────────────────

	Scénario: Des blancs retirés et des crossfades : hachures pleines, et fondus sur la partie jouée
		Étant donné un fichier de 2 s, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, aux crossfades de 0,2 s au début et 0,3 s à la fin
		Alors la frise montre les zones :
			| zone            | de   | à    | hachures | infobulle                                                                  |
			| blanc de début  | 0,00 | 0,50 | pleines  | Blanc de début : 0,50 s, retiré à l'antenne                                |
			| fondu d'entrée  | 0,50 | 0,70 | aucune   | Crossfade de début : 0,20 s, montée si le sonore précédent a un crossfade de fin |
			| fondu de sortie | 1,20 | 1,50 | aucune   | Crossfade de fin : 0,30 s                                                  |
			| blanc de fin    | 1,50 | 2,00 | pleines  | Blanc de fin : 0,50 s, retiré à l'antenne                                  |

	Scénario: Des blancs joués : hachures pâles, et fondus aux bouts du fichier
		Étant donné un fichier de 2 s, aux blancs de 0,5 s au début et 0,5 s à la fin, joués à l'antenne, aux crossfades de 0,2 s au début et 0,3 s à la fin
		Alors la frise montre les zones :
			| zone            | de   | à    | hachures | infobulle                                                                  |
			| blanc de début  | 0,00 | 0,50 | pâles    | Blanc de début : 0,50 s, joué à l'antenne                                  |
			| fondu d'entrée  | 0,00 | 0,20 | aucune   | Crossfade de début : 0,20 s, montée si le sonore précédent a un crossfade de fin |
			| fondu de sortie | 1,70 | 2,00 | aucune   | Crossfade de fin : 0,30 s                                                  |
			| blanc de fin    | 1,50 | 2,00 | pâles    | Blanc de fin : 0,50 s, joué à l'antenne                                    |

	Scénario: Un crossfade non paramétré est celui des préférences, marqué « (défaut) »
		Étant donné un fichier de 2 s, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, aux crossfades non paramétrés, par défaut de 0,4 s au début et absent à la fin
		Alors la frise montre les zones :
			| zone           | de   | à    | hachures | infobulle                                                                            |
			| blanc de début | 0,00 | 0,50 | pleines  | Blanc de début : 0,50 s, retiré à l'antenne                                          |
			| fondu d'entrée | 0,50 | 0,90 | aucune   | Crossfade de début : 0,40 s (défaut), montée si le sonore précédent a un crossfade de fin |
			| blanc de fin   | 1,50 | 2,00 | pleines  | Blanc de fin : 0,50 s, retiré à l'antenne                                            |

	Scénario: Hors des zones, l'infobulle donne l'instant du fichier sous la souris
		Étant donné un fichier de 2 s, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, sans crossfade
		Et la frise large de 400 points
		Alors l'infobulle de la frise à 200 points est « 0:01,00 »
		Et l'infobulle de la frise à 50 points est « Blanc de début : 0,50 s, retiré à l'antenne »

	# ─── Repères et volume ─────────────────────────────────────

	Plan du scénario: « Début joué » va au début de la partie jouée, « Fin jouée » quelques secondes avant le fondu de sortie
		Étant donné un fichier de <duree> s, aux blancs de 1 s au début et 2 s à la fin, retirés à l'antenne, aux crossfades de 0 s au début et 4 s à la fin
		Alors « Début joué » place la lecture à <debut> seconde, et « Fin jouée » à <fin> seconde

		Exemples:
			| duree | debut | fin |
			| 60    | 1     | 49  |
			| 8     | 1     | 1   |

	Plan du scénario: Écoutée comme à l'antenne, le volume suit les fondus de la partie jouée
		Étant donné un fichier de 2 s, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, aux crossfades de 0,2 s au début et 0,4 s à la fin
		Alors à <position> seconde, le volume de l'écoute comme à l'antenne est de <volume> %

		Exemples:
			| position | volume |
			| 0,25     | 0      |
			| 0,5      | 0      |
			| 0,6      | 50     |
			| 1        | 100    |
			| 1,3      | 50     |
			| 1,5      | 0      |
			| 1,8      | 0      |

	Plan du scénario: Écoutée comme à l'antenne, sans crossfade, le volume est plein dans la partie jouée, nul hors d'elle
		Étant donné un fichier de 2 s, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, sans crossfade
		Alors à <position> seconde, le volume de l'écoute comme à l'antenne est de <volume> %

		Exemples:
			| position | volume |
			| 0,25     | 0      |
			| 1        | 100    |
			| 1,8      | 0      |

	# ─── Souris et clavier ─────────────────────────────────────

	Scénario: Un clic sur la frise place la lecture là où il tombe
		Étant donné un fichier de 2 s, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, sans crossfade
		Et la frise large de 400 points
		Quand je clique sur la frise à 100 points
		Alors la frise a demandé la position 0,5 seconde

	Scénario: Glisser sur la frise ne place la lecture qu'au relâchement
		Étant donné un fichier de 2 s, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, sans crossfade
		Et la frise large de 400 points
		Quand j'appuie sur la frise à 100 points, puis glisse jusqu'à 300 points
		Alors la frise n'a demandé aucune position
		Et la tête de lecture de la frise est à 1,5 seconde
		Quand je relâche la frise
		Alors la frise a demandé la position 1,5 seconde

	Scénario: Au clavier, les flèches déplacent la lecture d'une seconde
		Étant donné un fichier de 60 s, aux blancs de 1 s au début et 2 s à la fin, retirés à l'antenne, sans crossfade
		Et la tête de lecture de la frise à 10 secondes
		Quand je tape la flèche droite sur la frise
		Alors la frise a demandé la position 11 secondes
		Quand je tape la flèche gauche sur la frise
		Alors la frise a demandé la position 10 secondes

	# ─── Forme d'onde ──────────────────────────────────────────

	Scénario: La forme d'onde du fichier se calcule en tâche de fond, sans bloquer l'interface
		Étant donné la forme d'onde du fichier de test « blancs.flac », de 2 secondes, en cours de calcul
		Alors l'interface a rendu la main avant la fin du calcul
		Et la forme d'onde est bientôt complète
		Et la forme d'onde est silencieuse de 0 à 0,45 seconde, et de 1,8 à 2 secondes
		Et la forme d'onde est sonore de 0,6 à 1,4 seconde, à mi-hauteur
		Et dessinée sur une frise de 400 points, la forme d'onde couvre chaque point de 0,6 à 1,4 seconde, sans trou

	Scénario: Un fichier illisible n'a pas de forme d'onde, et la frise le dit
		Étant donné la forme d'onde d'un fichier qui n'est pas un sonore, en cours de calcul
		Alors la forme d'onde est bientôt indisponible
		Et la frise de cette forme d'onde dit « Forme d'onde indisponible : » suivi de l'erreur de GStreamer

	Scénario: Hors de la lecture, la frise inactive garde les couleurs de sa forme d'onde, sans être grisée
		Étant donné la forme d'onde du fichier de test « blancs.flac », de 2 secondes, en cours de calcul
		Et la forme d'onde est bientôt complète
		Alors la frise de cette forme d'onde se dessine pareil, active ou inactive
