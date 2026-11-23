# language: fr
Fonctionnalité: Les points d'extension de Machin indexer
	En tant que développeur d'un plugin,
	je veux être prévenu de ce que trouve Machin indexer,
	afin de compléter un sonore : métadonnées, déclarations, analyse
	(https://github.com/dascritch/machincast/issues/590, ticket enfant de https://github.com/dascritch/machincast/issues/348).

	Contexte:
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles », avec un fichier « intro.flac » sain et un fichier « casse.mp3 » endommagé

	Scénario: Un plugin est prévenu de chaque nouveau sonore, puis de ce que sa vérification en a trouvé
		Étant donné un plugin chargé, abonné aux points de Machin indexer
		Quand l'indexeur fait une indexation rapide
		Alors le plugin a été prévenu de « indexer.sound_spotted » pour « jingles/intro.flac », trouvé par la banque « Jingles »
		Et le plugin a été prévenu de « indexer.sound_spotted » pour « jingles/casse.mp3 », trouvé par la banque « Jingles »
		Et le plugin a été prévenu de « indexer.sound_detailed » pour « jingles/intro.flac », de l'état « preview » à l'état « active », avec sa durée, sans problème
		Et le plugin a été prévenu de « indexer.sound_detailed » pour « jingles/casse.mp3 », de l'état « preview » à l'état « corrupt », sans durée, avec son problème
		Quand le plugin oublie ce qu'il a reçu
		Et l'indexeur fait une indexation rapide
		Alors le plugin n'a été prévenu de rien

	Scénario: L'erreur d'un plugin est consignée, et n'arrête ni le parcours ni la vérification
		Étant donné un plugin chargé « fautif », qui échoue à chaque point de Machin indexer
		Quand l'indexeur fait une indexation rapide
		Alors le sonore de « jingles/intro.flac » est à l'état « active », dans la banque « Jingles »
		Et le sonore de « jingles/casse.mp3 » est à l'état « corrupt »
		Et le journal du binaire dit que le plugin « fautif » a échoué au point « indexer.sound_spotted »
		Et le journal du binaire dit que le plugin « fautif » a échoué au point « indexer.sound_detailed »
