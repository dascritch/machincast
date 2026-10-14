# Règles — Développement

À lire avant toute modification de code.

## Cycle de travail

1. Chaque fonctionnalité part d'un ticket GitHub Issues.
2. Si aucun ticket n'existe, **ne pas le créer seul** : proposer un titre et une description au format user story, puis attendre que le ticket soit créé ensemble.

	```
	En tant que <rôle>,
	je veux que <comportement>,
	afin que <bénéfice>.
	```

3. Écrire d'abord le scénario BDD (voir [tests.md](tests.md)), le voir échouer, puis implémenter (TDD).
4. Une fonctionnalité = un test associé + un commit lié au ticket.
5. Mettre à jour la documentation Markdown dans `/doc` dans le même commit.

## Références aux tickets et aux PR

Toute référence à un ticket ou à une PR est un lien, jamais un numéro nu :

- en Markdown : `[#51](https://github.com/dascritch/machincast/issues/51)` ou `[PR #56](https://github.com/dascritch/machincast/pull/56)` ;
- dans un commentaire de code, une docstring ou un message : l'URL complète, par exemple `https://github.com/dascritch/machincast/issues/51`.

Un scénario ([`tests/features/references.feature`](../../tests/features/references.feature)) refuse les références nues. Seules les migrations déjà fusionnées y échappent : on ne les modifie jamais, même leurs commentaires.

## Messages de commit

Format Conventional Commits. Sous la première ligne, après une ligne vide : l'URL du ticket, puis à la ligne suivante le titre du ticket.

```
feat(lecture): bascule immédiate sur un événement prioritaire

https://github.com/dascritch/machincast/issues/123
Bascule sur un événement de priorité supérieure
```

Portées usuelles : `lecture`, `indexation`, `interface`, `wrapper`, `db`, `install`, `doc`.

## Style de code

- Python pour tout le projet, typé strictement : `mypy --strict` doit passer.
- Linter et formateur : ruff.
- Scripts bash (wrapper, autocomplétion, tests bats) : `set -euo pipefail` pour un exécutable, et shellcheck doit passer.
- **Indentation par tabulations**, pour des raisons d'accessibilité. Ne jamais convertir en espaces. Dans la configuration ruff : `indent-style = "tab"` pour le formateur, règle `W191` désactivée.
- Vocabulaire : « sonore », « banque », « événement ». « Playlist » désigne uniquement la liste exportée en .pls, .csv ou .html, jamais un objet en base ou à l'écran.
- Le nom du projet s'écrit toujours « MachinCast ».

## Exécutables

- Une nouvelle dépendance Python se déclare dans `pyproject.toml`, jamais en paquet apt `python3-*` : le venv n'utilise pas les paquets Python du système ([#51](https://github.com/dascritch/machincast/issues/51)).
- Tout exécutable s'appelle `Machin_<nom>` et est déclaré dans `pyproject.toml` (aucune compilation).
- Les binaires sans interface se lancent par convention via le wrapper `Machin` (voir [wrapper.md](wrapper.md)).
