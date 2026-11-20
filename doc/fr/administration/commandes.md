# Commandes et messages

[Guide d'administration](README.md) › Commandes et messages

- [Lancer les programmes : Machin](#lancer-les-programmes--machin)
- [Interface graphique : Machin interface](#interface-graphique--machin-interface)
- [Maintenance de la base : Machin maintenance-db](#maintenance-de-la-base--machin-maintenance-db)
- [Export et réimportation de la base : Machin backup-db, Machin restore-db](#export-et-réimportation-de-la-base--machin-backup-db-machin-restore-db)
- [Purge de la base : Machin purge](#purge-de-la-base--machin-purge)
- [Tâches régulières : Machin tasks](#tâches-régulières--machin-tasks)
- [Lecture par le service de diffusion : Machin grant-read](#lecture-par-le-service-de-diffusion--machin-grant-read)
- [État de la station : Machin status](#état-de-la-station--machin-status)
- [Bannière : Machin banner](#bannière--machin-banner)
- [Suivre le journal : Machin logs](#suivre-le-journal--machin-logs)
- [Messages et codes de sortie](#messages-et-codes-de-sortie)
- [Démarrages et fins dans le log](#démarrages-et-fins-dans-le-log)
- [Rapports de crash](#rapports-de-crash)

## Lancer les programmes : Machin

Tous les programmes de MachinCast se lancent par une seule commande, `Machin`, installée par `install.sh` pour tout le système. Elle s'utilise depuis n'importe quel répertoire, sans activer d'environnement Python.

```bash
Machin indexer                     # lance Machin_indexer
Machin indexer --full-audit     # les options qui suivent le programme lui sont transmises
Machin --help                         # aide complète
```

| Commande | Rôle |
| --- | --- |
| `Machin player` | Diffusion de l'antenne, normalement lancée comme service ([Service de diffusion](../../../INSTALL.fr.md#service-de-diffusion)). |
| `Machin indexer` | Enregistrement des fichiers déposés dans les répertoires des banques, vérification des fichiers sonores et mise à jour de la base. |
| `Machin interface` | [Interface graphique](#interface-graphique--machin-interface) de supervision et de programmation : l'antenne, la grille, les [listes](../utilisateur/listes.md#listes) et les fiches, la simulation, l'airplay et les incidents ([guide de l'antenne](../utilisateur/README.md)). |
| `Machin maintenance-db` | [Maintenance de la base de production](#maintenance-de-la-base--machin-maintenance-db) : sauvegarde, vérification du schéma et des rôles, optimisation. |
| `Machin backup-db` | [Export de la base de production](#export-et-réimportation-de-la-base--machin-backup-db-machin-restore-db) : une sauvegarde datée, sans rien modifier. |
| `Machin restore-db FICHIER` | [Réimportation d'une sauvegarde](#export-et-réimportation-de-la-base--machin-backup-db-machin-restore-db) dans une base neuve, vide. |
| `Machin purge` | [Purge de la base de production](#purge-de-la-base--machin-purge) : efface ce qui dépasse la durée de péremption, jamais un fichier. |
| `Machin grant-read` | [Lecture des sonores par le service de diffusion](#lecture-par-le-service-de-diffusion--machin-grant-read), qui tourne sous son propre compte. |
| `Machin status` | [État de la station](#état-de-la-station--machin-status) en une ligne, pour un script : Machin player, serveur, radio, événement actuel et suivant. |
| `Machin banner` | [Bannière de MachinCast](#bannière--machin-banner), avec à sa droite la version et l'état de la station. |
| `Machin logs` | Suivi en direct du journal du service de diffusion. |
| `Machin tasks` | [Tâches régulières](#tâches-régulières--machin-tasks) : ce qui est dû, lancé tous les quarts d'heure par le minuteur du service. |

**Options de `Machin`**, placées avant le nom du programme :

| Option | Effet |
| --- | --- |
| `--config FICHIER` ou `--config=FICHIER` | Fichier de configuration à transmettre au programme, au lieu de `machincast.toml` (voir [Configuration](configuration.md#configuration)). Placée après le nom du programme, l'option lui est transmise telle quelle, avec le même effet. |
| `-h` | Aide minimale, en deux lignes. |
| `--help` | Aide complète : programmes, options, exemples et codes de sortie. Elle affiche aussi le chemin du `machincast.toml` lu par défaut. |
| `--binaries` | Liste des programmes, un par ligne. L'autocomplétion s'en sert. |

**Options communes à chaque programme**, placées après son nom :

| Option | Effet |
| --- | --- |
| `-h`, `--help` | Aide du programme, par exemple `Machin indexer --help`. |
| `--version` | Version de MachinCast, par exemple `Machin_indexer (MachinCast) 0.9.1`. |
| `--config FICHIER` | Fichier de configuration à lire. |

**Autocomplétion.** Dans un terminal bash, la touche Tab complète les noms des programmes et `logs`, les options de `Machin`, les fichiers après `--config`, les options de chaque programme (lues dans son aide) et les options courantes de `journalctl` après `logs`. Elle demande le paquet `bash-completion`, qu'installe `install.sh`. Sans installation, `source bash-completion/Machin` la charge dans le terminal courant.

## Interface graphique : Machin interface

`Machin interface` ouvre l'interface graphique de l'équipe de l'antenne ; son usage est décrit dans le [guide de l'antenne](../utilisateur/README.md), que son menu **Aide → Documentation** ouvre dans le navigateur web.

- **Base** : elle se connecte à la base de production (`database.production`), avec le rôle `machincast_interface` ([Droits de chaque programme dans la base](configuration.md#droits-de-chaque-programme-dans-la-base)). Sans base, elle ouvre une fenêtre d'erreur, « MachinCast : base de données injoignable », qui renvoie à [En cas de problème](../../../INSTALL.fr.md#en-cas-de-problème) et donne l'erreur de PostgreSQL dans ses détails ; à sa fermeture, `Machin interface` s'arrête avec le code 1. Le message `base de données injoignable` (ou `erreur de base de données`, pour un compte sans droit) s'affiche aussi sur la sortie d'erreur. Sans affichage graphique, dans une session SSH par exemple, seul ce message s'affiche.
- **Même compte et même configuration que la diffusion** : l'onglet Antenne suit la diffusion par sa socket d'état, que n'ouvrent, avec le service de diffusion, que les comptes du groupe `machincast`, et, sans lui, que le compte qui diffuse ([État de la diffusion pour l'interface](diffusion.md#état-de-la-diffusion-pour-linterface)). Le menu **Diffusion** pilote le service de diffusion, avec l'authentification de la règle polkit du service ([Service de diffusion](../../../INSTALL.fr.md#service-de-diffusion)), ou, sans service, une diffusion d'essai lancée dans un terminal.
- **Réglages** : **Fichier → Préférences de l'interface…** et **Fichier → Paramètres du service…** écrivent dans les sections `[crossfades]`, `[audio]`, `[silences]`, `[dead_air]`, `[interface]`, `[schedule]`, `[backup]` et `[database]` (la seule clé `retention`) du `machincast.toml`, qui garde ses commentaires et ses autres réglages ; la fenêtre « Pour bien démarrer » écrit `audio.output`, `audio.device`, `audio.preview` et `interface.suggestions`. Un fichier qui ne peut pas être écrit laisse les réglages tels quels, et la barre d'état dit pourquoi. Une nouvelle icône de l'application (`interface.icon`, [#111](https://github.com/dascritch/machincast/issues/111)) réécrit aussi les raccourcis `machincast.desktop` déjà installés, dans `~/.local/share/applications` et sur le bureau, sans en créer ; l'image elle-même n'est ni copiée ni modifiée.
- **Votre installation** : **Aide → Votre installation…** ouvre le document de l'équipe ([#451](https://github.com/dascritch/machincast/issues/451)) dans le premier éditeur de texte présent de `kate`, `kwrite`, `gnome-text-editor`, `gedit`, `mousepad`, `xed`, `pluma` et `featherpad` ; sinon dans l'application que le bureau associe aux fichiers texte (`xdg-mime query default text/plain`), lancée par `gio launch` (paquet `libglib2.0-bin`), jamais dans celle des `.md`, souvent une visionneuse ([#491](https://github.com/dascritch/machincast/issues/491)). Pour en imposer un autre, l'associer aux fichiers texte : `xdg-mime default org.kde.kate.desktop text/plain`.
- **Indexation** : le menu **Maintenance** lance `Machin indexer --window`, avec la configuration de l'interface, dans son propre programme ([Indexation : Machin indexer](indexation.md)).
- **Simulation** : l'onglet Simulation lance `Machin player --simulation`, avec la configuration de l'interface, ses fichiers dans un répertoire temporaire (`--directory`) effacé à la fermeture de l'onglet ([Simuler la diffusion](diffusion.md#simuler-la-diffusion)).

## Maintenance de la base : Machin maintenance-db

`Machin maintenance-db` ([#127](https://github.com/dascritch/machincast/issues/127)) entretient la base de production (`database.production`), en trois étapes, dans l'ordre :

1. **Sauvegarde** : `pg_dump` copie la base dans un nouveau fichier daté, `<base>-<AAAA-MM-JJTHH-MM-SS>.dump`, au format personnalisé de PostgreSQL. Il s'écrit dans le répertoire des sauvegardes, `backup.directory`, le répertoire personnel du compte par défaut ([#347](https://github.com/dascritch/machincast/issues/347)), ou dans celui de `--backups`, créé au besoin. Aucune sauvegarde n'est effacée : les anciennes se suppriment à la main. **Une sauvegarde qui échoue arrête la maintenance**, sans rien modifier.
2. **Schéma** : les migrations manquantes sont appliquées, comme le fait `install.sh`. Une base qui avait reçu les quinze anciennes migrations, fondues depuis dans le schéma unique, garde ses données, et la maintenance l'annonce ; une base restée à une ancienne migration intermédiaire est laissée telle quelle, avec `schéma impossible à mettre à jour : …`, après sa sauvegarde ([#314](https://github.com/dascritch/machincast/issues/314), [Mettre à jour](../../../INSTALL.fr.md#mettre-à-jour)). Puis chacun des trois rôles de MachinCast doit pouvoir être endossé par le compte. Un rôle absent ou non autorisé est signalé, avec les deux commandes qu'un administrateur lance pour l'autoriser.
3. **Optimisation** : `VACUUM (ANALYZE)` récupère la place des lignes effacées et met à jour les statistiques qui guident PostgreSQL. La diffusion peut continuer pendant ce temps.

Le compte qui la lance doit être celui de MachinCast, propriétaire de la base : il n'a besoin d'aucun droit particulier sur le serveur. Elle se lance aussi depuis l'interface, menu **Maintenance → Maintenance de la base de données…**. L'interface demande d'abord confirmation, en donnant le répertoire où la sauvegarde sera enregistrée (le répertoire des sauvegardes de sa configuration), que le bouton « Choisir l'emplacement… » permet de changer. Elle l'ouvre ensuite dans une fenêtre de terminal, avec la configuration de l'interface et ce répertoire (`--backups`) ; la fenêtre reste ouverte à la fin, jusqu'à ce qu'on la ferme.

```bash
Machin maintenance-db
Machin maintenance-db --backups /srv/sauvegardes/machincast
```

| Option | Effet |
| --- | --- |
| `--backups REPERTOIRE` | Répertoire des sauvegardes, au lieu de `backup.directory`. |
| `--keep-open` | Une fois la maintenance finie, garde le terminal ouvert jusqu'à sa fermeture (ou `Ctrl-D`, `Ctrl-C`) ; Entrée n'y fait rien. L'interface s'en sert, pour que le compte rendu reste lisible. |

Elle se termine par `maintenance terminée` (code 0), ou par `maintenance terminée, avec des anomalies` (code 1) quand un rôle manque. Une base injoignable, une sauvegarde impossible ou un schéma impossible à mettre à jour donnent aussi le code 1.

**Restaurer une sauvegarde.** Elle est faite par le `pg_dump` de la version du serveur, `/usr/lib/postgresql/<version>/bin/pg_dump` ([#384](https://github.com/dascritch/machincast/issues/384)), sinon par celui du `PATH` : le `pg_dump` du `PATH` est le plus récent installé, et sa sauvegarde ne se relirait pas avec un `pg_restore` plus ancien (`unsupported version (1.16) in file header`). Sur un poste neuf, `./install.sh` propose de la réimporter dans la base qu'il crée ; à la main, `Machin restore-db` ([Export et réimportation](#export-et-réimportation-de-la-base--machin-backup-db-machin-restore-db)). Pour seulement la consulter, elle se relit avec le `pg_restore` du serveur, dans une base neuve, pour comparer avant de remplacer quoi que ce soit :

```bash
sudo -u postgres createdb --owner="$(id -un)" machincast_restauree
pg_restore --dbname=machincast_restauree --no-owner ~/machincast-2026-10-22T08-30-00.dump
```

## Export et réimportation de la base : Machin backup-db, Machin restore-db

Pour repartir vite après une panne, sur ce poste ou sur un autre ([#347](https://github.com/dascritch/machincast/issues/347)) :

1. **Exporter** : `Machin backup-db` sauvegarde la base de production, comme la première étape de la maintenance, sans rien modifier d'autre : `pg_dump` de la version du serveur, au format personnalisé de PostgreSQL, dans un nouveau fichier daté, `<base>-<AAAA-MM-JJTHH-MM-SS>.dump`, du répertoire des sauvegardes (`backup.directory`, le répertoire personnel du compte par défaut ; `--backups REPERTOIRE` pour un autre). L'interface le lance aussi, sans terminal, menu **Maintenance → Exporter la base…** ; la barre d'état dit où la sauvegarde est enregistrée, ou pourquoi elle n'a pas pu l'être. Le répertoire se règle dans **Fichier → Paramètres du service…**, page **Sauvegarde**, qui copie aussi `machincast.toml`, sous un nom daté, là où on le choisit, comme une clé USB.
2. **Réimporter** : sur le poste neuf, `./install.sh` crée la base de production, puis propose de réimporter une sauvegarde ([Réimporter une sauvegarde](../../../INSTALL.fr.md#réimporter-une-sauvegarde)). À la main, sur une base vide :

```bash
Machin backup-db
Machin backup-db --backups /media/cle/radio
Machin restore-db /media/cle/radio/machincast-2026-11-17T10-00-00.dump
```

`Machin restore-db FICHIER` vérifie d'abord la sauvegarde, et refuse :

- un fichier introuvable, ou qui n'est pas une sauvegarde de MachinCast : `pg_restore` ne le lit pas, ou les tables de MachinCast et le registre de ses migrations y manquent ;
- une sauvegarde d'une version plus récente de MachinCast, dont des migrations sont inconnues de celle installée : `… vient d'une version plus récente de MachinCast (migrations inconnues : …) : mettre d'abord MachinCast à jour` ;
- une base de production qui n'est pas vide : **une base n'est jamais écrasée**. Pour repartir d'une sauvegarde sur un poste déjà installé, la base se supprime d'abord, après une dernière sauvegarde (`sudo -u postgres dropdb machincast`, du nom de `database.production`) ; `./install.sh` la recrée, puis propose la réimportation.

Puis le `pg_restore` de la version du serveur la réimporte en une seule transaction : un échec laisse la base vide. Ses tables reviennent au compte qui la réimporte, avec les droits des rôles de MachinCast, que `./install.sh` a créés sur le serveur. Une sauvegarde d'une version plus ancienne reçoit enfin les migrations qui lui manquent. Code 0 si tout est fait, 1 sinon ; `Machin backup-db` de même. Ses fichiers sonores ne sont pas dans la sauvegarde : ils se recopient à part, aux mêmes chemins.

## Purge de la base : Machin purge

`Machin purge` ([#268](https://github.com/dascritch/machincast/issues/268)) efface de la base de production (`database.production`) ce qui dépasse la **durée de péremption**, `database.retention`, 60 jours par défaut, comptée depuis l'heure du lancement :

- les passages de l'airplay finis avant cette limite ; un passage commencé avant et fini après reste entier ;
- les lignes du log d'avant cette limite ;
- les sonores, banques, séquences et événements [supprimés depuis l'interface](../utilisateur/listes.md#supprimer-un-élément) depuis plus longtemps : ils ne peuvent plus se restaurer ;
- les sonores dont l'indexation a constaté la disparition du fichier (état `supprimé`) depuis plus longtemps ;
- les [sessions sautées](../utilisateur/grille.md#calendrier) d'avant cette limite ([#273](https://github.com/dascritch/machincast/issues/273)), qui ne servent plus à rien ; le bilan ne les compte pas.

Les passages plus récents d'un sonore effacé gardent son emplacement, son artiste et son titre, recopiés lors du passage. **Seules des lignes de la base sont effacées** : aucun fichier sonore, aucun répertoire ([Les fichiers sonores ne sont jamais modifiés](configuration.md#les-fichiers-sonores-ne-sont-jamais-modifiés)). Un fichier toujours présent dans le répertoire d'une banque est de nouveau indexé, comme un nouveau sonore. Tout s'efface en une seule fois, ou rien : une erreur laisse la base telle quelle.

```bash
Machin purge
```

Elle dit, et écrit dans le log de la base, ligne `purge`, ce qu'elle a effacé, par exemple :

```text
2026-12-20T12:00:03+01:00 purge de la base machincast, au-delà de 60 jours (avant le 21/10/2026 12:00) : 412 passages de l'airplay, 37 lignes du log, 2 sonores, 1 banque, 0 séquence, 1 événement effacés
```

Code 0 quand la purge est faite ; 1 si la base est injoignable, ou sur une erreur de la base : rien n'est alors effacé. Comme la maintenance, elle se lance avec le compte de MachinCast, propriétaire de la base, qui efface sans endosser de rôle.

**La durée** se règle dans `machincast.toml` ([Configuration](configuration.md#durée-de-péremption)), ou dans l'interface, **Fichier → Préférences de l'interface…**, page **Base**. **Avec le service de diffusion** (`./install.sh --service`), un minuteur systemd la lance chaque jour à l'heure de `schedule.daily`, 10:00 par défaut, réglable dans **Fichier → Paramètres du service…**, page **Tâches**, puis l'audit complet ([Service de diffusion](../../../INSTALL.fr.md#service-de-diffusion), [#455](https://github.com/dascritch/machincast/issues/455)) ; ses messages se lisent par `journalctl --unit=machincast-tasks.service`. Sans service, ou avec `--no-timers`, elle se lance à la main.

## Tâches régulières : Machin tasks

`Machin tasks` ([#455](https://github.com/dascritch/machincast/issues/455)) lance les tâches régulières qui sont dues, et rien d'autre. **Avec le service de diffusion** (`./install.sh --service`, sauf avec `--no-timers`), le minuteur systemd `machincast-tasks.timer` le lance tous les quarts d'heure, sous le compte de MachinCast ([Service de diffusion](../../../INSTALL.fr.md#service-de-diffusion)). Aujourd'hui, une tâche :

- **la tâche quotidienne**, une fois par jour à partir de l'heure de `schedule.daily`, 10:00 par défaut, réglable dans **Fichier → Paramètres du service…**, page **Tâches** : `Machin purge`, puis `Machin indexer --full-audit`. Elle remplace la purge de midi. `python -m machincast.schedule claim` dit si elle est due, et note son passage dans le répertoire d'état du service, `/var/lib/machincast-tasks` : une tâche manquée, poste éteint, passe au quart d'heure qui suit son démarrage ; une tâche en échec n'est pas relancée avant le lendemain.

Ce que fait chaque passage est dans le wrapper, pas dans l'unité systemd : une tâche peut s'y ajouter, ou le minuteur changer de périodicité, sans toucher à l'autre. `Machin tasks` ne prend pas d'argument, sauf `--config FICHIER` avant `tasks`, transmis à chaque tâche. Il se lance d'ordinaire par son unité, qui lui donne son répertoire d'état ; à la main, sans elle, il sort avec le code 2.

Code 0 quand rien n'était dû, ou que tout ce qui l'était a réussi : un audit complet déjà en cours, lancé depuis l'interface, n'est pas un échec ; sinon, celui de la première tâche en échec, qui arrête la tâche quotidienne (une purge en échec n'est pas suivie de l'audit) ; 127 sans le venv de MachinCast. Ses messages se lisent par `journalctl --unit=machincast-tasks.service`.

## Lecture par le service de diffusion : Machin grant-read

Le service de diffusion tourne sous son propre compte, `machincast` ([#381](https://github.com/dascritch/machincast/issues/381), [Service de diffusion](../../../INSTALL.fr.md#service-de-diffusion)) : il ne lit les sonores que si les droits du poste le lui permettent. Il ne lit **jamais** un répertoire personnel, et MachinCast ne change jamais les droits d'un répertoire personnel, ni d'une arborescence du système (`/etc`, `/bin`, `/sbin`, `/usr`, `/boot`, `/media`, `/mnt`…) : les sonores se déposent dans `/home/machincast`, qu'il lit déjà. Une discothèque peut aussi être sous `/home/machincast`, `/opt`, `/srv` ou `/var`, à condition que leur racine se traverse déjà : `Machin grant-read` ne la change jamais, ni les répertoires du système de `/var` (`lib`, `log`, `cache`, `spool`…). Pour ces répertoires, et tout autre hors des arborescences sensibles, `Machin grant-read` lui en donne la lecture :

```bash
Machin grant-read                          # les répertoires des banques et les fichiers ajoutés de la base de production
Machin grant-read /data/sonores/jingles    # seulement ces chemins
```

Pour chaque chemin, il donne au compte `machincast`, par des ACL (`setfacl`, paquet `acl`) :

- la **traversée** (`x`) des répertoires parents qui en manquent, sans le droit d'en lister le contenu ;
- la **lecture** (`r`, et `x` des répertoires) du chemin, de tout ce qu'il contient, et, par l'ACL par défaut d'un répertoire, des fichiers qui s'y ajouteront.

Rien d'autre ne change : ni le propriétaire, ni les droits de son groupe ou des autres, ni le contenu ou la date d'aucun fichier ([Les fichiers sonores ne sont jamais modifiés](configuration.md#les-fichiers-sonores-ne-sont-jamais-modifiés)). `ls -l` montre alors un `+` après les droits, et `getfacl` les détaille. Un chemin déjà lisible est seulement annoncé. Un changement qui toucherait une arborescence sensible est **refusé**, et rien n'est changé :

```text
/home/radio/sons : refusé, il est dans /home/radio, où MachinCast ne change jamais aucun droit
déposer les sonores dans /home/machincast, que le service de diffusion lit
```

`setfacl` ne change que ce qui appartient au compte qui le lance. Un répertoire d'un autre compte est signalé, avec la commande qu'un administrateur lance, par exemple :

```text
/data/partage : machincast ne peut pas le traverser, et il appartient à un autre compte
un administrateur peut lancer : sudo setfacl --modify=u:machincast:x /data/partage
```

Code 0 quand le service lit tout ; 1 sinon, ou sans compte `machincast` : le service n'est pas installé, et `Machin player` lit avec le compte qui le lance. Depuis l'interface, **Maintenance → Donner les droits de lecture des fichiers sonores au service de diffusion…** le lance dans un terminal, sur la base de l'interface ; l'ajout d'un répertoire à une banque, ou de fichiers, accepte toujours ce que le service lit déjà, refuse ce qu'il ne lit pas dans un répertoire personnel, vérifie que le service lit les autres, et propose sinon de les lui faire lire. Pendant la diffusion, un fichier que le service ne lit pas n'est pas joué : le log de la base le dit en alerte, `fichier illisible`, avec son chemin.

## État de la station : Machin status

`Machin status` ([#518](https://github.com/dascritch/machincast/issues/518)) répond par une ligne sur la sortie standard, pour un script, une barre d'état ou une supervision. Il ne fait que lire : la configuration, les programmes en cours et la grille de la base de production.

| Commande | Réponse | Code |
| --- | --- | --- |
| `Machin status`, ou `Machin status player` | `running` quand Machin player diffuse, sous n'importe quel compte, service de diffusion ou lancement à la main ; `stopped` sinon. Une simulation n'est pas une diffusion. | 0 s'il diffuse, 1 sinon |
| `Machin status server` | `service` quand le service de diffusion est installé, `test` sinon. | 0 |
| `Machin status radio` | Le nom de la radio, `metadata.public_text` de la configuration. | 0 |
| `Machin status event`, ou `Machin status event --now` | L'événement actuel, `09:00 → 11:00 : Matinale` : ses heures, à celles du poste, et son nom privé. | 0 ; 1 sans événement, sans rien écrire ; 3 si la base est injoignable |
| `Machin status event --next` | L'événement suivant, dans le même format. | De même |
| `Machin status summary` | Toutes ces réponses, une ligne `clé`, tabulation, `valeur` chacune : `server`, `radio`, `player` et, quand Machin player diffuse, `now` et `next`. C'est ce que lit [`Machin banner`](#bannière--machin-banner). Une base injoignable n'enlève que `now` et `next`. | 0 |

Un fil musical permanent n'a ni début ni fin : `Machin status event` donne l'heure où il a pris l'antenne, à la fin de l'événement d'avant, et celle où il sera interrompu, au début du suivant, par exemple `10:00 → 12:00 : Fil musical`. Ces heures se cherchent dans la semaine d'avant et la semaine d'après ; `--:--` dit celle qui n'y est pas. Les événements sont ceux de la grille : une session sautée l'est aussi ici, mais un événement avancé ou terminé à la main depuis l'antenne, que seul Machin player connaît, ne l'est pas. Un appel incorrect, comme `Machin status event --soon`, rend le code 2.

```bash
Machin status && echo "à l'antenne : $(Machin status event)"
```

## Serveur intranet : Machin intranet

`Machin intranet` ([#538](https://github.com/dascritch/machincast/issues/538)) sert l'intranet et son API aux autres postes du réseau, **en HTTPS seulement**. Il est **éteint par défaut** : tant que la section `[intranet]` de `machincast.toml` n'a pas `enabled = true`, il refuse de démarrer et le dit, code 4. Le plus simple est de l'allumer dans l'interface, **Fichier → Paramètres du service…**, page **Intranet**, qui donne aussi le port, le délai pour valider une connexion au pupitre, et l'adresse à donner aux autres postes.

- **Avec le service de diffusion** (`./install.sh --service`), l'unité `machincast-intranet.service` démarre avec le poste ; la page **Intranet** la redémarre ou l'arrête, ce qui demande le mot de passe d'un administrateur. Son journal : `journalctl -u machincast-intranet`.
- **Sans le service**, `Machin intranet` se lance à la main, dans un terminal, et s'arrête par <kbd>Ctrl</kbd>+<kbd>C</kbd>.
- **Certificat** : sans certificat donné (`intranet.certificate` et `intranet.key`, par exemple ceux de l'autorité de certification de la radio), Machin intranet en génère un auto-signé, au nom du poste et de chacune de ses adresses IP, et le refait quand une adresse change. Le navigateur d'un autre poste avertit à la première connexion : l'empreinte du certificat, que le journal donne au démarrage (`intranet sur https://10.0.0.12:8443/, certificat 9B:21:…`), doit être celle qu'il affiche.
- **Adresse** : sans nom de domaine interne, même en DHCP, l'intranet se joint par l'adresse IP du poste sur le réseau local, comme `https://10.0.0.12:8443/`. Une adresse fixe, réservée dans le DHCP, évite d'avoir à la redonner.
- **Connexion** ([#539](https://github.com/dascritch/machincast/issues/539)) : depuis un autre poste, ouvrir l'adresse de l'intranet, puis saisir le nom et le mot de passe d'un compte de l'onglet **API**. Le studio voit alors, au-dessus des onglets de l'interface, un bandeau orange qui nomme le compte, l'adresse et le navigateur du poste distant, et un **code à 6 chiffres** à lui donner, par téléphone par exemple ; ce code se saisit sur le poste distant, dans le délai réglé (30 minutes par défaut). **Refuser**, dans le bandeau, ferme la porte. Une session validée dure `intranet.session` heures, 12 par défaut ; **Se déconnecter** la ferme plus tôt.
- **Sessions** : l'onglet **API** montre, sous les comptes, les sessions du compte choisi, et en invalide une. **➕ Nouvelle session API…** en génère une pour un outil qui lit l'API : son jeton se donne dans l'en-tête `Authorization: Bearer …`, et n'est montré qu'une fois.
- **Accueil** ([#541](https://github.com/dascritch/machincast/issues/541)) : une fois connecté, l'intranet montre, sous un bandeau au nom de la radio et à l'état de la diffusion, l'antenne en direct : l'heure, le texte public, l'événement en cours et le suivant, le sonore en cours et le suivant, avec leurs décomptes en secondes, et les derniers sonores diffusés. La page se relit toute seule toutes les 5 secondes.
- **API** ([#540](https://github.com/dascritch/machincast/issues/540)) : les mêmes sessions lisent l'API, sous `/api/v1`, en JSON : `live` (l'antenne : sonore en cours, 5 suivants, 5 derniers, événements précédent, en cours et suivant), `incidents`, et les listes et fiches `events`, `sequences`, `banks` et `sounds`. Par exemple, avec le jeton d'une session générée dans l'onglet **API** : `curl --cacert certificate.pem -H "Authorization: Bearer <jeton>" https://10.0.0.12:8443/api/v1/live`.
- Le pare-feu du poste, s'il y en a un, doit laisser entrer le port choisi (8443 par défaut) depuis le réseau local seulement : l'intranet n'a pas à être joignable d'Internet.

## Bannière : Machin banner

`Machin banner` ([#517](https://github.com/dascritch/machincast/issues/517)) affiche le logo de MachinCast, son losange en orange. À sa droite : le numéro de version, puis, d'après [`Machin status summary`](#état-de-la-station--machin-status), la radio et le serveur (`Radio FMR · service`), `Machin player : en marche` ou `Machin player : arrêté` et, quand il diffuse, `En cours : …` et `Suivant : …`. Sans le venv de MachinCast, seule la version est à droite, et l'état du service de diffusion, s'il est installé, s'écrit sous le logo. Il ne prend aucun argument (code 2 sinon) et rend le code 0.

`./install.sh` commence par elle. **Avec le service de diffusion** (`./install.sh --service`), `/etc/profile.d/machincast.sh` la lance à chaque nouveau shell interactif, sur un terminal, pour tous les comptes du poste ; `./install.sh --remove-service` le retire ([Service de diffusion](../../../INSTALL.fr.md#service-de-diffusion)). Les couleurs ne viennent que sur un terminal, jamais avec la variable `NO_COLOR`.

## Suivre le journal : Machin logs

Chaque programme écrit aussi ses messages dans son fichier de `/var/log/machincast/`, `Machin_player.log`, `Machin_indexer.log`, `Machin_interface.log`…, chaque ligne précédée de son heure et de son niveau, `INFO`, `WARNING` ou `ERROR` ([#381](https://github.com/dascritch/machincast/issues/381)). `install.sh` crée ce répertoire, au groupe `machincast`, que partagent le compte du service de diffusion et le vôtre : chacun lit ce que l'autre y écrit. `logrotate` fait tourner ces fichiers chaque semaine.

`Machin logs` suit en direct le journal du service de diffusion, `machincast.service`. Les options qui suivent sont transmises à `journalctl`, par exemple :

```bash
Machin logs --since "1 hour ago" --priority=warning
```

Lire ce journal demande d'appartenir au groupe `systemd-journal`, ce que fait `install.sh`, effectif après le redémarrage du poste. Tant que le service de diffusion n'est pas installé ([#22](https://github.com/dascritch/machincast/issues/22), [Service de diffusion](../../../INSTALL.fr.md#service-de-diffusion)), le journal est vide : `Machin player`, lancé à la main, écrit dans son terminal. `Ctrl-C` arrête le suivi.

## Messages et codes de sortie

Chaque message commence par son heure, en ISO 8601, à la seconde, avec le décalage horaire du poste, par exemple `2026-10-23T07:55:19+02:00 à l'antenne : Frédéric Galliano – Multiples Un (Fil musical)` ([#253](https://github.com/dascritch/machincast/issues/253)) ; elle remplace le nom du programme, qui le précédait. Le journal du service (`Machin logs`) ajoute sa propre heure devant. Les informations, comme le bilan d'une indexation, vont sur la sortie standard ; les anomalies et les erreurs, sur la sortie d'erreur. Un script peut ainsi garder les unes et les autres séparément.

| Code | Signification |
| --- | --- |
| 0 | Le programme est allé au bout. Pour l'indexation, même si des sonores ont changé d'état : ce sont des anomalies, pas des erreurs. |
| 1 | Base de données injoignable ou perdue (pour `Machin interface`, au lancement), décodeur GStreamer manquant, `Machin indexer --window` sans affichage graphique, sortie audio indisponible, autre `Machin player` déjà en diffusion, maintenance de la base inachevée ou avec un rôle manquant, purge de la base impossible, ou fonction pas encore écrite. |
| 2 | Configuration invalide, ou appel incorrect (option inconnue, `--config` sans fichier, option refusée avec une autre). |
| 3 | `Machin indexer` : une autre indexation du même mode est déjà en cours sur la base ; celle-ci s'arrête aussitôt, sans rien toucher. Pas un échec pour les minuteurs des tâches ([#455](https://github.com/dascritch/machincast/issues/455)). |
| 127 | Programme ou `journalctl` introuvable, signalé par `Machin`. |

Les messages d'erreur courants et leur solution sont dans le tableau [En cas de problème](../../../INSTALL.fr.md#en-cas-de-problème) d'`INSTALL.md`.

## Démarrages et fins dans le log

`Machin player`, `Machin indexer`, `Machin maintenance-db` et `Machin purge` notent chacun de leurs lancements dans leur journal et dans le log de la base, que l'interface montre ([#341](https://github.com/dascritch/machincast/issues/341), [#342](https://github.com/dascritch/machincast/issues/342) pour `Machin player`, hors simulation). Une fausse manœuvre ou un plantage s'y retrouve, avec l'heure :

```text
2026-11-04T03:00:02+01:00 démarrage : Machin_indexer 0.9.1, pid 4812 : --full-audit
2026-11-04T03:12:47+01:00 fin : Machin_indexer, pid 4812 : code de sortie 0
```

- **Le démarrage**, nature `démarrage`, au niveau information : le programme, sa version, son numéro de processus (pid) et ses options.
- **La fin**, nature `fin` : le même pid, et le [code de sortie](#messages-et-codes-de-sortie). Elle est au niveau information pour le code 0, en **incident** pour tout autre code, comme le 2 d'une option refusée, et se lit alors dans l'onglet **Incidents** de l'interface.
- **Un plantage probable**, nature `plantage probable`, en incident : au lancement suivant d'un programme, si son démarrage précédent n'a pas noté de fin et que son processus ne tourne plus. Le programme a été tué, arrêté par un signal, ou le poste s'est éteint en cours de route : `Machin_purge, pid 3920, démarré le 03/11/2026 à 12:00, n'a pas noté sa fin`. S'il a laissé un [rapport de crash](#rapports-de-crash), le message se termine par son chemin : `; rapport de crash /var/log/machincast/crash-dump/Machin_purge-2026-11-03T12-00-00-3920.txt`. Un lancement précédent encore en cours n'en est pas un. Le service de diffusion arrêté par `systemctl stop`, ou par le bouton de l'interface, note sa fin ; tué ou privé de courant, il note le plantage probable à son redémarrage.

`Machin indexer --sound N`, que `Machin player` lance avant chaque sonore qu'il va jouer, ne note ni démarrage ni fin. `Machin maintenance-db --keep-open`, lancé depuis l'interface, note sa fin avant que sa fenêtre reste ouverte : la fermer n'est pas un plantage. Une configuration invalide ne dit pas quelle base joindre : seul le journal en parle. Une base injoignable n'empêche pas le programme de tourner : le journal dit que son démarrage n'a pas été noté dans la base.

## Rapports de crash

Quand un programme de MachinCast plante, il laisse un **rapport de crash** dans `/var/log/machincast/crash-dump/`, avec les logs ([#381](https://github.com/dascritch/machincast/issues/381)), ou, sur un poste où ce répertoire n'existe pas, dans `crash-dump/` du répertoire de MachinCast ; s'il ne peut écrire dans aucun, dans `/tmp/machincast/crash-dump/`, vidé au redémarrage du poste ([#342](https://github.com/dascritch/machincast/issues/342)). Le journal le signale : `rapport de crash écrit : /var/log/machincast/crash-dump/Machin_player-2026-11-09T14-03-12-4242.txt`. Le nom donne le programme, l'heure de son démarrage et son numéro de processus, les mêmes que dans le log.

Ce rapport est fait pour les développeurs : **joignez-le au ticket** qui signale le problème. Il contient :

- le programme, sa version, ses options, l'heure de son démarrage et celle du plantage ;
- la pile Python ;
- ce qu'ont répondu PostgreSQL, GStreamer ou le système, s'ils sont en cause, et les versions des outils ;
- pour `Machin indexer`, le fichier qu'il examinait ;
- pour `Machin interface`, les cartes son de l'antenne et de la pré-écoute, la sortie de `wpctl status`, l'onglet affiché et le sonore en pré-écoute ;
- pour `Machin player`, la carte son de l'antenne, la sortie de `wpctl status`, et les sonores précédent, à l'antenne et les 5 suivants annoncés : événement, séquence, banque, artiste et titre, fichier.

Un programme qui s'arrête d'un coup, sur une erreur de GStreamer ou de Qt, ou tué par `kill -9`, ne peut pas écrire tout son rapport : il n'y laisse que la pile de ses fils. `Machin` l'achève aussitôt après ([#413](https://github.com/dascritch/machincast/issues/413)) ; privé de courant, c'est son **lancement suivant** qui l'achève. Sa fin dit alors `Fin : inconnue`, et il donne ce qu'on retrouve encore : les versions, les cartes son du fichier de configuration et la sortie de `wpctl status` pour la diffusion et l'interface, puis les dernières lignes du journal du programme, qui disent ce qui jouait, le fichier que l'indexation analysait, l'onglet affiché ou le sonore en pré-écoute. Lancé dans un terminal, un programme n'écrit pas dans le journal : ces lignes manquent alors. Les rapports s'accumulent : effacez-les quand le ticket est traité. Un fichier caché qui finit par `.en-cours` est le rapport d'un programme qui tourne encore ; ne l'effacez pas.

