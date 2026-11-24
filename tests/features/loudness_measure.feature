# language: fr
Fonctionnalité: La mesure du niveau d'un sonore à l'audit complet : crête absolue et sonie EBU R128
	En tant que technicien d'antenne,
	je veux que l'audit complet de Machin indexer mesure le niveau de chaque sonore de type fichier,
	afin que la normalisation logicielle du niveau, et plus tard un compresseur ou un limiteur, s'appuient sur une mesure exacte.

	https://github.com/dascritch/machincast/issues/642, pour https://github.com/dascritch/machincast/issues/43. La crête
	absolue est le plus grand échantillon, en dBFS, à 48 kHz ; la sonie intégrée suit l'ITU-R BS.1770 et l'EBU R128 :
	une sinusoïde de 1 kHz à −23 dBFS sur les deux canaux d'un stéréo, ou à −20 dBFS en mono, fait −23 LUFS (EBU Tech
	3341). Elles sont rangées dans la colonne properties du sonore, sous la clé « loudness », au dixième près.

	Plan du scénario: Le décodage de l'audit complet mesure la crête et la sonie
		Étant donné un fichier wav de 20 secondes, sinusoïde de 1 kHz à <niveau> dBFS, <canaux>, à <fréquence> Hz
		Quand je vérifie ce fichier en audit complet
		Alors sa sonie intégrée est de <sonie> LUFS à 0,1 près
		Et sa crête est de <crête> dBFS à 0,1 près

		Exemples:
			| niveau | canaux | fréquence | sonie | crête |
			| -23    | stéréo | 48000     | -23   | -23   |
			| -23    | stéréo | 44100     | -23   | -23   |
			| -20    | mono   | 48000     | -23   | -20   |
			| -6     | mono   | 48000     | -9    | -6    |

	Scénario: Un silence numérique n'a ni crête ni sonie
		Étant donné un fichier wav de 20 secondes, silence, mono, à 48000 Hz
		Quand je vérifie ce fichier en audit complet
		Alors il n'a ni sonie intégrée ni crête

	Scénario: Un son plus court qu'un bloc de 400 ms n'a pas de sonie intégrée, mais sa crête
		Étant donné un fichier wav de 0,3 seconde, sinusoïde de 1 kHz à -20 dBFS, mono, à 48000 Hz
		Quand je vérifie ce fichier en audit complet
		Alors il n'a pas de sonie intégrée
		Et sa crête est de -20 dBFS à 0,1 près

	Scénario: Les blocs sous la porte relative ne comptent pas : un long silence ne fait pas baisser la sonie
		Étant donné un fichier wav fait de 10 secondes à -20 dBFS puis 30 secondes à -60 dBFS, mono, à 48000 Hz
		Quand je vérifie ce fichier en audit complet
		Alors sa sonie intégrée est de -23 LUFS à 0,1 près

	Scénario: Une vérification hors audit ne mesure rien
		Étant donné un fichier wav de 20 secondes, sinusoïde de 1 kHz à -20 dBFS, mono, à 48000 Hz
		Quand je vérifie ce fichier
		Alors le niveau n'a pas été mesuré

	Scénario: L'audit complet range la mesure dans les propriétés du sonore, sans toucher à ses autres clés
		Étant donné un fichier wav de 20 secondes, sinusoïde de 1 kHz à -23 dBFS, stéréo, à 48000 Hz
		Et un sonore à l'état « active » pour ce fichier
		Et ses propriétés {"horloge": {"sonne": true}}
		Quand l'indexeur fait un audit complet
		Alors ses propriétés sont {"horloge": {"sonne": true}, "loudness": {"integrated": -23.0, "peak": -23.0}}

	Scénario: Une indexation rapide laisse la mesure en place
		Étant donné un fichier wav de 20 secondes, sinusoïde de 1 kHz à -23 dBFS, stéréo, à 48000 Hz
		Et un sonore à l'état « active » pour ce fichier
		Et ses propriétés {"loudness": {"integrated": -14.2, "peak": -0.5}}
		Quand l'indexeur fait une indexation rapide
		Alors ses propriétés sont {"loudness": {"integrated": -14.2, "peak": -0.5}}
