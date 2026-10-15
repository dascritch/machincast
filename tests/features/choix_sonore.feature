# language: fr
Fonctionnalité: Choix d'un sonore dans une banque
	En tant que programmateur de l'antenne,
	je veux qu'une banque fournisse un sonore selon son mode, séquentiel ou aléatoire contrôlé,
	afin que l'antenne ne répète pas les mêmes titres.

	https://github.com/dascritch/machincast/issues/13 — spec § 4.4 et § 4.5. Le choix ne garde aucun état en
	mémoire : il se déduit de l'airplay, où chaque passage note la banque qui l'a fourni. Un sonore choisi est
	ici « joué » en ajoutant sa ligne de début à l'airplay. Les choix passent par les droits du binaire lecture.

	Contexte:
		Étant donné l'heure « 2026-10-15 12:00 »

	# ─── Séquentiel ────────────────────────────────────────────

	Scénario: Une banque séquentielle donne ses sonores dans l'ordre, puis reprend au début
		Étant donné une banque séquentielle « Jingles » contenant « a », « b », « c »
		Quand je joue 5 sonores de la banque « Jingles »
		Alors les sonores joués sont « a », « b », « c », « a », « b »

	Scénario: Une banque séquentielle reprend après le dernier sonore joué par elle
		Étant donné une banque séquentielle « Jingles » contenant « a », « b », « c »
		Et « b » a été joué via la banque « Jingles »
		Quand je joue 2 sonores de la banque « Jingles »
		Alors les sonores joués sont « c », « a »

	Scénario: Les passages via une autre banque ne comptent pas dans l'ordre séquentiel
		Étant donné une banque séquentielle « Jingles » contenant « a », « b », « c »
		Et une banque séquentielle « Habillage » contenant « c », « b »
		Et « a » a été joué via la banque « Jingles »
		Et « b » a été joué via la banque « Habillage »
		Et « b » a été joué sans banque
		Quand je joue 1 sonore de la banque « Jingles »
		Alors les sonores joués sont « b »

	Scénario: Une banque séquentielle saute les sonores qui ne sont pas jouables
		Étant donné une banque séquentielle « Jingles » contenant « a », « b », « c »
		Et le sonore « b » est à l'état « desactive »
		Quand je joue 3 sonores de la banque « Jingles »
		Alors les sonores joués sont « a », « c », « a »

	# ─── Aléatoire contrôlé ────────────────────────────────────

	Scénario: Une banque aléatoire ne répète aucun sonore avant de les avoir tous joués
		Étant donné une banque aléatoire « Titres » contenant « a », « b », « c », « d », « e »
		Et le hasard créé avec la graine 7
		Quand je joue 15 sonores de la banque « Titres »
		Alors chaque tranche de 5 sonores joués contient « a », « b », « c », « d », « e », une fois chacun

	Scénario: Le tirage aléatoire est reproductible avec une même graine
		Étant donné une banque aléatoire « Titres » contenant « a », « b », « c », « d », « e »
		Alors deux tirages de 10 sonores avec la graine 7 donnent la même suite
		Et des tirages de 10 sonores avec les graines 1 à 10 ne donnent pas tous la même suite

	Scénario: Le cycle reprend là où l'airplay l'a laissé
		Étant donné une banque aléatoire « Titres » contenant « a », « b », « c », « d »
		Et « c » a été joué via la banque « Titres »
		Et « a » a été joué via la banque « Titres »
		Alors les sonores qui restent à jouer dans le cycle de « Titres » sont « b », « d »

	Scénario: Un cycle terminé repart avec tous les sonores, sauf le dernier joué
		Étant donné une banque aléatoire « Titres » contenant « a », « b », « c »
		Et « a » a été joué via la banque « Titres »
		Et « c » a été joué via la banque « Titres »
		Et « b » a été joué via la banque « Titres »
		Alors les sonores qui restent à jouer dans le cycle de « Titres » sont « a », « c »

	Scénario: Le cycle est propre à chaque banque, même pour un sonore de plusieurs banques
		Étant donné une banque aléatoire « Titres » contenant « a », « b », « c »
		Et une banque aléatoire « Nouveautés » contenant « a », « d »
		Et « a » a été joué via la banque « Nouveautés »
		Et « b » a été joué via la banque « Titres »
		Alors les sonores qui restent à jouer dans le cycle de « Titres » sont « a », « c »

	Scénario: Un sonore ajouté à une banque aléatoire entre dans le cycle en cours
		Étant donné une banque aléatoire « Titres » contenant « a », « b »
		Et « a » a été joué via la banque « Titres »
		Et le sonore « z » ajouté à la banque « Titres »
		Alors les sonores qui restent à jouer dans le cycle de « Titres » sont « b », « z »

	# ─── Sonores jouables ──────────────────────────────────────

	Plan du scénario: Un sonore qui n'est pas jouable n'est jamais choisi
		Étant donné une banque <mode> « Jingles » contenant « a », « b »
		Et le hasard créé avec la graine 3
		Et le sonore « a » <condition>
		Quand je joue 4 sonores de la banque « Jingles »
		Alors les sonores joués sont « b », « b », « b », « b »

		Exemples:
			| mode        | condition                                         |
			| séquentielle | est à l'état « apercu »                          |
			| séquentielle | est à l'état « expire »                          |
			| séquentielle | est à l'état « errone »                          |
			| séquentielle | est à l'état « supprime »                        |
			| aléatoire   | est à l'état « desactive »                        |
			| séquentielle | n'est diffusable qu'à partir du « 2026-10-16 00:00 » |
			| aléatoire   | n'est plus diffusable depuis le « 2026-10-15 12:00 » |
			| séquentielle | a atteint son maximum de 2 lectures              |
			| aléatoire   | a atteint son maximum de 2 lectures               |

	Scénario: Un sonore sous son maximum de lectures reste jouable
		Étant donné une banque séquentielle « Jingles » contenant « a », « b »
		Et le sonore « a » a été lu 1 fois sur un maximum de 2 lectures
		Quand je joue 1 sonore de la banque « Jingles »
		Alors les sonores joués sont « a »

	Scénario: Un sonore dans sa période de diffusion est jouable
		Étant donné une banque séquentielle « Jingles » contenant « a »
		Et le sonore « a » est diffusable du « 2026-10-15 00:00 » au « 2026-10-16 00:00 »
		Quand je joue 1 sonore de la banque « Jingles »
		Alors les sonores joués sont « a »

	Plan du scénario: Une banque sans sonore jouable est traitée comme vide
		Étant donné une banque <mode> « Jingles » contenant « a », « b »
		Et le sonore « a » est à l'état « desactive »
		Et le sonore « b » est à l'état « errone »
		Alors la banque « Jingles » ne fournit aucun sonore

		Exemples:
			| mode         |
			| séquentielle |
			| aléatoire    |

	Scénario: Une banque sans sonore ne fournit rien
		Étant donné une banque séquentielle « Vide » contenant aucun sonore
		Alors la banque « Vide » ne fournit aucun sonore
