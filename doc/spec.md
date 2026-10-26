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
| **Feed** | Une URL de stream enregistrée pour être réutilisée par plusieurs sonores. Appelé « marque-page de stream » jusqu'à [#252](https://github.com/dascritch/machincast/issues/252) (table `marques_pages_streams`, migration `0012.feeds`). |

## 2. Composants

| Composant | Exécutable | Rôle |
| --- | --- | --- |
| Wrapper | `Machin` | Point d'entrée unique en ligne de commande pour tous les binaires, et suivi des logs du service. |
| Binaire lecture | `Machin_lecture` | Joue les événements, écrit l'airplay et le log. Tourne comme service systemd. |
| Binaire indexation | `Machin_indexation` | Vérifie les sonores et indexe les répertoires des banques. |
| Interface graphique | `Machin_interface` | Supervision, édition, simulation, pilotage du service. |
| Maintenance de la base | `Machin_maintenance-db` | Sauvegarde, vérifie le schéma et les rôles, et optimise la base de production ([#127](https://github.com/dascritch/machincast/issues/127)). |

Tous les exécutables commencent par `Machin_`. Les binaires sans interface graphique se lancent par convention via `Machin` (voir [§ 7](#7-wrapper-machin)) : ce n'est pas une contrainte technique, mais une façon de n'avoir qu'une commande à retenir.

### Communication entre composants

- **Base de données** : PostgreSQL, accédée par socket Unix locale.
- **État du binaire lecture** (en marche, sonore en cours, progression, prochain sonore) : socket Unix exposée par `Machin_lecture`, lue par l'interface. L'interface y envoie aussi ses demandes d'interruption manuelle ([#104](https://github.com/dascritch/machincast/issues/104), [§ 4.9](#49-interruption-manuelle)).
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
| `emplacement` | Chemin du fichier. Clé unique pour les fichiers qui ne sont pas supprimés. Vide pour un stream. |
| `supprime_le` | Demande de suppression depuis l'interface ; vide pour un sonore en service ([#267](https://github.com/dascritch/machincast/issues/267), [§ 8.9](#89-suppression)). Même colonne pour `banques`, `sequences` et `evenements`, dont le nom interne n'est unique que parmi ceux qui ne sont pas supprimés. |
| `disparu_le` | Disparition du fichier, constatée par l'indexation (état `supprime`) ; vide quand il n'a pas disparu ([#267](https://github.com/dascritch/machincast/issues/267)). |
| `url_stream` | URL directe d'un stream à usage unique (par exemple avec un SESSIONID dans l'URL). |
| `feed_id` | Référence à un feed de stream. |
| `secours_evenement_id` | Stream seulement : événement de priorité `secours` qui joue à la place du stream quand son flux tombe. Vide = l'événement de priorité inférieure (fil musical). Voir [§ 4.7](#47-streams). |
| `artiste`, `titre` | Métadonnées publiques, pré-remplies depuis les tags à l'indexation. Ce sont des colonnes, car elles servent au masquage, à la recherche et à l'airplay. |
| `metadonnees_musicales` | Objet JSON des métadonnées non critiques, pré-remplies depuis les tags ([#8](https://github.com/dascritch/machincast/issues/8)) : `annee`, `album`, `artiste_album`, `genre`, `compositeur`, `label`, `piste`. Extensible sans migration : les autres clés ne sont jamais touchées par l'indexeur. |
| `crossfade_debut`, `crossfade_fin` | Temps de crossfade en début et en fin de sonore. Facultatifs ([#145](https://github.com/dascritch/machincast/issues/145), migration `0007.sonores-crossfades-facultatifs`) : `NULL` n'est pas paramétré, et 0 seconde est un crossfade paramétré. La migration a rendu non paramétrés les 0 seconde que personne n'avait saisis (absents de `champs_edites`). |
| `max_lectures` | Nombre maximum de lectures sur la totalité de l'historique. Vide = illimité. |
| `debut_detecte`, `fin_detectee` | Blancs au début et à la fin du fichier, mesurés par l'audit complet au seuil `blancs.seuil` ([#146](https://github.com/dascritch/machincast/issues/146), migration `0008.detection-blancs`, [§ 6.1](#61-vérification-des-sonores-existants-hors-streams)) ; la fin détectée se compte depuis la fin du fichier. Positifs ou nuls ; `NULL` = aucun blanc détecté de ce côté. Le fichier n'est jamais modifié. |
| `detection_blancs` | Le sonore est joué sans ses blancs détectés, même placé directement dans un événement ou une séquence, ou fourni par une banque qui ne les retire pas ([§ 5.1](#51-lecture-audio)). Faux par défaut. |
| `etat` | État du sonore ([#66](https://github.com/dascritch/machincast/issues/66), [#69](https://github.com/dascritch/machincast/issues/69)) : `apercu`, `actif`, `desactive`, `expire`, `errone`, `non_supporte` ([#121](https://github.com/dascritch/machincast/issues/121), migration 0003) ou `supprime` (voir ci-dessous). Seul un sonore `actif` peut être joué. |
| `type_mime` | Type MIME du fichier, lu par libmagic au dernier examen de l'indexeur ([#121](https://github.com/dascritch/machincast/issues/121)) ; NULL avant, et pour un stream. |
| `masquer_metadonnees` | Masquage de l'artiste et du titre au niveau du sonore. Vide = hérite du niveau inférieur. |
| `duree` | Calculée par l'indexeur. Vide pour un stream. |
| `debut_diffusion`, `fin_diffusion` | Période de diffusion facultative (annonces limitées dans le temps). |
| `fichier_modifie_le`, `fichier_taille` | Date de modification et taille du fichier au dernier passage de l'indexeur, pour détecter un changement de contenu. |
| `verifie_le` | Date de la dernière vérification complète du fichier par l'indexeur, type lu puis décodage, en indexation rapide comme en audit complet ([#125](https://github.com/dascritch/machincast/issues/125)) ; NULL avant. Un fichier introuvable la garde. |
| `audite_le`, `audit_seuil` | Date du dernier audit complet du fichier, et seuil de blanc, en dB, auquel il a eu lieu ([#206](https://github.com/dascritch/machincast/issues/206), migration `0011.sonores-dernier-audit`) : tous deux `NULL` tant qu'il n'a jamais été audité, jamais l'un sans l'autre ; le seuil de -100 compris à 0 exclu. Posés par tout audit complet d'un fichier trouvé, quel que soit son verdict ; jamais par l'indexation rapide. |
| `audit_demande` | La prochaine indexation, même rapide, fait l'audit complet du sonore, blancs compris, puis efface la marque ; posée depuis l'interface ([#114](https://github.com/dascritch/machincast/issues/114)). Faux par défaut. Un fichier introuvable garde la sienne. |
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

- `type = fichier` ⇒ `emplacement` renseigné, `url_stream` et `feed_id` vides.
- `type = stream` ⇒ exactement un de `url_stream` ou `feed_id` renseigné.
- `secours_evenement_id` ⇒ `type = stream`, et l'événement désigné est de priorité `secours` (déclencheur en base, qui empêche aussi de changer la priorité d'un événement de secours désigné). Supprimer l'événement vide le champ.

Pas de champ format ni fréquence d'échantillonnage : l'échantillonnage peut varier dans un fichier lossy et n'a pas d'utilité en lossless.

#### `feeds`

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
| `duree_min`, `duree_max` | Durées minimale et maximale, facultatives (`NULL`), des sonores de la banque : strictement positives, la minimale au plus égale à la maximale. Un sonore qui en sort est signalé par l'interface, dans la fiche de cette banque et parmi les relations du sonore, jamais ailleurs ([#210](https://github.com/dascritch/machincast/issues/210)), et retiré de la banque par l'indexation ([#195](https://github.com/dascritch/machincast/issues/195), [§ 6.2](#62-indexation-des-répertoires-de-banques)) ; la diffusion n'en tient pas compte ([#147](https://github.com/dascritch/machincast/issues/147), migration `0006.banques-durees`). Elles se comparent à la durée complète du fichier, jamais à celle sans ses blancs. |
| `detection_blancs` | Les sonores joués via la banque le sont sans leurs blancs détectés ([#146](https://github.com/dascritch/machincast/issues/146), migration `0008.detection-blancs`, [§ 5.1](#51-lecture-audio)). Faux par défaut. |
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
| `priorite` | `secours` < `fil_musical` < `emission` < `special` ; `secours` est hors grille ([#16](https://github.com/dascritch/machincast/issues/16)) : un événement de secours ne passe jamais à l'antenne par la grille, seulement à la place d'un stream tombé ([§ 4.7](#47-streams)). |
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
- Valeurs énumérées : types `ENUM` PostgreSQL (`type_sonore`, `mode_banque`, `priorite_evenement`, `jour_semaine`, `type_ligne_airplay`, `niveau_log`, `etat_sonore`, `regle_crossfade`). Ajouter une valeur se fait par `ALTER TYPE … ADD VALUE` dans une nouvelle migration ; en retirer une demande de recréer le type. Leur ordre de déclaration permet les comparaisons : `secours < fil_musical < emission < special`, `lundi < … < dimanche`.
- `jours_recurrence` : tableau de `jour_semaine`. La récurrence est calculée en heure locale par le binaire lecture.
- `metadonnees_musicales` : objet JSON (`jsonb`), jamais un tableau ni une valeur nulle.
- Un événement ne peut pas avoir de fin sans début.
- Positions dans `banques_sonores`, `evenements_elements` et `sequences_elements` : uniques par banque, par événement ou par séquence, vérifiées en fin de transaction pour permettre de réordonner.
- Suppressions : un lien de banque, un élément d'événement ou un élément de séquence disparaît avec la banque, le sonore, la séquence ou l'événement qu'il référence, et quand l'interface le marque supprimé ([§ 8.9](#89-suppression)) ; `airplay` et `log` gardent leurs lignes, avec la référence passée à vide. Un feed utilisé par un sonore ne peut pas être supprimé. La validation préalable des suppressions est faite par l'interface ([§ 8.9](#89-suppression)).
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
| `feeds` | lire | — | lire, insérer, modifier, supprimer |
| `banques` | lire | lire | lire, insérer, modifier, supprimer |
| `banques_repertoires` | — | lire | lire, insérer, modifier, supprimer |
| `banques_sonores` | lire | lire, insérer, supprimer ([#195](https://github.com/dascritch/machincast/issues/195)) | lire, insérer, modifier, supprimer |
| `evenements` | lire | — | lire, insérer, modifier, supprimer |
| `evenements_elements` | lire | — | lire, insérer, modifier, supprimer |
| `sequences` | lire | — | lire, insérer, modifier, supprimer |
| `sequences_elements` | lire | — | lire, insérer, modifier, supprimer |
| `airplay` | lire, insérer | — | lire |
| `log` | insérer (sans `RETURNING`) | — | lire |

L'indexation ne supprime aucun sonore : un fichier disparu fait passer son sonore à l'état `supprime`. Elle ne supprime que des lignes de `banques_sonores`, pour retirer d'une banque les sonores hors de ses durées ([#195](https://github.com/dascritch/machincast/issues/195), [§ 6.2](#62-indexation-des-répertoires-de-banques)). Quand l'interface supprime un élément, les références dans `airplay` et `log` passent à vide avec les droits du propriétaire des tables ; l'interface n'a pas besoin de droit d'écriture sur ces deux tables.

## 4. Règles d'ordonnancement

### 4.1 Choix de l'événement actif

1. À tout instant, l'événement actif est celui de plus haute priorité dont la plage couvre l'instant, sauf s'il s'est terminé plus tôt pour cette occurrence (liste épuisée d'un événement sans fin, ou banque « ne pas répéter » sans autre élément jouable, voir [§ 4.4](#44-choix-dun-sonore-dans-une-banque)).
2. Deux événements de même priorité ne doivent pas se chevaucher : l'interface l'interdit à la saisie (`machincast.lecture.grille.chevauchement`, [#32](https://github.com/dascritch/machincast/issues/32)). Deux occurrences se chevauchent si elles ont un instant commun ; une occurrence sans fin ne compte que par son début ; un fil musical permanent et un événement de secours ne chevauchent rien. À priorité égale, une occurrence sans fin, ou un fil musical permanent, laisse la place à toute occurrence qui a commencé après elle, et reprend ensuite : un fil permanent sert de fond. Si deux occurrences bornées se chevauchent quand même, le binaire joue le **dernier modifié en base**.
3. Plusieurs fils musicaux peuvent coexister selon l'heure (nuit, jour), régis par leur récurrence.
4. Le changement d'heure ne fait l'objet d'aucune règle particulière : la diffusion est toujours en fil musical à cette heure de la nuit.
5. Occurrences ([#12](https://github.com/dascritch/machincast/issues/12), `machincast.lecture.grille`) : `debut` et `fin` sont ceux de la première occurrence. Sans récurrence, l'événement couvre `[debut, fin[`, ou `[debut, ∞[` sans fin. Avec récurrence, il revient chaque jour coché à partir du jour de `debut`, à l'heure murale de `debut`, jusqu'à l'heure murale de `fin` autant de jours plus tard que la première occurrence : un événement peut passer minuit, et c'est le jour de son début qui compte. Le poste travaille en heure locale, celle de Paris : le calcul se fait en heure murale, et un événement garde son heure au changement d'heure. Une occurrence sans fin couvre l'instant jusqu'à ce que sa liste soit épuisée ; le binaire la déclare alors terminée, et la suivante repart normalement.

### 4.2 Transitions

- **Début d'un événement** : il coupe **net** le sonore en cours, quel que soit le sonore. Un événement sans rien de jouable à son début (liste vide, ou rien de jouable dedans) ne coupe rien : il se termine aussitôt, et l'événement de priorité inférieure garde l'antenne ; si c'est celui du sonore en cours, ce sonore continue, et ni la socket d'état ni l'interface n'annoncent de coupure ([#253](https://github.com/dascritch/machincast/issues/253)).
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

- Adresse : `url_stream`, ou l'`url` du feed. L'airplay recopie cette adresse dans `emplacement`.
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

### 4.9 Interruption manuelle

Le responsable d'antenne peut sauter au sonore suivant, sauter après la séquence en cours, ou couper l'événement par le fil musical ([#104](https://github.com/dascritch/machincast/issues/104), [#228](https://github.com/dascritch/machincast/issues/228)). L'interface envoie la demande sur la socket d'état ([§ 5.4](#54-socket-détat)), depuis le menu « Diffusion » ([§ 8.11](#811-menu)) ; `Machin_lecture` la traite au début de son pas suivant (`Diffusion.interrompre`).

- **Arrêt du sonore** : le sonore en cours est coupé aussitôt, avec un fondu de la durée du crossfade de fin par défaut de la configuration (`crossfades.fin`), ou net sans lui, quels que soient ses propres crossfades. Le suivant monte pendant le crossfade de début par défaut (`crossfades.debut`), ou démarre à plein volume sans lui ; il démarre aussitôt, sauf s'il n'a pas de montée sous un fondu : il attend alors la fin du fondu. Le passage coupé se termine sans incident : c'est une opération normale.
- **Sauter au sonore suivant** (`sonore`) : le suivant est le prochain sonore annoncé ([§ 4.10](#410-playlist-immédiate)), s'il est encore jouable : les sonores à venir avancent d'un cran. Sinon, ou si le prochain sonore n'est annoncé que pour après une coupure, c'est celui que l'ordonnanceur choisit, et les sonores à venir sont recalculés.
- **Sauter après la séquence** (`sequence`) : le reste de la séquence n'est pas joué (`Ordonnanceur.abandonner_la_sequence`). Le suivant est le premier sonore annoncé, prochain ou à venir, qui ne continue pas la séquence ; les sonores à venir qui le suivent sont gardés. Si aucun n'est annoncé, ou qu'il n'est plus jouable, l'ordonnanceur choisit l'élément qui suit la séquence, et les sonores à venir sont recalculés. Hors d'une séquence, la demande est ignorée.
- **Couper l'événement par le fil musical** (`evenement`) : chaque occurrence active au-dessus du fil musical se termine, comme une liste épuisée, jusqu'à sa fin prévue (`Ordonnanceur.rendre_au_fil_musical`) : un spécial et l'émission qu'il recouvre ; un stream tombé n'est plus reconnecté. Une séquence en cours est abandonnée, et le fil musical prend aussitôt l'antenne, à l'élément qui suit son dernier joué ; les sonores à venir sont recalculés. Dans le fil musical, la demande est ignorée. Une occurrence terminée ainsi n'est retenue qu'en mémoire : un redémarrage de `Machin_lecture` la rend à l'antenne, comme une occurrence terminée plus tôt.
- **Log** : l'info `interruption manuelle`, avec ce qui est interrompu : `du sonore « Café à minuit »`, `de la séquence « Pub », dans « Matinale »`, `de l'événement « Matinale »`, et le sonore et l'événement en cours. Sans rien à l'antenne, hors d'une séquence pour une séquence, ou dans le fil musical pour un événement, la demande est ignorée, sans ligne de log, et signalée dans le journal du binaire (`interruption manuelle ignorée : …`).

### 4.10 Playlist immédiate

Après le prochain sonore, `Machin_lecture` prévoit les 5 sonores qui seront normalement diffusés ensuite ([#228](https://github.com/dascritch/machincast/issues/228), `Diffusion.a_venir`, `A_VENIR`). La socket d'état les publie ([§ 5.4](#54-socket-détat)), et l'accueil de l'interface les montre au-dessus de l'airplay ([§ 8.1](#81-écran-par-défaut)).

- **Prévision** : chaque sonore à venir est choisi comme le serait le prochain, à l'heure où le précédent appellera son suivant : au début de son crossfade de fin, à la coupure par un événement qui commence ([§ 4.2](#42-transitions)), ou, pour un stream, à la fin de son événement. Les sonores prévus comptent comme joués pour les suivants : position dans les listes et les séquences, cycles des banques, compteurs de lectures. La prévision ne laisse aucune trace (`Ordonnanceur.prevision`, `HistoriquePrevu`) : rien n'est consigné, ni en base ni dans le log, et l'état de l'ordonnanceur est rétabli, sauf le hasard. La liste s'arrête sur un silence, ou après un sonore dont la fin est inconnue (un stream sans fin d'événement).
- **Engagement** : les sonores à venir sont ceux qui passeront, dans cet ordre, tirages au hasard compris. À chaque changement de sonore, dans la situation attendue (c'est le prochain sonore qui a démarré, la grille n'a pas changé, et la coupure du sonore en cours est celle qui était prévue), le premier sonore à venir devient le prochain, et un cinquième est prévu au bout de la liste ; les occurrences que sa décision avait terminées le sont pour de bon (`Ordonnanceur.engager`), et ce qu'elle aurait consigné, comme un élément sauté, l'est alors (`Prevu.consignes`).
- **Imprévu** : sur une interruption manuelle ([§ 4.9](#49-interruption-manuelle)), sauf le saut au sonore annoncé, une coupure qui n'était pas prévue, une grille modifiée (événements, leurs listes ou les séquences, `EMPREINTE_DE_LA_GRILLE`), un stream tombé, ou un sonore annoncé qui n'est plus jouable à son tour, le prochain sonore et les 5 sonores à venir sont recalculés aussitôt que le sonore suivant démarre. Un sonore annoncé qui n'est plus jouable (désactivé, expiré, fichier introuvable) est remplacé par la décision prise à son tour.
- **Coupure** : à la coupure par un événement, ou quand le sonore coupé finit plus tôt, le sonore annoncé pour cet événement est joué, même tiré au hasard, s'il est encore valable.

## 5. Binaire lecture

`Machin_lecture` ne fait que lire les événements et les jouer. Il lit le fichier de configuration à son lancement et tourne comme service systemd. Sans périphérique d'antenne (`audio.peripherique`), il refuse de diffuser, sauf sur la sortie `factice` ([#116](https://github.com/dascritch/machincast/issues/116)).

Boucle de diffusion ([#88](https://github.com/dascritch/machincast/issues/88), `machincast.lecture.diffusion`) : connecté à la base de production avec le rôle `machincast_lecture`, le binaire consigne son démarrage, puis avance par pas d'environ 50 ms, à l'heure de son horloge. À chaque pas : les voies finies terminent leur passage dans l'airplay ; pendant un sonore, l'ordonnanceur dit s'il faut couper net ; au début du crossfade de fin du sonore en cours, il donne le suivant, lancé aussitôt s'ils se superposent, sinon à la fin du sonore en cours ; sans rien sur la sortie, le suivant démarre, ou c'est le silence. SIGTERM et SIGINT demandent l'arrêt, pris en compte à la fin du pas : les passages en cours se terminent sans incident, et l'arrêt est consigné. Base injoignable, perdue, ou sortie audio impossible à créer : code de sortie 1.

### 5.1 Lecture audio

- Bibliothèque : GStreamer via PyGObject (lecture, crossfade, streams).
- Sortie au choix dans la configuration : ALSA, PulseAudio ou PipeWire, chacune fournie par son greffon GStreamer (`gstreamer1.0-alsa`, `gstreamer1.0-pulseaudio`, `gstreamer1.0-pipewire`). La sortie `factice` ne joue aucun son, pour les tests et les essais (`machincast.audio`).
- L'heure courante est lue par une horloge injectable (`machincast.horloge`) et les tirages aléatoires par un générateur à graine (`machincast.hasard`).
- Crossfade selon `crossfade_debut` et `crossfade_fin` de chaque sonore ([#15](https://github.com/dascritch/machincast/issues/15), `machincast.lecture.moteur`) : le sonore monte de 0 à plein volume pendant `crossfade_debut` ; il s'éteint pendant ses `crossfade_fin` dernières secondes, et le sonore suivant démarre à ce moment-là. Deux sonores ne se superposent que si le sortant a un `crossfade_fin` et l'entrant un `crossfade_debut` : si l'un des deux vaut 0, le sortant joue jusqu'au bout à plein volume, puis l'entrant démarre à plein volume (décidé en relecture de [PR #86](https://github.com/dascritch/machincast/pull/86)). Chaque sonore joue dans sa propre voie (pipeline GStreamer) : deux voies se superposent pendant un crossfade, et la sortie les mélange (en ALSA, un périphérique qui mélange, comme `default`). La coupure nette arrête toutes les voies aussitôt.
- Le crossfade retenu, côté par côté ([#143](https://github.com/dascritch/machincast/issues/143), [#145](https://github.com/dascritch/machincast/issues/145), `machincast.lecture.diffusion.crossfade`) : celui que la banque qui a fourni le sonore impose ; sinon celui du sonore, s'il est paramétré (0 seconde en est un) ; sinon celui que la banque applique à défaut ; sinon celui de la configuration (`crossfades.debut`, `crossfades.fin`) ; sinon aucun. Un sonore placé directement dans un événement ou une séquence n'a pas de banque : il garde les siens, ou prend ceux de la configuration, même s'il figure dans une banque qui les impose. Les séquences et les événements n'ont pas de réglage de crossfade. L'enchaînement, l'heure estimée du prochain sonore sur la socket d'état et la simulation suivent les mêmes crossfades.
- Détection de blanc ([#146](https://github.com/dascritch/machincast/issues/146), `machincast.lecture.fondus`, `machincast.lecture.moteur`) : un fichier dont le sonore active la détection (`sonores.detection_blancs`), ou fourni par une banque qui l'active (`banques.detection_blancs`), est joué sans ses blancs détectés. Ses fondus se placent par rapport à ses bornes détectées ([#234](https://github.com/dascritch/machincast/issues/234), `fondus.placer`) : le fade-in « commence », « est en cours » ou « se termine » au début détecté (il en part, il en part la moitié de sa durée avant, ou toute sa durée avant ; par défaut, il se termine au début détecté) ; le fade-out « commence », « est en cours » ou « se termine » à la fin détectée (par défaut, il commence à la fin détectée). Les positions viennent des préférences (`crossfades.position_entree`, `crossfades.position_sortie`), pour tous les sonores : une banque ne règle que la présence et la durée des crossfades. La lecture va du début du fade-in à la fin du fade-out : elle s'étend dans les blancs d'autant que les fondus y débordent. Un fondu qui sortirait du fichier n'est pas joué hors du fichier : la lecture commence, ou s'arrête, au bord du fichier, au volume qu'aurait le fondu à cet instant (`Parametres.volume_de_depart`, `volume_d_arrivee`, `moteur.enveloppe`), et le fondu garde sa pente. La voie pré-lit le fichier, puis borne sa lecture par une recherche (seek) ; sa position, son enveloppe et ses fondus se comptent depuis le début de sa lecture. La durée jouée est celle de la partie jouée : l'enchaînement, l'heure estimée du prochain sonore sur la socket d'état et la simulation la suivent. Un côté sans blanc détecté (`NULL`) a son blanc nul ; des blancs qui ne laissent rien du sonore sont ignorés, et le sonore joué en entier, ses fondus aux bouts du fichier, comme un sonore joué avec ses blancs. Un stream n'est jamais rogné. Le fichier n'est jamais modifié.
- Avant de jouer un fichier, le binaire compare sa date de modification et sa taille avec la base. En cas d'écart, il le consigne dans le log (`alerte`, `fichier modifié`) et joue le fichier ; c'est l'indexeur qui mettra la base à jour. Un fichier introuvable n'est pas joué (`incident`, `fichier introuvable`) : l'ordonnanceur l'écarte pendant une heure, comme un sonore non jouable, et passe au suivant.
- S'il n'a aucun élément à lire dans le fil musical, il émet un silence et lève une alerte dans le log.
- Analyse au dernier moment ([#181](https://github.com/dascritch/machincast/issues/181), `machincast.lecture.analyse`) : au début de chaque sonore, quand il réserve le suivant, le binaire regarde si ce prochain sonore est un fichier jamais vérifié en entier (`verifie_le` vide), ou dont le fichier a changé depuis (date de modification ou taille, `machincast.empreinte.modifie`). Si c'est le cas, il lance `Machin_indexation --audit-complet --sonore N`, par son propre Python et avec sa configuration, dans un processus détaché de sa session, sans fenêtre, et ne l'attend jamais : un indexeur qui plante, ou pas encore fini, ne retarde ni ne bloque la lecture. Il le consigne (`info`, `analyse du prochain sonore`) ; une commande qui ne peut pas être lancée donne l'alerte `analyse impossible`. Un même sonore n'est pas redemandé avant une heure. Un stream n'est jamais analysé. La simulation ne lance aucune analyse.

### 5.2 Écritures

- `airplay` : une ligne au début et une ligne à la fin de chaque passage (insertions seules), par `machincast.lecture.enregistrement` ([#17](https://github.com/dascritch/machincast/issues/17)). La ligne de fin recopie la ligne de début : l'artiste et le titre restent ceux du moment du passage, même modifiés entre-temps. Une coupure nette n'est pas un incident (`sans_incident` vrai) ; une lecture interrompue par une erreur, si.
- `log` : toutes les opérations, normales comme incidents, avec l'heure de l'horloge du binaire. Natures déjà consignées : `démarrage` (info), `arrêt` (info), `début d'événement`, `fin d'événement`, `début de séquence` et `fin de séquence` (info, [#153](https://github.com/dascritch/machincast/issues/153)), `coupure nette` (info), `interruption manuelle` (info, [§ 4.9](#49-interruption-manuelle)), `sonore expiré` (info), `élément sauté` (info), `reconnexion abandonnée` (info), `silence` (alerte), `événement terminé plus tôt` (alerte), `sortie inaccessible` (alerte), `socket d'état indisponible` (alerte), `fichier modifié` (alerte), `fichier introuvable` (incident), `lecture interrompue` (incident), `flux tombé` (incident), `reprise du flux` (incident), `analyse du prochain sonore` (info) et `analyse impossible` (alerte), [#181](https://github.com/dascritch/machincast/issues/181).
- Débuts et fins à l'antenne ([#153](https://github.com/dascritch/machincast/issues/153), `Diffusion._noter_l_antenne`) : avant chaque passage qui commence, et à l'arrêt, le binaire note, au niveau info et avec l'événement, la fin de la séquence puis de l'événement que le passage ne continue pas, puis le début des siens. Un événement commence avec son premier passage (`« Journal », émission, de 20:00 à 20:30`, `« Élections », spécial, depuis 20:00`, `« Continue », fil musical, permanent`) et finit quand un passage d'un autre événement commence, coupure comprise, ou à l'arrêt (`« Journal »`). Une séquence (`« Pub », dans « Continue »`) commence avec un passage qui ne suit pas le précédent un élément plus loin dans la même séquence : une séquence qui revient aussitôt recommence. Les heures sont celles de l'antenne ; un silence ne termine rien. La simulation les note de même dans son log.
- `sonores.etat` : passage à `expire` ([§ 4.5](#45-sonore-jouable)).

### 5.3 Modules de sortie

| Module | Visibilité | Contenu |
| --- | --- | --- |
| stdout | privé | Sonores lancés : une ligne d'information `à l'antenne : artiste – titre (événement)` par passage qui commence, précédée comme toute ligne de son heure ISO 8601 (`machincast.journal`, [#253](https://github.com/dascritch/machincast/issues/253)). Débuts et fins d'événements et de séquences, comme dans le log : `début d'événement : « Journal », émission, de 20:00 à 20:30` ([#153](https://github.com/dascritch/machincast/issues/153)). |
| stderr | privé | Alertes et incidents du log (`alerte : nature : message`), erreurs du binaire. |
| CSV | privé | Airplay, un fichier par jour, nommé avec la date du jour au format ISO 8601. Une ligne par passage terminé : `debut;fin;duree;artiste;titre;emplacement;evenement;sequence;banque;sans_incident` (la colonne `sequence`, nom interne de la séquence qui a fait jouer le sonore, depuis [#99](https://github.com/dascritch/machincast/issues/99)), heures `AAAA-MM-JJ HH:MM:SS`, durée `HH:MM:SS`, `oui` ou `non`. Séparateur `;`, UTF-8 avec BOM, en-tête à la création ; jamais réécrit. |
| .pls | privé | Les 100 derniers fichiers joués, streams compris par leur adresse, du plus ancien au plus récent, avec artiste et titre ; réécrit à chaque passage. |
| HTML | public | Le sonore à l'antenne et les 20 précédents, du plus récent au plus ancien, avec masquage appliqué et sans emplacement de fichier ; page statique sans JavaScript, rafraîchie toutes les 30 s, réécrite à chaque passage. |

Les fichiers .pls et HTML sont remplacés d'un coup : un lecteur ne voit jamais une page à moitié écrite. Une sortie qui ne peut pas être écrite est consignée une fois dans le log (`sortie inaccessible`, alerte) et n'arrête pas la diffusion ; elle l'est de nouveau si elle redevient inaccessible après une écriture réussie. Choix décidés avec le ticket ([commentaire](https://github.com/dascritch/machincast/issues/19#issuecomment-6198038989)).

Un module privé indique tous les sonores. Un module public applique le masquage ([§ 4.8](#48-métadonnées-publiques-et-masquage)).

### 5.4 Socket d'état

Le binaire expose une socket Unix donnant à l'interface : état de marche, sonore en cours (début, durée, fin estimée, progression), prochain sonore (début et fin estimés, durée, indicateur « sain »), et les 5 sonores à venir après lui ([§ 4.10](#410-playlist-immédiate)).

Mise en œuvre ([#20](https://github.com/dascritch/machincast/issues/20), `machincast.lecture.etat`) :

- **Chemin** : `lecture.socket_etat` dans la configuration ; par défaut `$XDG_RUNTIME_DIR/machincast/lecture.sock`, ou `/run/user/<uid>/machincast/lecture.sock` sans cette variable. Le répertoire est en `0700` et la socket en `0600` : seul le compte qui diffuse les lit. Une socket déjà ouverte par un autre `Machin lecture` refuse la seconde diffusion (code de sortie 1, « un autre Machin lecture diffuse déjà ») ; une socket laissée par un binaire arrêté brutalement est remplacée. Une socket impossible à créer pour une autre raison est consignée (`socket d'état indisponible`, alerte), et la diffusion continue sans elle.
- **Protocole** : à la connexion, le binaire envoie le dernier état, puis chaque nouvel état, une ligne JSON en UTF-8 par état. Il publie à chaque changement, et au moins chaque seconde pendant un sonore pour la progression. Un client lent ou qui se déconnecte ne gêne jamais la diffusion.
- **Demandes** ([#104](https://github.com/dascritch/machincast/issues/104)) : un client peut envoyer des demandes d'interruption manuelle ([§ 4.9](#49-interruption-manuelle)), une ligne JSON en UTF-8 par demande : `{"commande": "interrompre", "element": "sonore"}`, ou `"sequence"`, ou `"evenement"`. Un fil par client les lit ; la diffusion les traite au début de son pas suivant, dans l'ordre d'arrivée. Une demande illisible, inconnue, ou de plus de 4096 octets est ignorée et signalée dans le journal du binaire (`demande ignorée sur la socket d'état`). Seul le compte qui diffuse peut ouvrir la socket : il n'y a pas d'autre contrôle. À l'arrêt, un dernier message `"etat": "arret"` part, puis la socket est fermée et effacée.
- **Version** : le champ `version` vaut 1. Il change quand un champ change de sens ou disparaît ; l'ajout d'un champ ne le change pas.
- **Prochain sonore** : il est réservé dès le début du sonore en cours (décidé en relecture de [#20](https://github.com/dascritch/machincast/issues/20)) : c'est lui qui est joué ensuite, tiré au hasard compris. La réservation tombe si un événement coupe la diffusion, si son événement n'est plus actif, ou s'il n'est plus jouable (désactivé, expiré) : le suivant est alors choisi à ce moment-là. Une réservation sans rien de jouable ne déclenche pas l'alerte de silence, qui vient à la fin du sonore en cours. Pendant un stream qui s'éteindra à la fin de son événement, le prochain sonore est choisi pour cette fin ([#242](https://github.com/dascritch/machincast/issues/242)) : c'est celui de l'événement qui reprendra l'antenne, et non le stream lui-même, que son émission, qui boucle, redonnerait à son début.

Champs d'un message :

| Champ | Type | Sens |
| --- | --- | --- |
| `version` | entier | Version du format : 1. |
| `horodatage` | date ISO 8601 | Heure de l'état, à l'horloge du binaire. |
| `etat` | texte | `diffusion` (un sonore est sur la sortie), `silence` (rien à diffuser) ou `arret` (dernier message, la diffusion s'arrête). |
| `en_cours` | objet ou `null` | Sonore à l'antenne ; `null` en silence et à l'arrêt. |
| `prochain` | objet ou `null` | Sonore réservé pour la suite ; `null` s'il n'y en a pas. |
| `a_venir` | liste d'objets | Sonores prévus après le prochain, dans l'ordre, 5 au plus ([§ 4.10](#410-playlist-immédiate), [#228](https://github.com/dascritch/machincast/issues/228), sans changer la version) ; vide sans prochain sonore, en silence et à l'arrêt. Chacun a les champs de `prochain`. |

Champs communs à `en_cours`, `prochain` et à chaque sonore de `a_venir` :

| Champ | Type | Sens |
| --- | --- | --- |
| `sonore` | entier | Identifiant du sonore. |
| `type` | texte | `fichier` ou `stream`. |
| `artiste`, `titre` | texte ou `null` | Métadonnées de la base, jamais masquées : l'interface est privée. |
| `evenement` | texte | Nom interne de l'événement qui le joue (ou de l'événement de secours). |
| `emplacement` | texte ou `null` | Chemin du fichier, ou adresse du stream (directe ou de son feed), comme dans l'`airplay`. Ajouté en relecture de [PR #106](https://github.com/dascritch/machincast/pull/106), sans changer la version. |
| `duree` | nombre ou `null` | Durée en secondes ; `null` pour un stream, dont la durée est inconnue. |
| `fin_estimee` | date ISO 8601 ou `null` | Fin prévue, `null` quand la durée ou le début sont inconnus. Pour le sonore en cours qu'un événement coupera, l'instant de la coupure, même pour un stream ([#169](https://github.com/dascritch/machincast/issues/169)). Pour un stream que rien ne coupe, la fin de son événement, où il s'éteint, `null` sans elle ([#242](https://github.com/dascritch/machincast/issues/242)). |
| `evenement_id` | entier | Identifiant de l'événement ([#144](https://github.com/dascritch/machincast/issues/144), sans changer la version). |
| `evenement_priorite` | texte | Priorité de l'événement : `special`, `emission`, `fil_musical` ou `secours` ([#228](https://github.com/dascritch/machincast/issues/228), sans changer la version). |
| `evenement_debut`, `evenement_fin` | date ISO 8601 ou `null` | Début et fin de l'occurrence de l'événement, en heure murale du poste, sans fuseau ; `null` pour un fil musical permanent, et pour la fin d'une occurrence sans fin. |
| `sequence`, `sequence_id` | texte, entier ou `null` | Séquence qui joue le sonore, nom interne et identifiant ; `null` hors d'une séquence. |
| `banque`, `banque_id` | texte, entier ou `null` | Banque qui a fourni le sonore ; `null` pour un sonore placé directement dans la liste. |

Champs propres à `en_cours` : `debut` (date ISO 8601 du début du passage), `position` (secondes jouées), `progression` (de 0 à 1, `null` pour un stream) et `texte_public` ([#144](https://github.com/dascritch/machincast/issues/144)) : ce que la page publique affiche du passage, masquage appliqué ([§ 4.8](#48-métadonnées-publiques-et-masquage)) ; `null` si le passage n'est pas encore dans l'airplay. `coupe_par` et `coupe_par_id` ([#169](https://github.com/dascritch/machincast/issues/169)) : le nom interne et l'identifiant de l'événement qui commencera pendant le sonore et le coupera net ([§ 4.2](#42-transitions)), `null` s'il ira jusqu'à sa fin. La coupure est cherchée au début du sonore, jusqu'au début de son crossfade de fin ; pour un stream, jusqu'à la fin de son occurrence, et 12 heures au plus. Le contexte d'un sonore (événement, séquence, banque, texte public) est lu une fois par sonore, pas à chaque message.

Champs propres à `prochain` et aux sonores de `a_venir` : `debut_estime` (date ISO 8601 : au début du crossfade de fin du sonore précédent s'ils se superposent, à sa fin sinon ; à l'instant de la coupure si un événement coupe le sonore précédent ; après un stream, à la fin de son événement, ou après son crossfade de fin sans superposition ; `null` après un sonore dont la fin est inconnue). Leur `fin_estimee` est l'instant de la coupure si un événement coupera le sonore, sinon son début estimé plus sa durée. Puis `sain` (indicateur du [§ 4.6](#46-sonore-sain) : `true` ou `false`, `null` pour un stream, qui n'est pas testé automatiquement). Après une coupure annoncée, le prochain sonore est **anticipé** ([#169](https://github.com/dascritch/machincast/issues/169)) : c'est celui que choisira la décision prise à la coupure, si rien ne change d'ici là, tirage au hasard compris. L'anticipation ne laisse aucune trace : rien n'est consigné, aucune occurrence n'est terminée et le hasard n'avance pas ; c'est la décision prise à la coupure qui choisit le sonore et consigne ce qu'il faut, comme un élément sauté.

Exemple, présenté ici sur plusieurs lignes ; le binaire envoie chaque message sur une seule :

```json
{"version": 1, "horodatage": "2026-10-14T20:00:30+02:00", "etat": "diffusion",
 "en_cours": {"sonore": 12, "type": "fichier", "artiste": "Les Gaufres", "titre": "Café à minuit",
  "emplacement": "/srv/musique/Les Gaufres/Café à minuit.flac", "evenement": "Fil de jour",
  "debut": "2026-10-14T20:00:00+02:00", "duree": 214.5, "fin_estimee": "2026-10-14T20:03:34.500000+02:00", "coupe_par": null, "coupe_par_id": null, "position": 30.0, "progression": 0.14},
 "prochain": {"sonore": 31, "type": "fichier", "artiste": null, "titre": "Jingle", "emplacement": "/srv/habillage/jingle.flac",
  "evenement": "Fil de jour",
  "debut_estime": "2026-10-14T20:03:30.500000+02:00", "duree": 8.0, "fin_estimee": "2026-10-14T20:03:38.500000+02:00", "sain": true},
 "a_venir": [{"sonore": 18, "type": "fichier", "artiste": "Les Gaufres", "titre": "Le matin",
  "emplacement": "/srv/musique/Les Gaufres/Le matin.flac", "evenement": "Fil de jour",
  "debut_estime": "2026-10-14T20:03:38.500000+02:00", "duree": 180.0, "fin_estimee": "2026-10-14T20:06:38.500000+02:00", "sain": true}]}
```

### 5.5 Mode simulation

Sur option de lancement, le binaire simule la diffusion entre deux dates et heures :

- aucune écriture en base, aucune sortie sonore ;
- l'état de départ (positions séquentielles, cycles aléatoires, compteurs de lectures, séquence en cours) est lu depuis `airplay`, puis tenu en mémoire pendant toute la simulation ; les règles sont celles de la diffusion, séquences comprises ;
- une graine (seed) rend le hasard reproductible, notamment pour les tests ;
- seules des sorties .csv, .pls et .html sont produites, nommées par défaut avec un préfixe `simulation` suivi des dates de début et de fin, nommage modifiable par paramètre.

Mise en œuvre ([#21](https://github.com/dascritch/machincast/issues/21), `machincast.lecture.simulation`, choix notés sur le [ticket](https://github.com/dascritch/machincast/issues/21#issuecomment-6199262518)) :

- **Commande** : `Machin_lecture --simulation DEBUT FIN [--graine N] [--nom NOM] [--repertoire REPERTOIRE]`. Les dates sont en ISO 8601, en heure du poste, et la fin suit le début. Code de sortie 2 sinon, et pour `--graine`, `--nom` ou `--repertoire` sans `--simulation`.
- **Aucune écriture en base**, au sens du cahier des charges (« pas une seule entrée ») : la simulation ouvre une seule transaction `REPEATABLE READ, READ ONLY` (`lecture_seule`), annulée à la fin. PostgreSQL y refuse toute écriture, et l'état de départ est celui de son ouverture.
- **État en mémoire** : la logique de lecture lit et écrit l'historique par un `Historique` (`machincast.lecture.historique`), la base en diffusion (`EN_BASE`) ou la mémoire en simulation (`HistoriqueSimule`). En mémoire, les passages, le log et les expirations simulés s'ajoutent à ce que la base contient : compteurs de lectures, cycles des banques, dernier élément de chaque événement.
- **Aucune sortie sonore** : `MoteurSimule` ne crée aucun pipeline GStreamer. La diffusion (`Diffusion`, la même qu'à l'antenne) avance d'échéance en échéance : fin prévue d'une voie, début du crossfade de fin du sonore en cours, prochain début ou fin d'une occurrence (`grille.prochain_changement`), fin de la période ; en silence, toutes les minutes.
- **Durées** : celles de la base. Un stream n'est pas contacté et tient jusqu'à la fin de son événement ou jusqu'à une coupure.
- **Sorties** : `<nom>.csv`, `<nom>.pls` et `<nom>.html` dans le répertoire de `sorties.csv`, ou dans celui de `--repertoire` ([#37](https://github.com/dascritch/machincast/issues/37)). Le nom par défaut est `simulation-AAAA-MM-JJTHHMM-AAAA-MM-JJTHHMM`. Ce sont trois fichiers pour toute la période. L'artiste et le titre y sont masqués comme sur la page publique ([§ 4.8](#48-métadonnées-publiques-et-masquage)), et l'emplacement de chaque fichier, donné dans les trois, permet de vérifier ce qui est joué (décidé en relecture de [PR #95](https://github.com/dascritch/machincast/pull/95)). La page HTML liste les alertes et incidents simulés, puis les passages, avec leur emplacement. Les alertes et incidents vont aussi sur la sortie d'erreur, préfixés de `simulation :`.

## 6. Binaire indexation

`Machin_indexation` est déclenché depuis l'interface, par son menu ([§ 8.11](#811-menu), [#38](https://github.com/dascritch/machincast/issues/38)), dans un processus à part avec la fenêtre de son journal (`--fenetre`, [#120](https://github.com/dascritch/machincast/issues/120)), ou depuis un terminal. Une seule indexation à la fois sur une base : elle tient un verrou consultatif de PostgreSQL (`pg_try_advisory_lock`) pendant tout son passage, et une deuxième s'arrête aussitôt, sans rien toucher (code de sortie 1). Une indexation peut être arrêtée entre deux fichiers ; le travail fait est gardé. Un cron ou un timer systemd pourra être ajouté plus tard selon les retours du terrain.

### 6.0 Modes d'indexation

Deux modes ([#69](https://github.com/dascritch/machincast/issues/69)).

- **Indexation rapide**, par défaut : un nouveau fichier est enregistré à l'état `apercu`, sans être décodé ([§ 6.2](#62-indexation-des-répertoires-de-banques)). Seuls les sonores en aperçu, et ceux dont le fichier a changé depuis sa dernière vérification (date de modification ou taille, [#10](https://github.com/dascritch/machincast/issues/10)), sont ensuite décodés et leurs tags lus. Pour les autres, seule la présence du fichier est contrôlée : un fichier disparu passe quand même son sonore à `supprime`. Un fichier jamais vérifié, sans date ni taille enregistrées, n'est pas comparé.
- **Audit complet**, option `--audit-complet` : les sonores de type fichier sont décodés, comme décrit ci-dessous ; lui seul mesure les blancs ([#146](https://github.com/dascritch/machincast/issues/146), [§ 6.1](#61-vérification-des-sonores-existants-hors-streams)). Il saute un sonore déjà audité au même seuil de blanc (`audite_le`, `audit_seuil`) dont le fichier n'a pas changé depuis : date de modification au plus égale à celle de l'audit, date et taille égales à celles enregistrées ([#206](https://github.com/dascritch/machincast/issues/206), `verification.deja_audite`). Il ne décode donc que les sonores jamais audités, ceux dont le fichier a changé, et tous après un changement de `blancs.seuil`. Une ligne d'information compte les sonores sautés (« 120 sonores déjà audités au seuil de -40 dB, aux fichiers inchangés : non décodés ; --forcer décode tous les sonores ») ; le bilan ne les compte pas parmi les vérifiés. Un fichier disparu est toujours repéré. La règle vaut pour tout audit complet : général, demandé ou d'un seul sonore. **`--forcer`**, avec `--audit-complet` seulement (sinon code 2), décode tous les sonores, comme avant : c'est lui qui repère un fichier abîmé sans que sa date ni sa taille aient changé.
- **Audit demandé** ([#114](https://github.com/dascritch/machincast/issues/114)) : un sonore marqué depuis l'interface (`audit_demande`) est audité en entier par la prochaine indexation, même rapide : décodé, ses blancs mesurés au seuil de la configuration. Sa marque s'efface quand son fichier est trouvé et vérifié ; l'audit complet et `--sonore` l'effacent aussi. Un sonore déjà audité au même seuil, au fichier inchangé, n'est pas redécodé : sa marque s'efface quand même ([#206](https://github.com/dascritch/machincast/issues/206)).
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
- Blancs, en audit complet seulement ([#146](https://github.com/dascritch/machincast/issues/146), `machincast.indexation.decodage`) : un élément `level` de GStreamer, entre `audioconvert` et `fakesink`, relève le niveau crête de chaque tranche de 10 ms, par canal. Le début détecté va du début du son décodé à la première tranche dont le canal le plus fort atteint le seuil (`blancs.seuil`, -40 dB par défaut) ; la fin détectée, de la fin de la dernière tranche qui l'atteint à la fin du son décodé. Un fichier sain enregistre ses blancs dans `debut_detecte` et `fin_detectee`, `NULL` tous deux s'il n'atteint jamais le seuil, sauf ceux listés dans `champs_edites`. Les blancs d'un fichier défectueux, ou d'un fichier décodé par l'indexation rapide, ne changent pas. Un nouveau seuil vaut donc pour les audits complets suivants, y compris l'analyse au dernier moment ([§ 5.1](#51-lecture-audio)).
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
- Durées d'une banque ([#195](https://github.com/dascritch/machincast/issues/195), `machincast.indexation.repertoires`) : un sonore déjà connu, de durée connue, qui sort des durées minimale ou maximale d'une banque (bornes comprises dans les durées), n'y est pas rattaché. Un sonore de durée encore inconnue, un nouveau fichier par exemple, trouvé dans le répertoire d'une banque qui a des durées, n'y est rattaché qu'après la vérification, même arrêtée, s'il est dans ses durées ou que sa durée reste inconnue (`rattacher_en_attente`, [#210](https://github.com/dascritch/machincast/issues/210)) : sinon, il n'y passe jamais, sans ligne au journal ni rattachement ou retrait au bilan. Après la vérification, chaque indexation, rapide ou audit complet, retire de chaque banque les sonores dont la durée en base est connue et sort de ses durées, qu'ils viennent de ses répertoires ou qu'ils aient été ajoutés à la main (`retirer_hors_durees`). `--sonore N` le fait pour ce seul sonore ; une indexation arrêtée et la vérification des fichiers ajoutés depuis l'interface ne retirent rien. La durée comparée est la durée complète en base, même saisie à la main ; un sonore de durée inconnue, un stream par exemple, n'est jamais retiré. Seule la ligne de `banques_sonores` disparaît : le sonore reste en base, dans ses autres banques, séquences et événements, et son fichier n'est jamais touché. Un retrait libère sa position, sans renuméroter les autres.
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
- STDOUT, au fil de l'indexation ([#120](https://github.com/dascritch/machincast/issues/120)) : une ligne par fichier trouvé dans les répertoires des banques (« nouveau sonore, ajouté à la banque … », « rattaché à la banque … » ; pour un sonore de durée encore inconnue, après la vérification, dans les seules banques dont il respecte les durées, ou « nouveau sonore » seul, [#210](https://github.com/dascritch/machincast/issues/210)), par fichier décodé sain (« sain, Artiste – Titre ; sonore passé actif », « … ; état actif conservé ») et par retrait d'une banque ([#195](https://github.com/dascritch/machincast/issues/195) : « retiré de la banque Jingles, durée 2:01 plus longue que son maximum, 2:00 »), désigné par son chemin.
- STDOUT, à la fin : le mode et le bilan, par exemple « indexation rapide : 3 nouveaux sonores, 1 rattachement, 0 retrait ; 3 sonores vérifiés ; 1 erroné, 0 non supporté, 1 supprimé, 0 rétabli, 3 sortis d'aperçu ». Les nouveaux sonores et les rattachements (sonore déjà connu ajouté à une banque) viennent du parcours des répertoires ; les retraits, des durées des banques ([#195](https://github.com/dascritch/machincast/issues/195)) ; les sonores vérifiés sont ceux qui ont été décodés ; les autres nombres comptent les changements d'état.
- Code de sortie : 0 quand la vérification est allée au bout, même si des sonores ont changé d'état : ce sont des anomalies non bloquantes ; 1 si la base est injoignable ou si un décodeur manque ; 2 pour une configuration invalide.

## 7. Wrapper Machin

Script bash `Machin` ([#6](https://github.com/dascritch/machincast/issues/6)) :

```
Machin [--config FICHIER] BINAIRE [OPTIONS…]
Machin logs [OPTIONS DE journalctl…]
Machin dev | dev-test | dev-captures [REPERTOIRE]
Machin -h | --help | --binaires
```

- `Machin BINAIRE` appelle `Machin_BINAIRE` (`lecture`, `indexation`, `interface` ou `maintenance-db`) en lui transmettant toutes les options qui suivent, intactes, et se termine avec son code de sortie. Le binaire est cherché d'abord dans le venv du projet (`.venv`, à côté du répertoire `bin/` du wrapper, même appelé par un lien symbolique), puis dans le `PATH` : le wrapper prépare ainsi l'environnement, sans qu'il soit besoin d'activer le venv.
- `--config FICHIER` (ou `--config=FICHIER`), placé avant le binaire, lui est transmis, notamment pour les tests. Placé après le binaire, il est transmis tel quel.
- `-h` affiche une aide minimale de deux lignes, `--help` l'aide complète. L'aide d'un binaire s'obtient par `Machin BINAIRE --help`.
- `Machin logs` suit en direct le journal du service de lecture, `machincast.service` (`journalctl --unit=machincast.service --follow`). Les options qui suivent sont transmises à `journalctl`, par exemple `--since "1 hour ago"`. Le journal d'un service système n'est lisible que par les groupes `adm` (dont fait partie le premier compte créé à l'installation d'Ubuntu) et `systemd-journal` : le compte qui utilise MachinCast doit pouvoir le lire, `install.sh` l'ajoute donc au groupe `systemd-journal`, qui donne la lecture du journal sans les droits d'administration de `adm` (voir [§ 10](#10-installation-et-déploiement)).
- `--binaires` liste les binaires, un par ligne ; l'autocomplétion s'en sert.
- Poste de développement ([#77](https://github.com/dascritch/machincast/issues/77)) : `Machin dev` ouvre un sous-shell interactif dans le répertoire de MachinCast, qui lit le `.bashrc` du compte, active le venv, définit `MACHINCAST_DEV=1` et préfixe l'invite de `(MachinCast dev)` ; `exit` en sort, avec son code. `Machin dev-test` lance, dans le répertoire de MachinCast, avec le venv en tête du `PATH` et `VIRTUAL_ENV` défini, `ruff check --no-cache .`, `ruff format --no-cache --check .`, `mypy --strict src/`, `shellcheck -x` sur les scripts bash, `pytest` puis `bats tests/wrapper`. Il les lance tous, même après un échec, puis affiche un bilan par outil. Sans cache, ruff ne garde pas le verdict d'un fichier dont l'ordre des imports dépend d'un autre. Un outil absent compte comme un échec, avec un message qui propose `./install.sh --dev`. Ni l'un ni l'autre ne prend d'argument. `Machin dev-captures [REPERTOIRE]` ([#128](https://github.com/dascritch/machincast/issues/128)) refait les captures d'écran du guide de l'antenne, dans `doc/captures` ou dans le répertoire donné : `tests/captures.py`, lancé par le Python du venv depuis le répertoire de MachinCast, remplit la base de test d'une démonstration, ouvre l'interface hors de l'écran à une heure fixe, et enregistre chaque écran en PNG ; il refuse `--config`, et n'ouvre jamais la base de production.
- Codes de sortie : celui du binaire, de `journalctl` ou du sous-shell de `dev` ; 1 pour `dev-test` si un outil a échoué ou manque ; 2 pour un appel incorrect du wrapper (binaire ou option inconnus, `--config` sans fichier, argument donné à `dev` ou `dev-test`, plus d'un à `dev-captures`, `--config` avec `dev-captures`) ; 127 si le binaire, `journalctl` ou le venv est introuvable.

- `Machin maintenance-db` ([#127](https://github.com/dascritch/machincast/issues/127), `machincast.maintenance`) entretient la base de production, avec le compte propriétaire de la base, sans endosser de rôle : sauvegarde par `pg_dump --format=custom` dans un fichier daté du répertoire `sauvegardes` (à côté du fichier de configuration, ou `--sauvegardes`), qui arrête tout si elle échoue ; migrations manquantes, puis vérification que chaque rôle est endossable (`pg_has_role(…, 'SET')`), un rôle manquant étant signalé avec les commandes qui l'autorisent ; `VACUUM (ANALYZE)`. `--garder-ouvert` garde le terminal ouvert une fois la maintenance finie : le programme lit l'entrée standard jusqu'à sa fin (fermeture du terminal, `Ctrl-D`) ou `Ctrl-C`, sans réagir à Entrée. Code 0 si tout est fait, 1 sinon. Aucune sauvegarde n'est effacée. Le journal (`log`) n'est pas purgé : son historique est gardé.

Autocomplétion bash (`bash-completion/Machin`) : binaires, `logs`, `dev` et `dev-test`, options du wrapper, fichiers après `--config`, options d'un binaire lues dans son aide, options courantes de `journalctl` après `logs`.

Le wrapper n'est pas copié dans le venv : en développement, il s'appelle par `bin/Machin`. `install.sh` installe le wrapper et l'autocomplétion pour tout le système (voir [§ 10](#10-installation-et-déploiement)).

## 8. Interface graphique

Python, PySide6 (Qt 6.10, version de Kubuntu 26.04 LTS).

**Conformation des textes** ([#108](https://github.com/dascritch/machincast/issues/108), `machincast.conformation.conformer`) : les noms (interne et public) des événements, séquences, banques et feeds, l'artiste, le titre et les métadonnées musicales des sonores saisis dans une fiche sont conformés à l'enregistrement : tout espace Unicode (tabulation, retour à la ligne, espace insécable, espace fine…) devient une espace simple, les espaces de début et de fin sont retirées et jamais deux ne se suivent ; les caractères de contrôle, les sélecteurs de variante, les caractères spéciaux (U+FFF0 à U+FFFF), les caractères à usage privé, les caractères non attribués et les espaces sans largeur (U+200B, U+FEFF) sont supprimés. Rien d'autre n'est changé : accents, écritures non latines et emoji restent tels quels. Les chemins et les adresses ne le sont jamais. Une fiche compare des textes conformés : un texte relu tel qu'en base, non conforme, n'est pas une modification.

### 8.1 Écran par défaut

- Heure actuelle.
- État du binaire lecture (en marche ou non).
- Les 5 sonores à venir après le prochain, en table, au-dessus de l'airplay ([§ 4.10](#410-playlist-immédiate)).
- Airplay des 10 derniers sonores, en table ([#244](https://github.com/dascritch/machincast/issues/244)) ; l'airplay sur plusieurs heures est dans son propre onglet.
- Sonore en cours mis en avant : emplacement (chemin du fichier ou adresse du stream), heure de début, durée totale, heure de fin estimée, temps qui reste ; pour un fichier, sa frise, à la place de la barre de progression.
- Juste à côté, le prochain sonore : emplacement, heures de début et de fin estimées, durée, indicateur « sain ». Le sonore en cours et le prochain sonore se partagent également la largeur de l'écran, de part et d'autre de la colonne de l'antenne ([#24](https://github.com/dascritch/machincast/issues/24)) ; un titre ou un nom d'événement trop long passe à la ligne (demandé en relecture de [PR #106](https://github.com/dascritch/machincast/pull/106)).
- Pour un stream, durée et heure de fin affichées comme inconnues.
- VU-mètre et bargraph de la sortie sonore (indisponibles avec la sortie ALSA).

Mise en œuvre ([#23](https://github.com/dascritch/machincast/issues/23), `machincast.interface.ecran_par_defaut`) :

- **État, sonore en cours et prochain sonore** : de la socket d'état ([§ 5.4](#54-socket-détat)), par `machincast.interface.etat.ClientEtat`, un `QLocalSocket` dans la boucle d'événements de Qt. Sans socket, ou quand elle se ferme, le binaire lecture est « À l'arrêt » et le client retente la connexion chaque seconde. Un message illisible est signalé sur la sortie d'erreur et ignoré.
- **Airplay** : les 10 derniers passages, même anciens (`airplay.DERNIERS`, [#244](https://github.com/dascritch/machincast/issues/244)), dans l'encart « Airplay : les 10 derniers sonores ». Lu en base avec le rôle de l'interface (`machincast.interface.airplay.lire_airplay`), à l'ouverture, puis seulement quand la socket annonce un autre sonore en cours (ou aucun) que celui que la table connaît. Jamais en boucle. Chaque relecture le dit (`EcranParDefaut.airplay_relu`), et l'onglet Airplay ouvert se relit aussi. Artiste et titre toujours affichés : l'interface est privée.
- **Encarts dépliables** ([#244](https://github.com/dascritch/machincast/issues/244), `machincast.interface.depliable`) : « À venir après le prochain sonore » et « Airplay : les 10 derniers sonores » se replient d'un clic sur leur titre, comme les encarts des fiches ; dépliés par défaut, un encart replié le reste pour le compte, dans les réglages des vues (`accueil/encarts-replies`, `depliable.retenir_dans`).
- **Onglet Airplay** ([#244](https://github.com/dascritch/machincast/issues/244), `machincast.interface.onglet_airplay.EcranAirplay`) : fermé au lancement, unique, il s'ouvre par « Affichage → Ouvrir l'onglet Airplay » et se ferme par sa croix ; son icône est celle de l'airplay. En haut, « Dernières heures », de 1 à 744 (un mois), 12 par défaut : le nombre d'heures montré, retenu pour le compte (`onglet-airplay/heures`). La table a les colonnes de l'airplay de l'accueil, dans le même ordre (vue `onglet-airplay`), du plus récent au plus ancien ; double-clic vers les fiches et « Pré-écoute… » au clic droit, comme dans l'accueil. Elle se relit à l'ouverture, à chaque réglage, quand l'accueil relit son airplay, et par « Rafraîchir les onglets ». « Exporter… » relit en base les passages montrés (`sorties.lire_passages`, avec `depuis`), et les enregistre au format du filtre choisi (`dialogues.choisir_export`, `machincast.interface.export_airplay`), sous le nom proposé `airplay-AAAA-MM-JJ-HHMM-12h.csv`, qui reçoit l'extension du format s'il ne l'a pas : un export ne remplace jamais un fichier sonore ([#96](https://github.com/dascritch/machincast/issues/96)). Chaque format donne les informations privées et publiques du passage : l'artiste, le titre et l'emplacement, et le texte public tel que la page publique l'affiche, masquage de la configuration appliqué ([§ 4.8](#48-métadonnées-publiques-et-masquage)) :
	- **CSV** (« Tableur CSV ») : UTF-8 avec BOM, séparateur `;`, en-tête `debut;fin;duree;artiste;titre;texte_public;emplacement;evenement;sequence;banque;sans_incident`, heures et durées comme le CSV de la diffusion ([§ 5.3](#53-modules-de-sortie)), du plus récent au plus ancien ;
	- **HTML** (« Page HTML ») : une page autonome, sans JavaScript, au tableau des mêmes colonnes, « Incident » à `oui` pour un passage qui en a eu un ;
	- **M3U** (« Liste de lecture M3U ») : `#EXTM3U`, puis du plus ancien au plus récent, comme le .pls, pour chaque passage qui a un emplacement : `#EXTINF:` sa durée diffusée (`-1` inconnue) et son artiste et titre, son texte public en commentaire (`# texte public : …`), et son emplacement.

	La barre d'état dit où l'export est enregistré (« Airplay exporté dans … »), ou pourquoi il ne l'a pas été.
- **Inconnus** : un stream a sa durée et sa progression « inconnue », et son indicateur « sain » « non testé ». Un stream qui finit avec son événement a pour horaire « 19:00:00 – 20:00:00 (fin de l'événement) », et le temps qui lui reste jusqu'à cette fin ([#242](https://github.com/dascritch/machincast/issues/242)) ; sans fin d'événement, « 19:00:00, durée inconnue », et le début estimé du prochain sonore est « inconnu ».
- **Disposition** ([#144](https://github.com/dascritch/machincast/issues/144)) : en haut, l'heure seule, à la seconde, la date du jour en infobulle (demandé avec [#191](https://github.com/dascritch/machincast/issues/191)), le texte public du sonore en cours entre guillemets (champ `texte_public` de la socket, `—` sans texte) et l'état ; puis l'événement à l'antenne et ses heures (« de 20:00 à 22:00 », « depuis 19:00 » sans fin, « permanent » pour un fil musical). Le bandeau ne montre que ces valeurs, sans intitulé : l'infobulle de l'état dit « État de Machin lecture », celle de l'événement « Événement à l'antenne » ([#191](https://github.com/dascritch/machincast/issues/191)). Chaque sonore a, une ligne par information, son événement, sa séquence, sa banque (`—` sans), son horaire sur une ligne (« 20:00:00 – 20:03:34 (3:34) », « 20:00:00, durée inconnue » pour un stream) et son emplacement. Le temps qui reste au sonore en cours, sans intitulé, à la seconde entamée : « reste 3:05 », sur la barre de progression d'un stream, au milieu de la frise d'un fichier, sur un fond qui le garde lisible (`Frise.legende`, `Frise.fond_de_la_legende`).
- **Frises** ([#230](https://github.com/dascritch/machincast/issues/230), `EcranParDefaut._montrer_la_frise`) : un fichier, en cours ou prochain, a la frise de la pré-écoute ([§ 8.3](#83-écran-de-détails-dun-sonore), `machincast.interface.frise`), non interactive (`Frise(interactive=False)`) : aucun clic, glissement ni touche n'y demande de position, et elle ne prend pas le focus. Elle remplace la barre de progression du sonore en cours ; un stream la garde, et n'a pas de frise. Frise et barre sont en tête de chaque sonore, au-dessus de son titre : les deux frises sont au même niveau, et le contenu des deux sonores se tasse vers le haut. Le VU-mètre de l'antenne prend toute la hauteur de sa colonne que lui laissent ses voyants, celle que les frises donnent à la ligne des sonores. Son plan est celui que la diffusion joue (`lire_le_plan`) : blancs retirés si le sonore ou la banque qui l'a fourni (`banque_id` de la socket) active la détection, crossfades selon les règles de cette banque, puis les crossfades par défaut des préférences, et positions des fondus des préférences ([#234](https://github.com/dascritch/machincast/issues/234)), comme `machincast.lecture.diffusion.crossfade` ; l'infobulle d'un crossfade qui ne vient pas du sonore dit d'où il vient (« imposé par la banque », « de la banque », « défaut »). Il se lit une fois par sonore et par banque, pas à chaque état publié ; une base injoignable laisse la frise sans plan, avec sa forme d'onde. La tête de lecture du sonore en cours suit `position`, comptée depuis le début de sa lecture, que les blancs et la position du fade-in placent ([§ 5.1](#51-lecture-audio), [#234](https://github.com/dascritch/machincast/issues/234)) ; celle du prochain n'en a pas. La forme d'onde se calcule en tâche de fond, une fois par sonore et par fichier : celle du prochain sonore sert encore quand il passe à l'antenne ; un minuteur de 100 ms la relève tant qu'un calcul est en cours, et seules restent celles des deux sonores montrés. Le fichier est celui de l'`emplacement` de la socket : un fichier introuvable depuis le poste de l'interface le dit sur la frise.
- **Sonores à venir** ([#228](https://github.com/dascritch/machincast/issues/228), `EcranParDefaut._afficher_a_venir`) : une table « À venir après le prochain sonore », juste au-dessus de l'airplay, haute de 5 lignes (sur un petit écran, elle se tasse jusqu'à 2 lignes, avec une barre de défilement, après l'airplay, qui se tasse jusqu'à une ligne), avec les colonnes de l'airplay, dans le même ordre : début et fin estimés, durée, artiste, titre, événement, séquence, banque, et « Incident », qui dit `pas sain` pour un sonore dont le fichier a posé problème ([§ 4.6](#46-sonore-sain)). Le plus lointain est en haut : le plus proche est juste au-dessus de l'airplay. Elle suit chaque état publié (champ `a_venir` de la socket), et se vide en silence et à l'arrêt. Comme dans l'airplay, un double-clic ouvre la fiche du sonore, de l'événement, de la séquence ou de la banque, et le clic droit sur une ligne propose « Pré-écoute… » de son sonore ; ses colonnes se règlent et se retiennent à part (`Colonnes`, vue `accueil-a-venir`).
- **Écouter le prochain sonore** ([#223](https://github.com/dascritch/machincast/issues/223)) : sur la ligne « Sain » du prochain sonore, « Pré-écoute », au casque, émet `EcranParDefaut.preecoute_demandee` avec le sonore, comme un clic sur sa frise (`Frise.cliquee`, émis par une frise non interactive) ; inactif sans prochain sonore. Pour un stream, « Tester la connexion du flux » le précède : le test de la fiche d'un sonore ([§ 8.3](#83-écran-de-détails-dun-sonore), `EssaiDeFlux`) sur l'`emplacement` de la socket, dont le résultat s'écrit dessous, et reste tant que ce stream est le prochain sonore.
- **Coupure** ([#169](https://github.com/dascritch/machincast/issues/169)) : un sonore qu'un événement coupera (champ `coupe_par` de la socket) a pour horaire « 20:00:00 – 20:02:00 (coupé par « Journal », sur 3:34) », ou « … (coupé par « Flash », durée inconnue) » pour un stream ; sa barre se remplit de son début à la coupure et dit « reste 1:30 avant « Journal » ». Le prochain sonore annoncé est celui de l'événement, à l'instant de la coupure.
- **Fiches** ([#144](https://github.com/dascritch/machincast/issues/144)) : un bouton à droite du titre de chaque sonore, et un à droite de son événement, de sa séquence et de sa banque, émettent `EcranParDefaut.ouverte(genre, identifiant, nom)`, que la fenêtre traite comme une ligne de liste ouverte ; ils sont inactifs sans sonore, et ceux de l'événement, de la séquence et de la banque sans leur identifiant dans l'état publié (`evenement_id`, `sequence_id`, `banque_id`). Dans l'airplay, un double-clic sur l'artiste ou le titre ouvre la fiche du sonore, sur l'événement, la séquence ou la banque celle de l'élément ; ailleurs, ou sur un élément supprimé depuis, il ne fait rien. La colonne « Incident » ne dit `oui` que pour un passage qui en a eu un.
- **VU-mètre de l'antenne** ([#24](https://github.com/dascritch/machincast/issues/24), `machincast.interface.moniteur`, `machincast.interface.vumetre`) : une colonne verticale « Antenne », entre le sonore en cours et le prochain sonore. Par canal, le VU, niveau moyen (RMS), en barre pleine, de -60 à 0 dBFS, vert, orange au-delà de -12 dB, rouge au-delà de -3 dB ; par-dessus, le bargraph de crête, plus clair, et un repère qui garde la plus haute crête 2 secondes. Les canaux gauche et droit, nommés « G » et « D » dessous, sont séparés par l'échelle en dB, graduée de 0 en haut à -60 en bas (0, -6, -12, -20, -30, -40, -50, -60) ; un nombre qui chevaucherait un nombre plus important n'est pas écrit (0 et -60 d'abord, puis -20, -6, -12, -40, -30, -50). Un son qui n'est pas stéréo a son échelle à droite. Deux voyants, écrits en petit : au-dessus du VU-mètre, « Saturation », allumé dès qu'une crête atteint -1 dBFS, et pendant 3 secondes ; dessous, « Silence », allumé après 5 secondes à -50 dBFS ou moins sur tous les canaux. Le voyant « Saturation » se cache par les préférences (`interface.saturation`, [#191](https://github.com/dascritch/machincast/issues/191)) ; le VU-mètre montre toujours les crêtes, et « Silence » reste affiché.
	- Port de monitoring : les niveaux se lisent sur le périphérique de l'antenne (`audio.peripherique`), sans rien demander à Machin lecture. Avec PipeWire, `pipewiresrc` sur son nœud, qui en capture la sortie (`stream.capture.sink`) ; avec PulseAudio, `pulsesrc` sur son « .monitor » ; sur la sortie factice, un signal de test de GStreamer. Le port est capté en stéréo (filtre `audio/x-raw,channels=2`) : sans contrainte, `pipewiresrc` et `pulsesrc` se contentent d'un canal. Le pipeline (port, `audioconvert`, `level`, `fakesink`) ne joue rien ; son bus est relevé toutes les 50 ms par un minuteur de Qt.
	- Indisponible : avec la sortie ALSA, qui n'a pas de port de monitoring, ou sans périphérique d'antenne, le VU-mètre le dit sous les voyants, sans erreur ni nouvel essai. Un port qui ne s'ouvre pas, ou qui se ferme, est signalé avec l'erreur de GStreamer, puis rouvert toutes les 5 secondes.
	- L'infobulle nomme le port écouté ; les préférences qui changent l'antenne le changent aussitôt. Un clic sur le VU-mètre, disponible, écoute l'antenne dans la fenêtre de pré-écoute ([§ 8.3](#83-écran-de-détails-dun-sonore)). La fermeture de l'interface arrête la capture.
- **Lancement** : `Machin_interface` se connecte à la base avant d'ouvrir son écran. Sans base, ou sans droit sur elle, il montre une fenêtre d'erreur (`machincast.interface.erreur.FenetreBaseInjoignable`, demandée en relecture de [PR #106](https://github.com/dascritch/machincast/pull/106)) : l'interface n'est pas utilisable et pourquoi, une invitation à lire `INSTALL.md` du répertoire de MachinCast, section « En cas de problème », avec un bouton qui ouvre ce document, et l'erreur de PostgreSQL en détail. Puis il s'arrête avec le code 1. La fenêtre n'est montrée que si un affichage graphique peut la montrer (`DISPLAY`, `WAYLAND_DISPLAY` ou `QT_QPA_PLATFORM`, sauf les plateformes invisibles `offscreen` et `minimal`) ; sinon, seul le message de la sortie d'erreur reste. Les textes propres à Qt, comme « Montrer les détails… », sont en français (`machincast.interface.application`).

### 8.2 Recherche et navigation

- Écrans de liste avec recherche pour les sonores, les banques, les séquences et les événements, menant aux écrans de détail.

Mise en œuvre des listes ([#26](https://github.com/dascritch/machincast/issues/26), `machincast.interface.listes`, `machincast.interface.fenetre`) :

- **Onglets** : la fenêtre a un onglet par écran, décidé avec le ticket : Accueil (l'écran par défaut, [§ 8.1](#81-écran-par-défaut)), ouvert au lancement, puis une liste par type, dans l'ordre de la recherche : Événements, Séquences, Banques, Sonores ; puis les Feeds ([§ 8.13](#813-feeds-de-streams)) ; enfin les Incidents ([§ 8.6](#86-écran-des-incidents)). Les listes des Sonores et des Feeds ne s'ouvrent pas au lancement ([#180](https://github.com/dascritch/machincast/issues/180), `FenetrePrincipale.ouvrir_liste`) : le menu « Affichage » les ouvre à leur place, après Banques et avant Incidents, ou les ramène au premier plan ; elles se ferment, et une liste fermée est gardée, avec son filtre et son tri. Les autres onglets fixes ne se ferment pas. Les 12 premiers onglets ont les raccourcis Maj+F1 à Maj+F12, selon leur rang ([#192](https://github.com/dascritch/machincast/issues/192), `FenetrePrincipale._creer_les_raccourcis`) : Maj+F1 est toujours l'accueil ; ouvrir ou fermer un onglet décale les suivants, et l'infobulle de chaque onglet donne son raccourci. Tout onglet s'ajoute et se retire par `_ajouter_onglet` et `_retirer_onglet`, qui les renumérotent.
- **Icônes des genres** ([#215](https://github.com/dascritch/machincast/issues/215), `machincast.interface.icones`) : chaque genre a son icône monochrome, dessinée pour MachinCast (SVG dans `src/machincast/interface/icones/`) : une croche pour un sonore, une feuille et sa liste à puces pour une séquence, un dossier pour une banque, une montre pour un événement, un calendrier pour la grille, une boule de divination pour la simulation. Elle prend la couleur du texte du thème (`QPalette.WindowText`), clair ou sombre, à la création de l'élément qui la porte. Elle désigne le genre partout : onglets des listes, des fiches (une nouvelle fiche comprise), de la grille (« Calendrier ») et de la simulation ; entrées du menu « Affichage » qui les ouvrent ; colonne « Type » de la recherche ; colonne du genre des relations de la fiche d'un sonore ; boutons « Fiche… » de l'accueil, pour le sonore en cours comme pour le suivant (sonore, événement, séquence, banque). Les onglets de l'accueil, des incidents, de la recherche et des feeds n'en ont pas. Un écran `.ui` ne prend jamais une icône du thème du poste pour un genre ; seuls « Dossier… » (`folder-open`) et « Pré-écoute… » (`audio-headphones`) de la fiche d'un sonore en gardent une, puisqu'ils ne désignent pas un genre.
- **Colonnes et ordre** : événements (nom, nom public, priorité, début, fin, récurrence, anomalie : « événement vide », [#140](https://github.com/dascritch/machincast/issues/140)), du plus prioritaire au moins prioritaire ; séquences (nom, nom public, anomalie : « séquence vide », [#138](https://github.com/dascritch/machincast/issues/138)) ; banques (nom, nom public, mode, ne pas répéter, premier répertoire dans l'ordre alphabétique) ; sonores (artiste, titre, type, état, durée, emplacement ; les durées d'une banque n'y sont pas signalées, [#210](https://github.com/dascritch/machincast/issues/210)), par artiste puis titre ; feeds (nom, adresse, nombre de streams qui le suivent), par nom. Un clic sur un titre de colonne trie.
- **Anomalies** ([#138](https://github.com/dascritch/machincast/issues/138)) : une ligne en anomalie (`Ligne.anomalie`) a l'icône d'avertissement de Qt sur sa première cellule et son explication en infobulle sur toutes ; le compte ajoute « dont n en anomalie », parmi les lignes que garde le filtre.
- **Filtre** : les lignes dont une colonne contient le texte, sans tenir compte des majuscules ni des accents (`FiltreSansAccents`) ; un compte « n sonores sur N ».
- **Sélection multiple** ([#114](https://github.com/dascritch/machincast/issues/114), `machincast.interface.groupes`) : les listes des sonores et des banques sélectionnent plusieurs lignes (Ctrl, Maj) ; les autres, une seule. Le clic droit propose les actions sur la sélection, ou sur la seule ligne cliquée si elle n'en fait pas partie. Chaque action demande confirmation (`dialogues.confirmer_action`), s'exécute en une transaction, relit la liste et annonce dans la barre d'état ce qui a réellement changé ; un choix abandonné ou une confirmation refusée ne change rien.
	- Sonores : **Activer**, **Désactiver** (un sonore en aperçu reste en aperçu), **Ajouter à des banques…** (choix parmi toutes, chaque sonore à la fin de chaque banque, sans doublon), **Retirer de banques…** (choix parmi celles où figure l'un des sonores ; les positions se resserrent ; un fichier d'un répertoire de la banque y reviendra à la prochaine indexation), **Demander un audit complet** (fichiers seulement, [§ 6.0](#60-modes-dindexation)). La colonne État d'un sonore marqué dit « actif, audit demandé ».
	- Banques : **Demander l'audit complet de leurs sonores**, et le masquage de l'artiste et du titre de leurs sonores : **Masquer**, **Afficher**, ou **hérités du sonore** (`banques.masquer_metadonnees`). « Dupliquer » ne vaut que pour une seule banque.
- **Lecture** : en base, avec le rôle de l'interface, chaque fois que l'onglet s'ouvre ; jamais en boucle. Le filtre est gardé.
- **Colonnes** ([#207](https://github.com/dascritch/machincast/issues/207), `machincast.interface.colonnes.Colonnes`) : tout tableau de l'interface, liste, recherche, incidents, airplay de l'accueil et de son onglet, simulation et tableaux des fiches, est une vue nommée (`liste-sonores`, `recherche`, `fiche-banque-sonores`…). Ses colonnes sont de largeur libre, la dernière s'étirant jusqu'au bord quand le tableau le prévoit, et s'ajustent à leur contenu à chaque lecture (modèle remis à zéro, lignes ajoutées ou réordonnées) et quand le tableau se montre ou change de taille : jamais par le mode `ResizeToContents` de Qt, qui ignore le contenu quand l'en-tête vertical est masqué. Une colonne élargie à la souris arrête l'ajustement pour la vue. Les titres se déplacent en les glissant ; le clic droit sur les titres ouvre le menu des colonnes : une case par colonne, dans l'ordre affiché, la dernière montrée inactive, puis « Rétablir les colonnes », qui revient à l'ordre et aux colonnes d'origine et réajuste. La disposition (`QHeaderView.saveState`) est gardée par vue, pour le compte, dans `$XDG_CONFIG_HOME/machincast/vues.ini` (`~/.config` par défaut), jamais dans `machincast.toml` ; une disposition gardée pour d'autres colonnes est oubliée, et le tri de la vue n'en est pas repris.
- **Détail** : un double-clic ou Entrée sur une ligne émet `FenetrePrincipale.detail_demande(genre, identifiant)`, et ouvre la fiche de l'élément ([§ 8.5](#85-écran-de-détails-dun-événement), [§ 8.12](#812-écran-de-détails-dune-séquence), [§ 8.4](#84-écran-de-détails-dune-banque), [§ 8.3](#83-écran-de-détails-dun-sonore)).
- **Création** : une liste peut avoir un bouton de création (`Source.nouveau`, signal `Liste.creation_demandee`) ; les listes des événements, des séquences, des banques et des sonores l'ont : « Nouvel événement », « Nouvelle séquence », « Nouvelle banque » et « Nouveau stream ». La liste des sonores a aussi « Ajouter des fichiers… » et accepte les dépôts de fichiers (`Source.fichiers`, signaux `Liste.ajout_demande` et `Liste.fichiers_deposes`) ; une liste dans un choix d'éléments n'a ni l'un ni l'autre.
- Champ de recherche globale, résultats au fil de la frappe dans l'ordre : événements, séquences, banques, sonores. Un écran de résultats dédié.

Mise en œuvre de la recherche globale ([#27](https://github.com/dascritch/machincast/issues/27), [#105](https://github.com/dascritch/machincast/issues/105), `machincast.interface.recherche`) :

- **Onglet** : « Recherche », qui se ferme, unique ; **Affichage → Rechercher…** ou Ctrl+F l'ouvre, ou y revient, le curseur dans le champ et son texte sélectionné (`EcranRecherche.focaliser`).
- **Champs cherchés** : le nom interne et le nom public des événements, des séquences et des banques ; l'artiste et le titre des sonores, jamais leur emplacement. Le texte est cherché dès 2 caractères (`MINIMUM`), n'importe où dans le champ, sans tenir compte des majuscules ni des accents (`translate()` et `lower()` en base, `listes.sans_accents` pour le texte tapé) ; `%`, `_` et `\` sont cherchés tels quels. En dessous, le compte dit « Tapez au moins 2 caractères. ».
- **Ordre** : événements, séquences, banques, sonores ; dans chaque type, par nom, sans tenir compte des majuscules. Un sonore se nomme « artiste – titre ».
- **Sans suggestions** : le champ ne propose pas de suggestions sous lui, jugées peu pratiques à l'usage ; la table suit la frappe.
- **Table des résultats** : colonnes Type, Nom interne, Nom public, Statut (l'état d'un sonore) ; jusqu'à 500 lignes (`LIMITE`). Le compte dit « aucun résultat », « 1 résultat », « N résultats », ou « N premiers résultats sur T » quand la limite coupe la table. Un double-clic ou Entrée sur une ligne ouvre la fiche de l'élément, sans toucher au texte tapé.
- **Lecture** : en base, avec le rôle de l'interface, à chaque frappe, à l'ouverture de l'onglet et par « Rafraîchir les onglets » (F5) ; jamais en boucle. Une erreur de base s'affiche à la place du compte.
- Vue calendrier (jour, semaine) montrant à la fois l'airplay (ce qui a effectivement été diffusé) et les événements prévus.

Mise en œuvre du calendrier ([#36](https://github.com/dascritch/machincast/issues/36), [#118](https://github.com/dascritch/machincast/issues/118), `machincast.interface.calendrier`) :

- **Onglet** : « Calendrier », ouvert par « Ouvrir l'onglet Grille horaire » du menu « Affichage » ([#180](https://github.com/dascritch/machincast/issues/180)) ; il se ferme, et n'est ouvert qu'une fois. Il se relit à son ouverture, à chaque changement de période et par « Rafraîchir les onglets » ; jamais en boucle.
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
- Pour un stream : choix entre URL directe et feed, choix de l'événement de secours ([§ 4.7](#47-streams)), test du stream à la demande.
- Table des derniers passages, avec indication des incidents.

Mise en œuvre ([#28](https://github.com/dascritch/machincast/issues/28), `machincast.interface.fiche_sonore`, `machincast.interface.essai_flux`), avec ce qui est commun aux fiches (`machincast.interface.fiche`, [§ 8.4](#84-écran-de-détails-dune-banque)) :

- **Encarts** ([#190](https://github.com/dascritch/machincast/issues/190), [#223](https://github.com/dascritch/machincast/issues/223), `machincast.interface.depliable`) : « Métadonnées », « Diffusion », « Enchainement », « Relations » et « Fichier » sont repliés à la première ouverture d'une fiche ; un clic sur leur titre, précédé de « ▸ » replié et « ▾ » déplié, ou Espace et Entrée quand l'encart a le focus, les déplie ou les replie. Seul un conteneur intérieur se cache : ce que la fiche montre ou cache dans l'encart selon le sonore n'est pas touché. « Sonore », « Stream » et « Derniers passages » restent dépliés. Les encarts dépliés ou repliés à la main sont retenus pour le compte, dans les réglages des vues (`fiche-sonore/encarts-deplies`, `fiche_sonore.retenir_l_encart`) : les fiches de sonore ouvertes ensuite, même après un redémarrage de l'interface, les déplient de même.
- **Frise** ([#223](https://github.com/dascritch/machincast/issues/223), `FicheSonore._actualiser_la_frise`) : pour un fichier, la frise de la pré-écoute, non interactive, sur toute la largeur de la fiche, au-dessus des encarts. Sa forme d'onde se calcule en tâche de fond, une fois par fichier. Son plan suit aussitôt les champs de la fiche, même pas encore enregistrés : crossfades, début et fin détectés, « Jouer sans les blancs détectés », avec les crossfades par défaut et les positions des fondus des préférences ; son infobulle donne le résumé du plan. Un stream n'a pas de frise.
- **Vérification complète** ([#190](https://github.com/dascritch/machincast/issues/190), `machincast.interface.verification.VerificationComplete`) : le bouton, à côté de « Pré-écoute… », pour un fichier enregistré, fait l'audit complet de ce seul sonore en tâche de fond, comme `Machin indexation --audit-complet --sonore N` : décodage, tags, blancs au seuil `blancs.seuil`. Déjà audité au même seuil, au fichier inchangé, il n'est pas redécodé, et la barre d'état le dit (« Déjà audité au seuil de -40 dB, fichier inchangé : Neige, actif. », [#206](https://github.com/dascritch/machincast/issues/206)). Le bouton devient « Vérification… », inactif, et la fiche dit « Vérification complète en cours… » ; à la fin, la barre d'état donne le résultat (« Vérification terminée : neige.flac, actif. »), et une question (`dialogues.proposer_rafraichissement`) propose de rafraîchir la fiche, qui montre alors ce que l'indexeur a écrit. Une fiche fermée entre-temps ne demande rien. Un stream ne se vérifie pas.
- **Onglet** : « Sonore : » suivi du titre, ou du nom du fichier, ou de l'adresse d'un stream. Une fiche par sonore ; une banque et un sonore de même identifiant ont chacun la leur.
- **Champs** : artiste, titre, les clés de `metadonnees_musicales` tenues par l'indexeur (`annee` et `piste` en nombres entiers) ; dans « Diffusion », dans cet ordre ([#223](https://github.com/dascritch/machincast/issues/223)) : masquage de l'artiste et du titre (« Selon la configuration », « Masqués », « Affichés »), période de diffusion à cocher (« Diffusion à partir du », « Diffusion jusqu'au »), maximum de lectures (0 = illimité) ; dans « Enchainement », pour un fichier, la détection de blanc ([#146](https://github.com/dascritch/machincast/issues/146)) : la case `detection_blancs` (« Jouer sans les blancs détectés »), et le début et la fin détectés, au centième de seconde, chacun à cocher (décoché : `NULL`, aucun blanc détecté de ce côté), qui ensemble restent plus courts que la durée du sonore ; puis, pour tout sonore, les crossfades de début et de fin, à cocher : décoché, non paramétré, `NULL` ([#145](https://github.com/dascritch/machincast/issues/145)). Chaque crossfade se règle d'un curseur horizontal (`machincast.interface.curseur.CurseurDeDuree`), de 0 à la durée maximale des préférences (10 s par défaut), à leur pas, la valeur écrite à sa droite (« 2,5 s ») ; un crossfade enregistré plus long allonge le curseur, sans être raboté. L'état. Les autres clés des métadonnées sont montrées, jamais modifiées. Les textes sont enregistrés sans les espaces qui les entourent ; un champ vide est NULL, ou une clé absente.
- **Écriture** : seuls les champs qui diffèrent de ce que la fiche a lu sont écrits, sous verrou de la ligne ; les autres gardent ce que l'indexation ou la diffusion y a mis entre-temps. Chacun est ajouté à `champs_edites`, sauf l'état. La fin de la période doit suivre son début ; un stream doit avoir une adresse ou un feed ; un sonore effacé de la base entre-temps n'est pas enregistré.
- **État** : la fiche montre tous les états, dans l'ordre de la liste des sonores ; seuls l'état du sonore, puis `actif` et `desactive`, se choisissent, les autres sont grisés ([#223](https://github.com/dascritch/machincast/issues/223)) ; un sonore `apercu` ne change pas d'état.
- **Stream** : adresse directe ou feed existant (leur gestion : [§ 8.13](#813-feeds-de-streams)) ; événement de secours parmi les événements `secours`, ou aucun. Le **test à la demande** décode le flux de l'adresse saisie, sans le jouer ni l'enregistrer, par GStreamer (`uridecodebin`, `fakesink`) : il répond dès une seconde de son décodée, et dit alors le type du flux et son débit, lus dans les tags de GStreamer (codec, débit nominal, sinon mesuré ; « de type inconnu », « à débit inconnu » sans eux, [#223](https://github.com/dascritch/machincast/issues/223)) : « Le flux répond : du son arrive, en MPEG-1 Layer 3 (MP3) à 128 kbit/s. » ; il ne répond pas sur une erreur ou après 10 s. Le bus est relevé par un minuteur de Qt : l'interface reste utilisable. La connexion se ferme à la fin du test, à la fermeture de la fiche et à celle de la fenêtre.
- **Passages** : les 50 derniers débuts de passage du sonore dans `airplay`, avec leur fin, et les lignes du log de ce sonore, de niveau `alerte` ou `incident`, notées entre le début et la fin du passage (ou depuis le début, pour le passage en cours). La colonne « sans incident » de l'airplay n'est plus montrée ([#125](https://github.com/dascritch/machincast/issues/125)) : les incidents eux-mêmes le disent.
- **Dossier** ([#125](https://github.com/dascritch/machincast/issues/125)) : un bouton ouvre le dossier du fichier dans le navigateur de fichiers du poste (`dialogues.ouvrir_dossier`), pour un fichier seulement.
- **Relations** : séquences (`sequences_elements`), banques (`banques_sonores`) et événements (`evenements_elements`) qui citent directement le sonore, dans cet ordre, puis par nom ; un double-clic demande leur fiche (`ouverture_demandee`). Une banque dont le sonore sort des durées a l'icône d'anomalie et une infobulle qui dit pourquoi ([#147](https://github.com/dascritch/machincast/issues/147)).
- **Fichier**, pour un fichier : `type_mime` ([#121](https://github.com/dascritch/machincast/issues/121)) ; encodage moyen, taille × 8 / durée, en kbit/s ; taille (unités décimales) et date de modification lues par `stat` à l'ouverture de la fiche, et date de création par `stat --format=%W` (statx), inconnue si le système de fichiers ne la garde pas ; `verifie_le`, la dernière vérification complète par l'indexeur.
- **Pré-écoute** ([#116](https://github.com/dascritch/machincast/issues/116), [#29](https://github.com/dascritch/machincast/issues/29), `machincast.interface.preecoute`) : le bouton « Pré-écoute… » de la fiche, inactif pour un nouveau stream pas encore enregistré, envoie le sonore à la fenêtre de pré-écoute (`Fiche.preecoute_demandee`). Le clic droit sur la ligne d'un sonore propose aussi « Pré-écoute… », en tête du menu, séparée des autres entrées, avec l'icône du bouton (`affichage.proposer_la_preecoute`, [#226](https://github.com/dascritch/machincast/issues/226)) : dans l'airplay de l'accueil (`EcranParDefaut.menu_de_l_airplay`), la liste des sonores (`Liste.menu_de_la_ligne`, hors des choix), les éléments d'une séquence ou d'un événement (`ListeElements.menu_de_la_ligne`) et les sonores d'une banque (`FicheBanque.menu_des_sonores`). Elle vaut pour le sonore de la ligne cliquée, même dans une sélection ; une ligne sans sonore en base (banque, séquence, fichier déposé pas encore enregistré, passage d'un sonore supprimé depuis) n'a pas cette entrée, ni de menu s'il n'en a pas d'autre. Chaque écran émet `preecoute_demandee`, que la fenêtre principale relie à sa pré-écoute. Cette fenêtre est indépendante, et unique pour toute l'interface (`FenetrePrincipale.preecoute`) : un autre sonore y remplace le précédent, à l'arrêt ; « Affichage → Pré-écoute… » la ramène au premier plan, avec son sonore, ou l'ouvre sans sonore. Elle se ferme avec l'interface, et sa fermeture arrête la lecture.
	- Lecteur : un pipeline playbin de GStreamer, relevé par un minuteur de Qt. Ses changements d'état (lecture, pause, arrêt), comme ceux du VU-mètre de l'antenne, de la forme d'onde et du test d'un flux, se font hors du fil de l'interface, un à un dans l'ordre demandé (`machincast.interface.etats.Pilote`, [#259](https://github.com/dascritch/machincast/issues/259)) : un serveur audio qui tarde à répondre, au retour d'un écran verrouillé, ne fige pas l'interface ; une erreur de la sortie arrête la pré-écoute, qui la signale. Boutons « ⏵ » (lecture), « ⏸ » (pause) et « ⏹ » (arrêt, qui ramène au début), nommés par leur infobulle ; la position d'un fichier se règle sur sa frise, pendant sa lecture ou sa pause ; temps écoulé sur durée, la durée en base avant la lecture. La fin du fichier ramène à l'arrêt ; un fichier introuvable ou une erreur de GStreamer est signalé (« Lecture impossible : … »).
	- Frise d'un fichier ([#224](https://github.com/dascritch/machincast/issues/224), `machincast.interface.frise`) : elle tient lieu de barre de position, sur toute la durée du fichier ; un stream, l'antenne et la fenêtre sans sonore n'ont ni frise ni barre de position. Elle montre :
		- la forme d'onde, calculée en tâche de fond dès que le fichier est chargé (`FormeDOnde`) : un pipeline GStreamer à part (`uridecodebin`, `audioconvert`, `level`, `fakesink` sans synchronisation) décode le fichier aussi vite qu'il le peut, et relève le niveau crête et le niveau moyen (RMS) du canal le plus fort ([#223](https://github.com/dascritch/machincast/issues/223)), par mesures de la durée du fichier sur 1 500, d'au moins 10 ms. Le minuteur de la fenêtre relève son bus : l'interface n'attend jamais, et la forme apparaît au fil du décodage. Le fichier n'est que lu. Un autre sonore, ou la fermeture de la fenêtre, arrête le calcul ; un fichier introuvable ou illisible le dit sur la frise (« Forme d'onde indisponible : … ») ;
		- les blancs détectés (`debut_detecte`, `fin_detectee`, [§ 6.1](#61-vérification-des-sonores-existants-hors-streams)) : hachures pleines, sur un voile, si le sonore est joué sans ses blancs (`detection_blancs`), hachures pâles s'ils sont joués ;
		- les crossfades, en rampes posées comme l'enveloppe de la diffusion (`machincast.lecture.moteur.enveloppe`), autour des blancs retirés selon les positions des fondus ([#234](https://github.com/dascritch/machincast/issues/234)) : une rampe qui déborde du fichier part, ou s'arrête, au volume qu'elle a au bord du fichier ; l'infobulle d'un fondu d'un sonore joué sans ses blancs dit sa position (« se termine au début détecté ») ; un crossfade non paramétré est celui des préférences ([§ 8.11](#811-menu)), et son infobulle le marque « (défaut) ». La montée n'a lieu à l'antenne que si le sonore précédent a un crossfade de fin, ce que dit son infobulle ;
		- la tête de lecture. Un clic, ou un glissement à son relâchement, place la lecture ; au clavier, les flèches la déplacent d'une seconde. L'infobulle nomme la zone sous la souris (« Blanc de fin : 0,50 s, retiré à l'antenne »), ou l'instant (« 0:01,00 »). Les zones se distinguent par leur motif, pas qu'à la couleur, celles du thème du poste. Hors de la lecture, la frise est inactive, mais ne se grise pas : elle garde ses couleurs.
		- Sous la frise, la partie jouée à l'antenne et sa durée (« Joué à l'antenne : 0:01,00 → 0:38,00 (0:37,00) »), qui suit la règle de la diffusion (`machincast.lecture.fondus.placer`, [#234](https://github.com/dascritch/machincast/issues/234)) : la lecture et ses fondus se placent autour des blancs selon les positions des fondus, suivie de « · blancs jamais mesurés » pour un fichier jamais audité (`audite_le`). « Début joué » place la lecture au début de la partie jouée, « Fin jouée » 5 secondes avant le fondu de sortie, ou avant la fin de la partie jouée sans fondu, jamais avant son début ; l'un et l'autre lancent la lecture au besoin. « Écouter comme à l'antenne » ne joue que la partie jouée : la lecture y commence, s'arrête à sa fin, et son volume (propriété `volume` du playbin) suit l'enveloppe des fondus, réglé à chaque relève ; décochée, la lecture reprend son plein volume.
		- La frise montre les valeurs enregistrées en base : une fiche modifiée s'enregistre avant d'être pré-écoutée. La banque par laquelle passera le sonore n'est pas connue : ses règles de crossfade et de détection de blanc n'y figurent pas.
	- VU-mètre : celui de l'accueil ([§ 8.1](#81-écran-par-défaut)), horizontal : niveau RMS de chaque canal (élément `level`), de -60 à 0 dB, orange au-delà de -12 dB, rouge au-delà de -3 dB, et crête par-dessus, avec son repère ; son échelle en dB, sous les canaux, va de -60 à gauche à 0 à droite.
	- Informations : format (codec), débit (celui des tags, sinon « ≈ » la taille du fichier sur sa durée), échantillonnage, canaux et, pour un stream, les secondes pré-décodées : la part remplie de son tampon de 5 secondes.
	- Sortie : sur la sortie de l'antenne (`audio.sortie`), le périphérique `audio.preecoute`, jamais celui de l'antenne. Le choix liste les périphériques du poste que voit GStreamer, comme `gst-device-monitor-1.0 Audio/Sink`, ceux de la sortie configurée seulement (`machincast.audio.peripheriques`) : nœuds PipeWire, désignés par leur `node.name`, périphériques PulseAudio ou ALSA, par leur nom interne ; celui de la diffusion y est grisé, suivi de « (diffusion) », et ne peut pas être choisi, même par le clavier ; le périphérique configuré vient d'abord, « (introuvable) » s'il est absent. Le choix arrête la lecture, et s'enregistre dans `audio.preecoute` du fichier de configuration, qui garde ses commentaires ; sans fichier, il vaut pour la session.
	- Écoute de l'antenne ([#24](https://github.com/dascritch/machincast/issues/24)) : un clic sur le VU-mètre de l'accueil charge l'antenne dans la fenêtre de pré-écoute, à la place du sonore précédent, à l'arrêt ; « Pré-écoute de l'antenne », en tête du menu « Diffusion », la charge de même et la lance aussitôt ([#223](https://github.com/dascritch/machincast/issues/223), [#245](https://github.com/dascritch/machincast/issues/245)). Le titre de la fenêtre est « en cours : » suivi du texte public du sonore en cours (champ `texte_public` de la socket d'état, `—` sans), qu'il suit tant que la fenêtre écoute l'antenne ; la source est « Antenne : » et le port de monitoring. Sous PipeWire, quand l'antenne et la pré-écoute y sont toutes deux, la lecture relie dans le graphe de PipeWire, par `pw-link` (`machincast.interface.liaison`), chaque port de monitoring de l'antenne (`<antenne>:monitor_FL`) à l'entrée du même canal du périphérique de pré-écoute (`<preecoute>:playback_FL`) ; une entrée unique, un casque mono, les reçoit tous. C'est une copie du flux de sortie, cadencée par PipeWire, sans rejouer le son ; le pipeline (port, `audioconvert`, `audioresample`, `level`, `fakesink`) ne fait que mesurer pour le VU-mètre. La pause, l'arrêt, un autre sonore, un autre périphérique et la fermeture de la fenêtre défont ces liens ; sans ports, ou sans `pw-link`, la lecture s'arrête et le dit. Avec PulseAudio, le pipeline joue ce port sur la sortie de pré-écoute. Dans les deux cas, comme un stream : sans position ni durée.

### 8.4 Écran de détails d'une banque

- Édition du nom interne et du nom public ([#99](https://github.com/dascritch/machincast/issues/99)).
- Masquage de l'artiste et du titre.
- Mode séquentiel ou aléatoire.
- Case « ne pas répéter » : la banque ne passe jamais deux fois de suite ([#63](https://github.com/dascritch/machincast/issues/63)).
- Case « détection de blanc », décochée pour une nouvelle banque : ses sonores sont joués sans leurs blancs détectés ([#146](https://github.com/dascritch/machincast/issues/146)).
- Durées minimale et maximale des sonores ([#147](https://github.com/dascritch/machincast/issues/147)), facultatives : un sonore qui en sort est marqué dans la liste de la fiche, d'après ses durées, avant même l'enregistrement, avec une infobulle (« 3:20 : plus court que le minimum de la banque, 3:30. »). Seules les durées de cette banque marquent ses sonores : un sonore hors des durées d'une autre banque n'y est pas marqué ([#210](https://github.com/dascritch/machincast/issues/210)) ; rien n'est refusé, sauf une minimale qui dépasse la maximale. La prochaine indexation le retire de la banque ([#195](https://github.com/dascritch/machincast/issues/195)).
- Crossfades de début et de fin ([#143](https://github.com/dascritch/machincast/issues/143)) : pour chacun, une règle, « Garder ceux des sonores », « Appliquer si le sonore n'en a pas » ou « Imposer à tous les sonores », et une durée, qui ne se modifie pas tant que la banque garde ceux des sonores.
- Liste des répertoires indexés : ajout et retrait.
- Liste des sonores liés, réordonnable par glisser-déposer en mode séquentiel. Ajout de sonores, y compris hors des répertoires de la banque.
- Retrait d'un sonore issu d'un répertoire de la banque : l'interface prévient qu'il sera réintégré à la prochaine indexation, et propose un lien ouvrant le navigateur de fichiers dans son répertoire. La suppression du fichier se fait hors de l'outil, parfois depuis un autre poste quand l'utilisateur n'a pas le droit d'écriture sur l'emplacement.
- Sélection multiple des sonores liés ([#114](https://github.com/dascritch/machincast/issues/114)) : une colonne État ; le clic droit sur plusieurs sonores les active ou les désactive, à l'enregistrement de la fiche (« Annuler » l'oublie ; un sonore en aperçu reste en aperçu) ; « Retirer le sonore » les retire tous, avec un seul avertissement pour ceux des répertoires de la banque ; « Monter » et « Descendre » ne servent qu'à un sonore seul.

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
- Priorité, choisie de la plus basse à la plus haute, comme `secours` < `fil_musical` < `emission` < `special` ([#253](https://github.com/dascritch/machincast/issues/253)) : secours, fil musical, émission, spécial.
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
- **Liste de lecture** : sonores, banques et séquences, comme la liste d'une séquence ([§ 8.12](#812-écran-de-détails-dune-séquence)) ; « Ajouter des feeds… » ([#167](https://github.com/dascritch/machincast/issues/167), `ListeElements._ajouter_feeds`) ajoute, pour chaque feed choisi, le premier stream par titre qui le suit, ou, sans stream qui le suive, crée à l'enregistrement un stream actif titré du nom du feed, un seul par feed ; un feed effacé entre-temps est oublié ; une séquence a pour détail son nombre d'éléments. Une liste vide s'enregistre, pour être complétée plus tard, avec un avertissement selon la priorité : une émission ou un spécial vide laisse l'antenne à l'événement de priorité inférieure, un fil musical vide se tait avec une alerte, un secours vide laisse le stream tombé à l'événement de priorité inférieure ([§ 4.2](#42-transitions), [#140](https://github.com/dascritch/machincast/issues/140)). Une ligne restée dans la liste garde son identifiant dans `evenements_elements`, que `airplay.element_id` désigne ([§ 4.2](#42-transitions)).
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

Mise en œuvre ([#37](https://github.com/dascritch/machincast/issues/37), `machincast.interface.simulation`) :

- **Onglet** : « Simulation », qui se ferme, unique ; **Affichage → Ouvrir l'onglet Simulation** l'ouvre, ou y revient avec son dernier résultat.
- **Période** : deux champs de date et d'heure, à la minute ; d'abord de l'heure qu'il est, à la minute, à un jour plus tard (`PERIODE`). Une fin qui ne suit pas le début ne lance rien (« La fin doit suivre le début. »). Pas de graine : chaque simulation tire au hasard (décision du ticket).
- **Lancement** : « Simuler » lance `Machin_lecture --simulation DEBUT FIN --repertoire R --nom simulation` (`commande_simulation`), par le Python de l'interface et avec sa configuration, dans un processus enfant (`QProcess`), sans attendre : l'interface reste utilisable, et la simulation garde le rôle de la lecture, sans rien écrire en base ([§ 5.5](#55-mode-simulation)). `R` est un répertoire temporaire, propre à l'onglet, jamais celui des sorties de la configuration ; il est effacé à la fermeture de l'onglet ou de la fenêtre, qui arrête une simulation en cours.
- **Résultat** : à la fin du processus, la table montre les passages de son CSV : Début, Fin, Artiste, Titre (masqués comme sur la page publique), Emplacement, Événement, Séquence, Banque. Le bilan compte les passages et les alertes ou incidents ; la liste sous la table donne ces derniers, lus sur la sortie d'erreur du binaire (les lignes `simulation : …`). Un échec affiche « Simulation impossible : » suivi du dernier message du binaire. Une nouvelle simulation remplace la précédente.
- **Export** : « Exporter… », actif après une simulation réussie, ouvre le sélecteur de fichier (`dialogues.choisir_export`), dont le filtre choisit la sortie copiée : .csv, .pls ou .html. Le nom proposé est `nom_par_defaut` de la période, et le fichier reçoit l'extension du format s'il ne l'a pas déjà (`avec_extension`) : un export ne remplace jamais un fichier sonore ([#96](https://github.com/dascritch/machincast/issues/96)). La barre d'état annonce le chemin écrit.

### 8.8 Ajout d'un sonore

- Fichier : par sélecteur de fichiers ou glisser-déposer. Déposer un fichier sur les sonores d'une banque l'enregistre déjà, à l'état `apercu` ([§ 8.4](#84-écran-de-détails-dune-banque)). Le fichier est référencé là où il se trouve, sans copie. Il peut être synchronisé depuis un autre ordinateur et changer de contenu sous le même nom (émission pré-enregistrée, rediffusion d'un direct). Il passe immédiatement par la vérification de l'indexeur.
- Stream : URL directe ou feed, et l'événement de secours.

Mise en œuvre ([#30](https://github.com/dascritch/machincast/issues/30), `machincast.interface.ajout`, `machincast.interface.verification`, `machincast.interface.fiche_sonore`) :

- **Fichiers** : « Ajouter des fichiers… » dans la liste des sonores (`dialogues.choisir_fichiers`, plusieurs à la fois), ou dépôt de fichiers sur la liste (`DepotDeFichiers`, copie seulement). Les fichiers sonores entrent en base en une transaction, sous leur chemin normalisé, à l'état `apercu` ; un fichier déjà en base ou choisi deux fois n'est pas ajouté de nouveau ; le reste est ignoré. La barre d'état annonce l'ajout.
- **Vérification immédiate** : `Verificateur` décode les sonores ajoutés dans un fil à part, l'une après l'autre des vérifications demandées, avec le code de l'indexeur (`verifier_sonores`, limité à ces sonores par `identifiants`) et son rôle en base (`Role.INDEXATION`, sur le socket et la base de la connexion de l'interface). Sa fin s'annonce dans la barre d'état, avec l'état de chaque sonore, et la liste ouverte se relit. Un décodeur absent ou une base injoignable laisse les sonores en aperçu, pour la prochaine indexation. Fermer la fenêtre attend la fin de la vérification en cours. Les fichiers déposés sur une banque, une séquence ou un événement ne sont pas vérifiés aussitôt (décision du ticket).
- **Stream** : « Nouveau stream » ouvre une fiche de sonore vide ; l'adresse directe ou le feed est obligatoire. Le stream entre en base à l'état `actif`, et ses autres champs s'écrivent comme une modification, marqués comme saisis à la main.

### 8.9 Suppression

- Un sonore présent dans un événement ou une banque n'est supprimé qu'après validation, en rappelant les événements et banques où il figure.
- Supprimer un sonore le retire des listes où il figure, **jamais son fichier**, qui reste à sa place ([#96](https://github.com/dascritch/machincast/issues/96)). Si le fichier est toujours dans le répertoire d'une banque, la prochaine indexation l'enregistre de nouveau comme un nouveau sonore.
- Même règle pour la suppression d'une banque, d'une séquence ou d'un événement.
- **Suppression différée** ([#267](https://github.com/dascritch/machincast/issues/267), partie de [#251](https://github.com/dascritch/machincast/issues/251)) : un sonore, une banque, une séquence ou un événement supprimé reste en base, marqué « supprimé » (`supprime_le`), jusqu'à sa péremption ; il n'est plus joué, ni proposé dans les listes, la recherche, les choix, les suggestions et la grille. Sa fiche se rouvre depuis l'historique, et se restaure. Un feed quitte la base.
- Les lignes `airplay` sont toujours conservées.

Mise en œuvre ([#33](https://github.com/dascritch/machincast/issues/33), `machincast.interface.suppression`, `Fiche.supprimer`) :

- **Bouton** « Supprimer… » au pied de chaque fiche, actif dès que l'élément est en base. La confirmation est toujours demandée (`dialogues.confirmer_suppression`, Entrée et Échap gardent l'élément), même pour un élément qui ne figure nulle part.
- **Question** : les banques, séquences et événements dont la liste contient l'élément, par nom, en signalant ceux qui n'auraient plus rien ; pour un sonore, son fichier, qui reste en place, et les banques dont un répertoire le contient, qui le réindexeront ; pour une banque, ses répertoires ; pour un événement, les streams qu'il secourt.
- **Question** : elle finit, sauf pour un feed, par « Marqué « supprimé », il se restaure depuis sa fiche. » (au féminin pour une banque ou une séquence).
- **Suppression** (`suppression.supprimer`, dans une transaction) : les lignes qui citent l'élément dans les listes des banques, des séquences et des événements sont effacées ; un événement ne secourt plus aucun stream (`secours_evenement_id` vidé) ; puis l'élément est marqué, `supprime_le` à l'heure de l'interface. Ses propres listes, ses répertoires, et les références de l'airplay et du log restent. Un feed est effacé (`DELETE`). Aucun fichier ni répertoire n'est touché. La fiche se ferme ensuite sans question ; un élément déjà effacé de la base ferme simplement sa fiche.
- **Fiche d'un élément supprimé** (`Fiche._montrer_la_suppression`) : rouverte depuis l'airplay, les incidents ou toute cellule qui le cite, elle dit « Supprimé le 19/10/2026 à 15:30 : « Restaurer » le remet en service. » ; ses champs, ses listes et ses boutons ne se modifient pas, et « Restaurer » remplace « Supprimer… ».
- **Restaurer** (`suppression.restaurer`) : `supprime_le` redevient vide ; l'élément ne revient pas dans les listes d'où il avait été retiré, ni comme secours des streams. Il est refusé si un autre élément a pris son nom, ou, pour un sonore, son fichier : « Restauration impossible : une autre banque s'appelle déjà « Publicité ». ».
- **Lecture et indexation** : la grille ignore les événements supprimés ; l'indexation ignore les sonores supprimés, et les répertoires des banques supprimées ; elle date la disparition d'un fichier (`disparu_le`).

### 8.10 Fil musical garanti

Si aucun événement de priorité fil musical n'existe, l'interface en recrée un.

Mise en œuvre ([#39](https://github.com/dascritch/machincast/issues/39), `machincast.interface.fil_musical.garantir`, appelé par `FenetrePrincipale`) :

- **Quand** : à l'ouverture de la fenêtre, après la suppression d'un événement, et après l'enregistrement d'un événement (qui peut avoir changé de priorité).
- **Quoi** : « Fil musical », permanent (sans début, ni fin, ni jours) et sans élément ; si ce nom est pris par un autre événement, le premier libre parmi « Fil musical 2 », « Fil musical 3 »… Sa liste reste à remplir dans sa fiche ; en attendant, la diffusion se tait et alerte quand il est à l'antenne ([§ 4.2](#42-transitions)).
- **Signalement** : la barre d'état le dit, et le journal le note en avertissement.

Suggestions au lancement ([#119](https://github.com/dascritch/machincast/issues/119), `machincast.interface.suggestions`, `FenetrePrincipale.proposer_au_lancement`, appelé par `Machin_interface` une fois la fenêtre montrée) :

- **Quand** : au lancement, si `interface.suggestions` est vrai (par défaut) et qu'il manque un événement de priorité fil musical, l'une des banques « Identifiant station », « Musique rotation lourde », « Musique rotation normale », « Musique rotation rare », « Musique rotation de nuit », « Partenariats », « Publicités », « Bande-annonce émissions » (nom interne, sans tenir compte des majuscules), ou, sur une sortie autre que `factice`, le périphérique de l'antenne (`audio.peripherique`). Elles remplacent alors la création automatique du fil musical au lancement, qui reste quand elles sont éteintes ; la garantie après la suppression ou l'enregistrement d'un événement ne change pas.
- **Fenêtre** : « Pour bien démarrer », modale (`dialogues.suggerer`) ; une ligne cochée par élément manquant ; le choix de l'antenne parmi les périphériques du poste de la sortie configurée, sauf celui de la pré-écoute ; « Ne plus proposer au lancement » ; « Créer » ou « Plus tard ».
- **Créer** : le fil musical comme ci-dessus ; les banques, sans répertoire, chacune avec ses réglages (`suggestions.REGLAGES`, [#231](https://github.com/dascritch/machincast/issues/231)) : « Identifiant station », aléatoire, marquée « ne pas répéter », de 2 minutes au plus ; les trois rotations lourde, normale et rare, aléatoires, de 15 minutes au plus ; la rotation de nuit, aléatoire, sans durée ; « Partenariats », « Publicités » et « Bande-annonce émissions », séquentielles, de 2 minutes au plus, avec des crossfades de début et de fin imposés à 0 seconde à tous leurs sonores, « Bande-annonce émissions » marquée « ne pas répéter » ; puis le premier fil musical sans élément, par nom, reçoit la rotation « Identifiant station », « Musique rotation lourde », « Musique rotation normale », « Musique rotation lourde », « Musique rotation rare », avec les banques qui existent. La barre d'état dit ce qui est créé.
- **Configuration** : l'antenne choisie et `interface.suggestions = false` s'écrivent par tomlkit, qui garde les commentaires du fichier ; sans fichier de configuration, rien ne s'écrit. Machin lecture prend l'antenne à son prochain démarrage.

### 8.11 Menu

- Ajouter un sonore, une banque, une séquence, un événement.
- Démarrer, arrêter le binaire lecture (via systemd et polkit, authentification par mot de passe ou empreinte digitale).
- Lancer une ré-indexation générale de toutes les banques.
- Choisir la sortie audio des pré-écoutes.

Mise en œuvre du menu ([#117](https://github.com/dascritch/machincast/issues/117), `FenetrePrincipale._garnir_menus`) :

- **Fichier** : « Préférences… » ([#145](https://github.com/dascritch/machincast/issues/145), `machincast.interface.preferences`). Sa première page, « Crossfades » ([#234](https://github.com/dascritch/machincast/issues/234)), règle la granularité, la durée maximale et les durées par défaut des crossfades, et la position des fondus par rapport aux blancs détectés : « Le fade-in, au début détecté » et « Le fade-out, à la fin détectée », chacun « commence », « est en cours » ou « se termine », enregistrés dans `crossfades.position_entree` et `crossfades.position_sortie`. Une frise de démonstration, celle de la pré-écoute ([§ 8.3](#83-écran-de-détails-dun-sonore)), non interactive, montre un sonore inventé de 30 s, aux blancs de 3 s et 4 s retirés à l'antenne, avec une forme d'onde inventée (`frise.forme_de_demonstration`), les durées par défaut saisies, même décochées, et les positions choisies ; elle suit chaque réglage, et sa légende donne la partie jouée. La page « Audio » règle les périphériques de l'antenne et de la pré-écoute, enregistrés dans `audio.peripherique` et `audio.preecoute` ; chacun est grisé dans l'autre choix, et « OK » ne donne jamais le même aux deux ([#116](https://github.com/dascritch/machincast/issues/116)) ; elle règle aussi le seuil de blanc, de -100 à -0,1 dB, enregistré dans `blancs.seuil` ([#146](https://github.com/dascritch/machincast/issues/146)) ; les réglages des crossfades s'enregistrent dans la section `[crossfades]` du fichier de configuration par tomlkit, qui garde ses commentaires ; les fiches ouvertes ensuite les suivent, et Machin lecture les prend à son prochain démarrage ; inactive sans fichier de configuration ; « Quitter » (Alt+Q), qui ferme la fenêtre comme sa case de fermeture, après la question sur les fiches modifiées. La page « Interface » affiche ou cache aussi le voyant « Saturation » de l'accueil, enregistré dans `interface.saturation`, et l'accueil le suit aussitôt ([#191](https://github.com/dascritch/machincast/issues/191)). Elle active ou éteint les suggestions au lancement, enregistrées dans `interface.suggestions` ([#119](https://github.com/dascritch/machincast/issues/119)). Elle choisit enfin l'icône de l'application ([#111](https://github.com/dascritch/machincast/issues/111)) : un aperçu, le chemin de l'image ou « Icône de MachinCast », « Choisir une image… » (SVG, PNG ou JPEG ; une image que Qt ne sait pas lire n'est pas prise, et la page affiche « Image illisible : … ») et « Icône de MachinCast », qui y revient. L'image est enregistrée dans `interface.icone`, retiré pour l'icône de MachinCast. Une icône changée vaut aussitôt pour les fenêtres, et pour les raccourcis déjà installés dans le menu des applications et sur le bureau (`machincast.raccourci.reecrire`), réécrits en gardant leurs droits, puisque sous Wayland la barre des tâches et le menu prennent l'icône du raccourci ; aucun raccourci n'est créé. La barre d'état dit où l'icône a été mise à jour. Au lancement, une icône illisible ou introuvable laisse celle de MachinCast, et la barre d'état le dit.
- **Affichage** : « Rechercher… » (Ctrl+F) ouvre l'onglet de la recherche globale ([#27](https://github.com/dascritch/machincast/issues/27), [§ 8.2](#82-recherche-et-navigation)) ; « Ouvrir l'onglet Sonores » et « Ouvrir l'onglet Feeds » ouvrent ces listes ([#180](https://github.com/dascritch/machincast/issues/180)) ; « Ouvrir l'onglet Grille horaire » ouvre l'onglet du calendrier, « Calendrier » ([§ 8.2](#82-recherche-et-navigation)) ; « Ouvrir l'onglet Simulation » ouvre l'onglet de la simulation ([#37](https://github.com/dascritch/machincast/issues/37), [§ 8.7](#87-écran-de-simulation)) ; « Ouvrir l'onglet Airplay » ouvre l'onglet de l'airplay ([#244](https://github.com/dascritch/machincast/issues/244), [§ 8.1](#81-écran-par-défaut)) ; « Pré-écoute… » ouvre la fenêtre de pré-écoute ([#116](https://github.com/dascritch/machincast/issues/116), [§ 8.3](#83-écran-de-détails-dun-sonore)) ; « Rafraîchir les onglets » (F5, [#148](https://github.com/dascritch/machincast/issues/148), `FenetrePrincipale.rafraichir`) relit l'onglet ouvert, l'airplay de l'accueil et chaque fiche ouverte (`Fiche.rafraichir`). Une fiche modifiée pose la question de fermeture (« avant de rafraîchir la fiche ») : enregistrer puis relire, abandonner et relire, ou la laisser telle quelle ; un enregistrement refusé la laisse aussi. La fiche d'un élément qui n'est plus en base se ferme. La barre d'état nomme les fiches laissées et fermées. Passer à un onglet le relit aussi ([#241](https://github.com/dascritch/machincast/issues/241), `FenetrePrincipale._onglet_ouvert`), s'il n'est pas en cours d'édition : une liste, les incidents, le calendrier, la recherche, l'onglet Airplay, l'airplay de l'accueil, et une fiche qui n'est pas modifiée, sans question ; une fiche modifiée reste telle quelle, et celle d'un élément effacé de la base se ferme (« Fiche fermée, son élément n'est plus en base : … »).
- **Diffusion**, en tête : « Pré-écoute de l'antenne », avec l'icône du casque, puis un trait ([#245](https://github.com/dascritch/machincast/issues/245)) ; elle écoute l'antenne aussitôt dans la fenêtre de pré-écoute ([§ 8.3](#83-écran-de-détails-dun-sonore)). Pendant l'écoute de l'antenne, lancée ou en pause, l'entrée devient « Arrêter la pré-écoute de l'antenne », qui l'arrête ; elle redevient « Pré-écoute de l'antenne » à l'arrêt, à la fermeture de la fenêtre ou quand elle passe à un sonore (`FenetrePreecoute.ecoute_changee`, [#256](https://github.com/dascritch/machincast/issues/256)). Alt+P fait l'un ou l'autre, dans la fenêtre principale ; pour le lui laisser, « Nom public » se saisit par Alt+U dans les fiches. Puis ([#25](https://github.com/dascritch/machincast/issues/25), `machincast.interface.pilotage`) : « Démarrer la diffusion », « Arrêter la diffusion » ; « Redémarrer » n'est plus proposé ([#223](https://github.com/dascritch/machincast/issues/223)) : arrêter puis démarrer fait de même. Avec le service `machincast.service` ([§ 10](#10-installation-et-déploiement)), chacune appelle `systemctl start|stop|restart machincast.service` dans un processus à part (`QProcess`), sans attendre : la règle polkit demande l'authentification d'un administrateur à l'agent polkit de la session ; jamais `sudo`. La barre d'état dit la réussite (« Diffusion démarrée. », « Diffusion arrêtée. », « Diffusion redémarrée. ») ou l'échec, avec le message de systemctl (« Diffusion non démarrée : … »). Les entrées suivent l'état du service (`ActiveState` de `systemctl show`, `machincast.service.lire_l_etat`), relu au lancement, à l'ouverture du menu et après chaque commande : arrêté ou en échec, démarrer ; en marche, arrêter. **Sans le service**, l'installation n'est pas définitive : la barre d'état le signale en permanence (« Installation non définitive : diffusion sans service »), avec une infobulle qui dit comment installer le service ; le menu pilote alors une **diffusion d'essai**, `Machin lecture` lancé à la main (ce n'est pas `Machin lecture --simulation`, qui ne joue rien) : « Démarrer la diffusion d'essai » lance `bin/Machin lecture`, la commande même du service (`pilotage.COMMANDE_DU_SERVICE`), qui lit la configuration du service, le `machincast.toml` du répertoire de MachinCast, et diffuse donc sur le même périphérique que lui ; dans une fenêtre de terminal (konsole, sinon x-terminal-emulator), détachée de l'interface. Une interface lancée sur une autre configuration le dit dans sa barre d'état ; `Machin lecture` annonce à son démarrage sa sortie, son périphérique et sa configuration ; « Arrêter la diffusion d'essai » envoie `SIGTERM`, comme `Ctrl-C`, au processus qui répond sur la socket d'état (son pid, lu par `SO_PEERCRED`, `ClientEtat.pid_du_lecteur`), et annonce l'arrêt quand la socket se ferme. Démarrer n'est active que sans diffusion sur la socket, arrêter qu'avec elle.
- **Interruptions** ([#104](https://github.com/dascritch/machincast/issues/104), [#228](https://github.com/dascritch/machincast/issues/228), `machincast.interface.interruption`) : après un trait, « Sauter au sonore suivant », « Sauter après la séquence », « Couper l'événement par le fil musical » ([§ 4.9](#49-interruption-manuelle)). Elles suivent l'état de la socket d'état : chacune n'est active que si son élément est à l'antenne, la dernière hors du fil musical (`evenement_priorite`), et son infobulle le nomme (« « Café à minuit » ») ou dit pourquoi elle est inactive (« Rien à l'antenne », « Aucune séquence à l'antenne », « Le fil musical est déjà à l'antenne »). Choisie, elle envoie la demande aussitôt, sans question (décision de [#104](https://github.com/dascritch/machincast/issues/104)) ; la barre d'état l'annonce (« Saut au sonore suivant demandé. »), ou dit que `Machin_lecture` ne répond pas sur sa socket d'état.
- **Maintenance** : « Moniteur de la sortie… », à venir ; « Indexation rapide » et « Audit complet » (ci-dessous).
- **Aide** : « Documentation » ouvre le guide de l'antenne, `doc/utilisateur/README.md` sur GitHub, dans le navigateur web ([#128](https://github.com/dascritch/machincast/issues/128)) ; « Signaler un problème… » ouvre les tickets GitHub dans le navigateur web (`dialogues.ouvrir_page`) ; « Version » montre le numéro de version et la date du dernier commit du dépôt d'où MachinCast est installé, à l'heure du poste (`machincast.interface.version`, `dialogues.montrer_version`), ou dit qu'elle est inconnue hors d'un dépôt git ou sans git.
- **À venir** : une entrée inactive, dont l'infobulle donne le ticket ; elle s'active avec son ticket. Ajouter un élément se fait depuis sa liste ([§ 8.2](#82-recherche-et-navigation)) ; la sortie des pré-écoutes se choisit dans la fenêtre de pré-écoute, que le menu « Affichage » ouvre ([#29](https://github.com/dascritch/machincast/issues/29)).

Mise en œuvre de la ré-indexation ([#38](https://github.com/dascritch/machincast/issues/38), [#120](https://github.com/dascritch/machincast/issues/120), `machincast.interface.indexation`) :

- **Menu** « Maintenance », avec « Indexation rapide » et « Audit complet » : les deux modes de `Machin_indexation` ([§ 6.0](#60-modes-dindexation)). Après un séparateur, « Maintenance de la base de données… » ([#127](https://github.com/dascritch/machincast/issues/127)) demande d'abord « Êtes-vous sûr de vouloir lancer cette opération ? », en donnant l'emplacement absolu où la sauvegarde sera enregistrée (`dialogues.confirmer_maintenance`, `pilotage.sauvegardes_de_la_maintenance`). « Choisir l'emplacement… » ouvre le sélecteur de répertoires sur cet emplacement, puis repose la question avec celui choisi ; un choix abandonné garde le précédent. Entrée et Échap l'annulent, et la barre d'état dit alors que rien n'a été lancé. Confirmée, elle ouvre `Machin maintenance-db --sauvegardes <emplacement> --garder-ouvert`, avec la configuration de l'interface, dans un terminal du poste (`pilotage.lancer_la_maintenance`, konsole ou x-terminal-emulator) ; la barre d'état dit qu'elle est lancée, ou qu'aucun terminal n'a été trouvé. Elle est inactive pendant une indexation, comme les deux autres.
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

### 8.13 Feeds de streams

- Création, modification et suppression des feeds ([§ 3.1](#feeds)) ; un feed qu'un stream suit ne se supprime pas.
- Test du flux à la demande.

Mise en œuvre ([#34](https://github.com/dascritch/machincast/issues/34), `machincast.interface.fiche_feed`, `listes.FEEDS`) :

- **Onglet** : la liste des feeds (nom, adresse, nombre de streams qui le suivent), avec « Nouveau feed » ; une fiche par feed, « Feed : <nom> », avec ce qui est commun aux fiches ([§ 8.4](#84-écran-de-détails-dune-banque)).
- **Champs** : nom obligatoire et unique, adresse obligatoire, enregistrés sans les espaces qui les entourent. La diffusion lit l'adresse du feed à chaque passage : une nouvelle adresse vaut pour tous les streams qui le suivent.
- **Test du flux** : `EssaiDeFlux`, comme pour un stream ([§ 8.3](#83-écran-de-détails-dun-sonore)), arrêté à la fermeture de la fiche.
- **Streams qui le suivent** : par titre, ou par l'adresse pour un stream sans titre ; ouvrir l'un d'eux ouvre sa fiche.
- **Suppression** : `suppression.question` lève `Empechee` pour un feed qu'un stream suit (la clé étrangère est `ON DELETE RESTRICT`) : la fiche nomme les streams, sans poser de question. Sinon, la confirmation habituelle ([§ 8.9](#89-suppression)).

### 8.14 Duplication

Un événement, une séquence ou une banque se duplique pour en faire une variante sans tout ressaisir ([#130](https://github.com/dascritch/machincast/issues/130)).

Mise en œuvre (`Fiche.copier`, `machincast.interface.fiche.nom_de_copie`, `FenetrePrincipale._dupliquer`) :

- **Accès** : le bouton « Dupliquer » au pied de la fiche, actif pour un élément enregistré dont la fiche n'est pas modifiée ; le clic droit sur une ligne des listes Événements, Séquences et Banques, entrée « Dupliquer » (`Liste.menu_de_la_ligne`, `Source.duplicable`). Les sonores et les feeds ne se dupliquent pas.
- **Nouvelle fiche** : la copie s'ouvre dans un nouvel onglet, « Nouvelle séquence, copie de Passage pub », sans rien écrire en base. Son nom interne est celui de l'original suivi de « (copie) », ou « (copie 2) », « (copie 3) »… s'il est pris, raccourci pour tenir dans les 255 caractères ; le nom public est le même. La fiche est modifiée dès son ouverture : « Enregistrer » crée l'élément, « Annuler » relit l'original, et fermer l'onglet demande quoi faire de la copie, comme pour toute fiche modifiée.
- **Ce qui est copié** :

| Élément | Copié | Pas copié |
| --- | --- | --- |
| Séquence | nom public, masquage, éléments dans l'ordre | les événements où elle figure |
| Événement | priorité, nom public, masquage, liste de lecture dans l'ordre | début, fin et jours de récurrence : une émission ou un spécial ne s'enregistre pas sans début, et le refus des chevauchements s'applique comme à tout événement |
| Banque | nom public, mode, masquage, « ne pas répéter », crossfades, durées des sonores, répertoires | la liste des sonores : la prochaine indexation la remplit depuis les répertoires |

- **Original intact** : les lignes d'une liste copiée sont des lignes nouvelles de la copie (`ListeElements.charger(…, copie=True)`) ; l'enregistrement ne reprend jamais une ligne d'une autre séquence ou d'un autre événement. Si l'original est effacé de la base pendant que sa copie est ouverte, « Annuler » et le rafraîchissement laissent la copie telle quelle, en le disant ; elle s'enregistre toujours.

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
| `audio.peripherique` | texte | pour diffuser | Périphérique de l'antenne. Absent, `Machin_lecture` refuse de diffuser (code 2), sauf sur la sortie `factice`, et l'interface le signale dans sa barre d'état ; il se règle dans les préférences de l'interface, page « Audio » ([#116](https://github.com/dascritch/machincast/issues/116)). |
| `audio.preecoute` | texte | oui | Périphérique de pré-écoute, différent de celui de l'antenne ; la fenêtre de pré-écoute de l'interface le réécrit quand on choisit une autre sortie. |
| `sorties.csv` | chemin | oui | Airplay CSV (privé), un fichier par jour : la date du jour au format ISO 8601 s'ajoute au nom (`airplay.csv` donne `airplay-2026-10-15.csv`). |
| `sorties.pls` | chemin | oui | Playlist .pls (privé) des 100 derniers fichiers joués. |
| `sorties.html` | chemin | oui | Page HTML (public) du sonore à l'antenne et des 20 précédents. |
| `metadonnees.masquer` | booléen | oui | Masquage par défaut de l'artiste et du titre. |
| `metadonnees.texte_public` | texte, 255 caractères au plus | oui | Texte public affiché à la place de l'artiste et du titre masqués, quand l'événement n'a pas de nom public. |
| `crossfades.granularite` | `seconde` ou `dixieme` | non | Pas des crossfades dans l'interface ([#145](https://github.com/dascritch/machincast/issues/145)) ; `dixieme` par défaut. |
| `crossfades.maximum` | nombre de secondes, strictement positif | non | Crossfade le plus long que l'interface propose ; 10 par défaut ([#223](https://github.com/dascritch/machincast/issues/223)). |
| `crossfades.debut`, `crossfades.fin` | nombre de secondes, de 0 à `crossfades.maximum` | non | Crossfades d'un sonore qui n'en a pas de paramétré, et que sa banque ne règle pas ; absents, il n'en a pas. |
| `crossfades.position_entree`, `crossfades.position_sortie` | `commence`, `en_cours` ou `termine` | non | Où le fade-in se place par rapport au début détecté, et le fade-out par rapport à la fin détectée, d'un sonore joué sans ses blancs, quelle que soit sa banque ([#234](https://github.com/dascritch/machincast/issues/234), [§ 5.1](#51-lecture-audio)) ; `termine` et `commence` par défaut. |
| `blancs.seuil` | nombre de dB, de -100 compris à 0 exclu | non | Niveau crête sous lequel le début et la fin d'un sonore sont un blanc, mesuré par l'audit complet ; -40 par défaut ([#146](https://github.com/dascritch/machincast/issues/146), [§ 6.1](#61-vérification-des-sonores-existants-hors-streams)). Réglable dans les préférences de l'interface, page « Audio ». |
| `interface.suggestions` | booléen | non | Au lancement, l'interface propose de créer ce qui manque pour démarrer ; `true` par défaut, réglable dans les préférences, page « Interface », et par la case « Ne plus proposer au lancement » de sa fenêtre ([#119](https://github.com/dascritch/machincast/issues/119), [§ 8.10](#810-fil-musical-garanti)). |
| `interface.icone` | chemin | non | Image SVG, PNG ou JPEG, icône des fenêtres, des raccourcis et de la barre des tâches ; l'icône de MachinCast sans elle, ou si l'image manque ; une autre extension est refusée. Réglable dans les préférences, page « Interface » ([#111](https://github.com/dascritch/machincast/issues/111)). |
| `interface.saturation` | booléen | non | Le voyant « Saturation » de la colonne Antenne de l'accueil est affiché ; `true` par défaut, réglable dans les préférences, page « Interface » ([#191](https://github.com/dascritch/machincast/issues/191)). |
| `lecture.socket_etat` | chemin | non | Socket d'état du binaire lecture, lue par l'interface ([§ 5.4](#54-socket-détat)). Par défaut `$XDG_RUNTIME_DIR/machincast/lecture.sock`. |

## 10. Installation et déploiement

- Cible : Ubuntu 26.04 LTS, et uniquement des versions LTS.
- Installation mono-utilisateur : un seul compte Unix utilise MachinCast, celui qui l'installe, et MachinCast se place dans son répertoire personnel.
- Livraison : archives `.tar.gz` publiées en releases sur le dépôt git (sur le repository <https://github.com/dascritch/machincast>).
- Chaque archive contient un `install.sh` ([#40](https://github.com/dascritch/machincast/issues/40)), à lancer depuis le répertoire de MachinCast (release décompressée ou dépôt git) avec son propre compte, jamais avec sudo : il demande sudo pour les seules étapes qui l'exigent. Relançable, il laisse en place chaque étape déjà faite. `./install.sh --simulation` affiche les commandes sans rien exécuter ; `./install.sh --dev` installe en plus les outils du poste de développement (paquets `bats`, `shellcheck` et `desktop-file-utils`, extra `[dev]` de pip, [#77](https://github.com/dascritch/machincast/issues/77)). Il :
	- vérifie le système : Ubuntu LTS, la cible étant 26.04 ;
	- liste les programmes de MachinCast en cours, sous tous les comptes du poste (`machincast.programmes`, bibliothèque standard seulement, lancé par le `python3` du système avant le venv, [#254](https://github.com/dascritch/machincast/issues/254)) : Machin lecture (service de diffusion, d'après son groupe de contrôle ; diffusion d'essai ; simulation), Machin indexation, Machin interface. S'il y en a, il demande de les arrêter pendant l'installation (`--arreter-les-programmes`, `--laisser-les-programmes` répondent d'avance ; sans terminal, ils continuent) : le service par `systemctl stop`, les autres par `SIGTERM`, puis `SIGKILL` après 15 secondes, avec `sudo` pour un autre compte. À la fin, même après un échec (`trap … EXIT`), il relance le service, et, pour son compte, la diffusion d'essai dans un terminal et l'interface, détachées, avec leurs arguments et depuis leur répertoire ; l'état des programmes arrêtés passe par un fichier JSON, jamais par une ligne de commande évaluée. Il dit ce qui reste à rouvrir à la main ;
	- installe par apt les seules dépendances système (bibliothèques de compilation de PyGObject, GStreamer et ses plugins, PostgreSQL, autocomplétion bash) ;
	- crée un environnement virtuel Python isolé, **sans** `--system-site-packages`, et y installe toutes les dépendances Python par pip (PySide6, PyGObject, psycopg, yoyo-migrations, python-magic, tomlkit). Le projet suit ainsi l'évolution des paquets sans dépendre des versions de la distribution hôte ;
	- copie `machincast.exemple.toml` en `machincast.toml` s'il n'existe pas ;
	- crée, en tant qu'utilisateur `postgres`, le rôle PostgreSQL du compte courant, **sans aucun droit particulier** (ni `CREATEDB`, ni `CREATEROLE`), les bases de production et de test dont ce compte devient propriétaire, et les trois rôles de groupe ; le compte applique ensuite le schéma, ce que la propriété des bases lui permet ;
	- autorise le compte courant à endosser les trois rôles de MachinCast, en tant qu'utilisateur `postgres` ; un autre compte s'ajoute plus tard de la même façon (voir `INSTALL.md`, [#71](https://github.com/dascritch/machincast/issues/71)) ;
	- ajoute le compte courant au groupe `systemd-journal`, pour suivre les logs du service avec `Machin logs` ;
	- installe en place : `/opt/machincast` est un lien vers le répertoire de MachinCast, `Machin` est relié depuis `/usr/local/bin`, l'autocomplétion depuis `/usr/share/bash-completion/completions` ;
	- vérifie que GStreamer sait décoder chacun des formats de la spec et créer la sortie audio configurée, sans jouer de son, et nomme sinon le paquet manquant (`python -m machincast.installation verifier`) ;
	- installe le raccourci de l'interface ([#62](https://github.com/dascritch/machincast/issues/62)), rédigé par `machincast.installation raccourci` (`machincast.raccourci`, avec l'icône de `interface.icone` quand elle existe, [#111](https://github.com/dascritch/machincast/issues/111) ; Desktop Entry Specification 1.5, validé par `desktop-file-validate`) : `bin/Machin interface`, lancé depuis le répertoire de MachinCast (clé `Path`), avec l'icône de MachinCast, `src/machincast/interface/machincast.png` : le logo des équipes techniques de la radio qui commissionne le logiciel, un panneau de chantier orange en losange avec un casque audio, PNG carré de 512 pixels aux coins transparents, lisible de 16 à 256 pixels ([#213](https://github.com/dascritch/machincast/issues/213)). Il va dans le menu des applications du compte (`$XDG_DATA_HOME/applications`, par défaut `~/.local/share/applications`), sans sudo. Il va aussi sur le bureau du compte (`xdg-user-dir DESKTOP`), exécutable, pour que Plasma le lance sans avertissement, si l'administrateur répond oui à la question posée à la première installation, ou avec `--bureau` ; `--sans-bureau` ne le dépose pas, et sans terminal la question n'est pas posée. Un raccourci déjà sur le bureau est mis à jour à chaque relance. L'application Qt porte la même icône, et se réclame du raccourci `machincast` (`setDesktopFileName`), pour que la barre des tâches retrouve son nom et son icône sous Wayland.
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
- **Droits sur les feeds** : modifiables par l'interface seule ; le binaire lecture les lit, l'indexeur n'y accède pas ([#50](https://github.com/dascritch/machincast/issues/50), voir [§ 3.2](#32-rôles-et-droits)).
- **Banque « ne pas répéter »** : un élément qui rappellerait une banque marquée « ne pas répéter » juste après elle est sauté, même d'un événement à l'autre ; s'il ne reste rien d'autre de jouable, l'événement se termine et l'événement inférieur prend le relais ([#63](https://github.com/dascritch/machincast/issues/63), voir [§ 4.4](#44-choix-dun-sonore-dans-une-banque)).
- **État d'un sonore** : le booléen `actif` devient un état `actif`, `desactive`, `expire`, `errone` ou `supprime` ; seul l'indexeur rétablit automatiquement un sonore, quand il l'avait lui-même déclaré `errone` ([#66](https://github.com/dascritch/machincast/issues/66), voir [§ 3.1](#sonores)).
- **Durées d'une banque** : l'indexation, rapide ou complète, retire d'une banque les sonores de durée connue qui sortent de ses durées, même ajoutés à la main, et n'y rattache pas un sonore connu hors de ses durées ([#195](https://github.com/dascritch/machincast/issues/195), voir [§ 6.2](#62-indexation-des-répertoires-de-banques)).
- **Indexation rapide** : par défaut, l'indexeur ne décode que les nouveaux fichiers, à l'état `apercu`, et ceux dont la date ou la taille a changé ([#10](https://github.com/dascritch/machincast/issues/10)), et repère les fichiers disparus ; l'audit complet (`--audit-complet`) décode ce qui n'a pas encore été audité à ce seuil de blanc, ou a changé depuis, et `--forcer` tout ([#69](https://github.com/dascritch/machincast/issues/69), [#206](https://github.com/dascritch/machincast/issues/206), voir [§ 6.0](#60-modes-dindexation)).
- **Détection de blanc** : mesurée par l'audit complet seulement, au seuil `blancs.seuil` (-40 dB par défaut) ; la fin détectée se compte depuis la fin du fichier ; appliquée à un sonore qui l'active ou fourni par une banque qui l'active, jamais par défaut ; un sonore sans blanc détecté est joué en entier ([#146](https://github.com/dascritch/machincast/issues/146), voir [§ 5.1](#51-lecture-audio) et [§ 6.1](#61-vérification-des-sonores-existants-hors-streams)).
- **Environnement virtuel** : isolé des paquets système, toutes les dépendances Python passent par pip ([#51](https://github.com/dascritch/machincast/issues/51), voir [§ 10](#10-installation-et-déploiement)).
