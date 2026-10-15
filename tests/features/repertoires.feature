# language: fr
Fonctionnalité: Indexation récursive des répertoires de banques
	En tant que programmateur de l'antenne,
	je veux que tout fichier audio déposé dans l'un des répertoires d'une banque y soit ajouté à la prochaine indexation,
	afin que alimenter une banque se limite à déposer des fichiers.

	https://github.com/dascritch/machincast/issues/9 — spec § 6.2. Chaque indexation parcourt d'abord les répertoires
	des banques, puis vérifie les sonores : un nouveau fichier, enregistré en aperçu, est décodé dans le même passage.

	# ─── Parcours ──────────────────────────────────────────────

	Scénario: Un fichier déposé dans le répertoire d'une banque y est ajouté puis vérifié
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Jingles » contient, dans l'ordre, « jingles/intro.flac »
		Et le sonore de « jingles/intro.flac » est à l'état « actif »
		Et le bilan indique « indexation rapide : 1 nouveau sonore, 0 rattachement ; 1 sonore vérifié ; 0 erroné, 0 supprimé, 0 rétabli, 1 sorti d'aperçu »

	Scénario: Les sous-répertoires sont parcourus, les fichiers ajoutés dans l'ordre de leur chemin
		Étant donné une banque « Fond » alimentée par le répertoire « fond »
		Et le fichier « fond/b/nappe.ogg », sain
		Et le fichier « fond/a/2/pluie.wav », sain
		Et le fichier « fond/a/1/vent.mp3 », sain
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Fond » contient, dans l'ordre, « fond/a/1/vent.mp3 », « fond/a/2/pluie.wav », « fond/b/nappe.ogg »

	Scénario: Seuls les fichiers des formats sonores sont indexés, quelle que soit la casse de leur extension
		Étant donné une banque « Divers » alimentée par le répertoire « divers »
		Et le fichier « divers/MAJUSCULES.MP3 », sain
		Et le fichier « divers/court.aif », sain
		Et le fichier « divers/note.txt », quelconque
		Et le fichier « divers/pochette.jpg », quelconque
		Et le fichier « divers/._intro.mp3 », quelconque
		Et le fichier « divers/.cache/cache.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Divers » contient, dans l'ordre, « divers/MAJUSCULES.MP3 », « divers/court.aif »

	Plan du scénario: Chaque format de la spécification est indexé
		Étant donné une banque « Formats » alimentée par le répertoire « formats »
		Et le fichier « formats/son.<extension> », sain
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Formats » contient, dans l'ordre, « formats/son.<extension> »
		Et le sonore de « formats/son.<extension> » est à l'état « actif »

		Exemples:
			| extension |
			| mp3       |
			| m4a       |
			| aac       |
			| ogg       |
			| flac      |
			| wav       |
			| aiff      |

	# ─── Pas de doublon ────────────────────────────────────────

	Scénario: Un fichier déjà indexé n'est pas dupliqué
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Et l'indexeur a fait une indexation rapide
		Quand l'indexeur fait une indexation rapide
		Alors la base contient 1 sonore
		Et la banque « Jingles » contient, dans l'ordre, « jingles/intro.flac »
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement ; 0 sonore vérifié ; 0 erroné, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Un répertoire qui alimente deux banques donne un seul sonore, présent dans les deux banques
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et une banque « Identifiants » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors la base contient 1 sonore
		Et la banque « Jingles » contient, dans l'ordre, « jingles/intro.flac »
		Et la banque « Identifiants » contient, dans l'ordre, « jingles/intro.flac »
		Et le bilan indique « indexation rapide : 1 nouveau sonore, 1 rattachement ; 1 sonore vérifié ; 0 erroné, 0 supprimé, 0 rétabli, 1 sorti d'aperçu »

	Scénario: Un sonore retiré à la main d'une banque y est réintégré en fin de liste
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/a.flac », sain
		Et le fichier « jingles/b.flac », sain
		Et l'indexeur a fait une indexation rapide
		Et « jingles/a.flac » a été retiré à la main de la banque « Jingles »
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Jingles » contient, dans l'ordre, « jingles/b.flac », « jingles/a.flac »
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 1 rattachement ; 0 sonore vérifié ; 0 erroné, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Un nouveau fichier s'ajoute après les sonores déjà présents dans la banque
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/b.flac », sain
		Et l'indexeur a fait une indexation rapide
		Et le fichier « jingles/a.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Jingles » contient, dans l'ordre, « jingles/b.flac », « jingles/a.flac »

	# ─── Anomalies ─────────────────────────────────────────────

	Scénario: Un répertoire introuvable est signalé, les autres banques sont indexées
		Étant donné une banque « Absente » alimentée par le répertoire « nulle-part »
		Et une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors la sortie d'erreur signale le répertoire « nulle-part » comme introuvable, pour la banque « Absente »
		Et la banque « Jingles » contient, dans l'ordre, « jingles/intro.flac »

	Scénario: Un fichier défectueux déposé dans une banque y est ajouté, puis signalé et passé erroné
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/abime.mp3 », endommagé
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Jingles » contient, dans l'ordre, « jingles/abime.mp3 »
		Et le sonore de « jingles/abime.mp3 » est à l'état « errone »
