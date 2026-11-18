# language: fr
Fonctionnalité: Copier et coller les éléments ou les sonores d'une liste, d'une fiche à l'autre
	En tant que programmateur musical,
	je veux sélectionner et copier plusieurs lignes à la fois d'une table,
	afin de les coller dans une table de même catégorie.

	https://github.com/dascritch/machincast/issues/129. La liste des éléments d'un événement et celle d'une séquence
	se choisissent ligne à ligne, ou plusieurs à la fois (Ctrl, Maj). Ctrl+C, ou « Copier » au clic droit, copie les
	lignes choisies, dans leur ordre ; Ctrl+V, ou « Coller », les ajoute après la ligne courante, ou en fin de liste
	sans ligne courante, dans la même fiche ou dans une autre, d'un événement ou d'une séquence. Une séquence ne
	contient pas de séquence : une séquence collée dans une séquence est laissée de côté, et la fiche le dit. Rien
	n'est en base avant « Enregistrer ».

	Les sonores d'une banque se copient et se collent de même, d'une banque à l'autre, ou avec les éléments d'un
	événement ou d'une séquence. Une banque ne contient que des sonores, chacun une fois : une banque ou une séquence
	collée dans une banque est laissée de côté, un sonore déjà dans la banque n'est pas collé une seconde fois, et la
	fiche le dit. En mode séquentiel, les sonores collés vont après la ligne courante ; en aléatoire, en fin de liste.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-11-18 10:30:00 »
		Et les sonores :
			| artist      | title        | type | state  | duration | location                  |
			|             | Jingle début | file | active | 5        | /srv/habillage/debut.flac |
			|             | Jingle fin   | file | active | 4        | /srv/habillage/fin.flac   |
			| Les Gaufres | Spot         | file | active | 30       | /srv/pubs/spot.flac       |
		Et la banque « Publicité », aléatoire, sans nom public, avec « Spot »
		Et la banque « Habillage », séquentielle, sans nom public, avec « Jingle début », « Jingle fin »
		Et la séquence « Passage pub », sans nom public, avec le sonore « Jingle début », la banque « Publicité », le sonore « Jingle fin »
		Et les événements :
			| name     | public_name | priority               | starts_at        | ends_at          | days   |
			| Continue |             | background_programming |                  |                  |        |
			| Matinale |             | show                   | 2026-11-19 07:00 | 2026-11-19 09:00 | monday |
			| Midi     |             | show                   | 2026-11-19 12:00 | 2026-11-19 13:00 | monday |
		Et l'événement « Matinale » joue la banque « Habillage », la séquence « Passage pub », le sonore « Spot », la banque « Publicité »
		Et l'événement « Midi » joue le sonore « Jingle fin »

	Scénario: Des lignes contiguës d'un événement se collent dans un autre événement, après sa ligne courante
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je choisis les éléments n° 2 à 3 de la liste
		Et je copie les éléments choisis
		Et j'ouvre la fiche de l'événement « Midi »
		Et je choisis les éléments n° 1 à 1 de la liste
		Et je colle les éléments
		Alors la liste de la fiche montre les éléments « Jingle fin », « Passage pub », « Les Gaufres – Spot »
		Et les lignes choisies de la liste sont « Passage pub », « Les Gaufres – Spot »
		Quand j'enregistre la fiche
		Alors les éléments de l'événement « Midi » sont, dans l'ordre, le sonore « Jingle fin », la séquence « Passage pub », le sonore « Spot »

	Scénario: Sans ligne courante, les éléments se collent en fin de liste ; coller deux fois les ajoute deux fois
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je choisis les éléments n° 1 à 1 de la liste
		Et je copie les éléments choisis
		Et j'ouvre la fiche de l'événement « Midi »
		Et je colle les éléments
		Et je colle les éléments
		Alors la liste de la fiche montre les éléments « Jingle fin », « Habillage », « Habillage »

	Scénario: Le clic droit propose « Copier » et « Coller », dans la même fiche
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je choisis les éléments n° 3 à 4 de la liste
		Et je choisis « Copier » au clic droit sur l'élément n° 3 de la liste
		Et je choisis les éléments n° 1 à 1 de la liste
		Et je choisis « Coller » au clic droit sur l'élément n° 1 de la liste
		Alors la liste de la fiche montre les éléments « Habillage », « Les Gaufres – Spot », « Publicité », « Passage pub », « Les Gaufres – Spot », « Publicité »

	Scénario: Une séquence collée dans une séquence est laissée de côté, et la fiche le dit
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je choisis les éléments n° 1 à 3 de la liste
		Et je copie les éléments choisis
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je colle les éléments
		Alors la liste de la fiche montre les éléments « Jingle début », « Publicité », « Jingle fin », « Habillage », « Les Gaufres – Spot »
		Et la fiche dit « Laissé de côté, une séquence ne contient pas de séquence : Passage pub. »

	Scénario: Des éléments d'une séquence se collent dans un événement
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je choisis les éléments n° 1 à 3 de la liste
		Et je copie les éléments choisis
		Et j'ouvre la fiche de l'événement « Midi »
		Et je colle les éléments
		Alors la liste de la fiche montre les éléments « Jingle fin », « Jingle début », « Publicité », « Jingle fin »

	Scénario: Un élément effacé de la base depuis la copie n'est pas collé
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je choisis les éléments n° 3 à 4 de la liste
		Et je copie les éléments choisis
		Et la banque « Publicité » est effacée de la base
		Et j'ouvre la fiche de l'événement « Midi »
		Et je colle les éléments
		Alors la liste de la fiche montre les éléments « Jingle fin », « Les Gaufres – Spot »

	Scénario: Rien de copié : « Coller » est inactif ; aucune ligne choisie : « Copier » l'est
		Étant donné un presse-papiers vide
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Midi »
		Alors le clic droit hors des lignes de la liste propose « Copier » inactif et « Coller » inactif
		Quand je choisis les éléments n° 1 à 1 de la liste
		Et je copie les éléments choisis
		Alors le clic droit hors des lignes de la liste propose « Copier » actif et « Coller » actif

	Scénario: Les lignes copiées passent aussi en texte, pour un tableur ou un message
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je choisis les éléments n° 3 à 4 de la liste
		Et je copie les éléments choisis
		Alors le presse-papiers contient le texte :
			"""
			sonore	Les Gaufres – Spot	/srv/pubs/spot.flac
			banque	Publicité	aléatoire
			"""

	# ─── Les sonores d'une banque ──────────────────────────────

	Scénario: Les sonores d'un événement se collent dans une banque séquentielle, après sa ligne courante
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je choisis les éléments n° 1 à 4 de la liste
		Et je copie les éléments choisis
		Et j'ouvre la fiche de la banque « Habillage »
		Et je choisis les éléments n° 1 à 1 de la liste
		Et je colle les éléments
		Alors la liste de la fiche montre les éléments « Jingle début », « Les Gaufres – Spot », « Jingle fin »
		Et les lignes choisies de la liste sont « Les Gaufres – Spot »
		Et la fiche dit « Laissé de côté, une banque ne contient que des sonores : Habillage, Passage pub, Publicité. »
		Quand j'enregistre la fiche
		Alors les sonores de la banque « Habillage » sont, dans l'ordre, « Jingle début », « Spot », « Jingle fin »

	Scénario: Les sonores d'une banque se collent dans une autre, une fois chacun
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Habillage »
		Et je choisis les éléments n° 1 à 2 de la liste
		Et je copie les éléments choisis
		Et j'ouvre la fiche de la banque « Publicité »
		Et je colle les éléments
		Alors la liste de la fiche montre les éléments « Les Gaufres – Spot », « Jingle début », « Jingle fin »
		Et les lignes choisies de la liste sont « Jingle début », « Jingle fin »
		Quand je colle les éléments
		Alors la liste de la fiche montre les éléments « Les Gaufres – Spot », « Jingle début », « Jingle fin »
		Et la fiche dit « Déjà dans la banque, pas collé une seconde fois : Jingle début, Jingle fin. »
		Quand j'enregistre la fiche
		Alors les sonores de la banque « Publicité » sont, dans l'ordre, « Spot », « Jingle début », « Jingle fin »

	Scénario: Ctrl+C et Ctrl+V copient les sonores d'une banque vers un événement
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Habillage »
		Et je choisis les éléments n° 1 à 2 de la liste
		Et j'appuie sur Ctrl+C dans la liste
		Et j'ouvre la fiche de l'événement « Midi »
		Et j'appuie sur Ctrl+V dans la liste
		Alors la liste de la fiche montre les éléments « Jingle fin », « Jingle début », « Jingle fin »

	Scénario: Le clic droit sur un sonore de la banque propose aussi « Copier » et « Coller »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Habillage »
		Et je choisis les éléments n° 2 à 2 de la liste
		Et je choisis « Copier » au clic droit sur l'élément n° 2 de la liste
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je choisis les éléments n° 1 à 1 de la liste
		Et je choisis « Coller » au clic droit sur l'élément n° 1 de la liste
		Alors la liste de la fiche montre les éléments « Jingle début », « Jingle fin », « Publicité », « Jingle fin »

	Scénario: Les sonores copiés d'une banque passent aussi en texte
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Publicité »
		Et je choisis les éléments n° 1 à 1 de la liste
		Et je copie les éléments choisis
		Alors le presse-papiers contient le texte :
			"""
			Les Gaufres – Spot	0:30	actif	/srv/pubs/spot.flac
			"""
