# language: fr
Fonctionnalité: Aide propre à l'onglet affiché, en page et en infobulles
	En tant que membre de l'équipe de l'antenne,
	je veux une aide propre à l'onglet affiché, en page et en infobulles,
	afin de comprendre un écran sans quitter mon travail.

	https://github.com/dascritch/machincast/issues/534. Chaque genre d'onglet a sa page d'aide, en Markdown, dans
	doc/fr/utilisateur/aide, illustrée d'une image annotée, doc/fr/captures/aide, que refait Machin dev-screenshots.
	Chaque élément de l'écran y est une ligne numérotée, « 1. **Nom** (`nom_qt`) : ce qu'il fait. », le numéro étant
	celui de l'image. Le menu « Aide » commence par « Aide sur … », qui ouvre la page de l'onglet affiché sur GitHub,
	puis « Aide contextuelle », F1, qui reprend ces lignes en infobulles : survoler un élément décrit montre son aide,
	cliquer dessus la garde ouverte, sans agir.

	Contexte:
		Étant donné l'horloge de l'interface au « 2026-10-21 09:00:00 »

	Scénario: Le menu « Aide » commence par l'aide de l'onglet affiché, puis l'aide contextuelle
		Quand la fenêtre de l'interface s'ouvre
		Alors le menu « Aide » a les entrées :
			| entrée                       | état     | raccourci | infobulle                                                                    |
			| Aide sur l'onglet Antenne    | active   |           |                                                                              |
			| Aide contextuelle            | active   | F1        |                                                                              |
			| — | | | |
			| Documentation                | active   |           |                                                                              |
			| Votre installation…          | active   |           |                                                                              |
			| Lien de l'équipe…            | inactive |           | Adresse à donner dans Fichier → Préférences de l'interface…, page Interface. |
			| Signaler un problème…        | active   |           |                                                                              |
			| Version                      | active   |           |                                                                              |

	Plan du scénario: « Aide sur … » nomme le genre de l'onglet affiché, dont la page décrit les éléments
		Chaque élément nommé par la page se trouve dans l'onglet, par son nom d'objet Qt ou son attribut, et l'image
		annotée de la page existe.

		Quand la fenêtre de l'interface s'ouvre
		Et j'affiche un onglet de genre « <genre> »
		Alors l'entrée « <entrée> » du menu « Aide » est active
		Et la page d'aide « <page> » décrit au moins 3 éléments, tous dans l'onglet affiché
		Et l'image annotée de la page d'aide « <page> » existe

		Exemples:
			| genre         | entrée                                 | page             |
			| on_air        | Aide sur l'onglet Antenne              | antenne          |
			| list:sound    | Aide sur la liste des sonores          | liste-sonores    |
			| list:bank     | Aide sur la liste des banques          | liste-banques    |
			| list:sequence | Aide sur la liste des séquences        | liste-sequences  |
			| list:event    | Aide sur la liste des événements       | liste-evenements |
			| list:feed     | Aide sur la liste des feeds            | liste-feeds      |
			| card:sound    | Aide sur la fiche d'un sonore          | fiche-sonore     |
			| card:bank     | Aide sur la fiche d'une banque         | fiche-banque     |
			| card:sequence | Aide sur la fiche d'une séquence       | fiche-sequence   |
			| card:event    | Aide sur la fiche d'un événement       | fiche-evenement  |
			| card:feed     | Aide sur la fiche d'un feed            | fiche-feed       |
			| calendar      | Aide sur la grille horaire             | grille           |
			| simulation    | Aide sur la simulation                 | simulation       |
			| airplay       | Aide sur l'onglet Airplay              | airplay          |
			| api           | Aide sur l'onglet API                  | api              |
			| search        | Aide sur la recherche                  | recherche        |
			| incidents     | Aide sur l'onglet Incidents            | incidents        |

	Scénario: « Aide sur … » ouvre la page de l'onglet affiché dans le navigateur web
		Étant donné MachinCast installé hors d'un dépôt git
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je choisis « Aide sur la liste des banques » dans le menu « Aide »
		Alors le navigateur web a ouvert « https://github.com/dascritch/machincast/blob/main/doc/fr/utilisateur/aide/liste-banques.md »

	Scénario: F1 active l'aide contextuelle, et l'entrée propose alors de la désactiver
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « F1 »
		Alors l'entrée « Désactiver l'aide contextuelle » du menu « Aide » est active
		Et la barre d'état annonce « Aide contextuelle : survolez ou cliquez un élément de l'onglet pour lire son aide ; F1 pour la quitter. »
		Quand j'appuie sur « F1 »
		Alors l'entrée « Aide contextuelle » du menu « Aide » est active

	Scénario: L'aide contextuelle active, cliquer sur un élément montre son aide, sans agir
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et j'appuie sur « F1 »
		Et je clique sur « Nouvelle banque »
		Alors l'aide contextuelle a montré « Nouvelle banque » : « ouvre une fiche vide ; rien n'est en base avant <b>Enregistrer</b>. »
		Et aucun onglet « Nouvelle banque » n'est ouvert

	Scénario: L'aide contextuelle active, survoler un élément montre son aide en infobulle
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et j'appuie sur « F1 »
		Et je survole le champ « filter_ » de l'onglet affiché
		Alors l'aide contextuelle a montré « Filtrer… » : « ne garde que les lignes dont une colonne contient le texte tapé, sans tenir compte des majuscules ni des accents. »

	Scénario: L'aide contextuelle suit l'onglet affiché
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « F1 »
		Et j'ouvre l'onglet « Incidents »
		Et je survole le champ « information » de l'onglet affiché
		Alors l'aide contextuelle a montré « Montrer aussi les informations » : « ajoute les opérations normales, comme les démarrages, les débuts et fins d'événements, et les interruptions manuelles. »

	Scénario: L'aide contextuelle désactivée, un clic agit comme d'habitude
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et j'appuie sur « F1 »
		Et j'appuie sur « F1 »
		Et je clique sur « Nouvelle banque »
		Alors l'aide contextuelle n'a rien montré
		Et l'onglet « Nouvelle banque » est ouvert
