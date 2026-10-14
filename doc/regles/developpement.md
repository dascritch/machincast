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
- **Indentation par tabulations**, pour des raisons d'accessibilité. Ne jamais convertir en espaces. Dans la configuration ruff : `indent-style = "tab"` pour le formateur, règle `W191` désactivée.
- Vocabulaire : « sonore », « banque », « événement ». « Playlist » désigne uniquement la liste exportée en .pls, .csv ou .html, jamais un objet en base ou à l'écran.
- Le nom du projet s'écrit toujours « MachinCast ».

## Exécutables

- Tout exécutable s'appelle `Machin_<nom>` et est déclaré dans `pyproject.toml` (aucune compilation).
- Les binaires sans interface se lancent par convention via le wrapper `Machin` (voir [wrapper.md](wrapper.md)).
