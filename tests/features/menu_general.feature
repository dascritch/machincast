# language: fr
Fonctionnalité: Menu général de l'interface
	En tant que technicien radio,
	je veux un menu général,
	afin d'accéder rapidement aux fonctions de maintenance de l'interface.

	https://github.com/dascritch/machincast/issues/117, spec § 8.11. La barre de menus a cinq menus : « Fichier »,
	« Affichage » (rafraichissement.feature), « Diffusion » (pilotage.feature), « Maintenance » et « Aide ». Une fonction pas encore écrite a son entrée, inactive, dont l'infobulle donne le ticket
	qui l'apportera. « Version » donne la date du dernier commit du dépôt git d'où MachinCast est installé ; dans les
	textes attendus, « <version> » est le numéro de version de MachinCast. L'indexation lancée depuis « Maintenance » a ses propres scénarios (indexation_interface.feature).

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 21:30:00 »
		Et les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Et la banque « Jingles », séquentielle, sans nom public, avec aucun

	Scénario: La barre de menus a les menus « Fichier », « Affichage », « Diffusion », « Maintenance » et « Aide »
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre de menus a les menus « Fichier », « Affichage », « Diffusion », « Maintenance », « Aide »
		Et le menu « Fichier » a les entrées :
			| entrée       | état     | raccourci | infobulle                               |
			| Préférences… | active   |           |                                         |
			| —            |          |           |                                         |
			| Quitter      | active   | Alt+Q     |                                         |
		Et le menu « Maintenance » a les entrées :
			| entrée                 | état     | raccourci | infobulle                      |
			| Moniteur de la sortie… | inactive |           | À venir : ticket 85 sur GitHub |
			| —                      |          |           |                                |
			| Indexation rapide      | active   |           |                                |
			| Audit complet          | active   |           |                                |
		Et le menu « Aide » a les entrées :
			| entrée                | état   | raccourci | infobulle |
			| Documentation         | active |           |           |
			| Signaler un problème… | active |           |           |
			| Version               | active |           |           |

	Scénario: « Documentation » ouvre le guide d'utilisation dans le navigateur web
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Documentation » dans le menu « Aide »
		Alors le navigateur web a ouvert « https://github.com/dascritch/machincast/blob/main/doc/utilisation.md »
		Et la fenêtre de l'interface est ouverte

	Scénario: « Signaler un problème… » ouvre les tickets de MachinCast dans le navigateur web
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Signaler un problème… » dans le menu « Aide »
		Alors le navigateur web a ouvert « https://github.com/dascritch/machincast/issues »
		Et la fenêtre de l'interface est ouverte

	Scénario: « Version » donne la version de MachinCast et la date de sa dernière modification
		Étant donné MachinCast installé depuis un dépôt git dont le dernier commit date du « 2026-10-18 12:05:00+00:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Version » dans le menu « Aide »
		# À l'heure du poste : Paris est alors à UTC+2.
		Alors la fenêtre de version a dit « MachinCast <version>, dernière modification le 2026-10-18 à 14:05. »

	Scénario: Par défaut, « Version » lit le dépôt d'où MachinCast est installé
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Version » dans le menu « Aide »
		Alors la fenêtre de version donne la date du dernier commit du dépôt de MachinCast

	Plan du scénario: « Version » le dit, quand la date de la dernière modification est introuvable
		Étant donné MachinCast installé <installation>
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Version » dans le menu « Aide »
		Alors la fenêtre de version a dit « MachinCast <version>, date de dernière modification inconnue : l'installation n'est pas un dépôt git. »

		Exemples:
			| installation                     |
			| hors d'un dépôt git              |
			| dans un dossier d'un autre dépôt |
			| depuis un dépôt git illisible    |
			| depuis un dépôt git, sans git    |

	Scénario: « Quitter » ferme la fenêtre de l'interface
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Quitter » dans le menu « Fichier »
		Alors la fenêtre de l'interface est fermée

	Scénario: Alt+Q quitte aussi, même depuis une fiche ouverte
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'appuie sur « Alt+Q »
		Alors la fenêtre de l'interface est fermée
		Et aucune question n'a été posée

	Plan du scénario: Quitter demande quoi faire des fiches modifiées, comme la fermeture de la fenêtre
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et je saisis le nom interne « Jingles du soir »
		Et je réponds « <reponse> » à la question de fermeture
		Et je choisis « Quitter » dans le menu « Fichier »
		Alors la question de fermeture a nommé « Banque : Jingles »
		Et la fenêtre de l'interface est <etat>

		Exemples:
			| reponse    | etat    |
			| Abandonner | fermée  |
			| Annuler    | ouverte |
