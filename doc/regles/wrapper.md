# Règles — Wrapper et déploiement

À lire avant de toucher au wrapper `Machin`, à `install.sh` ou au packaging. Détails : [spec.md § 7](../spec.md#7-wrapper-machin) et [§ 10](../spec.md#10-installation-et-déploiement).

## Wrapper `Machin`

- Script bash : `Machin <binaire> [options]` appelle `Machin_<binaire>`.
- Options génériques : aide minimale, aide complète, choix du fichier de configuration, suivi en direct des logs du binaire lecture.
- Autocomplétion bash fournie et installée.
- Testé avec bats.

## Configuration

- `machincast.toml` (TOML) dans le répertoire du projet, **ignoré par git**.
- Le modèle versionné porte un autre nom. Toute nouvelle clé y est ajoutée et documentée.

## Déploiement

- Cible : Ubuntu 26.04 LTS, uniquement des LTS.
- Releases `.tar.gz` sur le dépôt git, avec un `install.sh` qui installe dépendances apt, venv, bases et rôles, unité systemd, règle polkit, wrapper et autocomplétion.
- La règle polkit n'autorise que le démarrage, l'arrêt et le redémarrage du service de lecture.
