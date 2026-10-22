# language: fr
Fonctionnalité: Rafraîchir les onglets de l'interface
	En tant que programmateur radio,
	je veux rafraîchir les informations de tous les onglets,
	afin d'avoir à jour ce que d'autres postes, l'indexation et la diffusion ont changé en base.

	https://github.com/dascritch/machincast/issues/148, spec § 8.11. « Rafraîchir les onglets », dans le menu
	« Affichage » ou par F5, relit l'onglet ouvert, l'airplay de l'accueil et toutes les fiches ouvertes ; les autres
	listes se relisent déjà à l'ouverture de leur onglet. Une fiche modifiée demande d'abord quoi faire de ses
	modifications, comme à sa fermeture. Passer à un onglet le relit aussi, s'il n'est pas en cours d'édition
	(https://github.com/dascritch/machincast/issues/241) : une fiche modifiée, ou pas encore enregistrée, reste telle
	quelle, sans question. Les changements faits « par un autre poste » sont écrits directement en base.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 21:45:00 »
		Et les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Et les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement         |
			| Les Gaufres | Café à minuit | fichier | actif | 180   | /musique/cafe.flac  |
		Et la banque « Jingles », séquentielle, sans nom public, avec « Café à minuit »

	Scénario: « Rafraîchir les onglets » est dans le menu « Affichage », avec le raccourci F5
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre de menus a les menus « Fichier », « Affichage », « Diffusion », « Maintenance », « Aide »
		Et le menu « Affichage » a les entrées :
			| entrée                 | état   | raccourci | infobulle |
			| Rafraîchir les onglets | active | F5        |           |
			| Rechercher…            | active | Ctrl+F    |           |
			| Ouvrir l'onglet Sonores        | active |           |           |
			| Ouvrir l'onglet Marques-pages  | active |           |           |
			| Ouvrir l'onglet Grille horaire | active |           |           |
			| Ouvrir l'onglet Simulation     | active |           |           |
			| Ouvrir l'onglet Airplay        | active |           |           |
			| Pré-écoute…            | active |           |           |

	Scénario: La liste ouverte se relit
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et un autre poste ajoute la banque « Publicité »
		Alors le compte de la liste est « 1 banque »
		Quand j'appuie sur « F5 »
		Alors le compte de la liste est « 2 banques »
		Et la barre d'état annonce « Onglets rafraîchis. »

	Scénario: L'airplay de l'accueil se relit
		Quand la fenêtre de l'interface s'ouvre
		Et la diffusion note dans l'airplay le passage de « Café à minuit » à 21:40
		Alors l'airplay de l'accueil ne montre rien
		Quand je choisis « Rafraîchir les onglets » dans le menu « Affichage »
		Alors l'airplay de l'accueil montre « Café à minuit »

	Scénario: Un double-clic dans l'airplay relu ouvre la fiche du sonore
		https://github.com/dascritch/machincast/issues/144

		Quand la fenêtre de l'interface s'ouvre
		Et la diffusion note dans l'airplay le passage de « Café à minuit » à 21:40
		Et j'appuie sur « F5 »
		Et je double-clique sur « Café à minuit » dans l'airplay de l'accueil
		Alors l'onglet ouvert est « Sonore : Café à minuit »

	Scénario: Une fiche ouverte, qui n'est pas modifiée, se relit sans rien demander
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et un autre poste renomme la banque « Jingles » en « Jingles du matin »
		Et j'appuie sur « F5 »
		Alors aucune question n'a été posée
		Et l'onglet ouvert est « Banque : Jingles du matin »

	Plan du scénario: Une fiche modifiée demande d'abord quoi faire de ses modifications
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne « Jingles du soir »
		Et un autre poste renomme la banque « Jingles » en « Jingles du matin »
		Et je réponds « <reponse> » à la question de rafraîchissement
		Et j'appuie sur « F5 »
		Alors la question de rafraîchissement a nommé « Banque : Jingles »
		Et l'onglet ouvert est « Banque : <nom> »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont <boutons>
		Et la barre d'état annonce « <annonce> »

		Exemples:
			| reponse     | nom              | boutons  | annonce                                                                 |
			| Enregistrer | Jingles du soir  | inactifs | Onglets rafraîchis.                                                     |
			| Abandonner  | Jingles du matin | inactifs | Onglets rafraîchis.                                                     |
			| Annuler     | Jingles          | actifs   | Onglets rafraîchis. Fiches laissées telles quelles : « Banque : Jingles ». |

	Scénario: Une fiche modifiée qui ne s'enregistre pas reste telle quelle, et dit pourquoi
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne «  »
		Et je réponds « Enregistrer » à la question de rafraîchissement
		Et j'appuie sur « F5 »
		Alors la fiche signale « Le nom interne est obligatoire. »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs
		Et la barre d'état annonce « Onglets rafraîchis. Fiches laissées telles quelles : « Banque : Jingles ». »

	Scénario: La fiche d'un élément effacé de la base par un autre poste se ferme
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne « Jingles du soir »
		Et un autre poste efface la banque « Jingles »
		Et j'appuie sur « F5 »
		Alors aucune question n'a été posée
		Et la fenêtre n'a plus d'onglet de fiche
		Et la barre d'état annonce « Onglets rafraîchis. Fiches fermées, leur élément n'est plus en base : « Banque : Jingles ». »

	Scénario: Une nouvelle fiche, pas encore enregistrée, reste vide
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je clique sur « Nouvelle banque »
		Et j'appuie sur « F5 »
		Alors l'onglet ouvert est « Nouvelle banque »
		Et aucune question n'a été posée

	# ─── À l'ouverture d'un onglet (https://github.com/dascritch/machincast/issues/241) ─────

	Scénario: Revenir à l'onglet d'une fiche qui n'est pas modifiée la relit, sans rien demander
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ouvre l'onglet « Accueil »
		Et un autre poste renomme la banque « Jingles » en « Jingles du matin »
		Et j'ouvre l'onglet « Banque : Jingles »
		Alors aucune question n'a été posée
		Et l'onglet ouvert est « Banque : Jingles du matin »
		Et le nom interne de la fiche est « Jingles du matin »

	Scénario: Revenir à l'onglet d'une fiche en cours d'édition la laisse telle quelle, sans rien demander
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne « Jingles du soir »
		Et j'ouvre l'onglet « Accueil »
		Et un autre poste renomme la banque « Jingles » en « Jingles du matin »
		Et j'ouvre l'onglet « Banque : Jingles »
		Alors aucune question n'a été posée
		Et le nom interne de la fiche est « Jingles du soir »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs

	Scénario: Revenir à l'onglet d'une fiche dont l'élément a été effacé par un autre poste la ferme
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ouvre l'onglet « Accueil »
		Et un autre poste efface la banque « Jingles »
		Et j'ouvre l'onglet « Banque : Jingles »
		Alors aucune question n'a été posée
		Et la fenêtre n'a plus d'onglet de fiche
		Et la barre d'état annonce « Fiche fermée, son élément n'est plus en base : « Banque : Jingles ». »

	Scénario: Revenir à l'accueil relit son airplay
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et la diffusion note dans l'airplay le passage de « Café à minuit » à 21:40
		Et j'ouvre l'onglet « Accueil »
		Alors l'airplay de l'accueil montre « Café à minuit »

	Scénario: Revenir à une nouvelle fiche, pas encore enregistrée, la laisse telle quelle
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je clique sur « Nouvelle banque »
		Et je saisis le nom interne « Publicité »
		Et j'ouvre l'onglet « Accueil »
		Et j'ouvre l'onglet « Nouvelle banque »
		Alors le nom interne de la fiche est « Publicité »
		Et aucune question n'a été posée
