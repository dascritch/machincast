# language: fr
Fonctionnalité: Chaque programme de MachinCast se présente au serveur audio sous son nom et l'icône de MachinCast
	En tant qu'administrateur système,
	je veux que le lecteur s'indique correctement dans le réglage du son du poste,
	afin de comprendre qui fait quoi.

	https://github.com/dascritch/machincast/issues/296, https://github.com/dascritch/machincast/issues/343. Sans rien dire, une sortie GStreamer se présente à PipeWire ou à
	PulseAudio sous le nom de l'interpréteur, « Python 3.14 ». machincast.audio.create_output présente donc chaque sortie
	(Presentation) : le nom du programme (client-name, application.name), le nom de son flux (media.name), et l'icône
	« machincast » (application.icon-name pour PipeWire, application.icon_name pour PulseAudio), qu'install.sh installe
	dans le thème d'icônes du compte : le réglage du son de Plasma ne montre qu'une icône du thème. Une sortie ALSA ou
	factice n'a rien à présenter.

	Plan du scénario: La sortie d'un programme se présente sous son nom, celui de son flux, et l'icône de MachinCast
		Quand je crée la sortie « <sortie> » de <programme>
		Alors la sortie se présente comme « <nom> », pour le flux « <flux> », avec l'icône « machincast »

		Exemples:
			| sortie     | programme              | nom                     | flux        |
			| pipewire   | Machin player         | MachinCast lecteur      | Antenne     |
			| pulseaudio | Machin player         | MachinCast lecteur      | Antenne     |
			| pipewire   | la pré-écoute          | MachinCast interface    | Pré-écoute  |
			| pulseaudio | la pré-écoute          | MachinCast interface    | Pré-écoute  |
			| pipewire   | l'essai de la sortie   | MachinCast installation | Son de test |

	Plan du scénario: Une sortie ALSA ou factice n'a rien à présenter
		Quand je crée la sortie « <sortie> » de Machin player
		Alors la sortie est créée, sans présentation

		Exemples:
			| sortie  |
			| alsa    |
			| dummy   |

	Plan du scénario: L'écoute de l'antenne, dans l'interface, se présente sous le nom de l'interface
		https://github.com/dascritch/machincast/issues/343. La source qui relève les niveaux de l'antenne pour le
		vumètre est un flux de l'interface : sans présentation, pw-top la nommait « python3.14 ».

		Quand je crée l'écoute de l'antenne « <sortie> »
		Alors la source se présente comme « MachinCast interface », pour le flux « Écoute de l'antenne », avec l'icône « machincast »

		Exemples:
			| sortie     |
			| pipewire   |
			| pulseaudio |

	Scénario: L'écoute de l'antenne présentée écoute toujours la sortie de l'antenne
		Quand je crée l'écoute de l'antenne « pipewire »
		Alors la source écoute la sortie de son périphérique (stream.capture.sink)

	Plan du scénario: Un binaire se nomme auprès de GLib, pour tout client du serveur audio qu'il crée
		https://github.com/dascritch/machincast/issues/343. Un client que MachinCast ne présente pas lui-même, comme
		celui qui liste les périphériques, prend le nom de l'application de GLib, sinon celui de l'interpréteur.

		Quand <binaire> se nomme
		Alors GLib le nomme « <nom> », du programme « <binaire> »

		Exemples:
			| binaire          | nom                  |
			| Machin_player    | MachinCast lecteur   |
			| Machin_interface | MachinCast interface |

	Scénario: Machin_player et Machin_interface se nomment dès leur lancement
		Alors la fonction run de Machin_player et de Machin_interface commence par se nommer

	Scénario: PipeWire reçoit aussi le nom et l'icône pour le programme, pas seulement pour son flux
		Quand je crée la sortie « pipewire » de Machin player
		Alors les propriétés du client PipeWire de la sortie nomment « MachinCast lecteur », avec l'icône « machincast »

	Scénario: Machin player, la pré-écoute et l'essai de la sortie présentent leurs sorties
		Alors chaque appel à create_output, hors des tests, passe une présentation

	Scénario: install.sh installe l'icône de MachinCast dans le thème d'icônes du compte, sous le nom qu'annoncent les sorties
		Alors install.sh installe l'icône de MachinCast en « icons/hicolor/512x512/apps/machincast.png » du compte
