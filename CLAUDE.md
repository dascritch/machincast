# MachinCast

Système automatisé de diffusion sonore pour radio, sous Linux : il fournit un fil antenne en dehors des émissions en direct, à partir de banques de sonores et d'événements horaires.

Spécification fonctionnelle : [doc/spec.md](doc/spec.md).

## Stack

Python · PySide6 (Qt 6.10) · PostgreSQL via socket Unix (psycopg 3, auth peer) · GStreamer (PyGObject) · yoyo-migrations · pytest-bdd, pytest-qt, bats · ruff, mypy strict · cible Ubuntu 26.04 LTS.

## Commandes

```bash
# Prérequis système (compilation de PyGObject, GStreamer) — voir #51
sudo apt install libgirepository-2.0-dev libcairo2-dev gir1.2-gstreamer-1.0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good

# Installation de dev
python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
cp machincast.exemple.toml machincast.toml   # puis l'adapter ; jamais versionné

# Qualité
ruff check . && ruff format --check . && mypy --strict src/

# Tests
pytest

# Aide des exécutables
Machin_lecture --help
Machin_indexation --help
Machin_interface --help

# Lancement avec une configuration précise
Machin_lecture --config <fichier>
```

Commandes à venir : schéma de la base de test (`yoyo apply --database <url> migrations/`, #3), tests du wrapper (`bats tests/wrapper`, #6), lancement par le wrapper (`Machin lecture --config <fichier>`, #6).

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
