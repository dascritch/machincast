# Poste de développement

[Guide du développement](README.md) › Poste de développement

Un poste installé par `install.sh` suffit pour lancer les tests : le compte n'a besoin d'aucun droit PostgreSQL particulier, puisqu'il est propriétaire de la base de test et endosse déjà les trois rôles. Les tests ne créent jamais de compte PostgreSQL et n'attribuent jamais de rôle.

En plus, installer les outils de développement et les dépendances de test ([#77](https://github.com/dascritch/machincast/issues/77)) :

```bash
./install.sh --dev
```

`--dev` fait tout ce que fait l'installation, puis ajoute les paquets apt `bats`, `shellcheck` et `desktop-file-utils` (pour `desktop-file-validate`, qui vérifie le raccourci de l'interface) et installe dans le venv les dépendances de test (`pip install --editable ".[dev]"` : pytest, pytest-bdd, pytest-qt, ruff, mypy). Il est relançable, et `./install.sh --dev --simulation` montre ce qu'il fera. À la main, c'est l'équivalent de :

```bash
sudo apt install bats shellcheck desktop-file-utils
.venv/bin/pip install --editable ".[dev]"
```

Deux commandes du wrapper servent ensuite :

- **`Machin dev`** ouvre un nouveau shell dans le répertoire de MachinCast, environnement virtuel activé, avec l'invite `(MachinCast dev)`. Le `.bashrc` du compte est lu. `exit` en sort et ramène au shell de départ. Un programme ne peut pas activer le venv du shell qui l'a lancé : c'est pourquoi un nouveau shell s'ouvre.
- **`Machin dev-test`** lance toutes les vérifications, depuis le répertoire de MachinCast, avec les outils du venv, sans qu'il soit activé : `ruff check`, `ruff format --check` (tous deux sans cache), `mypy --strict`, `shellcheck`, `pytest` puis `bats`. Chacun est lancé, même après l'échec d'un précédent. À la fin, un bilan donne le résultat de chaque outil (`réussi`, `échec (code N)` ou `absent`). Le code de sortie est 0 si tous ont réussi, 1 sinon.

Sans `--dev`, ces deux commandes restent disponibles : il manque alors un outil ou le venv, et le message nomme ce qui manque et propose `./install.sh --dev` (code 1 pour `dev-test` quand un outil manque, 127 sans venv).

Les tests se lancent aussi un par un, depuis `Machin dev` ou après avoir activé le venv :

```bash
. .venv/bin/activate
pytest
bats tests/wrapper
```

Les tests lisent `tests/configuration-test.toml`, qui désigne la base de test `machincast_test`, celle du modèle de configuration. Ils ne touchent jamais à la base de production. Si `base.test` porte un autre nom dans `machincast.toml`, copier `tests/configuration-test.toml` dans le répertoire de MachinCast, y changer `base.test`, et désigner cette copie par la variable `MACHINCAST_CONFIG_TEST` :

```bash
cp tests/configuration-test.toml configuration-test-locale.toml   # puis y changer base.test
MACHINCAST_CONFIG_TEST=configuration-test-locale.toml pytest
```

Si PostgreSQL est injoignable, ou si le compte n'endosse pas les trois rôles, les scénarios de base de données sont ignorés avec la commande à lancer.

Sans `install.sh`, préparer la base de test à la main avec les étapes 2, 4 et 5 de [Installer à la main](../../INSTALL.md#installer-à-la-main), en ne créant que la base `machincast_test`. Les commandes de développement sont résumées dans [CLAUDE.md](../../CLAUDE.md), et les règles du projet dans [doc/regles](../regles/developpement.md).

## Captures d'écran du guide de l'antenne

Le [guide de l'antenne](../utilisateur/README.md) montre les écrans de l'interface ([#128](https://github.com/dascritch/machincast/issues/128)). Ses captures, dans `doc/captures`, se refont d'une commande, après un changement d'écran :

```bash
Machin dev-captures                   # dans doc/captures
Machin dev-captures /tmp/essai        # ailleurs, pour comparer
```

- **Base de démonstration** : la commande vide la **base de test** de la configuration des tests, la remplit d'une radio de démonstration, « Radio Exemple », puis ouvre l'interface hors de l'écran, sans fenêtre visible, le mercredi 21 octobre 2026 à 09:41:30. Elle n'ouvre jamais la base de production, et ses fichiers sonores sont des copies d'un fichier de test, dans le répertoire temporaire `machincast-demonstration`.
- **Reproductible** : mêmes données, même heure, même style Qt (Fusion), même taille de fenêtre (1280 × 800) : seule une modification des écrans change les images.
- **Liste** : les captures sont nommées dans `CAPTURES`, dans `tests/captures.py`. Une capture ajoutée doit être citée par le guide de l'antenne, et une image de `doc/captures` doit être une capture de la commande : les scénarios de `captures.feature` le vérifient.
- **Relire** les images avant de les livrer : une capture est un écran tel que l'utilisateur le verra, défauts compris.
