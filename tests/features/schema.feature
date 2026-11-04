# language: fr
Fonctionnalité: Schéma de la base de données
	En tant que développeur de MachinCast,
	je veux que les migrations yoyo créent toutes les tables de la spécification,
	afin que la base de production et la base de test aient un schéma strictement identique.

	Un schéma initial, 0001.initial-schema, aux noms anglais (https://github.com/dascritch/machincast/issues/358), que
	suivent les migrations d'après la première release, comme 0002.run-log. Une base
	créée avec l'ancien schéma, aux noms français, celui de 0001.schema-initial ou des migrations d'avant
	https://github.com/dascritch/machincast/issues/314, est refusée, sans rien modifier : elle se recrée.

	Contexte:
		Étant donné une base de test vide où les migrations sont appliquées

	Scénario: Les migrations créent toutes les tables
		Alors la base contient les tables :
			| table            |
			| sounds           |
			| feeds            |
			| banks            |
			| bank_directories |
			| bank_sounds      |
			| events           |
			| event_items      |
			| event_skips      |
			| sequences        |
			| sequence_items   |
			| airplay          |
			| log              |

	Scénario: La purge entre deux scénarios vide chaque table, et remet les identifiants à 1
		https://github.com/dascritch/machincast/issues/280 : la purge vide table par table (tests.database_fixtures.PURGE_ORDER),
		dans un ordre qui respecte les clés étrangères.

		Étant donné les éléments de référence en base
		Quand la base est purgée comme entre deux scénarios
		Alors la purge connaît chaque table de machincast.database.TABLES
		Et chaque table de la base est vide
		Et un nouveau sonore reçoit l'identifiant 1

	Scénario: Chaque type énuméré créé par les migrations est connu de MachinCast
		Alors les types énumérés de la base sont ceux de machincast.database.TYPES

	Scénario: Un sonore peut ne pas avoir de crossfade paramétré, et 0 seconde en est un
		https://github.com/dascritch/machincast/issues/145
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sounds" : type = 'file', location = '/a.flac'
		Alors le sonore « /a.flac » a ses crossfades non paramétrés
		Quand j'enregistre dans "sounds" : type = 'file', location = '/b.flac', crossfade_start = '0 s', crossfade_end = '0 s'
		Alors le sonore « /b.flac » a ses crossfades de 0 seconde

	Scénario: Les migrations s'annulent proprement
		Quand j'annule toutes les migrations
		Alors la base ne contient plus aucune table ni aucun type de MachinCast

	# ─── Ancien schéma, aux noms français (https://github.com/dascritch/machincast/issues/358) ───

	Plan du scénario: Une base créée avec l'ancien schéma, aux noms français, est refusée, sans rien modifier
		Étant donné les éléments de référence en base
		Et la base de test marquée comme ayant reçu l'ancienne migration « <migration> »
		Quand j'applique les migrations
		Alors l'application des migrations est refusée : « base machincast_test : ancien schéma, aux noms français (migration <migration>) ; la recréer, après l'avoir sauvegardée si elle contient quelque chose d'utile : sudo -u postgres dropdb machincast_test, puis ./install.sh »
		Et les migrations appliquées à la base de test sont celles d'avant
		Et la table « sounds » a 1 ligne

		Exemples:
			| migration                        |
			| 0001.schema-initial              |
			| 0015.vocabulaire-silences-blancs |

	Scénario: Une base neuve reçoit le schéma initial, puis les migrations qui le suivent
		https://github.com/dascritch/machincast/issues/341 : 0002.run-log, les démarrages et fins des binaires au log.
		Quand j'annule toutes les migrations
		Et j'applique les migrations
		Alors 2 migrations ont été appliquées
		Et les migrations appliquées à la base de test sont « 0001.initial-schema, 0002.run-log »

	# ─── Connexions (https://github.com/dascritch/machincast/issues/78) ───
	# Le ramasse-miettes est suspendu : une connexion qui n'est pas fermée explicitement reste ouverte.

	Scénario: Appliquer les migrations ne laisse aucune connexion ouverte
		Quand j'applique les migrations, ramasse-miettes suspendu
		Alors aucune connexion supplémentaire à la base de test ne reste ouverte

	Scénario: Annuler les migrations ne laisse aucune connexion ouverte
		Quand j'annule toutes les migrations, ramasse-miettes suspendu
		Alors aucune connexion supplémentaire à la base de test ne reste ouverte

	# ─── Sonores ───────────────────────────────────────────

	Plan du scénario: Un sonore cohérent est accepté
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sounds" : <valeurs>
		Alors la base accepte l'enregistrement

		Exemples:
			| valeurs                                                                                                       |
			| type = 'file', location = '/musique/a.flac'                                                                   |
			| type = 'file', location = '/musique/e.flac', state = 'expired'                                                |
			| type = 'file', location = '/musique/b.flac', duration = '3 min 12 s'                                          |
			| type = 'stream', stream_url = 'https://flux.exemple/direct?SESSIONID=42'                                      |
			| type = 'stream', feed_id = {feed}                                                                             |
			| type = 'file', location = '/c.mp3', broadcast_start = '2026-11-01', broadcast_end = '2026-11-30'              |
			| type = 'file', location = '/d.ogg', music_metadata = '{"year": 1987, "label": "Disques Exemple"}'            |
			| type = 'file', location = '/e.flac', detected_start = '0 s', detected_end = '2.5 s', silence_detection = true |

	Plan du scénario: Un sonore incohérent est refusé
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sounds" : <valeurs>
		Alors la base refuse l'enregistrement

		Exemples:
			| valeurs                                                                                           |
			| type = 'disque', location = '/musique/a.flac'                                                     |
			| type = 'file', location = '/musique/a.flac', state = 'inactif'                                    |
			| type = 'file'                                                                                     |
			| type = 'file', location = '/a.flac', stream_url = 'https://flux.exemple'                          |
			| type = 'stream'                                                                                   |
			| type = 'stream', stream_url = 'https://flux.exemple', feed_id = {feed}                            |
			| type = 'stream', stream_url = 'https://flux.exemple', location = '/a.flac'                        |
			| type = 'stream', stream_url = 'https://flux.exemple', duration = '1 min'                          |
			| type = 'file', location = '/a.flac', crossfade_start = '-2 s'                                     |
			| type = 'file', location = '/a.flac', max_plays = 0                                                |
			| type = 'file', location = '/a.flac', broadcast_start = '2026-11-30', broadcast_end = '2026-11-01' |
			| type = 'file', location = '/a.flac', music_metadata = '[1987]'                                    |
			| type = 'file', location = '/a.flac', music_metadata = 'null'                                      |
			| type = 'file', location = '/a.flac', detected_start = '-0.1 s'                                    |
			| type = 'file', location = '/a.flac', detected_end = '-1 s'                                        |
			| type = 'file', location = '/a.flac', silence_detection = NULL                                     |
			| type = 'file', location = '/a.flac', audit_requested = NULL                                       |
			| type = 'file', location = '/a.flac', audited_at = now()                                           |
			| type = 'file', location = '/a.flac', audit_threshold = -40                                        |
			| type = 'file', location = '/a.flac', audited_at = now(), audit_threshold = 0                      |
			| type = 'file', location = '/a.flac', audited_at = now(), audit_threshold = -100.5                 |

	Scénario: Deux sonores ne peuvent pas avoir le même emplacement
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sounds" : type = 'file', location = '/musique/a.flac'
		Et j'enregistre dans "sounds" : type = 'file', location = '/musique/a.flac'
		Alors la base refuse l'enregistrement

	# ─── Suppression différée (https://github.com/dascritch/machincast/issues/267) ───

	Plan du scénario: Un élément supprimé libère son nom, ou son emplacement, pour un nouvel élément
		Quand j'enregistre dans "<table>" : <valeurs>, deleted_at = now()
		Et j'enregistre dans "<table>" : <valeurs>
		Alors la base accepte l'enregistrement
		Quand j'enregistre dans "<table>" : <valeurs>
		Alors la base refuse l'enregistrement

		Exemples:
			| table      | valeurs                                                         |
			| sounds    | type = 'file', location = '/musique/a.flac'                     |
			| banks    | internal_name = 'Jingles', mode = 'random'                      |
			| sequences  | internal_name = 'Ouverture'                                     |
			| events | internal_name = 'Matinale', priority = 'background_programming' |

	Scénario: La date de modification est tenue à jour
		Étant donné les éléments de référence en base
		Quand je modifie le titre du sonore de référence
		Alors sa date de modification a avancé

	# ─── Banques ───────────────────────────────────────────

	Plan du scénario: Une banque incohérente est refusée
		Quand j'enregistre dans "banks" : <valeurs>
		Alors la base refuse l'enregistrement

		Exemples:
			| valeurs                                                                                    |
			| internal_name = 'Jingles', mode = 'melange'                                                |
			| mode = 'random'                                                                            |
			| internal_name = 'Jingles', mode = 'random', no_repeat = NULL                               |
			| internal_name = 'Jingles', mode = 'random', crossfade_start = '-1 s'                       |
			| internal_name = 'Jingles', mode = 'random', crossfade_end = '-1 s'                         |
			| internal_name = 'Jingles', mode = 'random', crossfade_start = NULL                         |
			| internal_name = 'Jingles', mode = 'random', crossfade_end_rule = 'toujours'                |
			| internal_name = 'Jingles', mode = 'random', crossfade_start_rule = NULL                    |
			| internal_name = 'Jingles', mode = 'random', min_duration = '0 s'                           |
			| internal_name = 'Jingles', mode = 'random', max_duration = '-1 s'                          |
			| internal_name = 'Jingles', mode = 'random', min_duration = '2 min', max_duration = '1 min' |
			| internal_name = 'Jingles', mode = 'random', silence_detection = NULL                       |

	# https://github.com/dascritch/machincast/issues/63

	Scénario: Une banque n'est pas marquée « ne pas répéter » par défaut
		Étant donné les éléments de référence en base
		Alors la banque de référence n'est pas marquée « ne pas répéter »

	# https://github.com/dascritch/machincast/issues/146

	Scénario: La détection de silence n'est activée par défaut ni pour une banque, ni pour un sonore, qui n'ont aucun silence détecté
		Étant donné les éléments de référence en base
		Alors la banque de référence n'active pas la détection de silence
		Et le sonore de référence n'active pas la détection de silence
		Et le sonore de référence n'a ni début ni fin détectés

	# https://github.com/dascritch/machincast/issues/114

	Scénario: Un sonore n'a pas d'audit complet demandé par défaut
		Étant donné les éléments de référence en base
		Alors le sonore de référence n'a pas d'audit complet demandé

	Scénario: Une banque peut avoir plusieurs répertoires
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "bank_directories" : bank_id = {banque}, directory = '/habillages/hors-saison'
		Et j'enregistre dans "bank_directories" : bank_id = {banque}, directory = '/habillages/hiver'
		Et j'enregistre dans "bank_directories" : bank_id = {banque}, directory = '/habillages/noel'
		Alors la base accepte l'enregistrement

	Scénario: Un même répertoire peut servir à plusieurs banques
		Étant donné les éléments de référence en base
		Et une deuxième banque en base
		Quand j'enregistre dans "bank_directories" : bank_id = {banque}, directory = '/habillages/hors-saison'
		Et j'enregistre dans "bank_directories" : bank_id = {banque2}, directory = '/habillages/hors-saison'
		Alors la base accepte l'enregistrement

	Scénario: Un répertoire ne figure qu'une fois dans une banque
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "bank_directories" : bank_id = {banque}, directory = '/habillages/noel'
		Et j'enregistre dans "bank_directories" : bank_id = {banque}, directory = '/habillages/noel'
		Alors la base refuse l'enregistrement

	Scénario: Un sonore ne figure qu'une fois dans une banque
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "bank_sounds" : bank_id = {banque}, sound_id = {sonore}, position = 1
		Et j'enregistre dans "bank_sounds" : bank_id = {banque}, sound_id = {sonore}, position = 2
		Alors la base refuse l'enregistrement

	Scénario: Deux sonores ne partagent pas la même position dans une banque
		Étant donné les éléments de référence en base
		Et un deuxième sonore en base
		Quand j'enregistre dans "bank_sounds" : bank_id = {banque}, sound_id = {sonore}, position = 1
		Et j'enregistre dans "bank_sounds" : bank_id = {banque}, sound_id = {sonore2}, position = 1
		Alors la base refuse l'enregistrement

	# ─── Événements ────────────────────────────────────────

	Plan du scénario: Un événement cohérent est accepté
		Quand j'enregistre dans "events" : <valeurs>
		Alors la base accepte l'enregistrement

		Exemples:
			| valeurs                                                                                                                                                                                                   |
			| internal_name = 'Fil permanent', priority = 'background_programming'                                                                                                                                      |
			| internal_name = 'Nuit', priority = 'background_programming', starts_at = '2026-10-14 22:00', ends_at = '2026-10-15 06:00', recurrence_days = '{monday,tuesday,wednesday,thursday,friday,saturday,sunday}' |
			| internal_name = 'Magazine', priority = 'show', starts_at = '2026-10-19 18:00', ends_at = '2026-10-19 19:00', recurrence_days = '{monday,tuesday,wednesday,thursday,friday}'                               |
			| internal_name = 'Rediffusion', priority = 'special', starts_at = '2026-10-20 14:00'                                                                                                                       |
			| internal_name = 'Secours direct', priority = 'fallback'                                                                                                                                                   |

	Plan du scénario: Un événement incohérent est refusé
		Quand j'enregistre dans "events" : <valeurs>
		Alors la base refuse l'enregistrement

		Exemples:
			| valeurs                                                                                                  |
			| internal_name = 'X', priority = 'urgence', starts_at = '2026-10-19 18:00'                                |
			| internal_name = 'X', priority = 'show'                                                                   |
			| internal_name = 'X', priority = 'special', ends_at = '2026-10-19 19:00'                                  |
			| internal_name = 'X', priority = 'background_programming', ends_at = '2026-10-19 19:00'                   |
			| internal_name = 'X', priority = 'show', starts_at = '2026-10-19 19:00', ends_at = '2026-10-19 18:00'     |
			| internal_name = 'X', priority = 'show', starts_at = '2026-10-19 18:00', recurrence_days = '{lundy}'      |
			| internal_name = 'X', priority = 'show', starts_at = '2026-10-19 18:00', recurrence_days = '{1}'          |
			| internal_name = 'X', priority = 'fallback', starts_at = '2026-10-19 18:00'                               |
			| internal_name = 'X', priority = 'fallback', starts_at = '2026-10-19 18:00', ends_at = '2026-10-19 19:00' |
			| internal_name = 'X', priority = 'fallback', recurrence_days = '{monday}'                                  |

	Scénario: Deux événements n'ont pas le même nom interne
		# https://github.com/dascritch/machincast/issues/32
		Quand j'enregistre dans "events" : internal_name = 'Continue', priority = 'background_programming'
		Et j'enregistre dans "events" : internal_name = 'Continue', priority = 'fallback'
		Alors la base refuse l'enregistrement

	Scénario: Les priorités sont ordonnées
		Alors la priorité "fallback" est inférieure à "background_programming"
		Et la priorité "background_programming" est inférieure à "show"
		Et la priorité "show" est inférieure à "special"

	# ─── Secours d'un stream (https://github.com/dascritch/machincast/issues/16) ───

	Plan du scénario: Seul un stream désigne un événement de secours, et seulement de priorité secours
		Étant donné les éléments de référence en base
		Et un événement de secours en base
		Quand j'enregistre dans "sounds" : <valeurs>
		Alors la base <verdict> l'enregistrement

		Exemples:
			| valeurs                                                                                 | verdict |
			| type = 'stream', stream_url = 'https://flux.exemple/a', fallback_event_id = {secours}   | accepte |
			| type = 'stream', stream_url = 'https://flux.exemple/b'                                  | accepte |
			| type = 'file', location = '/a.flac', fallback_event_id = {secours}                      | refuse  |
			| type = 'stream', stream_url = 'https://flux.exemple/c', fallback_event_id = {evenement} | refuse  |

	Scénario: Un événement de secours désigné par un stream garde sa priorité
		Étant donné les éléments de référence en base
		Et un événement de secours en base
		Et un stream secouru par cet événement
		Quand je passe l'événement de secours en émission
		Alors la base refuse l'enregistrement

	Scénario: Supprimer l'événement de secours laisse le stream sans secours
		Étant donné les éléments de référence en base
		Et un événement de secours en base
		Et un stream secouru par cet événement
		Quand je supprime l'événement de secours
		Alors le stream n'a plus d'événement de secours

	# ─── Sessions sautées (https://github.com/dascritch/machincast/issues/273) ───

	Scénario: Une session ne se saute qu'une fois
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "event_skips" : event_id = {evenement}, day = '2026-10-21'
		Et j'enregistre dans "event_skips" : event_id = {evenement}, day = '2026-10-21'
		Alors la base refuse l'enregistrement

	Scénario: Les sessions sautées partent avec leur événement
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "event_skips" : event_id = {evenement}, day = '2026-10-21'
		Et je supprime l'événement de référence
		Alors aucune session n'est sautée en base

	Scénario: Les jours de la semaine sont ordonnés du lundi au dimanche
		Alors le jour "monday" vient avant "sunday"

	Plan du scénario: Un élément de liste de lecture est une banque ou un sonore
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "event_items" : event_id = {evenement}, position = 1<complement>
		Alors la base <verdict> l'enregistrement

		Exemples:
			| complement                                      | verdict |
			| , bank_id = {banque}                            | accepte |
			| , sound_id = {sonore}                           | accepte |
			|                                                 | refuse  |
			| , bank_id = {banque}, sound_id = {sonore}       | refuse  |
			| , sequence_id = {sequence}                      | accepte |
			| , sequence_id = {sequence}, sound_id = {sonore} | refuse  |
			| , sequence_id = {sequence}, bank_id = {banque}  | refuse  |

	# ─── Séquences (https://github.com/dascritch/machincast/issues/99) ───

	Plan du scénario: Une séquence incohérente est refusée
		Quand j'enregistre dans "sequences" : <valeurs>
		Alors la base refuse l'enregistrement

		Exemples:
			| valeurs                                            |
			| public_name = 'Vous écoutez Radio Thune'           |
			| internal_name = 'Pub', hide_metadata = 'peut-être' |

	Scénario: Deux séquences n'ont pas le même nom interne
		Quand j'enregistre dans "sequences" : internal_name = 'Pub'
		Et j'enregistre dans "sequences" : internal_name = 'Pub'
		Alors la base refuse l'enregistrement

	Plan du scénario: Un élément de séquence est une banque ou un sonore, jamais une autre séquence
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sequence_items" : sequence_id = {sequence}, position = 1<complement>
		Alors la base <verdict> l'enregistrement

		Exemples:
			| complement                                | verdict |
			| , bank_id = {banque}                      | accepte |
			| , sound_id = {sonore}                     | accepte |
			|                                           | refuse  |
			| , bank_id = {banque}, sound_id = {sonore} | refuse  |
			| , position = 0, sound_id = {sonore}       | refuse  |

	Scénario: Une séquence fait revenir un même élément, chacun à sa position
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sequence_items" : sequence_id = {sequence}, position = 1, sound_id = {sonore}
		Et j'enregistre dans "sequence_items" : sequence_id = {sequence}, position = 2, bank_id = {banque}
		Et j'enregistre dans "sequence_items" : sequence_id = {sequence}, position = 3, bank_id = {banque}
		Alors la base accepte l'enregistrement

	Scénario: Deux éléments d'une séquence ne partagent pas la même position
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sequence_items" : sequence_id = {sequence}, position = 1, sound_id = {sonore}
		Et j'enregistre dans "sequence_items" : sequence_id = {sequence}, position = 1, bank_id = {banque}
		Alors la base refuse l'enregistrement

	Scénario: La date de modification d'une séquence est tenue à jour
		Étant donné les éléments de référence en base
		Quand je modifie le nom public de la séquence de référence
		Alors sa date de modification a avancé

	Scénario: L'airplay note la séquence et son élément joué, et les garde vides quand ils sont supprimés
		Étant donné les éléments de référence en base
		Et un élément de la séquence de référence, joué dans l'airplay
		Quand je supprime la séquence de référence
		Alors la ligne d'airplay existe toujours, sans référence à la séquence ni à son élément

	Scénario: Supprimer une séquence la retire des événements qui l'utilisaient
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "event_items" : event_id = {evenement}, position = 1, sequence_id = {sequence}
		Et je supprime la séquence de référence
		Alors l'événement de référence n'a plus d'élément

	Scénario: Un même jingle peut revenir plusieurs fois dans une liste
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "event_items" : event_id = {evenement}, position = 1, sound_id = {sonore}
		Et j'enregistre dans "event_items" : event_id = {evenement}, position = 2, bank_id = {banque}
		Et j'enregistre dans "event_items" : event_id = {evenement}, position = 3, sound_id = {sonore}
		Alors la base accepte l'enregistrement

	# ─── Airplay et log ────────────────────────────────────

	Plan du scénario: Les lignes d'airplay respectent leur type
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "airplay" : play_id = '7f0c1c2e-5d39-4a87-9a52-0c3c8c1f9a01', <valeurs>
		Alors la base <verdict> l'enregistrement

		Exemples:
			| valeurs                                                               | verdict |
			| line_type = 'start', sound_id = {sonore}, bank_id = {banque}          | accepte |
			| line_type = 'end', played_duration = '3 min', without_incident = true | accepte |
			| line_type = 'start', played_duration = '3 min'                        | refuse  |
			| line_type = 'end', without_incident = true                            | refuse  |
			| line_type = 'milieu'                                                  | refuse  |

	Scénario: Un passage n'a qu'une ligne de début
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "airplay" : play_id = '7f0c1c2e-5d39-4a87-9a52-0c3c8c1f9a01', line_type = 'start'
		Et j'enregistre dans "airplay" : play_id = '7f0c1c2e-5d39-4a87-9a52-0c3c8c1f9a01', line_type = 'start'
		Alors la base refuse l'enregistrement

	Scénario: L'airplay survit à la suppression du sonore
		Étant donné les éléments de référence en base
		Et un passage du sonore de référence dans l'airplay
		Quand je supprime le sonore de référence
		Alors la ligne d'airplay existe toujours, avec son titre recopié et sans référence au sonore

	Scénario: L'airplay note l'élément d'événement joué, et le garde vide quand l'élément est supprimé
		Étant donné les éléments de référence en base
		Et un élément de l'événement de référence, joué dans l'airplay
		Quand je supprime cet élément de l'événement
		Alors la ligne d'airplay existe toujours, sans référence à l'élément

	Plan du scénario: Le log n'accepte que les niveaux connus
		Quand j'enregistre dans "log" : level = '<niveau>', kind = 'demarrage'
		Alors la base <verdict> l'enregistrement

		Exemples:
			| niveau   | verdict |
			| info     | accepte |
			| warning   | accepte |
			| incident | accepte |
			| debug    | refuse  |

	# ─── Longueur des textes courts ────────────────────────

	Plan du scénario: Les textes saisis à la main sont limités à 255 caractères
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "<table>" : <autres>, <colonne> = repeat('é', <longueur>)
		Alors la base <verdict> l'enregistrement

		Exemples:
			| table      | autres                                                   | colonne     | longueur | verdict |
			| feeds      | url = 'https://flux.exemple'                             | name         | 255      | accepte |
			| feeds      | url = 'https://flux.exemple'                             | name         | 256      | refuse  |
			| sounds    | type = 'file', location = '/long/artiste.flac'           | artist     | 255      | accepte |
			| sounds    | type = 'file', location = '/long/artiste.flac'           | artist     | 256      | refuse  |
			| sounds    | type = 'file', location = '/long/titre.flac'             | title       | 256      | refuse  |
			| banks    | mode = 'random'                                          | internal_name | 255      | accepte |
			| banks    | mode = 'random'                                          | internal_name | 256      | refuse  |
			| banks    | mode = 'random', internal_name = 'X'                     | public_name  | 255      | accepte |
			| banks    | mode = 'random', internal_name = 'X'                     | public_name  | 256      | refuse  |
			| sequences  | public_name = 'Pub'                                      | internal_name | 255      | accepte |
			| sequences  | public_name = 'Pub'                                      | internal_name | 256      | refuse  |
			| sequences  | internal_name = 'X'                                      | public_name  | 256      | refuse  |
			| events | priority = 'background_programming'                      | internal_name | 255      | accepte |
			| events | priority = 'background_programming'                      | internal_name | 256      | refuse  |
			| events | priority = 'background_programming', internal_name = 'X' | public_name  | 256      | refuse  |
			| airplay    | play_id = gen_random_uuid(), line_type = 'start'         | artist     | 256      | refuse  |
			| airplay    | play_id = gen_random_uuid(), line_type = 'start'         | title       | 256      | refuse  |
			| log        | level = 'info'                                           | kind      | 255      | accepte |
			| log        | level = 'info'                                           | kind      | 256      | refuse  |

	Plan du scénario: Les chemins, URL et messages ne sont pas limités à 255 caractères
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "<table>" : <autres>, <colonne> = '<prefixe>' || repeat('x', 1000)
		Alors la base accepte l'enregistrement

		Exemples:
			| table               | autres                            | colonne     | prefixe                          |
			| sounds             | type = 'file'                     | location | /musique/                        |
			| sounds             | type = 'stream'                   | stream_url  | https://flux.exemple/?SESSIONID= |
			| feeds               | name = 'Long'                     | url         | https://flux.exemple/            |
			| bank_directories | bank_id = {banque}                | directory  | /habillages/                     |
			| log                 | level = 'incident', kind = 'flux' | message     | Détail :                         |
