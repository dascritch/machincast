# language: fr
Fonctionnalité: Listes filtrables des sonores, des banques, des séquences et des événements
	En tant que programmateur de l'antenne,
	je veux une liste filtrable pour chaque type d'élément,
	afin que j'accède rapidement à l'écran de détail voulu.

	https://github.com/dascritch/machincast/issues/26, spec § 8.2. La fenêtre de l'interface a un onglet par écran :
	l'onglet Antenne, ouvert par défaut, puis une liste par type d'élément. Les listes se lisent dans la base de test,
	avec le rôle de l'interface ; la fenêtre s'affiche hors de l'écran du poste.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-16 20:00:30 »

	# ─── Onglets ───────────────────────────────────────────────

	Scénario: La fenêtre s'ouvre sur l'onglet Antenne, suivi d'un onglet par liste
		Quand la fenêtre de l'interface s'ouvre
		Alors la fenêtre a les onglets « Antenne », « Calendrier », « Événements », « Séquences », « Banques », « Incidents »
		Et l'onglet ouvert est « Antenne »
		Et l'onglet « Antenne » montre l'écran par défaut

	# ─── Contenu des listes ────────────────────────────────────

	Scénario: La liste des sonores
		Étant donné les sonores :
			| artist      | title         | type   | state    | duration | location                    |
			| Les Gaufres | Café à minuit | file   | active   | 214      | /srv/musique/cafe.flac      |
			|             | Jingle        | file   | preview  |          | /srv/habillage/jingle.flac  |
			| Aube        | Matin clair   | file   | disabled | 3725     | /srv/musique/matin.flac     |
			|             | Direct studio | stream | active   |          | https://flux.exemple/direct |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors la liste montre :
			| ⚠️ | Artiste     | Titre         | Type    | État      | Durée    | Emplacement                 |
			|    | Aube        | Matin clair   | fichier | désactivé | 1:02:05  | /srv/musique/matin.flac     |
			|    | Les Gaufres | Café à minuit | fichier | actif     | 3:34     | /srv/musique/cafe.flac      |
			|    |             | Direct studio | stream  | actif     | inconnue | https://flux.exemple/direct |
			|    |             | Jingle        | fichier | aperçu    |          | /srv/habillage/jingle.flac  |
		Et le compte de la liste est « 4 sonores »

	Scénario: Un sonore hors des durées d'une banque n'est pas signalé dans la liste des sonores
		https://github.com/dascritch/machincast/issues/210 : les durées d'une banque ne concernent que ses sonores ; seule
		la fiche de la banque, et la fiche du sonore parmi ses relations, le signalent.

		Étant donné les sonores :
			| artist      | title         | type | state  | duration | location               |
			| Les Gaufres | Café à minuit | file | active | 214      | /srv/musique/cafe.flac |
			|             | Spot          | file | active | 30       | /srv/pubs/spot.flac    |
		Et la banque « Chansons », aléatoire, sans nom public, avec « Café à minuit », « Spot »
		Et la banque « Chansons » veut des sonores de 2:00 à 6:00
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors la liste montre :
			| ⚠️ | Artiste     | Titre         | Type    | État  | Durée | Emplacement            |
			|    | Les Gaufres | Café à minuit | fichier | actif | 3:34  | /srv/musique/cafe.flac |
			|    |             | Spot          | fichier | actif | 0:30  | /srv/pubs/spot.flac    |
		Et le compte de la liste est « 2 sonores »
		Et la liste marque en anomalie les lignes et infobulles :
			| ligne | infobulle |

	Scénario: La liste des banques
		Étant donné les sonores :
			| artist | title | type | state  | duration | location     |
			|        | j1    | file | active | 8        | /srv/j1.flac |
			|        | j2    | file | active | 8        | /srv/j2.flac |
		Et la banque « Jingles », séquentielle, de nom public « Radio Thune », marquée « ne pas répéter », avec « j1 », « j2 »
		Et la banque « Tubes », aléatoire, sans nom public, avec « j1 »
		Et les répertoires « /srv/jingles/hiver », « /srv/jingles/automne » de la banque « Jingles »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Alors la liste montre :
			| ⚠️ | Nom     | Nom public  | Mode         | Ne pas répéter | Répertoire           |
			|    | Jingles | Radio Thune | séquentielle | oui            | /srv/jingles/automne |
			|    | Tubes   |             | aléatoire    | non            |                      |
		Et le compte de la liste est « 2 banques »

	Scénario: La liste des séquences
		Étant donné les sonores :
			| artist | title | type | state  | duration | location     |
			|        | j1    | file | active | 8        | /srv/j1.flac |
		Et la banque « Tubes », aléatoire, sans nom public, avec « j1 »
		Et la séquence « Passage pub », de nom public « Vous écoutez Radio Thune », avec le sonore « j1 », la banque « Tubes »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Alors la liste montre :
			| ⚠️ | Nom         | Nom public               | Anomalie |
			|    | Passage pub | Vous écoutez Radio Thune |          |
		Et le compte de la liste est « 1 séquence »

	Scénario: Une séquence vide est signalée en anomalie dans la liste
		https://github.com/dascritch/machincast/issues/138 : une séquence vide s'enregistre, pour être complétée plus tard.

		Étant donné les sonores :
			| artist | title | type | state  | duration | location     |
			|        | j1    | file | active | 8        | /srv/j1.flac |
		Et la séquence « Passage pub », sans nom public, avec le sonore « j1 »
		Et la séquence « Brouillon », sans nom public, avec rien
		Et la séquence « Habillage », sans nom public, avec rien
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Alors la liste montre :
			| ⚠️ | Nom         | Nom public | Anomalie      |
			| ⚠️ | Brouillon   |            | séquence vide |
			| ⚠️ | Habillage   |            | séquence vide |
			|    | Passage pub |            |               |
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
			| name      | public_name     | priority               | starts_at        | ends_at          | days                      |
			| Continue  |                 | background_programming |                  |                  |                           |
			| Magazine  | Le magazine     | show                   | 2026-10-12 20:00 | 2026-10-12 21:00 | monday, wednesday, friday |
			| Élections | Soirée élection | special                | 2026-10-18 20:00 |                  |                           |
			| Secours   |                 | fallback               |                  |                  |                           |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Alors la liste montre :
			| ⚠️ | Nom       | Nom public      | Priorité    | Début            | Fin              | Récurrence                | Anomalie       |
			| ⚠️ | Élections | Soirée élection | spécial     | 2026-10-18 20:00 |                  |                           | événement vide |
			| ⚠️ | Magazine  | Le magazine     | émission    | 2026-10-12 20:00 | 2026-10-12 21:00 | lundi, mercredi, vendredi | événement vide |
			| ⚠️ | Continue  |                 | fil musical |                  |                  |                           | événement vide |
			| ⚠️ | Secours   |                 | secours     |                  |                  |                           | événement vide |
		Et le compte de la liste est « 4 événements, dont 4 en anomalie »

	Scénario: Un événement vide est signalé en anomalie dans la liste, avec ce que fait la diffusion selon sa priorité
		https://github.com/dascritch/machincast/issues/140 : un événement vide s'enregistre, pour être complété plus tard.

		Étant donné les sonores :
			| artist | title | type | state  | duration | location     |
			|        | j1    | file | active | 8        | /srv/j1.flac |
		Et les événements :
			| name      | public_name | priority               | starts_at        | ends_at          | days |
			| Continue  |             | background_programming |                  |                  |      |
			| Nuit      |             | background_programming | 2026-10-12 00:00 | 2026-10-12 06:00 |      |
			| Magazine  |             | show                   | 2026-10-12 20:00 | 2026-10-12 21:00 |      |
			| Élections |             | special                | 2026-10-18 20:00 |                  |      |
			| Secours   |             | fallback               |                  |                  |      |
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

	Scénario: Un secours qui fait appel à un flux externe est signalé en anomalie dans la liste
		https://github.com/dascritch/machincast/issues/403 : directement, par une banque ou par une séquence ; un
		autre événement peut jouer un stream.

		Étant donné les sonores :
			| artist | title       | type   | state  | duration | location                    |
			|        | j1          | file   | active | 8        | /srv/j1.flac                |
			|        | Radio Thune | stream | active |          | https://flux.exemple/direct |
		Et la banque « Relais », séquentielle, sans nom public, avec « Radio Thune »
		Et les événements :
			| name     | public_name | priority | starts_at        | ends_at          | days |
			| Continue |             | background_programming |                  |                  |      |
			| Direct   |             | show     | 2026-10-12 20:00 | 2026-10-12 21:00 |      |
			| Panne    |             | fallback |                  |                  |      |
			| Relève   |             | fallback |                  |                  |      |
			| Attente  |             | fallback |                  |                  |      |
		Et l'événement « Direct » joue le sonore « Radio Thune »
		Et l'événement « Panne » joue le sonore « Radio Thune »
		Et l'événement « Relève » joue la banque « Relais »
		Et l'événement « Attente » joue le sonore « j1 »
		Et l'événement « Continue » joue le sonore « j1 »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Alors le compte de la liste est « 5 événements, dont 2 en anomalie »
		Et la liste marque en anomalie les lignes et infobulles :
			| ligne  | infobulle |
			| Panne  | Un secours qui fait appel à un flux externe n'est pas recommandé : une perte du réseau le ferait taire, comme le flux qu'il secourt. |
			| Relève | Un secours qui fait appel à un flux externe n'est pas recommandé : une perte du réseau le ferait taire, comme le flux qu'il secourt. |

	Scénario: Une émission vide qui prête son nom au fil musical n'est pas en anomalie
		https://github.com/dascritch/machincast/issues/399 : sans liste, elle prête son nom pendant toute sa plage.

		Étant donné les sonores :
			| artist | title | type | state  | duration | location     |
			|        | j1    | file | active | 8        | /srv/j1.flac |
		Et les événements :
			| name     | public_name | priority               | starts_at        | ends_at          | days |
			| Continue |             | background_programming |                  |                  |      |
			| Magazine | Le magazine | show                   | 2026-10-12 20:00 | 2026-10-12 21:00 |      |
		Et l'événement « Continue » joue le sonore « j1 »
		Et l'événement « Magazine » prête, à la fin de sa liste, son nom au fil musical
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Alors le compte de la liste est « 2 événements »

	# ─── Colonne d'anomalie (https://github.com/dascritch/machincast/issues/327) ───

	Plan du scénario: La liste des <onglet> a, tout à gauche, la colonne d'anomalie
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « <onglet> »
		Alors la première colonne de la liste est « ⚠️ », avec l'infobulle « Anomalie : la ligne a un problème, que dit son infobulle »

		Exemples:
			| onglet     |
			| Événements |
			| Séquences  |
			| Banques    |
			| Sonores    |

	Scénario: La liste des feeds n'a pas de colonne d'anomalie
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Feeds »
		Alors la liste n'a pas de colonne « ⚠️ »

	Scénario: Une banque sans sonore actif, ou avec un sonore erroné ou non supporté, est signalée en anomalie dans la liste
		Étant donné les sonores :
			| artist | title | type | state       | duration | location     |
			|        | j1    | file | active      | 8        | /srv/j1.flac |
			|        | j2    | file | disabled    | 8        | /srv/j2.flac |
			|        | j3    | file | preview     | 8        | /srv/j3.flac |
			|        | j4    | file | corrupt     | 8        | /srv/j4.flac |
			|        | j5    | file | unsupported | 8        | /srv/j5.png  |
		Et la banque « Jingles », séquentielle, sans nom public, avec « j1 », « j2 »
		Et la banque « Archives », séquentielle, sans nom public, avec « j2 », « j3 »
		Et la banque « Nouveautés », aléatoire, sans nom public, avec rien
		Et la banque « Pubs », aléatoire, sans nom public, avec « j1 », « j4 »
		Et la banque « Spots », aléatoire, sans nom public, avec « j1 », « j4 », « j5 »
		Et la banque « Trous », aléatoire, sans nom public, avec « j4 »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Alors le compte de la liste est « 6 banques, dont 5 en anomalie »
		Et la liste marque en anomalie les lignes et infobulles :
			| ligne      | infobulle |
			| Archives   | Banque sans sonore actif : elle ne fournit rien, et l'élément qui l'appelle passe à son élément suivant. |
			| Nouveautés | Banque sans sonore actif : elle ne fournit rien, et l'élément qui l'appelle passe à son élément suivant. |
			| Pubs       | Banque avec 1 sonore erroné ou non supporté : la diffusion ne le joue pas. |
			| Spots      | Banque avec 2 sonores erronés ou non supportés : la diffusion ne les joue pas. |
			| Trous      | Banque sans sonore actif : elle ne fournit rien, et l'élément qui l'appelle passe à son élément suivant. |

	Scénario: Un sonore erroné ou non supporté est signalé en anomalie dans la liste ; désactivé, expiré ou en aperçu, non
		Étant donné les sonores :
			| artist | title     | type | state       | duration | location            |
			|        | Abîmé     | file | corrupt     | 8        | /srv/abime.flac     |
			|        | Actif     | file | active      | 8        | /srv/actif.flac     |
			|        | Aperçu    | file | preview     | 8        | /srv/apercu.flac    |
			|        | Désactivé | file | disabled    | 8        | /srv/desactive.flac |
			|        | Expiré    | file | expired     | 8        | /srv/expire.flac    |
			|        | Image     | file | unsupported | 8        | /srv/image.png      |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors le compte de la liste est « 6 sonores, dont 2 en anomalie »
		Et la liste marque en anomalie les lignes et infobulles :
			| ligne | infobulle |
			| Abîmé | Sonore erroné : son fichier est illisible ou endommagé, et la diffusion ne le joue pas. |
			| Image | Sonore non supporté : son fichier n'est pas un son lisible, et la diffusion ne le joue pas. |

	Scénario: La colonne d'anomalie trie les lignes en anomalie ensemble
		Étant donné les sonores :
			| artist | title | type | state  | duration | location     |
			|        | j1    | file | active | 8        | /srv/j1.flac |
		Et la séquence « Passage pub », sans nom public, avec le sonore « j1 »
		Et la séquence « Brouillon », sans nom public, avec rien
		Et la séquence « Zapping », sans nom public, avec rien
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Et je clique sur le titre de la colonne « ⚠️ »
		Alors la colonne « Nom » de la liste montre « Passage pub », « Brouillon », « Zapping »
		Quand je clique sur le titre de la colonne « ⚠️ »
		Alors la colonne « Nom » de la liste montre « Brouillon », « Zapping », « Passage pub »

	Scénario: Une liste se relit chaque fois que son onglet s'ouvre
		Étant donné les sonores :
			| artist | title | type | state  | duration | location     |
			|        | j1    | file | active | 8        | /srv/j1.flac |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et le sonore « j2 » est ajouté en base
		Et j'ouvre l'onglet « Antenne »
		Et j'ouvre l'onglet « Sonores »
		Alors le compte de la liste est « 2 sonores »

	Scénario: Une liste vide le dit
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Alors le compte de la liste est « aucune séquence »

	# ─── Filtre ─────────────────────────────────────────────────

	Plan du scénario: Le filtre garde les lignes qui contiennent le texte, dans n'importe quelle colonne, sans tenir compte des majuscules ni des accents
		Étant donné les sonores :
			| artist      | title         | type   | state  | duration | location                    |
			| Les Gaufres | Café à minuit | file   | active | 214      | /srv/musique/minuit.flac    |
			| Zélie       | Été indien    | file   | active | 180      | /srv/musique/indien.flac    |
			|             | Direct studio | stream | active |          | https://flux.exemple/direct |
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
			| artist      | title         | type | state  | duration | location                 |
			| Les Gaufres | Café à minuit | file | active | 214      | /srv/musique/minuit.flac |
			| Aube        | Matin clair   | file | active | 200      | /srv/musique/matin.flac  |
			| Zébulon     | Avril         | file | active | 100      | /srv/musique/avril.flac  |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors la liste montre les titres « Matin clair », « Café à minuit », « Avril »
		Quand je clique sur le titre de la colonne « Titre »
		Alors la liste montre les titres « Avril », « Café à minuit », « Matin clair »

	# ─── Pages de la liste des sonores (https://github.com/dascritch/machincast/issues/383) ───

	Scénario: La liste des sonores ne lit d'abord que sa première page, et la suite en descendant
		Étant donné 250 sonores sans artiste ni titre, de /srv/grande/1.flac à /srv/grande/250.flac
		Et les fiches chargent leurs tableaux par 100 lignes
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors la table de la liste a 100 lignes
		Et le compte de la liste est « 250 sonores »
		Quand je descends au bas de la table de la liste
		Alors la table de la liste a 200 lignes
		Quand je descends au bas de la table de la liste
		Alors la table de la liste a 250 lignes

	Scénario: Le tri d'une colonne porte sur tous les sonores, pas seulement ceux déjà lus
		Étant donné 250 sonores sans artiste ni titre, de /srv/grande/1.flac à /srv/grande/250.flac
		Et les sonores :
			| artist  | title | type | state  | duration | location                |
			| Zébulon | Avril | file | active | 100      | /srv/musique/avril.flac |
		Et les fiches chargent leurs tableaux par 100 lignes
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je clique sur le titre de la colonne « Emplacement »
		Et je clique sur le titre de la colonne « Emplacement »
		Alors la première ligne de la liste a pour titre « Avril »
		Et la table de la liste a 100 lignes

	Scénario: Le filtre cherche parmi tous les sonores, sans tenir compte des accents, et le compte les dit tous
		Étant donné 250 sonores sans artiste ni titre, de /srv/grande/1.flac à /srv/grande/250.flac
		Et les sonores :
			| artist  | title | type | state   | duration | location                |
			| Zébulon | Avril | file | corrupt | 100      | /srv/musique/avril.flac |
		Et les fiches chargent leurs tableaux par 100 lignes
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je tape « zebu » dans le filtre de la liste
		Alors la liste montre les titres « Avril »
		Et le compte de la liste est « 1 sonore sur 251, dont 1 en anomalie »

	Scénario: Un clic sur le titre « Priorité » classe les événements par importance, pas par ordre alphabétique
		https://github.com/dascritch/machincast/issues/272 : imprévu (https://github.com/dascritch/machincast/issues/402),
		spécial, émission, fil musical, secours ; un second clic inverse l'ordre.

		Étant donné les événements :
			| name     | public_name | priority               | starts_at        | ends_at          | days |
			| Aide     |             | fallback               |                  |                  |      |
			| Alerte   |             | breaking               | 2026-10-17 09:00 | 2026-10-17 09:05 |      |
			| Concert  |             | special                | 2026-10-17 20:00 | 2026-10-17 22:00 |      |
			| Continue |             | background_programming |                  |                  |      |
			| Journal  |             | show                   | 2026-10-17 12:00 | 2026-10-17 12:30 |      |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Événements »
		Et je clique sur le titre de la colonne « Nom »
		Alors la colonne « Priorité » de la liste montre « secours », « imprévu », « spécial », « fil musical », « émission »
		Quand je clique sur le titre de la colonne « Priorité »
		Alors la colonne « Priorité » de la liste montre « imprévu », « spécial », « émission », « fil musical », « secours »
		Et la colonne « Nom » de la liste montre « Alerte », « Concert », « Journal », « Continue », « Aide »
		Quand je clique sur le titre de la colonne « Priorité »
		Alors la colonne « Priorité » de la liste montre « secours », « fil musical », « émission », « spécial », « imprévu »

	Scénario: Un clic sur le titre « Durée » classe les sonores du plus court au plus long, ceux sans durée à la fin
		https://github.com/dascritch/machincast/issues/302 : par les secondes, pas par le texte ; un fichier pas encore
		mesuré vient après les durées connues, et un stream, qui n'a pas de fin, en dernier.

		Étant donné les sonores :
			| artist | title   | type   | state  | duration | location                    |
			| A      | Dix     | file   | active | 600      | /srv/musique/dix.flac       |
			| B      | Heure   | file   | active | 3725     | /srv/musique/heure.flac     |
			| C      | Deux    | file   | active | 120      | /srv/musique/deux.flac      |
			| D      | Direct  | stream | active |          | https://flux.exemple/direct |
			| E      | Inconnu | file   | active |          | /srv/musique/inconnu.flac   |
			| F      | Trois   | file   | active | 214      | /srv/musique/trois.flac     |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je clique sur le titre de la colonne « Durée »
		Alors la colonne « Titre » de la liste montre « Deux », « Trois », « Dix », « Heure », « Inconnu », « Direct »
		Quand je clique sur le titre de la colonne « Durée »
		Alors la colonne « Titre » de la liste montre « Direct », « Inconnu », « Heure », « Dix », « Trois », « Deux »

	Plan du scénario: Les dates et les jours des événements se trient dans l'ordre du temps, ceux qui n'en ont pas à la fin
		https://github.com/dascritch/machincast/issues/302

		Étant donné les événements :
			| name     | public_name | priority               | starts_at        | ends_at          | days            |
			| Continue |             | background_programming |                  |                  |                 |
			| Soirée   |             | show                   | 2026-10-20 20:00 | 2026-10-20 23:00 | thursday        |
			| Matinale |             | show                   | 2026-10-19 07:00 | 2026-10-19 09:00 | monday, tuesday |
			| Midi     |             | show                   | 2026-10-21 12:00 | 2026-10-21 13:00 | wednesday       |
			| Hebdo    |             | show                   | 2026-10-23 08:00 | 2026-10-23 09:00 | friday, monday  |
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
			| artist      | title         | type | state  | duration | location               |
			| Les Gaufres | Café à minuit | file | active | 214      | /srv/musique/cafe.flac |
			|             | Jingle        | file | active | 8        | /srv/jingle.flac       |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je tape « café » dans le filtre de la liste
		Et j'ouvre l'onglet « Antenne »
		Et j'ouvre l'onglet « Sonores »
		Alors la liste montre les titres « Café à minuit »

	# ─── Vers l'écran de détail ────────────────────────────────

	Scénario: Le filtre ne change pas l'élément ouvert
		Étant donné les sonores :
			| artist      | title         | type | state  | duration | location                |
			| Les Gaufres | Café à minuit | file | active | 214      | /srv/musique/cafe.flac  |
			| Aube        | Matin clair   | file | active | 200      | /srv/musique/matin.flac |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je tape « café » dans le filtre de la liste
		Et j'ouvre la ligne « Café à minuit »
		Alors l'écran de détail de sonore « Café à minuit » est demandé
