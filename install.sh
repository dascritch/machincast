#!/usr/bin/env bash
# Installation de MachinCast sur un poste Ubuntu LTS (https://github.com/dascritch/machincast/issues/40).
#
#   ./install.sh               installe, ou met à jour une installation existante : le script est relançable
#   ./install.sh --simulation  affiche les commandes sans rien exécuter
#   ./install.sh --dev         installe aussi les outils du poste de développement
#                              (https://github.com/dascritch/machincast/issues/77)
#   ./install.sh --service     installe aussi le service de diffusion : pour un ordinateur dédié à l'antenne
#                              (https://github.com/dascritch/machincast/issues/22)
#                              et le minuteur de la purge quotidienne de la base, à midi
#                              (https://github.com/dascritch/machincast/issues/268)
#   ./install.sh --remove-service   retire ce service et ce minuteur, la diffusion se lance de nouveau à la main
#   ./install.sh --desktop      dépose aussi le raccourci de l'interface sur le bureau, sans le demander
#   ./install.sh --no-desktop ne le dépose pas, sans le demander (https://github.com/dascritch/machincast/issues/62)
#   ./install.sh --stop-programs   arrête les programmes de MachinCast en cours, sans le demander
#   ./install.sh --leave-programs   les laisse tourner, sans le demander
#                              (https://github.com/dascritch/machincast/issues/254)
#   ./install.sh --help        aide
#
# À lancer depuis le répertoire de MachinCast (release décompressée ou dépôt git), avec son propre compte :
# le script demande sudo pour les seules étapes qui l'exigent. L'installation reste en place ; /opt/machincast
# est un lien vers ce répertoire. Le service systemd ne l'est que sur demande, avec --service
# (https://github.com/dascritch/machincast/issues/22).
#
# Règles : doc/fr/regles/wrapper.md. Documentation : INSTALL.md (https://github.com/dascritch/machincast/issues/71).

set -euo pipefail

RACINE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
# Messages en anglais, traduits dans la langue de la session (https://github.com/dascritch/machincast/issues/360).
# shellcheck source=bin/i18n.bash
. "${RACINE}/bin/i18n.bash"
charger_messages "${RACINE}"
LIEN_INSTALLATION="/opt/machincast"
LIEN_WRAPPER="/usr/local/bin/Machin"
LIEN_COMPLETION="/usr/share/bash-completion/completions/Machin"
# Service de diffusion, facultatif (https://github.com/dascritch/machincast/issues/22) : le même nom dans bin/Machin
# et machincast.installation.
UNITE="machincast.service"
FICHIER_UNITE="/etc/systemd/system/${UNITE}"
FICHIER_REGLE="/etc/polkit-1/rules.d/50-machincast.rules"
# Purge quotidienne de la base, installée avec le service (https://github.com/dascritch/machincast/issues/268) : les
# mêmes noms dans machincast.installation.
UNITE_PURGE="machincast-purge.service"
MINUTEUR_PURGE="machincast-purge.timer"
FICHIER_UNITE_PURGE="/etc/systemd/system/${UNITE_PURGE}"
FICHIER_MINUTEUR_PURGE="/etc/systemd/system/${MINUTEUR_PURGE}"
# Le service tourne sous son propre compte, avec son PipeWire et son WirePlumber
# (https://github.com/dascritch/machincast/issues/381) : les mêmes noms dans machincast.installation.
COMPTE_SERVICE="machincast"
DOSSIER_DU_COMPTE_SERVICE="/var/lib/machincast"
DOSSIER_D_EXECUTION_SERVICE="/run/machincast"
DOSSIER_DES_LOGS="/var/log/machincast"
UNITE_PIPEWIRE="machincast-pipewire.service"
UNITE_WIREPLUMBER="machincast-wireplumber.service"
FICHIER_UNITE_PIPEWIRE="/etc/systemd/system/${UNITE_PIPEWIRE}"
FICHIER_UNITE_WIREPLUMBER="/etc/systemd/system/${UNITE_WIREPLUMBER}"
FICHIER_TMPFILES="/etc/tmpfiles.d/machincast.conf"
FICHIER_LOGROTATE="/etc/logrotate.d/machincast"
DOSSIER_WIREPLUMBER_SERVICE="/etc/machincast"
FICHIER_WIREPLUMBER_SERVICE="${DOSSIER_WIREPLUMBER_SERVICE}/wireplumber/wireplumber.conf.d/50-machincast.conf"
# La carte de l'antenne, cachée aux sessions du poste : elle est au PipeWire du service.
FICHIER_WIREPLUMBER_BUREAU="/etc/wireplumber/wireplumber.conf.d/50-machincast.conf"
# Raccourci de l'interface (https://github.com/dascritch/machincast/issues/62) : dans le menu des applications du
# compte, et sur son bureau s'il le veut. Le même nom que RACCOURCI de machincast.interface.application.
RACCOURCI="machincast.desktop"
DOSSIER_APPLICATIONS="${XDG_DATA_HOME:-${HOME}/.local/share}/applications"
# L'icône de MachinCast dans le thème d'icônes du compte, sous le nom qu'annoncent les sorties audio à PipeWire et à
# PulseAudio (machincast.audio.ICONE, https://github.com/dascritch/machincast/issues/296).
ICONE_DU_THEME="${XDG_DATA_HOME:-${HOME}/.local/share}/icons/hicolor/512x512/apps/machincast.png"
CONFIGURATION="${RACINE}/machincast.toml"
VENV="${RACINE}/.venv"
ROLES=(player indexer interface)

# Prérequis système : ce que pip ne peut pas fournir (https://github.com/dascritch/machincast/issues/51).
# Même liste que CLAUDE.md, sans les outils de développement.
PAQUETS=(
	python3-venv python3-dev build-essential pkg-config libgirepository-2.0-dev libcairo2-dev
	gir1.2-gstreamer-1.0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad
	gstreamer1.0-alsa gstreamer1.0-pulseaudio gstreamer1.0-pipewire pipewire-bin libmagic1t64 postgresql bash-completion
	acl wireplumber
)
# Outils du poste de développement, installés par --dev : ceux de CLAUDE.md.
PAQUETS_DEV=(bats shellcheck desktop-file-utils pipewire wireplumber)

