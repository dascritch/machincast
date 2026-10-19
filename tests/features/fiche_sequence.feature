# language: fr
Fonctionnalité: Fiche d'une séquence
	En tant que programmateur de l'antenne,
	je veux gérer une séquence et sa liste ordonnée de sonores et de banques,
	afin de placer dans mes événements un enchaînement toujours identique, comme un passage publicitaire encadré de
	ses jingles.

	https://github.com/dascritch/machincast/issues/112, spec § 8.12. La fiche s'ouvre dans un onglet qui se ferme,
	depuis la liste des séquences, comme celle d'une banque (fiche_banque.feature, qui vérifie aussi l'enregistrement,
	l'annulation et la fermeture, communs aux fiches). Une séquence ne contient que des sonores et des banques, jamais
	une autre séquence ; un même élément peut y revenir. Un chemin qui commence par « …/ » est dans le répertoire
	temporaire du scénario.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 15:30:00 »
		Et les sonores :
			| artiste     | titre        | type    | etat  | duree | emplacement                 |
			|             | Jingle début | fichier | actif | 5     | /srv/habillage/debut.flac   |
			|             | Jingle fin   | fichier | actif | 4     | /srv/habillage/fin.flac     |
			| Les Gaufres | Spot         | fichier | actif | 30    | /srv/pubs/spot.flac         |
		Et la banque « Publicité », aléatoire, sans nom public, marquée « ne pas répéter », avec « Spot »
		Et la banque « Habillage », séquentielle, sans nom public, avec « Jingle début »
		Et la séquence « Passage pub », de nom public « Vous écoutez Radio Thune », avec le sonore « Jingle début », la banque « Publicité », le sonore « Jingle fin »

	# ─── Ouverture ─────────────────────────────────────────────

	Scénario: La fiche d'une séquence s'ouvre dans un onglet, depuis la liste des séquences
		Étant donné les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
			| Matinale |            | fil_musical |       |     |       |
		Et l'événement « Continue » joue la séquence « Passage pub »
		Et l'événement « Matinale » joue la séquence « Passage pub »
		Et l'événement « Continue » joue la séquence « Passage pub »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Et j'ouvre la ligne « Passage pub »
		Alors l'onglet ouvert est « Séquence : Passage pub »
		Et l'écran de détail de séquence « Passage pub » est demandé
		Et la fiche de la séquence montre le nom interne « Passage pub », le nom public « Vous écoutez Radio Thune » et le masquage « selon la banque ou le sonore »
		Et la fiche de la séquence montre les éléments :
			| Genre  | Élément      | Détail                       |
			| sonore | Jingle début | /srv/habillage/debut.flac    |
			| banque | Publicité    | aléatoire, ne pas répéter    |
			| sonore | Jingle fin   | /srv/habillage/fin.flac      |
		Et la fiche de la séquence montre les événements « Continue », « Matinale »
		Et la fiche de la séquence n'avertit de rien
		Quand je saisis le nom public « Radio Thune »
		Et j'enregistre la fiche
		Alors la fiche de la séquence montre les événements « Continue », « Matinale »

	Scénario: Une nouvelle séquence se crée depuis la liste des séquences
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Et je clique sur « Nouvelle séquence »
		Alors l'onglet ouvert est « Nouvelle séquence »
		Et la fiche de la séquence montre le nom interne «  », le nom public «  » et le masquage « selon la banque ou le sonore »
		Et la fiche de la séquence montre les événements aucun
		Quand je saisis le nom interne « Ouverture »
		Et j'ajoute les banques « Habillage »
		Et j'ajoute les sonores « Spot », « Jingle fin »
		Et j'enregistre la fiche
		Alors la séquence « Ouverture » est en base : sans nom public, masquage « selon la banque ou le sonore »
		Et les éléments de la séquence « Ouverture » sont, dans l'ordre, la banque « Habillage », le sonore « Spot », le sonore « Jingle fin »
		Et l'onglet ouvert est « Séquence : Ouverture »
		Quand j'ouvre l'onglet « Séquences »
		Alors la liste montre :
			| Nom         | Nom public               |
			| Ouverture   |                          |
			| Passage pub | Vous écoutez Radio Thune |

	# ─── Champs ────────────────────────────────────────────────

	Plan du scénario: Les champs modifiés partent en base à l'enregistrement
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je saisis le nom interne «  Passage pub du soir  »
		Et je saisis le nom public « <nom public> »
		Et je choisis le masquage « <masquage> »
		Et j'enregistre la fiche
		Alors la séquence « Passage pub du soir » est en base : <en base>
		Et l'onglet ouvert est « Séquence : Passage pub du soir »

		Exemples:
			| nom public    | masquage                     | en base                                                         |
			| Pub du soir   | masqués                      | nom public « Pub du soir », masquage « masqués »                |
			|               | affichés                     | sans nom public, masquage « affichés »                          |
			| Radio Thune   | selon la banque ou le sonore | nom public « Radio Thune », masquage « selon la banque ou le sonore » |

	Plan du scénario: Une séquence invalide n'est pas enregistrée, et dit pourquoi
		Étant donné la séquence « Ouverture », sans nom public, avec la banque « Habillage »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je saisis le nom interne « <nom> »
		Et <action>
		Et j'enregistre la fiche
		Alors la fiche signale « <message> »
		Et les éléments de la séquence « Passage pub » sont, dans l'ordre, le sonore « Jingle début », la banque « Publicité », le sonore « Jingle fin »

		Exemples:
			| nom         | action                                                                       | message                                                    |
			|             | je saisis le nom public « Autre »                                            | Le nom interne est obligatoire.                            |
			| Ouverture   | je saisis le nom public « Autre »                                            | Une autre séquence s'appelle déjà « Ouverture ».           |
			| Passage pub | je retire les éléments « Jingle début », « Publicité », « Jingle fin »       | Une séquence contient au moins un sonore ou une banque.    |

	# ─── Éléments ──────────────────────────────────────────────

	Scénario: Les éléments se réordonnent, se retirent, et un même élément peut revenir
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je choisis l'élément « Jingle fin »
		Et je clique sur « Monter »
		Et j'ajoute les sonores « Jingle début »
		Et j'ajoute les banques « Habillage », « Publicité »
		Et je choisis l'élément n° 5
		Et je clique sur « Retirer l'élément »
		Alors les choix ont précisé « Un sonore ou une banque peut revenir plusieurs fois dans une séquence. »
		Et la fiche de la séquence montre les éléments « Jingle début », « Jingle fin », « Publicité », « Jingle début », « Publicité »
		Quand j'enregistre la fiche
		Alors les éléments de la séquence « Passage pub » sont, dans l'ordre, le sonore « Jingle début », le sonore « Jingle fin », la banque « Publicité », le sonore « Jingle début », la banque « Publicité »

	Scénario: Une ligne restée dans la liste reste celle que désigne l'historique de diffusion, à sa nouvelle place
		# La diffusion reprend une séquence après la ligne de son dernier passage (spec § 4.3) ; une ligne retirée ne
		# désigne plus rien.
		Étant donné « Jingle fin » qui vient de passer dans la séquence « Passage pub »
		Et « Jingle début » qui vient de passer dans la séquence « Passage pub »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je choisis l'élément « Jingle fin »
		Et je clique sur « Monter »
		Et je retire les éléments « Jingle début »
		Et j'ajoute les sonores « Jingle début »
		Et j'enregistre la fiche
		Alors l'historique de diffusion désigne, dans la séquence « Passage pub », la ligne n° 1 et aucune ligne

	Scénario: Les boutons d'une ligne ne servent qu'à une ligne choisie, et « Monter » et « Descendre » pas aux extrémités
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Alors les boutons de ligne actifs de la séquence sont aucun
		Quand je choisis l'élément « Jingle début »
		Alors les boutons de ligne actifs de la séquence sont « Retirer l'élément », « Descendre »
		Quand je choisis l'élément « Publicité »
		Alors les boutons de ligne actifs de la séquence sont « Retirer l'élément », « Monter », « Descendre »
		Quand je clique sur « Descendre »
		Alors les boutons de ligne actifs de la séquence sont « Retirer l'élément », « Monter »
		Et la fiche de la séquence montre les éléments « Jingle début », « Jingle fin », « Publicité »
		Quand je clique sur « Monter »
		Alors la fiche de la séquence montre les éléments « Jingle début », « Publicité », « Jingle fin »

	Scénario: Les éléments se glissent, mais une ligne ne se dépose pas dans une autre
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Alors les éléments de la séquence se réordonnent par glisser-déposer, sans se déposer les uns dans les autres

	Plan du scénario: Toute modification des éléments rend « Enregistrer » et « Annuler » actifs
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et <modification>
		Alors les boutons « Enregistrer » et « Annuler » de la fiche sont actifs

		Exemples:
			| modification                                         |
			| j'ajoute les sonores « Spot »                        |
			| j'ajoute les banques « Habillage »                   |
			| je retire les éléments « Publicité »                 |
			| je choisis l'élément « Publicité », puis je descends |
			| je saisis le nom interne « Autre »                   |
			| je saisis le nom public « Autre »                    |
			| je choisis le masquage « masqués »                   |

	Scénario: Renoncer au choix de sonores ou de banques ne change rien
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et j'ajoute les sonores aucun
		Et j'ajoute les banques aucun
		Alors la fiche de la séquence montre les éléments « Jingle début », « Publicité », « Jingle fin »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs

	Scénario: Un sonore ou une banque effacé de la base pendant la modification est oublié à l'enregistrement
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et j'ajoute les banques « Habillage »
		Et j'ajoute les sonores « Spot »
		Et la banque « Habillage » est effacée de la base
		Et le sonore « Spot » est effacé de la base
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et les éléments de la séquence « Passage pub » sont, dans l'ordre, le sonore « Jingle début », la banque « Publicité », le sonore « Jingle fin »

	# ─── Dépôt depuis le navigateur de fichiers ────────────────

	Scénario: Des fichiers sonores déposés s'ajoutent, en base ou non, et le reste est ignoré
		Étant donné les dossiers « …/nouveaux » du scénario
		Et les fichiers « …/nouveaux/Annonce.ogg », « …/notes.txt » du scénario
		Et les sonores :
			| artiste | titre  | type    | etat  | duree | emplacement             |
			|         | Neige  | fichier | actif | 12    | …/neige.ogg             |
		Et les fichiers « …/neige.ogg » du scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je dépose sur les éléments de la séquence « …/nouveaux/Annonce.ogg », « …/neige.ogg », « …/notes.txt », « …/nouveaux », « …/nouveaux/Annonce.ogg »
		Alors le dépôt est accepté comme une copie
		Et la fiche de la séquence montre les éléments « Jingle début », « Publicité », « Jingle fin », « Annonce.ogg », « Neige », « Annonce.ogg »
		Et la fiche signale « Ignorés, ce ne sont pas des fichiers sonores : notes.txt, nouveaux. »
		# Un fichier pas encore en base n'a pas de fiche.
		Quand j'ouvre l'élément « Annonce.ogg » de la séquence
		Alors l'onglet ouvert est « Séquence : Passage pub »
		Quand j'enregistre la fiche
		Alors les éléments de la séquence « Passage pub » sont, dans l'ordre, le sonore « Jingle début », la banque « Publicité », le sonore « Jingle fin », le fichier « …/nouveaux/Annonce.ogg », le sonore « Neige », le fichier « …/nouveaux/Annonce.ogg »
		Et le fichier « …/nouveaux/Annonce.ogg » est en base, à l'état aperçu, sans artiste ni titre
		Et les fichiers déposés sont intacts

	Scénario: Un glisser qui ne propose pas la copie est refusé
		Étant donné les fichiers « …/nouveau.ogg » du scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je dépose sur les éléments de la séquence « …/nouveau.ogg », en ne proposant que le déplacement
		Alors le dépôt est refusé
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs

	# ─── Banque « ne pas répéter » ─────────────────────────────

	Plan du scénario: Une banque « ne pas répéter » sur deux lignes contiguës est signalée, sans empêcher d'enregistrer
		Étant donné la séquence « Essai », sans nom public, avec <éléments>
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Essai »
		Alors la fiche de la séquence avertit <avertissement>

		Exemples:
			| éléments                                                                            | avertissement                                                                                                     |
			| la banque « Publicité », la banque « Publicité »                                    | « Ligne 2 : la banque « Publicité » vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. » |
			| la banque « Publicité », le sonore « Spot », la banque « Publicité »                | de rien                                                                                                           |
			| la banque « Habillage », la banque « Habillage »                                    | de rien                                                                                                           |
			| la banque « Publicité », le sonore « Spot », la banque « Publicité », la banque « Publicité » | « Ligne 4 : la banque « Publicité » vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. » |

	Scénario: L'avertissement suit les modifications, et la séquence s'enregistre quand même
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et j'ajoute les banques « Publicité »
		Et je choisis l'élément n° 4
		Et je clique sur « Monter »
		Alors la fiche de la séquence avertit « Ligne 3 : la banque « Publicité » vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. »
		Quand j'enregistre la fiche
		Alors la fiche ne signale rien
		Et les éléments de la séquence « Passage pub » sont, dans l'ordre, le sonore « Jingle début », la banque « Publicité », la banque « Publicité », le sonore « Jingle fin »
		Et la fiche de la séquence avertit « Ligne 3 : la banque « Publicité » vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. »
		Quand je choisis l'élément n° 3
		Et je clique sur « Descendre »
		Alors la fiche de la séquence n'avertit de rien

	Scénario: À la relecture, une banque qui ne refuse plus de se répéter n'est plus signalée
		Étant donné la séquence « Essai », sans nom public, avec la banque « Publicité », la banque « Publicité »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Essai »
		Et la banque « Publicité » n'est plus marquée « ne pas répéter » en base
		Et je saisis le nom public « Autre »
		Et j'annule les modifications de la fiche
		Alors la fiche de la séquence n'avertit de rien
		Et la fiche de la séquence montre les éléments :
			| Genre  | Élément   | Détail    |
			| banque | Publicité | aléatoire |
			| banque | Publicité | aléatoire |

	# ─── Liens vers les autres fiches ──────────────────────────

	Scénario: Ouvrir un élément ou un événement ouvre sa fiche
		Étant donné les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Et l'événement « Continue » joue la séquence « Passage pub »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et j'ouvre l'élément « Publicité » de la séquence
		Alors l'onglet ouvert est « Banque : Publicité »
		Quand j'ouvre l'onglet « Séquence : Passage pub »
		Et j'ouvre l'élément « Jingle fin » de la séquence
		Alors l'onglet ouvert est « Sonore : Jingle fin »
		Quand j'ouvre l'onglet « Séquence : Passage pub »
		Et j'ouvre l'événement « Continue » de la séquence
		Alors l'onglet ouvert est « Événement : Continue »
