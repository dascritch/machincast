# shellcheck shell=bash
# Outils communs aux tests bats du wrapper Machin (https://github.com/dascritch/machincast/issues/6).

# Les tests attendent les messages en français, comme les scénarios pytest (tests/__init__.py,
# https://github.com/dascritch/machincast/issues/360).
export LANGUAGE=fr

# Variables lues par les fichiers .bats qui chargent ce fichier.
# shellcheck disable=SC2034
RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC2034
MACHIN_DU_DEPOT="${RACINE}/bin/Machin"
# shellcheck disable=SC2034
COMPLETION="${RACINE}/bash-completion/Machin"

# Écrit dans le répertoire $1 un bouchon exécutable nommé $2.
# Avec --help, il affiche une aide au format argparse ; sinon, il affiche son nom puis chaque argument
# entre crochets (rien sans argument), et se termine avec le code ${CODE_BOUCHON} (0 par défaut).
ecrire_bouchon() {
	cat >"$1/$2" <<-'FIN'
		#!/bin/bash
		if [[ ${1-} == --help ]]; then
			printf 'usage: %s [-h] [--version] [--config FICHIER]\n\n' "${0##*/}"
			printf 'options:\n'
			printf '  -h, --help        show this help message and exit\n'
			printf '  --version         show program version number and exit\n'
			printf '  --config FICHIER  fichier de configuration TOML\n'
			exit 0
		fi
		printf '%s' "${0##*/}"
		if (($# > 0)); then
			printf ' [%s]' "$@"
		fi
		printf '\n'
		exit "${CODE_BOUCHON:-0}"
	FIN
	chmod +x "$1/$2"
}

# Prépare un projet factice, sans toucher au dépôt ni à son venv :
#   ${PROJET}/bin/Machin           copie du wrapper, dans ${MACHIN}
#   ${PROJET}/.venv/bin/Machin_*   bouchons des trois binaires, dans ${VENV}
#   ${BOUCHONS}/journalctl         bouchon de journalctl, en tête du PATH
preparer_projet() {
	PROJET="${BATS_TEST_TMPDIR}/projet"
	VENV="${PROJET}/.venv/bin"
	BOUCHONS="${BATS_TEST_TMPDIR}/bouchons"
	MACHIN="${PROJET}/bin/Machin"
	mkdir -p "${PROJET}/bin" "${VENV}" "${BOUCHONS}"
	cp "${MACHIN_DU_DEPOT}" "${MACHIN}"
	# Ses traductions : bin/i18n.bash et le catalogue bash du français (https://github.com/dascritch/machincast/issues/360).
	cp "${RACINE}/bin/i18n.bash" "${PROJET}/bin/"
	mkdir -p "${PROJET}/src/machincast/locale/fr/LC_MESSAGES"
	cp "${RACINE}/src/machincast/locale/fr/LC_MESSAGES/machincast.bash" "${PROJET}/src/machincast/locale/fr/LC_MESSAGES/"
	local nom
	for nom in Machin_player Machin_indexer Machin_interface; do
		ecrire_bouchon "${VENV}" "${nom}"
	done
	ecrire_bouchon "${BOUCHONS}" journalctl
	PATH="${BOUCHONS}:${PATH}"
	export PATH
}
