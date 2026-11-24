# language: fr
Fonctionnalité: Les entrées audio, choisies et nommées dans les Paramètres du service, réservées au service
	En tant que technicien radio,
	je veux choisir et nommer les entrées de carte son que MachinCast peut passer à l'antenne,
	afin qu'elles soient réservées au service de diffusion, comme sa sortie d'antenne.

	https://github.com/dascritch/machincast/issues/622, ticket enfant de https://github.com/dascritch/machincast/issues/513.
	Les entrées vivent dans audio.inputs de la configuration du service. Le service installé, des entrées changées se
	réservent aussitôt : pkexec lance python -m machincast.input_reservation, qui réécrit le fragment WirePlumber des
	sessions du poste et relance le WirePlumber du service ; puis l'interface relance celui de sa session. Les
	scénarios de la commande travaillent dans une racine à part (--root) ; pkexec et systemctl y sont des scripts, en
	tête du PATH, qui notent leurs arguments ; pkexec lance ensuite la commande, sans autre droit.

	Contexte:
		Étant donné les entrées de carte son du poste :
			| identifiant                 | nom              |
			| alsa_input.usb-studio       | Studio USB       |
			| alsa_input.pci.analog       | Entrée ligne     |
			| preecoute-factice           | Micro du casque  |

	# ─── La commande ───────────────────────────────────────────

	Scénario: La commande réserve les entrées : elle réécrit le fragment des sessions, puis relance le WirePlumber du service
		Étant donné une configuration du service sur la sortie « pipewire », avec les entrées « Studio A » sur « alsa_input.usb-studio » et « Ligne » sur « alsa_input.pci.analog »
		Quand je lance « python -m machincast.input_reservation » avec cette configuration, dans la racine du scénario
		Alors la commande se termine avec le code 0
		Et le fragment « /etc/wireplumber/wireplumber.conf.d/50-machincast.conf » désactive les nœuds « alsa_input.usb-studio » « alsa_input.pci.analog »
		Et systemctl a été lancé avec « restart machincast-wireplumber.service »
		Et la commande a dit « entrées audio réservées au service de diffusion : Studio A, Ligne »

	Scénario: Sans entrée, la commande ne cache plus que la carte de l'antenne
		Étant donné une configuration du service sur la sortie « pipewire », sans entrée
		Quand je lance « python -m machincast.input_reservation » avec cette configuration, dans la racine du scénario
		Alors la commande se termine avec le code 0
		Et le fragment « /etc/wireplumber/wireplumber.conf.d/50-machincast.conf » désactive seulement la carte de l'antenne
		Et la commande a dit « aucune entrée audio réservée au service de diffusion »

	Scénario: Un WirePlumber du service qui ne redémarre pas est signalé
		Étant donné une configuration du service sur la sortie « pipewire », avec les entrées « Studio A » sur « alsa_input.usb-studio »
		Et systemctl qui échoue
		Quand je lance « python -m machincast.input_reservation » avec cette configuration, dans la racine du scénario
		Alors la commande se termine avec le code 1
		Et la commande a dit un message qui commence par « entrées audio non réservées : »

	Scénario: Une configuration invalide n'écrit rien
		Étant donné une configuration du service dont deux entrées s'appellent « Studio »
		Quand je lance « python -m machincast.input_reservation » avec cette configuration, dans la racine du scénario
		Alors la commande se termine avec le code 2
		Et le fragment « /etc/wireplumber/wireplumber.conf.d/50-machincast.conf » n'existe pas
		Et systemctl n'a pas été lancé

	# ─── La page « Audio » des Paramètres du service ───────────

	Scénario: Les Paramètres du service montrent les entrées audio ; les préférences de l'interface, non
		Quand la fenêtre des paramètres du service s'ouvre, avec l'entrée « Studio A » sur « alsa_input.usb-studio »
		Alors sa page « Audio » a le bloc « Entrées audio », avec :
			| nom      | entrée     |
			| Studio A | Studio USB |
		Et il propose d'ajouter « Entrée ligne »
		Quand la fenêtre des préférences de l'interface s'ouvre
		Alors sa page « Audio » n'a pas de bloc « Entrées audio »

	Scénario: Ajouter une entrée, la nommer : les paramètres la donnent, sans les espaces de son nom
		Quand la fenêtre des paramètres du service s'ouvre, sans entrée
		Et j'y ajoute l'entrée « Entrée ligne »
		Et je nomme « Plateau 2 » la ligne « Entrée ligne »
		Alors il propose d'ajouter « Studio USB »
		Et les paramètres donnent les entrées « Plateau 2 » sur « alsa_input.pci.analog »
		Et « OK » est actif
		Quand j'y ajoute l'entrée « Studio USB »
		Alors il ne propose plus rien à ajouter

	Plan du scénario: Un nom vide, ou pris deux fois, empêche d'enregistrer, et le bloc dit pourquoi
		Quand la fenêtre des paramètres du service s'ouvre, avec l'entrée « Studio A » sur « alsa_input.usb-studio »
		Et j'y ajoute l'entrée « Entrée ligne »
		Et je nomme « <nom> » la ligne « Entrée ligne »
		Alors « OK » est inactif
		Et le bloc des entrées dit « <message> »

		Exemples:
			| nom      | message                                    |
			|          | Chaque entrée audio demande un nom.        |
			| Studio A | Deux entrées audio s'appellent « Studio A ». |

	Scénario: Retirer une entrée la rend aux entrées à ajouter
		Quand la fenêtre des paramètres du service s'ouvre, avec l'entrée « Studio A » sur « alsa_input.usb-studio »
		Et j'y retire la ligne « Studio USB »
		Alors les paramètres ne donnent aucune entrée
		Et il propose d'ajouter « Studio USB », « Entrée ligne »

	Scénario: Une entrée de la configuration que le poste ne voit plus reste, introuvable
		Quand la fenêtre des paramètres du service s'ouvre, avec l'entrée « Studio mobile » sur « alsa_input.usb-mobile »
		Alors sa page « Audio » a le bloc « Entrées audio », avec :
			| nom           | entrée                                |
			| Studio mobile | alsa_input.usb-mobile (introuvable)   |

	Scénario: Les entrées s'écrivent dans audio.inputs ; sans entrée, la clé disparaît
		Étant donné le fichier de configuration de l'interface
		Quand les préférences écrivent les entrées « Studio A » sur « alsa_input.usb-studio » et « Ligne » sur « alsa_input.pci.analog »
		Alors la configuration relue a les entrées « Studio A » sur « alsa_input.usb-studio », « Ligne » sur « alsa_input.pci.analog »
		Quand les préférences écrivent aucune entrée
		Alors le fichier de configuration n'a plus de clé « inputs »

	# ─── La réservation, depuis l'interface ────────────────────

	Scénario: Service installé, des entrées changées se réservent aussitôt, puis le WirePlumber de la session redémarre
		Étant donné pkexec et systemctl imités
		Quand l'interface réserve les entrées de sa configuration
		Alors pkexec a lancé « python -m machincast.input_reservation --config » avec la configuration, dans la racine du scénario
		Et systemctl a été lancé avec « restart machincast-wireplumber.service », puis « --user restart wireplumber.service »
		Et la réservation a dit « Entrées audio réservées au service de diffusion. »

	Scénario: Une authentification refusée ne réserve rien
		Étant donné pkexec et systemctl imités
		Et pkexec qui refuse l'authentification
		Quand l'interface réserve les entrées de sa configuration
		Alors systemctl n'a pas été lancé
		Et la réservation a dit « Entrées audio non réservées : authentification refusée. »

	Plan du scénario: Enregistrer des entrées changées les réserve avec le service installé, jamais sans
		Étant donné l'horloge de l'interface au « 2026-11-24 10:00:00 »
		Et le service de diffusion <installé>
		Quand la fenêtre de l'interface s'ouvre
		Et j'enregistre dans les Paramètres du service l'entrée « Studio A » sur « alsa_input.usb-studio »
		Alors la configuration de l'interface a les entrées « Studio A » sur « alsa_input.usb-studio »
		Et la réservation des entrées a été demandée <fois>

		Exemples:
			| installé       | fois     |
			| installé       | 1 fois   |
			| non installé   | 0 fois   |
