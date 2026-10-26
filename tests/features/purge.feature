# language: fr
Fonctionnalité: Désherbage de la base : Machin purge
	En tant que technicien radio,
	je veux une suppression des données passée une certaine période,
	afin de maintenir en conditions opérationnelles le service.

	https://github.com/dascritch/machincast/issues/268, partie de https://github.com/dascritch/machincast/issues/251.
	Machin purge efface de la base de production ce qui dépasse la durée de péremption (base.peremption, 60 jours par
	défaut) : les lignes de l'airplay et du log plus vieilles qu'elle ; les sonores, banques, séquences et événements
	supprimés depuis plus longtemps (https://github.com/dascritch/machincast/issues/267) ; les sonores dont le fichier
	a disparu depuis plus longtemps. Seules les données en base sont effacées, jamais un fichier sonore ni un
	répertoire (https://github.com/dascritch/machincast/issues/96). La purge travaille sur la base de test, désignée
	comme base de production d'une configuration du scénario ; son horloge est fixée.

	Contexte:
		Étant donné une configuration dont la base de production est la base de test
		Et l'horloge de la purge au « 2026-12-20 12:00:00 »

	Scénario: La purge efface ce qui dépasse 60 jours, et garde le reste
		Étant donné les passages de l'airplay, et autant de lignes du log :
			| date       | titre  |
			| 2026-10-01 | Vieux  |
			| 2026-11-01 | Récent |
		Et les éléments en base :
			| genre     | nom                      | supprimé le | fichier disparu le |
			| sonore    | Ancien supprimé          | 2026-10-01  |                    |
			| sonore    | Récemment supprimé       | 2026-12-01  |                    |
			| sonore    | En service               |             |                    |
			| sonore    | Disparu il y a longtemps |             | 2026-10-01         |
			| sonore    | Disparu récemment        |             | 2026-12-01         |
			| banque    | Vieille banque           | 2026-10-01  |                    |
			| banque    | Banque récente           | 2026-12-01  |                    |
			| séquence  | Vieille séquence         | 2026-10-01  |                    |
			| événement | Vieil événement          | 2026-10-01  |                    |
			| événement | Matinale                 |             |                    |
		Quand je lance « Machin purge »
		Alors la purge se termine avec le code 0
		Et la purge a annoncé « purge de la base machincast_test, au-delà de 60 jours (avant le 21/10/2026 12:00) : 1 passage de l'airplay, 1 ligne du log, 2 sonores, 1 banque, 1 séquence, 1 événement effacés »
		Et la purge n'a rien signalé
		Et l'airplay garde les passages « Récent »
		Et le log garde ses lignes du 2026-11-01, et une ligne « purge » qui reprend l'annonce
		Et en base restent les sonores « Récemment supprimé », « En service », « Disparu récemment »
		Et en base restent les banques « Banque récente »
		Et en base ne reste aucune séquence
		Et en base restent les événements « Matinale »

	Scénario: Un passage récent d'un sonore effacé garde son titre et son emplacement
		Étant donné les éléments en base :
			| genre  | nom             | supprimé le | fichier disparu le |
			| sonore | Ancien supprimé | 2026-10-01  |                    |
		Et un passage du sonore « Ancien supprimé » le 2026-11-01
		Quand je lance « Machin purge »
		Alors l'airplay garde le passage « Ancien supprimé », à l'emplacement « /srv/Ancien supprimé.flac », sans sonore en base

	Scénario: Un passage commencé avant la limite, et fini après, reste entier
		Étant donné un passage « À cheval », commencé le « 2026-10-21 11:58:00 » et fini le « 2026-10-21 12:02:00 »
		Quand je lance « Machin purge »
		Alors l'airplay garde le début et la fin du passage « À cheval »

	Scénario: La purge suit la durée de péremption de la configuration
		Étant donné la durée de péremption de 30 jours dans la configuration
		Et les passages de l'airplay, et autant de lignes du log :
			| date       | titre  |
			| 2026-11-01 | Récent |
			| 2026-12-01 | Proche |
		Quand je lance « Machin purge »
		Alors la purge a annoncé « purge de la base machincast_test, au-delà de 30 jours (avant le 20/11/2026 12:00) : 1 passage de l'airplay, 1 ligne du log, 0 sonore, 0 banque, 0 séquence, 0 événement effacés »
		Et l'airplay garde les passages « Proche »

	Scénario: Les fichiers des sonores effacés restent à leur place, intacts
		Étant donné le fichier sonore « …/archives/vieux.flac » du sonore « Vieux », supprimé le 2026-10-01
		Quand je lance « Machin purge »
		Alors en base ne reste aucun sonore
		Et le fichier « …/archives/vieux.flac » est toujours là, intact

	Scénario: Un stream supprimé, une fois effacé, ne retient plus son feed
		Étant donné le feed « Studio », suivi par le stream « Direct », supprimé le 2026-10-01
		Quand je lance « Machin purge »
		Alors aucun stream ne suit plus le feed « Studio », qui peut se supprimer

	Scénario: Une base injoignable est signalée, et rien n'est effacé
		Étant donné une configuration dont la base de production est injoignable
		Quand je lance « Machin purge »
		Alors la purge se termine avec le code 1
		Et la purge a signalé une base de données injoignable

	Scénario: Machin purge est un binaire du wrapper
		Alors « purge » est un binaire du wrapper, déclaré dans pyproject.toml
