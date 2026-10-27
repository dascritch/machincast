# Règles — Tests

À lire avant d'écrire ou de lancer un test.

## Outils

| Partie | Outil |
| --- | --- |
| Binaires Python (lecture, indexation) | pytest + pytest-bdd (scénarios Gherkin) |
| Interface graphique | pytest-qt |
| Wrapper `Machin` | bats |

Les scénarios Gherkin sont écrits en français (`# language: fr`).

## Poste de test

- La suite de tests tourne sur **Ubuntu 26.04 LTS**, la cible, avec sa version de GStreamer, la 1.28 ([#284](https://github.com/dascritch/machincast/issues/284)) : les défauts de GStreamer changent d'une version à l'autre, et un résultat obtenu sur une autre version ne vaut pas pour la cible. Le scénario « GStreamer et ses greffons sont au moins dans la version vérifiée », de `installation.feature`, échoue sur un poste plus ancien.
- Un compte rendu de test ou de mesure (ticket, PR, commentaire) donne la version d'Ubuntu et celle de GStreamer du poste.
- Un défaut de GStreamer se mesure hors du code de MachinCast, avec `python -m tests.mesures_gstreamer` ([poste de développement](../developpement/poste.md#mesurer-les-blocages-de-gstreamer)), avant d'écrire ou de retirer un contournement.

## Base de test

- Les tests lisent `tests/configuration-test.toml`, ou le fichier désigné par la variable d'environnement `MACHINCAST_CONFIG_TEST` ([#5](https://github.com/dascritch/machincast/issues/5)).
- Les tests n'utilisent **jamais** la base de production, uniquement la base de test. Une configuration dont `base.test` vaut `base.production` est refusée au chargement, et `tests/base_test.py` arrête la session s'il rencontre ce cas.
- Un scénario qui a besoin de la base demande la fixture `base_vide` (`tests/conftest.py`) : base migrée, tables vides, identifiants remis à 1. Le schéma est recréé une fois par session, puis seulement purgé ([#280](https://github.com/dascritch/machincast/issues/280)) : yoyo ne repasse que s'il manque une migration, après un scénario qui en a annulé, et les tables se vident par `DELETE`, dans l'ordre de `tests.base_test.ORDRE_DE_PURGE`, dix fois plus vite qu'un `TRUNCATE`. Une table ajoutée à `machincast.base.TABLES` s'y ajoute aussi : un scénario de `schema.feature` le vérifie.
- Le schéma de la base de test est appliqué par les mêmes migrations yoyo que la production (voir [base-de-donnees.md](base-de-donnees.md)).
- Les tests ne créent jamais de compte PostgreSQL et n'attribuent jamais de rôle ([PR #72](https://github.com/dascritch/machincast/pull/72)). Le compte qui les lance doit déjà endosser les trois rôles de MachinCast (`WITH INHERIT FALSE, SET TRUE`), comme après `install.sh`, sans aucun droit particulier sur le serveur. Sinon, `base_vide` ignore les scénarios de base en indiquant la commande `postgres` à lancer (`CLAUDE.md`). Un compte superutilisateur endosse les rôles sans autorisation : les scénarios de base passent, mais celui de `roles.feature` qui vérifie les autorisations du compte échoue, en expliquant pourquoi et en donnant les commandes à lancer.
- Un ordre attendu ne dépend jamais de la collation de la base de test, qui suit la langue du poste : en `C.UTF-8`, « Élodie » vient après « Les Gaufres » ; en français, avant ([#134](https://github.com/dascritch/machincast/issues/134)). Une liste rangée en base ne compare pas, dans un scénario, des noms qui commencent par une lettre accentuée, ou qui ne diffèrent que par les majuscules. Pour vérifier, une configuration de test peut désigner une base créée en collation française : `CREATE DATABASE … TEMPLATE template0 LOCALE_PROVIDER icu ICU_LOCALE 'fr-FR' LOCALE 'C.UTF-8'`, puis `MACHINCAST_CONFIG_TEST`.
- Entre deux tests, les tables sont **purgées** (`DELETE`, puis les séquences des identifiants remises à 1). Chaque test recrée les entrées dont il a besoin, dans la fonction ou dans la classe de test. Aucun test ne dépend des données d'un autre.

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
- Tout tri ou toute comparaison de texte dans un test fixe la locale à `C` (`LC_ALL=C sort`) : les tests donnent le même résultat en français, en anglais ou en `C` ([#79](https://github.com/dascritch/machincast/issues/79)).
- Ils copient le wrapper dans un projet factice dont le venv ne contient que des bouchons des binaires, et placent un bouchon de `journalctl` en tête du `PATH` (`tests/wrapper/aide_test.bash`) : ils ne lancent jamais la diffusion ni ne lisent le journal système.
- Les tests qui demandent les vrais binaires sont ignorés si le venv du dépôt (`.venv`) n'existe pas.
- `tests/wrapper/dev.bats` vérifie `Machin dev` et `Machin dev-test` avec des bouchons des outils, qui notent leurs appels ; `Machin dev` y reçoit ses commandes sur l'entrée standard, avec un `HOME` temporaire ([#77](https://github.com/dascritch/machincast/issues/77)).
- `tests/captures.py` ([#128](https://github.com/dascritch/machincast/issues/128)) est l'outil de `Machin dev-captures`, pas un test : il remplit la base de test d'une démonstration et capture l'interface hors de l'écran. `captures.feature` vérifie qu'il produit une image par capture, et que `doc/captures` et le guide de l'antenne les ont toutes, et seulement elles.
- Toutes les vérifications d'un coup : `Machin dev-test`, qui lance ruff sans cache (un cache peut masquer un import mal rangé quand un module est créé après coup).

## Configuration

Les tests utilisent leur propre fichier de configuration, passé par le paramètre de configuration du wrapper ou du binaire, jamais `machincast.toml`. Un binaire lancé sans `--config` lirait le `machincast.toml` du dépôt, donc la base de production : aucun test ne lance un binaire sans `--config`. Les scénarios du fichier par défaut appellent `machincast.cli.lancer` en remplaçant `machincast.configuration.REPERTOIRE_PROJET` par un répertoire temporaire ([#76](https://github.com/dascritch/machincast/issues/76)).

`tests/configuration-test.toml` nomme comme base de production une base qui n'existe pas, différente de celle du modèle `machincast.exemple.toml` : un scénario de `socle.feature` le vérifie. Un scénario qui lance un binaire avec une configuration valide lui donne une socket PostgreSQL qui n'existe pas : le binaire ne peut joindre aucune base, et surtout pas la base de production que nomme cette configuration. Les scénarios qui ont besoin de la base appellent les fonctions Python avec une connexion à la base de test.

## Interface graphique

- Les écrans s'ouvrent avec pytest-qt (fixture `qtbot`), hors de l'écran du poste : `tests/conftest.py` règle `QT_QPA_PLATFORM=offscreen` avant toute création d'application Qt ([#23](https://github.com/dascritch/machincast/issues/23)). Aucune fenêtre ne s'ouvre pendant les tests, même sur un poste avec affichage.
- `QTest` ne sait taper que l'ASCII : une étape qui tape du texte insère les lettres accentuées directement dans le champ (`insert`), comme une méthode de saisie.
- Une attente se fait par `qtbot.waitUntil`, avec un délai : jamais de `sleep`. Les étapes « bientôt » d'un scénario attendent ainsi un état publié par la socket.
- Une attente attend un signal, pas la fin d'un délai ([#280](https://github.com/dascritch/machincast/issues/280)) : une demande ignorée sur la socket se voit dans le journal du binaire (`caplog`), un tube nommé se ferme quand la vérification abandonne le décodage. Seule l'absence d'un événement (« reste », « toujours », « aucun ») se vérifie après un court délai fixe. Un scénario ne dure que le temps de ce qu'il vérifie : une simulation de quelques minutes suffit à montrer qu'aucun fichier n'est touché.
- Une fenêtre se libère à la fin de son scénario : pytest-qt la ferme et demande sa suppression (`deleteLater`), que la fixture `interface` fait aussitôt (`QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)`). Sans elle, les fenêtres des scénarios qui n'attendent rien s'accumulent, et le premier scénario qui attend les supprime toutes, au détriment de son délai ([#262](https://github.com/dascritch/machincast/issues/262)). Un widget de l'interface sans onglet ni fenêtre appartient à la fenêtre, caché, pour ne pas lui survivre.
- Les fenêtres de dialogue des fiches (`machincast.interface.dialogues`) sont remplacées par le fixture `interface` (`tests/etapes_interface.py`) : il donne les réponses du scénario et note chaque question posée. Les vraies fenêtres sont vérifiées à part (`dialogues.feature`) : un minuteur y clique dès que la fenêtre modale est ouverte, et la ferme si l'étape échoue. Les boutons standard de Qt s'y trouvent par leur rôle, puisque les tests ne chargent pas la traduction `qtbase_fr`.
- Un dépôt depuis le navigateur de fichiers se simule en envoyant à la zone de la liste (`viewport()`) les événements `QDragEnterEvent`, `QDragMoveEvent` puis `QDropEvent`, avec Maj enfoncée : l'action proposée est alors le déplacement, que l'écran doit changer en copie. Les fichiers déposés sont créés dans le répertoire temporaire du scénario, noté « …/ » dans les scénarios ; un vrai glisser à la souris ne se simule pas hors écran.
- Le test d'un flux depuis l'interface se vérifie sur le serveur de flux local (`tests/flux.py`) : il compte ses connexions ouvertes, et un flux « avare » n'envoie qu'une demi-seconde de son, moins que ce qu'attend le test. Le délai du test se raccourcit en remplaçant `essai_flux.DELAI`. Une fonction d'étape ne commence jamais par `test` : pytest la prendrait pour un test.
- Les étapes partagées par plusieurs écrans (fenêtre, onglets, listes, questions) sont dans `tests/etapes_interface.py`, chargé comme greffon ; celles d'un écran sont dans son fichier de test.
- La socket d'état d'un scénario est un vrai serveur du binaire lecture (`machincast.lecture.etat.SocketEtat`), ouvert dans le répertoire temporaire du scénario, qui y publie les états comme la diffusion.
- Un scénario qui lance le binaire `Machin_interface` lui donne une configuration dont la socket PostgreSQL n'existe pas : il s'arrête avec le code 1, sans fenêtre, puisque le processus hérite de `QT_QPA_PLATFORM=offscreen`. La fenêtre d'erreur se vérifie en appelant `main` dans le processus des tests, sa méthode `exec` remplacée : aucune fenêtre modale n'attend un clic.

## Audio

Les tests du binaire lecture n'utilisent pas de sortie sonore réelle : la configuration de test choisit la sortie `factice` (élément GStreamer `fakesink`), ou le mode simulation, qui n'ouvre aucune sortie ([#21](https://github.com/dascritch/machincast/issues/21)). `machincast.audio.jouer_son_de_test` vérifie qu'un son traverse une sortie jusqu'au bout.
