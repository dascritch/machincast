# language: fr
Fonctionnalité: Analyse du prochain sonore au dernier moment
	En tant que technicien d'antenne,
	je veux que Machin lecture fasse analyser le prochain sonore qu'il va jouer, s'il n'a pas été vérifié en entier,
	afin qu'un fichier jamais décodé, ou changé depuis, soit vérifié avant de passer à l'antenne.

	https://github.com/dascritch/machincast/issues/181. Au début de chaque sonore, Machin lecture réserve le suivant.
	Si ce prochain sonore est un fichier jamais vérifié en entier (sans date de vérification complète), ou dont le
	fichier a changé depuis (date de modification ou taille), il lance « Machin indexation --audit-complet --sonore N »
	dans un processus à part, sans fenêtre, et ne l'attend pas : que l'indexeur plante ou n'ait pas fini, le sonore
	est joué à son heure. Un même sonore n'est pas redemandé avant une heure. Un stream n'est jamais analysé.

	Les scénarios remplacent Machin indexation par une commande imitée, qui note ses arguments, sauf le dernier,
	qui lance le vrai Machin indexation sur la base de test.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 19:59:50 »

	Scénario: Le prochain sonore jamais vérifié en entier est analysé pendant le sonore en cours
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et le sonore « f1 » a été vérifié en entier
		Et une commande d'analyse imitée
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Alors l'analyse est demandée bientôt pour le sonore « f2 », en audit complet
		Et l'analyse tourne dans sa propre session, à l'abri d'un Ctrl-C dans le terminal de la diffusion
		Et le log contient 1 info « analyse du prochain sonore »

	Scénario: Un sonore vérifié en entier, dont le fichier n'a pas changé, n'est pas analysé
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et le sonore « f1 » a été vérifié en entier
		Et le sonore « f2 » a été vérifié en entier
		Et une commande d'analyse imitée
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 4 pas d'une seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « f2 », « f1 », « f2 »
		Et aucune analyse n'a été demandée

	Scénario: Un sonore dont le fichier a changé depuis sa vérification est analysé
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et le sonore « f1 » a été vérifié en entier
		Et le sonore « f2 » a été vérifié en entier
		Et le fichier du sonore « f2 » a changé depuis sa vérification
		Et une commande d'analyse imitée
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Alors l'analyse est demandée bientôt pour le sonore « f2 », en audit complet

	Scénario: Un stream n'est jamais analysé
		Étant donné un serveur de flux local, avec le flux « direct » en ligne
		Et le stream « Radio » à l'adresse du flux « direct »
		Et le fil musical permanent « Continue », avec les sonores « f1 », « Radio »
		Et le sonore « f1 » a été vérifié en entier
		Et une commande d'analyse imitée
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Et la diffusion s'arrête
		Alors aucune analyse n'a été demandée

	Scénario: Un même sonore n'est pas redemandé avant une heure
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et le sonore « f1 » a été vérifié en entier
		Et une commande d'analyse imitée
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 4 pas d'une seconde
		Alors l'analyse est demandée bientôt pour le sonore « f2 », en audit complet
		Et le log contient 1 info « analyse du prochain sonore »
		Quand l'horloge du binaire passe au « 2026-10-14 21:00:00 »
		Et la diffusion tourne 2 pas d'une seconde
		Alors le log contient 2 info « analyse du prochain sonore »

	Scénario: Une analyse qui ne peut pas être lancée est consignée, et le sonore est joué quand même
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et le sonore « f1 » a été vérifié en entier
		Et une commande d'analyse introuvable
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 2 pas d'une seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « f2 »
		Et le log contient 1 alerte « analyse impossible »
		Et le log contient 0 info « analyse du prochain sonore »

	Scénario: Un indexeur qui plante ne bloque pas la lecture
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et le sonore « f1 » a été vérifié en entier
		Et une commande d'analyse qui plante
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors l'airplay montre les passages « f1 », « f2 », « f1 »
		Et chaque passage a sa ligne de fin, sans incident

	Scénario: Le vrai Machin indexation vérifie le prochain sonore en entier
		Étant donné le fil musical permanent « Continue », avec les sonores « f1 », « f2 »
		Et le sonore « f1 » a été vérifié en entier
		Et Machin indexation comme commande d'analyse, sur la base de test
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Alors le sonore « f2 » a bientôt sa date de vérification complète
