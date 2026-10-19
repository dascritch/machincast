# Guide d'utilisation

Ce guide décrit ce que MachinCast sait déjà faire, pour l'utilisateur et l'administrateur du poste de diffusion. Il ne demande pas de connaître le code. L'installation est décrite dans [INSTALL.md](../INSTALL.md) ; le fonctionnement complet visé, dans la [spécification](spec.md).

> **État du projet** : MachinCast est en cours de développement. Aujourd'hui, `Machin indexation` enregistre les fichiers déposés dans les répertoires des banques et vérifie les sonores, `Machin lecture` diffuse la grille depuis un terminal, et `Machin interface` montre ce qui passe à l'antenne, et gère les banques et les sonores. Le service de diffusion et les autres écrans de l'interface sont à venir : la section [Ce qui n'existe pas encore](#ce-qui-nexiste-pas-encore) donne le ticket de chaque manque.

## Sommaire

- [Lancer les programmes : Machin](#lancer-les-programmes--machin)
- [Configuration](#configuration)
- [Les fichiers sonores ne sont jamais modifiés](#les-fichiers-sonores-ne-sont-jamais-modifiés)
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
| `Machin lecture` | Diffusion de l'antenne, normalement lancée comme service ([à venir](#ce-qui-nexiste-pas-encore)). |
| `Machin indexation` | Enregistrement des fichiers déposés dans les répertoires des banques, vérification des fichiers sonores et mise à jour de la base. |
| `Machin interface` | Interface graphique de supervision et de programmation. Pour l'instant, son [écran par défaut](#interface-graphique--machin-interface), les [listes](#listes), les fiches d'une [banque](#fiche-dune-banque), d'un [sonore](#fiche-dun-sonore) et d'une [séquence](#fiche-dune-séquence). |
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

## Les fichiers sonores ne sont jamais modifiés

MachinCast ne fait que **lire** les fichiers sonores ([#96](https://github.com/dascritch/machincast/issues/96)). Aucun de ses programmes ne les supprime, ne les renomme, ne les déplace, ne les remplace ni n'y écrit, quoi qu'il arrive à leur entrée dans la base :

- un sonore passé à l'état `supprimé`, `désactivé`, `expiré` ou `erroné` garde son fichier tel quel ;
- un sonore dont l'emplacement, l'artiste ou le titre change garde son fichier tel quel ;
- un sonore supprimé de la base garde son fichier : s'il est encore dans le répertoire d'une banque, la prochaine indexation l'enregistre de nouveau, comme un nouveau sonore à l'état `aperçu`, puis `actif` une fois vérifié.

Supprimer un fichier sonore du disque reste une décision humaine, prise hors de MachinCast.

Pour la même raison, une sortie ne peut pas être placée sur un fichier sonore. La configuration refuse un chemin de `sorties.csv`, `sorties.pls`, `sorties.html` ou `lecture.socket_etat` qui se termine par l'extension d'un fichier sonore (`.mp3`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.wav`, `.aiff`, `.aif`, en majuscules comme en minuscules), avec le code de sortie 2 :

```text
Machin_lecture : configuration invalide : /home/xavier/machincast/machincast.toml : clé sorties.csv : « musique/airplay.mp3 » porte l'extension d'un fichier sonore, et MachinCast n'écrit jamais dans un fichier sonore
```

Si une sortie devait malgré tout tomber sur un tel chemin, elle n'est pas écrite : elle est signalée dans le log par l'alerte `sortie inaccessible`, qui mentionne `fichier sonore protégé`, et la diffusion continue. De même, la socket d'état n'est alors pas ouverte : l'alerte `socket d'état indisponible` est notée, et la diffusion continue sans elle. Les fichiers d'une simulation finissent toujours par `.csv`, `.pls` ou `.html` : quel que soit leur nom, ils ne remplacent jamais un fichier sonore.

## Vérifier les sonores : Machin indexation

`Machin indexation` fait deux choses, dans cet ordre :

1. il enregistre les fichiers déposés dans les répertoires des banques, et les range dans leur banque ;
2. il vérifie que les fichiers des sonores sont présents et sains, met à jour leur durée et leurs tags, et change leur état si besoin.

Il ne modifie jamais les fichiers sonores eux-mêmes, et ne supprime jamais un sonore de la base.

### Alimenter une banque

Alimenter une banque se limite à déposer des fichiers dans l'un de ses répertoires, puis à lancer `Machin indexation` ([#9](https://github.com/dascritch/machincast/issues/9)). Les répertoires d'une banque se choisissent dans [sa fiche](#fiche-dune-banque), dans l'interface ([#31](https://github.com/dascritch/machincast/issues/31)) ; une banque peut en avoir plusieurs, et un même répertoire peut alimenter plusieurs banques.

- **Sous-répertoires** : ils sont tous parcourus, dans l'ordre de leur nom. Un lien symbolique vers un autre répertoire n'est pas suivi, pour éviter les boucles ; le répertoire d'une banque peut, lui, être un lien.
- **Formats** : `.mp3`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.wav`, `.aiff` et `.aif`, que l'extension soit écrite en minuscules ou en majuscules. Les autres fichiers (pochettes, textes, vidéos `.mp4`…) sont ignorés.
- **Fichiers cachés** : un fichier ou un répertoire dont le nom commence par un point est ignoré, comme les fichiers `._*.mp3` qu'écrit macOS sur un disque partagé.
- **Nouveau fichier** : il devient un sonore à l'état `aperçu`, ajouté **en fin de liste** de la banque, puis décodé dans la même indexation. Les fichiers d'un même passage sont ajoutés dans l'ordre de leur chemin.
- **Fichier déjà connu** : il n'est jamais enregistré deux fois, même trouvé par plusieurs banques. Il est ajouté en fin de liste de chaque banque dont il n'est pas encore membre.
- **Sonore retiré à la main d'une banque** : tant que son fichier reste dans l'un des répertoires de la banque, l'indexation suivante l'y **réintègre**, en fin de liste. Pour l'en retirer durablement, il faut déplacer le fichier hors de ses répertoires. La [fiche de la banque](#fiche-dune-banque) le rappelle au retrait.
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
| `expiré` | Maximum de lectures atteint, ou période de diffusion terminée : posé par `Machin lecture` ([#18](https://github.com/dascritch/machincast/issues/18)). | non | Par l'interface seulement. |
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

Les champs suivent les tags du fichier : un tag retiré du fichier vide le champ au passage suivant. **Un champ modifié à la main dans l'interface n'est plus jamais écrasé** par l'indexeur ([Fiche d'un sonore](#fiche-dun-sonore)). Les tags d'un fichier défectueux ne sont pas lus, et les valeurs en base restent telles quelles.

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

`Machin lecture` diffuse la grille sur la sortie audio de la configuration, en continu, jusqu'à ce qu'on l'arrête ([#88](https://github.com/dascritch/machincast/issues/88)), fichiers et streams. Il sait aussi simuler une période à l'avance, sans son ni écriture en base (voir [Simuler la diffusion](#simuler-la-diffusion)). Le service systemd est à venir (voir [Ce qui n'existe pas encore](#ce-qui-nexiste-pas-encore)).

### Lancer et arrêter la diffusion

```bash
Machin lecture                   # avec le machincast.toml du répertoire de MachinCast
Machin lecture --config <fichier>
```

- **Base** : `Machin lecture` diffuse la grille de la base de production (`base.production`), avec le rôle `machincast_lecture`. Si la base est injoignable, il s'arrête aussitôt avec le code 1 et le message `base de données injoignable`.
- **Sortie** : il joue sur la sortie de `audio.sortie`. Si elle ne peut pas être créée, il s'arrête avec le code 1 et le message `sortie audio indisponible`.
- **En marche** : il affiche la sortie utilisée, note `démarrage` dans le log, puis enchaîne les sonores sans intervention. Chaque passage est écrit dans l'airplay au moment où il commence et où il finit.
- **Arrêt** : `Ctrl-C` dans le terminal, ou le signal `SIGTERM` (arrêt d'un service). Le sonore en cours s'arrête, son passage est terminé dans l'airplay, sans incident, `arrêt` est noté dans le log, et le programme s'arrête avec le code 0.
- **Perte de la base en cours de diffusion** : la sortie se coupe, et le programme s'arrête avec le code 1 et le message `erreur de base de données`.
- **Un seul `Machin lecture` à la fois** : deux diffusions en même temps joueraient chacune leurs sonores et écriraient chacune leur airplay. Un second `Machin lecture` lancé sur la même socket d'état est refusé : il s'arrête avec le code 1 et le message `diffusion refusée : … un autre Machin lecture diffuse déjà`.

### Simuler la diffusion

Pour vérifier une grille avant sa mise à l'antenne, `Machin lecture` simule ce qu'il diffuserait entre deux dates et heures ([#21](https://github.com/dascritch/machincast/issues/21)) :

```bash
Machin lecture --simulation "2026-10-20 06:00" "2026-10-20 22:00"
Machin lecture --simulation "2026-10-20 06:00" "2026-10-21 06:00" --graine 42 --nom essai-mardi
```

| Option | Rôle |
| --- | --- |
| `--simulation DEBUT FIN` | Période simulée, en heure du poste : `2026-10-20 20:00`, ou `2026-10-20T20:00:00`. La fin doit suivre le début. |
| `--graine N` | Graine du hasard : la même graine donne la même simulation, tirages aléatoires compris. Sans graine, chaque simulation tire autrement. |
| `--nom NOM` | Nom des fichiers produits, sans extension ni `/`. Par défaut, `simulation-` suivi des dates de début et de fin, par exemple `simulation-2026-10-20T0600-2026-10-20T2200`. |

- **Rien n'est écrit en base**, au sens strict : la simulation lit la base de production dans une transaction en lecture seule, où PostgreSQL refuse toute écriture. Elle part de l'état réel, c'est-à-dire la position dans chaque liste, le cycle de chaque banque aléatoire et le nombre de lectures de chaque sonore, puis tient ses propres passages en mémoire. Un sonore qui atteindrait son maximum de lectures pendant la simulation est noté expiré dans la simulation seulement.
- **Aucun son n'est joué**, et la sortie audio n'est pas ouverte : une simulation peut tourner pendant la diffusion, sur le même poste. Elle ne dure que quelques secondes pour une journée.
- **Durées** : ce sont celles de la base, mesurées par l'indexation. Un stream n'est pas contacté : la simulation suppose qu'il tient jusqu'à la fin de son événement.
- **Mêmes règles que la diffusion** : priorités, coupures nettes, crossfades, fichiers disparus (incident `fichier introuvable`), silences (alerte `silence`).
- **Résultat** : trois fichiers dans le dossier des sorties (celui de `sorties.csv`), pour toute la période :
  - un CSV, avec les mêmes colonnes que l'airplay CSV ;
  - une playlist `.pls` ;
  - une page HTML, avec la liste des alertes et incidents simulés puis le tableau des passages.

  L'artiste et le titre y sont masqués comme sur la page publique (voir [Sorties de la diffusion](#sorties-de-la-diffusion)), et l'emplacement de chaque fichier, donné partout, permet de vérifier ce qui sera joué. Un fichier du même nom est remplacé.
- **Messages** : les alertes et incidents simulés s'affichent aussi au fil de l'eau sur la sortie d'erreur, datés et préfixés de `simulation :`. Le bilan, avec le nombre de passages, d'alertes et d'incidents et les chemins des fichiers, s'affiche à la fin.
- **Codes de sortie** : 0 une fois la simulation finie, même avec des alertes ; 1 si la base est injoignable ou si les fichiers ne peuvent pas être écrits ; 2 pour une période ou un nom invalides, ou pour `--graine` ou `--nom` sans `--simulation`.

### État de la diffusion pour l'interface

`Machin lecture` publie son état sur une socket Unix, que l'interface lit pour afficher ce qui passe à l'antenne ([#20](https://github.com/dascritch/machincast/issues/20)) :

- **Emplacement** : `lecture.socket_etat` dans la configuration, ou par défaut `lecture.sock` dans le dossier `machincast` du répertoire d'exécution du compte (`$XDG_RUNTIME_DIR`, en général `/run/user/1000`). Seul le compte qui diffuse peut la lire. Elle disparaît à l'arrêt de la diffusion et au redémarrage du poste.
- **Contenu** : l'état de marche (diffusion, silence ou arrêt), le sonore en cours (emplacement, début, durée, fin prévue, progression), et le prochain sonore (emplacement, début et fin prévus, durée, s'il est sain). Pour un stream, la durée et la fin sont inconnues. Le format est décrit champ par champ dans la [spécification, § 5.4](spec.md#54-socket-détat).
- **Le prochain sonore annoncé est celui qui passera** : il est choisi dès le début du sonore en cours, même tiré au hasard dans une banque. Il ne change que si un événement coupe la diffusion, si son événement est fini, ou s'il est désactivé ou expiré entre-temps.
- **Sain** : un fichier présent, lisible, à l'état `actif`, dont la dernière lecture s'est terminée sans incident. Un stream n'est pas testé : son état sain est inconnu.
- Pour voir l'état à la main : `socat - UNIX-CONNECT:"${XDG_RUNTIME_DIR}/machincast/lecture.sock"` (paquet `socat`), une ligne JSON par changement ; `Ctrl-C` pour quitter.

Une socket impossible à créer (dossier sans droit d'écriture, par exemple) est signalée dans le log par l'alerte `socket d'état indisponible` : la diffusion continue sans elle.

La diffusion suit les règles ci-dessous.

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

### Quel sonore une banque fournit

Un élément « banque » d'un événement fait jouer **un seul** sonore de cette banque, choisi selon son mode ([#13](https://github.com/dascritch/machincast/issues/13)) :

- **Séquentiel** : le sonore qui suit, dans l'ordre de la banque, le dernier joué par elle ; après le dernier, la banque reprend au début.
- **Aléatoire contrôlé** : un sonore tiré au hasard parmi ceux que la banque n'a pas encore joués dans son cycle. Tant que tous ses sonores ne sont pas passés, aucun ne revient ; le cycle suivant ne commence jamais par le dernier joué. Un sonore ajouté à la banque entre dans le cycle en cours.
- **Banque par banque** : seuls comptent les passages fournis par la banque elle-même. Un sonore présent dans deux banques suit le cycle de chacune séparément, et un sonore joué directement dans un événement ne compte pour aucune banque.
- **Sonores jouables** : seul un sonore à l'état `actif` est choisi, dans sa période de diffusion quand elle est renseignée, et tant qu'il n'a pas atteint son maximum de lectures, compté sur toute la diffusion. Un sonore `aperçu`, `désactivé`, `expiré`, `erroné` ou `supprimé` est sauté.
- **Rien de jouable** : la banque ne fournit rien, et la diffusion passe à l'élément suivant de l'événement, comme pour une banque vide.

Le choix se déduit de l'historique de diffusion : il reprend là où il en était après un redémarrage.

**Banque « ne pas répéter »** ([#63](https://github.com/dascritch/machincast/issues/63)). Une banque marquée « ne pas répéter », par exemple une banque de jingles, ne passe jamais deux fois de suite :

- **Pas deux fois de suite** : si le dernier sonore diffusé a été fourni par cette banque, l'élément suivant qui la rappelle est sauté, et la diffusion passe à l'élément d'après, comme pour une banque vide. Une liste « jingle, jingle, titre » donne donc un jingle puis le titre.
- **D'un événement à l'autre** : la règle tient même quand la banque finit un événement et commence le suivant, quand le sonore précédent a été coupé net par le début d'un événement, et après un redémarrage, puisqu'elle se lit dans l'historique de diffusion.
- **Seuls comptent les passages fournis par la banque** : un sonore de la banque placé directement dans un événement ne compte pas.
- **Plus rien de jouable** : si, la banque sautée, il ne reste rien de jouable dans la liste d'une émission ou d'un spécial, l'événement se termine pour cette occurrence, avec l'alerte `événement terminé plus tôt` dans le log ; l'événement en dessous reprend. Un fil musical, lui, se tait, avec l'alerte `silence`, jusqu'à ce qu'un autre événement commence.
- **Dans le log** : chaque élément sauté est noté une fois, en info `élément sauté`, avec la banque et l'événement. La décision se prend dès le début du sonore précédent, quand la diffusion réserve le suivant : c'est l'heure notée dans le log.
- **Simulation** : la simulation applique la même règle, à partir de l'historique réel puis des passages simulés.

La case « ne pas répéter » d'une banque se coche dans [sa fiche](#fiche-dune-banque) ([#31](https://github.com/dascritch/machincast/issues/31)). La [fiche d'une séquence](#fiche-dune-séquence) prévient quand une banque marquée y occupe deux lignes qui se suivent : le deuxième appel sera toujours sauté ([#112](https://github.com/dascritch/machincast/issues/112)). L'écran d'un événement le fera aussi, y compris pour la dernière et la première ligne d'une liste qui boucle ([#32](https://github.com/dascritch/machincast/issues/32)).

### Expiration des sonores

`Machin lecture` passe un sonore `actif` à l'état `expiré` ([#18](https://github.com/dascritch/machincast/issues/18)) :

- **Maximum de lectures** : dès le passage qui l'atteint, compté sur toute la diffusion, quels que soient l'événement et la banque. Le sonore finit de jouer ce passage.
- **Période de diffusion** : dès que sa date de fin est atteinte. `Machin lecture` vérifie tous les sonores à son démarrage, puis chaque minute.
- **Dans le log** : une ligne `sonore expiré` par sonore, avec sa cause, par exemple « maximum de 2 lectures atteint » ou « période de diffusion terminée le 2026-10-14 20:00:00 ».
- **Rien d'autre ne change** : seul l'état du sonore est modifié, et seulement depuis `actif`. Un sonore `aperçu`, `désactivé`, `erroné` ou `supprimé` garde son état. Pour le remettre à l'antenne, [sa fiche](#fiche-dun-sonore) le repasse à `actif`, après avoir relevé son maximum ou repoussé sa période ; sinon, il expire de nouveau.

### Comment une liste de lecture se déroule

La liste d'un événement se joue ainsi ([#14](https://github.com/dascritch/machincast/issues/14)) :

- **Ordre** : les éléments passent dans l'ordre de la liste. Un même élément peut y figurer plusieurs fois, par exemple un jingle entre chaque titre. Un élément banque fait jouer un seul sonore de la banque.
- **Éléments sautés** : une banque dont aucun sonore n'est jouable, ou un sonore qui ne l'est pas, est sauté ; la liste passe à l'élément suivant.
- **Boucle** : arrivée au bout avant la fin de l'événement, la liste reprend au début.
- **Émission ou spécial sans fin** : la liste ne boucle pas. Une fois jouée, l'événement en dessous reprend, en général le fil musical. De même pour une émission dont plus rien n'est jouable.
- **Début d'un événement** : il coupe net le sonore en cours, quel qu'il soit. Une émission qui commence à 20:00 démarre à 20:00 pile.
- **Fin d'un événement** : si aucun autre ne commence, le dernier sonore est joué jusqu'au bout, puis le fil musical reprend. Si un autre événement commence juste après, il coupe ce dernier sonore.
- **Retour au fil musical** : le fil reprend à l'élément qui suit le dernier qu'il a joué, pas au début de sa liste.
- **Chaque occurrence** d'une émission récurrente reprend sa liste au début.
- **Rien à diffuser** : silence à l'antenne, et une alerte `silence` dans le log. Le silence cesse dès qu'un sonore redevient jouable ou qu'une émission commence.

### Séquences

Une **séquence** est une suite de sonores et de banques, jouée dans l'ordre, qu'on place comme un seul élément dans la liste d'un ou de plusieurs événements ([#99](https://github.com/dascritch/machincast/issues/99)). Par exemple, une séquence « passage publicitaire » joue :

1. le sonore « jingle début de publicité » ;
2. la banque « publicité » ;
3. la banque « publicité » ;
4. le sonore « jingle fin de publicité » ;
5. la banque « jingle station ».

À la diffusion :

- **Ordre** : les éléments passent dans l'ordre de la séquence, et chaque banque fait jouer un seul sonore. Une séquence ne contient que des sonores et des banques, jamais une autre séquence.
- **Éléments sautés** : un élément non jouable de la séquence est ignoré, et la séquence passe à l'élément suivant. Une séquence dont rien n'est jouable est sautée, comme une banque vide : l'événement passe à l'élément suivant de sa liste.
- **Banque « ne pas répéter »** : comme dans un événement, un appel à une banque marquée juste après elle est sauté. Dans l'exemple, si la banque « publicité » est marquée, sa deuxième ligne est sautée.
- **Comme un seul sonore** : à la fin de son événement, si aucun autre ne commence, la séquence est jouée jusqu'au bout. Un événement qui commence coupe net le sonore en cours de la séquence, et la séquence avec lui : ses éléments restants ne sont pas joués.
- **Ensuite** : après la séquence, jouée en entier ou coupée, la liste de l'événement reprend à l'élément qui suit la séquence.
- **Redémarrage** : la position dans la séquence se lit dans l'historique de diffusion. Après un redémarrage, la séquence reprend là où elle en était, si rien d'autre n'est passé entre-temps.
- **Stream** : un stream tombé dans une séquence est remplacé par son événement de secours, comme ailleurs (voir [Streams](#streams)).
- **Simulation** : la simulation applique les mêmes règles.

Les séquences se créent et se modifient dans leur fiche ([Fiche d'une séquence](#fiche-dune-séquence)). Leur place dans la liste d'un événement se choisira dans l'écran de l'événement ([#32](https://github.com/dascritch/machincast/issues/32)). En attendant, elle s'écrit en base, par exemple avec `psql` sous le compte propriétaire de la base, ici en troisième ligne de l'événement « Continue » :

```bash
psql --dbname=machincast <<'SQL'
INSERT INTO evenements_elements (evenement_id, position, sequence_id)
	SELECT e.id, 3, s.id FROM evenements e, sequences s
	WHERE e.nom_interne = 'Continue' AND s.nom_interne = 'Passage publicitaire';
SQL
```

### Sortie audio

La sortie audio de l'antenne se règle dans la configuration (`audio.sortie` : `pipewire`, `pulseaudio`, `alsa`, ou `factice` pour un essai sans son), et `install.sh` vérifie qu'elle peut être créée. Les sonores s'y enchaînent ainsi ([#15](https://github.com/dascritch/machincast/issues/15)) :

- **Crossfade de début** d'un sonore : il monte progressivement, de silencieux à plein volume, pendant ce temps.
- **Crossfade de fin** d'un sonore : le sonore suivant démarre autant avant la fin, et celui-ci s'éteint progressivement pendant ce temps. Les deux se superposent.
- **Les deux crossfades sont nécessaires** : deux sonores ne se superposent que si le premier a un crossfade de fin **et** le second un crossfade de début. Si l'un des deux est à 0, le premier joue jusqu'au bout à plein volume, puis le second démarre aussitôt à plein volume, sans fondu.
- **Coupure nette** : au début d'un événement, le sonore en cours s'arrête aussitôt, sans fondu.
- **Avant de jouer un fichier**, sa date de modification et sa taille sont comparées à celles de l'indexation. Un écart est noté dans le log en alerte `fichier modifié`, et le fichier est quand même joué ; la prochaine indexation mettra la base à jour. Un fichier disparu n'est pas joué : l'incident `fichier introuvable` est noté dans le log, et la diffusion passe aussitôt au sonore suivant. Le sonore n'est plus proposé pendant une heure, pour ne pas noter le même incident à chaque tour de liste ; la prochaine indexation le passera à l'état `supprimé`.
- **Superposition** : pendant un crossfade, deux sonores jouent en même temps. PipeWire et PulseAudio les mélangent toujours. En `alsa`, il faut un périphérique qui mélange, comme `default` ; un périphérique matériel direct (`hw:…`) ne joue qu'un son à la fois.

### Streams

Un sonore de type stream relaie un flux audio HTTP ou HTTPS, un direct extérieur par exemple, à son adresse directe ou à celle d'un marque-page ([#16](https://github.com/dascritch/machincast/issues/16)) :

- **Métadonnées** : l'airplay note l'artiste et le titre du sonore en base, jamais ceux que le flux annonce (tags ICY). L'emplacement noté est l'adresse du flux.
- **Début d'un événement** de priorité égale ou supérieure : il coupe net le stream, comme un fichier.
- **Fin de son événement** : le stream s'éteint pendant son crossfade de fin. Le sonore suivant démarre en même temps s'il a un crossfade de début, sinon à la fin du fondu ; sans crossfade de fin, le stream s'arrête net.
- **Flux tombé** : un flux qui ne répond pas, ou qui s'arrête avant la fin de son événement, même proprement, est tombé. Son passage se termine en incident, et le log note l'incident `flux tombé`, avec l'adresse du flux et l'erreur. L'**événement de secours** du stream joue sa liste en boucle à sa place. Un stream sans événement de secours laisse jouer l'événement en dessous, le plus souvent le fil musical.
- **Reconnexion** : tant que son événement est à l'antenne, `Machin lecture` retente la connexion toutes les 5 secondes, sans rien faire entendre. Dès que le flux revient, le stream reprend l'antenne : il monte pendant son crossfade de début, et le sonore de remplacement s'éteint pendant ce temps ; sans crossfade de début, le remplacement s'arrête net. La reprise est notée dans le log par l'incident `reprise du flux`, avec l'adresse du flux et la durée de la panne : l'écran des incidents montrera ainsi chaque panne et sa fin.
- **Fin de l'événement pendant la panne** : la reconnexion est abandonnée (`reconnexion abandonnée` dans le log), et la diffusion continue normalement.

Un **événement de secours** est un événement de priorité `secours` : il n'a ni début, ni fin, ni jours de récurrence, et ne passe jamais à l'antenne par la grille, seulement à la place d'un stream tombé. Chaque stream désigne le sien, ou aucun, dans [sa fiche](#fiche-dun-sonore). Tant que l'interface ne permet pas de créer un stream ([#30](https://github.com/dascritch/machincast/issues/30)) ni un événement ([#32](https://github.com/dascritch/machincast/issues/32)), ceux-ci s'enregistrent directement en base.

### Sorties de la diffusion

`Machin lecture` publie ce qu'il diffuse sur plusieurs sorties ([#19](https://github.com/dascritch/machincast/issues/19)), aux chemins de la section `[sorties]` de la configuration, compris depuis le répertoire du fichier de configuration (par défaut, le dossier `sorties` du répertoire de MachinCast, créé au besoin) :

| Sortie | Pour qui | Contenu |
| --- | --- | --- |
| Sortie standard | équipe | Une ligne `à l'antenne : artiste – titre (événement)` à chaque passage. |
| Sortie d'erreur | équipe | Les alertes et incidents du log, et les erreurs du programme. |
| CSV (`sorties.csv`) | équipe | Un fichier par jour, nommé avec sa date : `airplay.csv` donne `airplay-2026-10-15.csv`. Une ligne par passage terminé : début, fin, durée, artiste, titre, emplacement, événement, séquence, banque, sans incident (`oui` ou `non`). Séparateur `;`, s'ouvre directement dans LibreOffice ou Excel. Jamais réécrit. |
| Playlist `.pls` (`sorties.pls`) | équipe | Les 100 derniers fichiers joués, streams compris, du plus ancien au plus récent : pour réécouter ce qui est passé. |
| Page HTML (`sorties.html`) | public | Le sonore à l'antenne et les 20 précédents, avec l'heure. Page statique, à publier sur le site de la radio ; elle se recharge toute seule toutes les 30 secondes et ne montre jamais l'emplacement d'un fichier. |

**Masquage de l'artiste et du titre.** Sur la page publique seulement, l'artiste et le titre d'un passage peuvent être masqués. Le choix se fait à cinq niveaux : l'événement, puis la séquence qui a fait jouer le sonore ([#99](https://github.com/dascritch/machincast/issues/99)), puis la banque qui l'a fourni, puis le sonore, puis `metadonnees.masquer` dans la configuration. C'est le premier niveau renseigné qui décide : un événement qui dit « afficher » l'emporte sur un sonore qui dit « masquer ». Masqués, l'artiste et le titre laissent la place au premier nom public renseigné, dans le même ordre : celui de l'événement, puis de la séquence, puis de la banque ; s'il n'y en a aucun, à `metadonnees.texte_public`. Les autres sorties disent toujours tout.

Une sortie impossible à écrire (dossier sans droit d'écriture, disque plein) est signalée une fois dans le log par l'alerte `sortie inaccessible`, avec le chemin et l'erreur. La diffusion continue.

### Historique de diffusion et log

Chaque passage à l'antenne est noté dans l'historique de diffusion, l'**airplay** ([#17](https://github.com/dascritch/machincast/issues/17)) :

- deux lignes par passage, une au début et une à la fin, reliées entre elles ;
- l'emplacement, l'artiste et le titre du sonore, **tels qu'ils étaient au moment du passage**, même s'ils sont modifiés ensuite ou si le sonore est supprimé ;
- la banque qui a fourni le sonore, l'événement et l'élément de sa liste ;
- sur la ligne de fin, la durée effectivement diffusée, et si la lecture s'est déroulée sans incident. Un sonore coupé net par le début d'un événement n'est pas un incident.

Le **log** note les opérations du binaire lecture, avec leur heure, leur niveau et ce qu'elles concernent (sonore, banque, événement) :

| Nature | Niveau | Quand |
| --- | --- | --- |
| `démarrage` | info | `Machin lecture` démarre la diffusion ; le message donne sa version. |
| `arrêt` | info | `Machin lecture` arrête la diffusion, sur `Ctrl-C` ou `SIGTERM`. |
| `coupure nette` | info | Un événement commence et coupe le sonore en cours. |
| `silence` | alerte | Rien à diffuser. |
| `fichier modifié` | alerte | Le fichier a changé depuis l'indexation ; il est quand même joué. |
| `fichier introuvable` | incident | Le fichier a disparu ; il n'est pas joué. |
| `lecture interrompue` | incident | La lecture d'un fichier s'est arrêtée sur une erreur, dont le message est noté. |
| `flux tombé` | incident | Le flux d'un stream ne répond pas, ou s'est arrêté avant la fin de son événement ; le message donne l'adresse et l'erreur. |
| `reprise du flux` | incident | Le flux d'un stream tombé est revenu, et le stream reprend l'antenne ; le message donne l'adresse et la durée de la panne. |
| `sonore expiré` | info | Un sonore a atteint son maximum de lectures ou la fin de sa période de diffusion ; le message donne la cause. |
| `socket d'état indisponible` | alerte | La socket d'état ne peut pas être créée ; la diffusion continue sans elle. |
| `sortie inaccessible` | alerte | Une sortie (CSV, .pls ou page HTML) ne peut pas être écrite ; le message donne le chemin et l'erreur. |
| `élément sauté` | info | Un élément rappelle la banque « ne pas répéter » qui vient de passer : il est sauté. Le message donne la banque et la position de l'élément. |
| `événement terminé plus tôt` | alerte | Une émission ou un spécial n'a plus rien de jouable une fois la banque « ne pas répéter » sautée : il se termine, et l'événement en dessous reprend. |
| `reconnexion abandonnée` | info | L'événement d'un stream tombé n'est plus à l'antenne : plus de tentative de reconnexion. |

L'airplay et le log ne sont jamais modifiés ni effacés par le binaire lecture : il ne peut qu'y ajouter des lignes.

## Interface graphique : Machin interface

`Machin interface` se connecte à la base de production, avec les droits de l'interface, puis ouvre sa fenêtre. Elle a un onglet par écran ([#26](https://github.com/dascritch/machincast/issues/26)) : **Accueil**, ouvert au lancement, puis **Événements**, **Séquences**, **Banques** et **Sonores**.

**Sans base de données**, l'interface n'est pas utilisable : `Machin interface` ouvre alors une fenêtre d'erreur, « MachinCast : base de données injoignable ». Elle explique pourquoi, et invite à lire le document `INSTALL.md` du répertoire de MachinCast, section [En cas de problème](../INSTALL.md#en-cas-de-problème). Son bouton « Ouvrir INSTALL.md » ouvre ce document, et ses détails donnent l'erreur de PostgreSQL. À sa fermeture, `Machin interface` s'arrête avec le code 1. Le message `base de données injoignable` (ou `erreur de base de données`, pour un compte sans droit) s'affiche aussi sur la sortie d'erreur. Sans affichage graphique, par exemple dans une session SSH, seul ce message s'affiche.

### Accueil

L'onglet Accueil est l'**écran par défaut** ([#23](https://github.com/dascritch/machincast/issues/23)), qui montre en un coup d'œil ce qui passe et ce qui va passer :

- **En haut** : la date et l'heure du poste, à la seconde, et l'état du binaire lecture : `En diffusion`, `En silence` (rien à diffuser) ou `À l'arrêt`.
- **Sonore en cours et prochain sonore**, côte à côte, chacun sur la moitié de la largeur de la fenêtre ; un titre trop long passe à la ligne.
- **Sonore en cours** : l'artiste et le titre, l'événement qui le joue, l'emplacement (chemin du fichier, ou adresse du stream), l'heure de début, la durée, l'heure de fin estimée et une barre de progression.
- **Prochain sonore** : l'artiste et le titre, l'événement, l'emplacement, les heures de début et de fin estimées, la durée et l'indicateur « sain » (`oui` si le fichier est présent, actif, lisible et que sa dernière lecture s'est passée sans incident, `non` sinon).
- **Emplacement** : un long chemin ne déborde pas, sa fin (le nom du fichier) reste visible ; il se fait défiler, se sélectionne et se copie, et son infobulle le donne en entier.
- **Stream** : sa durée et sa fin sont `inconnue`, et la barre de progression affiche `durée inconnue`. Un stream n'est pas testé à l'avance : son indicateur « sain » est `non testé`. Après un stream, le début du prochain sonore est `inconnu`.
- **Airplay des 12 dernières heures** : une table, du passage le plus récent au plus ancien, avec le début, la fin (`en cours` pour le sonore à l'antenne), la durée diffusée, l'artiste, le titre, l'événement, la séquence, la banque et `oui` ou `non` pour « sans incident ». L'interface est réservée à l'équipe : l'artiste et le titre y sont toujours affichés, même masqués sur la page publique.

D'où viennent ces informations :

- **Sonore en cours, prochain sonore, état** : de la socket d'état de `Machin lecture`, au chemin `lecture.socket_etat` de la configuration (voir [État de la diffusion pour l'interface](#état-de-la-diffusion-pour-linterface)). L'interface doit donc tourner sous le même compte que la diffusion, et avec la même configuration. Sans socket, ou quand `Machin lecture` s'arrête, l'écran affiche `À l'arrêt`, et se reconnecte tout seul, chaque seconde, dès que la diffusion reprend.
- **Airplay** : de la base, à l'ouverture, puis chaque fois que la socket annonce un nouveau sonore. L'interface n'interroge jamais la base en boucle. Si la base devient injoignable, la table reste telle qu'elle était, et l'erreur `airplay illisible` s'affiche sur la sortie d'erreur.

Le VU-mètre de la sortie viendra avec [#24](https://github.com/dascritch/machincast/issues/24), et le pilotage du service avec [#25](https://github.com/dascritch/machincast/issues/25).

### Listes

Les onglets Événements, Séquences, Banques et Sonores donnent chacun la liste de tous les éléments de ce type ([#26](https://github.com/dascritch/machincast/issues/26)) :

| Onglet | Colonnes | Ordre |
| --- | --- | --- |
| Événements | nom, nom public, priorité, début, fin, jours de récurrence | du plus prioritaire (spécial) au moins prioritaire (secours), puis par nom |
| Séquences | nom, nom public | par nom |
| Banques | nom, nom public, mode (séquentielle ou aléatoire), « ne pas répéter », premier répertoire (dans l'ordre alphabétique), vide pour une banque sans répertoire | par nom |
| Sonores | artiste, titre, type (fichier ou stream), état, durée, emplacement (chemin du fichier ou adresse du stream) | par artiste, les sonores sans artiste à la fin, puis par titre |

- **Filtre** : le champ « Filtrer… » garde les lignes dont une colonne contient le texte tapé, sans tenir compte des majuscules ni des accents : `cafe` trouve « Café à minuit », `stream` tous les streams, `/srv/musique` tous les fichiers de ce répertoire. Le compte, à côté, dit combien de lignes restent, par exemple `2 sonores sur 340`. La croix du champ efface le filtre.
- **Tri** : un clic sur le titre d'une colonne trie la liste selon cette colonne ; un second clic inverse l'ordre.
- **Mise à jour** : une liste se relit dans la base chaque fois que son onglet s'ouvre, en gardant son filtre. Elle ne se relit jamais d'elle-même pendant qu'on la regarde.
- **Détails** : un double-clic sur une ligne, ou la touche Entrée, ouvre l'écran de détails de l'élément. Pour une séquence, une banque ou un sonore, c'est sa fiche ([séquence](#fiche-dune-séquence), [banque](#fiche-dune-banque), [sonore](#fiche-dun-sonore)). Celui d'un événement est encore à venir ([#32](https://github.com/dascritch/machincast/issues/32)) : en attendant, la barre d'état, en bas de la fenêtre, l'annonce.
- **Créer** : les boutons **Nouvelle séquence** et **Nouvelle banque**, à côté du filtre de leur liste, ouvrent une fiche vide. Les événements et les sonores n'ont pas encore ce bouton.

### Fiche d'une banque

La fiche d'une banque s'ouvre dans un **nouvel onglet**, nommé « Banque : » suivi de son nom, depuis la liste des banques ([#31](https://github.com/dascritch/machincast/issues/31)) ; une fiche vide s'appelle « Nouvelle banque ». Une banque déjà ouverte revient au premier plan, sans second onglet. L'onglet d'une fiche se ferme par sa croix, contrairement à ceux de l'accueil et des listes.

| Champ | Rôle |
| --- | --- |
| Nom interne | Obligatoire, et propre à la banque : c'est son nom dans les listes, le log et l'airplay. |
| Nom public | Facultatif. Affiché sur la page publique à la place de l'artiste et du titre masqués, si l'événement et la séquence n'en ont pas ([Sorties de la diffusion](#sorties-de-la-diffusion)). |
| Mode | `Séquentielle` : les sonores passent dans l'ordre de la liste. `Aléatoire` : ils sont tirés au hasard ([Quel sonore une banque fournit](#quel-sonore-une-banque-fournit)). |
| Artiste et titre | `Masqués` ou `Affichés` sur la page publique, sauf si l'événement ou la séquence en décide. `Hérité du sonore` laisse décider le sonore, puis la configuration. |
| Ne pas répéter | La banque ne passe jamais deux fois de suite ([Quel sonore une banque fournit](#quel-sonore-une-banque-fournit)). |

**Enregistrer et annuler** : les modifications restent dans la fiche jusqu'au clic sur **Enregistrer**, qui les écrit toutes à la fois ; **Annuler** remet la fiche telle qu'elle est en base. Les deux boutons ne servent que quand la fiche est modifiée.

- Les noms sont enregistrés sans les espaces qui les entourent. Un nom interne vide est refusé (« Le nom interne est obligatoire. »), comme celui d'une autre banque (« Une autre banque s'appelle déjà « Tubes ». ») : rien n'est enregistré, et la fiche garde ses modifications.
- Si la base est injoignable, la fiche affiche « Enregistrement impossible : » et l'erreur de PostgreSQL, et garde ses modifications ; l'erreur s'affiche aussi sur la sortie d'erreur.
- **Fermer une fiche modifiée**, par son onglet ou en fermant la fenêtre, demande quoi faire des modifications : **Enregistrer** (Entrée), **Abandonner**, ou **Annuler** (Échap), qui garde la fiche ouverte. Si l'enregistrement échoue, la fiche reste ouverte.

**Répertoires indexés** : les fichiers sonores de ces répertoires, et de leurs sous-répertoires, sont rattachés à la banque par `Machin indexation` ([Alimenter une banque](#alimenter-une-banque)). **Ajouter un répertoire…** ouvre le sélecteur de répertoires du poste ; on peut aussi y **déposer des dossiers** glissés depuis le navigateur de fichiers (un fichier déposé là est ignoré, et la fiche le dit). Un répertoire déjà présent n'est pas ajouté deux fois. **Retirer le répertoire** retire celui qui est choisi dans la liste. Les répertoires sont rangés dans l'ordre de leurs caractères. Rien n'est indexé à l'enregistrement : les fichiers d'un nouveau répertoire arrivent dans la banque à la prochaine indexation.

**Sonores** : la liste montre chaque sonore (artiste et titre), sa durée (`inconnue` pour un stream, vide pour un fichier pas encore décodé) et son emplacement.

- **Ordre** : en mode séquentiel, un sonore se déplace par glisser-déposer, ou en le choisissant puis avec **Monter** et **Descendre**. En mode aléatoire, l'ordre ne compte pas, et ne se change pas.
- **Ajouter des sonores…** ouvre la liste des sonores déjà en base, avec son filtre. Plusieurs sonores se choisissent avec Ctrl ou Maj, puis **Ajouter** ; un double-clic en choisit un seul. Ils s'ajoutent en fin de liste, même s'ils sont hors des répertoires de la banque ; un sonore déjà dans la banque n'est pas ajouté deux fois. Un nouveau fichier se dépose sur la liste (ci-dessous), ou dans un répertoire de la banque avant de lancer `Machin indexation` ; l'ajout par un sélecteur de fichiers viendra avec [#30](https://github.com/dascritch/machincast/issues/30).
- **Déposer des fichiers** glissés depuis le navigateur de fichiers les ajoute en fin de liste, dans les deux modes, une fois chacun. Un fichier déjà en base reprend son sonore. Un fichier pas encore en base est montré par son nom, et devient à l'enregistrement un sonore à l'état `aperçu`, que la prochaine indexation décodera ; « Annuler » ou « Abandonner » ne l'enregistrent pas. Les dossiers et les fichiers qui ne sont pas sonores (voir les formats dans [Alimenter une banque](#alimenter-une-banque)) sont ignorés, et la fiche le dit.
- **Un dépôt est toujours une copie** : le fichier reste où il est, et n'est pas touché. Même avec Maj enfoncée, qui demande d'habitude un déplacement au navigateur de fichiers, la fiche ne l'accepte que comme une copie ; un glisser qui ne propose que le déplacement est refusé.
- **Retirer le sonore** retire le sonore choisi de la banque, sans rien demander s'il est hors de ses répertoires. Si son fichier est dans l'un des répertoires de la fiche, ou de leurs sous-répertoires, un avertissement rappelle que **la prochaine indexation l'y remettra** : **Retirer quand même**, **Ouvrir le dossier** du fichier dans le navigateur de fichiers du poste, pour l'en déplacer (le sonore reste dans la banque), ou **Annuler**. MachinCast ne déplace ni ne supprime jamais le fichier ([Les fichiers sonores ne sont jamais modifiés](#les-fichiers-sonores-ne-sont-jamais-modifiés)) : c'est à faire hors de l'outil, parfois depuis un autre poste quand le compte n'a pas le droit d'écrire dans le répertoire. Le sonore reste en base, dans ses autres banques et événements.
- **Indexation pendant la modification** : les sonores que `Machin indexation` rattache à la banque pendant que la fiche est ouverte sont gardés à l'enregistrement, en fin de liste. Un sonore effacé de la base entre-temps est oublié.

### Fiche d'un sonore

La fiche d'un sonore s'ouvre depuis la liste des sonores, dans un nouvel onglet nommé « Sonore : » suivi de son titre, ou du nom de son fichier, ou de l'adresse d'un stream ([#28](https://github.com/dascritch/machincast/issues/28)). Elle se comporte comme [celle d'une banque](#fiche-dune-banque) : **Enregistrer** et **Annuler**, une seule fiche par sonore, et la question à la fermeture d'une fiche modifiée.

**Sonore** : le type, l'emplacement du fichier et sa durée, qui ne se modifient pas, et l'**état**. La fiche pose `actif` ou `désactivé` ; un sonore `expiré`, `erroné` ou `supprimé` peut revenir à `actif` (voir [États d'un sonore](#états-dun-sonore)). Un sonore en `aperçu` attend sa première indexation, et son état ne se choisit pas.

**Métadonnées** : artiste, titre, année, album, artiste de l'album, genre, compositeur, label et piste. Les autres métadonnées, ajoutées hors de MachinCast, sont montrées sans se modifier. Un champ vide n'a pas de valeur ; les textes sont enregistrés sans les espaces qui les entourent.

**Diffusion** :

- **Crossfade de début et de fin**, en secondes (voir [Sortie audio](#sortie-audio)).
- **Maximum de lectures** : `illimité` à 0 (voir [Expiration des sonores](#expiration-des-sonores)).
- **Artiste et titre** : `Masqués` ou `Affichés` sur la page publique, sauf si l'événement, la séquence ou la banque en décide ; `Selon la configuration` laisse décider la configuration (voir [Sorties de la diffusion](#sorties-de-la-diffusion)).
- **Diffusion à partir du**, **Diffusion jusqu'au** : la période de diffusion, chacune à cocher. Une case cochée part de l'heure du moment, à la minute. La fin doit suivre le début, sinon la fiche le dit et n'enregistre rien.

**Saisi à la main** : chaque champ modifié à l'enregistrement est noté comme saisi à la main, et la fiche en donne la liste. L'**indexeur ne le modifie plus jamais**, même vidé : un album effacé ne revient pas des tags du fichier. L'état n'est jamais noté ainsi : l'indexeur peut encore passer un sonore à `erroné`, puis de nouveau à `actif`. Seuls les champs modifiés sont écrits : ce que l'indexation ou la diffusion change pendant que la fiche est ouverte (un titre lu dans les tags, un sonore qui expire) est gardé.

**Stream** (voir [Streams](#streams)) :

- **Adresse directe** ou **Marque-page**, parmi les marques-pages en base ; leur gestion viendra avec [#34](https://github.com/dascritch/machincast/issues/34). Un stream sans adresse n'est pas enregistré.
- **Événement de secours** : parmi les événements de priorité `secours`, ou `Aucun : le fil musical`.
- **Tester le flux** : la fiche se connecte à l'adresse saisie, même pas encore enregistrée, et dit `Le flux répond : du son arrive.` dès qu'une seconde de son est décodée. Sinon, elle dit `Le flux ne répond pas :` suivi de l'erreur (adresse invalide, serveur injoignable, réponse en erreur), ou `le son n'arrive pas en 10 s.`. Rien n'est joué. La connexion se ferme à la fin du test, et à la fermeture de la fiche ou de la fenêtre.

**Derniers passages** : les 50 derniers passages du sonore, du plus récent au plus ancien, avec le début, la fin (`en cours` pour le passage à l'antenne), la durée diffusée, l'événement, la séquence, la banque, « sans incident », et les alertes et incidents que le log a notés pour ce sonore pendant le passage. L'infobulle de cette dernière colonne les détaille, avec leur heure et leur message.

La pré-écoute viendra avec [#29](https://github.com/dascritch/machincast/issues/29), l'ajout d'un sonore avec [#30](https://github.com/dascritch/machincast/issues/30), sa suppression avec [#33](https://github.com/dascritch/machincast/issues/33).

### Fiche d'une séquence

La fiche d'une [séquence](#séquences) s'ouvre depuis la liste des séquences, dans un nouvel onglet nommé « Séquence : » suivi de son nom ([#112](https://github.com/dascritch/machincast/issues/112)) ; **Nouvelle séquence** ouvre une fiche vide. Elle se comporte comme [celle d'une banque](#fiche-dune-banque) : **Enregistrer** et **Annuler**, une seule fiche par séquence, et la question à la fermeture d'une fiche modifiée.

| Champ | Rôle |
| --- | --- |
| Nom interne | Obligatoire, et propre à la séquence : c'est son nom dans les listes, le log et l'airplay. |
| Nom public | Facultatif. Affiché sur la page publique à la place de l'artiste et du titre masqués, si l'événement n'en a pas ([Sorties de la diffusion](#sorties-de-la-diffusion)). |
| Artiste et titre | `Masqués` ou `Affichés` sur la page publique, pour les sonores que la séquence fait jouer, sauf si l'événement en décide. `Selon la banque ou le sonore` laisse décider la banque, puis le sonore, puis la configuration. |

Les noms sont enregistrés sans les espaces qui les entourent. Rien n'est enregistré, et la fiche le dit, pour un nom interne vide (« Le nom interne est obligatoire. »), celui d'une autre séquence (« Une autre séquence s'appelle déjà « Ouverture ». »), ou une séquence sans élément (« Une séquence contient au moins un sonore ou une banque. »).

**Éléments** : la liste ordonnée des sonores et des banques que la séquence joue. Chaque ligne donne le genre de l'élément, son nom (artiste et titre d'un sonore, ou le nom de son fichier tant qu'il n'est pas décodé) et un détail : l'emplacement d'un sonore, le mode d'une banque et « ne pas répéter » si elle l'est.

- **Ordre** : un élément se déplace par glisser-déposer, ou en le choisissant puis avec **Monter** et **Descendre**.
- **Ajouter des sonores…** et **Ajouter des banques…** ouvrent la liste de ceux déjà en base, avec son filtre ; plusieurs se choisissent avec Ctrl ou Maj, puis **Ajouter**. Ils s'ajoutent en fin de liste. **Un même sonore ou une même banque peut revenir** plusieurs fois. Une séquence ne contient jamais une autre séquence.
- **Déposer des fichiers** glissés depuis le navigateur de fichiers les ajoute en fin de liste, une fois par fichier déposé, comme sur [la fiche d'une banque](#fiche-dune-banque) : un fichier déjà en base reprend son sonore, un autre devient à l'enregistrement un sonore à l'état `aperçu`, les dossiers et les fichiers qui ne sont pas sonores sont ignorés, et la fiche le dit. Un dépôt est toujours une copie : le fichier n'est pas touché.
- **Retirer l'élément** retire la ligne choisie, sans rien demander : le sonore ou la banque reste en base.
- **Banque « ne pas répéter »** : quand une banque marquée « ne pas répéter » est appelée deux fois de suite, la fiche signale sous la liste la ligne du deuxième appel, qui sera toujours sauté à la diffusion (« Ligne 3 : la banque « Publicité » vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. »). Ce n'est qu'un avertissement : la séquence s'enregistre quand même.
- **Pendant la modification** : un sonore ou une banque effacé de la base entre-temps est oublié à l'enregistrement. Une ligne restée dans la liste reste celle que désigne l'historique de diffusion : après un redémarrage, la séquence reprend après elle, à sa nouvelle place ([Séquences](#séquences)).

**Ouvrir un élément** : un double-clic, ou Entrée, sur un sonore ou une banque ouvre sa fiche dans un autre onglet. Un fichier déposé n'a pas de fiche avant l'enregistrement.

**Événements** : la liste des événements où la séquence figure, par nom ; elle ne se modifie pas ici. Un double-clic demande l'écran de l'événement, encore à venir ([#32](https://github.com/dascritch/machincast/issues/32)).

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
| 1 | Base de données injoignable ou perdue (pour `Machin interface`, au lancement), décodeur GStreamer manquant, sortie audio indisponible, autre `Machin lecture` déjà en diffusion, ou fonction pas encore écrite. |
| 2 | Configuration invalide, ou appel incorrect (option inconnue, `--config` sans fichier). |
| 127 | Programme ou `journalctl` introuvable, signalé par `Machin`. |

Les messages d'erreur courants et leur solution sont dans le tableau [En cas de problème](../INSTALL.md#en-cas-de-problème) d'`INSTALL.md`.

## Droits de chaque programme dans la base

Chaque programme agit dans la base avec ses propres droits : le compte qui le lance n'a accès à rien par lui-même, et le programme endosse son rôle PostgreSQL dès la connexion. Un programme ne peut donc pas faire plus que ce qui suit, même lancé par un compte qui a les trois rôles.

| Programme | Rôle PostgreSQL | Ce qu'il peut faire |
| --- | --- | --- |
| `Machin lecture` | `machincast_lecture` | Lire la programmation, séquences comprises ; passer un sonore à `expiré` ; ajouter des lignes à l'airplay et au log, sans jamais les modifier ni les supprimer. |
| `Machin indexation` | `machincast_indexation` | Lire les banques et leurs répertoires ; ajouter et mettre à jour des sonores, et les ranger dans les banques. Il ne supprime rien et n'écrit pas dans le log. |
| `Machin interface` | `machincast_interface` | Tout modifier dans les sonores, les banques, les séquences et les événements ; lire l'airplay et le log, sans les modifier. |

Le détail, table par table, est dans la [spécification, § 3.2](spec.md#32-rôles-et-droits). Ajouter un autre compte est décrit dans [INSTALL.md](../INSTALL.md#ajouter-un-autre-compte).

## Ce qui n'existe pas encore

| Manque | Ticket |
| --- | --- |
| Document d'audit des anomalies de l'indexation, en CSV et HTML | [#11](https://github.com/dascritch/machincast/issues/11) |
| Prolonger un stream dont le direct déborde | [#47](https://github.com/dascritch/machincast/issues/47) |
| Service systemd de diffusion | [#22](https://github.com/dascritch/machincast/issues/22) |
| Autres écrans de l'interface : VU-mètre, pilotage du service, recherche globale, détails, ajout et suppression, incidents, calendrier, simulation, indexation | [#24](https://github.com/dascritch/machincast/issues/24) à [#39](https://github.com/dascritch/machincast/issues/39) |
| Raccourci de bureau et icône de l'interface | [#62](https://github.com/dascritch/machincast/issues/62) |
