# language: fr
Fonctionnalité: Export et réimportation de la base de données
	En tant que responsable technique,
	je veux exporter la base de données, et la réimporter sur un poste neuf,
	afin de redémarrer plus vite après une panne, sur ce poste ou sur un autre.

	https://github.com/dascritch/machincast/issues/347, plan de reprise d'activité. « Machin backup-db » sauvegarde la
	base de production (pg_dump, format personnalisé de PostgreSQL), comme la première étape de « Machin
	maintenance-db », dans un fichier daté du répertoire des sauvegardes (backup.directory, le répertoire personnel du
	compte par défaut). « Machin restore-db FICHIER » la réimporte dans une base de production vide, comme install.sh
	vient de la créer, après avoir vérifié que le fichier est une sauvegarde de MachinCast, d'une version qui n'est pas
	plus récente que celle installée ; puis il applique les migrations qui lui manquent. Une base qui n'est pas vide n'est
	jamais écrasée. Les scénarios travaillent sur la base de test, désignée comme base de production d'une configuration
	du scénario, ses sauvegardes dans son répertoire.

	Contexte:
		Étant donné une configuration dont la base de production est la base de test
		Et la séquence « Fil du matin » en base

	# ─── Export : Machin backup-db ───

	Scénario: L'export sauvegarde la base dans un fichier daté du répertoire des sauvegardes
		Quand je lance « Machin backup-db »
		Alors la commande se termine avec le code 0
		Et une sauvegarde datée de la base est dans le répertoire « sauvegardes » de la configuration, lisible par le pg_restore du serveur
		Et la commande a annoncé, dans l'ordre :
			| ligne                                                                                         |
			| sauvegarde de la base machincast_test dans …/sauvegardes/machincast_test-2026-10-22T08-30-00.dump |
			| sauvegarde faite                                                                              |

	Scénario: L'export va dans le répertoire demandé
		Quand je lance « Machin backup-db --backups …/ailleurs »
		Alors une sauvegarde datée de la base est dans le répertoire « ailleurs » de la configuration, lisible par le pg_restore du serveur

	Scénario: Sans pg_dump, l'export échoue et le dit
		Étant donné pg_dump absent du poste
		Quand je lance « Machin backup-db »
		Alors la commande se termine avec le code 1
		Et la commande a signalé « sauvegarde impossible : pg_dump introuvable, installer postgresql-client »

	# ─── Réimportation : Machin restore-db ───

	Scénario: Une sauvegarde se réimporte dans une base vide, avec ses données
		Étant donné une sauvegarde de la base de test
		Et la base de test vidée, comme install.sh vient de la créer
		Quand je lance « Machin restore-db <sauvegarde> »
		Alors la commande se termine avec le code 0
		Et la séquence « Fil du matin » est en base
		Et la base de test a toutes ses migrations
		Et la commande a annoncé, dans l'ordre :
			| ligne                                                                  |
			| réimportation de …/sauvegardes/machincast_test-2026-10-22T08-30-00.dump dans la base machincast_test |
			| réimportation faite                                                    |
			| schéma de la base machincast_test à jour                               |

	Scénario: Une sauvegarde d'une version plus ancienne reçoit les migrations qui lui manquent
		Étant donné la dernière migration retirée de la base de test
		Et une sauvegarde de la base de test
		Et la base de test vidée, comme install.sh vient de la créer
		Quand je lance « Machin restore-db <sauvegarde> »
		Alors la commande se termine avec le code 0
		Et la commande a annoncé « schéma de la base machincast_test : 1 migration appliquée »
		Et la base de test a toutes ses migrations

	Scénario: Une sauvegarde d'une version plus récente de MachinCast est refusée
		Étant donné une migration « 9999.futur » notée en base, inconnue de cette version
		Et une sauvegarde de la base de test
		Et la base de test vidée, comme install.sh vient de la créer
		Quand je lance « Machin restore-db <sauvegarde> »
		Alors la commande se termine avec le code 1
		Et la commande a signalé « <sauvegarde> vient d'une version plus récente de MachinCast (migrations inconnues : 9999.futur) : mettre d'abord MachinCast à jour »
		Et la base de test est toujours vide

	Scénario: Un fichier qui n'est pas une sauvegarde de MachinCast est refusé
		Étant donné le fichier « pas-une-sauvegarde.dump », qui n'est pas une sauvegarde
		Et la base de test vidée, comme install.sh vient de la créer
		Quand je lance « Machin restore-db …/pas-une-sauvegarde.dump »
		Alors la commande se termine avec le code 1
		Et la commande a signalé un fichier « …/pas-une-sauvegarde.dump » qui n'est pas une sauvegarde de MachinCast
		Et la base de test est toujours vide

	Scénario: Une base qui n'est pas vide n'est jamais écrasée
		Étant donné une sauvegarde de la base de test
		Quand je lance « Machin restore-db <sauvegarde> »
		Alors la commande se termine avec le code 1
		Et la commande a signalé « la base machincast_test n'est pas vide : une sauvegarde ne se réimporte que dans une base neuve, comme install.sh la crée »
		Et la séquence « Fil du matin » est en base

	Scénario: Les droits d'une sauvegarde d'avant Machin webserver passent au rôle machincast_webserver, jamais ses données
		https://github.com/dascritch/machincast/issues/654 : Machin intranet est devenu Machin webserver, et son rôle de
		groupe machincast_intranet, machincast_webserver. Le script que pg_restore tire d'une sauvegarde d'avant est
		rejoué par psql, une ligne de droits traduite ; une ligne de COPY reste telle quelle.
		Quand le script d'une sauvegarde d'avant est traduit :
			"""
			GRANT SELECT ON TABLE public.events TO machincast_intranet;
			REVOKE ALL ON TABLE public.api_users FROM machincast_intranet;
			COPY public.log (id, message) FROM stdin;
			1	GRANT SELECT ON TABLE public.events TO machincast_intranet;
			\.
			GRANT USAGE ON SEQUENCE public.log_id_seq TO machincast_player;
			"""
		Alors le script rejoué est :
			"""
			GRANT SELECT ON TABLE public.events TO machincast_webserver;
			REVOKE ALL ON TABLE public.api_users FROM machincast_webserver;
			COPY public.log (id, message) FROM stdin;
			1	GRANT SELECT ON TABLE public.events TO machincast_intranet;
			\.
			GRANT USAGE ON SEQUENCE public.log_id_seq TO machincast_player;
			"""

	Scénario: Un fichier introuvable est signalé
		Étant donné la base de test vidée, comme install.sh vient de la créer
		Quand je lance « Machin restore-db …/introuvable.dump »
		Alors la commande se termine avec le code 1
		Et la commande a signalé « …/introuvable.dump introuvable »

	Plan du scénario: Le wrapper connaît les deux commandes
		Alors « <binaire> » est un binaire du wrapper, déclaré dans pyproject.toml par « <point d'entrée> »

		Exemples:
			| binaire    | point d'entrée                 |
			| backup-db  | machincast.backup:backup_main  |
			| restore-db | machincast.backup:restore_main |
