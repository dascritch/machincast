#!/usr/bin/env bats
# Outils du poste de développement : Machin dev et Machin dev-test (https://github.com/dascritch/machincast/issues/77).
# Les outils sont remplacés par des bouchons qui notent leur appel dans ${APPELS}.

# ${stderr} est rempli par « run --separate-stderr » de bats.
# shellcheck disable=SC2154
bats_require_minimum_version 1.5.0

setup() {
	load aide_test
	preparer_projet
	APPELS="${BATS_TEST_TMPDIR}/appels"
	ECHECS="${BATS_TEST_TMPDIR}/echecs"
	export APPELS ECHECS
	touch "${ECHECS}"
	local outil
	for outil in ruff mypy pytest; do
		ecrire_outil "${VENV}" "${outil}"
	done
	for outil in shellcheck bats; do
		ecrire_outil "${BOUCHONS}" "${outil}"
	done
	# Venv factice : activate le signale par VIRTUAL_ENV, comme le vrai.
	# shellcheck disable=SC2016
	printf 'VIRTUAL_ENV=%q\nexport VIRTUAL_ENV\nPATH="${VIRTUAL_ENV}/bin:${PATH}"\n' "${PROJET}/.venv" \
		>"${VENV}/activate"
}

# Bouchon d'outil : note son nom, ses arguments, son répertoire courant et VIRTUAL_ENV ; échoue si son nom figure
# dans ${ECHECS}.
ecrire_outil() {
	cat >"$1/$2" <<-'FIN'
		#!/bin/bash
		nom="${0##*/}"
		printf '%s' "${nom}" >>"${APPELS}"
		(($# > 0)) && printf ' [%s]' "$@" >>"${APPELS}"
		printf ' dans %s, venv %s\n' "${PWD}" "${VIRTUAL_ENV-aucun}" >>"${APPELS}"
		! grep -qx "${nom}" "${ECHECS}"
	FIN
	chmod +x "$1/$2"
}

# ─── Machin dev-test ───────────────────────────────────────

@test "Machin dev-test lance chaque outil, dans l'ordre, depuis le répertoire de MachinCast" {
	cd "${BATS_TEST_TMPDIR}"
	run "${MACHIN}" dev-test
	[ "${status}" -eq 0 ]
	run cut -d ' ' -f 1 "${APPELS}"
	[ "${output}" = "$(printf '%s\n' ruff ruff mypy shellcheck pytest bats)" ]
	run grep -c " dans ${PROJET}, " "${APPELS}"
	[ "${output}" -eq 6 ]
}

@test "Machin dev-test donne à chaque outil ses arguments" {
	run "${MACHIN}" dev-test
	grep -qF "ruff [check] [--no-cache] [.] " "${APPELS}"
	grep -qF "ruff [format] [--no-cache] [--check] [.] " "${APPELS}"
	grep -qF "mypy [--strict] [src/] " "${APPELS}"
	grep -qF "shellcheck [-x] [install.sh] [bin/Machin] [bash-completion/Machin] " "${APPELS}"
	grep -qF "bats [tests/wrapper] " "${APPELS}"
}

@test "les outils de Machin dev-test voient le venv du projet, sans qu'il soit activé" {
	PATH="${BOUCHONS}:/usr/bin:/bin" run "${MACHIN}" dev-test
	[ "${status}" -eq 0 ]
	run grep -c "venv ${PROJET}/.venv$" "${APPELS}"
	[ "${output}" -eq 6 ]
}

@test "Machin dev-test affiche un bilan par outil" {
	run "${MACHIN}" dev-test
	[[ "${output}" == *"ruff check"*"réussi"* ]]
	[[ "${output}" == *"ruff format --check"*"réussi"* ]]
	[[ "${output}" == *"mypy --strict"*"réussi"* ]]
	[[ "${output}" == *"shellcheck"*"réussi"* ]]
	[[ "${output}" == *"pytest"*"réussi"* ]]
	[[ "${output}" == *"bats"*"réussi"* ]]
	[[ "${output}" == *"tous les outils ont réussi"* ]]
}

@test "après un échec, Machin dev-test lance quand même les outils suivants et se termine en échec" {
	printf 'mypy\n' >"${ECHECS}"
	run "${MACHIN}" dev-test
	[ "${status}" -eq 1 ]
	run cut -d ' ' -f 1 "${APPELS}"
	[ "${output}" = "$(printf '%s\n' ruff ruff mypy shellcheck pytest bats)" ]
	run "${MACHIN}" dev-test
	[[ "${output}" == *"mypy --strict"*"échec"* ]]
	[[ "${output}" == *"1 outil en échec : mypy --strict"* ]]
}

@test "un outil absent est signalé par Machin dev-test, avec ./install.sh --dev" {
	rm "${VENV}/ruff"
	run "${MACHIN}" dev-test
	[ "${status}" -eq 1 ]
	[[ "${output}" == *"ruff introuvable"*"./install.sh --dev"* ]]
	run cut -d ' ' -f 1 "${APPELS}"
	[ "${output}" = "$(printf '%s\n' mypy shellcheck pytest bats)" ]
}

@test "sans venv, Machin dev-test le signale avec ./install.sh --dev et le code 127" {
	rm -r "${PROJET}/.venv"
	run -127 --separate-stderr "${MACHIN}" dev-test
	[ "${status}" -eq 127 ]
	[[ "${stderr}" == *"${PROJET}/.venv"*"./install.sh --dev"* ]]
}

# ─── Machin dev ────────────────────────────────────────────

# Lance Machin dev depuis un autre répertoire, avec les commandes données sur l'entrée standard.
machin_dev() {
	cd "${BATS_TEST_TMPDIR}" || return
	HOME="${BATS_TEST_TMPDIR}" run "${2:--0}" --separate-stderr "${MACHIN}" dev <<<"$1"
}

@test "Machin dev ouvre un sous-shell dans le répertoire de MachinCast, venv activé" {
	# shellcheck disable=SC2016
	machin_dev 'printf "%s|%s|%s\n" "${PWD}" "${VIRTUAL_ENV}" "${MACHINCAST_DEV}"'
	[ "${status}" -eq 0 ]
	[[ "${output}" == *"${PROJET}|${PROJET}/.venv|1"* ]]
}

@test "l'invite du sous-shell de Machin dev le signale" {
	# shellcheck disable=SC2016
	machin_dev 'printf "%s\n" "${PS1}"'
	[[ "${output}" == *"(MachinCast dev)"* ]]
}

@test "exit sort du sous-shell de Machin dev, avec son code" {
	machin_dev 'exit 4' -4
	[ "${status}" -eq 4 ]
}

@test "le sous-shell de Machin dev lit encore le .bashrc du compte" {
	printf 'MARQUE_BASHRC=lu\n' >"${BATS_TEST_TMPDIR}/.bashrc"
	# shellcheck disable=SC2016
	machin_dev 'printf "%s\n" "${MARQUE_BASHRC-}"'
	[[ "${output}" == *"lu"* ]]
}

@test "sans venv, Machin dev le signale avec ./install.sh --dev et le code 127" {
	rm -r "${PROJET}/.venv"
	machin_dev 'exit 0' -127
	[ "${status}" -eq 127 ]
	[[ "${stderr}" == *"${PROJET}/.venv"*"./install.sh --dev"* ]]
}

# ─── Aide ──────────────────────────────────────────────────

@test "l'aide complète de Machin a une section Développement" {
	run "${MACHIN}" --help
	[[ "${output}" == *"Développement"*"dev "*"dev-test"*"./install.sh --dev"* ]]
}

# ─── Machin dev-captures ───────────────────────────────────

@test "Machin dev-captures produit les captures du guide avec le Python du venv, depuis le répertoire de MachinCast" {
	ecrire_outil "${VENV}" python
	cd "${BATS_TEST_TMPDIR}"
	run "${MACHIN}" dev-captures
	[ "${status}" -eq 0 ]
	grep -qF "python [-m] [tests.captures] dans ${PROJET}, venv ${PROJET}/.venv" "${APPELS}"
}

@test "Machin dev-captures transmet le répertoire où écrire les captures" {
	ecrire_outil "${VENV}" python
	run "${MACHIN}" dev-captures /tmp/essai
	[ "${status}" -eq 0 ]
	grep -qF "python [-m] [tests.captures] [/tmp/essai] dans ${PROJET}" "${APPELS}"
}

@test "Machin dev-captures refuse --config : il n'écrit que dans la base de test" {
	run --separate-stderr "${MACHIN}" --config autre.toml dev-captures
	[ "${status}" -eq 2 ]
	[[ "${stderr}" == *"--config ne s'applique pas à dev-captures"* ]]
}

@test "Machin dev-captures refuse plus d'un répertoire" {
	run --separate-stderr "${MACHIN}" dev-captures un deux
	[ "${status}" -eq 2 ]
	[[ "${stderr}" == *"dev-captures prend au plus un répertoire"* ]]
}
