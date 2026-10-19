# language: fr
Fonctionnalité: Lancer l'indexation depuis l'interface
	En tant que technicien d'antenne,
	je veux lancer une ré-indexation générale depuis le menu et en voir le rapport,
	afin que les banques soient à jour après un dépôt de fichiers.

	https://github.com/dascritch/machincast/issues/38, spec § 6 et § 8.11. Le menu « Maintenance » lance l'indexation
	rapide ou l'audit complet, comme Machin indexation : avec son code et son rôle en base, en tâche de fond. Le rapport
	s'ouvre à la fin, avec les anomalies. Les fichiers de test sont ceux de tests/fichiers-sonores ; un chemin qui
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

	Scénario: L'indexation rapide enregistre et vérifie les nouveaux fichiers des banques, puis montre son rapport
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je lance « Indexation rapide » depuis le menu « Maintenance »
		Et l'indexation se termine
		Alors le rapport « Indexation rapide » a dit « Indexation rapide terminée : 2 nouveaux sonores, 0 rattachement ; 2 sonores vérifiés ; 0 erroné, 0 supprimé, 0 rétabli, 2 sortis d'aperçu. »
		Et le rapport n'a signalé aucune anomalie
		Et la barre d'état annonce « Indexation rapide terminée : 2 nouveaux sonores, 0 rattachement ; 2 sonores vérifiés ; 0 erroné, 0 supprimé, 0 rétabli, 2 sortis d'aperçu. »
		Et les sonores de la banque « Publicité » en base sont :
			| emplacement       | etat  | titre         |
			| …/vieux.wav       | actif | Ancien        |
			| …/pubs/cafe.flac  | actif | Café à minuit |
			| …/pubs/jingle.wav | actif | None          |
		Et le compte de la liste est « 3 sonores »
		Et les fichiers déposés sont intacts

	Scénario: Le rapport donne les anomalies, fichier par fichier
		Étant donné le fichier « …/pubs/faux.mp3 », qui n'est pas un son
		Quand la fenêtre de l'interface s'ouvre
		Et je lance « Indexation rapide » depuis le menu « Maintenance »
		Et l'indexation se termine
		Alors le rapport « Indexation rapide » a dit « Indexation rapide terminée : 3 nouveaux sonores, 0 rattachement ; 3 sonores vérifiés ; 1 erroné, 0 supprimé, 0 rétabli, 3 sortis d'aperçu. »
		Et le rapport a signalé 1 anomalie, sur « …/pubs/faux.mp3 »

	Scénario: Seul l'audit complet revérifie les sonores actifs
		Étant donné le fichier « …/vieux.wav », qui n'est pas un son
		Quand la fenêtre de l'interface s'ouvre
		Et je lance « Indexation rapide » depuis le menu « Maintenance »
		Et l'indexation se termine
		Alors le sonore « Ancien » est à l'état « actif »
		Quand je lance « Audit complet » depuis le menu « Maintenance »
		Et l'indexation se termine
		Alors le rapport « Audit complet » a dit « Audit complet terminé : 0 nouveau sonore, 0 rattachement ; 3 sonores vérifiés ; 1 erroné, 0 supprimé, 0 rétabli, 0 sorti d'aperçu. »
		Et le rapport a signalé 1 anomalie, sur « …/vieux.wav »
		Et le sonore « Ancien » est à l'état « erroné »
		Et le journal de l'indexeur n'est plus écouté

	Scénario: Les anomalies d'une vérification menée en même temps ne vont pas au rapport
		Étant donné une indexation qui attend
		Et le fichier « …/ajouts/faux.mp3 », qui n'est pas un son
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je lance « Indexation rapide » depuis le menu « Maintenance »
		Et l'indexation en est à son premier décodage
		Et j'ajoute les fichiers « …/ajouts/faux.mp3 »
		Et la vérification des fichiers ajoutés se termine
		Et l'indexation attendue reprend, et se termine
		Alors la barre d'état a annoncé « Vérification terminée : faux.mp3, erroné. »
		Et le rapport « Indexation rapide » a dit « Indexation rapide terminée : 2 nouveaux sonores, 0 rattachement ; 2 sonores vérifiés ; 0 erroné, 0 supprimé, 0 rétabli, 2 sortis d'aperçu. »
		Et le rapport n'a signalé aucune anomalie

	Scénario: Pendant l'indexation, l'interface reste utilisable, et une seule indexation tourne à la fois
		Étant donné une indexation qui attend
		Quand la fenêtre de l'interface s'ouvre
		Et je lance « Indexation rapide » depuis le menu « Maintenance »
		Alors la barre d'état annonce « Indexation rapide en cours… »
		Et le menu « Maintenance » ne propose plus rien
		Quand j'ouvre l'onglet « Banques »
		Alors le compte de la liste est « 1 banque »
		Quand l'indexation attendue reprend, et se termine
		Alors le menu « Maintenance » propose « Indexation rapide », « Audit complet »

	Scénario: Une indexation impossible le dit, et laisse vérifiés les sonores déjà vérifiés
		Étant donné un indexeur qui ne sait pas décoder les fichiers
		Quand la fenêtre de l'interface s'ouvre
		Et je lance « Indexation rapide » depuis le menu « Maintenance »
		Et l'indexation se termine
		Alors le rapport « Indexation rapide » a dit « Indexation impossible : aucun décodeur pour ce format ; les sonores déjà vérifiés le restent. »

	Scénario: Fermer la fenêtre attend la fin de l'indexation en cours
		Étant donné une indexation qui attend
		Quand la fenêtre de l'interface s'ouvre
		Et je lance « Indexation rapide » depuis le menu « Maintenance »
		Et je ferme la fenêtre de l'interface, pendant que l'indexation attendue reprend
		Et la fenêtre fermée a tout traité
		Alors aucun rapport n'a été montré
		Et les sonores de la banque « Publicité » en base sont :
			| emplacement       | etat  | titre         |
			| …/vieux.wav       | actif | Ancien        |
			| …/pubs/cafe.flac  | actif | Café à minuit |
			| …/pubs/jingle.wav | actif | None          |
