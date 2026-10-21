# Commandes et messages

[Guide d'administration](README.md) › Commandes et messages

- [Lancer les programmes : Machin](#lancer-les-programmes--machin)
- [Interface graphique : Machin interface](#interface-graphique--machin-interface)
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

## Suivre le journal : Machin logs

`Machin logs` suit en direct le journal du service de diffusion, `machincast.service`. Les options qui suivent sont transmises à `journalctl`, par exemple :

```bash
Machin logs --since "1 hour ago" --priority=warning
```

Lire ce journal demande d'appartenir au groupe `systemd-journal`, ce que fait `install.sh`, effectif après le redémarrage du poste. Tant que le service de diffusion n'est pas installé ([#22](https://github.com/dascritch/machincast/issues/22), [Service de diffusion](../../INSTALL.md#service-de-diffusion)), le journal est vide : `Machin lecture`, lancé à la main, écrit dans son terminal. `Ctrl-C` arrête le suivi.

## Messages et codes de sortie

Chaque message commence par le nom du programme, par exemple `Machin_indexation :`. Les informations, comme le bilan d'une indexation, vont sur la sortie standard ; les anomalies et les erreurs, sur la sortie d'erreur. Un script peut ainsi garder les unes et les autres séparément.

| Code | Signification |
| --- | --- |
| 0 | Le programme est allé au bout. Pour l'indexation, même si des sonores ont changé d'état : ce sont des anomalies, pas des erreurs. |
| 1 | Base de données injoignable ou perdue (pour `Machin interface`, au lancement), décodeur GStreamer manquant, autre indexation en cours sur la base, `Machin indexation --fenetre` sans affichage graphique, sortie audio indisponible, autre `Machin lecture` déjà en diffusion, ou fonction pas encore écrite. |
| 2 | Configuration invalide, ou appel incorrect (option inconnue, `--config` sans fichier). |
| 127 | Programme ou `journalctl` introuvable, signalé par `Machin`. |

Les messages d'erreur courants et leur solution sont dans le tableau [En cas de problème](../../INSTALL.md#en-cas-de-problème) d'`INSTALL.md`.
