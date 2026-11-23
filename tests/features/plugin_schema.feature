# language: fr
Fonctionnalité: Le schéma SQL d'un plugin et son installation
	https://github.com/dascritch/machincast/issues/586, ticket enfant de
	https://github.com/dascritch/machincast/issues/348 : les migrations d'un plugin sont dans son migrations/, préfixées
	de son nom, comme ses tables, « horloge__ » ; python -m machincast.plugins.installation, que lance son install.sh,
	seul à créer ses tables, les applique ou les annule après une sauvegarde, sans toucher au cœur. La « base de production » de ces scénarios est la base de test.

	Contexte:
		Étant donné le plugin « horloge », pour « Machin_player », avec la migration « horloge.0001.sonneries » qui crée la table « horloge__sonneries », lisible par « machincast_player »

	Scénario: Installer un plugin applique ses migrations après une sauvegarde de la base, sans toucher au cœur
		Quand le plugin « horloge » est installé
		Alors l'installation réussit
		Et une sauvegarde de la base précède « plugin « horloge » : 1 migration appliquée »
		Et la table « horloge__sonneries » existe, et « machincast_player » peut la lire
		Et les migrations du cœur sont toutes appliquées
		Quand le plugin « horloge » est installé
		Alors l'installation réussit, et dit « plugin « horloge » : rien à faire », sans sauvegarde

	Scénario: Désinstaller un plugin annule ses migrations après une sauvegarde, et ne touche à rien d'autre
		Étant donné le plugin « horloge » installé, et un sonore en base
		Quand le plugin « horloge » est désinstallé
		Alors l'installation réussit
		Et une sauvegarde de la base précède « plugin « horloge » : 1 migration annulée »
		Et la table « horloge__sonneries » n'existe pas
		Et les migrations du cœur sont toutes appliquées, et le sonore est toujours en base

	Scénario: Avec --simulation, l'installation dit ce qu'elle ferait, sans rien faire
		Quand le plugin « horloge » est installé avec --simulation
		Alors l'installation réussit, et dit « plugin « horloge », simulation : sauvegarde, puis application de horloge.0001.sonneries », sans sauvegarde
		Et la table « horloge__sonneries » n'existe pas

	Scénario: Tant que ses tables ne sont pas créées, le plugin est écarté, et la raison dit comment l'installer
		Quand MachinCast vérifie si « horloge » peut être activé
		Alors il ne peut pas l'être, parce que « ses tables ne sont pas créées : activez-le dans les paramètres du service de Machin interface, qui l'installe, ou lancez {plugins}/horloge/install.sh »
		Quand le plugin « horloge » est installé
		Et MachinCast vérifie si « horloge » peut être activé
		Alors il peut l'être

	Scénario: L'onglet « Plugins », qui l'installe à sa validation, ne l'écarte pas pour ses tables à créer
		Quand l'onglet « Plugins » vérifie si « horloge » peut être activé
		Alors il peut l'être

	Scénario: Une table demandée qui manque dit comment l'installer
		Étant donné le plugin « horloge » installé, et un sonore en base
		Et le plugin « horloge » demande la table « horloge_reveils »
		Quand MachinCast vérifie si « horloge » peut être activé
		Alors il ne peut pas l'être, parce que « la table « horloge_reveils » manque : installez le plugin avec {plugins}/horloge/install.sh »

	Plan du scénario: Des migrations fautives refusent l'installation, sans rien faire
		Étant donné que le plugin « horloge » a <défaut>
		Quand le plugin « horloge » est installé
		Alors l'installation est refusée, code 2, parce que « <raison> », sans sauvegarde
		Et la table « horloge__sonneries » n'existe pas

		Exemples:
			| défaut                                       | raison                                                                                                        |
			| la migration « 0002.alarmes »                | migration 0002.alarmes.sql : son nom commence par « horloge. »                                                 |
			| la migration « horloge.0002.alarmes » sans son annulation | migration horloge.0002.alarmes.sql : son annulation horloge.0002.alarmes.rollback.sql manque     |
			| la migration « horloge.0002.alarmes » qui donne à « machincast_indexer » | migration horloge.0002.alarmes.sql : elle donne des droits à machincast_indexer, le rôle d'un binaire où il ne s'accroche pas |
			| la migration « horloge.0002.alarmes » qui crée la table « alarmes » | migration horloge.0002.alarmes.sql : la table « alarmes » commence par « horloge__ » |
			| la migration « horloge.0002.alarmes » qui crée la vue « horloge_alarmes » | migration horloge.0002.alarmes.sql : la table « horloge_alarmes » commence par « horloge__ » |
			| des migrations, mais pas d'install.sh        | ses migrations n'ont pas de install.sh, qui crée ses tables                                                   |

	Scénario: Machin maintenance-db ne crée pas les tables d'un plugin : seul son install.sh les crée
		Étant donné les plugins activés « horloge »
		Quand la maintenance met à jour le schéma de la base
		Alors la table « horloge__sonneries » n'existe pas

	Scénario: Le préfixe d'un plugin au nom composé change son tiret en « _ »
		Alors les tables du plugin « mini-horloge » commencent par « mini_horloge__ »
