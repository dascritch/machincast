# language: fr
Fonctionnalité: Colonnes des tableaux, ajustées, réordonnables, masquables et gardées par vue
	En tant que programmateur de l'antenne,
	je veux que les colonnes des tableaux s'ajustent à leur contenu, et pouvoir les réordonner, les cacher et les élargir,
	afin de lire ce qui m'importe, et de retrouver ma disposition d'une session à l'autre.

	https://github.com/dascritch/machincast/issues/207. Chaque tableau de l'interface est une vue : chaque liste, la
	recherche, les incidents, l'airplay de l'onglet Antenne, la simulation, et les tableaux des fiches. Ses colonnes s'ajustent
	à leur contenu à chaque lecture, tant qu'aucune n'a été élargie à la main. Un titre se glisse pour déplacer sa
	colonne ; un clic droit sur les titres coche les colonnes montrées, ou rétablit la disposition d'origine. L'ordre,
	les colonnes cachées et les largeurs sont gardés par vue, pour le compte de l'utilisateur, dans ses réglages, et
	jamais dans le fichier de configuration du poste.

	Contexte:
		Étant donné l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et les sonores :
			| artist      | title         | type | state    | duration | location                                    |
			| Les Gaufres | Café à minuit | file | active   | 214      | /srv/musique/Les Gaufres/Café à minuit.flac |
			| Café Noir   | Nuit blanche  | file | disabled | 180      | /srv/musique/Café Noir/Nuit blanche.flac    |
		Et la banque « Rotation », aléatoire, sans nom public, avec « Café à minuit », « Nuit blanche »
		Et la banque « Nuit », séquentielle, sans nom public, avec « Nuit blanche »

	# ─── Ajustement au contenu ─────────────────────────────────

	Scénario: Les colonnes de la recherche montrent leur contenu en entier
		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « Ctrl+F »
		Et je tape « cafe » dans le champ de recherche
		Alors la colonne « Type » de l'onglet « Recherche » montre « Sonore » en entier
		Et la colonne « Nom interne » de l'onglet « Recherche » montre « Les Gaufres – Café à minuit » en entier
		Et la dernière colonne de l'onglet « Recherche » s'étire jusqu'au bord du tableau

	Scénario: Les colonnes d'une liste montrent leur contenu en entier, et suivent une nouvelle lecture
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors la colonne « Emplacement » de l'onglet « Sonores » montre « /srv/musique/Les Gaufres/Café à minuit.flac » en entier
		Quand le sonore « Un titre bien plus long que tous les autres titres » est ajouté en base
		Et j'appuie sur « F5 »
		Alors la colonne « Titre » de l'onglet « Sonores » montre « Un titre bien plus long que tous les autres titres » en entier

	# ─── Largeur, ordre, colonnes cachées ──────────────────────

	Scénario: Une colonne élargie à la main garde sa largeur, même après une nouvelle lecture et d'une session à l'autre
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'élargis la colonne « Artiste » de l'onglet « Sonores » à 300 pixels
		Et j'appuie sur « F5 »
		Alors la colonne « Artiste » de l'onglet « Sonores » fait 300 pixels
		Quand je ferme la fenêtre de l'interface
		Et la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors la colonne « Artiste » de l'onglet « Sonores » fait 300 pixels

	Scénario: Une colonne se déplace en glissant son titre, et garde sa place d'une session à l'autre
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je glisse la colonne « Titre » de l'onglet « Sonores » en première place
		Alors les colonnes de l'onglet « Sonores » sont « Titre », « ⚠️ », « Artiste », « Type », « État », « Durée », « Emplacement »
		Quand je ferme la fenêtre de l'interface
		Et la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors les colonnes de l'onglet « Sonores » sont « Titre », « ⚠️ », « Artiste », « Type », « État », « Durée », « Emplacement »

	Scénario: Le clic droit sur les titres coche les colonnes montrées
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je décoche « Emplacement » dans le menu des colonnes de l'onglet « Sonores »
		Alors les colonnes de l'onglet « Sonores » sont « ⚠️ », « Artiste », « Titre », « Type », « État », « Durée »
		Et le menu des colonnes de l'onglet « Sonores » propose :
			| entrée                 | état     |
			| ⚠️                     | coché    |
			| Artiste                | coché    |
			| Titre                  | coché    |
			| Type                   | coché    |
			| État                   | coché    |
			| Durée                  | coché    |
			| Emplacement            | décoché  |
			| —                      |          |
			| Rétablir les colonnes  |          |
		Quand je coche « Emplacement » dans le menu des colonnes de l'onglet « Sonores »
		Alors les colonnes de l'onglet « Sonores » sont « ⚠️ », « Artiste », « Titre », « Type », « État », « Durée », « Emplacement »

	Scénario: La dernière colonne montrée ne se décoche pas
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Et je décoche « ⚠️ » dans le menu des colonnes de l'onglet « Séquences »
		Et je décoche « Nom public » dans le menu des colonnes de l'onglet « Séquences »
		Et je décoche « Anomalie » dans le menu des colonnes de l'onglet « Séquences »
		Alors les colonnes de l'onglet « Séquences » sont « Nom »
		Et l'entrée « Nom » du menu des colonnes de l'onglet « Séquences » est inactive

	Scénario: « Rétablir les colonnes » revient à la disposition d'origine, ajustée au contenu
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je glisse la colonne « Titre » de l'onglet « Sonores » en première place
		Et je décoche « Emplacement » dans le menu des colonnes de l'onglet « Sonores »
		Et j'élargis la colonne « Artiste » de l'onglet « Sonores » à 300 pixels
		Et je choisis « Rétablir les colonnes » dans le menu des colonnes de l'onglet « Sonores »
		Alors les colonnes de l'onglet « Sonores » sont « ⚠️ », « Artiste », « Titre », « Type », « État », « Durée », « Emplacement »
		Et la colonne « Emplacement » de l'onglet « Sonores » montre « /srv/musique/Les Gaufres/Café à minuit.flac » en entier
		Et la colonne « Artiste » de l'onglet « Sonores » ne fait pas 300 pixels
		Quand je ferme la fenêtre de l'interface
		Et la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors les colonnes de l'onglet « Sonores » sont « ⚠️ », « Artiste », « Titre », « Type », « État », « Durée », « Emplacement »

	# ─── Par vue, par compte ───────────────────────────────────

	Scénario: Chaque vue a sa disposition, gardée dans les réglages du compte, pas dans la configuration du poste
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je décoche « Nom public » dans le menu des colonnes de l'onglet « Banques »
		Alors les colonnes de l'onglet « Événements » sont « ⚠️ », « Nom », « Nom public », « Priorité », « Début », « Fin », « Récurrence », « Anomalie »
		Et les réglages du compte gardent la vue « liste-banques »
		Et le fichier de configuration n'a pas changé

	Scénario: Une disposition gardée pour d'autres colonnes, d'une version précédente, est oubliée
		Étant donné une disposition de la vue « liste-sonores », sa dernière colonne en premier, gardée pour les colonnes « Artiste », « Titre », « Type », « État », « Durée », « Fichier », « Anomalie »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors les colonnes de l'onglet « Sonores » sont « ⚠️ », « Artiste », « Titre », « Type », « État », « Durée », « Emplacement »

	Scénario: Le tri d'une liste n'est pas gardé d'une session à l'autre, même avec sa disposition
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je clique sur le titre de la colonne « Titre »
		Et je glisse la colonne « Durée » de l'onglet « Sonores » en première place
		Alors la liste montre les titres « Café à minuit », « Nuit blanche »
		Quand je ferme la fenêtre de l'interface
		Et la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Alors la liste montre les titres « Nuit blanche », « Café à minuit »
		Et les colonnes de l'onglet « Sonores » sont « Durée », « ⚠️ », « Artiste », « Titre », « Type », « État », « Emplacement »

	Scénario: Le tableau d'une fiche relue en arrière-plan s'ajuste quand on y revient
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Rotation »
		Et j'ouvre l'onglet « Antenne »
		Et le sonore « Un titre bien plus long que tous les autres titres » est ajouté à la banque « Rotation » en base
		Et j'appuie sur « F5 »
		Et j'ouvre l'onglet « Banque : Rotation »
		Alors la colonne « Sonore » du tableau « Sonores » de la fiche montre « Un titre bien plus long que tous les autres titres » en entier

	Scénario: Le tableau d'une fiche garde sa disposition pour toutes les fiches du même genre
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Rotation »
		Et je décoche « Emplacement » dans le menu des colonnes du tableau « Sonores » de la fiche
		Et je ferme l'onglet « Banque : Rotation »
		Et j'ouvre la fiche de la banque « Nuit »
		Alors les colonnes du tableau « Sonores » de la fiche sont « Sonore », « Durée », « État »

	Scénario: Tous les tableaux de l'interface ont des colonnes déplaçables et leur menu des colonnes
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre chaque onglet et la fiche de chaque genre
		Alors chaque tableau de l'interface a des colonnes déplaçables, de largeur libre, avec le menu des colonnes de sa vue
		Et le clic droit hors des lignes de chaque tableau de l'interface ne propose que « Exporter ce tableau… »

	# ─── Exporter un tableau (https://github.com/dascritch/machincast/issues/329) ───

	Scénario: « Exporter ce tableau… » enregistre le tableau tel qu'il est affiché, en CSV
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je glisse la colonne « Titre » de l'onglet « Sonores » en première place
		Et je décoche « Emplacement » dans le menu des colonnes de l'onglet « Sonores »
		Et je décoche « ⚠️ » dans le menu des colonnes de l'onglet « Sonores »
		Et je clique sur le titre de la colonne « Titre »
		Et je clique sur le titre de la colonne « Titre »
		Et je choisis « Exporter ce tableau… » au clic droit dans le tableau de l'onglet « Sonores », vers « sonores.csv »
		Alors le sélecteur de fichier a proposé « liste-sonores.csv »
		Et le fichier « sonores.csv » contient, en UTF-8 avec BOM :
			"""
			Titre;Artiste;Type;État;Durée
			Nuit blanche;Café Noir;fichier;désactivé;3:00
			Café à minuit;Les Gaufres;fichier;actif;3:34
			"""
		Et la barre d'état annonce que le tableau est exporté dans « sonores.csv »

	Scénario: Seules les lignes que garde le filtre sont exportées
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je tape « nuit » dans le filtre de la liste
		Et je choisis « Exporter ce tableau… » au clic droit dans le tableau de l'onglet « Banques », vers « banques.csv »
		Alors le fichier « banques.csv » contient, en UTF-8 avec BOM :
			"""
			⚠️;Nom;Nom public;Mode;Ne pas répéter;Répertoire
			⚠️;Nuit;;séquentielle;non;
			"""

	Scénario: Le clic droit sur une ligne propose ses entrées, puis « Exporter ce tableau… »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Alors le clic droit sur la ligne « Nuit » de l'onglet « Banques » propose d'abord « Dupliquer », et finit par « — », « Exporter ce tableau… »

	Scénario: Un fichier choisi sans l'extension .csv la reçoit ; jamais un fichier sonore n'est écrit
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je choisis « Exporter ce tableau… » au clic droit dans le tableau de l'onglet « Banques », vers « Nuit blanche.flac »
		Alors le fichier « Nuit blanche.flac.csv » contient la ligne « ⚠️;Nom;Nom public;Mode;Ne pas répéter;Répertoire »
		Et le fichier « Nuit blanche.flac » n'existe pas

	Scénario: Un export impossible le dit dans la barre d'état
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je choisis « Exporter ce tableau… » au clic droit dans le tableau de l'onglet « Banques », vers « absent/banques.csv »
		Alors la barre d'état commence par « Export impossible : »

	Scénario: Abandonner le choix du fichier n'exporte rien
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et j'abandonne « Exporter ce tableau… » au clic droit dans le tableau de l'onglet « Banques »
		Alors aucun fichier n'est exporté
