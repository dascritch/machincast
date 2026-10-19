# language: fr
Fonctionnalité: Marques-pages de streams
	En tant que programmateur de l'antenne,
	je veux enregistrer et modifier des adresses de streams réutilisables,
	afin qu'un même flux intermittent serve à plusieurs sonores.

	https://github.com/dascritch/machincast/issues/34, spec § 3.1 et § 8.13. Les marques-pages ont leur onglet, avec
	leur liste ; chacun a sa fiche, qui s'ouvre dans un onglet qui se ferme, comme celle d'une banque
	(fiche_banque.feature, qui vérifie aussi l'enregistrement, l'annulation et la fermeture, communs aux fiches). Un
	marque-page que suit un stream ne se supprime pas.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 20:00:00 »
		Et les marques-pages « Radio Machin » à « https://machin.exemple/live », « Radio Bidule » à « https://bidule.exemple/live »
		Et les sonores :
			| artiste | titre       | type   | etat  | duree | emplacement             |
			|         | Machin nuit | stream | actif |       | https://flux.exemple/b  |
			|         | Machin soir | stream | actif |       | https://flux.exemple/a  |
			|         | Machin aube | stream | actif |       | https://flux.exemple/c  |
		Et les streams « Machin soir », « Machin nuit » suivent le marque-page « Radio Machin »
		Et le stream « Machin aube » suit le marque-page « Radio Bidule »

	# ─── Liste ─────────────────────────────────────────────────

	Scénario: Les marques-pages ont leur liste, avec le nombre de streams qui suivent chacun
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Marques-pages »
		Alors la liste montre :
			| Nom          | Adresse                     | Streams |
			| Radio Bidule | https://bidule.exemple/live | 1       |
			| Radio Machin | https://machin.exemple/live | 2       |
		Et le compte de la liste est « 2 marques-pages »
		Quand je tape « machin » dans le filtre de la liste
		Alors le compte de la liste est « 1 marque-page sur 2 »

	# ─── Fiche ─────────────────────────────────────────────────

	Scénario: La fiche d'un marque-page s'ouvre depuis sa liste, et montre les streams qui le suivent
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Marques-pages »
		Et j'ouvre la ligne « Radio Machin »
		Alors l'onglet ouvert est « Marque-page : Radio Machin »
		Et l'écran de détail de marque-page « Radio Machin » est demandé
		Et la fiche du marque-page montre le nom « Radio Machin » et l'adresse « https://machin.exemple/live »
		Et la fiche du marque-page montre les streams « Machin nuit », « Machin soir »
		Quand j'ouvre le stream « Machin soir » du marque-page
		Alors l'onglet ouvert est « Sonore : Machin soir »

	Scénario: Un nouveau marque-page se crée depuis sa liste
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Marques-pages »
		Et je clique sur « Nouveau marque-page »
		Alors l'onglet ouvert est « Nouveau marque-page »
		Et la fiche du marque-page montre le nom «  » et l'adresse «  »
		Et la fiche du marque-page montre les streams aucun
		Et le bouton « Supprimer… » de la fiche est inactif
		Quand je saisis le nom du marque-page «  Radio Truc  »
		Et je saisis l'adresse du marque-page «  https://truc.exemple/live  »
		Et j'enregistre la fiche
		Alors le marque-page « Radio Truc » est en base, à l'adresse « https://truc.exemple/live »
		Et l'onglet ouvert est « Marque-page : Radio Truc »
		Quand j'ouvre l'onglet « Marques-pages »
		Alors la liste montre :
			| Nom          | Adresse                     | Streams |
			| Radio Bidule | https://bidule.exemple/live | 1       |
			| Radio Machin | https://machin.exemple/live | 2       |
			| Radio Truc   | https://truc.exemple/live   | 0       |

	Scénario: Une nouvelle adresse vaut pour tous les streams qui suivent le marque-page
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Marques-pages »
		Et j'ouvre la ligne « Radio Machin »
		Et je saisis l'adresse du marque-page « https://machin.exemple/nouveau »
		Et j'enregistre la fiche
		Alors le marque-page « Radio Machin » est en base, à l'adresse « https://machin.exemple/nouveau »
		Et le stream « Machin soir » joue l'adresse « https://machin.exemple/nouveau »
		Et la fiche du marque-page montre les streams « Machin nuit », « Machin soir »

	Plan du scénario: Un marque-page invalide n'est pas enregistré, et dit pourquoi
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Marques-pages »
		Et j'ouvre la ligne « Radio Machin »
		Et je saisis le nom du marque-page « <nom> »
		Et je saisis l'adresse du marque-page « <adresse> »
		Et j'enregistre la fiche
		Alors la fiche signale « <message> »
		Et le marque-page « Radio Machin » est en base, à l'adresse « https://machin.exemple/live »

		Exemples:
			| nom          | adresse                     | message                                            |
			|              | https://machin.exemple/live | Le nom est obligatoire.                            |
			| Radio Bidule | https://machin.exemple/live | Un autre marque-page s'appelle déjà « Radio Bidule ». |
			| Radio Machin |                             | L'adresse est obligatoire.                         |

	Plan du scénario: Toute modification rend « Enregistrer » et « Annuler » actifs
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Marques-pages »
		Et j'ouvre la ligne « Radio Machin »
		Et je saisis <champ> du marque-page « Autre »
		Alors les boutons « Enregistrer » et « Annuler » de la fiche sont actifs

		Exemples:
			| champ      |
			| le nom     |
			| l'adresse  |

	# ─── Test du flux ──────────────────────────────────────────

	Plan du scénario: Le test du flux dit s'il répond, sans attendre l'enregistrement
		Étant donné un serveur de flux local, avec le flux « direct » en ligne
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Marques-pages »
		Et j'ouvre la ligne « Radio Bidule »
		Et je saisis l'adresse du flux « <flux> » du serveur local dans la fiche du marque-page
		Et je teste le flux du marque-page
		Alors le test du flux du marque-page dit bientôt <verdict>

		Exemples:
			| flux   | verdict                                  |
			| direct | « Le flux répond : du son arrive. »      |
			| muet   | qu'il ne répond pas                      |

	Scénario: Fermer la fiche arrête le test en cours
		Étant donné un serveur de flux local, avec le flux « direct » en ligne
		Et le flux « direct » du serveur local est avare
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Marques-pages »
		Et j'ouvre la ligne « Radio Bidule »
		Et je saisis l'adresse du flux « direct » du serveur local dans la fiche du marque-page
		Et je teste le flux du marque-page
		Et le serveur de flux local a bientôt 1 connexion
		Et je ferme l'onglet « Marque-page : Radio Bidule »
		Alors le serveur de flux local n'a bientôt plus de connexion

	# ─── Suppression ───────────────────────────────────────────

	Scénario: Un marque-page qu'aucun stream ne suit se supprime, après confirmation
		Étant donné le stream « Machin aube » suit le marque-page « Radio Machin »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Marques-pages »
		Et j'ouvre la ligne « Radio Bidule »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la question de suppression, intitulée « Supprimer le marque-page », a dit :
			| texte                                                  |
			| Supprimer de la base le marque-page « Radio Bidule » ? |
			| Aucun stream ne le suit.                               |
		Et le marque-page « Radio Bidule » n'est plus en base
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Marques-pages »

	Scénario: Un stream qui suit un marque-page se supprime, lui
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Machin soir »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors le sonore « Machin soir » n'est plus en base
		Et le marque-page « Radio Machin » est toujours en base

	Scénario: Un marque-page que suit un stream ne se supprime pas, et la fiche dit pourquoi
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Marques-pages »
		Et j'ouvre la ligne « Radio Machin »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors aucune question n'a été posée
		Et la fiche signale « Les streams « Machin nuit », « Machin soir » suivent ce marque-page : choisir pour eux une autre adresse avant de le supprimer. »
		Et le marque-page « Radio Machin » est toujours en base
		Et l'onglet ouvert est « Marque-page : Radio Machin »
