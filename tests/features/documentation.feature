# language: fr
Fonctionnalité: Documentation d'installation et definition of done
	En tant qu'administrateur du poste de diffusion,
	je veux un INSTALL.md fidèle à install.sh et aux commandes réelles de MachinCast,
	afin d'installer et de mettre à jour un poste sans connaître le code.

	INSTALL.md n'est pas exécuté par ces scénarios : ils vérifient que ce qu'il cite existe et reste cohérent
	avec install.sh et CLAUDE.md (https://github.com/dascritch/machincast/issues/71).

	# ─── Documentation par langue (https://github.com/dascritch/machincast/issues/355) ───

	Scénario: Les documents de premier niveau sont en anglais, avec leur source française, et doc est rangé par langue
		Alors chaque document de premier niveau est en anglais, avec sa source française, et chacun mène à l'autre
		Et doc ne contient que des répertoires de langue, dont la source française doc/fr
		Et chaque lien relatif des documents de premier niveau et de doc/fr mène à un fichier du dépôt

	# ─── INSTALL.md ────────────────────────────────────────────

	Plan du scénario: <readme> mène à <install>
		Alors <readme> contient un lien vers <install>

		Exemples:
			| readme       | install       |
			| README.md    | INSTALL.md    |
			| README.fr.md | INSTALL.fr.md |

	Scénario: CLAUDE.md et install.sh demandent les mêmes paquets apt
		Alors la première commande apt de CLAUDE.md installe les paquets d'install.sh

	Plan du scénario: <install> est fidèle à install.sh et aux commandes de MachinCast
		INSTALL.md, en anglais, et INSTALL.fr.md, sa source française, citent les mêmes commandes.

		Alors la première commande apt de <install> installe les paquets d'install.sh
		Et chaque paquet apt d'install.sh figure dans un tableau de <install>
		Et <install>, install.sh et CLAUDE.md accordent les trois rôles par le même GRANT
		Et aucune commande createuser de <install> ne donne de droit particulier
		Et chaque option d'install.sh citée dans <install> figure dans son aide
		Et chaque commande Machin citée dans <install> appelle un binaire et des options qui existent
		Et chaque étape de machincast.installation citée dans <install> existe
		Et chaque lien relatif de <install> mène à un fichier du dépôt
		Et chaque ancre citée par <install> mène à un titre du fichier visé

		Exemples:
			| install       |
			| INSTALL.md    |
			| INSTALL.fr.md |

	# ─── Definition of done ────────────────────────────────────

	Scénario: Un ticket n'est terminé qu'avec sa documentation pour les humains
		Alors les règles de développement ont une section « Definition of done » qui exige la documentation humaine
		Et les impératifs de CLAUDE.md renvoient à la definition of done
		Et le modèle de description de PR comporte la case « documentation humaine à jour »

	Scénario: Les informations des versions publiées concordent : nouveautés, RELEASE.md, README.md, leurs sources françaises, et pyproject.toml
		https://github.com/dascritch/machincast/issues/208 : chaque version publiée a sa section, « ## <version> — <date> »,
		la plus récente d'abord, dans les nouveautés de l'interface, en anglais et en français
		(https://github.com/dascritch/machincast/issues/369), et dans RELEASE.md, aux mêmes dates ; README.md donne la
		dernière, « **Version <version>**, publiée le <date> », et pyproject.toml n'a pas de version plus ancienne. Tant
		qu'aucune version n'est publiée, il n'y a rien à faire concorder.
		Alors les nouveautés de l'interface ont une section par version, de la plus récente à la plus ancienne
		Et RELEASE.md a les mêmes versions, aux mêmes dates, dans le même ordre
		Et RELEASE.fr.md a les mêmes versions, aux mêmes dates, dans le même ordre
		Et src/machincast/interface/news.fr.md a les mêmes versions, aux mêmes dates, dans le même ordre
		Et README.md donne la dernière version publiée et sa date
		Et README.fr.md donne la dernière version publiée et sa date
		Et la version de pyproject.toml n'est pas plus ancienne que la dernière publiée

	Scénario: L'archive d'une release contient de quoi installer MachinCast, sous un répertoire au numéro de la version
		https://github.com/dascritch/machincast/issues/41 : l'archive se fait par git archive, comme le décrit
		doc/fr/developpement/release.md ; elle est faite ici du commit en cours.
		Quand je fais l'archive de la version de pyproject.toml
		Alors l'archive a pour répertoire « machincast-<version> »
		Et l'archive contient « install.sh », exécutable
		Et l'archive contient « pyproject.toml », « bin/Machin », « src/machincast/migrations/0001.initial-schema.sql », « src/machincast/interface/news.md », « src/machincast/interface/news.fr.md », « machincast.exemple.toml »
		Et l'archive contient « README.md », « INSTALL.md », « RELEASE.md », « TROUBLESHOOTING.md », « LICENSE », « doc/fr/utilisateur/README.md », « doc/fr/administration/README.md »
		Et l'archive contient « README.fr.md », « INSTALL.fr.md », « RELEASE.fr.md », « TROUBLESHOOTING.fr.md », « CONTRIBUTION.md », « CONTRIBUTION.fr.md »
