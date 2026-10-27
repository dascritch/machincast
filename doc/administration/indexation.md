# Indexation : Machin indexation

[Guide d'administration](README.md) › Indexation

- [Ce que fait Machin indexation](#ce-que-fait-machin-indexation)
- [Alimenter une banque](#alimenter-une-banque)
- [Indexation rapide et audit complet](#indexation-rapide-et-audit-complet)
- [Verdicts de la vérification d'un fichier](#verdicts-de-la-vérification-dun-fichier)
- [États d'un sonore](#états-dun-sonore)
- [Tags et métadonnées](#tags-et-métadonnées)
- [Détection de blanc](#détection-de-blanc)
- [Ce qu'affiche l'indexation](#ce-quaffiche-lindexation)

## Ce que fait Machin indexation

`Machin indexation` fait deux choses, dans cet ordre :

1. il enregistre les fichiers déposés dans les répertoires des banques, et les range dans leur banque ;
2. il vérifie que les fichiers des sonores sont présents et sains, met à jour leur durée et leurs tags, et change leur état si besoin.

Il ne modifie jamais les fichiers sonores eux-mêmes, et ne supprime jamais un sonore de la base.

Il se lance depuis un terminal, ou depuis le menu **Maintenance** de l'interface ([Lancer l'indexation depuis l'interface](../utilisateur/sonores.md#indexation-depuis-linterface)), qui fait exactement le même travail.

## Alimenter une banque

Alimenter une banque se limite à déposer des fichiers dans l'un de ses répertoires, puis à lancer `Machin indexation` ([#9](https://github.com/dascritch/machincast/issues/9)). Les répertoires d'une banque se choisissent dans [sa fiche](../utilisateur/sonores.md#fiche-dune-banque), dans l'interface ([#31](https://github.com/dascritch/machincast/issues/31)) ; une banque peut en avoir plusieurs, et un même répertoire peut alimenter plusieurs banques.

- **Sous-répertoires** : ils sont tous parcourus, dans l'ordre de leur nom. Un lien symbolique vers un autre répertoire n'est pas suivi, pour éviter les boucles ; le répertoire d'une banque peut, lui, être un lien.
- **Formats** : `.mp3`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.wav`, `.aiff` et `.aif`, que l'extension soit écrite en minuscules ou en majuscules. Les autres fichiers (pochettes, textes, vidéos `.mp4`…) sont ignorés.
- **Fichiers cachés** : un fichier ou un répertoire dont le nom commence par un point est ignoré, comme les fichiers `._*.mp3` qu'écrit macOS sur un disque partagé.
- **Nouveau fichier** : il devient un sonore à l'état `aperçu`, ajouté **en fin de liste** de la banque, puis décodé dans la même indexation. Les fichiers d'un même passage sont ajoutés dans l'ordre de leur chemin.
- **Fichier déjà connu** : il n'est jamais enregistré deux fois, même trouvé par plusieurs banques. Il est ajouté en fin de liste de chaque banque dont il n'est pas encore membre.
- **Sonore retiré à la main d'une banque** : tant que son fichier reste dans l'un des répertoires de la banque, l'indexation suivante l'y **réintègre**, en fin de liste. Pour l'en retirer durablement, il faut déplacer le fichier hors de ses répertoires. La [fiche de la banque](../utilisateur/sonores.md#fiche-dune-banque) le rappelle au retrait.
- **Durées de la banque** ([#195](https://github.com/dascritch/machincast/issues/195)) : une banque qui a une durée minimale ou maximale ([fiche de la banque](../utilisateur/sonores.md#fiche-dune-banque)) ne garde que les sonores dans ses durées, bornes comprises.
  - Un sonore déjà connu, de durée connue, hors de ses durées, n'y est pas ajouté, même si son fichier est dans l'un de ses répertoires.
  - Un nouveau fichier, ou un sonore de durée encore inconnue, n'y entre qu'une fois décodé, à la fin de l'indexation, et seulement s'il est dans ses durées ([#210](https://github.com/dascritch/machincast/issues/210)). Sinon, il n'y passe jamais : ni ligne, ni rattachement, ni retrait au bilan. Un même répertoire peut donc alimenter une banque de jingles courts et une banque de titres longs sans que chaque fichier soit annoncé comme retiré de l'autre. Si l'indexation est arrêtée avant de le décoder, sa durée reste inconnue et il y entre.
  - **Chaque indexation**, rapide ou complète, retire de la banque les sonores qui y étaient déjà, de durée connue, qui sortent de ses durées, **même ajoutés à la main** : des durées resserrées s'appliquent dès l'indexation suivante. `Machin indexation --sonore N` le fait pour ce seul sonore. Une indexation arrêtée ne retire rien, ni la vérification des fichiers ajoutés depuis l'interface.
  - La durée comparée est la durée complète du fichier, même saisie à la main dans la fiche du sonore, jamais celle sans ses blancs. Un sonore de durée inconnue, comme un stream, n'est jamais retiré.
  - Un sonore retiré reste en base, dans ses autres banques, séquences et événements, et son fichier n'est pas touché. Chaque retrait a sa ligne ([Ce qu'affiche l'indexation](#ce-quaffiche-lindexation)).
  - Une fiche de la banque ouverte pendant l'indexation remet le sonore à l'enregistrement ; l'indexation suivante le retire de nouveau.
- **Répertoire introuvable** : il est signalé sur la sortie d'erreur, avec le nom de la banque, et les autres banques sont indexées normalement. Un sous-répertoire illisible est signalé de la même façon.
- **Fichier déplacé** : à son nouvel emplacement, c'est un nouveau sonore ; l'ancien passe à l'état `supprimé`.

## Indexation rapide et audit complet

| Commande | Ce qui est vérifié |
| --- | --- |
| `Machin indexation` | **Indexation rapide**, par défaut. Sont décodés, et leurs tags lus, les sonores à l'état `aperçu`, c'est-à-dire nouvellement trouvés, et ceux dont le fichier a changé depuis sa dernière vérification : sa date de modification ou sa taille diffère ([#10](https://github.com/dascritch/machincast/issues/10)). Une émission pré-enregistrée remplacée sous le même nom, par exemple synchronisée depuis un autre poste, est ainsi revérifiée : nouvelle durée, nouveaux tags, sauf les champs saisis à la main. Pour les autres, seule la présence du fichier est contrôlée : un fichier disparu est quand même repéré, et son sonore passe `supprimé`. Un fichier déplacé est enregistré comme un nouveau sonore, à son nouvel emplacement, s'il est dans le répertoire d'une banque. |
| `Machin indexation --audit-complet` | **Audit complet** : les sonores de type fichier sont décodés en entier. C'est lui, et lui seul, qui mesure les blancs au début et à la fin de chaque fichier ([Détection de blanc](#détection-de-blanc)). Il ne décode pas un sonore **déjà audité au même seuil de blanc, dont le fichier n'a pas changé depuis** ([#206](https://github.com/dascritch/machincast/issues/206)) : une ligne compte ceux-là, `120 sonores déjà audités au seuil de -40 dB, aux fichiers inchangés : non décodés ; --forcer décode tous les sonores`. Il reste donc court sur une grosse discothèque, et refait tout après un changement du seuil de blanc. À lancer après la première indexation, puis de temps en temps. |
| `Machin indexation --audit-complet --forcer` | **Audit complet forcé** : tous les sonores de type fichier sont décodés, même déjà audités et inchangés. C'est lui qui repère un fichier abîmé après son audit sans que sa date ni sa taille aient changé, une corruption du disque par exemple. `--forcer` sans `--audit-complet` est refusé avec le code 2. |
| Audit demandé depuis l'interface | **Quelques sonores en entier**, sans auditer toute la discothèque ([#114](https://github.com/dascritch/machincast/issues/114)) : le clic droit dans les listes Sonores ou Banques marque les sonores choisis, et la **prochaine indexation, même rapide**, les décode en entier et mesure leurs blancs, puis efface la marque ; un sonore déjà audité au même seuil, au fichier inchangé, n'est pas redécodé ([#206](https://github.com/dascritch/machincast/issues/206)) ([Agir sur plusieurs sonores ou banques](../utilisateur/listes.md#agir-sur-plusieurs-sonores-ou-banques)). |
| `Machin indexation --audit-complet --sonore N` | **Un seul sonore**, le numéro N, décodé en entier ([#181](https://github.com/dascritch/machincast/issues/181)) : ni parcours des répertoires, ni document d'audit ; ses anomalies s'affichent sur la sortie d'erreur. Il peut tourner pendant une autre indexation. Un sonore inconnu, ou un stream, est refusé avec le code 1. C'est ainsi que `Machin lecture` fait vérifier, au dernier moment, le sonore qu'il va jouer ([Diffusion : Machin lecture](diffusion.md#ce-que-fait-machin-lecture)). Sans `--audit-complet`, le sonore n'est décodé que s'il est en aperçu ou si son fichier a changé ; avec, que s'il n'a pas déjà été audité au même seuil, au fichier inchangé, sauf avec `--forcer`. |
| `Machin indexation --fenetre` | La même indexation, rapide ou complète (avec `--audit-complet`), qui montre son journal dans une fenêtre au lieu du terminal : c'est ainsi que l'interface la lance ([Lancer l'indexation depuis l'interface](../utilisateur/sonores.md#indexation-depuis-linterface)). Il faut un affichage graphique. |

**Une seule indexation à la fois** sur une base (sauf `--sonore`, qui ne vérifie qu'un sonore), qu'elle soit lancée d'un terminal, de l'interface ou d'un autre poste : une deuxième s'arrête aussitôt, sans rien toucher, avec le message `indexation refusée : une autre indexation est en cours sur cette base` et le code 1. Elle pourra être relancée une fois la première finie.

Le décodage est fait sans jouer le son, bien plus vite que le temps réel : une dizaine de minutes de son en moins d'une seconde. Un audit complet d'une grande discothèque peut tout de même prendre du temps.

Les streams ne sont jamais vérifiés.

## Verdicts de la vérification d'un fichier

Avant de le décoder, l'indexeur lit le **type réel** du fichier dans ses premiers octets, avec libmagic, sans se fier à son extension ([#121](https://github.com/dascritch/machincast/issues/121)). Ce type est enregistré en base, par exemple `audio/mpeg`, `audio/flac`, ou `video/mp4` pour un `.m4a`. Un type qui n'est pas du son (texte, image, PDF…) donne aussitôt le verdict `non supporté`, sans décodage. Un type que libmagic ne reconnaît pas, comme un fichier vide, laisse le décodage trancher.

Chaque fichier examiné reçoit l'un de ces verdicts :

| Verdict | Signification |
| --- | --- |
| `sain` | Le fichier se décode entièrement. Sa durée décodée, sa date de modification et sa taille sont enregistrées. |
| `endommagé` | Le fichier se décode, mais des données manquent : rupture de continuité dans le son, ou durée décodée plus courte que celle annoncée par l'en-tête du fichier (fichier tronqué, trames perdues). |
| `non supporté` | Le type du fichier n'est pas sonore, quelle que soit son extension : un texte ou une image renommés en `.mp3`, par exemple. Le fichier n'est pas décodé, et le problème donne son type (« de type text/plain, ce n'est pas un fichier sonore »). |
| `illisible` | Le fichier n'est pas du son, il est vide ou son conteneur est cassé, aucun son n'a pu être décodé, ou le décodage ne progresse plus pendant 30 secondes (disque ou partage réseau bloqué). |
| `introuvable` | Aucun fichier à l'emplacement enregistré : il a été supprimé ou déplacé. |

Un décodage qui ne produit aucun son en 2,5 secondes est repris depuis le début, jusqu'à six fois : un disque réseau en veille a ainsi 15 secondes pour répondre, et un fichier AIFF, dont GStreamer bloque parfois le démarrage, n'est pas déclaré illisible à tort ([#280](https://github.com/dascritch/machincast/issues/280)).

Jusqu'à la correction de [#149](https://github.com/dascritch/machincast/issues/149), une indexation de plus de quelques centaines de fichiers épuisait les descripteurs de fichier du système : la console répétait des messages `GStreamer-CRITICAL` (`gst_bus_timed_pop_filtered`, `gst_poll_get_read_gpollfd`), et les fichiers suivants, même sains, étaient déclarés `illisible` (« décodage bloqué au démarrage »). Après la mise à jour, un **audit complet** les décode de nouveau : les sonores sains passés `erroné` redeviennent `actif`, et le bilan les compte parmi les rétablis. Ces messages ne doivent plus apparaître ; s'ils reviennent, c'est à signaler dans un ticket.

Quelques défauts échappent à la vérification : des octets altérés dans un WAV ou un AIFF, qui n'ont ni somme de contrôle ni trames ; un WAV, un Ogg, un MP3 sans durée dans son en-tête ou un AAC brut (`.aac`), tronqué, qui se décode comme un fichier plus court mais sain.

## États d'un sonore

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

## Tags et métadonnées

Pour un fichier `sain`, l'indexeur lit les tags du fichier pendant le décodage, et les nettoie comme les textes saisis dans l'interface ([#108](https://github.com/dascritch/machincast/issues/108), [Interface graphique](commandes.md#interface-graphique--machin-interface)) : ID3 (MP3, et AIFF quand il en porte), commentaires Vorbis (Ogg, FLAC), atomes MP4 (M4A) et chunk INFO (WAV, qui ne porte que l'artiste, le titre, l'album, le genre et l'année).

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

Les champs suivent les tags du fichier : un tag retiré du fichier vide le champ au passage suivant. **Un champ modifié à la main dans l'interface n'est plus jamais écrasé** par l'indexeur ([Fiche d'un sonore](../utilisateur/sonores.md#fiche-dun-sonore)). Les tags d'un fichier défectueux ne sont pas lus, et les valeurs en base restent telles quelles.

## Détection de blanc

Un fichier peut commencer ou finir par un blanc : un silence, un souffle, une fin de réverbération. Pour ne pas les entendre à l'antenne, la diffusion peut jouer un sonore sans eux ([#146](https://github.com/dascritch/machincast/issues/146)). **Le fichier n'est jamais modifié** : seules les durées de ses blancs sont notées en base ([Les fichiers sonores ne sont jamais modifiés](configuration.md#les-fichiers-sonores-ne-sont-jamais-modifiés)).

- **Mesure** : l'[audit complet](#indexation-rapide-et-audit-complet), `Machin indexation --audit-complet`, mesure le niveau crête de chaque tranche de 10 ms de chaque fichier sain, sur son canal le plus fort. Le **début détecté** est le blanc avant la première tranche qui atteint le seuil ; la **fin détectée**, le blanc après la dernière, compté depuis la fin du fichier. L'analyse au dernier moment de `Machin lecture` est un audit complet : elle les mesure aussi. L'indexation rapide ne les mesure pas.
- **Seuil** : `blancs.seuil` dans `machincast.toml`, réglable dans les [préférences](../utilisateur/prise-en-main.md#préférences), page « Audio » : de -100 dB compris à 0 dB exclu, -40 dB par défaut, 0 dB étant la pleine échelle. Un fichier qui n'atteint jamais le seuil n'a aucun blanc détecté, et il est joué en entier.
- **Quand la détection s'applique** : jamais par défaut. Un sonore est joué sans ses blancs si sa [fiche](../utilisateur/sonores.md#fiche-dun-sonore) l'active, ou si la [banque](../utilisateur/sonores.md#fiche-dune-banque) qui l'a fourni l'active. Un sonore placé directement dans un événement ou une séquence suit donc son propre réglage. Les streams ne sont jamais concernés.
- **Jeu** : ses [crossfades](diffusion.md#sortie-audio) se placent autour de son début et de sa fin détectés ([#234](https://github.com/dascritch/machincast/issues/234)) : par défaut, le fade-in se termine au début détecté, et le fade-out commence à la fin détectée ; « commence », « est en cours » ou « se termine » se règlent dans les [préférences](../utilisateur/prise-en-main.md#préférences) (`crossfades.position_entree`, `crossfades.position_sortie`), pour tous les sonores. La lecture s'étend dans les blancs d'autant que les fondus y débordent, sans jamais sortir du fichier. Sa durée à l'antenne est celle de cette partie jouée. L'heure estimée du prochain sonore, l'airplay et la [simulation](diffusion.md#simuler-la-diffusion) suivent ces durées.
- **Sans blanc détecté** : un côté sans blanc détecté n'est pas rogné. Un sonore jamais audité, par exemple ajouté par une indexation rapide, est donc joué en entier, même si la détection s'applique : lancer un audit complet après avoir ajouté des sonores ou activé la détection. Des blancs qui, ensemble, ne laisseraient rien du sonore sont ignorés.
- **Correction à la main** : le début et la fin détectés se corrigent dans la fiche du sonore ; l'audit complet ne les modifie plus ensuite.
- **Ce qui n'en tient pas compte** : les durées minimale et maximale d'une banque ([#147](https://github.com/dascritch/machincast/issues/147)) se comparent à la durée complète du fichier.

## Ce qu'affiche l'indexation

Une ligne par sonore indexé, au fil de l'indexation ([#120](https://github.com/dascritch/machincast/issues/120)), avec le chemin du fichier et son statut. Sur la sortie standard, les fichiers trouvés dans les répertoires des banques, puis chaque fichier décodé sain, avec le nom du sonore quand ses tags en donnent un, et ce que devient son état, puis les nouveaux fichiers de durée encore inconnue, une fois décodés, dans les seules banques dont ils respectent les durées, ou seuls s'ils n'en respectent aucune ([#210](https://github.com/dascritch/machincast/issues/210)), puis chaque sonore déjà membre d'une banque, retiré parce qu'il sort de ses durées ([#195](https://github.com/dascritch/machincast/issues/195)) :

```text
2026-10-15T08:15:00+02:00 /musique/jingles/intro.flac : nouveau sonore, ajouté à la banque Jingles
2026-10-15T08:15:00+02:00 /musique/titres/cafe.flac : rattaché à la banque Nuit
2026-10-15T08:15:00+02:00 /musique/jingles/intro.flac : sain, Radio Machin – Générique ; sonore passé actif
2026-10-15T08:15:00+02:00 /musique/titres/cafe.flac : sain, Les Gaufres – Café à minuit ; état actif conservé
2026-10-15T08:15:00+02:00 /musique/titres/aube.flac : sain, Aube – Matin clair ; sonore passé actif
2026-10-15T08:15:00+02:00 /musique/titres/aube.flac : nouveau sonore, ajouté à la banque Nuit
2026-10-15T08:15:00+02:00 /musique/titres/mix.flac : retiré de la banque Nuit, durée 1:02:05 plus longue que son maximum, 8:00
```

En indexation rapide, un sonore qui n'est ni nouveau ni en aperçu n'est pas décodé, et n'a donc pas de ligne, sauf si son fichier a disparu. Sur la sortie d'erreur, une ligne par fichier défectueux, avec le problème et sa conséquence :

```text
2026-10-15T08:15:00+02:00 /musique/jingles/intro.mp3 : endommagé : 2 rupture(s) de continuité au décodage, des données ont été perdues ; sonore passé erroné
2026-10-15T08:15:00+02:00 /musique/fond/nappe.flac : introuvable : aucun fichier à cet emplacement ; état désactivé conservé
```

Puis le bilan, sur la sortie standard :

```text
2026-10-15T08:15:00+02:00 indexation rapide : 3 nouveaux sonores, 1 rattachement, 0 retrait ; 3 sonores vérifiés ; 1 erroné, 0 non supporté, 1 supprimé, 0 rétabli, 3 sortis d'aperçu
```

Les nouveaux sonores sont les fichiers enregistrés pour la première fois ; les rattachements, les sonores déjà connus ajoutés à une banque dont ils n'étaient pas membres ; les retraits, les sonores déjà membres d'une banque, retirés parce qu'ils sortent de ses durées ([Alimenter une banque](#alimenter-une-banque)). Les sonores vérifiés sont ceux qui ont été décodés ; les autres nombres comptent les changements d'état.

Enfin, le chemin du **document d'audit** du passage ([#11](https://github.com/dascritch/machincast/issues/11)) :

```text
2026-10-15T08:15:00+02:00 document d'audit : /tmp/machincast-audit-2026-10-15T08:15:00.csv, /tmp/machincast-audit-2026-10-15T08:15:00.html
```

Chaque indexation, rapide ou complète, lancée d'un terminal ou de l'interface, écrit ce document dans `/tmp`, en deux formats : un `.csv` pour un tableur (séparé par des points-virgules) et un `.html` pour un navigateur. Il est nommé avec la date et l'heure locale de son lancement. Il ne liste que les **anomalies**, une ligne par fichier défectueux : date du passage, chemin du fichier, verdict (`endommagé`, `illisible`, `introuvable`), problème et conséquence pour le sonore. Les opérations normales n'y figurent pas. La dernière ligne du CSV, de verdict `bilan`, porte le bilan du passage ; sans anomalie, c'est la seule. Les répertoires de banque introuvables restent sur la sortie d'erreur. Le document n'est pas écrit quand l'indexation s'interrompt (décodeur manquant, base perdue, autre indexation en cours). S'il ne peut pas être écrit, l'indexation le signale sur la sortie d'erreur et va quand même au bout. `/tmp` se vide au redémarrage de la machine : copier ailleurs les documents à garder.

Si GStreamer n'a pas de décodeur pour un format, la vérification s'arrête et nomme les paquets à installer, sans changer l'état des sonores : le fichier n'y est pour rien.
