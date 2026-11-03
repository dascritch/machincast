"""Scénarios du type de fichier d'un sonore (https://github.com/dascritch/machincast/issues/121).

Les étapes sont dans tests/indexing_steps.py : l'indexeur examine de vrais fichiers, avec libmagic.
"""

from pytest_bdd import scenarios

scenarios("file_type.feature")
