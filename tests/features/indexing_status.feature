# language: fr
Fonctionnalité: Statut des indexations de sonores
	En tant que programmateur,
	je veux voir dans une fenêtre où en sont les indexations : répertoires parcourus et sonores indexés,
	afin de savoir si une indexation a encore du travail, et laquelle lancer.

	https://github.com/dascritch/machincast/issues/392. Menu « Maintenance », « Statut des indexations… » : les nombres
	sont lus dans la base, toutes les deux secondes tant que la fenêtre est ouverte. Un répertoire compte une fois,
	même s'il alimente plusieurs banques ; il est parcouru s'il l'a été depuis le dernier démarrage de Machin_indexer
	noté dans le log. Les sonores fichiers non supprimés se répartissent en trois parts : sans indexation, indexation
	sommaire seule (vérifiés), indexation complète (audités).

	Contexte:
		Étant donné les banques « Jingles », des répertoires « /sons/jingles » et « /sons/communs », et « Pubs », des répertoires « /sons/pubs » et « /sons/communs »
		Et un démarrage de Machin_indexer noté dans le log il y a une heure
		Et les répertoires « /sons/jingles » et « /sons/communs » parcourus depuis, et « /sons/pubs » parcouru avant
		Et 1 sonore sans indexation, 2 sonores à l'indexation sommaire et 3 sonores à l'indexation complète
		Et un sonore supprimé et un stream

	Scénario: Le statut compte les répertoires et les sonores
		Quand le statut des indexations est lu
		Alors il compte 1 répertoire à scanner et 2 répertoires scannés
		Et il compte 6 sonores détectés, 2 à l'indexation sommaire et 3 à l'indexation complète

	Scénario: Sans démarrage dans le log, un répertoire déjà parcouru compte comme scanné
		Étant donné aucun démarrage de Machin_indexer dans le log
		Quand le statut des indexations est lu
		Alors il compte 0 répertoire à scanner et 3 répertoires scannés

	Scénario: La fenêtre montre les nombres et les deux camemberts
		Quand j'ouvre « Statut des indexations… » dans le menu « Maintenance »
		Alors la fenêtre « Statut des indexations » montre :
			| ligne                                     | valeur   |
			| Répertoires à scanner                     | 1 (33 %) |
			| Répertoires scannés                       | 2 (67 %) |
			| Sonores détectés                          | 6        |
			| Sonores à l'indexation sommaire           | 2 (33 %) |
			| Sonores à l'indexation complète           | 3 (50 %) |
		Et le camembert « Répertoires » a les parts : « Scannés » 2, « À scanner » 1
		Et le camembert « Sonores » a les parts : « Audit complet » 3, « Indexation sommaire » 2, « Pas encore indexés » 1

	Scénario: La fenêtre suit l'indexation en cours
		Étant donné la fenêtre « Statut des indexations » ouverte
		Quand le répertoire « /sons/pubs » est parcouru
		Et la fenêtre se met à jour
		Alors la fenêtre « Statut des indexations » montre :
			| ligne                 | valeur    |
			| Répertoires à scanner | 0 (0 %)   |
			| Répertoires scannés   | 3 (100 %) |

	Scénario: L'indexeur note la fin du parcours de chaque répertoire
		Étant donné une banque « Live » du répertoire de test « live », qui contient un fichier flac
		Quand l'indexeur parcourt les répertoires des banques
		Alors le répertoire « live » a une date de parcours
