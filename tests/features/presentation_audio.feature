# language: fr
Fonctionnalité: Chaque programme de MachinCast se présente au serveur audio sous son nom et l'icône de MachinCast
	En tant qu'administrateur système,
	je veux que le lecteur s'indique correctement dans le réglage du son du poste,
	afin de comprendre qui fait quoi.

	https://github.com/dascritch/machincast/issues/296. Sans rien dire, une sortie GStreamer se présente à PipeWire ou à
	PulseAudio sous le nom de l'interpréteur, « Python 3.14 ». machincast.audio.creer_sortie présente donc chaque sortie
	(Presentation) : le nom du programme (client-name, application.name), le nom de son flux (media.name), et l'icône
	« machincast » (application.icon-name pour PipeWire, application.icon_name pour PulseAudio), qu'install.sh installe
	dans le thème d'icônes du compte : le réglage du son de Plasma ne montre qu'une icône du thème. Une sortie ALSA ou
	factice n'a rien à présenter.

	Plan du scénario: La sortie d'un programme se présente sous son nom, celui de son flux, et l'icône de MachinCast
		Quand je crée la sortie « <sortie> » de <programme>
		Alors la sortie se présente comme « <nom> », pour le flux « <flux> », avec l'icône « machincast »

		Exemples:
			| sortie     | programme              | nom                     | flux        |
			| pipewire   | Machin lecture         | MachinCast lecteur      | Antenne     |
			| pulseaudio | Machin lecture         | MachinCast lecteur      | Antenne     |
			| pipewire   | la pré-écoute          | MachinCast interface    | Pré-écoute  |
			| pulseaudio | la pré-écoute          | MachinCast interface    | Pré-écoute  |
			| pipewire   | l'essai de la sortie   | MachinCast installation | Son de test |

	Plan du scénario: Une sortie ALSA ou factice n'a rien à présenter
		Quand je crée la sortie « <sortie> » de Machin lecture
		Alors la sortie est créée, sans présentation

		Exemples:
			| sortie  |
			| alsa    |
			| factice |

	Scénario: PipeWire reçoit aussi le nom et l'icône pour le programme, pas seulement pour son flux
		Quand je crée la sortie « pipewire » de Machin lecture
		Alors les propriétés du client PipeWire de la sortie nomment « MachinCast lecteur », avec l'icône « machincast »

	Scénario: Machin lecture, la pré-écoute et l'essai de la sortie présentent leurs sorties
		Alors chaque appel à creer_sortie, hors des tests, passe une présentation

	Scénario: install.sh installe l'icône de MachinCast dans le thème d'icônes du compte, sous le nom qu'annoncent les sorties
		Alors install.sh installe l'icône de MachinCast en « icons/hicolor/512x512/apps/machincast.png » du compte
