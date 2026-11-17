#!/usr/bin/env bats
# Machin tasks : les tâches régulières, que lance tous les quarts d'heure le minuteur du service
# (https://github.com/dascritch/machincast/issues/455).

# ${stderr} est rempli par « run --separate-stderr » de bats.
# shellcheck disable=SC2154
bats_require_minimum_version 1.5.0

setup() {
	load aide_test
	preparer_projet
	ecrire_bouchon_code "${VENV}" python CODE_RESERVE
	ecrire_bouchon_code "${VENV}" Machin_purge CODE_PURGE
	ecrire_bouchon_code "${VENV}" Machin_indexer CODE_AUDIT
}

# Écrit dans le répertoire $1 un bouchon exécutable nommé $2, qui affiche son nom et ses arguments entre crochets, et se
# termine avec le code de la variable d'environnement $3 (0 sans elle).
ecrire_bouchon_code() {
	cat >"$1/$2" <<-FIN
		#!/bin/bash
		printf '%s' "\${0##*/}"
		if ((\$# > 0)); then
			printf ' [%s]' "\$@"
		fi
		printf '\n'
		exit "\${$3:-0}"
	FIN
	chmod +x "$1/$2"
}

@test "Machin tasks, la tâche quotidienne due, lance la purge puis l'audit complet" {
	run "${MACHIN}" tasks
	[ "${status}" -eq 0 ]
	[ "${output}" = "$(printf '%s\n' 'python [-m] [machincast.schedule] [claim]' 'Machin_purge' 'Machin_indexer [--full-audit]')" ]
}

@test "Machin tasks, la tâche quotidienne pas encore due, ne lance rien d'autre" {
	CODE_RESERVE=1 run "${MACHIN}" tasks
	[ "${status}" -eq 0 ]
	[ "${output}" = 'python [-m] [machincast.schedule] [claim]' ]
}

@test "Machin tasks : une purge en échec arrête la tâche quotidienne, avec son code" {
	CODE_PURGE=1 run "${MACHIN}" tasks
	[ "${status}" -eq 1 ]
	[ "${output}" = "$(printf '%s\n' 'python [-m] [machincast.schedule] [claim]' 'Machin_purge')" ]
}

@test "Machin tasks : un audit complet déjà en cours (code 3) n'est pas un échec" {
	CODE_AUDIT=3 run "${MACHIN}" tasks
	[ "${status}" -eq 0 ]
}

@test "Machin tasks : un audit en échec donne son code" {
	CODE_AUDIT=1 run "${MACHIN}" tasks
	[ "${status}" -eq 1 ]
}

@test "Machin tasks : une réserve impossible (code 2) est le code de Machin tasks, sans rien lancer" {
	CODE_RESERVE=2 run "${MACHIN}" tasks
	[ "${status}" -eq 2 ]
	[ "${output}" = 'python [-m] [machincast.schedule] [claim]' ]
}

@test "Machin --config FICHIER tasks transmet la configuration à la réserve et aux binaires" {
	run "${MACHIN}" --config essai.toml tasks
	[ "${status}" -eq 0 ]
	[ "${output}" = "$(printf '%s\n' 'python [-m] [machincast.schedule] [claim] [--config] [essai.toml]' 'Machin_purge [--config] [essai.toml]' 'Machin_indexer [--config] [essai.toml] [--full-audit]')" ]
}

@test "Machin tasks ne prend pas d'argument" {
	run --separate-stderr "${MACHIN}" tasks --vite
	[ "${status}" -eq 2 ]
	[[ "${stderr}" == *"tasks ne prend pas d'argument"* ]]
}

@test "Machin tasks sans le Python du venv est signalé avec le code 127" {
	rm "${VENV}/python"
	run -127 --separate-stderr "${MACHIN}" tasks
	[ "${status}" -eq 127 ]
	[[ "${stderr}" == *"python"* ]]
}
