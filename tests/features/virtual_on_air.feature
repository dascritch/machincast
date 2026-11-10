# language: fr
Fonctionnalité: L'antenne sur la sortie factice reste écoutable, sur une carte virtuelle
	En tant que développeur,
	je veux que la sortie Antenne vers la carte son factice reste monitorable sur les niveaux sonores et la sortie son,
	afin de mener des tests sur l'interface même quand je n'ai qu'une seule carte son.

	https://github.com/dascritch/machincast/issues/400. Sur l'entrée « sortie factice » de l'antenne (audio.device =
	"dummy") d'une sortie PipeWire ou PulseAudio, Machin player crée, le temps de sa diffusion, la carte virtuelle
	« MachinCast antenne factice » (support.null-audio-sink, node.name machincast_antenne_factice), par un pw-cli lié à
	son processus, et y joue l'antenne. L'interface en écoute le port de monitoring, pour le VU-mètre et la pré-écoute
	de l'antenne, comme celui d'une vraie carte. Sans PipeWire joignable, ou sur une sortie ALSA, l'antenne factice ne
	joue nulle part, et son VU-mètre montre un signal de test (https://github.com/dascritch/machincast/issues/339).

	Plan du scénario: L'antenne factice s'écoute sur la carte virtuelle d'une sortie PipeWire ou PulseAudio
		Étant donné l'antenne sur l'entrée « sortie factice » de la sortie « <sortie> »
		Alors l'antenne est jouée et écoutée sur « <carte> »

		Exemples:
			| sortie     | carte                      |
			| pipewire   | machincast_antenne_factice |
			| pulseaudio | machincast_antenne_factice |
			| alsa       | la sortie factice          |
			| dummy      | la sortie factice          |

	Scénario: Machin player joue l'antenne factice sur la carte virtuelle, qui existe le temps de sa diffusion
		Étant donné un PipeWire à part
		Quand Machin player joue l'antenne factice d'une sortie « pipewire »
		Alors PipeWire a la carte « machincast_antenne_factice », décrite « MachinCast antenne factice »
		Et le flux de Machin player joue sur « machincast_antenne_factice »
		Quand Machin player s'arrête
		Alors PipeWire n'a plus la carte « machincast_antenne_factice »

	Scénario: La carte virtuelle disparaît avec Machin player, même tué
		Étant donné un PipeWire à part
		Quand Machin player joue l'antenne factice d'une sortie « pipewire »
		Et Machin player est tué
		Alors PipeWire n'a plus la carte « machincast_antenne_factice »

	Scénario: Le VU-mètre de l'antenne factice mesure ce que Machin player y joue
		Étant donné un PipeWire à part
		Quand Machin player joue l'antenne factice d'une sortie « pipewire »
		Alors le port de monitoring de l'antenne factice relève un son au-dessus de -40 dB

	Scénario: Sans PipeWire joignable, Machin player diffuse l'antenne factice sans carte virtuelle, et le dit
		Quand Machin player prépare l'antenne factice d'une sortie « pipewire », sans PipeWire joignable
		Alors l'antenne est jouée sur la sortie factice
		Et le log dit « carte virtuelle « MachinCast antenne factice » non créée »
