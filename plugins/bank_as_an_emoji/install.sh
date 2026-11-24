#!/usr/bin/env bash
# Installe ou met à jour la banque en emoji (sans option), la désinstalle (--remove), ou dit ce qui serait fait
# (--simulation) : https://github.com/dascritch/machincast/issues/505. Le plugin n'a ni table ni colonne : l'emoji est
# au début du nom interne de la banque.
set -euo pipefail
plugin="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${MACHINCAST_PYTHON:-${plugin}/../../.venv/bin/python}" -m machincast.plugins.installation "${plugin}" "$@"
