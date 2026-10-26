# Configuration et droits

[Guide d'administration](README.md) › Configuration et droits

- [Configuration](#configuration)
- [Les fichiers sonores ne sont jamais modifiés](#les-fichiers-sonores-ne-sont-jamais-modifiés)
- [Sorties de la diffusion](#sorties-de-la-diffusion)
- [Réglages de l'interface, par compte](#réglages-de-linterface-par-compte)
- [Droits de chaque programme dans la base](#droits-de-chaque-programme-dans-la-base)

## Configuration

Chaque programme lit sa configuration dans le fichier `machincast.toml` **du répertoire de MachinCast**, quel que soit le répertoire d'où il est lancé ([#76](https://github.com/dascritch/machincast/issues/76)). `Machin --help` affiche son chemin complet. Une autre configuration, placée elle aussi dans le répertoire de MachinCast, se désigne par `--config`.

Le modèle commenté est `machincast.exemple.toml`, et le [tableau des clés de la spécification](../spec.md#9-configuration) donne le type et le rôle de chacune. Toute clé inconnue est refusée, pour détecter les fautes de frappe : le programme s'arrête alors avec le code 2 et un message qui nomme le fichier et la clé, par exemple :

```text
2026-10-15T08:15:00+02:00 configuration invalide : /home/xavier/machincast/machincast.toml : clé audio.sortei inconnue
```

Les chemins relatifs du fichier (sorties CSV, HTML et .pls) se comprennent depuis le répertoire du fichier de configuration.

## Les fichiers sonores ne sont jamais modifiés

MachinCast ne fait que **lire** les fichiers sonores ([#96](https://github.com/dascritch/machincast/issues/96)). Aucun de ses programmes ne les supprime, ne les renomme, ne les déplace, ne les remplace ni n'y écrit, quoi qu'il arrive à leur entrée dans la base :

- un sonore passé à l'état `supprimé`, `désactivé`, `expiré` ou `erroné` garde son fichier tel quel ;
- un sonore dont l'emplacement, l'artiste ou le titre change garde son fichier tel quel ;
- un sonore supprimé de la base, depuis [sa fiche](../utilisateur/listes.md#supprimer-un-élément), garde son fichier : s'il est encore dans le répertoire d'une banque, la prochaine indexation l'enregistre de nouveau, comme un nouveau sonore à l'état `aperçu`, puis `actif` une fois vérifié.

Supprimer un fichier sonore du disque reste une décision humaine, prise hors de MachinCast.

Pour la même raison, une sortie ne peut pas être placée sur un fichier sonore. La configuration refuse un chemin de `sorties.csv`, `sorties.pls`, `sorties.html` ou `lecture.socket_etat` qui se termine par l'extension d'un fichier sonore (`.mp3`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.wav`, `.aiff`, `.aif`, en majuscules comme en minuscules), avec le code de sortie 2 :

```text
2026-10-15T08:15:00+02:00 configuration invalide : /home/xavier/machincast/machincast.toml : clé sorties.csv : « musique/airplay.mp3 » porte l'extension d'un fichier sonore, et MachinCast n'écrit jamais dans un fichier sonore
```

Si une sortie devait malgré tout tomber sur un tel chemin, elle n'est pas écrite : elle est signalée dans le log par l'alerte `sortie inaccessible`, qui mentionne `fichier sonore protégé`, et la diffusion continue. De même, la socket d'état n'est alors pas ouverte : l'alerte `socket d'état indisponible` est notée, et la diffusion continue sans elle. Les fichiers d'une simulation finissent toujours par `.csv`, `.pls` ou `.html` : quel que soit leur nom, ils ne remplacent jamais un fichier sonore.

## Sorties de la diffusion

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

## Réglages de l'interface, par compte

L'interface garde, pour chaque compte, la disposition des colonnes de chacun de ses tableaux : leur ordre, les colonnes cachées et les largeurs choisies ([#207](https://github.com/dascritch/machincast/issues/207), [Colonnes des tableaux](../utilisateur/listes.md#colonnes-des-tableaux)). Ce n'est pas un réglage du poste : il n'est pas dans `machincast.toml`, mais dans `~/.config/machincast/vues.ini` (ou `$XDG_CONFIG_HOME/machincast/vues.ini`), une section par tableau, comme `[liste-sonores]` ou `[fiche-banque-sonores]`. Supprimer ce fichier rend à tous les tableaux du compte leur disposition d'origine ; « Rétablir les colonnes », dans l'interface, le fait pour un seul. Une disposition gardée pour d'autres colonnes, par une version précédente de MachinCast, est oubliée.

## Droits de chaque programme dans la base

Chaque programme agit dans la base avec ses propres droits : le compte qui le lance n'a accès à rien par lui-même, et le programme endosse son rôle PostgreSQL dès la connexion. Un programme ne peut donc pas faire plus que ce qui suit, même lancé par un compte qui a les trois rôles.

| Programme | Rôle PostgreSQL | Ce qu'il peut faire |
| --- | --- | --- |
| `Machin lecture` | `machincast_lecture` | Lire la programmation, séquences comprises ; passer un sonore à `expiré` ; ajouter des lignes à l'airplay et au log, sans jamais les modifier ni les supprimer. |
| `Machin indexation` | `machincast_indexation` | Lire les banques et leurs répertoires ; ajouter et mettre à jour des sonores, et les ranger dans les banques. Il ne supprime rien et n'écrit pas dans le log. |
| `Machin interface` | `machincast_interface` | Tout modifier dans les sonores, les banques, les séquences et les événements ; lire l'airplay et le log, sans les modifier. |

Le détail, table par table, est dans la [spécification, § 3.2](../spec.md#32-rôles-et-droits). Ajouter un autre compte est décrit dans [INSTALL.md](../../INSTALL.md#ajouter-un-autre-compte).
