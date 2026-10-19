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
4. Une fonctionnalité = un test associé + un commit lié au ticket, puis un commit par correction ([Corrections d'une PR ouverte](#corrections-dune-pr-ouverte)).
5. Mettre à jour la documentation Markdown dans `/doc` dans le même commit.
6. Vérifier la [definition of done](#definition-of-done) avant de demander la relecture.

## Definition of done

Un ticket n'est terminé que si :

- ses scénarios BDD ont été écrits d'abord, vus en échec, puis réussis ;
- `ruff`, `mypy --strict`, `shellcheck`, `pytest` et `bats` passent ;
- ses fonctions et ses actions externes sont documentées pour les humains ([#71](https://github.com/dascritch/machincast/issues/71)) : tout ce qu'un utilisateur ou un administrateur voit ou déclenche, c'est-à-dire les commandes, options et codes de retour, les clés de configuration, les fichiers produits, les messages affichés et les effets sur le système (base, journal, sortie audio, fichiers sonores) ;
- la spécification et les règles de développement sont à jour.

La documentation pour les humains s'adresse aux utilisateurs et aux administrateurs, pas aux développeurs. Elle va dans [`INSTALL.md`](../../INSTALL.md) pour l'installation, et dans le [guide d'utilisation](../utilisation.md) pour tout le reste, distinct de la spécification et de ces règles ; elle est mise à jour dans le commit du ticket. Les scénarios de [`guide.feature`](../../tests/features/guide.feature) échouent quand une option d'un programme, un état d'un sonore, un verdict de vérification ou une clé de métadonnées manque au guide ([#74](https://github.com/dascritch/machincast/issues/74)).

Le modèle de description de PR ([`.github/pull_request_template.md`](../../.github/pull_request_template.md)) reprend ces points en cases à cocher, dont « documentation humaine à jour », cochées avant la demande de relecture. Un scénario de [`documentation.feature`](../../tests/features/documentation.feature) vérifie que cette section, le renvoi de `CLAUDE.md` et la case du modèle de PR existent.

## Références aux tickets et aux PR

Toute référence à un ticket ou à une PR est un lien, jamais un numéro nu :

- en Markdown : `[#51](https://github.com/dascritch/machincast/issues/51)` ou `[PR #56](https://github.com/dascritch/machincast/pull/56)` ;
- dans un commentaire de code, une docstring ou un message : l'URL complète, par exemple `https://github.com/dascritch/machincast/issues/51`.

Un scénario ([`tests/features/references.feature`](../../tests/features/references.feature)) refuse les références nues, partout, migrations comprises.

## Messages de commit

Format Conventional Commits. Sous la première ligne, après une ligne vide : l'URL du ticket, puis à la ligne suivante le titre du ticket.

```
feat(lecture): bascule immédiate sur un événement prioritaire

https://github.com/dascritch/machincast/issues/123
Bascule sur un événement de priorité supérieure
```

Portées usuelles : `lecture`, `indexation`, `interface`, `wrapper`, `db`, `install`, `doc`.

## Corrections d'une PR ouverte

Une correction d'une PR ouverte, demandée en relecture ou trouvée ensuite, est un **nouveau commit**, poussé sans forcer ([#131](https://github.com/dascritch/machincast/issues/131)). Le relecteur voit ainsi ce qui a changé depuis sa dernière relecture.

- Jamais de `git commit --amend`, de `git rebase` ni de `git push --force` (ou `--force-with-lease`) sur la branche d'une PR ouverte : son historique n'est jamais réécrit.
- Le message suit le format ci-dessus, lié au même ticket, avec le type qui convient : `fix` pour un défaut, `refactor`, `test` ou `docs` pour le reste. Par exemple :

```
fix(interface): le dépôt d'un fichier sonore n'est accepté que comme une copie

https://github.com/dascritch/machincast/issues/31
Écran de détails d'une banque
```

## Style de code

- Python pour tout le projet, typé strictement : `mypy --strict` doit passer.
- Linter et formateur : ruff.
- Jamais de `print` : les messages passent par `logging`, avec un journal par module (`logging.getLogger(__name__)`). `machincast.journal.configurer` envoie les informations sur la sortie standard, les anomalies (`warning`) et les erreurs (`error`) sur la sortie d'erreur, préfixées du nom de l'exécutable. Un scénario de [`socle.feature`](../../tests/features/socle.feature) refuse tout `print` dans `src/` (revue de [PR #65](https://github.com/dascritch/machincast/pull/65)).
- Chaînes Python : f-strings (ou t-strings), jamais la notation `str % valeur`, même indirectement : un message de journal est une f-string (`journal.error(f"base {nom} injoignable : {erreur}")`), un format de `logging` s'écrit avec `style="{"` ([#73](https://github.com/dascritch/machincast/issues/73)). Seule exception : les `%s` des requêtes SQL, qui sont des valeurs liées par psycopg et non du formatage de chaîne.
- Scripts bash (wrapper, autocomplétion, `install.sh`, tests bats) : `set -euo pipefail` pour un exécutable, et shellcheck doit passer. Une variable s'écrit toujours avec accolades, `"${RACINE}"` et jamais `"$RACINE"` ([#73](https://github.com/dascritch/machincast/issues/73)).
- Deux scénarios de [`socle.feature`](../../tests/features/socle.feature) refusent la notation `%` dans le Python du dépôt et les variables bash sans accolades.
- Conditions (revue de [PR #100](https://github.com/dascritch/machincast/pull/100)) : dans une condition qui enchaîne `and` ou `or`, chaque opérande est entre parenthèses, par exemple `if (actif is not None) and (dernier.debut is not None) and (self._a_commence(actif, dernier.debut)):`. Une longue condition se coupe avant chaque `and` ou `or`, une parenthèse par ligne.
- Pas d'expression conditionnelle qui décide d'un appel, comme `evenement = None if identifiant is None else lire_evenement(connexion, identifiant)` : une valeur par défaut, puis un `if` explicite (revue de [PR #100](https://github.com/dascritch/machincast/pull/100)). La conversion d'une valeur lue en base reste permise sur une ligne : `None if valeur is None else int(str(valeur))`.
- Ces deux règles valent pour tout le code Python de `src/` et de `tests/`, hors écrans compilés par `pyside6-uic`, et pour toute expression : valeur par défaut comprise, `(nom) or ("")`. Les seuls appels permis dans une branche d'expression conditionnelle sont les conversions `int`, `str` et `bool`. Deux scénarios de [`socle.feature`](../../tests/features/socle.feature) les vérifient, avec des exemples de code accepté et refusé (`tests/style.py`, [#103](https://github.com/dascritch/machincast/issues/103)) ; la règle SIM108 de ruff, qui réclame une expression conditionnelle à la place d'un `if`, est désactivée.
- **Indentation par tabulations**, pour des raisons d'accessibilité. Ne jamais convertir en espaces. Dans la configuration ruff : `indent-style = "tab"` pour le formateur, règle `W191` désactivée.
- Vocabulaire : « sonore », « banque », « événement ». « Playlist » désigne uniquement la liste exportée en .pls, .csv ou .html, jamais un objet en base ou à l'écran.
- Le nom du projet s'écrit toujours « MachinCast ».

## Fichiers sonores

**Règle absolue** ([#96](https://github.com/dascritch/machincast/issues/96)) : MachinCast ne supprime jamais un fichier sonore, quels que soient les changements de son entrée dans la table `sonores` (état `supprime`, `desactive`, `expire` ou `errone`, emplacement ou tags modifiés, ligne effacée). Il ne le renomme, ne le déplace, ne le remplace et n'y écrit jamais non plus : les fichiers sonores ne sont que lus. Supprimer un sonore, c'est supprimer sa ligne en base, jamais son fichier.

- Aucun programme ne supprime, ne renomme ni ne remplace de fichier, sauf les fichiers que MachinCast crée lui-même (socket d'état, fichiers temporaires des sorties, fichier de démarrage de `Machin dev`). Chacune de ces lignes porte, sur la ligne ou celle du dessus, le commentaire `fichier de MachinCast :` suivi du fichier concerné.
- Un scénario de [`protection.feature`](../../tests/features/protection.feature) refuse, dans `src/`, `bin/Machin` et `install.sh`, toute suppression, tout renommage ou tout remplacement sans cette justification (`machincast.protection.injustifiees`) : en Python, `.unlink(`, `.rmdir(`, `.rename(`, `os.remove`, `os.unlink`, `os.rmdir`, `os.removedirs`, `os.rename`, `os.renames`, `os.replace`, `shutil.rmtree` et `shutil.move` ; en bash, `rm`, `rmdir`, `mv`, `unlink` et `shred`. `Path.replace` ne se distingue pas de `str.replace` : il est interdit, on écrit `os.replace` avec la justification.
- Tout fichier écrit par MachinCast passe d'abord par `machincast.protection.verifier_ecriture`, qui lève `FichierSonoreProtege` pour un chemin à l'extension d'un fichier sonore (`EXTENSIONS_SONORES`, celles que l'indexeur enregistre). La configuration refuse aussi ces chemins pour `sorties.*` et `lecture.socket_etat`.
- Les scénarios de protection vérifient, octet par octet, taille et date de modification comprises, que les fichiers d'une banque restent intacts après chaque changement de leur entrée, l'indexation rapide, l'audit complet, la diffusion et la simulation.

## Exécutables

- Une nouvelle dépendance Python se déclare dans `pyproject.toml`, jamais en paquet apt `python3-*` : le venv n'utilise pas les paquets Python du système ([#51](https://github.com/dascritch/machincast/issues/51)).
- Tout exécutable s'appelle `Machin_<nom>` et est déclaré dans `pyproject.toml` (aucune compilation).
- Les binaires sans interface se lancent par convention via le wrapper `Machin` (voir [wrapper.md](wrapper.md)).
