# language: fr
Fonctionnalité: Un emoji annonce l'intention des boutons et des menus qui ajoutent, retirent ou suppriment
	En tant qu'équipe de l'antenne,
	je veux reconnaître d'un coup d'œil ce qu'un bouton va faire,
	afin de ne pas retirer ou supprimer par mégarde.

	https://github.com/dascritch/machincast/issues/294. Un bouton, une entrée de menu, général ou contextuel, ou la
	réponse d'une question, commence par ➕ quand il ajoute des lignes à un tableau, par ➖ quand il en retire, et par ❌
	quand il supprime une fiche, ou le confirme (machincast.interface.intentions). L'emoji est dans le texte : sa couleur
	est celle de la police d'emoji du poste. Les titres des fenêtres et des questions n'en ont pas.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 15:30:42 »
		Et les sonores :
			| artiste     | titre        | type    | etat  | duree | emplacement               |
			|             | Jingle début | fichier | actif | 5     | /srv/habillage/debut.flac |
			| Les Gaufres | Spot         | fichier | actif | 30    | /srv/pubs/spot.flac       |
		Et la banque « Publicité », aléatoire, sans nom public, avec « Spot »
		Et la séquence « Passage pub », sans nom public, avec le sonore « Jingle début », la banque « Publicité »
		Et les événements :
			| nom      | nom_public | priorite    | debut            | fin              | jours |
			| Continue |            | fil_musical |                  |                  |       |
		Et les feeds « Studio mobile » « https://flux.exemple/direct »

	Plan du scénario: Les boutons d'une fiche qui ajoutent, retirent ou suppriment portent leur emoji
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de <genre> « <nom> » par son identifiant
		Alors les boutons de la fiche qui ajoutent, retirent ou suppriment sont <boutons>

		Exemples:
			| genre       | nom           | boutons                                                                                                                                      |
			| la banque   | Publicité     | « ➕ Ajouter un répertoire… », « ➖ Retirer le répertoire », « ➕ Ajouter des sonores… », « ➖ Retirer le sonore », « ❌ Supprimer… »            |
			| l'événement | Continue      | « ➕ Ajouter des sonores… », « ➕ Ajouter des banques… », « ➕ Ajouter des séquences… », « ➕ Ajouter des feeds… », « ➖ Retirer l'élément », « ❌ Supprimer… » |
			| la séquence | Passage pub   | « ➕ Ajouter des sonores… », « ➕ Ajouter des banques… », « ➖ Retirer l'élément », « ❌ Supprimer… »                                          |
			| le sonore   | Spot          | « ❌ Supprimer… »                                                                                                                             |
			| le feed     | Studio mobile | « ❌ Supprimer… »                                                                                                                             |

	Scénario: Le titre d'une question d'action groupée n'a pas d'emoji, son bouton si
		Alors l'action groupée « ajouter » s'intitule « Ajouter à des banques », au bouton « ➕ Ajouter à des banques »
		Et l'action groupée « retirer » s'intitule « Retirer de banques », au bouton « ➖ Retirer de banques »
