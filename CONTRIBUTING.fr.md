# Contribuer à MachinCast

*[English version](CONTRIBUTING.md)*

Avant toute modification, lire [CLAUDE.md](CLAUDE.md) et les [règles de développement](doc/fr/regles/developpement.md) : ticket, scénarios BDD d'abord, un commit par fonctionnalité, indentation par tabulations, [definition of done](doc/fr/regles/developpement.md#definition-of-done). Le poste de développement s'installe avec `./install.sh --dev` ([INSTALL.md](INSTALL.fr.md)).

## Écrans de l'interface

Les écrans de `Machin_interface` sont des écrans Qt Widgets, dessinés avec **Qt Widgets Designer** et compilés en modules Python par **`pyside6-uic`**. Les deux outils sont fournis par le paquet PySide6 du venv : ils ont la même version de Qt que l'interface, et il n'y a rien à installer en plus. On ne prend ni le Designer d'apt ou de Qt Creator, dont la version de Qt peut différer, ni Qt Design Studio, qui sert à QML.

### Dessiner un écran

```bash
bin/Machin dev           # sous-shell dans le dépôt, venv activé
pyside6-designer src/machincast/interface/ui/bank_card.ui
```

- Un écran = un fichier `.ui` dans `src/machincast/interface/ui/`, nommé en français et en `snake_case`, comme le module qu'il produira : `bank_card.ui`, `event_card.ui`.
- Les `objectName` des widgets sont en français et en `snake_case` (`internal_name`, `public_name`, `sound_list`), puisqu'ils deviennent des attributs Python : `self.ui.internal_name`.
- Les textes de l'écran sont en anglais ; ils se traduisent par le catalogue de MachinCast ([traduire MachinCast](#traduire-machincast)). Un texte qui ne se traduit pas (un symbole, un format) se coche « non traduisible » (`notr`) ; un même mot anglais aux traductions différentes reçoit un commentaire (`comment`), qui devient son contexte.
- Vocabulaire à l'écran : celui de la spécification ([§ 1](doc/fr/spec.md#1-vocabulaire)) et des [règles de l'interface](doc/fr/regles/interface.md), « banque » et jamais « playlist » ; en anglais, *bank*.
- Les champs de texte courts sont limités à 255 caractères (`maxLength`), comme en base.
- Le fichier `.ui` ne contient que la disposition. Le comportement (signaux, requêtes, validation, glisser-déposer) s'écrit en Python, dans la classe de l'écran, où il est testé avec pytest-qt.

### Compiler un écran

Après chaque enregistrement dans le Designer, régénérer le module Python :

```bash
pyside6-uic src/machincast/interface/ui/bank_card.ui -o src/machincast/interface/ui/fiche_banque.py
```

- Le fichier `.ui` et le module généré sont versionnés ensemble, dans le même commit.
- Un module généré ne se modifie **jamais** à la main : il serait écrasé à la compilation suivante. Toute modification passe par le `.ui`.
- Le module généré est indenté par espaces et n'est pas annoté : c'est la seule exception à la règle des tabulations et au typage strict. Il est exclu de `ruff`, et `mypy` y tolère les fonctions non annotées.

### Utiliser un écran compilé

```python
from PySide6.QtWidgets import QWidget

from machincast.interface.ui.bank_card import Ui_FicheBanque


class FicheBanque(QWidget):
	def __init__(self) -> None:
		super().__init__()
		self.ui = Ui_FicheBanque()
		self.ui.setupUi(self)
		self.ui.nom_interne.textChanged.connect(self._nom_modifie)
```

`mypy --strict` connaît les widgets créés par `setupUi` : un `objectName` mal orthographié, ou un widget retiré du `.ui`, est signalé à la vérification de types.

### Configuration des outils

Elle est dans `pyproject.toml` depuis le premier écran, l'écran par défaut ([#23](https://github.com/dascritch/machincast/issues/23)), dans les sections `[tool.ruff]` et `[tool.mypy]` :

```toml
[tool.ruff]
extend-exclude = ["src/machincast/interface/ui/*.py"]

[tool.mypy]
# setupUi n'est pas annoté : l'appeler depuis un code typé reste permis.
untyped_calls_exclude = ["machincast.interface.ui"]

[[tool.mypy.overrides]]
# Modules générés par pyside6-uic.
module = ["machincast.interface.ui.*"]
disallow_untyped_defs = false
disallow_untyped_calls = false
# Les titres de colonnes d'une table (horizontalHeaderItem) y sont posés sans vérifier leur existence.
disable_error_code = ["union-attr"]
```

Garder `src/machincast/interface/ui/__init__.py`, sans quoi les modules générés ne sont pas importables.

## Traduire MachinCast

MachinCast écrit ses messages en anglais et les traduit par des catalogues gettext, un par langue : [`src/machincast/locale/fr/LC_MESSAGES/machincast.po`](src/machincast/locale/fr/LC_MESSAGES/machincast.po) pour le français ([#360](https://github.com/dascritch/machincast/issues/360)). Le catalogue couvre le code Python, les écrans `.ui`, le wrapper `Machin` et `install.sh` ; les règles d'écriture des messages sont dans les [règles de développement](doc/fr/regles/developpement.md#messages-et-traductions).

```bash
bin/Machin dev                          # sous-shell dans le dépôt, venv activé
python -m machincast.catalog            # relève les messages et met à jour chaque catalogue
python -m machincast.catalog --check    # vérifie, sans rien écrire : ce que fait language.feature
python -m machincast.catalog --new de   # crée le catalogue d'une nouvelle langue, ici l'allemand
```

- Le `.po` se traduit avec tout éditeur de catalogues gettext (Poedit, Lokalize, Gtranslator) ou un éditeur de texte. Un message nouveau y arrive sans traduction ; une traduction existante est gardée tant que son message ne change pas.
- Une traduction garde les champs de son message, `{count}`, `{name}`… même déplacés, et les `%s` d'un message de script dans le même ordre. Elle peut changer l'ordre des mots et s'accorder : un message au pluriel a ses deux formes (`msgstr[0]`, `msgstr[1]`), un message à contexte (`msgctxt`) une traduction par contexte.
- Rien n'est à compiler : MachinCast lit le `.po` tel quel, et `python -m machincast.catalog` écrit à côté `machincast.bash`, la part des scripts, que le wrapper et `install.sh` chargent sans gettext. Les textes de Qt (boutons standard des fenêtres) viennent de la traduction livrée avec PySide6.
- Une nouvelle langue est parlée dès que son catalogue existe ; une langue dont le pluriel ne suit pas la règle anglaise (`n != 1`) a sa règle dans `PLURALS` de [`machincast.i18n`](src/machincast/i18n.py).
