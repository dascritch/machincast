#!/usr/bin/env bash
# Installe ou met à jour les émissions en alternance (sans option), les désinstalle (--remove), ou dit ce qui serait
# fait (--simulation) : https://github.com/dascritch/machincast/issues/609. Le plugin n'a ni table ni colonne : ses
# données sont dans la colonne properties des événements (https://github.com/dascritch/machincast/issues/607).
set -euo pipefail
plugin="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${MACHINCAST_PYTHON:-${plugin}/../../.venv/bin/python}" -m machincast.plugins.installation "${plugin}" "$@"
