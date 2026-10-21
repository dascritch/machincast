# language: fr
Fonctionnalité: Robustesse du code, relevée au tour du code source
	En tant qu'équipe de l'antenne,
	je veux que MachinCast ne laisse ni ressource ouverte ni attente sans fin,
	afin que la diffusion et l'interface tiennent des jours sans être relancées.

	https://github.com/dascritch/machincast/issues/187. Chaque scénario couvre un risque relevé au tour du code : une
	socket ou un descripteur qui reste ouvert après une erreur, une mémoire qui grossit sans limite, une commande
	système qui peut ne jamais répondre, une réponse inattendue qui ferait planter un écran.

	# ─── Socket d'état de Machin lecture ──────────────────────

	Scénario: Une socket d'état qui ne peut pas être ouverte ne laisse aucun descripteur ouvert
		Étant donné une socket d'état dont le chemin est trop long pour le système
		Quand Machin lecture tente de l'ouvrir
		Alors l'ouverture échoue
		Et aucun descripteur de fichier n'est resté ouvert

	Scénario: Une diffusion arrêtée par une erreur ferme sa socket d'état
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et la socket d'état de la diffusion dans un répertoire temporaire
		Et le fil musical permanent « Continue », avec les sonores « f1 »
		Quand la diffusion démarre au plus vite
		Et une erreur interrompt la boucle de diffusion
		Alors l'erreur remonte jusqu'à Machin lecture
		Et la socket d'état est effacée, et plus rien n'y répond

	# ─── Client de la socket d'état, dans l'interface ─────────

	Scénario: Des octets sans fin de ligne ne font pas grossir la mémoire de l'interface
		Étant donné un serveur de socket d'état de test
		Quand l'interface s'y connecte
		Et le serveur envoie 100000 octets sans fin de ligne, puis un message complet
		Alors l'interface a ignoré les octets en trop, en le signalant
		Et elle a reçu le message complet

	# ─── Commandes système de l'interface ─────────────────────

	Plan du scénario: La date de création d'un fichier est inconnue quand stat <cas>
		Quand la fiche d'un sonore demande la date de création de son fichier, et que stat <cas>
		Alors la date de création est inconnue

		Exemples:
			| cas                       |
			| ne répond pas             |
			| ne donne pas un nombre    |
			| n'existe pas sur le poste |

	Plan du scénario: La version de MachinCast se donne sans date quand git <cas>
		Quand Aide → Version demande la date du dernier commit, et que git <cas>
		Alors la date du dernier commit est inconnue

		Exemples:
			| cas                       |
			| ne répond pas             |
			| ne donne aucune date      |
			| n'existe pas sur le poste |
