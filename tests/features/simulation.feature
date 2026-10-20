# language: fr
Fonctionnalité: Mode simulation de Machin lecture
	En tant que programmateur de l'antenne,
	je veux que le binaire simule ce qu'il diffuserait entre deux dates,
	afin que je vérifie une grille avant sa mise à l'antenne.

	https://github.com/dascritch/machincast/issues/21, spec § 5.5. La simulation lit la base dans une seule
	transaction en lecture seule : PostgreSQL y refuse toute écriture. Les passages, le log et les expirations
	simulés restent en mémoire. Aucun son n'est joué : la diffusion avance d'échéance en échéance, à l'horloge de la
	simulation. Les durées sont celles de la base : les sonores des scénarios y durent une minute.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et des sorties de simulation dans un répertoire temporaire, avec le texte public « Radio Exemple »

	# ─── Ce qui serait diffusé ─────────────────────────────────

	Scénario: La simulation donne ce qui serait diffusé, sans rien écrire en base
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 1 minute
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:05 »
		Alors la simulation donne les passages :
			| debut               | fin                 | titre |
			| 2026-10-20 20:00:00 | 2026-10-20 20:01:00 | f1    |
			| 2026-10-20 20:01:00 | 2026-10-20 20:02:00 | f2    |
			| 2026-10-20 20:02:00 | 2026-10-20 20:03:00 | f1    |
			| 2026-10-20 20:03:00 | 2026-10-20 20:04:00 | f2    |
			| 2026-10-20 20:04:00 | 2026-10-20 20:05:00 | f1    |
		Et la base n'a pas changé

	Scénario: Pendant la simulation, PostgreSQL refuse toute écriture
		Quand une écriture dans le log est tentée pendant une simulation
		Alors PostgreSQL la refuse, la transaction étant en lecture seule

	Scénario: La simulation ne joue aucun son, même sans sortie audio disponible
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et chaque sonore dure 1 minute
		Et aucune sortie audio ne peut être créée
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:02 »
		Alors la simulation donne 2 passages

	# ─── État de départ et état en mémoire ─────────────────────

	Scénario: L'état de départ est lu dans l'airplay
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Et chaque sonore dure 1 minute
		Et « f2 » a été joué dans le fil « Continue » le « 2026-10-19 08:00 »
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:02 »
		Alors la simulation donne les titres « f3 », « f1 »

	Scénario: Les cycles aléatoires suivent les passages simulés, tenus en mémoire
		Étant donné le fil musical permanent « Continue », avec la banque aléatoire « Rotation » des sonores « a », « b », « c »
		Et chaque sonore dure 1 minute
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:06 », avec la graine 3
		Alors chaque tranche de 3 passages joue « a », « b » et « c », chacun une fois

	Scénario: Avec la même graine, la simulation donne le même résultat
		Étant donné le fil musical permanent « Continue », avec la banque aléatoire « Rotation » des sonores « a », « b », « c », « d », « e »
		Et chaque sonore dure 1 minute
		Quand je simule deux fois la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:10 », avec la graine 7
		Alors les deux simulations donnent les mêmes passages

	Scénario: Le maximum de lectures compte les passages simulés, et l'expiration reste en mémoire
		Étant donné le fil musical permanent « Continue », avec les sonores « annonce », « f1 »
		Et chaque sonore dure 1 minute
		Et le sonore « annonce » a un maximum de 2 lectures
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:06 »
		Alors la simulation donne les titres « annonce », « f1 », « annonce », « f1 », « f1 », « f1 »
		Et la simulation a consigné 1 info « sonore expiré »
		Et le sonore « annonce » est toujours à l'état « actif » en base

	Scénario: Une banque « ne pas répéter » ne passe pas deux fois de suite, d'après l'airplay puis les passages simulés
		Étant donné la banque séquentielle « Jingles » des sonores « j1 », « j2 », marquée « ne pas répéter »
		Et le fil musical permanent « Continue », avec la banque « Jingles », la banque « Jingles » et le sonore « f »
		Et chaque sonore dure 1 minute
		Et « j1 » a été joué via la banque « Jingles » le « 2026-10-19 08:00 »
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:03 »
		Alors la simulation donne les titres « f », « j2 », « f »
		Et la simulation a consigné 3 info « élément sauté »
		Et la base n'a pas changé

	Scénario: Une séquence est simulée comme à la diffusion, et ses sorties la masquent par son nom public
		Étant donné la banque « Spots » des sonores « a », « b », de nom public « Publicité »
		Et la séquence « Pub », qui appelle deux fois la banque « Spots », de nom public « Vous écoutez Radio Thune », masquée
		Et le fil musical permanent « Continue », avec la séquence « Pub » et le sonore « f »
		Et chaque sonore dure 1 minute
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:04 »
		Alors la simulation donne les titres « a », « b », « f », « a »
		Et les sorties de la simulation montrent « f », mais pas « b », remplacé par « Vous écoutez Radio Thune »
		Et le CSV de la simulation nomme la séquence « Pub » pour 3 passages

	# ─── Grille ────────────────────────────────────────────────

	Scénario: Une émission coupe net à son heure, puis son dernier sonore va jusqu'au bout
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et l'émission « Flash » du « 2026-10-20 20:02:30 » au « 2026-10-20 20:04:00 », avec le sonore « m »
		Et chaque sonore dure 1 minute
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:06 »
		Alors la simulation donne les passages :
			| debut               | fin                 | titre |
			| 2026-10-20 20:00:00 | 2026-10-20 20:01:00 | f1    |
			| 2026-10-20 20:01:00 | 2026-10-20 20:02:00 | f1    |
			| 2026-10-20 20:02:00 | 2026-10-20 20:02:30 | f1    |
			| 2026-10-20 20:02:30 | 2026-10-20 20:03:30 | m     |
			| 2026-10-20 20:03:30 | 2026-10-20 20:04:30 | m     |
			| 2026-10-20 20:04:30 | 2026-10-20 20:05:30 | f1    |
			| 2026-10-20 20:05:30 | 2026-10-20 20:06:00 | f1    |

	Scénario: Les crossfades sont simulés
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 1 minute
		Et chaque sonore a 10 seconde de crossfade de début et de fin
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:02 »
		Alors la simulation donne les passages :
			| debut               | fin                 | titre |
			| 2026-10-20 20:00:00 | 2026-10-20 20:01:00 | f1    |
			| 2026-10-20 20:00:50 | 2026-10-20 20:01:50 | f2    |
			| 2026-10-20 20:01:40 | 2026-10-20 20:02:00 | f1    |

	Scénario: Les crossfades qu'une banque impose sont simulés
		https://github.com/dascritch/machincast/issues/143

		Étant donné le fil musical permanent « Continue », avec la banque séquentielle « Titres » des sonores « f1 », « f2 »
		Et chaque sonore dure 1 minute
		Et la banque « Titres » impose 10 seconde de crossfade de début
		Et la banque « Titres » applique à défaut 20 seconde de crossfade de fin
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:02 »
		Alors la simulation donne les passages :
			| debut               | fin                 | titre |
			| 2026-10-20 20:00:00 | 2026-10-20 20:01:00 | f1    |
			| 2026-10-20 20:00:40 | 2026-10-20 20:01:40 | f2    |
			| 2026-10-20 20:01:20 | 2026-10-20 20:02:00 | f1    |

	Scénario: Les crossfades par défaut de la configuration sont simulés
		https://github.com/dascritch/machincast/issues/145

		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 1 minute
		Et les crossfades par défaut de la configuration sont de 10 seconde au début et de 10 à la fin
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:02 »
		Alors la simulation donne les passages :
			| debut               | fin                 | titre |
			| 2026-10-20 20:00:00 | 2026-10-20 20:01:00 | f1    |
			| 2026-10-20 20:00:50 | 2026-10-20 20:01:50 | f2    |
			| 2026-10-20 20:01:40 | 2026-10-20 20:02:00 | f1    |

	Scénario: Un stream simulé dure jusqu'à la fin de son événement, sans contacter le flux
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et le stream « Direct » à l'adresse « http://127.0.0.1:9/aucun-flux »
		Et l'émission « Direct » du « 2026-10-20 20:01:00 » au « 2026-10-20 20:03:00 », avec le sonore « Direct »
		Et chaque sonore dure 1 minute
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:04 »
		Alors la simulation donne les passages :
			| debut               | fin                 | titre  |
			| 2026-10-20 20:00:00 | 2026-10-20 20:01:00 | f1     |
			| 2026-10-20 20:01:00 | 2026-10-20 20:03:00 | Direct |
			| 2026-10-20 20:03:00 | 2026-10-20 20:04:00 | f1     |

	# ─── Sorties ───────────────────────────────────────────────

	Scénario: Les sorties sont nommées par défaut « simulation » suivi des dates, pour toute la période
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 1 minute
		Et le masquage de tous les sonores
		Quand je simule la diffusion du « 2026-10-20 23:58 » au « 2026-10-21 00:02 »
		Alors la simulation a écrit « simulation-2026-10-20T2358-2026-10-21T0002 » en .csv, .pls et .html
		Et le CSV de la simulation a 4 lignes de passage, sur les deux jours
		Et la playlist de la simulation compte 4 entrées
		Et la page de la simulation montre l'emplacement de chaque fichier joué

	Scénario: Les sorties de la simulation masquent l'artiste et le titre comme la page publique, et donnent l'emplacement
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et chaque sonore dure 1 minute
		Et le masquage du sonore « f2 »
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:02 »
		Alors les sorties de la simulation montrent « f1 », mais pas « f2 », remplacé par « Radio Exemple »
		Et les sorties de la simulation donnent l'emplacement des fichiers de « f1 » et de « f2 »

	Scénario: Le nom des sorties se change par paramètre
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et chaque sonore dure 1 minute
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:01 », sous le nom « essai-grille »
		Alors la simulation a écrit « essai-grille » en .csv, .pls et .html

	Scénario: La page de la simulation signale les alertes et incidents simulés
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 »
		Et le sonore « f1 » est à l'état « desactive »
		Quand je simule la diffusion du « 2026-10-20 20:00 » au « 2026-10-20 20:01 »
		Alors la page de la simulation signale l'alerte « silence »
		Et le journal du binaire a signalé « simulation : 2026-10-20 20:00:00 : alerte : silence »

	# ─── Ligne de commande ─────────────────────────────────────

	Plan du scénario: Machin lecture refuse une période de simulation invalide
		Quand je lance Machin_lecture avec « --simulation <debut> <fin> »
		Alors il s'arrête avec le code 2, en signalant « <motif> »

		Exemples:
			| debut               | fin                 | motif                         |
			| "2026-10-20 22:00"  | "2026-10-20 20:00"  | la fin doit suivre le début   |
			| "hier"              | "2026-10-20 20:00"  | date invalide                 |
			| "2026-10-20 20:00"  | "2026-10-20 20:00"  | la fin doit suivre le début   |

	Scénario: Sans base de données joignable, la simulation s'arrête avec le code 1
		Quand je lance Machin_lecture avec « --simulation "2026-10-20 20:00" "2026-10-20 21:00" » et une socket inexistante
		Alors il s'arrête avec le code 1, en signalant « base de données injoignable »
