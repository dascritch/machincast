# Configuration et droits

[Guide d'administration](README.md) › Configuration et droits

- [Configuration](#configuration)
- [Les fichiers sonores ne sont jamais modifiés](#les-fichiers-sonores-ne-sont-jamais-modifiés)
- [Sorties de la diffusion](#sorties-de-la-diffusion)
- [Réglages de l'interface, par compte](#réglages-de-linterface-par-compte)
- [Durée de péremption](#durée-de-péremption)
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

Pour la même raison, une sortie ne peut pas être placée sur un fichier sonore. La configuration refuse un chemin de `outputs.csv`, `outputs.pls`, `outputs.html` ou `player.state_socket` qui se termine par l'extension d'un fichier sonore (`.mp3`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.wav`, `.aiff`, `.aif`, en majuscules comme en minuscules), avec le code de sortie 2 :

```text
2026-10-15T08:15:00+02:00 configuration invalide : /home/xavier/machincast/machincast.toml : clé outputs.csv : « musique/airplay.mp3 » porte l'extension d'un fichier sonore, et MachinCast n'écrit jamais dans un fichier sonore
```

Si une sortie devait malgré tout tomber sur un tel chemin, elle n'est pas écrite : elle est signalée dans le log par l'alerte `sortie inaccessible`, qui mentionne `fichier sonore protégé`, et la diffusion continue. De même, la socket d'état n'est alors pas ouverte : l'alerte `socket d'état indisponible` est notée, et la diffusion continue sans elle. Les fichiers d'une simulation finissent toujours par `.csv`, `.pls` ou `.html` : quel que soit leur nom, ils ne remplacent jamais un fichier sonore.

## Sorties de la diffusion

`Machin player` publie ce qu'il diffuse sur plusieurs sorties ([#19](https://github.com/dascritch/machincast/issues/19)), aux chemins de la section `[outputs]` de la configuration, compris depuis le répertoire du fichier de configuration (par défaut, le dossier `sorties` du répertoire de MachinCast, créé au besoin) :

| Sortie | Pour qui | Contenu |
| --- | --- | --- |
| Sortie standard | équipe | Une ligne `à l'antenne : artiste – titre (événement)` à chaque passage, et une ligne à chaque début ou fin d'événement ou de séquence, comme dans le log : `début d'événement : « Journal », émission, de 20:00 à 20:30` ([#153](https://github.com/dascritch/machincast/issues/153)). |
| Sortie d'erreur | équipe | Les alertes et incidents du log, et les erreurs du programme. |
| CSV (`outputs.csv`) | équipe | Un fichier par jour, nommé avec sa date : `airplay.csv` donne `airplay-2026-10-15.csv`. Une ligne par passage terminé : début, fin, durée, artiste, titre, emplacement, événement, séquence, banque, sans incident (`oui` ou `non`). Séparateur `;`, s'ouvre directement dans LibreOffice ou Excel. Jamais réécrit. |
| Playlist `.pls` (`outputs.pls`) | équipe | Les 100 derniers fichiers joués, streams compris, du plus ancien au plus récent : pour réécouter ce qui est passé. |
| Page HTML (`outputs.html`) | public | Le sonore à l'antenne et les 20 précédents, avec l'heure. Page statique, à publier sur le site de la radio ; elle se recharge toute seule toutes les 30 secondes et ne montre jamais l'emplacement d'un fichier. |

**Masquage de l'artiste et du titre.** Sur la page publique seulement, l'artiste et le titre d'un passage peuvent être masqués. Le choix se fait à cinq niveaux : l'événement, puis la séquence qui a fait jouer le sonore ([#99](https://github.com/dascritch/machincast/issues/99)), puis la banque qui l'a fourni, puis le sonore, puis `metadata.hide` dans la configuration. C'est le premier niveau renseigné qui décide : un événement qui dit « afficher » l'emporte sur un sonore qui dit « masquer ». Masqués, l'artiste et le titre laissent la place au premier nom public renseigné, dans le même ordre : celui de l'événement, puis de la séquence, puis de la banque ; s'il n'y en a aucun, à `metadata.public_text`. Les autres sorties disent toujours tout.

Une sortie impossible à écrire (dossier sans droit d'écriture, disque plein) est signalée une fois dans le log par l'alerte `sortie inaccessible`, avec le chemin et l'erreur. La diffusion continue.

## Réglages de l'interface, par compte

L'interface garde, pour chaque compte, la disposition des colonnes de chacun de ses tableaux : leur ordre, les colonnes cachées et les largeurs choisies ([#207](https://github.com/dascritch/machincast/issues/207), [Colonnes des tableaux](../utilisateur/listes.md#colonnes-des-tableaux)). Ce n'est pas un réglage du poste : il n'est pas dans `machincast.toml`, mais dans `~/.config/machincast/vues.ini` (ou `$XDG_CONFIG_HOME/machincast/vues.ini`), une section par tableau, comme `[liste-sonores]` ou `[fiche-banque-sonores]`. Supprimer ce fichier rend à tous les tableaux du compte leur disposition d'origine ; « Rétablir les colonnes », dans l'interface, le fait pour un seul. Une disposition gardée pour d'autres colonnes, par une version précédente de MachinCast, est oubliée.

## Fichiers créés par MachinCast

MachinCast tient la liste des fichiers qu'il a créés ([#652](https://github.com/dascritch/machincast/issues/652)) : `fichiers-machincast.txt`, à côté du fichier de configuration, un chemin complet par ligne, dans l'ordre alphabétique. Ce sont **les seuls fichiers qu'il modifie, remplace ou efface**, et ceux à **sauvegarder pour reprendre l'activité** sur un autre poste, avec une sauvegarde de la base :

- la configuration et les réglages : `machincast.toml`, les réglages des vues de chaque compte (`vues.ini`), les unités, règles et fragments qu'installe `./install.sh --service` dans `/etc` et `/usr/share/polkit-1`, le raccourci de l'interface et son icône, les réglages des cartes son toujours éveillées ;
- les données : les sorties de `Machin player` (le CSV de chaque jour, la playlist `.pls`, la page HTML), les fichiers de `Machin player --simulation`, les rapports de l'audit complet, les exports de l'interface (airplay, tableaux, simulation), les sauvegardes de la base de `Machin backup-db` et `Machin maintenance-db`, le document « Votre installation », et **les certificats et clés de l'intranet**, ceux que désignent `intranet.certificate` et `intranet.key` comme ceux que génère `Machin intranet` (dans `/var/lib/machincast-intranet` avec le service, que la sauvegarde lit en administrateur).

N'y sont pas : les logs (`/var/log/machincast`), les fichiers d'exécution (sockets, PID, rapports de plantage, fichiers temporaires, fichiers de l'onglet Simulation), l'environnement virtuel et le dépôt.

**Un fichier qui existe hors de la liste n'est jamais touché**, même s'il porte le nom qu'attend MachinCast : une sortie posée sur un document de la radio, un export qui tomberait sur un fichier existant. L'écriture est refusée avec le message :

```text
/home/xavier/machincast/sorties/airplay.html : pas créé par MachinCast, il n'est pas dans /home/xavier/machincast/fichiers-machincast.txt : MachinCast n'y touche pas
```

Pour une sortie de `Machin player`, c'est l'alerte `sortie inaccessible`, et la diffusion continue ; pour un export de l'interface, la barre d'état le dit ; pour `install.sh`, l'installation s'arrête en nommant le fichier. Des réglages des vues hors de la liste restent tels quels : les tableaux se règlent alors le temps de la session, et le journal le dit une fois. Pour que MachinCast reprenne un tel fichier, le déplacer, ou ajouter son chemin complet à la liste.

À la mise à jour, `install.sh` ajoute à la liste les fichiers qu'une version d'avant la liste avait créés, s'ils existent, et les énumère : ceux que la configuration désigne, ceux qu'il installe. Avec le service de diffusion, la liste appartient au compte de MachinCast et au groupe `machincast`, en `0660` : le service y inscrit ses sorties. Le serveur intranet, sous son propre compte, ne peut que la lire : `./install.sh --service` y inscrit d'avance le certificat et la clé qu'il génère.

## Plugins

Un plugin ajoute une fonction à MachinCast ([#348](https://github.com/dascritch/machincast/issues/348)) : c'est un répertoire de `plugins/`, dans le répertoire de MachinCast.
Il s'active dans la section `[plugins]`, et ses réglages, s'il en a, vont dans sa propre section ([#585](https://github.com/dascritch/machincast/issues/585)) :

```toml
[plugins]
enabled = ["cartwall"]

[plugins.cartwall]
# Les réglages du plugin, que décrit son README.md.
```

Sans éditer le fichier, l'onglet « Plugins » des « Paramètres du service… » (menu « Fichier ») liste chaque plugin, avec son nom et sa version ; déplié, sa description et, s'il ne peut pas être activé, pourquoi, par exemple sa table qui manque tant que son `install.sh` n'a pas été lancé ; sa case l'active ou le désactive, dans `[plugins] enabled`, sans toucher aux réglages des plugins ([#587](https://github.com/dascritch/machincast/issues/587)).
Le menu « Plugins » de la fenêtre principale ouvre la fenêtre de chaque plugin activé : son nom, sa version, sa description et les réglages qu'il apporte.
L'activation vaut au démarrage de chaque programme : relancer la diffusion, l'indexation, l'interface et le serveur intranet.
Chaque programme ne charge que les plugins qui le concernent, et seulement s'ils sont activables : une version de MachinCast qui leur convient, les plugins qu'ils demandent, leurs bibliothèques, leurs programmes et leurs tables.
Un plugin écarté l'est dans le journal du programme (`Machin logs` pour la diffusion), avec ses raisons, par exemple `plugin « cartwall » pas chargé : le programme « ffmpeg » manque` ; le programme démarre quand même.
Un nom de plugin mal écrit, ou donné deux fois, refuse la configuration (code 2).

Les tables d'un plugin ne sont créées que par son `install.sh`, après une sauvegarde de la base ([#586](https://github.com/dascritch/machincast/issues/586)), toutes préfixées de son nom et de `__` (`cartwall__buttons`) : à la validation des « Paramètres du service… », chaque plugin qu'ils activent lance son `install.sh` ([#587](https://github.com/dascritch/machincast/issues/587)) ; la barre d'état dit la fin, ou l'échec et sa raison.
`./install.sh`, celui de MachinCast, relance aussi l'`install.sh` de chaque plugin activé, après la base et ses rôles, pour ses mises à jour ; `./install.sh --simulation` lui transmet `--simulation`.
À la main, `plugins/cartwall/install.sh` crée ses tables, après une sauvegarde de la base, `--simulation` dit ce qu'il ferait, `--remove` les retire, toujours après une sauvegarde ; désactiver un plugin ne retire pas ses tables.
Tant que ses tables ne sont pas créées, chaque programme l'écarte, et son journal dit comment l'installer.
Ni l'un ni l'autre ne touche aux tables de MachinCast ni aux fichiers sonores.
`Machin maintenance-db` ne touche pas aux tables des plugins.

## Durée de péremption

`database.retention` ([#268](https://github.com/dascritch/machincast/issues/268)) est la durée, en jours entiers, 1 au moins, après laquelle [`Machin purge`](commandes.md#purge-de-la-base--machin-purge) efface de la base les passages de l'airplay, les lignes du log, et les éléments supprimés ou dont le fichier a disparu. 60 jours par défaut ; un nombre décimal, un texte ou 0 sont refusés (code 2). L'interface la règle aussi, **Fichier → Préférences de l'interface…**, page **Base**, qui l'écrit dans la section `[database]`, et la fiche d'un élément supprimé donne le jour où il sera effacé.

```toml
[database]
retention = 90
```

## Droits de chaque programme dans la base

Chaque programme agit dans la base avec ses propres droits : le compte qui le lance n'a accès à rien par lui-même, et le programme endosse son rôle PostgreSQL dès la connexion. Un programme ne peut donc pas faire plus que ce qui suit, même lancé par un compte qui a les quatre rôles.

| Programme | Rôle PostgreSQL | Ce qu'il peut faire |
| --- | --- | --- |
| `Machin player` | `machincast_player` | Lire la programmation, séquences comprises ; passer un sonore à `expiré` ; ajouter des lignes à l'airplay et au log, sans jamais les modifier ni les supprimer. |
| `Machin indexer` | `machincast_indexer` | Lire les banques et leurs répertoires ; ajouter et mettre à jour des sonores, les ranger dans les banques, et en retirer ceux qui sortent de leurs durées ; noter la fin du parcours de chaque répertoire. Il ne supprime aucun sonore, et n'ajoute au log que ses démarrages et ses fins ([Démarrages et fins dans le log](commandes.md#démarrages-et-fins-dans-le-log)). |
| `Machin interface` | `machincast_interface` | Tout modifier dans les sonores, les banques, les séquences et les événements ; lire l'airplay et le log, sans les modifier ; gérer les comptes de l'intranet ([#537](https://github.com/dascritch/machincast/issues/537)), leur application d'authentification, et oublier leurs navigateurs connus ([#601](https://github.com/dascritch/machincast/issues/601)). |
| Serveur intranet | `machincast_intranet` | Lire les comptes de l'intranet, sans les modifier ([#537](https://github.com/dascritch/machincast/issues/537)) ; ouvrir, valider et fermer leurs sessions ([#539](https://github.com/dascritch/machincast/issues/539)) ; retenir leurs navigateurs connus, sans les oublier ([#601](https://github.com/dascritch/machincast/issues/601)) ; lire la programmation, l'airplay et le log pour l'API, sans rien en écrire ([#540](https://github.com/dascritch/machincast/issues/540)). |

`Machin maintenance-db`, `Machin backup-db`, `Machin restore-db` et `Machin purge` n'endossent aucun rôle : ils agissent en propriétaire de la base, ce qu'est le compte de MachinCast. Seule la purge efface des lignes de l'airplay et du log.

Le détail, table par table, est dans la [spécification, § 3.2](../spec.md#32-rôles-et-droits). Ajouter un autre compte est décrit dans [INSTALL.md](../../../INSTALL.fr.md#ajouter-un-autre-compte).

## Comptes de l'intranet

L'intranet et son API ([#524](https://github.com/dascritch/machincast/issues/524)) ne laissent entrer que les comptes créés dans l'onglet **API** de l'interface, qu'ouvre **Affichage → Ouvrir l'onglet API** ([#537](https://github.com/dascritch/machincast/issues/537)).
L'[aide de l'onglet](../utilisateur/aide/api.md) décrit chacun de ses éléments.

- **➕ Nouveau compte…** demande un nom, un mot de passe, sa confirmation et un rôle.
	Le nom se tape dans l'adresse de l'intranet, `https://nom@adresse` : lettres sans accent, chiffres, point, tiret et souligné.
	Le mot de passe a au moins 12 caractères.
- **Rôle** : `consulter` donne l'intranet et l'API en lecture ; `actions API` donne la même chose, et les actions que l'API proposera.
- **Changer le mot de passe…**, **Désactiver** (puis **Réactiver**) et **❌ Supprimer…** agissent sur le compte choisi.
	Un compte désactivé ou supprimé ne se connecte plus.
- Il n'y a pas de récupération de mot de passe : un mot de passe oublié se change ici.
- MachinCast ne garde jamais un mot de passe, seulement son empreinte scrypt salée : même la base ne permet pas de le retrouver.
- Les comptes ne servent qu'une fois le serveur intranet allumé ([#538](https://github.com/dascritch/machincast/issues/538)) : voir [Serveur intranet](commandes.md#serveur-intranet--machin-intranet).
