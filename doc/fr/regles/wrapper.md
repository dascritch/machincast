# Règles — Wrapper et déploiement

À lire avant de toucher au wrapper `Machin`, à `install.sh` ou au packaging.
Détails : [spec.md § 7](../spec.md#7-wrapper-machin) et [§ 10](../spec.md#10-installation-et-déploiement).

## Wrapper `Machin`

- Script bash [`bin/Machin`](../../../bin/Machin) : `Machin <binaire> [options]` appelle `Machin_<binaire>`, options et code de sortie transmis intacts.
	Pas par `exec` ([#413](https://github.com/dascritch/machincast/issues/413)) : le wrapper attend la fin du binaire, `INT`, `TERM` et `HUP` neutralisés pour lui seul (le binaire les reçoit par le groupe du terminal ou le cgroup du service), et, si le binaire meurt d'un signal (code 129 à 159), fait achever ses rapports de crash en cours par `python -m machincast.crash` (`achever_rapports`), avec le Python du venv du binaire, sinon celui de sa ligne `#!`.
- Options génériques : aide minimale (`-h`), aide complète (`--help`), choix du fichier de configuration (`--config`), suivi en direct des logs du binaire lecture (`Machin logs`), liste des binaires (`--binaries`).
- Tâches régulières ([#455](https://github.com/dascritch/machincast/issues/455)) : `Machin tasks` (`lancer_taches`) lance chaque tâche due, l'une après l'autre ; c'est la seule commande du minuteur `machincast-tasks.timer`, tous les quarts d'heure.
	Une nouvelle tâche est une fonction appelée par `lancer_taches`, qui ne fait rien tant qu'elle n'est pas due : ni l'unité ni le minuteur ne changent.
	Les binaires s'y lancent par `lancer_binaire`, qui rend leur code au lieu de sortir.
- Développement ([#77](https://github.com/dascritch/machincast/issues/77)) : `Machin dev` (sous-shell, venv activé) et `Machin dev-test` (toutes les vérifications, avec un bilan).
	`Machin dev-test --coverage`, avant `--scenarios` s'il y en a ([#438](https://github.com/dascritch/machincast/issues/438)), lance `pytest` par `coverage run -m pytest` puis ajoute au bilan `coverage combine` et `coverage report`.
	La liste des outils de `dev-test` est celle de la section « Qualité » et des tests de `CLAUDE.md` : la changer d'un côté, c'est la changer de l'autre.
	Ils restent visibles sans `--dev`, et nomment alors ce qui manque.
	`Machin dev-screenshots` ([#128](https://github.com/dascritch/machincast/issues/128)) refait les captures du guide de l'antenne avec le Python du venv, depuis le répertoire de MachinCast (`python -m tests.screenshots`) : jamais avec `--config`, puisqu'il n'écrit que dans la base de test.
- Un nouveau binaire `Machin_<nom>` s'ajoute aussi au tableau `BINAIRES` du wrapper et à son aide complète : un test bats vérifie que `BINAIRES` correspond à `[project.scripts]` de `pyproject.toml`.
	Un nom peut contenir un tiret, comme `Machin_maintenance-db` ([#127](https://github.com/dascritch/machincast/issues/127)).
- `Machin status` ([#518](https://github.com/dascritch/machincast/issues/518)) est un binaire comme les autres, `Machin_status` : le wrapper ne fait que l'appeler.
	Ses réponses vont sur la sortie standard, une ligne chacune, pour qu'un script les lise : tout autre message passe par le journal.
	Une nouvelle réponse s'ajoute à `machincast.status`, avec ses scénarios (`status.feature`), sans toucher au wrapper.
- `Machin banner` ([#517](https://github.com/dascritch/machincast/issues/517)) est écrit en bash dans le wrapper, sans Python ni base : il est lancé à chaque nouveau shell du service et doit rester instantané.
	Le script de session `/etc/profile.d/machincast.sh` est statique (`machincast.installation.profile`) : le numéro de version vient de `pyproject.toml` à l'exécution, pour que `install.sh` n'ait pas à le réécrire à chaque version.
- Le binaire est cherché d'abord dans le venv du projet (`<projet>/.venv/bin`, le projet étant le parent du `bin/` du wrapper, liens symboliques résolus), puis dans le `PATH`.
	Le venv n'a pas besoin d'être activé.
- Le wrapper n'est pas installé dans le venv : en développement, `bin/Machin` ; en production, `install.sh` le rend accessible à tout le système.
- Codes de sortie propres au wrapper : 2 pour un appel incorrect, 127 pour un binaire ou `journalctl` introuvable.
- Le nom de l'unité systemd, `machincast.service`, est fixé dans le wrapper : le changer demande de changer aussi l'unité installée.
- Autocomplétion bash [`bash-completion/Machin`](../../../bash-completion/Machin) : les binaires viennent de `Machin --binaries` et leurs options de leur aide, sans liste à recopier.
- Testé avec bats ([`tests/wrapper`](../../../tests/wrapper)), vérifié par shellcheck.
	Messages et aide écrits en anglais et traduits par le catalogue ([#360](https://github.com/dascritch/machincast/issues/360), [messages et traductions](developpement.md#messages-et-traductions)) ; les tests les lisent en français.

## Configuration

- `machincast.toml` (TOML) dans le répertoire du projet, **ignoré par git**.
	Sans `--config`, les binaires le lisent là, quel que soit le répertoire courant : `machincast.configuration.default_file()`, déduit de l'emplacement du paquet, installé en mode éditable.
	Le wrapper n'ajoute pas de `--config` : il appelle les binaires du `.venv` de ce même répertoire, et son aide affiche ce chemin ([#76](https://github.com/dascritch/machincast/issues/76)).
- Un fichier de configuration se trouve toujours dans le répertoire du dépôt : la documentation, l'aide et les exemples n'en désignent jamais un ailleurs (revue de [PR #65](https://github.com/dascritch/machincast/pull/65)).
- Le modèle versionné est `machincast.exemple.toml`.
	Toute nouvelle clé y est ajoutée et commentée, dans `src/machincast/configuration.py` (clés connues et validation) et dans le tableau de [spec.md § 9](../spec.md#9-configuration).
- Les clés inconnues sont refusées : ne jamais assouplir cette règle.

## Déploiement

- Cible : Ubuntu 26.04 LTS, uniquement des LTS.
- Releases `.tar.gz` sur le dépôt git, avec un `install.sh` ([#40](https://github.com/dascritch/machincast/issues/40)) qui installe dépendances apt, venv, configuration, bases et rôles, groupe `systemd-journal`, liens vers `/opt/machincast`, wrapper et autocomplétion, puis vérifie les greffons GStreamer.
	Le service systemd et la règle polkit sont facultatifs ([#22](https://github.com/dascritch/machincast/issues/22)).
- `install.sh` vérifie d'abord l'accès au réseau ([#376](https://github.com/dascritch/machincast/issues/376), `verifier_reseau`, avant d'arrêter quoi que ce soit) : sans lui, une première installation s'arrête, une mise à jour continue sans apt ni pip (`RESEAU`).
- `install.sh` se lance avec son propre compte, jamais avec sudo, et doit rester relançable : chaque étape vérifie d'abord si elle est déjà faite.
	Toute commande qui modifie le système passe par `executer`, pour que `--simulation` l'affiche sans l'exécuter.
- `install.sh` n'appelle que des commandes système : shellcheck le vérifie, et `installation.feature` relit son texte (ce qu'il installe et retire pour le service, ses questions, l'absence de `setfacl`, `chmod` et `chown`).
	Ce qui se teste en l'exécutant passe par `machincast.installation` (lecture de la configuration, schéma, greffons GStreamer), et par `machincast.programs` pour les programmes en cours ([#254](https://github.com/dascritch/machincast/issues/254)) : ce dernier n'emploie que la bibliothèque standard, car `install.sh` le lance avec le `python3` du système, avant de toucher au venv.
- Les messages d'`install.sh` ont quatre niveaux ([#517](https://github.com/dascritch/machincast/issues/517)) : `info`, caché sans `--verbose` ni `--simulation`, pour ce qui est technique ou déjà fait ; `annonce`, toujours montré, pour ce que le technicien doit lire ; `avertissement`, en jaune ; `echec`, en jaune vif sur fond rouge sombre, sur la sortie d'erreur.
	Une nouvelle ligne est une `info`, sauf si un technicien doit la lire : l'oublier n'avertit de rien, la montrer à tort noie l'essentiel.
	Les couleurs passent par `choisir_couleurs` (terminal seulement, `NO_COLOR` les coupe, `FORCE_COLOR` les impose pour les tests).
	Une question passe par `interroger` : en blanc et en gras, ou dans une fenêtre `kdialog` sur un poste graphique local (`graphique`), jamais par un `read -p`.
- La liste des paquets apt d'`install.sh` est celle des prérequis de `CLAUDE.md`, sans les outils de développement, que `--dev` ajoute (`PAQUETS_DEV`).
- [`INSTALL.md`](../../../INSTALL.fr.md) documente `install.sh` pour l'administrateur, étape par étape, avec les commandes équivalentes à la main ([#71](https://github.com/dascritch/machincast/issues/71)).
	Toute modification d'`install.sh`, du wrapper ou de `machincast.installation` le met à jour dans le même commit.
	[`documentation.feature`](../../../tests/features/documentation.feature) vérifie que ses paquets apt, son `GRANT`, les options, binaires et étapes qu'il cite et ses liens restent cohérents avec `install.sh`, `CLAUDE.md` et le code.
- Le compte qui installe ne reçoit aucun droit particulier sur le serveur PostgreSQL (ni `CREATEDB`, ni `CREATEROLE`) : tout ce qui en demande passe par `sudo -u postgres` (revue de [PR #72](https://github.com/dascritch/machincast/pull/72)).
- Environnement virtuel isolé : jamais `--system-site-packages`.
	Toute dépendance Python est déclarée dans `pyproject.toml` et installée par pip ; apt ne fournit que les bibliothèques système ([#51](https://github.com/dascritch/machincast/issues/51)).
- La règle polkit n'autorise que le démarrage, l'arrêt et le redémarrage du service de lecture, au compte de MachinCast, avec l'authentification d'un administrateur ([#22](https://github.com/dascritch/machincast/issues/22)).
	Les scénarios d'`installation.feature` l'exécutent avec Duktape, le moteur JavaScript de polkitd, par la dépendance de test `dukpy` (moins de 0.6, passé ensuite à QuickJS) : une règle écrite en ES5, comme polkitd l'attend, sans `node` ni paquet apt ([#470](https://github.com/dascritch/machincast/issues/470)).
- Raccourci de l'interface ([#62](https://github.com/dascritch/machincast/issues/62)) : rédigé par `machincast.shortcut.write`, que `machincast.installation shortcut` écrit avec l'icône de `interface.icon` ([#111](https://github.com/dascritch/machincast/issues/111)) et que les préférences de l'interface réécrivent (`rewrite`) ; les tests remplacent `MENU_FOLDER` et `DESKTOP_FOLDER` (fixture `sample_shortcuts`), jamais les raccourcis du compte.
	Il se teste (`desktop-file-validate` compris) ; `install.sh` l'installe pour le compte, sans sudo, dans `$XDG_DATA_HOME/applications`, et sur le bureau (`xdg-user-dir DESKTOP`, exécutable) si la question posée l'accepte, ou avec `--desktop`.
	Avec celle d'arrêter les programmes en cours ([#254](https://github.com/dascritch/machincast/issues/254)) et celle de mettre à jour un service installé qui ne l'est plus ([#376](https://github.com/dascritch/machincast/issues/376), `verifier_le_service_installe`), ce sont les trois seules questions d'`install.sh` sans `--service`, qui pose en plus celles du poste dédié, de l'emplacement de MachinCast et des sonores d'un répertoire personnel ([#381](https://github.com/dascritch/machincast/issues/381)) : aucune n'est posée en simulation ni sans terminal, et celle du bureau ne l'est pas quand le raccourci y est déjà.
	Son nom, `machincast.desktop`, est celui que l'interface donne à `setDesktopFileName` (`machincast.interface.application.SHORTCUT`).
	L'icône est `src/machincast/interface/machincast.png`, le logo des équipes techniques de la radio ([#213](https://github.com/dascritch/machincast/issues/213)), données du paquet.
- Une fonction d'`install.sh` appelée par `if` ou `||` ne s'arrête pas d'elle-même sur une erreur (`set -e` y est suspendu) : chaque commande dont l'échec laisserait un fichier faux ou vide y finit par `|| echec "…"`.
- Le service de lecture tourne sous son propre compte système, `machincast`, avec son PipeWire et son WirePlumber, hors de toute session ([#381](https://github.com/dascritch/machincast/issues/381)) ; le compte de MachinCast rejoint son groupe, qui lit ses logs et pré-écoute l'antenne.
	Le service ne lit jamais un répertoire personnel : MachinCast va en `/opt/machincast`, les sonores en `/home/machincast` ; `install.sh` ne change jamais aucun droit (ni `setfacl`, ni `chmod`, ni `chown`).
	Les unités, la règle et les configurations sont rédigées par `machincast.installation` (`unit`, `pipewire-unit`, `wireplumber-unit`, `wireplumber-service`, `wireplumber-desktop`, `tmpfiles`, `logrotate`, `rule`), où elles se testent ; `install.sh --service` ne fait que les installer, et seulement si elles ont changé ; `--remove-service` retire tout, sauf les logs et tout répertoire qui contient un fichier sonore ([#430](https://github.com/dascritch/machincast/issues/430)).
- L'installation est mono-utilisateur : un seul compte Unix utilise MachinCast, celui qui l'installe, dans son répertoire personnel, d'où seule l'installation du service le déplace vers `/opt/machincast` ([#381](https://github.com/dascritch/machincast/issues/381)).
	Ce compte lit le journal du service : `install.sh` l'ajoute au groupe `systemd-journal`, jamais à `adm`, qui donne d'autres droits d'administration.
