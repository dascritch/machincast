"""Les fixtures des scénarios de la normalisation du niveau (https://github.com/dascritch/machincast/issues/43).

Ils reprennent celles de MachinCast (tests/conftest.py), sur la même base de test : le plugin n'a ni table ni
colonne : ses réglages sont dans machincast.toml, l'ajustement manuel de chaque sonore dans sa colonne properties.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PLUGIN / "src"))

pytest_plugins = ["tests.conftest"]
