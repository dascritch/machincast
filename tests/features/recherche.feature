# language: fr
Fonctionnalité: Recherche globale
	En tant que programmateur de l'antenne,
	je veux qu'un champ de recherche unique propose des résultats au fil de la frappe,
	afin de trouver n'importe quel élément sans savoir de quel type il est.

	https://github.com/dascritch/machincast/issues/27, https://github.com/dascritch/machincast/issues/105, spec § 8.2.
	L'onglet « Recherche », qui se ferme, s'ouvre par « Affichage → Rechercher… » ou Ctrl+F. Dès deux caractères, sans
	tenir compte des majuscules ni des accents, le texte est cherché dans le nom interne et le nom public des
	événements, des séquences et des banques, et dans l'artiste et le titre des sonores. La table des résultats suit la
	frappe, jusqu'à une limite, dans l'ordre : événements, séquences, banques, sonores, chacun par nom. Le champ ne
	propose pas de suggestions. Ouvrir une ligne de la table ouvre la fiche de l'élément.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et les sonores :
			| artiste     | titre         | type    | etat      | duree | emplacement             |
			| Les Gaufres | Café à minuit | fichier | actif     | 214   | /srv/musique/minuit.flac |
			| Café Noir   | Nuit blanche  | fichier | desactive | 180   | /srv/musique/nuit.flac   |
			|             | Jingle        | fichier | actif     | 5     | /srv/cafe/jingle.flac    |
		Et la banque « Cafés chantants », aléatoire, sans nom public, avec « Café à minuit »
		Et la banque « Habillage », séquentielle, de nom public « Le café des ondes », avec « Jingle »
		Et la séquence « Café-croissant », sans nom public, avec le sonore « Jingle »
		Et les événements :
			| nom           | nom_public   | priorite    | debut               | fin                 | jours |
			| Fil de jour   |              | fil_musical |                     |                     |       |
			| Café du matin |              | emission    | 2026-10-21 07:00:00 | 2026-10-21 09:00:00 |       |
			| Matinale      | Le petit CAFÉ | emission   | 2026-10-21 10:00:00 | 2026-10-21 11:00:00 |       |

	# ─── Ouverture ─────────────────────────────────────────────

	Scénario: L'onglet « Recherche » s'ouvre par le menu Affichage, une seule fois, et se ferme
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Rechercher… » dans le menu « Affichage »
		Alors l'onglet ouvert est « Recherche »
		Et le champ de recherche a le focus
		Et seul l'onglet « Recherche » a un bouton de fermeture
		Quand j'ouvre l'onglet « Sonores »
		Et je choisis « Rechercher… » dans le menu « Affichage »
		Alors l'onglet ouvert est « Recherche »
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Marques-pages », « Incidents », « Recherche »
		Quand je ferme l'onglet « Recherche »
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Marques-pages », « Incidents »

	Scénario: Ctrl+F ouvre la recherche, ou y revient en sélectionnant le texte cherché
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « Ctrl+F »
		Alors l'onglet ouvert est « Recherche »
		Quand je tape « jingle » dans le champ de recherche
		Et j'ouvre l'onglet « Accueil »
		Et j'appuie sur « Ctrl+F »
		Alors l'onglet ouvert est « Recherche »
		Et le champ de recherche a le focus, avec « jingle » sélectionné

	# ─── Résultats ─────────────────────────────────────────────

	Scénario: La table suit la frappe, dans l'ordre des types, sans tenir compte des accents, sans suggestions
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « Ctrl+F »
		Et je tape « cafe » dans le champ de recherche
		Alors le champ de recherche ne propose pas de suggestions
		Et les résultats sont :
			| Type      | Nom interne                 | Nom public        | Statut    |
			| Événement | Café du matin               |                   |           |
			| Événement | Matinale                    | Le petit CAFÉ     |           |
			| Séquence  | Café-croissant              |                   |           |
			| Banque    | Cafés chantants             |                   |           |
			| Banque    | Habillage                   | Le café des ondes |           |
			| Sonore    | Café Noir – Nuit blanche    |                   | désactivé |
			| Sonore    | Les Gaufres – Café à minuit |                   | actif     |
		Et le compte des résultats est « 7 résultats »

	Scénario: Le texte tapé peut avoir des majuscules et des accents
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « Ctrl+F »
		Et je tape « CAFÉ-croissant » dans le champ de recherche
		Alors les résultats nommés sont « Café-croissant »
		Et le compte des résultats est « 1 résultat »

	Scénario: L'emplacement d'un sonore n'est pas cherché, seulement son artiste et son titre
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « Ctrl+F »
		Et je tape « srv » dans le champ de recherche
		Alors les résultats nommés sont aucun
		Et le compte des résultats est « aucun résultat »

	Scénario: En dessous de deux caractères, rien n'est cherché
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « Ctrl+F »
		Et je tape « c » dans le champ de recherche
		Alors les résultats nommés sont aucun
		Et le compte des résultats est « Tapez au moins 2 caractères. »

	Scénario: Les caractères spéciaux de SQL sont cherchés tels quels
		Étant donné les sonores :
			| artiste | titre         | type    | etat  | duree | emplacement           |
			|         | 100% Gaufres  | fichier | actif | 60    | /srv/pubs/cent.flac   |
			|         | 1000 Gaufres  | fichier | actif | 60    | /srv/pubs/mille.flac  |
			|         | Gaufre_royale | fichier | actif | 60    | /srv/pubs/royale.flac |
			|         | Gaufre royale | fichier | actif | 60    | /srv/pubs/autre.flac  |
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « Ctrl+F »
		Et je tape « 0% » dans le champ de recherche
		Alors les résultats nommés sont « 100% Gaufres »
		Quand je tape « e_r » dans le champ de recherche
		Alors les résultats nommés sont « Gaufre_royale »

	Scénario: La table s'arrête à sa limite, qu'elle annonce
		Étant donné 12 sonores titrés « Spot 01 » à « Spot 12 »
		Et une table de résultats limitée à 11 lignes
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « Ctrl+F »
		Et je tape « spot » dans le champ de recherche
		Alors les résultats nommés sont « Spot 01 », « Spot 02 », « Spot 03 », « Spot 04 », « Spot 05 », « Spot 06 », « Spot 07 », « Spot 08 », « Spot 09 », « Spot 10 », « Spot 11 »
		Et le compte des résultats est « 11 premiers résultats sur 12 »

	# ─── Fiches ────────────────────────────────────────────────

	Plan du scénario: Ouvrir une ligne de la table ouvre la fiche de l'élément, et garde le texte cherché
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « Ctrl+F »
		Et je tape « cafe » dans le champ de recherche
		Et j'ouvre le résultat « <ligne> »
		Alors l'onglet ouvert est « <onglet> »
		Et l'écran de détail de <genre> « <nom> » est demandé
		Quand j'ouvre l'onglet « Recherche »
		Alors le champ de recherche contient « cafe »

		Exemples:
			| ligne                       | onglet                    | genre     | nom            |
			| Matinale                    | Événement : Matinale      | événement | Matinale       |
			| Café-croissant              | Séquence : Café-croissant | séquence  | Café-croissant |
			| Habillage                   | Banque : Habillage        | banque    | Habillage      |
			| Les Gaufres – Café à minuit | Sonore : Café à minuit    | sonore    | Café à minuit  |

	# ─── Mise à jour ───────────────────────────────────────────

	Scénario: Rafraîchir les onglets relance la recherche
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « Ctrl+F »
		Et je tape « cafe » dans le champ de recherche
		Et la banque « Café crème » est ajoutée en base
		Alors le compte des résultats est « 7 résultats »
		Quand j'appuie sur « F5 »
		Alors le compte des résultats est « 8 résultats »
