# Installer MachinCast

Ce document décrit l'installation de MachinCast sur un poste de diffusion, sa vérification, sa mise à jour et l'ajout d'autres comptes. Il s'adresse à l'administrateur du poste : il ne demande pas de connaître le code. L'usage des programmes une fois installés est décrit dans le [guide d'administration](doc/administration/README.md), et celui de l'interface graphique dans le [guide de l'antenne](doc/utilisateur/README.md). Le poste de développement est décrit dans le [guide du développement](doc/developpement/poste.md).

Le script `install.sh` fait tout le travail. La section [Installer à la main](#installer-à-la-main) détaille chacune de ses étapes, pour qui veut les faire soi-même ou comprendre ce qu'il fait.

> **État du projet** : MachinCast est en cours de développement. L'indexation vérifie les sonores, et `Machin lecture` diffuse la grille, depuis un terminal ou comme service, et l'interface graphique (`Machin interface`) n'a pas encore tous ses écrans. La section [Ce qui n'existe pas encore](#ce-qui-nexiste-pas-encore) donne le ticket de chaque manque.

## Sommaire

- [En bref](#en-bref)
- [Prérequis](#prérequis)
- [Récupérer MachinCast](#récupérer-machincast)
- [Installer avec install.sh](#installer-avec-installsh)
- [Adapter la configuration](#adapter-la-configuration)
- [Vérifier l'installation](#vérifier-linstallation)
- [Service de diffusion](#service-de-diffusion)
- [Ajouter un autre compte](#ajouter-un-autre-compte)
- [Mettre à jour](#mettre-à-jour)
- [Installer à la main](#installer-à-la-main)
- [Désinstaller](#désinstaller)
- [En cas de problème](#en-cas-de-problème)
- [Ce qui n'existe pas encore](#ce-qui-nexiste-pas-encore)

## En bref

```bash
git clone https://github.com/dascritch/machincast.git ~/machincast
cd ~/machincast
./install.sh --simulation   # affiche ce qui sera fait, sans rien changer
./install.sh
```

Ensuite : adapter `machincast.toml` ([voir plus bas](#adapter-la-configuration)), puis redémarrer le poste pour lire le journal du service.

## Prérequis

- **Ubuntu 26.04 LTS**. Les autres versions LTS (24.04…) sont acceptées, avec un avertissement ; les versions qui ne sont pas LTS sont refusées. MachinCast est vérifié avec la version de GStreamer d'Ubuntu 26.04, la 1.28 : avec une version plus ancienne, comme la 1.24 d'Ubuntu 24.04, l'installation avertit, et rien n'est garanti ([#284](https://github.com/dascritch/machincast/issues/284)).
- **Le compte qui utilisera MachinCast, avec le droit `sudo`**. L'installation est mono-utilisateur : un seul compte Unix utilise MachinCast, celui qui l'installe. Le script se lance avec ce compte, jamais avec `sudo` : il demande le mot de passe pour les seules étapes qui l'exigent.
- **Un accès à Internet**, pour apt et pip.
- **PostgreSQL 16 ou plus récent**, installé par le script s'il manque. Ubuntu 26.04 fournit une version qui convient.

Paquets installés par apt : uniquement ce que pip ne peut pas fournir. Toutes les bibliothèques Python, elles, viennent de pip, dans un environnement isolé ([#51](https://github.com/dascritch/machincast/issues/51)).

| Paquet | Rôle |
| --- | --- |
| `python3-venv` | Création de l'environnement virtuel Python. |
| `python3-dev` | En-têtes Python, pour compiler PyGObject lors du `pip install`. |
| `build-essential` | Compilateur C, pour PyGObject. |
| `pkg-config` | Recherche des bibliothèques lors de la compilation. |
| `libgirepository-2.0-dev` | Introspection GObject, dont PyGObject a besoin pour accéder à GStreamer. |
| `libcairo2-dev` | Cairo, dépendance de compilation de PyGObject. |
| `gir1.2-gstreamer-1.0` | Description de GStreamer pour PyGObject. |
| `gstreamer1.0-plugins-base` | Décodage Ogg Vorbis, conversion et rééchantillonnage audio. |
| `gstreamer1.0-plugins-good` | Décodage MP3, FLAC et WAV ; découpage des fichiers AAC bruts (`.aac`) ; lecture des streams HTTP et HTTPS. |
| `gstreamer1.0-plugins-bad` | Décodage AAC (fichiers `.m4a` et `.aac`). |
| `gstreamer1.0-alsa` | Sortie audio `alsa`. |
| `gstreamer1.0-pulseaudio` | Sortie audio `pulseaudio`. |
| `gstreamer1.0-pipewire` | Sortie audio `pipewire`. |
| `pipewire-bin` | `pw-link`, qui relie l'antenne à la pré-écoute pour l'écouter sous PipeWire ([#24](https://github.com/dascritch/machincast/issues/24)). Déjà présent avec PipeWire sur une Ubuntu de bureau. |
| `libmagic1t64` | Reconnaissance du type réel des fichiers sonores, sans se fier à leur extension ([#121](https://github.com/dascritch/machincast/issues/121)). |
| `postgresql` | Serveur de base de données. |
| `bash-completion` | Chargement de l'autocomplétion de `Machin`. Déjà présent sur une Ubuntu standard, absent d'une installation minimale. |

## Récupérer MachinCast

MachinCast s'installe **en place** : le répertoire où il se trouve devient le répertoire d'installation, et `/opt/machincast` pointe vers lui. Il ne faut donc plus le déplacer après l'installation.

L'installation est mono-utilisateur : MachinCast se place dans le répertoire personnel du compte qui l'utilise, par exemple `~/machincast`.

```bash
git clone https://github.com/dascritch/machincast.git ~/machincast
cd ~/machincast
```

Les archives `.tar.gz` publiées en releases sur GitHub ne sont pas encore disponibles ([#41](https://github.com/dascritch/machincast/issues/41)). Une fois publiées, elles s'utiliseront de la même façon : décompresser l'archive dans le répertoire choisi, puis lancer `./install.sh` depuis ce répertoire.

## Installer avec install.sh

Depuis le répertoire de MachinCast, avec son propre compte :

```bash
./install.sh --simulation   # affiche les commandes sans rien exécuter
./install.sh                # installe
./install.sh --dev          # installe, avec les outils du poste de développement
./install.sh --service      # installe, avec le service de diffusion : ordinateur dédié à l'antenne seulement
./install.sh --bureau       # installe, et dépose le raccourci de l'interface sur le bureau sans le demander
./install.sh --sans-bureau  # installe, sans raccourci sur le bureau ni question
./install.sh --arreter-les-programmes  # arrête sans le demander les programmes de MachinCast en cours
./install.sh --laisser-les-programmes  # les laisse tourner, sans le demander
./install.sh --help         # aide
```

`--dev` se combine avec `--simulation`. Voir [Poste de développement](doc/developpement/poste.md).

**Relançable** : chaque étape déjà faite est laissée telle quelle. En cas d'échec, corriger ce que le message indique, puis relancer le script. À la relance, PostgreSQL signale par des lignes `NOTICE:  role … has already been granted membership …` que le compte était déjà autorisé : ce n'est pas une erreur.

**Ce qu'il demande** : le mot de passe `sudo`, pour apt, pour les commandes passées en tant qu'utilisateur `postgres`, pour l'ajout au groupe `systemd-journal`, pour les liens dans `/opt`, `/usr/local/bin` et `/usr/share`, et, avec `--service`, pour la session du compte, l'unité systemd et la règle polkit. Deux questions au plus. Si des programmes de MachinCast tournent : « Les arrêter pendant l'installation, puis les relancer ? [o/N] » ; Entrée répond non. `--arreter-les-programmes` et `--laisser-les-programmes` y répondent d'avance ; sans terminal, elle n'est pas posée, et ils continuent. À la première installation : « Déposer aussi le raccourci de MachinCast sur le bureau ? [O/n] » ; Entrée répond oui. `--bureau` et `--sans-bureau` y répondent d'avance ; sans terminal, par exemple dans un script, elle n'est pas posée, et le raccourci ne va pas sur le bureau.

**Ce qu'il fait**, dans l'ordre :

| Étape | Ce qui se passe | Ce qui est modifié sur le poste |
| --- | --- | --- |
| Système | Vérifie qu'il est lancé sans `sudo`, sur une Ubuntu LTS. | Rien. |
| Programmes de MachinCast en cours | Liste ceux qui tournent, sous tous les comptes du poste : `Machin lecture` (le service de diffusion, une diffusion d'essai, une simulation), `Machin indexation`, `Machin interface`. Une mise à jour, et ses migrations de la base, ne doit pas se faire sous eux : selon la réponse à la question, il les arrête, le service par `systemctl stop`, les autres par un signal, avec `sudo` pour ceux d'un autre compte ([#254](https://github.com/dascritch/machincast/issues/254)). **Arrêtée, la diffusion se tait jusqu'à la fin de l'installation** ; l'interface perd les fiches qui n'étaient pas enregistrées. | Rien, ou programmes arrêtés. |
| Paquets système | Installe les paquets du [tableau des prérequis](#prérequis). | Paquets apt. |
| Environnement virtuel Python | Crée `.venv` dans le répertoire de MachinCast, sans accès aux paquets Python du système, et y installe MachinCast et ses dépendances. | `.venv` dans le répertoire de MachinCast. |
| Configuration | Copie `machincast.exemple.toml` en `machincast.toml` s'il n'existe pas. Un `machincast.toml` existant n'est jamais modifié. | `machincast.toml`. |
| PostgreSQL | En tant qu'utilisateur `postgres` : crée le rôle PostgreSQL du compte, **sans aucun droit particulier** sur le serveur ; crée les bases de production et de test nommées dans `machincast.toml`, dont le compte devient propriétaire ; crée les trois rôles de groupe de MachinCast. Puis, avec le compte : applique le schéma aux deux bases. | Serveur PostgreSQL. |
| Rôles | En tant qu'utilisateur `postgres` : autorise le compte à endosser les trois rôles de MachinCast, sans en hériter les droits. | Serveur PostgreSQL. |
| Journal système | Ajoute le compte au groupe `systemd-journal`, pour lire le journal du service. Effectif après le redémarrage du poste. | Groupes du compte. |
| Liens | `/opt/machincast` vers le répertoire de MachinCast ; `/usr/local/bin/Machin` vers le wrapper ; l'autocomplétion bash dans `/usr/share/bash-completion/completions/Machin`. | Trois liens symboliques. |
| Version et greffons GStreamer, sortie audio | Avertit si GStreamer ou ses greffons sont plus anciens que la version 1.28, avec laquelle MachinCast est vérifié, en nommant le paquet à mettre à jour ([#284](https://github.com/dascritch/machincast/issues/284)). Vérifie que GStreamer sait décoder MP3, M4A, AAC, Ogg, FLAC et WAV, lire les streams HTTP et HTTPS, et créer la sortie audio de `machincast.toml`, sans jouer aucun son. | Rien. |
| Raccourci de l'interface | Installe le raccourci **MachinCast**, avec son icône, dans le menu des applications du compte, rubrique Multimédia. Selon la réponse à la question, ou `--bureau`, le dépose aussi sur le bureau du compte (le dossier que donne `xdg-user-dir DESKTOP`, « Bureau » en français), exécutable pour que Plasma le lance sans avertissement. Un raccourci déjà sur le bureau est mis à jour sans question ; `--sans-bureau` le laisse tel quel ([#62](https://github.com/dascritch/machincast/issues/62)). | `~/.local/share/applications/machincast.desktop`, et `machincast.desktop` sur le bureau. |

**Relance des programmes de MachinCast** : avant d'afficher `Installation terminée`, et même après un échec, il relance ceux qu'il a arrêtés : le service de diffusion (sauf avec `--retirer-service`), et, pour son compte, la diffusion d'essai dans un terminal et l'interface dans la session graphique, avec leurs arguments. Il dit ce qui reste à rouvrir : une indexation interrompue, la simulation de l'interface, et les programmes des autres comptes, que leur compte relance.

À la fin, il affiche `Installation terminée`. Le service de diffusion n'est installé que sur demande : voir [Service de diffusion](#service-de-diffusion).

**Rôles PostgreSQL.** Chaque programme de MachinCast agit avec ses propres droits : `machincast_lecture` pour la diffusion, `machincast_indexation` pour l'indexation, `machincast_interface` pour l'interface graphique. Un compte de la radio se connecte avec son propre rôle PostgreSQL, qui ne donne accès à rien en lui-même : chaque programme endosse son rôle dès la connexion. Le détail est dans la [spécification, § 3.2](doc/spec.md#32-rôles-et-droits).

## Adapter la configuration

La configuration est le fichier `machincast.toml`, dans le répertoire de MachinCast. Il n'est jamais versionné par git. Le modèle `machincast.exemple.toml` commente chaque clé, et le [tableau des clés de la spécification](doc/spec.md#9-configuration) en donne le type et le rôle.

À adapter au moins :

- `audio.sortie` : `pipewire` (valeur du modèle), `pulseaudio`, `alsa`, ou `factice` pour un essai sans aucun son ; avec `alsa`, le VU-mètre de l'interface est indisponible, faute de port de monitoring ([#24](https://github.com/dascritch/machincast/issues/24)) ;
- `audio.peripherique` : le périphérique de l'antenne, **obligatoire pour diffuser** (sauf avec `factice`) : sans lui, `Machin lecture` refuse de démarrer. Il peut aussi se choisir dans l'interface, **Fichier → Préférences…**, page **Audio**, qui l'écrit dans `machincast.toml`. `.venv/bin/python -m machincast.installation peripheriques` liste les périphériques de la sortie configurée, avec leur identifiant à recopier ; s'il n'en trouve aucun, il dit tout ce que voit GStreamer, et `gst-device-monitor-1.0 Audio/Sink` en donne le détail ;
- `audio.preecoute` : le périphérique de pré-écoute de l'interface, différent de celui de l'antenne ; il peut aussi se choisir ensuite dans la fenêtre de pré-écoute de l'interface ;
- `metadonnees.texte_public` : le nom affiché sur la page publique à la place d'un titre masqué ;
- `lecture.socket_etat` : facultatif, la socket d'état lue par l'interface ; par défaut dans le répertoire d'exécution du compte (`$XDG_RUNTIME_DIR/machincast/lecture.sock`) ;
- `[sorties]` : les chemins de l'airplay CSV (un fichier par jour), de la playlist et de la page HTML publique, dans le dossier `sorties` du répertoire de MachinCast par défaut. Pour publier la page sur le site de la radio, la copier ou la servir depuis ce chemin.

Les noms des bases (`base.production` et `base.test`) se choisissent **avant** de lancer `install.sh`, qui crée les bases sous ces noms. La base de test doit porter un autre nom que la base de production : MachinCast refuse sinon la configuration.

Toute clé inconnue est refusée, pour détecter les fautes de frappe. Après une modification, relancer `./install.sh` vérifie la configuration et la sortie audio.

Sans l'option `--config`, les programmes lisent toujours le `machincast.toml` du répertoire de MachinCast, quel que soit le répertoire d'où ils sont lancés ([#76](https://github.com/dascritch/machincast/issues/76)). `Machin --help` indique son chemin complet. Une autre configuration, placée elle aussi dans le répertoire de MachinCast, se désigne par `--config` :

```bash
Machin indexation                                         # lit ~/machincast/machincast.toml
Machin indexation --config ~/machincast/essai.toml        # lit essai.toml
```

## Vérifier l'installation

Redémarrer d'abord le poste, pour que le groupe `systemd-journal` soit pris en compte. Sous Ubuntu Desktop, se déconnecter puis se reconnecter ne suffit pas toujours : les nouveaux terminaux peuvent garder les anciens groupes de la session. Puis :

```bash
id -nG                                     # doit citer systemd-journal
Machin --help                              # aide du wrapper, liste des programmes
Machin indexation --help                   # aide de l'indexation
Machin indexation                          # indexation rapide
```

`Machin indexation` affiche un bilan, par exemple `2026-10-15T08:15:00+02:00 indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu`, et se termine avec le code 0. Sur un poste neuf, aucune banque n'existe encore, donc aucun répertoire à parcourir : les banques se créent dans l'interface, à venir ([#31](https://github.com/dascritch/machincast/issues/31)).

**Première indexation.** L'indexation rapide, par défaut, ne décode que les sonores nouvellement découverts (état « aperçu ») et vérifie seulement la présence des autres fichiers. L'audit complet décode tous les sonores, ce qui peut être long sur une grande discothèque :

```bash
Machin indexation                   # rapide
Machin indexation --audit-complet   # complet, à lancer une fois après la première indexation
```

Les anomalies (fichier endommagé, illisible ou introuvable) s'affichent sur la sortie d'erreur avec le chemin du fichier ; elles ne bloquent pas l'indexation.

**Journal du service.** `Machin logs` suit le journal du service de diffusion. Tant que le service n'est pas installé ([#22](https://github.com/dascritch/machincast/issues/22)), il n'affiche rien, ce qui est normal.

## Service de diffusion

**Pour un ordinateur dédié à l'antenne seulement** ([#22](https://github.com/dascritch/machincast/issues/22)). Sans service, `Machin lecture` se lance à la main, et s'arrête avec son terminal : c'est ce qui convient pour essayer MachinCast. Avec le service, `machincast.service`, la diffusion démarre avec le poste, sans connexion de personne, et redémarre seule après un plantage.

```bash
./install.sh --service            # installe le service, ou le met à jour
./install.sh --retirer-service    # le retire
```

`--service` se combine avec `--simulation`. **Ce qu'il fait**, après les étapes habituelles :

| Étape | Ce qui se passe | Ce qui est modifié sur le poste |
| --- | --- | --- |
| Session du compte | Garde active, dès le démarrage du poste, la session du compte qui installe (`loginctl enable-linger`) : c'est là que tournent PipeWire ou PulseAudio, et la socket d'état que lit l'interface. | Session du compte. |
| Unité systemd | Installe `/etc/systemd/system/machincast.service`, rédigé par `python -m machincast.installation unite`, puis recharge systemd. | Une unité systemd. |
| Règle polkit | Installe `/etc/polkit-1/rules.d/50-machincast.rules`, rédigée par `python -m machincast.installation regle`. | Une règle polkit. |
| Activation | Active le service au démarrage du poste, et le démarre ; une unité modifiée redémarre le service. | Service activé. |
| Purge quotidienne | Installe `/etc/systemd/system/machincast-purge.service` et son minuteur `machincast-purge.timer`, rédigés par `python -m machincast.installation unite-purge` et `minuteur-purge`, et active le minuteur ([#268](https://github.com/dascritch/machincast/issues/268)). | Une unité et un minuteur systemd. |

**Le service** tourne sous le compte qui a installé MachinCast, pas sous un compte système : il en a le rôle PostgreSQL, les fichiers et la session audio. Il lance `bin/Machin lecture`, avec le `machincast.toml` du répertoire de MachinCast, et le relance 5 secondes après un plantage. Son arrêt envoie `SIGTERM`, qui termine proprement le passage en cours. Ses messages vont dans le journal du système : `Machin logs` les suit.

**La purge quotidienne** lance `bin/Machin purge` chaque jour à midi, sous le même compte : elle efface de la base ce qui dépasse la durée de péremption, `base.peremption`, 60 jours par défaut, et jamais un fichier ([Purge de la base](doc/administration/commandes.md#purge-de-la-base--machin-purge)). Une purge manquée, poste éteint à midi, se fait à son démarrage. `systemctl list-timers machincast-purge.timer` donne la prochaine ; `journalctl --unit=machincast-purge.service`, ce que les précédentes ont effacé.

**La règle polkit** n'autorise que trois actions sur `machincast.service`, au seul compte de MachinCast : le démarrer, l'arrêter et le redémarrer, avec le mot de passe, ou l'empreinte, d'un administrateur du poste. Elle n'autorise rien d'autre, ni sur une autre unité. Jamais de `sudo` pour piloter la diffusion :

```bash
systemctl start machincast.service
systemctl stop machincast.service
systemctl restart machincast.service
systemctl status machincast.service
```

**Depuis l'interface**, le menu **Diffusion** fait la même chose, avec la même authentification ([guide de l'antenne](doc/utilisateur/antenne.md#piloter-la-diffusion), [#25](https://github.com/dascritch/machincast/issues/25)). Tant que le service n'est pas installé, la barre d'état de l'interface affiche `Installation non définitive : diffusion sans service`, et le menu **Diffusion** pilote une diffusion d'essai : `Machin lecture` dans une fenêtre de terminal, que l'interface sait arrêter et redémarrer.

**Avant d'installer le service**, arrêter tout `Machin lecture` lancé à la main : un second Machin lecture est refusé, tant que la socket d'état est occupée, et le service redémarrerait sans fin.

À la main, sans `install.sh` :

```bash
sudo loginctl enable-linger "$(id -un)"
.venv/bin/python -m machincast.installation unite --config machincast.toml > machincast.service
.venv/bin/python -m machincast.installation regle --config machincast.toml > 50-machincast.rules
.venv/bin/python -m machincast.installation unite-purge --config machincast.toml > machincast-purge.service
.venv/bin/python -m machincast.installation minuteur-purge --config machincast.toml > machincast-purge.timer
sudo install --mode=644 machincast.service machincast-purge.service machincast-purge.timer /etc/systemd/system/
sudo install --mode=644 50-machincast.rules /etc/polkit-1/rules.d/50-machincast.rules
sudo systemctl daemon-reload
sudo systemctl enable --now machincast.service machincast-purge.timer
```

`--retirer-service` arrête et désactive le service et le minuteur de la purge, puis retire leurs unités et la règle : la purge se lance ensuite à la main, par `Machin purge`. La session du compte reste active au démarrage ; `sudo loginctl disable-linger "$(id -un)"` la retire.

## Ajouter un autre compte

MachinCast est prévu pour un seul compte Unix, celui qui l'installe, et `install.sh` n'autorise que lui. Si un autre compte doit exceptionnellement y accéder, un administrateur (un compte avec `sudo`) lance, en remplaçant `programmation` par le nom du compte :

```bash
COMPTE=programmation
# Rôle PostgreSQL du compte, sans aucun droit particulier sur le serveur
sudo -u postgres createuser "${COMPTE}"
# Autorisation à endosser les trois rôles de MachinCast, sans en hériter les droits
sudo -u postgres psql -c "GRANT machincast_lecture, machincast_indexation, machincast_interface TO \"${COMPTE}\" WITH INHERIT FALSE, SET TRUE"
# Lecture du journal du service, effective après le redémarrage du poste
sudo usermod --append --groups systemd-journal "${COMPTE}"
```

Pour ne lui donner qu'une partie des droits, ne nommer que les rôles voulus dans le `GRANT` : par exemple `machincast_indexation` seul pour un compte qui ne fait qu'indexer.

Le compte doit aussi pouvoir lire le répertoire de MachinCast. Sous Ubuntu, un répertoire personnel n'est lisible que par son propriétaire : une installation dans `~/machincast` reste donc inaccessible aux autres comptes tant que ces droits ne sont pas changés.

Pour retirer l'accès d'un compte :

```bash
COMPTE=programmation
sudo -u postgres psql -c "REVOKE machincast_lecture, machincast_indexation, machincast_interface FROM \"${COMPTE}\""
```

## Mettre à jour

Depuis le répertoire de MachinCast :

```bash
git pull
./install.sh
```

`install.sh` met à jour les dépendances Python et applique les nouvelles migrations du schéma aux deux bases. Si des programmes de MachinCast tournent, il propose d'abord de les arrêter, puis les relance à la fin ([Installer avec install.sh](#installer-avec-installsh)) : pour ne pas faire taire l'antenne au mauvais moment, lancer la mise à jour hors d'une émission. `machincast.toml` n'est pas modifié : comparer avec `machincast.exemple.toml` pour y ajouter les nouvelles clés, que MachinCast signale sinon comme manquantes.

À la main, sans relancer `install.sh` :

```bash
git pull
.venv/bin/pip install --editable .
.venv/bin/python -m machincast.installation migrer --config machincast.toml
```

`migrer` applique le schéma aux bases de production et de test de la configuration. Pour une seule base, la même chose avec yoyo :

```bash
.venv/bin/yoyo apply --batch --database "postgresql+psycopg:///machincast?host=/var/run/postgresql" src/machincast/migrations/
```

**Entretenir la base.** `Machin maintenance-db` ([#127](https://github.com/dascritch/machincast/issues/127)) sauvegarde la base de production avec `pg_dump`, dans le répertoire `sauvegardes` de MachinCast, applique les migrations manquantes, vérifie les rôles, puis l'optimise (`VACUUM ANALYZE`). L'interface la lance aussi, après confirmation, menu **Maintenance → Maintenance de la base de données…**. Détails et restauration : [Maintenance de la base](doc/administration/commandes.md#maintenance-de-la-base--machin-maintenance-db).

**Purger la base.** `Machin purge` ([#268](https://github.com/dascritch/machincast/issues/268)) efface de la base de production l'airplay et le log plus vieux que la durée de péremption (`base.peremption`, 60 jours par défaut), et les éléments supprimés depuis plus longtemps ; jamais un fichier. Le service de diffusion l'installe avec un minuteur, chaque jour à midi : une installation qui a déjà le service le reçoit en relançant `./install.sh --service`. Détails : [Purge de la base](doc/administration/commandes.md#purge-de-la-base--machin-purge).

**Marques-pages devenus feeds.** La migration `0012.feeds` ([#252](https://github.com/dascritch/machincast/issues/252)) renomme la table `marques_pages_streams` en `feeds`, et la colonne `marque_page_id` des sonores en `feed_id`, sans toucher aux données ; les droits des trois rôles suivent. Une requête écrite à la main sur les anciens noms est à corriger. La disposition des colonnes de l'ancien onglet « Marques-pages » n'est pas reprise : celle de l'onglet « Feeds » repart des colonnes par défaut.

**Base créée avant une fusion des migrations.** Avant toute mise en production, les migrations ont été fusionnées en une seule, trois fois ([PR #70](https://github.com/dascritch/machincast/pull/70), puis [PR #90](https://github.com/dascritch/machincast/pull/90), qui ajoute la priorité `secours` des événements, puis [PR #100](https://github.com/dascritch/machincast/pull/100), qui ajoute les séquences et la banque « ne pas répéter »). Une base créée avant une fusion ne peut pas être mise à jour. Pour la reconnaître, lister les migrations qu'elle a reçues, et vérifier qu'elle connaît les séquences :

```bash
psql --dbname=machincast -c "SELECT migration_id FROM _yoyo_migration"
psql --dbname=machincast -c "SELECT to_regclass('sequences')"
```

Si la première liste contient autre chose que `0001.schema-initial` et les migrations qui la suivent (`0002.evenements-nom-unique`…), ou si la seconde répond une valeur vide au lieu de `sequences`, recréer la base. **Cela efface son contenu** : ce n'est possible que tant que MachinCast n'est pas en production. Les commandes de ce document utilisent le nom de base du modèle, `machincast` : le remplacer par celui de `base.production` (ou `base.test`) dans `machincast.toml`.

```bash
sudo -u postgres dropdb machincast
./install.sh
```

**Deux événements du même nom.** Depuis la migration `0002.evenements-nom-unique` ([#32](https://github.com/dascritch/machincast/issues/32)), deux événements n'ont plus le même nom interne. Sur une base où c'est le cas, la migration s'arrête, sans rien changer, sur l'erreur `could not create unique index "evenements_nom_interne_key"`, qui nomme le nom en double. Lister les noms en double, renommer l'un des événements, puis relancer la migration :

```bash
psql --dbname=machincast -c "SELECT nom_interne, array_agg(id) FROM evenements GROUP BY nom_interne HAVING count(*) > 1"
psql --dbname=machincast -c "UPDATE evenements SET nom_interne = 'Matinale du samedi' WHERE id = 42"
```

## Installer à la main

Les commandes ci-dessous sont celles qu'enchaîne `install.sh`. Elles se lancent depuis le répertoire de MachinCast, avec son propre compte. Les noms de bases sont ceux du modèle de configuration : `machincast` et `machincast_test`.

**1. Paquets système.**

```bash
sudo apt install python3-venv python3-dev build-essential pkg-config libgirepository-2.0-dev libcairo2-dev \
	gir1.2-gstreamer-1.0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
	gstreamer1.0-alsa gstreamer1.0-pulseaudio gstreamer1.0-pipewire pipewire-bin libmagic1t64 postgresql bash-completion
```

**2. Environnement virtuel Python.** Jamais `--system-site-packages` : MachinCast ne doit pas dépendre des versions des paquets Python de la distribution.

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install --editable .
```

**3. Configuration.**

```bash
cp machincast.exemple.toml machincast.toml
```

Puis l'adapter (voir [Adapter la configuration](#adapter-la-configuration)).

**4. PostgreSQL.** Tout ce qui demande des droits sur le serveur passe par l'utilisateur `postgres` : le compte ne reçoit ni `CREATEDB`, ni `CREATEROLE`. Il devient seulement propriétaire des deux bases, ce qui lui permet d'y appliquer le schéma.

```bash
sudo -u postgres createuser "$(id -un)"
sudo -u postgres createdb --owner="$(id -un)" machincast
sudo -u postgres createdb --owner="$(id -un)" machincast_test
sudo -u postgres psql -c "CREATE ROLE machincast_lecture NOLOGIN" -c "CREATE ROLE machincast_indexation NOLOGIN" \
	-c "CREATE ROLE machincast_interface NOLOGIN"
.venv/bin/python -m machincast.installation migrer --config machincast.toml
```

Les trois rôles de groupe appartiennent au serveur, pas à une base : ils servent aux deux bases, et ne se créent qu'une fois. Une erreur `role … already exists` signifie qu'ils existent déjà.

**5. Rôles du compte.**

```bash
sudo -u postgres psql -c "GRANT machincast_lecture, machincast_indexation, machincast_interface TO \"$(id -un)\" WITH INHERIT FALSE, SET TRUE"
```

**6. Journal système.**

```bash
sudo usermod --append --groups systemd-journal "$(id -un)"
```

**7. Liens.**

```bash
sudo ln --symbolic --force --no-dereference "$(pwd)" /opt/machincast
sudo ln --symbolic --force --no-dereference /opt/machincast/bin/Machin /usr/local/bin/Machin
sudo ln --symbolic --force --no-dereference /opt/machincast/bash-completion/Machin /usr/share/bash-completion/completions/Machin
```

Sans ces liens, le wrapper s'appelle par `bin/Machin` depuis le répertoire de MachinCast, et l'autocomplétion se charge dans le shell courant par `source bash-completion/Machin`.

**Raccourci de l'interface.** Dans le menu des applications, puis, si on le veut, sur le bureau, exécutable :

```bash
.venv/bin/python -m machincast.installation raccourci --config machincast.toml >machincast.desktop
install -D --mode=644 machincast.desktop ~/.local/share/applications/machincast.desktop
install -D --mode=755 machincast.desktop "$(xdg-user-dir DESKTOP)/machincast.desktop"
rm machincast.desktop
```

Le raccourci lance `bin/Machin interface` depuis le répertoire de MachinCast, avec l'icône `src/machincast/interface/machincast.png`, le logo des équipes techniques de la radio ([#213](https://github.com/dascritch/machincast/issues/213)), ou l'image de `interface.icone` quand elle existe ([#111](https://github.com/dascritch/machincast/issues/111)) ; une icône choisie dans les préférences de l'interface réécrit aussitôt les raccourcis installés. Déplacer le répertoire de MachinCast demande de le refaire.

**8. Vérification des greffons GStreamer et de la sortie audio.**

```bash
.venv/bin/python -m machincast.installation verifier --config machincast.toml
```

Pour chaque greffon manquant, la commande nomme le paquet apt à installer.

## Désinstaller

```bash
./install.sh --retirer-service   # si le service de diffusion est installé
sudo rm /opt/machincast /usr/local/bin/Machin /usr/share/bash-completion/completions/Machin
rm --force ~/.local/share/applications/machincast.desktop "$(xdg-user-dir DESKTOP)/machincast.desktop"
sudo -u postgres dropdb machincast
sudo -u postgres dropdb machincast_test
```

Les noms de bases sont ceux du modèle : reprendre ceux de `base.production` et `base.test` dans `machincast.toml`. Sur un poste de développement, la base de test peut servir à d'autres copies de MachinCast : ne la supprimer que si elle n'est plus utilisée.

**Les deux commandes `dropdb` effacent la programmation et l'historique de diffusion.** Les fichiers sonores, eux, ne sont jamais modifiés ni supprimés par MachinCast ([#96](https://github.com/dascritch/machincast/issues/96)) : ils restent en place, ni la désinstallation ni la suppression des bases n'y touchent. Le répertoire de MachinCast peut ensuite être supprimé. Les rôles PostgreSQL et les paquets apt restent en place : ils peuvent servir à d'autres logiciels.

## En cas de problème

| Message | Cause et solution |
| --- | --- |
| `install.sh : lancer install.sh avec son propre compte, sans sudo` | Le script a été lancé avec `sudo` ou en `root`. Le relancer avec son compte. |
| `install.sh : Ubuntu LTS requis (cible : 26.04 LTS)` | Le système n'est pas une Ubuntu LTS. `./install.sh --simulation` montre tout de même les commandes. |
| `install.sh : configuration … à corriger, puis relancer install.sh` | `machincast.toml` est invalide : le message précédent nomme la clé en cause. |
| `périphérique de l'antenne non renseigné : …` | `audio.peripherique` manque : le donner dans `machincast.toml`, ou dans l'interface, **Fichier → Préférences…**, page **Audio**. Puis relancer la diffusion. |
| `sortie audio indisponible : …` | La sortie de `audio.sortie` ne peut pas être créée : installer le greffon nommé, ou vérifier `audio.peripherique`. Relancer `install.sh` vérifie la sortie. |
| `indexation refusée : une autre indexation est en cours sur cette base` | Une indexation tourne déjà sur la base, lancée d'un terminal, de l'interface ou d'un autre poste. Attendre sa fin, puis relancer. Sa fenêtre, si elle vient de l'interface, peut l'arrêter. |
| `--fenetre demande un affichage graphique …` | `--fenetre` a été donné sans session graphique, par exemple en SSH : lancer `Machin indexation` sans `--fenetre`, son journal s'affiche dans le terminal. |
| `base de données injoignable` | PostgreSQL n'est pas démarré (`sudo systemctl start postgresql`), ou `base.socket` ne désigne pas sa socket. |
| `droits insuffisants pour appliquer le schéma dans la base …` | La base existait déjà et appartient à un autre compte, ou ses tables ont été créées par un autre compte. Tant qu'elle ne contient rien d'utile, la supprimer (`sudo -u postgres dropdb …`) puis relancer `install.sh`, qui la recrée. |
| `… : greffon GStreamer absent, installer …` | Un format sonore ou la sortie audio configurée ne peut pas fonctionner. Installer le paquet nommé, puis relancer `install.sh`. |
| `GStreamer 1.24.2 : MachinCast est vérifié avec la version 1.28 (Ubuntu 26.04 LTS) ; mettre à jour libgstreamer1.0-0` | Avertissement : GStreamer, ou l'un de ses greffons, est plus ancien que la version vérifiée. L'installation continue, mais la version installée n'a pas été vérifiée. Passer le poste en Ubuntu 26.04 LTS, ou mettre à jour le paquet nommé. |
| `install.sh : … existe et n'est pas un lien symbolique` | Un fichier ou un répertoire occupe déjà la place d'un lien, par exemple une ancienne installation dans `/opt/machincast`. Le déplacer, puis relancer `install.sh`. |
| `configuration invalide : …` (code 2) | Le message nomme le fichier et la clé en cause. `fichier de configuration introuvable` : le `machincast.toml` du répertoire de MachinCast n'existe pas ; le copier depuis `machincast.exemple.toml`, ou relancer `install.sh`. |
| `install.sh` : `attention : … est superutilisateur de PostgreSQL` | Le compte peut tout faire sur le serveur PostgreSQL, et endosse les rôles de MachinCast sans autorisation, ce que MachinCast ne demande pas. S'il ne sert pas à autre chose, retirer ce droit avec la commande donnée. Tant qu'il est superutilisateur, le scénario de `roles.feature` qui vérifie les autorisations du compte de test échoue, en donnant les commandes à lancer. |
| `erreur de base de données : … permission denied to set role …` | Le compte n'est pas autorisé à endosser le rôle : voir [Ajouter un autre compte](#ajouter-un-autre-compte). |
| Fenêtre « MachinCast : base de données injoignable », au lancement de `Machin interface` | L'interface n'accède pas à la base de `base.production`. Le bouton « Ouvrir INSTALL.md » ouvre ce document, et les détails de la fenêtre donnent l'erreur de PostgreSQL. `connection … failed` ou `No such file or directory` : PostgreSQL n'est pas démarré (`sudo systemctl start postgresql`), ou `base.socket` ne désigne pas sa socket. `database … does not exist` : relancer `install.sh`, qui crée la base. `permission denied to set role` : voir [Ajouter un autre compte](#ajouter-un-autre-compte). |
| `sauvegarde impossible : pg_dump introuvable, installer postgresql-client` | `pg_dump` manque : `sudo apt install postgresql-client`, puis relancer. Rien n'a été modifié. |
| `sauvegarde impossible : … ; maintenance arrêtée, rien n'a été modifié` | Le répertoire des sauvegardes ne peut pas être écrit, le disque est plein, ou `pg_dump` a échoué : son erreur suit. Corriger, ou donner un autre répertoire avec `--sauvegardes`. |
| `rôle … : absent du serveur, ou non endossable par le compte` | Lancer, avec un compte administrateur, les deux commandes données par le message, puis relancer la maintenance. Voir aussi [Ajouter un autre compte](#ajouter-un-autre-compte). |
| `Machin logs` réclame le groupe `adm` ou `systemd-journal`, ou n'affiche que des messages de son propre compte | Le groupe n'est pas encore pris en compte par la session. Si `id -nG "$(id -un)"` cite `systemd-journal` mais pas `id -nG`, l'ajout est fait : redémarrer le poste. Sinon, relancer `install.sh`. |

Les messages d'information s'affichent sur la sortie standard ; les anomalies et les erreurs sur la sortie d'erreur. Chaque ligne commence par son heure, en ISO 8601, avec le décalage horaire du poste, par exemple `2026-10-23T07:55:19+02:00 sortie audio indisponible : …` ([#253](https://github.com/dascritch/machincast/issues/253)) ; le tableau ci-dessus la laisse de côté. Celles de `install.sh` commencent par `install.sh :`.

## Ce qui n'existe pas encore

| Manque | Ticket |
| --- | --- |
| Archives `.tar.gz` publiées en releases | [#41](https://github.com/dascritch/machincast/issues/41) |
