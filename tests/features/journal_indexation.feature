# language: fr
Fonctionnalité: Journal de l'indexation, dans sa propre fenêtre
	En tant que technicien d'antenne,
	je veux suivre l'indexation ligne par ligne dans une fenêtre à part de l'interface,
	afin de voir chaque sonore indexé, et de pouvoir fermer l'interface sans attendre la fin d'un audit complet.

	https://github.com/dascritch/machincast/issues/120, spec § 6.3 et § 8.11. Machin indexation --fenetre, que
	l'interface lance dans un processus à part (indexation_interface.feature), montre dans sa fenêtre ce qu'il écrirait
	dans le terminal ; à la fin, il conclut par le bilan et le nombre d'anomalies. Fermer la fenêtre pendant
	l'indexation demande s'il faut l'arrêter. Comme dans le terminal, le journal annonce le document d'audit du passage
	(audit_indexation.feature). Les scénarios ouvrent la fenêtre dans le processus des tests. Les
	fichiers de test sont ceux de tests/fichiers-sonores ; un chemin qui commence par « …/ » est dans le répertoire
	temporaire du scénario.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et le fichier de test « tags.flac » copié en « …/pubs/cafe.flac »
		Et le fichier de test « sain.wav » copié en « …/pubs/jingle.wav »
		Et les sonores :
			| artiste | titre  | type    | etat  | duree | emplacement |
			|         | Ancien | fichier | actif | 1     | …/vieux.wav |
		Et le fichier de test « sain.wav » copié en « …/vieux.wav »
		Et la banque « Publicité », aléatoire, sans nom public, avec « Ancien »
		Et les répertoires « …/pubs » de la banque « Publicité »

	Scénario: L'indexation rapide enregistre et vérifie les nouveaux fichiers des banques, et son journal le montre ligne par ligne
		Quand le journal « Indexation rapide » de l'indexation s'ouvre
		Et l'indexation se termine
		Alors le journal de l'indexation montre :
			| ligne                                                                                                                     |
			| Machin_indexation : …/pubs/cafe.flac : nouveau sonore, ajouté à la banque Publicité                                       |
			| Machin_indexation : …/pubs/jingle.wav : nouveau sonore, ajouté à la banque Publicité                                      |
			| Machin_indexation : …/pubs/cafe.flac : sain, Les Gaufres Électriques – Café à minuit ; sonore passé actif                 |
			| Machin_indexation : …/pubs/jingle.wav : sain ; sonore passé actif                                                         |
			| Machin_indexation : indexation rapide : 2 nouveaux sonores, 0 rattachement ; 2 sonores vérifiés ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 2 sortis d'aperçu |
			| Machin_indexation : document d'audit : …/audit/machincast-audit-2026-10-15T08:15:00.csv, …/audit/machincast-audit-2026-10-15T08:15:00.html |
		Et le journal « Indexation rapide » de l'indexation conclut « Indexation rapide terminée : 2 nouveaux sonores, 0 rattachement ; 2 sonores vérifiés ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 2 sortis d'aperçu. »
		Et le journal de l'indexation ne signale aucune anomalie
		Et les sonores de la banque « Publicité » en base sont :
			| emplacement       | etat  | titre         |
			| …/vieux.wav       | actif | Ancien        |
			| …/pubs/cafe.flac  | actif | Café à minuit |
			| …/pubs/jingle.wav | actif | None          |
		Et les fichiers déposés sont intacts
		Quand je ferme le journal de l'indexation
		Alors aucune question n'a été posée
		Et le journal de l'indexation est fermé

	Scénario: Le journal compte les anomalies, données fichier par fichier
		Étant donné le fichier « …/pubs/faux.mp3 », qui n'est pas un son
		Quand le journal « Indexation rapide » de l'indexation s'ouvre
		Et l'indexation se termine
		Alors le journal « Indexation rapide » de l'indexation conclut « Indexation rapide terminée : 3 nouveaux sonores, 0 rattachement ; 3 sonores vérifiés ; 0 erroné, 1 non supporté, 0 supprimé, 0 rétabli, 3 sortis d'aperçu. 1 anomalie, dans le journal ci-dessus. »
		Et le journal de l'indexation signale 1 anomalie, sur « …/pubs/faux.mp3 »

	Scénario: Seul l'audit complet revérifie les sonores actifs
		Étant donné le fichier « …/vieux.wav », qui n'est pas un son
		Et le fichier « …/pubs/faux.mp3 », qui n'est pas un son
		Et l'indexeur a fait une indexation rapide
		Alors le sonore « Ancien » est à l'état « actif »
		Quand le journal « Audit complet » de l'indexation s'ouvre
		Et l'indexation se termine
		Alors le journal « Audit complet » de l'indexation conclut « Audit complet terminé : 0 nouveau sonore, 0 rattachement ; 4 sonores vérifiés ; 0 erroné, 1 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu. 2 anomalies, dans le journal ci-dessus. »
		Et le journal de l'indexation signale 2 anomalies, sur « …/vieux.wav », « …/pubs/faux.mp3 »
		Et le sonore « Ancien » est à l'état « non supporté »
		Et le journal de l'indexeur n'est plus écouté

	Scénario: Pendant l'indexation, le journal dit qu'elle est en cours
		Étant donné une indexation qui attend
		Quand le journal « Indexation rapide » de l'indexation s'ouvre
		Alors le journal « Indexation rapide » de l'indexation est ouvert
		Et le journal « Indexation rapide » de l'indexation conclut « Indexation rapide en cours… »
		Quand l'indexation attendue reprend, et se termine
		Alors le journal « Indexation rapide » de l'indexation conclut « Indexation rapide terminée : 2 nouveaux sonores, 0 rattachement ; 2 sonores vérifiés ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 2 sortis d'aperçu. »

	Scénario: Une indexation impossible le dit, et laisse vérifiés les sonores déjà vérifiés
		Étant donné un indexeur qui ne sait pas décoder les fichiers
		Quand le journal « Indexation rapide » de l'indexation s'ouvre
		Et l'indexation se termine
		Alors le journal « Indexation rapide » de l'indexation conclut « Indexation impossible : aucun décodeur pour ce format ; les sonores déjà vérifiés le restent. 1 anomalie, dans le journal ci-dessus. »
		Et le journal de l'indexation montre :
			| ligne                                                                                  |
			| Machin_indexation : …/pubs/cafe.flac : nouveau sonore, ajouté à la banque Publicité    |
			| Machin_indexation : …/pubs/jingle.wav : nouveau sonore, ajouté à la banque Publicité   |
			| Machin_indexation : indexation impossible : aucun décodeur pour ce format              |

	Scénario: Une seule indexation à la fois sur la base
		Étant donné une autre indexation en cours sur la base
		Quand le journal « Indexation rapide » de l'indexation s'ouvre
		Et l'indexation se termine
		Alors le journal « Indexation rapide » de l'indexation conclut « Indexation impossible : une autre indexation est en cours sur cette base ; les sonores déjà vérifiés le restent. 1 anomalie, dans le journal ci-dessus. »
		Et les sonores de la banque « Publicité » en base sont :
			| emplacement | etat  | titre  |
			| …/vieux.wav | actif | Ancien |

	Scénario: Fermer le journal pendant l'indexation, en la laissant continuer, garde la fenêtre ouverte
		Étant donné une indexation qui attend
		Quand le journal « Indexation rapide » de l'indexation s'ouvre
		Et l'indexation en est à son premier décodage
		Et je ferme le journal de l'indexation, en répondant « Continuer »
		Alors la question d'arrêt de l'indexation a nommé « Indexation rapide »
		Et le journal « Indexation rapide » de l'indexation est ouvert
		Quand l'indexation attendue reprend, et se termine
		Alors les sonores de la banque « Publicité » en base sont :
			| emplacement       | etat  | titre         |
			| …/vieux.wav       | actif | Ancien        |
			| …/pubs/cafe.flac  | actif | Café à minuit |
			| …/pubs/jingle.wav | actif | None          |

	Scénario: Fermer le journal pendant l'indexation, en l'arrêtant, l'arrête après le fichier en cours
		Étant donné une indexation qui attend
		Quand le journal « Indexation rapide » de l'indexation s'ouvre
		Et l'indexation en est à son premier décodage
		Et je ferme le journal de l'indexation, en répondant « Arrêter », pendant que l'indexation attendue reprend
		Alors la question d'arrêt de l'indexation a nommé « Indexation rapide »
		Et le journal de l'indexation est fermé
		Et l'indexation est arrêtée
		Et les sonores de la banque « Publicité » en base sont :
			| emplacement       | etat   | titre         |
			| …/vieux.wav       | actif  | Ancien        |
			| …/pubs/cafe.flac  | actif  | Café à minuit |
			| …/pubs/jingle.wav | apercu | None          |
		Et le journal de l'indexeur n'est plus écouté

	Scénario: Machin indexation --fenetre demande un affichage graphique
		Quand je lance Machin indexation --fenetre sans affichage graphique
		Alors la commande se termine avec le code 1
		Et la sortie d'erreur de la commande mentionne « --fenetre demande un affichage graphique »
