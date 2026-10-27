# language: fr
Fonctionnalité: Fiche d'un événement
	En tant que programmateur de l'antenne,
	je veux créer et modifier un événement et sa liste de lecture,
	afin de construire la grille d'antenne.

	https://github.com/dascritch/machincast/issues/32, spec § 8.5. La fiche s'ouvre dans un onglet qui se ferme, depuis
	la liste des événements, comme celle d'une banque (fiche_banque.feature, qui vérifie aussi l'enregistrement,
	l'annulation et la fermeture, communs aux fiches). Sa liste de lecture se gère comme celle d'une séquence
	(fiche_sequence.feature), avec les séquences en plus. Les dates sont en heure de Paris ; le 19 octobre 2026 est un
	lundi. Un chemin qui commence par « …/ » est dans le répertoire temporaire du scénario.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 15:30:42 »
		Et les sonores :
			| artiste     | titre        | type    | etat  | duree | emplacement               |
			|             | Jingle début | fichier | actif | 5     | /srv/habillage/debut.flac |
			|             | Jingle fin   | fichier | actif | 4     | /srv/habillage/fin.flac   |
			| Les Gaufres | Spot         | fichier | actif | 30    | /srv/pubs/spot.flac       |
		Et la banque « Publicité », aléatoire, sans nom public, marquée « ne pas répéter », avec « Spot »
		Et la banque « Habillage », séquentielle, sans nom public, avec « Jingle début »
		Et la séquence « Passage pub », sans nom public, avec le sonore « Jingle début », la banque « Publicité », le sonore « Jingle fin »
		Et les événements :
			| nom      | nom_public  | priorite    | debut            | fin              | jours                                     |
			| Continue |             | fil_musical |                  |                  |                                           |
			| Matinale | Le réveil   | emission    | 2026-10-19 07:00 | 2026-10-19 09:00 | lundi, mardi, mercredi, jeudi, vendredi   |
			| Journal  |             | emission    | 2026-10-21 09:00 | 2026-10-21 09:30 |                                           |
			| Panne    |             | secours     |                  |                  |                                           |
		Et l'événement « Matinale » joue la banque « Habillage », la séquence « Passage pub », le sonore « Spot »
		Et l'événement « Continue » joue la banque « Habillage »

	# ─── Ouverture ─────────────────────────────────────────────

	Scénario: La fiche d'un événement s'ouvre dans un onglet, depuis la liste des événements
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Et j'ouvre la ligne « Matinale »
		Alors l'onglet ouvert est « Événement : Matinale »
		Et l'écran de détail de événement « Matinale » est demandé
		Et la fiche de l'événement montre :
			| champ            | valeur                                   |
			| Nom interne      | Matinale                                 |
			| Nom public       | Le réveil                                |
			| Priorité         | émission                                 |
			| Artiste et titre | selon la séquence, la banque ou le sonore |
			| Début            | 19/10/2026 07:00                         |
			| Fin              | 19/10/2026 09:00                         |
			| Jours            | lundi, mardi, mercredi, jeudi, vendredi  |
		Et la fiche de l'événement montre les éléments :
			| Genre    | Élément            | Détail              |
			| banque   | Habillage          | séquentielle        |
			| séquence | Passage pub        | 3 éléments          |
			| sonore   | Les Gaufres – Spot | /srv/pubs/spot.flac |
		Et la fiche de l'événement n'avertit de rien
		Et la grille de la fiche de l'événement se saisit par « Début », « Fin », les jours

	Scénario: Un fil musical permanent n'a ni début, ni fin, ni jours
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Continue »
		Alors la fiche de l'événement montre :
			| champ    | valeur      |
			| Priorité | fil musical |
			| Début    |             |
			| Fin      |             |
			| Jours    |             |
		Et la grille de la fiche de l'événement se saisit par « Début »

	Scénario: Un nouvel événement se crée depuis la liste des événements
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Et je clique sur « Nouvel événement »
		Alors l'onglet ouvert est « Nouvel événement »
		Et la fiche de l'événement montre :
			| champ            | valeur                                    |
			| Nom interne      |                                           |
			| Priorité         | émission                                  |
			| Artiste et titre | selon la séquence, la banque ou le sonore |
			| Début            |                                           |
			| Jours            |                                           |
		Et la fiche de l'événement montre les éléments aucun
		Et la priorité se choisit parmi « secours », « fil musical », « émission », « spécial », de la plus basse à la plus haute
		Quand je coche « Début » dans la fiche de l'événement
		Alors la fiche de l'événement montre :
			| champ | valeur           |
			| Début | 19/10/2026 15:30 |
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs
		Quand je saisis le nom interne « Midi »
		Et je saisis dans la fiche de l'événement :
			| champ | valeur           |
			| Fin   | 19/10/2026 16:30 |
			| Jours | lundi, jeudi     |
		Et j'ajoute les banques « Habillage »
		Et j'enregistre la fiche
		Alors l'événement « Midi » a en base :
			| champ               | valeur                    |
			| nom_public          | None                      |
			| priorite            | emission                  |
			| masquer_metadonnees | None                      |
			| debut               | 2026-10-19 15:30:00+02:00 |
			| fin                 | 2026-10-19 16:30:00+02:00 |
			| jours_recurrence    | ['lundi', 'jeudi']        |
		Et les éléments de l'événement « Midi » sont, dans l'ordre, la banque « Habillage »
		Et l'onglet ouvert est « Événement : Midi »
		Quand j'ouvre l'onglet « Événements »
		Alors la liste montre :
			| Nom      | Nom public | Priorité    | Début            | Fin              | Récurrence                              | Anomalie       |
			| Journal  |            | émission    | 2026-10-21 09:00 | 2026-10-21 09:30 |                                         | événement vide |
			| Matinale | Le réveil  | émission    | 2026-10-19 07:00 | 2026-10-19 09:00 | lundi, mardi, mercredi, jeudi, vendredi |                |
			| Midi     |            | émission    | 2026-10-19 15:30 | 2026-10-19 16:30 | lundi, jeudi                            |                |
			| Continue |            | fil musical |                  |                  |                                         |                |
			| Panne    |            | secours     |                  |                  |                                         | événement vide |

	Scénario: Chaque liste propose de créer un élément
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Sonores » dans le menu « Affichage »
		Et je choisis « Ouvrir l'onglet Feeds » dans le menu « Affichage »
		Alors les listes qui proposent de créer un élément sont « Événements : Nouvel événement », « Séquences : Nouvelle séquence », « Banques : Nouvelle banque », « Sonores : Nouveau stream », « Feeds : Nouveau feed »

	# ─── Champs ────────────────────────────────────────────────

	Scénario: Les champs modifiés partent en base à l'enregistrement
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je saisis le nom interne «  Matinale du week-end  »
		Et je saisis le nom public « Bonjour »
		Et je saisis dans la fiche de l'événement :
			| champ            | valeur           |
			| Priorité         | spécial          |
			| Artiste et titre | masqués          |
			| Début            | 24/10/2026 08:00 |
			| Fin              | 24/10/2026 10:30 |
			| Jours            | samedi, dimanche |
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et l'événement « Matinale du week-end » a en base :
			| champ               | valeur                    |
			| nom_public          | Bonjour                   |
			| priorite            | special                   |
			| masquer_metadonnees | True                      |
			| debut               | 2026-10-24 08:00:00+02:00 |
			| fin                 | 2026-10-24 10:30:00+02:00 |
			| jours_recurrence    | ['samedi', 'dimanche']    |
		Et l'onglet ouvert est « Événement : Matinale du week-end »

	Scénario: Un événement de secours n'a ni dates ni jours : il ne joue qu'à la place d'un stream tombé
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je saisis dans la fiche de l'événement :
			| champ    | valeur  |
			| Priorité | secours |
		Alors la fiche de l'événement montre :
			| champ | valeur |
			| Début |        |
			| Fin   |        |
			| Jours |        |
		Et la grille de la fiche de l'événement se saisit par rien
		Quand j'enregistre la fiche
		Alors l'événement « Matinale » a en base :
			| champ            | valeur  |
			| priorite         | secours |
			| debut            | None    |
			| fin              | None    |
			| jours_recurrence | []      |

	Scénario: Sans début, un événement n'a ni fin ni jours
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je saisis dans la fiche de l'événement :
			| champ    | valeur      |
			| Priorité | fil musical |
			| Début    |             |
		Alors la fiche de l'événement montre :
			| champ | valeur |
			| Fin   |        |
			| Jours |        |
		Et la grille de la fiche de l'événement se saisit par « Début »
		Quand j'enregistre la fiche
		Alors l'événement « Matinale » a en base :
			| champ            | valeur      |
			| priorite         | fil_musical |
			| debut            | None        |
			| fin              | None        |
			| jours_recurrence | []          |

	Scénario: Une fin cochée part d'une heure après le début
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Et je clique sur « Nouvel événement »
		Et je saisis dans la fiche de l'événement :
			| champ | valeur           |
			| Début | 22/10/2026 18:00 |
		Et je coche « Fin » dans la fiche de l'événement
		Alors la fiche de l'événement montre :
			| champ | valeur           |
			| Fin   | 22/10/2026 19:00 |
		Et la grille de la fiche de l'événement se saisit par « Début », « Fin », les jours

	Scénario: Un événement vide s'enregistre, avec un avertissement
		https://github.com/dascritch/machincast/issues/140 : il se complétera plus tard ; la diffusion ne s'y bloque pas (deroule.feature), et la
		liste des événements le montre en anomalie (listes.feature).

		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je retire les éléments « Habillage », « Passage pub », « Les Gaufres – Spot »
		Alors la fiche de l'événement avertit « Événement vide : il ne joue rien, et l'événement de priorité inférieure prend le relais pendant sa plage. »
		Quand j'enregistre la fiche
		Alors la fiche ne signale rien
		Et les éléments de l'événement « Matinale » sont, dans l'ordre, aucun
		Et la fiche de l'événement avertit « Événement vide : il ne joue rien, et l'événement de priorité inférieure prend le relais pendant sa plage. »
		Quand j'ajoute les sonores « Spot »
		Alors la fiche de l'événement n'avertit de rien

	Scénario: L'avertissement d'un événement vide dit ce que fait la diffusion, selon sa priorité
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Panne »
		Alors la fiche de l'événement avertit « Événement vide : il ne joue rien, et l'événement de priorité inférieure remplace le stream tombé. »
		Quand je choisis la priorité « fil musical »
		Alors la fiche de l'événement avertit « Événement vide : il ne joue rien, et la diffusion se tait, avec une alerte, quand il est à l'antenne. »
		Quand je choisis la priorité « spécial »
		Alors la fiche de l'événement avertit « Événement vide : il ne joue rien, et l'événement de priorité inférieure prend le relais pendant sa plage. »

	Scénario: Un nouvel événement, vide, s'enregistre sans élément
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Et je clique sur « Nouvel événement »
		Alors la fiche de l'événement avertit « Événement vide : il ne joue rien, et l'événement de priorité inférieure prend le relais pendant sa plage. »
		Quand je saisis le nom interne « Brouillon »
		Et je coche « Début » dans la fiche de l'événement
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et les éléments de l'événement « Brouillon » sont, dans l'ordre, aucun

	Scénario: Une session sautée ne compte pas dans les chevauchements
		https://github.com/dascritch/machincast/issues/273 : une émission posée sur une session sautée la remplace, et
		l'événement récurrent se modifie encore.

		Étant donné la session du 2026-10-21 de l'événement « Matinale » est sautée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je saisis la fin « 19/10/2026 09:15 » dans la fiche de l'événement
		Et j'enregistre la fiche
		Alors la fiche ne signale rien

	Plan du scénario: Un événement invalide n'est pas enregistré, et dit pourquoi
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et <action>
		Et j'enregistre la fiche
		Alors la fiche signale « <message> »
		Et l'événement « Matinale » a en base :
			| champ            | valeur                                                    |
			| priorite         | emission                                                  |
			| fin              | 2026-10-19 09:00:00+02:00                                 |
		Et les éléments de l'événement « Matinale » sont, dans l'ordre, la banque « Habillage », la séquence « Passage pub », le sonore « Spot »

		Exemples:
			| action                                                                       | message                                                                                    |
			| je saisis le nom interne «  »                                                | Le nom interne est obligatoire.                                                            |
			| je saisis le nom interne « Continue »                                        | Un autre événement s'appelle déjà « Continue ».                                            |
			| je décoche « Début » dans la fiche de l'événement                            | Une émission ou un spécial a un début.                                                     |
			| je saisis la fin « 19/10/2026 07:00 » dans la fiche de l'événement           | La fin doit suivre le début.                                                               |
			| je saisis la fin « 19/10/2026 09:15 » dans la fiche de l'événement           | Chevauche l'événement « Journal », de même priorité, le 21/10/2026 à 09:00.                |
			| je saisis la fin « 21/10/2026 08:00 » dans la fiche de l'événement           | Chevauche l'événement « Journal », de même priorité, le 21/10/2026 à 09:00.                |

	Scénario: Un fil musical daté s'enregistre à côté du fil musical permanent, qui sert de fond
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Et je clique sur « Nouvel événement »
		Et je saisis le nom interne « Nuit »
		Et je saisis dans la fiche de l'événement :
			| champ    | valeur                                                    |
			| Priorité | fil musical                                               |
			| Début    | 20/10/2026 00:00                                          |
			| Fin      | 20/10/2026 06:00                                          |
			| Jours    | lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche |
		Et j'ajoute les banques « Habillage »
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et l'onglet ouvert est « Événement : Nuit »

	Scénario: Un événement de secours qu'un stream désigne garde sa priorité
		Étant donné les sonores :
			| artiste | titre       | type   | etat  | duree | emplacement                 |
			|         | Radio Thune | stream | actif |       | https://flux.exemple/direct |
		Et le stream « Radio Thune » a pour événement de secours « Panne »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Panne »
		Et je saisis dans la fiche de l'événement :
			| champ    | valeur      |
			| Priorité | fil musical |
		Et j'ajoute les banques « Habillage »
		Et j'enregistre la fiche
		Alors la fiche signale « Des streams ont cet événement pour secours : « Radio Thune ». Il reste de priorité « Secours ». »
		Et l'événement « Panne » a en base :
			| champ    | valeur  |
			| priorite | secours |
		Quand je choisis la priorité « secours »
		Et je saisis le nom interne « Panne du direct »
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et l'onglet ouvert est « Événement : Panne du direct »

	# ─── À l'antenne (https://github.com/dascritch/machincast/issues/266) ───
	# Un événement enregistré, supprimé ou restauré vaut aussitôt à l'antenne : la fenêtre demande à Machin lecture de
	# relire la grille, qui recalcule le sonore en cours et les sonores à venir si ce qui règle l'antenne a changé.

	Scénario: Enregistrer un événement demande à Machin lecture de relire la grille
		Étant donné la socket d'état de Machin lecture ouverte pour l'interface
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je saisis la fin « 19/10/2026 08:30 » dans la fiche de l'événement
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et Machin lecture a reçu la demande de relire la grille

	Scénario: Supprimer un événement demande à Machin lecture de relire la grille
		Étant donné la socket d'état de Machin lecture ouverte pour l'interface
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Journal »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors Machin lecture a reçu la demande de relire la grille

	Scénario: Restaurer un événement demande à Machin lecture de relire la grille
		Étant donné la socket d'état de Machin lecture ouverte pour l'interface
		Et l'événement « Journal » est supprimé depuis l'interface
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre depuis l'historique la fiche de l'événement « Journal »
		Et je clique sur « Restaurer »
		Alors Machin lecture a reçu la demande de relire la grille

	Scénario: Un nom public changé n'est pas un changement de ce qui règle l'antenne
		Quand la fenêtre de l'interface s'ouvre
		Et je note l'empreinte de la grille
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je saisis le nom public « Le grand réveil »
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et l'empreinte de la grille n'a pas changé
		Quand je saisis la fin « 19/10/2026 08:30 » dans la fiche de l'événement
		Et j'enregistre la fiche
		Alors l'empreinte de la grille a changé

	Scénario: Sans Machin lecture, un événement s'enregistre comme toujours
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je saisis la fin « 19/10/2026 08:30 » dans la fiche de l'événement
		Et j'enregistre la fiche
		Alors la fiche ne signale rien

	# ─── Liste de lecture ──────────────────────────────────────

	Scénario: Les éléments se réordonnent, se retirent, et un même élément peut revenir
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je choisis l'élément « Les Gaufres – Spot » de l'événement
		Et je clique sur « Monter »
		Et j'ajoute les séquences « Passage pub »
		Et j'ajoute les sonores « Jingle fin »
		Et je choisis l'élément n° 1 de l'événement
		Et je clique sur « Retirer l'élément »
		Alors les choix ont précisé « Un sonore, une banque ou une séquence peut revenir plusieurs fois dans un événement. »
		Et la fiche de l'événement montre les éléments « Les Gaufres – Spot », « Passage pub », « Passage pub », « Jingle fin »
		Quand j'enregistre la fiche
		Alors les éléments de l'événement « Matinale » sont, dans l'ordre, le sonore « Spot », la séquence « Passage pub », la séquence « Passage pub », le sonore « Jingle fin »

	Scénario: Une ligne restée dans la liste reste celle que désigne l'historique de diffusion, à sa nouvelle place
		# La diffusion reprend un fil musical après la ligne de son dernier passage (spec § 4.2) ; une ligne retirée
		# ne désigne plus rien.
		Étant donné « Spot » qui vient de passer dans l'événement « Matinale »
		Et « Habillage » qui vient de passer dans l'événement « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je choisis l'élément « Les Gaufres – Spot » de l'événement
		Et je clique sur « Monter »
		Et je clique sur « Monter »
		Et je choisis l'élément « Habillage » de l'événement
		Et je clique sur « Retirer l'élément »
		Et j'ajoute les banques « Habillage »
		Et j'enregistre la fiche
		Alors l'historique de diffusion désigne, dans l'événement « Matinale », la ligne n° 1 et aucune ligne

	Scénario: Des fichiers sonores déposés s'ajoutent, et un nouveau fichier devient un sonore à l'enregistrement
		Étant donné les fichiers « …/Annonce.ogg », « …/notes.txt » du scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Continue »
		Et je dépose sur les éléments de l'événement « …/Annonce.ogg », « …/notes.txt »
		Alors le dépôt est accepté comme une copie
		Et la fiche de l'événement montre les éléments « Habillage », « Annonce.ogg »
		Et la fiche signale « Ignorés, ce ne sont pas des fichiers sonores : notes.txt. »
		Quand j'enregistre la fiche
		Alors les éléments de l'événement « Continue » sont, dans l'ordre, la banque « Habillage », le fichier « …/Annonce.ogg »
		Et le fichier « …/Annonce.ogg » est en base, à l'état aperçu, sans artiste ni titre
		Et les fichiers déposés sont intacts

	Scénario: Un feed ajouté reprend le stream qui le suit, ou en crée un à l'enregistrement
		https://github.com/dascritch/machincast/issues/167 : pour retransmettre une émission en extérieur, le stream s'ajoute depuis son
		feed, sans passer par la liste des sonores. Le premier stream par titre qui suit le feed est repris ;
		sans stream qui le suive, un stream actif, titré du nom du feed, est créé à l'enregistrement.

		Étant donné les feeds « Studio B », « https://flux.exemple/studio-b », « Relais », « https://flux.exemple/relais »
		Et les sonores :
			| artiste | titre        | type   | etat  | duree | emplacement                   |
			|         | Studio B bis | stream | actif |       | https://flux.exemple/studio-b |
			|         | Direct B     | stream | actif |       | https://flux.exemple/studio-b |
		Et les streams « Studio B bis », « Direct B » suivent le feed « Studio B »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Journal »
		Et j'ajoute les feeds « Studio B », « Relais »
		Alors la fiche de l'événement montre les éléments :
			| Genre  | Élément  | Détail                                       |
			| sonore | Direct B | https://flux.exemple/studio-b                |
			| sonore | Relais   | https://flux.exemple/relais, nouveau stream |
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs
		Quand j'enregistre la fiche
		Alors la fiche ne signale rien
		Et les éléments de l'événement « Journal » sont, dans l'ordre, le sonore « Direct B », le sonore « Relais »
		Et le stream « Relais » est en base, actif, et suit le feed « Relais »
		Et la fiche de l'événement montre les éléments « Direct B », « Relais »

	Scénario: Un même feed ajouté deux fois ne crée qu'un stream, et un feed effacé entre-temps est oublié
		Étant donné les feeds « Relais », « https://flux.exemple/relais », « Ancien », « https://flux.exemple/ancien »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Journal »
		Et j'ajoute les feeds « Relais », « Ancien », « Relais »
		Et le feed « Ancien » est effacé de la base
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et les éléments de l'événement « Journal » sont, dans l'ordre, le sonore « Relais », le sonore « Relais »
		Et 1 stream suit le feed « Relais »

	Scénario: Un feed effacé pendant son choix est oublié, et les boutons de ligne suivent l'ajout
		Étant donné les feeds « Relais », « https://flux.exemple/relais », « Ancien », « https://flux.exemple/ancien »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je choisis l'élément n° 3 de l'événement
		Alors les boutons de ligne actifs de l'événement sont « Retirer l'élément », « Monter »
		Quand j'ajoute les feeds « Ancien », « Relais », en effaçant « Ancien » de la base pendant le choix
		Alors la fiche de l'événement montre les éléments « Habillage », « Passage pub », « Les Gaufres – Spot », « Relais »
		Et les boutons de ligne actifs de l'événement sont « Retirer l'élément », « Monter », « Descendre »

	Scénario: Renoncer au choix des feeds ne change rien
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Journal »
		Et j'ajoute les feeds aucun
		Alors la fiche de l'événement montre les éléments aucun
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs

	Plan du scénario: Toute modification rend « Enregistrer » et « Annuler » actifs
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et <modification>
		Alors les boutons « Enregistrer » et « Annuler » de la fiche sont actifs

		Exemples:
			| modification                                                |
			| je saisis le nom interne « Autre »                          |
			| je saisis le nom public « Autre »                           |
			| je choisis le masquage « masqués »                          |
			| je choisis la priorité « spécial »                          |
			| je saisis la fin « 19/10/2026 10:00 » dans la fiche de l'événement |
			| je décoche « Fin » dans la fiche de l'événement             |
			| je décoche « mardi » dans la fiche de l'événement           |
			| j'ajoute les séquences « Passage pub »                      |
			| je retire les éléments « Habillage »                        |

	Scénario: Le détail d'une séquence donne son nombre d'éléments
		Étant donné la séquence « Générique », sans nom public, avec le sonore « Jingle fin »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Continue »
		Et j'ajoute les séquences « Générique », « Passage pub »
		Alors la fiche de l'événement montre les éléments :
			| Genre    | Élément     | Détail       |
			| banque   | Habillage   | séquentielle |
			| séquence | Générique   | 1 élément    |
			| séquence | Passage pub | 3 éléments   |

	Scénario: Renoncer au choix des séquences ne change rien
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et j'ajoute les séquences aucun
		Alors les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs

	Scénario: Une séquence effacée de la base pendant la modification est oubliée à l'enregistrement
		Étant donné la séquence « Ouverture », sans nom public, avec le sonore « Jingle début »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Continue »
		Et j'ajoute les séquences « Ouverture »
		Et la séquence « Ouverture » est effacée de la base
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et les éléments de l'événement « Continue » sont, dans l'ordre, la banque « Habillage »

	# ─── Banque « ne pas répéter » ─────────────────────────────

	Plan du scénario: Une banque « ne pas répéter » appelée juste après elle-même est signalée, en tenant compte de la boucle et des séquences
		Étant donné la séquence « Pub d'abord », sans nom public, avec la banque « Publicité », le sonore « Jingle fin »
		Et la séquence « Pub ensuite », sans nom public, avec le sonore « Jingle début », la banque « Publicité »
		Et les événements :
			| nom   | nom_public | priorite | debut            | fin   | jours |
			| Essai |            | special  | 2026-11-02 10:00 | <fin> |       |
		Et l'événement « Essai » joue <éléments>
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Essai »
		Alors la fiche de l'événement avertit <avertissement>

		Exemples:
			| fin              | éléments                                                                 | avertissement |
			|                  | la banque « Publicité », la banque « Publicité »                          | « Ligne 2 : la banque « Publicité » vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. » |
			| 2026-11-02 11:00 | la banque « Publicité », le sonore « Spot », la banque « Publicité »     | « Ligne 1 : la banque « Publicité » vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. » |
			|                  | la banque « Publicité », le sonore « Spot », la banque « Publicité »     | de rien |
			| 2026-11-02 11:00 | la banque « Habillage », la banque « Habillage »                          | de rien |
			| 2026-11-02 11:00 | la banque « Publicité », la séquence « Pub d'abord »                      | « Ligne 2 : la séquence « Pub d'abord » commence par la banque « Publicité », qui vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. » |
			| 2026-11-02 11:00 | la séquence « Pub ensuite », la banque « Publicité »                      | « Ligne 2 : la banque « Publicité » vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. » |
			| 2026-11-02 11:00 | la séquence « Pub d'abord », la séquence « Pub d'abord »                  | de rien |
			| 2026-11-02 11:00 | la banque « Publicité », la séquence « Passage pub »                      | de rien |

	Scénario: L'avertissement suit la priorité et la fin, qui décident de la boucle, et n'empêche pas d'enregistrer
		Étant donné les événements :
			| nom   | nom_public | priorite | debut            | fin              | jours |
			| Essai |            | special  | 2026-11-02 10:00 | 2026-11-02 11:00 |       |
		Et l'événement « Essai » joue la banque « Publicité », le sonore « Spot », la banque « Publicité »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Essai »
		Et je décoche « Fin » dans la fiche de l'événement
		Alors la fiche de l'événement n'avertit de rien
		Quand je saisis dans la fiche de l'événement :
			| champ    | valeur      |
			| Priorité | fil musical |
		Alors la fiche de l'événement avertit « Ligne 1 : la banque « Publicité » vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. »
		Quand j'enregistre la fiche
		Alors la fiche ne signale rien
		Et l'événement « Essai » a en base :
			| champ    | valeur      |
			| priorite | fil_musical |
			| fin      | None        |

	Scénario: Une banque marquée « ne pas répéter » pendant la modification est signalée dès son ajout
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et la banque « Habillage » est marquée « ne pas répéter » en base
		Et j'ajoute les banques « Habillage »
		Alors la fiche de l'événement avertit « Ligne 1 : la banque « Habillage » vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. »

	# ─── Liens vers les autres fiches ──────────────────────────

	Scénario: Ouvrir un élément ouvre sa fiche
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et j'ouvre l'élément « Passage pub » de l'événement
		Alors l'onglet ouvert est « Séquence : Passage pub »
		Quand j'ouvre l'onglet « Événement : Matinale »
		Et j'ouvre l'élément « Habillage » de l'événement
		Alors l'onglet ouvert est « Banque : Habillage »
		Quand j'ouvre l'onglet « Événement : Matinale »
		Et j'ouvre l'élément « Les Gaufres – Spot » de l'événement
		Alors l'onglet ouvert est « Sonore : Spot »
