# language: fr
Fonctionnalité: Onglet Airplay, réglable et exportable
	En tant que responsable d'antenne,
	je veux l'historique de diffusion dans un onglet à part, sur la durée de mon choix, et pouvoir l'exporter,
	afin de garder l'accueil compact, et de transmettre ce qui est passé à l'antenne.

	https://github.com/dascritch/machincast/issues/244, spec § 8.1. L'onglet est fermé au lancement, et s'ouvre depuis
	le menu « Affichage ». Il montre les passages des dernières heures, 12 par défaut ; le nombre d'heures se règle en
	haut de l'onglet, et il est retenu pour le compte. « Exporter… » enregistre ce que l'onglet montre en CSV, en HTML
	ou en M3U, avec l'artiste, le titre et l'emplacement, et le texte public, tel que la page publique l'affiche.

	Contexte:
		Étant donné l'horloge de l'interface au « 2026-10-16 20:01:00 »
		Et les passages dans l'airplay :
			| debut               | fin                 | artiste     | titre         | evenement   | sequence | banque | sans_incident |
			| 2026-10-15 20:00:00 | 2026-10-15 20:03:00 | Ancien      | Hier          | Fil de jour |          |        | oui           |
			| 2026-10-16 18:00:00 | 2026-10-16 19:02:05 |             | Le journal    | Journal     |          |        | oui           |
			| 2026-10-16 19:50:00 | 2026-10-16 19:51:00 |             | Spot          | Fil de jour | Pub      | Spots  | non           |
			| 2026-10-16 20:00:00 |                     | Les Gaufres | Café à minuit | Fil de jour |          | Titres |               |

	Scénario: L'onglet Airplay est fermé au lancement, et s'ouvre depuis le menu « Affichage »
		Quand la fenêtre de l'interface s'ouvre
		Alors la fenêtre a les onglets « Accueil », « Calendrier », « Événements », « Séquences », « Banques », « Incidents »
		Quand je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Alors la fenêtre a les onglets « Accueil », « Calendrier », « Événements », « Séquences », « Banques », « Incidents », « Airplay »
		Et l'onglet ouvert est « Airplay »

	Scénario: L'onglet montre les passages des 12 dernières heures, du plus récent au plus ancien, avec les colonnes de l'accueil
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Alors l'onglet Airplay montre les 12 dernières heures
		Et la table de l'onglet Airplay montre :
			| debut    | fin      | duree   | artiste     | titre         | evenement   | sequence | banque | incident |
			| 20:00:00 | en cours |         | Les Gaufres | Café à minuit | Fil de jour |          | Titres |          |
			| 19:50:00 | 19:51:00 | 1:00    |             | Spot          | Fil de jour | Pub      | Spots  | oui      |
			| 18:00:00 | 19:02:05 | 1:02:05 |             | Le journal    | Journal     |          |        |          |

	Scénario: Le nombre d'heures se règle, la table le suit, et il est retenu pour le compte
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et je règle l'onglet Airplay sur 25 heures
		Alors la table de l'onglet Airplay a 4 lignes
		Quand je règle l'onglet Airplay sur 1 heure
		Alors la table de l'onglet Airplay a 2 lignes
		Quand je règle l'onglet Airplay sur 25 heures
		Et la fenêtre de l'interface se ferme, puis s'ouvre de nouveau
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Alors l'onglet Airplay montre les 25 dernières heures
		Et la table de l'onglet Airplay a 4 lignes

	Scénario: Un seul onglet Airplay, qui se ferme par sa croix
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et j'ouvre l'onglet « Accueil »
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Alors la fenêtre a les onglets « Accueil », « Calendrier », « Événements », « Séquences », « Banques », « Incidents », « Airplay »
		Et l'onglet ouvert est « Airplay »
		Quand je ferme l'onglet « Airplay »
		Alors la fenêtre a les onglets « Accueil », « Calendrier », « Événements », « Séquences », « Banques », « Incidents »

	Scénario: Un double-clic ouvre la fiche, et le clic droit propose la pré-écoute du sonore
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et j'ouvre dans l'onglet Airplay la cellule « Pub »
		Alors l'onglet ouvert est « Séquence : Pub »
		Quand j'ouvre l'onglet « Airplay »
		Alors le clic droit sur la ligne « Spot » de l'onglet Airplay propose « Pré-écoute… »

	Scénario: Rafraîchir les onglets relit l'onglet Airplay
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et le passage de « Jingle » commence dans l'airplay à 20:00:30
		Et je choisis « Rafraîchir les onglets » dans le menu « Affichage »
		Alors la table de l'onglet Airplay a 4 lignes

	Scénario: L'onglet Airplay se relit quand l'accueil voit un nouveau sonore
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et le passage de « Jingle » commence dans l'airplay à 20:00:30
		Et l'accueil relit son airplay, pour un nouveau sonore
		Alors la table de l'onglet Airplay a 4 lignes

	# ─── Export ────────────────────────────────────────────────

	Scénario: L'export CSV donne l'artiste, le titre et l'emplacement, et le texte public, masquage appliqué
		Étant donné le masquage de tous les sonores et de tous les événements
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et j'exporte l'onglet Airplay sous « matinale », avec le filtre « Tableur CSV (*.csv) »
		Alors l'export proposait le nom « airplay-2026-10-16-2001-12h.csv »
		Et l'export « matinale.csv » a l'en-tête « debut;fin;duree;artiste;titre;texte_public;emplacement;evenement;sequence;banque;sans_incident »
		Et l'export « matinale.csv » a 3 passages, le premier « 2026-10-16 20:00:00;;;Les Gaufres;Café à minuit;Radio de test;…;Fil de jour;;Titres; »
		Et la barre d'état annonce un export, « Airplay exporté dans » suivi de son chemin

	Scénario: L'export HTML est une page qui donne les deux, l'artiste et le titre, et le texte public
		Étant donné le masquage de tous les sonores et de tous les événements
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et j'exporte l'onglet Airplay sous « matinale », avec le filtre « Page HTML (*.html) »
		Alors l'export « matinale.html » est une page HTML de 3 passages
		Et l'export « matinale.html » contient « Les Gaufres », « Café à minuit », « Radio de test » et l'emplacement de « Café à minuit »
		Et dans l'export « matinale.html », la ligne de « Spot » a l'incident « oui », celle du « Le journal » aucun

	Scénario: L'export M3U est une liste de lecture, du plus ancien au plus récent, avec le texte public en commentaire
		Étant donné le masquage de tous les sonores et de tous les événements
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et j'exporte l'onglet Airplay sous « matinale », avec le filtre « Liste de lecture M3U (*.m3u) »
		Alors l'export « matinale.m3u » commence par « #EXTM3U »
		Et l'export « matinale.m3u » donne, dans l'ordre, les emplacements de « Le journal », « Spot », « Café à minuit »
		Et l'export « matinale.m3u » contient « #EXTINF:-1,Les Gaufres – Café à minuit » et « # texte public : Radio de test »

	Scénario: Un export ne remplace jamais un fichier sonore
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et j'exporte l'onglet Airplay sous « matinale.flac », avec le filtre « Tableur CSV (*.csv) »
		Alors l'export « matinale.flac.csv » a 3 passages
		Et il n'y a pas d'export « matinale.flac »

	Scénario: Un export abandonné n'écrit rien
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Airplay » dans le menu « Affichage »
		Et j'abandonne l'export de l'onglet Airplay
		Alors aucun fichier n'a été exporté
