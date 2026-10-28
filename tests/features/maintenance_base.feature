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
		Et une sauvegarde datée de la base est dans le répertoire « sauvegardes » de la configuration, lisible par pg_restore
		Et la maintenance a annoncé, dans l'ordre :
			| ligne                                                                                         |
			| sauvegarde de la base machincast_test dans …/sauvegardes/machincast_test-2026-10-22T08-30-00.dump |
			| sauvegarde faite                                                                              |
			| schéma de la base machincast_test à jour                                                      |
			| rôles machincast_lecture, machincast_indexation, machincast_interface endossables par le compte |
			| base machincast_test optimisée (VACUUM ANALYZE)                                               |
			| maintenance terminée                                                                          |
		Et la table « sonores » vient d'être nettoyée par VACUUM, et ses statistiques recalculées

	Scénario: Une migration manquante est appliquée, après la sauvegarde
		Étant donné la dernière migration retirée de la base de test
		Quand je lance « Machin maintenance-db »
		Alors la maintenance se termine avec le code 0
		Et la maintenance a annoncé « schéma de la base machincast_test : 1 migration appliquée »
		Et la base de test a toutes ses migrations

	Scénario: Une base qui a reçu les quinze anciennes migrations est reconnue à jour, sans rien perdre
		https://github.com/dascritch/machincast/issues/314 : ces migrations sont fondues dans le schéma unique.

		Étant donné la base de test marquée comme ayant reçu les quinze anciennes migrations
		Quand je lance « Machin maintenance-db »
		Alors la maintenance se termine avec le code 0
		Et la maintenance a annoncé « base machincast_test : les migrations 0002.evenements-nom-unique à 0015.vocabulaire-silences-blancs, fondues dans 0001.schema-initial, sont oubliées ; ses données ne changent pas »
		Et la maintenance a annoncé « schéma de la base machincast_test à jour »

	Scénario: Une base restée à une ancienne migration intermédiaire est sauvegardée, puis laissée telle quelle
		Étant donné la base de test marquée comme ayant reçu les anciennes migrations jusqu'à « 0009.sonores-audit-demande »
		Quand je lance « Machin maintenance-db »
		Alors la maintenance se termine avec le code 1
		Et une sauvegarde datée de la base est dans le répertoire « sauvegardes » de la configuration, lisible par pg_restore
		Et la maintenance a signalé « schéma impossible à mettre à jour : base machincast_test : ancien schéma, sans la migration 0010.indexation-retire-des-banques ; la mettre à jour avec MachinCast cd2e564 (git checkout cd2e564, puis ./install.sh), puis revenir à la version actuelle, ou la recréer si elle ne contient rien d'utile ; la sauvegarde est faite, rien d'autre »
		Et la maintenance n'a annoncé ni le schéma ni l'optimisation

	Scénario: Les sauvegardes vont dans le répertoire demandé
		Quand je lance « Machin maintenance-db --sauvegardes …/ailleurs »
		Alors une sauvegarde datée de la base est dans le répertoire « ailleurs » de la configuration, lisible par pg_restore

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
		Quand je lance « Machin maintenance-db --garder-ouvert », j'appuie deux fois sur Entrée, puis je ferme le terminal
		Alors la maintenance se termine avec le code 0
		Et la maintenance a dit « Maintenance finie : cette fenêtre reste ouverte, la fermer quand vous voulez. »
		Et la maintenance n'a rendu la main qu'à la fermeture du terminal

	Scénario: Ctrl-C dans le terminal gardé ouvert rend la main sans erreur
		Quand je lance « Machin maintenance-db --garder-ouvert », puis je tape Ctrl-C
		Alors la maintenance se termine avec le code 0

	Scénario: Le wrapper connaît maintenance-db
		Alors « maintenance-db » est un binaire du wrapper, déclaré dans pyproject.toml
