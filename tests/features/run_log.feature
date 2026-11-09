# language: fr
Fonctionnalité: Démarrages et fins des binaires dans le log
	En tant qu'administrateur technique,
	je veux trouver dans les logs les démarrages et fins de Machin indexer, Machin maintenance-db et Machin purge,
	afin d'identifier d'éventuels soucis ou fausses manœuvres
	(https://github.com/dascritch/machincast/issues/341).

	Chacun note son démarrage et sa fin au journal et au log de la base, Machin player compris depuis
	https://github.com/dascritch/machincast/issues/342. Un démarrage précédent sans
	fin, dont le processus ne tourne plus, est un plantage probable, noté en incident. Dans les textes attendus,
	« <version> » est la version de MachinCast, « <pid> » le pid du lancement, « <ancien pid> » celui du démarrage
	précédent, et « …/ » le répertoire du scénario.

	Contexte:
		Étant donné une configuration dont la base de production est la base de test

	Plan du scénario: Un lancement note son démarrage et sa fin, avec ses options, au journal et au log de la base
		Quand je lance « <commande> »
		Alors le lancement se termine avec le code 0
		Et le journal a noté « démarrage : <démarrage> »
		Et le journal a noté « fin : <binaire>, pid <pid> : code de sortie 0 »
		Et le log de la base a noté, au niveau info, le « démarrage » « <démarrage> », puis la « fin » « <binaire>, pid <pid> : code de sortie 0 »

		Exemples:
			| commande                                      | binaire               | démarrage                                                            |
			| Machin purge                                  | Machin_purge          | Machin_purge <version>, pid <pid>                                    |
			| Machin indexer --full-audit                   | Machin_indexer        | Machin_indexer <version>, pid <pid> : --full-audit                   |
			| Machin maintenance-db --backups …/sauvegardes | Machin_maintenance-db | Machin_maintenance-db <version>, pid <pid> : --backups …/sauvegardes |

	Scénario: Une fin en erreur note son code de sortie, en incident
		Le code 2 est celui d'une option refusée : --force ne va qu'avec --full-audit.
		Quand je lance « Machin indexer --force »
		Alors le lancement se termine avec le code 2
		Et le journal a signalé « incident : fin : Machin_indexer, pid <pid> : code de sortie 2 »
		Et le log de la base a noté, au niveau incident, la « fin » « Machin_indexer, pid <pid> : code de sortie 2 »

	Scénario: Un démarrage précédent sans fin, dont le processus ne tourne plus, est un plantage probable
		Étant donné un démarrage de « Machin_purge » noté le 2026-11-01 à 03:00 par un processus qui ne tourne plus, sans fin
		Quand je lance « Machin purge »
		Alors le lancement se termine avec le code 0
		Et le log de la base a noté, au niveau incident, le « plantage probable » « Machin_purge, pid <ancien pid>, démarré le 01/11/2026 à 03:00, n'a pas noté sa fin »
		Et le journal a signalé « incident : plantage probable : Machin_purge, pid <ancien pid>, démarré le 01/11/2026 à 03:00, n'a pas noté sa fin »

	Scénario: Le démarrage précédent d'un lancement encore en cours n'est pas un plantage
		Étant donné un démarrage de « Machin_indexer » noté à l'instant par un processus qui tourne encore, sans fin
		Quand je lance « Machin indexer »
		Alors le log de la base n'a noté aucun plantage probable

	Scénario: Ni un lancement précédent qui a noté sa fin, ni le plantage d'un autre binaire ne sont un plantage probable
		Étant donné un démarrage de « Machin_indexer » noté le 2026-11-01 à 03:00 par un processus qui ne tourne plus, sans fin
		Quand je lance « Machin purge »
		Et je lance « Machin purge »
		Alors le log de la base n'a noté aucun plantage probable

	Scénario: La vérification d'un seul sonore, que Machin player demande avant chaque sonore, ne note ni démarrage ni fin
		Quand je lance « Machin indexer --sound 1 »
		Alors le log de la base n'a noté ni démarrage ni fin

	Scénario: La maintenance note sa fin avant de garder son terminal ouvert
		L'interface lance la maintenance dans un terminal qui reste ouvert : le fermer ne fait pas un plantage.
		Quand je lance « Machin maintenance-db --backups …/sauvegardes --keep-open »
		Alors le terminal est resté ouvert après la « fin » notée au log de la base

	Scénario: Une base injoignable n'empêche pas le lancement, et le journal dit que son démarrage n'a pas été noté
		Étant donné une configuration dont la base de production est injoignable
		Quand je lance « Machin purge »
		Alors le lancement se termine avec le code 1
		Et le journal a signalé que le démarrage de « Machin_purge » n'a pas été noté dans la base

	# ─── Machin player (https://github.com/dascritch/machincast/issues/342) ───
	# La diffusion est remplacée par une diffusion qui s'arrête aussitôt, avec le code donné, comme run_broadcast.

	Scénario: Machin player note son démarrage et sa fin, comme les autres binaires
		Étant donné une diffusion de Machin player qui s'arrête avec le code 0
		Quand je lance « Machin player »
		Alors le lancement se termine avec le code 0
		Et le log de la base a noté, au niveau info, le « démarrage » « Machin_player <version>, pid <pid> », puis la « fin » « Machin_player, pid <pid> : code de sortie 0 »

	Scénario: Une diffusion arrêtée en erreur note son code de sortie, en incident
		Le code 1 : une sortie audio indisponible, un autre Machin player déjà en diffusion.
		Étant donné une diffusion de Machin player qui s'arrête avec le code 1
		Quand je lance « Machin player »
		Alors le lancement se termine avec le code 1
		Et le log de la base a noté, au niveau incident, la « fin » « Machin_player, pid <pid> : code de sortie 1 »

	Scénario: Sans périphérique d'antenne, Machin player note sa fin au code 2, en incident
		Étant donné une configuration sans périphérique d'antenne
		Quand je lance « Machin player »
		Alors le lancement se termine avec le code 2
		Et le log de la base a noté, au niveau incident, la « fin » « Machin_player, pid <pid> : code de sortie 2 »

	Scénario: Le plantage probable d'un Machin player précédent donne le chemin de son rapport de crash
		Étant donné un démarrage de « Machin_player » noté le 2026-11-01 à 03:00 par un processus qui ne tourne plus, sans fin
		Et le rapport de crash en cours de ce démarrage, laissé par son processus
		Et une diffusion de Machin player qui s'arrête avec le code 0
		Quand je lance « Machin player »
		Alors le log de la base a noté, au niveau incident, le « plantage probable » « Machin_player, pid <ancien pid>, démarré le 01/11/2026 à 03:00, n'a pas noté sa fin ; rapport de crash …/crash-dump/Machin_player-2026-11-01T03-00-00-<ancien pid>.txt »

	Scénario: La simulation ne note ni démarrage ni fin
		Quand je lance « Machin player --simulation 2026-11-01T20:00 2026-11-01T20:10 --directory …/simulation »
		Alors le lancement se termine avec le code 0
		Et le log de la base n'a noté ni démarrage ni fin
