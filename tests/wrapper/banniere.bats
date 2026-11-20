#!/usr/bin/env bats
# Machin banner : la bannière de MachinCast, lancée par install.sh et à chaque nouveau shell
# (https://github.com/dascritch/machincast/issues/517).

# ${lines} est rempli par « run » de bats.
# shellcheck disable=SC2154
setup() {
	load aide_test
	preparer_projet
	printf '[project]\nname = "machincast"\nversion = "1.2.3"\n' >"${PROJET}/pyproject.toml"
	# Ni service ni systemd : le bouchon de systemctl ne connaît pas l'unité.
	ecrire_systemctl absent
}

# Un bouchon de systemctl : « show » dit si l'unité est chargée, « is-active » si elle tourne.
# $1 : absent, arrete ou en-marche.
ecrire_systemctl() {
	cat >"${BOUCHONS}/systemctl" <<-FIN
		#!/bin/bash
		case "\$1" in
			show) [[ "$1" == absent ]] || echo loaded ;;
			is-active) [[ "$1" == en-marche ]] ;;
		esac
	FIN
	chmod +x "${BOUCHONS}/systemctl"
}

@test "Machin banner affiche la bannière, et le numéro de version à droite de sa dernière ligne" {
	run "${MACHIN}" banner
	[ "${status}" -eq 0 ]
	[ "${#lines[@]}" -eq 5 ]
	[ "${lines[0]}" = '        __  __            _     _        ____          _  ' ]
	[ "${lines[4]}" = '  \/   |_|  |_|\__,_|\___|_| |_|_|_| |_|\____\__,_|___/\__|  v1.2.3' ]
}

@test "Machin banner, sur un terminal, met le losange en orange, et lui seul" {
	FORCE_COLOR=1 run "${MACHIN}" banner
	[ "${status}" -eq 0 ]
	[ "${lines[0]}" = '        __  __            _     _        ____          _  ' ]
	[ "${lines[1]}" = $'\e[38;5;208m  /\\   \e[0m|  \\/  | __ _  ___| |__ (_)_ __  / ___|__ _ ___| |_ ' ]
	[ "${lines[3]}" = $'\e[38;5;208m \\  /  \e[0m| |  | | (_| | (__| | | | | | | | |__| (_| \\__ \\ |_ ' ]
}

@test "Machin banner n'ajoute aucune couleur avec NO_COLOR, même forcée" {
	NO_COLOR=1 FORCE_COLOR=1 run "${MACHIN}" banner
	[ "${status}" -eq 0 ]
	[[ "${output}" != *$'\e'* ]]
}

@test "Machin banner ne dit rien du service quand il n'est pas installé" {
	run "${MACHIN}" banner
	[ "${#lines[@]}" -eq 5 ]
}

@test "Machin banner dit que Machin player tourne" {
	ecrire_systemctl en-marche
	run "${MACHIN}" banner
	[ "${status}" -eq 0 ]
	[ "${lines[5]}" = 'Machin player : en marche' ]
}

@test "Machin banner dit que Machin player est arrêté" {
	ecrire_systemctl arrete
	run "${MACHIN}" banner
	[ "${status}" -eq 0 ]
	[ "${lines[5]}" = 'Machin player : arrêté' ]
}

@test "Machin banner ne prend pas d'argument" {
	run "${MACHIN}" banner extra
	[ "${status}" -eq 2 ]
}
