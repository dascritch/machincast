# MachinCast

Système automatisé de diffusion sonore pour radio, sous Linux : il fournit un fil antenne en dehors des émissions en direct, à partir de banques de sonores et d'événements horaires.

Spécification fonctionnelle : [doc/spec.md](doc/spec.md).

## Stack

Python · PySide6 (Qt 6.10) · PostgreSQL via socket Unix (psycopg 3, auth peer) · GStreamer (PyGObject) · yoyo-migrations · pytest-bdd, pytest-qt, bats · ruff, mypy strict · cible Ubuntu 26.04 LTS.

## Commandes

```bash
# Prérequis système : uniquement ce que pip ne peut pas fournir (https://github.com/dascritch/machincast/issues/51)
# — compilation de PyGObject, GStreamer et ses plugins (plugins-bad : AIFF, AAC et encodeurs des tests), libmagic (type
# des fichiers, https://github.com/dascritch/machincast/issues/121), PostgreSQL, autocomplétion bash
sudo apt install python3-venv python3-dev build-essential pkg-config libgirepository-2.0-dev libcairo2-dev \
	gir1.2-gstreamer-1.0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
	gstreamer1.0-alsa gstreamer1.0-pulseaudio gstreamer1.0-pipewire pipewire-bin libmagic1t64 postgresql bash-completion
# Outils de développement du wrapper bash
sudo apt install bats shellcheck

# Installation d'un poste, relançable : ./install.sh (--simulation pour voir les commandes sans les exécuter,
# --dev pour ajouter bats, shellcheck et les dépendances de test)
# Installation de dev : venv isolé, jamais --system-site-packages (https://github.com/dascritch/machincast/issues/51)
python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"   # procédure complète : INSTALL.md
cp machincast.exemple.toml machincast.toml   # puis l'adapter ; jamais versionné

# Base de test locale (PostgreSQL ≥ 16, authentification peer) : ./install.sh la prépare. Le compte n'a besoin
# d'aucun droit particulier (ni CREATEDB, ni CREATEROLE) : propriétaire de la base, il endosse les trois rôles
# sans en hériter les droits. Les tests ne créent jamais de compte et n'attribuent jamais de rôle. À la main :
sudo -u postgres createuser "$(id -un)"
sudo -u postgres createdb --owner="$(id -un)" machincast_test
sudo -u postgres psql -c "CREATE ROLE machincast_lecture NOLOGIN" -c "CREATE ROLE machincast_indexation NOLOGIN" \
	-c "CREATE ROLE machincast_interface NOLOGIN"
sudo -u postgres psql -c "GRANT machincast_lecture, machincast_indexation, machincast_interface TO \"$(id -un)\" WITH INHERIT FALSE, SET TRUE"

# Toutes les vérifications ci-dessous d'un coup, avec un bilan par outil (venv non activé) : bin/Machin dev-test
# Sous-shell dans le dépôt, venv activé : bin/Machin dev

# Qualité
ruff check . && ruff format --check . && mypy --strict src/
shellcheck -x install.sh bin/Machin bash-completion/Machin tests/wrapper/*.bash tests/wrapper/*.bats

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
- Une correction d'une PR ouverte est un nouveau commit, jamais un amend ([#131](https://github.com/dascritch/machincast/issues/131)). Une branche se remet à jour avec `main` par `git rebase`, jamais par un commit de fusion, puis `git push --force-with-lease` ; voir [doc/regles/developpement.md](doc/regles/developpement.md#corrections-dune-pr-ouverte).
- Indentation par **tabulations**.
- Ne jamais toucher à la base de production pendant les tests.
- **Un fichier sonore n'est jamais supprimé, renommé, déplacé, remplacé ni écrit par MachinCast**, quels que soient les changements de son entrée dans `sonores` ([#96](https://github.com/dascritch/machincast/issues/96)). Un répertoire de banque non plus : supprimer un sonore ou une banque ne supprime que son entrée en base ([#33](https://github.com/dascritch/machincast/issues/33)). Voir [doc/regles/developpement.md](doc/regles/developpement.md#fichiers-sonores).
- Un ticket n'est terminé que si ses fonctions et actions externes sont documentées pour les humains : voir la [definition of done](doc/regles/developpement.md#definition-of-done).
