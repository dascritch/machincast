# language: fr
Fonctionnalité: Listes filtrables des sonores, des banques, des séquences et des événements
	En tant que programmateur de l'antenne,
	je veux une liste filtrable pour chaque type d'élément,
	afin que j'accède rapidement à l'écran de détail voulu.

	https://github.com/dascritch/machincast/issues/26, spec § 8.2. La fenêtre de l'interface a un onglet par écran :
	l'écran d'accueil, ouvert par défaut, puis une liste par type d'élément. Les listes se lisent dans la base de test,
	avec le rôle de l'interface ; la fenêtre s'affiche hors de l'écran du poste.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-16 20:00:30 »

	# ─── Onglets ───────────────────────────────────────────────

	Scénario: La fenêtre s'ouvre sur l'accueil, suivi d'un onglet par liste
		Quand la fenêtre de l'interface s'ouvre
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores »
		Et l'onglet ouvert est « Accueil »
		Et l'onglet « Accueil » montre l'écran par défaut

	# ─── Contenu des listes ────────────────────────────────────

	Scénario: La liste des sonores
		Étant donné les sonores :
			| artiste     | titre         | type    | etat      | duree | emplacement                         |
			| Les Gaufres | Café à minuit | fichier | actif     | 214   | /srv/musique/cafe.flac              |
			|             | Jingle        | fichier | apercu    |       | /srv/habillage/jingle.flac          |
			| Aube        | Matin clair   | fichier | desactive | 3725  | /srv/musique/matin.flac             |
			|             | Direct studio | stream  | actif     |       | https://flux.exemple/direct         |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors la liste montre :
			| Artiste     | Titre         | Type    | État      | Durée   | Emplacement                 |
			| Aube        | Matin clair   | fichier | désactivé | 1:02:05 | /srv/musique/matin.flac     |
			| Les Gaufres | Café à minuit | fichier | actif     | 3:34    | /srv/musique/cafe.flac      |
			|             | Direct studio | stream  | actif     | inconnue | https://flux.exemple/direct |
			|             | Jingle        | fichier | aperçu    |         | /srv/habillage/jingle.flac  |
		Et le compte de la liste est « 4 sonores »

	Scénario: La liste des banques
		Étant donné les sonores :
			| artiste | titre | type    | etat  | duree | emplacement   |
			|         | j1    | fichier | actif | 8     | /srv/j1.flac  |
			|         | j2    | fichier | actif | 8     | /srv/j2.flac  |
		Et la banque « Jingles », séquentielle, de nom public « Radio Thune », marquée « ne pas répéter », avec « j1 », « j2 »
		Et la banque « Tubes », aléatoire, sans nom public, avec « j1 »
		Et les répertoires « /srv/jingles/hiver », « /srv/jingles/automne » de la banque « Jingles »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Alors la liste montre :
			| Nom     | Nom public  | Mode         | Ne pas répéter | Répertoire           |
			| Jingles | Radio Thune | séquentielle | oui            | /srv/jingles/automne |
			| Tubes   |             | aléatoire    | non            |                      |
		Et le compte de la liste est « 2 banques »

	Scénario: La liste des séquences
		Étant donné les sonores :
			| artiste | titre | type    | etat  | duree | emplacement  |
			|         | j1    | fichier | actif | 8     | /srv/j1.flac |
		Et la banque « Tubes », aléatoire, sans nom public, avec « j1 »
		Et la séquence « Passage pub », de nom public « Vous écoutez Radio Thune », avec le sonore « j1 » et la banque « Tubes »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Alors la liste montre :
			| Nom         | Nom public               |
			| Passage pub | Vous écoutez Radio Thune |
		Et le compte de la liste est « 1 séquence »

	Scénario: La liste des événements, du plus prioritaire au moins prioritaire
		Étant donné les événements :
			| nom       | nom_public    | priorite    | debut            | fin              | jours                     |
			| Continue  |               | fil_musical |                  |                  |                           |
			| Magazine  | Le magazine   | emission    | 2026-10-12 20:00 | 2026-10-12 21:00 | lundi, mercredi, vendredi |
			| Élections | Soirée élection | special   | 2026-10-18 20:00 |                  |                           |
			| Secours   |               | secours     |                  |                  |                           |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Alors la liste montre :
			| Nom       | Nom public      | Priorité    | Début            | Fin              | Récurrence                |
			| Élections | Soirée élection | spécial     | 2026-10-18 20:00 |                  |                           |
			| Magazine  | Le magazine     | émission    | 2026-10-12 20:00 | 2026-10-12 21:00 | lundi, mercredi, vendredi |
			| Continue  |                 | fil musical |                  |                  |                           |
			| Secours   |                 | secours     |                  |                  |                           |
		Et le compte de la liste est « 4 événements »

	Scénario: Une liste se relit chaque fois que son onglet s'ouvre
		Étant donné les sonores :
			| artiste | titre | type    | etat  | duree | emplacement  |
			|         | j1    | fichier | actif | 8     | /srv/j1.flac |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et le sonore « j2 » est ajouté en base
		Et j'ouvre l'onglet « Accueil »
		Et j'ouvre l'onglet « Sonores »
		Alors le compte de la liste est « 2 sonores »

	Scénario: Une liste vide le dit
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Alors le compte de la liste est « aucune séquence »

	# ─── Filtre ─────────────────────────────────────────────────

	Plan du scénario: Le filtre garde les lignes qui contiennent le texte, dans n'importe quelle colonne, sans tenir compte des majuscules ni des accents
		Étant donné les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement                 |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/musique/minuit.flac    |
			| Élodie      | Été indien    | fichier | actif | 180   | /srv/musique/indien.flac    |
			|             | Direct studio | stream  | actif |       | https://flux.exemple/direct |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je tape « <filtre> » dans le filtre de la liste
		Alors la liste montre les titres <titres>
		Et le compte de la liste est « <compte> »

		Exemples:
			| filtre  | titres                                     | compte          |
			| gauf    | « Café à minuit »                          | 1 sonore sur 3  |
			| CAFE    | « Café à minuit »                          | 1 sonore sur 3  |
			| ete     | « Été indien »                             | 1 sonore sur 3  |
			| ÉLODIE  | « Été indien »                             | 1 sonore sur 3  |
			| les gauf | « Café à minuit »                         | 1 sonore sur 3  |
			| stream  | « Direct studio »                          | 1 sonore sur 3  |
			| /srv/   | « Café à minuit », « Été indien »          | 2 sonores sur 3 |
			| xyz     | aucun                                      | 0 sonore sur 3  |

	Scénario: Un clic sur le titre d'une colonne trie la liste
		Étant donné les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement              |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/musique/minuit.flac |
			| Aube        | Matin clair   | fichier | actif | 200   | /srv/musique/matin.flac  |
			| Zébulon     | Avril         | fichier | actif | 100   | /srv/musique/avril.flac  |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors la liste montre les titres « Matin clair », « Café à minuit », « Avril »
		Quand je clique sur le titre de la colonne « Titre »
		Alors la liste montre les titres « Avril », « Café à minuit », « Matin clair »

	Scénario: Le filtre se garde quand la liste se relit
		Étant donné les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement            |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/musique/cafe.flac |
			|             | Jingle        | fichier | actif | 8     | /srv/jingle.flac       |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je tape « café » dans le filtre de la liste
		Et j'ouvre l'onglet « Accueil »
		Et j'ouvre l'onglet « Sonores »
		Alors la liste montre les titres « Café à minuit »

	# ─── Vers l'écran de détail ────────────────────────────────

	Plan du scénario: Ouvrir une ligne demande l'écran de détail de l'élément, et l'annonce tant qu'il est à venir
		# Ceux d'une banque et d'un sonore sont leurs fiches : fiche_banque.feature, fiche_sonore.feature.
		Étant donné les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement            |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/musique/cafe.flac |
		Et la banque « Tubes », aléatoire, sans nom public, avec « Café à minuit »
		Et la séquence « Passage pub », de nom public « Vous écoutez Radio Thune », avec le sonore « Café à minuit » et la banque « Tubes »
		Et les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « <onglet> »
		Et j'ouvre la ligne « <nom> »
		Alors l'écran de détail de <genre> « <nom> » est demandé
		Et la barre d'état annonce « <annonce> »

		Exemples:
			| onglet     | nom           | genre        | annonce                                                                                  |
			| Séquences  | Passage pub   | séquence     | Écran de détails de la séquence « Passage pub » : à venir, https://github.com/dascritch/machincast/issues/112 |
			| Événements | Continue      | événement    | Écran de détails de l'événement « Continue » : à venir, https://github.com/dascritch/machincast/issues/32 |

	Scénario: Le filtre ne change pas l'élément ouvert
		Étant donné les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement            |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/musique/cafe.flac |
			| Aube        | Matin clair   | fichier | actif | 200   | /srv/musique/matin.flac |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je tape « café » dans le filtre de la liste
		Et j'ouvre la ligne « Café à minuit »
		Alors l'écran de détail de sonore « Café à minuit » est demandé
