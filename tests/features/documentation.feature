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