SIMULATION=false
DEV=false
SERVICE=false
RETIRER_SERVICE=false
# Raccourci sur le bureau : demander, oui ou non.
BUREAU=demander
# Service déjà installé mais pas à jour, sans --service (https://github.com/dascritch/machincast/issues/376) : le mettre à
# jour, demandé à la question.
METTRE_A_JOUR_LE_SERVICE=false
# Programmes de MachinCast en cours (https://github.com/dascritch/machincast/issues/254) : demander, oui ou non ;
# ceux qu'install.sh a arrêtés, à relancer à la fin, même après un échec.
ARRETER=demander
ARRETER_DEMANDE=0
ETAT_DES_PROGRAMMES=""
PROGRAMMES_ARRETES=false
SERVICE_ARRETE=false
# Secondes laissées à un programme pour s'arrêter, avant de l'y forcer.
DELAI_D_ARRET=15
# Accès au réseau (https://github.com/dascritch/machincast/issues/376) : une seule de ces adresses qui répond suffit,
# quelle que soit sa réponse. Sans réseau, apt et pip ne peuvent rien installer ni mettre à jour.
ADRESSES_DU_RESEAU=(
	https://dascritch.net/machincast_test_its_connection
	https://cpu.pm/machincast_test_its_connection
	https://google.com
)
DELAI_DU_RESEAU=10
RESEAU=true
UTILISATEUR="$(id -un)"

aide() {
	tf 'Usage: ./install.sh [--simulation] [--dev] [--service | --remove-service] [--desktop | --no-desktop]
                    [--stop-programs | --leave-programs]

Installs MachinCast in place, from this directory (%s), after checking the network access, without
which a first installation stops, and an update goes on without updating the packages and dependencies:
  0. running MachinCast programs, under all the accounts of the computer: Machin player (broadcast
     service, trial broadcast, simulation), Machin indexer, Machin interface. If they are running,
     the question is asked whether to stop them during the installation, except with --stop-programs or
     --leave-programs; with no possible answer, they go on. Stopped, the broadcast goes silent
     until the end, and the interface loses its unsaved cards. At the end, even after a failure,
     install.sh relaunches the broadcast service, and the trial broadcast and the interface of %s;
     it tells what remains to reopen: the indexing, and the programs of the other accounts;
  1. system packages (apt);
  2. isolated Python virtual environment and dependencies (pip);
  3. machincast.toml, copied from the model if it does not exist;
  4. PostgreSQL role of the account %s (without any particular right), production and test databases
     that it owns, MachinCast roles, schema;
  5. authorisation of %s to the roles %s, systemd-journal group;
  6. links %s, %s and the bash autocompletion;
  7. check of the GStreamer version and plugins, and of the audio output;
  8. shortcut of the interface in the applications menu of %s, and, if wanted,
     on the desktop: the question is asked, except with --desktop or --no-desktop; MachinCast
     icon in the icon theme, for the sound settings of the computer.
With --dev, also the tools of the development computer: %s (apt) and the
test dependencies (pip, extra [dev]), for Machin dev and Machin dev-test.
With --service, also the broadcast service %s, only for a computer dedicated to the
on-air output, whose on-air output is a sound card, through the PipeWire or ALSA output (otherwise
install.sh stops and recommends another one): Machin player starts with the computer, under its
own account %s, with its own PipeWire, and restarts after a crash. %s joins the group %s, which
reads its logs (%s) and pre-listens to the on-air output; the service reads MachinCast, and the
on-air card is hidden from the sessions of the computer. A polkit rule lets it start, stop and
restart with the password of an administrator; a systemd timer, %s, launches every day at noon
Machin purge, which erases from the database what exceeds the expiry duration. Without --service, none
of this is installed: the broadcast and the purge are launched by hand. A service installed before is
checked: if it is not up to date for this version, the question is asked whether to update it.

Can be run again: each step already done is left as is.
To run with your own account, not with sudo: the script asks for sudo when needed.

Options:
  --simulation  shows the commands without running anything
  --dev         also installs the tools of the development computer
  --service     also installs the broadcast service (computer dedicated to the on-air output only)
  --remove-service
                removes the broadcast service, its PipeWire, its account, its polkit rule and the purge
                timer; the logs stay
  --desktop      also puts the shortcut of the interface on the desktop, without asking
  --no-desktop does not put it on the desktop, without asking
  --stop-programs
                stops the running MachinCast programs, without asking
  --leave-programs
                lets them run during the installation, without asking
  -h, --help    this help
' "${RACINE}" "${UTILISATEUR}" "${UTILISATEUR}" "${UTILISATEUR}" "${ROLES[*]}" "${LIEN_INSTALLATION}" "${LIEN_WRAPPER}" "${UTILISATEUR}" "${PAQUETS_DEV[*]}" "${UNITE}" "${COMPTE_SERVICE}" "${UTILISATEUR}" "${COMPTE_SERVICE}" "${DOSSIER_DES_LOGS}" "${MINUTEUR_PURGE}"
}

# Les messages s'écrivent en anglais, en format de printf entre apostrophes, suivi de leurs valeurs : etape, info et
# echec les traduisent dans la langue de la session (bin/i18n.bash, https://github.com/dascritch/machincast/issues/360).
etape() {
	printf '\n==> '
	tf "$@"
	printf '\n'
}

info() {
	printf '    '
	tf "$@"
	printf '\n'
}

echec() {
	{
		tf 'install.sh: %s\n' "$(tf "$@")"
	} >&2
	exit 1
}

# Exécute une commande, ou l'affiche seulement en simulation.
executer() {
	if "${SIMULATION}"; then
		printf '    [simulation] %s\n' "$*"
	else
		"$@"
	fi
}

