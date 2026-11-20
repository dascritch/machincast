# language: fr
Fonctionnalité: Espace disque
	En tant qu'administrateur du poste,
	je veux une fenêtre « Espace disque » dans le menu « Maintenance »,
	afin de savoir où déposer des sonores et ce que chaque banque occupe.

	https://github.com/dascritch/machincast/issues/533. La fenêtre donne les points de montage où le service de
	diffusion lit un sonore, avec leur espace libre et leur taille, puis un tableau des répertoires indexés par une
	banque : le répertoire, la banque, le volume qu'il occupe, compté en tâche de fond, et l'espace libre de son point
	de montage. Un double-clic sur le répertoire l'ouvre dans le gestionnaire de fichiers. Un chemin qui commence par
	« …/ » est dans le répertoire du scénario.

	Contexte:
		Étant donné l'horloge de l'interface au « 2026-11-20 10:00:00 »
		Et la banque « Musique », aléatoire, sans nom public, avec aucun
		Et la banque « Jingles », séquentielle, sans nom public, avec aucun
		Et le répertoire « …/musique » contient des fichiers de 1500 et 500 octets
		Et le répertoire « …/jingles » contient des fichiers de 250 octets
		Et les répertoires « …/musique » de la banque « Musique »
		Et les répertoires « …/jingles », « …/disparu » de la banque « Jingles »

	Scénario: « Espace disque… » est dans le menu « Maintenance »
		Quand la fenêtre de l'interface s'ouvre
		Alors le menu « Maintenance » propose « Indexation rapide », « Audit complet », « Statut des indexations… », « Maintenance de la base de données… », « Exporter la base… », « Espace disque… »

	Scénario: Les répertoires des banques disent ce qu'ils occupent, et l'espace libre de leur point de montage
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Espace disque… » dans le menu « Maintenance »
		Alors la fenêtre « Espace disque » montre bientôt les répertoires :
			| répertoire  | banque  | occupé      |
			| …/disparu   | Jingles | inaccessible |
			| …/jingles   | Jingles | 250 o       |
			| …/musique   | Musique | 2,0 ko      |
		Et chaque répertoire qui existe a l'espace libre de son point de montage

	Scénario: Les points de montage sont ceux des répertoires que le service peut lire, chacun une fois
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Espace disque… » dans le menu « Maintenance »
		Alors la fenêtre « Espace disque » montre le point de montage du répertoire du scénario, une seule fois, avec son espace libre et sa taille

	Scénario: Un double-clic sur un répertoire l'ouvre dans le gestionnaire de fichiers
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Espace disque… » dans le menu « Maintenance »
		Et je double-clique sur le répertoire « …/musique » de la fenêtre « Espace disque »
		Alors le navigateur de fichiers a ouvert « …/musique »
