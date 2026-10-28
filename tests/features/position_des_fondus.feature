# language: fr
Fonctionnalité: Position des fondus par rapport aux silences détectés
	En tant que programmateur d'antenne,
	je veux régler où tombent le fade-in et le fade-out d'un sonore par rapport à ses silences détectés,
	afin que les enchaînements ne laissent ni trou ni son coupé.

	https://github.com/dascritch/machincast/issues/234. Pour un sonore joué sans ses silences (détection de silence du
	sonore ou de sa banque, https://github.com/dascritch/machincast/issues/146), le fade-in « commence », « est en
	cours » ou « se termine » au début détecté (par défaut, « se termine ») ; le fade-out « commence », « est en
	cours » ou « se termine » à la fin détectée (par défaut, « commence »). La lecture s'étend donc dans le silence d'autant
	que le fondu y déborde. Un fondu qui sortirait du fichier n'est pas joué hors du fichier : la lecture commence, ou
	s'arrête, au bord du fichier, au volume qu'aurait le fondu à cet instant, comme s'il avait déjà commencé. Un sonore
	joué avec ses silences l'est en entier, fondus aux bouts du fichier. La position se règle dans les préférences
	(section [crossfades]), pour tous les sonores : une banque ne règle que la présence et la durée des crossfades.

	Ces scénarios essaient le placement seul (machincast.lecture.fondus), puis la diffusion sur la base de test.

	# ─── Placement ─────────────────────────────────────────────

	Plan du scénario: La position des fondus place la lecture et ses fondus autour des silences détectés
		Étant donné un fichier de 60 secondes, aux silences détectés de <debut> au début et <fin> à la fin, <joue>
		Et des crossfades de 4 secondes au début et 8 à la fin
		Quand le fade-in <entree> au début détecté, et le fade-out <sortie> à la fin détectée
		Alors la lecture va de <de> à <a> secondes du fichier
		Et le fade-in dure <duree_entree> secondes, depuis le volume <depart>
		Et le fade-out dure <duree_sortie> secondes, jusqu'au volume <arrivee>

		Exemples:
			| debut | fin   | joue                  | entree      | sortie      | de | a  | duree_entree | depart | duree_sortie | arrivee |
			| 5 s   | 6 s   | sans ses silences       | se termine  | commence    | 1  | 60 | 4            | 0      | 6            | 0,25    |
			| 5 s   | 6 s   | sans ses silences       | est en cours| est en cours| 3  | 58 | 4            | 0      | 8            | 0       |
			| 5 s   | 6 s   | sans ses silences       | commence    | se termine  | 5  | 54 | 4            | 0      | 8            | 0       |
			| 1 s   | 6 s   | sans ses silences       | se termine  | se termine  | 0  | 54 | 1            | 0,75   | 8            | 0       |
			| aucun | 6 s   | sans ses silences       | se termine  | se termine  | 0  | 54 | 0            | 1      | 8            | 0       |
			| 5 s   | aucun | sans ses silences       | commence    | commence    | 5  | 60 | 4            | 0      | 0            | 1       |
			| 5 s   | 6 s   | avec ses silences       | se termine  | commence    | 0  | 60 | 4            | 0      | 8            | 0       |
			| 30 s  | 30 s  | sans ses silences       | se termine  | commence    | 0  | 60 | 4            | 0      | 8            | 0       |

	Plan du scénario: Les positions se lisent dans la configuration, et s'écrivent ainsi
		Alors la position « <position> » s'écrit « <cle> » dans la configuration

		Exemples:
			| position     | cle      |
			| commence     | commence |
			| est en cours | en_cours |
			| se termine   | termine  |

	# ─── Diffusion ─────────────────────────────────────────────

	Scénario: La diffusion joue le sonore selon les positions des préférences
		Étant donné le sonore « Respiration », de 60 secondes, aux silences détectés de 5 s au début et 6 s à la fin, qui active la détection de silence, avec des crossfades de 4 secondes au début et 8 à la fin
		Et les positions des fondus de la configuration : fade-in « est en cours », fade-out « se termine »
		Quand la diffusion lit les paramètres de « Respiration », sans banque
		Alors ses paramètres de lecture : à partir de 3 s du fichier, pendant 51 s, fade-in de 4 s depuis 0, fade-out de 8 s jusqu'à 0

	Scénario: Par défaut, le fade-in se termine au début détecté, et le fade-out commence à la fin détectée
		Étant donné le sonore « Respiration », de 60 secondes, aux silences détectés de 5 s au début et 6 s à la fin, qui active la détection de silence, avec des crossfades de 4 secondes au début et 8 à la fin
		Quand la diffusion lit les paramètres de « Respiration », sans banque
		Alors ses paramètres de lecture : à partir de 1 s du fichier, pendant 59 s, fade-in de 4 s depuis 0, fade-out de 6 s jusqu'à 0,25

	Scénario: Une banque règle la durée des crossfades, les préférences leur position
		Étant donné le sonore « Respiration », de 60 secondes, aux silences détectés de 5 s au début et 6 s à la fin, qui active la détection de silence, avec des crossfades de 4 secondes au début et 8 à la fin
		Et les positions des fondus de la configuration : fade-in « est en cours », fade-out « se termine »
		Et la banque « Nuit », avec « Respiration », qui impose un crossfade de fin de 2 secondes
		Quand la diffusion lit les paramètres de « Respiration », de la banque « Nuit »
		Alors ses paramètres de lecture : à partir de 3 s du fichier, pendant 51 s, fade-in de 4 s depuis 0, fade-out de 2 s jusqu'à 0
