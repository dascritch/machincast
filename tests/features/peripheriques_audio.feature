# language: fr
Fonctionnalité: Périphériques de sortie du poste
	En tant que technicien d'antenne,
	je veux choisir les périphériques de l'antenne et de la pré-écoute parmi ceux du poste,
	afin de ne pas avoir à recopier leur nom à la main.

	https://github.com/dascritch/machincast/issues/116. machincast.audio.peripheriques demande à GStreamer les
	périphériques de sortie audio du poste, comme gst-device-monitor-1.0 Audio/Sink, et ne garde que ceux de la sortie
	configurée : nœuds PipeWire, périphériques PulseAudio ou ALSA. L'identifiant est celui qu'écrivent
	audio.peripherique et audio.preecoute : le nom du nœud PipeWire (node.name), sinon le nom interne du périphérique.
	« python -m machincast.installation peripheriques » les liste ; sans aucun, il dit tout ce que voit GStreamer.
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
			| factice    | aucun                                                                                  |

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
