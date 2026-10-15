# Règles — Wrapper et déploiement

À lire avant de toucher au wrapper `Machin`, à `install.sh` ou au packaging. Détails : [spec.md § 7](../spec.md#7-wrapper-machin) et [§ 10](../spec.md#10-installation-et-déploiement).

## Wrapper `Machin`

- Script bash [`bin/Machin`](../../bin/Machin) : `Machin <binaire> [options]` appelle `Machin_<binaire>` par `exec`, options et code de sortie transmis intacts.
- Options génériques : aide minimale (`-h`), aide complète (`--help`), choix du fichier de configuration (`--config`), suivi en direct des logs du binaire lecture (`Machin logs`), liste des binaires (`--binaires`).
- Un nouveau binaire `Machin_<nom>` s'ajoute aussi au tableau `BINAIRES` du wrapper et à son aide complète : un test bats vérifie que `BINAIRES` correspond à `[project.scripts]` de `pyproject.toml`.
- Le binaire est cherché d'abord dans le venv du projet (`<projet>/.venv/bin`, le projet étant le parent du `bin/` du wrapper, liens symboliques résolus), puis dans le `PATH`. Le venv n'a pas besoin d'être activé.
- Le wrapper n'est pas installé dans le venv : en développement, `bin/Machin` ; en production, `install.sh` le rend accessible à tout le système.
- Codes de sortie propres au wrapper : 2 pour un appel incorrect, 127 pour un binaire ou `journalctl` introuvable.
- Le nom de l'unité systemd, `machincast.service`, est fixé dans le wrapper : le changer demande de changer aussi l'unité installée.
- Autocomplétion bash [`bash-completion/Machin`](../../bash-completion/Machin) : les binaires viennent de `Machin --binaires` et leurs options de leur aide, sans liste à recopier.
- Testé avec bats ([`tests/wrapper`](../../tests/wrapper)), vérifié par shellcheck. Messages et aide en français.

## Configuration

- `machincast.toml` (TOML) dans le répertoire du projet, **ignoré par git**.
- Un fichier de configuration se trouve toujours dans le répertoire du dépôt : la documentation, l'aide et les exemples n'en désignent jamais un ailleurs (revue de [PR #65](https://github.com/dascritch/machincast/pull/65)).
- Le modèle versionné est `machincast.exemple.toml`. Toute nouvelle clé y est ajoutée et commentée, dans `src/machincast/configuration.py` (clés connues et validation) et dans le tableau de [spec.md § 9](../spec.md#9-configuration).
- Les clés inconnues sont refusées : ne jamais assouplir cette règle.

## Déploiement

- Cible : Ubuntu 26.04 LTS, uniquement des LTS.
- Releases `.tar.gz` sur le dépôt git, avec un `install.sh` ([#40](https://github.com/dascritch/machincast/issues/40)) qui installe dépendances apt, venv, configuration, bases et rôles, groupe `systemd-journal`, liens vers `/opt/machincast`, wrapper et autocomplétion, puis vérifie les greffons GStreamer. Le service systemd et la règle polkit sont facultatifs ([#22](https://github.com/dascritch/machincast/issues/22)).
- `install.sh` se lance avec son propre compte, jamais avec sudo, et doit rester relançable : chaque étape vérifie d'abord si elle est déjà faite. Toute commande qui modifie le système passe par `executer`, pour que `--simulation` l'affiche sans l'exécuter.
- `install.sh` n'appelle que des commandes système et n'a pas de tests automatisés : shellcheck seulement. Ce qui se teste passe par `machincast.installation` (lecture de la configuration, schéma, greffons GStreamer).
- La liste des paquets apt d'`install.sh` est celle des prérequis de `CLAUDE.md`, sans les outils de développement.
- Le compte qui installe ne reçoit aucun droit particulier sur le serveur PostgreSQL (ni `CREATEDB`, ni `CREATEROLE`) : tout ce qui en demande passe par `sudo -u postgres` (revue de [PR #72](https://github.com/dascritch/machincast/pull/72)).
- Environnement virtuel isolé : jamais `--system-site-packages`. Toute dépendance Python est déclarée dans `pyproject.toml` et installée par pip ; apt ne fournit que les bibliothèques système ([#51](https://github.com/dascritch/machincast/issues/51)).
- La règle polkit n'autorise que le démarrage, l'arrêt et le redémarrage du service de lecture.
- Tous les comptes de la radio lisent le journal du service : `install.sh` les ajoute au groupe `systemd-journal`, jamais à `adm`, qui donne d'autres droits d'administration.
