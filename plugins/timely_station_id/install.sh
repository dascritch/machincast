#!/usr/bin/env bash
# Installe ou met à jour le station ID régulier (sans option), le désinstalle (--remove), ou dit ce qui serait fait
# (--simulation) : https://github.com/dascritch/machincast/issues/460. Le plugin n'a ni table ni colonne : ses réglages
# sont dans machincast.toml, et le choix de chaque événement dans sa colonne properties.
set -euo pipefail
plugin="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${MACHINCAST_PYTHON:-${plugin}/../../.venv/bin/python}" -m machincast.plugins.installation "${plugin}" "$@"
