# language: fr
Fonctionnalité: Le VU-mètre et la pré-écoute de chaque entrée audio, dans les Paramètres du service
	En tant que technicien radio,
	je veux voir un VU-mètre et pré-écouter chaque entrée audio, dans les Paramètres du service,
	afin de vérifier qu'un studio envoie bien du son avant de le passer à l'antenne.

	https://github.com/dascritch/machincast/issues/624, ticket enfant de https://github.com/dascritch/machincast/issues/513.
	Sur la sortie factice, une entrée donne le signal de test du moniteur de l'antenne, et la pré-écoute joue sur la
	sortie factice. Les entrées de carte son du poste sont celles du scénario (machincast.audio.input_devices).

	Contexte:
		Étant donné les entrées de carte son du poste :
			| identifiant           | nom          |
			| alsa_input.usb-studio | Studio USB   |
			| alsa_input.pci.analog | Entrée ligne |

	Scénario: Chaque entrée a son VU-mètre, qui montre sa modulation tant que la fenêtre est ouverte
		Quand les Paramètres du service s'affichent, sur la sortie « dummy », avec l'entrée « Studio A » sur « alsa_input.usb-studio »
		Alors le VU-mètre de « Studio A » montre bientôt sa modulation
		Quand la fenêtre se ferme
		Alors le VU-mètre de « Studio A » n'écoute plus son entrée

	Scénario: Une entrée introuvable le dit à la place de son VU-mètre
		Quand les Paramètres du service s'affichent, sur la sortie « pipewire », avec l'entrée « Studio mobile » sur « alsa_input.usb-mobile »
		Alors à la place du VU-mètre de « Studio mobile », le bloc dit « Introuvable : le poste ne voit pas cette entrée audio. »

	Scénario: « Pré-écoute » écoute l'entrée choisie sur la sortie de pré-écoute, jusqu'à ce qu'on l'arrête
		Quand les Paramètres du service s'affichent, sur la sortie « dummy », avec l'entrée « Studio A » sur « alsa_input.usb-studio »
		Alors « Pré-écoute » est inactif
		Quand je choisis la ligne « Studio A »
		Et je clique sur « 🎧 Pré-écoute »
		Alors l'entrée « alsa_input.usb-studio » s'écoute sur la sortie de pré-écoute « preecoute-factice », jamais à l'antenne
		Et le bouton s'appelle « ⏹ Arrêter la pré-écoute »
		Quand je clique sur « ⏹ Arrêter la pré-écoute »
		Alors aucune entrée ne s'écoute

	Scénario: Une pré-écoute sur la sortie factice n'a rien à faire entendre
		Quand les Paramètres du service s'affichent, sur la sortie « dummy », avec l'entrée « Studio A » sur « alsa_input.usb-studio », et la pré-écoute sur la sortie factice
		Et je choisis la ligne « Studio A »
		Alors « Pré-écoute » est inactif, avec l'infobulle « La sortie de pré-écoute est la sortie factice : rien à entendre. »

	Scénario: Service installé, l'entrée s'écoute par le PipeWire du service, verrouillée sur elle
		Étant donné le PipeWire du service qui répond
		Alors la source de l'entrée « alsa_input.usb-studio » sur la sortie « pipewire » est pipewiresrc, sur ce périphérique, par le PipeWire du service
