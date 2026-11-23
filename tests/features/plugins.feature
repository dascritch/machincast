# language: fr
Fonctionnalité: Le socle des plugins
	https://github.com/dascritch/machincast/issues/585, ticket enfant de
	https://github.com/dascritch/machincast/issues/348 : un plugin est un répertoire de plugins/, avec son
	manifest.json, son check.py facultatif et son paquet Python dans src/machincast_<nom>/. Activé dans
	machincast.toml, section [plugins], il est chargé par les binaires où il s'accroche, s'il est activable ; ses
	fonctions s'abonnent aux points d'extension. Les plugins de ces scénarios sont créés dans un répertoire temporaire,
	désigné par [plugins] directory.

	Scénario: Un plugin valide est découvert, avec son nom, sa version et sa description dans la langue de MachinCast
		Étant donné le plugin « horloge » 1.2.0, pour « Machin_player », décrit « Speaks the time » et en français « Dit l'heure »
		Quand MachinCast cherche ses plugins
		Alors il trouve « horloge » 1.2.0, « horloge », « Dit l'heure »

	Plan du scénario: Un manifest invalide est refusé avec sa raison
		Étant donné le plugin « horloge » dont le manifest a <défaut>
		Quand MachinCast cherche ses plugins
		Alors il trouve « horloge », refusé parce que « <raison> »

		Exemples:
			| défaut                                  | raison                                                                    |
			| aucun fichier                           | pas de manifest.json                                                      |
			| un JSON illisible                       | manifest.json illisible                                                   |
			| le nom « pendule »                      | name : « pendule », mais le répertoire est « horloge »                    |
			| la version « un »                       | version : « un » n'est pas une version, comme 1.0.2                       |
			| une description de 201 caractères       | description : 200 caractères au plus                                      |
			| le binaire « Machin_cafetiere »         | binaries : inconnu Machin_cafetiere                                       |
			| aucun binaire                           | binaries : au moins un binaire est attendu                                |
			| la clé « auteur »                       | clé inconnue auteur                                                       |
			| les versions de MachinCast « bientôt »  | machincast : « bientôt » n'est pas un spécificateur de versions, comme « >=1.0,<2 » |
			| la langue « tlh »                       | l10n : langue inconnue « tlh »                                            |

	Scénario: Un répertoire au nom invalide est refusé
		Étant donné le répertoire de plugin « mon plugin »
		Quand MachinCast cherche ses plugins
		Alors il trouve « mon plugin », refusé parce que « « mon plugin » n'est pas un nom de plugin : lettres, chiffres, « _ » et « - » seulement »

	Scénario: Un plugin activé est chargé dans les binaires où il s'accroche, et pas ailleurs
		Étant donné le plugin « horloge » 1.2.0, pour « Machin_player », décrit « Speaks the time » et en français « Dit l'heure »
		Et les plugins activés « horloge »
		Quand « Machin_player » charge ses plugins
		Alors les plugins chargés sont « horloge »
		Et le journal dit « plugin « horloge » 1.2.0 chargé »
		Quand « Machin_indexer » charge ses plugins
		Alors aucun plugin n'est chargé

	Scénario: Un plugin qui n'est pas activé n'est pas chargé
		Étant donné le plugin « horloge » 1.2.0, pour « Machin_player », décrit « Speaks the time » et en français « Dit l'heure »
		Quand « Machin_player » charge ses plugins
		Alors aucun plugin n'est chargé

	Plan du scénario: Un plugin activé mais pas activable est écarté avec ses raisons, et le binaire démarre quand même
		Étant donné le plugin « horloge » 1.2.0, pour « Machin_player », décrit « Speaks the time » et en français « Dit l'heure »
		Et que le plugin « horloge » demande <demande>
		Et les plugins activés « horloge »
		Quand « Machin_player » charge ses plugins
		Alors aucun plugin n'est chargé
		Et « horloge » est écarté parce que « <raison> »

		Exemples:
			| demande                                   | raison                                                                  |
			| le programme « cafetiere-introuvable »    | le programme « cafetiere-introuvable » manque                           |
			| le module Python « module_introuvable »   | le module Python « module_introuvable » manque                          |
			| le plugin « pendule » >=1.0               | il demande le plugin « pendule », qui n'est pas activé                  |
			| MachinCast >=999                          | MachinCast {machincast} n'est pas de ses versions, >=999                |
			| un check.py qui répond « pas de carte son » | pas de carte son                                                      |
			| un check.py qui plante                    | son check.py a échoué : boum                                            |

	Scénario: Un plugin enregistré avec une erreur est écarté, sans empêcher les autres
		Étant donné le plugin « horloge » 1.2.0, pour « Machin_player », décrit « Speaks the time » et en français « Dit l'heure »
		Et le plugin « pendule » 1.0.0, pour « Machin_player », décrit « Swings » et en français « Balance »
		Et que le register du plugin « horloge » plante
		Et les plugins activés « horloge », « pendule »
		Quand « Machin_player » charge ses plugins
		Alors les plugins chargés sont « pendule »
		Et « horloge » est écarté parce que « boum »

	Scénario: Un plugin est chargé après ceux qu'il demande, et dans la version qu'il demande
		Étant donné le plugin « horloge » 1.2.0, pour « Machin_player », décrit « Speaks the time » et en français « Dit l'heure »
		Et le plugin « aiguille » 1.0.0, pour « Machin_player », décrit « Hands » et en français « Aiguilles »
		Et que le plugin « aiguille » demande le plugin « horloge » >=1.0
		Et les plugins activés « aiguille », « horloge »
		Quand « Machin_player » charge ses plugins
		Alors les plugins chargés sont « horloge », « aiguille »
		Et le contexte de « aiguille » connaît les plugins « horloge » 1.2.0, « aiguille » 1.0.0, et la version de MachinCast

	Scénario: Un plugin qui demande une autre version d'un plugin est écarté
		Étant donné le plugin « horloge » 1.2.0, pour « Machin_player », décrit « Speaks the time » et en français « Dit l'heure »
		Et le plugin « aiguille » 1.0.0, pour « Machin_player », décrit « Hands » et en français « Aiguilles »
		Et que le plugin « aiguille » demande le plugin « horloge » >=2
		Et les plugins activés « aiguille », « horloge »
		Quand « Machin_player » charge ses plugins
		Alors les plugins chargés sont « horloge »
		Et « aiguille » est écarté parce que « il demande le plugin « horloge » >=2, 1.2.0 trouvé »

	Scénario: Des plugins qui se demandent en cercle sont écartés
		Étant donné le plugin « horloge » 1.2.0, pour « Machin_player », décrit « Speaks the time » et en français « Dit l'heure »
		Et le plugin « aiguille » 1.0.0, pour « Machin_player », décrit « Hands » et en français « Aiguilles »
		Et que le plugin « aiguille » demande le plugin « horloge » >=1.0
		Et que le plugin « horloge » demande le plugin « aiguille » >=1.0
		Et les plugins activés « aiguille », « horloge »
		Quand « Machin_player » charge ses plugins
		Alors aucun plugin n'est chargé
		Et « horloge » est écarté parce que « il se demande lui-même, par les plugins qu'il demande »

	Scénario: Un plugin reçoit ses réglages, la section [plugins.<nom>] de machincast.toml
		Étant donné le plugin « horloge » 1.2.0, pour « Machin_player », décrit « Speaks the time » et en français « Dit l'heure »
		Et les plugins activés « horloge », réglé par « format = "%H:%M" »
		Quand « Machin_player » charge ses plugins
		Alors le contexte de « horloge » a pour réglages « format » = « %H:%M »

	Plan du scénario: La section [plugins] de machincast.toml refuse ce qui n'est pas un plugin
		Étant donné une configuration dont la section [plugins] contient « <contenu> »
		Quand la configuration est chargée
		Alors elle est refusée parce que « <raison> »

		Exemples:
			| contenu                          | raison                                                          |
			| enabled = "horloge"              | clé plugins.enabled : une liste de noms de plugins est attendue |
			| enabled = ["mon plugin"]         | clé plugins.enabled : « mon plugin » n'est pas un nom de plugin |
			| enabled = ["horloge", "horloge"] | clé plugins.enabled : « horloge » est donné deux fois           |
			| couleur = "rouge"                | clé plugins.couleur inconnue                                    |

	# ─── Points d'extension ───

	Scénario: Une notification prévient chaque abonné sans attendre, et l'erreur d'un abonné ne gêne ni l'appelant ni les autres
		Étant donné un registre où « horloge » déclare le point « horloge.tic »
		Et que « horloge » s'abonne à « horloge.tic » en plantant
		Et que « pendule » s'abonne à « horloge.tic » en notant ce qu'il reçoit
		Quand le point « horloge.tic » est notifié avec « heure » = « 12:00 »
		Alors la notification est rendue avant la fin des abonnés
		Et « pendule » reçoit « heure » = « 12:00 »
		Et le journal dit « le plugin « horloge » a échoué au point d'extension « horloge.tic » : boum »

	Scénario: Une demande rassemble la réponse de chaque abonné, dans l'ordre, sans celle qui échoue
		Étant donné un registre où « horloge » déclare le point « horloge.pages »
		Et que « horloge » s'abonne à « horloge.pages » en répondant « accueil »
		Et que « aiguille » s'abonne à « horloge.pages » en plantant
		Et que « pendule » s'abonne à « horloge.pages » en répondant « balancier »
		Quand le point « horloge.pages » est demandé
		Alors les réponses sont « horloge » « accueil », « pendule » « balancier »

	Scénario: Un plugin ne s'abonne qu'à un point déclaré, et ne déclare que les siens
		Étant donné un registre où « horloge » déclare le point « horloge.tic »
		Alors s'abonner au point « horloge.tac » est refusé parce que « point d'extension inconnu « horloge.tac » »
		Et « pendule » ne peut pas déclarer le point « horloge.toc »
