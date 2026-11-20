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

@test "Machin banner affiche la bannière, et le numéro de version à droite de sa première ligne" {
	run "${MACHIN}" banner
	[ "${status}" -eq 0 ]
	[ "${#lines[@]}" -eq 5 ]
	[ "${lines[0]}" = '        __  __            _     _        ____          _     v1.2.3' ]
	[ "${lines[4]}" = '  \/   |_|  |_|\__,_|\___|_| |_|_|_| |_|\____\__,_|___/\__|' ]
}

@test "Machin banner, sur un terminal, met le losange en orange, et lui seul" {
	FORCE_COLOR=1 run "${MACHIN}" banner
	[ "${status}" -eq 0 ]
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

# Un Machin_status de bouchon, qui répond comme « Machin status summary » : $1 la réponse du player.
ecrire_status() {
	cat >"${VENV}/Machin_status" <<-FIN
		#!/bin/bash
		[[ "\$1" == summary ]] || exit 2
		printf 'server\tservice\nradio\tRadio FMR\nplayer\t$1\n'
		if [[ "$1" == running ]]; then
			printf 'now\t09:00 → 11:00 : Matinale\nnext\t12:00 → 13:30 : Midi-info\n'
		fi
	FIN
	chmod +x "${VENV}/Machin_status"
}

@test "Machin banner, avec Machin status, dit à droite la version, la radio, le serveur et que Machin player tourne" {
	ecrire_status running
	run "${MACHIN}" banner
	[ "${status}" -eq 0 ]
	[ "${#lines[@]}" -eq 5 ]
	[[ "${lines[0]}" == *"v1.2.3" ]]
	[[ "${lines[1]}" == *" Radio FMR · service" ]]
	[[ "${lines[2]}" == *"Machin player : en marche" ]]
}

@test "Machin banner, quand Machin player tourne, dit à droite l'événement en cours et le suivant" {
	ecrire_status running
	run "${MACHIN}" banner
	[[ "${lines[3]}" == *"En cours : 09:00 → 11:00 : Matinale" ]]
	[[ "${lines[4]}" == *"Suivant : 12:00 → 13:30 : Midi-info" ]]
}

@test "Machin banner, quand Machin player est arrêté, ne dit aucun événement" {
	ecrire_status stopped
	run "${MACHIN}" banner
	[ "${#lines[@]}" -eq 5 ]
	[[ "${lines[2]}" == *"Machin player : arrêté" ]]
	[[ "${lines[3]}" != *"En cours"* ]]
	[[ "${lines[4]}" != *"Suivant"* ]]
}

@test "Machin banner garde son losange orange avec la colonne de droite" {
	ecrire_status running
	FORCE_COLOR=1 run "${MACHIN}" banner
	[[ "${lines[1]}" == $'\e[38;5;208m  /\\   \e[0m|'* ]]
}
