# language: fr
Fonctionnalité: Périphériques de sortie du poste
	En tant que technicien d'antenne,
	je veux choisir les périphériques de l'antenne et de la pré-écoute parmi ceux du poste,
	afin de ne pas avoir à recopier leur nom à la main.

	https://github.com/dascritch/machincast/issues/116. machincast.audio.devices demande à GStreamer les
	périphériques de sortie audio du poste, comme gst-device-monitor-1.0 Audio/Sink, et ne garde que ceux de la sortie
	configurée : nœuds PipeWire, périphériques PulseAudio ou ALSA. L'identifiant est celui qu'écrivent
	audio.device et audio.preview : le nom du nœud PipeWire (node.name), sinon le nom interne du périphérique.
	« python -m machincast.installation devices » les liste ; sans aucun, il dit tout ce que voit GStreamer.
	Les scénarios remplacent les périphériques que voit GStreamer ; « (vide) » est un nom interne vide.

	Contexte:
		Étant donné les périphériques vus par GStreamer :
			| type              | nom            | node.name                     | internal-name          |
			| GstPipeWireDevice | Haut-parleurs  | alsa_output.pci.analog-stereo |                        |
			| GstPipeWireDevice | Casque USB     | alsa_output.usb-casque        |                        |
			| GstPipeWireDevice | Sans nom       |                               |                        |
			| GstPulseDevice    | Casque (Pulse) |                               | alsa_output.usb-casque |
			| GstAlsaDevice     | HDA Intel      |                               | hw:0                   |
			| GstAlsaDevice     | Nom interne vide |                             | (vide)                 |

	Plan du scénario: Seuls les périphériques de la sortie configurée sont proposés
		Alors les périphériques de la sortie « <sortie> » sont <liste>

		Exemples:
			| sortie     | liste                                                                                 |
			| pipewire   | « alsa_output.pci.analog-stereo » « Haut-parleurs », « alsa_output.usb-casque » « Casque USB » |
			| pulseaudio | « alsa_output.usb-casque » « Casque (Pulse) »                                          |
			| alsa       | « hw:0 » « HDA Intel »                                                                 |
			| dummy      | aucun                                                                                  |

	Scénario: La liste des périphériques dit le rôle de chacun dans la configuration
		Étant donné une configuration sur la sortie « pipewire », avec l'antenne « alsa_output.pci.analog-stereo » et la pré-écoute « alsa_output.usb-casque »
		Quand je liste les périphériques de la configuration
		Alors la liste est :
			"""
			alsa_output.pci.analog-stereo	Haut-parleurs	antenne
			alsa_output.usb-casque	Casque USB	pré-écoute
			"""

	Scénario: Sans périphérique de la sortie configurée, la liste dit tout ce que voit GStreamer
		Étant donné les périphériques vus par GStreamer :
			| type           | nom     | node.name | internal-name |
			| GstPulseDevice | Casque  |           | casque        |
			| GstAlsaDevice  | Inconnu |           |               |
		Et une configuration sur la sortie « pipewire », avec l'antenne « a » et la pré-écoute « b »
		Quand je liste les périphériques de la configuration
		Alors la liste est :
			"""
			aucun périphérique de sortie « pipewire » ; périphériques de sortie vus par GStreamer :
			GstPulseDevice	Casque	casque
			GstAlsaDevice	Inconnu	sans identifiant
			"""

	Plan du scénario: Les entrées de carte son de la sortie configurée, sans les sources qui écoutent une sortie
		https://github.com/dascritch/machincast/issues/622 : les entrées audio que MachinCast peut passer à l'antenne.

		Étant donné les entrées et les sorties vues par GStreamer :
			| type              | nom                 | node.name                      | internal-name                 | classe       |
			| GstPipeWireDevice | Haut-parleurs       | alsa_output.pci.analog-stereo  |                               | Audio/Sink   |
			| GstPipeWireDevice | Studio A            | alsa_input.usb-studio          |                               | Audio/Source |
			| GstPulseDevice    | Studio A (Pulse)    |                                | alsa_input.usb-studio         | Audio/Source |
			| GstPulseDevice    | Moniteur            |                                | alsa_output.pci.monitor       | Audio/Source |
			| GstAlsaDevice     | Entrée HDA          |                                | hw:0                          | Audio/Source |
		Alors les entrées de la sortie « <sortie> » sont <liste>

		Exemples:
			| sortie     | liste                                                  |
			| pipewire   | « alsa_input.usb-studio » « Studio A »                 |
			| pulseaudio | « alsa_input.usb-studio » « Studio A (Pulse) »         |
			| alsa       | « hw:0 » « Entrée HDA »                                |
			| dummy      | aucune                                                 |
