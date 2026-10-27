# Diffusion : Machin lecture

[Guide d'administration](README.md) › Diffusion

- [Ce que fait Machin lecture](#ce-que-fait-machin-lecture)
- [Lancer et arrêter la diffusion](#lancer-et-arrêter-la-diffusion)
- [Simuler la diffusion](#simuler-la-diffusion)
- [État de la diffusion pour l'interface](#état-de-la-diffusion-pour-linterface)
- [Sortie audio](#sortie-audio)
- [Historique de diffusion et log](#historique-de-diffusion-et-log)

## Ce que fait Machin lecture

`Machin lecture` diffuse la grille sur la sortie audio de la configuration, en continu, jusqu'à ce qu'on l'arrête ([#88](https://github.com/dascritch/machincast/issues/88)), fichiers et streams. Il sait aussi simuler une période à l'avance, sans son ni écriture en base (voir [Simuler la diffusion](#simuler-la-diffusion)). Sur un ordinateur dédié à l'antenne, il tourne comme service, `machincast.service` ([INSTALL.md](../../INSTALL.md#service-de-diffusion)), que l'interface démarre, arrête et redémarre ([Piloter la diffusion depuis l'interface](../utilisateur/antenne.md#piloter-la-diffusion)).

## Lancer et arrêter la diffusion

```bash
Machin lecture                   # avec le machincast.toml du répertoire de MachinCast
Machin lecture --config <fichier>
```

- **Base** : `Machin lecture` diffuse la grille de la base de production (`base.production`), avec le rôle `machincast_lecture`. Si la base est injoignable, il s'arrête aussitôt avec le code 1 et le message `base de données injoignable`.
- **Sortie** : il joue sur la sortie de `audio.sortie`, sur le périphérique de l'antenne, `audio.peripherique`. Sans ce périphérique, il refuse de diffuser avec le code 2 et le message `périphérique de l'antenne non renseigné` : le périphérique par défaut pourrait être celui de la pré-écoute. Il se règle dans `machincast.toml` ou dans les [préférences](../utilisateur/prise-en-main.md#préférences) de l'interface ([#116](https://github.com/dascritch/machincast/issues/116)) ; seule la sortie `factice` des essais s'en passe. Si la sortie ne peut pas être créée, il s'arrête avec le code 1 et le message `sortie audio indisponible`.
- **En marche** : il affiche la sortie utilisée, note `démarrage` dans le log, puis enchaîne les sonores sans intervention. Chaque passage est écrit dans l'airplay au moment où il commence et où il finit.
- **Arrêt** : `Ctrl-C` dans le terminal, ou le signal `SIGTERM` (arrêt d'un service). Le sonore en cours s'arrête, son passage est terminé dans l'airplay, sans incident, `arrêt` est noté dans le log, et le programme s'arrête avec le code 0.
- **Perte de la base en cours de diffusion** : la sortie se coupe, et le programme s'arrête avec le code 1 et le message `erreur de base de données`.
- **Un seul `Machin lecture` à la fois** : deux diffusions en même temps joueraient chacune leurs sonores et écriraient chacune leur airplay. Un second `Machin lecture` lancé sur la même socket d'état est refusé : il s'arrête avec le code 1 et le message `diffusion refusée : … un autre Machin lecture diffuse déjà`.

## Simuler la diffusion

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
| `--repertoire REPERTOIRE` | Répertoire où écrire les fichiers produits ([#37](https://github.com/dascritch/machincast/issues/37)). Par défaut, celui de `sorties.csv` de la configuration. L'écran de simulation de l'interface s'en sert pour son répertoire temporaire. |

- **Rien n'est écrit en base**, au sens strict : la simulation lit la base de production dans une transaction en lecture seule, où PostgreSQL refuse toute écriture. Elle part de l'état réel, c'est-à-dire la position dans chaque liste, le cycle de chaque banque aléatoire et le nombre de lectures de chaque sonore, puis tient ses propres passages en mémoire. Un sonore qui atteindrait son maximum de lectures pendant la simulation est noté expiré dans la simulation seulement.
- **Aucun son n'est joué**, et la sortie audio n'est pas ouverte : une simulation peut tourner pendant la diffusion, sur le même poste. Elle ne dure que quelques secondes pour une journée.
- **Durées** : ce sont celles de la base, mesurées par l'indexation. Un stream n'est pas contacté : la simulation suppose qu'il tient jusqu'à la fin de son événement.
- **Mêmes règles que la diffusion** : priorités, coupures nettes, crossfades, fichiers disparus (incident `fichier introuvable`), silences (alerte `silence`).
- **Résultat** : trois fichiers dans le dossier des sorties (celui de `sorties.csv`, ou celui de `--repertoire`), pour toute la période :
  - un CSV, avec les mêmes colonnes que l'airplay CSV ;
  - une playlist `.pls` ;
  - une page HTML, avec la liste des alertes et incidents simulés puis le tableau des passages.

  L'artiste et le titre y sont masqués comme sur la page publique (voir [Sorties de la diffusion](configuration.md#sorties-de-la-diffusion)), et l'emplacement de chaque fichier, donné partout, permet de vérifier ce qui sera joué. Un fichier du même nom est remplacé.
- **Messages** : les alertes et incidents simulés s'affichent aussi au fil de l'eau sur la sortie d'erreur, datés et préfixés de `simulation :`. Le bilan, avec le nombre de passages, d'alertes et d'incidents et les chemins des fichiers, s'affiche à la fin.
- **Codes de sortie** : 0 une fois la simulation finie, même avec des alertes ; 1 si la base est injoignable ou si les fichiers ne peuvent pas être écrits ; 2 pour une période ou un nom invalides, ou pour `--graine`, `--nom` ou `--repertoire` sans `--simulation`.

## État de la diffusion pour l'interface

`Machin lecture` publie son état sur une socket Unix, que l'interface lit pour afficher ce qui passe à l'antenne ([#20](https://github.com/dascritch/machincast/issues/20)) :

- **Emplacement** : `lecture.socket_etat` dans la configuration, ou par défaut `lecture.sock` dans le dossier `machincast` du répertoire d'exécution du compte (`$XDG_RUNTIME_DIR`, en général `/run/user/1000`). Seul le compte qui diffuse peut la lire. Elle disparaît à l'arrêt de la diffusion et au redémarrage du poste.
- **Contenu** : l'état de marche (diffusion, silence ou arrêt), le sonore en cours (emplacement, début, durée, fin prévue, progression), le prochain sonore (emplacement, début et fin prévus, durée, s'il est sain), et les 5 sonores à venir après lui, avec les mêmes informations ([#228](https://github.com/dascritch/machincast/issues/228)). Pour un stream, la durée est inconnue ; sa fin prévue est celle de son événement, où il s'éteint, et le prochain sonore est celui qui reprendra l'antenne à ce moment-là ([#242](https://github.com/dascritch/machincast/issues/242)). Le format est décrit champ par champ dans la [spécification, § 5.4](../spec.md#54-socket-détat).
- **Le prochain sonore annoncé est celui qui passera** : il est choisi dès le début du sonore en cours, même tiré au hasard dans une banque. Il ne change que si un événement coupe la diffusion, si son événement est fini, ou s'il est désactivé ou expiré entre-temps.
- **Les sonores à venir aussi** ([#228](https://github.com/dascritch/machincast/issues/228)) : chacun est choisi à l'heure où il serait demandé, coupures par les événements comprises, et ils passeront dans cet ordre. À chaque changement de sonore, la liste avance d'un cran, et `Machin lecture` prévoit le cinquième. Sur un imprévu (interruption depuis l'interface, coupure qui n'était pas prévue, grille modifiée, stream tombé, sonore qui n'est plus jouable), elle est recalculée en entier. La prévision n'écrit rien, ni dans l'airplay, ni dans le log.
- **Sain** : un fichier présent, lisible, à l'état `actif`, dont la dernière lecture s'est terminée sans incident. Un stream n'est pas testé : son état sain est inconnu.
- **Demandes** : dans l'autre sens, l'interface y envoie ses demandes d'interruption ([Interrompre l'antenne](../utilisateur/antenne.md#interrompre-lantenne), [#104](https://github.com/dascritch/machincast/issues/104)).
- Pour voir l'état à la main : `socat - UNIX-CONNECT:"${XDG_RUNTIME_DIR}/machincast/lecture.sock"` (paquet `socat`), une ligne JSON par changement ; `Ctrl-C` pour quitter.

Une socket impossible à créer (dossier sans droit d'écriture, par exemple) est signalée dans le log par l'alerte `socket d'état indisponible` : la diffusion continue sans elle.

La diffusion suit les règles ci-dessous.

## Sortie audio

La sortie audio de l'antenne se règle dans la configuration (`audio.sortie` : `pipewire`, `pulseaudio`, `alsa`, ou `factice` pour un essai sans son), et `install.sh` vérifie qu'elle peut être créée. Les sonores s'y enchaînent ainsi ([#15](https://github.com/dascritch/machincast/issues/15)) :

- **Crossfade de début** d'un sonore : il monte progressivement, de silencieux à plein volume, pendant ce temps.
- **Crossfade de fin** d'un sonore : le sonore suivant démarre autant avant la fin, et celui-ci s'éteint progressivement pendant ce temps. Les deux se superposent.
- **Les deux crossfades sont nécessaires** : deux sonores ne se superposent que si le premier a un crossfade de fin **et** le second un crossfade de début. Si l'un des deux est à 0, le premier joue jusqu'au bout à plein volume, puis le second démarre aussitôt à plein volume, sans fondu.
- **D'où viennent les crossfades** ([#145](https://github.com/dascritch/machincast/issues/145)) : ceux qu'impose la banque qui a fourni le sonore ; sinon ceux de la fiche du sonore, s'ils y sont paramétrés (0 seconde en est un) ; sinon ceux que la banque applique à défaut ; sinon ceux des [préférences](../utilisateur/prise-en-main.md#préférences), section `[crossfades]` du `machincast.toml` ; sinon aucun. Pour un sonore joué sans ses blancs, leur position autour du début et de la fin détectés vient des clés `position_entree` et `position_sortie` de la même section, quelle que soit la banque ([#234](https://github.com/dascritch/machincast/issues/234)).
- **Coupure nette** : au début d'un événement, le sonore en cours s'arrête aussitôt, sans fondu.
- **Avant de jouer un fichier**, sa date de modification et sa taille sont comparées à celles de l'indexation. Un écart est noté dans le log en alerte `fichier modifié`, et le fichier est quand même joué ; la prochaine indexation, même rapide, le revérifie et met la base à jour. Un fichier disparu n'est pas joué : l'incident `fichier introuvable` est noté dans le log, et la diffusion passe aussitôt au sonore suivant. Le sonore n'est plus proposé pendant une heure, pour ne pas noter le même incident à chaque tour de liste ; la prochaine indexation le passera à l'état `supprimé`.
- **Analyse au dernier moment** ([#181](https://github.com/dascritch/machincast/issues/181)) : pendant chaque sonore, si le **prochain** est un fichier jamais vérifié en entier, ou dont le fichier a changé depuis sa vérification, `Machin lecture` lance `Machin indexation --audit-complet --sonore N` sur lui seul, en arrière-plan, sans fenêtre ; ses lignes s'ajoutent au journal de `Machin lecture`. La diffusion ne l'attend pas : si l'analyse plante, ou n'a pas fini, le sonore est joué à son heure. Elle est notée dans le log, en info `analyse du prochain sonore`. Un même sonore n'est pas redemandé avant une heure ; un stream n'est jamais analysé.
- **Superposition** : pendant un crossfade, deux sonores jouent en même temps. PipeWire et PulseAudio les mélangent toujours. En `alsa`, il faut un périphérique qui mélange, comme `default` ; un périphérique matériel direct (`hw:…`) ne joue qu'un son à la fois.

## Historique de diffusion et log

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
| `interruption manuelle` | info | Depuis l'interface, le sonore en cours a été sauté, la séquence en cours sautée, ou l'événement en cours coupé par le fil musical ([Interrompre l'antenne](../utilisateur/antenne.md#interrompre-lantenne)) ; le message dit lequel, par exemple `du sonore « Café à minuit »`. Le sonore coupé s'éteint pendant le crossfade de fin par défaut de la configuration, ou net sans lui. |
| `silence` | alerte | Rien à diffuser. |
| `analyse du prochain sonore` | info | Le prochain sonore n'a pas été vérifié en entier, ou son fichier a changé : `Machin indexation` l'analyse en arrière-plan ([Sortie audio](#sortie-audio)). |
| `analyse impossible` | alerte | `Machin indexation` n'a pas pu être lancé pour le prochain sonore ; le message donne l'erreur. Le sonore est joué quand même. |
| `fichier modifié` | alerte | Le fichier a changé depuis l'indexation ; il est quand même joué. |
| `fichier introuvable` | incident | Le fichier a disparu ; il n'est pas joué. |
| `lecture interrompue` | incident | La lecture d'un fichier s'est arrêtée sur une erreur, dont le message est noté. |
| `lecture bloquée` | incident | Le lecteur d'un fichier n'a rien joué 3 secondes après son démarrage ; le sonore suivant est joué ([#281](https://github.com/dascritch/machincast/issues/281)). Constaté sur des AIFF avec l'ancien lecteur, `playbin`, de GStreamer 1.24 et 1.28 ; le lecteur actuel, `playbin3`, ne s'est jamais bloqué dans les mesures ([#284](https://github.com/dascritch/machincast/issues/284)). Fortuit : le sonore rejoue normalement ensuite. |
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
