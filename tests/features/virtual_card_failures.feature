# language: fr
Fonctionnalité: La carte virtuelle de l'antenne factice échoue sans bruit, et ne laisse aucun pw-cli
	En tant que mainteneur de MachinCast,
	je veux que chaque échec de la création de la carte virtuelle soit testé sans PipeWire,
	afin que la diffusion continue sur la sortie factice et que le log dise pourquoi.

	https://github.com/dascritch/machincast/issues/444. Les scénarios de virtual_on_air.feature lancent un vrai PipeWire ;
	ceux-ci imitent pw-cli et ses pannes : ils tournent sur tout poste, sans PipeWire.

	Plan du scénario: Une panne de pw-cli laisse l'antenne factice sans carte, et le log en donne la raison
		Quand Machin player prépare l'antenne factice avec un pw-cli qui « <panne> »
		Alors l'antenne est jouée sur la sortie factice
		Et le log dit « <raison> »
		Et aucun pw-cli ne reste lancé

		Exemples:
			| panne                       | raison                           |
			| est absent                  | pw-cli introuvable               |
			| ne peut pas se lancer       | pw-cli refuse de se lancer       |
			| refuse la commande          | pipe cassé                       |
			| s'arrête tout de suite      | PipeWire injoignable             |
			| ne montre jamais la carte   | PipeWire injoignable             |
			| ne répond pas à sa requête  | PipeWire injoignable             |
			| ne s'arrête pas à terminate | PipeWire injoignable             |

	Scénario: Le pw-cli de la carte reçoit SIGTERM quand Machin player s'arrête
		Quand le pw-cli de la carte est préparé avant son lancement
		Alors il reçoit SIGTERM à la mort de son parent
