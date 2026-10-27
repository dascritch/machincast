# language: fr
Fonctionnalité: Fiche d'une banque
	En tant que programmateur de l'antenne,
	je veux gérer une banque et la liste de ses sonores,
	afin de contrôler ce que la banque peut diffuser et dans quel ordre.

	https://github.com/dascritch/machincast/issues/31, spec § 8.4. La fiche s'ouvre dans un onglet qui se ferme, depuis
	la liste des banques ; ses modifications ne partent en base qu'au clic sur « Enregistrer ». Les fenêtres de dialogue
	(choix d'un répertoire ou de sonores, questions) sont remplacées par les réponses du scénario, qui note chaque
	question posée. Un chemin qui commence par « …/ » est dans le répertoire temporaire du scénario.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-16 20:00:30 »
		Et les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement                   |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/jingles/hiver/cafe.flac  |
			| Aube        | Matin clair   | fichier | actif | 200   | /srv/jingles/hiver/matin.flac |
			|             | Jingle        | fichier | actif | 8     | /srv/habillage/jingle.flac    |
			|             | Spot          | fichier | actif | 30    | /srv/pubs/spot.flac           |
		Et la banque « Jingles », séquentielle, de nom public « Radio Thune », marquée « ne pas répéter », avec « Café à minuit », « Matin clair »
		Et les répertoires « /srv/jingles/hiver » de la banque « Jingles »
		Et la banque « Jingles » applique à défaut 1 seconde de crossfade de fin

	# ─── Ouverture et fermeture ────────────────────────────────

	Scénario: La fiche d'une banque s'ouvre dans un onglet, depuis la liste des banques
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et j'ouvre la ligne « Jingles »
		Alors l'onglet ouvert est « Banque : Jingles »
		Et la fiche montre le nom interne « Jingles », le nom public « Radio Thune », le mode « séquentielle », le masquage « hérité du sonore » et « ne pas répéter » coché
		Et la fiche montre les répertoires « /srv/jingles/hiver »
		Et la fiche montre les sonores :
			| Sonore                      | Durée | État  | Emplacement                   |
			| Les Gaufres – Café à minuit | 3:34  | actif | /srv/jingles/hiver/cafe.flac  |
			| Aube – Matin clair          | 3:20  | actif | /srv/jingles/hiver/matin.flac |
		Et l'écran de détail de banque « Jingles » est demandé

	# ─── Ouvrir un sonore (https://github.com/dascritch/machincast/issues/115) ─────

	Scénario: Un double-clic sur un sonore de la banque ouvre sa fiche
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ouvre le sonore « Aube – Matin clair » de la banque
		Alors l'onglet ouvert est « Sonore : Matin clair »
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents », « Banque : Jingles », « Sonore : Matin clair »

	Scénario: Entrée sur le sonore choisi ouvre aussi sa fiche
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je choisis le sonore « Les Gaufres – Café à minuit » de la banque, puis j'appuie sur Entrée
		Alors l'onglet ouvert est « Sonore : Café à minuit »

	Scénario: Ouvrir un sonore laisse la banque modifiée telle quelle
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne « Jingles du soir »
		Et j'ouvre le sonore « Aube – Matin clair » de la banque
		Et j'ouvre l'onglet « Banque : Jingles »
		Alors les boutons « Enregistrer » et « Annuler » de la fiche sont actifs
		Et aucune question n'a été posée

	Scénario: Un fichier déposé, pas encore enregistré, n'a pas encore de fiche
		Étant donné les fichiers « …/nouveau.ogg » du scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je dépose sur les sonores de la fiche « …/nouveau.ogg »
		Et j'ouvre le sonore « nouveau.ogg » de la banque
		Alors l'onglet ouvert est « Banque : Jingles »

	Scénario: Un sonore sans durée ou sans titre le montre, un fichier pas encore décodé par son nom
		Étant donné les sonores :
			| artiste | titre         | type    | etat   | duree | emplacement                 |
			|         | Direct studio | stream  | actif  |       | https://flux.exemple/direct |
			|         | Nouveau       | fichier | apercu |       | /srv/jingles/nouveau.flac   |
			|         |               | stream  | actif  |       | https://flux.exemple/autre  |
			| Aube    |               | fichier | actif  | 60    | /srv/jingles/aube.flac      |
			|         |               | fichier | apercu |       | /srv/jingles/brut.flac      |
		Et la banque « Tubes », aléatoire, sans nom public, avec « Direct studio », « Nouveau »
		Et les sonores sans titre « https://flux.exemple/autre », « /srv/jingles/aube.flac », « /srv/jingles/brut.flac » sont dans la banque « Tubes »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Tubes »
		Alors la fiche montre les sonores :
			| Sonore        | Durée    | État   | Emplacement                 |
			| Direct studio | inconnue | actif  | https://flux.exemple/direct |
			| Nouveau       |          | aperçu | /srv/jingles/nouveau.flac   |
			| (sans titre)  | inconnue | actif  | https://flux.exemple/autre  |
			| Aube          | 1:00     | actif  | /srv/jingles/aube.flac      |
			| brut.flac     |          | aperçu | /srv/jingles/brut.flac      |

	Scénario: Une fiche déjà ouverte revient au premier plan, sans second onglet
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ouvre l'onglet « Accueil »
		Et j'ouvre la fiche de la banque « Jingles »
		Alors l'onglet ouvert est « Banque : Jingles »
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents », « Banque : Jingles »

	Scénario: Chaque clic sur « Nouvelle banque » ouvre une nouvelle fiche
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je clique sur « Nouvelle banque »
		Et j'ouvre l'onglet « Banques »
		Et je clique sur « Nouvelle banque »
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents », « Nouvelle banque », « Nouvelle banque »

	Scénario: Seuls les onglets des fiches se ferment, pas ceux de l'accueil et des listes
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Alors seul l'onglet « Banque : Jingles » a un bouton de fermeture

	Scénario: Une fiche sans modification se ferme sans question
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je ferme l'onglet « Banque : Jingles »
		Alors aucune question n'a été posée
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents »
		Et la fiche fermée est libérée

	Plan du scénario: Fermer une fiche modifiée demande quoi faire de ses modifications
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne « Jingles du soir »
		Et je réponds « <reponse> » à la question de fermeture
		Et je ferme l'onglet « Banque : Jingles »
		Alors la question de fermeture a nommé « Banque : Jingles »
		Et la fenêtre <a ou non> d'onglet de fiche
		Et la banque « <nom> » est en base : nom public « Radio Thune », séquentielle, masquage « hérité du sonore », avec « ne pas répéter »

		Exemples:
			| reponse     | a ou non  | nom             |
			| Enregistrer | n'a plus  | Jingles du soir |
			| Abandonner  | n'a plus  | Jingles         |
			| Annuler     | a encore  | Jingles         |

	Plan du scénario: Fermer la fenêtre demande aussi quoi faire des fiches modifiées
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne « Jingles du soir »
		Et je réponds « <reponse> » à la question de fermeture
		Et je ferme la fenêtre de l'interface
		Alors la fenêtre de l'interface est <etat>
		Et la banque « <nom> » est en base : nom public « Radio Thune », séquentielle, masquage « hérité du sonore », avec « ne pas répéter »

		Exemples:
			| reponse     | etat     | nom             |
			| Enregistrer | fermée   | Jingles du soir |
			| Abandonner  | fermée   | Jingles         |
			| Annuler     | ouverte  | Jingles         |

	# ─── Modification ──────────────────────────────────────────

	Scénario: Les champs modifiés partent en base à l'enregistrement
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne « Jingles d'été »
		Et je saisis le nom public « Radio Thune, l'été »
		Et je choisis le mode « aléatoire »
		Et je choisis le masquage « masqués »
		Et je décoche « ne pas répéter »
		Alors la banque « Jingles » est en base : nom public « Radio Thune », séquentielle, masquage « hérité du sonore », avec « ne pas répéter »
		Quand j'enregistre la fiche
		Alors la banque « Jingles d'été » est en base : nom public « Radio Thune, l'été », aléatoire, masquage « masqués », sans « ne pas répéter »
		Et l'onglet ouvert est « Banque : Jingles d'été »

	Plan du scénario: Le masquage a trois valeurs, dont « hérité du sonore », qui laisse décider le sonore
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je choisis le masquage « masqués »
		Et j'enregistre la fiche
		Et je choisis le masquage « <masquage> »
		Et j'enregistre la fiche
		Alors la banque « Jingles » est en base : nom public « Radio Thune », séquentielle, masquage « <masquage> », avec « ne pas répéter »

		Exemples:
			| masquage         |
			| hérité du sonore |
			| masqués          |
			| affichés         |

	Plan du scénario: Cocher une durée des sonores d'une grande banque ne gèle pas la fiche
		https://github.com/dascritch/machincast/issues/194 : chaque marque posée ou effacée faisait recalculer la largeur de
		toute la colonne, et cocher la durée maximale, encore à 0:00:00, marquait d'un coup tous les sonores.

		Étant donné 3000 sonores de 3:00 de plus dans la banque « Jingles »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je coche la durée <borne> des sonores
		Alors la fiche a marqué hors des durées <marques> sonores en moins de 2 secondes

		Exemples:
			| borne    | marques |
			| maximale | 3002    |
			| minimale | 0       |

	# ─── Détection de blanc (https://github.com/dascritch/machincast/issues/146) ─────────────────

	Scénario: Une nouvelle banque n'active pas la détection de blanc
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je clique sur « Nouvelle banque »
		Alors la case « détection de blanc » de la fiche est décochée

	Scénario: La détection de blanc d'une banque part en base à l'enregistrement
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Alors la case « détection de blanc » de la fiche est décochée
		Quand je coche « détection de blanc »
		Alors la banque « Jingles » n'active pas la détection de blanc
		Quand j'enregistre la fiche
		Alors la banque « Jingles » active la détection de blanc
		Quand je décoche « détection de blanc »
		Et j'enregistre la fiche
		Alors la banque « Jingles » n'active pas la détection de blanc

	# ─── Crossfades (https://github.com/dascritch/machincast/issues/143) ─────────────────────────

	Scénario: Une banque laisse d'abord ses sonores décider de leurs crossfades
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je clique sur « Nouvelle banque »
		Alors la fiche montre les crossfades :
			| côté  | règle                   | durée | durée modifiable |
			| début | Garder ceux des sonores | 0,0 s | non              |
			| fin   | Garder ceux des sonores | 0,0 s | non              |
		Et le crossfade de début se règle parmi « Garder ceux des sonores », « Appliquer si le sonore n'en a pas », « Imposer à tous les sonores »

	Scénario: Les règles et les durées des crossfades partent en base à l'enregistrement, chaque côté la sienne
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je choisis pour le crossfade de début la règle « Imposer à tous les sonores »
		Et je saisis 1,5 seconde de crossfade de début dans la fiche
		Et je choisis pour le crossfade de fin la règle « Appliquer si le sonore n'en a pas »
		Et je saisis 2,2 seconde de crossfade de fin dans la fiche
		Alors la fiche montre les crossfades :
			| côté  | règle                             | durée  | durée modifiable |
			| début | Imposer à tous les sonores        | 1,5 s  | oui              |
			| fin   | Appliquer si le sonore n'en a pas | 2,2 s  | oui              |
		Quand j'enregistre la fiche
		Alors la banque « Jingles » a en base les crossfades « impose » 1,5 seconde au début, et « a_defaut » 2,2 secondes à la fin
		Quand je choisis pour le crossfade de début la règle « Garder ceux des sonores »
		Et j'enregistre la fiche
		Alors la banque « Jingles » a en base les crossfades « sonore » 1,5 seconde au début, et « a_defaut » 2,2 secondes à la fin
		Et la fiche montre les crossfades :
			| côté  | règle                             | durée  | durée modifiable |
			| début | Garder ceux des sonores           | 1,5 s  | non              |
			| fin   | Appliquer si le sonore n'en a pas | 2,2 s  | oui              |

	# ─── Durées des sonores (https://github.com/dascritch/machincast/issues/147) ───────────────────

	Scénario: Les durées minimale et maximale des sonores sont facultatives, et partent en base
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Alors la fiche montre les durées des sonores : minimale aucune, maximale aucune
		Quand je fixe la durée minimale des sonores à « 0:03:00 »
		Et je fixe la durée maximale des sonores à « 0:06:30 »
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et la banque « Jingles » a en base les durées des sonores de 180 à 390 secondes
		Quand je retire la durée minimale des sonores
		Et j'enregistre la fiche
		Alors la banque « Jingles » a en base les durées des sonores d'aucune à 390 secondes
		Et la fiche montre les durées des sonores : minimale aucune, maximale « 0:06:30 »

	Scénario: Une durée minimale plus longue que la maximale n'est pas enregistrée, et dit pourquoi
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je fixe la durée minimale des sonores à « 0:05:00 »
		Et je fixe la durée maximale des sonores à « 0:04:00 »
		Et j'enregistre la fiche
		Alors la fiche signale « La durée minimale des sonores dépasse la durée maximale. »
		Et l'erreur est en haut de la fiche, sur un liseret rouge de 4 pixels
		Et les champs signalés par ⚠️ sont « Durée minimale des sonores », « Durée maximale des sonores »
		Et la banque « Jingles » a en base les durées des sonores d'aucune à aucune secondes

	Scénario: Un sonore hors des durées de la banque est signalé dans sa liste, sans être refusé
		https://github.com/dascritch/machincast/issues/147 : le signalement est permissif ; il suit les durées de la fiche, avant même
		l'enregistrement. Un sonore de durée inconnue n'est pas signalé.

		Étant donné les sonores :
			| artiste | titre    | type    | etat   | duree | emplacement                 |
			|         | Inconnu  | fichier | apercu |       | /srv/jingles/hiver/inconnu.flac |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ajoute les sonores « Inconnu »
		Alors la fiche ne marque aucun sonore hors des durées
		Quand je fixe la durée minimale des sonores à « 0:03:20 »
		Et je fixe la durée maximale des sonores à « 0:03:34 »
		Alors la fiche ne marque aucun sonore hors des durées
		Quand je retire la durée maximale des sonores
		Et je fixe la durée minimale des sonores à « 0:03:30 »
		Alors la fiche marque hors des durées les sonores :
			| sonore             | infobulle                                                    |
			| Aube – Matin clair | 3:20 : plus court que le minimum de la banque, 3:30.         |
		Quand je fixe la durée maximale des sonores à « 0:03:30 »
		Alors la fiche marque hors des durées les sonores :
			| sonore                      | infobulle                                            |
			| Les Gaufres – Café à minuit | 3:34 : plus long que le maximum de la banque, 3:30.  |
			| Aube – Matin clair          | 3:20 : plus court que le minimum de la banque, 3:30. |
		Quand j'ajoute les sonores « Jingle »
		Alors la fiche marque hors des durées les sonores :
			| sonore                      | infobulle                                            |
			| Les Gaufres – Café à minuit | 3:34 : plus long que le maximum de la banque, 3:30.  |
			| Aube – Matin clair          | 3:20 : plus court que le minimum de la banque, 3:30. |
			| Jingle                      | 0:08 : plus court que le minimum de la banque, 3:30. |
		Quand j'enregistre la fiche
		Alors la fiche ne signale rien
		Et la banque « Jingles » a en base les durées des sonores de 210 à 210 secondes
		Quand je retire la durée minimale des sonores
		Et je retire la durée maximale des sonores
		Alors la fiche ne marque aucun sonore hors des durées

	Scénario: Les durées en base marquent les sonores dès l'ouverture, et changer une durée déjà fixée modifie la fiche
		Étant donné la banque « Jingles » veut des sonores d'au plus 3:30
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Alors la fiche montre les durées des sonores : minimale aucune, maximale « 0:03:30 »
		Et la fiche marque hors des durées les sonores :
			| sonore                      | infobulle                                           |
			| Les Gaufres – Café à minuit | 3:34 : plus long que le maximum de la banque, 3:30. |
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs
		Quand je fixe la durée maximale des sonores à « 0:20:00 »
		Alors la fiche ne marque aucun sonore hors des durées
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs

	Scénario: Un sonore hors des durées d'une autre banque n'est pas signalé dans celle-ci
		https://github.com/dascritch/machincast/issues/210 : chaque banque ne signale que ses propres durées.

		Étant donné la banque « Pubs », aléatoire, sans nom public, avec « Café à minuit », « Spot »
		Et la banque « Pubs » veut des sonores d'au moins 0:10 et d'au plus 1:00
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Alors la fiche ne marque aucun sonore hors des durées
		Quand j'ouvre la fiche de la banque « Pubs »
		Alors la fiche marque hors des durées les sonores :
			| sonore                      | infobulle                                           |
			| Les Gaufres – Café à minuit | 3:34 : plus long que le maximum de la banque, 1:00. |

	Scénario: Les noms sont enregistrés sans les espaces qui les entourent, et un nom public vide n'en est pas un
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne «  Jingles du soir  »
		Et je saisis le nom public «   »
		Et j'enregistre la fiche
		Alors la banque « Jingles du soir » est en base : sans nom public, séquentielle, masquage « hérité du sonore », avec « ne pas répéter »

	Plan du scénario: Une fiche invalide n'est pas enregistrée, et dit pourquoi
		Étant donné la banque « Tubes », aléatoire, sans nom public, avec « Spot »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne « <nom> »
		Et je saisis le nom public « Autre nom »
		Et j'enregistre la fiche
		Alors la fiche signale « <message> »
		Et la banque « Jingles » est en base : nom public « Radio Thune », séquentielle, masquage « hérité du sonore », avec « ne pas répéter »
		Et l'onglet ouvert est « Banque : Jingles »

		Exemples:
			| nom   | message                                    |
			|       | Le nom interne est obligatoire.            |
			| Tubes | Une autre banque s'appelle déjà « Tubes ». |

	Scénario: Un nom interne fait d'espaces est vide, donc refusé
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne «    »
		Et j'enregistre la fiche
		Alors la fiche signale « Le nom interne est obligatoire. »
		Et les champs signalés par ⚠️ sont « Nom interne »

	Scénario: Le message d'une fiche invalide s'efface à l'enregistrement suivant
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne «  »
		Et j'enregistre la fiche
		Et je saisis le nom interne « Jingles du soir »
		Et j'enregistre la fiche
		Alors la fiche ne signale rien

	Scénario: Une base injoignable à l'enregistrement est signalée, et la fiche garde ses modifications
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne « Jingles du soir »
		Et la base devient injoignable pour l'interface
		Et j'enregistre la fiche
		Alors la fiche signale un enregistrement impossible
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs
		Et la banque « Jingles » est en base : nom public « Radio Thune », séquentielle, masquage « hérité du sonore », avec « ne pas répéter »

	Scénario: « Annuler » remet la fiche telle qu'elle est en base
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne « Autre nom »
		Et je saisis le nom public « Autre »
		Et je choisis le mode « aléatoire »
		Et je choisis le masquage « affichés »
		Et je décoche « ne pas répéter »
		Et j'ajoute le répertoire « /srv/jingles/automne »
		Et je descends le sonore « Café à minuit »
		Et j'annule les modifications de la fiche
		Alors la fiche montre le nom interne « Jingles », le nom public « Radio Thune », le mode « séquentielle », le masquage « hérité du sonore » et « ne pas répéter » coché
		Et la fiche montre les répertoires « /srv/jingles/hiver »
		Et la fiche montre les sonores « Les Gaufres – Café à minuit », « Aube – Matin clair »
		Quand je ferme l'onglet « Banque : Jingles »
		Alors aucune question n'a été posée

	Plan du scénario: Toute modification de la fiche rend « Enregistrer » et « Annuler » actifs
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je réponds « Retirer quand même » à l'avertissement de réintégration
		Et <modification>
		Alors les boutons « Enregistrer » et « Annuler » de la fiche sont actifs

		Exemples:
			| modification                                                                                  |
			| je saisis le nom interne « Jingles du soir »                                                  |
			| je saisis le nom public « Radio Thune, le soir »                                              |
			| je choisis le mode « aléatoire »                                                              |
			| je choisis le masquage « masqués »                                                            |
			| je décoche « ne pas répéter »                                                                 |
			| je choisis pour le crossfade de début la règle « Imposer à tous les sonores »                 |
			| je choisis pour le crossfade de fin la règle « Garder ceux des sonores »                      |
			| je saisis 2 seconde de crossfade de fin dans la fiche                                         |
			| je fixe la durée minimale des sonores à « 0:01:00 »                                           |
			| je fixe la durée maximale des sonores à « 0:10:00 »                                           |
			| j'ajoute le répertoire « /srv/jingles/automne »                                               |
			| je retire le répertoire « /srv/jingles/hiver »                                                |
			| j'ajoute les sonores « Spot »                                                                 |
			| je retire le sonore « Café à minuit »                                                         |
			| je descends le sonore « Café à minuit »                                                       |
			| je monte le sonore « Matin clair »                                                            |

	Scénario: Les boutons « Enregistrer » et « Annuler » ne servent qu'à une fiche modifiée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Alors les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs
		Quand je coche « ne pas répéter »
		Et je décoche « ne pas répéter »
		Alors les boutons « Enregistrer » et « Annuler » de la fiche sont actifs
		Quand j'enregistre la fiche
		Alors les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs

	# ─── Nouvelle banque ───────────────────────────────────────

	Scénario: Une nouvelle banque se crée depuis la liste des banques
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je clique sur « Nouvelle banque »
		Alors l'onglet ouvert est « Nouvelle banque »
		Et la fiche montre le nom interne «  », le nom public «  », le mode « séquentielle », le masquage « hérité du sonore » et « ne pas répéter » décoché
		Quand je saisis le nom interne « Habillage »
		Et j'ajoute le répertoire « /srv/habillage/ »
		Et j'enregistre la fiche
		Alors la banque « Habillage » est en base : sans nom public, séquentielle, masquage « hérité du sonore », sans « ne pas répéter »
		Et les répertoires de la banque « Habillage » sont « /srv/habillage » en base
		Et l'onglet ouvert est « Banque : Habillage »
		Quand j'ouvre l'onglet « Banques »
		Alors la liste montre :
			| Nom       | Nom public  | Mode         | Ne pas répéter | Répertoire         |
			| Habillage |             | séquentielle | non            | /srv/habillage     |
			| Jingles   | Radio Thune | séquentielle | oui            | /srv/jingles/hiver |
		Quand j'ouvre la ligne « Habillage »
		Alors l'onglet ouvert est « Banque : Habillage »
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents », « Banque : Habillage »

	# ─── Répertoires ───────────────────────────────────────────

	Scénario: Une banque a plusieurs répertoires, qui s'ajoutent et se retirent
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ajoute le répertoire « /srv/jingles/automne »
		Et j'ajoute le répertoire « /srv/jingles/printemps »
		Et j'ajoute le répertoire « /srv/jingles/automne »
		Et je retire le répertoire « /srv/jingles/hiver »
		Alors la fiche montre les répertoires « /srv/jingles/automne », « /srv/jingles/printemps »
		Quand j'enregistre la fiche
		Alors les répertoires de la banque « Jingles » sont « /srv/jingles/automne », « /srv/jingles/printemps » en base

	Scénario: Les répertoires sont rangés dans l'ordre de leurs caractères
		Étant donné les répertoires « /srv/jingles/printemps », « /srv/jingles/automne » de la banque « Jingles »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Alors la fiche montre les répertoires « /srv/jingles/automne », « /srv/jingles/hiver », « /srv/jingles/printemps »
		Quand j'ajoute le répertoire « /srv/jingles/bis »
		Alors la fiche montre les répertoires « /srv/jingles/automne », « /srv/jingles/bis », « /srv/jingles/hiver », « /srv/jingles/printemps »

	Scénario: Un répertoire déjà présent n'est pas ajouté de nouveau
		Étant donné les dossiers « …/jingles/automne » du scénario
		Et les répertoires « …/jingles/automne » de la banque « Jingles »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ajoute le répertoire « /srv/jingles/hiver/ »
		Et je dépose sur les répertoires de la fiche « …/jingles/automne »
		Alors la fiche montre les répertoires « /srv/jingles/hiver », « …/jingles/automne »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs

	Scénario: Renoncer au choix d'un répertoire ne change rien
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je renonce à choisir un répertoire
		Alors la fiche montre les répertoires « /srv/jingles/hiver »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs

	# ─── Sonores ───────────────────────────────────────────────

	Scénario: Les sonores se réordonnent, et l'ordre part en base
		Étant donné la banque « Tubes », séquentielle, sans nom public, avec « Café à minuit », « Matin clair », « Jingle »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Tubes »
		Et je choisis le sonore « Café à minuit »
		Et je clique sur « Descendre »
		Et je clique sur « Descendre »
		Et je choisis le sonore « Matin clair »
		Et je clique sur « Monter »
		Alors la fiche montre les sonores « Aube – Matin clair », « Jingle », « Les Gaufres – Café à minuit »
		Quand j'enregistre la fiche
		Alors les sonores de la banque « Tubes » sont, dans l'ordre, « Matin clair », « Jingle », « Café à minuit »

	Scénario: Les boutons d'une ligne ne servent qu'à une ligne choisie, et « Monter » et « Descendre » pas aux extrémités
		Étant donné la banque « Tubes », séquentielle, sans nom public, avec « Café à minuit », « Matin clair », « Jingle »
		Et les répertoires « /srv/jingles/hiver », « /srv/habillage » de la banque « Tubes »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Tubes »
		Alors les boutons de ligne actifs de la fiche sont aucun
		Quand je choisis le répertoire « /srv/habillage »
		Et je choisis le sonore « Café à minuit »
		Alors les boutons de ligne actifs de la fiche sont « Retirer le répertoire », « Retirer le sonore », « Descendre »
		Quand je choisis le sonore « Matin clair »
		Alors les boutons de ligne actifs de la fiche sont « Retirer le répertoire », « Retirer le sonore », « Monter », « Descendre »
		Quand je clique sur « Descendre »
		Alors les boutons de ligne actifs de la fiche sont « Retirer le répertoire », « Retirer le sonore », « Monter »
		Quand je clique sur « Retirer le répertoire »
		Et je clique sur « Retirer le répertoire »
		Et je réponds « Retirer quand même » à l'avertissement de réintégration
		Et je clique sur « Retirer le sonore »
		Alors la fiche montre les répertoires aucun
		Et la fiche montre les sonores « Les Gaufres – Café à minuit », « Jingle »
		Et les boutons de ligne actifs de la fiche sont « Retirer le sonore », « Monter »
		Quand j'ajoute les sonores « Spot »
		Alors les boutons de ligne actifs de la fiche sont « Retirer le sonore », « Monter », « Descendre »

	Scénario: Une ligne de sonore ne se dépose pas dans une autre
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Alors aucune ligne de sonore de la fiche n'accepte qu'on y dépose une autre

	Plan du scénario: Le glisser-déposer et les boutons pour réordonner ne servent qu'en mode séquentiel
		Étant donné la banque « Tubes », <mode depart>, sans nom public, avec « Spot », « Jingle », « Café à minuit »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Tubes »
		Et je choisis le sonore « Jingle »
		Alors les sonores de la fiche <verdict depart> se réordonner
		Et les répertoires et les sonores de la fiche acceptent les dépôts
		Quand je choisis le mode « <mode> »
		Alors les sonores de la fiche <verdict> se réordonner
		Et les répertoires et les sonores de la fiche acceptent les dépôts

		Exemples:
			| mode depart  | verdict depart | mode         | verdict        |
			| séquentielle | peuvent        | aléatoire    | ne peuvent pas |
			| aléatoire    | ne peuvent pas | séquentielle | peuvent        |

	Scénario: Des sonores déjà en base s'ajoutent, y compris hors des répertoires de la banque
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ajoute les sonores « Jingle », « Spot », « Café à minuit »
		Alors le choix a précisé « Un sonore qui est déjà dans la banque n'y est pas ajouté une seconde fois. »
		Et la fiche montre les sonores « Les Gaufres – Café à minuit », « Aube – Matin clair », « Jingle », « Spot »
		Quand j'enregistre la fiche
		Alors les sonores de la banque « Jingles » sont, dans l'ordre, « Café à minuit », « Matin clair », « Jingle », « Spot »

	Scénario: Un sonore effacé de la base pendant son choix n'est pas ajouté
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ajoute les sonores « Jingle », « Spot », en effaçant « Jingle » de la base pendant le choix
		Alors la fiche montre les sonores « Les Gaufres – Café à minuit », « Aube – Matin clair », « Spot »

	Scénario: Un sonore effacé de la base pendant la modification n'est pas enregistré
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ajoute les sonores « Jingle », « Spot »
		Et le sonore « Jingle » est effacé de la base
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et les sonores de la banque « Jingles » sont, dans l'ordre, « Café à minuit », « Matin clair », « Spot »

	Scénario: Retirer un sonore placé hors des répertoires de la banque ne demande rien
		Étant donné les sonores :
			| artiste | titre         | type   | etat  | duree | emplacement                 |
			|         | Direct studio | stream | actif |       | https://flux.exemple/direct |
		Et la banque « Tubes », aléatoire, sans nom public, avec « Spot », « Café à minuit », « Direct studio »
		Et les répertoires « /srv/jingles/hiver », « /srv/pub » de la banque « Tubes »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Tubes »
		Et je retire le sonore « Spot »
		Et je retire le sonore « Direct studio »
		Alors aucune question n'a été posée
		Quand j'enregistre la fiche
		Alors les sonores de la banque « Tubes » sont, dans l'ordre, « Café à minuit »

	Plan du scénario: Retirer un sonore issu d'un répertoire de la banque prévient qu'il sera réintégré
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je réponds « <reponse> » à l'avertissement de réintégration
		Et je retire le sonore « Café à minuit »
		Alors l'avertissement de réintégration nomme « Les Gaufres – Café à minuit », le répertoire « /srv/jingles/hiver » et la prochaine indexation
		Et la fiche montre les sonores <sonores>
		Et le navigateur de fichiers a ouvert <dossier>

		Exemples:
			| reponse            | sonores                                                    | dossier                |
			| Retirer quand même | « Aube – Matin clair »                                     | aucun dossier          |
			| Ouvrir le dossier  | « Les Gaufres – Café à minuit », « Aube – Matin clair »    | « /srv/jingles/hiver » |
			| Annuler            | « Les Gaufres – Café à minuit », « Aube – Matin clair »    | aucun dossier          |

	Scénario: L'avertissement vaut aussi pour un sonore d'un sous-répertoire, et pour un répertoire pas encore enregistré
		Étant donné les sonores :
			| artiste | titre | type    | etat  | duree | emplacement                         |
			|         | Neige | fichier | actif | 12    | /srv/jingles/automne/neige/neige.ogg |
		Et la banque « Tubes », aléatoire, sans nom public, avec « Neige »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Tubes »
		Et j'ajoute le répertoire « /srv/jingles/automne »
		Et je réponds « Ouvrir le dossier » à l'avertissement de réintégration
		Et je retire le sonore « Neige »
		Alors l'avertissement de réintégration nomme « Neige », le répertoire « /srv/jingles/automne » et la prochaine indexation
		Et le navigateur de fichiers a ouvert « /srv/jingles/automne/neige »

	Scénario: Le retrait d'un sonore part en base à l'enregistrement
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je réponds « Retirer quand même » à l'avertissement de réintégration
		Et je retire le sonore « Café à minuit »
		Et j'enregistre la fiche
		Alors les sonores de la banque « Jingles » sont, dans l'ordre, « Matin clair »
		Et le sonore « Café à minuit » est toujours en base

	Scénario: Les sonores qu'une indexation rattache pendant la modification sont gardés, en fin de liste
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je descends le sonore « Café à minuit »
		Et l'indexation rattache le sonore « Jingle » à la banque « Jingles »
		Et j'enregistre la fiche
		Alors les sonores de la banque « Jingles » sont, dans l'ordre, « Matin clair », « Café à minuit », « Jingle »
		Et la fiche montre les sonores « Aube – Matin clair », « Les Gaufres – Café à minuit », « Jingle »

	Scénario: Un sonore ajouté à la fiche, et qu'une indexation rattache aussi pendant la modification, n'y est qu'une fois
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ajoute les sonores « Jingle »
		Et l'indexation rattache le sonore « Jingle » à la banque « Jingles »
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et les sonores de la banque « Jingles » sont, dans l'ordre, « Café à minuit », « Matin clair », « Jingle »

	# ─── Dépôt depuis le navigateur de fichiers ────────────────

	Scénario: Des dossiers déposés sur les répertoires s'y ajoutent, et un fichier est ignoré
		Étant donné les dossiers « …/jingles/automne », « …/jingles/printemps » du scénario
		Et les fichiers « …/notes.txt » du scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je dépose sur les répertoires de la fiche « …/jingles/printemps/ », « …/notes.txt », « …/jingles/automne », « …/jingles/printemps »
		Alors le dépôt est accepté comme une copie
		Et la fiche montre les répertoires « /srv/jingles/hiver », « …/jingles/automne », « …/jingles/printemps »
		Et la fiche signale « Ignorés, ce ne sont pas des répertoires : notes.txt. »
		Quand j'enregistre la fiche
		Et je dépose sur les répertoires de la fiche « …/jingles/automne/../printemps/ »
		Alors la fiche ne signale rien
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs
		Alors les répertoires de la banque « Jingles » sont « /srv/jingles/hiver », « …/jingles/automne », « …/jingles/printemps » en base

	Scénario: Des fichiers sonores déposés sur les sonores s'ajoutent, en base ou non, et le reste est ignoré
		Étant donné les dossiers « …/nouveaux », « …/album.flac » du scénario
		Et les fichiers « …/jingles/neige.flac », « …/nouveaux/Gros titre.MP3 », « …/notes.txt » du scénario
		Et les sonores :
			| artiste | titre | type    | etat  | duree | emplacement           |
			|         | Neige | fichier | actif | 12    | …/jingles/neige.flac  |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je dépose sur les sonores de la fiche « …/nouveaux/Gros titre.MP3 », « …/nouveaux/../jingles/neige.flac », « …/notes.txt », « …/nouveaux », « …/album.flac », « …/nouveaux/Gros titre.MP3 »
		Alors le dépôt est accepté comme une copie
		Et la fiche montre les sonores :
			| Sonore                      | Durée | État   | Emplacement                   |
			| Les Gaufres – Café à minuit | 3:34  | actif  | /srv/jingles/hiver/cafe.flac  |
			| Aube – Matin clair          | 3:20  | actif  | /srv/jingles/hiver/matin.flac |
			| Gros titre.MP3              |       | aperçu | …/nouveaux/Gros titre.MP3     |
			| Neige                       | 0:12  | actif  | …/jingles/neige.flac          |
		Et la fiche signale « Ignorés, ce ne sont pas des fichiers sonores : notes.txt, nouveaux, album.flac. Un dossier se dépose sur les répertoires indexés. »
		Et le fichier « …/nouveaux/Gros titre.MP3 » n'est pas en base
		Quand j'enregistre la fiche
		Alors les sonores de la banque « Jingles » sont, dans l'ordre, « Café à minuit », « Matin clair », le fichier « …/nouveaux/Gros titre.MP3 », « Neige »
		Et le fichier « …/nouveaux/Gros titre.MP3 » est en base, à l'état aperçu, sans artiste ni titre
		Et les fichiers déposés sont intacts
		Et la fiche montre les sonores « Les Gaufres – Café à minuit », « Aube – Matin clair », « Gros titre.MP3 », « Neige »

	Scénario: Un fichier sonore déjà dans la fiche, déposé de nouveau, n'y est qu'une fois
		Étant donné les fichiers « …/jingles/neige.flac », « …/a.ogg », « …/b.ogg » du scénario
		Et les sonores :
			| artiste | titre | type    | etat  | duree | emplacement          |
			|         | Neige | fichier | actif | 12    | …/jingles/neige.flac |
		Et la banque « Tubes », aléatoire, sans nom public, avec « Neige »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Tubes »
		Et je dépose sur les sonores de la fiche « …/jingles/neige.flac »
		Alors la fiche montre les sonores « Neige »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs
		Quand je dépose sur les sonores de la fiche « …/a.ogg », « …/b.ogg »
		Alors la fiche montre les sonores « Neige », « a.ogg », « b.ogg »
		Quand je dépose sur les sonores de la fiche « …/b.ogg », « …/a.ogg »
		Alors la fiche montre les sonores « Neige », « a.ogg », « b.ogg »
		Et la fiche ne signale rien

	Scénario: Les boutons de ligne suivent les sonores déposés
		Étant donné les fichiers « …/nouveau.ogg » du scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je choisis le sonore « Matin clair »
		Alors les boutons de ligne actifs de la fiche sont « Retirer le sonore », « Monter »
		Quand je dépose sur les sonores de la fiche « …/nouveau.ogg »
		Alors les boutons de ligne actifs de la fiche sont « Retirer le sonore », « Monter », « Descendre »

	Scénario: Un glisser abandonné avant le dépôt ne change rien
		Étant donné les dossiers « …/jingles/automne » du scénario
		Et les fichiers « …/nouveau.ogg » du scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je glisse sans les déposer sur les répertoires de la fiche « …/jingles/automne »
		Et je glisse sans les déposer sur les sonores de la fiche « …/nouveau.ogg »
		Alors la fiche montre les répertoires « /srv/jingles/hiver »
		Et la fiche montre les sonores « Les Gaufres – Café à minuit », « Aube – Matin clair »
		Et la fiche ne signale rien
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs

	Scénario: Un fichier déposé, enregistré par une indexation avant l'enregistrement de la fiche, est repris
		Étant donné les fichiers « …/nouveau.ogg » du scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je dépose sur les sonores de la fiche « …/nouveau.ogg »
		Et l'indexation enregistre le fichier « …/nouveau.ogg »
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et les sonores de la banque « Jingles » sont, dans l'ordre, « Café à minuit », « Matin clair », le fichier « …/nouveau.ogg »

	Scénario: Un fichier déposé puis annulé n'entre pas en base
		Étant donné les fichiers « …/nouveau.ogg » du scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je dépose sur les sonores de la fiche « …/nouveau.ogg »
		Et j'annule les modifications de la fiche
		Alors la fiche montre les sonores « Les Gaufres – Café à minuit », « Aube – Matin clair »
		Et le fichier « …/nouveau.ogg » n'est pas en base

	Plan du scénario: Un glisser qui ne propose pas la copie est refusé : la fiche ne déplace jamais un fichier
		Étant donné les dossiers « …/jingles/automne » du scénario
		Et les fichiers « …/nouveau.ogg » du scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je dépose sur les <liste> de la fiche « <chemin> », en ne proposant que le déplacement
		Alors le dépôt est refusé
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs

		Exemples:
			| liste       | chemin             |
			| répertoires | …/jingles/automne  |
			| sonores     | …/nouveau.ogg      |

	Plan du scénario: Un glisser sans fichier local n'est pas pris par la fiche
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je dépose sur les <liste> de la fiche <quoi>
		Alors le dépôt est refusé
		Et la fiche ne signale rien
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs

		Exemples:
			| liste       | quoi                               |
			| répertoires | un texte                           |
			| sonores     | un texte                           |
			| répertoires | « https://exemple.org/hiver/ »     |
			| sonores     | « https://exemple.org/neige.flac » |

	# ─── Choix des sonores à ajouter ───────────────────────────

	Scénario: Le choix des sonores à ajouter se filtre, et en prend plusieurs à la fois
		Quand j'ouvre le choix des sonores
		Et je tape « srv/jingles » dans le filtre du choix des sonores
		Et je sélectionne toutes les lignes du choix des sonores
		Alors le choix des sonores donne « Matin clair », « Café à minuit »

	Scénario: Le choix des sonores les donne dans l'ordre de la liste, quel que soit l'ordre des clics
		Quand j'ouvre le choix des sonores
		Et je sélectionne les lignes « Spot », puis « Café à minuit » du choix des sonores
		Alors le choix des sonores donne « Café à minuit », « Spot »

	Scénario: Ouvrir une ligne du choix des sonores la choisit
		Quand j'ouvre le choix des sonores
		Et j'ouvre la ligne « Spot » du choix des sonores
		Alors le choix des sonores est validé
		Et le choix des sonores donne « Spot »
