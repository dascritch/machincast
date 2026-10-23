# language: fr
Fonctionnalité: Dupliquer un événement, une séquence ou une banque
	En tant que programmateur musical,
	je veux dupliquer un élément que j'édite,
	afin d'accélérer mes modifications triviales.

	https://github.com/dascritch/machincast/issues/130, spec § 8.4, § 8.5 et § 8.12. « Dupliquer », dans la fiche d'un
	élément enregistré et non modifié, ou au clic droit sur sa ligne dans sa liste, ouvre une nouvelle fiche
	pré-remplie, au nom interne suivi de « (copie) » ; rien n'entre en base avant « Enregistrer ». La copie d'une
	séquence garde tout ; celle d'un événement, sa priorité, ses noms, son masquage et sa liste de lecture, sans dates
	ni jours ; celle d'une banque, tout sauf sa liste de sonores : ses répertoires la rempliront à la prochaine
	indexation. L'original n'est jamais touché. Un chemin qui commence par « …/ » est dans le répertoire temporaire
	du scénario.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 08:00:00 »
		Et les sonores :
			| artiste     | titre        | type    | etat  | duree | emplacement                 |
			|             | Jingle début | fichier | actif | 5     | /srv/habillage/debut.flac   |
			|             | Jingle fin   | fichier | actif | 4     | /srv/habillage/fin.flac     |
			| Les Gaufres | Spot         | fichier | actif | 30    | /srv/pubs/spot.flac         |
		Et la banque « Publicité », aléatoire, de nom public « Pub », marquée « ne pas répéter », avec « Spot »
		Et les répertoires « …/pubs », « …/annonces » de la banque « Publicité »
		Et la séquence « Passage pub », de nom public « Vous écoutez Radio Thune », avec le sonore « Jingle début », la banque « Publicité », le sonore « Jingle fin »
		Et les événements :
			| nom      | nom_public     | priorite | debut               | fin                 | jours        |
			| Matinale | La matinale    | emission | 2026-10-19 07:00:00 | 2026-10-19 09:00:00 | lundi, mardi |
		Et l'événement « Matinale » masque les métadonnées
		Et l'événement « Matinale » joue la séquence « Passage pub », la banque « Publicité », le sonore « Spot »

	# ─── Séquence ──────────────────────────────────────────────

	Scénario: La copie d'une séquence garde tout, et n'entre en base qu'à l'enregistrement
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Alors le bouton « Dupliquer » de la fiche est actif
		Quand je clique sur « Dupliquer »
		Alors l'onglet ouvert est « Nouvelle séquence, copie de Passage pub »
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents », « Séquence : Passage pub », « Nouvelle séquence, copie de Passage pub »
		Et la fiche montre le nom interne « Passage pub (copie) » et le nom public « Vous écoutez Radio Thune »
		Et la fiche montre les éléments « Jingle début », « Publicité », « Jingle fin »
		Et la fiche ne montre aucun événement où figure la séquence
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs
		Et le bouton « Dupliquer » de la fiche est inactif
		Et le bouton « Supprimer… » de la fiche est inactif
		Et la séquence « Passage pub (copie) » n'est pas en base
		Quand j'enregistre la fiche
		Alors l'onglet ouvert est « Séquence : Passage pub (copie) »
		Et la séquence « Passage pub (copie) » a en base le nom public « Vous écoutez Radio Thune » et les éléments le sonore « Jingle début », la banque « Publicité », le sonore « Jingle fin »
		Et la séquence « Passage pub » a en base le nom public « Vous écoutez Radio Thune » et les éléments le sonore « Jingle début », la banque « Publicité », le sonore « Jingle fin »
		Et le bouton « Dupliquer » de la fiche est actif

	Scénario: Une copie déjà prise donne « (copie 2) », puis « (copie 3) »
		Étant donné la séquence « Passage pub (copie) », sans nom public, avec rien
		Et la séquence « Passage pub (copie 2) », sans nom public, avec rien
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je clique sur « Dupliquer »
		Alors la fiche montre le nom interne « Passage pub (copie 3) » et le nom public « Vous écoutez Radio Thune »

	Scénario: Un nom interne trop long est raccourci pour que sa copie tienne en base
		Étant donné la séquence au nom interne de 255 caractères « a »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Et je choisis « Dupliquer » au clic droit sur la ligne de 255 caractères « a »
		Alors le nom interne de la copie est de 247 caractères « a », suivis de « (copie) »
		Quand j'enregistre la fiche
		Alors la fiche ne signale rien

	Scénario: Annuler une copie revient à la copie, toujours à enregistrer
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je clique sur « Dupliquer »
		Et je saisis le nom public « Autre chose »
		Et je retire les éléments « Jingle fin »
		Et j'annule les modifications de la fiche
		Alors la fiche montre le nom interne « Passage pub (copie) » et le nom public « Vous écoutez Radio Thune »
		Et la fiche montre les éléments « Jingle début », « Publicité », « Jingle fin »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs

	Scénario: Une copie dont l'original est effacé reste telle quelle, et s'enregistre
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je clique sur « Dupliquer »
		Et je saisis le nom public « Autre chose »
		Et la séquence « Passage pub » est effacée de la base
		Et j'annule les modifications de la fiche
		Alors la fiche signale « L'original n'est plus en base : la copie reste telle quelle. »
		Et la fiche montre le nom interne « Passage pub (copie) » et le nom public « Autre chose »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs
		Quand j'enregistre la fiche
		Alors la séquence « Passage pub (copie) » a en base le nom public « Autre chose » et les éléments le sonore « Jingle début », la banque « Publicité », le sonore « Jingle fin »

	Scénario: Fermer une copie sans l'enregistrer ne laisse rien en base
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je clique sur « Dupliquer »
		Et je ferme l'onglet « Nouvelle séquence, copie de Passage pub »
		Et je réponds « Abandonner » à la question de fermeture
		Alors la question de fermeture a nommé « Nouvelle séquence, copie de Passage pub »
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents », « Séquence : Passage pub »
		Et la séquence « Passage pub (copie) » n'est pas en base

	Scénario: Une fiche modifiée, ou pas encore enregistrée, ne se duplique pas
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je saisis le nom public « Radio Thune »
		Alors le bouton « Dupliquer » de la fiche est inactif
		Quand j'annule les modifications de la fiche
		Alors le bouton « Dupliquer » de la fiche est actif
		Quand j'ouvre l'onglet « Séquences »
		Et je clique sur « Nouvelle séquence »
		Alors le bouton « Dupliquer » de la fiche est inactif

	# ─── Événement ─────────────────────────────────────────────

	Scénario: La copie d'un événement garde sa priorité, ses noms, son masquage et sa liste, sans dates ni jours
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je clique sur « Dupliquer »
		Alors l'onglet ouvert est « Nouvel événement, copie de Matinale »
		Et la fiche montre le nom interne « Matinale (copie) » et le nom public « La matinale »
		Et la fiche de l'événement copié montre la priorité « Émission », le masquage « Masqués », ni début, ni fin, ni jours
		Et la fiche montre les éléments « Passage pub », « Publicité », « Les Gaufres – Spot »
		Quand j'enregistre la fiche
		Alors la fiche signale « Une émission ou un spécial a un début. »
		Et l'événement « Matinale (copie) » n'est pas en base
		Quand je donne à l'événement copié le début « 2026-10-21 20:00 »
		Et j'enregistre la fiche
		Alors l'onglet ouvert est « Événement : Matinale (copie) »
		Et l'événement « Matinale (copie) » a en base la priorité « emission », le nom public « La matinale », masqué, le début « 2026-10-21 20:00 », sans fin ni jours
		Et l'événement « Matinale (copie) » a en base les éléments la séquence « Passage pub », la banque « Publicité », le sonore « Spot »
		Et l'événement « Matinale » a en base la priorité « emission », le nom public « La matinale », masqué, le début « 2026-10-19 07:00 », la fin « 2026-10-19 09:00 », les jours « lundi, mardi »
		Et l'événement « Matinale » a en base les éléments la séquence « Passage pub », la banque « Publicité », le sonore « Spot »

	# ─── Banque ────────────────────────────────────────────────

	Scénario: La copie d'une banque garde ses réglages et ses répertoires, sans ses sonores
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Publicité »
		Et je clique sur « Dupliquer »
		Alors l'onglet ouvert est « Nouvelle banque, copie de Publicité »
		Et la fiche montre le nom interne « Publicité (copie) » et le nom public « Pub »
		Et la fiche de la banque copiée montre le mode « Aléatoire », « ne pas répéter » coché, les répertoires « …/annonces », « …/pubs », et aucun sonore
		Quand j'enregistre la fiche
		Alors l'onglet ouvert est « Banque : Publicité (copie) »
		Et la banque « Publicité (copie) » a en base le nom public « Pub », le mode « aleatoire », « ne pas répéter », les répertoires « …/annonces », « …/pubs » et les sonores aucun
		Et la banque « Publicité » a en base le nom public « Pub », le mode « aleatoire », « ne pas répéter », les répertoires « …/annonces », « …/pubs » et les sonores « Spot »

	# ─── Listes ────────────────────────────────────────────────

	Plan du scénario: Le clic droit sur une ligne de liste duplique son élément
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « <onglet> »
		Et je choisis « Dupliquer » au clic droit sur la ligne « <nom> »
		Alors l'onglet ouvert est « <titre> »
		Et la fiche montre le nom interne « <copie> » et le nom public « <nom public> »

		Exemples:
			| onglet      | nom         | titre                                     | copie               | nom public               |
			| Événements  | Matinale    | Nouvel événement, copie de Matinale       | Matinale (copie)    | La matinale              |
			| Séquences   | Passage pub | Nouvelle séquence, copie de Passage pub   | Passage pub (copie) | Vous écoutez Radio Thune |
			| Banques     | Publicité   | Nouvelle banque, copie de Publicité       | Publicité (copie)   | Pub                      |

	Scénario: Seules les listes des événements, des séquences et des banques proposent de dupliquer
		Étant donné les feeds « Relais », « https://flux.exemple/relais »
		Quand la fenêtre de l'interface s'ouvre
		Alors les listes qui proposent de dupliquer au clic droit sont « Événements », « Séquences », « Banques »