# Vrai si l'adresse répond, quelle que soit sa réponse : par curl, ou, sans curl, par le python3 du système.
repond() {
	local adresse="$1"
	if command -v curl >/dev/null; then
		curl --head --silent --output /dev/null --max-time "${DELAI_DU_RESEAU}" "${adresse}"
		return
	fi
	python3 -c '
import sys, urllib.error, urllib.request
try:
	urllib.request.urlopen(urllib.request.Request(sys.argv[1], method="HEAD"), timeout=float(sys.argv[2]))
except urllib.error.HTTPError:
	pass
except OSError:
	sys.exit(1)
' "${adresse}" "${DELAI_DU_RESEAU}"
}

# Sans réseau, une première installation ne peut pas aller plus loin ; une mise à jour continue, sans apt ni pip.
verifier_reseau() {
	etape 'Network access'
	local adresse
	for adresse in "${ADRESSES_DU_RESEAU[@]}"; do
		if repond "${adresse}"; then
			info '%s answers' "${adresse}"
			return
		fi
		info '%s does not answer' "${adresse}"
	done
	if [[ ! -x "${VENV}/bin/python" ]]; then
		echec 'no network access: a first installation needs it, for the system packages and the Python dependencies'
	fi
	RESEAU=false
	info 'no network access: the system packages and the Python dependencies will not be updated; the installation goes on'
}

verifier_systeme() {
	etape 'System'
	[[ "$(id -u)" -ne 0 ]] || echec 'run install.sh with your own account, without sudo: it asks for it when needed'
	[[ -r /etc/os-release ]] || echec '/etc/os-release unreadable: system not recognised'
	local id version
	id="$(. /etc/os-release && printf '%s' "${ID:-}")"
	version="$(. /etc/os-release && printf '%s' "${VERSION_ID:-}")"
	# Les LTS d'Ubuntu sortent en avril des années paires : 24.04, 26.04…
	if [[ "${id}" != ubuntu ]] || ! [[ "${version}" =~ ^[0-9]*[02468]\.04$ ]]; then
		"${SIMULATION}" || echec 'Ubuntu LTS required (target: 26.04 LTS), found: %s %s' "${id}" "${version}"
		info 'unsupported system (%s %s), ignored in simulation' "${id}" "${version}"
	elif [[ "${version}" != 26.04 ]]; then
		info 'Ubuntu %s LTS: the target is 26.04 LTS, the installation goes on' "${version}"
	else
		info 'Ubuntu %s LTS' "${version}"
	fi
}

# Programmes de MachinCast en cours (https://github.com/dascritch/machincast/issues/254), lus par
# machincast.programs avec le python3 du système : le venv peut manquer, ou changer pendant l'installation.
programmes() {
	PYTHONPATH="${RACINE}/src" python3 -m machincast.programs "$@"
}

vouloir_arreter() {
	local reponse
	case "${ARRETER}" in
		oui) return 0 ;;
		non) return 1 ;;
	esac
	if "${SIMULATION}"; then
		info '[simulation] question: stop them during the installation?'
		return 0
	fi
	if [[ ! -t 0 ]]; then
		info 'no question without a terminal: ./install.sh --stop-programs stops them'
		return 1
	fi
	read -r -p "    $(t 'Stop them during the installation, then relaunch them? [y/N] ')" reponse
	# Oui : « o » en français, « y » en anglais.
	[[ "${reponse}" =~ ^[oOyY] ]]
}

# Attend la fin des processus, puis force celle des retardataires ; ceux d'un autre compte, par sudo.
attendre_l_arret() {
	local pid du_compte restant attente
	for ((attente = 0; attente < DELAI_D_ARRET; attente++)); do
		restant=false
		for pid in "$@"; do
			[[ -e "/proc/${pid%:*}" ]] && restant=true
		done
		"${restant}" || return 0
		sleep 1
	done
	for pid in "$@"; do
		du_compte="${pid#*:}"
		pid="${pid%:*}"
		[[ -e "/proc/${pid}" ]] || continue
		info 'pid %s still there after %s s: forced stop' "${pid}" "${DELAI_D_ARRET}"
		if [[ "${du_compte}" == yes ]]; then
			kill -KILL "${pid}" 2>/dev/null || true
		else
			sudo kill -KILL "${pid}" || true
		fi
	done
}

