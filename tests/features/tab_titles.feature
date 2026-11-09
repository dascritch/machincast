# language: fr
Fonctionnalité: Titres des onglets et menu « Onglets »
	En tant que technicien d'antenne,
	je veux que les titres des onglets restent courts, et retrouver chaque onglet ouvert dans un menu,
	afin que la barre des onglets reste utilisable quand une fiche a un nom très long.

	https://github.com/dascritch/machincast/issues/398. Le titre affiché d'un onglet a au plus 40 caractères : au-delà,
	il est coupé, et finit par « … ». L'infobulle de l'onglet donne alors le titre entier, au-dessus de son raccourci
	(tab_shortcuts.feature). Une fiche s'ouvre depuis sa liste, à sa droite (movable_tabs.feature). Le menu « Onglets »
	liste les onglets ouverts, dans leur ordre, avec leur titre entier et
	leur raccourci ; l'onglet ouvert y est coché, et choisir une entrée ouvre son onglet.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et les événements :
			| name        | public_name | priority               | starts_at | ends_at | days |
			| Fil de jour |             | background_programming |           |         |      |
		Et la séquence « Une séquence au nom vraiment beaucoup trop long », sans nom public, avec rien
		Et la séquence « Quarante caractères tout pile », sans nom public, avec rien

	Scénario: Un titre de plus de 40 caractères est coupé, et son infobulle le donne en entier
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Une séquence au nom vraiment beaucoup trop long »
		Alors l'onglet ouvert affiche « Séquence : Une séquence au nom vraiment… »
		Et l'infobulle de l'onglet ouvert est « Séquence : Une séquence au nom vraiment beaucoup trop long », puis « Maj+F5 »

	Scénario: Un titre de 40 caractères s'affiche en entier, et son infobulle ne donne que son raccourci
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Quarante caractères tout pile »
		Alors l'onglet ouvert affiche « Séquence : Quarante caractères tout pile »
		Et l'infobulle de l'onglet ouvert est « Maj+F5 »

	Scénario: Le menu « Onglets » liste les onglets ouverts, avec leur titre entier, et coche l'onglet ouvert
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Une séquence au nom vraiment beaucoup trop long »
		Alors le menu « Onglets » liste :
			| onglet                                                     | raccourci | cochée |
			| Antenne                                                    | Maj+F1    | non    |
			| Calendrier                                                 | Maj+F2    | non    |
			| Événements                                                 | Maj+F3    | non    |
			| Séquences                                                  | Maj+F4    | non    |
			| Séquence : Une séquence au nom vraiment beaucoup trop long | Maj+F5    | oui    |
			| Banques                                                    | Maj+F6    | non    |
			| Incidents                                                  | Maj+F7    | non    |

	Scénario: Choisir un onglet dans le menu « Onglets » l'ouvre
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Une séquence au nom vraiment beaucoup trop long »
		Et je choisis l'onglet « Calendrier » dans le menu « Onglets »
		Alors l'onglet ouvert est « Calendrier »
		Quand je choisis l'onglet « Séquence : Une séquence au nom vraiment beaucoup trop long » dans le menu « Onglets »
		Alors l'onglet ouvert affiche « Séquence : Une séquence au nom vraiment… »

	Scénario: Un onglet fermé quitte le menu « Onglets »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Quarante caractères tout pile »
		Et je ferme l'onglet « Séquence : Quarante caractères tout pile »
		Alors le menu « Onglets » liste :
			| onglet     | raccourci | cochée |
			| Antenne    | Maj+F1    | non    |
			| Calendrier | Maj+F2    | non    |
			| Événements | Maj+F3    | non    |
			| Séquences  | Maj+F4    | non    |
			| Banques    | Maj+F5    | oui    |
			| Incidents  | Maj+F6    | non    |
