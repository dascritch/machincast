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

@test "Machin player appelle Machin_player en lui transmettant les options" {
	run "${MACHIN}" player --simulation --seed 42
	[ "${status}" -eq 0 ]
	[ "${output}" = "Machin_player [--simulation] [--seed] [42]" ]
}

@test "Machin indexer et Machin interface appellent leur binaire" {
	run "${MACHIN}" indexer
	[ "${output}" = "Machin_indexer" ]
	run "${MACHIN}" interface
	[ "${output}" = "Machin_interface" ]
}

@test "les arguments contenant des espaces sont transmis intacts" {
	run "${MACHIN}" indexer "un répertoire/avec des espaces" ""
	[ "${output}" = "Machin_indexer [un répertoire/avec des espaces] []" ]
}

@test "le code de sortie du binaire est celui du wrapper" {
	CODE_BOUCHON=3 run "${MACHIN}" player
	[ "${status}" -eq 3 ]
}

@test "un binaire mort d'un signal fait achever ses rapports de crash par le Python de son venv" {
	# https://github.com/dascritch/machincast/issues/413 : 139 = 128 + SIGSEGV.
	ecrire_bouchon "${VENV}" python
	CODE_BOUCHON=139 run "${MACHIN}" --config ici.toml player
	[ "${status}" -eq 139 ]
	[ "${lines[0]}" = "Machin_player [--config] [ici.toml]" ]
	[ "${lines[1]}" = "python [-m] [machincast.crash] [Machin_player] [--config] [ici.toml]" ]
}

@test "un binaire qui se termine sans signal ne fait rien achever" {
	ecrire_bouchon "${VENV}" python
	CODE_BOUCHON=3 run "${MACHIN}" interface
	[ "${status}" -eq 3 ]
	[ "${output}" = "Machin_interface" ]
}

@test "l'aide d'un binaire est celle du binaire lui-même" {
	run "${MACHIN}" player --help
	[ "${status}" -eq 0 ]
	[[ "${lines[0]}" == "usage: Machin_player "* ]]
}

@test "un binaire inconnu est refusé avec le code 2" {
	run --separate-stderr "${MACHIN}" diffusion
	[ "${status}" -eq 2 ]
	[[ "${stderr}" == *"binaire inconnu : diffusion"* ]]
	[[ "${stderr}" == *"player"*"indexer"*"interface"* ]]
}

@test "les anciens noms français des binaires et de --binaires sont refusés avec le code 2" {
	# https://github.com/dascritch/machincast/issues/356 : pas de compatibilité, les installations se refont de zéro.
	for ancien in lecture indexation dev-captures; do
		run --separate-stderr "${MACHIN}" "${ancien}"
		[ "${status}" -eq 2 ]
		[[ "${stderr}" == *"binaire inconnu : ${ancien}"* ]]
	done
	run --separate-stderr "${MACHIN}" --binaires
	[ "${status}" -eq 2 ]
}

@test "le wrapper appelle les binaires du venv du projet sans qu'il soit activé" {
	PATH="${BOUCHONS}:/usr/bin:/bin" run "${MACHIN}" player
	[ "${output}" = "Machin_player" ]
}

@test "le binaire du venv du projet passe avant celui du PATH" {
	printf '#!/bin/bash\necho "Machin_player du PATH"\n' >"${BOUCHONS}/Machin_player"
	chmod +x "${BOUCHONS}/Machin_player"
	run "${MACHIN}" player
	[ "${output}" = "Machin_player" ]
}

@test "sans venv dans le projet, le binaire est cherché dans le PATH" {
	rm -r "${PROJET}/.venv"
	ecrire_bouchon "${BOUCHONS}" Machin_indexer
	run "${MACHIN}" indexer
	[ "${output}" = "Machin_indexer" ]
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
	run "${MACHIN}" --binaries
	[ "${status}" -eq 0 ]
	local declares
	declares="$(sed -n 's/^Machin_\([a-z-]*\) = .*/\1/p' "${RACINE}/pyproject.toml" | LC_ALL=C sort)"
	[ -n "${declares}" ]
	[ "$(printf '%s\n' "${lines[@]}" | LC_ALL=C sort)" = "${declares}" ]
}

# ─── Configuration ─────────────────────────────────────────

@test "--config placé avant le binaire lui est transmis" {
	run "${MACHIN}" --config essai.toml player --simulation
	[ "${status}" -eq 0 ]
	[ "${output}" = "Machin_player [--config] [essai.toml] [--simulation]" ]
}

@test "--config=FICHIER placé avant le binaire lui est transmis" {
	run "${MACHIN}" --config=essai.toml indexer
	[ "${output}" = "Machin_indexer [--config] [essai.toml]" ]
}

@test "--config placé après le binaire est transmis tel quel" {
	run "${MACHIN}" player --config essai.toml
	[ "${output}" = "Machin_player [--config] [essai.toml]" ]
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
	[[ "${output}" == *"player"*"indexer"*"interface"* ]]
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
	for attendu in player indexer interface logs --config --binaries machincast.service 127; do
		[[ "${output}" == *"${attendu}"* ]] || { echo "absent de l'aide complète : ${attendu}"; return 1; }
	done
}

@test "Machin --help indique le machincast.toml du projet, lu par défaut, même appelé par un lien" {
	# https://github.com/dascritch/machincast/issues/76
	local reel lien
	reel="$(readlink -f "${PROJET}")"
	lien="${BATS_TEST_TMPDIR}/lien-Machin"
	ln -s "${MACHIN}" "${lien}"
	run "${lien}" --help
	[ "${status}" -eq 0 ]
	[[ "${output}" == *"${reel}/machincast.toml"* ]]
}

@test "Machin sans argument affiche l'aide minimale sur la sortie d'erreur avec le code 2" {
	run --separate-stderr "${MACHIN}"
	[ "${status}" -eq 2 ]
	[ -z "${output}" ]
	[[ "${stderr}" == *"Usage : Machin"* ]]
}

@test "une option inconnue du wrapper est refusée avec le code 2" {
	run --separate-stderr "${MACHIN}" --verbeux player
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

@test "avec le venv du dépôt, Machin player --version affiche la version de MachinCast sans activer le venv" {
	[ -x "${RACINE}/.venv/bin/Machin_player" ] || skip "venv du dépôt absent : python3 -m venv .venv && .venv/bin/pip install -e \".[dev]\""
	PATH="/usr/bin:/bin" run "${MACHIN_DU_DEPOT}" player --version
	[ "${status}" -eq 0 ]
	[[ "${output}" == "Machin_player (MachinCast) "* ]]
}
