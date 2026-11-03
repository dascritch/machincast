# language: fr
Fonctionnalité: Langue des messages
	En tant qu'opérateur d'une radio, francophone ou non,
	je veux que MachinCast me parle dans la langue de ma session,
	afin de comprendre ses messages, son aide et son interface sans traduire moi-même
	(https://github.com/dascritch/machincast/issues/360).

	Le code écrit ses messages en anglais ; le catalogue français les traduit. Les scénarios se jouent en français.

	Plan du scénario: La langue est celle de la session, l'anglais à défaut
		Étant donné les variables de langue « <variables> »
		Alors la langue des messages est « <langue> »

		Exemples:
			| variables                          | langue |
			| LANG=fr_FR.UTF-8                   | fr     |
			| LANG=en_GB.UTF-8                   | en     |
			| LANG=de_DE.UTF-8                   | en     |
			| LANG=C.UTF-8                       | en     |
			|                                    | en     |
			| LC_ALL=fr_CA.UTF-8 LANG=en_US.UTF-8 | fr     |
			| LC_MESSAGES=fr_BE LANG=en_US        | fr     |
			| LANGUAGE=de:fr LANG=en_US.UTF-8     | fr     |
			| LANGUAGE=en LANG=fr_FR.UTF-8        | en     |

	Plan du scénario: Un binaire parle la langue de sa session
		Quand je demande l'aide de Machin_player dans une session « <variables> »
		Alors l'aide commence par « <début> »

		Exemples:
			| variables        | début                                                                   |
			| LANG=fr_FR.UTF-8 | Lit les événements programmés et les diffuse sur la sortie audio       |
			| LANG=en_US.UTF-8 | Reads the programmed events and broadcasts them on the configured audio |
			| LANG=es_ES.UTF-8 | Reads the programmed events and broadcasts them on the configured audio |

	Plan du scénario: L'interface traduit ses écrans dans la langue de la session
		Quand j'ouvre les préférences de l'interface dans une session « <variables> »
		Alors leur titre est « <titre> »

		Exemples:
			| variables        | titre       |
			| LANG=fr_FR.UTF-8 | Préférences |
			| LANG=en_US.UTF-8 | Preferences |

	Scénario: Un message du log, gardé en anglais, se traduit à l'affichage
		Alors le message « dropped stream » du log s'affiche « flux tombé »
		Et le message « No stream follows it. » du log s'affiche « Aucun stream ne le suit. »
		Et le message « purge of database radio, beyond 30 days (before 2026-10-20 12:00): 2 plays of the airplay, 1 line of the log, 0 sound erased » du log s'affiche « purge de la base radio, au-delà de 30 jours (avant le 20/10/2026 à 12:00) : 2 passages de l'airplay, 1 ligne du log, 0 sonore effacés »
		Et le message « a message that no catalogue knows » du log s'affiche « a message that no catalogue knows »

	Scénario: Le catalogue français est à jour et complet
		Quand je vérifie les catalogues de traduction
		Alors la vérification réussit
		Et chaque traduction garde les champs de son message