arreter_les_programmes() {
	etape 'Running MachinCast programs'
	ETAT_DES_PROGRAMMES="$(mktemp --tmpdir machincast-programmes.XXXXXX.json)"
	local liste
	if ! liste="$(programmes list --state "${ETAT_DES_PROGRAMMES}")"; then
		info 'running programs unreadable: the installation goes on without stopping them'
		return
	fi
	if [[ -z "${liste}" ]]; then
		info 'none'
		return
	fi
	local pid du_compte service libelle
	while IFS=$'\t' read -r pid du_compte service libelle; do
		info '%s, pid %s' "${libelle}" "${pid}"
	done <<<"${liste}"
	info 'an update, and its database migrations, must not happen under them'
	info 'stopped, the broadcast goes silent until the end of the installation; the interface loses its unsaved cards'
	if ! vouloir_arreter; then
		info 'they go on: the database may change under them, relaunch them after the installation'
		return
	fi
	PROGRAMMES_ARRETES=true
	trap relancer_les_programmes EXIT
	local arretes=()
	while IFS=$'\t' read -r pid du_compte service libelle; do
		if [[ "${service}" == yes ]]; then
			if ! "${SERVICE_ARRETE}"; then
				executer sudo systemctl stop "${UNITE}"
				SERVICE_ARRETE=true
			fi
		elif [[ "${du_compte}" == yes ]]; then
			executer kill -TERM "${pid}"
			arretes+=("${pid}:oui")
		else
			executer sudo kill -TERM "${pid}"
			arretes+=("${pid}:non")
		fi
	done <<<"${liste}"
	if ! "${SIMULATION}" && ((${#arretes[@]} > 0)); then
		attendre_l_arret "${arretes[@]}"
	fi
	info 'stopped: relaunched at the end of the installation'
}

# À la fin, ou à la sortie d'install.sh après un échec : une seule fois.
relancer_les_programmes() {
	"${PROGRAMMES_ARRETES}" || return 0
	PROGRAMMES_ARRETES=false
	etape 'Relaunch of the MachinCast programs'
	if "${SERVICE_ARRETE}"; then
		if "${RETIRER_SERVICE}"; then
			info 'broadcast service removed: not relaunched'
		else
			executer sudo systemctl start "${UNITE}" || info 'broadcast service not relaunched: Machin logs tells why'
		fi
	fi
	local options=() ligne
	"${SIMULATION}" && options+=(--simulation)
	while IFS= read -r ligne; do
		info '%s' "${ligne}"
	done < <(programmes restart --state "${ETAT_DES_PROGRAMMES}" "${options[@]}")
	rm --force "${ETAT_DES_PROGRAMMES}" # fichier de MachinCast : état des programmes arrêtés, temporaire
}

installer_paquets() {
	etape 'System packages'
	if ! "${RESEAU}"; then
		info 'not updated: no network access'
		return
	fi
	executer sudo apt-get update
	local paquets=("${PAQUETS[@]}")
	"${DEV}" && paquets+=("${PAQUETS_DEV[@]}")
	executer sudo apt-get install --yes "${paquets[@]}"
}

installer_venv() {
	etape 'Python virtual environment'
	# Jamais --system-site-packages : toutes les dépendances Python viennent de pip.
	if [[ -x "${VENV}/bin/python" ]]; then
		info '%s already exists' "${VENV}"
	else
		executer python3 -m venv "${VENV}"
	fi
	if ! "${RESEAU}"; then
		info 'Python dependencies not updated: no network access'
		return
	fi
	executer "${VENV}/bin/pip" install --upgrade pip
	if "${DEV}"; then
		executer "${VENV}/bin/pip" install --editable "${RACINE}[dev]"
	else
		executer "${VENV}/bin/pip" install --editable "${RACINE}"
	fi
}

preparer_configuration() {
	etape 'Configuration'
	if [[ -e "${CONFIGURATION}" ]]; then
		info '%s already exists: kept' "${CONFIGURATION}"
	else
		executer cp "${RACINE}/machincast.exemple.toml" "${CONFIGURATION}"
		info 'to adapt: audio output, devices, outputs (see doc/fr/spec.md § 9)'
	fi
}

# Appelle machincast.installation, qui lit la configuration et applique le schéma. En simulation, tant que
# machincast.toml n'a pas été copié, le modèle tient lieu de configuration.
installation() {
	local configuration="${CONFIGURATION}"
	if "${SIMULATION}" && [[ ! -e "${configuration}" ]]; then
		configuration="${RACINE}/machincast.exemple.toml"
	fi
	"${VENV}/bin/python" -m machincast.installation "$1" --config "${configuration}"
}

# Vrai si la requête, qui reçoit le nom en variable psql :'nom', renvoie 1. En simulation, rien n'est demandé
# à PostgreSQL : l'objet est supposé absent, pour afficher toutes les commandes.
existe_en_base() {
	local requete="$1" nom="$2"
	"${SIMULATION}" && return 1
	[[ "$(sudo -u postgres psql --no-psqlrc --tuples-only --no-align --variable=nom="${nom}" <<<"${requete}")" == 1 ]]
}

preparer_postgresql() {
	etape 'PostgreSQL'
	[[ "${UTILISATEUR}" =~ ^[a-z_][a-z0-9_-]*$ ]] || echec 'unexpected account name for PostgreSQL: %s' "${UTILISATEUR}"
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info '[simulation] databases read in %s once the virtual environment is created' "${CONFIGURATION}"
		return
	fi
	local lus socket production test
	lus="$(installation databases)" || echec 'configuration %s to correct, then run install.sh again' "${CONFIGURATION}"
	{
		read -r socket
		read -r production
		read -r test
	} <<<"${lus}"

	# Le compte courant n'a aucun droit particulier sur le serveur (ni CREATEDB ni CREATEROLE) : tout ce qui en
	# demande est fait par l'utilisateur postgres. Le compte reçoit seulement la propriété des deux bases, qui lui
	# permet d'y appliquer le schéma (doc/fr/spec.md § 3.2).
	if existe_en_base "SELECT 1 FROM pg_roles WHERE rolname = :'nom'" "${UTILISATEUR}"; then
		info 'PostgreSQL role %s exists' "${UTILISATEUR}"
	else
		executer sudo -u postgres createuser "${UTILISATEUR}"
	fi
	local base
	for base in "${production}" "${test}"; do
		if existe_en_base "SELECT 1 FROM pg_database WHERE datname = :'nom'" "${base}"; then
			info 'database %s exists' "${base}"
		else
			executer sudo -u postgres createdb --host="${socket}" --owner="${UTILISATEUR}" "${base}"
		fi
	done
	# Les rôles de groupe appartiennent au serveur. La migration ne les crée que s'ils manquent, ce qui demanderait
	# CREATEROLE : postgres les crée donc d'abord.
	if "${SIMULATION}"; then
		info '[simulation] sudo -u postgres psql: CREATE ROLE %s NOLOGIN, if they do not exist' "${ROLES[*]/#/machincast_}"
	else
		sudo -u postgres psql --no-psqlrc --quiet --set=ON_ERROR_STOP=1 <<-'SQL'
			DO $$
			DECLARE
				role text;
			BEGIN
				FOREACH role IN ARRAY ARRAY['machincast_player', 'machincast_indexer', 'machincast_interface'] LOOP
					IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = role) THEN
						EXECUTE format('CREATE ROLE %I NOLOGIN', role);
					END IF;
				END LOOP;
			END;
			$$;
		SQL
		info 'roles machincast_player, machincast_indexer and machincast_interface present'
	fi
	executer "${VENV}/bin/python" -m machincast.installation migrate --config "${CONFIGURATION}"
	etape 'Roles'
	# Les rôles appartiennent au serveur : une seule autorisation vaut pour les deux bases. Elle est donnée par
	# l'utilisateur postgres, qui peut attribuer les rôles quel que soit le compte qui les a créés. Sans héritage
	# des droits : chaque binaire endosse son rôle par SET ROLE (doc/fr/spec.md § 3.2).
	if "${SIMULATION}"; then
		info '[simulation] sudo -u postgres psql: GRANT machincast_player, machincast_indexer, machincast_interface TO %s WITH INHERIT FALSE, SET TRUE' "${UTILISATEUR}"
	else
		sudo -u postgres psql --no-psqlrc --quiet --set=ON_ERROR_STOP=1 --variable=nom="${UTILISATEUR}" <<-'SQL'
			GRANT machincast_player, machincast_indexer, machincast_interface TO :"nom" WITH INHERIT FALSE, SET TRUE;
		SQL
		info '%s can assume the roles %s' "${UTILISATEUR}" "${ROLES[*]}"
	fi
	# Un superutilisateur endosse tous les rôles sans autorisation, et peut tout faire sur le serveur : l'installation
	# voulue ne donne au compte aucun droit particulier (doc/fr/spec.md § 3.2). install.sh ne retire pas ce droit, qui peut
	# servir à autre chose sur le poste : il le signale.
	if existe_en_base "SELECT 1 FROM pg_roles WHERE rolname = :'nom' AND rolsuper" "${UTILISATEUR}"; then
		info 'warning: %s is a PostgreSQL superuser, which MachinCast does not require; to' "${UTILISATEUR}"
		info 'remove it: sudo -u postgres psql -c %s' "'ALTER ROLE \"${UTILISATEUR}\" NOSUPERUSER'"
	fi
}

autoriser_journal() {
	etape 'System journal'
	if id -nG "${UTILISATEUR}" | tr ' ' '\n' | grep -qx systemd-journal; then
		info '%s already belongs to the systemd-journal group' "${UTILISATEUR}"
	else
		# systemd-journal, jamais adm : la lecture du journal sans droits d'administration.
		executer sudo usermod --append --groups systemd-journal "${UTILISATEUR}"
		info 'effective after the computer restarts'
	fi
}

relier() {
	local cible="$1" lien="$2"
	if [[ -e "${lien}" && ! -L "${lien}" ]]; then
		echec '%s exists and is not a symbolic link: move it before running install.sh again' "${lien}"
	fi
	if [[ -L "${lien}" && "$(readlink "${lien}")" == "${cible}" ]]; then
		info '%s → %s' "${lien}" "${cible}"
	else
		executer sudo ln --symbolic --force --no-dereference "${cible}" "${lien}"
	fi
}

installer_liens() {
	etape 'Links'
	relier "${RACINE}" "${LIEN_INSTALLATION}"
	relier "${LIEN_INSTALLATION}/bin/Machin" "${LIEN_WRAPPER}"
	relier "${LIEN_INSTALLATION}/bash-completion/Machin" "${LIEN_COMPLETION}"
}

verifier_greffons() {
	etape 'GStreamer version and plugins, audio output'
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info '[simulation] check done once the virtual environment is created'
		return
	fi
	installation check || echec 'install the indicated packages, then run install.sh again'
}

# Installe le fichier rédigé par machincast.installation, s'il diffère de celui en place ; vrai s'il a changé.
installer_fichier() {
	local action="$1" destination="$2" redige
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info '[simulation] %s, written by machincast.installation %s' "${destination}" "${action}"
		return 0
	fi
	redige="$(mktemp)"
	# Appelée par if ou ||, la fonction ne s'arrête pas d'elle-même sur une erreur (set -e) : jamais de fichier vide.
	installation "${action}" >"${redige}" || echec 'machincast.installation %s failed: %s not installed' "${action}" "${destination}"
	if [[ -r "${destination}" ]] && cmp --silent "${redige}" "${destination}"; then
		info '%s is up to date' "${destination}"
		rm --force "${redige}" # fichier de MachinCast : unité ou règle rédigée, temporaire
		return 1
	fi
	executer sudo install -D --mode=644 --owner=root --group=root "${redige}" "${destination}"
	rm --force "${redige}" # fichier de MachinCast : unité ou règle rédigée, temporaire
	return 0
}

# Installe pour le compte, sans sudo, le raccourci rédigé par machincast.installation, s'il diffère de celui en place
# ou n'a pas les droits voulus ; vrai s'il a changé.
installer_raccourci_en() {
	local destination="$1" droits="$2" redige
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info '[simulation] %s, written by machincast.installation shortcut' "${destination}"
		return 0
	fi
	redige="$(mktemp)"
	installation shortcut >"${redige}" || echec 'machincast.installation shortcut failed: %s not installed' "${destination}"
	if [[ -r "${destination}" ]] && cmp --silent "${redige}" "${destination}" \
		&& [[ "$(stat --format=%a "${destination}")" == "${droits}" ]]; then
		info '%s is up to date' "${destination}"
		rm --force "${redige}" # fichier de MachinCast : raccourci rédigé, temporaire
		return 1
	fi
	executer install -D --mode="${droits}" "${redige}" "${destination}"
	rm --force "${redige}" # fichier de MachinCast : raccourci rédigé, temporaire
	return 0
}

# Le dossier du bureau du compte, « Bureau » en français ; rien s'il n'en a pas.
dossier_du_bureau() {
	local dossier
	command -v xdg-user-dir >/dev/null || return 0
	dossier="$(xdg-user-dir DESKTOP)"
	# Sans bureau configuré, xdg-user-dir répond le dossier personnel.
	if [[ -n "${dossier}" && "${dossier}" != "${HOME}" ]]; then
		printf '%s\n' "${dossier}"
	fi
}

# Vrai si le raccourci va sur le bureau : déjà là, demandé par --desktop, ou accepté à la question.
vouloir_le_bureau() {
	local raccourci="$1" reponse
	case "${BUREAU}" in
		oui) return 0 ;;
		non) return 1 ;;
	esac
	[[ -e "${raccourci}" ]] && return 0
	if "${SIMULATION}"; then
		info '[simulation] question: also put the shortcut on the desktop?'
		return 0
	fi
	if [[ ! -t 0 ]]; then
		info 'no question without a terminal: ./install.sh --desktop puts it on the desktop'
		return 1
	fi
	read -r -p "    $(t 'Also put the MachinCast shortcut on the desktop? [Y/n] ')" reponse
	[[ ! "${reponse}" =~ ^[nN] ]]
}

