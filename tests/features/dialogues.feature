# language: fr
Fonctionnalité: Fenêtres de dialogue des fiches
	En tant que programmateur de l'antenne,
	je veux que les fiches me posent leurs questions dans des fenêtres claires, en français,
	afin de ne jamais perdre une modification ni retirer un sonore sans le savoir.

	https://github.com/dascritch/machincast/issues/31, https://github.com/dascritch/machincast/issues/112,
	https://github.com/dascritch/machincast/issues/32. Les scénarios des fiches remplacent ces fenêtres par leurs
	réponses ; ceux-ci ouvrent les vraies fenêtres, hors de l'écran du poste, et y cliquent.

	Contexte:
		Étant donné le poste à l'heure de Paris

	Plan du scénario: La question de fermeture d'une fiche modifiée propose trois réponses
		Quand la question de fermeture de « Banque : Jingles » s'ouvre, et que j'y <geste>
		Alors la question a dit « « Banque : Jingles » a des modifications qui ne sont pas enregistrées. »
		Et la question a précisé « Les enregistrer avant de fermer la fiche ? »
		Et la question a proposé « Enregistrer », « Abandonner », « Annuler »
		Et la réponse est « <reponse> »

		Exemples:
			| geste                      | reponse     |
			| clique sur « Enregistrer » | Enregistrer |
			| clique sur « Abandonner »  | Abandonner  |
			| clique sur « Annuler »     | Annuler     |
			| tape Échap                 | Annuler     |
			| tape Entrée                | Enregistrer |

	Scénario: Avant de rafraîchir une fiche modifiée, la même question le précise
		Quand la question de rafraîchissement de « Banque : Jingles » s'ouvre, et que j'y tape Échap
		Alors la question a dit « « Banque : Jingles » a des modifications qui ne sont pas enregistrées. »
		Et la question a précisé « Les enregistrer avant de rafraîchir la fiche ? »
		Et la réponse est « Annuler »

	Plan du scénario: Fermer le journal d'une indexation en cours demande s'il faut l'arrêter
		Quand la question d'arrêt de « Audit complet » s'ouvre, et que j'y <geste>
		Alors la question a dit « L'indexation est en cours : « Audit complet ». »
		Et la question a précisé « L'arrêter ? Elle s'arrête après le fichier en cours ; le travail fait est gardé, la prochaine indexation reprendra le reste. »
		Et la question a proposé « Arrêter », « Continuer »
		Et la réponse est « <reponse> »

		Exemples:
			| geste                    | reponse |
			| clique sur « Arrêter »   | True    |
			| clique sur « Continuer » | False   |
			| tape Échap               | False   |
			| tape Entrée              | False   |

	Plan du scénario: L'avertissement de réintégration d'un sonore retiré propose trois réponses
		Quand l'avertissement de réintégration « Café à minuit reviendra » s'ouvre, et que j'y <geste>
		Alors la question a dit « Café à minuit reviendra »
		Et la question a proposé « Retirer quand même », « Ouvrir le dossier », « Annuler »
		Et la réponse est « <reponse> »

		Exemples:
			| geste                             | reponse            |
			| clique sur « Retirer quand même » | Retirer quand même |
			| clique sur « Ouvrir le dossier »  | Ouvrir le dossier  |
			| clique sur « Annuler »            | Annuler            |
			| tape Échap                        | Annuler            |
			| tape Entrée                       | Annuler            |

	Plan du scénario: La confirmation d'une suppression ne supprime que sur « Supprimer »
		# https://github.com/dascritch/machincast/issues/33
		Quand la question de suppression « Supprimer le sonore » s'ouvre, et que j'y <geste>
		Alors la question a dit « Supprimer de la base le sonore « Spot » ? »
		Et la question a proposé « Supprimer », « Annuler »
		Et la réponse est « <reponse> »

		Exemples:
			| geste                    | reponse |
			| clique sur « Supprimer » | True    |
			| clique sur « Annuler »   | False   |
			| tape Échap               | False   |
			| tape Entrée              | False   |

	Plan du scénario: La confirmation d'une action sur une sélection ne la fait que sur son bouton, ou Entrée
		# https://github.com/dascritch/machincast/issues/114
		Quand la confirmation de l'action « Désactiver » s'ouvre, et que j'y <geste>
		Alors la question a dit « Désactiver 2 sonores ? Un sonore en aperçu reste en aperçu. »
		Et la question a proposé « Désactiver », « Annuler »
		Et la réponse est « <reponse> »

		Exemples:
			| geste                     | reponse |
			| clique sur « Désactiver » | True    |
			| clique sur « Annuler »    | False   |
			| tape Échap                | False   |
			| tape Entrée               | True    |

	Plan du scénario: La création d'un événement depuis le calendrier ne se fait que sur « Créer »
		# https://github.com/dascritch/machincast/issues/36 : rien n'est enregistré avant la fiche, Entrée crée.
		Quand la question de création s'ouvre, et que j'y <geste>
		Alors la question a dit « Créer un événement le dimanche 25 octobre 2026 de 13:00 à 14:00 ? »
		Et la question a proposé « Créer », « Annuler »
		Et la réponse est « <reponse> »

		Exemples:
			| geste                  | reponse |
			| clique sur « Créer »   | True    |
			| clique sur « Annuler » | False   |
			| tape Échap             | False   |
			| tape Entrée            | True    |

	Plan du scénario: Le choix d'un répertoire donne le répertoire choisi, ou rien s'il est abandonné
		Quand le sélecteur de répertoires du poste donne « <selecteur> »
		Alors le répertoire choisi est <choisi>

		Exemples:
			| selecteur      | choisi               |
			| /srv/jingles   | « /srv/jingles »     |
			|                | aucun                |

	Plan du scénario: Le choix des sonores, des banques, des séquences ou des marques-pages donne ceux sélectionnés, ou aucun s'il est abandonné
		Étant donné les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement                  |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/jingles/hiver/cafe.flac |
			|             | Spot          | fichier | actif | 30    | /srv/pubs/spot.flac          |
		Et la banque « Publicité », aléatoire, sans nom public, avec « Spot »
		Et la banque « Habillage », séquentielle, sans nom public, avec « Café à minuit »
		Et la séquence « Passage pub », sans nom public, avec le sonore « Spot »
		Et les marques-pages « Relais », « https://flux.exemple/relais »
		Quand le choix des <genre> s'ouvre, avec la remarque « <remarque> », et que j'y sélectionne tout, puis clique sur « <bouton> »
		Alors le choix s'est intitulé « Ajouter des <genre> »
		Et le choix n'a proposé ni création ni ajout de fichiers
		Et le choix n'a proposé aucune action au clic droit
		Et le choix a expliqué « <explication> »
		Et les <genre> choisis sont <choisis>

		Exemples:
			| genre   | remarque                   | bouton  | explication                                                                                          | choisis                     |
			| sonores |                            | Ajouter | Choisir parmi les sonores déjà en base (Ctrl ou Maj pour en prendre plusieurs).                       | « Café à minuit », « Spot » |
			| sonores |                            | Annuler | Choisir parmi les sonores déjà en base (Ctrl ou Maj pour en prendre plusieurs).                       | aucun                       |
			| banques | Une banque peut revenir.   | Ajouter | Choisir parmi les banques déjà en base (Ctrl ou Maj pour en prendre plusieurs). Une banque peut revenir. | « Habillage », « Publicité » |
			| banques | Une banque peut revenir.   | Annuler | Choisir parmi les banques déjà en base (Ctrl ou Maj pour en prendre plusieurs). Une banque peut revenir. | aucun                       |
			| séquences | Une séquence peut revenir. | Ajouter | Choisir parmi les séquences déjà en base (Ctrl ou Maj pour en prendre plusieurs). Une séquence peut revenir. | « Passage pub » |
			| marques-pages | Un élément peut revenir. | Ajouter | Choisir parmi les marques-pages déjà en base (Ctrl ou Maj pour en prendre plusieurs). Un élément peut revenir. | « Relais » |

	Scénario: Le choix des banques peut ne proposer que certaines d'entre elles
		# https://github.com/dascritch/machincast/issues/114
		Étant donné les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement                  |
			|             | Spot          | fichier | actif | 30    | /srv/pubs/spot.flac          |
		Et la banque « Publicité », aléatoire, sans nom public, avec « Spot »
		Et la banque « Habillage », séquentielle, sans nom public, avec « Spot »
		Et la banque « Nuit », aléatoire, sans nom public, avec « Spot »
		Quand le choix des banques s'ouvre, parmi « Publicité », « Nuit », et que j'y sélectionne tout, puis clique sur « Ajouter »
		Alors les banques choisies sont « Nuit », « Publicité »

	Scénario: Ouvrir un dossier le montre dans le navigateur de fichiers du poste
		Quand j'ouvre le dossier « /srv/jingles/hiver »
		Alors le poste a ouvert l'adresse « file:///srv/jingles/hiver »
