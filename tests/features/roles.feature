# language: fr
Fonctionnalité: Rôles PostgreSQL et droits par binaire
	En tant que développeur de MachinCast,
	je veux que chaque binaire se connecte avec son propre rôle, aux droits limités au strict nécessaire,
	afin qu'un bug dans un binaire ne puisse pas corrompre les données qu'il n'a pas à toucher.

	Contexte:
		Étant donné une base de test migrée avec les éléments de référence

	Scénario: Droits du binaire lecture
		Alors le rôle "machincast_lecture" a exactement ces droits :
			| table                 | lire | inserer | modifier | supprimer |
			| sonores               | oui  | non     | non      | non       |
			| marques_pages_streams | oui  | non     | non      | non       |
			| banques               | oui  | non     | non      | non       |
			| banques_repertoires   | non  | non     | non      | non       |
			| banques_sonores       | oui  | non     | non      | non       |
			| evenements            | oui  | non     | non      | non       |
			| evenements_elements   | oui  | non     | non      | non       |
			| sequences             | oui  | non     | non      | non       |
			| sequences_elements    | oui  | non     | non      | non       |
			| airplay               | oui  | oui     | non      | non       |
			| log                   | non  | oui     | non      | non       |

	Scénario: Droits du binaire indexation
		Alors le rôle "machincast_indexation" a exactement ces droits :
			| table                 | lire | inserer | modifier | supprimer |
			| sonores               | oui  | oui     | oui      | non       |
			| marques_pages_streams | non  | non     | non      | non       |
			| banques               | oui  | non     | non      | non       |
			| banques_repertoires   | oui  | non     | non      | non       |
			| banques_sonores       | oui  | oui     | non      | non       |
			| evenements            | non  | non     | non      | non       |
			| evenements_elements   | non  | non     | non      | non       |
			| sequences             | non  | non     | non      | non       |
			| sequences_elements    | non  | non     | non      | non       |
			| airplay               | non  | non     | non      | non       |
			| log                   | non  | non     | non      | non       |

	Scénario: Droits de l'interface
		Alors le rôle "machincast_interface" a exactement ces droits :
			| table                 | lire | inserer | modifier | supprimer |
			| sonores               | oui  | oui     | oui      | oui       |
			| marques_pages_streams | oui  | oui     | oui      | oui       |
			| banques               | oui  | oui     | oui      | oui       |
			| banques_repertoires   | oui  | oui     | oui      | oui       |
			| banques_sonores       | oui  | oui     | oui      | oui       |
			| evenements            | oui  | oui     | oui      | oui       |
			| evenements_elements   | oui  | oui     | oui      | oui       |
			| sequences             | oui  | oui     | oui      | oui       |
			| sequences_elements    | oui  | oui     | oui      | oui       |
			| airplay               | oui  | non     | non      | non       |
			| log                   | oui  | non     | non      | non       |

	Plan du scénario: Le binaire lecture ne modifie que le champ « etat » des sonores
		Alors le rôle "machincast_lecture" <verdict> modifier la colonne "<colonne>" des sonores

		Exemples:
			| colonne | verdict  |
			| etat    | peut     |
			| titre   | ne peut pas |
			| duree   | ne peut pas |

	Scénario: Le binaire lecture enregistre un passage complet
		Quand le rôle "machincast_lecture" enregistre le début et la fin d'un passage, puis une entrée de log
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
			| machincast_lecture    |
			| machincast_indexation |
			| machincast_interface  |

	Scénario: L'annulation des migrations ne supprime pas les rôles
		Quand j'annule toutes les migrations
		Alors les trois rôles existent toujours
