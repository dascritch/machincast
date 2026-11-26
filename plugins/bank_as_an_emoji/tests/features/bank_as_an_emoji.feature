# language: fr
Fonctionnalité: La banque en emoji : un emoji au début du nom interne d'une banque, choisi dans sa fiche
	En tant que technicien radio,
	je veux que le nom interne de la banque commence par un emoji,
	afin de la reconnaître d'un coup d'œil dans les tableaux d'airplay et des sonores à venir.

	https://github.com/dascritch/machincast/issues/505. L'emoji est rangé dans les premiers caractères du nom interne,
	suivi d'une espace : « 🌟 Publicités ». Dans la fiche de la banque, le nom interne éditable ne le montre pas : il est
	précédé du bouton de l'emoji, qui ouvre le sélecteur d'emojis de KDE, plasma-emojier : il copie l'emoji choisi
	dans le presse-papiers, d'où la fiche le prend. Sans lui, le bouton ouvre une grille d'emojis. Les tableaux, qui
	montrent le nom interne, montrent l'emoji avec lui.

	Contexte:
		Étant donné les banques « 🌟 Publicités » et « Jingles »
		Et le plugin de la banque en emoji, chargé

	# ─── Le nom interne ────────────────────────────────────

	Plan du scénario: L'emoji d'un nom interne est le pictogramme qui le commence, suivi d'une espace
		Alors le nom interne « <nom> » a l'emoji « <emoji> » et le nom « <reste> »

		Exemples:
			| nom              | emoji | reste             |
			| 🌟 Publicités    | 🌟    | Publicités        |
			| ☀️ Matinale      | ☀️    | Matinale          |
			| 🇫🇷 Chanson      | 🇫🇷    | Chanson           |
			| 👩‍🔧 Atelier       | 👩‍🔧    | Atelier           |
			| 👍🏽 Bravo         | 👍🏽    | Bravo             |
			| Publicités       |       | Publicités        |
			| 🌟Publicités     |       | 🌟Publicités      |
			| Top 🌟 Hits      |       | Top 🌟 Hits       |

	# ─── La fiche de la banque ─────────────────────────────

	Scénario: La fiche montre le bouton de l'emoji, puis le nom interne sans son emoji
		Quand j'ouvre la fiche de la banque « 🌟 Publicités »
		Alors le bouton de l'emoji montre « 🌟 »
		Et le nom interne éditable est « Publicités »
		Et le champ du nom interne de la fiche est caché
		Et le bouton de l'emoji est devant le nom interne, dans la ligne « Nom interne »
		Et la fiche n'est pas modifiée

	Scénario: Une banque sans emoji a un bouton « Emoji… », et rien à retirer
		Quand j'ouvre la fiche de la banque « Jingles »
		Alors le bouton de l'emoji montre « Emoji… »
		Et « Retirer l'emoji » est inactif
		Et le nom interne éditable est « Jingles »

	Scénario: Le raccourci du libellé « Nom interne » va au nom sans emoji
		Quand j'ouvre la fiche de la banque « Jingles »
		Et le raccourci du libellé « Nom interne » donne le focus à son champ
		Alors le nom interne éditable a le focus

	Scénario: Le bouton de l'emoji ouvre le sélecteur d'emojis de KDE, et l'emoji qu'il copie va au nom interne
		Étant donné le sélecteur d'emojis de KDE installé
		Quand j'ouvre la fiche de la banque « Jingles »
		Et je clique sur le bouton de l'emoji
		Alors le sélecteur d'emojis de KDE est lancé
		Quand il copie « 📢 » dans le presse-papiers
		Alors le bouton de l'emoji montre « 📢 »
		Et la fiche est modifiée
		Quand j'enregistre la fiche
		Alors la banque « 📢 Jingles » est en base, et « Jingles » n'y est plus

	Scénario: Chaque emoji copié remplace le précédent, et ce qui n'est pas un emoji est ignoré
		Étant donné le sélecteur d'emojis de KDE installé
		Quand j'ouvre la fiche de la banque « Jingles »
		Et je clique sur le bouton de l'emoji
		Et il copie « 📢 » dans le presse-papiers
		Et il copie « 👩‍🔧 » dans le presse-papiers
		Et le presse-papiers reçoit « un texte »
		Alors le bouton de l'emoji montre « 👩‍🔧 »

	Scénario: Un emoji copié hors d'un choix est ignoré
		Étant donné le sélecteur d'emojis de KDE installé
		Quand j'ouvre la fiche de la banque « Jingles »
		Et le presse-papiers reçoit « 📢 »
		Alors le bouton de l'emoji montre « Emoji… »
		Quand je clique sur le bouton de l'emoji
		Et le choix se termine, dix minutes après
		Et il copie « 📢 » dans le presse-papiers
		Alors le bouton de l'emoji montre « Emoji… »

	Scénario: Sans le sélecteur de KDE, le bouton ouvre une grille d'emojis
		Étant donné le sélecteur d'emojis de KDE absent
		Quand j'ouvre la fiche de la banque « Jingles »
		Et je clique sur le bouton de l'emoji
		Alors la grille d'emojis s'ouvre
		Quand je choisis « 📢 » dans la grille
		Alors la grille d'emojis est fermée
		Et le bouton de l'emoji montre « 📢 »

	Scénario: Dans la grille, un autre emoji se colle ; un texte qui n'en est pas un est ignoré
		Étant donné le sélecteur d'emojis de KDE absent
		Quand j'ouvre la fiche de la banque « Jingles »
		Et je clique sur le bouton de l'emoji
		Et je colle « ab » dans la grille, puis Entrée
		Alors la grille d'emojis s'ouvre
		Et le bouton de l'emoji montre « Emoji… »
		Quand je colle « 👩‍🔧 » dans la grille, puis Entrée
		Et j'enregistre la fiche
		Alors la banque « 👩‍🔧 Jingles » est en base, et « Jingles » n'y est plus

	Scénario: Choisir un emoji le met au début du nom interne enregistré
		Quand j'ouvre la fiche de la banque « Jingles »
		Et je choisis l'emoji « 📢 »
		Alors la fiche est modifiée

	Scénario: Changer le nom garde l'emoji
		Quand j'ouvre la fiche de la banque « 🌟 Publicités »
		Et je remplace le nom interne éditable par « Réclames »
		Et j'enregistre la fiche
		Alors la banque « 🌟 Réclames » est en base, et « 🌟 Publicités » n'y est plus

	Scénario: « Retirer l'emoji » le retire du nom interne
		Quand j'ouvre la fiche de la banque « 🌟 Publicités »
		Et je clique sur « Retirer l'emoji »
		Et j'enregistre la fiche
		Alors la banque « Publicités » est en base, et « 🌟 Publicités » n'y est plus

	Scénario: Un emoji sans nom ne fait pas un nom : la fiche demande le nom interne
		Quand j'ouvre la fiche de la banque « 🌟 Publicités »
		Et je remplace le nom interne éditable par « »
		Et j'enregistre la fiche
		Alors la fiche dit l'erreur « Le nom interne est obligatoire. »
		Et la banque « 🌟 Publicités » est toujours en base

	Scénario: La copie d'une banque garde son emoji
		Quand j'ouvre la copie de la banque « 🌟 Publicités »
		Alors le bouton de l'emoji montre « 🌟 »
		Et le nom interne éditable est « Publicités (copie) »

	Scénario: Annuler rend l'emoji et le nom enregistrés
		Quand j'ouvre la fiche de la banque « 🌟 Publicités »
		Et je choisis l'emoji « 📢 »
		Et j'annule la fiche
		Alors le bouton de l'emoji montre « 🌟 »
		Et la fiche n'est pas modifiée

	Scénario: La fiche d'une banque supprimée fige le sélecteur et le nom
		Étant donné la banque « Jingles » supprimée
		Quand j'ouvre la fiche de la banque « Jingles »
		Alors le bouton de l'emoji et le nom interne éditable sont figés

	# ─── Le plugin ─────────────────────────────────────────

	Plan du scénario: Le plugin ne s'abonne qu'au point de la fiche d'une banque, dans Machin interface
		Quand le plugin de la banque en emoji s'enregistre dans « <binaire> »
		Alors il s'abonne seulement à <points>

		Exemples:
			| binaire          | points                 |
			| Machin_interface | « interface.bank_card » |
			| Machin_webserver  | aucun point            |
			| Machin_player    | aucun point            |
