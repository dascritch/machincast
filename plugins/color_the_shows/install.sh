#!/usr/bin/env bash
# Installe ou met à jour les couleurs des émissions (sans option), les désinstalle (--remove), ou dit ce qui serait
# fait (--simulation) : https://github.com/dascritch/machincast/issues/628. Ses deux tables, les genres et les
# couleurs des priorités, viennent de ses migrations.
set -euo pipefail
plugin="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${MACHINCAST_PYTHON:-${plugin}/../../.venv/bin/python}" -m machincast.plugins.installation "${plugin}" "$@"
