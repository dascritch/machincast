# MachinCast

Système automatisé de diffusion sonore pour radio, sous Linux : il fournit un fil antenne en dehors des émissions en direct, à partir de banques de sonores et d'événements horaires.

Spécification fonctionnelle : [doc/spec.md](doc/spec.md).

## Stack

Python · PySide6 (Qt 6.10) · PostgreSQL via socket Unix (psycopg 3, auth peer) · GStreamer (PyGObject) · yoyo-migrations · pytest-bdd, pytest-qt, bats · ruff, mypy strict · cible Ubuntu 26.04 LTS.

## Commandes

```bash
# Prérequis système : uniquement ce que pip ne peut pas fournir (https://github.com/dascritch/machincast/issues/51)
# — compilation de PyGObject, GStreamer et ses plugins (plugins-bad : AIFF, AAC et encodeurs des tests), PostgreSQL
sudo apt install python3-venv python3-dev build-essential pkg-config libgirepository-2.0-dev libcairo2-dev \
	gir1.2-gstreamer-1.0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
	gstreamer1.0-alsa gstreamer1.0-pulseaudio gstreamer1.0-pipewire postgresql
# Outils de développement du wrapper bash
sudo apt install bats shellcheck

# Installation de dev : venv isolé, jamais --system-site-packages (https://github.com/dascritch/machincast/issues/51)
python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
cp machincast.exemple.toml machincast.toml   # puis l'adapter ; jamais versionné

# Base de test locale (PostgreSQL ≥ 16, authentification peer)
createdb machincast_test

# Autoriser un utilisateur système à endosser des rôles
# (par un rôle PostgreSQL qui a CREATEROLE et qui a créé les rôles, par exemple celui qui applique les migrations)
python -m machincast.droits --base machincast_test autoriser "$(id -un)" lecture indexation interface

# Qualité
ruff check . && ruff format --check . && mypy --strict src/
shellcheck -x bin/Machin bash-completion/Machin tests/wrapper/*.bash tests/wrapper/*.bats

# Tests : configuration tests/configuration-test.toml, ou celle désignée par MACHINCAST_CONFIG_TEST
# (les scénarios de base de données sont ignorés si PostgreSQL est injoignable)
pytest
bats tests/wrapper

# Schéma de la base de test, à la main
yoyo apply --batch --database "postgresql+psycopg:///machincast_test?host=/var/run/postgresql" src/machincast/migrations/

# Wrapper : prend les binaires dans .venv, sans qu'il soit activé
bin/Machin --help
bin/Machin lecture --help

# Lancement avec une configuration précise, suivi des logs du service
bin/Machin lecture --config <fichier>
bin/Machin indexation --audit-complet   # par défaut : indexation rapide, seuls les sonores en aperçu sont décodés
bin/Machin logs

# Autocomplétion dans le shell courant
source bash-completion/Machin
```

## Règles selon le contexte

Lire le bloc correspondant **avant** de modifier le code concerné :

| Contexte | Règles |
| --- | --- |
| Toute modification (tickets, commits, style, tabulations) | [doc/regles/developpement.md](doc/regles/developpement.md) |
| Écrire ou lancer des tests | [doc/regles/tests.md](doc/regles/tests.md) |
| Schéma, requêtes, droits | [doc/regles/base-de-donnees.md](doc/regles/base-de-donnees.md) |
| `Machin_lecture` | [doc/regles/binaire-lecture.md](doc/regles/binaire-lecture.md) |
| `Machin_indexation` | [doc/regles/indexation.md](doc/regles/indexation.md) |
| `Machin_interface` | [doc/regles/interface.md](doc/regles/interface.md) |
| Wrapper `Machin`, configuration, `install.sh` | [doc/regles/wrapper.md](doc/regles/wrapper.md) |

## Impératifs

- TDD avec scénarios BDD : pas de fonctionnalité sans test.
- Un commit par fonctionnalité, lié à un ticket GitHub Issues. Sans ticket, proposer une user story et attendre.
- Indentation par **tabulations**.
- Ne jamais toucher à la base de production pendant les tests.
