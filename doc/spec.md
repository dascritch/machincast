# MachinCast — Spécification fonctionnelle

Version révisée du 14 octobre 2026, issue de la revue de la spécification initiale.

MachinCast est un système automatisé de diffusion sonore pour radio. Il fournit un fil antenne diffusable en dehors des émissions en direct, à partir de banques de sonores et d'événements horaires. Il fonctionne sous Linux (Ubuntu LTS).

## Sommaire

1. [Vocabulaire](#1-vocabulaire)
2. [Composants](#2-composants)
3. [Base de données](#3-base-de-données)
4. [Règles d'ordonnancement](#4-règles-dordonnancement)
5. [Binaire lecture](#5-binaire-lecture)
6. [Binaire indexation](#6-binaire-indexation)
7. [Wrapper Machin](#7-wrapper-machin)
8. [Interface graphique](#8-interface-graphique)
9. [Configuration](#9-configuration)
10. [Installation et déploiement](#10-installation-et-déploiement)
11. [Développements ultérieurs](#11-développements-ultérieurs)
12. [Points à confirmer](#12-points-à-confirmer)

---

## 1. Vocabulaire

| Terme | Sens |
| --- | --- |
| **Sonore** | Un fichier audio ou un stream. Unité de base de la diffusion. |
| **Banque** | Un ensemble ordonné de sonores, alimenté par un ou plusieurs répertoires indexés et/ou à la main. Quand une banque est jouée, un seul de ses sonores est tiré. |
| **Événement** | Une plage horaire, éventuellement récurrente, avec une priorité et une liste de lecture de banques, de sonores et/ou de séquences. |
| **Séquence** | Une suite ordonnée de sonores et/ou de banques, réutilisable dans un ou plusieurs événements, par exemple un passage publicitaire ([#99](https://github.com/dascritch/machincast/issues/99)). Elle se joue en entier, dans l'ordre, comme un seul sonore. |
| **Fil musical** | Priorité la plus basse. Le fil musical tourne quand aucun événement de priorité supérieure n'est actif. |
| **Airplay** | L'historique de ce qui a effectivement été diffusé. |
| **Playlist** | Uniquement la liste générée à la volée par le binaire lecture et exportée en .pls, .csv ou .html. **La playlist n'existe pas en base.** Dans les écrans et les menus, on parle de « banque », jamais de « playlist ». |
| **Marque-page** | Une URL de stream enregistrée pour être réutilisée par plusieurs sonores. |

## 2. Composants

| Composant | Exécutable | Rôle |
| --- | --- | --- |
| Wrapper | `Machin` | Point d'entrée unique en ligne de commande pour tous les binaires, et suivi des logs du service. |
| Binaire lecture | `Machin_lecture` | Joue les événements, écrit l'airplay et le log. Tourne comme service systemd. |
| Binaire indexation | `Machin_indexation` | Vérifie les sonores et indexe les répertoires des banques. |
| Interface graphique | `Machin_interface` | Supervision, édition, simulation, pilotage du service. |

Tous les exécutables commencent par `Machin_`. Les binaires sans interface graphique se lancent par convention via `Machin` (voir [§ 7](#7-wrapper-machin)) : ce n'est pas une contrainte technique, mais une façon de n'avoir qu'une commande à retenir.

### Communication entre composants

- **Base de données** : PostgreSQL, accédée par socket Unix locale.
- **État du binaire lecture** (en marche, sonore en cours, progression, prochain sonore) : socket Unix exposée par `Machin_lecture`, lue par l'interface.
- **Niveaux du VU-mètre** : port de monitoring de la sortie audio (PulseAudio ou PipeWire). Avec la sortie ALSA, qui n'en expose pas, le VU-mètre ne fonctionne pas. C'est accepté.
- **Pilotage du service** : systemd, via une règle polkit (voir [§ 10](#10-installation-et-déploiement)).

## 3. Base de données

Deux bases à la structure strictement identique : la base de production et la base de test, utilisée notamment pour le TDD. Le schéma est géré par migrations **yoyo-migrations**, appliquées aux deux bases.

### 3.1 Tables

#### `sonores`

| Champ | Description |
| --- | --- |
| `id` | Identifiant. |
| `type` | `fichier` ou `stream`. |
| `emplacement` | Chemin du fichier. Clé unique pour les fichiers. Vide pour un stream. |
| `url_stream` | URL directe d'un stream à usage unique (par exemple avec un SESSIONID dans l'URL). |
| `marque_page_id` | Référence à un marque-page de stream. |
| `secours_evenement_id` | Stream seulement : événement de priorité `secours` qui joue à la place du stream quand son flux tombe. Vide = l'événement de priorité inférieure (fil musical). Voir [§ 4.7](#47-streams). |
| `artiste`, `titre` | Métadonnées publiques, pré-remplies depuis les tags à l'indexation. Ce sont des colonnes, car elles servent au masquage, à la recherche et à l'airplay. |
| `metadonnees_musicales` | Objet JSON des métadonnées non critiques, pré-remplies depuis les tags ([#8](https://github.com/dascritch/machincast/issues/8)) : `annee`, `album`, `artiste_album`, `genre`, `compositeur`, `label`, `piste`. Extensible sans migration : les autres clés ne sont jamais touchées par l'indexeur. |
| `crossfade_debut`, `crossfade_fin` | Temps de crossfade en début et en fin de sonore. Facultatifs ([#145](https://github.com/dascritch/machincast/issues/145), migration `0007.sonores-crossfades-facultatifs`) : `NULL` n'est pas paramétré, et 0 seconde est un crossfade paramétré. La migration a rendu non paramétrés les 0 seconde que personne n'avait saisis (absents de `champs_edites`). |
| `max_lectures` | Nombre maximum de lectures sur la totalité de l'historique. Vide = illimité. |
| `etat` | État du sonore ([#66](https://github.com/dascritch/machincast/issues/66), [#69](https://github.com/dascritch/machincast/issues/69)) : `apercu`, `actif`, `desactive`, `expire`, `errone`, `non_supporte` ([#121](https://github.com/dascritch/machincast/issues/121), migration 0003) ou `supprime` (voir ci-dessous). Seul un sonore `actif` peut être joué. |
| `type_mime` | Type MIME du fichier, lu par libmagic au dernier examen de l'indexeur ([#121](https://github.com/dascritch/machincast/issues/121)) ; NULL avant, et pour un stream. |
| `masquer_metadonnees` | Masquage de l'artiste et du titre au niveau du sonore. Vide = hérite du niveau inférieur. |
| `duree` | Calculée par l'indexeur. Vide pour un stream. |
| `debut_diffusion`, `fin_diffusion` | Période de diffusion facultative (annonces limitées dans le temps). |
| `fichier_modifie_le`, `fichier_taille` | Date de modification et taille du fichier au dernier passage de l'indexeur, pour détecter un changement de contenu. |
| `verifie_le` | Date de la dernière vérification complète du fichier par l'indexeur, type lu puis décodage, en indexation rapide comme en audit complet ([#125](https://github.com/dascritch/machincast/issues/125)) ; NULL avant. Un fichier introuvable la garde. |
| `champs_edites` | Liste des champs saisis à la main dans l'interface : nom de colonne (`artiste`, `titre`, `duree`…), ou `metadonnees_musicales.<clé>` pour une clé des métadonnées musicales (`metadonnees_musicales.annee`). L'indexeur ne les modifie plus jamais. |
| `indexe_le` | Date de la première indexation. |
| `modifie_le` | Horodatage de la dernière modification en base. |

États d'un sonore ([#66](https://github.com/dascritch/machincast/issues/66)) :

| État | Affiché | Posé par | Sens | Retour à `actif` |
| --- | --- | --- | --- | --- |
| `apercu` | aperçu | indexeur, interface | nouveau fichier, enregistré sans être décodé ([#69](https://github.com/dascritch/machincast/issues/69)) ; pas jouable | par l'indexeur, au premier décodage d'un fichier sain |
| `actif` | actif | interface, indexeur | jouable, sous réserve de sa période de diffusion et de son maximum de lectures | — |
| `desactive` | désactivé | interface | choix humain | par l'interface seulement |
| `expire` | expiré | binaire lecture | maximum de lectures atteint ou fin de la période de diffusion ([§ 4.5](#45-sonore-jouable)) | par l'interface seulement |
| `errone` | erroné | indexeur | fichier illisible ou endommagé | automatique, par l'indexeur, quand le fichier redevient sain |
| `supprime` | supprimé | indexeur | fichier introuvable (supprimé ou déplacé) | par l'interface seulement ; un fichier déplacé est réindexé comme nouveau sonore |

**Le fichier d'un sonore n'est jamais supprimé, renommé, déplacé, remplacé ni écrit par MachinCast** ([#96](https://github.com/dascritch/machincast/issues/96)), quels que soient les changements de son entrée : état, emplacement, tags, ou suppression de la ligne. L'état `supprime` constate qu'un fichier a disparu, il ne le fait pas disparaître. Aucune sortie (CSV, .pls, HTML, socket d'état, fichiers de simulation) ne peut être placée sur un chemin à l'extension d'un fichier sonore.

L'indexeur ne change l'état que d'un sonore `apercu`, `actif` ou `errone`. Un fichier ajouté à la main depuis l'interface commence aussi à l'état `apercu` ; un stream, jamais vérifié, commence à l'état `actif`. Un sonore `desactive`, `expire` ou `supprime` garde son état, même si son fichier est défectueux ; l'anomalie est quand même signalée.

Contraintes :

- `type = fichier` ⇒ `emplacement` renseigné, `url_stream` et `marque_page_id` vides.
- `type = stream` ⇒ exactement un de `url_stream` ou `marque_page_id` renseigné.
- `secours_evenement_id` ⇒ `type = stream`, et l'événement désigné est de priorité `secours` (déclencheur en base, qui empêche aussi de changer la priorité d'un événement de secours désigné). Supprimer l'événement vide le champ.

Pas de champ format ni fréquence d'échantillonnage : l'échantillonnage peut varier dans un fichier lossy et n'a pas d'utilité en lossless.

#### `marques_pages_streams`

| Champ | Description |
| --- | --- |
| `id`, `nom`, `url` | Une URL de stream réutilisable, souvent fonctionnelle par intermittence. |

#### `banques`

| Champ | Description |
| --- | --- |
| `id`, `nom_interne` | Identification. |
| `nom_public` | Affiché à la place de l'artiste et du titre masqués, après ceux de l'événement et de la séquence ([§ 4.8](#48-métadonnées-publiques-et-masquage), [#99](https://github.com/dascritch/machincast/issues/99)). Vide = aucun. |
| `mode` | `sequentiel` ou `aleatoire`. |
| `masquer_metadonnees` | Masquage au niveau de la banque. Vide = hérite. |
| `ne_pas_repeter` | La banque ne peut pas passer deux fois de suite, même d'un événement à l'autre (voir [§ 4.4](#44-choix-dun-sonore-dans-une-banque), [#63](https://github.com/dascritch/machincast/issues/63)). Faux par défaut. |
| `crossfade_debut_regle`, `crossfade_debut`, `crossfade_fin_regle`, `crossfade_fin` | Crossfades des sonores joués via la banque, chaque côté avec sa règle (type `regle_crossfade`) : `sonore` garde celui du sonore (par défaut), `a_defaut` donne celui de la banque au sonore qui n'en a pas (0 seconde), `impose` le donne à tout sonore ([#143](https://github.com/dascritch/machincast/issues/143), migration `0005.banques-crossfades`). |
| `duree_min`, `duree_max` | Durées minimale et maximale, facultatives (`NULL`), des sonores de la banque : strictement positives, la minimale au plus égale à la maximale. Un sonore qui en sort n'est que signalé par l'interface ; la diffusion n'en tient pas compte ([#147](https://github.com/dascritch/machincast/issues/147), migration `0006.banques-durees`). |
| `modifie_le` | Horodatage de la dernière modification. |

#### `banques_repertoires`

| Champ | Description |
| --- | --- |
| `banque_id`, `repertoire` | Répertoires indexés d'une banque. Une banque peut en avoir plusieurs (par exemple « Habillages Noël » = répertoires hors saison, hiver et Noël), et un même répertoire peut alimenter plusieurs banques. |

#### `banques_sonores` (many-to-many)

| Champ | Description |
| --- | --- |
| `banque_id`, `sonore_id` | Liaison. Un sonore peut appartenir à plusieurs banques. |
| `position` | Ordre dans la banque, réordonnable par glisser-déposer. Un sonore ajouté par l'indexeur se place en fin de liste. |

Un sonore présent dans plusieurs banques est autorisé. Il sera signalé ultérieurement comme anomalie non bloquante.

Un sonore situé hors des répertoires d'une banque peut y être ajouté à la main.

#### `evenements`

| Champ | Description |
| --- | --- |
| `id`, `nom_interne`, `nom_public` | Identification. Le nom interne est unique (migration `0002.evenements-nom-unique`, [#32](https://github.com/dascritch/machincast/issues/32)). |
| `priorite` | `fil_musical` < `emission` < `special`, plus `secours`, hors grille ([#16](https://github.com/dascritch/machincast/issues/16)) : un événement de secours ne passe jamais à l'antenne par la grille, seulement à la place d'un stream tombé ([§ 4.7](#47-streams)). |
| `debut`, `fin` | Date et heure de début et de fin de la première occurrence. Voir les règles ci-dessous. |
| `jours_recurrence` | Jours de la semaine où l'événement se répète, nommés de `lundi` à `dimanche` (plusieurs jours possibles). Vide = pas de récurrence. Tous les jours cochés = quotidien. |
| `masquer_metadonnees` | Masquage au niveau de l'événement. Vide = hérite. |
| `modifie_le` | Horodatage de la dernière modification, utilisé pour départager deux événements en conflit. |

Règles sur les dates :

- Seuls les événements de priorité `fil_musical` peuvent avoir un `debut` vide. Un fil musical sans `debut` ni `fin` est permanent.
- Un événement de priorité `secours` n'a ni `debut`, ni `fin`, ni `jours_recurrence`. Sa liste boucle, comme celle d'un fil musical.
- Les priorités `emission` et `special` peuvent avoir une `fin` vide. Leur liste de lecture ne boucle alors pas : l'événement se termine quand sa liste est épuisée.
- Un événement peut passer minuit.
- Pas de date de fin de récurrence, pas d'exceptions (jours fériés).

#### `evenements_elements`

| Champ | Description |
| --- | --- |
| `evenement_id`, `position` | Liste ordonnée, réordonnable par glisser-déposer. |
| `banque_id`, `sonore_id`, `sequence_id` | Exactement un des trois est renseigné. |

Un même élément peut apparaître plusieurs fois dans la liste (par exemple un jingle entre chaque titre).

#### `sequences`

Suites de sonores et de banques réutilisables dans les événements ([#99](https://github.com/dascritch/machincast/issues/99)).

| Champ | Description |
| --- | --- |
| `id`, `nom_interne`, `nom_public` | Identification. Le nom public s'affiche à la place de l'artiste et du titre masqués, après celui de l'événement ([§ 4.8](#48-métadonnées-publiques-et-masquage)). |
| `masquer_metadonnees` | Masquage au niveau de la séquence. Vide = hérite. |
| `modifie_le` | Horodatage de la dernière modification. |

#### `sequences_elements`

| Champ | Description |
| --- | --- |
| `sequence_id`, `position` | Liste ordonnée, réordonnable par glisser-déposer, éventuellement vide : une séquence vide s'enregistre, pour être complétée plus tard, et la diffusion la saute ([#138](https://github.com/dascritch/machincast/issues/138)). |
| `banque_id`, `sonore_id` | Exactement un des deux est renseigné. Une séquence ne contient jamais une autre séquence, pour écarter tout appel cyclique ; l'imbrication est un [développement ultérieur](#11-développements-ultérieurs). |

Comme dans un événement, un même élément peut apparaître plusieurs fois (par exemple deux appels à la banque de publicités).

#### `airplay`

L'historique de diffusion. Les lignes ne sont **jamais supprimées**, même quand le sonore, la banque ou l'événement l'est.

| Champ | Description |
| --- | --- |
| `id`, `passage_id` | Une ligne au début et une ligne à la fin de chaque passage, reliées par `passage_id`. |
| `type_ligne` | `debut` ou `fin`. |
| `horodatage` | Heure de début ou de fin. |
| `sonore_id`, `banque_id`, `evenement_id` | Références facultatives. `banque_id` est indispensable au cycle aléatoire propre à chaque banque. |
| `element_id` | Élément de la liste de l'événement qui a fait jouer le passage ([#14](https://github.com/dascritch/machincast/issues/14)) : un même élément peut figurer plusieurs fois dans une liste, seul lui dit où la reprendre. Vide si l'élément est supprimé. |
| `sequence_id`, `sequence_element_id` | Pour un sonore joué par une séquence : la séquence et son élément, qui dit où la reprendre ([#99](https://github.com/dascritch/machincast/issues/99)). Vides si la séquence ou l'élément est supprimé. |
| `emplacement`, `artiste`, `titre` | Recopiés au moment du passage, pour garder l'historique après suppression. |
| `duree_diffusee` | Sur la ligne de fin : durée effectivement diffusée. |
| `sans_incident` | Sur la ligne de fin : la lecture s'est-elle déroulée sans incident. |

#### `log`

Journal de toutes les opérations du binaire lecture, normales comme incidents.

| Champ | Description |
| --- | --- |
| `id`, `horodatage` | |
| `niveau` | `info`, `alerte` ou `incident`. |
| `nature` | Nature de l'opération ou de l'incident. |
| `message` | Détail. |
| `sonore_id`, `banque_id`, `evenement_id` | Références facultatives, renseignées quand elles sont disponibles. |

L'indexeur n'écrit pas dans le log : ses incidents ne figurent donc pas dans l'écran des incidents.

#### Choix de modélisation

Le schéma, les rôles et les droits sont créés par la migration `src/machincast/migrations/0001.schema-initial.sql`, fusion des migrations écrites avant toute mise en production ([PR #70](https://github.com/dascritch/machincast/pull/70), [PR #90](https://github.com/dascritch/machincast/pull/90), [PR #100](https://github.com/dascritch/machincast/pull/100), cette dernière pour la banque « ne pas répéter », les séquences et le nom public des banques). Les migrations suivantes s'ajoutent sans fusion : `0002.evenements-nom-unique` rend unique le nom interne d'un événement ([#32](https://github.com/dascritch/machincast/issues/32)).

- Durées (`duree`, crossfades, `duree_diffusee`) : type `interval`. Dates : `timestamptz`.
- Textes saisis à la main (noms internes et publics, artiste, titre, nature d'une entrée du log) : `varchar(255)`, la même limite que l'interface. Chemins, URL et messages détaillés : `text`, sans limite fixée à l'avance.
- Valeurs énumérées : types `ENUM` PostgreSQL (`type_sonore`, `mode_banque`, `priorite_evenement`, `jour_semaine`, `type_ligne_airplay`, `niveau_log`, `etat_sonore`). Ajouter une valeur se fait par `ALTER TYPE … ADD VALUE` dans une nouvelle migration ; en retirer une demande de recréer le type. Leur ordre de déclaration permet les comparaisons : `fil_musical < emission < special`, `lundi < … < dimanche`.
- `jours_recurrence` : tableau de `jour_semaine`. La récurrence est calculée en heure locale par le binaire lecture.
- `metadonnees_musicales` : objet JSON (`jsonb`), jamais un tableau ni une valeur nulle.
- Un événement ne peut pas avoir de fin sans début.
- Positions dans `banques_sonores`, `evenements_elements` et `sequences_elements` : uniques par banque, par événement ou par séquence, vérifiées en fin de transaction pour permettre de réordonner.
- Suppressions : un lien de banque, un élément d'événement ou un élément de séquence disparaît avec la banque, le sonore, la séquence ou l'événement qu'il référence ; `airplay` et `log` gardent leurs lignes, avec la référence passée à vide. Un marque-page utilisé par un sonore ne peut pas être supprimé. La validation préalable des suppressions est faite par l'interface ([§ 8.9](#89-suppression)).
- Pour un stream, la colonne `emplacement` de `airplay` recopie l'URL diffusée.
- `modifie_le` est mis à jour par un déclencheur à chaque modification de `sonores`, `banques`, `evenements` et `sequences`.

### 3.2 Rôles et droits

Un rôle PostgreSQL par binaire : `machincast_lecture`, `machincast_indexation`, `machincast_interface`. Ils sont créés par la migration `0001.schema-initial` ([#4](https://github.com/dascritch/machincast/issues/4)) et partagés par la base de production et la base de test.

- Ce sont des **rôles de groupe**, sans connexion. Un utilisateur système se connecte avec son propre rôle, par authentification **peer** sur la socket Unix.
- L'utilisateur est membre des rôles qu'il peut endosser, **sans en hériter les droits** : connecté, il n'a accès à rien. Chaque binaire endosse son rôle par `SET ROLE` dès la connexion (`machincast.base.connecter`). L'indexation lancée depuis l'interface, sous l'utilisateur de bureau, agit donc avec les seuls droits de l'indexation.
- Un administrateur autorise un compte en tant qu'utilisateur `postgres` : `GRANT machincast_lecture, machincast_indexation, machincast_interface TO <compte> WITH INHERIT FALSE, SET TRUE` ; `install.sh` le fait pour le compte qui installe ([#40](https://github.com/dascritch/machincast/issues/40)).
- Le respect des droits est en plus vérifié dans le code source.
- PostgreSQL 16 ou plus récent est requis (options `INHERIT` et `SET` des appartenances).

| Table | Lecture (`Machin_lecture`) | Indexation (`Machin_indexation`) | Interface (`Machin_interface`) |
| --- | --- | --- | --- |
| `sonores` | lire ; modifier la seule colonne `etat` | lire, insérer, modifier | lire, insérer, modifier, supprimer |
| `marques_pages_streams` | lire | — | lire, insérer, modifier, supprimer |
| `banques` | lire | lire | lire, insérer, modifier, supprimer |
| `banques_repertoires` | — | lire | lire, insérer, modifier, supprimer |
| `banques_sonores` | lire | lire, insérer | lire, insérer, modifier, supprimer |
| `evenements` | lire | — | lire, insérer, modifier, supprimer |
| `evenements_elements` | lire | — | lire, insérer, modifier, supprimer |
| `sequences` | lire | — | lire, insérer, modifier, supprimer |
| `sequences_elements` | lire | — | lire, insérer, modifier, supprimer |
| `airplay` | lire, insérer | — | lire |
| `log` | insérer (sans `RETURNING`) | — | lire |

L'indexation ne supprime rien : un fichier disparu fait passer son sonore à l'état `supprime`. Quand l'interface supprime un élément, les références dans `airplay` et `log` passent à vide avec les droits du propriétaire des tables ; l'interface n'a pas besoin de droit d'écriture sur ces deux tables.

## 4. Règles d'ordonnancement

### 4.1 Choix de l'événement actif

1. À tout instant, l'événement actif est celui de plus haute priorité dont la plage couvre l'instant, sauf s'il s'est terminé plus tôt pour cette occurrence (liste épuisée d'un événement sans fin, ou banque « ne pas répéter » sans autre élément jouable, voir [§ 4.4](#44-choix-dun-sonore-dans-une-banque)).
2. Deux événements de même priorité ne doivent pas se chevaucher : l'interface l'interdit à la saisie (`machincast.lecture.grille.chevauchement`, [#32](https://github.com/dascritch/machincast/issues/32)). Deux occurrences se chevauchent si elles ont un instant commun ; une occurrence sans fin ne compte que par son début ; un fil musical permanent et un événement de secours ne chevauchent rien. À priorité égale, une occurrence sans fin, ou un fil musical permanent, laisse la place à toute occurrence qui a commencé après elle, et reprend ensuite : un fil permanent sert de fond. Si deux occurrences bornées se chevauchent quand même, le binaire joue le **dernier modifié en base**.
3. Plusieurs fils musicaux peuvent coexister selon l'heure (nuit, jour), régis par leur récurrence.
4. Le changement d'heure ne fait l'objet d'aucune règle particulière : la diffusion est toujours en fil musical à cette heure de la nuit.
5. Occurrences ([#12](https://github.com/dascritch/machincast/issues/12), `machincast.lecture.grille`) : `debut` et `fin` sont ceux de la première occurrence. Sans récurrence, l'événement couvre `[debut, fin[`, ou `[debut, ∞[` sans fin. Avec récurrence, il revient chaque jour coché à partir du jour de `debut`, à l'heure murale de `debut`, jusqu'à l'heure murale de `fin` autant de jours plus tard que la première occurrence : un événement peut passer minuit, et c'est le jour de son début qui compte. Le poste travaille en heure locale, celle de Paris : le calcul se fait en heure murale, et un événement garde son heure au changement d'heure. Une occurrence sans fin couvre l'instant jusqu'à ce que sa liste soit épuisée ; le binaire la déclare alors terminée, et la suivante repart normalement.

### 4.2 Transitions

- **Début d'un événement** : il coupe **net** le sonore en cours, quel que soit le sonore.
- **Fin d'un événement** : si aucun autre événement ne suit, le dernier sonore est joué jusqu'au bout, puis le suivant est choisi selon les règles du fil musical actif. Si un autre événement suit immédiatement, son début coupe net le dernier sonore.
- **Retour au fil musical** : il reprend à l'élément qui suit le dernier joué, d'après la table `airplay` (`element_id`), d'une occurrence à l'autre.
- **Séquence** ([#99](https://github.com/dascritch/machincast/issues/99)) : pour les transitions, une séquence est traitée comme un seul sonore. À la fin d'un événement sans successeur immédiat, elle est jouée jusqu'au bout, au nom de son événement. Un événement qui commence coupe net le sonore en cours de la séquence, et la séquence avec lui : ses éléments restants ne sont pas joués. Après une séquence, jouée en entier ou coupée, la liste reprend à l'élément qui suit la séquence. Une séquence ne reprend que si le dernier passage de tout l'airplay vient d'elle, ce qui vaut aussi après un redémarrage. Pendant la suspension d'un stream tombé de la séquence, son secours joue comme ailleurs ([§ 4.7](#47-streams)).
- **Rien à diffuser** : silence, et une alerte `silence` dans le log, une seule fois par silence. Le silence cesse dès qu'un sonore redevient jouable ou qu'un autre événement commence.
- L'ordonnanceur (`machincast.lecture.deroule`, [#14](https://github.com/dascritch/machincast/issues/14)) décide à chaque instant : continuer, couper net, jouer un sonore ou se taire. Un événement coupe le sonore en cours s'il a commencé après le début de ce sonore ; sinon le sonore va jusqu'au bout.

### 4.3 Liste de lecture d'un événement

- Les éléments sont joués dans l'ordre de `position`.
- Un élément banque fait jouer **un seul** sonore de cette banque.
- Un élément séquence ([#99](https://github.com/dascritch/machincast/issues/99)) joue les éléments de la séquence dans l'ordre de leur `position`, chaque banque faisant jouer un seul sonore. Un élément non jouable de la séquence est ignoré ; une séquence dont rien n'est jouable est sautée, comme une banque vide. Sa position se lit dans `airplay.sequence_element_id`.
- Si la liste est terminée avant la fin de l'événement, elle reprend au début (boucle).
- Un événement `emission` ou `special` sans date de fin ne boucle pas : il se termine à la fin de sa liste.
- Un élément qui ne donne rien (banque sans sonore jouable, sonore non jouable) est sauté. Une émission ou un spécial dont plus rien n'est jouable se termine pour cette occurrence ; pour un fil musical, silence et alerte.
- Une émission ou un spécial reprend sa liste au début à chaque occurrence : seuls comptent les passages de l'occurrence en cours.

### 4.4 Choix d'un sonore dans une banque

- **Séquentiel** : le sonore qui suit, dans l'ordre de `position`, le dernier joué via cette banque.
- **Aléatoire contrôlé** : un sonore joué via cette banque n'est plus rejouable tant que tous les autres sonores de la banque n'ont pas été joués. Chaque banque a son propre cycle. Au début d'un nouveau cycle, le dernier sonore joué est écarté, pour ne pas passer deux fois de suite (sauf s'il est seul jouable). Un sonore ajouté à la banque entre dans le cycle en cours.
- Le choix ne garde aucun état en mémoire : ordre séquentiel et cycles se déduisent des passages de l'`airplay` fournis par la banque (`banque_id`), seuls à compter ([#13](https://github.com/dascritch/machincast/issues/13), `machincast.lecture.banques`). Un redémarrage du binaire ne perturbe donc rien.
- Seuls les sonores **jouables** sont candidats (voir ci-dessous). Si aucun ne l'est, on passe à l'élément suivant de l'événement, comme si la banque était vide.
- **Ne pas répéter** ([#63](https://github.com/dascritch/machincast/issues/63)) : si le dernier passage de l'`airplay` a été joué via une banque marquée `ne_pas_repeter`, l'élément qui rappelle cette banque est sauté, et on passe à l'élément suivant, comme si la banque était vide. Un événement à l'autre, la règle s'applique de la même façon : la banque en fin d'un événement puis au début du suivant ne passe pas deux fois. Il en va de même dans une séquence, et de l'événement à la séquence ([#99](https://github.com/dascritch/machincast/issues/99)) : un appel à la banque qui vient de passer est sauté, et on passe au sonore suivant de la séquence. Seuls comptent les passages joués via la banque, comme pour le cycle aléatoire : un sonore de la banque placé directement comme élément d'un événement ne compte pas.
	- Si, une fois la banque sautée, plus rien n'est jouable dans la liste de l'événement, cet événement se termine pour cette occurrence : l'événement de priorité inférieure dont la plage couvre l'instant prend le relais. Pour un fil musical, silence et alerte, comme quand rien n'est jouable.
	- Log : `info` `élément sauté` pour chaque élément sauté, une fois par élément et par passage ; `alerte` `événement terminé plus tôt` pour un événement terminé à cause du saut. La décision se prend quand le sonore suivant est réservé, dès le début du sonore en cours ([§ 5.4](#54-socket-détat)).
	- Le mode simulation applique la même règle, à partir de l'airplay puis des passages simulés ([§ 5.5](#55-mode-simulation)).
	- Schéma : colonne `banques.ne_pas_repeter`, dans la migration `0001.schema-initial`.

### 4.5 Sonore jouable

Un sonore est jouable s'il est à l'état `actif` (jamais en `apercu`, tant que son fichier n'a pas été décodé), si l'instant est dans sa période de diffusion (quand elle est renseignée), et si son maximum de lectures n'est pas atteint.

Passages automatiques à l'état `expire` par le binaire lecture, chacun consigné dans le log (`sonore expiré`, info, avec la cause) ([#18](https://github.com/dascritch/machincast/issues/18), `machincast.lecture.expiration`) :

- maximum de lectures atteint (compté sur la totalité de l'historique `airplay`, lignes de début) : vérifié à chaque passage qui commence ;
- date de fin de diffusion atteinte (la période s'entend fin exclue) : tous les sonores sont vérifiés au démarrage du binaire, puis chaque minute.

Seul un sonore `actif` expire, et seule sa colonne `etat` change. Un état unique couvre les deux causes : l'interface retrouve la cause en comparant `max_lectures` au nombre de passages, ou `fin_diffusion` à l'heure courante.

### 4.6 Sonore « sain »

Indicateur affiché pour le prochain sonore : fichier présent, actif, lisible, dernière lecture sans incident. Un stream n'est pas testé automatiquement ; l'interface permet de le tester à la demande.

### 4.7 Streams

Décidé avec le ticket [#16](https://github.com/dascritch/machincast/issues/16) (`machincast.lecture.diffusion`, `machincast.lecture.deroule`) :

- Adresse : `url_stream`, ou l'`url` du marque-page. L'airplay recopie cette adresse dans `emplacement`.
- Début d'un événement de priorité égale ou supérieure : coupure nette, comme pour un fichier.
- Fin de l'événement du stream : le stream s'éteint pendant son `crossfade_fin`, et s'arrête à la fin du fondu (aussitôt si `crossfade_fin` vaut 0). Le sonore suivant démarre en même temps s'il a un `crossfade_debut` (superposition, [§ 5.1](#51-lecture-audio)), sinon à la fin du fondu.
- Flux tombé : toute interruption avant la fin de son événement, erreur réseau, réponse en erreur, ou fin propre du flux. Le passage se termine en incident, et le log note l'incident `flux tombé`, avec l'adresse et l'erreur. L'occurrence du stream est suspendue : tant qu'elle reste active, la liste de l'événement de secours du stream la remplace, en boucle, reprise à l'élément qui suit le dernier joué ; sans événement de secours, ou sans rien de jouable dans sa liste, l'événement de priorité inférieure.
- Reconnexion en tâche de fond : une voie muette retente la connexion toutes les 5 secondes. Dès que le son arrive, crossfade immédiat : le stream monte pendant son `crossfade_debut`, et les sonores de remplacement s'éteignent pendant ce même temps (coupure nette à 0). Nouveau passage dans l'airplay, et l'incident `reprise du flux` dans le log, avec l'adresse et la durée de la panne : chaque panne a ses deux lignes d'incident, début et fin.
- L'occurrence du stream n'est plus active (fin de l'événement, ou un autre commence) : la reconnexion est abandonnée, `reconnexion abandonnée` (info) dans le log.
- Les métadonnées ICY du flux ne sont pas relayées : l'artiste et le titre viennent de la base.
- Prolonger un stream dont le direct déborde : [#47](https://github.com/dascritch/machincast/issues/47).

### 4.8 Métadonnées publiques et masquage

Artiste et titre sont **masqués**, jamais remplacés. Chaque niveau porte son indicateur de masquage. La valeur retenue est celle du premier niveau renseigné, dans cet ordre de priorité :

**Événement > Séquence > Banque > Sonore > valeur par défaut du fichier de configuration**

Les sorties privées affichent toujours tout. Les sorties publiques respectent le masquage.

Quand l'artiste et le titre sont masqués, la sortie publique affiche à leur place :

1. le premier nom public renseigné, dans le même ordre que le masquage : celui de l'événement, puis de la séquence, puis de la banque ([#99](https://github.com/dascritch/machincast/issues/99)) ;
2. sinon, le texte public par défaut de la configuration (`metadonnees.texte_public`).

Mise en œuvre ([#19](https://github.com/dascritch/machincast/issues/19), `machincast.lecture.sorties`) : chaque indicateur `masquer_metadonnees` vide hérite du niveau suivant. Les indicateurs sont lus en base quand la page publique est écrite, à chaque passage. Un passage sans artiste ni titre affiche aussi le premier nom public renseigné, ou le texte public. Un nom public vide compte comme non renseigné.

## 5. Binaire lecture

`Machin_lecture` ne fait que lire les événements et les jouer. Il lit le fichier de configuration à son lancement et tourne comme service systemd.

Boucle de diffusion ([#88](https://github.com/dascritch/machincast/issues/88), `machincast.lecture.diffusion`) : connecté à la base de production avec le rôle `machincast_lecture`, le binaire consigne son démarrage, puis avance par pas d'environ 50 ms, à l'heure de son horloge. À chaque pas : les voies finies terminent leur passage dans l'airplay ; pendant un sonore, l'ordonnanceur dit s'il faut couper net ; au début du crossfade de fin du sonore en cours, il donne le suivant, lancé aussitôt s'ils se superposent, sinon à la fin du sonore en cours ; sans rien sur la sortie, le suivant démarre, ou c'est le silence. SIGTERM et SIGINT demandent l'arrêt, pris en compte à la fin du pas : les passages en cours se terminent sans incident, et l'arrêt est consigné. Base injoignable, perdue, ou sortie audio impossible à créer : code de sortie 1.

### 5.1 Lecture audio

- Bibliothèque : GStreamer via PyGObject (lecture, crossfade, streams).
- Sortie au choix dans la configuration : ALSA, PulseAudio ou PipeWire, chacune fournie par son greffon GStreamer (`gstreamer1.0-alsa`, `gstreamer1.0-pulseaudio`, `gstreamer1.0-pipewire`). La sortie `factice` ne joue aucun son, pour les tests et les essais (`machincast.audio`).
- L'heure courante est lue par une horloge injectable (`machincast.horloge`) et les tirages aléatoires par un générateur à graine (`machincast.hasard`).
- Crossfade selon `crossfade_debut` et `crossfade_fin` de chaque sonore ([#15](https://github.com/dascritch/machincast/issues/15), `machincast.lecture.moteur`) : le sonore monte de 0 à plein volume pendant `crossfade_debut` ; il s'éteint pendant ses `crossfade_fin` dernières secondes, et le sonore suivant démarre à ce moment-là. Deux sonores ne se superposent que si le sortant a un `crossfade_fin` et l'entrant un `crossfade_debut` : si l'un des deux vaut 0, le sortant joue jusqu'au bout à plein volume, puis l'entrant démarre à plein volume (décidé en relecture de [PR #86](https://github.com/dascritch/machincast/pull/86)). Chaque sonore joue dans sa propre voie (pipeline GStreamer) : deux voies se superposent pendant un crossfade, et la sortie les mélange (en ALSA, un périphérique qui mélange, comme `default`). La coupure nette arrête toutes les voies aussitôt.
- Le crossfade retenu, côté par côté ([#143](https://github.com/dascritch/machincast/issues/143), [#145](https://github.com/dascritch/machincast/issues/145), `machincast.lecture.diffusion.crossfade`) : celui que la banque qui a fourni le sonore impose ; sinon celui du sonore, s'il est paramétré (0 seconde en est un) ; sinon celui que la banque applique à défaut ; sinon celui de la configuration (`crossfades.debut`, `crossfades.fin`) ; sinon aucun. Un sonore placé directement dans un événement ou une séquence n'a pas de banque : il garde les siens, ou prend ceux de la configuration, même s'il figure dans une banque qui les impose. Les séquences et les événements n'ont pas de réglage de crossfade. L'enchaînement, l'heure estimée du prochain sonore sur la socket d'état et la simulation suivent les mêmes crossfades.
- Avant de jouer un fichier, le binaire compare sa date de modification et sa taille avec la base. En cas d'écart, il le consigne dans le log (`alerte`, `fichier modifié`) et joue le fichier ; c'est l'indexeur qui mettra la base à jour. Un fichier introuvable n'est pas joué (`incident`, `fichier introuvable`) : l'ordonnanceur l'écarte pendant une heure, comme un sonore non jouable, et passe au suivant.
- S'il n'a aucun élément à lire dans le fil musical, il émet un silence et lève une alerte dans le log.
- Analyse au dernier moment ([#181](https://github.com/dascritch/machincast/issues/181), `machincast.lecture.analyse`) : au début de chaque sonore, quand il réserve le suivant, le binaire regarde si ce prochain sonore est un fichier jamais vérifié en entier (`verifie_le` vide), ou dont le fichier a changé depuis (date de modification ou taille, `machincast.empreinte.modifie`). Si c'est le cas, il lance `Machin_indexation --audit-complet --sonore N`, par son propre Python et avec sa configuration, dans un processus détaché de sa session, sans fenêtre, et ne l'attend jamais : un indexeur qui plante, ou pas encore fini, ne retarde ni ne bloque la lecture. Il le consigne (`info`, `analyse du prochain sonore`) ; une commande qui ne peut pas être lancée donne l'alerte `analyse impossible`. Un même sonore n'est pas redemandé avant une heure. Un stream n'est jamais analysé. La simulation ne lance aucune analyse.

### 5.2 Écritures

- `airplay` : une ligne au début et une ligne à la fin de chaque passage (insertions seules), par `machincast.lecture.enregistrement` ([#17](https://github.com/dascritch/machincast/issues/17)). La ligne de fin recopie la ligne de début : l'artiste et le titre restent ceux du moment du passage, même modifiés entre-temps. Une coupure nette n'est pas un incident (`sans_incident` vrai) ; une lecture interrompue par une erreur, si.
- `log` : toutes les opérations, normales comme incidents, avec l'heure de l'horloge du binaire. Natures déjà consignées : `démarrage` (info), `arrêt` (info), `début d'événement`, `fin d'événement`, `début de séquence` et `fin de séquence` (info, [#153](https://github.com/dascritch/machincast/issues/153)), `coupure nette` (info), `sonore expiré` (info), `élément sauté` (info), `reconnexion abandonnée` (info), `silence` (alerte), `événement terminé plus tôt` (alerte), `sortie inaccessible` (alerte), `socket d'état indisponible` (alerte), `fichier modifié` (alerte), `fichier introuvable` (incident), `lecture interrompue` (incident), `flux tombé` (incident), `reprise du flux` (incident), `analyse du prochain sonore` (info) et `analyse impossible` (alerte), [#181](https://github.com/dascritch/machincast/issues/181).
- Débuts et fins à l'antenne ([#153](https://github.com/dascritch/machincast/issues/153), `Diffusion._noter_l_antenne`) : avant chaque passage qui commence, et à l'arrêt, le binaire note, au niveau info et avec l'événement, la fin de la séquence puis de l'événement que le passage ne continue pas, puis le début des siens. Un événement commence avec son premier passage (`« Journal », émission, de 20:00 à 20:30`, `« Élections », spécial, depuis 20:00`, `« Continue », fil musical, permanent`) et finit quand un passage d'un autre événement commence, coupure comprise, ou à l'arrêt (`« Journal »`). Une séquence (`« Pub », dans « Continue »`) commence avec un passage qui ne suit pas le précédent un élément plus loin dans la même séquence : une séquence qui revient aussitôt recommence. Les heures sont celles de l'antenne ; un silence ne termine rien. La simulation les note de même dans son log.
- `sonores.etat` : passage à `expire` ([§ 4.5](#45-sonore-jouable)).

### 5.3 Modules de sortie

| Module | Visibilité | Contenu |
| --- | --- | --- |
| stdout | privé | Sonores lancés : une ligne d'information `à l'antenne : artiste – titre (événement)` par passage qui commence. Débuts et fins d'événements et de séquences, comme dans le log : `début d'événement : « Journal », émission, de 20:00 à 20:30` ([#153](https://github.com/dascritch/machincast/issues/153)). |
| stderr | privé | Alertes et incidents du log (`alerte : nature : message`), erreurs du binaire. |
| CSV | privé | Airplay, un fichier par jour, nommé avec la date du jour au format ISO 8601. Une ligne par passage terminé : `debut;fin;duree;artiste;titre;emplacement;evenement;sequence;banque;sans_incident` (la colonne `sequence`, nom interne de la séquence qui a fait jouer le sonore, depuis [#99](https://github.com/dascritch/machincast/issues/99)), heures `AAAA-MM-JJ HH:MM:SS`, durée `HH:MM:SS`, `oui` ou `non`. Séparateur `;`, UTF-8 avec BOM, en-tête à la création ; jamais réécrit. |
| .pls | privé | Les 100 derniers fichiers joués, streams compris par leur adresse, du plus ancien au plus récent, avec artiste et titre ; réécrit à chaque passage. |
| HTML | public | Le sonore à l'antenne et les 20 précédents, du plus récent au plus ancien, avec masquage appliqué et sans emplacement de fichier ; page statique sans JavaScript, rafraîchie toutes les 30 s, réécrite à chaque passage. |

Les fichiers .pls et HTML sont remplacés d'un coup : un lecteur ne voit jamais une page à moitié écrite. Une sortie qui ne peut pas être écrite est consignée une fois dans le log (`sortie inaccessible`, alerte) et n'arrête pas la diffusion ; elle l'est de nouveau si elle redevient inaccessible après une écriture réussie. Choix décidés avec le ticket ([commentaire](https://github.com/dascritch/machincast/issues/19#issuecomment-6198038989)).

Un module privé indique tous les sonores. Un module public applique le masquage ([§ 4.8](#48-métadonnées-publiques-et-masquage)).

### 5.4 Socket d'état

Le binaire expose une socket Unix donnant à l'interface : état de marche, sonore en cours (début, durée, fin estimée, progression), prochain sonore (début et fin estimés, durée, indicateur « sain »).

Mise en œuvre ([#20](https://github.com/dascritch/machincast/issues/20), `machincast.lecture.etat`) :

- **Chemin** : `lecture.socket_etat` dans la configuration ; par défaut `$XDG_RUNTIME_DIR/machincast/lecture.sock`, ou `/run/user/<uid>/machincast/lecture.sock` sans cette variable. Le répertoire est en `0700` et la socket en `0600` : seul le compte qui diffuse les lit. Une socket déjà ouverte par un autre `Machin lecture` refuse la seconde diffusion (code de sortie 1, « un autre Machin lecture diffuse déjà ») ; une socket laissée par un binaire arrêté brutalement est remplacée. Une socket impossible à créer pour une autre raison est consignée (`socket d'état indisponible`, alerte), et la diffusion continue sans elle.
- **Protocole** : à la connexion, le binaire envoie le dernier état, puis chaque nouvel état, une ligne JSON en UTF-8 par état. Il publie à chaque changement, et au moins chaque seconde pendant un sonore pour la progression. Le client n'envoie rien. Un client lent ou qui se déconnecte ne gêne jamais la diffusion. À l'arrêt, un dernier message `"etat": "arret"` part, puis la socket est fermée et effacée.
- **Version** : le champ `version` vaut 1. Il change quand un champ change de sens ou disparaît ; l'ajout d'un champ ne le change pas.
- **Prochain sonore** : il est réservé dès le début du sonore en cours (décidé en relecture de [#20](https://github.com/dascritch/machincast/issues/20)) : c'est lui qui est joué ensuite, tiré au hasard compris. La réservation tombe si un événement coupe la diffusion, si son événement n'est plus actif, ou s'il n'est plus jouable (désactivé, expiré) : le suivant est alors choisi à ce moment-là. Une réservation sans rien de jouable ne déclenche pas l'alerte de silence, qui vient à la fin du sonore en cours.

Champs d'un message :

| Champ | Type | Sens |
| --- | --- | --- |
| `version` | entier | Version du format : 1. |
| `horodatage` | date ISO 8601 | Heure de l'état, à l'horloge du binaire. |
| `etat` | texte | `diffusion` (un sonore est sur la sortie), `silence` (rien à diffuser) ou `arret` (dernier message, la diffusion s'arrête). |
| `en_cours` | objet ou `null` | Sonore à l'antenne ; `null` en silence et à l'arrêt. |
| `prochain` | objet ou `null` | Sonore réservé pour la suite ; `null` s'il n'y en a pas. |

Champs communs à `en_cours` et `prochain` :

| Champ | Type | Sens |
| --- | --- | --- |
| `sonore` | entier | Identifiant du sonore. |
| `type` | texte | `fichier` ou `stream`. |
| `artiste`, `titre` | texte ou `null` | Métadonnées de la base, jamais masquées : l'interface est privée. |
| `evenement` | texte | Nom interne de l'événement qui le joue (ou de l'événement de secours). |
| `emplacement` | texte ou `null` | Chemin du fichier, ou adresse du stream (directe ou de son marque-page), comme dans l'`airplay`. Ajouté en relecture de [PR #106](https://github.com/dascritch/machincast/pull/106), sans changer la version. |
| `duree` | nombre ou `null` | Durée en secondes ; `null` pour un stream, dont la durée est inconnue. |
| `fin_estimee` | date ISO 8601 ou `null` | Fin prévue, `null` quand la durée ou le début sont inconnus. Pour le sonore en cours qu'un événement coupera, l'instant de la coupure, même pour un stream ([#169](https://github.com/dascritch/machincast/issues/169)). |
| `evenement_id` | entier | Identifiant de l'événement ([#144](https://github.com/dascritch/machincast/issues/144), sans changer la version). |
| `evenement_debut`, `evenement_fin` | date ISO 8601 ou `null` | Début et fin de l'occurrence de l'événement, en heure murale du poste, sans fuseau ; `null` pour un fil musical permanent, et pour la fin d'une occurrence sans fin. |
| `sequence`, `sequence_id` | texte, entier ou `null` | Séquence qui joue le sonore, nom interne et identifiant ; `null` hors d'une séquence. |
| `banque`, `banque_id` | texte, entier ou `null` | Banque qui a fourni le sonore ; `null` pour un sonore placé directement dans la liste. |

Champs propres à `en_cours` : `debut` (date ISO 8601 du début du passage), `position` (secondes jouées), `progression` (de 0 à 1, `null` pour un stream) et `texte_public` ([#144](https://github.com/dascritch/machincast/issues/144)) : ce que la page publique affiche du passage, masquage appliqué ([§ 4.8](#48-métadonnées-publiques-et-masquage)) ; `null` si le passage n'est pas encore dans l'airplay. `coupe_par` et `coupe_par_id` ([#169](https://github.com/dascritch/machincast/issues/169)) : le nom interne et l'identifiant de l'événement qui commencera pendant le sonore et le coupera net ([§ 4.2](#42-transitions)), `null` s'il ira jusqu'à sa fin. La coupure est cherchée au début du sonore, jusqu'au début de son crossfade de fin ; pour un stream, jusqu'à la fin de son occurrence, et 12 heures au plus. Le contexte d'un sonore (événement, séquence, banque, texte public) est lu une fois par sonore, pas à chaque message.

Champs propres à `prochain` : `debut_estime` (date ISO 8601, `null` après un stream : au début du crossfade de fin du sonore en cours s'ils se superposent, à sa fin sinon ; à l'instant de la coupure si un événement coupe le sonore en cours) et `sain` (indicateur du [§ 4.6](#46-sonore-sain) : `true` ou `false`, `null` pour un stream, qui n'est pas testé automatiquement). Après une coupure annoncée, le prochain sonore est **anticipé** ([#169](https://github.com/dascritch/machincast/issues/169)) : c'est celui que choisira la décision prise à la coupure, si rien ne change d'ici là, tirage au hasard compris. L'anticipation ne laisse aucune trace : rien n'est consigné, aucune occurrence n'est terminée et le hasard n'avance pas ; c'est la décision prise à la coupure qui choisit le sonore et consigne ce qu'il faut, comme un élément sauté.

Exemple, présenté ici sur plusieurs lignes ; le binaire envoie chaque message sur une seule :

```json
{"version": 1, "horodatage": "2026-10-14T20:00:30+02:00", "etat": "diffusion",
 "en_cours": {"sonore": 12, "type": "fichier", "artiste": "Les Gaufres", "titre": "Café à minuit",
  "emplacement": "/srv/musique/Les Gaufres/Café à minuit.flac", "evenement": "Fil de jour",
  "debut": "2026-10-14T20:00:00+02:00", "duree": 214.5, "fin_estimee": "2026-10-14T20:03:34.500000+02:00", "coupe_par": null, "coupe_par_id": null, "position": 30.0, "progression": 0.14},
 "prochain": {"sonore": 31, "type": "fichier", "artiste": null, "titre": "Jingle", "emplacement": "/srv/habillage/jingle.flac",
  "evenement": "Fil de jour",
  "debut_estime": "2026-10-14T20:03:30.500000+02:00", "duree": 8.0, "fin_estimee": "2026-10-14T20:03:38.500000+02:00", "sain": true}}
```

### 5.5 Mode simulation

Sur option de lancement, le binaire simule la diffusion entre deux dates et heures :

- aucune écriture en base, aucune sortie sonore ;
- l'état de départ (positions séquentielles, cycles aléatoires, compteurs de lectures, séquence en cours) est lu depuis `airplay`, puis tenu en mémoire pendant toute la simulation ; les règles sont celles de la diffusion, séquences comprises ;
- une graine (seed) rend le hasard reproductible, notamment pour les tests ;
- seules des sorties .csv, .pls et .html sont produites, nommées par défaut avec un préfixe `simulation` suivi des dates de début et de fin, nommage modifiable par paramètre.

Mise en œuvre ([#21](https://github.com/dascritch/machincast/issues/21), `machincast.lecture.simulation`, choix notés sur le [ticket](https://github.com/dascritch/machincast/issues/21#issuecomment-6199262518)) :

- **Commande** : `Machin_lecture --simulation DEBUT FIN [--graine N] [--nom NOM]`. Les dates sont en ISO 8601, en heure du poste, et la fin suit le début. Code de sortie 2 sinon, et pour `--graine` ou `--nom` sans `--simulation`.
- **Aucune écriture en base**, au sens du cahier des charges (« pas une seule entrée ») : la simulation ouvre une seule transaction `REPEATABLE READ, READ ONLY` (`lecture_seule`), annulée à la fin. PostgreSQL y refuse toute écriture, et l'état de départ est celui de son ouverture.
- **État en mémoire** : la logique de lecture lit et écrit l'historique par un `Historique` (`machincast.lecture.historique`), la base en diffusion (`EN_BASE`) ou la mémoire en simulation (`HistoriqueSimule`). En mémoire, les passages, le log et les expirations simulés s'ajoutent à ce que la base contient : compteurs de lectures, cycles des banques, dernier élément de chaque événement.
- **Aucune sortie sonore** : `MoteurSimule` ne crée aucun pipeline GStreamer. La diffusion (`Diffusion`, la même qu'à l'antenne) avance d'échéance en échéance : fin prévue d'une voie, début du crossfade de fin du sonore en cours, prochain début ou fin d'une occurrence (`grille.prochain_changement`), fin de la période ; en silence, toutes les minutes.
- **Durées** : celles de la base. Un stream n'est pas contacté et tient jusqu'à la fin de son événement ou jusqu'à une coupure.
- **Sorties** : `<nom>.csv`, `<nom>.pls` et `<nom>.html` dans le répertoire de `sorties.csv`. Le nom par défaut est `simulation-AAAA-MM-JJTHHMM-AAAA-MM-JJTHHMM`. Ce sont trois fichiers pour toute la période. L'artiste et le titre y sont masqués comme sur la page publique ([§ 4.8](#48-métadonnées-publiques-et-masquage)), et l'emplacement de chaque fichier, donné dans les trois, permet de vérifier ce qui est joué (décidé en relecture de [PR #95](https://github.com/dascritch/machincast/pull/95)). La page HTML liste les alertes et incidents simulés, puis les passages, avec leur emplacement. Les alertes et incidents vont aussi sur la sortie d'erreur, préfixés de `simulation :`.

## 6. Binaire indexation

`Machin_indexation` est déclenché depuis l'interface, par son menu ([§ 8.11](#811-menu), [#38](https://github.com/dascritch/machincast/issues/38)), dans un processus à part avec la fenêtre de son journal (`--fenetre`, [#120](https://github.com/dascritch/machincast/issues/120)), ou depuis un terminal. Une seule indexation à la fois sur une base : elle tient un verrou consultatif de PostgreSQL (`pg_try_advisory_lock`) pendant tout son passage, et une deuxième s'arrête aussitôt, sans rien toucher (code de sortie 1). Une indexation peut être arrêtée entre deux fichiers ; le travail fait est gardé. Un cron ou un timer systemd pourra être ajouté plus tard selon les retours du terrain.

### 6.0 Modes d'indexation

Deux modes ([#69](https://github.com/dascritch/machincast/issues/69)).

- **Indexation rapide**, par défaut : un nouveau fichier est enregistré à l'état `apercu`, sans être décodé ([§ 6.2](#62-indexation-des-répertoires-de-banques)). Seuls les sonores en aperçu, et ceux dont le fichier a changé depuis sa dernière vérification (date de modification ou taille, [#10](https://github.com/dascritch/machincast/issues/10)), sont ensuite décodés et leurs tags lus. Pour les autres, seule la présence du fichier est contrôlée : un fichier disparu passe quand même son sonore à `supprime`. Un fichier jamais vérifié, sans date ni taille enregistrées, n'est pas comparé.
- **Audit complet**, option `--audit-complet` : tous les sonores de type fichier sont décodés, comme décrit ci-dessous ; c'est lui qui repère un fichier abîmé sans que sa date ni sa taille aient changé.
- **Un seul sonore**, option `--sonore N` ([#181](https://github.com/dascritch/machincast/issues/181)) : seul le sonore N est vérifié, rapidement ou en audit complet, sans parcours des répertoires, sans le verrou de l'indexation et sans document d'audit ; ses anomalies vont sur la sortie d'erreur. Un sonore inconnu ou un stream est refusé (code 1), `--fenetre` aussi (code 2). C'est ainsi que `Machin_lecture` fait analyser le prochain sonore ([§ 5.1](#51-lecture-audio)).

### 6.1 Vérification des sonores existants (hors streams)

- Type du fichier, avant tout décodage ([#121](https://github.com/dascritch/machincast/issues/121), `machincast.indexation.type_fichier`) : libmagic lit ses premiers octets, et le type est enregistré dans `type_mime`. Un type `audio/…`, ou un conteneur sonore (`video/mp4`, `application/ogg`), est décodé. Un type indéterminé (`application/octet-stream`, `inode/x-empty`) aussi : le décodage tranche. Tout autre type donne le verdict **non supporté**, sans décodage : sonore `apercu`, `actif`, `errone` ou `non_supporte` passé `non_supporte`, les autres états conservés. Un fichier non supporté qui devient sain repasse `actif`, compté parmi les rétablis.
- Décodage complet du fichier (GStreamer), pour s'assurer qu'il n'est pas endommagé ([#7](https://github.com/dascritch/machincast/issues/7)). Le fichier est décodé sans être joué, bien plus vite que le temps réel (une dizaine de minutes de son en moins d'une seconde).
- GStreamer est tolérant : la plupart des fichiers tronqués ou corrompus se décodent sans erreur, en un son plus court ou parasité. Le verdict repose donc sur trois signes :
	- **introuvable** : aucun fichier à son emplacement ;
	- **illisible** : erreur de GStreamer (fichier qui n'est pas du son, vide, conteneur cassé), aucun son décodé, ou décodage qui ne progresse plus pendant 30 secondes (disque ou partage réseau bloqué). Un décodage qui ne produit aucun son en 5 secondes est repris depuis le début, jusqu'à trois tentatives : GStreamer se bloque parfois au démarrage d'un pipeline (environ un décodage sur cent, fichiers sains compris), et un disque réseau en veille a ainsi le temps de répondre ;
	- **endommagé** : rupture de continuité dans le son décodé, signe que le décodeur a sauté des données (constaté en MP3, Ogg, M4A et AAC brut) ;
	- **endommagé** : durée décodée plus courte que la durée annoncée par l'en-tête, au-delà de 75 ms ou de 0,1 % (fichier tronqué ou trames perdues, constaté en FLAC, AIFF et M4A).
- Limites propres aux formats : des octets altérés dans un WAV ou un AIFF passent inaperçus (ni somme de contrôle ni trames) ; un WAV, un Ogg, un MP3 sans en-tête de durée ou un AAC brut (`.aac`, sans durée annoncée) tronqué se décode comme un fichier plus court et sain.
- Fichier sain : la durée décodée, la date de modification et la taille du fichier sont enregistrées ; un sonore `apercu` ou `errone` devient `actif`.
- Fichier illisible ou endommagé : signalé sur STDERR, sonore `apercu` ou `actif` passé `errone`.
- Fichier introuvable (supprimé ou déplacé) : signalé sur STDERR, sonore `apercu`, `actif` ou `errone` passé `supprime`. Un fichier déplacé sera réindexé comme nouveau sonore.
- Un sonore `desactive`, `expire` ou `supprime` garde son état ; son fichier défectueux est quand même signalé ([§ 3.1](#sonores), [#66](https://github.com/dascritch/machincast/issues/66)).
- Chaque décodage libère tout ce qu'il a ouvert : une indexation de milliers de fichiers ne garde aucun descripteur de fichier ouvert ([#149](https://github.com/dascritch/machincast/issues/149)).
- Décodeur GStreamer absent pour un format : la vérification s'arrête et indique les paquets à installer, sans changer l'état du sonore, car le fichier n'y est pour rien.
- Date de modification ou taille changée : nouvelle vérification complète, mise à jour de la durée et des tags, **sans toucher aux champs édités à la main**.

### 6.2 Indexation des répertoires de banques

- Parcours récursif de chacun des répertoires de chaque banque ([#9](https://github.com/dascritch/machincast/issues/9)), avant la vérification des sonores, dans le même passage : un nouveau fichier, enregistré à l'état `apercu`, est décodé aussitôt après, en indexation rapide comme en audit complet.
- Formats : mp3, AAC en conteneur MP4 (`.m4a`) ou brut en trames ADTS (`.aac`), ogg, flac, wav, aiff, reconnus à l'extension `.mp3`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.wav`, `.aiff` ou `.aif`, quelle que soit sa casse. L'extension `.mp4`, souvent une vidéo, n'est pas prise. Les autres fichiers sont ignorés, ainsi que les fichiers et répertoires cachés (nom commençant par un point, comme les `._*` de macOS).
- Sous-répertoires parcourus dans l'ordre de leur nom ; les liens symboliques vers des répertoires ne sont pas suivis (boucles), sauf le répertoire de la banque lui-même. Un répertoire relatif, introuvable ou illisible est signalé sur STDERR avec le nom de la banque ; les autres sont indexés.
- Chaque fichier non encore indexé est ajouté à `sonores` (`apercu`, `indexe_le` renseigné), puis rattaché à la banque en fin de liste ; les fichiers d'un même passage dans l'ordre de leur chemin. Sa durée et ses tags sont enregistrés par la vérification qui suit.
- L'emplacement est unique : un fichier trouvé par plusieurs banques donne un seul sonore, rattaché à chacune. Un sonore trouvé dans le répertoire d'une banque dont il n'est pas membre, par exemple retiré à la main, y est rattaché en fin de liste ; l'interface l'annonce au moment du retrait.
- Une transaction par fichier : une interruption garde le travail fait.

#### Tags ([#8](https://github.com/dascritch/machincast/issues/8))

- Les tags sont lus par GStreamer pendant le décodage complet de la vérification, sans autre lecture du fichier : ID3 (MP3, et AIFF quand le fichier en porte), Vorbis comments (Ogg, FLAC), atomes MP4 (M4A), chunk INFO (WAV : artiste, titre, album, genre, année seulement).
- Correspondance : artiste ← artiste ; titre ← titre ; `annee` ← date de sortie ; `album`, `artiste_album`, `genre`, `compositeur` ← tags du même nom ; `label` ← organisation (Vorbis `ORGANIZATION`) ou éditeur (ID3 `TPUB`) ; `piste` ← numéro de piste.
- L'année vient d'une date, ou d'un horodatage **sans heure** : un horodatage avec heure est une date de création, comme celle qu'un M4A sans date de sortie annonce pour son conteneur, et ne devient jamais l'année du morceau.
- Textes conformés comme ceux de l'interface ([#108](https://github.com/dascritch/machincast/issues/108), [§ 8](#8-interface-graphique)), puis ignorés s'ils sont vides, au profit du tag suivant ; artiste et titre tronqués à 255 caractères, la limite des colonnes.
- Pour un fichier sain, l'indexeur tient l'artiste, le titre et les clés ci-dessus à l'image des tags : un tag absent vide le champ, sauf s'il a été édité à la main. Les tags d'un fichier défectueux ne sont pas lus : les valeurs en base restent telles quelles.

### 6.3 Sorties

STDOUT et STDERR uniquement, plus une sortie texte au format CSV et HTML. L'indexeur n'écrit pas dans le log.

- STDERR : une ligne par fichier défectueux, désigné par son chemin, avec le problème et la conséquence (« sonore passé erroné », « état désactivé conservé »). Les messages passent par `logging` : anomalies (`warning`) et erreurs (`error`) sur STDERR, informations sur STDOUT.
- Document d'audit ([#11](https://github.com/dascritch/machincast/issues/11), `machincast.indexation.audit`) : à chaque passage qui va au bout, un `.csv` (séparé par des points-virgules, UTF-8 avec BOM) et un `.html`, dans `/tmp`, nommés avec l'horodatage ISO 8601 du lancement en heure locale, sans fuseau : `/tmp/machincast-audit-2026-10-15T08:15:00.csv`. L'heure vient de `machincast.horloge`. Une ligne par anomalie de fichier : date du passage, chemin (jamais l'identifiant du sonore), verdict, problème, conséquence ; la dernière ligne du CSV, de verdict `bilan`, porte le bilan. Aucune opération normale. Sans anomalie, le document ne porte que le bilan. Ses chemins sont annoncés sur STDOUT, après le bilan ; un document impossible à écrire est signalé sur STDERR, sans changer le code de sortie.
- STDOUT, au fil de l'indexation ([#120](https://github.com/dascritch/machincast/issues/120)) : une ligne par fichier trouvé dans les répertoires des banques (« nouveau sonore, ajouté à la banque … », « rattaché à la banque … ») et par fichier décodé sain (« sain, Artiste – Titre ; sonore passé actif », « … ; état actif conservé »), désigné par son chemin.
- STDOUT, à la fin : le mode et le bilan, par exemple « indexation rapide : 3 nouveaux sonores, 1 rattachement ; 3 sonores vérifiés ; 1 erroné, 0 non supporté, 1 supprimé, 0 rétabli, 3 sortis d'aperçu ». Les nouveaux sonores et les rattachements (sonore déjà connu ajouté à une banque) viennent du parcours des répertoires ; les sonores vérifiés sont ceux qui ont été décodés ; les autres nombres comptent les changements d'état.
- Code de sortie : 0 quand la vérification est allée au bout, même si des sonores ont changé d'état : ce sont des anomalies non bloquantes ; 1 si la base est injoignable ou si un décodeur manque ; 2 pour une configuration invalide.

## 7. Wrapper Machin

Script bash `Machin` ([#6](https://github.com/dascritch/machincast/issues/6)) :

```
Machin [--config FICHIER] BINAIRE [OPTIONS…]
Machin logs [OPTIONS DE journalctl…]
Machin dev | dev-test
Machin -h | --help | --binaires
```

- `Machin BINAIRE` appelle `Machin_BINAIRE` (`lecture`, `indexation` ou `interface`) en lui transmettant toutes les options qui suivent, intactes, et se termine avec son code de sortie. Le binaire est cherché d'abord dans le venv du projet (`.venv`, à côté du répertoire `bin/` du wrapper, même appelé par un lien symbolique), puis dans le `PATH` : le wrapper prépare ainsi l'environnement, sans qu'il soit besoin d'activer le venv.
- `--config FICHIER` (ou `--config=FICHIER`), placé avant le binaire, lui est transmis, notamment pour les tests. Placé après le binaire, il est transmis tel quel.
- `-h` affiche une aide minimale de deux lignes, `--help` l'aide complète. L'aide d'un binaire s'obtient par `Machin BINAIRE --help`.
- `Machin logs` suit en direct le journal du service de lecture, `machincast.service` (`journalctl --unit=machincast.service --follow`). Les options qui suivent sont transmises à `journalctl`, par exemple `--since "1 hour ago"`. Le journal d'un service système n'est lisible que par les groupes `adm` (dont fait partie le premier compte créé à l'installation d'Ubuntu) et `systemd-journal` : le compte qui utilise MachinCast doit pouvoir le lire, `install.sh` l'ajoute donc au groupe `systemd-journal`, qui donne la lecture du journal sans les droits d'administration de `adm` (voir [§ 10](#10-installation-et-déploiement)).
- `--binaires` liste les binaires, un par ligne ; l'autocomplétion s'en sert.
- Poste de développement ([#77](https://github.com/dascritch/machincast/issues/77)) : `Machin dev` ouvre un sous-shell interactif dans le répertoire de MachinCast, qui lit le `.bashrc` du compte, active le venv, définit `MACHINCAST_DEV=1` et préfixe l'invite de `(MachinCast dev)` ; `exit` en sort, avec son code. `Machin dev-test` lance, dans le répertoire de MachinCast, avec le venv en tête du `PATH` et `VIRTUAL_ENV` défini, `ruff check --no-cache .`, `ruff format --no-cache --check .`, `mypy --strict src/`, `shellcheck -x` sur les scripts bash, `pytest` puis `bats tests/wrapper`. Il les lance tous, même après un échec, puis affiche un bilan par outil. Sans cache, ruff ne garde pas le verdict d'un fichier dont l'ordre des imports dépend d'un autre. Un outil absent compte comme un échec, avec un message qui propose `./install.sh --dev`. Ni l'un ni l'autre ne prend d'argument.
- Codes de sortie : celui du binaire, de `journalctl` ou du sous-shell de `dev` ; 1 pour `dev-test` si un outil a échoué ou manque ; 2 pour un appel incorrect du wrapper (binaire ou option inconnus, `--config` sans fichier, argument donné à `dev` ou `dev-test`) ; 127 si le binaire, `journalctl` ou le venv est introuvable.

Autocomplétion bash (`bash-completion/Machin`) : binaires, `logs`, `dev` et `dev-test`, options du wrapper, fichiers après `--config`, options d'un binaire lues dans son aide, options courantes de `journalctl` après `logs`.

Le wrapper n'est pas copié dans le venv : en développement, il s'appelle par `bin/Machin`. `install.sh` installe le wrapper et l'autocomplétion pour tout le système (voir [§ 10](#10-installation-et-déploiement)).

## 8. Interface graphique

Python, PySide6 (Qt 6.10, version de Kubuntu 26.04 LTS).

**Conformation des textes** ([#108](https://github.com/dascritch/machincast/issues/108), `machincast.conformation.conformer`) : les noms (interne et public) des événements, séquences, banques et marques-pages, l'artiste, le titre et les métadonnées musicales des sonores saisis dans une fiche sont conformés à l'enregistrement : tout espace Unicode (tabulation, retour à la ligne, espace insécable, espace fine…) devient une espace simple, les espaces de début et de fin sont retirées et jamais deux ne se suivent ; les caractères de contrôle, les sélecteurs de variante, les caractères spéciaux (U+FFF0 à U+FFFF), les caractères à usage privé, les caractères non attribués et les espaces sans largeur (U+200B, U+FEFF) sont supprimés. Rien d'autre n'est changé : accents, écritures non latines et emoji restent tels quels. Les chemins et les adresses ne le sont jamais. Une fiche compare des textes conformés : un texte relu tel qu'en base, non conforme, n'est pas une modification.

### 8.1 Écran par défaut

- Heure actuelle.
- État du binaire lecture (en marche ou non).
- Airplay des 12 dernières heures, en table.
- Sonore en cours mis en avant : emplacement (chemin du fichier ou adresse du stream), heure de début, durée totale, heure de fin estimée, barre de progression.
- Juste à côté, le prochain sonore : emplacement, heures de début et de fin estimées, durée, indicateur « sain ». Le sonore en cours et le prochain sonore occupent chacun la moitié de la largeur de l'écran ; un titre ou un nom d'événement trop long passe à la ligne (demandé en relecture de [PR #106](https://github.com/dascritch/machincast/pull/106)).
- Pour un stream, durée et heure de fin affichées comme inconnues.
- VU-mètre et bargraph de la sortie sonore (indisponibles avec la sortie ALSA).

Mise en œuvre ([#23](https://github.com/dascritch/machincast/issues/23), `machincast.interface.ecran_par_defaut`), sans le VU-mètre, qui vient avec [#24](https://github.com/dascritch/machincast/issues/24) :

- **État, sonore en cours et prochain sonore** : de la socket d'état ([§ 5.4](#54-socket-détat)), par `machincast.interface.etat.ClientEtat`, un `QLocalSocket` dans la boucle d'événements de Qt. Sans socket, ou quand elle se ferme, le binaire lecture est « À l'arrêt » et le client retente la connexion chaque seconde. Un message illisible est signalé sur la sortie d'erreur et ignoré.
- **Airplay** : lu en base avec le rôle de l'interface (`machincast.interface.airplay.lire_airplay`), à l'ouverture, puis seulement quand la socket annonce un autre sonore en cours (ou aucun) que celui que la table connaît. Jamais en boucle. Artiste et titre toujours affichés : l'interface est privée.
- **Inconnus** : un stream a sa durée, sa fin et sa progression « inconnue », et son indicateur « sain » « non testé ». Le début estimé du prochain sonore après un stream est « inconnu ».
- **Disposition** ([#144](https://github.com/dascritch/machincast/issues/144)) : en haut, l'heure, le texte public du sonore en cours entre guillemets (champ `texte_public` de la socket, `—` sans texte) et l'état ; puis l'événement à l'antenne et ses heures (« de 20:00 à 22:00 », « depuis 19:00 » sans fin, « permanent » pour un fil musical). Chaque sonore a, une ligne par information, son événement, sa séquence, sa banque (`—` sans), son horaire sur une ligne (« 20:00:00 – 20:03:34 (3:34) », « 20:00:00, durée inconnue » pour un stream) et son emplacement. La barre de progression du sonore en cours, sans intitulé, dit le temps qui reste, à la seconde entamée : « reste 3:05 ».
- **Coupure** ([#169](https://github.com/dascritch/machincast/issues/169)) : un sonore qu'un événement coupera (champ `coupe_par` de la socket) a pour horaire « 20:00:00 – 20:02:00 (coupé par « Journal », sur 3:34) », ou « … (coupé par « Flash », durée inconnue) » pour un stream ; sa barre se remplit de son début à la coupure et dit « reste 1:30 avant « Journal » ». Le prochain sonore annoncé est celui de l'événement, à l'instant de la coupure.
- **Fiches** ([#144](https://github.com/dascritch/machincast/issues/144)) : un bouton à droite du titre de chaque sonore, et un à droite de son événement, de sa séquence et de sa banque, émettent `EcranParDefaut.ouverte(genre, identifiant, nom)`, que la fenêtre traite comme une ligne de liste ouverte ; ils sont inactifs sans sonore, et ceux de l'événement, de la séquence et de la banque sans leur identifiant dans l'état publié (`evenement_id`, `sequence_id`, `banque_id`). Dans l'airplay, un double-clic sur l'artiste ou le titre ouvre la fiche du sonore, sur l'événement, la séquence ou la banque celle de l'élément ; ailleurs, ou sur un élément supprimé depuis, il ne fait rien. La colonne « Incident » ne dit `oui` que pour un passage qui en a eu un.
- **Lancement** : `Machin_interface` se connecte à la base avant d'ouvrir son écran. Sans base, ou sans droit sur elle, il montre une fenêtre d'erreur (`machincast.interface.erreur.FenetreBaseInjoignable`, demandée en relecture de [PR #106](https://github.com/dascritch/machincast/pull/106)) : l'interface n'est pas utilisable et pourquoi, une invitation à lire `INSTALL.md` du répertoire de MachinCast, section « En cas de problème », avec un bouton qui ouvre ce document, et l'erreur de PostgreSQL en détail. Puis il s'arrête avec le code 1. La fenêtre n'est montrée que si un affichage graphique peut la montrer (`DISPLAY`, `WAYLAND_DISPLAY` ou `QT_QPA_PLATFORM`, sauf les plateformes invisibles `offscreen` et `minimal`) ; sinon, seul le message de la sortie d'erreur reste. Les textes propres à Qt, comme « Montrer les détails… », sont en français (`machincast.interface.application`).

### 8.2 Recherche et navigation

- Écrans de liste avec recherche pour les sonores, les banques, les séquences et les événements, menant aux écrans de détail.

Mise en œuvre des listes ([#26](https://github.com/dascritch/machincast/issues/26), `machincast.interface.listes`, `machincast.interface.fenetre`) :

- **Onglets** : la fenêtre a un onglet par écran, décidé avec le ticket : Accueil (l'écran par défaut, [§ 8.1](#81-écran-par-défaut)), ouvert au lancement, puis une liste par type, dans l'ordre de la recherche : Événements, Séquences, Banques, Sonores ; puis les Marques-pages ([§ 8.13](#813-marques-pages-de-streams)) ; enfin les Incidents ([§ 8.6](#86-écran-des-incidents)).
- **Colonnes et ordre** : événements (nom, nom public, priorité, début, fin, récurrence, anomalie : « événement vide », [#140](https://github.com/dascritch/machincast/issues/140)), du plus prioritaire au moins prioritaire ; séquences (nom, nom public, anomalie : « séquence vide », [#138](https://github.com/dascritch/machincast/issues/138)) ; banques (nom, nom public, mode, ne pas répéter, premier répertoire dans l'ordre alphabétique) ; sonores (artiste, titre, type, état, durée, emplacement, anomalie : « hors durées » d'une banque où il figure, [#147](https://github.com/dascritch/machincast/issues/147)), par artiste puis titre ; marques-pages (nom, adresse, nombre de streams qui le suivent), par nom. Un clic sur un titre de colonne trie.
- **Anomalies** ([#138](https://github.com/dascritch/machincast/issues/138)) : une ligne en anomalie (`Ligne.anomalie`) a l'icône d'avertissement de Qt sur sa première cellule et son explication en infobulle sur toutes ; le compte ajoute « dont n en anomalie », parmi les lignes que garde le filtre.
- **Filtre** : les lignes dont une colonne contient le texte, sans tenir compte des majuscules ni des accents (`FiltreSansAccents`) ; un compte « n sonores sur N ».
- **Lecture** : en base, avec le rôle de l'interface, chaque fois que l'onglet s'ouvre ; jamais en boucle. Le filtre est gardé.
- **Détail** : un double-clic ou Entrée sur une ligne émet `FenetrePrincipale.detail_demande(genre, identifiant)`, et ouvre la fiche de l'élément ([§ 8.5](#85-écran-de-détails-dun-événement), [§ 8.12](#812-écran-de-détails-dune-séquence), [§ 8.4](#84-écran-de-détails-dune-banque), [§ 8.3](#83-écran-de-détails-dun-sonore)).
- **Création** : une liste peut avoir un bouton de création (`Source.nouveau`, signal `Liste.creation_demandee`) ; les listes des événements, des séquences, des banques et des sonores l'ont : « Nouvel événement », « Nouvelle séquence », « Nouvelle banque » et « Nouveau stream ». La liste des sonores a aussi « Ajouter des fichiers… » et accepte les dépôts de fichiers (`Source.fichiers`, signaux `Liste.ajout_demande` et `Liste.fichiers_deposes`) ; une liste dans un choix d'éléments n'a ni l'un ni l'autre.
- Champ de recherche globale avec auto-suggestion, résultats dans l'ordre : événements, banques, sonores. Un écran de résultats dédié.
- Vue calendrier (jour, semaine) montrant à la fois l'airplay (ce qui a effectivement été diffusé) et les événements prévus.

Mise en œuvre du calendrier ([#36](https://github.com/dascritch/machincast/issues/36), [#118](https://github.com/dascritch/machincast/issues/118), `machincast.interface.calendrier`) :

- **Onglet** : « Calendrier », ouvert par le menu « Affichage » ; il se ferme, et n'est ouvert qu'une fois. Il se relit à son ouverture, à chaque changement de période et par « Rafraîchir les onglets » ; jamais en boucle.
- **Vues** : semaine, du lundi au dimanche, ou jour, de 0 h à 24 h ; « Semaine précédente », « Aujourd'hui », « Semaine suivante » (ou « Jour … »), de 28 jours avant à 28 jours après aujourd'hui : une période se montre tant qu'elle touche cette portée. Passer en vue jour montre aujourd'hui s'il est dans la semaine montrée, sinon son lundi.
- **Prévu** : chaque occurrence d'un événement, récurrences comprises (`machincast.lecture.grille.prevoir`, qui suit les règles de `evenement_actif`). Un bloc est plein là où son événement serait à l'antenne, estompé là où un autre le masque (priorité plus haute, ou fil permanent qui cède). Une occurrence sans fin se dessine jusqu'au début suivant d'une priorité égale ou plus haute, au plus tard minuit ; ce qui joue se calcule avec cette fin. Une occurrence de 24 heures ou plus et un fil musical permanent vont dans la bande de la journée entière, entre le nom du jour et les heures ; une occurrence qui passe minuit donne un bloc par jour. Des blocs qui se chevauchent se placent côte à côte, chacun à la première colonne libre de leur groupe. Les événements de secours, hors grille, n'y sont pas.
- **Diffusé** : l'airplay, en bandes étroites à droite de chaque jour, sur le fond du passé. Les passages successifs d'un même événement font une bande ; un passage sans fin dure jusqu'au passage suivant, ou jusqu'à maintenant pour le dernier, en cours. Un événement supprimé se nomme « Événement supprimé ».
- **Priorités** : une case par priorité (« Spécial », « Émission », « Fil musical »), toutes cochées à l'ouverture, montre ou cache ses blocs et ses bandes ; ce qui joue ne change pas. L'airplay d'un événement supprimé est toujours montré.
- **Survol** : l'infobulle d'un bloc donne l'événement et son nom public, sa priorité, ses heures, sa récurrence et ce qui en joue ; celle d'une bande, ses heures à la seconde et son nombre de passages.
- **Double-clic** sur un bloc ou une bande : la fiche de son événement ([§ 8.5](#85-écran-de-détails-dun-événement)).
- **Clic sur une heure libre** pas encore passée : `dialogues.confirmer_creation` propose un événement sur l'heure entière cliquée, 13:00 – 14:00 pour un clic à 13:37 (« Créer », par défaut, ou « Annuler ») ; « Créer » ouvre la fiche d'un nouvel événement, début et fin cochés, modifiée mais pas enregistrée (`FicheEvenement.prevoir`).

### 8.3 Écran de détails d'un sonore

- Édition de tous les champs : artiste, titre, métadonnées musicales (année, etc.), crossfades, maximum de lectures, état (actif ou désactivé ; expiré, erroné et supprimé sont affichés, et l'interface peut les ramener à actif), masquage, période de diffusion. Tout champ saisi ici est marqué comme édité à la main et n'est plus modifié par l'indexeur.
- Pré-écoute dans une fenêtre de l'interface, sur un périphérique de sortie obligatoirement différent de celui du binaire lecture (mise en œuvre ci-dessous).
- Pour un stream : choix entre URL directe et marque-page, choix de l'événement de secours ([§ 4.7](#47-streams)), test du stream à la demande.
- Table des derniers passages, avec indication des incidents.

Mise en œuvre ([#28](https://github.com/dascritch/machincast/issues/28), `machincast.interface.fiche_sonore`, `machincast.interface.essai_flux`), avec ce qui est commun aux fiches (`machincast.interface.fiche`, [§ 8.4](#84-écran-de-détails-dune-banque)) :

- **Onglet** : « Sonore : » suivi du titre, ou du nom du fichier, ou de l'adresse d'un stream. Une fiche par sonore ; une banque et un sonore de même identifiant ont chacun la leur.
- **Champs** : artiste, titre, les clés de `metadonnees_musicales` tenues par l'indexeur (`annee` et `piste` en nombres entiers), crossfades, à cocher : décoché, non paramétré, `NULL` ([#145](https://github.com/dascritch/machincast/issues/145)), avec le pas et la durée maximale des préférences, maximum de lectures (0 = illimité), masquage (« Selon la configuration », « Masqués », « Affichés »), période de diffusion à cocher, état. Les autres clés des métadonnées sont montrées, jamais modifiées. Les textes sont enregistrés sans les espaces qui les entourent ; un champ vide est NULL, ou une clé absente.
- **Écriture** : seuls les champs qui diffèrent de ce que la fiche a lu sont écrits, sous verrou de la ligne ; les autres gardent ce que l'indexation ou la diffusion y a mis entre-temps. Chacun est ajouté à `champs_edites`, sauf l'état. La fin de la période doit suivre son début ; un stream doit avoir une adresse ou un marque-page ; un sonore effacé de la base entre-temps n'est pas enregistré.
- **État** : la fiche propose l'état du sonore, puis `actif` et `desactive` ; un sonore `apercu` ne change pas d'état.
- **Stream** : adresse directe ou marque-page existant (leur gestion : [§ 8.13](#813-marques-pages-de-streams)) ; événement de secours parmi les événements `secours`, ou aucun. Le **test à la demande** décode le flux de l'adresse saisie, sans le jouer ni l'enregistrer, par GStreamer (`uridecodebin`, `fakesink`) : il répond dès une seconde de son décodée, et ne répond pas sur une erreur ou après 10 s. Le bus est relevé par un minuteur de Qt : l'interface reste utilisable. La connexion se ferme à la fin du test, à la fermeture de la fiche et à celle de la fenêtre.
- **Passages** : les 50 derniers débuts de passage du sonore dans `airplay`, avec leur fin, et les lignes du log de ce sonore, de niveau `alerte` ou `incident`, notées entre le début et la fin du passage (ou depuis le début, pour le passage en cours). La colonne « sans incident » de l'airplay n'est plus montrée ([#125](https://github.com/dascritch/machincast/issues/125)) : les incidents eux-mêmes le disent.
- **Dossier** ([#125](https://github.com/dascritch/machincast/issues/125)) : un bouton ouvre le dossier du fichier dans le navigateur de fichiers du poste (`dialogues.ouvrir_dossier`), pour un fichier seulement.
- **Relations** : séquences (`sequences_elements`), banques (`banques_sonores`) et événements (`evenements_elements`) qui citent directement le sonore, dans cet ordre, puis par nom ; un double-clic demande leur fiche (`ouverture_demandee`). Une banque dont le sonore sort des durées a l'icône d'anomalie et une infobulle qui dit pourquoi ([#147](https://github.com/dascritch/machincast/issues/147)).
- **Fichier**, pour un fichier : `type_mime` ([#121](https://github.com/dascritch/machincast/issues/121)) ; encodage moyen, taille × 8 / durée, en kbit/s ; taille (unités décimales) et date de modification lues par `stat` à l'ouverture de la fiche, et date de création par `stat --format=%W` (statx), inconnue si le système de fichiers ne la garde pas ; `verifie_le`, la dernière vérification complète par l'indexeur.
- **Pré-écoute** ([#116](https://github.com/dascritch/machincast/issues/116), [#29](https://github.com/dascritch/machincast/issues/29), `machincast.interface.preecoute`) : le bouton « Pré-écoute… » de la fiche, inactif pour un nouveau stream pas encore enregistré, envoie le sonore à la fenêtre de pré-écoute (`FicheSonore.preecoute_demandee`). Cette fenêtre est indépendante, et unique pour toute l'interface (`FenetrePrincipale.preecoute`) : un autre sonore y remplace le précédent, à l'arrêt ; « Affichage → Pré-écoute… » la ramène au premier plan, avec son sonore, ou l'ouvre sans sonore. Elle se ferme avec l'interface, et sa fermeture arrête la lecture.
	- Lecteur : un pipeline playbin de GStreamer, relevé par un minuteur de Qt. Boutons « ⏵ » (lecture), « ⏸ » (pause) et « ⏹ » (arrêt, qui ramène au début), nommés par leur infobulle ; barre de position pendant la lecture d'un fichier ou sa pause, jamais pour un stream ; temps écoulé sur durée, la durée en base avant la lecture. La fin du fichier ramène à l'arrêt ; un fichier introuvable ou une erreur de GStreamer est signalé (« Lecture impossible : … »).
	- VU-mètre : niveau RMS de chaque canal (élément `level`), de -60 à 0 dB, orange au-delà de -12 dB, rouge au-delà de -3 dB.
	- Informations : format (codec), débit (celui des tags, sinon « ≈ » la taille du fichier sur sa durée), échantillonnage, canaux et, pour un stream, les secondes pré-décodées : la part remplie de son tampon de 5 secondes.
	- Sortie : sur la sortie de l'antenne (`audio.sortie`), le périphérique `audio.preecoute`, jamais celui de l'antenne. Le choix liste les périphériques du poste que donne le fournisseur de GStreamer de la sortie (PipeWire, PulseAudio, ALSA) ; celui de la diffusion y est grisé, suivi de « (diffusion) », et ne peut pas être choisi, même par le clavier ; le périphérique configuré vient d'abord, « (introuvable) » s'il est absent. Le choix arrête la lecture, et s'enregistre dans `audio.preecoute` du fichier de configuration, qui garde ses commentaires ; sans fichier, il vaut pour la session.
	- L'écoute de l'antenne viendra avec son VU-mètre ([#24](https://github.com/dascritch/machincast/issues/24)).

### 8.4 Écran de détails d'une banque

- Édition du nom interne et du nom public ([#99](https://github.com/dascritch/machincast/issues/99)).
- Masquage de l'artiste et du titre.
- Mode séquentiel ou aléatoire.
- Case « ne pas répéter » : la banque ne passe jamais deux fois de suite ([#63](https://github.com/dascritch/machincast/issues/63)).
- Durées minimale et maximale des sonores ([#147](https://github.com/dascritch/machincast/issues/147)), facultatives : un sonore qui en sort est marqué dans la liste de la fiche, d'après ses durées, avant même l'enregistrement, avec une infobulle (« 3:20 : plus court que le minimum de la banque, 3:30. ») ; rien n'est refusé, sauf une minimale qui dépasse la maximale.
- Crossfades de début et de fin ([#143](https://github.com/dascritch/machincast/issues/143)) : pour chacun, une règle, « Garder ceux des sonores », « Appliquer si le sonore n'en a pas » ou « Imposer à tous les sonores », et une durée, qui ne se modifie pas tant que la banque garde ceux des sonores.
- Liste des répertoires indexés : ajout et retrait.
- Liste des sonores liés, réordonnable par glisser-déposer en mode séquentiel. Ajout de sonores, y compris hors des répertoires de la banque.
- Retrait d'un sonore issu d'un répertoire de la banque : l'interface prévient qu'il sera réintégré à la prochaine indexation, et propose un lien ouvrant le navigateur de fichiers dans son répertoire. La suppression du fichier se fait hors de l'outil, parfois depuis un autre poste quand l'utilisateur n'a pas le droit d'écriture sur l'emplacement.

Mise en œuvre ([#31](https://github.com/dascritch/machincast/issues/31), `machincast.interface.fiche_banque`, `machincast.interface.choix`, `machincast.interface.dialogues`) :

- **Onglet** : la fiche s'ouvre dans un onglet de la fenêtre, « Banque : <nom interne> », depuis la liste des banques ; une fiche déjà ouverte revient au premier plan. Le bouton « Nouvelle banque » de la liste ouvre une fiche vide, « Nouvelle banque » : séquentielle, au masquage hérité, sans « ne pas répéter ». Seuls les onglets des fiches se ferment.
- **Enregistrement** : les modifications restent dans la fiche jusqu'à « Enregistrer », qui les écrit en une transaction, puis relit la banque ; « Annuler » la relit sans rien écrire. Les deux boutons ne servent qu'à une fiche modifiée. Les noms sont enregistrés sans les espaces qui les entourent, un nom public vide comme NULL. Un nom interne vide ou déjà pris, ou une base injoignable, laisse la fiche modifiée, avec un message.
- **Fermeture** : fermer une fiche modifiée, ou la fenêtre qui en a, demande Enregistrer (Entrée), Abandonner ou Annuler (Échap) ; un enregistrement refusé garde la fiche ouverte.
- **Masquage** : « Hérité du sonore » (NULL), « Masqués » (vrai), « Affichés » (faux).
- **Répertoires** : enregistrés sous leur forme normale (`os.path.normpath`), sans doublon, rangés dans l'ordre de leurs caractères.
- **Sonores** : réordonnables par glisser-déposer ou par « Monter » et « Descendre », en mode séquentiel seulement ; une ligne ne se dépose pas dans une autre. Les boutons d'une ligne ne servent qu'à une ligne choisie. L'ajout se fait parmi les sonores déjà en base (`Choix`, la liste filtrable des sonores à sélection multiple), ou par dépôt de fichiers (ci-dessous) ; l'ajout de fichiers depuis la liste des sonores est décrit au [§ 8.8](#88-ajout-dun-sonore). L'avertissement de réintégration vaut pour un fichier sous l'un des répertoires de la fiche, sous-répertoires compris, et ouvre le dossier du fichier. Un double-clic ou Entrée sur un sonore demande sa fiche (`ouverture_demandee`, [#115](https://github.com/dascritch/machincast/issues/115)) ; une ligne de fichier déposé, sans identifiant, n'en demande pas.
- **Dépôt depuis le navigateur de fichiers** (`machincast.interface.depot.DepotDeFichiers`, un filtre d'événements sur la zone d'une liste) : des dossiers sur les répertoires, des fichiers sonores sur les sonores, dans les deux modes. Le dépôt est toujours accepté comme une copie, jamais comme un déplacement que le navigateur de fichiers achèverait en supprimant l'original ([#96](https://github.com/dascritch/machincast/issues/96)) ; un glisser qui ne propose pas la copie est refusé. Les chemins sont pris sous leur forme normale. Un fichier déjà en base reprend son sonore ; un fichier pas encore en base devient, à l'enregistrement seulement, un sonore à l'état `apercu` ([§ 8.8](#88-ajout-dun-sonore)). Le reste est ignoré, et la fiche le dit. Un glisser sans fichier local (texte, adresse web, ligne d'une liste) passe au travers.
- **Indexation concurrente** : à l'enregistrement, la liste en base est réécrite dans l'ordre de la fiche, suivie des sonores rattachés depuis la lecture de la fiche, ni présents dans la fiche, ni retirés par elle. Un sonore effacé de la base entre-temps est oublié.

### 8.5 Écran de détails d'un événement

- Nom interne et nom public.
- Priorité : fil musical, émission, spécial.
- Masquage de l'artiste et du titre.
- Dates et heures de début et de fin, avec les règles du [§ 3.1](#evenements).
- Récurrence : jours de la semaine à cocher.
- Liste de lecture de banques, de sonores et/ou de séquences ([#99](https://github.com/dascritch/machincast/issues/99)), réordonnable par glisser-déposer, doublons autorisés.
- Avertissement quand une banque « ne pas répéter » occupe deux lignes contiguës, y compris la dernière et la première d'un événement qui boucle : le deuxième appel sera ignoré à la diffusion ([§ 4.4](#44-choix-dun-sonore-dans-une-banque), [#63](https://github.com/dascritch/machincast/issues/63)). L'avertissement n'empêche pas d'enregistrer.
- Refus d'un chevauchement avec un événement de même priorité.

Mise en œuvre ([#32](https://github.com/dascritch/machincast/issues/32), `machincast.interface.fiche_evenement`, `machincast.interface.elements`), avec ce qui est commun aux fiches (`machincast.interface.fiche`, [§ 8.4](#84-écran-de-détails-dune-banque)) :

- **Onglet** : « Événement : <nom interne> », depuis la liste des événements ; « Nouvel événement » ouvre une fiche vide, de priorité `emission`, au masquage hérité.
- **Champs** : noms enregistrés sans les espaces qui les entourent, un nom public vide comme NULL, un nom interne unique ; priorité ; masquage « Selon la séquence, la banque ou le sonore » (NULL), « Masqués » (vrai), « Affichés » (faux).
- **Grille** : début et fin de la première occurrence, chacun à cocher, et sept cases de jours. Un début coché part de l'heure de l'horloge, à la minute ; une fin cochée qui ne suit pas le début, d'une heure après lui. Sans début, la fin et les jours se décochent et ne se saisissent pas ; la priorité `secours` décoche le début. Refusés : une émission ou un spécial sans début, une fin qui ne suit pas le début, un chevauchement ([§ 4.1](#41-choix-de-lévénement-actif)), nommé avec le premier instant commun, et un changement de priorité d'un événement de secours qu'un stream désigne, que la base refuserait aussi.
- **Liste de lecture** : sonores, banques et séquences, comme la liste d'une séquence ([§ 8.12](#812-écran-de-détails-dune-séquence)) ; « Ajouter des marques-pages… » ([#167](https://github.com/dascritch/machincast/issues/167), `ListeElements._ajouter_marques_pages`) ajoute, pour chaque marque-page choisi, le premier stream par titre qui le suit, ou, sans stream qui le suive, crée à l'enregistrement un stream actif titré du nom du marque-page, un seul par marque-page ; un marque-page effacé entre-temps est oublié ; une séquence a pour détail son nombre d'éléments. Une liste vide s'enregistre, pour être complétée plus tard, avec un avertissement selon la priorité : une émission ou un spécial vide laisse l'antenne à l'événement de priorité inférieure, un fil musical vide se tait avec une alerte, un secours vide laisse le stream tombé à l'événement de priorité inférieure ([§ 4.2](#42-transitions), [#140](https://github.com/dascritch/machincast/issues/140)). Une ligne restée dans la liste garde son identifiant dans `evenements_elements`, que `airplay.element_id` désigne ([§ 4.2](#42-transitions)).
- **Avertissement** : `deroule.appels_ignores_aux_bords`, la liste bouclant sauf pour une émission ou un spécial sans fin ; une séquence compte par la banque de sa première ligne et celle de sa dernière. Recalculé à chaque changement de la liste, de la priorité ou de la fin.

### 8.6 Écran des incidents

Table des incidents du log : horaire, lien vers le sonore, lien vers la banque, lien vers l'événement quand il est renseigné.

Mise en œuvre ([#35](https://github.com/dascritch/machincast/issues/35), `machincast.interface.incidents.EcranIncidents`) :

- **Onglet** « Incidents », le dernier des onglets fixes ; il se relit à chaque ouverture, comme une liste.
- **Entrées** : niveaux `alerte` et `incident`, et `info` sur demande (« Montrer aussi les informations ») ; du plus récent au plus ancien ; les 500 plus récentes au plus, ce que dit le compte. Colonnes : horaire (heure du poste), niveau, nature, message, sonore (artiste et titre, ou fichier, ou adresse), banque, événement.
- **Filtre** : `FiltreSansAccents`, comme les listes ([§ 8.2](#82-recherche-et-navigation)).
- **Liens** : un double-clic sur une cellule de sonore, de banque ou d'événement demande sa fiche (`EcranIncidents.ouverte`) ; ailleurs, rien. Un élément supprimé laisse sa cellule vide.

### 8.7 Écran de simulation

L'utilisateur saisit une date et heure de début et de fin. L'interface lance le binaire lecture en mode simulation et présente la table des sonores qui seraient joués, exportable en .pls, .csv et .html.

### 8.8 Ajout d'un sonore

- Fichier : par sélecteur de fichiers ou glisser-déposer. Déposer un fichier sur les sonores d'une banque l'enregistre déjà, à l'état `apercu` ([§ 8.4](#84-écran-de-détails-dune-banque)). Le fichier est référencé là où il se trouve, sans copie. Il peut être synchronisé depuis un autre ordinateur et changer de contenu sous le même nom (émission pré-enregistrée, rediffusion d'un direct). Il passe immédiatement par la vérification de l'indexeur.
- Stream : URL directe ou marque-page, et l'événement de secours.

Mise en œuvre ([#30](https://github.com/dascritch/machincast/issues/30), `machincast.interface.ajout`, `machincast.interface.verification`, `machincast.interface.fiche_sonore`) :

- **Fichiers** : « Ajouter des fichiers… » dans la liste des sonores (`dialogues.choisir_fichiers`, plusieurs à la fois), ou dépôt de fichiers sur la liste (`DepotDeFichiers`, copie seulement). Les fichiers sonores entrent en base en une transaction, sous leur chemin normalisé, à l'état `apercu` ; un fichier déjà en base ou choisi deux fois n'est pas ajouté de nouveau ; le reste est ignoré. La barre d'état annonce l'ajout.
- **Vérification immédiate** : `Verificateur` décode les sonores ajoutés dans un fil à part, l'une après l'autre des vérifications demandées, avec le code de l'indexeur (`verifier_sonores`, limité à ces sonores par `identifiants`) et son rôle en base (`Role.INDEXATION`, sur le socket et la base de la connexion de l'interface). Sa fin s'annonce dans la barre d'état, avec l'état de chaque sonore, et la liste ouverte se relit. Un décodeur absent ou une base injoignable laisse les sonores en aperçu, pour la prochaine indexation. Fermer la fenêtre attend la fin de la vérification en cours. Les fichiers déposés sur une banque, une séquence ou un événement ne sont pas vérifiés aussitôt (décision du ticket).
- **Stream** : « Nouveau stream » ouvre une fiche de sonore vide ; l'adresse directe ou le marque-page est obligatoire. Le stream entre en base à l'état `actif`, et ses autres champs s'écrivent comme une modification, marqués comme saisis à la main.

### 8.9 Suppression

- Un sonore présent dans un événement ou une banque n'est supprimé qu'après validation, en rappelant les événements et banques où il figure.
- Supprimer un sonore supprime son entrée en base, **jamais son fichier**, qui reste à sa place ([#96](https://github.com/dascritch/machincast/issues/96)). Si le fichier est toujours dans le répertoire d'une banque, la prochaine indexation l'enregistre de nouveau comme un nouveau sonore.
- Même règle pour la suppression d'une banque, d'une séquence ou d'un événement.
- Les lignes `airplay` sont toujours conservées.

Mise en œuvre ([#33](https://github.com/dascritch/machincast/issues/33), `machincast.interface.suppression`, `Fiche.supprimer`) :

- **Bouton** « Supprimer… » au pied de chaque fiche, actif dès que l'élément est en base. La confirmation est toujours demandée (`dialogues.confirmer_suppression`, Entrée et Échap gardent l'élément), même pour un élément qui ne figure nulle part.
- **Question** : les banques, séquences et événements dont la liste contient l'élément, par nom, en signalant ceux qui n'auraient plus rien ; pour un sonore, son fichier, qui reste en place, et les banques dont un répertoire le contient, qui le réindexeront ; pour une banque, ses répertoires ; pour un événement, les streams qu'il secourt.
- **Suppression** : un `DELETE` de la ligne, dans une transaction ; les clés étrangères retirent l'élément des listes (`ON DELETE CASCADE`) et vident les références de l'airplay, du log et des streams (`ON DELETE SET NULL`). Aucun fichier ni répertoire n'est touché. La fiche se ferme ensuite sans question ; un élément déjà effacé ferme simplement sa fiche.

### 8.10 Fil musical garanti

Si aucun événement de priorité fil musical n'existe, l'interface en recrée un.

Mise en œuvre ([#39](https://github.com/dascritch/machincast/issues/39), `machincast.interface.fil_musical.garantir`, appelé par `FenetrePrincipale`) :

- **Quand** : à l'ouverture de la fenêtre, après la suppression d'un événement, et après l'enregistrement d'un événement (qui peut avoir changé de priorité).
- **Quoi** : « Fil musical », permanent (sans début, ni fin, ni jours) et sans élément ; si ce nom est pris par un autre événement, le premier libre parmi « Fil musical 2 », « Fil musical 3 »… Sa liste reste à remplir dans sa fiche ; en attendant, la diffusion se tait et alerte quand il est à l'antenne ([§ 4.2](#42-transitions)).
- **Signalement** : la barre d'état le dit, et le journal le note en avertissement.

### 8.11 Menu

- Ajouter un sonore, une banque, une séquence, un événement.
- Démarrer, arrêter, redémarrer le binaire lecture (via systemd et polkit, authentification par mot de passe ou empreinte digitale).
- Lancer une ré-indexation générale de toutes les banques.
- Choisir la sortie audio des pré-écoutes.

Mise en œuvre du menu ([#117](https://github.com/dascritch/machincast/issues/117), `FenetrePrincipale._garnir_menus`) :

- **Fichier** : « Préférences… » ([#145](https://github.com/dascritch/machincast/issues/145), `machincast.interface.preferences`), dont la page « Interface » règle la granularité, la durée maximale et les durées par défaut des crossfades, enregistrées dans la section `[crossfades]` du fichier de configuration par tomlkit, qui garde ses commentaires ; les fiches ouvertes ensuite les suivent, et Machin lecture les prend à son prochain démarrage ; inactive sans fichier de configuration ; « Quitter » (Alt+Q), qui ferme la fenêtre comme sa case de fermeture, après la question sur les fiches modifiées.
- **Affichage** : « Calendrier » ouvre l'onglet du calendrier ([§ 8.2](#82-recherche-et-navigation)) ; « Pré-écoute… » ouvre la fenêtre de pré-écoute ([#116](https://github.com/dascritch/machincast/issues/116), [§ 8.3](#83-écran-de-détails-dun-sonore)) ; « Rafraîchir les onglets » (F5, [#148](https://github.com/dascritch/machincast/issues/148), `FenetrePrincipale.rafraichir`) relit l'onglet ouvert, l'airplay de l'accueil et chaque fiche ouverte (`Fiche.rafraichir`). Une fiche modifiée pose la question de fermeture (« avant de rafraîchir la fiche ») : enregistrer puis relire, abandonner et relire, ou la laisser telle quelle ; un enregistrement refusé la laisse aussi. La fiche d'un élément qui n'est plus en base se ferme. La barre d'état nomme les fiches laissées et fermées.
- **Diffusion** ([#25](https://github.com/dascritch/machincast/issues/25), `machincast.interface.pilotage`) : « Démarrer la diffusion », « Arrêter la diffusion », « Redémarrer la diffusion ». Avec le service `machincast.service` ([§ 10](#10-installation-et-déploiement)), chacune appelle `systemctl start|stop|restart machincast.service` dans un processus à part (`QProcess`), sans attendre : la règle polkit demande l'authentification d'un administrateur à l'agent polkit de la session ; jamais `sudo`. La barre d'état dit la réussite (« Diffusion démarrée. », « Diffusion arrêtée. », « Diffusion redémarrée. ») ou l'échec, avec le message de systemctl (« Diffusion non démarrée : … »). Les entrées suivent l'état du service (`ActiveState` de `systemctl show`, `machincast.service.lire_l_etat`), relu au lancement, à l'ouverture du menu et après chaque commande : arrêté, démarrer ; en marche, arrêter ou redémarrer ; en échec, démarrer ou redémarrer. **Sans le service**, l'installation n'est pas définitive : la barre d'état le signale en permanence (« Installation non définitive : diffusion sans service »), avec une infobulle qui dit comment installer le service ; le menu pilote alors une **diffusion d'essai**, `Machin lecture` lancé à la main (ce n'est pas `Machin lecture --simulation`, qui ne joue rien) : « Démarrer la diffusion d'essai » lance `bin/Machin lecture --config <configuration de l'interface>` dans une fenêtre de terminal (konsole, sinon x-terminal-emulator), détachée de l'interface ; « Arrêter la diffusion d'essai » envoie `SIGTERM`, comme `Ctrl-C`, au processus qui répond sur la socket d'état (son pid, lu par `SO_PEERCRED`, `ClientEtat.pid_du_lecteur`), et annonce l'arrêt quand la socket se ferme ; « Redémarrer la diffusion d'essai » l'arrête de même, puis la relance dans un terminal. Démarrer n'est active que sans diffusion sur la socket, arrêter et redémarrer qu'avec elle.
- **Maintenance** : « Moniteur de la sortie… », à venir ; « Indexation rapide » et « Audit complet » (ci-dessous).
- **Aide** : « Documentation » ouvre le guide d'utilisation, `doc/utilisation.md` sur GitHub, dans le navigateur web ; « Signaler un problème… » ouvre les tickets GitHub dans le navigateur web (`dialogues.ouvrir_page`) ; « Version » montre le numéro de version et la date du dernier commit du dépôt d'où MachinCast est installé, à l'heure du poste (`machincast.interface.version`, `dialogues.montrer_version`), ou dit qu'elle est inconnue hors d'un dépôt git ou sans git.
- **À venir** : une entrée inactive, dont l'infobulle donne le ticket ; elle s'active avec son ticket. Ajouter un élément se fait depuis sa liste ([§ 8.2](#82-recherche-et-navigation)) ; la sortie des pré-écoutes se choisit dans la fenêtre de pré-écoute, que le menu « Affichage » ouvre ([#29](https://github.com/dascritch/machincast/issues/29)).

Mise en œuvre de la ré-indexation ([#38](https://github.com/dascritch/machincast/issues/38), [#120](https://github.com/dascritch/machincast/issues/120), `machincast.interface.indexation`) :

- **Menu** « Maintenance », avec « Indexation rapide » et « Audit complet » : les deux modes de `Machin_indexation` ([§ 6.0](#60-modes-dindexation)).
- **Processus à part** : l'interface lance `Machin_indexation --fenetre` (et `--audit-complet`), par le Python de l'interface et avec sa configuration (`commande_indexation`), dans un processus détaché (`lancer_detachee`, `QProcess.startDetached`). Fermer l'interface ne l'attend pas et ne l'arrête pas. Tant que ce processus tourne (`processus_actif`, regardé chaque seconde), les actions du menu sont inactives ; à sa fin, la barre d'état le dit, et renvoie au rafraîchissement des onglets. Un processus qui ne se lance pas est signalé dans la barre d'état.
- **Journal** (`machincast.interface.journal_indexation.FenetreJournal`) : la fenêtre de `Machin_indexation --fenetre`. `Indexation` y fait tourner `indexer` dans un fil à part, avec son rôle en base, et relaie au fil de l'eau les lignes que l'indexeur journalise, comme dans le terminal ([§ 6.3](#63-sorties)) : sonores indexés, anomalies, bilan. À la fin, la fenêtre conclut par le bilan et le nombre d'anomalies. Un décodeur absent, une base injoignable ou une autre indexation en cours interrompt l'indexation, et le journal le dit ; les transactions déjà faites restent.
- **Fermeture du journal** : pendant l'indexation, `dialogues.confirmer_arret_indexation` demande s'il faut l'arrêter (« Continuer » par défaut, Échap aussi). « Arrêter » pose l'arrêt de l'indexeur, qui s'arrête après le fichier en cours ; la fenêtre se ferme ensuite, et le processus s'arrête.

### 8.12 Écran de détails d'une séquence

Décidé avec le ticket [#99](https://github.com/dascritch/machincast/issues/99).

- Nom interne et nom public.
- Masquage de l'artiste et du titre.
- Liste ordonnée de sonores et/ou de banques, réordonnable par glisser-déposer, doublons autorisés, jamais une autre séquence. Une séquence vide s'enregistre, avec un avertissement, et la liste des séquences la signale en anomalie ([#138](https://github.com/dascritch/machincast/issues/138)).
- Avertissement quand une banque « ne pas répéter » occupe deux lignes contiguës : le deuxième appel sera ignoré à la diffusion (`deroule.appels_ignores`, sans boucle). L'avertissement n'empêche pas d'enregistrer.
- Liste des événements où la séquence figure. Sa suppression suit la règle du [§ 8.9](#89-suppression).

Mise en œuvre ([#112](https://github.com/dascritch/machincast/issues/112), `machincast.interface.fiche_sequence`), avec ce qui est commun aux fiches (`machincast.interface.fiche`, [§ 8.4](#84-écran-de-détails-dune-banque)) :

- **Onglet** : « Séquence : <nom interne> », depuis la liste des séquences ; « Nouvelle séquence » ouvre une fiche vide, au masquage hérité.
- **Champs** : noms enregistrés sans les espaces qui les entourent, un nom public vide comme NULL ; masquage « Selon la banque ou le sonore » (NULL), « Masqués » (vrai), « Affichés » (faux). Un nom interne vide ou déjà pris laisse la fiche modifiée, avec un message ; une séquence sans élément s'enregistre, et la fiche avertit qu'elle ne joue rien ([#138](https://github.com/dascritch/machincast/issues/138)).
- **Éléments** (`machincast.interface.elements`, commun avec la fiche d'un événement) : genre, nom (artiste et titre d'un sonore, le nom du fichier d'un sonore pas encore décodé, le nom interne d'une banque) et détail (emplacement d'un sonore ; mode d'une banque, et « ne pas répéter »). Réordonnables par glisser-déposer ou par « Monter » et « Descendre » ; une ligne ne se dépose pas dans une autre. L'ajout se fait parmi les sonores et les banques déjà en base (`Choix`, avec la remarque qu'un élément peut revenir), ou par dépôt de fichiers sonores, comme sur la fiche d'une banque : copie seulement, un fichier pas encore en base devenant un sonore `apercu` à l'enregistrement.
- **Écriture** : à l'enregistrement, une ligne restée dans la liste garde son identifiant dans `sequences_elements`, à sa nouvelle position, pour que `airplay.sequence_element_id` la désigne toujours ([§ 4.3](#43-liste-de-lecture-dun-événement)) ; les lignes retirées sont supprimées, les nouvelles ajoutées. Un sonore ou une banque effacé de la base entre-temps est oublié.
- **Avertissement** : sous la liste, une ligne par appel sauté, « Ligne N : la banque « … » vient de passer, et ne passe jamais deux fois de suite : cet appel sera sauté. », recalculé à chaque changement de la liste.
- **Liens** : ouvrir un élément ou un événement ouvre sa fiche, par `Fiche.ouverture_demandee`, que la fenêtre traite comme l'ouverture d'une ligne de liste.

### 8.13 Marques-pages de streams

- Création, modification et suppression des marques-pages ([§ 3.1](#marques_pages_streams)) ; un marque-page qu'un stream suit ne se supprime pas.
- Test du flux à la demande.

Mise en œuvre ([#34](https://github.com/dascritch/machincast/issues/34), `machincast.interface.fiche_marque_page`, `listes.MARQUES_PAGES`) :

- **Onglet** : la liste des marques-pages (nom, adresse, nombre de streams qui le suivent), avec « Nouveau marque-page » ; une fiche par marque-page, « Marque-page : <nom> », avec ce qui est commun aux fiches ([§ 8.4](#84-écran-de-détails-dune-banque)).
- **Champs** : nom obligatoire et unique, adresse obligatoire, enregistrés sans les espaces qui les entourent. La diffusion lit l'adresse du marque-page à chaque passage : une nouvelle adresse vaut pour tous les streams qui le suivent.
- **Test du flux** : `EssaiDeFlux`, comme pour un stream ([§ 8.3](#83-écran-de-détails-dun-sonore)), arrêté à la fermeture de la fiche.
- **Streams qui le suivent** : par titre, ou par l'adresse pour un stream sans titre ; ouvrir l'un d'eux ouvre sa fiche.
- **Suppression** : `suppression.question` lève `Empechee` pour un marque-page qu'un stream suit (la clé étrangère est `ON DELETE RESTRICT`) : la fiche nomme les streams, sans poser de question. Sinon, la confirmation habituelle ([§ 8.9](#89-suppression)).

## 9. Configuration

- Format TOML, lu par `tomllib`.
- Le fichier `machincast.toml` se trouve dans le répertoire du projet et est ignoré par `.gitignore`. Le modèle versionné, documenté clé par clé, est `machincast.exemple.toml`.
- Sans option, chaque binaire lit le `machincast.toml` du répertoire de MachinCast (dépôt local ou release décompressée), quel que soit le répertoire courant, qu'il soit appelé directement ou par le wrapper. Ce répertoire se déduit de l'emplacement du paquet Python, installé en mode éditable ; c'est aussi celui du wrapper, qui appelle les binaires de son `.venv` ([#76](https://github.com/dascritch/machincast/issues/76)). L'option `--config <fichier>`, commune à tous les binaires et transmise par le wrapper, permet d'utiliser une autre configuration, notamment pour les tests.
- Les chemins relatifs sont résolus depuis le répertoire du fichier de configuration.
- Toute clé ou section inconnue est refusée. Une clé obligatoire manquante, un type invalide ou une valeur hors des choix possibles arrête le binaire avec le code 2 et un message qui nomme le fichier et la clé.
- De nouvelles clés s'ajouteront au fil du projet ; chacune est documentée dans le modèle.

| Clé | Type | Obligatoire | Rôle |
| --- | --- | --- | --- |
| `base.socket` | texte | oui | Répertoire de la socket Unix de PostgreSQL. |
| `base.production` | texte | oui | Nom de la base de production. |
| `base.test` | texte | oui | Nom de la base de test. Doit différer de `base.production`. |
| `audio.sortie` | `alsa`, `pulseaudio`, `pipewire` ou `factice` | oui | Sortie audio de l'antenne. `factice` ne joue aucun son (tests, essais). |
| `audio.peripherique` | texte | non | Périphérique de l'antenne ; absent = périphérique par défaut. |
| `audio.preecoute` | texte | oui | Périphérique de pré-écoute, différent de celui de l'antenne ; la fenêtre de pré-écoute de l'interface le réécrit quand on choisit une autre sortie. |
| `sorties.csv` | chemin | oui | Airplay CSV (privé), un fichier par jour : la date du jour au format ISO 8601 s'ajoute au nom (`airplay.csv` donne `airplay-2026-10-15.csv`). |
| `sorties.pls` | chemin | oui | Playlist .pls (privé) des 100 derniers fichiers joués. |
| `sorties.html` | chemin | oui | Page HTML (public) du sonore à l'antenne et des 20 précédents. |
| `metadonnees.masquer` | booléen | oui | Masquage par défaut de l'artiste et du titre. |
| `metadonnees.texte_public` | texte, 255 caractères au plus | oui | Texte public affiché à la place de l'artiste et du titre masqués, quand l'événement n'a pas de nom public. |
| `crossfades.granularite` | `seconde` ou `dixieme` | non | Pas des crossfades dans l'interface ([#145](https://github.com/dascritch/machincast/issues/145)) ; `dixieme` par défaut. |
| `crossfades.maximum` | nombre de secondes, strictement positif | non | Crossfade le plus long que l'interface propose ; 5 par défaut. |
| `crossfades.debut`, `crossfades.fin` | nombre de secondes, de 0 à `crossfades.maximum` | non | Crossfades d'un sonore qui n'en a pas de paramétré, et que sa banque ne règle pas ; absents, il n'en a pas. |
| `lecture.socket_etat` | chemin | non | Socket d'état du binaire lecture, lue par l'interface ([§ 5.4](#54-socket-détat)). Par défaut `$XDG_RUNTIME_DIR/machincast/lecture.sock`. |

## 10. Installation et déploiement

- Cible : Ubuntu 26.04 LTS, et uniquement des versions LTS.
- Installation mono-utilisateur : un seul compte Unix utilise MachinCast, celui qui l'installe, et MachinCast se place dans son répertoire personnel.
- Livraison : archives `.tar.gz` publiées en releases sur le dépôt git (sur le repository <https://github.com/dascritch/machincast>).
- Chaque archive contient un `install.sh` ([#40](https://github.com/dascritch/machincast/issues/40)), à lancer depuis le répertoire de MachinCast (release décompressée ou dépôt git) avec son propre compte, jamais avec sudo : il demande sudo pour les seules étapes qui l'exigent. Relançable, il laisse en place chaque étape déjà faite. `./install.sh --simulation` affiche les commandes sans rien exécuter ; `./install.sh --dev` installe en plus les outils du poste de développement (paquets `bats` et `shellcheck`, extra `[dev]` de pip, [#77](https://github.com/dascritch/machincast/issues/77)). Il :
	- vérifie le système : Ubuntu LTS, la cible étant 26.04 ;
	- installe par apt les seules dépendances système (bibliothèques de compilation de PyGObject, GStreamer et ses plugins, PostgreSQL, autocomplétion bash) ;
	- crée un environnement virtuel Python isolé, **sans** `--system-site-packages`, et y installe toutes les dépendances Python par pip (PySide6, PyGObject, psycopg, yoyo-migrations, python-magic, tomlkit). Le projet suit ainsi l'évolution des paquets sans dépendre des versions de la distribution hôte ;
	- copie `machincast.exemple.toml` en `machincast.toml` s'il n'existe pas ;
	- crée, en tant qu'utilisateur `postgres`, le rôle PostgreSQL du compte courant, **sans aucun droit particulier** (ni `CREATEDB`, ni `CREATEROLE`), les bases de production et de test dont ce compte devient propriétaire, et les trois rôles de groupe ; le compte applique ensuite le schéma, ce que la propriété des bases lui permet ;
	- autorise le compte courant à endosser les trois rôles de MachinCast, en tant qu'utilisateur `postgres` ; un autre compte s'ajoute plus tard de la même façon (voir `INSTALL.md`, [#71](https://github.com/dascritch/machincast/issues/71)) ;
	- ajoute le compte courant au groupe `systemd-journal`, pour suivre les logs du service avec `Machin logs` ;
	- installe en place : `/opt/machincast` est un lien vers le répertoire de MachinCast, `Machin` est relié depuis `/usr/local/bin`, l'autocomplétion depuis `/usr/share/bash-completion/completions` ;
	- vérifie que GStreamer sait décoder chacun des formats de la spec et créer la sortie audio configurée, sans jouer de son, et nomme sinon le paquet manquant (`python -m machincast.installation verifier`).
- Service de diffusion ([#22](https://github.com/dascritch/machincast/issues/22)), **facultatif**, pour un ordinateur dédié à l'antenne seulement : `./install.sh --service` l'installe, `--retirer-service` le retire ; sans lui, `Machin lecture` se lance à la main, pour essayer l'outil avant de l'installer définitivement. Tant que le service n'est pas installé, l'interface d'administration le signale dans sa barre d'état, et lance `Machin lecture` dans une fenêtre de terminal ([#25](https://github.com/dascritch/machincast/issues/25), [§ 8.11](#811-menu)).
	- Unité `/etc/systemd/system/machincast.service`, rédigée par `machincast.installation unite` : `bin/Machin lecture` sous le compte de MachinCast et son groupe, pas sous un compte système, pour garder son rôle PostgreSQL (authentification peer), ses fichiers et sa session audio ; `XDG_RUNTIME_DIR` de cette session, gardée active dès le démarrage par `loginctl enable-linger` (PipeWire ou PulseAudio, socket d'état) ; `Restart=on-failure` après 5 secondes ; arrêt par `SIGTERM`, qui termine proprement le passage en cours, 15 secondes au plus ; messages dans journald, sous l'identifiant `machincast` ; après le réseau, PostgreSQL et le son ; activée pour `multi-user.target`.
	- Règle `/etc/polkit-1/rules.d/50-machincast.rules`, rédigée par `machincast.installation regle` : sur `machincast.service` seulement, les verbes `start`, `stop` et `restart` de `org.freedesktop.systemd1.manage-units`, pour le seul compte de MachinCast, avec l'authentification d'un administrateur (`AUTH_ADMIN` : mot de passe, ou empreinte si PAM la propose) ; elle ne décide de rien d'autre. Jamais de `sudo` pour piloter la diffusion.

## 11. Développements ultérieurs

| Sujet | Contenu | Raison du report |
| --- | --- | --- |
| Anomalie multi-banques | Signaler comme anomalie non bloquante un sonore présent dans plusieurs banques. | Non bloquant. |
| Normalisation du niveau sonore | Sur la sortie ou par fichier, par exemple mesure EBU R128 par l'indexeur via GStreamer, cible -23 LUFS (norme broadcast EBU) ou réglable. | Un compresseur de dynamique matériel est déjà branché avant les départs antenne. À voir après le déploiement. |
| Déclarations SACEM | ISRC, label, compositeur sur les sonores. | En attente de l'équipe juridique : la radio relève d'une catégorie spécifique avec un accord propre avec la SACEM. |
| Quotas | Propriétés « francophone » et « nouveauté », attribuables au niveau du sonore ou de la banque. La « nouveauté » aura une durée maximale par sonore, comptée à partir de son indexation. | La radio a des accords spécifiques sur les quotas. |
| Indexation planifiée | Cron ou timer systemd. | Selon les retours du terrain. |
| Séquences imbriquées | Une séquence qui en contient une autre, avec un refus des appels cycliques. | Écarté avec les séquences ([#99](https://github.com/dascritch/machincast/issues/99)) : une séquence ne contient que des sonores et des banques. |

## 12. Points à confirmer

Aucun point en attente.

### Points tranchés

- **Durée diffusée** : deux lignes d'airplay par passage, une au début et une à la fin, reliées par `passage_id` ; la ligne de fin porte la durée effectivement diffusée ([#48](https://github.com/dascritch/machincast/issues/48), voir [§ 3.1](#airplay)).
- **Affichage public masqué** : nom public de l'événement, sinon texte public par défaut de la configuration ([#49](https://github.com/dascritch/machincast/issues/49), voir [§ 4.8](#48-métadonnées-publiques-et-masquage)).
- **Droits sur les marques-pages** : modifiables par l'interface seule ; le binaire lecture les lit, l'indexeur n'y accède pas ([#50](https://github.com/dascritch/machincast/issues/50), voir [§ 3.2](#32-rôles-et-droits)).
- **Banque « ne pas répéter »** : un élément qui rappellerait une banque marquée « ne pas répéter » juste après elle est sauté, même d'un événement à l'autre ; s'il ne reste rien d'autre de jouable, l'événement se termine et l'événement inférieur prend le relais ([#63](https://github.com/dascritch/machincast/issues/63), voir [§ 4.4](#44-choix-dun-sonore-dans-une-banque)).
- **État d'un sonore** : le booléen `actif` devient un état `actif`, `desactive`, `expire`, `errone` ou `supprime` ; seul l'indexeur rétablit automatiquement un sonore, quand il l'avait lui-même déclaré `errone` ([#66](https://github.com/dascritch/machincast/issues/66), voir [§ 3.1](#sonores)).
- **Indexation rapide** : par défaut, l'indexeur ne décode que les nouveaux fichiers, à l'état `apercu`, et ceux dont la date ou la taille a changé ([#10](https://github.com/dascritch/machincast/issues/10)), et repère les fichiers disparus ; l'audit complet (`--audit-complet`) décode tout ([#69](https://github.com/dascritch/machincast/issues/69), voir [§ 6.0](#60-modes-dindexation)).
- **Environnement virtuel** : isolé des paquets système, toutes les dépendances Python passent par pip ([#51](https://github.com/dascritch/machincast/issues/51), voir [§ 10](#10-installation-et-déploiement)).
