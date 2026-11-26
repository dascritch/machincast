# Règles — Développement

À lire avant toute modification de code.

## Cycle de travail

1. Chaque fonctionnalité part d'un ticket GitHub Issues, sur une branche tirée de `preprod` ([Branches](#branches)).
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

## Branches

Trois branches protégées, sans commit direct ([#480](https://github.com/dascritch/machincast/issues/480)) :

| Branche | Ce qu'elle porte | Ce qui y entre |
| --- | --- | --- |
| `preprod` | Les tickets terminés, en attente de la prochaine release. | Les PR des branches de ticket. |
| `qualif` | La release candidate, qui tourne une semaine à l'antenne. | Une PR de `preprod` vers `qualif`, par release ; les PR des corrections de la qualification. |
| `main` | La dernière version publiée, taguée. | Une PR de `qualif` vers `main`, après la semaine de qualification. |

- **Un ticket** part de `preprod`, sur une branche `dev/<numéro>-<sujet>`, et y revient par une PR.
	Sa PR ne lance que les scénarios du ticket, jamais la suite complète ([Quels tests lancer](tests.md#quels-tests-lancer)).
- **Une release candidate** passe de `preprod` à `qualif` par une PR, qui s'accompagne de la suite complète, de la documentation à jour, de sa traduction anglaise et de ses captures d'écran refaites ([Publier une version](../developpement/release.md)).
- **La qualification** dure une semaine : la release candidate tourne à l'antenne depuis `qualif`.
	Un défaut trouvé pendant cette semaine se corrige par un ticket dont la branche part de `qualif` et y revient : la release candidate n'embarque aucune nouvelle fonctionnalité de `preprod`.
	Sa branche s'appelle `fix/<numéro>-<sujet>`, et sa PR, vers `qualif`, ne lance que les scénarios du ticket, comme celle d'un ticket vers `preprod` ([#491](https://github.com/dascritch/machincast/issues/491)).
	La release candidate étant déjà traduite, sa documentation se met à jour en français **et** en anglais, `doc/en` et les documents de premier niveau compris, et le ticket s'ajoute à la section de la version dans `RELEASE.fr.md` et `RELEASE.md`.
	La correction revient ensuite sur `preprod` par une PR de `qualif` vers `preprod`, et la semaine reprend.
	Puis une PR de `qualif` vers `main` la livre, et elle est taguée sur `main`.
- **Entre branches protégées**, les PR de `preprod` vers `qualif`, de `qualif` vers `main` et de `qualif` vers `preprod` se mergent par un commit de fusion, « Create a merge commit » sur GitHub, jamais par « Rebase and merge » : les commits gardent leurs identifiants d'une branche à l'autre, et une correction de la qualification revient sur `preprod` sans ramener en double ceux de la release ([#491](https://github.com/dascritch/machincast/issues/491)).
	Les PR d'un ticket, vers `preprod` ou vers `qualif`, peuvent se merger comme avant.

## Definition of done

Un ticket n'est terminé que si :

- ses scénarios BDD ont été écrits d'abord, vus en échec, puis réussis ;
- `bin/Machin dev-test --scenarios` passe, avec les fonctionnalités du ticket et celles qui utilisent ses modules, plus `wrapper` si le wrapper, `install.sh` ou la configuration change ; la PR dit lesquelles ont tourné ([Quels tests lancer](tests.md#quels-tests-lancer), [#408](https://github.com/dascritch/machincast/issues/408)).
	La suite complète revient au ticket « Tests, revue de code et performances », tous les 10 tickets fermés, et à la PR de chaque release candidate, de `preprod` vers `qualif` ([Branches](#branches)) ;
- ses fonctions et ses actions externes sont documentées pour les humains ([#71](https://github.com/dascritch/machincast/issues/71)) : tout ce qu'un utilisateur ou un administrateur voit ou déclenche, c'est-à-dire les commandes, options et codes de retour, les clés de configuration, les fichiers produits, les messages affichés et les effets sur le système (base, journal, sortie audio, fichiers sonores) ;
- la spécification et les règles de développement sont à jour.

La documentation pour les humains va dans le guide de son public ([#128](https://github.com/dascritch/machincast/issues/128)), mise à jour dans le commit du ticket, distincte de la spécification et de ces règles :

- **Équipe de l'antenne** : le [guide de l'antenne](../utilisateur/README.md), `doc/fr/utilisateur` : le métier de l'antenne et l'interface graphique, en mots simples, sans commande à taper ni détail technique (clé de configuration, socket, chemin de fichier produit).
	Un écran nouveau ou changé a sa capture, refaite par `Machin dev-screenshots` ([Poste de développement](../developpement/poste.md#captures-décran-du-guide-de-lantenne)) et relue avant d'être livrée.
- **Administrateur du poste** : [`INSTALL.md`](../../../INSTALL.fr.md) pour l'installation, et le [guide d'administration](../administration/README.md), `doc/fr/administration`, pour les commandes, leurs options et codes de sortie, la configuration, les fichiers produits, les messages et les droits.
- **Développeur** : le [guide du développement](../developpement/README.md), `doc/fr/developpement`, la spécification et ces règles.

**Langues** ([#352](https://github.com/dascritch/machincast/issues/352), [#355](https://github.com/dascritch/machincast/issues/355)) : la documentation française est la source, celle qu'un ticket met à jour.
Les documents de premier niveau (`README.md`, `INSTALL.md`, `TROUBLESHOOTING.md`, `CONTRIBUTING.md`, `RELEASE.md`) sont en anglais, chacun avec sa source française, `*.fr.md` ; chacun mène à l'autre par un lien en tête.
`doc/` a un répertoire par langue : `doc/fr/`, la source, et `doc/en/`, sa traduction.
`doc/en/` ne traduit que les guides humains, le [guide de l'antenne](../utilisateur/README.md) (`utilisateur`) et le [guide d'administration](../administration/README.md) (`administration`), sous les mêmes noms de pages ; leurs captures et leurs images restent celles de `doc/fr/`.
La spécification, l'architecture, ces règles et le guide du développement restent en français : un document anglais qui les cite mène à `doc/fr/`, avec la mention « (French) ».
Un ticket ne met à jour que les sources françaises ; la traduction anglaise, des documents de premier niveau comme de `doc/en/`, ne se refait qu'à la préparation d'une release ([Publier une version](../developpement/release.md)).
Un scénario de [`documentation.feature`](../../../tests/features/documentation.feature) vérifie les deux versions de chaque document de premier niveau, et les liens de `doc/fr`.
`doc/` n'a que des répertoires de langue ; un fichier commun à toutes les langues, comme la bannière du README (`doc/banner.jpg`), reste à sa racine ([#461](https://github.com/dascritch/machincast/issues/461)).

**Langue du code** ([#359](https://github.com/dascritch/machincast/issues/359)) : les noms du code et des tests sont en anglais — paquets, modules, classes, fonctions, variables, fichiers `.ui` et leurs `objectName`, noms des fichiers de test et des `.feature`, clés et valeurs des formats échangés entre programmes (socket d'état, `music_metadata`, configuration).
Le vocabulaire suit celui du schéma ([#358](https://github.com/dascritch/machincast/issues/358)) : sonore → `sound`, banque → `bank`, événement → `event`, élément → `item`, fil musical → `background_programming`, secours → `fallback`, pré-écoute → `preview`, antenne → `on_air`, fiche → `card`, frise → `timeline`, blanc → `dead_air`.
Restent en français les commentaires et les docstrings, rédigés comme la documentation source, et le texte des scénarios (`# language: fr`).
Les textes montrés à l'utilisateur sont écrits en anglais et traduits ([messages et traductions](#messages-et-traductions)).
Un nom qui commence par `test` est réservé aux tests, que pytest ramasse : un outil des tests s'appelle `sample_…`.

**Une phrase par ligne** ([#445](https://github.com/dascritch/machincast/issues/445)) : la spécification, `doc/fr/spec.md`, et ces règles, `doc/fr/regles/*.md`, s'écrivent une phrase par ligne, pour qu'un diff ne montre que la phrase changée.
La suite d'un élément de liste s'indente d'une tabulation de plus que son tiret ; un saut de ligne simple ne change pas le rendu.
Un titre, une ligne de tableau et un bloc de code restent d'un seul tenant.
Les fichiers, leurs titres et leurs ancres ne changent pas.
Un scénario de [`documentation.feature`](../../../tests/features/documentation.feature) le vérifie (`tests.markdown.sentence_ends`, qui ne coupe ni dans le code, ni dans un lien, des parenthèses ou des guillemets, ni après une abréviation ou un numéro), et qu'aucune ligne ne dépasse 2 000 caractères.

Une même fonction peut paraître dans deux guides, chacun pour son public : l'onglet Simulation dans le guide de l'antenne, `Machin player --simulation` dans le guide d'administration.
Les scénarios de [`guide.feature`](../../../tests/features/guide.feature) échouent quand une option d'un programme manque au guide d'administration, ou un état d'un sonore, un verdict de vérification ou une clé de métadonnées au guide de l'antenne ([#74](https://github.com/dascritch/machincast/issues/74)) ; ceux de [`screenshots.feature`](../../../tests/features/screenshots.feature), quand une capture manque, ou n'est pas citée.

Le modèle de description de PR ([`.github/pull_request_template.md`](../../../.github/pull_request_template.md)) reprend ces points en cases à cocher, dont « documentation humaine à jour », cochées avant la demande de relecture.
Un scénario de [`documentation.feature`](../../../tests/features/documentation.feature) vérifie que cette section, le renvoi de `AGENTS.md` et la case du modèle de PR existent.

## Références aux tickets et aux PR

Toute référence à un ticket ou à une PR est un lien, jamais un numéro nu :

- en Markdown : `[#51](https://github.com/dascritch/machincast/issues/51)` ou `[PR #56](https://github.com/dascritch/machincast/pull/56)` ;
- dans un commentaire de code, une docstring ou un message : l'URL complète, par exemple `https://github.com/dascritch/machincast/issues/51`.

Un scénario ([`tests/features/references.feature`](../../../tests/features/references.feature)) refuse les références nues, partout, migrations comprises.

## Messages de commit

Format Conventional Commits.
Sous la première ligne, après une ligne vide : l'URL du ticket, puis à la ligne suivante le titre du ticket.

```
feat(lecture): bascule immédiate sur un événement prioritaire

https://github.com/dascritch/machincast/issues/123
Bascule sur un événement de priorité supérieure
```

Portées usuelles : `lecture`, `indexation`, `interface`, `wrapper`, `db`, `install`, `doc`.

## Corrections d'une PR ouverte

Une correction d'une PR ouverte, demandée en relecture ou trouvée ensuite, est un **nouveau commit** ([#131](https://github.com/dascritch/machincast/issues/131)).
Le relecteur voit ainsi ce qui a changé depuis sa dernière relecture.

- Jamais de `git commit --amend` : un commit déjà poussé n'est jamais modifié.
- Pour remettre la branche d'une PR à jour avec sa branche de base, `preprod` pour un ticket, `qualif` pour une correction de la qualification (par exemple après la fusion d'une autre PR qui touche les mêmes fichiers), `git rebase` sur elle, jamais un commit de fusion : chaque commit est rejoué tel quel, et un conflit se résout dans le commit qui le provoque.
	La branche se pousse alors avec `git push --force-with-lease`, jamais `--force`, qui écraserait un commit poussé entre-temps.
- Le message suit le format ci-dessus, lié au même ticket, avec le type qui convient : `fix` pour un défaut, `refactor`, `test` ou `docs` pour le reste.
	Par exemple :

```
fix(interface): le dépôt d'un fichier sonore n'est accepté que comme une copie

https://github.com/dascritch/machincast/issues/31
Écran de détails d'une banque
```

## Style de code

- Python pour tout le projet, typé strictement : `mypy --strict` doit passer.
- Linter et formateur : ruff.
- Jamais de `print` : les messages passent par `logging`, avec un journal par module (`logging.getLogger(__name__)`).
	Une erreur imprévue rattrapée se journalise par `log.exception`, qui garde son traceback : les formateurs de `machincast.log` l'écrivent sous la ligne ([#574](https://github.com/dascritch/machincast/issues/574)).
	`machincast.log.configured` envoie les informations sur la sortie standard, les anomalies (`warning`) et les erreurs (`error`) sur la sortie d'erreur ; chaque ligne commence par l'heure de son message, en ISO 8601 à la seconde, avec le décalage horaire du poste ([#253](https://github.com/dascritch/machincast/issues/253)), au lieu du nom de l'exécutable.
	Un scénario de [`base.feature`](../../../tests/features/base.feature) refuse tout `print` dans `src/` (revue de [PR #65](https://github.com/dascritch/machincast/pull/65)).
- Chaînes Python : f-strings (ou t-strings), jamais la notation `str % valeur`, même indirectement : un message de journal est une f-string (`log.error(f"base {nom} injoignable : {erreur}")`), un format de `logging` s'écrit avec `style="{"` ([#73](https://github.com/dascritch/machincast/issues/73)).
	Seule exception : les `%s` des requêtes SQL, qui sont des valeurs liées par psycopg et non du formatage de chaîne.
- Scripts bash (wrapper, autocomplétion, `install.sh`, tests bats) : `set -euo pipefail` pour un exécutable, et shellcheck doit passer.
	Une variable s'écrit toujours avec accolades, `"${RACINE}"` et jamais `"$RACINE"` ([#73](https://github.com/dascritch/machincast/issues/73)).
- Deux scénarios de [`base.feature`](../../../tests/features/base.feature) refusent la notation `%` dans le Python du dépôt et les variables bash sans accolades.
- Conditions (revue de [PR #100](https://github.com/dascritch/machincast/pull/100)) : dans une condition qui enchaîne `and` ou `or`, chaque opérande est entre parenthèses, par exemple `if (actif is not None) and (last.start is not None) and (self._has_started(actif, last.start)):`.
	Une longue condition se coupe avant chaque `and` ou `or`, une parenthèse par ligne.
- Code développé ([#340](https://github.com/dascritch/machincast/issues/340)) : le code se lit de haut en bas, une instruction à la fois, sans forme compacte à déplier de tête.
  - Pas d'expression conditionnelle, `a if b else c` : une valeur par défaut puis un `if`, `evenement = None` puis `if identifiant is not None: evenement = read_event(connexion, identifiant)`, ou un `if`/`else` développé.
  	Une valeur lue en base, qui peut être absente, se convertit par `machincast.conversion` : `text_or_none`, `integer_or_none`, `boolean_or_none`, `duration_or_none`, `list_or_none` ([#187](https://github.com/dascritch/machincast/issues/187)), jamais par une fonction `_text` réécrite dans le module.
  - Pas de `elif` : un `match`/`case`, un `return` qui sort de la fonction, ou un `if` dans le `else`.
  - Pas de compréhension, de liste, d'ensemble ou de dictionnaire, ni d'expression génératrice, `[s.title for s in sonores if s.active]`, `any(…)` sur un générateur compris : une boucle `for` développée, qui remplit la liste ou décide d'un booléen.
  	Un calcul qu'un `lambda` ou un `assert` faisait d'une traite devient une fonction nommée, qui dit ce qu'elle vérifie (`sound_shown()`, `_apart(cadre, autres)`), ou une boucle d'`assert`.
  - Pas de `continue` : une sous-fonction, dont un simple `return` dit qu'on passe à l'élément suivant, ou une condition développée autour de la suite de la boucle.
  	Une sous-fonction porte un nom qui dit ce qu'elle fait (`_readable_directory`, `_starts_on`), jamais un nom générique (`handle_x`).
  - Une variable porte un nom qui dit ce qu'elle contient (`kept_lines`, `skipped_days`), jamais un nom de passe (`chosen_2`, `p_list`).
- Complexité ([#439](https://github.com/dascritch/machincast/issues/439)) : ruff refuse une fonction de plus de 15 chemins (`C901`, `max-complexity` de `pyproject.toml`).
	Les fonctions imbriquées comptent dans celle qui les contient : une fonction qui en déclare plusieurs se découpe en fonctions de module ou en méthodes, chacune avec un nom qui dit ce qu'elle fait et ses données en paramètres.
	Ne pas relever le seuil pour faire passer une fonction : la découper.
- Signatures ([#441](https://github.com/dascritch/machincast/issues/441)) : un appel se lit sans ouvrir la définition.
	Un paramètre booléen est nommé obligatoire (`*,` avant lui) : `finish_play(connection, play, instant, cut=True)`, jamais `…, True`.
	Ruff le refuse dans `src/` (`FBT001`, `FBT002`).
	Seule exception, le paramètre d'un signal de Qt, que Qt passe par sa position (un slot connecté) : `# noqa: FBT001  # signal de Qt…`.
	Un `threading.Thread` passe ses arguments par `kwargs`, un signal ne se connecte jamais à une fonction à booléen nommé.
	Une fonction qui reçoit plus d'une poignée de paramètres de lecture reçoit un objet : `PlayStart` pour `begin_play`, `TrackOptions` pour `Engine.play` et `Track`.
- Docstrings et petits nettoyages ([#443](https://github.com/dascritch/machincast/issues/443)) : une fonction ou une méthode publique (sans `_` initial) de plus de 15 lignes a une docstring en français qui dit ce qu'elle fait, hors du code généré de `interface/ui/` ; un scénario de `base.feature` le vérifie.
	Ruff refuse une affectation à soi-même (`PLW0127`) et un `subprocess.run` sans `check` explicite (`PLW1510`, `check=False` quand le code de retour est lu à la main).
	`G004` reste inactive : les logs s'écrivent en f-string, jamais en notation `%`.
	Le code mort, sans appelant, est retiré, pas gardé « au cas où ».
- Ces règles valent pour tout le code Python de `src/` et de `tests/`, hors écrans compilés par `pyside6-uic`.
	Deux scénarios de [`base.feature`](../../../tests/features/base.feature) les vérifient, avec des exemples de code accepté et refusé (`tests/style.py`, [#103](https://github.com/dascritch/machincast/issues/103), [#340](https://github.com/dascritch/machincast/issues/340)) ; les règles SIM108 et SIM110 de ruff, qui réclament une expression conditionnelle à la place d'un `if` ou un `any()` à la place d'une boucle, sont désactivées.
- **Indentation par tabulations**, pour des raisons d'accessibilité.
	Ne jamais convertir en espaces.
	Dans la configuration ruff : `indent-style = "tab"` pour le formateur, règle `W191` désactivée.
- **Pas de longueur de ligne maximale** ([#384](https://github.com/dascritch/machincast/issues/384)) : la règle `E501` de ruff est désactivée, une contrainte d'éditeurs qui n'a plus cours.
	`ruff format` coupe encore le code à 120 caractères (`line-length`) ; une docstring, un commentaire ou une chaîne plus longs ne sont plus refusés.
- Ressources ([#187](https://github.com/dascritch/machincast/issues/187)) : une socket, un fichier ou un processus s'ouvre dans un `with`, ou se ferme dans un `try` dont l'échec la referme avant de remonter l'erreur ; un pipeline GStreamer finit à `Gst.State.NULL`, et un gestionnaire de signal qui retient son objet est déconnecté ([#149](https://github.com/dascritch/machincast/issues/149)).
	Un tampon rempli par une socket a une taille maximale.
	Une boucle qui s'arrête sur une erreur referme d'abord ce qu'elle a ouvert, comme la socket d'état de `Machin player`.
- Commandes système (`subprocess.run`) : toujours avec un `timeout`, et une réponse inattendue (sortie vide, valeur illisible) rattrapée comme une absence, jamais par un plantage de l'écran qui l'a demandée.
	Un processus lancé sans l'attendre (`Popen`) est relevé ensuite, pour ne pas laisser de zombie.
- Vocabulaire : « sonore », « banque », « événement ».
	« Playlist » désigne uniquement la liste exportée en .pls, .csv ou .html, jamais un objet en base ou à l'écran.
- Le nom du projet s'écrit toujours « MachinCast ».

## Messages et traductions

MachinCast parle la langue de la session ([#360](https://github.com/dascritch/machincast/issues/360)) : celle de `LANGUAGE`, `LC_ALL`, `LC_MESSAGES` puis `LANG`, la première renseignée ; l'anglais pour une langue sans catalogue.
Le code écrit ses messages en anglais, la langue source ; chaque autre langue a son catalogue gettext, [`src/machincast/locale/<langue>/LC_MESSAGES/machincast.po`](../../../src/machincast/locale/fr/LC_MESSAGES/machincast.po), versionné et lu tel quel par [`machincast.i18n`](../../../src/machincast/i18n.py) : il n'y a ni `.mo` ni `.qm` à compiler.

- **Python** : un message montré s'écrit `_("…")`, importé de `machincast.i18n`.
	Ses valeurs sont des champs nommés, remplis après la traduction : `_("{count} files read in {directory}").format(count=count, directory=directory)`, jamais une f-string, que le catalogue ne connaîtrait pas, ni une phrase assemblée de morceaux : une traduction doit pouvoir déplacer les champs et accorder les mots.
	Un nombre s'accorde par `counted("{count} file", "{count} files", count)` (ou `ngettext`) ; un même mot anglais aux traductions différentes se distingue par `pgettext("contexte", "…")` ; une date passe par `short_date` ou `date_and_hour`.
- **Log** : `kind` et `message` de la table `log` se gardent en anglais, marqués `N_("…")` (et `N_counted`) pour le catalogue ; l'interface, le journal et les exports les traduisent à l'affichage par `logged()`, qui reconnaît les gabarits du catalogue.
	Une date y est écrite en ISO 8601 (`2026-10-20 20:00`), un nombre décimal avec un point ; `logged()` les montre à la façon de la langue, `20/10/2026 à 20:00` et `10,5` en français.
	Un nom entre guillemets, `“{name}”`, est gardé tel quel.
	Une phrase stockée est un seul gabarit, jamais deux gabarits accolés par une espace.
- **Écrans** : les textes des `.ui` sont en anglais ; `pyside6-uic` les passe à `QCoreApplication.translate`, que `ScreenCatalog` ([`application.py`](../../../src/machincast/interface/application.py)) traduit par le même catalogue.
	Un texte qui ne se traduit pas (un symbole, un format) porte `notr="true"`.
- **Bash** : le wrapper et `install.sh` écrivent `t '…'` ou `tf 'format %s' "${valeur}"`, et `etape`, `info`, `echec` d'`install.sh` prennent un format de `printf` suivi de ses valeurs ([`bin/i18n.bash`](../../../bin/i18n.bash)).
	Le message est entre apostrophes, en un seul morceau, pour être relevé.
- **Ne se traduisent pas** : les noms du code, les clés et valeurs des formats échangés (configuration, socket d'état, CSV de l'airplay et de la simulation), les unités systemd et la règle polkit, écrites en anglais.
- **Catalogue** : après tout ajout ou changement de message (ses références ne donnent que le fichier, sans numéro de ligne : déplacer du code ne le change pas), `python -m machincast.catalog` relève les messages du code, des écrans et des scripts, met à jour chaque `.po` et le catalogue bash qui en découle (`machincast.bash`), sans perdre les traductions existantes ; on traduit ensuite les messages nouveaux, laissés vides.
	Le scénario [`language.feature`](../../../tests/features/language.feature) échoue tant qu'un catalogue n'est pas à jour, qu'un message n'y est pas traduit, ou qu'une traduction perd un champ de son message.
- **Tests** : les scénarios se jouent en français, la langue de leurs textes attendus, fixée par [`tests/__init__.py`](../../../tests/__init__.py) avant tout import de `machincast`, et par `tests/wrapper/aide_test.bash` pour bats ; `language.feature` vérifie l'anglais et le repli.
	Un message gardé en anglais dans le log se vérifie en anglais en base.

## Fichiers sonores

**Règle absolue** ([#96](https://github.com/dascritch/machincast/issues/96)) : MachinCast ne supprime jamais un fichier sonore, quels que soient les changements de son entrée dans la table `sounds` (état `missing`, `disabled`, `expired` ou `corrupt`, emplacement ou tags modifiés, ligne effacée).
Il ne le renomme, ne le déplace, ne le remplace et n'y écrit jamais non plus : les fichiers sonores ne sont que lus.
Supprimer un sonore, c'est supprimer sa ligne en base, jamais son fichier ; supprimer une banque, c'est supprimer sa ligne, jamais ses répertoires ni ce qu'ils contiennent ([#33](https://github.com/dascritch/machincast/issues/33)).

**Seule exception** ([#381](https://github.com/dascritch/machincast/issues/381)) : à `install.sh --service`, les répertoires de banque et les fichiers ajoutés qui sont dans un répertoire personnel, que le service de diffusion ne lit jamais, se déplacent vers `/home/machincast` si l'administrateur l'accepte explicitement, à chaque fois (`machincast.personal`).
Chaque ligne qui les déplace porte le commentaire `sonore déplacé avec accord :` (`protection.CONSENT_MARK`).
Rien d'autre ne déplace jamais un sonore.

**Droits** ([#381](https://github.com/dascritch/machincast/issues/381)) : MachinCast ne change jamais les droits d'un répertoire personnel, ni d'une arborescence du système (`machincast.access.sensitive_tree`) ; `install.sh` ne lance jamais `setfacl`, `chmod` ni `chown`.

**Désinstallation** ([#430](https://github.com/dascritch/machincast/issues/430)) : `install.sh` ne retire un répertoire que par `retirer_repertoires`, qui garde le répertoire d'accueil des sonores, `/home/machincast`, même vide, et tout répertoire qui contient un fichier sonore (`EXTENSIONS_SONORES`, celles de `protection.SOUND_EXTENSIONS`, quelle que soit la casse) ; il dit ceux qu'il garde.

- Aucun programme ne supprime, ne renomme ni ne remplace de fichier, sauf les fichiers que MachinCast crée lui-même (socket d'état, fichiers temporaires des sorties, fichier de démarrage de `Machin dev`).
	Chacune de ces lignes porte, sur la ligne ou celle du dessus, le commentaire `fichier de MachinCast :` suivi du fichier concerné.
- Un scénario de [`protection.feature`](../../../tests/features/protection.feature) refuse, dans `src/`, `bin/Machin` et `install.sh`, toute suppression, tout renommage ou tout remplacement sans cette justification (`machincast.protection.unjustified`) : en Python, `.unlink(`, `.rmdir(`, `.rename(`, `os.remove`, `os.unlink`, `os.rmdir`, `os.removedirs`, `os.rename`, `os.renames`, `os.replace`, `shutil.rmtree` et `shutil.move` ; en bash, `rm`, `rmdir`, `mv`, `unlink` et `shred`.
	`Path.replace` ne se distingue pas de `str.replace` : il est interdit, on écrit `os.replace` avec la justification.
- **Fichiers créés** ([#652](https://github.com/dascritch/machincast/issues/652)) : MachinCast ne modifie, ne remplace ni n'efface que les fichiers de sa liste, `fichiers-machincast.txt`, à côté de la configuration (`machincast.created_files`).
	Un fichier de configuration, de réglages ou de données à sauvegarder s'écrit par `created_files.write_text`, ou par `created_files.check` avant et `created_files.record` après ; il s'efface par `created_files.delete`.
	Les logs et les fichiers d'exécution (sockets, PID, rapports de plantage, fichiers temporaires) n'y vont pas.
	`install.sh` passe par `verifier_le_fichier`, `inscrire` et `desinscrire`.
	Les tests posent leur liste dans leur répertoire (fixture `created_files_list`, variable `MACHINCAST_CREATED_FILES` pour les binaires qu'ils lancent), jamais à côté d'une configuration du dépôt.
- Tout fichier écrit par MachinCast passe d'abord par `machincast.protection.check_writing`, qui lève `ProtectedSoundFile` pour un chemin à l'extension d'un fichier sonore (`SOUND_EXTENSIONS`, celles que l'indexeur enregistre).
	La configuration refuse aussi ces chemins pour `outputs.*` et `player.state_socket`.
- Les scénarios de protection vérifient, octet par octet, taille et date de modification comprises, que les fichiers d'une banque restent intacts après chaque changement de leur entrée, l'indexation rapide, l'audit complet, la diffusion et la simulation.

## Exécutables

- Une nouvelle dépendance Python se déclare dans `pyproject.toml`, jamais en paquet apt `python3-*` : le venv n'utilise pas les paquets Python du système ([#51](https://github.com/dascritch/machincast/issues/51)).
	Sa version exacte s'ajoute à `constraints.txt`, que `install.sh` passe à pip pour des installations reproductibles ([#438](https://github.com/dascritch/machincast/issues/438)).
- Un `# noqa` doit supprimer quelque chose : la règle `RUF100` de ruff refuse celui qui vise une règle non appliquée.
	Une explication se garde dans un commentaire à côté, jamais dans le `# noqa` ([#438](https://github.com/dascritch/machincast/issues/438)).
- Tout exécutable s'appelle `Machin_<nom>` et est déclaré dans `pyproject.toml` (aucune compilation).
- Les binaires sans interface se lancent par convention via le wrapper `Machin` (voir [wrapper.md](wrapper.md)).
