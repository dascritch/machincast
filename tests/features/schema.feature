# language: fr
Fonctionnalité: Schéma de la base de données
	En tant que développeur de MachinCast,
	je veux que les migrations yoyo créent toutes les tables de la spécification,
	afin que la base de production et la base de test aient un schéma strictement identique.

	Contexte:
		Étant donné une base de test vide où les migrations sont appliquées

	Scénario: Les migrations créent toutes les tables
		Alors la base contient les tables :
			| table                 |
			| sonores               |
			| feeds                 |
			| banques               |
			| banques_repertoires   |
			| banques_sonores       |
			| evenements            |
			| evenements_elements   |
			| sequences             |
			| sequences_elements    |
			| airplay               |
			| log                   |

	Scénario: Chaque type énuméré créé par les migrations est connu de MachinCast
		Alors les types énumérés de la base sont ceux de machincast.base.TYPES

	Scénario: Un sonore peut ne pas avoir de crossfade paramétré, et 0 seconde en est un
		https://github.com/dascritch/machincast/issues/145
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sonores" : type = 'fichier', emplacement = '/a.flac'
		Alors le sonore « /a.flac » a ses crossfades non paramétrés
		Quand j'enregistre dans "sonores" : type = 'fichier', emplacement = '/b.flac', crossfade_debut = '0 s', crossfade_fin = '0 s'
		Alors le sonore « /b.flac » a ses crossfades de 0 seconde

	Scénario: La migration des crossfades facultatifs ne garde que les crossfades saisis à la main
		https://github.com/dascritch/machincast/issues/145 : un crossfade de 0 seconde que personne n'a saisi n'était qu'une valeur par défaut ;
		saisi à la main (champs_edites), 0 seconde compris, il est gardé.

		Quand j'annule les migrations depuis « 0007.sonores-crossfades-facultatifs »
		Et j'enregistre les sonores aux crossfades :
			| emplacement | crossfade_debut | crossfade_fin | champs_edites                     |
			| /a.flac     | 0 s             | 0 s           |                                   |
			| /b.flac     | 0 s             | 2 s           | crossfade_debut                   |
			| /c.flac     | 1 s             | 0 s           | crossfade_debut, crossfade_fin    |
			| /d.flac     | 3 s             | 0 s           |                                   |
		Et j'applique les migrations
		Alors les crossfades des sonores sont :
			| emplacement | crossfade_debut | crossfade_fin |
			| /a.flac     |                 |               |
			| /b.flac     | 0 s             |               |
			| /c.flac     | 1 s             | 0 s           |
			| /d.flac     |                 |               |
		Quand j'annule les migrations depuis « 0007.sonores-crossfades-facultatifs »
		Alors les crossfades des sonores sont :
			| emplacement | crossfade_debut | crossfade_fin |
			| /a.flac     | 0 s             | 0 s           |
			| /b.flac     | 0 s             | 0 s           |
			| /c.flac     | 1 s             | 0 s           |
			| /d.flac     | 0 s             | 0 s           |

	Scénario: Les migrations s'annulent proprement
		Quand j'annule toutes les migrations
		Alors la base ne contient plus aucune table ni aucun type de MachinCast

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
		Quand j'enregistre dans "sonores" : <valeurs>
		Alors la base accepte l'enregistrement

		Exemples:
			| valeurs                                                                   |
			| type = 'fichier', emplacement = '/musique/a.flac'                         |
			| type = 'fichier', emplacement = '/musique/e.flac', etat = 'expire'        |
			| type = 'fichier', emplacement = '/musique/b.flac', duree = '3 min 12 s'   |
			| type = 'stream', url_stream = 'https://flux.exemple/direct?SESSIONID=42'  |
			| type = 'stream', feed_id = {feed}                           |
			| type = 'fichier', emplacement = '/c.mp3', debut_diffusion = '2026-11-01', fin_diffusion = '2026-11-30' |
			| type = 'fichier', emplacement = '/d.ogg', metadonnees_musicales = '{"annee": 1987, "label": "Disques Exemple"}' |
			| type = 'fichier', emplacement = '/e.flac', debut_detecte = '0 s', fin_detectee = '2.5 s', detection_blancs = true |

	Plan du scénario: Un sonore incohérent est refusé
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sonores" : <valeurs>
		Alors la base refuse l'enregistrement

		Exemples:
			| valeurs                                                                         |
			| type = 'disque', emplacement = '/musique/a.flac'                                |
			| type = 'fichier', emplacement = '/musique/a.flac', etat = 'inactif'             |
			| type = 'fichier'                                                                |
			| type = 'fichier', emplacement = '/a.flac', url_stream = 'https://flux.exemple'  |
			| type = 'stream'                                                                 |
			| type = 'stream', url_stream = 'https://flux.exemple', feed_id = {feed} |
			| type = 'stream', url_stream = 'https://flux.exemple', emplacement = '/a.flac'   |
			| type = 'stream', url_stream = 'https://flux.exemple', duree = '1 min'           |
			| type = 'fichier', emplacement = '/a.flac', crossfade_debut = '-2 s'             |
			| type = 'fichier', emplacement = '/a.flac', max_lectures = 0                     |
			| type = 'fichier', emplacement = '/a.flac', debut_diffusion = '2026-11-30', fin_diffusion = '2026-11-01' |
			| type = 'fichier', emplacement = '/a.flac', metadonnees_musicales = '[1987]'                     |
			| type = 'fichier', emplacement = '/a.flac', metadonnees_musicales = 'null'                       |
			| type = 'fichier', emplacement = '/a.flac', debut_detecte = '-0.1 s'                             |
			| type = 'fichier', emplacement = '/a.flac', fin_detectee = '-1 s'                                |
			| type = 'fichier', emplacement = '/a.flac', detection_blancs = NULL                              |
			| type = 'fichier', emplacement = '/a.flac', audit_demande = NULL                                 |
			| type = 'fichier', emplacement = '/a.flac', audite_le = now()                                     |
			| type = 'fichier', emplacement = '/a.flac', audit_seuil = -40                                    |
			| type = 'fichier', emplacement = '/a.flac', audite_le = now(), audit_seuil = 0                   |
			| type = 'fichier', emplacement = '/a.flac', audite_le = now(), audit_seuil = -100.5              |

	Scénario: Deux sonores ne peuvent pas avoir le même emplacement
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sonores" : type = 'fichier', emplacement = '/musique/a.flac'
		Et j'enregistre dans "sonores" : type = 'fichier', emplacement = '/musique/a.flac'
		Alors la base refuse l'enregistrement

	# ─── Suppression différée (https://github.com/dascritch/machincast/issues/267) ───

	Plan du scénario: Un élément supprimé libère son nom, ou son emplacement, pour un nouvel élément
		Quand j'enregistre dans "<table>" : <valeurs>, supprime_le = now()
		Et j'enregistre dans "<table>" : <valeurs>
		Alors la base accepte l'enregistrement
		Quand j'enregistre dans "<table>" : <valeurs>
		Alors la base refuse l'enregistrement

		Exemples:
			| table      | valeurs                                            |
			| sonores    | type = 'fichier', emplacement = '/musique/a.flac'  |
			| banques    | nom_interne = 'Jingles', mode = 'aleatoire'        |
			| sequences  | nom_interne = 'Ouverture'                          |
			| evenements | nom_interne = 'Matinale', priorite = 'fil_musical' |

	Scénario: Annuler la migration de la suppression différée efface les éléments supprimés
		Quand j'enregistre dans "banques" : nom_interne = 'Jingles', mode = 'aleatoire', supprime_le = now()
		Et j'enregistre dans "banques" : nom_interne = 'Jingles', mode = 'aleatoire'
		Et j'annule les migrations depuis « 0013.suppression-differee »
		Alors la table « banques » a 1 ligne
		Quand j'applique les migrations
		Alors aucune connexion supplémentaire à la base de test ne reste ouverte

	Scénario: La migration date la disparition des sonores déjà à l'état supprimé
		Quand j'annule les migrations depuis « 0013.suppression-differee »
		Et j'enregistre dans "sonores" : type = 'fichier', emplacement = '/a.flac', etat = 'supprime'
		Et j'enregistre dans "sonores" : type = 'fichier', emplacement = '/b.flac', etat = 'actif'
		Et j'applique les migrations
		Alors le sonore « /a.flac » a une date de disparition
		Et le sonore « /b.flac » n'a pas de date de disparition

	Scénario: La date de modification est tenue à jour
		Étant donné les éléments de référence en base
		Quand je modifie le titre du sonore de référence
		Alors sa date de modification a avancé

	# ─── Banques ───────────────────────────────────────────

	Plan du scénario: Une banque incohérente est refusée
		Quand j'enregistre dans "banques" : <valeurs>
		Alors la base refuse l'enregistrement

		Exemples:
			| valeurs                                        |
			| nom_interne = 'Jingles', mode = 'melange'      |
			| mode = 'aleatoire'                             |
			| nom_interne = 'Jingles', mode = 'aleatoire', ne_pas_repeter = NULL |
			| nom_interne = 'Jingles', mode = 'aleatoire', crossfade_debut = '-1 s' |
			| nom_interne = 'Jingles', mode = 'aleatoire', crossfade_fin = '-1 s' |
			| nom_interne = 'Jingles', mode = 'aleatoire', crossfade_debut = NULL |
			| nom_interne = 'Jingles', mode = 'aleatoire', crossfade_fin_regle = 'toujours' |
			| nom_interne = 'Jingles', mode = 'aleatoire', crossfade_debut_regle = NULL |
			| nom_interne = 'Jingles', mode = 'aleatoire', duree_min = '0 s' |
			| nom_interne = 'Jingles', mode = 'aleatoire', duree_max = '-1 s' |
			| nom_interne = 'Jingles', mode = 'aleatoire', duree_min = '2 min', duree_max = '1 min' |
			| nom_interne = 'Jingles', mode = 'aleatoire', detection_blancs = NULL |

	# https://github.com/dascritch/machincast/issues/63

	Scénario: Une banque n'est pas marquée « ne pas répéter » par défaut
		Étant donné les éléments de référence en base
		Alors la banque de référence n'est pas marquée « ne pas répéter »

	# https://github.com/dascritch/machincast/issues/146

	Scénario: La détection de blanc n'est activée par défaut ni pour une banque, ni pour un sonore, qui n'ont aucun blanc détecté
		Étant donné les éléments de référence en base
		Alors la banque de référence n'active pas la détection de blanc
		Et le sonore de référence n'active pas la détection de blanc
		Et le sonore de référence n'a ni début ni fin détectés

	Scénario: La migration de la détection de blanc ne l'active pour aucune banque ni aucun sonore existants
		Quand j'annule les migrations depuis « 0008.detection-blancs »
		Et j'enregistre dans "banques" : nom_interne = 'Titres', mode = 'aleatoire'
		Et j'enregistre dans "sonores" : type = 'fichier', emplacement = '/a.flac'
		Et j'applique les migrations
		Alors la banque « Titres » n'active pas la détection de blanc
		Et le sonore « /a.flac » n'active pas la détection de blanc
		Quand j'annule les migrations depuis « 0008.detection-blancs »
		Alors aucune connexion supplémentaire à la base de test ne reste ouverte

	# https://github.com/dascritch/machincast/issues/114

	Scénario: Un sonore n'a pas d'audit complet demandé par défaut
		Étant donné les éléments de référence en base
		Alors le sonore de référence n'a pas d'audit complet demandé

	Scénario: La migration de l'audit demandé n'en demande pour aucun sonore existant
		Quand j'annule les migrations depuis « 0009.sonores-audit-demande »
		Et j'enregistre dans "sonores" : type = 'fichier', emplacement = '/a.flac'
		Et j'applique les migrations
		Alors le sonore « /a.flac » n'a pas d'audit complet demandé
		Quand j'annule les migrations depuis « 0009.sonores-audit-demande »
		Alors aucune connexion supplémentaire à la base de test ne reste ouverte

	Scénario: La migration des feeds renomme les marques-pages de streams sans toucher à leurs données
		https://github.com/dascritch/machincast/issues/252 : la table marques_pages_streams devient feeds, et la colonne
		marque_page_id des sonores devient feed_id ; un nouveau feed prend l'identifiant suivant.

		Quand j'annule les migrations depuis « 0012.feeds »
		Et j'enregistre dans "marques_pages_streams" : nom = 'Studio mobile', url = 'https://flux.exemple'
		Et j'enregistre dans "sonores" : type = 'stream', titre = 'Le direct', marque_page_id = (SELECT max(id) FROM marques_pages_streams)
		Et j'applique les migrations
		Alors le sonore « Le direct » suit le feed « Studio mobile »
		Quand j'enregistre dans "feeds" : nom = 'Radio FMR', url = 'https://fmr.exemple'
		Alors la base accepte l'enregistrement
		Quand j'annule les migrations depuis « 0012.feeds »
		Alors aucune connexion supplémentaire à la base de test ne reste ouverte

	Scénario: Une banque peut avoir plusieurs répertoires
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "banques_repertoires" : banque_id = {banque}, repertoire = '/habillages/hors-saison'
		Et j'enregistre dans "banques_repertoires" : banque_id = {banque}, repertoire = '/habillages/hiver'
		Et j'enregistre dans "banques_repertoires" : banque_id = {banque}, repertoire = '/habillages/noel'
		Alors la base accepte l'enregistrement

	Scénario: Un même répertoire peut servir à plusieurs banques
		Étant donné les éléments de référence en base
		Et une deuxième banque en base
		Quand j'enregistre dans "banques_repertoires" : banque_id = {banque}, repertoire = '/habillages/hors-saison'
		Et j'enregistre dans "banques_repertoires" : banque_id = {banque2}, repertoire = '/habillages/hors-saison'
		Alors la base accepte l'enregistrement

	Scénario: Un répertoire ne figure qu'une fois dans une banque
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "banques_repertoires" : banque_id = {banque}, repertoire = '/habillages/noel'
		Et j'enregistre dans "banques_repertoires" : banque_id = {banque}, repertoire = '/habillages/noel'
		Alors la base refuse l'enregistrement

	Scénario: Un sonore ne figure qu'une fois dans une banque
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "banques_sonores" : banque_id = {banque}, sonore_id = {sonore}, position = 1
		Et j'enregistre dans "banques_sonores" : banque_id = {banque}, sonore_id = {sonore}, position = 2
		Alors la base refuse l'enregistrement

	Scénario: Deux sonores ne partagent pas la même position dans une banque
		Étant donné les éléments de référence en base
		Et un deuxième sonore en base
		Quand j'enregistre dans "banques_sonores" : banque_id = {banque}, sonore_id = {sonore}, position = 1
		Et j'enregistre dans "banques_sonores" : banque_id = {banque}, sonore_id = {sonore2}, position = 1
		Alors la base refuse l'enregistrement

	# ─── Événements ────────────────────────────────────────

	Plan du scénario: Un événement cohérent est accepté
		Quand j'enregistre dans "evenements" : <valeurs>
		Alors la base accepte l'enregistrement

		Exemples:
			| valeurs                                                                                                        |
			| nom_interne = 'Fil permanent', priorite = 'fil_musical'                                                        |
			| nom_interne = 'Nuit', priorite = 'fil_musical', debut = '2026-10-14 22:00', fin = '2026-10-15 06:00', jours_recurrence = '{lundi,mardi,mercredi,jeudi,vendredi,samedi,dimanche}' |
			| nom_interne = 'Magazine', priorite = 'emission', debut = '2026-10-19 18:00', fin = '2026-10-19 19:00', jours_recurrence = '{lundi,mardi,mercredi,jeudi,vendredi}' |
			| nom_interne = 'Rediffusion', priorite = 'special', debut = '2026-10-20 14:00'                                   |
			| nom_interne = 'Secours direct', priorite = 'secours'                                                            |

	Plan du scénario: Un événement incohérent est refusé
		Quand j'enregistre dans "evenements" : <valeurs>
		Alors la base refuse l'enregistrement

		Exemples:
			| valeurs                                                                                          |
			| nom_interne = 'X', priorite = 'urgence', debut = '2026-10-19 18:00'                              |
			| nom_interne = 'X', priorite = 'emission'                                                         |
			| nom_interne = 'X', priorite = 'special', fin = '2026-10-19 19:00'                                |
			| nom_interne = 'X', priorite = 'fil_musical', fin = '2026-10-19 19:00'                            |
			| nom_interne = 'X', priorite = 'emission', debut = '2026-10-19 19:00', fin = '2026-10-19 18:00'   |
			| nom_interne = 'X', priorite = 'emission', debut = '2026-10-19 18:00', jours_recurrence = '{lundy}' |
			| nom_interne = 'X', priorite = 'emission', debut = '2026-10-19 18:00', jours_recurrence = '{1}'    |
			| nom_interne = 'X', priorite = 'secours', debut = '2026-10-19 18:00'                              |
			| nom_interne = 'X', priorite = 'secours', debut = '2026-10-19 18:00', fin = '2026-10-19 19:00'    |
			| nom_interne = 'X', priorite = 'secours', jours_recurrence = '{lundi}'                            |

	Scénario: Deux événements n'ont pas le même nom interne
		# https://github.com/dascritch/machincast/issues/32, migration 0002.evenements-nom-unique.
		Quand j'enregistre dans "evenements" : nom_interne = 'Continue', priorite = 'fil_musical'
		Et j'enregistre dans "evenements" : nom_interne = 'Continue', priorite = 'secours'
		Alors la base refuse l'enregistrement

	Scénario: Les priorités sont ordonnées
		Alors la priorité "secours" est inférieure à "fil_musical"
		Et la priorité "fil_musical" est inférieure à "emission"
		Et la priorité "emission" est inférieure à "special"

	# ─── Secours d'un stream (https://github.com/dascritch/machincast/issues/16) ───

	Plan du scénario: Seul un stream désigne un événement de secours, et seulement de priorité secours
		Étant donné les éléments de référence en base
		Et un événement de secours en base
		Quand j'enregistre dans "sonores" : <valeurs>
		Alors la base <verdict> l'enregistrement

		Exemples:
			| valeurs                                                                               | verdict |
			| type = 'stream', url_stream = 'https://flux.exemple/a', secours_evenement_id = {secours}   | accepte |
			| type = 'stream', url_stream = 'https://flux.exemple/b'                                     | accepte |
			| type = 'fichier', emplacement = '/a.flac', secours_evenement_id = {secours}                | refuse  |
			| type = 'stream', url_stream = 'https://flux.exemple/c', secours_evenement_id = {evenement} | refuse  |

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

	Scénario: Les jours de la semaine sont ordonnés du lundi au dimanche
		Alors le jour "lundi" vient avant "dimanche"

	Plan du scénario: Un élément de liste de lecture est une banque ou un sonore
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "evenements_elements" : evenement_id = {evenement}, position = 1<complement>
		Alors la base <verdict> l'enregistrement

		Exemples:
			| complement                                  | verdict |
			| , banque_id = {banque}                      | accepte |
			| , sonore_id = {sonore}                      | accepte |
			|                                             | refuse  |
			| , banque_id = {banque}, sonore_id = {sonore} | refuse  |
			| , sequence_id = {sequence}                  | accepte |
			| , sequence_id = {sequence}, sonore_id = {sonore} | refuse  |
			| , sequence_id = {sequence}, banque_id = {banque} | refuse  |

	# ─── Séquences (https://github.com/dascritch/machincast/issues/99) ───

	Plan du scénario: Une séquence incohérente est refusée
		Quand j'enregistre dans "sequences" : <valeurs>
		Alors la base refuse l'enregistrement

		Exemples:
			| valeurs                                       |
			| nom_public = 'Vous écoutez Radio Thune'       |
			| nom_interne = 'Pub', masquer_metadonnees = 'peut-être' |

	Scénario: Deux séquences n'ont pas le même nom interne
		Quand j'enregistre dans "sequences" : nom_interne = 'Pub'
		Et j'enregistre dans "sequences" : nom_interne = 'Pub'
		Alors la base refuse l'enregistrement

	Plan du scénario: Un élément de séquence est une banque ou un sonore, jamais une autre séquence
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sequences_elements" : sequence_id = {sequence}, position = 1<complement>
		Alors la base <verdict> l'enregistrement

		Exemples:
			| complement                                   | verdict |
			| , banque_id = {banque}                       | accepte |
			| , sonore_id = {sonore}                       | accepte |
			|                                              | refuse  |
			| , banque_id = {banque}, sonore_id = {sonore} | refuse  |
			| , position = 0, sonore_id = {sonore}         | refuse  |

	Scénario: Une séquence fait revenir un même élément, chacun à sa position
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sequences_elements" : sequence_id = {sequence}, position = 1, sonore_id = {sonore}
		Et j'enregistre dans "sequences_elements" : sequence_id = {sequence}, position = 2, banque_id = {banque}
		Et j'enregistre dans "sequences_elements" : sequence_id = {sequence}, position = 3, banque_id = {banque}
		Alors la base accepte l'enregistrement

	Scénario: Deux éléments d'une séquence ne partagent pas la même position
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "sequences_elements" : sequence_id = {sequence}, position = 1, sonore_id = {sonore}
		Et j'enregistre dans "sequences_elements" : sequence_id = {sequence}, position = 1, banque_id = {banque}
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
		Quand j'enregistre dans "evenements_elements" : evenement_id = {evenement}, position = 1, sequence_id = {sequence}
		Et je supprime la séquence de référence
		Alors l'événement de référence n'a plus d'élément

	Scénario: Un même jingle peut revenir plusieurs fois dans une liste
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "evenements_elements" : evenement_id = {evenement}, position = 1, sonore_id = {sonore}
		Et j'enregistre dans "evenements_elements" : evenement_id = {evenement}, position = 2, banque_id = {banque}
		Et j'enregistre dans "evenements_elements" : evenement_id = {evenement}, position = 3, sonore_id = {sonore}
		Alors la base accepte l'enregistrement

	# ─── Airplay et log ────────────────────────────────────

	Plan du scénario: Les lignes d'airplay respectent leur type
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "airplay" : passage_id = '7f0c1c2e-5d39-4a87-9a52-0c3c8c1f9a01', <valeurs>
		Alors la base <verdict> l'enregistrement

		Exemples:
			| valeurs                                                                      | verdict |
			| type_ligne = 'debut', sonore_id = {sonore}, banque_id = {banque}             | accepte |
			| type_ligne = 'fin', duree_diffusee = '3 min', sans_incident = true           | accepte |
			| type_ligne = 'debut', duree_diffusee = '3 min'                               | refuse  |
			| type_ligne = 'fin', sans_incident = true                                     | refuse  |
			| type_ligne = 'milieu'                                                        | refuse  |

	Scénario: Un passage n'a qu'une ligne de début
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "airplay" : passage_id = '7f0c1c2e-5d39-4a87-9a52-0c3c8c1f9a01', type_ligne = 'debut'
		Et j'enregistre dans "airplay" : passage_id = '7f0c1c2e-5d39-4a87-9a52-0c3c8c1f9a01', type_ligne = 'debut'
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
		Quand j'enregistre dans "log" : niveau = '<niveau>', nature = 'demarrage'
		Alors la base <verdict> l'enregistrement

		Exemples:
			| niveau   | verdict |
			| info     | accepte |
			| alerte   | accepte |
			| incident | accepte |
			| debug    | refuse  |

	# ─── Longueur des textes courts ────────────────────────

	Plan du scénario: Les textes saisis à la main sont limités à 255 caractères
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "<table>" : <autres>, <colonne> = repeat('é', <longueur>)
		Alors la base <verdict> l'enregistrement

		Exemples:
			| table                 | autres                                                  | colonne     | longueur | verdict |
			| feeds | url = 'https://flux.exemple'                            | nom         | 255      | accepte |
			| feeds | url = 'https://flux.exemple'                            | nom         | 256      | refuse  |
			| sonores               | type = 'fichier', emplacement = '/long/artiste.flac'    | artiste     | 255      | accepte |
			| sonores               | type = 'fichier', emplacement = '/long/artiste.flac'    | artiste     | 256      | refuse  |
			| sonores               | type = 'fichier', emplacement = '/long/titre.flac'      | titre       | 256      | refuse  |
			| banques               | mode = 'aleatoire'                                      | nom_interne | 255      | accepte |
			| banques               | mode = 'aleatoire'                                      | nom_interne | 256      | refuse  |
			| banques               | mode = 'aleatoire', nom_interne = 'X'                   | nom_public  | 255      | accepte |
			| banques               | mode = 'aleatoire', nom_interne = 'X'                   | nom_public  | 256      | refuse  |
			| sequences             | nom_public = 'Pub'                                      | nom_interne | 255      | accepte |
			| sequences             | nom_public = 'Pub'                                      | nom_interne | 256      | refuse  |
			| sequences             | nom_interne = 'X'                                       | nom_public  | 256      | refuse  |
			| evenements            | priorite = 'fil_musical'                                | nom_interne | 255      | accepte |
			| evenements            | priorite = 'fil_musical'                                | nom_interne | 256      | refuse  |
			| evenements            | priorite = 'fil_musical', nom_interne = 'X'             | nom_public  | 256      | refuse  |
			| airplay               | passage_id = gen_random_uuid(), type_ligne = 'debut'    | artiste     | 256      | refuse  |
			| airplay               | passage_id = gen_random_uuid(), type_ligne = 'debut'    | titre       | 256      | refuse  |
			| log                   | niveau = 'info'                                         | nature      | 255      | accepte |
			| log                   | niveau = 'info'                                         | nature      | 256      | refuse  |

	Plan du scénario: Les chemins, URL et messages ne sont pas limités à 255 caractères
		Étant donné les éléments de référence en base
		Quand j'enregistre dans "<table>" : <autres>, <colonne> = '<prefixe>' || repeat('x', 1000)
		Alors la base accepte l'enregistrement

		Exemples:
			| table                 | autres                                       | colonne     | prefixe                     |
			| sonores               | type = 'fichier'                             | emplacement | /musique/                   |
			| sonores               | type = 'stream'                              | url_stream  | https://flux.exemple/?SESSIONID= |
			| feeds | nom = 'Long'                                 | url         | https://flux.exemple/       |
			| banques_repertoires   | banque_id = {banque}                         | repertoire  | /habillages/                |
			| log                   | niveau = 'incident', nature = 'flux'         | message     | Détail :                    |
