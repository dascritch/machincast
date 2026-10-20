# language: fr
Fonctionnalité: Lancer l'indexation depuis l'interface
	En tant que technicien d'antenne,
	je veux lancer une ré-indexation générale depuis le menu et en suivre le journal,
	afin que les banques soient à jour après un dépôt de fichiers.

	https://github.com/dascritch/machincast/issues/38, spec § 6 et § 8.11. Le menu « Maintenance » lance l'indexation
	rapide ou l'audit complet, comme Machin indexation : avec son code et son rôle en base, en tâche de fond. Son journal
	s'ouvre dans une fenêtre à part, et montre ligne par ligne ce que Machin indexation écrirait dans le terminal
	(https://github.com/dascritch/machincast/issues/120) ; à la fin, il conclut par le bilan et le nombre d'anomalies. Les fichiers de test sont ceux de tests/fichiers-sonores ; un chemin qui
	commence par « …/ » est dans le répertoire temporaire du scénario.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 21:00:00 »
		Et les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Et le fichier de test « tags.flac » copié en « …/pubs/cafe.flac »
		Et le fichier de test « sain.wav » copié en « …/pubs/jingle.wav »
		Et les sonores :
			| artiste | titre  | type    | etat  | duree | emplacement |
			|         | Ancien | fichier | actif | 1     | …/vieux.wav |
		Et le fichier de test « sain.wav » copié en « …/vieux.wav »
		Et la banque « Publicité », aléatoire, sans nom public, avec « Ancien »
		Et les répertoires « …/pubs » de la banque « Publicité »

	Scénario: Le menu « Maintenance » lance l'indexation rapide ou l'audit complet
		Quand la fenêtre de l'interface s'ouvre
		Alors le menu « Maintenance » propose « Indexation rapide », « Audit complet »

	Scénario: L'indexation rapide enregistre et vérifie les nouveaux fichiers des banques, et son journal le montre ligne par ligne
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je choisis « Indexation rapide » dans le menu « Maintenance »
		Et l'indexation se termine
		Alors le journal « Indexation rapide » de l'indexation est ouvert
		Et le journal de l'indexation montre :
			| ligne                                                                                                                     |
			| Machin_indexation : …/pubs/cafe.flac : nouveau sonore, ajouté à la banque Publicité                                       |
			| Machin_indexation : …/pubs/jingle.wav : nouveau sonore, ajouté à la banque Publicité                                      |
			| Machin_indexation : …/pubs/cafe.flac : sain, Les Gaufres Électriques – Café à minuit ; sonore passé actif                 |
			| Machin_indexation : …/pubs/jingle.wav : sain ; sonore passé actif                                                         |
			| Machin_indexation : indexation rapide : 2 nouveaux sonores, 0 rattachement ; 2 sonores vérifiés ; 0 erroné, 0 supprimé, 0 rétabli, 2 sortis d'aperçu |
		Et le journal « Indexation rapide » de l'indexation conclut « Indexation rapide terminée : 2 nouveaux sonores, 0 rattachement ; 2 sonores vérifiés ; 0 erroné, 0 supprimé, 0 rétabli, 2 sortis d'aperçu. »
		Et le journal de l'indexation ne signale aucune anomalie
		Quand je ferme le journal de l'indexation
		Alors le journal de l'indexation est fermé
		Et la barre d'état annonce « Indexation rapide terminée : 2 nouveaux sonores, 0 rattachement ; 2 sonores vérifiés ; 0 erroné, 0 supprimé, 0 rétabli, 2 sortis d'aperçu. »
		Et les sonores de la banque « Publicité » en base sont :
			| emplacement       | etat  | titre         |
			| …/vieux.wav       | actif | Ancien        |
			| …/pubs/cafe.flac  | actif | Café à minuit |
			| …/pubs/jingle.wav | actif | None          |
		Et le compte de la liste est « 3 sonores »
		Et les fichiers déposés sont intacts

	Scénario: Le journal compte les anomalies, données fichier par fichier
		Étant donné le fichier « …/pubs/faux.mp3 », qui n'est pas un son
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Indexation rapide » dans le menu « Maintenance »
		Et l'indexation se termine
		Alors le journal « Indexation rapide » de l'indexation conclut « Indexation rapide terminée : 3 nouveaux sonores, 0 rattachement ; 3 sonores vérifiés ; 1 erroné, 0 supprimé, 0 rétabli, 3 sortis d'aperçu. 1 anomalie, dans le journal ci-dessus. »
		Et le journal de l'indexation signale 1 anomalie, sur « …/pubs/faux.mp3 »

	Scénario: Seul l'audit complet revérifie les sonores actifs, et son journal repart de zéro
		Étant donné le fichier « …/vieux.wav », qui n'est pas un son
		Et le fichier « …/pubs/faux.mp3 », qui n'est pas un son
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Indexation rapide » dans le menu « Maintenance »
		Et l'indexation se termine
		Alors le sonore « Ancien » est à l'état « actif »
		Et le journal de l'indexation signale 1 anomalie, sur « …/pubs/faux.mp3 »
		Quand je choisis « Audit complet » dans le menu « Maintenance »
		Et l'indexation se termine
		Alors le journal « Audit complet » de l'indexation conclut « Audit complet terminé : 0 nouveau sonore, 0 rattachement ; 4 sonores vérifiés ; 1 erroné, 0 supprimé, 0 rétabli, 0 sorti d'aperçu. 2 anomalies, dans le journal ci-dessus. »
		Et la première ligne du journal de l'indexation commence par « Machin_indexation : …/vieux.wav : illisible »
		Et le journal de l'indexation signale 2 anomalies, sur « …/vieux.wav », « …/pubs/faux.mp3 »
		Et le sonore « Ancien » est à l'état « erroné »
		Et le journal de l'indexeur n'est plus écouté

	Scénario: Les lignes d'une vérification menée en même temps ne vont pas au journal
		Étant donné une indexation qui attend
		Et le fichier « …/ajouts/faux.mp3 », qui n'est pas un son
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je choisis « Indexation rapide » dans le menu « Maintenance »
		Et l'indexation en est à son premier décodage
		Et j'ajoute les fichiers « …/ajouts/faux.mp3 »
		Et la vérification des fichiers ajoutés se termine
		Et l'indexation attendue reprend, et se termine
		Alors la barre d'état a annoncé « Vérification terminée : faux.mp3, erroné. »
		Et le journal « Indexation rapide » de l'indexation conclut « Indexation rapide terminée : 2 nouveaux sonores, 0 rattachement ; 2 sonores vérifiés ; 0 erroné, 0 supprimé, 0 rétabli, 2 sortis d'aperçu. »
		Et le journal de l'indexation ne signale aucune anomalie

	Scénario: Pendant l'indexation, l'interface reste utilisable, et une seule indexation tourne à la fois
		Étant donné une indexation qui attend
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Indexation rapide » dans le menu « Maintenance »
		Alors la barre d'état annonce « Indexation rapide en cours… »
		Et le journal « Indexation rapide » de l'indexation est ouvert
		Et le journal « Indexation rapide » de l'indexation conclut « Indexation rapide en cours… »
		Et le menu « Maintenance » ne propose plus rien
		Quand j'ouvre l'onglet « Banques »
		Alors le compte de la liste est « 1 banque »
		Quand l'indexation attendue reprend, et se termine
		Alors le menu « Maintenance » propose « Indexation rapide », « Audit complet »

	Scénario: Une indexation impossible le dit, et laisse vérifiés les sonores déjà vérifiés
		Étant donné un indexeur qui ne sait pas décoder les fichiers
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Indexation rapide » dans le menu « Maintenance »
		Et l'indexation se termine
		Alors le journal « Indexation rapide » de l'indexation conclut « Indexation impossible : aucun décodeur pour ce format ; les sonores déjà vérifiés le restent. 1 anomalie, dans le journal ci-dessus. »
		Et le journal de l'indexation montre :
			| ligne                                                                                  |
			| Machin_indexation : …/pubs/cafe.flac : nouveau sonore, ajouté à la banque Publicité    |
			| Machin_indexation : …/pubs/jingle.wav : nouveau sonore, ajouté à la banque Publicité   |
			| Machin_indexation : indexation impossible : aucun décodeur pour ce format              |

	Scénario: Fermer la fenêtre attend la fin de l'indexation en cours
		Étant donné une indexation qui attend
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Indexation rapide » dans le menu « Maintenance »
		Et je ferme la fenêtre de l'interface, pendant que l'indexation attendue reprend
		Et la fenêtre fermée a tout traité
		Alors le journal de l'indexation est fermé
		Et les sonores de la banque « Publicité » en base sont :
			| emplacement       | etat  | titre         |
			| …/vieux.wav       | actif | Ancien        |
			| …/pubs/cafe.flac  | actif | Café à minuit |
			| …/pubs/jingle.wav | actif | None          |
