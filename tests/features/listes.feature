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
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents »
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
			| Artiste     | Titre         | Type    | État      | Durée    | Emplacement                 |
			| Aube        | Matin clair   | fichier | désactivé | 1:02:05  | /srv/musique/matin.flac     |
			| Les Gaufres | Café à minuit | fichier | actif     | 3:34     | /srv/musique/cafe.flac      |
			|             | Direct studio | stream  | actif     | inconnue | https://flux.exemple/direct |
			|             | Jingle        | fichier | aperçu    |          | /srv/habillage/jingle.flac  |
		Et le compte de la liste est « 4 sonores »

	Scénario: Un sonore hors des durées d'une banque n'est pas signalé dans la liste des sonores
		https://github.com/dascritch/machincast/issues/210 : les durées d'une banque ne concernent que ses sonores ; seule
		la fiche de la banque, et la fiche du sonore parmi ses relations, le signalent.

		Étant donné les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement            |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/musique/cafe.flac |
			|             | Spot          | fichier | actif | 30    | /srv/pubs/spot.flac    |
		Et la banque « Chansons », aléatoire, sans nom public, avec « Café à minuit », « Spot »
		Et la banque « Chansons » veut des sonores de 2:00 à 6:00
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors la liste montre :
			| Artiste     | Titre         | Type    | État  | Durée | Emplacement            |
			| Les Gaufres | Café à minuit | fichier | actif | 3:34  | /srv/musique/cafe.flac |
			|             | Spot          | fichier | actif | 0:30  | /srv/pubs/spot.flac    |
		Et le compte de la liste est « 2 sonores »
		Et la liste marque en anomalie les lignes et infobulles :
			| ligne | infobulle |

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
		Et la séquence « Passage pub », de nom public « Vous écoutez Radio Thune », avec le sonore « j1 », la banque « Tubes »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Alors la liste montre :
			| Nom         | Nom public               | Anomalie |
			| Passage pub | Vous écoutez Radio Thune |          |
		Et le compte de la liste est « 1 séquence »

	Scénario: Une séquence vide est signalée en anomalie dans la liste
		https://github.com/dascritch/machincast/issues/138 : une séquence vide s'enregistre, pour être complétée plus tard.

		Étant donné les sonores :
			| artiste | titre | type    | etat  | duree | emplacement  |
			|         | j1    | fichier | actif | 8     | /srv/j1.flac |
		Et la séquence « Passage pub », sans nom public, avec le sonore « j1 »
		Et la séquence « Brouillon », sans nom public, avec rien
		Et la séquence « Habillage », sans nom public, avec rien
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Alors la liste montre :
			| Nom         | Nom public | Anomalie      |
			| Brouillon   |            | séquence vide |
			| Habillage   |            | séquence vide |
			| Passage pub |            |               |
		Et le compte de la liste est « 3 séquences, dont 2 en anomalie »
		Et la liste marque en anomalie les lignes « Brouillon », « Habillage », avec l'infobulle « Séquence vide : elle ne joue rien, et un événement qui l'appelle passe à son élément suivant. »
		Quand je tape « vide » dans le filtre de la liste
		Alors le compte de la liste est « 2 séquences sur 3, dont 2 en anomalie »
		Quand je tape « pub » dans le filtre de la liste
		Alors le compte de la liste est « 1 séquence sur 3 »
		Quand je tape « brouillon » dans le filtre de la liste
		Alors le compte de la liste est « 1 séquence sur 3, dont 1 en anomalie »

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
			| Nom       | Nom public      | Priorité    | Début            | Fin              | Récurrence                | Anomalie       |
			| Élections | Soirée élection | spécial     | 2026-10-18 20:00 |                  |                           | événement vide |
			| Magazine  | Le magazine     | émission    | 2026-10-12 20:00 | 2026-10-12 21:00 | lundi, mercredi, vendredi | événement vide |
			| Continue  |                 | fil musical |                  |                  |                           | événement vide |
			| Secours   |                 | secours     |                  |                  |                           | événement vide |
		Et le compte de la liste est « 4 événements, dont 4 en anomalie »

	Scénario: Un événement vide est signalé en anomalie dans la liste, avec ce que fait la diffusion selon sa priorité
		https://github.com/dascritch/machincast/issues/140 : un événement vide s'enregistre, pour être complété plus tard.

		Étant donné les sonores :
			| artiste | titre | type    | etat  | duree | emplacement  |
			|         | j1    | fichier | actif | 8     | /srv/j1.flac |
		Et les événements :
			| nom       | nom_public | priorite    | debut            | fin              | jours |
			| Continue  |            | fil_musical |                  |                  |       |
			| Nuit      |            | fil_musical | 2026-10-12 00:00 | 2026-10-12 06:00 |       |
			| Magazine  |            | emission    | 2026-10-12 20:00 | 2026-10-12 21:00 |       |
			| Élections |            | special     | 2026-10-18 20:00 |                  |       |
			| Secours   |            | secours     |                  |                  |       |
		Et l'événement « Continue » joue le sonore « j1 »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Alors le compte de la liste est « 5 événements, dont 4 en anomalie »
		Et la liste marque en anomalie les lignes et infobulles :
			| ligne     | infobulle |
			| Élections | Événement vide : il ne joue rien, et l'événement de priorité inférieure prend le relais pendant sa plage. |
			| Magazine  | Événement vide : il ne joue rien, et l'événement de priorité inférieure prend le relais pendant sa plage. |
			| Nuit      | Événement vide : il ne joue rien, et la diffusion se tait, avec une alerte, quand il est à l'antenne. |
			| Secours   | Événement vide : il ne joue rien, et l'événement de priorité inférieure remplace le stream tombé. |

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
			| Zélie       | Été indien    | fichier | actif | 180   | /srv/musique/indien.flac    |
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
			| ZÉLIE   | « Été indien »                             | 1 sonore sur 3  |
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

	Scénario: Un clic sur le titre « Priorité » classe les événements par importance, pas par ordre alphabétique
		https://github.com/dascritch/machincast/issues/272 : spécial, émission, fil musical, secours ; un second clic
		inverse l'ordre.

		Étant donné les événements :
			| nom      | nom_public | priorite    | debut            | fin              | jours |
			| Aide     |            | secours     |                  |                  |       |
			| Concert  |            | special     | 2026-10-17 20:00 | 2026-10-17 22:00 |       |
			| Continue |            | fil_musical |                  |                  |       |
			| Journal  |            | emission    | 2026-10-17 12:00 | 2026-10-17 12:30 |       |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Et je clique sur le titre de la colonne « Nom »
		Alors la colonne « Priorité » de la liste montre « secours », « spécial », « fil musical », « émission »
		Quand je clique sur le titre de la colonne « Priorité »
		Alors la colonne « Priorité » de la liste montre « spécial », « émission », « fil musical », « secours »
		Et la colonne « Nom » de la liste montre « Concert », « Journal », « Continue », « Aide »
		Quand je clique sur le titre de la colonne « Priorité »
		Alors la colonne « Priorité » de la liste montre « secours », « fil musical », « émission », « spécial »

	Scénario: Un clic sur le titre « Durée » classe les sonores du plus court au plus long, ceux sans durée à la fin
		https://github.com/dascritch/machincast/issues/302 : par les secondes, pas par le texte ; un fichier pas encore
		mesuré vient après les durées connues, et un stream, qui n'a pas de fin, en dernier.

		Étant donné les sonores :
			| artiste | titre    | type    | etat  | duree | emplacement                 |
			| A       | Dix      | fichier | actif | 600   | /srv/musique/dix.flac       |
			| B       | Heure    | fichier | actif | 3725  | /srv/musique/heure.flac     |
			| C       | Deux     | fichier | actif | 120   | /srv/musique/deux.flac      |
			| D       | Direct   | stream  | actif |       | https://flux.exemple/direct |
			| E       | Inconnu  | fichier | actif |       | /srv/musique/inconnu.flac   |
			| F       | Trois    | fichier | actif | 214   | /srv/musique/trois.flac     |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je clique sur le titre de la colonne « Durée »
		Alors la colonne « Titre » de la liste montre « Deux », « Trois », « Dix », « Heure », « Inconnu », « Direct »
		Quand je clique sur le titre de la colonne « Durée »
		Alors la colonne « Titre » de la liste montre « Direct », « Inconnu », « Heure », « Dix », « Trois », « Deux »

	Plan du scénario: Les dates et les jours des événements se trient dans l'ordre du temps, ceux qui n'en ont pas à la fin
		https://github.com/dascritch/machincast/issues/302

		Étant donné les événements :
			| nom      | nom_public | priorite    | debut            | fin              | jours           |
			| Continue |            | fil_musical |                  |                  |                 |
			| Soirée   |            | emission    | 2026-10-20 20:00 | 2026-10-20 23:00 | jeudi           |
			| Matinale |            | emission    | 2026-10-19 07:00 | 2026-10-19 09:00 | lundi, mardi    |
			| Midi     |            | emission    | 2026-10-21 12:00 | 2026-10-21 13:00 | mercredi        |
			| Hebdo    |            | emission    | 2026-10-23 08:00 | 2026-10-23 09:00 | vendredi, lundi |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Et je clique sur le titre de la colonne « <colonne> »
		Alors la colonne « Nom » de la liste montre <noms>

		Exemples:
			| colonne    | noms                                                          |
			| Début      | « Matinale », « Soirée », « Midi », « Hebdo », « Continue »   |
			| Fin        | « Matinale », « Soirée », « Midi », « Hebdo », « Continue »   |
			| Récurrence | « Matinale », « Hebdo », « Midi », « Soirée », « Continue »   |

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
