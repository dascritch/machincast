#!/usr/bin/env bats
# Autocomplétion bash du wrapper Machin (https://github.com/dascritch/machincast/issues/6).

bats_require_minimum_version 1.5.0

setup() {
	load aide_test
	preparer_projet
	PATH="${PROJET}/bin:${PATH}"
	# shellcheck source=bash-completion/Machin
	source "${COMPLETION}"
}

# Simule une ligne de commande en cours de saisie : chaque argument est un mot, le dernier est complété. Les
# propositions sont triées en locale C, quelle que soit celle du terminal : en français ou en anglais, « -h » se
# rangerait sinon parmi les options longues (https://github.com/dascritch/machincast/issues/79).
completer() {
	COMP_WORDS=("$@")
	COMP_CWORD=$((${#COMP_WORDS[@]} - 1))
	COMP_LINE="$*"
	COMP_POINT=${#COMP_LINE}
	COMPREPLY=()
	_Machin Machin "${COMP_WORDS[COMP_CWORD]}" "${COMP_WORDS[COMP_CWORD - 1]}"
	printf '%s\n' "${COMPREPLY[@]}" | LC_ALL=C sort
}

@test "la complétion est enregistrée pour la commande Machin" {
	run complete -p Machin
	[ "${status}" -eq 0 ]
	[[ "${output}" == *"-F _Machin"* ]]
}

@test "Machin <TAB> propose les binaires, logs, dev et dev-test" {
	run completer Machin ""
	[ "${output}" = "$(printf '%s\n' dev dev-test indexation interface lecture logs)" ]
}

@test "Machin dev-test <TAB> ne propose rien de plus" {
	run completer Machin dev-test ""
	[ "${output}" = "" ]
}

@test "Machin in<TAB> propose les binaires qui commencent par in" {
	run completer Machin in
	[ "${output}" = "$(printf '%s\n' indexation interface)" ]
}

@test "Machin -<TAB> propose les options du wrapper" {
	run completer Machin -
	[ "${output}" = "$(printf '%s\n' --binaires --config --help -h)" ]
}

@test "Machin --config <TAB> propose des fichiers" {
	cd "${BATS_TEST_TMPDIR}"
	touch essai.toml autre.toml
	run completer Machin --config es
	[ "${output}" = "essai.toml" ]
}

@test "Machin --config=<TAB> propose des fichiers" {
	cd "${BATS_TEST_TMPDIR}"
	touch essai.toml
	run completer Machin --config = es
	[ "${output}" = "essai.toml" ]
}

@test "après --config FICHIER, Machin l<TAB> propose encore les binaires" {
	run completer Machin --config essai.toml l
	[ "${output}" = "$(printf '%s\n' lecture logs)" ]
}

@test "Machin lecture -<TAB> propose les options lues dans l'aide du binaire" {
	run completer Machin lecture -
	[ "${output}" = "$(printf '%s\n' --config --help --version -h)" ]
}

@test "Machin lecture --config <TAB> propose des fichiers" {
	cd "${BATS_TEST_TMPDIR}"
	touch essai.toml
	run completer Machin lecture --config es
	[ "${output}" = "essai.toml" ]
}

@test "Machin logs --<TAB> propose les options courantes de journalctl" {
	run completer Machin logs --
	[[ "${output}" == *"--since"* ]]
	[[ "${output}" == *"--priority"* ]]
	[[ "${output}" != *"--config"* ]]
}

@test "avec le venv du dépôt, Machin indexation --<TAB> propose les vraies options du binaire" {
	[ -x "${RACINE}/.venv/bin/Machin_indexation" ] || skip "venv du dépôt absent"
	PATH="${RACINE}/bin:/usr/bin:/bin"
	run completer Machin indexation --
	[[ "${output}" == *"--config"* ]]
	[[ "${output}" == *"--version"* ]]
}
