# language: fr
Fonctionnalité: Documentation d'installation et definition of done
	En tant qu'administrateur du poste de diffusion,
	je veux un INSTALL.md fidèle à install.sh et aux commandes réelles de MachinCast,
	afin d'installer et de mettre à jour un poste sans connaître le code.

	INSTALL.md n'est pas exécuté par ces scénarios : ils vérifient que ce qu'il cite existe et reste cohérent
	avec install.sh et CLAUDE.md (https://github.com/dascritch/machincast/issues/71).

	# ─── INSTALL.md ────────────────────────────────────────────

	Scénario: README.md mène à INSTALL.md
		Alors README.md contient un lien vers INSTALL.md

	Scénario: INSTALL.md, install.sh et CLAUDE.md demandent les mêmes paquets apt
		Alors la première commande apt d'INSTALL.md installe les paquets d'install.sh
		Et la première commande apt de CLAUDE.md installe les paquets d'install.sh

	Scénario: Chaque paquet apt est expliqué
		Alors chaque paquet apt d'install.sh figure dans un tableau d'INSTALL.md

	Scénario: Les rôles de MachinCast sont accordés partout de la même façon, sans héritage des droits
		Alors INSTALL.md, install.sh et CLAUDE.md accordent les trois rôles par le même GRANT
		Et aucune commande createuser d'INSTALL.md ne donne de droit particulier

	Scénario: Les commandes citées par INSTALL.md existent
		Alors chaque option d'install.sh citée dans INSTALL.md figure dans son aide
		Et chaque commande Machin citée dans INSTALL.md appelle un binaire et des options qui existent
		Et chaque étape de machincast.installation citée dans INSTALL.md existe

	Scénario: Les liens relatifs et les ancres d'INSTALL.md mènent quelque part
		Alors chaque lien relatif d'INSTALL.md mène à un fichier du dépôt
		Et chaque ancre citée par INSTALL.md mène à un titre du fichier visé

	# ─── Definition of done ────────────────────────────────────

	Scénario: Un ticket n'est terminé qu'avec sa documentation pour les humains
		Alors les règles de développement ont une section « Definition of done » qui exige la documentation humaine
		Et les impératifs de CLAUDE.md renvoient à la definition of done
		Et le modèle de description de PR comporte la case « documentation humaine à jour »

	Scénario: Les informations des versions publiées concordent : nouveautés, RELEASE.md, README.md et pyproject.toml
		https://github.com/dascritch/machincast/issues/208 : chaque version publiée a sa section, « ## <version> — <date> »,
		la plus récente d'abord, dans les nouveautés de l'interface et dans RELEASE.md, aux mêmes dates ; README.md donne la
		dernière, « **Version <version>**, publiée le <date> », et pyproject.toml n'a pas de version plus ancienne. Tant
		qu'aucune version n'est publiée, il n'y a rien à faire concorder.
		Alors les nouveautés de l'interface ont une section par version, de la plus récente à la plus ancienne
		Et RELEASE.md a les mêmes versions, aux mêmes dates, dans le même ordre
		Et README.md donne la dernière version publiée et sa date
		Et la version de pyproject.toml n'est pas plus ancienne que la dernière publiée
