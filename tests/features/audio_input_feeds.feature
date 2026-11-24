# language: fr
Fonctionnalité: Un feed et un stream par entrée audio, joués par Machin player
	En tant que responsable de la programmation,
	je veux que chaque entrée audio choisie devienne un feed, suivi d'un stream,
	afin de l'insérer comme source dans un événement, ou de couper l'antenne par elle, comme un stream.

	https://github.com/dascritch/machincast/issues/623, ticket enfant de https://github.com/dascritch/machincast/issues/513.
	Un feed d'entrée audio a pour adresse « input: » suivi du périphérique de l'entrée, que Machin player capte ; seuls
	les Paramètres du service donnent une telle adresse. Le service de diffusion n'est pas installé : enregistrer
	les Paramètres du service ne réserve rien (audio_inputs.feature).

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-11-24 10:00:00 »
		Et le service de diffusion non installé

	# ─── Les feeds des entrées, à l'enregistrement des Paramètres du service ───

	Scénario: Une entrée nouvelle a son feed, et un stream actif qui le suit, de son nom
		Quand la fenêtre de l'interface s'ouvre
		Et j'enregistre dans les Paramètres du service l'entrée « Studio A » sur « alsa_input.usb-studio »
		Alors le feed « Studio A » est en base, sur l'entrée « alsa_input.usb-studio »
		Et le stream « Studio A » est en base, actif, et suit le feed « Studio A »

	Scénario: Une entrée renommée renomme son feed, sans nouveau stream
		Étant donné le feed d'entrée « Studio A » sur « alsa_input.usb-studio », suivi de son stream
		Quand la fenêtre de l'interface s'ouvre
		Et j'enregistre dans les Paramètres du service l'entrée « Plateau 2 » sur « alsa_input.usb-studio »
		Alors le feed « Plateau 2 » est en base, sur l'entrée « alsa_input.usb-studio »
		Et 1 stream suit le feed « Plateau 2 »

	Scénario: Un nom déjà pris par un feed d'adresse laisse l'entrée sans feed, et la barre d'état le dit
		Étant donné les feeds « Studio A » à « https://studio.exemple/live »
		Quand la fenêtre de l'interface s'ouvre
		Et j'enregistre dans les Paramètres du service l'entrée « Studio A » sur « alsa_input.usb-studio »
		Alors aucun feed n'est sur l'entrée « alsa_input.usb-studio »
		Et la barre d'état dit, entre autres, « L'entrée audio « Studio A » n'a pas de feed : un autre feed porte déjà ce nom. »

	# ─── La fiche et la liste des feeds ────────────────────────

	Scénario: La fiche d'un feed d'entrée montre son périphérique, sans adresse, ni mémoire tampon, ni test
		Étant donné le feed d'entrée « Studio A » sur « alsa_input.usb-studio », suivi de son stream
		Quand la fenêtre de l'interface s'ouvre
		Et les Paramètres du service ont l'entrée « Studio A » sur « alsa_input.usb-studio »
		Et j'ouvre l'onglet « Feeds »
		Alors la liste montre :
			| Nom      | Adresse                     | Streams |
			| Studio A | input:alsa_input.usb-studio | 1       |
		Quand j'ouvre la ligne « Studio A »
		Alors la fiche du feed d'entrée montre « Entrée audio : » « alsa_input.usb-studio », sans mémoire tampon ni test
		Et son nom ne se change pas dans la fiche
		Et la fiche n'avertit pas en haut

	Scénario: La fiche d'un feed d'adresse refuse une adresse d'entrée audio
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Feeds »
		Et je clique sur « Nouveau feed »
		Et je saisis le nom du feed « Studio pirate »
		Et je saisis l'adresse du feed « input:alsa_input.usb-studio »
		Et j'enregistre la fiche
		Alors la fiche signale « Une adresse commençant par « input: » est réservée aux entrées audio des paramètres du service. »
		Et aucun feed n'est sur l'entrée « alsa_input.usb-studio »

	Scénario: Une entrée retirée des Paramètres du service garde son feed, que sa fiche signale
		Étant donné le feed d'entrée « Studio A » sur « alsa_input.usb-studio », suivi de son stream
		Quand la fenêtre de l'interface s'ouvre
		Et j'enregistre dans les Paramètres du service l'entrée « Ligne » sur « alsa_input.pci.analog »
		Alors le feed « Studio A » est en base, sur l'entrée « alsa_input.usb-studio »
		Quand j'ouvre l'onglet « Feeds »
		Et j'ouvre la ligne « Studio A »
		Alors la fiche avertit en haut « Entrée audio retirée des paramètres du service : ses streams ne jouent plus rien. »

	# ─── Machin player ─────────────────────────────────────────

	Scénario: Le stream d'un feed d'entrée se joue à l'adresse de l'entrée, sans mémoire tampon
		Étant donné le feed d'entrée « Studio A » sur « alsa_input.usb-studio », suivi de son stream
		Alors Machin player joue le stream « Studio A » à l'adresse « input:alsa_input.usb-studio », sans mémoire tampon

	Scénario: Sur la sortie factice, une entrée se capte comme un son de test, jusqu'à la coupure
		Étant donné un moteur audio sur la sortie factice, en temps réel
		Quand il joue l'adresse « input:alsa_input.usb-studio »
		Et 500 millisecondes s'écoulent
		Alors la voie capte « audiotestsrc », et sa position avance
		Quand il coupe net
		Alors la voie est coupée

	Scénario: Une entrée que le poste ne voit pas met la voie en erreur dès son démarrage
		Étant donné un moteur audio sur la sortie factice, en temps réel, qui ne voit aucune entrée
		Quand il joue l'adresse « input:alsa_input.usb-mobile »
		Alors la voie est en erreur « entrée audio alsa_input.usb-mobile introuvable »

	Plan du scénario: L'entrée se capte par la source de la sortie audio, réglée sur son périphérique
		Alors la capture de « alsa_input.usb-studio » sur la sortie « <sortie> » est un élément « <élément> », dont « <propriété> » vaut « alsa_input.usb-studio »

		Exemples:
			| sortie     | élément     | propriété     |
			| pipewire   | pipewiresrc | target-object |
			| pulseaudio | pulsesrc    | device        |

	Scénario: Sous PipeWire, la capture est verrouillée sur son entrée, et se présente comme une entrée audio
		Alors la capture de « alsa_input.usb-studio » sur la sortie « pipewire » ne se replie jamais sur une autre entrée
		Et elle se présente comme le flux « Entrée audio » de « MachinCast lecteur »

	Scénario: La simulation joue une entrée comme un stream, sans fin connue
		Quand la simulation joue l'adresse « input:alsa_input.usb-studio »
		Alors sa voie joue, sans fin prévue
