# language: fr
Fonctionnalité: Lancer l'indexation depuis l'interface
	En tant que technicien d'antenne,
	je veux lancer une ré-indexation générale depuis le menu, sans bloquer l'interface,
	afin que les banques soient à jour après un dépôt de fichiers, même si l'indexation dure des heures.

	https://github.com/dascritch/machincast/issues/38 et https://github.com/dascritch/machincast/issues/120, spec § 8.11.
	Le menu « Maintenance » lance Machin indexer --window dans un processus à part, détaché de l'interface : son
	journal s'ouvre dans sa propre fenêtre (journal_indexation.feature), et fermer l'interface ne l'arrête pas. Les
	scénarios remplacent Machin indexer par un programme factice, qui note ses options et attend qu'on le termine.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-20 09:00:00 »
		Et les événements :
			| name     | public_name | priority               | starts_at | ends_at | days |
			| Continue |             | background_programming |           |         |      |
		Et un Machin indexer factice, qui attend

	Scénario: Le menu « Maintenance » lance l'indexation rapide ou l'audit complet
		Quand la fenêtre de l'interface s'ouvre
		Alors le menu « Maintenance » propose « Indexation rapide », « Audit complet », « Maintenance de la base de données… »

	Plan du scénario: Machin indexer est lancé dans son propre processus, avec sa fenêtre
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « <mode> » dans le menu « Maintenance »
		Alors Machin indexer a été lancé avec <options>
		Et la barre d'état annonce « <lancement> »
		Et le menu « Maintenance » ne propose plus rien
		Quand l'interface a regardé plusieurs fois si le Machin indexer factice tourne
		Alors le menu « Maintenance » ne propose plus rien
		Quand le Machin indexer factice se termine
		Alors le menu « Maintenance » propose « Indexation rapide », « Audit complet », « Maintenance de la base de données… »
		Et la barre d'état annonce « <fin> »

		Exemples:
			| mode              | options                         | lancement                                          | fin                                                                                    |
			| Indexation rapide | « --window »                   | Indexation rapide lancée, dans sa propre fenêtre.  | Indexation rapide terminée ; « Rafraîchir les onglets » (F5) montre ses changements.   |
			| Audit complet     | « --window », « --full-audit » | Audit complet lancé, dans sa propre fenêtre.    | Audit complet terminé ; « Rafraîchir les onglets » (F5) montre ses changements.        |

	Scénario: Fermer l'interface n'attend pas l'indexation, et ne l'arrête pas
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Audit complet » dans le menu « Maintenance »
		Et je ferme la fenêtre de l'interface
		Alors la fenêtre de l'interface est fermée
		Et le Machin indexer factice tourne toujours

	Scénario: Un Machin indexer qui ne se lance pas est signalé, et le menu le propose toujours
		Étant donné un Machin indexer introuvable
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Indexation rapide » dans le menu « Maintenance »
		Alors la barre d'état annonce « Indexation impossible : Machin indexer n'a pas pu être lancé. »
		Et le menu « Maintenance » propose « Indexation rapide », « Audit complet », « Maintenance de la base de données… »

	Plan du scénario: Machin indexer reçoit la configuration de l'interface
		Alors la commande d'indexation, pour la configuration <configuration>, est « <commande> »

		Exemples:
			| configuration                  | commande                                                          |
			| par défaut                     | <python> -m machincast.indexation                                  |
			| « /etc/machincast.toml »       | <python> -m machincast.indexation --config /etc/machincast.toml    |
			| « reglages/machincast.toml »   | <python> -m machincast.indexation --config …/reglages/machincast.toml |
