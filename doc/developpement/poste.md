# Poste de développement

[Guide du développement](README.md) › Poste de développement

**Le poste de développement et de test est en Ubuntu 26.04 LTS**, la cible de MachinCast, avec sa version de GStreamer, la 1.28 ([#284](https://github.com/dascritch/machincast/issues/284)). Les défauts de GStreamer dépendent de sa version : un résultat de test, ou une mesure, obtenu sur une autre version ne vaut pas pour la cible. Un scénario de `installation.feature` échoue sur un poste dont GStreamer est plus ancien. Un compte rendu de test, un ticket ou une PR donne la version d'Ubuntu et celle de GStreamer du poste (`gst-inspect-1.0 --version`).

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

## Mesurer les blocages de GStreamer

Certains défauts de GStreamer, sur l'AIFF surtout, ont demandé des contournements : décodage repris au démarrage ([#280](https://github.com/dascritch/machincast/issues/280)), voie bloquée remplacée ([#281](https://github.com/dascritch/machincast/issues/281)), lecteur `playbin3` ([#284](https://github.com/dascritch/machincast/issues/284)). Leur fréquence se mesure hors du code de MachinCast, à refaire à chaque mise à jour de GStreamer, avant d'écrire ou de retirer un contournement :

```bash
.venv/bin/python -m tests.mesures_gstreamer                  # 1 000 essais par pipeline et par format
.venv/bin/python -m tests.mesures_gstreamer -n 200 -j 4      # quatre mesures à la fois, sous charge
.venv/bin/python -m tests.mesures_gstreamer --synchrone --pipelines playbin playbin3 --formats aiff   # en temps réel
```

Chaque essai décode un fichier de `tests/fichiers-sonores`, par le pipeline de la vérification (`decodebin`), ses variantes (`queue ! decodebin`, `decodebin3`) ou un lecteur (`playbin`, `playbin3`). Le bilan donne le poste et la version de GStreamer, puis un tableau Markdown des essais sains, bloqués au démarrage, bloqués en cours, en erreur, ou qui ne rendent plus la main ; puis, pour chaque pipeline, s'il rend la main sur un fichier dont la lecture se bloque (tube nommé). Le tableau se recopie tel quel dans un ticket.

Mesures d'Ubuntu 26.04 LTS, GStreamer 1.28.2 ([#284](https://github.com/dascritch/machincast/issues/284)), en AIFF, les autres formats ne se bloquant pas au démarrage :

| Pipeline | Bloqués au démarrage | Remarque | Décision |
| --- | --- | --- | --- |
| `decodebin` | 44 sur 1 000 | rend la main sur un tube | gardé pour la vérification, avec ses six tentatives |
| `queue ! decodebin` | 0 sur 1 000 | bloqués en cours : 9 WAV, 1 M4A et 1 AIFF sur 1 000 | écarté |
| `decodebin3` | 0 sur 1 000 | ne rend pas la main sur un tube | écarté |
| `playbin` | 62 sur 1 000 ; 36 sur 300 en temps réel | | remplacé |
| `playbin3` | 0 sur 1 000 ; 0 sur 300 en temps réel | | lecteur de l'antenne et de la pré-écoute |

Au vu de ces mesures, **l'AIFF n'est plus pris en charge** ([#284](https://github.com/dascritch/machincast/issues/284)) : l'indexation l'ignore, la documentation ne le cite plus parmi les formats, et la suite de tests ne le décode plus. `tests/fichiers-sonores/sain.aiff` ne sert qu'à ces mesures. Les contournements restent, pour les AIFF déjà en base. Si une version de GStreamer ne bloque plus l'AIFF, ces mesures le montreront : son retour passera par un ticket.

### État des signalements

Au 27 octobre 2026, le défaut est référencé dans le suivi de MachinCast : [#236](https://github.com/dascritch/machincast/issues/236) (exemples AIFF des tests mis de côté sous GStreamer 1.24), [#280](https://github.com/dascritch/machincast/issues/280) (décodage repris), [#281](https://github.com/dascritch/machincast/issues/281) (voie bloquée remplacée) et [#284](https://github.com/dascritch/machincast/issues/284) (mesures sur 1.28 et passage à `playbin3`).

**Aucun signalement de ce défaut précis**, un démarrage d'AIFF bloqué dans `decodebin` ou `playbin`, n'a été trouvé chez GStreamer, chez une distribution ou dans une application. Les recherches portaient sur le suivi de GStreamer, Launchpad (Ubuntu), le Bugzilla de Red Hat (Fedora) et les dépôts d'applications GStreamer. Les signalements voisins :

- **Même famille de défaut, autres éléments** : le lecteur de musique [Ferrous](https://github.com/Tiaxi/ferrous) (KDE, Rust et Qt 6) constate des démarrages bloqués au hasard, sous charge, dans `parsebin`, donc par `uridecodebin3` et `playbin3`, sur des MP3 : 49 sur 3 600 essais avec GStreamer 1.24.2, 10 sur 600 avec 1.28.8 ([ticket 223 de Ferrous](https://github.com/Tiaxi/ferrous/issues/223)). Il les contourne en relançant le morceau ([PR 228 de Ferrous](https://github.com/Tiaxi/ferrous/pull/228)). La correction de GStreamer est sur la branche principale ([commit 51cb58de](https://gitlab.freedesktop.org/gstreamer/gstreamer/-/commit/51cb58deb133e1b7ffca69189377684d81666068), [MR !12700](https://gitlab.freedesktop.org/gstreamer/gstreamer/-/merge_requests/12700)), et sur la branche 1.28 après la 1.28.8 ([commit 228f1734](https://gitlab.freedesktop.org/gstreamer/gstreamer/-/commit/228f1734cd1f89039ef46706750e3e1af0629983), [MR !12716](https://gitlab.freedesktop.org/gstreamer/gstreamer/-/merge_requests/12716)) : Ubuntu 26.04, en 1.28.2, ne l'a pas. Une autre course de `parsebin` et `decodebin3`, corrigée pour GStreamer 1.26 ([MR !7609](https://gitlab.freedesktop.org/gstreamer/gstreamer/-/merge_requests/7609)), touchait aussi Ubuntu 24.04 ([PR 222 de Ferrous](https://github.com/Tiaxi/ferrous/pull/222)). Nos mesures ne bloquent pas `playbin3` : rien ne montre que ce soit le même défaut.
- **`aiffparse`, plus anciens** : `aiffparse` est dans les greffons « bad », ceux que GStreamer juge encore peu éprouvés. Plusieurs de ses défauts ont été corrigés en 2013, pour gst-plugins-bad 1.1.4 ([notes de version](https://gstreamer.freedesktop.org/releases/gst-plugins-bad/1.1.4.html) : GNOME [705674](https://bugzilla.gnome.org/show_bug.cgi?id=705674) « aiffparse broken », [705675](https://bugzilla.gnome.org/show_bug.cgi?id=705675), [705993](https://bugzilla.gnome.org/show_bug.cgi?id=705993)). Le convertisseur SoundConverter a signalé la même année « AIFF and FLAC break GStreamer pipeline » ([Launchpad, bogue 1121132](https://bugs.launchpad.net/soundconverter/+bug/1121132)). Ces défauts sont différents : ils ne bloquaient pas un démarrage sur vingt-cinq.
- **Notes de version de GStreamer 1.28.3 à 1.28.8** : aucune ne corrige `aiffparse`, ni un blocage au démarrage de `decodebin` ou `playbin`.

Le défaut reste à signaler chez GStreamer, avec `tests/mesures_gstreamer.py` pour le reproduire. Un signalement ouvert depuis, chez GStreamer ou ailleurs, s'ajoute à cette liste.
