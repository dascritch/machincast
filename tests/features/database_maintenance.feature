# language: fr
Fonctionnalité: Maintenance de la base de données
	En tant que technicien radio,
	je veux une façon simplifiée de faire la maintenance de la base de données,
	afin de ne pas avoir à connaître l'effroi de mal taper une commande dans psql.

	https://github.com/dascritch/machincast/issues/127. « Machin maintenance-db » enchaîne trois étapes sur la base de
	production de la configuration : il la sauvegarde (pg_dump) dans un fichier daté, vérifie son schéma (migrations
	manquantes appliquées, rôles de MachinCast endossables par le compte), puis l'optimise (VACUUM ANALYZE). Une
	sauvegarde qui échoue arrête tout : rien n'est modifié sans sauvegarde. Les scénarios travaillent sur la base de
	test, désignée comme base de production d'une configuration du scénario ; les sauvegardes vont dans son répertoire.

	Contexte:
		Étant donné une configuration dont la base de production est la base de test

	Scénario: La maintenance sauvegarde la base, vérifie son schéma, puis l'optimise
		Quand je lance « Machin maintenance-db »
		Alors la maintenance se termine avec le code 0
		Et une sauvegarde datée de la base est dans le répertoire « sauvegardes » de la configuration, lisible par le pg_restore du serveur
		Et la maintenance a annoncé, dans l'ordre :
			| ligne                                                                                         |
			| sauvegarde de la base machincast_test dans …/sauvegardes/machincast_test-2026-10-22T08-30-00.dump |
			| sauvegarde faite                                                                              |
			| schéma de la base machincast_test à jour                                                      |
			| rôles machincast_player, machincast_indexer, machincast_interface endossables par le compte |
			| base machincast_test optimisée (VACUUM ANALYZE)                                               |
			| maintenance terminée                                                                          |
		Et la table « sounds » vient d'être nettoyée par VACUUM, et ses statistiques recalculées

	Scénario: Une migration manquante est appliquée, après la sauvegarde
		Étant donné la dernière migration retirée de la base de test
		Quand je lance « Machin maintenance-db »
		Alors la maintenance se termine avec le code 0
		Et la maintenance a annoncé « schéma de la base machincast_test : 1 migration appliquée »
		Et la base de test a toutes ses migrations

	Scénario: Les sauvegardes vont dans le répertoire demandé
		Quand je lance « Machin maintenance-db --backups …/ailleurs »
		Alors une sauvegarde datée de la base est dans le répertoire « ailleurs » de la configuration, lisible par le pg_restore du serveur

	Plan du scénario: La sauvegarde est faite par le pg_dump de la version du serveur, sinon par celui du PATH
		https://github.com/dascritch/machincast/issues/384 : le pg_dump du PATH est le plus récent installé, et sa
		sauvegarde ne se relirait pas avec le pg_restore d'un serveur plus ancien. Ici, le PATH mène à celui de la 16.
		Étant donné les programmes de PostgreSQL 16 et 18 installés
		Alors pour un serveur <serveur>, la maintenance prend « <pg_dump> »

		Exemples:
			| serveur | pg_dump           |
			| 16      | …/16/bin/pg_dump  |
			| 18      | …/18/bin/pg_dump  |
			| 17      | …/16/bin/pg_dump  |

	Scénario: Sans pg_dump, rien n'est fait, ni migration ni optimisation
		Étant donné pg_dump absent du poste
		Quand je lance « Machin maintenance-db »
		Alors la maintenance se termine avec le code 1
		Et la maintenance a signalé « sauvegarde impossible : pg_dump introuvable, installer postgresql-client ; maintenance arrêtée, rien n'a été modifié »
		Et la maintenance n'a annoncé ni le schéma ni l'optimisation

	Scénario: Un rôle que le compte ne peut pas endosser est signalé, avec la commande qui l'autorise, et la base est quand même optimisée
		Étant donné un rôle « machincast_inconnu » attendu en plus par MachinCast
		Quand je lance « Machin maintenance-db »
		Alors la maintenance se termine avec le code 1
		Et la maintenance a signalé « rôle machincast_inconnu : absent du serveur, ou non endossable par le compte ; à faire par un administrateur : sudo -u postgres psql -c "CREATE ROLE machincast_inconnu NOLOGIN" ; sudo -u postgres psql -c "GRANT machincast_inconnu TO <compte> WITH INHERIT FALSE, SET TRUE" »
		Et la maintenance a annoncé « base machincast_test optimisée (VACUUM ANALYZE) »
		Et la maintenance a annoncé « maintenance terminée, avec des anomalies »

	Scénario: Dans un terminal, la maintenance le garde ouvert jusqu'à sa fermeture, même après Entrée
		Quand je lance « Machin maintenance-db --keep-open », j'appuie deux fois sur Entrée, puis je ferme le terminal
		Alors la maintenance se termine avec le code 0
		Et la maintenance a dit « Maintenance finie : cette fenêtre reste ouverte, la fermer quand vous voulez. »
		Et la maintenance n'a rendu la main qu'à la fermeture du terminal

	Scénario: Ctrl-C dans le terminal gardé ouvert rend la main sans erreur
		Quand je lance « Machin maintenance-db --keep-open », puis je tape Ctrl-C
		Alors la maintenance se termine avec le code 0

	Scénario: Le wrapper connaît maintenance-db
		Alors « maintenance-db » est un binaire du wrapper, déclaré dans pyproject.toml
