#!/usr/bin/env bats
# Wrapper Machin : appel des binaires, aide et suivi des logs (https://github.com/dascritch/machincast/issues/6).

# ${stderr} est rempli par « run --separate-stderr » de bats.
# shellcheck disable=SC2154
bats_require_minimum_version 1.5.0

setup() {
	load aide_test
	preparer_projet
}

# ─── Appel des binaires ────────────────────────────────────

@test "Machin lecture appelle Machin_lecture en lui transmettant les options" {
	run "${MACHIN}" lecture --simulation --graine 42
	[ "${status}" -eq 0 ]
	[ "${output}" = "Machin_lecture [--simulation] [--graine] [42]" ]
}

@test "Machin indexation et Machin interface appellent leur binaire" {
	run "${MACHIN}" indexation
	[ "${output}" = "Machin_indexation" ]
	run "${MACHIN}" interface
	[ "${output}" = "Machin_interface" ]
}

@test "les arguments contenant des espaces sont transmis intacts" {
	run "${MACHIN}" indexation "un répertoire/avec des espaces" ""
	[ "${output}" = "Machin_indexation [un répertoire/avec des espaces] []" ]
}

@test "le code de sortie du binaire est celui du wrapper" {
	CODE_BOUCHON=3 run "${MACHIN}" lecture
	[ "${status}" -eq 3 ]
}

@test "l'aide d'un binaire est celle du binaire lui-même" {
	run "${MACHIN}" lecture --help
	[ "${status}" -eq 0 ]
	[[ "${lines[0]}" == "usage: Machin_lecture "* ]]
}

@test "un binaire inconnu est refusé avec le code 2" {
	run --separate-stderr "${MACHIN}" diffusion
	[ "${status}" -eq 2 ]
	[[ "${stderr}" == *"binaire inconnu : diffusion"* ]]
	[[ "${stderr}" == *"lecture"*"indexation"*"interface"* ]]
}

@test "le wrapper appelle les binaires du venv du projet sans qu'il soit activé" {
	PATH="${BOUCHONS}:/usr/bin:/bin" run "${MACHIN}" lecture
	[ "${output}" = "Machin_lecture" ]
}

@test "le binaire du venv du projet passe avant celui du PATH" {
	printf '#!/bin/bash\necho "Machin_lecture du PATH"\n' >"${BOUCHONS}/Machin_lecture"
	chmod +x "${BOUCHONS}/Machin_lecture"
	run "${MACHIN}" lecture
	[ "${output}" = "Machin_lecture" ]
}

@test "sans venv dans le projet, le binaire est cherché dans le PATH" {
	rm -r "${PROJET}/.venv"
	ecrire_bouchon "${BOUCHONS}" Machin_indexation
	run "${MACHIN}" indexation
	[ "${output}" = "Machin_indexation" ]
}

@test "appelé par un lien symbolique, le wrapper trouve le venv de son projet" {
	local liens="${BATS_TEST_TMPDIR}/liens"
	mkdir -p "${liens}"
	ln -s "${MACHIN}" "${liens}/Machin"
	PATH="${BOUCHONS}:/usr/bin:/bin" run "${liens}/Machin" interface
	[ "${output}" = "Machin_interface" ]
}

@test "un binaire absent est signalé avec le code 127 et la façon de l'installer" {
	rm "${VENV}/Machin_interface"
	PATH="${BOUCHONS}:/usr/bin:/bin" run -127 --separate-stderr "${MACHIN}" interface
	[[ "${stderr}" == *"Machin_interface introuvable"* ]]
	[[ "${stderr}" == *"${PROJET}/.venv"* ]]
	[[ "${stderr}" == *'pip install -e ".[dev]"'* ]]
}

@test "la liste des binaires du wrapper est celle des exécutables déclarés dans pyproject.toml" {
	run "${MACHIN}" --binaires
	[ "${status}" -eq 0 ]
	local declares
	declares="$(sed -n 's/^Machin_\([a-z]*\) = .*/\1/p' "${RACINE}/pyproject.toml" | sort)"
	[ -n "${declares}" ]
	[ "$(printf '%s\n' "${lines[@]}" | sort)" = "${declares}" ]
}

# ─── Configuration ─────────────────────────────────────────

