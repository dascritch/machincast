# language: fr
Fonctionnalité: Rôles PostgreSQL et droits par binaire
	En tant que développeur de MachinCast,
	je veux que chaque binaire se connecte avec son propre rôle, aux droits limités au strict nécessaire,
	afin qu'un bug dans un binaire ne puisse pas corrompre les données qu'il n'a pas à toucher.

	Contexte:
		Étant donné une base de test migrée avec les éléments de référence

	Scénario: Droits du binaire lecture
		Alors le rôle "machincast_player" a exactement ces droits :
			| table            | lire | inserer | modifier | supprimer |
			| sounds           | oui  | non     | non      | non       |
			| feeds            | oui  | non     | non      | non       |
			| banks            | oui  | non     | non      | non       |
			| bank_directories | non  | non     | non      | non       |
			| bank_sounds      | oui  | non     | non      | non       |
			| events           | oui  | non     | non      | non       |
			| event_items      | oui  | non     | non      | non       |
			| event_skips      | oui  | non     | non      | non       |
			| sequences        | oui  | non     | non      | non       |
			| sequence_items   | oui  | non     | non      | non       |
			| airplay          | oui  | oui     | non      | non       |
			| log              | non  | oui     | non      | non       |

	Scénario: Droits du binaire indexation
		https://github.com/dascritch/machincast/issues/195 : l'indexation retire d'une banque les sonores hors de ses durées.
		https://github.com/dascritch/machincast/issues/341 : elle note ses démarrages et ses fins au log, sans le lire.

		Alors le rôle "machincast_indexer" a exactement ces droits :
			| table            | lire | inserer | modifier | supprimer |
			| sounds           | oui  | oui     | oui      | non       |
			| feeds            | non  | non     | non      | non       |
			| banks            | oui  | non     | non      | non       |
			| bank_directories | oui  | non     | non      | non       |
			| bank_sounds      | oui  | oui     | non      | oui       |
			| events           | non  | non     | non      | non       |
			| event_items      | non  | non     | non      | non       |
			| event_skips      | non  | non     | non      | non       |
			| sequences        | non  | non     | non      | non       |
			| sequence_items   | non  | non     | non      | non       |
			| airplay          | non  | non     | non      | non       |
			| log              | non  | oui     | non      | non       |

	Scénario: Droits de l'interface
		Alors le rôle "machincast_interface" a exactement ces droits :
			| table            | lire | inserer | modifier | supprimer |
			| sounds           | oui  | oui     | oui      | oui       |
			| feeds            | oui  | oui     | oui      | oui       |
			| banks            | oui  | oui     | oui      | oui       |
			| bank_directories | oui  | oui     | oui      | oui       |
			| bank_sounds      | oui  | oui     | oui      | oui       |
			| events           | oui  | oui     | oui      | oui       |
			| event_items      | oui  | oui     | oui      | oui       |
			| event_skips      | oui  | oui     | non      | oui       |
			| sequences        | oui  | oui     | oui      | oui       |
			| sequence_items   | oui  | oui     | oui      | oui       |
			| airplay          | oui  | non     | non      | non       |
			| log              | oui  | non     | non      | non       |

	Plan du scénario: Le binaire lecture ne modifie que le champ « etat » des sonores
		Alors le rôle "machincast_player" <verdict> modifier la colonne "<colonne>" des sonores

		Exemples:
			| colonne | verdict  |
			| state    | peut     |
			| title   | ne peut pas |
			| duration   | ne peut pas |

	Plan du scénario: L'indexation et la lecture, parmi les rôles, retrouvent le démarrage précédent d'un binaire
		https://github.com/dascritch/machincast/issues/341 : la fonction machincast_previous_start ne rend que l'heure, le
		pid et la fin du dernier démarrage noté ; elle lit le log avec les droits du propriétaire de la base.
		https://github.com/dascritch/machincast/issues/342 : la lecture aussi, sans lire le log.
		Alors le rôle "<role>" <verdict> retrouver le démarrage précédent d'un binaire

		Exemples:
			| role                 | verdict     |
			| machincast_indexer   | peut        |
			| machincast_player    | peut        |
			| machincast_interface | ne peut pas |

	Scénario: Le binaire lecture enregistre un passage complet
		Quand le rôle "machincast_player" enregistre le début et la fin d'un passage, puis une entrée de log
		Alors les deux lignes d'airplay et l'entrée de log sont en base

	Scénario: Supprimer un sonore depuis l'interface conserve l'airplay
		Étant donné un passage du sonore de référence dans l'airplay
		Quand le rôle "machincast_interface" supprime le sonore de référence
		Alors la ligne d'airplay existe toujours, sans référence au sonore

	Scénario: Le compte qui lance les tests endosse les trois rôles, sans en hériter les droits
		Alors le compte courant peut endosser chacun des trois rôles, sans en hériter les droits

	Plan du scénario: Chaque binaire se connecte avec son propre rôle
		Quand je me connecte à la base de test avec le rôle "<role>"
		Alors la connexion agit en tant que "<role>"

		Exemples:
			| role                  |
			| machincast_player    |
			| machincast_indexer |
			| machincast_interface  |

	Scénario: L'annulation des migrations ne supprime pas les rôles
		Quand j'annule toutes les migrations
		Alors les trois rôles existent toujours
