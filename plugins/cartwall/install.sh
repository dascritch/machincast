#!/usr/bin/env bash
# Installe ou met à jour le cartouchier (sans option), le désinstalle (--remove), ou dit ce qui serait fait
# (--simulation), après une sauvegarde de la base : https://github.com/dascritch/machincast/issues/586.
set -euo pipefail
plugin="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${MACHINCAST_PYTHON:-${plugin}/../../.venv/bin/python}" -m machincast.plugins.installation "${plugin}" "$@"
