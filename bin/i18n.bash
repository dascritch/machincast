# shellcheck shell=bash
# Traduction des messages du wrapper Machin et d'install.sh (https://github.com/dascritch/machincast/issues/360).
#
# Les messages s'écrivent en anglais, entre apostrophes, pour que python -m machincast.catalog les relève :
#   t 'English message'                  le message traduit, sans retour à la ligne
#   tf 'Copied %s files\n' "${nombre}"   le message traduit, comme format de printf
# Leur traduction vient du catalogue de la langue de la session, src/machincast/locale/<langue>/LC_MESSAGES/
# machincast.bash, que python -m machincast.catalog écrit d'après le .po : ni gettext ni Python ne sont lancés. La
# langue se choisit comme dans machincast.i18n : LANGUAGE, LC_ALL, LC_MESSAGES puis LANG, la première renseignée ;
# l'anglais à défaut.

declare -gA MACHINCAST_MESSAGES=()

# La langue de la session, parmi celles qui ont un catalogue dans le répertoire de MachinCast $1 ; en à défaut.
langue_de_session() {
	local racine="$1" variable valeur candidat code candidats
	for variable in LANGUAGE LC_ALL LC_MESSAGES LANG; do
		valeur="${!variable-}"
		[[ -n "${valeur}" ]] || continue
		IFS=: read -r -a candidats <<<"${valeur}"
		for candidat in "${candidats[@]}"; do
			code="${candidat%%[_.@-]*}"
			code="${code,,}"
			[[ "${code}" == en ]] && break 2
			if [[ -n "${code}" && -r "${racine}/src/machincast/locale/${code}/LC_MESSAGES/machincast.bash" ]]; then
				printf '%s\n' "${code}"
				return
			fi
		done
		break
	done
	printf 'en\n'
}

# Charge le catalogue de la langue de la session ; $1 : le répertoire de MachinCast.
charger_messages() {
	local langue catalogue
	langue="$(langue_de_session "$1")"
	catalogue="$1/src/machincast/locale/${langue}/LC_MESSAGES/machincast.bash"
	if [[ "${langue}" != en && -r "${catalogue}" ]]; then
		# shellcheck source=/dev/null
		. "${catalogue}"
	fi
}

t() {
	printf '%s' "${MACHINCAST_MESSAGES["$1"]-$1}"
}

tf() {
	local format="${MACHINCAST_MESSAGES["$1"]-$1}"
	shift
	# shellcheck disable=SC2059
	printf -- "${format}" "$@"
}