# Installe pour le compte, sans sudo, l'icône de MachinCast dans son thème d'icônes, si elle diffère de celle en place.
installer_icone() {
	local destination="$1" source="${RACINE}/src/machincast/interface/machincast.png"
	if [[ -r "${destination}" ]] && cmp --silent "${source}" "${destination}"; then
		info '%s is up to date' "${destination}"
		return
	fi
	executer install -D --mode=644 "${source}" "${destination}"
}

installer_raccourci() {
	etape 'Shortcut of the interface'
	installer_raccourci_en "${DOSSIER_APPLICATIONS}/${RACCOURCI}" 644 || true
	installer_icone "${ICONE_DU_THEME}"
	local bureau
	bureau="$(dossier_du_bureau)"
	if [[ -z "${bureau}" ]]; then
		info 'no desktop folder for %s: shortcut in the applications menu only' "${UTILISATEUR}"
		return
	fi
	if vouloir_le_bureau "${bureau}/${RACCOURCI}"; then
		# Exécutable : Plasma lance alors le raccourci du bureau sans demander de confirmation.
		installer_raccourci_en "${bureau}/${RACCOURCI}" 755 || true
	elif [[ -e "${bureau}/${RACCOURCI}" ]]; then
		info '%s/%s left as is' "${bureau}" "${RACCOURCI}"
	else
		info 'no shortcut on the desktop; ./install.sh --desktop puts it there'
	fi
}