@test "--config placé avant le binaire lui est transmis" {
	run "${MACHIN}" --config essai.toml lecture --simulation
	[ "${status}" -eq 0 ]
	[ "${output}" = "Machin_lecture [--config] [essai.toml] [--simulation]" ]
}

@test "--config=FICHIER placé avant le binaire lui est transmis" {
	run "${MACHIN}" --config=essai.toml indexation
	[ "${output}" = "Machin_indexation [--config] [essai.toml]" ]
}

@test "--config placé après le binaire est transmis tel quel" {
	run "${MACHIN}" lecture --config essai.toml
	[ "${output}" = "Machin_lecture [--config] [essai.toml]" ]
}

@test "--config sans fichier est refusé avec le code 2" {
	run --separate-stderr "${MACHIN}" --config
	[ "${status}" -eq 2 ]
	[[ "${stderr}" == *"--config demande un fichier"* ]]
	run --separate-stderr "${MACHIN}" --config=
	[ "${status}" -eq 2 ]
}

# ─── Aide ──────────────────────────────────────────────────

@test "Machin -h affiche une aide minimale de quelques lignes" {
	run "${MACHIN}" -h
	[ "${status}" -eq 0 ]
	[ "${#lines[@]}" -le 5 ]
	[[ "${output}" == *"Usage : Machin"* ]]
	[[ "${output}" == *"lecture"*"indexation"*"interface"* ]]
	[[ "${output}" == *"Machin --help"* ]]
}

@test "Machin --help affiche l'aide complète : binaires, options, logs et codes de sortie" {
	run "${MACHIN}" --help
	[ "${status}" -eq 0 ]
	run "${MACHIN}" -h
	local minimale="${#lines[@]}"
	run "${MACHIN}" --help
	[ "${#lines[@]}" -gt "${minimale}" ]
	local attendu
	for attendu in lecture indexation interface logs --config --binaires machincast.service 127; do
		[[ "${output}" == *"${attendu}"* ]] || { echo "absent de l'aide complète : ${attendu}"; return 1; }
	done
}

@test "Machin sans argument affiche l'aide minimale sur la sortie d'erreur avec le code 2" {
	run --separate-stderr "${MACHIN}"
	[ "${status}" -eq 2 ]
	[ -z "${output}" ]
	[[ "${stderr}" == *"Usage : Machin"* ]]
}

@test "une option inconnue du wrapper est refusée avec le code 2" {
	run --separate-stderr "${MACHIN}" --verbeux lecture
	[ "${status}" -eq 2 ]
	[[ "${stderr}" == *"option inconnue : --verbeux"* ]]
}

# ─── Logs ──────────────────────────────────────────────────

@test "Machin logs suit en direct le journal du service de lecture" {
	run "${MACHIN}" logs
	[ "${status}" -eq 0 ]
	[ "${output}" = "journalctl [--unit=machincast.service] [--follow]" ]
}

@test "Machin logs transmet ses options à journalctl" {
	run "${MACHIN}" logs --since "1 hour ago" --priority=warning
	[ "${output}" = "journalctl [--unit=machincast.service] [--follow] [--since] [1 hour ago] [--priority=warning]" ]
}

@test "Machin logs refuse --config, qui ne le concerne pas" {
	run --separate-stderr "${MACHIN}" --config essai.toml logs
	[ "${status}" -eq 2 ]
	[[ "${stderr}" == *"--config ne s'applique pas à logs"* ]]
}

@test "Machin logs sans journalctl est signalé avec le code 127" {
	local vide="${BATS_TEST_TMPDIR}/vide"
	mkdir -p "${vide}"
	ln -s "$(command -v bash)" "${vide}/bash"
	run -127 --separate-stderr env PATH="${vide}" "${MACHIN}" logs
	[[ "${stderr}" == *"journalctl introuvable"* ]]
}

# ─── Avec les vrais binaires ───────────────────────────────

@test "avec le venv du dépôt, Machin lecture --version affiche la version de MachinCast sans activer le venv" {
	[ -x "${RACINE}/.venv/bin/Machin_lecture" ] || skip "venv du dépôt absent : python3 -m venv .venv && .venv/bin/pip install -e \".[dev]\""
	PATH="/usr/bin:/bin" run "${MACHIN_DU_DEPOT}" lecture --version
	[ "${status}" -eq 0 ]
	[[ "${output}" == "Machin_lecture (MachinCast) "* ]]
}
