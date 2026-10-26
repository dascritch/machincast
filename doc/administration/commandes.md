# Commandes et messages

[Guide d'administration](README.md) › Commandes et messages

- [Lancer les programmes : Machin](#lancer-les-programmes--machin)
- [Interface graphique : Machin interface](#interface-graphique--machin-interface)
- [Maintenance de la base : Machin maintenance-db](#maintenance-de-la-base--machin-maintenance-db)
- [Suivre le journal : Machin logs](#suivre-le-journal--machin-logs)
- [Messages et codes de sortie](#messages-et-codes-de-sortie)

## Lancer les programmes : Machin

Tous les programmes de MachinCast se lancent par une seule commande, `Machin`, installée par `install.sh` pour tout le système. Elle s'utilise depuis n'importe quel répertoire, sans activer d'environnement Python.

```bash
Machin indexation                     # lance Machin_indexation
Machin indexation --audit-complet     # les options qui suivent le programme lui sont transmises
Machin --help                         # aide complète
```

| Commande | Rôle |
| --- | --- |
| `Machin lecture` | Diffusion de l'antenne, normalement lancée comme service ([à venir](README.md#ce-qui-nexiste-pas-encore)). |
| `Machin indexation` | Enregistrement des fichiers déposés dans les répertoires des banques, vérification des fichiers sonores et mise à jour de la base. |
| `Machin interface` | Interface graphique de supervision et de programmation. Pour l'instant, son [écran par défaut](#interface-graphique--machin-interface), les [listes](../utilisateur/listes.md#listes), les fiches d'un [événement](../utilisateur/grille.md#fiche-dun-événement), d'une [séquence](../utilisateur/grille.md#fiche-dune-séquence), d'une [banque](../utilisateur/sonores.md#fiche-dune-banque) et d'un [sonore](../utilisateur/sonores.md#fiche-dun-sonore). |
| `Machin maintenance-db` | [Maintenance de la base de production](#maintenance-de-la-base--machin-maintenance-db) : sauvegarde, vérification du schéma et des rôles, optimisation. |
| `Machin logs` | Suivi en direct du journal du service de diffusion. |

**Options de `Machin`**, placées avant le nom du programme :

| Option | Effet |
| --- | --- |
| `--config FICHIER` ou `--config=FICHIER` | Fichier de configuration à transmettre au programme, au lieu de `machincast.toml` (voir [Configuration](configuration.md#configuration)). Placée après le nom du programme, l'option lui est transmise telle quelle, avec le même effet. |
| `-h` | Aide minimale, en deux lignes. |
| `--help` | Aide complète : programmes, options, exemples et codes de sortie. Elle affiche aussi le chemin du `machincast.toml` lu par défaut. |
| `--binaires` | Liste des programmes, un par ligne. L'autocomplétion s'en sert. |

**Options communes à chaque programme**, placées après son nom :

| Option | Effet |
| --- | --- |
| `-h`, `--help` | Aide du programme, par exemple `Machin indexation --help`. |
| `--version` | Version de MachinCast, par exemple `Machin_indexation (MachinCast) 0.1.0`. |
| `--config FICHIER` | Fichier de configuration à lire. |

**Autocomplétion.** Dans un terminal bash, la touche Tab complète les noms des programmes et `logs`, les options de `Machin`, les fichiers après `--config`, les options de chaque programme (lues dans son aide) et les options courantes de `journalctl` après `logs`. Elle demande le paquet `bash-completion`, qu'installe `install.sh`. Sans installation, `source bash-completion/Machin` la charge dans le terminal courant.

## Interface graphique : Machin interface

`Machin interface` ouvre l'interface graphique de l'équipe de l'antenne ; son usage est décrit dans le [guide de l'antenne](../utilisateur/README.md), que son menu **Aide → Documentation** ouvre dans le navigateur web.

- **Base** : elle se connecte à la base de production (`base.production`), avec le rôle `machincast_interface` ([Droits de chaque programme dans la base](configuration.md#droits-de-chaque-programme-dans-la-base)). Sans base, elle ouvre une fenêtre d'erreur, « MachinCast : base de données injoignable », qui renvoie à [En cas de problème](../../INSTALL.md#en-cas-de-problème) et donne l'erreur de PostgreSQL dans ses détails ; à sa fermeture, `Machin interface` s'arrête avec le code 1. Le message `base de données injoignable` (ou `erreur de base de données`, pour un compte sans droit) s'affiche aussi sur la sortie d'erreur. Sans affichage graphique, dans une session SSH par exemple, seul ce message s'affiche.
- **Même compte et même configuration que la diffusion** : l'accueil suit la diffusion par sa socket d'état, que seul le compte qui diffuse peut ouvrir ([État de la diffusion pour l'interface](diffusion.md#état-de-la-diffusion-pour-linterface)). Le menu **Diffusion** pilote le service de diffusion, avec l'authentification de la règle polkit du service ([Service de diffusion](../../INSTALL.md#service-de-diffusion)), ou, sans service, une diffusion d'essai lancée dans un terminal.
- **Réglages** : **Fichier → Préférences…** écrit dans les sections `[crossfades]`, `[audio]`, `[blancs]` et `[interface]` du `machincast.toml`, qui garde ses commentaires et ses autres réglages ; la fenêtre « Pour bien démarrer » écrit `audio.peripherique` et `interface.suggestions`. Un fichier qui ne peut pas être écrit laisse les réglages tels quels, et la barre d'état dit pourquoi. Une nouvelle icône de l'application (`interface.icone`, [#111](https://github.com/dascritch/machincast/issues/111)) réécrit aussi les raccourcis `machincast.desktop` déjà installés, dans `~/.local/share/applications` et sur le bureau, sans en créer ; l'image elle-même n'est ni copiée ni modifiée.
- **Indexation** : le menu **Maintenance** lance `Machin indexation --fenetre`, avec la configuration de l'interface, dans son propre programme ([Indexation : Machin indexation](indexation.md)).
- **Simulation** : l'onglet Simulation lance `Machin lecture --simulation`, avec la configuration de l'interface, ses fichiers dans un répertoire temporaire (`--repertoire`) effacé à la fermeture de l'onglet ([Simuler la diffusion](diffusion.md#simuler-la-diffusion)).

## Maintenance de la base : Machin maintenance-db

`Machin maintenance-db` ([#127](https://github.com/dascritch/machincast/issues/127)) entretient la base de production (`base.production`), en trois étapes, dans l'ordre :

1. **Sauvegarde** : `pg_dump` copie la base dans un nouveau fichier daté, `<base>-<AAAA-MM-JJTHH-MM-SS>.dump`, au format personnalisé de PostgreSQL. Il s'écrit dans le répertoire `sauvegardes`, à côté du fichier de configuration, ou dans celui de `--sauvegardes`, créé au besoin. Aucune sauvegarde n'est effacée : les anciennes se suppriment à la main. **Une sauvegarde qui échoue arrête la maintenance**, sans rien modifier.
2. **Schéma** : les migrations manquantes sont appliquées, comme le fait `install.sh`, puis chacun des trois rôles de MachinCast doit pouvoir être endossé par le compte. Un rôle absent ou non autorisé est signalé, avec les deux commandes qu'un administrateur lance pour l'autoriser.
3. **Optimisation** : `VACUUM (ANALYZE)` récupère la place des lignes effacées et met à jour les statistiques qui guident PostgreSQL. La diffusion peut continuer pendant ce temps.

Le compte qui la lance doit être celui de MachinCast, propriétaire de la base : il n'a besoin d'aucun droit particulier sur le serveur. Elle se lance aussi depuis l'interface, menu **Maintenance → Maintenance de la base de données…**. L'interface demande d'abord confirmation, en donnant le répertoire où la sauvegarde sera enregistrée (`sauvegardes`, à côté de sa configuration), que le bouton « Choisir l'emplacement… » permet de changer. Elle l'ouvre ensuite dans une fenêtre de terminal, avec la configuration de l'interface et ce répertoire (`--sauvegardes`) ; la fenêtre reste ouverte à la fin, jusqu'à ce qu'on la ferme.

```bash
Machin maintenance-db
Machin maintenance-db --sauvegardes /srv/sauvegardes/machincast
```

| Option | Effet |
| --- | --- |
| `--sauvegardes REPERTOIRE` | Répertoire des sauvegardes, au lieu de `sauvegardes` à côté du fichier de configuration. |
| `--garder-ouvert` | Une fois la maintenance finie, garde le terminal ouvert jusqu'à sa fermeture (ou `Ctrl-D`, `Ctrl-C`) ; Entrée n'y fait rien. L'interface s'en sert, pour que le compte rendu reste lisible. |

Elle se termine par `maintenance terminée` (code 0), ou par `maintenance terminée, avec des anomalies` (code 1) quand un rôle manque. Une base injoignable ou une sauvegarde impossible donnent aussi le code 1.

**Restaurer une sauvegarde.** Elle se relit avec `pg_restore`, de préférence dans une base neuve, pour comparer avant de remplacer quoi que ce soit :

```bash
sudo -u postgres createdb --owner="$(id -un)" machincast_restauree
pg_restore --dbname=machincast_restauree --no-owner sauvegardes/machincast-2026-10-22T08-30-00.dump
```

## Suivre le journal : Machin logs

`Machin logs` suit en direct le journal du service de diffusion, `machincast.service`. Les options qui suivent sont transmises à `journalctl`, par exemple :

```bash
Machin logs --since "1 hour ago" --priority=warning
```

Lire ce journal demande d'appartenir au groupe `systemd-journal`, ce que fait `install.sh`, effectif après le redémarrage du poste. Tant que le service de diffusion n'est pas installé ([#22](https://github.com/dascritch/machincast/issues/22), [Service de diffusion](../../INSTALL.md#service-de-diffusion)), le journal est vide : `Machin lecture`, lancé à la main, écrit dans son terminal. `Ctrl-C` arrête le suivi.

## Messages et codes de sortie

Chaque message commence par son heure, en ISO 8601, à la seconde, avec le décalage horaire du poste, par exemple `2026-10-23T07:55:19+02:00 à l'antenne : Frédéric Galliano – Multiples Un (Fil musical)` ([#253](https://github.com/dascritch/machincast/issues/253)) ; elle remplace le nom du programme, qui le précédait. Le journal du service (`Machin logs`) ajoute sa propre heure devant. Les informations, comme le bilan d'une indexation, vont sur la sortie standard ; les anomalies et les erreurs, sur la sortie d'erreur. Un script peut ainsi garder les unes et les autres séparément.

| Code | Signification |
| --- | --- |
| 0 | Le programme est allé au bout. Pour l'indexation, même si des sonores ont changé d'état : ce sont des anomalies, pas des erreurs. |
| 1 | Base de données injoignable ou perdue (pour `Machin interface`, au lancement), décodeur GStreamer manquant, autre indexation en cours sur la base, `Machin indexation --fenetre` sans affichage graphique, sortie audio indisponible, autre `Machin lecture` déjà en diffusion, maintenance de la base inachevée ou avec un rôle manquant, ou fonction pas encore écrite. |
| 2 | Configuration invalide, ou appel incorrect (option inconnue, `--config` sans fichier). |
| 127 | Programme ou `journalctl` introuvable, signalé par `Machin`. |

Les messages d'erreur courants et leur solution sont dans le tableau [En cas de problème](../../INSTALL.md#en-cas-de-problème) d'`INSTALL.md`.
