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
| `Machin interface` | Interface graphique de supervision et de programmation. Pour l'instant, son [écran par défaut](#interface-graphique--machin-interface), les [listes](#listes), les fiches d'un [événement](#fiche-dun-événement), d'une [séquence](#fiche-dune-séquence), d'une [banque](#fiche-dune-banque) et d'un [sonore](#fiche-dun-sonore). |
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
- un sonore supprimé de la base, depuis [sa fiche](#supprimer-un-élément), garde son fichier : s'il est encore dans le répertoire d'une banque, la prochaine indexation l'enregistre de nouveau, comme un nouveau sonore à l'état `aperçu`, puis `actif` une fois vérifié.

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

Il se lance depuis un terminal, ou depuis le menu **Maintenance** de l'interface ([Lancer l'indexation depuis l'interface](#lancer-lindexation-depuis-linterface)), qui fait exactement le même travail.

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
| `Machin indexation` | **Indexation rapide**, par défaut. Sont décodés, et leurs tags lus, les sonores à l'état `aperçu`, c'est-à-dire nouvellement trouvés, et ceux dont le fichier a changé depuis sa dernière vérification : sa date de modification ou sa taille diffère ([#10](https://github.com/dascritch/machincast/issues/10)). Une émission pré-enregistrée remplacée sous le même nom, par exemple synchronisée depuis un autre poste, est ainsi revérifiée : nouvelle durée, nouveaux tags, sauf les champs saisis à la main. Pour les autres, seule la présence du fichier est contrôlée : un fichier disparu est quand même repéré, et son sonore passe `supprimé`. Un fichier déplacé est enregistré comme un nouveau sonore, à son nouvel emplacement, s'il est dans le répertoire d'une banque. |
| `Machin indexation --audit-complet` | **Audit complet** : tous les sonores de type fichier sont décodés. C'est lui qui repère un fichier abîmé après son indexation sans que sa date ni sa taille aient changé. C'est aussi lui, et lui seul, qui mesure les blancs au début et à la fin de chaque fichier ([Détection de blanc](#détection-de-blanc)). À lancer après la première indexation, puis de temps en temps. |
| Audit demandé depuis l'interface | **Quelques sonores en entier**, sans auditer toute la discothèque ([#114](https://github.com/dascritch/machincast/issues/114)) : le clic droit dans les listes Sonores ou Banques marque les sonores choisis, et la **prochaine indexation, même rapide**, les décode en entier et mesure leurs blancs, puis efface la marque ([Agir sur plusieurs sonores ou banques](#agir-sur-plusieurs-sonores-ou-banques)). |
| `Machin indexation --audit-complet --sonore N` | **Un seul sonore**, le numéro N, décodé en entier ([#181](https://github.com/dascritch/machincast/issues/181)) : ni parcours des répertoires, ni document d'audit ; ses anomalies s'affichent sur la sortie d'erreur. Il peut tourner pendant une autre indexation. Un sonore inconnu, ou un stream, est refusé avec le code 1. C'est ainsi que `Machin lecture` fait vérifier, au dernier moment, le sonore qu'il va jouer ([Diffusion : Machin lecture](#diffusion--machin-lecture)). Sans `--audit-complet`, le sonore n'est décodé que s'il est en aperçu ou si son fichier a changé. |
| `Machin indexation --fenetre` | La même indexation, rapide ou complète (avec `--audit-complet`), qui montre son journal dans une fenêtre au lieu du terminal : c'est ainsi que l'interface la lance ([Lancer l'indexation depuis l'interface](#lancer-lindexation-depuis-linterface)). Il faut un affichage graphique. |

**Une seule indexation à la fois** sur une base (sauf `--sonore`, qui ne vérifie qu'un sonore), qu'elle soit lancée d'un terminal, de l'interface ou d'un autre poste : une deuxième s'arrête aussitôt, sans rien toucher, avec le message `indexation refusée : une autre indexation est en cours sur cette base` et le code 1. Elle pourra être relancée une fois la première finie.

Le décodage est fait sans jouer le son, bien plus vite que le temps réel : une dizaine de minutes de son en moins d'une seconde. Un audit complet d'une grande discothèque peut tout de même prendre du temps.

Les streams ne sont jamais vérifiés.

### Verdicts de la vérification d'un fichier

Avant de le décoder, l'indexeur lit le **type réel** du fichier dans ses premiers octets, avec libmagic, sans se fier à son extension ([#121](https://github.com/dascritch/machincast/issues/121)). Ce type est enregistré en base, par exemple `audio/mpeg`, `audio/flac`, ou `video/mp4` pour un `.m4a`. Un type qui n'est pas du son (texte, image, PDF…) donne aussitôt le verdict `non supporté`, sans décodage. Un type que libmagic ne reconnaît pas, comme un fichier vide, laisse le décodage trancher.

Chaque fichier examiné reçoit l'un de ces verdicts :

| Verdict | Signification |
| --- | --- |
| `sain` | Le fichier se décode entièrement. Sa durée décodée, sa date de modification et sa taille sont enregistrées. |
| `endommagé` | Le fichier se décode, mais des données manquent : rupture de continuité dans le son, ou durée décodée plus courte que celle annoncée par l'en-tête du fichier (fichier tronqué, trames perdues). |
| `non supporté` | Le type du fichier n'est pas sonore, quelle que soit son extension : un texte ou une image renommés en `.mp3`, par exemple. Le fichier n'est pas décodé, et le problème donne son type (« de type text/plain, ce n'est pas un fichier sonore »). |
| `illisible` | Le fichier n'est pas du son, il est vide ou son conteneur est cassé, aucun son n'a pu être décodé, ou le décodage ne progresse plus pendant 30 secondes (disque ou partage réseau bloqué). |
| `introuvable` | Aucun fichier à l'emplacement enregistré : il a été supprimé ou déplacé. |

Un décodage qui ne produit aucun son en 5 secondes est repris depuis le début, jusqu'à trois fois : un disque réseau en veille a ainsi le temps de répondre.

Jusqu'à la correction de [#149](https://github.com/dascritch/machincast/issues/149), une indexation de plus de quelques centaines de fichiers épuisait les descripteurs de fichier du système : la console répétait des messages `GStreamer-CRITICAL` (`gst_bus_timed_pop_filtered`, `gst_poll_get_read_gpollfd`), et les fichiers suivants, même sains, étaient déclarés `illisible` (« décodage bloqué au démarrage »). Après la mise à jour, un **audit complet** les décode de nouveau : les sonores sains passés `erroné` redeviennent `actif`, et le bilan les compte parmi les rétablis. Ces messages ne doivent plus apparaître ; s'ils reviennent, c'est à signaler dans un ticket.

Quelques défauts échappent à la vérification : des octets altérés dans un WAV ou un AIFF, qui n'ont ni somme de contrôle ni trames ; un WAV, un Ogg, un MP3 sans durée dans son en-tête ou un AAC brut (`.aac`), tronqué, qui se décode comme un fichier plus court mais sain.

### États d'un sonore

| État | Sens | Jouable | Comment il en sort |
| --- | --- | --- | --- |
| `aperçu` | Fichier nouvellement trouvé, pas encore décodé. | non | Par l'indexeur, au premier décodage sain : il devient `actif`. |
| `actif` | Sonore en service. | oui, dans sa période de diffusion et sous son maximum de lectures | — |
| `désactivé` | Retiré de l'antenne par un choix humain, dans l'interface. | non | Par l'interface seulement. |
| `expiré` | Maximum de lectures atteint, ou période de diffusion terminée : posé par `Machin lecture` ([#18](https://github.com/dascritch/machincast/issues/18)). | non | Par l'interface seulement. |
| `erroné` | Fichier `endommagé` ou `illisible`. | non | Automatiquement, quand l'indexeur trouve le fichier redevenu sain : il redevient `actif`. |
| `non supporté` | Fichier dont le type n'est pas sonore ([#121](https://github.com/dascritch/machincast/issues/121)). | non | Automatiquement, quand le fichier est remplacé par un vrai son : l'indexation suivante le décode, et il redevient `actif`. L'interface peut aussi le passer `actif` ou `désactivé`. |
| `supprimé` | Fichier `introuvable`. | non | Par l'interface seulement. Un fichier déplacé est réindexé comme un nouveau sonore. |

L'indexeur ne change que l'état d'un sonore en `aperçu`, `actif`, `erroné` ou `non supporté` :

| État avant | Fichier `sain` | Fichier `endommagé` ou `illisible` | Fichier `non supporté` | Fichier `introuvable` |
| --- | --- | --- | --- | --- |
| `aperçu`, `actif`, `erroné`, `non supporté` | `actif` | `erroné` | `non supporté` | `supprimé` |
| `désactivé`, `expiré`, `supprimé` | inchangé | inchangé, anomalie signalée | inchangé, anomalie signalée | inchangé, anomalie signalée |

Le bilan compte à part les sonores passés `non supporté`, et compte parmi les rétablis ceux qui redeviennent `actif`.

L'indexeur ne supprime jamais un sonore de la base.

### Tags et métadonnées

Pour un fichier `sain`, l'indexeur lit les tags du fichier pendant le décodage, et les nettoie comme les textes saisis dans l'interface ([#108](https://github.com/dascritch/machincast/issues/108), [Interface graphique](#interface-graphique--machin-interface)) : ID3 (MP3, et AIFF quand il en porte), commentaires Vorbis (Ogg, FLAC), atomes MP4 (M4A) et chunk INFO (WAV, qui ne porte que l'artiste, le titre, l'album, le genre et l'année).

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

Une ligne par sonore indexé, au fil de l'indexation ([#120](https://github.com/dascritch/machincast/issues/120)), avec le chemin du fichier et son statut. Sur la sortie standard, les fichiers trouvés dans les répertoires des banques, puis chaque fichier décodé sain, avec le nom du sonore quand ses tags en donnent un, et ce que devient son état :

```text
Machin_indexation : /musique/jingles/intro.flac : nouveau sonore, ajouté à la banque Jingles
Machin_indexation : /musique/titres/cafe.flac : rattaché à la banque Nuit
Machin_indexation : /musique/jingles/intro.flac : sain, Radio Machin – Générique ; sonore passé actif
Machin_indexation : /musique/titres/cafe.flac : sain, Les Gaufres – Café à minuit ; état actif conservé
```

En indexation rapide, un sonore qui n'est ni nouveau ni en aperçu n'est pas décodé, et n'a donc pas de ligne, sauf si son fichier a disparu. Sur la sortie d'erreur, une ligne par fichier défectueux, avec le problème et sa conséquence :

```text
Machin_indexation : /musique/jingles/intro.mp3 : endommagé : 2 rupture(s) de continuité au décodage, des données ont été perdues ; sonore passé erroné
Machin_indexation : /musique/fond/nappe.flac : introuvable : aucun fichier à cet emplacement ; état désactivé conservé
```

Puis le bilan, sur la sortie standard :

```text
Machin_indexation : indexation rapide : 3 nouveaux sonores, 1 rattachement ; 3 sonores vérifiés ; 1 erroné, 0 non supporté, 1 supprimé, 0 rétabli, 3 sortis d'aperçu
```

Les nouveaux sonores sont les fichiers enregistrés pour la première fois ; les rattachements, les sonores déjà connus ajoutés à une banque dont ils n'étaient pas membres. Les sonores vérifiés sont ceux qui ont été décodés ; les autres nombres comptent les changements d'état.

Enfin, le chemin du **document d'audit** du passage ([#11](https://github.com/dascritch/machincast/issues/11)) :

```text
Machin_indexation : document d'audit : /tmp/machincast-audit-2026-10-15T08:15:00.csv, /tmp/machincast-audit-2026-10-15T08:15:00.html
```

Chaque indexation, rapide ou complète, lancée d'un terminal ou de l'interface, écrit ce document dans `/tmp`, en deux formats : un `.csv` pour un tableur (séparé par des points-virgules) et un `.html` pour un navigateur. Il est nommé avec la date et l'heure locale de son lancement. Il ne liste que les **anomalies**, une ligne par fichier défectueux : date du passage, chemin du fichier, verdict (`endommagé`, `illisible`, `introuvable`), problème et conséquence pour le sonore. Les opérations normales n'y figurent pas. La dernière ligne du CSV, de verdict `bilan`, porte le bilan du passage ; sans anomalie, c'est la seule. Les répertoires de banque introuvables restent sur la sortie d'erreur. Le document n'est pas écrit quand l'indexation s'interrompt (décodeur manquant, base perdue, autre indexation en cours). S'il ne peut pas être écrit, l'indexation le signale sur la sortie d'erreur et va quand même au bout. `/tmp` se vide au redémarrage de la machine : copier ailleurs les documents à garder.

Si GStreamer n'a pas de décodeur pour un format, la vérification s'arrête et nomme les paquets à installer, sans changer l'état des sonores : le fichier n'y est pour rien.

## Diffusion : Machin lecture

`Machin lecture` diffuse la grille sur la sortie audio de la configuration, en continu, jusqu'à ce qu'on l'arrête ([#88](https://github.com/dascritch/machincast/issues/88)), fichiers et streams. Il sait aussi simuler une période à l'avance, sans son ni écriture en base (voir [Simuler la diffusion](#simuler-la-diffusion)). Sur un ordinateur dédié à l'antenne, il tourne comme service, `machincast.service` ([INSTALL.md](../INSTALL.md#service-de-diffusion)), que l'interface démarre, arrête et redémarre ([Piloter la diffusion depuis l'interface](#piloter-la-diffusion-depuis-linterface)).

### Lancer et arrêter la diffusion

```bash
Machin lecture                   # avec le machincast.toml du répertoire de MachinCast
Machin lecture --config <fichier>
```

- **Base** : `Machin lecture` diffuse la grille de la base de production (`base.production`), avec le rôle `machincast_lecture`. Si la base est injoignable, il s'arrête aussitôt avec le code 1 et le message `base de données injoignable`.
- **Sortie** : il joue sur la sortie de `audio.sortie`, sur le périphérique de l'antenne, `audio.peripherique`. Sans ce périphérique, il refuse de diffuser avec le code 2 et le message `périphérique de l'antenne non renseigné` : le périphérique par défaut pourrait être celui de la pré-écoute. Il se règle dans `machincast.toml` ou dans les [préférences](#préférences) de l'interface ([#116](https://github.com/dascritch/machincast/issues/116)) ; seule la sortie `factice` des essais s'en passe. Si la sortie ne peut pas être créée, il s'arrête avec le code 1 et le message `sortie audio indisponible`.
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
- **Fil musical permanent** : un fil musical sans date de début ni de fin sert de fond : il couvre tout le temps où rien d'autre n'est programmé, pas même un autre fil musical ([#32](https://github.com/dascritch/machincast/issues/32)).
- **Toujours un fil musical** : s'il n'en existe aucun, `Machin interface` en crée un, « Fil musical », permanent et sans élément ([#39](https://github.com/dascritch/machincast/issues/39)). Elle le vérifie à son lancement, après la suppression d'un événement et après l'enregistrement d'un événement, et la barre d'état le dit. Sa liste se remplit dans sa [fiche](#fiche-dun-événement) ; vide, il laisse l'antenne en silence, avec une alerte.
- **Dates** : le début et la fin d'un événement sont ceux de sa première diffusion. L'événement est à l'antenne de son début, inclus, à sa fin, exclue : une émission de 20:00 à 22:00 laisse la place à 22:00 pile.
- **Récurrence** : un événement qui se répète revient chacun des jours cochés, à la même heure, à partir de sa première diffusion. Il n'a pas de date de fin de récurrence, ni d'exception pour les jours fériés.
- **Passage de minuit** : un événement peut commencer un jour et finir le lendemain, par exemple de 23:00 à 01:00. Pour un événement récurrent, c'est le jour du début qui compte : une émission du lundi 23:00 à 01:00 est à l'antenne dans la nuit du lundi au mardi.
- **Fils musicaux selon l'heure** : plusieurs fils musicaux peuvent se relayer, par exemple un fil de nuit de 00:00 à 06:00 et un fil de jour de 06:00 à 00:00, tous les jours.
- **Émission ou spécial sans fin** : il reste à l'antenne jusqu'à la fin de sa liste de lecture, qui ne boucle pas ; l'événement en dessous reprend alors. S'il est récurrent, il revient à sa prochaine date. Un événement de même priorité qui commence après lui prend l'antenne, puis il reprend là où il en était, si sa liste n'est pas épuisée ([#32](https://github.com/dascritch/machincast/issues/32)).
- **Chevauchement** : deux événements de même priorité ne se chevauchent pas : la [fiche d'un événement](#fiche-dun-événement) le refuse. Un fil musical permanent ne chevauche rien, et un événement sans fin ne compte que par son début. Si deux événements se chevauchent quand même, écrits directement en base, c'est le dernier modifié qui passe.
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

La case « ne pas répéter » d'une banque se coche dans [sa fiche](#fiche-dune-banque) ([#31](https://github.com/dascritch/machincast/issues/31)). Les fiches d'une [séquence](#fiche-dune-séquence) et d'un [événement](#fiche-dun-événement) préviennent quand une banque marquée y est appelée juste après elle-même : ce deuxième appel sera toujours sauté ([#112](https://github.com/dascritch/machincast/issues/112), [#32](https://github.com/dascritch/machincast/issues/32)). Pour un événement, la fiche compte aussi la dernière ligne avant la première quand la liste boucle, et les banques par lesquelles commencent et finissent ses séquences.

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

Les séquences se créent et se modifient dans leur fiche ([Fiche d'une séquence](#fiche-dune-séquence)), et prennent place dans la liste de lecture d'un événement depuis la fiche de celui-ci ([Fiche d'un événement](#fiche-dun-événement)).

### Sortie audio

La sortie audio de l'antenne se règle dans la configuration (`audio.sortie` : `pipewire`, `pulseaudio`, `alsa`, ou `factice` pour un essai sans son), et `install.sh` vérifie qu'elle peut être créée. Les sonores s'y enchaînent ainsi ([#15](https://github.com/dascritch/machincast/issues/15)) :

- **Crossfade de début** d'un sonore : il monte progressivement, de silencieux à plein volume, pendant ce temps.
- **Crossfade de fin** d'un sonore : le sonore suivant démarre autant avant la fin, et celui-ci s'éteint progressivement pendant ce temps. Les deux se superposent.
- **Les deux crossfades sont nécessaires** : deux sonores ne se superposent que si le premier a un crossfade de fin **et** le second un crossfade de début. Si l'un des deux est à 0, le premier joue jusqu'au bout à plein volume, puis le second démarre aussitôt à plein volume, sans fondu.
- **D'où viennent les crossfades** ([#145](https://github.com/dascritch/machincast/issues/145)) : ceux qu'impose la banque qui a fourni le sonore ; sinon ceux de la fiche du sonore, s'ils y sont paramétrés (0 seconde en est un) ; sinon ceux que la banque applique à défaut ; sinon ceux des [préférences](#préférences), section `[crossfades]` du `machincast.toml` ; sinon aucun.
- **Coupure nette** : au début d'un événement, le sonore en cours s'arrête aussitôt, sans fondu.
- **Avant de jouer un fichier**, sa date de modification et sa taille sont comparées à celles de l'indexation. Un écart est noté dans le log en alerte `fichier modifié`, et le fichier est quand même joué ; la prochaine indexation, même rapide, le revérifie et met la base à jour. Un fichier disparu n'est pas joué : l'incident `fichier introuvable` est noté dans le log, et la diffusion passe aussitôt au sonore suivant. Le sonore n'est plus proposé pendant une heure, pour ne pas noter le même incident à chaque tour de liste ; la prochaine indexation le passera à l'état `supprimé`.
- **Analyse au dernier moment** ([#181](https://github.com/dascritch/machincast/issues/181)) : pendant chaque sonore, si le **prochain** est un fichier jamais vérifié en entier, ou dont le fichier a changé depuis sa vérification, `Machin lecture` lance `Machin indexation --audit-complet --sonore N` sur lui seul, en arrière-plan, sans fenêtre ; ses lignes s'ajoutent au journal de `Machin lecture`. La diffusion ne l'attend pas : si l'analyse plante, ou n'a pas fini, le sonore est joué à son heure. Elle est notée dans le log, en info `analyse du prochain sonore`. Un même sonore n'est pas redemandé avant une heure ; un stream n'est jamais analysé.
- **Superposition** : pendant un crossfade, deux sonores jouent en même temps. PipeWire et PulseAudio les mélangent toujours. En `alsa`, il faut un périphérique qui mélange, comme `default` ; un périphérique matériel direct (`hw:…`) ne joue qu'un son à la fois.

### Détection de blanc

Un fichier peut commencer ou finir par un blanc : un silence, un souffle, une fin de réverbération. Pour ne pas les entendre à l'antenne, la diffusion peut jouer un sonore sans eux ([#146](https://github.com/dascritch/machincast/issues/146)). **Le fichier n'est jamais modifié** : seules les durées de ses blancs sont notées en base ([Les fichiers sonores ne sont jamais modifiés](#les-fichiers-sonores-ne-sont-jamais-modifiés)).

- **Mesure** : l'[audit complet](#indexation-rapide-et-audit-complet), `Machin indexation --audit-complet`, mesure le niveau crête de chaque tranche de 10 ms de chaque fichier sain, sur son canal le plus fort. Le **début détecté** est le blanc avant la première tranche qui atteint le seuil ; la **fin détectée**, le blanc après la dernière, compté depuis la fin du fichier. L'analyse au dernier moment de `Machin lecture` est un audit complet : elle les mesure aussi. L'indexation rapide ne les mesure pas.
- **Seuil** : `blancs.seuil` dans `machincast.toml`, réglable dans les [préférences](#préférences), page « Audio » : de -100 dB compris à 0 dB exclu, -40 dB par défaut, 0 dB étant la pleine échelle. Un fichier qui n'atteint jamais le seuil n'a aucun blanc détecté, et il est joué en entier.
- **Quand la détection s'applique** : jamais par défaut. Un sonore est joué sans ses blancs si sa [fiche](#fiche-dun-sonore) l'active, ou si la [banque](#fiche-dune-banque) qui l'a fourni l'active. Un sonore placé directement dans un événement ou une séquence suit donc son propre réglage. Les streams ne sont jamais concernés.
- **Jeu** : le sonore commence à son début détecté et s'arrête à sa fin détectée. Sa durée à l'antenne est celle sans ses blancs, et les [crossfades](#sortie-audio) se comptent depuis ces bornes : la montée part du début détecté, l'extinction finit à la fin détectée, et le sonore suivant démarre autant avant. L'heure estimée du prochain sonore, l'airplay et la [simulation](#simuler-la-diffusion) suivent ces durées.
- **Sans blanc détecté** : un côté sans blanc détecté n'est pas rogné. Un sonore jamais audité, par exemple ajouté par une indexation rapide, est donc joué en entier, même si la détection s'applique : lancer un audit complet après avoir ajouté des sonores ou activé la détection. Des blancs qui, ensemble, ne laisseraient rien du sonore sont ignorés.
- **Correction à la main** : le début et la fin détectés se corrigent dans la fiche du sonore ; l'audit complet ne les modifie plus ensuite.
- **Ce qui n'en tient pas compte** : les durées minimale et maximale d'une banque ([#147](https://github.com/dascritch/machincast/issues/147)) se comparent à la durée complète du fichier.

### Streams

Un sonore de type stream relaie un flux audio HTTP ou HTTPS, un direct extérieur par exemple, à son adresse directe ou à celle d'un marque-page ([#16](https://github.com/dascritch/machincast/issues/16)) :

- **Métadonnées** : l'airplay note l'artiste et le titre du sonore en base, jamais ceux que le flux annonce (tags ICY). L'emplacement noté est l'adresse du flux.
- **Début d'un événement** de priorité égale ou supérieure : il coupe net le stream, comme un fichier.
- **Fin de son événement** : le stream s'éteint pendant son crossfade de fin. Le sonore suivant démarre en même temps s'il a un crossfade de début, sinon à la fin du fondu ; sans crossfade de fin, le stream s'arrête net.
- **Flux tombé** : un flux qui ne répond pas, ou qui s'arrête avant la fin de son événement, même proprement, est tombé. Son passage se termine en incident, et le log note l'incident `flux tombé`, avec l'adresse du flux et l'erreur. L'**événement de secours** du stream joue sa liste en boucle à sa place. Un stream sans événement de secours laisse jouer l'événement en dessous, le plus souvent le fil musical.
- **Reconnexion** : tant que son événement est à l'antenne, `Machin lecture` retente la connexion toutes les 5 secondes, sans rien faire entendre. Dès que le flux revient, le stream reprend l'antenne : il monte pendant son crossfade de début, et le sonore de remplacement s'éteint pendant ce temps ; sans crossfade de début, le remplacement s'arrête net. La reprise est notée dans le log par l'incident `reprise du flux`, avec l'adresse du flux et la durée de la panne : l'[écran des incidents](#incidents) montre ainsi chaque panne et sa fin.
- **Fin de l'événement pendant la panne** : la reconnexion est abandonnée (`reconnexion abandonnée` dans le log), et la diffusion continue normalement.

Un **événement de secours** est un événement de priorité `secours` : il n'a ni début, ni fin, ni jours de récurrence, et ne passe jamais à l'antenne par la grille, seulement à la place d'un stream tombé. Chaque stream désigne le sien, ou aucun, dans [sa fiche](#fiche-dun-sonore). Un événement de secours se crée dans [sa fiche](#fiche-dun-événement), un stream depuis la liste des sonores ([Ajouter un sonore](#ajouter-un-sonore)).

### Sorties de la diffusion

`Machin lecture` publie ce qu'il diffuse sur plusieurs sorties ([#19](https://github.com/dascritch/machincast/issues/19)), aux chemins de la section `[sorties]` de la configuration, compris depuis le répertoire du fichier de configuration (par défaut, le dossier `sorties` du répertoire de MachinCast, créé au besoin) :

| Sortie | Pour qui | Contenu |
| --- | --- | --- |
| Sortie standard | équipe | Une ligne `à l'antenne : artiste – titre (événement)` à chaque passage, et une ligne à chaque début ou fin d'événement ou de séquence, comme dans le log : `début d'événement : « Journal », émission, de 20:00 à 20:30` ([#153](https://github.com/dascritch/machincast/issues/153)). |
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
| `analyse du prochain sonore` | info | Le prochain sonore n'a pas été vérifié en entier, ou son fichier a changé : `Machin indexation` l'analyse en arrière-plan ([Sortie audio](#sortie-audio)). |
| `analyse impossible` | alerte | `Machin indexation` n'a pas pu être lancé pour le prochain sonore ; le message donne l'erreur. Le sonore est joué quand même. |
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
| `début d'événement`, `fin d'événement` | info | Un événement prend l'antenne, avec son premier sonore, ou la laisse, quand un sonore d'un autre événement commence, ou à l'arrêt de `Machin lecture` ([#153](https://github.com/dascritch/machincast/issues/153)). Le message donne son nom, sa priorité et ses heures : « « Journal », émission, de 20:00 à 20:30 ». Un silence ne termine pas l'événement. |
| `début de séquence`, `fin de séquence` | info | De même pour une séquence : « « Pub », dans « Continue » ». Une séquence qui revient aussitôt recommence. |
| `reconnexion abandonnée` | info | L'événement d'un stream tombé n'est plus à l'antenne : plus de tentative de reconnexion. |

L'airplay et le log ne sont jamais modifiés ni effacés par le binaire lecture : il ne peut qu'y ajouter des lignes.

## Interface graphique : Machin interface

**Textes saisis** ([#108](https://github.com/dascritch/machincast/issues/108)) : les noms, l'artiste, le titre et les métadonnées musicales sont nettoyés à l'enregistrement, pour ne pas gêner les sorties, les flux et les afficheurs : tout espace Unicode (tabulation, retour à la ligne, espace insécable, espace fine…) devient une espace simple, les espaces de début et de fin sont retirées et jamais deux ne se suivent ; les caractères de contrôle, les sélecteurs de variante, les caractères spéciaux (U+FFF0 à U+FFFF), les caractères à usage privé, les caractères non attribués et les espaces sans largeur (U+200B, U+FEFF) sont supprimés. Rien d'autre n'est changé : accents, écritures non latines et emoji restent tels quels. Les chemins de fichiers et les adresses de streams sont gardés tels quels. Les tags lus par l'indexeur sont nettoyés de même.

`Machin interface` se connecte à la base de production, avec les droits de l'interface, puis ouvre sa fenêtre. Elle a un onglet par écran ([#26](https://github.com/dascritch/machincast/issues/26)) : **Accueil**, ouvert au lancement, puis **Événements**, **Séquences**, **Banques**, **Sonores**, **Marques-pages** et **Incidents**. Le **Calendrier** s'ouvre à la demande ([Calendrier](#calendrier)). La barre de menus, en haut de la fenêtre, a cinq menus ([Menus](#menus)).

**Sans base de données**, l'interface n'est pas utilisable : `Machin interface` ouvre alors une fenêtre d'erreur, « MachinCast : base de données injoignable ». Elle explique pourquoi, et invite à lire le document `INSTALL.md` du répertoire de MachinCast, section [En cas de problème](../INSTALL.md#en-cas-de-problème). Son bouton « Ouvrir INSTALL.md » ouvre ce document, et ses détails donnent l'erreur de PostgreSQL. À sa fermeture, `Machin interface` s'arrête avec le code 1. Le message `base de données injoignable` (ou `erreur de base de données`, pour un compte sans droit) s'affiche aussi sur la sortie d'erreur. Sans affichage graphique, par exemple dans une session SSH, seul ce message s'affiche.

### Accueil

L'onglet Accueil est l'**écran par défaut** ([#23](https://github.com/dascritch/machincast/issues/23)), qui montre en un coup d'œil ce qui passe et ce qui va passer :

- **En haut** : la date et l'heure du poste, à la seconde, le **texte public** du sonore en cours entre guillemets, tel que l'affiche la page publique (`—` sans texte, par exemple pour un sonore masqué), et l'état du binaire lecture : `En diffusion`, `En silence` (rien à diffuser) ou `À l'arrêt` ([#144](https://github.com/dascritch/machincast/issues/144)).
- **Événement à l'antenne** : son nom et ses heures, « de 20:00 à 22:00 », « depuis 19:00 » pour une occurrence sans fin, ou « permanent » pour un fil musical ([#144](https://github.com/dascritch/machincast/issues/144)). Ni l'état ni l'événement n'ont d'intitulé, implicites : leur infobulle les nomme ([#191](https://github.com/dascritch/machincast/issues/191)).
- **Sonore en cours et prochain sonore**, côte à côte, chacun sur la moitié de la largeur de la fenêtre, de part et d'autre de la colonne **Antenne** ; un titre trop long passe à la ligne.
- **Sonore en cours** : l'artiste et le titre, l'événement qui le joue, la séquence et la banque d'où il vient (`—` s'il n'en vient pas), l'horaire sur une ligne, « 20:00:00 – 20:03:34 (3:34) » (début, fin estimée et durée), l'emplacement (chemin du fichier, ou adresse du stream) et une barre de progression qui dit le temps qui reste, « reste 3:05 » ([#144](https://github.com/dascritch/machincast/issues/144)).
- **Prochain sonore** : les mêmes informations, avec l'horaire estimé, et l'indicateur « sain » (`oui` si le fichier est présent, actif, lisible et que sa dernière lecture s'est passée sans incident, `non` sinon).
- **Emplacement** : un long chemin ne déborde pas, sa fin (le nom du fichier) reste visible ; il se fait défiler, se sélectionne et se copie, et son infobulle le donne en entier.
- **Coupure annoncée** ([#169](https://github.com/dascritch/machincast/issues/169)) : quand un événement commencera pendant le sonore en cours, il le coupera net. L'horaire du sonore finit alors à la coupure et nomme l'événement, « 20:00:00 – 20:02:00 (coupé par « Journal », sur 3:34) », et la barre de progression dit le temps qui reste jusqu'à elle, « reste 1:30 avant « Journal » ». Le prochain sonore est celui que jouera cet événement, à partir de la coupure. Un stream qu'un événement coupera a ainsi une fin et un temps qui reste.
- **Ouvrir les fiches** ([#144](https://github.com/dascritch/machincast/issues/144)) : le bouton à droite du titre ouvre la fiche du sonore ; ceux à droite de l'événement, de la séquence et de la banque, la fiche de l'élément. Ils sont inactifs sans sonore, en silence par exemple, et ceux de la séquence et de la banque quand le sonore n'en a pas.
- **Stream** : son horaire est « 20:00:00, durée inconnue », et la barre de progression affiche `durée inconnue`. Un stream n'est pas testé à l'avance : son indicateur « sain » est `non testé`. Après un stream, le début du prochain sonore est `inconnu`.
- **Airplay des 12 dernières heures** : une table, du passage le plus récent au plus ancien, avec le début, la fin (`en cours` pour le sonore à l'antenne), la durée diffusée, l'artiste, le titre, l'événement, la séquence, la banque et `oui` dans la colonne « Incident » pour un passage qui en a eu un. Un double-clic sur l'artiste ou le titre ouvre la fiche du sonore, sur l'événement, la séquence ou la banque la fiche de cet élément ([#144](https://github.com/dascritch/machincast/issues/144)). L'interface est réservée à l'équipe : l'artiste et le titre y sont toujours affichés, même masqués sur la page publique.

D'où viennent ces informations :

- **Sonore en cours, prochain sonore, état** : de la socket d'état de `Machin lecture`, au chemin `lecture.socket_etat` de la configuration (voir [État de la diffusion pour l'interface](#état-de-la-diffusion-pour-linterface)). L'interface doit donc tourner sous le même compte que la diffusion, et avec la même configuration. Sans socket, ou quand `Machin lecture` s'arrête, l'écran affiche `À l'arrêt`, et se reconnecte tout seul, chaque seconde, dès que la diffusion reprend.
- **Airplay** : de la base, à l'ouverture, puis chaque fois que la socket annonce un nouveau sonore. L'interface n'interroge jamais la base en boucle. Si la base devient injoignable, la table reste telle qu'elle était, et l'erreur `airplay illisible` s'affiche sur la sortie d'erreur.

La diffusion se démarre et s'arrête par le menu **Diffusion** ([Piloter la diffusion depuis l'interface](#piloter-la-diffusion-depuis-linterface)).

#### VU-mètre de l'antenne

Entre les deux sonores, la colonne **Antenne** montre ce qui sort réellement à l'antenne ([#24](https://github.com/dascritch/machincast/issues/24)) :

- **Saturation**, au-dessus du VU-mètre : ce voyant s'allume, rouge, dès qu'une crête atteint -1 dB, et le reste 3 secondes, pour qu'un écrêtage bref ne passe pas inaperçu. Il se cache dans les [Préférences](#préférences), page « Interface », si l'on n'en veut pas ([#191](https://github.com/dascritch/machincast/issues/191)).
- **VU-mètre** : une barre par canal, de -60 dB en bas à 0 dB en haut ; la barre du canal gauche, « G », et celle du canal droit, « D », sont séparées par l'échelle en dB. Quand la colonne est trop basse, l'échelle n'écrit que les nombres qui tiennent, toujours 0 et -60. La partie pleine est le niveau moyen ; la partie plus claire au-dessus, le bargraph, la crête du moment ; un trait garde la plus haute crête pendant 2 secondes. Vert, orange au-delà de -12 dB, rouge au-delà de -3 dB.
- **Silence**, sous le VU-mètre : ce voyant s'allume, orange, quand tous les canaux restent à -50 dB ou moins pendant 5 secondes : un blanc d'antenne. Il s'éteint dès que le son revient.
- **Écouter l'antenne** : un clic sur le VU-mètre ouvre la [pré-écoute](#pré-écoute) sur l'antenne, sans la lancer : **⏵** la fait entendre dans le casque.

Le VU-mètre écoute le port de monitoring du périphérique de l'antenne, `audio.peripherique`, que son infobulle nomme : il montre le son de l'antenne, quel que soit le programme qui le joue, et ne dérange pas `Machin lecture`. Changer l'antenne dans les [Préférences](#préférences) le fait suivre aussitôt. Il ne fonctionne qu'avec les sorties `pipewire` et `pulseaudio` :

| Sous les voyants | Ce qu'il faut faire |
| --- | --- |
| `Indisponible avec la sortie ALSA, qui n'a pas de port de monitoring.` | Rien : ALSA ne permet pas d'écouter une sortie. Passer à `pipewire` ou `pulseaudio` pour avoir le VU-mètre. |
| `Indisponible : périphérique de l'antenne à renseigner.` | Choisir le périphérique de l'antenne dans **Fichier → Préférences…**, page **Audio**. |
| `Indisponible :` suivi d'une erreur de GStreamer | Le périphérique est débranché, ou le serveur son ne répond pas. Le VU-mètre réessaie toutes les 5 secondes, et reprend tout seul. |

### Listes

Les onglets Événements, Séquences, Banques, Sonores et Marques-pages donnent chacun la liste de tous les éléments de ce type ([#26](https://github.com/dascritch/machincast/issues/26)) :

| Onglet | Colonnes | Ordre |
| --- | --- | --- |
| Événements | nom, nom public, priorité, début, fin, jours de récurrence, anomalie (`événement vide`) | du plus prioritaire (spécial) au moins prioritaire (secours), puis par nom |
| Séquences | nom, nom public, anomalie (`séquence vide`) | par nom |
| Banques | nom, nom public, mode (séquentielle ou aléatoire), « ne pas répéter », premier répertoire (dans l'ordre alphabétique), vide pour une banque sans répertoire | par nom |
| Sonores | artiste, titre, type (fichier ou stream), état, durée, emplacement (chemin du fichier ou adresse du stream), anomalie (`hors durées` d'une banque où il figure, [#147](https://github.com/dascritch/machincast/issues/147)) | par artiste, les sonores sans artiste à la fin, puis par titre |
| Marques-pages | nom, adresse, nombre de streams qui le suivent | par nom |

- **Filtre** : le champ « Filtrer… » garde les lignes dont une colonne contient le texte tapé, sans tenir compte des majuscules ni des accents : `cafe` trouve « Café à minuit », `stream` tous les streams, `/srv/musique` tous les fichiers de ce répertoire. Le compte, à côté, dit combien de lignes restent, par exemple `2 sonores sur 340`. La croix du champ efface le filtre.
- **Anomalies** ([#138](https://github.com/dascritch/machincast/issues/138), [#140](https://github.com/dascritch/machincast/issues/140)) : une ligne qui pose problème, une séquence ou un événement vide, un sonore hors des durées d'une banque ([#147](https://github.com/dascritch/machincast/issues/147)), a l'icône d'avertissement, et son infobulle dit pourquoi. Le compte les dénombre parmi les lignes montrées : `3 séquences, dont 2 en anomalie`. Taper `vide` dans le filtre ne garde que les séquences vides.
- **Tri** : un clic sur le titre d'une colonne trie la liste selon cette colonne ; un second clic inverse l'ordre.
- **Mise à jour** : une liste se relit dans la base chaque fois que son onglet s'ouvre, en gardant son filtre. Elle ne se relit jamais d'elle-même pendant qu'on la regarde.
- **Détails** : un double-clic sur une ligne, ou la touche Entrée, ouvre la fiche de l'élément ([événement](#fiche-dun-événement), [séquence](#fiche-dune-séquence), [banque](#fiche-dune-banque), [sonore](#fiche-dun-sonore)).
- **Créer** : les boutons **Nouvel événement**, **Nouvelle séquence**, **Nouvelle banque**, **Nouveau stream** et **Nouveau marque-page**, à côté du filtre de leur liste, ouvrent une fiche vide. La liste des sonores a aussi **Ajouter des fichiers…**, et accepte les fichiers déposés ([Ajouter un sonore](#ajouter-un-sonore)).
- **Dupliquer** ([#130](https://github.com/dascritch/machincast/issues/130)) : un clic droit sur une ligne des listes Événements, Séquences et Banques propose **Dupliquer**, qui ouvre une copie de l'élément dans une nouvelle fiche ([Dupliquer un élément](#dupliquer-un-élément)).
- **Plusieurs à la fois** : dans les listes Sonores et Banques, Ctrl et Maj sélectionnent plusieurs lignes, et le clic droit propose des actions sur toutes ([Agir sur plusieurs sonores ou banques](#agir-sur-plusieurs-sonores-ou-banques)).

### Agir sur plusieurs sonores ou banques

Dans les listes **Sonores** et **Banques**, plusieurs lignes se sélectionnent à la fois, avec Ctrl (une par une) ou Maj (d'une ligne à une autre) ([#114](https://github.com/dascritch/machincast/issues/114)). Le **clic droit** sur la sélection propose ses actions ; sur une ligne hors de la sélection, il n'agit que sur elle. Chaque action demande confirmation, par exemple « Désactiver 3 sonores ? », puis la liste se relit et la barre d'état dit ce qui a changé, par exemple « 2 sonores désactivés. ». **Annuler** ne change rien.

| Liste | Action | Effet |
| --- | --- | --- |
| Sonores | **Activer**, **Désactiver** | L'état des sonores choisis, comme dans leur fiche. Un sonore en aperçu reste en aperçu, jusqu'à sa vérification par l'indexation. |
| Sonores | **Ajouter à des banques…** | Ouvre le choix des banques ; chaque sonore s'ajoute à la fin de chaque banque choisie, sauf s'il y est déjà. |
| Sonores | **Retirer de banques…** | Ouvre le choix parmi les banques où figure l'un des sonores ; ils en sont retirés. Un sonore dont le fichier est dans un répertoire de la banque y reviendra à la prochaine indexation : déplacer d'abord son fichier, hors de MachinCast. |
| Sonores | **Demander un audit complet** | La prochaine indexation, même rapide, décode ces fichiers en entier et mesure leurs blancs, puis oublie la demande ([Indexation rapide et audit complet](#indexation-rapide-et-audit-complet)). La colonne État dit « actif, audit demandé » en attendant. Un stream n'est jamais vérifié. |
| Banques | **Demander l'audit complet de leurs sonores** | La même demande, pour tous les sonores des banques choisies. |
| Banques | **Masquer l'artiste et le titre**, **Afficher l'artiste et le titre**, **Artiste et titre hérités du sonore** | Le réglage « Artiste et titre » de chaque banque choisie, comme dans sa fiche. |

Une seule banque choisie propose aussi **Dupliquer** ([Dupliquer un élément](#dupliquer-un-élément)).

### Fiche d'une banque

La fiche d'une banque s'ouvre dans un **nouvel onglet**, nommé « Banque : » suivi de son nom, depuis la liste des banques ([#31](https://github.com/dascritch/machincast/issues/31)) ; une fiche vide s'appelle « Nouvelle banque ». Une banque déjà ouverte revient au premier plan, sans second onglet. L'onglet d'une fiche se ferme par sa croix, contrairement à ceux de l'accueil et des listes.

| Champ | Rôle |
| --- | --- |
| Nom interne | Obligatoire, et propre à la banque : c'est son nom dans les listes, le log et l'airplay. |
| Nom public | Facultatif. Affiché sur la page publique à la place de l'artiste et du titre masqués, si l'événement et la séquence n'en ont pas ([Sorties de la diffusion](#sorties-de-la-diffusion)). |
| Mode | `Séquentielle` : les sonores passent dans l'ordre de la liste. `Aléatoire` : ils sont tirés au hasard ([Quel sonore une banque fournit](#quel-sonore-une-banque-fournit)). |
| Artiste et titre | `Masqués` ou `Affichés` sur la page publique, sauf si l'événement ou la séquence en décide. `Hérité du sonore` laisse décider le sonore, puis la configuration. |
| Ne pas répéter | La banque ne passe jamais deux fois de suite ([Quel sonore une banque fournit](#quel-sonore-une-banque-fournit)). |
| Détection de blanc | Décochée pour une nouvelle banque. Cochée, les sonores joués via la banque le sont sans les blancs détectés à leur début et à leur fin ([Détection de blanc](#détection-de-blanc)). |
| Durée minimale, durée maximale des sonores | Facultatives, à cocher ([#147](https://github.com/dascritch/machincast/issues/147)) : pour ne pas confondre un mix, une chanson et une publicité. Un sonore qui en sort est marqué dans la liste des sonores de la fiche, dès la saisie, avec une infobulle (« 3:20 : plus court que le minimum de la banque, 3:30. ») ; il l'est aussi dans l'onglet Sonores et dans les relations de sa fiche. Rien n'est refusé, et la diffusion n'en tient pas compte ; seule une durée minimale plus longue que la maximale empêche d'enregistrer. |
| Crossfade de début, crossfade de fin | Pour les sonores joués via la banque ([#143](https://github.com/dascritch/machincast/issues/143)), chacun avec sa règle : `Garder ceux des sonores` laisse le crossfade de chaque sonore (la durée de la banque est alors grisée) ; `Appliquer si le sonore n'en a pas` donne la durée de la banque aux sonores dont le crossfade est de 0 seconde ; `Imposer à tous les sonores` la donne à tous. Un sonore placé directement dans un événement ou une séquence garde toujours les siens. |

**Enregistrer et annuler** : les modifications restent dans la fiche jusqu'au clic sur **Enregistrer**, qui les écrit toutes à la fois ; **Annuler** remet la fiche telle qu'elle est en base. Les deux boutons ne servent que quand la fiche est modifiée.

- Les noms sont enregistrés sans les espaces qui les entourent. Un nom interne vide est refusé (« Le nom interne est obligatoire. »), comme celui d'une autre banque (« Une autre banque s'appelle déjà « Tubes ». ») : rien n'est enregistré, et la fiche garde ses modifications.
- Si la base est injoignable, la fiche affiche « Enregistrement impossible : » et l'erreur de PostgreSQL, et garde ses modifications ; l'erreur s'affiche aussi sur la sortie d'erreur.
- **Fermer une fiche modifiée**, par son onglet ou en fermant la fenêtre, demande quoi faire des modifications : **Enregistrer** (Entrée), **Abandonner**, ou **Annuler** (Échap), qui garde la fiche ouverte. Si l'enregistrement échoue, la fiche reste ouverte.

**Répertoires indexés** : les fichiers sonores de ces répertoires, et de leurs sous-répertoires, sont rattachés à la banque par `Machin indexation` ([Alimenter une banque](#alimenter-une-banque)). **Ajouter un répertoire…** ouvre le sélecteur de répertoires du poste ; on peut aussi y **déposer des dossiers** glissés depuis le navigateur de fichiers (un fichier déposé là est ignoré, et la fiche le dit). Un répertoire déjà présent n'est pas ajouté deux fois. **Retirer le répertoire** retire celui qui est choisi dans la liste. Les répertoires sont rangés dans l'ordre de leurs caractères. Rien n'est indexé à l'enregistrement : les fichiers d'un nouveau répertoire arrivent dans la banque à la prochaine indexation.

**Sonores** : la liste montre chaque sonore (artiste et titre), sa durée (`inconnue` pour un stream, vide pour un fichier pas encore décodé) et son emplacement.

- **Ordre** : en mode séquentiel, un sonore se déplace par glisser-déposer, ou en le choisissant puis avec **Monter** et **Descendre**. En mode aléatoire, l'ordre ne compte pas, et ne se change pas.
- **Ouvrir un sonore** : un double-clic sur un sonore de la liste, ou Entrée sur le sonore choisi, ouvre sa fiche dans un nouvel onglet ([#115](https://github.com/dascritch/machincast/issues/115)). La fiche de la banque reste ouverte, avec ses modifications. Un fichier déposé n'a de fiche qu'une fois la banque enregistrée.
- **Ajouter des sonores…** ouvre la liste des sonores déjà en base, avec son filtre. Plusieurs sonores se choisissent avec Ctrl ou Maj, puis **Ajouter** ; un double-clic en choisit un seul. Ils s'ajoutent en fin de liste, même s'ils sont hors des répertoires de la banque ; un sonore déjà dans la banque n'est pas ajouté deux fois. Un nouveau fichier se dépose sur la liste (ci-dessous), ou dans un répertoire de la banque avant de lancer `Machin indexation`, ou s'ajoute d'abord depuis la liste des sonores ([Ajouter un sonore](#ajouter-un-sonore)).
- **Déposer des fichiers** glissés depuis le navigateur de fichiers les ajoute en fin de liste, dans les deux modes, une fois chacun. Un fichier déjà en base reprend son sonore. Un fichier pas encore en base est montré par son nom, et devient à l'enregistrement un sonore à l'état `aperçu`, que la prochaine indexation décodera ; « Annuler » ou « Abandonner » ne l'enregistrent pas. Les dossiers et les fichiers qui ne sont pas sonores (voir les formats dans [Alimenter une banque](#alimenter-une-banque)) sont ignorés, et la fiche le dit.
- **Un dépôt est toujours une copie** : le fichier reste où il est, et n'est pas touché. Même avec Maj enfoncée, qui demande d'habitude un déplacement au navigateur de fichiers, la fiche ne l'accepte que comme une copie ; un glisser qui ne propose que le déplacement est refusé.
- **Retirer le sonore** retire le sonore choisi de la banque, sans rien demander s'il est hors de ses répertoires. Si son fichier est dans l'un des répertoires de la fiche, ou de leurs sous-répertoires, un avertissement rappelle que **la prochaine indexation l'y remettra** : **Retirer quand même**, **Ouvrir le dossier** du fichier dans le navigateur de fichiers du poste, pour l'en déplacer (le sonore reste dans la banque), ou **Annuler**. MachinCast ne déplace ni ne supprime jamais le fichier ([Les fichiers sonores ne sont jamais modifiés](#les-fichiers-sonores-ne-sont-jamais-modifiés)) : c'est à faire hors de l'outil, parfois depuis un autre poste quand le compte n'a pas le droit d'écrire dans le répertoire. Le sonore reste en base, dans ses autres banques et événements.
- **Plusieurs sonores** ([#114](https://github.com/dascritch/machincast/issues/114)) : Ctrl et Maj en choisissent plusieurs. **Retirer le sonore** les retire tous ; ceux des répertoires de la fiche sont nommés ensemble, dans un seul avertissement. **Monter** et **Descendre** ne servent qu'à un sonore seul. La colonne **État** montre l'état de chaque sonore : le clic droit sur les sonores choisis propose **Activer** et **Désactiver**, que la colonne montre aussitôt et qu'**Enregistrer** écrit avec le reste de la fiche ; **Annuler** l'oublie. Un sonore en aperçu, ou un fichier déposé pas encore enregistré, reste en aperçu.
- **Indexation pendant la modification** : les sonores que `Machin indexation` rattache à la banque pendant que la fiche est ouverte sont gardés à l'enregistrement, en fin de liste. Un sonore effacé de la base entre-temps est oublié.

### Fiche d'un sonore

La fiche d'un sonore s'ouvre depuis la liste des sonores, dans un nouvel onglet nommé « Sonore : » suivi de son titre, ou du nom de son fichier, ou de l'adresse d'un stream ([#28](https://github.com/dascritch/machincast/issues/28)). Elle se comporte comme [celle d'une banque](#fiche-dune-banque) : **Enregistrer** et **Annuler**, une seule fiche par sonore, et la question à la fermeture d'une fiche modifiée.

**Sonore** : le type, l'emplacement du fichier et sa durée, qui ne se modifient pas, et l'**état**. La fiche pose `actif` ou `désactivé` ; un sonore `expiré`, `erroné` ou `supprimé` peut revenir à `actif` (voir [États d'un sonore](#états-dun-sonore)). Un sonore en `aperçu` attend sa première indexation, et son état ne se choisit pas.

**Métadonnées** : artiste, titre, année, album, artiste de l'album, genre, compositeur, label et piste. Les autres métadonnées, ajoutées hors de MachinCast, sont montrées sans se modifier. Un champ vide n'a pas de valeur ; les textes sont enregistrés sans les espaces qui les entourent.

**Diffusion** :

- **Crossfade de début et de fin**, en secondes (voir [Sortie audio](#sortie-audio)), à cocher ([#145](https://github.com/dascritch/machincast/issues/145)) : décoché, le crossfade n'est pas paramétré, et vient de la banque ou des [préférences](#préférences) ; 0 seconde est un crossfade paramétré. Leur pas et leur durée maximale suivent les préférences.
- **Maximum de lectures** : `illimité` à 0 (voir [Expiration des sonores](#expiration-des-sonores)).
- **Artiste et titre** : `Masqués` ou `Affichés` sur la page publique, sauf si l'événement, la séquence ou la banque en décide ; `Selon la configuration` laisse décider la configuration (voir [Sorties de la diffusion](#sorties-de-la-diffusion)).
- **Diffusion à partir du**, **Diffusion jusqu'au** : la période de diffusion, chacune à cocher. Une case cochée part de l'heure du moment, à la minute. La fin doit suivre le début, sinon la fiche le dit et n'enregistre rien.

**Détection de blanc**, pour un fichier seulement ([Détection de blanc](#détection-de-blanc)) :

- **Jouer sans les blancs détectés** : décochée par défaut. Cochée, le sonore est joué sans ses blancs, même placé directement dans un événement ou une séquence, ou fourni par une banque qui ne les retire pas.
- **Début détecté**, **Fin détectée** : en secondes, au centième, mesurés par l'audit complet ; la fin se compte depuis la fin du fichier. Chacun est à cocher : décoché, aucun blanc n'est détecté de ce côté, qui n'est pas rogné. Ils se corrigent à la main, et l'audit complet ne les modifie plus ensuite. Ensemble, ils doivent rester plus courts que la durée du sonore, sinon la fiche dit « Les blancs détectés doivent laisser du son : ensemble, plus courts que la durée du sonore. » et n'enregistre rien.

**Saisi à la main** : chaque champ modifié à l'enregistrement est noté comme saisi à la main, et la fiche en donne la liste. L'**indexeur ne le modifie plus jamais**, même vidé : un album effacé ne revient pas des tags du fichier. L'état n'est jamais noté ainsi : l'indexeur peut encore passer un sonore à `erroné`, puis de nouveau à `actif`. Seuls les champs modifiés sont écrits : ce que l'indexation ou la diffusion change pendant que la fiche est ouverte (un titre lu dans les tags, un sonore qui expire) est gardé.

**Stream** (voir [Streams](#streams)) :

- **Adresse directe** ou **Marque-page**, parmi les [marques-pages](#marques-pages) en base. Un stream sans adresse n'est pas enregistré.
- **Événement de secours** : parmi les événements de priorité `secours`, ou `Aucun : le fil musical`.
- **Tester le flux** : la fiche se connecte à l'adresse saisie, même pas encore enregistrée, et dit `Le flux répond : du son arrive.` dès qu'une seconde de son est décodée. Sinon, elle dit `Le flux ne répond pas :` suivi de l'erreur (adresse invalide, serveur injoignable, réponse en erreur), ou `le son n'arrive pas en 10 s.`. Rien n'est joué. La connexion se ferme à la fin du test, et à la fermeture de la fiche ou de la fenêtre.

**Derniers passages** : les 50 derniers passages du sonore, du plus récent au plus ancien, avec le début, la fin (`en cours` pour le passage à l'antenne), la durée diffusée, l'événement, la séquence, la banque, et les alertes et incidents que le log a notés pour ce sonore pendant le passage. L'infobulle de cette dernière colonne les détaille, avec leur heure et leur message.

**Dossier** : le bouton à droite de l'emplacement ouvre le dossier du fichier dans le navigateur de fichiers du poste ([#125](https://github.com/dascritch/machincast/issues/125)), par exemple pour en écarter le fichier. MachinCast lui-même n'y touche pas ([Les fichiers sonores ne sont jamais modifiés](#les-fichiers-sonores-ne-sont-jamais-modifiés)).

**Relations** : les séquences, banques et événements dont la liste cite directement le sonore, par genre puis par nom. Un double-clic ouvre leur fiche. Sans relation, la fiche le dit. Une banque dont le sonore sort des durées a l'icône d'avertissement, et son infobulle dit pourquoi ([#147](https://github.com/dascritch/machincast/issues/147)).

**Fichier**, pour un sonore de type fichier :

| Champ | Contenu |
| --- | --- |
| Type | Le type réel du fichier, lu par l'indexeur ([Verdicts de la vérification d'un fichier](#verdicts-de-la-vérification-dun-fichier)) ; `inconnu` avant sa première vérification. |
| Encodage moyen | La taille du fichier rapportée à sa durée, en kbit/s : une moyenne sur le fichier entier, pochette et tags compris. |
| Taille | En unités décimales : `1,2 Mo` pour 1 234 567 octets. |
| Créé le, Modifié le | Lus sur le fichier, à l'ouverture de la fiche, sans le modifier. La création est `inconnue` sur un système de fichiers qui ne la garde pas. Un fichier absent : `introuvable`. |
| Dernière vérification complète | Le dernier passage de l'indexeur qui a lu son type et l'a décodé en entier, en indexation rapide comme en audit complet ; `jamais` avant le premier. |

Le bouton **Pré-écoute…** fait écouter le sonore ([Pré-écoute](#pré-écoute)). L'ajout d'un sonore : [Ajouter un sonore](#ajouter-un-sonore) ; sa suppression : [Supprimer un élément](#supprimer-un-élément).

### Fiche d'une séquence

La fiche d'une [séquence](#séquences) s'ouvre depuis la liste des séquences, dans un nouvel onglet nommé « Séquence : » suivi de son nom ([#112](https://github.com/dascritch/machincast/issues/112)) ; **Nouvelle séquence** ouvre une fiche vide. Elle se comporte comme [celle d'une banque](#fiche-dune-banque) : **Enregistrer** et **Annuler**, une seule fiche par séquence, et la question à la fermeture d'une fiche modifiée.

| Champ | Rôle |
| --- | --- |
| Nom interne | Obligatoire, et propre à la séquence : c'est son nom dans les listes, le log et l'airplay. |
| Nom public | Facultatif. Affiché sur la page publique à la place de l'artiste et du titre masqués, si l'événement n'en a pas ([Sorties de la diffusion](#sorties-de-la-diffusion)). |
| Artiste et titre | `Masqués` ou `Affichés` sur la page publique, pour les sonores que la séquence fait jouer, sauf si l'événement en décide. `Selon la banque ou le sonore` laisse décider la banque, puis le sonore, puis la configuration. |

Les noms sont enregistrés sans les espaces qui les entourent. Rien n'est enregistré, et la fiche le dit, pour un nom interne vide (« Le nom interne est obligatoire. ») ou celui d'une autre séquence (« Une autre séquence s'appelle déjà « Ouverture ». »).

**Séquence vide** ([#138](https://github.com/dascritch/machincast/issues/138)) : une séquence sans élément s'enregistre, pour être complétée plus tard. La fiche avertit « Séquence vide : elle ne joue rien, et un événement qui l'appelle passe à son élément suivant. » : la diffusion la saute sans bloquer l'événement, et la liste des séquences la montre en anomalie.

**Éléments** : la liste ordonnée des sonores et des banques que la séquence joue. Chaque ligne donne le genre de l'élément, son nom (artiste et titre d'un sonore, ou le nom de son fichier tant qu'il n'est pas décodé) et un détail : l'emplacement d'un sonore, le mode d'une banque et « ne pas répéter » si elle l'est.

- **Ordre** : un élément se déplace par glisser-déposer, ou en le choisissant puis avec **Monter** et **Descendre**.
- **Ajouter des sonores…** et **Ajouter des banques…** ouvrent la liste de ceux déjà en base, avec son filtre ; plusieurs se choisissent avec Ctrl ou Maj, puis **Ajouter**. Ils s'ajoutent en fin de liste. **Un même sonore ou une même banque peut revenir** plusieurs fois. Une séquence ne contient jamais une autre séquence.
- **Déposer des fichiers** glissés depuis le navigateur de fichiers les ajoute en fin de liste, une fois par fichier déposé, comme sur [la fiche d'une banque](#fiche-dune-banque) : un fichier déjà en base reprend son sonore, un autre devient à l'enregistrement un sonore à l'état `aperçu`, les dossiers et les fichiers qui ne sont pas sonores sont ignorés, et la fiche le dit. Un dépôt est toujours une copie : le fichier n'est pas touché.
- **Retirer l'élément** retire la ligne choisie, sans rien demander : le sonore ou la banque reste en base.
- **Banque « ne pas répéter »** : quand une banque marquée « ne pas répéter » est appelée deux fois de suite, la fiche signale sous la liste la ligne du deuxième appel, qui sera toujours sauté à la diffusion (« Ligne 3 : la banque « Publicité » vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. »). Ce n'est qu'un avertissement : la séquence s'enregistre quand même.
- **Pendant la modification** : un sonore ou une banque effacé de la base entre-temps est oublié à l'enregistrement. Une ligne restée dans la liste reste celle que désigne l'historique de diffusion : après un redémarrage, la séquence reprend après elle, à sa nouvelle place ([Séquences](#séquences)).

**Ouvrir un élément** : un double-clic, ou Entrée, sur un sonore ou une banque ouvre sa fiche dans un autre onglet. Un fichier déposé n'a pas de fiche avant l'enregistrement.

**Événements** : la liste des événements où la séquence figure, par nom ; elle ne se modifie pas ici, mais dans la [fiche de l'événement](#fiche-dun-événement), qu'un double-clic ouvre.

### Fiche d'un événement

La fiche d'un événement s'ouvre depuis la liste des événements, dans un nouvel onglet nommé « Événement : » suivi de son nom ([#32](https://github.com/dascritch/machincast/issues/32)) ; **Nouvel événement** ouvre une fiche vide, de priorité `Émission`. Elle se comporte comme [celle d'une banque](#fiche-dune-banque) : **Enregistrer** et **Annuler**, une seule fiche par événement, et la question à la fermeture d'une fiche modifiée.

| Champ | Rôle |
| --- | --- |
| Nom interne | Obligatoire, et propre à l'événement : c'est son nom dans les listes, le log et l'airplay. |
| Nom public | Facultatif. Affiché sur la page publique à la place de l'artiste et du titre masqués ([Sorties de la diffusion](#sorties-de-la-diffusion)). |
| Priorité | `Fil musical`, `Émission` ou `Spécial` ([Quel événement est à l'antenne](#quel-événement-est-à-lantenne)), ou `Secours`, qui ne joue qu'à la place d'un stream tombé ([Streams](#streams)). |
| Artiste et titre | `Masqués` ou `Affichés` sur la page publique, pour tout ce que l'événement fait jouer. `Selon la séquence, la banque ou le sonore` laisse décider la séquence, puis la banque, puis le sonore, puis la configuration. |

**Grille** : le **Début** et la **Fin** de la première occurrence, chacun à cocher, puis les **jours** où elle revient chaque semaine, à la même heure (aucun jour coché : une seule occurrence). Toutes les heures sont celles de Paris.

- Un début coché part de l'heure du moment, à la minute ; une fin cochée, d'une heure après le début.
- Sans début, ni fin ni jours : un fil musical sans début est permanent, et sert de fond. Décocher le début décoche aussi la fin et les jours.
- Un événement de secours n'a ni début, ni fin, ni jours : choisir `Secours` les décoche.
- Une émission ou un spécial a un début ; sans fin, il dure jusqu'au bout de sa liste ([Quel événement est à l'antenne](#quel-événement-est-à-lantenne)).

**Rien n'est enregistré**, et la fiche dit pourquoi :

- un nom interne vide, ou celui d'un autre événement (« Un autre événement s'appelle déjà « Continue ». ») ;
- une émission ou un spécial sans début, ou une fin qui ne suit pas le début ;
- un **chevauchement** avec un autre événement de même priorité : la fiche nomme le premier, avec le premier instant commun (« Chevauche l'événement « Journal », de même priorité, le 21/10/2026 à 09:00. »). Les occurrences récurrentes comptent toutes. Un événement sans fin ne compte que par son début, et un fil musical permanent ne chevauche rien ;
- une priorité changée pour un événement de secours qu'un stream désigne (« Des streams ont cet événement pour secours : « Radio Thune ». Il reste de priorité « Secours ». »).

**Événement vide** ([#140](https://github.com/dascritch/machincast/issues/140)) : un événement sans élément s'enregistre, pour être complété plus tard. La fiche avertit de ce qu'en fera la diffusion, selon sa priorité :

- émission ou spécial : « Événement vide : il ne joue rien, et l'événement de priorité inférieure prend le relais pendant sa plage. » ;
- fil musical : « Événement vide : il ne joue rien, et la diffusion se tait, avec une alerte, quand il est à l'antenne. » ;
- secours : « Événement vide : il ne joue rien, et l'événement de priorité inférieure remplace le stream tombé. ».

La liste des événements le montre en anomalie, avec le même texte en infobulle.

**Liste de lecture** : les sonores, les banques et les [séquences](#séquences) que l'événement joue, dans l'ordre. Elle se gère comme celle d'une [séquence](#fiche-dune-séquence) : glisser-déposer, **Monter** et **Descendre**, **Ajouter des sonores…**, **Ajouter des banques…** et **Ajouter des séquences…**, dépôt de fichiers sonores, **Retirer l'élément**. **Ajouter des marques-pages…** ([#167](https://github.com/dascritch/machincast/issues/167)) ajoute un stream directement depuis son [marque-page](#marques-pages), pour retransmettre une émission en extérieur : le stream qui suit déjà ce marque-page (le premier par titre, s'il y en a plusieurs) ; sinon, un nouveau stream, actif, titré du nom du marque-page, créé à l'enregistrement (la ligne le dit : « nouveau stream »). Un même marque-page ajouté deux fois ne crée qu'un stream. Un même élément peut revenir. Le détail d'une séquence est son nombre d'éléments. Une ligne restée dans la liste reste celle que désigne l'historique de diffusion : un fil musical reprend après elle, à sa nouvelle place ([Comment une liste de lecture se déroule](#comment-une-liste-de-lecture-se-déroule)).

**Banque « ne pas répéter »** : la fiche signale chaque appel d'une banque marquée juste après elle-même, qui sera toujours sauté à la diffusion. La liste boucle, sauf pour une émission ou un spécial sans fin : la première ligne suit alors la dernière. Une séquence compte par les banques qui la commencent et la finissent (« Ligne 2 : la séquence « Pub d'abord » commence par la banque « Publicité », qui vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. »). Ce n'est qu'un avertissement : l'événement s'enregistre quand même.

**Ouvrir un élément** : un double-clic, ou Entrée, sur un sonore, une banque ou une séquence ouvre sa fiche dans un autre onglet.

### Ajouter un sonore

La liste des sonores ajoute des fichiers et des streams ([#30](https://github.com/dascritch/machincast/issues/30)).

**Fichiers** : **Ajouter des fichiers…** ouvre le sélecteur de fichiers du poste, où plusieurs fichiers se choisissent à la fois ; on peut aussi **déposer des fichiers** sur la liste, glissés depuis le navigateur de fichiers.

- Un fichier est **référencé là où il se trouve, sans copie**, et n'est jamais modifié ([Les fichiers sonores ne sont jamais modifiés](#les-fichiers-sonores-ne-sont-jamais-modifiés)). Il peut donc être synchronisé depuis un autre ordinateur, et changer de contenu sous le même nom (une émission pré-enregistrée, la rediffusion d'un direct). Un dépôt est toujours une copie : même avec Maj enfoncée, le fichier reste où il est ; un glisser qui ne propose que le déplacement est refusé.
- Il entre en base à l'état `aperçu`, puis **l'indexeur le vérifie aussitôt**, en tâche de fond : l'interface reste utilisable. La barre d'état, en bas de la fenêtre, annonce l'ajout (« 2 fichiers ajoutés, en cours de vérification. »), puis la fin de la vérification, avec l'état de chaque sonore (« Vérification terminée : Les Gaufres – Café à minuit, actif ; faux.mp3, erroné. »). Le sonore prend alors sa durée, son artiste et son titre lus dans les tags, comme avec `Machin indexation` ([États d'un sonore](#états-dun-sonore)).
- Un fichier déjà en base n'est pas ajouté une seconde fois ; les dossiers et les fichiers qui ne sont pas sonores (voir les formats dans [Alimenter une banque](#alimenter-une-banque)) sont ignorés. La barre d'état le dit.
- Si l'indexeur ne sait pas décoder un format (un paquet GStreamer manque), le sonore reste en `aperçu` : la prochaine indexation le reprendra. Fermer la fenêtre attend la fin de la vérification en cours.

Seuls les fichiers ajoutés depuis la liste des sonores sont vérifiés aussitôt : un fichier déposé sur une banque, une séquence ou un événement attend la prochaine indexation.

**Stream** : **Nouveau stream** ouvre une [fiche de sonore](#fiche-dun-sonore) vide, nommée « Nouveau stream ». L'adresse directe ou le marque-page est obligatoire ; l'événement de secours, le titre et les autres champs se saisissent comme pour un stream existant. Le stream entre en base à l'état `actif`.

### Marques-pages

Un **marque-page** est une adresse de flux réutilisable, souvent en ligne par intermittence : plusieurs streams peuvent le suivre, et jouent son adresse ([#34](https://github.com/dascritch/machincast/issues/34)). L'onglet **Marques-pages** en donne la liste ; **Nouveau marque-page** ouvre une fiche vide, et un double-clic la fiche d'un marque-page, dans un onglet nommé « Marque-page : » suivi de son nom. Elle se comporte comme [celle d'une banque](#fiche-dune-banque) : **Enregistrer** et **Annuler**, une seule fiche par marque-page, et la question à la fermeture d'une fiche modifiée.

- **Nom** : obligatoire, et propre au marque-page. **Adresse** : obligatoire. Les deux sont enregistrés sans les espaces qui les entourent. Une nouvelle adresse vaut aussitôt pour tous les streams qui suivent le marque-page.
- **Tester le flux** : comme dans la [fiche d'un sonore](#fiche-dun-sonore), la fiche se connecte à l'adresse saisie, même pas encore enregistrée, et dit si du son arrive. Rien n'est joué, et la connexion se ferme à la fin du test ou à la fermeture de la fiche.
- **Streams qui le suivent** : un double-clic ouvre la fiche du stream, où il choisit son marque-page ou une adresse directe.
- **Supprimer…** : un marque-page qu'un stream suit ne se supprime pas ; la fiche nomme ces streams, qui doivent d'abord choisir une autre adresse. Sinon, la suppression se confirme comme ailleurs ([Supprimer un élément](#supprimer-un-élément)).

### Incidents

L'onglet **Incidents** montre les alertes et les incidents que `Machin lecture` a notés dans le log, du plus récent au plus ancien ([#35](https://github.com/dascritch/machincast/issues/35)) : horaire, niveau, nature, message, et le sonore, la banque et l'événement concernés quand ils sont renseignés. La liste des natures est dans [Historique de diffusion et log](#historique-de-diffusion-et-log).

- **Montrer aussi les informations** ajoute les entrées de niveau `info` (démarrage, élément sauté, sonore expiré, débuts et fins d'événements et de séquences [#153](https://github.com/dascritch/machincast/issues/153)…).
- **Filtre** : comme pour les listes, sans tenir compte des majuscules ni des accents ; le compte dit combien d'entrées restent.
- **Liens** : un double-clic sur le sonore, la banque ou l'événement d'une entrée ouvre sa fiche. Un élément supprimé depuis laisse sa cellule vide ; l'entrée garde son message.
- **Lecture** : l'écran se relit chaque fois que son onglet s'ouvre. Seules les 500 entrées les plus récentes sont lues : le compte le dit alors (« 500 entrées, les plus récentes »).
- `Machin indexation` n'écrit pas dans le log : ses anomalies sont sur sa sortie d'erreur, dans son document d'audit ([Ce qu'affiche l'indexation](#ce-quaffiche-lindexation)), ou dans le journal de l'indexation lancée depuis l'interface, pas ici.

### Passer d'un onglet à l'autre au clavier

Les 12 premiers onglets s'ouvrent au clavier, par <kbd>Maj</kbd>+<kbd>F1</kbd> à <kbd>Maj</kbd>+<kbd>F12</kbd>, selon leur rang ([#192](https://github.com/dascritch/machincast/issues/192)) : <kbd>Maj</kbd>+<kbd>F1</kbd> est toujours l'Accueil, <kbd>Maj</kbd>+<kbd>F2</kbd> à <kbd>Maj</kbd>+<kbd>F6</kbd> les listes Événements, Séquences, Banques, Sonores et Marques-pages, <kbd>Maj</kbd>+<kbd>F7</kbd> les Incidents, puis les fiches et le calendrier dans l'ordre où ils sont ouverts. Fermer un onglet décale ceux qui le suivent : leur raccourci change. L'infobulle de chaque onglet donne le sien ; au-delà du douzième, un onglet n'en a pas.

### Menus

La barre de menus donne accès aux fonctions générales de l'interface ([#117](https://github.com/dascritch/machincast/issues/117)). Une fonction pas encore écrite a déjà son entrée, grisée : son infobulle, au survol, donne le ticket qui l'apportera.

| Menu | Entrée | Rôle |
| --- | --- | --- |
| Fichier | Préférences… | Règle les crossfades de l'interface ([Préférences](#préférences)). L'icône de l'application viendra avec [#111](https://github.com/dascritch/machincast/issues/111). |
| Fichier | Quitter | Ferme l'interface, aussi par <kbd>Alt</kbd> + <kbd>Q</kbd>, même depuis une fiche. Comme la fermeture de la fenêtre, demande d'abord quoi faire des fiches modifiées ; « Annuler » garde l'interface ouverte. La diffusion n'est pas concernée : `Machin lecture` continue. |
| Affichage | Pré-écoute… | Ouvre la fenêtre de pré-écoute, pour écouter un sonore ou choisir sa sortie ([Pré-écoute](#pré-écoute)). |
| Affichage | Calendrier | Ouvre l'onglet du calendrier de la grille ([Calendrier](#calendrier)). |
| Affichage | Rafraîchir les onglets | Relit ce que d'autres postes, l'indexation ou la diffusion ont changé en base, aussi par <kbd>F5</kbd> ([Rafraîchir les onglets](#rafraîchir-les-onglets)). |
| Diffusion | Démarrer la diffusion, Arrêter la diffusion, Redémarrer la diffusion | Pilotent le service de diffusion, selon son état ; sans le service, une diffusion d'essai ([Piloter la diffusion depuis l'interface](#piloter-la-diffusion-depuis-linterface)). |
| Maintenance | Moniteur de la sortie… | À venir ([#85](https://github.com/dascritch/machincast/issues/85)). |
| Maintenance | Indexation rapide, Audit complet | Lancent l'indexation ([Lancer l'indexation depuis l'interface](#lancer-lindexation-depuis-linterface)). |
| Aide | Documentation | Ouvre ce guide d'utilisation sur GitHub, dans le navigateur web du poste. |
| Aide | Signaler un problème… | Ouvre les tickets de MachinCast sur GitHub, dans le navigateur web du poste. |
| Aide | Version | Donne le numéro de version de MachinCast, et la date de sa dernière modification : celle du dernier commit du dépôt git d'où il est installé ([INSTALL.md](../INSTALL.md)), à l'heure du poste. Une installation qui n'est pas un dépôt git, ou un poste sans git, ne donne que le numéro de version. |

### Préférences

**Fichier → Préférences…** ouvre la fenêtre des préférences ([#145](https://github.com/dascritch/machincast/issues/145)). Sa page **Interface** règle les crossfades :

| Réglage | Rôle |
| --- | --- |
| Granularité | `Au dixième de seconde` (par défaut) ou `À la seconde` : le pas des champs de crossfade des fiches d'un sonore et d'une banque. |
| Durée maximale | Le crossfade le plus long que proposent ces champs, 5 secondes par défaut. Une valeur déjà plus longue reste telle quelle. |
| Début par défaut, fin par défaut | À cocher : le crossfade d'un sonore qui n'en a pas de paramétré, et que sa banque ne règle pas ([D'où viennent les crossfades](#sortie-audio)). Ils ne dépassent pas la durée maximale. |

La même page règle l'**accueil** ([#191](https://github.com/dascritch/machincast/issues/191)) : **Afficher le voyant de saturation de l'accueil**, cochée par défaut, montre le voyant « Saturation » de la colonne Antenne. Décochée, il disparaît aussitôt, à l'enregistrement des préférences ; le VU-mètre montre toujours les crêtes, et le voyant « Silence » reste. Elle s'enregistre dans `interface.saturation`.

Sa page **Audio** règle les périphériques ([#116](https://github.com/dascritch/machincast/issues/116)) :

| Réglage | Rôle |
| --- | --- |
| Antenne | Le périphérique sur lequel `Machin lecture` diffuse, `audio.peripherique`. Tant qu'il n'est pas renseigné, il se propose « (à renseigner) », la barre d'état de l'interface affiche `Périphérique de l'antenne à renseigner`, et `Machin lecture` refuse de diffuser. |
| Pré-écoute | Le périphérique de la [pré-écoute](#pré-écoute), `audio.preecoute`. |

Chaque liste propose les périphériques du poste ; un périphérique configuré mais débranché reste proposé, suivi de « (introuvable) ». Le périphérique choisi pour l'un est grisé dans l'autre : l'antenne et la pré-écoute n'utilisent jamais le même. **Machin lecture** prend le nouveau périphérique d'antenne à son prochain démarrage (**Diffusion → Redémarrer la diffusion**).

La même page règle le **seuil de blanc** ([#146](https://github.com/dascritch/machincast/issues/146)), `blancs.seuil`, de -100 à -0,1 dB, -40 dB par défaut : le niveau crête sous lequel le début et la fin d'un sonore sont un blanc ([Détection de blanc](#détection-de-blanc)). Un nouveau seuil vaut pour les audits complets suivants : les blancs déjà mesurés ne changent qu'au prochain audit.

**OK** les enregistre dans les sections `[crossfades]`, `[audio]`, `[blancs]` et `[interface]` du fichier de configuration, `machincast.toml`, qui garde ses commentaires et ses autres réglages ; la barre d'état le dit. Les fiches ouvertes ensuite les suivent ; **Machin lecture** prend les durées par défaut à son prochain démarrage. Un fichier qui ne peut pas être écrit laisse les préférences telles quelles, et la barre d'état dit pourquoi. **Annuler** ne change rien.

### Pré-écoute

Le bouton **Pré-écoute…** de la fiche d'un sonore, fichier ou stream, l'ouvre dans la **fenêtre de pré-écoute** ([#116](https://github.com/dascritch/machincast/issues/116), [#29](https://github.com/dascritch/machincast/issues/29)) : une fenêtre à part, qui reste ouverte quand on change d'onglet. Il n'y en a qu'une : pré-écouter un autre sonore le met à la place du précédent, à l'arrêt. **Affichage → Pré-écoute…** la ramène au premier plan, ou l'ouvre sans sonore. Fermer la fenêtre arrête la pré-écoute. Un nouveau stream se pré-écoute une fois enregistré.

- **Lecteur** : **⏵** lance la lecture, **⏸** la met en pause, **⏹** l'arrête et revient au début. Pendant la lecture d'un fichier, ou sa pause, la barre de position permet d'aller n'importe où, pour en vérifier la fin par exemple ; un stream n'a pas de position. À la fin du fichier, la pré-écoute revient à l'arrêt. Un fichier introuvable est signalé : « Lecture impossible : fichier introuvable, … ».
- **VU-mètre** : le même que celui de l'[Accueil](#vu-mètre-de-lantenne), couché : le niveau moyen de chaque canal, sa crête par-dessus et le trait de la plus haute crête, avec l'échelle en dB dessous, de -60 à gauche à 0 à droite.
- **Informations** : le format, le débit (celui annoncé par le fichier ou le flux, sinon une estimation « ≈ » d'après la taille du fichier), l'échantillonnage, les canaux et, pour un stream, les secondes **pré-décodées** : le son déjà reçu d'avance, sur 5 secondes au plus. Un flux qui en a peu risque de couper.
- **Sortie** : la pré-écoute joue sur le périphérique `audio.preecoute` de la configuration, **jamais sur celui de l'antenne**. La liste **Sortie** propose les périphériques du poste ; celui de la diffusion y est grisé, suivi de « (diffusion) » : il ne peut pas être choisi ; un périphérique configuré mais débranché reste proposé, suivi de « (introuvable) ». Choisir une autre sortie arrête la pré-écoute, et l'enregistre dans `machincast.toml`, qui garde ses commentaires.

**Écouter l'antenne** ([#24](https://github.com/dascritch/machincast/issues/24)) : un clic sur le VU-mètre de l'[Accueil](#vu-mètre-de-lantenne) charge l'antenne dans la pré-écoute, à la place du sonore précédent, et à l'arrêt : la fenêtre s'intitule « Pré-écoute : Antenne », et **⏵** fait entendre, sur le périphérique de pré-écoute, ce qui sort à l'antenne. Comme un stream, l'antenne n'a ni durée ni position. Avec PipeWire, **⏵** relie directement l'antenne au périphérique de pré-écoute, dans PipeWire : c'est le son même de l'antenne, sans décalage ni saccade, et **⏸** ou **⏹** défont ce lien. Il faut pour cela `pw-link`, du paquet `pipewire-bin` ([INSTALL.md](../INSTALL.md)) ; sans lui, la pré-écoute dit `Lecture impossible : pw-link introuvable ; installer pipewire-bin.`

### Calendrier

**Affichage → Calendrier** ouvre la grille dans un onglet ([#36](https://github.com/dascritch/machincast/issues/36), [#118](https://github.com/dascritch/machincast/issues/118)) : ce qui est prévu, et ce qui a été diffusé. Il s'ouvre sur la semaine du jour, du lundi au dimanche, de 0 h à 24 h ; une ligne rouge marque l'heure qu'il est.

- **Naviguer** : « Semaine précédente », « Aujourd'hui », « Semaine suivante », de 28 jours avant à 28 jours après aujourd'hui. « Jour » montre un seul jour, aujourd'hui s'il est dans la semaine montrée, et se pagine par jour ; « Semaine » revient à la semaine.
- **Ce qui est prévu** : chaque occurrence d'un événement est un bloc, à sa couleur de priorité, récurrences comprises. Le bloc est **plein** là où l'événement passerait à l'antenne, **estompé** là où un autre le masque : une priorité plus haute, ou, pour un fil musical permanent, n'importe quel autre fil musical. Deux blocs qui se chevauchent se placent côte à côte. Les fils musicaux permanents et les occurrences de 24 heures ou plus sont dans la **bande de la journée entière**, sous le nom du jour. Une émission ou un spécial **sans fin** se dessine jusqu'au début suivant d'une priorité égale ou plus haute, au plus tard jusqu'à minuit : sa durée réelle dépend de sa liste. Les événements de secours ne passent jamais par la grille, et n'y sont pas.
- **Ce qui a été diffusé** : à droite de chaque jour, sur fond plus clair pour le passé, une bande étroite par événement réellement joué : les passages successifs d'un même événement n'en font qu'une. Un écart entre le bloc et la bande montre un écart entre la grille et l'antenne.
- **Spécial, Émission, Fil musical** : chaque case montre ou cache les blocs et les bandes de sa priorité. Ce qui joue ne change pas : un bloc caché masque toujours ceux qu'il masquait.
- **Survoler** un bloc donne l'événement, son nom public, sa priorité, ses heures, sa récurrence et ce qui en joue ; une bande, ses heures à la seconde et son nombre de passages.
- **Double-cliquer** sur un bloc ou une bande ouvre la fiche de son événement.
- **Cliquer sur une heure libre**, pas encore passée, propose de créer un événement sur l'heure entière : un clic à 13:37 propose 13:00 – 14:00, par exemple « Créer un événement le dimanche 25 octobre 2026 de 13:00 à 14:00 ? ». **Créer** ouvre la fiche d'un nouvel événement, réglé sur cette heure ; rien n'est en base avant **Enregistrer**.

Le calendrier se relit à l'ouverture de son onglet, à chaque changement de semaine ou de jour, et par **Affichage → Rafraîchir les onglets** (<kbd>F5</kbd>).

### Rafraîchir les onglets

Ce que montre l'interface est lu en base à l'ouverture de chaque onglet ; ce qu'un autre poste, l'indexation ou la diffusion y changent ensuite n'apparaît pas tout seul. **Affichage → Rafraîchir les onglets**, ou <kbd>F5</kbd>, relit tout d'un coup ([#148](https://github.com/dascritch/machincast/issues/148)) :

- l'onglet ouvert, liste, incidents ou calendrier ; les autres listes se relisent déjà quand on les ouvre ;
- l'airplay de l'accueil ;
- toutes les fiches ouvertes. Une fiche modifiée demande d'abord quoi faire de ses modifications, comme à sa fermeture : **Enregistrer** les écrit puis relit la fiche, **Abandonner** les perd et relit la fiche, **Annuler** laisse la fiche telle quelle. Une fiche dont l'enregistrement est refusé reste aussi telle quelle, et dit pourquoi.
- La fiche d'un élément effacé de la base depuis un autre poste se ferme, sans question : ses modifications sont perdues.

La barre d'état le confirme (« Onglets rafraîchis. »), et nomme les fiches laissées telles quelles ou fermées.

### Piloter la diffusion depuis l'interface

Le menu **Diffusion** démarre, arrête et redémarre `Machin lecture`, sans terminal ([#25](https://github.com/dascritch/machincast/issues/25)). Ses entrées suivent l'état de la diffusion, relu à chaque ouverture du menu.

**Avec le service** de diffusion (`./install.sh --service`, [INSTALL.md](../INSTALL.md#service-de-diffusion)) :

| État du service | Entrées actives |
| --- | --- |
| Arrêté | Démarrer la diffusion |
| En marche | Arrêter la diffusion, Redémarrer la diffusion |
| En échec (il a planté trop souvent) | Démarrer la diffusion, Redémarrer la diffusion |

Chaque entrée demande le mot de passe, ou l'empreinte, d'un administrateur du poste : c'est la règle polkit du service, qui n'autorise rien d'autre. L'interface reste utilisable pendant la demande. La barre d'état dit ensuite ce qu'il en est : `Diffusion démarrée.`, `Diffusion arrêtée.`, `Diffusion redémarrée.`, ou l'échec avec la raison donnée par systemd, par exemple `Diffusion non démarrée : …` quand l'authentification est refusée ; la diffusion reste alors telle qu'elle était.

**Sans le service**, l'installation n'est pas définitive : la diffusion ne démarre pas avec le poste, et ne redémarre pas seule après un plantage. La barre d'état l'affiche en permanence, à droite : `Installation non définitive : diffusion sans service` ; son infobulle dit comment installer le service. Le menu pilote alors une **diffusion d'essai** : `Machin lecture` lancé à la main, qui joue bel et bien à l'antenne (rien à voir avec `Machin lecture --simulation`, qui ne joue rien, [Simuler la diffusion](#simuler-la-diffusion)).

| Entrée | Active | Ce qu'elle fait |
| --- | --- | --- |
| Démarrer la diffusion d'essai | Quand rien ne diffuse | Ouvre `Machin lecture` dans une fenêtre de terminal (konsole, sinon le terminal par défaut du poste, `x-terminal-emulator`), comme le lancerait le service : avec le `machincast.toml` du répertoire de MachinCast, donc sur le même périphérique d'antenne. Si l'interface a été lancée avec une autre configuration, la barre d'état le dit. La première ligne du terminal donne la sortie, le périphérique et la configuration de la diffusion. Fermer l'interface ne l'arrête pas. |
| Arrêter la diffusion d'essai | Quand une diffusion d'essai tourne | L'arrête comme <kbd>Ctrl</kbd> + <kbd>C</kbd> dans son terminal : le passage en cours se termine proprement. La barre d'état annonce `Arrêt de la diffusion d'essai demandé…`, puis `Diffusion d'essai arrêtée.` |
| Redémarrer la diffusion d'essai | Quand une diffusion d'essai tourne | L'arrête de même, puis la relance dans une nouvelle fenêtre de terminal. |

Une diffusion d'essai lancée depuis un terminal, sans passer par l'interface, se pilote de la même façon : l'interface reconnaît le `Machin lecture` qui lui répond sur la socket d'état. Sans terminal sur le poste, la barre d'état dit de lancer `Machin lecture` à la main.

### Lancer l'indexation depuis l'interface

Le menu **Maintenance** lance `Machin indexation` sans passer par un terminal ([#38](https://github.com/dascritch/machincast/issues/38)), par exemple après avoir déposé des fichiers dans le répertoire d'une banque :

- **Indexation rapide** : comme `Machin indexation` ; les nouveaux fichiers des banques sont enregistrés et vérifiés, ceux qui ont changé sont revérifiés, la présence des autres est contrôlée.
- **Audit complet** : comme `Machin indexation --audit-complet` ; tous les fichiers sont décodés de nouveau. Plus long, il repère aussi un fichier abîmé sans que sa date ni sa taille aient changé.

Voir [Indexation rapide et audit complet](#indexation-rapide-et-audit-complet) pour le détail des deux modes.

- **Dans son propre programme** ([#120](https://github.com/dascritch/machincast/issues/120)) : l'interface lance `Machin indexation --fenetre`, avec sa configuration, à part d'elle. L'interface reste utilisable, et **peut être fermée** : l'indexation continue, avec sa fenêtre. La barre d'état dit « Indexation rapide lancée, dans sa propre fenêtre. » ; tant que l'indexation tourne, le menu ne la propose plus. À sa fin, la barre d'état le dit : **Affichage → Rafraîchir les onglets** (<kbd>F5</kbd>) montre alors ses changements ([Rafraîchir les onglets](#rafraîchir-les-onglets)).
- **Sa fenêtre** montre, ligne par ligne et au fil de l'indexation, ce que `Machin indexation` écrirait dans le terminal ([Ce qu'affiche l'indexation](#ce-quaffiche-lindexation)) : chaque sonore indexé avec son statut, les anomalies, puis le bilan. Le texte se sélectionne et se copie. À la fin, elle conclut par le bilan, par exemple « Indexation rapide terminée : 2 nouveaux sonores, 0 rattachement ; 2 sonores vérifiés ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 2 sortis d'aperçu. », suivi du nombre d'anomalies s'il y en a.
- **Fermer sa fenêtre** pendant l'indexation demande s'il faut l'arrêter. **Arrêter** l'arrête après le fichier en cours : le travail fait est gardé, et la prochaine indexation reprendra le reste. **Continuer**, ou Échap, laisse la fenêtre ouverte et l'indexation continuer. Une fois l'indexation finie, **Fermer** la referme sans question.
- **Indexation impossible** : si un décodeur manque (un paquet GStreamer n'est pas installé, voir [INSTALL.md](../INSTALL.md)), si la base ne répond plus, ou si une autre indexation tourne déjà sur la base, la fenêtre le dit : « Indexation impossible : … ; les sonores déjà vérifiés le restent. ». Le travail fait jusque-là est gardé.

### Dupliquer un élément

Pour créer une variante d'un événement, d'une séquence ou d'une banque, **Dupliquer** en fait une copie ([#130](https://github.com/dascritch/machincast/issues/130)) : le bouton au pied de sa fiche, ou le clic droit sur sa ligne dans la liste. Le bouton n'est actif que pour un élément déjà enregistré, dont la fiche n'a pas de modification en cours : enregistrer ou annuler d'abord.

La copie s'ouvre dans un nouvel onglet, par exemple « Nouvelle séquence, copie de Passage pub ». **Rien n'est enregistré tant qu'on n'a pas cliqué sur Enregistrer** : fermer l'onglet propose d'enregistrer la copie ou de l'abandonner. Son nom interne est celui de l'original suivi de « (copie) », puis « (copie 2) », « (copie 3) »… si ce nom est déjà pris ; on le change avant d'enregistrer. **Annuler** revient à la copie telle qu'elle s'est ouverte.

| Copie d'une | Elle garde | Elle n'a pas |
| --- | --- | --- |
| Séquence | le nom public, le masquage et tous les éléments, dans l'ordre | — |
| Événement | la priorité, le nom public, le masquage et la liste de lecture | de dates ni de jours : choisir son créneau avant d'enregistrer. Une émission ou un spécial sans début ne s'enregistre pas, et deux événements de même priorité ne se chevauchent pas. |
| Banque | le nom public, le mode, le masquage, « ne pas répéter », les crossfades, les durées et les répertoires | de sonores : la prochaine indexation la remplit depuis ses répertoires. Sans répertoire, ajouter ses sonores à la main. |

L'original n'est jamais modifié. S'il est supprimé pendant que sa copie est ouverte, la copie reste telle quelle et s'enregistre normalement.

### Supprimer un élément

Chaque fiche a un bouton **Supprimer…** ([#33](https://github.com/dascritch/machincast/issues/33)). Il demande toujours confirmation : **Supprimer**, ou **Annuler** (Entrée et Échap annulent). La question dit où l'élément figure, et quelle banque, séquence ou liste d'événement n'aurait plus rien après son retrait. Une fiche pas encore enregistrée n'a rien à supprimer.

**Seule l'entrée en base est supprimée.** Les fichiers sonores et les répertoires des banques restent à leur place, intacts ([Les fichiers sonores ne sont jamais modifiés](#les-fichiers-sonores-ne-sont-jamais-modifiés)). L'élément est retiré des listes où il figure, et l'historique de diffusion garde ses passages, avec l'emplacement, l'artiste et le titre du moment.

| Élément supprimé | Retiré de | Ce qui reste |
| --- | --- | --- |
| Sonore | ses banques, séquences et listes d'événements | Son fichier. S'il est dans un répertoire de banque, la prochaine indexation l'enregistre de nouveau, comme un nouveau sonore : la question le rappelle. |
| Banque | ses séquences et listes d'événements | Ses répertoires et leurs fichiers ; ses sonores, en base. |
| Séquence | ses listes d'événements | Ses sonores et ses banques, en base. |
| Événement | — | Ses sonores, banques et séquences, en base. Les streams qui l'avaient pour secours n'en ont plus. |
| Marque-page | — | Rien : un marque-page qu'un stream suit ne se supprime pas. La fiche nomme les streams, qui doivent d'abord choisir une autre adresse. |

La fiche se ferme après la suppression, sans demander quoi faire de ses modifications. Si la base est injoignable, rien n'est supprimé : la fiche affiche « Suppression impossible : » et l'erreur de PostgreSQL.

## Suivre le journal : Machin logs

`Machin logs` suit en direct le journal du service de diffusion, `machincast.service`. Les options qui suivent sont transmises à `journalctl`, par exemple :

```bash
Machin logs --since "1 hour ago" --priority=warning
```

Lire ce journal demande d'appartenir au groupe `systemd-journal`, ce que fait `install.sh`, effectif après le redémarrage du poste. Tant que le service de diffusion n'est pas installé ([#22](https://github.com/dascritch/machincast/issues/22), [Service de diffusion](../INSTALL.md#service-de-diffusion)), le journal est vide : `Machin lecture`, lancé à la main, écrit dans son terminal. `Ctrl-C` arrête le suivi.

## Messages et codes de sortie

Chaque message commence par le nom du programme, par exemple `Machin_indexation :`. Les informations, comme le bilan d'une indexation, vont sur la sortie standard ; les anomalies et les erreurs, sur la sortie d'erreur. Un script peut ainsi garder les unes et les autres séparément.

| Code | Signification |
| --- | --- |
| 0 | Le programme est allé au bout. Pour l'indexation, même si des sonores ont changé d'état : ce sont des anomalies, pas des erreurs. |
| 1 | Base de données injoignable ou perdue (pour `Machin interface`, au lancement), décodeur GStreamer manquant, autre indexation en cours sur la base, `Machin indexation --fenetre` sans affichage graphique, sortie audio indisponible, autre `Machin lecture` déjà en diffusion, ou fonction pas encore écrite. |
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
| Prolonger un stream dont le direct déborde | [#47](https://github.com/dascritch/machincast/issues/47) |
| Autres écrans de l'interface : recherche globale, simulation | [#27](https://github.com/dascritch/machincast/issues/27), [#37](https://github.com/dascritch/machincast/issues/37) |
| Raccourci de bureau et icône de l'interface | [#62](https://github.com/dascritch/machincast/issues/62) |
