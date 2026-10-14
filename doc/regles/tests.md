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

- Les tests lisent `tests/configuration-test.toml`, ou le fichier désigné par la variable d'environnement `MACHINCAST_CONFIG_TEST` ([#5](https://github.com/dascritch/machincast/issues/5)).
- Les tests n'utilisent **jamais** la base de production, uniquement la base de test. Une configuration dont `base.test` vaut `base.production` est refusée au chargement, et `tests/base_test.py` arrête la session s'il rencontre ce cas.
- Un scénario qui a besoin de la base demande la fixture `base_vide` (`tests/conftest.py`) : base migrée, tables vides, identifiants remis à 1. Le schéma est recréé une fois par session, puis seulement purgé.
- Le schéma de la base de test est appliqué par les mêmes migrations yoyo que la production (voir [base-de-donnees.md](base-de-donnees.md)).
- Entre deux tests, les tables sont **purgées** (`TRUNCATE … RESTART IDENTITY`). Chaque test recrée les entrées dont il a besoin, dans la fonction ou dans la classe de test. Aucun test ne dépend des données d'un autre.

## Hasard et temps

- Tout tirage aléatoire passe par un `random.Random` reçu en paramètre, créé par `machincast.hasard.creer_hasard(graine)` : même graine, mêmes tirages.
- L'heure courante passe par une `machincast.horloge.Horloge` reçue en paramètre : `HorlogeSysteme` en production, `HorlogeFixe` dans les tests, que le test fait avancer avec `avancer()`. Les heures ont toujours un fuseau.
- Un scénario de [`tests/features/socle.feature`](../../tests/features/socle.feature) refuse, dans `src/`, tout appel direct à `datetime.now()`, `time.time()` ou au module `random` en dehors de ces deux modules.

## Configuration

Les tests utilisent leur propre fichier de configuration, passé par le paramètre de configuration du wrapper ou du binaire, jamais `machincast.toml`.

## Audio

Les tests du binaire lecture n'utilisent pas de sortie sonore réelle : la configuration de test choisit la sortie `factice` (élément GStreamer `fakesink`), ou le mode simulation. `machincast.audio.jouer_son_de_test` vérifie qu'un son traverse une sortie jusqu'au bout.