# Vrai si le fichier en place est celui que rédige machincast.installation ; sans rien installer.
fichier_a_jour() {
	local action="$1" destination="$2" redige
	redige="$(mktemp)"
	if ! installation "${action}" >"${redige}"; then
		rm --force "${redige}" # fichier de MachinCast : unité ou règle rédigée, temporaire
		return 1
	fi
	if [[ -r "${destination}" ]] && cmp --silent "${redige}" "${destination}"; then
		rm --force "${redige}" # fichier de MachinCast : unité ou règle rédigée, temporaire
		return 0
	fi
	rm --force "${redige}" # fichier de MachinCast : unité ou règle rédigée, temporaire
	return 1
}

# Les fichiers du service installé qui ne sont plus ceux de cette version de MachinCast, un par ligne : après une mise
# à jour, l'unité d'avant peut appeler un programme qui n'existe plus (https://github.com/dascritch/machincast/issues/376).
fichiers_du_service_perimes() {
	local paire
	for paire in "unit:${FICHIER_UNITE}" "pipewire-unit:${FICHIER_UNITE_PIPEWIRE}" \
		"wireplumber-unit:${FICHIER_UNITE_WIREPLUMBER}" "wireplumber-service:${FICHIER_WIREPLUMBER_SERVICE}" \
		"wireplumber-desktop:${FICHIER_WIREPLUMBER_BUREAU}" "tmpfiles:${FICHIER_TMPFILES}" \
		"logrotate:${FICHIER_LOGROTATE}" "purge-unit:${FICHIER_UNITE_PURGE}" "purge-timer:${FICHIER_MINUTEUR_PURGE}" \
		"rule:${FICHIER_REGLE}"; do
		fichier_a_jour "${paire%%:*}" "${paire#*:}" || printf '%s\n' "${paire#*:}"
	done
}

vouloir_mettre_a_jour_le_service() {
	local reponse
	if "${SIMULATION}"; then
		info '[simulation] question: update the broadcast service?'
		return 0
	fi
	if [[ ! -t 0 ]]; then
		info 'no question without a terminal: ./install.sh --service updates it'
		return 1
	fi
	read -r -p "    $(t 'Update the broadcast service? It restarts if it is running. [Y/n] ')" reponse
	[[ ! "${reponse}" =~ ^[nN] ]]
}

# Sans --service, le service déjà installé est vérifié : pas à jour, la question est posée de le mettre à jour.
verifier_le_service_installe() {
	if [[ ! -e "${FICHIER_UNITE}" ]]; then
		info 'not installed: the broadcast is launched by hand, with Machin player'
		info 'on a computer dedicated to the on-air output: ./install.sh --service'
		return
	fi
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info '[simulation] installed service compared with machincast.installation once the virtual environment is created'
		return
	fi
	local perimes
	perimes="$(fichiers_du_service_perimes)"
	if [[ -z "${perimes}" ]]; then
		info 'installed and up to date'
		return
	fi
	info 'installed, but not up to date for this version of MachinCast, it may no longer start: %s' "${perimes//$'\n'/, }"
	if vouloir_mettre_a_jour_le_service; then
		METTRE_A_JOUR_LE_SERVICE=true
	else
		info 'left as is; ./install.sh --service updates it'
	fi
}

# Le compte du service et son groupe, que rejoint le compte de MachinCast : il lit ses logs et pré-écoute l'antenne.
creer_le_compte_du_service() {
	if getent passwd "${COMPTE_SERVICE}" >/dev/null; then
		info 'account %s present' "${COMPTE_SERVICE}"
	else
		executer sudo useradd --system --user-group --home-dir "${DOSSIER_DU_COMPTE_SERVICE}" --no-create-home \
			--shell /usr/sbin/nologin --comment 'MachinCast broadcast service' "${COMPTE_SERVICE}"
	fi
	if id -nG "${UTILISATEUR}" | tr ' ' '\n' | grep -qx "${COMPTE_SERVICE}"; then
		info '%s already belongs to the %s group' "${UTILISATEUR}" "${COMPTE_SERVICE}"
	else
		executer sudo usermod --append --groups "${COMPTE_SERVICE}" "${UTILISATEUR}"
		info 'effective after the computer restarts'
	fi
}

