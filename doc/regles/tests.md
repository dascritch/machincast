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
- Les tests ne créent jamais de compte PostgreSQL et n'attribuent jamais de rôle ([PR #72](https://github.com/dascritch/machincast/pull/72)). Le compte qui les lance doit déjà endosser les trois rôles de MachinCast (`WITH INHERIT FALSE, SET TRUE`), comme après `install.sh`, sans aucun droit particulier sur le serveur. Sinon, `base_vide` ignore les scénarios de base en indiquant la commande `postgres` à lancer (`CLAUDE.md`).
- Entre deux tests, les tables sont **purgées** (`TRUNCATE … RESTART IDENTITY`). Chaque test recrée les entrées dont il a besoin, dans la fonction ou dans la classe de test. Aucun test ne dépend des données d'un autre.

## Fichiers sonores

- Les fichiers sonores de test sont versionnés dans `tests/fichiers-sonores/` : une seconde de sinusoïde en mono, la plus petite taille utile (5 secondes au plus), un fichier sain par format de la spec, AAC brut (`sain.aac`) compris (revue de [PR #65](https://github.com/dascritch/machincast/pull/65)). Les fichiers `sain.*` n'ont aucun tag ; les fichiers `tags.*` portent `tests.sons.TAGS_DE_TEST`, sauf en AIFF où GStreamer ne sait pas écrire de tags ([#8](https://github.com/dascritch/machincast/issues/8)).
- Les étapes partagées par plusieurs fonctionnalités (fichiers, sonores en base, passage de l'indexeur) sont dans `tests/etapes_indexation.py`, chargé comme greffon par `tests/conftest.py`.
- Un scénario en copie un dans son répertoire temporaire (`tests.sons.copie_de_test`), puis peut le tronquer ou le corrompre de façon déterministe ; le dépôt n'est jamais modifié.
- Pour les régénérer, avec les encodeurs GStreamer : `python -m tests.sons`.

## Hasard et temps

- Tout tirage aléatoire passe par un `random.Random` reçu en paramètre, créé par `machincast.hasard.creer_hasard(graine)` : même graine, mêmes tirages.
- L'heure courante passe par une `machincast.horloge.Horloge` reçue en paramètre : `HorlogeSysteme` en production, `HorlogeFixe` dans les tests, que le test fait avancer avec `avancer()`. Les heures ont toujours un fuseau.
- Un scénario de [`tests/features/socle.feature`](../../tests/features/socle.feature) refuse, dans `src/`, tout appel direct à `datetime.now()`, `time.time()` ou au module `random` en dehors de ces deux modules.

## Wrapper

- Les tests bats sont dans `tests/wrapper` et se lancent par `bats tests/wrapper` (bats ≥ 1.5).
- Ils copient le wrapper dans un projet factice dont le venv ne contient que des bouchons des binaires, et placent un bouchon de `journalctl` en tête du `PATH` (`tests/wrapper/aide_test.bash`) : ils ne lancent jamais la diffusion ni ne lisent le journal système.
- Les tests qui demandent les vrais binaires sont ignorés si le venv du dépôt (`.venv`) n'existe pas.

## Configuration

Les tests utilisent leur propre fichier de configuration, passé par le paramètre de configuration du wrapper ou du binaire, jamais `machincast.toml`. Un binaire lancé sans `--config` lirait le `machincast.toml` du dépôt, donc la base de production : aucun test ne lance un binaire sans `--config`. Les scénarios du fichier par défaut appellent `machincast.cli.lancer` en remplaçant `machincast.configuration.REPERTOIRE_PROJET` par un répertoire temporaire ([#76](https://github.com/dascritch/machincast/issues/76)).

`tests/configuration-test.toml` nomme comme base de production une base qui n'existe pas, différente de celle du modèle `machincast.exemple.toml` : un scénario de `socle.feature` le vérifie. Un scénario qui lance un binaire avec une configuration valide lui donne une socket PostgreSQL qui n'existe pas : le binaire ne peut joindre aucune base, et surtout pas la base de production que nomme cette configuration. Les scénarios qui ont besoin de la base appellent les fonctions Python avec une connexion à la base de test.

## Audio

Les tests du binaire lecture n'utilisent pas de sortie sonore réelle : la configuration de test choisit la sortie `factice` (élément GStreamer `fakesink`), ou le mode simulation. `machincast.audio.jouer_son_de_test` vérifie qu'un son traverse une sortie jusqu'au bout.
