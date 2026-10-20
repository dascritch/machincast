# language: fr
Fonctionnalité: Masquage des métadonnées et modules de sortie
	En tant que programmateur de l'antenne,
	je veux que l'artiste et le titre soient masqués sur les sorties publiques selon la priorité Événement > Séquence > Banque > Sonore > configuration,
	afin que certaines diffusions restent anonymes pour le public.

	https://github.com/dascritch/machincast/issues/19, spec § 4.8 et § 5.3 ; niveau de la séquence :
	https://github.com/dascritch/machincast/issues/99. Les sorties privées (journal, CSV, .pls)
	disent tout ; la sortie publique (HTML) applique le masquage. Les fichiers de sortie sont écrits dans un
	répertoire temporaire, à la place des chemins de la configuration.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et des sorties dans un répertoire temporaire, avec le texte public « Radio Exemple »

	# ─── Masquage ──────────────────────────────────────────────

	Plan du scénario: Le masquage retenu est celui du premier niveau renseigné : événement, séquence, banque, sonore, configuration
		Étant donné le masquage <evenement> pour l'événement, <sequence> pour la séquence, <banque> pour la banque, <sonore> pour le sonore et <configuration> dans la configuration
		Alors l'artiste et le titre sont <verdict> sur la sortie publique

		Exemples:
			| evenement | sequence | banque | sonore | configuration | verdict  |
			| vide      | vide     | vide   | vide   | non           | affichés |
			| vide      | vide     | vide   | vide   | oui           | masqués  |
			| vide      | vide     | vide   | oui    | non           | masqués  |
			| vide      | vide     | vide   | non    | oui           | affichés |
			| vide      | vide     | non    | oui    | oui           | affichés |
			| vide      | vide     | oui    | non    | non           | masqués  |
			| vide      | oui      | non    | non    | non           | masqués  |
			| vide      | non      | oui    | oui    | oui           | affichés |
			| oui       | non      | non    | non    | non           | masqués  |
			| non       | oui      | oui    | oui    | oui           | affichés |

	Plan du scénario: Masqués, l'artiste et le titre laissent la place au premier nom public renseigné : événement, séquence, banque
		Étant donné un passage masqué, de nom public <evenement> pour l'événement, <sequence> pour la séquence et <banque> pour la banque
		Quand les sorties sont mises à jour
		Alors la page publique montre « <texte> » comme sonore à l'antenne

		Exemples:
			| evenement  | sequence     | banque       | texte                    |
			| « Nuit »   | « Pub »      | « Jingles »  | Nuit                     |
			| vide       | « Pub »      | « Jingles »  | Pub                      |
			| vide       | vide         | « Jingles »  | Jingles                  |
			| vide       | vide         | vide         | Radio Exemple            |

	Scénario: Masqués, l'artiste et le titre laissent la place au nom public de l'événement
		Étant donné le passage de « Les Gaufres » – « Café à minuit » dans l'émission « Nuit », de nom public « La nuit des auditeurs », masquée
		Quand les sorties sont mises à jour
		Alors la page publique montre « La nuit des auditeurs »
		Et la page publique ne montre ni « Les Gaufres » ni « Café à minuit »

	Scénario: Sans nom public de l'événement, ils laissent la place au texte public de la configuration
		Étant donné le passage de « Les Gaufres » – « Café à minuit » dans l'émission « Nuit », sans nom public, masquée
		Quand les sorties sont mises à jour
		Alors la page publique montre « Radio Exemple »
		Et la page publique ne montre ni « Les Gaufres » ni « Café à minuit »

	# ─── Page publique (HTML) ──────────────────────────────────

	Scénario: La page publique montre le sonore à l'antenne, puis les 20 précédents
		Étant donné 25 passages terminés, puis un passage en cours de « Artiste en cours » – « Titre en cours »
		Quand les sorties sont mises à jour
		Alors la page publique montre « Titre en cours » comme sonore à l'antenne
		Et la page publique liste 20 passages précédents, du plus récent au plus ancien
		Et la page publique se rafraîchit toutes les 30 secondes

	Scénario: Entre deux sonores, la page publique montre le texte public, puis les 20 derniers passages
		Étant donné 25 passages terminés, sans passage en cours
		Quand les sorties sont mises à jour
		Alors la page publique montre « Radio Exemple » comme sonore à l'antenne
		Et la page publique liste 20 passages précédents, du plus récent au plus ancien

	Scénario: La page publique ne montre jamais l'emplacement d'un fichier, et échappe le texte
		Étant donné un passage terminé de « <Groupe> & Cie » – « Titre »
		Et le passage de « <Groupe> & Cie » – « Titre » dans l'émission « Nuit », sans nom public, affichée
		Quand les sorties sont mises à jour
		Alors la page publique montre 2 fois « &lt;Groupe&gt; &amp; Cie »
		Et la page publique ne montre pas « <Groupe> »
		Et la page publique ne montre pas l'emplacement du fichier

	# ─── Sorties privées ───────────────────────────────────────

	Scénario: La playlist .pls liste les 100 derniers fichiers joués, du plus ancien au plus récent, sans masquage
		Étant donné 105 passages terminés, masqués
		Quand les sorties sont mises à jour
		Alors la playlist compte 100 entrées, du passage 6 au passage 105
		Et chaque entrée de la playlist donne l'artiste et le titre

	Scénario: Le CSV du jour reçoit une ligne par passage terminé, sans masquage
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et le masquage de tous les sonores
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors le CSV « airplay-2026-10-14.csv » commence par l'en-tête et le BOM
		Et le CSV « airplay-2026-10-14.csv » a les lignes :
			| debut               | fin                 | duree    | titre | evenement | sans_incident |
			| 2026-10-14 19:59:50 | 2026-10-14 19:59:51 | 00:00:01 | f1    | Continue  | oui           |
			| 2026-10-14 19:59:51 | 2026-10-14 19:59:52 | 00:00:01 | f2    | Continue  | oui           |
			| 2026-10-14 19:59:52 | 2026-10-14 19:59:53 | 00:00:01 | f1    | Continue  | oui           |

	Scénario: Chaque jour a son CSV, nommé par sa date
		Étant donné l'horloge du binaire au « 2026-10-14 23:59:58 »
		Et le fil musical permanent « Continue », avec les sonores « f1 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors le CSV « airplay-2026-10-14.csv » a 2 lignes de passage
		Et le CSV « airplay-2026-10-15.csv » a 1 ligne de passage

	Scénario: Le journal du binaire annonce le début et la fin des événements et des séquences
		https://github.com/dascritch/machincast/issues/153

		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et la séquence « Pub » des sonores « s1 », « s2 », jouée par le fil musical permanent « Continue », avant le sonore « f3 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Et la diffusion s'arrête
		Alors le journal du binaire a annoncé « début d'événement : « Continue », fil musical, permanent », en information
		Et le journal du binaire a annoncé « début de séquence : « Pub », dans « Continue » », en information
		Et le journal du binaire a annoncé « fin de séquence : « Pub », dans « Continue » », en information
		Et le journal du binaire a annoncé « fin d'événement : « Continue » », en information

	Scénario: Le journal du binaire annonce chaque passage avec l'artiste et le titre, même masqués
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le fil musical permanent « Continue », avec les sonores « f1 »
		Et le masquage de tous les sonores
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Et la diffusion s'arrête
		Alors le journal du binaire a annoncé « f1 », en information

	Scénario: Les alertes et les incidents du log vont aussi sur la sortie d'erreur du binaire
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le fil musical permanent « Continue », avec les sonores « disparu », « f1 »
		Et le fichier du sonore « disparu » a été supprimé
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Et la diffusion s'arrête
		Alors le journal du binaire a signalé « fichier introuvable », en anomalie

	Scénario: Une sortie inaccessible est signalée une fois, sans arrêter la diffusion
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le fil musical permanent « Continue », avec les sonores « f1 »
		Et la page publique ne peut pas être écrite
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « f1 », « f1 »
		Et le log contient 1 alerte « sortie inaccessible »

	Scénario: Machin lecture écrit ses sorties aux chemins de la configuration
		Alors les sorties de Machin lecture sont celles de la configuration de test
