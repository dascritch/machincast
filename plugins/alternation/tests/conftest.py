"""Les fixtures des scénarios des émissions en alternance (https://github.com/dascritch/machincast/issues/609).

Ils reprennent celles de MachinCast (tests/conftest.py), sur la même base de test : le plugin n'a ni table ni
colonne, ses données sont dans la colonne properties des événements.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PLUGIN / "src"))

pytest_plugins = ["tests.conftest"]
