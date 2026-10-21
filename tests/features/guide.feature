# language: fr
Fonctionnalité: Documentation par public
	En tant qu'utilisateur de l'interface graphique, administrateur du poste ou développeur,
	je veux une documentation qui ne s'adresse qu'à moi, claire et sans superflu,
	afin de comprendre très vite ce qui me concerne.

	https://github.com/dascritch/machincast/issues/74, https://github.com/dascritch/machincast/issues/128. Trois
	dossiers, un par public : doc/utilisateur, le métier de l'antenne et l'interface graphique, que le menu
	« Aide → Documentation » ouvre ; doc/administration, avec INSTALL.md, les commandes, la configuration et la
	maintenance ; doc/developpement, la spécification, les règles et le poste de développement. doc/utilisation.md,
	l'ancien guide, n'est plus qu'un index qui renvoie à chacun. Ces scénarios vérifient que chaque guide couvre ce
	que les programmes exposent : un ajout au code sans documentation les fait échouer.

	# ─── Organisation ──────────────────────────────────────────

	Scénario: README.md mène à chaque public, et INSTALL.md au guide d'administration
		Alors README.md contient un lien vers doc/utilisateur/README.md
		Et README.md contient un lien vers doc/administration/README.md
		Et README.md contient un lien vers doc/developpement/README.md
		Et INSTALL.md contient un lien vers doc/administration/README.md

	Scénario: L'ancien guide d'utilisation renvoie à chaque public
		Alors doc/utilisation.md contient un lien vers utilisateur/README.md
		Et doc/utilisation.md contient un lien vers administration/README.md
		Et doc/utilisation.md contient un lien vers developpement/README.md

	Plan du scénario: Chaque page d'un guide figure dans son sommaire
		Alors chaque page de doc/<dossier> est liée depuis doc/<dossier>/README.md

		Exemples:
			| dossier        |
			| utilisateur    |
			| administration |
			| developpement  |

	Scénario: Le guide utilisateur ne fait taper aucune commande
		Alors aucune page du guide utilisateur n'a de bloc de commandes à taper

	# ─── Couverture ────────────────────────────────────────────

	Scénario: Le wrapper est entièrement documenté dans le guide d'administration
		Alors chaque binaire du wrapper est documenté dans le guide d'administration
		Et chaque option du wrapper est documentée dans le guide d'administration
		Et la commande « Machin logs » est documentée dans le guide d'administration

	Plan du scénario: Chaque option d'un binaire est documentée dans le guide d'administration
		Alors chaque option de l'aide de « <executable> » est documentée dans le guide d'administration

		Exemples:
			| executable        |
			| Machin_lecture    |
			| Machin_indexation |
			| Machin_interface  |

	Scénario: Les états des sonores et les verdicts de la vérification sont documentés dans le guide utilisateur
		Alors chaque état d'un sonore est documenté dans le guide utilisateur
		Et chaque verdict de la vérification d'un fichier est documenté dans le guide utilisateur

	Scénario: Les métadonnées lues dans les tags sont documentées dans le guide utilisateur
		Alors chaque clé de métadonnées musicales tenue par l'indexeur est documentée dans le guide utilisateur

	# ─── Liens ─────────────────────────────────────────────────

	Scénario: Les liens relatifs et les ancres de la documentation mènent quelque part
		Alors chaque lien relatif de la documentation mène à un fichier du dépôt
		Et chaque ancre citée par la documentation mène à un titre du fichier visé
