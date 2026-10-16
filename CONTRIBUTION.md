# Contribuer à MachinCast

Avant toute modification, lire [CLAUDE.md](CLAUDE.md) et les [règles de développement](doc/regles/developpement.md) : ticket, scénarios BDD d'abord, un commit par fonctionnalité, indentation par tabulations, [definition of done](doc/regles/developpement.md#definition-of-done). Le poste de développement s'installe avec `./install.sh --dev` ([INSTALL.md](INSTALL.md)).

## Écrans de l'interface

Les écrans de `Machin_interface` sont des écrans Qt Widgets, dessinés avec **Qt Widgets Designer** et compilés en modules Python par **`pyside6-uic`**. Les deux outils sont fournis par le paquet PySide6 du venv : ils ont la même version de Qt que l'interface, et il n'y a rien à installer en plus. On ne prend ni le Designer d'apt ou de Qt Creator, dont la version de Qt peut différer, ni Qt Design Studio, qui sert à QML.

### Dessiner un écran

```bash
bin/Machin dev           # sous-shell dans le dépôt, venv activé
pyside6-designer src/machincast/interface/ui/fiche_banque.ui
```

- Un écran = un fichier `.ui` dans `src/machincast/interface/ui/`, nommé en français et en `snake_case`, comme le module qu'il produira : `fiche_banque.ui`, `fiche_evenement.ui`.
- Les `objectName` des widgets sont en français et en `snake_case` (`nom_interne`, `nom_public`, `liste_sonores`), puisqu'ils deviennent des attributs Python : `self.ui.nom_interne`.
- Vocabulaire à l'écran : celui de la spécification ([§ 1](doc/spec.md#1-vocabulaire)) et des [règles de l'interface](doc/regles/interface.md), « banque » et jamais « playlist ».
- Les champs de texte courts sont limités à 255 caractères (`maxLength`), comme en base.
- Le fichier `.ui` ne contient que la disposition. Le comportement (signaux, requêtes, validation, glisser-déposer) s'écrit en Python, dans la classe de l'écran, où il est testé avec pytest-qt.

### Compiler un écran

Après chaque enregistrement dans le Designer, régénérer le module Python :

```bash
pyside6-uic src/machincast/interface/ui/fiche_banque.ui -o src/machincast/interface/ui/fiche_banque.py
```

- Le fichier `.ui` et le module généré sont versionnés ensemble, dans le même commit.
- Un module généré ne se modifie **jamais** à la main : il serait écrasé à la compilation suivante. Toute modification passe par le `.ui`.
- Le module généré est indenté par espaces et n'est pas annoté : c'est la seule exception à la règle des tabulations et au typage strict. Il est exclu de `ruff`, et `mypy` y tolère les fonctions non annotées.

### Utiliser un écran compilé

```python
from PySide6.QtWidgets import QWidget

from machincast.interface.ui.fiche_banque import Ui_FicheBanque


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
```

Garder `src/machincast/interface/ui/__init__.py`, sans quoi les modules générés ne sont pas importables.
