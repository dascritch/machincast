# language: fr
Fonctionnalité: Choix des cartes son de l'antenne et de la pré-écoute
	En tant que technicien radio,
	je veux choisir et tester les cartes son de l'antenne et de la pré-écoute, dès le premier lancement,
	afin d'aller à l'essentiel pour la suite.

	https://github.com/dascritch/machincast/issues/339 : un même bloc « Cartes son » (machincast.interface.sound_cards)
	sert à la page « Audio » des préférences et à la fenêtre « Pour bien démarrer ». Il choisit le type de sortie
	(audio.output), puis la carte son de l'antenne (audio.device) et celle de la pré-écoute (audio.preview),
	parmi les périphériques du poste et l'entrée « Sortie factice » (configuration.DUMMY). La carte choisie pour l'une
	est grisée dans l'autre. L'antenne ne prend la sortie factice que sans service de diffusion installé : c'est une
	installation provisoire. Service en marche, la carte de l'antenne ne se choisit ni ne se teste. « Tester » joue
	2 secondes de sinusoïde à 1000 Hz, à -3 dB, sur la carte choisie ; les scénarios remplacent sa sortie par une sortie
	factice, et raccourcissent le son.

	Contexte:
		Étant donné les périphériques audio du poste :
			| identifiant | nom        |
			| carte-1     | Carte 1    |
			| casque-usb  | Casque USB |

	# ─── Choix ─────────────────────────────────────────────────

	Scénario: Le bloc propose le type de sortie, puis pour chaque carte les périphériques du poste et la sortie factice
		Quand le bloc des cartes son s'ouvre sur la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « casque-usb », sans service de diffusion
		Alors son type de sortie est « PipeWire », parmi « PipeWire », « PulseAudio », « ALSA »
		Et son choix de l'antenne propose :
			| carte          | état     |
			| Carte 1        | active   |
			| Casque USB     | inactive |
			| Sortie factice | active   |
		Et son choix de la pré-écoute propose :
			| carte          | état     |
			| Casque USB     | active   |
			| Carte 1        | inactive |
			| Sortie factice | active   |
		Et il donne la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « casque-usb »

	Scénario: La sortie factice choisie pour l'antenne est grisée pour la pré-écoute, et inversement
		Quand le bloc des cartes son s'ouvre sur la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « casque-usb », sans service de diffusion
		Et j'y choisis pour l'antenne « Sortie factice »
		Alors son choix de la pré-écoute propose :
			| carte          | état     |
			| Casque USB     | active   |
			| Carte 1        | active   |
			| Sortie factice | inactive |
		Et il donne la sortie « pipewire », l'antenne « dummy » et la pré-écoute « casque-usb »
		Quand j'y choisis pour la pré-écoute « Carte 1 »
		Alors son choix de l'antenne propose :
			| carte          | état     |
			| Carte 1        | inactive |
			| Casque USB     | active   |
			| Sortie factice | active   |

	Scénario: Une configuration sur la sortie factice se montre sur l'entrée « Sortie factice »
		Quand le bloc des cartes son s'ouvre sur la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « dummy », sans service de diffusion
		Alors son choix de la pré-écoute propose :
			| carte          | état     |
			| Sortie factice | active   |
			| Carte 1        | inactive |
			| Casque USB     | active   |
		Et il donne la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « dummy »

	Scénario: Le type de sortie factice des essais n'est proposé que s'il est déjà configuré
		Quand le bloc des cartes son s'ouvre sur la sortie « dummy », l'antenne non renseignée et la pré-écoute « casque-usb », sans service de diffusion
		Alors son type de sortie est « Factice, aucun son », parmi « PipeWire », « PulseAudio », « ALSA », « Factice, aucun son »

	Scénario: Changer de type de sortie relit les cartes du poste ; l'antenne reste à renseigner, la pré-écoute garde la sienne si elle y est
		Quand le bloc des cartes son s'ouvre sur la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « casque-usb », sans service de diffusion
		Et j'y choisis le type de sortie « PulseAudio »
		Alors son choix de l'antenne propose :
			| carte          | état     |
			| (à renseigner) | active   |
			| Carte 1        | active   |
			| Casque USB     | inactive |
			| Sortie factice | active   |
		Et il donne la sortie « pulseaudio », l'antenne non renseignée et la pré-écoute « casque-usb »

	Scénario: L'antenne sur la sortie factice y reste quand le type de sortie change
		Quand le bloc des cartes son s'ouvre sur la sortie « pipewire », l'antenne « dummy » et la pré-écoute « casque-usb », sans service de diffusion
		Et j'y choisis le type de sortie « ALSA »
		Alors il donne la sortie « alsa », l'antenne « dummy » et la pré-écoute « casque-usb »

	# ─── Service de diffusion ──────────────────────────────────

	Scénario: Service de diffusion installé, l'antenne ne prend plus la sortie factice ; la pré-écoute, si
		Quand le bloc des cartes son s'ouvre sur la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « casque-usb », service de diffusion à l'arrêt
		Alors son choix de l'antenne propose :
			| carte          | état     |
			| Carte 1        | active   |
			| Casque USB     | inactive |
			| Sortie factice | inactive |
		Et dans son choix de l'antenne, « Sortie factice » a pour infobulle « Seulement sans service de diffusion installé : l'antenne d'un poste dédié joue toujours sur une carte son. »
		Et son choix de la pré-écoute propose :
			| carte          | état     |
			| Casque USB     | active   |
			| Carte 1        | inactive |
			| Sortie factice | active   |
		Et le choix de l'antenne, son bouton « Tester » et le type de sortie sont actifs

	Scénario: Service de diffusion en marche, la carte de l'antenne ne se choisit ni ne se teste
		Quand le bloc des cartes son s'ouvre sur la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « casque-usb », service de diffusion en marche
		Alors le choix de l'antenne, son bouton « Tester » et le type de sortie sont inactifs, avec l'infobulle « Arrêter la diffusion pour choisir la carte son de l'antenne. »
		Et le choix de la pré-écoute et son bouton « Tester » sont actifs

	# ─── Tester ────────────────────────────────────────────────

	Scénario: Le son de test est une sinusoïde à 1000 Hz, à -3 dB, de 2 secondes
		Quand je construis le son de test de la sortie « pipewire », carte « carte-1 »
		Alors c'est une sinusoïde à 1000 Hz, à -3 dB, de 2 secondes
		Et il joue sur l'élément « pipewiresink », carte « carte-1 », présenté comme « MachinCast interface », flux « Son de test »

	Scénario: « Tester » joue le son de test sur la carte choisie, et le dit
		Étant donné des sons de test de 0,2 seconde, sur une sortie factice
		Quand le bloc des cartes son s'ouvre sur la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « casque-usb », sans service de diffusion
		Et je clique sur « Tester » de l'antenne
		Alors le bloc dit « Son de test sur « Carte 1 »… »
		Et ses boutons « Tester » sont inactifs
		Et le son de test a été demandé sur la sortie « pipewire », carte « carte-1 »
		Et le bloc dit bientôt « Son de test joué sur « Carte 1 ». »
		Et ses boutons « Tester » sont actifs
		Quand je clique sur « Tester » de la pré-écoute
		Alors le son de test a été demandé sur la sortie « pipewire », carte « casque-usb »
		Et le bloc dit bientôt « Son de test joué sur « Casque USB ». »

	Scénario: Un son de test impossible le dit
		Étant donné des sons de test sur une sortie qui ne peut pas être créée
		Quand le bloc des cartes son s'ouvre sur la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « casque-usb », sans service de diffusion
		Et je clique sur « Tester » de l'antenne
		Alors le bloc dit bientôt « Son de test impossible sur « Carte 1 » : sortie introuvable »
		Et ses boutons « Tester » sont actifs

	Plan du scénario: « Tester » ne sert qu'à une vraie carte
		Quand le bloc des cartes son s'ouvre sur la sortie « pipewire », l'antenne <antenne> et la pré-écoute « casque-usb », sans service de diffusion
		Alors le bouton « Tester » de l'antenne est inactif, avec l'infobulle « <infobulle> »

		Exemples:
			| antenne        | infobulle                            |
			| non renseignée | Choisir d'abord une carte son.       |
			| « dummy »    | La sortie factice ne joue aucun son. |
