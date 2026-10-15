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
| **Événement** | Une plage horaire, éventuellement récurrente, avec une priorité et une liste de lecture de banques et/ou de sonores. |
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
| `artiste`, `titre` | Métadonnées publiques, pré-remplies depuis les tags à l'indexation. Ce sont des colonnes, car elles servent au masquage, à la recherche et à l'airplay. |
| `metadonnees_musicales` | Objet JSON des métadonnées non critiques (année, label, genre…), pré-remplies depuis les tags. Extensible sans migration. |
| `crossfade_debut`, `crossfade_fin` | Temps de crossfade en début et en fin de sonore. |
| `max_lectures` | Nombre maximum de lectures sur la totalité de l'historique. Vide = illimité. |
| `etat` | État du sonore ([#66](https://github.com/dascritch/machincast/issues/66)) : `actif`, `desactive`, `expire`, `errone` ou `supprime` (voir ci-dessous). Seul un sonore `actif` peut être joué. |
| `masquer_metadonnees` | Masquage de l'artiste et du titre au niveau du sonore. Vide = hérite du niveau inférieur. |
| `duree` | Calculée par l'indexeur. Vide pour un stream. |
| `debut_diffusion`, `fin_diffusion` | Période de diffusion facultative (annonces limitées dans le temps). |
| `fichier_modifie_le`, `fichier_taille` | Date de modification et taille du fichier au dernier passage de l'indexeur, pour détecter un changement de contenu. |
| `champs_edites` | Liste des champs saisis à la main dans l'interface. L'indexeur ne les modifie plus jamais. |
| `indexe_le` | Date de la première indexation. |
| `modifie_le` | Horodatage de la dernière modification en base. |

États d'un sonore ([#66](https://github.com/dascritch/machincast/issues/66)) :

| État | Affiché | Posé par | Sens | Retour à `actif` |
| --- | --- | --- | --- | --- |
| `actif` | actif | interface, indexeur | jouable, sous réserve de sa période de diffusion et de son maximum de lectures | — |
| `desactive` | désactivé | interface | choix humain | par l'interface seulement |
| `expire` | expiré | binaire lecture | maximum de lectures atteint ou fin de la période de diffusion ([§ 4.5](#45-sonore-jouable)) | par l'interface seulement |
| `errone` | erroné | indexeur | fichier illisible ou endommagé | automatique, par l'indexeur, quand le fichier redevient sain |
| `supprime` | supprimé | indexeur | fichier introuvable (supprimé ou déplacé) | par l'interface seulement ; un fichier déplacé est réindexé comme nouveau sonore |

L'indexeur ne change l'état que d'un sonore `actif` ou `errone`. Un sonore `desactive`, `expire` ou `supprime` garde son état, même si son fichier est défectueux ; l'anomalie est quand même signalée.

Contraintes :

- `type = fichier` ⇒ `emplacement` renseigné, `url_stream` et `marque_page_id` vides.
- `type = stream` ⇒ exactement un de `url_stream` ou `marque_page_id` renseigné.

Pas de champ format ni fréquence d'échantillonnage : l'échantillonnage peut varier dans un fichier lossy et n'a pas d'utilité en lossless.

#### `marques_pages_streams`

| Champ | Description |
| --- | --- |
| `id`, `nom`, `url` | Une URL de stream réutilisable, souvent fonctionnelle par intermittence. |

#### `banques`

| Champ | Description |
| --- | --- |
| `id`, `nom_interne` | Identification. |
| `mode` | `sequentiel` ou `aleatoire`. |
| `masquer_metadonnees` | Masquage au niveau de la banque. Vide = hérite. |
| `ne_pas_repeter` | La banque ne peut pas passer deux fois de suite, même d'un événement à l'autre (voir [§ 4.4](#44-choix-dun-sonore-dans-une-banque), [#63](https://github.com/dascritch/machincast/issues/63)). Faux par défaut. |
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
| `id`, `nom_interne`, `nom_public` | Identification. |
| `priorite` | `fil_musical` < `emission` < `special`. |
| `debut`, `fin` | Date et heure de début et de fin de la première occurrence. Voir les règles ci-dessous. |
| `jours_recurrence` | Jours de la semaine où l'événement se répète, nommés de `lundi` à `dimanche` (plusieurs jours possibles). Vide = pas de récurrence. Tous les jours cochés = quotidien. |
| `masquer_metadonnees` | Masquage au niveau de l'événement. Vide = hérite. |
| `modifie_le` | Horodatage de la dernière modification, utilisé pour départager deux événements en conflit. |

Règles sur les dates :

- Seuls les événements de priorité `fil_musical` peuvent avoir un `debut` vide. Un fil musical sans `debut` ni `fin` est permanent.
- Les priorités `emission` et `special` peuvent avoir une `fin` vide. Leur liste de lecture ne boucle alors pas : l'événement se termine quand sa liste est épuisée.
- Un événement peut passer minuit.
- Pas de date de fin de récurrence, pas d'exceptions (jours fériés).

#### `evenements_elements`

| Champ | Description |
| --- | --- |
| `evenement_id`, `position` | Liste ordonnée, réordonnable par glisser-déposer. |
| `banque_id`, `sonore_id` | Exactement un des deux est renseigné. |

Un même élément peut apparaître plusieurs fois dans la liste (par exemple un jingle entre chaque titre).

#### `airplay`

L'historique de diffusion. Les lignes ne sont **jamais supprimées**, même quand le sonore, la banque ou l'événement l'est.

| Champ | Description |
| --- | --- |
| `id`, `passage_id` | Une ligne au début et une ligne à la fin de chaque passage, reliées par `passage_id`. |
| `type_ligne` | `debut` ou `fin`. |
| `horodatage` | Heure de début ou de fin. |
| `sonore_id`, `banque_id`, `evenement_id` | Références facultatives. `banque_id` est indispensable au cycle aléatoire propre à chaque banque. |
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

Le schéma est créé par la migration `src/machincast/migrations/0001.schema-initial.sql`, puis modifié par les suivantes (`0003.etat-sonores` : état d'un sonore, [#66](https://github.com/dascritch/machincast/issues/66)).

- Durées (`duree`, crossfades, `duree_diffusee`) : type `interval`. Dates : `timestamptz`.
- Textes saisis à la main (noms internes et publics, artiste, titre, nature d'une entrée du log) : `varchar(255)`, la même limite que l'interface. Chemins, URL et messages détaillés : `text`, sans limite fixée à l'avance.
- Valeurs énumérées : types `ENUM` PostgreSQL (`type_sonore`, `mode_banque`, `priorite_evenement`, `jour_semaine`, `type_ligne_airplay`, `niveau_log`, `etat_sonore`). Leur ordre de déclaration permet les comparaisons : `fil_musical < emission < special`, `lundi < … < dimanche`.
- `jours_recurrence` : tableau de `jour_semaine`. La récurrence est calculée en heure locale par le binaire lecture.
- `metadonnees_musicales` : objet JSON (`jsonb`), jamais un tableau ni une valeur nulle.
- Un événement ne peut pas avoir de fin sans début.
- Positions dans `banques_sonores` et `evenements_elements` : uniques par banque ou par événement, vérifiées en fin de transaction pour permettre de réordonner.
- Suppressions : un lien de banque ou un élément d'événement disparaît avec la banque, le sonore ou l'événement qu'il référence ; `airplay` et `log` gardent leurs lignes, avec la référence passée à vide. Un marque-page utilisé par un sonore ne peut pas être supprimé. La validation préalable des suppressions est faite par l'interface ([§ 8.9](#89-suppression)).
- Pour un stream, la colonne `emplacement` de `airplay` recopie l'URL diffusée.
- `modifie_le` est mis à jour par un déclencheur à chaque modification de `sonores`, `banques` et `evenements`.

### 3.2 Rôles et droits

Un rôle PostgreSQL par binaire : `machincast_lecture`, `machincast_indexation`, `machincast_interface`. Ils sont créés par la migration `0002.droits` ([#4](https://github.com/dascritch/machincast/issues/4)) et partagés par la base de production et la base de test.

- Ce sont des **rôles de groupe**, sans connexion. Un utilisateur système se connecte avec son propre rôle, par authentification **peer** sur la socket Unix.
- L'utilisateur est membre des rôles qu'il peut endosser, **sans en hériter les droits** : connecté, il n'a accès à rien. Chaque binaire endosse son rôle par `SET ROLE` dès la connexion (`machincast.base.connecter`). L'indexation lancée depuis l'interface, sous l'utilisateur de bureau, agit donc avec les seuls droits de l'indexation.
- Un administrateur autorise un utilisateur avec `python -m machincast.droits --base <base> autoriser <utilisateur> <rôle>…` ; `install.sh` l'utilise ([#40](https://github.com/dascritch/machincast/issues/40)).
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
| `airplay` | lire, insérer | — | lire |
| `log` | insérer (sans `RETURNING`) | — | lire |

L'indexation ne supprime rien : un fichier disparu fait passer son sonore à l'état `supprime`. Quand l'interface supprime un élément, les références dans `airplay` et `log` passent à vide avec les droits du propriétaire des tables ; l'interface n'a pas besoin de droit d'écriture sur ces deux tables.

## 4. Règles d'ordonnancement

### 4.1 Choix de l'événement actif

1. À tout instant, l'événement actif est celui de plus haute priorité dont la plage couvre l'instant, sauf s'il s'est terminé plus tôt pour cette occurrence (liste épuisée d'un événement sans fin, ou banque « ne pas répéter » sans autre élément jouable, voir [§ 4.4](#44-choix-dun-sonore-dans-une-banque)).
2. Deux événements de même priorité ne doivent pas se chevaucher : l'interface l'interdit à la saisie. Si le cas se présente quand même, le binaire joue le **dernier modifié en base**.
3. Plusieurs fils musicaux peuvent coexister selon l'heure (nuit, jour), régis par leur récurrence.
4. Le changement d'heure ne fait l'objet d'aucune règle particulière : la diffusion est toujours en fil musical à cette heure de la nuit.

### 4.2 Transitions

- **Début d'un événement** : il coupe **net** le sonore en cours, quel que soit le sonore.
- **Fin d'un événement** : si aucun autre événement ne suit, le dernier sonore est joué jusqu'au bout, puis le suivant est choisi selon les règles du fil musical actif. Si un autre événement suit immédiatement, son début coupe net le dernier sonore.
- **Retour au fil musical** : il reprend à l'élément qui suit le dernier joué, d'après la table `airplay`.

### 4.3 Liste de lecture d'un événement

- Les éléments sont joués dans l'ordre de `position`.
- Un élément banque fait jouer **un seul** sonore de cette banque.
- Si la liste est terminée avant la fin de l'événement, elle reprend au début (boucle).
- Un événement `emission` ou `special` sans date de fin ne boucle pas : il se termine à la fin de sa liste.

### 4.4 Choix d'un sonore dans une banque

- **Séquentiel** : le sonore qui suit, dans l'ordre de `position`, le dernier joué via cette banque.
- **Aléatoire contrôlé** : un sonore joué via cette banque n'est plus rejouable tant que tous les autres sonores de la banque n'ont pas été joués. Chaque banque a son propre cycle.
- Seuls les sonores **jouables** sont candidats (voir ci-dessous). Si aucun ne l'est, on passe à l'élément suivant de l'événement, comme si la banque était vide.
- **Ne pas répéter** ([#63](https://github.com/dascritch/machincast/issues/63)) : si le dernier passage de l'`airplay` a été joué via une banque marquée `ne_pas_repeter`, l'élément qui rappelle cette banque est sauté, et on passe à l'élément suivant, comme si la banque était vide. Un événement à l'autre, la règle s'applique de la même façon : la banque en fin d'un événement puis au début du suivant ne passe pas deux fois. Seuls comptent les passages joués via la banque, comme pour le cycle aléatoire : un sonore de la banque placé directement comme élément d'un événement ne compte pas.
	- Si, une fois la banque sautée, plus rien n'est jouable dans la liste de l'événement, cet événement se termine pour cette occurrence : l'événement de priorité inférieure dont la plage couvre l'instant prend le relais. Pour un fil musical, silence et alerte, comme quand rien n'est jouable.
	- Log : `info` pour chaque élément sauté, `alerte` pour un événement terminé plus tôt.

### 4.5 Sonore jouable

Un sonore est jouable s'il est à l'état `actif`, si l'instant est dans sa période de diffusion (quand elle est renseignée), et si son maximum de lectures n'est pas atteint.

Passages automatiques à l'état `expire` par le binaire lecture, chacun consigné dans le log :

- maximum de lectures atteint (compté sur la totalité de l'historique `airplay`) ;
- date de fin de diffusion passée.

### 4.6 Sonore « sain »

Indicateur affiché pour le prochain sonore : fichier présent, actif, lisible, dernière lecture sans incident. Un stream n'est pas testé automatiquement ; l'interface permet de le tester à la demande.

### 4.7 Streams

- Un stream s'arrête au premier déclencheur, par ordre de priorité : début d'un événement de priorité égale ou supérieure, puis fin de l'événement en cours, puis fin de diffusion du stream.
- Si le flux tombe : passage à l'élément suivant, avec des tentatives de reconnexion en tâche de fond.
- Les métadonnées ICY du flux ne sont pas relayées.

### 4.8 Métadonnées publiques et masquage

Artiste et titre sont **masqués**, jamais remplacés. Chaque niveau porte son indicateur de masquage. La valeur retenue est celle du premier niveau renseigné, dans cet ordre de priorité :

**Événement > Banque > Sonore > valeur par défaut du fichier de configuration**

Les sorties privées affichent toujours tout. Les sorties publiques respectent le masquage.

Quand l'artiste et le titre sont masqués, la sortie publique affiche à leur place :

1. le nom public de l'événement en cours, s'il est renseigné ;
2. sinon, le texte public par défaut de la configuration (`metadonnees.texte_public`).

## 5. Binaire lecture

`Machin_lecture` ne fait que lire les événements et les jouer. Il lit le fichier de configuration à son lancement et tourne comme service systemd.

### 5.1 Lecture audio

- Bibliothèque : GStreamer via PyGObject (lecture, crossfade, streams).
- Sortie au choix dans la configuration : ALSA, PulseAudio ou PipeWire, chacune fournie par son greffon GStreamer (`gstreamer1.0-alsa`, `gstreamer1.0-pulseaudio`, `gstreamer1.0-pipewire`). La sortie `factice` ne joue aucun son, pour les tests et les essais (`machincast.audio`).
- L'heure courante est lue par une horloge injectable (`machincast.horloge`) et les tirages aléatoires par un générateur à graine (`machincast.hasard`).
- Crossfade selon `crossfade_debut` et `crossfade_fin` de chaque sonore.
- Avant de jouer un fichier, le binaire compare sa date de modification et sa taille avec la base. En cas d'écart, il le consigne dans le log ; c'est l'indexeur qui mettra la base à jour.
- S'il n'a aucun élément à lire dans le fil musical, il émet un silence et lève une alerte dans le log.

### 5.2 Écritures

- `airplay` : une ligne au début et une ligne à la fin de chaque passage (insertions seules).
- `log` : toutes les opérations, normales comme incidents.
- `sonores.etat` : passage à `expire` ([§ 4.5](#45-sonore-jouable)).

### 5.3 Modules de sortie

| Module | Visibilité | Contenu |
| --- | --- | --- |
| stdout | privé | Sonores lancés (airplay). |
| stderr | privé | Incidents et crashes. |
| CSV | privé | Airplay. |
| .pls | privé | Playlist de fichiers. |
| HTML | public | Airplay, avec masquage appliqué. |

Un module privé indique tous les sonores. Un module public applique le masquage ([§ 4.8](#48-métadonnées-publiques-et-masquage)).

### 5.4 Socket d'état

Le binaire expose une socket Unix donnant à l'interface : état de marche, sonore en cours (début, durée, fin estimée, progression), prochain sonore (début et fin estimés, durée, indicateur « sain »).

### 5.5 Mode simulation

Sur option de lancement, le binaire simule la diffusion entre deux dates et heures :

- aucune écriture en base, aucune sortie sonore ;
- l'état de départ (positions séquentielles, cycles aléatoires, compteurs de lectures) est lu depuis `airplay`, puis tenu en mémoire pendant toute la simulation ;
- une graine (seed) rend le hasard reproductible, notamment pour les tests ;
- seules des sorties .csv, .pls et .html sont produites, nommées par défaut avec un préfixe `simulation` suivi des dates de début et de fin, nommage modifiable par paramètre.

## 6. Binaire indexation

`Machin_indexation` est déclenché depuis l'interface. Un cron ou un timer systemd pourra être ajouté plus tard selon les retours du terrain.

### 6.1 Vérification des sonores existants (hors streams)

- Décodage complet du fichier (GStreamer), pour s'assurer qu'il n'est pas endommagé ([#7](https://github.com/dascritch/machincast/issues/7)). Le fichier est décodé sans être joué, bien plus vite que le temps réel (une dizaine de minutes de son en moins d'une seconde).
- GStreamer est tolérant : la plupart des fichiers tronqués ou corrompus se décodent sans erreur, en un son plus court ou parasité. Le verdict repose donc sur trois signes :
	- **introuvable** : aucun fichier à son emplacement ;
	- **illisible** : erreur de GStreamer (fichier qui n'est pas du son, vide, conteneur cassé), aucun son décodé, ou décodage qui ne progresse plus pendant 30 secondes (disque ou partage réseau bloqué). Un décodage qui ne produit aucun son en 5 secondes est repris depuis le début, jusqu'à trois tentatives : GStreamer se bloque parfois au démarrage d'un pipeline (environ un décodage sur cent, fichiers sains compris), et un disque réseau en veille a ainsi le temps de répondre ;
	- **endommagé** : rupture de continuité dans le son décodé, signe que le décodeur a sauté des données (constaté en MP3, Ogg et M4A) ;
	- **endommagé** : durée décodée plus courte que la durée annoncée par l'en-tête, au-delà de 75 ms ou de 0,1 % (fichier tronqué ou trames perdues, constaté en FLAC, AIFF et M4A).
- Limites propres aux formats : des octets altérés dans un WAV ou un AIFF passent inaperçus (ni somme de contrôle ni trames) ; un WAV, un Ogg ou un MP3 sans en-tête de durée tronqué se décode comme un fichier plus court et sain.
- Fichier sain : la durée décodée, la date de modification et la taille du fichier sont enregistrées ; un sonore `errone` redevient `actif`.
- Fichier illisible ou endommagé : signalé sur STDERR, sonore `actif` passé `errone`.
- Fichier introuvable (supprimé ou déplacé) : signalé sur STDERR, sonore `actif` ou `errone` passé `supprime`. Un fichier déplacé sera réindexé comme nouveau sonore.
- Un sonore `desactive`, `expire` ou `supprime` garde son état ; son fichier défectueux est quand même signalé ([§ 3.1](#sonores), [#66](https://github.com/dascritch/machincast/issues/66)).
- Décodeur GStreamer absent pour un format : la vérification s'arrête et indique les paquets à installer, sans changer l'état du sonore, car le fichier n'y est pour rien.
- Date de modification ou taille changée : nouvelle vérification complète, mise à jour de la durée et des tags, **sans toucher aux champs édités à la main**.

### 6.2 Indexation des répertoires de banques

- Parcours récursif de chacun des répertoires de chaque banque.
- Formats : mp3, m4a/AAC (« mp4 »), ogg, flac, wav, aiff.
- Chaque fichier non encore indexé est vérifié, ajouté à `sonores` avec sa durée et ses tags (ID3, Vorbis comments) pour l'artiste, le titre et les métadonnées musicales (année, etc.), puis rattaché à la banque en fin de liste.

### 6.3 Sorties

STDOUT et STDERR uniquement, plus une sortie texte au format CSV et HTML. L'indexeur n'écrit pas dans le log.

- STDERR : une ligne par fichier défectueux, désigné par son chemin, avec le problème et la conséquence (« sonore passé erroné », « état désactivé conservé »). Les messages passent par `logging` : anomalies (`warning`) et erreurs (`error`) sur STDERR, informations sur STDOUT.
- Les anomalies relevées seront regroupées dans un document d'audit, en CSV et en HTML ([#11](https://github.com/dascritch/machincast/issues/11)).
- STDOUT : le bilan des changements d'état, par exemple « 12 sonores vérifiés : 1 erroné, 0 supprimé, 1 rétabli ».
- Code de sortie : 0 quand la vérification est allée au bout, même si des sonores ont changé d'état : ce sont des anomalies non bloquantes ; 1 si la base est injoignable ou si un décodeur manque ; 2 pour une configuration invalide.

## 7. Wrapper Machin

Script bash `Machin` ([#6](https://github.com/dascritch/machincast/issues/6)) :

```
Machin [--config FICHIER] BINAIRE [OPTIONS…]
Machin logs [OPTIONS DE journalctl…]
Machin -h | --help | --binaires
```

- `Machin BINAIRE` appelle `Machin_BINAIRE` (`lecture`, `indexation` ou `interface`) en lui transmettant toutes les options qui suivent, intactes, et se termine avec son code de sortie. Le binaire est cherché d'abord dans le venv du projet (`.venv`, à côté du répertoire `bin/` du wrapper, même appelé par un lien symbolique), puis dans le `PATH` : le wrapper prépare ainsi l'environnement, sans qu'il soit besoin d'activer le venv.
- `--config FICHIER` (ou `--config=FICHIER`), placé avant le binaire, lui est transmis, notamment pour les tests. Placé après le binaire, il est transmis tel quel.
- `-h` affiche une aide minimale de deux lignes, `--help` l'aide complète. L'aide d'un binaire s'obtient par `Machin BINAIRE --help`.
- `Machin logs` suit en direct le journal du service de lecture, `machincast.service` (`journalctl --unit=machincast.service --follow`). Les options qui suivent sont transmises à `journalctl`, par exemple `--since "1 hour ago"`. Le journal d'un service système n'est lisible que par les groupes `adm` (dont fait partie le premier compte créé à l'installation d'Ubuntu) et `systemd-journal` : tous les comptes de la radio doivent pouvoir le lire, `install.sh` les ajoute donc au groupe `systemd-journal`, qui donne la lecture du journal sans les droits d'administration de `adm` (voir [§ 10](#10-installation-et-déploiement)).
- `--binaires` liste les binaires, un par ligne ; l'autocomplétion s'en sert.
- Codes de sortie : celui du binaire ou de `journalctl` ; 2 pour un appel incorrect du wrapper (binaire ou option inconnus, `--config` sans fichier) ; 127 si le binaire ou `journalctl` est introuvable.

Autocomplétion bash (`bash-completion/Machin`) : binaires et `logs`, options du wrapper, fichiers après `--config`, options d'un binaire lues dans son aide, options courantes de `journalctl` après `logs`.

Le wrapper n'est pas copié dans le venv : en développement, il s'appelle par `bin/Machin`. `install.sh` installe le wrapper et l'autocomplétion pour tout le système (voir [§ 10](#10-installation-et-déploiement)).

## 8. Interface graphique

Python, PySide6 (Qt 6.10, version de Kubuntu 26.04 LTS).

### 8.1 Écran par défaut

- Heure actuelle.
- État du binaire lecture (en marche ou non).
- Airplay des 12 dernières heures, en table.
- Sonore en cours mis en avant : heure de début, durée totale, heure de fin estimée, barre de progression.
- Juste à côté, le prochain sonore : heures de début et de fin estimées, durée, indicateur « sain ».
- Pour un stream, durée et heure de fin affichées comme inconnues.
- VU-mètre et bargraph de la sortie sonore (indisponibles avec la sortie ALSA).

### 8.2 Recherche et navigation

- Écrans de liste avec recherche pour les sonores, les banques et les événements, menant aux écrans de détail.
- Champ de recherche globale avec auto-suggestion, résultats dans l'ordre : événements, banques, sonores. Un écran de résultats dédié.
- Vue calendrier (jour, semaine) montrant à la fois l'airplay (ce qui a effectivement été diffusé) et les événements prévus.

### 8.3 Écran de détails d'un sonore

- Édition de tous les champs : artiste, titre, métadonnées musicales (année, etc.), crossfades, maximum de lectures, état (actif ou désactivé ; expiré, erroné et supprimé sont affichés, et l'interface peut les ramener à actif), masquage, période de diffusion. Tout champ saisi ici est marqué comme édité à la main et n'est plus modifié par l'indexeur.
- Pré-écoute avec un programme de lecture externe, sur un périphérique de sortie obligatoirement différent de celui du binaire lecture.
- Pour un stream : choix entre URL directe et marque-page, test du stream à la demande.
- Table des derniers passages, avec indication des incidents.

### 8.4 Écran de détails d'une banque

- Édition du nom interne.
- Masquage de l'artiste et du titre.
- Mode séquentiel ou aléatoire.
- Case « ne pas répéter » : la banque ne passe jamais deux fois de suite ([#63](https://github.com/dascritch/machincast/issues/63)).
- Liste des répertoires indexés : ajout et retrait.
- Liste des sonores liés, réordonnable par glisser-déposer en mode séquentiel. Ajout de sonores, y compris hors des répertoires de la banque.
- Retrait d'un sonore issu d'un répertoire de la banque : l'interface prévient qu'il sera réintégré à la prochaine indexation, et propose un lien ouvrant le navigateur de fichiers dans son répertoire. La suppression du fichier se fait hors de l'outil, parfois depuis un autre poste quand l'utilisateur n'a pas le droit d'écriture sur l'emplacement.

### 8.5 Écran de détails d'un événement

- Nom interne et nom public.
- Priorité : fil musical, émission, spécial.
- Masquage de l'artiste et du titre.
- Dates et heures de début et de fin, avec les règles du [§ 3.1](#evenements).
- Récurrence : jours de la semaine à cocher.
- Liste de lecture de banques et/ou de sonores, réordonnable par glisser-déposer, doublons autorisés.
- Avertissement quand une banque « ne pas répéter » occupe deux lignes contiguës, y compris la dernière et la première d'un événement qui boucle : le deuxième appel sera ignoré à la diffusion ([§ 4.4](#44-choix-dun-sonore-dans-une-banque), [#63](https://github.com/dascritch/machincast/issues/63)). L'avertissement n'empêche pas d'enregistrer.
- Refus d'un chevauchement avec un événement de même priorité.

### 8.6 Écran des incidents

Table des incidents du log : horaire, lien vers le sonore, lien vers la banque, lien vers l'événement quand il est renseigné.

### 8.7 Écran de simulation

L'utilisateur saisit une date et heure de début et de fin. L'interface lance le binaire lecture en mode simulation et présente la table des sonores qui seraient joués, exportable en .pls, .csv et .html.

### 8.8 Ajout d'un sonore

- Fichier : par sélecteur de fichiers ou glisser-déposer. Le fichier est référencé là où il se trouve, sans copie. Il peut être synchronisé depuis un autre ordinateur et changer de contenu sous le même nom (émission pré-enregistrée, rediffusion d'un direct). Il passe immédiatement par la vérification de l'indexeur.
- Stream : URL directe ou marque-page.

### 8.9 Suppression

- Un sonore présent dans un événement ou une banque n'est supprimé qu'après validation, en rappelant les événements et banques où il figure.
- Même règle pour la suppression d'une banque ou d'un événement.
- Les lignes `airplay` sont toujours conservées.

### 8.10 Fil musical garanti

Si aucun événement de priorité fil musical n'existe, l'interface en recrée un.

### 8.11 Menu

- Ajouter un sonore, une banque, un événement.
- Démarrer, arrêter, redémarrer le binaire lecture (via systemd et polkit, authentification par mot de passe ou empreinte digitale).
- Lancer une ré-indexation générale de toutes les banques.
- Choisir la sortie audio des pré-écoutes.

## 9. Configuration

- Format TOML, lu par `tomllib`.
- Le fichier `machincast.toml` se trouve dans le répertoire du projet et est ignoré par `.gitignore`. Le modèle versionné, documenté clé par clé, est `machincast.exemple.toml`.
- Sans option, chaque binaire lit `machincast.toml` dans le répertoire courant. L'option `--config <fichier>`, commune à tous les binaires et transmise par le wrapper, permet d'utiliser une autre configuration, notamment pour les tests.
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
| `audio.preecoute` | texte | oui | Périphérique de pré-écoute, différent de celui de l'antenne. |
| `sorties.csv` | chemin | oui | Airplay CSV (privé). |
| `sorties.pls` | chemin | oui | Playlist .pls (privé). |
| `sorties.html` | chemin | oui | Airplay HTML (public). |
| `metadonnees.masquer` | booléen | oui | Masquage par défaut de l'artiste et du titre. |
| `metadonnees.texte_public` | texte, 255 caractères au plus | oui | Texte public affiché à la place de l'artiste et du titre masqués, quand l'événement n'a pas de nom public. |

## 10. Installation et déploiement

- Cible : Ubuntu 26.04 LTS, et uniquement des versions LTS.
- Livraison : archives `.tar.gz` publiées en releases sur le dépôt git (sur le repository <https://github.com/dascritch/machincast>).
- Chaque archive contient un `install.sh` qui :
	- installe par apt les seules dépendances système (bibliothèques de compilation de PyGObject, GStreamer et ses plugins, PostgreSQL) ;
	- crée un environnement virtuel Python isolé, **sans** `--system-site-packages`, et y installe toutes les dépendances Python par pip (PySide6, PyGObject, psycopg, yoyo-migrations). Le projet suit ainsi l'évolution des paquets sans dépendre des versions de la distribution hôte ;
	- crée les bases de production et de test, et leurs rôles ;
	- installe l'unité systemd de `Machin_lecture`, `machincast.service`, et la règle polkit limitée au démarrage, à l'arrêt et au redémarrage de ce service ;
	- installe le wrapper `Machin` et son autocomplétion bash ;
	- ajoute les comptes de la radio au groupe `systemd-journal`, pour que tous puissent suivre les logs du service avec `Machin logs`.

## 11. Développements ultérieurs

| Sujet | Contenu | Raison du report |
| --- | --- | --- |
| Anomalie multi-banques | Signaler comme anomalie non bloquante un sonore présent dans plusieurs banques. | Non bloquant. |
| Normalisation du niveau sonore | Sur la sortie ou par fichier, par exemple mesure EBU R128 par l'indexeur via GStreamer, cible -23 LUFS (norme broadcast EBU) ou réglable. | Un compresseur de dynamique matériel est déjà branché avant les départs antenne. À voir après le déploiement. |
| Déclarations SACEM | ISRC, label, compositeur sur les sonores. | En attente de l'équipe juridique : la radio relève d'une catégorie spécifique avec un accord propre avec la SACEM. |
| Quotas | Propriétés « francophone » et « nouveauté », attribuables au niveau du sonore ou de la banque. La « nouveauté » aura une durée maximale par sonore, comptée à partir de son indexation. | La radio a des accords spécifiques sur les quotas. |
| Indexation planifiée | Cron ou timer systemd. | Selon les retours du terrain. |

## 12. Points à confirmer

Aucun point en attente.

### Points tranchés

- **Durée diffusée** : deux lignes d'airplay par passage, une au début et une à la fin, reliées par `passage_id` ; la ligne de fin porte la durée effectivement diffusée ([#48](https://github.com/dascritch/machincast/issues/48), voir [§ 3.1](#airplay)).
- **Affichage public masqué** : nom public de l'événement, sinon texte public par défaut de la configuration ([#49](https://github.com/dascritch/machincast/issues/49), voir [§ 4.8](#48-métadonnées-publiques-et-masquage)).
- **Droits sur les marques-pages** : modifiables par l'interface seule ; le binaire lecture les lit, l'indexeur n'y accède pas ([#50](https://github.com/dascritch/machincast/issues/50), voir [§ 3.2](#32-rôles-et-droits)).
- **Banque « ne pas répéter »** : un élément qui rappellerait une banque marquée « ne pas répéter » juste après elle est sauté, même d'un événement à l'autre ; s'il ne reste rien d'autre de jouable, l'événement se termine et l'événement inférieur prend le relais ([#63](https://github.com/dascritch/machincast/issues/63), voir [§ 4.4](#44-choix-dun-sonore-dans-une-banque)).
- **État d'un sonore** : le booléen `actif` devient un état `actif`, `desactive`, `expire`, `errone` ou `supprime` ; seul l'indexeur rétablit automatiquement un sonore, quand il l'avait lui-même déclaré `errone` ([#66](https://github.com/dascritch/machincast/issues/66), voir [§ 3.1](#sonores)).
- **Environnement virtuel** : isolé des paquets système, toutes les dépendances Python passent par pip ([#51](https://github.com/dascritch/machincast/issues/51), voir [§ 10](#10-installation-et-déploiement)).
