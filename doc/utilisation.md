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

`Machin lecture` diffuse la grille sur la sortie audio de la configuration, en continu, jusqu'à ce qu'on l'arrête ([#88](https://github.com/dascritch/machincast/issues/88)), fichiers et streams. Le service systemd et le mode simulation sont à venir (voir [Ce qui n'existe pas encore](#ce-qui-nexiste-pas-encore)).

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
- **Un seul `Machin lecture` à la fois** : deux diffusions en même temps joueraient chacune leurs sonores et écriraient chacune leur airplay.

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

Un **événement de secours** est un événement de priorité `secours` : il n'a ni début, ni fin, ni jours de récurrence, et ne passe jamais à l'antenne par la grille, seulement à la place d'un stream tombé. Chaque stream désigne le sien, ou aucun (`secours_evenement_id` du sonore). Tant que l'interface ne permet pas de les saisir ([#30](https://github.com/dascritch/machincast/issues/30), [#32](https://github.com/dascritch/machincast/issues/32)), ils s'enregistrent directement en base.

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
| `reconnexion abandonnée` | info | L'événement d'un stream tombé n'est plus à l'antenne : plus de tentative de reconnexion. |

L'airplay et le log ne sont jamais modifiés ni effacés par le binaire lecture : il ne peut qu'y ajouter des lignes.

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
| 1 | Base de données injoignable ou perdue, décodeur GStreamer manquant, sortie audio indisponible, ou fonction pas encore écrite. |
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
| Prolonger un stream dont le direct déborde | [#47](https://github.com/dascritch/machincast/issues/47) |
| Désactivations automatiques des sonores (maximum de lectures, fin de période) | [#18](https://github.com/dascritch/machincast/issues/18) |
| Masquage des métadonnées et sorties de l'airplay (CSV, .pls, HTML) | [#19](https://github.com/dascritch/machincast/issues/19) |
| État de la diffusion pour l'interface | [#20](https://github.com/dascritch/machincast/issues/20) |
| Mode simulation de la diffusion | [#21](https://github.com/dascritch/machincast/issues/21) |
| Service systemd de diffusion | [#22](https://github.com/dascritch/machincast/issues/22) |
| Interface graphique | [#23](https://github.com/dascritch/machincast/issues/23) et suivants |
| Outils du poste de développement | [#77](https://github.com/dascritch/machincast/issues/77) |
