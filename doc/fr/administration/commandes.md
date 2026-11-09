# Commandes et messages

[Guide d'administration](README.md) › Commandes et messages

- [Lancer les programmes : Machin](#lancer-les-programmes--machin)
- [Interface graphique : Machin interface](#interface-graphique--machin-interface)
- [Maintenance de la base : Machin maintenance-db](#maintenance-de-la-base--machin-maintenance-db)
- [Purge de la base : Machin purge](#purge-de-la-base--machin-purge)
- [Suivre le journal : Machin logs](#suivre-le-journal--machin-logs)
- [Messages et codes de sortie](#messages-et-codes-de-sortie)
- [Démarrages et fins dans le log](#démarrages-et-fins-dans-le-log)

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
| `Machin interface` | Interface graphique de supervision et de programmation. Pour l'instant, son [écran par défaut](#interface-graphique--machin-interface), les [listes](../utilisateur/listes.md#listes), les fiches d'un [événement](../utilisateur/grille.md#fiche-dun-événement), d'une [séquence](../utilisateur/grille.md#fiche-dune-séquence), d'une [banque](../utilisateur/sonores.md#fiche-dune-banque) et d'un [sonore](../utilisateur/sonores.md#fiche-dun-sonore). |
| `Machin maintenance-db` | [Maintenance de la base de production](#maintenance-de-la-base--machin-maintenance-db) : sauvegarde, vérification du schéma et des rôles, optimisation. |
| `Machin purge` | [Purge de la base de production](#purge-de-la-base--machin-purge) : efface ce qui dépasse la durée de péremption, jamais un fichier. |
| `Machin logs` | Suivi en direct du journal du service de diffusion. |

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
| `--version` | Version de MachinCast, par exemple `Machin_indexer (MachinCast) 0.1.0`. |
| `--config FICHIER` | Fichier de configuration à lire. |

**Autocomplétion.** Dans un terminal bash, la touche Tab complète les noms des programmes et `logs`, les options de `Machin`, les fichiers après `--config`, les options de chaque programme (lues dans son aide) et les options courantes de `journalctl` après `logs`. Elle demande le paquet `bash-completion`, qu'installe `install.sh`. Sans installation, `source bash-completion/Machin` la charge dans le terminal courant.

## Interface graphique : Machin interface

`Machin interface` ouvre l'interface graphique de l'équipe de l'antenne ; son usage est décrit dans le [guide de l'antenne](../utilisateur/README.md), que son menu **Aide → Documentation** ouvre dans le navigateur web.

- **Base** : elle se connecte à la base de production (`database.production`), avec le rôle `machincast_interface` ([Droits de chaque programme dans la base](configuration.md#droits-de-chaque-programme-dans-la-base)). Sans base, elle ouvre une fenêtre d'erreur, « MachinCast : base de données injoignable », qui renvoie à [En cas de problème](../../../INSTALL.fr.md#en-cas-de-problème) et donne l'erreur de PostgreSQL dans ses détails ; à sa fermeture, `Machin interface` s'arrête avec le code 1. Le message `base de données injoignable` (ou `erreur de base de données`, pour un compte sans droit) s'affiche aussi sur la sortie d'erreur. Sans affichage graphique, dans une session SSH par exemple, seul ce message s'affiche.
- **Même compte et même configuration que la diffusion** : l'onglet Antenne suit la diffusion par sa socket d'état, que seul le compte qui diffuse peut ouvrir ([État de la diffusion pour l'interface](diffusion.md#état-de-la-diffusion-pour-linterface)). Le menu **Diffusion** pilote le service de diffusion, avec l'authentification de la règle polkit du service ([Service de diffusion](../../../INSTALL.fr.md#service-de-diffusion)), ou, sans service, une diffusion d'essai lancée dans un terminal.
- **Réglages** : **Fichier → Préférences…** écrit dans les sections `[crossfades]`, `[audio]`, `[silences]`, `[dead_air]`, `[interface]` et `[database]` (la seule clé `retention`) du `machincast.toml`, qui garde ses commentaires et ses autres réglages ; la fenêtre « Pour bien démarrer » écrit `audio.output`, `audio.device`, `audio.preview` et `interface.suggestions`. Un fichier qui ne peut pas être écrit laisse les réglages tels quels, et la barre d'état dit pourquoi. Une nouvelle icône de l'application (`interface.icon`, [#111](https://github.com/dascritch/machincast/issues/111)) réécrit aussi les raccourcis `machincast.desktop` déjà installés, dans `~/.local/share/applications` et sur le bureau, sans en créer ; l'image elle-même n'est ni copiée ni modifiée.
- **Indexation** : le menu **Maintenance** lance `Machin indexer --window`, avec la configuration de l'interface, dans son propre programme ([Indexation : Machin indexer](indexation.md)).
- **Simulation** : l'onglet Simulation lance `Machin player --simulation`, avec la configuration de l'interface, ses fichiers dans un répertoire temporaire (`--directory`) effacé à la fermeture de l'onglet ([Simuler la diffusion](diffusion.md#simuler-la-diffusion)).

## Maintenance de la base : Machin maintenance-db

`Machin maintenance-db` ([#127](https://github.com/dascritch/machincast/issues/127)) entretient la base de production (`database.production`), en trois étapes, dans l'ordre :

1. **Sauvegarde** : `pg_dump` copie la base dans un nouveau fichier daté, `<base>-<AAAA-MM-JJTHH-MM-SS>.dump`, au format personnalisé de PostgreSQL. Il s'écrit dans le répertoire `sauvegardes`, à côté du fichier de configuration, ou dans celui de `--backups`, créé au besoin. Aucune sauvegarde n'est effacée : les anciennes se suppriment à la main. **Une sauvegarde qui échoue arrête la maintenance**, sans rien modifier.
2. **Schéma** : les migrations manquantes sont appliquées, comme le fait `install.sh`. Une base qui avait reçu les quinze anciennes migrations, fondues depuis dans le schéma unique, garde ses données, et la maintenance l'annonce ; une base restée à une ancienne migration intermédiaire est laissée telle quelle, avec `schéma impossible à mettre à jour : …`, après sa sauvegarde ([#314](https://github.com/dascritch/machincast/issues/314), [Mettre à jour](../../../INSTALL.fr.md#mettre-à-jour)). Puis chacun des trois rôles de MachinCast doit pouvoir être endossé par le compte. Un rôle absent ou non autorisé est signalé, avec les deux commandes qu'un administrateur lance pour l'autoriser.
3. **Optimisation** : `VACUUM (ANALYZE)` récupère la place des lignes effacées et met à jour les statistiques qui guident PostgreSQL. La diffusion peut continuer pendant ce temps.

Le compte qui la lance doit être celui de MachinCast, propriétaire de la base : il n'a besoin d'aucun droit particulier sur le serveur. Elle se lance aussi depuis l'interface, menu **Maintenance → Maintenance de la base de données…**. L'interface demande d'abord confirmation, en donnant le répertoire où la sauvegarde sera enregistrée (`sauvegardes`, à côté de sa configuration), que le bouton « Choisir l'emplacement… » permet de changer. Elle l'ouvre ensuite dans une fenêtre de terminal, avec la configuration de l'interface et ce répertoire (`--backups`) ; la fenêtre reste ouverte à la fin, jusqu'à ce qu'on la ferme.

```bash
Machin maintenance-db
Machin maintenance-db --backups /srv/sauvegardes/machincast
```

| Option | Effet |
| --- | --- |
| `--backups REPERTOIRE` | Répertoire des sauvegardes, au lieu de `sauvegardes` à côté du fichier de configuration. |
| `--keep-open` | Une fois la maintenance finie, garde le terminal ouvert jusqu'à sa fermeture (ou `Ctrl-D`, `Ctrl-C`) ; Entrée n'y fait rien. L'interface s'en sert, pour que le compte rendu reste lisible. |

Elle se termine par `maintenance terminée` (code 0), ou par `maintenance terminée, avec des anomalies` (code 1) quand un rôle manque. Une base injoignable, une sauvegarde impossible ou un schéma impossible à mettre à jour donnent aussi le code 1.

**Restaurer une sauvegarde.** Elle est faite par le `pg_dump` de la version du serveur, `/usr/lib/postgresql/<version>/bin/pg_dump` ([#384](https://github.com/dascritch/machincast/issues/384)), sinon par celui du `PATH` : le `pg_dump` du `PATH` est le plus récent installé, et sa sauvegarde ne se relirait pas avec un `pg_restore` plus ancien (`unsupported version (1.16) in file header`). Elle se relit avec le `pg_restore` du serveur, de préférence dans une base neuve, pour comparer avant de remplacer quoi que ce soit :

```bash
sudo -u postgres createdb --owner="$(id -un)" machincast_restauree
pg_restore --dbname=machincast_restauree --no-owner sauvegardes/machincast-2026-10-22T08-30-00.dump
```

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

**La durée** se règle dans `machincast.toml` ([Configuration](configuration.md#durée-de-péremption)), ou dans l'interface, **Fichier → Préférences…**, page **Base**. **Avec le service de diffusion** (`./install.sh --service`), un minuteur systemd la lance chaque jour à midi ([Service de diffusion](../../../INSTALL.fr.md#service-de-diffusion)) ; ses messages se lisent par `journalctl --unit=machincast-purge.service`. Sans service, elle se lance à la main.

## Suivre le journal : Machin logs

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
| 1 | Base de données injoignable ou perdue (pour `Machin interface`, au lancement), décodeur GStreamer manquant, autre indexation du même mode en cours sur la base, `Machin indexer --window` sans affichage graphique, sortie audio indisponible, autre `Machin player` déjà en diffusion, maintenance de la base inachevée ou avec un rôle manquant, purge de la base impossible, ou fonction pas encore écrite. |
| 2 | Configuration invalide, ou appel incorrect (option inconnue, `--config` sans fichier, option refusée avec une autre). |
| 127 | Programme ou `journalctl` introuvable, signalé par `Machin`. |

Les messages d'erreur courants et leur solution sont dans le tableau [En cas de problème](../../../INSTALL.fr.md#en-cas-de-problème) d'`INSTALL.md`.

## Démarrages et fins dans le log

`Machin player`, `Machin indexer`, `Machin maintenance-db` et `Machin purge` notent chacun de leurs lancements dans leur journal et dans le log de la base, que l'interface montre ([#341](https://github.com/dascritch/machincast/issues/341), [#342](https://github.com/dascritch/machincast/issues/342) pour `Machin player`, hors simulation). Une fausse manœuvre ou un plantage s'y retrouve, avec l'heure :

```text
2026-11-04T03:00:02+01:00 démarrage : Machin_indexer 0.9.0, pid 4812 : --full-audit
2026-11-04T03:12:47+01:00 fin : Machin_indexer, pid 4812 : code de sortie 0
```

- **Le démarrage**, nature `démarrage`, au niveau information : le programme, sa version, son numéro de processus (pid) et ses options.
- **La fin**, nature `fin` : le même pid, et le [code de sortie](#messages-et-codes-de-sortie). Elle est au niveau information pour le code 0, en **incident** pour tout autre code, comme le 2 d'une option refusée, et se lit alors dans l'onglet **Incidents** de l'interface.
- **Un plantage probable**, nature `plantage probable`, en incident : au lancement suivant d'un programme, si son démarrage précédent n'a pas noté de fin et que son processus ne tourne plus. Le programme a été tué, arrêté par un signal, ou le poste s'est éteint en cours de route : `Machin_purge, pid 3920, démarré le 03/11/2026 à 12:00, n'a pas noté sa fin`. S'il a laissé un [rapport de crash](#rapports-de-crash), le message se termine par son chemin : `; rapport de crash /opt/machincast/crash-dump/Machin_purge-2026-11-03T12-00-00-3920.txt`. Un lancement précédent encore en cours n'en est pas un. Le service de diffusion arrêté par `systemctl stop`, ou par le bouton de l'interface, note sa fin ; tué ou privé de courant, il note le plantage probable à son redémarrage.

`Machin indexer --sound N`, que `Machin player` lance avant chaque sonore qu'il va jouer, ne note ni démarrage ni fin. `Machin maintenance-db --keep-open`, lancé depuis l'interface, note sa fin avant que sa fenêtre reste ouverte : la fermer n'est pas un plantage. Une configuration invalide ne dit pas quelle base joindre : seul le journal en parle. Une base injoignable n'empêche pas le programme de tourner : le journal dit que son démarrage n'a pas été noté dans la base.

## Rapports de crash

Quand un programme de MachinCast plante, il laisse un **rapport de crash** dans le répertoire `crash-dump/` du répertoire de MachinCast (`/opt/machincast/crash-dump/` sur un poste installé), ou, s'il ne peut pas y écrire, dans `/tmp/machincast/crash-dump/`, vidé au redémarrage du poste ([#342](https://github.com/dascritch/machincast/issues/342)). Le journal le signale : `rapport de crash écrit : /opt/machincast/crash-dump/Machin_player-2026-11-09T14-03-12-4242.txt`. Le nom donne le programme, l'heure de son démarrage et son numéro de processus, les mêmes que dans le log.

Ce rapport est fait pour les développeurs : **joignez-le au ticket** qui signale le problème. Il contient :

- le programme, sa version, ses options, l'heure de son démarrage et celle du plantage ;
- la pile Python ;
- ce qu'ont répondu PostgreSQL, GStreamer ou le système, s'ils sont en cause, et les versions des outils ;
- pour `Machin indexer`, le fichier qu'il examinait ;
- pour `Machin interface`, les cartes son de l'antenne et de la pré-écoute, la sortie de `wpctl status` et le sonore en pré-écoute ;
- pour `Machin player`, la carte son de l'antenne, la sortie de `wpctl status`, et les sonores précédent, à l'antenne et les 5 suivants annoncés : événement, séquence, banque, artiste et titre, fichier.

Un programme qui s'arrête d'un coup, sur une erreur de GStreamer ou de Qt, tué par `kill -9` ou privé de courant, ne peut pas écrire son rapport sur le moment : son **lancement suivant** l'achève, avec ce qu'il avait noté en dernier, et sa fin dit `Fin : inconnue`. Les rapports s'accumulent : effacez-les quand le ticket est traité. Un fichier caché qui finit par `.en-cours` est le rapport d'un programme qui tourne encore ; ne l'effacez pas.

