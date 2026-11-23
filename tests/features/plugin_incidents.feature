# language: fr
Fonctionnalité: log_incident, l'avertissement d'un incident grave
	En tant que responsable d'antenne,
	je veux qu'un plugin puisse m'avertir d'un incident grave,
	afin d'être prévenu en urgence, par messagerie par exemple
	(https://github.com/dascritch/machincast/issues/592, ticket enfant de https://github.com/dascritch/machincast/issues/348).

	Scénario: Un incident consigné au log par Machin player prévient le plugin, avec ce qu'il concerne
		Étant donné un plugin « témoin » chargé dans « Machin_player », abonné à « log_incident »
		Et le sonore « Direct » de l'événement « Matinale »
		Quand Machin player consigne l'incident « dropped stream » : « the stream stopped before the end of its event », pour le sonore « Direct » et l'événement « Matinale »
		Alors le plugin « témoin » a été prévenu 1 fois
		Et il a reçu de « Machin_player » l'incident de niveau « incident », de nature « flux tombé », au message « le flux s'est arrêté avant la fin de son événement »
		Et l'incident concerne le sonore « Direct » et l'événement « Matinale », sans banque

	Scénario: Une alerte ou une information du log n'en est pas un
		Étant donné un plugin « témoin » chargé dans « Machin_player », abonné à « log_incident »
		Quand Machin player consigne l'alerte « dead air » : « nothing to broadcast »
		Et Machin player consigne l'information « stop » : « stop requested »
		Alors le plugin « témoin » a été prévenu 0 fois

	Plan du scénario: Une erreur du journal de chaque binaire prévient le plugin
		Étant donné un plugin « témoin » chargé dans « <binaire> », abonné à « log_incident »
		Quand le journal de « <binaire> » consigne l'erreur « base injoignable » du module « machincast.exemple »
		Et le journal de « <binaire> » consigne l'avertissement « disque presque plein » du module « machincast.exemple »
		Alors le plugin « témoin » a été prévenu 1 fois
		Et il a reçu de « <binaire> » l'incident de niveau « error », de nature « machincast.exemple », au message « base injoignable »

		Exemples:
			| binaire          |
			| Machin_player    |
			| Machin_indexer   |
			| Machin_interface |
			| Machin_intranet  |

	Scénario: Un plugin qui échoue à prévenir ne crée pas d'incident à son tour
		Étant donné un plugin « témoin » chargé dans « Machin_player », abonné à « log_incident »
		Et un plugin « fautif », qui échoue à « log_incident »
		Et un plugin « bavard », qui consigne une erreur au journal à « log_incident »
		Quand le journal de « Machin_player » consigne l'erreur « base injoignable » du module « machincast.exemple »
		Alors le plugin « témoin » a été prévenu 1 fois
		Et le journal du binaire dit que le plugin « fautif » a échoué au point « log_incident »
