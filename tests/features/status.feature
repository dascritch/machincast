# language: fr
Fonctionnalité: État de la station pour le shell : Machin status
	En tant que technicien radio,
	je veux interroger depuis le shell l'état de la station,
	afin d'alimenter un script, une barre d'état ou une supervision.

	https://github.com/dascritch/machincast/issues/518.
	Machin status répond par une ligne, sur la sortie standard : « Machin status server » dit « service » quand le
	service de diffusion est installé et « test » sinon ; « Machin status radio » donne le nom de la radio
	(metadata.public_text) ; « Machin status event --now » et « Machin status event --next » donnent l'événement actuel
	et le suivant, « {début} → {fin} : {nom privé} », aux heures du poste. Sans événement, rien n'est écrit et le code
	de sortie est 1. « Machin status », seul, dit l'état de Machin player (« running » ou « stopped », code 0 ou 1), et
	« Machin status event », seul, est « Machin status event --now ». Un fil musical permanent n'a ni début ni fin :
	celles qu'on lit sont l'heure où il a pris l'antenne, et l'heure où il sera interrompu. La commande ne fait que lire : l'horloge des scénarios est fixée au 2026-11-20 à 10:30.

	Contexte:
		Étant donné une configuration dont la base de production est la base de test
		Et l'horloge de l'état à « 2026-11-20 10:30:00 »

	Scénario: Le service de diffusion installé, le serveur est en service
		Étant donné que le service de diffusion est installé
		Quand je lance « Machin status server »
		Alors l'état répond « service » avec le code 0

	Scénario: Sans le service de diffusion, c'est une installation de test
		Étant donné que le service de diffusion n'est pas installé
		Quand je lance « Machin status server »
		Alors l'état répond « test » avec le code 0

	Scénario: La radio porte le nom du texte public de la configuration
		Étant donné que le nom de la radio est « Radio FMR »
		Quand je lance « Machin status radio »
		Alors l'état répond « Radio FMR » avec le code 0

	Scénario: L'événement actuel et le suivant disent leurs heures et leur nom privé
		Étant donné les événements en base :
			| nom privé        | priorité | début            | fin              |
			| Matinale interne | show     | 2026-11-20 09:00 | 2026-11-20 11:00 |
			| Midi-info        | show     | 2026-11-20 12:00 | 2026-11-20 13:30 |
			| Soirée           | show     | 2026-11-20 20:00 | 2026-11-20 22:00 |
		Quand je lance « Machin status event --now »
		Alors l'état répond « 09:00 → 11:00 : Matinale interne » avec le code 0
		Quand je lance « Machin status event --next »
		Alors l'état répond « 12:00 → 13:30 : Midi-info » avec le code 0

	Scénario: Un fil musical dit l'heure où il a pris l'antenne et l'heure où il sera interrompu
		Étant donné les événements en base :
			| nom privé        | priorité               | début            | fin              |
			| Fil musical      | background_programming |                  |                  |
			| Matinale interne | show                   | 2026-11-20 09:00 | 2026-11-20 10:00 |
			| Midi-info        | show                   | 2026-11-20 12:00 | 2026-11-20 13:30 |
		Quand je lance « Machin status event --now »
		Alors l'état répond « 10:00 → 12:00 : Fil musical » avec le code 0

	Scénario: Un fil musical seul, sans événement avant ni après, n'a ni début ni fin
		Étant donné les événements en base :
			| nom privé   | priorité               | début | fin |
			| Fil musical | background_programming |       |     |
		Quand je lance « Machin status event --now »
		Alors l'état répond « --:-- → --:-- : Fil musical » avec le code 0

	Scénario: Un fil musical encore sur l'antenne n'a pas de fin avant le prochain événement
		Étant donné les événements en base :
			| nom privé        | priorité               | début            | fin              |
			| Fil musical      | background_programming |                  |                  |
			| Matinale interne | show                   | 2026-11-20 09:00 | 2026-11-20 10:00 |
		Quand je lance « Machin status event --now »
		Alors l'état répond « 10:00 → --:-- : Fil musical » avec le code 0

	Scénario: Machin status event, sans option, est l'événement actuel
		Étant donné les événements en base :
			| nom privé        | priorité | début            | fin              |
			| Matinale interne | show     | 2026-11-20 09:00 | 2026-11-20 11:00 |
		Quand je lance « Machin status event »
		Alors l'état répond « 09:00 → 11:00 : Matinale interne » avec le code 0

	Scénario: Machin status, seul, dit que Machin player diffuse
		Étant donné Machin player qui diffuse
		Quand je lance « Machin status »
		Alors l'état répond « running » avec le code 0

	Scénario: Machin status player est aussi l'état de Machin player
		Étant donné Machin player qui diffuse
		Quand je lance « Machin status player »
		Alors l'état répond « running » avec le code 0

	Scénario: Sans Machin player, l'état est arrêté, avec le code 1
		Étant donné qu'aucun Machin player ne tourne
		Quand je lance « Machin status »
		Alors l'état répond « stopped » avec le code 1

	Scénario: Une simulation de Machin player n'est pas une diffusion
		Étant donné Machin player en simulation
		Quand je lance « Machin status »
		Alors l'état répond « stopped » avec le code 1

	Scénario: Sans événement suivant, rien n'est écrit et le code est 1
		Étant donné les événements en base :
			| nom privé        | priorité | début            | fin              |
			| Matinale interne | show     | 2026-11-20 09:00 | 2026-11-20 11:00 |
		Quand je lance « Machin status event --next »
		Alors l'état n'écrit rien et se termine avec le code 1

	Scénario: Sans événement actuel, rien n'est écrit et le code est 1
		Étant donné les événements en base :
			| nom privé | priorité | début            | fin              |
			| Soirée    | show     | 2026-11-20 20:00 | 2026-11-20 22:00 |
		Quand je lance « Machin status event --now »
		Alors l'état n'écrit rien et se termine avec le code 1

	Scénario: Un événement supprimé n'est ni actuel ni suivant
		Étant donné les événements en base :
			| nom privé | priorité | début            | fin              |
			| Soirée    | show     | 2026-11-20 20:00 | 2026-11-20 22:00 |
		Et que l'événement « Soirée » est supprimé
		Quand je lance « Machin status event --next »
		Alors l'état n'écrit rien et se termine avec le code 1

	Scénario: Une base injoignable est signalée, avec le code 3
		Étant donné une configuration dont la base de production est injoignable
		Quand je lance « Machin status event --now »
		Alors l'état n'écrit rien et se termine avec le code 3

	Scénario: Le résumé de la bannière donne le serveur, la radio, le player, et les événements quand le player diffuse
		Étant donné que le service de diffusion est installé
		Et que le nom de la radio est « Radio FMR »
		Et Machin player qui diffuse
		Et les événements en base :
			| nom privé        | priorité | début            | fin              |
			| Matinale interne | show     | 2026-11-20 09:00 | 2026-11-20 11:00 |
			| Midi-info        | show     | 2026-11-20 12:00 | 2026-11-20 13:30 |
		Quand je lance « Machin status summary »
		Alors l'état écrit les lignes :
			| clé    | valeur                              |
			| server | service                             |
			| radio  | Radio FMR                           |
			| player | running                             |
			| now    | 09:00 → 11:00 : Matinale interne    |
			| next   | 12:00 → 13:30 : Midi-info           |

	Scénario: Le résumé de la bannière ne cherche aucun événement quand le player ne diffuse pas
		Étant donné que le service de diffusion n'est pas installé
		Et que le nom de la radio est « Radio FMR »
		Et aucun Machin player ne tourne
		Quand je lance « Machin status summary »
		Alors l'état écrit les lignes :
			| clé    | valeur    |
			| server | test      |
			| radio  | Radio FMR |
			| player | stopped   |

	Scénario: Le résumé garde le serveur, la radio et le player quand la base est injoignable
		Étant donné que le service de diffusion n'est pas installé
		Et que le nom de la radio est « Radio FMR »
		Et une configuration dont la base de production est injoignable
		Et Machin player qui diffuse
		Quand je lance « Machin status summary »
		Alors l'état écrit les lignes :
			| clé    | valeur  |
			| server | test    |
			| radio  | Radio FMR |
			| player | running |

	Scénario: Une option inconnue de l'événement est refusée
		Quand je lance « Machin status event --soon »
		Alors l'état est refusé avec le code 2
