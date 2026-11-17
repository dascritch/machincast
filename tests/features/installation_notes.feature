# language: fr
Fonctionnalité: Votre installation, un document éditable, et le lien de l'équipe
	En tant que technicien radio,
	je veux un lien rapide vers la documentation de notre installation,
	afin d'avoir les informations utiles depuis ce poste, même pressé.

	https://github.com/dascritch/machincast/issues/451. « Votre installation » est un document Markdown, sur le Bureau du
	compte par défaut, ou à l'emplacement de interface.notes. Il se crée depuis un modèle, dans la langue de la session,
	par install.sh à l'installation, ou par l'interface s'il manque, et n'est jamais écrasé. Aide → « Votre
	installation… » l'ouvre toujours dans un éditeur de texte (https://github.com/dascritch/machincast/issues/491) : le
	premier présent de kate, kwrite, gnome-text-editor, gedit, mousepad, xed, pluma et featherpad, sinon l'application
	que le bureau associe aux fichiers texte (text/plain), jamais celle des .md, une visionneuse comme Okular. Aide →
	« Lien de l'équipe… » ouvre dans le navigateur l'adresse de interface.team_link : un cloud local, un Gitlab, un
	Jira… Un chemin qui commence par « …/ » est dans le répertoire du scénario ; xdg-user-dir, xdg-mime, gio et les
	éditeurs y sont des scripts, qui notent leurs arguments.

	Contexte:
		Étant donné l'horloge de l'interface au « 2026-11-17 13:00:00 »

	# ─── Le document et son modèle ─────────────────────────────

	Scénario: Le document se crée sur le Bureau, depuis le modèle de la langue de la session
		Étant donné le Bureau « …/Bureau » du compte
		Quand je crée le document de l'installation, en français
		Alors le document « …/Bureau/Votre installation MachinCast.md » commence par « Complétez ce document, il est à vous ! »
		Et il contient les titres « Contact technique », « Programmation musicale », « Partenariats », « Publicités », « Gestion des émissions pré-enregistrées », « Gestion des directs extérieurs »

	Scénario: En anglais, le document et son modèle sont en anglais
		Étant donné le Bureau « …/Desktop » du compte
		Quand je crée le document de l'installation, en anglais
		Alors le document « …/Desktop/Your MachinCast installation.md » commence par « Fill in this document, it is yours! »

	Scénario: Un document qui existe déjà n'est jamais remplacé
		Étant donné le Bureau « …/Bureau » du compte
		Et le document « …/Bureau/Votre installation MachinCast.md » qui contient « Appeler Paul au 06 00 00 00 00 »
		Quand je crée le document de l'installation, en français
		Alors le document « …/Bureau/Votre installation MachinCast.md » commence par « Appeler Paul au 06 00 00 00 00 »
		Et la création a dit « document de l'installation déjà là : …/Bureau/Votre installation MachinCast.md »

	Scénario: Le document va à l'emplacement de interface.notes
		Étant donné le Bureau « …/Bureau » du compte
		Et la configuration avec interface.notes « …/partage/radio.md »
		Quand je crée le document de l'installation, en français
		Alors le document « …/partage/radio.md » commence par « Complétez ce document, il est à vous ! »

	Scénario: Sans Bureau, le document va dans le répertoire personnel
		Étant donné un poste sans xdg-user-dir
		Quand je crée le document de l'installation, en français
		Alors le document « <personnel>/Votre installation MachinCast.md » commence par « Complétez ce document, il est à vous ! »

	# ─── Le menu « Aide » de l'interface ───────────────────────

	Scénario: « Votre installation… » crée le document s'il manque, et l'ouvre dans kwrite
		Étant donné le Bureau « …/Bureau » du compte
		Et les éditeurs « kwrite », « gnome-text-editor » sur le poste
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Votre installation… » dans le menu « Aide »
		Alors « kwrite » a ouvert « …/Bureau/Votre installation MachinCast.md »
		Et le document « …/Bureau/Votre installation MachinCast.md » commence par « Complétez ce document, il est à vous ! »
		Et la barre d'état annonce « Votre installation : …/Bureau/Votre installation MachinCast.md, créé depuis le modèle. »

	Plan du scénario: Le premier éditeur présent ouvre le document
		Étant donné le Bureau « …/Bureau » du compte
		Et le document « …/Bureau/Votre installation MachinCast.md » qui contient « Notes »
		Et les éditeurs <présents> sur le poste
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Votre installation… » dans le menu « Aide »
		Alors « <éditeur> » a ouvert « …/Bureau/Votre installation MachinCast.md »
		Et la barre d'état annonce « Votre installation : …/Bureau/Votre installation MachinCast.md. »

		Exemples:
			| présents                                | éditeur           |
			| « kate », « kwrite »                    | kate              |
			| « gnome-text-editor », « gedit »        | gnome-text-editor |
			| « featherpad », « mousepad »            | mousepad          |
			| « pluma », « featherpad »               | pluma             |

	Scénario: Sans éditeur connu, l'application des fichiers texte du bureau ouvre le document, jamais celle des .md
		Étant donné le Bureau « …/Bureau » du compte
		Et le document « …/Bureau/Votre installation MachinCast.md » qui contient « Notes »
		Et le bureau associe les fichiers texte à « org.exemple.bloc-notes.desktop », et les .md à Okular
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Votre installation… » dans le menu « Aide »
		Alors gio a lancé « org.exemple.bloc-notes.desktop » sur « …/Bureau/Votre installation MachinCast.md »
		Et la barre d'état annonce « Votre installation : …/Bureau/Votre installation MachinCast.md. »
		Et le navigateur web n'a rien ouvert

	Scénario: Sans aucun éditeur, la barre d'état le dit, et donne le chemin du document
		Étant donné le Bureau « …/Bureau » du compte
		Et le document « …/Bureau/Votre installation MachinCast.md » qui contient « Notes »
		Et les éditeurs « kwrite » sur le poste
		Quand le poste n'a plus d'éditeur de texte
		Et la fenêtre de l'interface s'ouvre
		Et je choisis « Votre installation… » dans le menu « Aide »
		Alors la barre d'état annonce « Votre installation : aucun éditeur de texte trouvé ; le document est …/Bureau/Votre installation MachinCast.md. »
		Et le navigateur web n'a rien ouvert

	Scénario: Sans adresse, « Lien de l'équipe… » est inactive, et son infobulle dit où la donner
		Quand la fenêtre de l'interface s'ouvre
		Alors le menu « Aide » a les entrées :
			| entrée                | état     | raccourci | infobulle                                                                               |
			| Documentation         | active   |           |                                                                                         |
			| Votre installation…   | active   |           |                                                                                         |
			| Lien de l'équipe…     | inactive |           | Adresse à donner dans Fichier → Préférences de l'interface…, page Interface.            |
			| Signaler un problème… | active   |           |                                                                                         |
			| Version               | active   |           |                                                                                         |

	Scénario: « Lien de l'équipe… » ouvre l'adresse de interface.team_link dans le navigateur
		Étant donné la configuration de l'interface avec interface.team_link « https://cloud.radio.example/antenne »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Lien de l'équipe… » dans le menu « Aide »
		Alors le navigateur web a ouvert « https://cloud.radio.example/antenne »

	# ─── Préférences de l'interface ────────────────────────────

	Scénario: La page « Interface » règle le document et le lien de l'équipe, et les donne
		Quand la fenêtre des préférences de l'interface s'ouvre sur le document « /srv/radio/notes.md » et le lien « https://gitlab.radio.example »
		Alors elle montre le document « /srv/radio/notes.md » et le lien « https://gitlab.radio.example »
		Quand j'y saisis le document « /srv/radio/antenne.md » et le lien « https://jira.radio.example »
		Et j'y clique sur « OK »
		Alors elle a donné le document « /srv/radio/antenne.md » et le lien « https://jira.radio.example »

	Scénario: Un document laissé vide reprend celui du Bureau, et un lien vide n'en donne aucun
		Quand la fenêtre des préférences de l'interface s'ouvre sur le document « /srv/radio/notes.md » et le lien « https://gitlab.radio.example »
		Et j'y saisis le document «  » et le lien «  »
		Et j'y clique sur « OK »
		Alors elle n'a donné ni document ni lien

	Scénario: Le document et le lien réglés vont dans la section [interface]
		Étant donné les préférences seront réglées avec le document « /srv/radio/notes.md » et le lien « https://gitlab.radio.example »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors le fichier de configuration contient la ligne « notes = "/srv/radio/notes.md" »
		Et le fichier de configuration contient la ligne « team_link = "https://gitlab.radio.example" »

	# ─── install.sh ────────────────────────────────────────────

	Scénario: install.sh crée le document de l'installation, sans jamais le remplacer
		Alors install.sh crée le document de l'installation par « python -m machincast.notes create », avec sa configuration