# Le rôle PostgreSQL du compte du service : il se connecte par authentification peer, et n'endosse que le rôle de
# Machin player, sans en hériter les droits (doc/fr/spec.md § 3.2).
autoriser_le_service_en_base() {
	if "${SIMULATION}"; then
		info '[simulation] sudo -u postgres psql: CREATE ROLE %s LOGIN; GRANT machincast_player TO %s WITH INHERIT FALSE, SET TRUE' \
			"${COMPTE_SERVICE}" "${COMPTE_SERVICE}"
		return
	fi
	sudo -u postgres psql --no-psqlrc --quiet --set=ON_ERROR_STOP=1 <<-'SQL'
		DO $$
		BEGIN
			IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'machincast') THEN
				CREATE ROLE machincast LOGIN;
			END IF;
		END;
		$$;
		GRANT machincast_player TO machincast WITH INHERIT FALSE, SET TRUE;
	SQL
	info '%s can assume the role machincast_player' "${COMPTE_SERVICE}"
}

# Le compte du service lit MachinCast : son programme, son environnement virtuel et sa configuration. Les droits de
# lecture sont donnés par des ACL, sans rien changer d'autre ; les répertoires parents, au compte, sont seulement
# traversés.
donner_la_lecture_au_service() {
	local chemin parent
	chemin="$(realpath "$1")"
	parent="$(dirname "${chemin}")"
	while [[ "${parent}" != / ]]; do
		if [[ -O "${parent}" ]]; then
			executer setfacl --modify="u:${COMPTE_SERVICE}:x" "${parent}"
		fi
		parent="$(dirname "${parent}")"
	done
	executer setfacl --recursive --modify="u:${COMPTE_SERVICE}:rX,d:u:${COMPTE_SERVICE}:rX" "${chemin}"
	info '%s can read %s' "${COMPTE_SERVICE}" "${chemin}"
}

retirer_la_lecture_au_service() {
	local chemin parent
	chemin="$(realpath "$1")"
	executer setfacl --recursive --remove="u:${COMPTE_SERVICE}" --remove="d:u:${COMPTE_SERVICE}" "${chemin}"
	parent="$(dirname "${chemin}")"
	while [[ "${parent}" != / ]]; do
		if [[ -O "${parent}" ]]; then
			executer setfacl --remove="u:${COMPTE_SERVICE}" "${parent}"
		fi
		parent="$(dirname "${parent}")"
	done
}

# Le WirePlumber des sessions relit sa configuration : la carte de l'antenne y disparaît, ou y revient.
relancer_le_wireplumber_du_bureau() {
	if systemctl --user is-active --quiet wireplumber.service 2>/dev/null; then
		executer systemctl --user restart wireplumber.service
	fi
}

installer_service() {
	etape 'Broadcast service'
	if ! "${SERVICE}"; then
		verifier_le_service_installe
		"${METTRE_A_JOUR_LE_SERVICE}" || return 0
	fi
	# L'antenne d'un poste dédié joue toujours sur une carte son (https://github.com/dascritch/machincast/issues/339),
	# par le PipeWire du service (https://github.com/dascritch/machincast/issues/381).
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info '[simulation] on-air output checked by machincast.installation on-air once the virtual environment is created'
	else
		installation on-air || echec 'broadcast service not installed: the on-air output does not suit it'
	fi
	info 'for a computer dedicated to the on-air output: Machin player starts with the computer, as %s' "${COMPTE_SERVICE}"
	creer_le_compte_du_service
	autoriser_le_service_en_base
	donner_la_lecture_au_service "${RACINE}"
	# Le service ne dépend plus de la session du compte (https://github.com/dascritch/machincast/issues/381).
	if [[ "$(loginctl show-user "${UTILISATEUR}" --property=Linger --value 2>/dev/null)" == yes ]]; then
		info 'the session of %s no longer needs to stay active at startup: sudo loginctl disable-linger %s' \
			"${UTILISATEUR}" "${UTILISATEUR}"
	fi
	# Les répertoires d'exécution, des logs et des rapports de crash, au groupe du service.
	installer_fichier tmpfiles "${FICHIER_TMPFILES}" || true
	executer sudo systemd-tmpfiles --create "${FICHIER_TMPFILES}"
	installer_fichier logrotate "${FICHIER_LOGROTATE}" || true
	local unites_changees=false service_change=false purge_changee=false
	if installer_fichier wireplumber-service "${FICHIER_WIREPLUMBER_SERVICE}"; then
		service_change=true
	fi
	if installer_fichier wireplumber-desktop "${FICHIER_WIREPLUMBER_BUREAU}"; then
		relancer_le_wireplumber_du_bureau
		service_change=true
	fi
	local paire
	for paire in "pipewire-unit:${FICHIER_UNITE_PIPEWIRE}" "wireplumber-unit:${FICHIER_UNITE_WIREPLUMBER}" \
		"unit:${FICHIER_UNITE}"; do
		if installer_fichier "${paire%%:*}" "${paire#*:}"; then
			unites_changees=true
		fi
	done
	if installer_fichier purge-unit "${FICHIER_UNITE_PURGE}"; then
		purge_changee=true
	fi
	if installer_fichier purge-timer "${FICHIER_MINUTEUR_PURGE}"; then
		purge_changee=true
	fi
	if "${unites_changees}" || "${purge_changee}"; then
		executer sudo systemctl daemon-reload
	fi
	installer_fichier rule "${FICHIER_REGLE}" || true
	executer sudo systemctl enable --now "${UNITE_PIPEWIRE}" "${UNITE_WIREPLUMBER}" "${UNITE}"
	if "${unites_changees}" || "${service_change}"; then
		# Une unité ou une configuration modifiée ne vaut qu'au redémarrage du service, s'il tournait déjà.
		executer sudo systemctl try-restart "${UNITE_PIPEWIRE}" "${UNITE_WIREPLUMBER}" "${UNITE}"
	fi
	# La purge de la base, chaque jour à midi : Machin purge, sous le compte de MachinCast, propriétaire de la base.
	executer sudo systemctl enable --now "${MINUTEUR_PURGE}"
	info 'follow the broadcast: Machin logs; the daily purge: journalctl --unit=%s' "${UNITE_PURGE}"
}

