#!/usr/bin/env bash
# Installe ou met à jour la normalisation du niveau (sans option), la désinstalle (--remove), ou dit ce qui serait fait
# (--simulation) : https://github.com/dascritch/machincast/issues/43. Le plugin n'a ni table ni colonne : ses réglages
# sont dans machincast.toml, l'ajustement manuel de chaque sonore dans sa colonne properties.
set -euo pipefail
plugin="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${MACHINCAST_PYTHON:-${plugin}/../../.venv/bin/python}" -m machincast.plugins.installation "${plugin}" "$@"
