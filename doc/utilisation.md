# Guide d'utilisation

Ce guide décrit ce que MachinCast sait déjà faire, pour l'utilisateur et l'administrateur du poste de diffusion. Il ne demande pas de connaître le code. L'installation est décrite dans [INSTALL.md](../INSTALL.md) ; le fonctionnement complet visé, dans la [spécification](spec.md).

> **État du projet** : MachinCast est en cours de développement. Aujourd'hui, `Machin indexation` enregistre les fichiers déposés dans les répertoires des banques et vérifie les sonores. La diffusion (`Machin lecture`) et l'interface graphique (`Machin interface`) sont à venir : la section [Ce qui n'existe pas encore](#ce-qui-nexiste-pas-encore) donne le ticket de chaque manque.

## Sommaire

- [Lancer les programmes : Machin](#lancer-les-programmes--machin)
- [Configuration](#configuration)
- [Vérifier les sonores : Machin indexation](#vérifier-les-sonores--machin-indexation)
- [Diffusion : Machin lecture](#diffusion--machin-lecture)
- [Interface graphique : Machin interface](#interface-graphique--machin-interface)
- [Suivre le journal : Machin logs](#suivre-le-journal--machin-logs)
- [Messages et codes de sortie](#messages-et-codes-de-sortie)
- [Droits de chaque programme dans la base](#droits-de-chaque-programme-dans-la-base)
- [Ce qui n'existe pas encore](#ce-qui-nexiste-pas-encore)

## Lancer les programmes : Machin

Tous les programmes de MachinCast se lancent par une seule commande, `Machin`, installée par `install.sh` pour tout le système. Elle s'utilise depuis n'importe quel répertoire, sans activer d'environnement Python.

```bash
Machin indexation                     # lance Machin_indexation
Machin indexation --audit-complet     # les options qui suivent le programme lui sont transmises
Machin --help                         # aide complète
```

| Commande | Rôle |
| --- | --- |
| `Machin lecture` | Diffusion de l'antenne, normalement lancée comme service. [Pas encore écrite](#diffusion--machin-lecture). |
| `Machin indexation` | Enregistrement des fichiers déposés dans les répertoires des banques, vérification des fichiers sonores et mise à jour de la base. |
| `Machin interface` | Interface graphique de programmation. [Pas encore écrite](#interface-graphique--machin-interface). |
| `Machin logs` | Suivi en direct du journal du service de diffusion. |

**Options de `Machin`**, placées avant le nom du programme :

| Option | Effet |
| --- | --- |
| `--config FICHIER` ou `--config=FICHIER` | Fichier de configuration à transmettre au programme, au lieu de `machincast.toml` (voir [Configuration](#configuration)). Placée après le nom du programme, l'option lui est transmise telle quelle, avec le même effet. |
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

## Configuration

Chaque programme lit sa configuration dans le fichier `machincast.toml` **du répertoire de MachinCast**, quel que soit le répertoire d'où il est lancé ([#76](https://github.com/dascritch/machincast/issues/76)). `Machin --help` affiche son chemin complet. Une autre configuration, placée elle aussi dans le répertoire de MachinCast, se désigne par `--config`.

Le modèle commenté est `machincast.exemple.toml`, et le [tableau des clés de la spécification](spec.md#9-configuration) donne le type et le rôle de chacune. Toute clé inconnue est refusée, pour détecter les fautes de frappe : le programme s'arrête alors avec le code 2 et un message qui nomme le fichier et la clé, par exemple :

```text
Machin_indexation : configuration invalide : /home/xavier/machincast/machincast.toml : clé audio.sortei inconnue
```

Les chemins relatifs du fichier (sorties CSV, HTML et .pls) se comprennent depuis le répertoire du fichier de configuration.

## Vérifier les sonores : Machin indexation

`Machin indexation` fait deux choses, dans cet ordre :

1. il enregistre les fichiers déposés dans les répertoires des banques, et les range dans leur banque ;
2. il vérifie que les fichiers des sonores sont présents et sains, met à jour leur durée et leurs tags, et change leur état si besoin.

Il ne modifie jamais les fichiers sonores eux-mêmes, et ne supprime jamais un sonore de la base.

### Alimenter une banque

Alimenter une banque se limite à déposer des fichiers dans l'un de ses répertoires, puis à lancer `Machin indexation` ([#9](https://github.com/dascritch/machincast/issues/9)). Les répertoires d'une banque se choisissent dans l'interface ([#31](https://github.com/dascritch/machincast/issues/31)) ; une banque peut en avoir plusieurs, et un même répertoire peut alimenter plusieurs banques.

- **Sous-répertoires** : ils sont tous parcourus, dans l'ordre de leur nom. Un lien symbolique vers un autre répertoire n'est pas suivi, pour éviter les boucles ; le répertoire d'une banque peut, lui, être un lien.
- **Formats** : `.mp3`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.wav`, `.aiff` et `.aif`, que l'extension soit écrite en minuscules ou en majuscules. Les autres fichiers (pochettes, textes, vidéos `.mp4`…) sont ignorés.
- **Fichiers cachés** : un fichier ou un répertoire dont le nom commence par un point est ignoré, comme les fichiers `._*.mp3` qu'écrit macOS sur un disque partagé.
- **Nouveau fichier** : il devient un sonore à l'état `aperçu`, ajouté **en fin de liste** de la banque, puis décodé dans la même indexation. Les fichiers d'un même passage sont ajoutés dans l'ordre de leur chemin.
- **Fichier déjà connu** : il n'est jamais enregistré deux fois, même trouvé par plusieurs banques. Il est ajouté en fin de liste de chaque banque dont il n'est pas encore membre.
- **Sonore retiré à la main d'une banque** : tant que son fichier reste dans l'un des répertoires de la banque, l'indexation suivante l'y **réintègre**, en fin de liste. Pour l'en retirer durablement, il faut déplacer le fichier hors de ses répertoires.
- **Répertoire introuvable** : il est signalé sur la sortie d'erreur, avec le nom de la banque, et les autres banques sont indexées normalement. Un sous-répertoire illisible est signalé de la même façon.
- **Fichier déplacé** : à son nouvel emplacement, c'est un nouveau sonore ; l'ancien passe à l'état `supprimé`.

### Indexation rapide et audit complet

| Commande | Ce qui est vérifié |
| --- | --- |
| `Machin indexation` | **Indexation rapide**, par défaut. Seuls les sonores à l'état `aperçu`, c'est-à-dire nouvellement trouvés, sont décodés et leurs tags lus. Pour les autres, seule la présence du fichier est contrôlée : un fichier disparu est quand même repéré. |
| `Machin indexation --audit-complet` | **Audit complet** : tous les sonores de type fichier sont décodés. C'est lui qui repère un fichier abîmé après son indexation, ou modifié depuis. À lancer après la première indexation, puis de temps en temps. |

Le décodage est fait sans jouer le son, bien plus vite que le temps réel : une dizaine de minutes de son en moins d'une seconde. Un audit complet d'une grande discothèque peut tout de même prendre du temps.

Les streams ne sont jamais vérifiés.

### Verdicts de la vérification d'un fichier

Chaque fichier décodé reçoit l'un de ces verdicts :

| Verdict | Signification |
| --- | --- |
| `sain` | Le fichier se décode entièrement. Sa durée décodée, sa date de modification et sa taille sont enregistrées. |
| `endommagé` | Le fichier se décode, mais des données manquent : rupture de continuité dans le son, ou durée décodée plus courte que celle annoncée par l'en-tête du fichier (fichier tronqué, trames perdues). |
| `illisible` | Le fichier n'est pas du son, il est vide ou son conteneur est cassé, aucun son n'a pu être décodé, ou le décodage ne progresse plus pendant 30 secondes (disque ou partage réseau bloqué). |
| `introuvable` | Aucun fichier à l'emplacement enregistré : il a été supprimé ou déplacé. |

Un décodage qui ne produit aucun son en 5 secondes est repris depuis le début, jusqu'à trois fois : un disque réseau en veille a ainsi le temps de répondre.

Quelques défauts échappent à la vérification : des octets altérés dans un WAV ou un AIFF, qui n'ont ni somme de contrôle ni trames ; un WAV, un Ogg, un MP3 sans durée dans son en-tête ou un AAC brut (`.aac`), tronqué, qui se décode comme un fichier plus court mais sain.

### États d'un sonore

| État | Sens | Jouable | Comment il en sort |
| --- | --- | --- | --- |
| `aperçu` | Fichier nouvellement trouvé, pas encore décodé. | non | Par l'indexeur, au premier décodage sain : il devient `actif`. |
| `actif` | Sonore en service. | oui, dans sa période de diffusion et sous son maximum de lectures | — |
| `désactivé` | Retiré de l'antenne par un choix humain, dans l'interface. | non | Par l'interface seulement. |
| `expiré` | Maximum de lectures atteint, ou période de diffusion terminée. | non | Par l'interface seulement. |
| `erroné` | Fichier `endommagé` ou `illisible`. | non | Automatiquement, quand l'indexeur trouve le fichier redevenu sain : il redevient `actif`. |
| `supprimé` | Fichier `introuvable`. | non | Par l'interface seulement. Un fichier déplacé est réindexé comme un nouveau sonore. |

L'indexeur ne change que l'état d'un sonore en `aperçu`, `actif` ou `erroné` :

| État avant | Fichier `sain` | Fichier `endommagé` ou `illisible` | Fichier `introuvable` |
| --- | --- | --- | --- |
| `aperçu` | `actif` | `erroné` | `supprimé` |
| `actif` | `actif` | `erroné` | `supprimé` |
| `erroné` | `actif` | `erroné` | `supprimé` |
| `désactivé`, `expiré`, `supprimé` | inchangé | inchangé, anomalie signalée | inchangé, anomalie signalée |

L'indexeur ne supprime jamais un sonore de la base.

### Tags et métadonnées

Pour un fichier `sain`, l'indexeur lit les tags du fichier pendant le décodage : ID3 (MP3, et AIFF quand il en porte), commentaires Vorbis (Ogg, FLAC), atomes MP4 (M4A) et chunk INFO (WAV, qui ne porte que l'artiste, le titre, l'album, le genre et l'année).

| Champ du sonore | Tag lu |
| --- | --- |
| `artiste` | artiste, tronqué à 255 caractères |
| `titre` | titre, tronqué à 255 caractères |
| `annee` | année de la date de sortie. Un horodatage avec une heure, comme la date de création qu'annoncent certains M4A, n'est jamais pris pour l'année du morceau. |
| `album` | album |
| `artiste_album` | artiste de l'album |
| `genre` | genre |
| `compositeur` | compositeur |
| `label` | organisation (Vorbis `ORGANIZATION`) ou éditeur (ID3 `TPUB`) |
| `piste` | numéro de piste |

Les champs suivent les tags du fichier : un tag retiré du fichier vide le champ au passage suivant. **Un champ modifié à la main dans l'interface n'est plus jamais écrasé** par l'indexeur. Les tags d'un fichier défectueux ne sont pas lus, et les valeurs en base restent telles quelles.

### Ce qu'affiche l'indexation

Une ligne par fichier défectueux, sur la sortie d'erreur, avec le chemin du fichier, le problème et sa conséquence :

```text
Machin_indexation : /musique/jingles/intro.mp3 : endommagé : 2 rupture(s) de continuité au décodage, des données ont été perdues ; sonore passé erroné
Machin_indexation : /musique/fond/nappe.flac : introuvable : aucun fichier à cet emplacement ; état désactivé conservé
```

Puis le bilan, sur la sortie standard :

```text
Machin_indexation : indexation rapide : 3 nouveaux sonores, 1 rattachement ; 3 sonores vérifiés ; 1 erroné, 1 supprimé, 0 rétabli, 3 sortis d'aperçu
```

Les nouveaux sonores sont les fichiers enregistrés pour la première fois ; les rattachements, les sonores déjà connus ajoutés à une banque dont ils n'étaient pas membres. Les sonores vérifiés sont ceux qui ont été décodés ; les autres nombres comptent les changements d'état. Un regroupement de ces anomalies dans un document d'audit, en CSV et en HTML, est à venir ([#11](https://github.com/dascritch/machincast/issues/11)).

Si GStreamer n'a pas de décodeur pour un format, la vérification s'arrête et nomme les paquets à installer, sans changer l'état des sonores : le fichier n'y est pour rien.

## Diffusion : Machin lecture

`Machin lecture` lit sa configuration, puis s'arrête avec le code 1 et le message `pas encore implémenté`, avec le lien du ticket de la diffusion. Le choix des sonores, la lecture audio et le mode simulation sont à venir (voir [Ce qui n'existe pas encore](#ce-qui-nexiste-pas-encore)). Le choix de l'événement à diffuser est déjà écrit, et suit les règles ci-dessous.

### Quel événement est à l'antenne

À tout instant, la diffusion suit **un seul événement**, choisi ainsi ([#12](https://github.com/dascritch/machincast/issues/12)) :

- **Priorité** : un événement `spécial` l'emporte sur une `émission`, qui l'emporte sur un `fil musical`. Quand l'événement prioritaire se termine, celui qui est en dessous reprend.
- **Fil musical permanent** : un fil musical sans date de début ni de fin couvre tout le temps où rien d'autre n'est programmé.
- **Dates** : le début et la fin d'un événement sont ceux de sa première diffusion. L'événement est à l'antenne de son début, inclus, à sa fin, exclue : une émission de 20:00 à 22:00 laisse la place à 22:00 pile.
- **Récurrence** : un événement qui se répète revient chacun des jours cochés, à la même heure, à partir de sa première diffusion. Il n'a pas de date de fin de récurrence, ni d'exception pour les jours fériés.
- **Passage de minuit** : un événement peut commencer un jour et finir le lendemain, par exemple de 23:00 à 01:00. Pour un événement récurrent, c'est le jour du début qui compte : une émission du lundi 23:00 à 01:00 est à l'antenne dans la nuit du lundi au mardi.
- **Fils musicaux selon l'heure** : plusieurs fils musicaux peuvent se relayer, par exemple un fil de nuit de 00:00 à 06:00 et un fil de jour de 06:00 à 00:00, tous les jours.
- **Émission ou spécial sans fin** : il reste à l'antenne jusqu'à la fin de sa liste de lecture, qui ne boucle pas ; l'événement en dessous reprend alors. S'il est récurrent, il revient à sa prochaine date.
- **Chevauchement** : deux événements de même priorité ne devraient pas se chevaucher, et l'interface l'empêchera. Si c'est le cas quand même, c'est le dernier modifié qui passe.
- **Changement d'heure** : un événement garde son heure. Une émission quotidienne de 21:00 reste à 21:00 après le passage à l'heure d'été ou d'hiver. La nuit du changement d'heure, l'heure sautée ou répétée tombe dans le fil musical de nuit.

Toutes les heures de la grille sont en heure de Paris, l'heure locale du poste.

### Sortie audio

La sortie audio de l'antenne est déjà réglée dans la configuration (`audio.sortie` : `pipewire`, `pulseaudio`, `alsa`, ou `factice` pour un essai sans son), et `install.sh` vérifie qu'elle peut être créée.

## Interface graphique : Machin interface

`Machin interface` lit sa configuration, puis s'arrête avec le code 1 et le message `pas encore implémenté`, avec le lien du ticket de l'écran par défaut ([#23](https://github.com/dascritch/machincast/issues/23)).

## Suivre le journal : Machin logs

`Machin logs` suit en direct le journal du service de diffusion, `machincast.service`. Les options qui suivent sont transmises à `journalctl`, par exemple :

```bash
Machin logs --since "1 hour ago" --priority=warning
```

Lire ce journal demande d'appartenir au groupe `systemd-journal`, ce que fait `install.sh`, effectif après le redémarrage du poste. Tant que le service de diffusion n'est pas installé ([#22](https://github.com/dascritch/machincast/issues/22)), le journal est vide. `Ctrl-C` arrête le suivi.

## Messages et codes de sortie

Chaque message commence par le nom du programme, par exemple `Machin_indexation :`. Les informations, comme le bilan d'une indexation, vont sur la sortie standard ; les anomalies et les erreurs, sur la sortie d'erreur. Un script peut ainsi garder les unes et les autres séparément.

| Code | Signification |
| --- | --- |
| 0 | Le programme est allé au bout. Pour l'indexation, même si des sonores ont changé d'état : ce sont des anomalies, pas des erreurs. |
| 1 | Base de données injoignable, décodeur GStreamer manquant, ou fonction pas encore écrite. |
| 2 | Configuration invalide, ou appel incorrect (option inconnue, `--config` sans fichier). |
| 127 | Programme ou `journalctl` introuvable, signalé par `Machin`. |

Les messages d'erreur courants et leur solution sont dans le tableau [En cas de problème](../INSTALL.md#en-cas-de-problème) d'`INSTALL.md`.

## Droits de chaque programme dans la base

Chaque programme agit dans la base avec ses propres droits : le compte qui le lance n'a accès à rien par lui-même, et le programme endosse son rôle PostgreSQL dès la connexion. Un programme ne peut donc pas faire plus que ce qui suit, même lancé par un compte qui a les trois rôles.

| Programme | Rôle PostgreSQL | Ce qu'il peut faire |
| --- | --- | --- |
| `Machin lecture` | `machincast_lecture` | Lire la programmation ; passer un sonore à `expiré` ; ajouter des lignes à l'airplay et au log, sans jamais les modifier ni les supprimer. |
| `Machin indexation` | `machincast_indexation` | Lire les banques et leurs répertoires ; ajouter et mettre à jour des sonores, et les ranger dans les banques. Il ne supprime rien et n'écrit pas dans le log. |
| `Machin interface` | `machincast_interface` | Tout modifier dans les sonores, les banques et les événements ; lire l'airplay et le log, sans les modifier. |

Le détail, table par table, est dans la [spécification, § 3.2](spec.md#32-rôles-et-droits). Ajouter un autre compte est décrit dans [INSTALL.md](../INSTALL.md#ajouter-un-autre-compte).

## Ce qui n'existe pas encore

| Manque | Ticket |
| --- | --- |
| Document d'audit des anomalies de l'indexation, en CSV et HTML | [#11](https://github.com/dascritch/machincast/issues/11) |
| Diffusion : choix de l'événement actif et des sonores, lecture audio, streams | [#12](https://github.com/dascritch/machincast/issues/12) à [#16](https://github.com/dascritch/machincast/issues/16) |
| Airplay, log et désactivations automatiques | [#17](https://github.com/dascritch/machincast/issues/17), [#18](https://github.com/dascritch/machincast/issues/18) |
| Mode simulation de la diffusion | [#21](https://github.com/dascritch/machincast/issues/21) |
| Service systemd de diffusion | [#22](https://github.com/dascritch/machincast/issues/22) |
| Interface graphique | [#23](https://github.com/dascritch/machincast/issues/23) et suivants |
| Outils du poste de développement | [#77](https://github.com/dascritch/machincast/issues/77) |
