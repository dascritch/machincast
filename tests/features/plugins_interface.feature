# language: fr
Fonctionnalité: Les plugins dans l'interface : l'onglet « Plugins » et le menu « Plugins »
	En tant que responsable du poste,
	je veux voir la liste des plugins et les activer depuis l'interface,
	afin de choisir les fonctions de ma radio sans éditer machincast.toml.

	https://github.com/dascritch/machincast/issues/587, ticket enfant de
	https://github.com/dascritch/machincast/issues/348. L'onglet « Plugins » des « Paramètres du service de
	diffusion… » liste chaque plugin du répertoire des plugins ; sa case l'active ou le désactive, dans [plugins]
	enabled. Le menu « Plugins » de la fenêtre principale ouvre la fenêtre de chaque plugin activé. Les plugins de ces
	scénarios sont créés dans un répertoire temporaire, désigné par [plugins] directory.

	Contexte:
		Étant donné le plugin « horloge » 1.2.0, pour « Machin_interface », décrit « Speaks the time » et en français « Dit l'heure »
		Et le plugin « cartes » 0.3, pour « Machin_intranet », décrit « Cards » et en français « Des cartes »
		Et le plugin « cartes » demande le plugin « absent » >=1
		Et le plugin « casse » dont le manifest a un JSON illisible

	Scénario: L'onglet « Plugins » déplie chaque plugin qui ne peut pas être activé, avec ses raisons
		Étant donné les plugins activés « horloge »
		Quand j'ouvre les paramètres du service
		Alors ils ont l'onglet « Plugins »
		Et l'onglet « Plugins » montre, un élément dépliable par plugin :
			| case      | plugin  | version | état          | déplié |
			| sans case | cartes  | 0.3     | pas activable | oui    |
			| sans case | casse   |         | pas activable | oui    |
			| cochée    | horloge | 1.2.0   | activable     | non    |
		Et le plugin « cartes », déplié, dit :
			| Des cartes                                              |
			| Il ne peut pas être activé :                            |
			| • il demande le plugin « absent », qui n'est pas activé |
		Et le plugin « casse », déplié, dit :
			| Il ne peut pas être activé : |
			| • manifest.json illisible    |
		Et le plugin « horloge », déplié, dit :
			| Dit l'heure |
		Et l'onglet « Plugins » ne demande pas de relancer

	Scénario: Les préférences de l'interface n'ont pas d'onglet « Plugins »
		Quand j'ouvre les préférences de l'interface
		Alors elles n'ont pas l'onglet « Plugins »

	Scénario: Cocher un plugin l'active, et demande de relancer la diffusion, l'indexation et l'interface
		Quand j'ouvre les paramètres du service
		Et je coche le plugin « horloge »
		Alors les paramètres activent les plugins « horloge »
		Et l'onglet « Plugins » demande de relancer la diffusion, l'indexation et l'interface
		Et ce changement redémarre le service de diffusion

	Scénario: Décocher un plugin le désactive, même s'il ne peut plus être activé
		Étant donné les plugins activés « cartes », « horloge »
		Quand j'ouvre les paramètres du service
		Et je décoche le plugin « cartes »
		Alors les paramètres activent les plugins « horloge »

	Scénario: Un plugin activé qui n'est plus dans le répertoire se désactive
		Étant donné les plugins activés « horloge », « disparu »
		Quand j'ouvre les paramètres du service
		Alors le plugin « disparu », déplié, dit :
			| Il ne peut pas être activé :        |
			| • absent du répertoire des plugins |
		Quand je décoche le plugin « disparu »
		Alors les paramètres activent les plugins « horloge »

	# ─── L'installation à la validation ──────────────────
	# Les tables d'un plugin sont créées par MachinCast (machincast.plugins.installation), après une sauvegarde de la
	# base : à la validation des paramètres, chaque plugin qu'ils activent s'installe, par son install.sh, ou, sans lui,
	# par l'installation commune.

	Scénario: Un plugin dont les tables sont à créer est activable, et l'onglet dit qu'elles le seront à la validation
		Étant donné le plugin « horloge » a la migration « horloge.0001.sonneries » qui crée la table « horloge_sonneries »
		Et la base de production des scénarios est la base de test
		Quand j'ouvre les paramètres du service
		Alors le plugin « horloge », déplié, dit :
			| Dit l'heure                                                                                       |
			| Ses tables seront créées à la validation des paramètres, après une sauvegarde de la base. |
		Et l'onglet « Plugins » a « horloge » activable

	Scénario: À la validation, un plugin activé lance son install.sh, avec la sauvegarde et la configuration
		Étant donné le plugin « horloge » a un install.sh qui note ses arguments
		Quand je valide les paramètres en activant « horloge »
		Alors l'install.sh de « horloge » a reçu la sauvegarde et la configuration
		Et l'installation dit « plugin « horloge » installé »

	Scénario: Sans install.sh, MachinCast installe le plugin : ses tables, après une sauvegarde de la base
		Étant donné le plugin « horloge » a la migration « horloge.0001.sonneries » qui crée la table « horloge_sonneries »
		Et la base de production des scénarios est la base de test
		Quand je valide les paramètres en activant « horloge »
		Alors l'installation dit « plugin « horloge » installé »
		Et la table « horloge_sonneries » existe, après une sauvegarde de la base

	Scénario: Un install.sh en échec le dit, avec sa dernière ligne
		Étant donné le plugin « horloge » a un install.sh qui échoue en disant « paquet manquant »
		Quand je valide les paramètres en activant « horloge »
		Alors l'installation dit « installation du plugin « horloge » en échec, code 3 : paquet manquant »

	Scénario: Désactiver un plugin n'installe rien, et ne retire pas ses tables
		Étant donné les plugins activés « horloge »
		Quand j'ouvre les paramètres du service
		Et je décoche le plugin « horloge »
		Et je valide les paramètres
		Alors la validation n'installe aucun plugin

	Scénario: Les plugins activés s'écrivent dans [plugins] enabled, leurs réglages restent
		Étant donné un fichier de configuration avec « [plugins.horloge] » et « couleur = "rouge" # la couleur »
		Quand j'enregistre les plugins activés « horloge », « cartes »
		Alors le fichier active les plugins « horloge », « cartes »
		Et le fichier garde « couleur = "rouge" # la couleur »

	Scénario: Sans plugin activé, le fichier ne gagne pas de section [plugins]
		Étant donné un fichier de configuration sans section [plugins]
		Quand j'enregistre les plugins activés aucun
		Alors le fichier n'a pas de section [plugins]

	Scénario: Le menu « Plugins » a une entrée par plugin activé, qui ouvre sa fenêtre
		Étant donné les plugins activés « horloge »
		Et le plugin « horloge » apporte à sa fenêtre le réglage « Sonner les heures »
		Quand l'interface charge ses plugins
		Alors le menu « Plugins » propose « horloge… »
		Quand j'ouvre la fenêtre du plugin « horloge »
		Alors elle montre « horloge », « 1.2.0 », « Dit l'heure » et le réglage « Sonner les heures »

	Scénario: Un plugin sans réglages le dit dans sa fenêtre
		Étant donné les plugins activés « horloge »
		Quand l'interface charge ses plugins
		Et j'ouvre la fenêtre du plugin « horloge »
		Alors elle montre « horloge », « 1.2.0 », « Dit l'heure », et dit « Ce plugin n'apporte pas de réglages ici. »

	Scénario: Sans plugin activé, le menu « Plugins » le dit
		Quand l'interface charge ses plugins
		Alors le menu « Plugins » propose seulement « Aucun plugin activé », grisé
