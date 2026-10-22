# language: fr
Fonctionnalité: Pré-écoute d'un sonore depuis le menu contextuel de sa ligne
	En tant que technicien radio,
	je veux lancer la pré-écoute d'un sonore depuis le menu contextuel de sa ligne, partout où des sonores sont listés,
	afin de l'écouter sans ouvrir sa fiche.

	https://github.com/dascritch/machincast/issues/226. Un clic droit sur la ligne d'un sonore propose « Pré-écoute… »,
	en tête du menu : dans l'airplay de l'accueil, dans la liste des sonores, dans les éléments d'une séquence (et d'un
	événement, qui partagent la même liste) et dans les sonores d'une banque. L'entrée charge le sonore dans la fenêtre
	de pré-écoute, comme le bouton de sa fiche : la même fenêtre, à l'arrêt. Une ligne qui ne désigne pas de sonore en
	base n'a pas cette entrée.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-20 19:10:00 »
		Et les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement                  |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/musique/cafe.flac       |
			|             | Jingle        | fichier | actif | 5     | /srv/habillage/jingle.flac   |
		Et la banque « Habillage », séquentielle, sans nom public, avec « Jingle », « Café à minuit »

	# ─── Liste des sonores ─────────────────────────────────────

	Scénario: La liste des sonores propose la pré-écoute en tête du menu de la ligne
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ouvre le menu contextuel de la ligne « Café à minuit » de la liste
		Alors le menu contextuel commence par « Pré-écoute… », puis un séparateur
		Et le menu contextuel propose toujours « Demander un audit complet »
		Quand je choisis « Pré-écoute… » dans le menu contextuel
		Alors la fenêtre de pré-écoute est ouverte, titrée « Pré-écoute : Les Gaufres – Café à minuit »
		Et la pré-écoute est « À l'arrêt »

	Scénario: Avec plusieurs sonores sélectionnés, la pré-écoute est celle de la ligne cliquée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je sélectionne les lignes « Café à minuit » et « Jingle » de la liste
		Et j'ouvre le menu contextuel de la ligne « Jingle » de la liste
		Et je choisis « Pré-écoute… » dans le menu contextuel
		Alors la fenêtre de pré-écoute est ouverte, titrée « Pré-écoute : Jingle »

	Scénario: La liste des banques ne propose pas de pré-écoute
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et j'ouvre le menu contextuel de la ligne « Habillage » de la liste
		Alors le menu contextuel ne propose pas « Pré-écoute… »

	# ─── Airplay ───────────────────────────────────────────────

	Scénario: Une ligne de l'airplay propose la pré-écoute de son sonore
		Étant donné « Café à minuit » passé à l'antenne à 19:02
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre le menu contextuel de la ligne « Café à minuit » de l'airplay
		Alors le menu contextuel commence par « Pré-écoute… »
		Quand je choisis « Pré-écoute… » dans le menu contextuel
		Alors la fenêtre de pré-écoute est ouverte, titrée « Pré-écoute : Les Gaufres – Café à minuit »

	Scénario: Une ligne de l'airplay dont le sonore a été supprimé depuis n'a pas de menu
		Étant donné « Ancien titre » passé à l'antenne à 19:02, son sonore supprimé depuis
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre le menu contextuel de la ligne « Ancien titre » de l'airplay
		Alors il n'y a pas de menu contextuel

	# ─── Séquence et événement ─────────────────────────────────

	Scénario: Dans une séquence, la ligne d'un sonore propose sa pré-écoute, pas celle d'une banque
		Étant donné la séquence « Ouverture », sans nom public, avec le sonore « Café à minuit », la banque « Habillage »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Ouverture »
		Et j'ouvre le menu contextuel de la ligne « Habillage » des éléments
		Alors il n'y a pas de menu contextuel
		Quand j'ouvre le menu contextuel de la ligne « Café à minuit » des éléments
		Alors le menu contextuel commence par « Pré-écoute… »
		Quand je choisis « Pré-écoute… » dans le menu contextuel
		Alors la fenêtre de pré-écoute est ouverte, titrée « Pré-écoute : Les Gaufres – Café à minuit »

	Scénario: Dans un événement, la ligne d'un sonore propose aussi sa pré-écoute
		Étant donné les événements :
			| nom      | nom_public  | priorite | debut               | fin                 | jours        |
			| Matinale | La matinale | emission | 2026-10-19 07:00:00 | 2026-10-19 09:00:00 | lundi, mardi |
		Et l'événement « Matinale » joue le sonore « Jingle »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et j'ouvre le menu contextuel de la ligne « Jingle » des éléments
		Et je choisis « Pré-écoute… » dans le menu contextuel
		Alors la fenêtre de pré-écoute est ouverte, titrée « Pré-écoute : Jingle »

	# ─── Banque ────────────────────────────────────────────────

	Scénario: Dans une banque, la ligne d'un sonore propose sa pré-écoute, avant le choix de son état
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Habillage »
		Et j'ouvre le menu contextuel de la ligne « Café à minuit » des sonores de la banque
		Alors le menu contextuel commence par « Pré-écoute… », puis un séparateur
		Et le menu contextuel propose toujours « Activer »
		Quand je choisis « Pré-écoute… » dans le menu contextuel
		Alors la fenêtre de pré-écoute est ouverte, titrée « Pré-écoute : Les Gaufres – Café à minuit »

	Scénario: Un fichier déposé dans une banque, pas encore enregistré, n'a pas de pré-écoute
		Étant donné les fichiers « …/nouveau.ogg » du scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Habillage »
		Et je dépose « …/nouveau.ogg » sur les sonores de la banque
		Et j'ouvre le menu contextuel de la ligne « nouveau.ogg » des sonores de la banque
		Alors le menu contextuel ne propose pas « Pré-écoute… »