# Retire un fichier installé par --service, s'il existe ; vrai s'il existait.
retirer_fichier() {
	local fichier="$1"
	if [[ -e "${fichier}" ]]; then
		executer sudo rm --force "${fichier}" # fichier de MachinCast : installé par --service
		return 0
	fi
	info '%s missing' "${fichier}"
	return 1
}

retirer_service() {
	etape 'Removal of the broadcast service'
	local unite
	for unite in "${UNITE}" "${UNITE_WIREPLUMBER}" "${UNITE_PIPEWIRE}" "${MINUTEUR_PURGE}"; do
		if [[ -e "/etc/systemd/system/${unite}" ]]; then
			executer sudo systemctl disable --now "${unite}"
		fi
	done
	local fichier
	for fichier in "${FICHIER_UNITE}" "${FICHIER_UNITE_WIREPLUMBER}" "${FICHIER_UNITE_PIPEWIRE}" \
		"${FICHIER_MINUTEUR_PURGE}" "${FICHIER_UNITE_PURGE}" "${FICHIER_REGLE}" "${FICHIER_TMPFILES}" \
		"${FICHIER_LOGROTATE}" "${FICHIER_WIREPLUMBER_SERVICE}"; do
		retirer_fichier "${fichier}" || true
	done
	executer sudo systemctl daemon-reload
	if [[ -d "${DOSSIER_WIREPLUMBER_SERVICE}" ]]; then
		# Répertoires de MachinCast, vides une fois son fragment retiré : rmdir n'efface rien d'autre.
		executer sudo rmdir --ignore-fail-on-non-empty --parents "$(dirname "${FICHIER_WIREPLUMBER_SERVICE}")"
	fi
	# La carte de l'antenne revient aux sessions du poste.
	if retirer_fichier "${FICHIER_WIREPLUMBER_BUREAU}"; then
		relancer_le_wireplumber_du_bureau
	fi
	if getent passwd "${COMPTE_SERVICE}" >/dev/null; then
		retirer_la_lecture_au_service "${RACINE}"
		if "${SIMULATION}"; then
			info '[simulation] sudo -u postgres psql: DROP ROLE IF EXISTS %s' "${COMPTE_SERVICE}"
		else
			sudo -u postgres psql --no-psqlrc --quiet --set=ON_ERROR_STOP=1 --command='DROP ROLE IF EXISTS machincast'
		fi
		# Le groupe du même nom part avec le compte, une fois que le compte de MachinCast n'en est plus membre.
		if id -nG "${UTILISATEUR}" | tr ' ' '\n' | grep -qx "${COMPTE_SERVICE}"; then
			executer sudo gpasswd --delete "${UTILISATEUR}" "${COMPTE_SERVICE}"
		fi
		executer sudo userdel "${COMPTE_SERVICE}"
		# Répertoires du service : l'état de son WirePlumber, ses sockets.
		executer sudo rm --recursive --force "${DOSSIER_DU_COMPTE_SERVICE}" "${DOSSIER_D_EXECUTION_SERVICE}"
	else
		info 'account %s missing' "${COMPTE_SERVICE}"
	fi
	info 'the logs stay in %s: sudo rm -r %s removes them' "${DOSSIER_DES_LOGS}" "${DOSSIER_DES_LOGS}"
	info 'the broadcast is launched by hand again, with Machin player; the database purge, with Machin purge'
}

conclure() {
	etape 'Installation finished'
	info 'Help: Machin --help'
	info 'Interface: MachinCast, in the applications menu, or Machin interface'
	info 'First indexing: Machin indexer, then Machin indexer --full-audit'
	if "${DEV}"; then
		info 'Development computer: Machin dev opens a shell, venv activated; Machin dev-test runs the checks'
	fi
}

principal() {
	while (($# > 0)); do
		case "$1" in
			--simulation) SIMULATION=true ;;
			--dev) DEV=true ;;
			--service) SERVICE=true ;;
			--remove-service) RETIRER_SERVICE=true ;;
			--desktop) BUREAU=oui ;;
			--no-desktop) BUREAU=non ;;
			--stop-programs)
				ARRETER=oui
				ARRETER_DEMANDE=$((ARRETER_DEMANDE + 1))
				;;
			--leave-programs)
				ARRETER=non
				ARRETER_DEMANDE=$((ARRETER_DEMANDE + 1))
				;;
			-h | --help)
				aide
				exit 0
				;;
			*)
				aide >&2
				echec 'unknown option: %s' "$1"
				;;
		esac
		shift
	done
	if "${SERVICE}" && "${RETIRER_SERVICE}"; then
		echec '--service and --remove-service do not go together'
	fi
	if [[ "${ARRETER}" != demander ]] && ((ARRETER_DEMANDE > 1)); then
		echec '--stop-programs and --leave-programs do not go together'
	fi
	cd "${RACINE}"
	verifier_systeme
	verifier_reseau
	arreter_les_programmes
	installer_paquets
	installer_venv
	preparer_configuration
	preparer_postgresql
	autoriser_journal
	installer_liens
	verifier_greffons
	installer_raccourci
	if "${RETIRER_SERVICE}"; then
		retirer_service
	else
		installer_service
	fi
	relancer_les_programmes
	conclure
}

principal "$@"
