# Règles — Tests

À lire avant d'écrire ou de lancer un test.

## Outils

| Partie | Outil |
| --- | --- |
| Binaires Python (lecture, indexation) | pytest + pytest-bdd (scénarios Gherkin) |
| Interface graphique | pytest-qt |
| Wrapper `Machin` | bats |

Les scénarios Gherkin sont écrits en français (`# language: fr`).

## Base de test

- Les tests n'utilisent **jamais** la base de production, uniquement la base de test.
- Le schéma de la base de test est appliqué par les mêmes migrations yoyo que la production (voir [base-de-donnees.md](base-de-donnees.md)).
- Entre deux tests, les tables sont **purgées**. Chaque test recrée les entrées dont il a besoin, dans la fonction ou dans la classe de test. Aucun test ne dépend des données d'un autre.

## Hasard et temps

- Tout tirage aléatoire passe par une graine (seed) injectable, pour des résultats reproductibles.
- L'heure courante est injectable : aucun test ne dépend de l'horloge réelle.

## Configuration

Les tests utilisent leur propre fichier de configuration, passé par le paramètre de configuration du wrapper ou du binaire, jamais `machincast.toml`.

## Audio

Les tests du binaire lecture n'utilisent pas de sortie sonore réelle : sortie factice GStreamer ou mode simulation.
