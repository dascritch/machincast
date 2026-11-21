# Sécurité du service et comptes applicatifs

[Guide d'administration](README.md) › Sécurité

*[English version](../../en/administration/securite.md)*

- [Principe : un compte par usage](#principe--un-compte-par-usage)
- [Les comptes du poste](#les-comptes-du-poste)
- [Les rôles dans la base](#les-rôles-dans-la-base)
- [Les sockets de Machin player](#les-sockets-de-machin-player)
- [Réservé au réseau de la radio, jamais à Internet](#réservé-au-réseau-de-la-radio-jamais-à-internet)
- [HTTPS seulement, même par une simple adresse IP](#https-seulement-même-par-une-simple-adresse-ip)
- [Le serveur intranet, exposé au réseau](#le-serveur-intranet-exposé-au-réseau)
- [Ce qui demande un administrateur](#ce-qui-demande-un-administrateur)
- [Les fichiers sonores](#les-fichiers-sonores)
- [Mode test, sans le service](#mode-test-sans-le-service)
- [Limites connues](#limites-connues)

## Principe : un compte par usage

MachinCast ne fait tourner aucun programme avec plus de droits qu'il ne lui en faut. Chaque programme a son compte système, et chaque compte n'endosse dans la base que le rôle de son programme. Une erreur ou une faille dans un programme ne donne donc que ce que ce programme peut déjà faire.

C'est ce que met en place `./install.sh --service`, sur un poste dédié à l'antenne ([#381](https://github.com/dascritch/machincast/issues/381), [#549](https://github.com/dascritch/machincast/issues/549)). Sans le service, sur un poste d'essai, tout tourne sous le compte qui lance les programmes : voir [Mode test](#mode-test-sans-le-service).

## Les comptes du poste

| Compte | Ce qu'il fait tourner | Ses groupes | Il lit | Il écrit |
| --- | --- | --- | --- | --- |
| **Le compte de MachinCast**, celui qui l'installe | L'interface, Machin indexer, les tâches régulières (purge, indexation, audit), la maintenance de la base | `machincast`, `systemd-journal` | Le dépôt, les banques, les logs du service | Ses fichiers de configuration, les sauvegardes ; il est propriétaire des bases de production et de test |
| **`machincast`**, le service de diffusion | Machin player, son PipeWire et son WirePlumber | `machincast` | Le dépôt, `/home/machincast`, les banques dont `Machin grant-read` lui a donné la lecture | `/run/machincast`, `/var/log/machincast`, `/var/lib/machincast` |
| **`machincast-intranet`**, le serveur intranet | Machin intranet | `machincast-intranet` seulement | Le dépôt et `machincast.toml`, la base au rôle `machincast_intranet`, sa socket de Machin player | `/var/lib/machincast-intranet`, son certificat, et rien d'autre |

- `machincast` et `machincast-intranet` sont des comptes système, sans mot de passe ni shell : personne ne s'y connecte.
- Le compte de MachinCast rejoint le groupe `machincast`, pour lire les logs du service, pré-écouter l'antenne et piloter Machin player depuis l'interface. Il rejoint aussi `systemd-journal`, pour lire le journal du service.
- **`machincast-intranet` n'est pas dans le groupe `machincast`.** Ce groupe donne le PipeWire du service, avec lequel on pourrait jouer du son à l'antenne sans passer par Machin player, ainsi que les logs, les rapports de crash et les sonores de `/home/machincast`. Le serveur intranet n'a besoin de rien de tout cela.
- `./install.sh --remove-service` retire les deux comptes système et leurs rôles dans la base.

## Les rôles dans la base

MachinCast ne se connecte à PostgreSQL que par la socket Unix, en authentification **peer** : le compte système est le rôle de connexion, sans mot de passe.

- Quatre **rôles de groupe**, sans connexion, un par programme : `machincast_player`, `machincast_indexer`, `machincast_interface` et `machincast_intranet`. Leurs droits, table par table, sont dans [Droits de chaque programme dans la base](configuration.md#droits-de-chaque-programme-dans-la-base).
- Chaque compte peut **endosser** les rôles de ses programmes, **sans en hériter les droits** (`WITH INHERIT FALSE, SET TRUE`). Connecté, il n'a accès à rien ; chaque programme endosse son rôle dès la connexion.

| Compte | Rôles qu'il peut endosser |
| --- | --- |
| Le compte de MachinCast | Les quatre, et il est propriétaire des bases |
| `machincast` | `machincast_player` seulement |
| `machincast-intranet` | `machincast_intranet` seulement |

**Pourquoi des comptes séparés, et pas seulement des rôles.** Endosser un rôle borne les requêtes d'un programme qui se comporte bien. Mais un programme détourné, qui exécuterait du code arbitraire, pourrait quitter ce rôle et retrouver tous les droits de son compte. Le compte de MachinCast, propriétaire des bases, ne fait donc jamais tourner le serveur exposé au réseau.

Le rôle `machincast_intranet` ne fait que lire, sauf les sessions de l'intranet, dont il ne modifie que les colonnes de la validation. Il ne peut pas accepter une connexion à la place du pupitre : seule l'interface le peut ([#547](https://github.com/dascritch/machincast/issues/547)).

## Les sockets de Machin player

Machin player publie son état et reçoit des demandes (couper l'antenne, interrompre, insérer, avancer l'événement suivant…) par deux sockets Unix, au même protocole.

| Socket | Répertoire, droits | Qui s'y connecte | Les demandes |
| --- | --- | --- | --- |
| `/run/machincast/lecture.sock`, la socket d'état | `2770`, groupe `machincast` ; la socket en `0660` | Machin player, l'interface du compte de MachinCast | Sans compte : une demande qui nomme un compte de l'API est ignorée |
| `/run/machincast-intranet/intranet.sock`, la socket de l'intranet | `2750`, au compte `machincast` et au groupe `machincast-intranet` ; la socket en `0660` | Le seul serveur intranet | Chaque demande nomme le compte de l'API qui la fait, obligatoire |

- Une socket ne sépare pas la lecture de l'écriture : qui peut s'y connecter peut aussi envoyer des demandes. C'est pourquoi le serveur intranet a sa socket à lui, plutôt qu'une place dans le groupe `machincast`.
- Machin player ne croit le compte d'une demande que sur la socket de l'intranet, où personne d'autre ne se connecte. Le serveur intranet le tient de la session de la personne connectée.
- Le log de la base dit, pour chaque action d'antenne demandée, d'où elle vient (`interface` ou `intranet`) et quel compte de l'API l'a faite. Le nom du compte reste, même une fois le compte supprimé.

## Réservé au réseau de la radio, jamais à Internet

**MachinCast ne doit jamais être joignable directement depuis Internet.** Le poste de diffusion fait l'antenne : il se protège comme une régie, pas comme un serveur web.

- **Aucune redirection de port** vers le poste depuis la box ou le routeur de la radio, ni vers le port de l'intranet (8443 par défaut), ni vers un autre.
- **Pour travailler à distance, passer par le VPN de la radio** : on rejoint d'abord son réseau, puis l'intranet, comme depuis un poste de la radio.
- **Limiter l'écoute au réseau de la radio** : Machin intranet écoute par défaut sur toutes les adresses du poste (`intranet.address`, `0.0.0.0`). Sur un poste qui a plusieurs cartes réseau, ou une adresse publique, `intranet.address` se règle sur l'adresse du réseau de la radio. Un pare-feu du poste peut aussi n'accepter le port de l'intranet que de ce réseau, par exemple `sudo ufw allow from 192.168.1.0/24 to any port 8443 proto tcp`.
- **PostgreSQL n'écoute pas pour MachinCast** : tous ses programmes s'y connectent par la socket Unix du poste. Rien n'oblige la base à écouter le réseau.

**Le nombre d'utilisateurs est limité, par conception.** L'intranet et son API servent l'équipe de la radio, pas un public :

- chaque compte se crée à la main, dans l'onglet **API** de l'interface, au pupitre ; il n'y a ni inscription, ni récupération de mot de passe ;
- chaque connexion s'accepte à la main, au pupitre, et un compte n'a que deux connexions en attente à la fois ;
- chaque action d'antenne demandée depuis l'intranet est consignée avec le compte qui l'a faite.

Il se gère donc comme les clés du studio : quelques comptes nominatifs, un par personne, jamais partagés, désactivés quand la personne quitte l'équipe. Pour un public, une page de la radio publie le titre en cours (la sortie HTML et `.pls` de Machin player) ; elle ne passe pas par l'intranet.

## HTTPS seulement, même par une simple adresse IP

**Toutes les communications avec Machin intranet sont chiffrées, en HTTPS, sans exception** ([#538](https://github.com/dascritch/machincast/issues/538)) : les pages, l'API, la connexion, ses cookies et ses jetons.

- **Aucun port en clair.** Machin intranet n'écoute qu'en TLS ; une requête en HTTP clair sur son port ne reçoit aucune réponse HTTP. Il n'y a pas non plus de redirection du clair vers le chiffré, qui laisserait passer la première requête en clair.
- **Même par une simple adresse IP.** Un réseau de radio n'a souvent ni nom de domaine interne ni autorité de certification. Sans certificat donné, Machin intranet en génère un, au nom du poste et de **chacune de ses adresses IP** : `https://10.0.0.12:8443/` est chiffré comme le serait un nom.
- **Le premier contact se vérifie.** Ce certificat est auto-signé : le navigateur avertit à la première connexion. On compare alors l'empreinte qu'il affiche à celle que donne le journal de Machin intranet au démarrage (`intranet sur https://10.0.0.12:8443/, certificat 9B:21:…`), puis on l'accepte. Un certificat de l'autorité de certification de la radio, donné par `intranet.certificate` et `intranet.key`, évite cet avertissement.
- **Le navigateur ne revient jamais en clair.** Chaque réponse le lui demande (`Strict-Transport-Security`), et le cookie de session ne part que sur une connexion chiffrée (`Secure`).
- **Pour un script qui appelle l'API**, on lui donne le certificat à croire (par exemple `curl --cacert cert.pem`), plutôt que de désactiver la vérification (`curl -k`), qui l'exposerait à une interception.

Pourquoi même sur le réseau de la radio : un Wi-Fi de locaux associatifs, un poste invité ou un appareil compromis suffisent à lire ce qui passe en clair. Le mot de passe, le code donné au pupitre et le jeton de session ne passent donc jamais en clair, quel que soit le réseau.

## Le serveur intranet, exposé au réseau

Machin intranet est le seul programme de MachinCast qui écoute le réseau. Il est **éteint par défaut**, et s'allume dans **Fichier → Paramètres du service…**, page **Intranet** ([Serveur intranet](commandes.md#serveur-intranet--machin-intranet)).

**Le transport** : HTTPS seulement ([ci-dessus](#https-seulement-même-par-une-simple-adresse-ip)). Chaque réponse interdit aussi au navigateur d'afficher la page dans un cadre, de charger une ressource d'ailleurs ou de garder la page en cache, et un formulaire envoyé d'un autre site est refusé : l'intranet se fie d'abord à ce que le navigateur dit de la provenance du formulaire, qu'une page ne peut pas falsifier ([#571](https://github.com/dascritch/machincast/issues/571)).

**Les connexions**

- Seuls les comptes de l'onglet **API** se connectent. Les mots de passe ont au moins 12 caractères, et la base n'en garde que l'empreinte scrypt salée.
- Un nom inconnu, un compte désactivé ou un mot de passe faux reçoivent la même réponse, dans le même temps.
- **Chaque connexion se décide au pupitre** : le bandeau orange de l'interface dit qui demande à se connecter, d'où et avec quel navigateur. **Accepter** montre un code à 6 chiffres, à donner à la personne ; **Refuser** ferme la porte. Avant l'acceptation, aucun code n'est même essayé ([#547](https://github.com/dascritch/machincast/issues/547)).
- Cinq codes faux d'une même adresse ou d'un même compte font attendre un quart d'heure, et un compte n'a que deux connexions en attente à la fois : un mot de passe volé ne suffit pas à forcer le code.
- Une session dure 12 heures par défaut. Changer le mot de passe d'un compte, ou le désactiver, met fin à toutes ses sessions, que sa réactivation ne fait pas revivre ([#548](https://github.com/dascritch/machincast/issues/548)).
- Le cookie de session n'est jamais envoyé en clair, ni lu par un script de la page, ni envoyé depuis un autre site ; la base n'en garde que l'empreinte.

**Le cloisonnement de l'unité** (`machincast-intranet.service`)

- Tout le système est en lecture seule, le dépôt et `machincast.toml` compris ; seul son répertoire d'état, `/var/lib/machincast-intranet`, s'écrit.
- Aucun répertoire personnel n'est visible, aucun périphérique, aucune capacité du noyau.
- Seules les sockets Unix, IP et netlink sont permises (netlink pour lire les adresses du poste), et seuls les appels système d'un service ordinaire, sans les appels privilégiés ; `capset` reste permis, que `ip` appelle pour lâcher ses capacités, même sans en avoir ([#556](https://github.com/dascritch/machincast/issues/556)) : il ne peut qu'en retirer.
- `systemd-analyze security machincast-intranet` mesure ce cloisonnement.

Ses messages vont dans le journal du système : `journalctl -u machincast-intranet`.

## Ce qui demande un administrateur

- **Installer ou retirer le service**, `./install.sh --service` ou `--remove-service`, demande `sudo` : comptes, unités, règles et fragments du système. install.sh se lance avec son propre compte, et ne demande `sudo` que pour ces étapes.
- **Démarrer, arrêter ou redémarrer** le service de diffusion ou le serveur intranet depuis l'interface : la règle polkit le permet au seul compte de MachinCast, avec le mot de passe d'un administrateur. Elle ne permet rien d'autre, ni sur une autre unité.
	Un compte administrateur (groupe `sudo`) donne son propre mot de passe, gardé quelques minutes ; un autre compte, celui d'un administrateur ([#558](https://github.com/dascritch/machincast/issues/558)).
	Sans fenêtre de mot de passe sur le bureau, par exemple dans une session `ssh -X`, il se demande dans une fenêtre de terminal qu'ouvre l'interface ; sans terminal, l'interface donne la commande `sudo systemctl …` à lancer.
- **Éteindre, redémarrer ou mettre en veille le poste** demande le mot de passe d'un administrateur, à tout compte ; les touches d'alimentation, le capot et Ctrl+Alt+Suppr en console sont ignorés ([#448](https://github.com/dascritch/machincast/issues/448)).

## Les fichiers sonores

- **MachinCast n'écrit, ne renomme, ne déplace, ne remplace ni ne supprime jamais un fichier sonore**, ni un répertoire de banque : supprimer un sonore ou une banque ne retire que son entrée en base ([#96](https://github.com/dascritch/machincast/issues/96)). Voir [Les fichiers sonores ne sont jamais modifiés](configuration.md#les-fichiers-sonores-ne-sont-jamais-modifiés).
- La seule exception est le déplacement des sonores hors d'un répertoire personnel, accepté explicitement à `./install.sh --service`.
- `Machin grant-read` donne au seul compte `machincast` la lecture des banques, par des ACL, sans changer le propriétaire ni les droits du groupe. Il refuse de toucher aux droits d'un répertoire personnel ou d'une arborescence du système (`/etc`, `/usr`, `/media`, `/mnt`…) ([#381](https://github.com/dascritch/machincast/issues/381)).
- Le serveur intranet ne lit aucun fichier sonore : son API ne donne que ce qui est en base.

## Mode test, sans le service

Sans `./install.sh --service`, sur un poste d'essai, tous les programmes tournent sous le compte qui les lance. La page **Intranet** des paramètres le rappelle.

| | Avec le service | En mode test |
| --- | --- | --- |
| Machin player | Sous `machincast`, avec son PipeWire | Sous ton compte, dans un terminal |
| Machin intranet | Sous `machincast-intranet`, unité cloisonnée | Sous ton compte, dans un terminal, sans cloisonnement |
| Rôles dans la base | Un par compte | Ton compte endosse chacun d'eux, mais il est aussi propriétaire des bases |
| Sockets de Machin player | Dans `/run/machincast` et `/run/machincast-intranet`, à leurs groupes | Dans `$XDG_RUNTIME_DIR/machincast`, privées à ton compte |
| Messages | Journal du système, et `/var/log/machincast` pour Machin player | Le terminal, et `/var/log/machincast` si ton compte peut y écrire |

Le protocole des sockets est le même : le compte de l'API reste obligatoire sur la socket de l'intranet, et le log dit d'où vient chaque action. Le mode test sert à essayer MachinCast et l'intranet, **pas à ouvrir le poste au réseau de la radio**.

## Limites connues

- Le certificat auto-signé se refait quand une adresse du poste change, en DHCP : chaque navigateur doit alors l'accepter de nouveau, en comparant son empreinte. Un certificat donné par l'autorité de certification de la radio (`intranet.certificate` et `intranet.key`) l'évite.
- Les constats de la relecture de sécurité qui restent à corriger sont suivis dans [#546](https://github.com/dascritch/machincast/issues/546).
