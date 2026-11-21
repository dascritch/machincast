# language: fr
Fonctionnalité: Comptes de l'intranet et de l'API, dans l'onglet « API »
	En tant que responsable de l'antenne,
	je veux créer, dans un onglet « API » de l'interface, les comptes de ceux qui pourront se connecter à l'intranet et
	à l'API, avec un mot de passe et un rôle,
	afin de décider qui peut consulter l'antenne à distance, et de le retirer à tout moment.

	https://github.com/dascritch/machincast/issues/537, ticket enfant de
	https://github.com/dascritch/machincast/issues/524. Un compte a un nom, qui se tape dans une adresse
	(https://nom@adresse), un mot de passe d'au moins 12 caractères, dont la base ne garde que l'empreinte scrypt salée,
	et un rôle : « consulter », l'intranet et l'API en lecture, ou « actions API », de même et les actions à venir.

	Contexte:
		Étant donné l'horloge de l'interface au « 2026-11-20 10:00:00 »

	Scénario: Le menu « Affichage » ouvre l'onglet « API », vide au départ
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet API » dans le menu « Affichage »
		Alors l'onglet ouvert est « API »
		Et les comptes de l'onglet API sont :
			| utilisateur | rôle | état |
		Et les boutons « Changer le mot de passe… », « Désactiver » et « ❌ Supprimer… » de l'onglet API sont grisés

	Scénario: Créer un compte n'en garde que l'empreinte du mot de passe
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet API » dans le menu « Affichage »
		Et je crée le compte « regie », mot de passe « tisane-au-micro », rôle « consulter »
		Alors les comptes de l'onglet API sont :
			| utilisateur | rôle      | état  |
			| regie       | consulter | actif |
		Et le compte « regie » est choisi dans l'onglet API
		Et la barre d'état annonce « Compte regie créé. »
		Et la base garde, pour « regie », l'empreinte de « tisane-au-micro », jamais le mot de passe lui-même

	Plan du scénario: La fenêtre d'un nouveau compte refuse une saisie qui ne convient pas, et dit pourquoi
		Étant donné les comptes de l'intranet :
			| nom   | mot de passe    | rôle      | état  |
			| regie | tisane-au-micro | consulter | actif |
		Quand la fenêtre de l'interface s'ouvre
		Et je saisis dans la fenêtre d'un nouveau compte « <nom> », « <mot de passe> », confirmé par « <confirmation> », puis OK
		Alors la fenêtre du compte reste ouverte, et dit « <refus> »

		Exemples:
			| nom         | mot de passe    | confirmation    | refus                                                                                |
			|             | tisane-au-micro | tisane-au-micro | Le nom est obligatoire.                                                              |
			| régie       | tisane-au-micro | tisane-au-micro | Le nom ne prend que des lettres sans accent, des chiffres, le point, le tiret et le souligné. |
			| la regie    | tisane-au-micro | tisane-au-micro | Le nom ne prend que des lettres sans accent, des chiffres, le point, le tiret et le souligné. |
			| regie       | tisane-au-micro | tisane-au-micro | Un autre compte porte déjà ce nom.                                                   |
			| technique   | court           | court           | Le mot de passe demande au moins 12 caractères.                                      |
			| technique   | tisane-au-micro | tisane-au-micra | Le mot de passe et sa confirmation diffèrent.                                        |

	Scénario: La fenêtre d'un nouveau compte accepte une saisie qui convient
		Quand la fenêtre de l'interface s'ouvre
		Et je saisis dans la fenêtre d'un nouveau compte « technique.2 », « tisane-au-micro », confirmé par « tisane-au-micro », puis OK
		Alors la fenêtre du compte est acceptée

	Scénario: Changer le rôle d'un compte
		Étant donné les comptes de l'intranet :
			| nom   | mot de passe    | rôle      | état  |
			| regie | tisane-au-micro | consulter | actif |
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet API » dans le menu « Affichage »
		Et je choisis le compte « regie » dans l'onglet API
		Et je donne au compte le rôle « actions API »
		Alors les comptes de l'onglet API sont :
			| utilisateur | rôle        | état  |
			| regie       | actions API | actif |
		Et la barre d'état annonce « regie a désormais le rôle actions API. »

	Scénario: Changer le mot de passe d'un compte
		Étant donné les comptes de l'intranet :
			| nom   | mot de passe    | rôle      | état  |
			| regie | tisane-au-micro | consulter | actif |
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet API » dans le menu « Affichage »
		Et je choisis le compte « regie » dans l'onglet API
		Et je change le mot de passe du compte pour « café-du-matin-42 »
		Alors la base garde, pour « regie », l'empreinte de « café-du-matin-42 », jamais le mot de passe lui-même
		Et la barre d'état annonce « Mot de passe de regie changé. »

	Scénario: Désactiver un compte, puis le réactiver
		Étant donné les comptes de l'intranet :
			| nom   | mot de passe    | rôle      | état  |
			| regie | tisane-au-micro | consulter | actif |
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet API » dans le menu « Affichage »
		Et je choisis le compte « regie » dans l'onglet API
		Et je clique sur « Désactiver »
		Alors les comptes de l'onglet API sont :
			| utilisateur | rôle      | état       |
			| regie       | consulter | désactivé  |
		Et la barre d'état annonce « regie désactivé : il ne peut plus se connecter. »
		Quand je clique sur « Réactiver »
		Alors les comptes de l'onglet API sont :
			| utilisateur | rôle      | état  |
			| regie       | consulter | actif |

	# ─── Un mot de passe qui a fuité (https://github.com/dascritch/machincast/issues/548) ───

	Scénario: Changer le mot de passe met fin aux sessions du compte, et à elles seules
		Étant donné les comptes de l'intranet :
			| nom       | mot de passe    | rôle      | état  |
			| regie     | tisane-au-micro | consulter | actif |
			| stagiaire | cafe-du-matin-1 | consulter | actif |
		Et « regie » a une session valide et une session à valider
		Et « stagiaire » a une session valide et une session à valider
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet API » dans le menu « Affichage »
		Et je choisis le compte « regie » dans l'onglet API
		Et je change le mot de passe du compte pour « café-du-matin-42 »
		Alors la barre d'état annonce « Mot de passe de regie changé. 2 sessions terminées. »
		Et les sessions de « regie » sont toutes invalides
		Et « stagiaire » a encore 1 session valide et 1 session à valider

	Scénario: Désactiver un compte met fin à ses sessions, et le réactiver n'en fait revivre aucune
		Étant donné les comptes de l'intranet :
			| nom   | mot de passe    | rôle      | état  |
			| regie | tisane-au-micro | consulter | actif |
		Et « regie » a une session valide et une session à valider
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet API » dans le menu « Affichage »
		Et je choisis le compte « regie » dans l'onglet API
		Et je clique sur « Désactiver »
		Alors la barre d'état annonce « regie désactivé : il ne peut plus se connecter. 2 sessions terminées. »
		Quand je clique sur « Réactiver »
		Alors la barre d'état annonce « regie réactivé. »
		Et les sessions de « regie » sont toutes invalides

	Scénario: Supprimer un compte, après confirmation
		Étant donné les comptes de l'intranet :
			| nom   | mot de passe    | rôle      | état  |
			| regie | tisane-au-micro | consulter | actif |
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet API » dans le menu « Affichage »
		Et je choisis le compte « regie » dans l'onglet API
		Et je supprime le compte, en répondant « ❌ Supprimer »
		Alors la question de suppression, intitulée « Supprimer un compte », a dit :
			| texte                                                                                      |
			| Supprimer le compte de l'intranet regie ? Il ne pourra plus se connecter, et ses sessions prendront fin. |
		Et les comptes de l'onglet API sont :
			| utilisateur | rôle | état |
		Et la barre d'état annonce « Compte regie supprimé. »

	Scénario: Annuler la suppression d'un compte le garde
		Étant donné les comptes de l'intranet :
			| nom   | mot de passe    | rôle      | état  |
			| regie | tisane-au-micro | consulter | actif |
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet API » dans le menu « Affichage »
		Et je choisis le compte « regie » dans l'onglet API
		Et je supprime le compte, en répondant « Annuler »
		Alors les comptes de l'onglet API sont :
			| utilisateur | rôle      | état  |
			| regie       | consulter | actif |

	Scénario: L'onglet « API » se rouvre au lancement suivant
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet API » dans le menu « Affichage »
		Et la fenêtre de l'interface se ferme, puis s'ouvre de nouveau
		Alors l'onglet ouvert est « API »
