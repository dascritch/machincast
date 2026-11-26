#!/usr/bin/env bash
# Installation de MachinCast sur un poste Ubuntu LTS (https://github.com/dascritch/machincast/issues/40).
#
#   ./install.sh               installe, ou met à jour une installation existante : le script est relançable
#   ./install.sh --simulation  affiche les commandes sans rien exécuter, avec toutes les informations
#   ./install.sh --verbose     affiche aussi les lignes techniques, cachées sinon (https://github.com/dascritch/machincast/issues/517)
#   ./install.sh --dev         installe aussi les outils du poste de développement
#                              (https://github.com/dascritch/machincast/issues/77)
#   ./install.sh --service     installe aussi le service de diffusion : pour un ordinateur dédié à l'antenne
#                              (https://github.com/dascritch/machincast/issues/22)
#                              et les minuteurs de ses tâches : l'indexation rapide toutes les heures, la purge
#                              puis l'audit complet chaque jour à l'heure réglée
#                              (https://github.com/dascritch/machincast/issues/268,
#                              https://github.com/dascritch/machincast/issues/455)
#   ./install.sh --service --no-timers   sans ces minuteurs, pour un poste dont les tâches sont pilotées ailleurs
#   ./install.sh --remove-service   retire ce service et ces minuteurs, la diffusion se lance de nouveau à la main
#   ./install.sh --desktop      dépose aussi le raccourci de l'interface sur le bureau, sans le demander
#   ./install.sh --no-desktop ne le dépose pas, sans le demander (https://github.com/dascritch/machincast/issues/62)
#   ./install.sh --stop-programs   arrête les programmes de MachinCast en cours, sans le demander
#   ./install.sh --leave-programs   les laisse tourner, sans le demander
#                              (https://github.com/dascritch/machincast/issues/254)
#   ./install.sh --restore FICHIER   réimporte cette sauvegarde dans la base de production qu'il crée, sans le demander
#   ./install.sh --no-restore  ne propose pas d'en réimporter une (https://github.com/dascritch/machincast/issues/347)
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
# L'action polkit des paramètres du service, que vérifie Machin interface : polkit ne lit les actions que sous
# /usr/share/polkit-1/actions, où ce seul fichier s'installe (https://github.com/dascritch/machincast/issues/603).
FICHIER_POLITIQUE="/usr/share/polkit-1/actions/org.machincast.service-settings.policy"
# Le poste d'antenne ne s'éteint, ne redémarre ni ne se met en veille par mégarde
# (https://github.com/dascritch/machincast/issues/448) : la règle polkit le demande à un administrateur, ces fragments
# neutralisent les touches, le capot et Ctrl+Alt+Suppr en console.
FICHIER_LOGIND="/etc/systemd/logind.conf.d/50-machincast.conf"
FICHIER_SYSTEME="/etc/systemd/system.conf.d/50-machincast.conf"
# Les cartes son du poste d'antenne ne s'endorment jamais (https://github.com/dascritch/machincast/issues/499) : les
# mêmes chemins dans machincast.power_save.
FICHIER_MODPROBE="/etc/modprobe.d/machincast.conf"
FICHIER_USB="/etc/udev/rules.d/50-machincast-usb.rules"
# Purge quotidienne de la base, installée avec le service (https://github.com/dascritch/machincast/issues/268) : les
# mêmes noms dans machincast.installation.
# Les tâches du service (https://github.com/dascritch/machincast/issues/455) : l'indexation rapide toutes les heures, et
# tous les quarts d'heure, Machin tasks, qui lance la tâche quotidienne, la purge puis l'audit complet, à l'heure de
# schedule.daily ; les mêmes noms dans machincast.service.
UNITE_TACHES="machincast-tasks.service"
MINUTEUR_TACHES="machincast-tasks.timer"
UNITE_INDEXATION="machincast-indexing.service"
MINUTEUR_INDEXATION="machincast-indexing.timer"
FICHIER_UNITE_TACHES="/etc/systemd/system/${UNITE_TACHES}"
# Le serveur intranet (https://github.com/dascritch/machincast/issues/538), éteint tant que intranet.enabled n'est pas
# vrai ; le même nom dans machincast.service.
UNITE_INTRANET="machincast-webserver.service"
FICHIER_UNITE_INTRANET="/etc/systemd/system/${UNITE_INTRANET}"
FICHIER_MINUTEUR_TACHES="/etc/systemd/system/machincast-tasks.timer"
FICHIER_UNITE_INDEXATION="/etc/systemd/system/${UNITE_INDEXATION}"
FICHIER_MINUTEUR_INDEXATION="/etc/systemd/system/${MINUTEUR_INDEXATION}"
# L'ancien minuteur de la purge, à midi (https://github.com/dascritch/machincast/issues/268) : la tâche quotidienne le
# remplace, il est retiré à la mise à jour.
ANCIENNE_UNITE_PURGE="machincast-purge.service"
ANCIEN_MINUTEUR_PURGE="machincast-purge.timer"
FICHIER_ANCIENNE_UNITE_PURGE="/etc/systemd/system/${ANCIENNE_UNITE_PURGE}"
FICHIER_ANCIEN_MINUTEUR_PURGE="/etc/systemd/system/${ANCIEN_MINUTEUR_PURGE}"
# Le service tourne sous son propre compte, avec son PipeWire et son WirePlumber
# (https://github.com/dascritch/machincast/issues/381) : les mêmes noms dans machincast.installation.
COMPTE_SERVICE="machincast"
DOSSIER_DU_COMPTE_SERVICE="/var/lib/machincast"
DOSSIER_D_EXECUTION_SERVICE="/run/machincast"
# Le compte du serveur intranet, hors du groupe du service, et le répertoire de la socket que Machin player lui réserve
# (https://github.com/dascritch/machincast/issues/549) : les mêmes noms dans machincast.installation.
COMPTE_INTRANET="machincast-webserver"
DOSSIER_D_EXECUTION_INTRANET="/run/machincast-webserver"
# Le certificat et la clé que le serveur intranet génère dans son répertoire d'état, à sauvegarder : inscrits d'avance
# dans la liste des fichiers créés, qu'il ne fait que lire (https://github.com/dascritch/machincast/issues/652). Les
# mêmes noms dans machincast.installation (INTRANET_STATE) et machincast.webserver.certificate.
CERTIFICATS_INTRANET=("/var/lib/machincast-webserver/certificate.pem" "/var/lib/machincast-webserver/key.pem")
DOSSIER_DES_LOGS="/var/log/machincast"
UNITE_PIPEWIRE="machincast-pipewire.service"
UNITE_WIREPLUMBER="machincast-wireplumber.service"
FICHIER_UNITE_PIPEWIRE="/etc/systemd/system/${UNITE_PIPEWIRE}"
FICHIER_UNITE_WIREPLUMBER="/etc/systemd/system/${UNITE_WIREPLUMBER}"
FICHIER_TMPFILES="/etc/tmpfiles.d/machincast.conf"
FICHIER_LOGROTATE="/etc/logrotate.d/machincast"
# La bannière de chaque nouveau shell, quand le service est installé (https://github.com/dascritch/machincast/issues/517) :
# le même chemin dans machincast.installation.
FICHIER_PROFIL="/etc/profile.d/machincast.sh"
DOSSIER_WIREPLUMBER_SERVICE="/etc/machincast"
FICHIER_WIREPLUMBER_SERVICE="${DOSSIER_WIREPLUMBER_SERVICE}/wireplumber/wireplumber.conf.d/50-machincast.conf"
# Le répertoire d'accueil des sonores (machincast.access.WELCOME) : les répertoires personnels restent fermés au
# service, et leurs droits ne changent jamais.
ACCUEIL="/home/machincast"
# Les extensions des fichiers sonores (machincast.protection.SOUND_EXTENSIONS) : un répertoire qui en contient un ne se
# retire jamais (https://github.com/dascritch/machincast/issues/430).
EXTENSIONS_SONORES=(aac aif aiff flac m4a mp3 ogg wav)
# Accepte, sans question, de dédier le poste à l'antenne : --dedicated.
DEDIE=false
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
# La liste des fichiers créés par MachinCast, à côté de sa configuration, les seuls qu'il modifie ou efface
# (https://github.com/dascritch/machincast/issues/652) : le même nom dans machincast.created_files.
LISTE_FICHIERS="${RACINE}/fichiers-machincast.txt"
VENV="${RACINE}/.venv"
ROLES=(player indexer interface webserver)
# Machin intranet, devenu Machin webserver (https://github.com/dascritch/machincast/issues/654) : ses anciens noms, que
# renommer_machin_intranet reprend sur un poste installé avant.
ANCIEN_COMPTE_INTRANET="machincast-intranet"
ANCIEN_ROLE_INTRANET="machincast_intranet"
ANCIENNE_UNITE_INTRANET="machincast-intranet.service"
ANCIEN_FICHIER_UNITE_INTRANET="/etc/systemd/system/${ANCIENNE_UNITE_INTRANET}"
ANCIEN_ETAT_INTRANET="/var/lib/machincast-intranet"
ETAT_INTRANET="/var/lib/machincast-webserver"
ANCIEN_ETAT_DU_COMPTE="${XDG_STATE_HOME:-${HOME}/.local/state}/machincast/intranet"
ETAT_DU_COMPTE="${XDG_STATE_HOME:-${HOME}/.local/state}/machincast/webserver"

# Prérequis système : ce que pip ne peut pas fournir (https://github.com/dascritch/machincast/issues/51).
# Même liste que AGENTS.md, sans les outils de développement.
PAQUETS=(
	python3-venv python3-dev build-essential pkg-config libgirepository-2.0-dev libcairo2-dev
	gir1.2-gstreamer-1.0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad
	gstreamer1.0-alsa gstreamer1.0-pulseaudio gstreamer1.0-pipewire pipewire-bin libmagic1t64 postgresql bash-completion
	acl wireplumber
)
# Outils du poste de développement, installés par --dev : ceux de AGENTS.md.
PAQUETS_DEV=(bats shellcheck desktop-file-utils pipewire wireplumber)

SIMULATION=false
# Toutes les informations, y compris les lignes techniques (https://github.com/dascritch/machincast/issues/517) : sans
# --verbose, ni --simulation, les lignes « info » sont cachées.
VERBEUX=false
DEV=false
SERVICE=false
RETIRER_SERVICE=false
# Les minuteurs des tâches du service (https://github.com/dascritch/machincast/issues/455) : --no-timers les écarte.
MINUTEURS=true
# Raccourci sur le bureau : demander, oui ou non.
BUREAU=demander
# Réimportation d'une sauvegarde dans la base de production qu'install.sh vient de créer
# (https://github.com/dascritch/machincast/issues/347) : demander, oui (celle de --restore) ou non.
REIMPORTER=demander
SAUVEGARDE=""
# Service déjà installé, sans --service ni --remove-service (https://github.com/dascritch/machincast/issues/557) : cette
# installation le met à jour, comme avec --service, sans redemander de dédier le poste.
SERVICE_DEJA_INSTALLE=false
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
# Couleurs (https://github.com/dascritch/machincast/issues/517) : sur un terminal seulement, jamais avec NO_COLOR ;
# FORCE_COLOR les impose, pour les tests. Un avertissement a son texte en jaune, un échec est en jaune vif sur un fond
# rouge sombre, une question en blanc et en gras.
choisir_couleurs() {
	JAUNE=""
	GRAS=""
	FIN_DE_COULEUR=""
	if [[ -z "${NO_COLOR:-}" ]] && { [[ -t 1 ]] || [[ -n "${FORCE_COLOR:-}" ]]; }; then
		JAUNE=$'\e[33m'
		GRAS=$'\e[1;97m'
		FIN_DE_COULEUR=$'\e[0m'
	fi
}
choisir_couleurs

aide() {
	tf 'Usage: ./install.sh [--simulation] [--verbose] [--dev] [--service [--dedicated] [--no-timers] | --remove-service] [--desktop | --no-desktop]
                    [--stop-programs | --leave-programs] [--restore FILE | --no-restore]

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
     that it owns, MachinCast roles, schema; a new production database can first take back a backup of a
     previous installation, on this computer or another one (Machin backup-db): the question is asked,
     with kdialog on a graphical desktop, in the terminal otherwise, except with --restore or --no-restore;
  5. authorisation of %s to the roles %s, systemd-journal group;
  6. links %s, %s and the bash autocompletion;
  7. check of the GStreamer version and plugins, and of the audio output;
  8. shortcut of the interface in the applications menu of %s, and, if wanted,
     on the desktop: the question is asked, except with --desktop or --no-desktop; MachinCast
     icon in the icon theme, for the sound settings of the computer; the editable document « Your
     installation », on the desktop, from its template, never over an existing one.
With --dev, also the tools of the development computer: %s (apt) and the
test dependencies (pip, extra [dev]), for Machin dev and Machin dev-test.
With --service, also the broadcast service %s, only for a computer dedicated to the
on-air output, whose on-air output is a sound card, through the PipeWire or ALSA output (otherwise
install.sh stops and recommends another one). install.sh first asks to dedicate the computer, then
to move MachinCast out of a personal directory, to /opt/machincast: the service never reads the
personal directories, whose rights never change. Machin player starts with the computer, under its
own account %s, with its own PipeWire, and restarts after a crash. %s joins the group %s, which
reads its logs (%s) and pre-listens to the on-air output; the on-air card is reserved for the
service. The intranet server, switched off by default, runs under its own account, machincast-webserver,
outside that group. The sound files go in /home/machincast: those of the database in a personal directory
are moved there, removed from the database, or left, not played, as chosen. A polkit rule lets it start, stop and
restart with the password of an administrator, and asks for that password to power off, reboot or suspend the
computer; its power, reboot and suspend keys, its lid and Ctrl+Alt+Del on the console are ignored. Two
systemd timers run under %s: %s, the quick indexing every hour, and %s, Machin tasks every
quarter of an hour, which runs the daily task once a day from the hour set by schedule.daily (10:00 by
default, also in the interface): Machin purge, which erases from the database what exceeds the expiry
duration, then a full audit. Without --service,
none of this is installed: the broadcast, the indexing and the purge are launched by hand. A service
installed before is checked: if it is not up to date for this version, the question is asked whether
to update it.

Can be run again: each step already done is left as is.
To run with your own account, not with sudo: the script asks for sudo when needed.

Options:
  --simulation  shows the commands without running anything, with all the information
  --verbose     shows all the information, the technical lines too (links, SQL operations, files already up
                to date); without it, nor --simulation, only the steps, the warnings and what must be read
  --dev         also installs the tools of the development computer
  --service     also installs the broadcast service (computer dedicated to the on-air output only);
                once installed, install.sh updates it even without --service
  --no-timers   with --service, installs neither timer of the tasks, and removes those installed before:
                the tasks are run by another tool, such as Ansible
  --remove-service
                removes the broadcast service, its PipeWire, its accounts, its polkit rule, the
                protection of the computer and the timers of the tasks; the logs and /home/machincast stay
  --dedicated   with --service, dedicates the computer and moves MachinCast to /opt/machincast,
                without asking
  --desktop      also puts the shortcut of the interface on the desktop, without asking
  --no-desktop does not put it on the desktop, without asking
  --stop-programs
                stops the running MachinCast programs, without asking
  --leave-programs
                lets them run during the installation, without asking
  --restore FILE
                restores this backup into the production database that install.sh creates, without asking
  --no-restore  does not offer to restore a backup
  -h, --help    this help
' "${RACINE}" "${UTILISATEUR}" "${UTILISATEUR}" "${UTILISATEUR}" "${ROLES[*]}" "${LIEN_INSTALLATION}" "${LIEN_WRAPPER}" "${UTILISATEUR}" "${PAQUETS_DEV[*]}" "${UNITE}" "${COMPTE_SERVICE}" "${UTILISATEUR}" "${COMPTE_SERVICE}" "${DOSSIER_DES_LOGS}" "${UTILISATEUR}" "${MINUTEUR_INDEXATION}" "${MINUTEUR_TACHES}"
}

# Les messages s'écrivent en anglais, en format de printf entre apostrophes, suivi de leurs valeurs : etape, info et
# echec les traduisent dans la langue de la session (bin/i18n.bash, https://github.com/dascritch/machincast/issues/360).
etape() {
	printf '\n==> '
	tf "$@"
	printf '\n'
}

# Une information technique, cachée sans --verbose ni --simulation : ce qui est déjà fait, un lien, une requête.
info() {
	if ! "${VERBEUX}" && ! "${SIMULATION}"; then
		return 0
	fi
	annonce "$@"
}

# Une information que le technicien doit lire, toujours montrée.
annonce() {
	printf '    '
	tf "$@"
	printf '\n'
}

# Un avertissement : ce qui va changer, ou ce qui ne marchera pas, en jaune.
avertissement() {
	printf '%s  ! ' "${JAUNE}"
	tf "$@"
	printf '%s\n' "${FIN_DE_COULEUR}"
}

# Un échec : toute sa ligne en jaune vif sur un fond rouge sombre, sur la sortie d'erreur.
echec() {
	local debut="" fin=""
	if [[ -z "${NO_COLOR:-}" ]] && { [[ -t 2 ]] || [[ -n "${FORCE_COLOR:-}" ]]; }; then
		debut=$'\e[1;93;48;5;88m'
		fin=$'\e[0m'
	fi
	{
		printf '%s' "${debut}"
		tf 'install.sh: %s' "$(tf "$@")"
		printf '%s\n' "${fin}"
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
	avertissement 'no network access: the system packages and the Python dependencies will not be updated; the installation goes on'
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
		avertissement 'Ubuntu %s LTS: the target is 26.04 LTS, the installation goes on' "${version}"
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
	case "${ARRETER}" in
		oui) return 0 ;;
		non) return 1 ;;
	esac
	if "${SIMULATION}"; then
		info '[simulation] question: stop them during the installation?'
		return 0
	fi
	if ! peut_demander; then
		annonce 'no question without a terminal: ./install.sh --stop-programs stops them'
		return 1
	fi
	interroger "$(t 'Stop them during the installation, then relaunch them? [y/N] ')" n
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
		avertissement 'pid %s still there after %s s: forced stop' "${pid}" "${DELAI_D_ARRET}"
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
		avertissement 'running programs unreadable: the installation goes on without stopping them'
		return
	fi
	if [[ -z "${liste}" ]]; then
		annonce 'none'
		return
	fi
	local pid du_compte service libelle
	while IFS=$'\t' read -r pid du_compte service libelle; do
		annonce '%s, pid %s' "${libelle}" "${pid}"
	done <<<"${liste}"
	annonce 'an update, and its database migrations, must not happen under them'
	annonce 'stopped, the broadcast goes silent until the end of the installation; the interface loses its unsaved cards'
	if ! vouloir_arreter; then
		avertissement 'they go on: the database may change under them, relaunch them after the installation'
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
	annonce 'stopped: relaunched at the end of the installation'
}

# À la fin, ou à la sortie d'install.sh après un échec : une seule fois.
relancer_les_programmes() {
	"${PROGRAMMES_ARRETES}" || return 0
	PROGRAMMES_ARRETES=false
	etape 'Relaunch of the MachinCast programs'
	if "${SERVICE_ARRETE}"; then
		if "${RETIRER_SERVICE}"; then
			annonce 'broadcast service removed: not relaunched'
		else
			executer sudo systemctl start "${UNITE}" || info 'broadcast service not relaunched: Machin logs tells why'
		fi
	fi
	local options=() ligne
	"${SIMULATION}" && options+=(--simulation)
	while IFS= read -r ligne; do
		annonce '%s' "${ligne}"
	done < <(programmes restart --state "${ETAT_DES_PROGRAMMES}" "${options[@]}")
	rm --force "${ETAT_DES_PROGRAMMES}" # fichier de MachinCast : état des programmes arrêtés, temporaire
}

installer_paquets() {
	etape 'System packages'
	if ! "${RESEAU}"; then
		avertissement 'not updated: no network access'
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
		avertissement 'Python dependencies not updated: no network access'
		return
	fi
	executer "${VENV}/bin/pip" install --upgrade pip
	# Les versions de constraints.txt, pour que deux postes aient les mêmes (https://github.com/dascritch/machincast/issues/438).
	if "${DEV}"; then
		executer "${VENV}/bin/pip" install --constraint "${RACINE}/constraints.txt" --editable "${RACINE}[dev]"
	else
		executer "${VENV}/bin/pip" install --constraint "${RACINE}/constraints.txt" --editable "${RACINE}"
	fi
}

preparer_configuration() {
	etape 'Configuration'
	if [[ -e "${CONFIGURATION}" ]]; then
		info '%s already exists: kept' "${CONFIGURATION}"
	else
		executer cp "${RACINE}/machincast.exemple.toml" "${CONFIGURATION}"
		inscrire "${CONFIGURATION}"
		annonce 'to adapt: audio output, devices, outputs (see doc/fr/spec.md § 9)'
	fi
	adopter_les_fichiers
}

# La liste des fichiers créés (machincast.created_files), par le python3 du système, comme machincast.programs.
fichiers_crees() {
	PYTHONPATH="${RACINE}/src" python3 -m machincast.created_files --list "${LISTE_FICHIERS}" "$@"
}

# Inscrit dans la liste des fichiers créés ceux qu'install.sh vient de créer.
inscrire() {
	if "${SIMULATION}"; then
		info '[simulation] %s added to %s' "$*" "${LISTE_FICHIERS}"
		return 0
	fi
	fichiers_crees add "$@" || echec '%s not added to %s' "$*" "${LISTE_FICHIERS}"
}

# Retire de la liste des fichiers créés ceux qu'install.sh vient d'effacer.
desinscrire() {
	if "${SIMULATION}"; then
		info '[simulation] %s removed from %s' "$*" "${LISTE_FICHIERS}"
		return 0
	fi
	fichiers_crees forget "$@" || echec '%s not removed from %s' "$*" "${LISTE_FICHIERS}"
}

# Échoue si le fichier existe sans être dans la liste des fichiers créés : install.sh n'y touche pas.
verifier_le_fichier() {
	if "${SIMULATION}" && [[ ! -e "${LISTE_FICHIERS}" ]]; then
		return 0
	fi
	fichiers_crees check "$1" || echec '%s is not a file of MachinCast: move it, or add it to %s' "$1" "${LISTE_FICHIERS}"
}

# Les fichiers qu'une version d'avant la liste a créés entrent dans la liste
# (https://github.com/dascritch/machincast/issues/652) : ceux que la configuration désigne (machincast.installation
# created-files), ceux qu'install.sh installe, s'ils existent. Ensuite, tout autre fichier est refusé.
adopter_les_fichiers() {
	local designes=() sortie bureau
	if "${SIMULATION}"; then
		info '[simulation] files of MachinCast already there added to %s' "${LISTE_FICHIERS}"
		return 0
	fi
	# Un chemin par ligne : un nom de fichier peut avoir des espaces, comme le document de l'installation.
	sortie="$(installation created-files)" || echec 'machincast.installation created-files failed'
	if [[ -n "${sortie}" ]]; then
		mapfile -t designes <<<"${sortie}"
	fi
	bureau="$(dossier_du_bureau)"
	sortie="$(fichiers_crees adopt "${designes[@]}" "${FICHIER_UNITE}" "${FICHIER_REGLE}" \
		"${FICHIER_POLITIQUE}" "${FICHIER_LOGIND}" "${FICHIER_SYSTEME}" "${FICHIER_MODPROBE}" "${FICHIER_USB}" \
		"${FICHIER_UNITE_TACHES}" "${FICHIER_UNITE_INTRANET}" "${ANCIEN_FICHIER_UNITE_INTRANET}" "${FICHIER_MINUTEUR_TACHES}" "${FICHIER_UNITE_INDEXATION}" \
		"${FICHIER_MINUTEUR_INDEXATION}" "${FICHIER_ANCIENNE_UNITE_PURGE}" "${FICHIER_ANCIEN_MINUTEUR_PURGE}" \
		"${FICHIER_UNITE_PIPEWIRE}" "${FICHIER_UNITE_WIREPLUMBER}" "${FICHIER_TMPFILES}" "${FICHIER_LOGROTATE}" \
		"${FICHIER_PROFIL}" "${FICHIER_WIREPLUMBER_SERVICE}" "${FICHIER_WIREPLUMBER_BUREAU}" \
		"${DOSSIER_APPLICATIONS}/${RACCOURCI}" "${ICONE_DU_THEME}" "${bureau:-${HOME}}/${RACCOURCI}")" \
		|| echec 'files of MachinCast not added to %s' "${LISTE_FICHIERS}"
	if [[ -z "${sortie}" ]]; then
		info 'no file of MachinCast to add to %s' "${LISTE_FICHIERS}"
		return 0
	fi
	annonce 'files already created by MachinCast, now in %s:' "${LISTE_FICHIERS}"
	printf '%s\n' "${sortie}" | sed 's/^/      /'
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
	local base nouvelle_production=false
	for base in "${production}" "${test}"; do
		if existe_en_base "SELECT 1 FROM pg_database WHERE datname = :'nom'" "${base}"; then
			info 'database %s exists' "${base}"
		else
			executer sudo -u postgres createdb --host="${socket}" --owner="${UTILISATEUR}" "${base}"
			if [[ "${base}" == "${production}" ]]; then
				nouvelle_production=true
			fi
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
				FOREACH role IN ARRAY ARRAY['machincast_player', 'machincast_indexer', 'machincast_interface', 'machincast_webserver'] LOOP
					IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = role) THEN
						EXECUTE format('CREATE ROLE %I NOLOGIN', role);
					END IF;
				END LOOP;
			END;
			$$;
		SQL
		info 'roles machincast_player, machincast_indexer, machincast_interface and machincast_webserver present'
	fi
	# Une base de production neuve peut reprendre celle d'une installation précédente, avant le schéma, qui lui applique
	# ensuite les migrations qui lui manquent (https://github.com/dascritch/machincast/issues/347).
	if "${nouvelle_production}"; then
		reimporter_une_sauvegarde
	fi
	executer "${VENV}/bin/python" -m machincast.installation migrate --config "${CONFIGURATION}"
	etape 'Roles'
	# Les rôles appartiennent au serveur : une seule autorisation vaut pour les deux bases. Elle est donnée par
	# l'utilisateur postgres, qui peut attribuer les rôles quel que soit le compte qui les a créés. Sans héritage
	# des droits : chaque binaire endosse son rôle par SET ROLE (doc/fr/spec.md § 3.2).
	if "${SIMULATION}"; then
		info '[simulation] sudo -u postgres psql: GRANT machincast_player, machincast_indexer, machincast_interface, machincast_webserver TO %s WITH INHERIT FALSE, SET TRUE' "${UTILISATEUR}"
	else
		sudo -u postgres psql --no-psqlrc --quiet --set=ON_ERROR_STOP=1 --variable=nom="${UTILISATEUR}" <<-'SQL'
			GRANT machincast_player, machincast_indexer, machincast_interface, machincast_webserver TO :"nom" WITH INHERIT FALSE, SET TRUE;
		SQL
		info '%s can assume the roles %s' "${UTILISATEUR}" "${ROLES[*]}"
	fi
	# Un superutilisateur endosse tous les rôles sans autorisation, et peut tout faire sur le serveur : l'installation
	# voulue ne donne au compte aucun droit particulier (doc/fr/spec.md § 3.2). install.sh ne retire pas ce droit, qui peut
	# servir à autre chose sur le poste : il le signale.
	if existe_en_base "SELECT 1 FROM pg_roles WHERE rolname = :'nom' AND rolsuper" "${UTILISATEUR}"; then
		avertissement 'warning: %s is a PostgreSQL superuser, which MachinCast does not require; to' "${UTILISATEUR}"
		avertissement 'remove it: sudo -u postgres psql -c %s' "'ALTER ROLE \"${UTILISATEUR}\" NOSUPERUSER'"
	fi
}

autoriser_journal() {
	etape 'System journal'
	if id -nG "${UTILISATEUR}" | tr ' ' '\n' | grep -qx systemd-journal; then
		info '%s already belongs to the systemd-journal group' "${UTILISATEUR}"
	else
		# systemd-journal, jamais adm : la lecture du journal sans droits d'administration.
		executer sudo usermod --append --groups systemd-journal "${UTILISATEUR}"
		annonce 'effective after the computer restarts'
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
	# Déplacé en /opt/machincast pour le service, MachinCast y est lui-même : pas de lien.
	if [[ "${RACINE}" != "${LIEN_INSTALLATION}" ]]; then
		relier "${RACINE}" "${LIEN_INSTALLATION}"
	fi
	relier "${LIEN_INSTALLATION}/bin/Machin" "${LIEN_WRAPPER}"
	relier "${LIEN_INSTALLATION}/bash-completion/Machin" "${LIEN_COMPLETION}"
}

# L'install.sh de chaque plugin activé, après la base et ses rôles : il crée ses tables, après une sauvegarde de la base,
# et refait ce qu'il faut à sa mise à jour (https://github.com/dascritch/machincast/issues/587). Le Python du venv lui
# est donné ; en simulation, il dit seulement ce qu'il ferait.
installer_plugins() {
	etape 'Plugins'
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info '[simulation] plugins installed once the virtual environment is created'
		return
	fi
	local scripts script
	scripts="$(installation plugins)" || echec 'the enabled plugins cannot be read from the configuration'
	if [[ -z "${scripts}" ]]; then
		info 'no enabled plugin to install'
		return
	fi
	while IFS= read -r script; do
		annonce 'plugin %s' "$(basename "$(dirname "${script}")")"
		if "${SIMULATION}"; then
			MACHINCAST_PYTHON="${VENV}/bin/python" "${script}" --simulation --config "${CONFIGURATION}" ||
				avertissement 'plugin %s: its install.sh failed' "${script}"
		else
			MACHINCAST_PYTHON="${VENV}/bin/python" "${script}" --config "${CONFIGURATION}" ||
				echec 'plugin %s: its install.sh failed; fix it, or disable the plugin, then run install.sh again' "${script}"
		fi
	done <<<"${scripts}"
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
	verifier_le_fichier "${destination}"
	executer sudo install -D --mode=644 --owner=root --group=root "${redige}" "${destination}"
	rm --force "${redige}" # fichier de MachinCast : unité ou règle rédigée, temporaire
	inscrire "${destination}"
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
	verifier_le_fichier "${destination}"
	executer install -D --mode="${droits}" "${redige}" "${destination}"
	rm --force "${redige}" # fichier de MachinCast : raccourci rédigé, temporaire
	inscrire "${destination}"
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
	local raccourci="$1"
	case "${BUREAU}" in
		oui) return 0 ;;
		non) return 1 ;;
	esac
	[[ -e "${raccourci}" ]] && return 0
	if "${SIMULATION}"; then
		info '[simulation] question: also put the shortcut on the desktop?'
		return 0
	fi
	if ! peut_demander; then
		annonce 'no question without a terminal: ./install.sh --desktop puts it on the desktop'
		return 1
	fi
	interroger "$(t 'Also put the MachinCast shortcut on the desktop? [Y/n] ')" o
}

# Installe pour le compte, sans sudo, l'icône de MachinCast dans son thème d'icônes, si elle diffère de celle en place.
installer_icone() {
	local destination="$1" source="${RACINE}/src/machincast/interface/machincast.png"
	if [[ -r "${destination}" ]] && cmp --silent "${source}" "${destination}"; then
		info '%s is up to date' "${destination}"
		return
	fi
	verifier_le_fichier "${destination}"
	executer install -D --mode=644 "${source}" "${destination}"
	inscrire "${destination}"
}

installer_raccourci() {
	etape 'Shortcut of the interface'
	installer_raccourci_en "${DOSSIER_APPLICATIONS}/${RACCOURCI}" 644 || true
	installer_icone "${ICONE_DU_THEME}"
	# Le document de l'équipe, « Votre installation », sur le Bureau ou à l'emplacement de interface.notes, depuis son
	# modèle ; jamais par-dessus un document qui existe (https://github.com/dascritch/machincast/issues/451).
	executer "${VENV}/bin/python" -m machincast.notes create --config "${CONFIGURATION}" ||
		avertissement 'installation document not created: Help → Your installation… in the interface creates it'
	local bureau
	bureau="$(dossier_du_bureau)"
	if [[ -z "${bureau}" ]]; then
		annonce 'no desktop folder for %s: shortcut in the applications menu only' "${UTILISATEUR}"
		return
	fi
	if vouloir_le_bureau "${bureau}/${RACCOURCI}"; then
		# Exécutable : Plasma lance alors le raccourci du bureau sans demander de confirmation.
		installer_raccourci_en "${bureau}/${RACCOURCI}" 755 || true
	elif [[ -e "${bureau}/${RACCOURCI}" ]]; then
		info '%s/%s left as is' "${bureau}" "${RACCOURCI}"
	else
		annonce 'no shortcut on the desktop; ./install.sh --desktop puts it there'
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
	for paire in "unit:${FICHIER_UNITE}" "intranet-unit:${FICHIER_UNITE_INTRANET}" "pipewire-unit:${FICHIER_UNITE_PIPEWIRE}" \
		"wireplumber-unit:${FICHIER_UNITE_WIREPLUMBER}" "wireplumber-service:${FICHIER_WIREPLUMBER_SERVICE}" \
		"wireplumber-desktop:${FICHIER_WIREPLUMBER_BUREAU}" "tmpfiles:${FICHIER_TMPFILES}" \
		"logrotate:${FICHIER_LOGROTATE}" "profile:${FICHIER_PROFIL}" \
		"rule:${FICHIER_REGLE}" "policy:${FICHIER_POLITIQUE}" "logind:${FICHIER_LOGIND}" \
		"system-conf:${FICHIER_SYSTEME}" \
		"power-save:${FICHIER_MODPROBE}" "usb-power:${FICHIER_USB}"; do
		fichier_a_jour "${paire%%:*}" "${paire#*:}" || printf '%s\n' "${paire#*:}"
	done
	# Les minuteurs ne se vérifient que s'ils sont installés : le choix de --no-timers tient
	# (https://github.com/dascritch/machincast/issues/455).
	if [[ -e "${FICHIER_MINUTEUR_TACHES}" ]]; then
		for paire in "tasks-unit:${FICHIER_UNITE_TACHES}" "tasks-timer:${FICHIER_MINUTEUR_TACHES}" \
			"indexing-unit:${FICHIER_UNITE_INDEXATION}" "indexing-timer:${FICHIER_MINUTEUR_INDEXATION}"; do
			fichier_a_jour "${paire%%:*}" "${paire#*:}" || printf '%s\n' "${paire#*:}"
		done
	fi
	# L'ancien minuteur de la purge, à midi, est périmé : la mise à jour le remplace.
	if [[ -e "${FICHIER_ANCIEN_MINUTEUR_PURGE}" ]]; then
		printf '%s\n' "${FICHIER_ANCIEN_MINUTEUR_PURGE}"
	fi
}

# Sans --service ni --remove-service, un service déjà installé se met à jour comme avec --service : une mise à jour du
# poste n'oublie pas le service (https://github.com/dascritch/machincast/issues/557). Le poste est déjà dédié à
# l'antenne ; le choix de --no-timers tient : sans minuteur installé, aucun n'est ajouté.
reprendre_le_service_installe() {
	if "${SERVICE}" || "${RETIRER_SERVICE}" || [[ ! -e "${FICHIER_UNITE}" ]]; then
		return 0
	fi
	annonce 'broadcast service installed: this installation updates it too, as ./install.sh --service'
	SERVICE=true
	SERVICE_DEJA_INSTALLE=true
	if [[ ! -e "${FICHIER_MINUTEUR_TACHES}" ]] && [[ ! -e "${FICHIER_ANCIEN_MINUTEUR_PURGE}" ]]; then
		MINUTEURS=false
	fi
}

# Le service déjà installé : ce qui n'est plus à jour pour cette version de MachinCast, et que l'installation refait.
dire_le_service_perime() {
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
	annonce 'installed, not up to date for this version of MachinCast, updated now: %s' "${perimes//$'\n'/, }"
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
		annonce 'effective after the computer restarts'
	fi
}

# Machin intranet est devenu Machin webserver (https://github.com/dascritch/machincast/issues/654). Sur un poste installé
# avant, son unité s'arrête et part ; son compte, son groupe et ses rôles PostgreSQL prennent leur nouveau nom, en
# gardant leurs droits ; son répertoire d'état, et le certificat qu'il y a généré, aussi. Relançable : seul ce qui
# porte encore l'ancien nom change.
renommer_machin_intranet() {
	etape 'Machin webserver, formerly Machin intranet'
	if [[ -e "${ANCIEN_FICHIER_UNITE_INTRANET}" ]]; then
		# Adoptée par adopter_les_fichiers, elle est dans la liste des fichiers créés : elle en sort.
		verifier_le_fichier "${ANCIEN_FICHIER_UNITE_INTRANET}"
		executer sudo systemctl disable --now "${ANCIENNE_UNITE_INTRANET}"
		executer sudo rm --force "${ANCIEN_FICHIER_UNITE_INTRANET}" # fichier de MachinCast : l'unité de Machin intranet
		desinscrire "${ANCIEN_FICHIER_UNITE_INTRANET}"
		executer sudo systemctl daemon-reload
		annonce '%s removed: %s replaces it' "${ANCIENNE_UNITE_INTRANET}" "${UNITE_INTRANET}"
	fi
	if getent passwd "${ANCIEN_COMPTE_INTRANET}" >/dev/null && ! getent passwd "${COMPTE_INTRANET}" >/dev/null; then
		executer sudo usermod --login "${COMPTE_INTRANET}" --comment 'MachinCast web server' "${ANCIEN_COMPTE_INTRANET}"
		annonce 'account %s renamed %s' "${ANCIEN_COMPTE_INTRANET}" "${COMPTE_INTRANET}"
	fi
	if getent group "${ANCIEN_COMPTE_INTRANET}" >/dev/null && ! getent group "${COMPTE_INTRANET}" >/dev/null; then
		executer sudo groupmod --new-name "${COMPTE_INTRANET}" "${ANCIEN_COMPTE_INTRANET}"
	fi
	if [[ -d "${ANCIEN_ETAT_INTRANET}" && ! -e "${ETAT_INTRANET}" ]]; then
		# fichier de MachinCast : le répertoire d'état de Machin intranet, et son certificat généré, sous le nouveau nom
		executer sudo mv "${ANCIEN_ETAT_INTRANET}" "${ETAT_INTRANET}"
		# Le certificat et la clé, sous leur nouveau chemin dans la liste des fichiers créés.
		desinscrire "${ANCIEN_ETAT_INTRANET}/certificate.pem" "${ANCIEN_ETAT_INTRANET}/key.pem"
		inscrire "${CERTIFICATS_INTRANET[@]}"
	fi
	if [[ -d "${ANCIEN_ETAT_DU_COMPTE}" && ! -e "${ETAT_DU_COMPTE}" ]]; then
		# fichier de MachinCast : le répertoire d'état du compte pour Machin intranet, sous le nouveau nom
		executer mv "${ANCIEN_ETAT_DU_COMPTE}" "${ETAT_DU_COMPTE}"
		desinscrire "${ANCIEN_ETAT_DU_COMPTE}/certificate.pem" "${ANCIEN_ETAT_DU_COMPTE}/key.pem"
		inscrire "${ETAT_DU_COMPTE}/certificate.pem" "${ETAT_DU_COMPTE}/key.pem"
	fi
	if "${SIMULATION}"; then
		info '[simulation] sudo -u postgres psql: ALTER ROLE %s RENAME TO machincast_webserver, ALTER ROLE "%s" RENAME TO "%s", if they exist' \
			"${ANCIEN_ROLE_INTRANET}" "${ANCIEN_COMPTE_INTRANET}" "${COMPTE_INTRANET}"
		return 0
	fi
	# Renommés, les rôles gardent leurs droits sur les deux bases et leurs appartenances.
	sudo -u postgres psql --no-psqlrc --quiet --set=ON_ERROR_STOP=1 <<-'SQL' || echec 'roles of Machin intranet not renamed'
		DO $$
		BEGIN
			IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'machincast_intranet')
				AND NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'machincast_webserver') THEN
				ALTER ROLE machincast_intranet RENAME TO machincast_webserver;
			END IF;
			IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'machincast-intranet')
				AND NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'machincast-webserver') THEN
				ALTER ROLE "machincast-intranet" RENAME TO "machincast-webserver";
			END IF;
		END;
		$$;
	SQL
	info 'roles of Machin webserver under their new names'
}

# Le compte du serveur intranet et son groupe : distinct du compte du service, hors de son groupe, il ne lit ni les
# sonores, ni le PipeWire du service, ni ses logs (https://github.com/dascritch/machincast/issues/549).
creer_le_compte_de_l_intranet() {
	if getent passwd "${COMPTE_INTRANET}" >/dev/null; then
		info 'account %s present' "${COMPTE_INTRANET}"
		return
	fi
	executer sudo useradd --system --user-group --home-dir /nonexistent --no-create-home \
		--shell /usr/sbin/nologin --comment 'MachinCast web server' "${COMPTE_INTRANET}"
}

# Le rôle PostgreSQL du compte du serveur intranet : il se connecte par authentification peer, et n'endosse que le
# rôle machincast_webserver, sans en hériter les droits (doc/fr/spec.md § 3.2).
autoriser_l_intranet_en_base() {
	if "${SIMULATION}"; then
		info '[simulation] sudo -u postgres psql: CREATE ROLE "%s" LOGIN; GRANT machincast_webserver TO "%s" WITH INHERIT FALSE, SET TRUE' \
			"${COMPTE_INTRANET}" "${COMPTE_INTRANET}"
		return
	fi
	sudo -u postgres psql --no-psqlrc --quiet --set=ON_ERROR_STOP=1 <<-'SQL'
		DO $$
		BEGIN
			IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'machincast-webserver') THEN
				CREATE ROLE "machincast-webserver" LOGIN;
			END IF;
		END;
		$$;
		GRANT machincast_webserver TO "machincast-webserver" WITH INHERIT FALSE, SET TRUE;
	SQL
	info '%s can assume the role machincast_webserver' "${COMPTE_INTRANET}"
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

# Vrai si le chemin est dans un répertoire personnel, liens résolus : /home, sauf le répertoire d'accueil des sonores,
# /root et celui du compte. Le service n'y lit jamais rien, et leurs droits ne changent jamais
# (https://github.com/dascritch/machincast/issues/381).
dans_un_repertoire_personnel() {
	local chemin
	chemin="$(realpath --canonicalize-missing "$1")/"
	case "${chemin}" in
		"${ACCUEIL}"/*) return 1 ;;
		/home/* | /root/* | "$(realpath --canonicalize-missing "${HOME}")"/*) return 0 ;;
	esac
	return 1
}

# Un poste graphique, local, où kdialog pose les questions dans une fenêtre ; sinon, sans doute par ssh, elles se
# posent dans le terminal (https://github.com/dascritch/machincast/issues/347, https://github.com/dascritch/machincast/issues/517).
graphique() {
	[[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]] && [[ -z "${SSH_CONNECTION:-}" ]] && command -v kdialog >/dev/null
}

# Vrai s'il y a un moyen de poser une question : une fenêtre, ou un terminal.
peut_demander() {
	graphique || en_terminal
}

# Pose une question en oui ou non ; vrai pour oui. $1 : la question, déjà traduite ; $2 : o ou n, la réponse d'une
# réponse vide ; $3 et $4 : les libellés des boutons de la fenêtre, facultatifs. Dans une fenêtre kdialog, ou dans le
# terminal, la question en blanc et en gras.
interroger() {
	local question="$1" defaut="$2" reponse
	if graphique; then
		if (($# > 3)); then
			kdialog --title MachinCast --yesno "${question%%[[:space:]]\[*}" --yes-label "$3" --no-label "$4"
		else
			kdialog --title MachinCast --yesno "${question%%[[:space:]]\[*}"
		fi
		return
	fi
	if [[ "${question}" != *'['* ]]; then
		question="${question} $(t '[y/N]')"
	fi
	printf '    %s%s%s ' "${GRAS}" "${question}" "${FIN_DE_COULEUR}"
	read -r reponse
	# Oui : « o » en français, « y » en anglais.
	if [[ "${defaut}" == o ]]; then
		[[ ! "${reponse}" =~ ^[nN] ]]
	else
		[[ "${reponse}" =~ ^[oOyY] ]]
	fi
}

# Une question en oui ou non ; vrai pour oui. En simulation, elle est seulement dite ; sans terminal, la réponse est
# non, sauf avec --dedicated.
demander_oui() {
	local question="$1"
	if "${DEDIE}"; then
		return 0
	fi
	if "${SIMULATION}"; then
		info '[simulation] question: %s' "$(t "${question}")"
		return 0
	fi
	if ! peut_demander; then
		annonce 'no question without a terminal: ./install.sh --service --dedicated accepts'
		return 1
	fi
	interroger "$(t "${question}")" n
}

en_terminal() {
	[[ -t 0 ]]
}

# Faut-il réimporter une sauvegarde ? Vrai pour oui.
demander_reimportation() {
	interroger "$(t 'You seem to be making a new installation of MachinCast. Had you already run it on this computer or on another one? Should its database be recovered?')" n \
		"$(t 'Yes, restore a backup')" "$(t 'No, start from scratch')"
}

# Le fichier de la sauvegarde, cherché à partir du répertoire personnel ; rien s'il n'est pas choisi.
choisir_sauvegarde() {
	local fichier=""
	if graphique; then
		kdialog --title MachinCast --getopenfilename "${HOME}" "*.dump|$(t 'MachinCast backups (*.dump)')" || true
		return
	fi
	read -r -e -p "    $(t 'File of the backup (Machin backup-db): ')" fichier || true
	printf '%s\n' "${fichier/#\~/${HOME}}"
}

# Machin restore-db, qui vérifie la sauvegarde et ne la réimporte que dans une base vide.
restaurer() {
	executer "${VENV}/bin/Machin_restore-db" --config "${CONFIGURATION}" "$1"
}

# La base de production vient d'être créée : réimporter la base d'une installation précédente, sur ce poste ou sur un
# autre, sauvegardée par Machin backup-db ou Machin maintenance-db (https://github.com/dascritch/machincast/issues/347).
# Une réimportation refusée repose la question ; avec --restore, elle arrête install.sh, avant le schéma.
reimporter_une_sauvegarde() {
	local fichier
	if [[ "${REIMPORTER}" == non ]]; then
		return 0
	fi
	if [[ "${REIMPORTER}" == oui ]]; then
		restaurer "${SAUVEGARDE}" ||
			echec 'backup %s not restored: correct, then Machin restore-db FILE before running ./install.sh again' "${SAUVEGARDE}"
		return 0
	fi
	if "${SIMULATION}"; then
		info '[simulation] question: restore a backup of a previous installation into the new database?'
		return 0
	fi
	if ! graphique && ! en_terminal; then
		annonce 'new database, no backup restored: ./install.sh --restore FILE restores one'
		return 0
	fi
	while demander_reimportation; do
		fichier="$(choisir_sauvegarde)"
		if [[ -n "${fichier}" ]] && restaurer "${fichier}"; then
			annonce 'backup %s restored' "${fichier}"
			return 0
		fi
		avertissement 'backup not restored: choose another one, or start from scratch'
	done
	annonce 'new database: starting from scratch'
}

# Le poste devient celui de l'antenne : l'administrateur le sait, et l'accepte, avant que rien ne change.
confirmer_le_poste_dedie() {
	avertissement 'This installation changes the computer: it becomes dedicated to the on-air output of MachinCast.'
	avertissement 'A system account, %s, plays the on-air output, with its own PipeWire, from the start of the computer.' \
		"${COMPTE_SERVICE}"
	avertissement 'The on-air sound card is reserved for it: no other application can use it any more.'
	avertissement 'Personal directories stay closed to it: their rights never change. The sound files go in %s.' \
		"${ACCUEIL}"
	if ! demander_oui 'Dedicate this computer to the on-air output? [y/N]'; then
		echec 'broadcast service not installed: the computer is not dedicated to the on-air output'
	fi
}

# MachinCast dans un répertoire personnel : le service ne peut pas le lire. Il se déplace en /opt/machincast, un lien
# prend sa place, et install.sh reprend depuis là, avec les mêmes options ; l'environnement virtuel, qui garde ses
# chemins, se refait.
relocaliser_machincast() {
	dans_un_repertoire_personnel "${RACINE}" || return 0
	etape 'Location of MachinCast'
	info '%s is in a personal directory, which the broadcast service never reads' "${RACINE}"
	if [[ -e "${LIEN_INSTALLATION}" && ! -L "${LIEN_INSTALLATION}" ]]; then
		echec '%s exists and is not a symbolic link: move it before running install.sh again' "${LIEN_INSTALLATION}"
	fi
	if ! demander_oui 'Move MachinCast to /opt/machincast, and leave a link in its place? [y/N]'; then
		echec 'broadcast service not installed: MachinCast must be outside the personal directories'
	fi
	if [[ -L "${LIEN_INSTALLATION}" ]]; then
		executer sudo rm "${LIEN_INSTALLATION}" # fichier de MachinCast : le lien d'install.sh, jamais un répertoire
	fi
	executer sudo mkdir --parents "$(dirname "${LIEN_INSTALLATION}")"
	# fichier de MachinCast : son propre répertoire, programme et configuration, jamais un sonore
	executer sudo mv "${RACINE}" "${LIEN_INSTALLATION}"
	executer ln --symbolic "${LIEN_INSTALLATION}" "${RACINE}"
	# L'environnement virtuel, créé par install.sh, dont les scripts gardent l'ancien chemin.
	retirer_repertoires "${LIEN_INSTALLATION}/.venv"
	if "${SIMULATION}"; then
		info '[simulation] install.sh would start again from %s' "${LIEN_INSTALLATION}"
		return 0
	fi
	info 'install.sh starts again from %s' "${LIEN_INSTALLATION}"
	exec "${LIEN_INSTALLATION}/install.sh" "${ARGUMENTS[@]}"
}

# Le répertoire d'accueil des sonores : au compte de MachinCast, qui y dépose, et au groupe du service, qui le lit.
creer_l_accueil() {
	if [[ -d "${ACCUEIL}" ]]; then
		info '%s present' "${ACCUEIL}"
		return
	fi
	executer sudo install --directory --owner="${UTILISATEUR}" --group="${COMPTE_SERVICE}" --mode=2750 "${ACCUEIL}"
}

# Les sonores de la base dans un répertoire personnel : déplacés dans le répertoire d'accueil, retirés de la base, ou
# laissés, sans passer à l'antenne. Le déplacement est la seule exception à
# https://github.com/dascritch/machincast/issues/96, accepté à chaque fois.
traiter_les_sonores_personnels() {
	local liste reponse
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info '[simulation] sound files in personal directories listed once the virtual environment is created'
		return
	fi
	if ! liste="$(installation personal-sounds)"; then
		if "${SIMULATION}"; then
			info '[simulation] sound files in personal directories not listed: the production database is missing'
			return
		fi
		echec 'sound files in personal directories not listed'
	fi
	if [[ -z "${liste}" ]]; then
		info 'no sound file of the database in a personal directory'
		return
	fi
	avertissement 'These bank directories and added files are in a personal directory, which the broadcast service never reads:'
	printf '      %s\n' "${liste}"
	if "${SIMULATION}"; then
		info '[simulation] question: move them to %s, remove them from the database, or leave them?' "${ACCUEIL}"
		return
	fi
	if ! peut_demander; then
		avertissement 'left in place, not played on air: ./install.sh --service, in a terminal, moves them'
		return
	fi
	if graphique; then
		reponse="$(kdialog --title MachinCast --menu "$(t 'These bank directories and added files are in a personal directory, which the broadcast service never reads:')" \
			m "$(tf 'Move them to %s' "${ACCUEIL}")" r "$(t 'Remove them from the database')" l "$(t 'Leave them, not played')")" || reponse=l
	else
		printf '    %s%s%s ' "${GRAS}" "$(tf 'Move them to %s [m], remove them from the database [r], or leave them, not played [l]?' "${ACCUEIL}")" "${FIN_DE_COULEUR}"
		read -r reponse
	fi
	case "${reponse}" in
		[mMdD]*) installation move-personal-sounds || avertissement 'some sound files are not moved: see above' ;;
		[rR]*) installation forget-personal-sounds ;;
		*) annonce 'left in place, not played on air' ;;
	esac
}

# Le premier fichier sonore d'un répertoire, quelle que soit la casse de son extension ; rien s'il n'en contient aucun.
# --sudo : pour un répertoire du compte du service.
premier_sonore() {
	local prefixe=() extension criteres=()
	if [[ "$1" == --sudo ]]; then
		shift
		if ! "${SIMULATION}"; then
			prefixe=(sudo)
		fi
	fi
	for extension in "${EXTENSIONS_SONORES[@]}"; do
		if ((${#criteres[@]} > 0)); then
			criteres+=(-o)
		fi
		criteres+=(-iname "*.${extension}")
	done
	"${prefixe[@]}" find "$1" -type f \( "${criteres[@]}" \) -print -quit 2>/dev/null || true
}

# Retire des répertoires créés par MachinCast, jamais le répertoire d'accueil des sonores, ni un répertoire qui contient
# un fichier sonore, quel qu'il soit : il reste, et install.sh le dit (https://github.com/dascritch/machincast/issues/430).
# --sudo : pour des répertoires du compte du service.
retirer_repertoires() {
	local option=() repertoire sonore
	if [[ "$1" == --sudo ]]; then
		option=(--sudo)
		shift
	fi
	for repertoire in "$@"; do
		if [[ ! -e "${repertoire}" ]]; then
			continue
		fi
		case "$(realpath --canonicalize-missing "${repertoire}")/" in
			"${ACCUEIL}"/* | "$(dirname "${ACCUEIL}")"/)
				avertissement '%s kept: it is the directory of the sound files' "${repertoire}"
				continue
				;;
		esac
		sonore="$(premier_sonore "${option[@]}" "${repertoire}")"
		if [[ -n "${sonore}" ]]; then
			avertissement '%s kept: it contains sound files, such as %s' "${repertoire}" "${sonore}"
			continue
		fi
		if ((${#option[@]} > 0)); then
			# fichier de MachinCast : un répertoire qu'il a créé, sans aucun fichier sonore
			executer sudo rm --recursive --force "${repertoire}"
		else
			# fichier de MachinCast : un répertoire qu'il a créé, sans aucun fichier sonore
			executer rm --recursive --force "${repertoire}"
		fi
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
		annonce 'not installed: the broadcast is launched by hand, with Machin player'
		annonce 'on a computer dedicated to the on-air output: ./install.sh --service'
		return 0
	fi
	if "${SERVICE_DEJA_INSTALLE}"; then
		dire_le_service_perime
	fi
	# L'antenne d'un poste dédié joue toujours sur une carte son (https://github.com/dascritch/machincast/issues/339),
	# par le PipeWire du service (https://github.com/dascritch/machincast/issues/381).
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info '[simulation] on-air output checked by machincast.installation on-air once the virtual environment is created'
	else
		installation on-air || echec 'broadcast service not installed: the on-air output does not suit it'
	fi
	annonce 'for a computer dedicated to the on-air output: Machin player starts with the computer, as %s' "${COMPTE_SERVICE}"
	creer_le_compte_du_service
	autoriser_le_service_en_base
	creer_le_compte_de_l_intranet
	autoriser_l_intranet_en_base
	inscrire "${CERTIFICATS_INTRANET[@]}"
	creer_l_accueil
	traiter_les_sonores_personnels
	# Le service ne dépend plus de la session du compte (https://github.com/dascritch/machincast/issues/381).
	if [[ "$(loginctl show-user "${UTILISATEUR}" --property=Linger --value 2>/dev/null)" == yes ]]; then
		annonce 'the session of %s no longer needs to stay active at startup: sudo loginctl disable-linger %s' \
			"${UTILISATEUR}" "${UTILISATEUR}"
	fi
	# Les répertoires d'exécution, des logs et des rapports de crash, au groupe du service.
	installer_fichier tmpfiles "${FICHIER_TMPFILES}" || true
	executer sudo systemd-tmpfiles --create "${FICHIER_TMPFILES}"
	installer_fichier logrotate "${FICHIER_LOGROTATE}" || true
	installer_fichier profile "${FICHIER_PROFIL}" || true
	local unites_changees=false service_change=false
	if installer_fichier wireplumber-service "${FICHIER_WIREPLUMBER_SERVICE}"; then
		service_change=true
	fi
	if installer_fichier wireplumber-desktop "${FICHIER_WIREPLUMBER_BUREAU}"; then
		relancer_le_wireplumber_du_bureau
		service_change=true
	fi
	local paire
	for paire in "pipewire-unit:${FICHIER_UNITE_PIPEWIRE}" "wireplumber-unit:${FICHIER_UNITE_WIREPLUMBER}" \
		"unit:${FICHIER_UNITE}" "intranet-unit:${FICHIER_UNITE_INTRANET}"; do
		if installer_fichier "${paire%%:*}" "${paire#*:}"; then
			unites_changees=true
		fi
	done
	if "${unites_changees}"; then
		executer sudo systemctl daemon-reload
	fi
	installer_fichier rule "${FICHIER_REGLE}" || true
	installer_fichier policy "${FICHIER_POLITIQUE}" || true
	proteger_le_poste
	garder_les_cartes_eveillees
	executer sudo systemctl enable --now "${UNITE_PIPEWIRE}" "${UNITE_WIREPLUMBER}" "${UNITE}"
	# Le serveur intranet démarre avec le poste, et s'arrête aussitôt tant qu'il est éteint dans machincast.toml.
	executer sudo systemctl enable "${UNITE_INTRANET}"
	if "${unites_changees}" || "${service_change}"; then
		# Une unité ou une configuration modifiée ne vaut qu'au redémarrage du service, s'il tournait déjà.
		executer sudo systemctl try-restart "${UNITE_PIPEWIRE}" "${UNITE_WIREPLUMBER}" "${UNITE}" "${UNITE_INTRANET}"
	fi
	# Les tâches du service (https://github.com/dascritch/machincast/issues/455) : sans --service, une mise à jour garde
	# les minuteurs s'ils sont installés, l'ancien de la purge compris, et n'en ajoute pas sinon
	# (reprendre_le_service_installe).
	retirer_ancienne_purge
	if "${MINUTEURS}"; then
		installer_minuteurs
	else
		retirer_minuteurs
	fi
	annonce 'follow the broadcast: Machin logs'
}

# Les minuteurs des tâches (https://github.com/dascritch/machincast/issues/455), sous le compte de MachinCast :
# l'indexation rapide toutes les heures ; tous les quarts d'heure, Machin tasks, qui lance ce qui est dû : la tâche
# quotidienne, la purge puis l'audit complet, à l'heure de schedule.daily.
installer_minuteurs() {
	local changes=false
	if installer_fichier tasks-unit "${FICHIER_UNITE_TACHES}"; then
		changes=true
	fi
	if installer_fichier tasks-timer "${FICHIER_MINUTEUR_TACHES}"; then
		changes=true
	fi
	if installer_fichier indexing-unit "${FICHIER_UNITE_INDEXATION}"; then
		changes=true
	fi
	if installer_fichier indexing-timer "${FICHIER_MINUTEUR_INDEXATION}"; then
		changes=true
	fi
	if "${changes}"; then
		executer sudo systemctl daemon-reload
	fi
	executer sudo systemctl enable --now "${MINUTEUR_TACHES}" "${MINUTEUR_INDEXATION}"
	annonce 'the tasks: journalctl --unit=%s --unit=%s; the hour of the daily task: schedule.daily' \
		"${UNITE_INDEXATION}" "${UNITE_TACHES}"
}

# Retire les minuteurs des tâches, s'ils sont installés : --no-timers, ou le retrait du service.
retirer_minuteurs() {
	local minuteur fichier retire=false
	for minuteur in "${MINUTEUR_TACHES}" "${MINUTEUR_INDEXATION}"; do
		if [[ -e "/etc/systemd/system/${minuteur}" ]]; then
			executer sudo systemctl disable --now "${minuteur}"
		fi
	done
	for fichier in "${FICHIER_MINUTEUR_TACHES}" "${FICHIER_UNITE_TACHES}" "${FICHIER_MINUTEUR_INDEXATION}" \
		"${FICHIER_UNITE_INDEXATION}"; do
		if [[ -e "${fichier}" ]]; then
			retirer_fichier "${fichier}" || true
			retire=true
		fi
	done
	if "${retire}"; then
		executer sudo systemctl daemon-reload
	fi
}

# Retire l'ancien minuteur de la purge, à midi, et son unité, s'ils sont installés : la tâche quotidienne les remplace
# (https://github.com/dascritch/machincast/issues/455).
retirer_ancienne_purge() {
	if [[ ! -e "${FICHIER_ANCIEN_MINUTEUR_PURGE}" ]] && [[ ! -e "${FICHIER_ANCIENNE_UNITE_PURGE}" ]]; then
		return 0
	fi
	if [[ -e "${FICHIER_ANCIEN_MINUTEUR_PURGE}" ]]; then
		executer sudo systemctl disable --now "${ANCIEN_MINUTEUR_PURGE}"
	fi
	retirer_fichier "${FICHIER_ANCIEN_MINUTEUR_PURGE}" || true
	retirer_fichier "${FICHIER_ANCIENNE_UNITE_PURGE}" || true
	executer sudo systemctl daemon-reload
}

# Le poste d'antenne ne s'éteint, ne redémarre ni ne se met en veille par mégarde
# (https://github.com/dascritch/machincast/issues/448) : la règle polkit le demande à un administrateur ; logind ignore
# les touches et le capot, relu sans fermer les sessions ; systemd ignore la rafale de Ctrl+Alt+Suppr, relu en se
# réexécutant ; ctrl-alt-del.target est masqué.
proteger_le_poste() {
	if installer_fichier logind "${FICHIER_LOGIND}"; then
		executer sudo systemctl reload systemd-logind
	fi
	if installer_fichier system-conf "${FICHIER_SYSTEME}"; then
		executer sudo systemctl daemon-reexec
	fi
	if [[ "$(systemctl is-enabled ctrl-alt-del.target 2>/dev/null || true)" != "masked" ]]; then
		executer sudo systemctl mask ctrl-alt-del.target
	fi
}

# Les cartes son du poste d'antenne ne s'endorment jamais (https://github.com/dascritch/machincast/issues/499) :
# snd_hda_intel sans économie d'énergie, et les périphériques USB toujours éveillés ; machincast.power_save les applique
# aussitôt, sans attendre le redémarrage.
garder_les_cartes_eveillees() {
	local change=false
	if installer_fichier power-save "${FICHIER_MODPROBE}"; then
		change=true
	fi
	if installer_fichier usb-power "${FICHIER_USB}"; then
		change=true
	fi
	if "${change}"; then
		executer sudo "${VENV}/bin/python" -m machincast.power_save wake --root /
	fi
}

# Retire un fichier installé par --service, s'il existe ; vrai s'il existait.
retirer_fichier() {
	local fichier="$1"
	if [[ -e "${fichier}" ]]; then
		verifier_le_fichier "${fichier}"
		executer sudo rm --force "${fichier}" # fichier de MachinCast : installé par --service
		desinscrire "${fichier}"
		return 0
	fi
	info '%s missing' "${fichier}"
	return 1
}

retirer_service() {
	etape 'Removal of the broadcast service'
	local unite
	retirer_minuteurs
	retirer_ancienne_purge
	for unite in "${UNITE_INTRANET}" "${UNITE}" "${UNITE_WIREPLUMBER}" "${UNITE_PIPEWIRE}"; do
		if [[ -e "/etc/systemd/system/${unite}" ]]; then
			executer sudo systemctl disable --now "${unite}"
		fi
	done
	local fichier
	for fichier in "${FICHIER_UNITE}" "${FICHIER_UNITE_INTRANET}" "${FICHIER_UNITE_WIREPLUMBER}" "${FICHIER_UNITE_PIPEWIRE}" \
		"${FICHIER_REGLE}" "${FICHIER_POLITIQUE}" "${FICHIER_TMPFILES}" \
		"${FICHIER_LOGROTATE}" "${FICHIER_PROFIL}" "${FICHIER_WIREPLUMBER_SERVICE}" "${FICHIER_LOGIND}" "${FICHIER_SYSTEME}" \
		"${FICHIER_MODPROBE}" "${FICHIER_USB}"; do
		retirer_fichier "${fichier}" || true
	done
	executer sudo systemctl daemon-reload
	# Les cartes son retrouvent leur économie d'énergie au prochain redémarrage
	# (https://github.com/dascritch/machincast/issues/499).
	executer sudo udevadm control --reload
	annonce 'the sound cards go back to power saving at the next restart'
	# La politique d'Ubuntu revient (https://github.com/dascritch/machincast/issues/448) : extinction, redémarrage et
	# veille sans mot de passe, touches, capot et Ctrl+Alt+Suppr actifs.
	if [[ "$(systemctl is-enabled ctrl-alt-del.target 2>/dev/null || true)" == "masked" ]]; then
		executer sudo systemctl unmask ctrl-alt-del.target
	fi
	executer sudo systemctl reload systemd-logind
	executer sudo systemctl daemon-reexec
	if [[ -d "${DOSSIER_WIREPLUMBER_SERVICE}" ]]; then
		# fichier de MachinCast : ses répertoires, vides une fois son fragment retiré, et seulement s'ils sont vides
		executer sudo rmdir --ignore-fail-on-non-empty --parents "$(dirname "${FICHIER_WIREPLUMBER_SERVICE}")"
	fi
	# La carte de l'antenne revient aux sessions du poste.
	if retirer_fichier "${FICHIER_WIREPLUMBER_BUREAU}"; then
		relancer_le_wireplumber_du_bureau
	fi
	if getent passwd "${COMPTE_SERVICE}" >/dev/null; then
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
		# Les répertoires du service, l'état de son WirePlumber et ses sockets ; ceux qui contiennent des sonores restent.
		retirer_repertoires --sudo "${DOSSIER_DU_COMPTE_SERVICE}" "${DOSSIER_D_EXECUTION_SERVICE}"
	else
		info 'account %s missing' "${COMPTE_SERVICE}"
	fi
	if getent passwd "${COMPTE_INTRANET}" >/dev/null; then
		if "${SIMULATION}"; then
			info '[simulation] sudo -u postgres psql: DROP ROLE IF EXISTS "%s"' "${COMPTE_INTRANET}"
		else
			sudo -u postgres psql --no-psqlrc --quiet --set=ON_ERROR_STOP=1 \
				--command='DROP ROLE IF EXISTS "machincast-webserver"'
		fi
		executer sudo userdel "${COMPTE_INTRANET}"
		retirer_repertoires --sudo "${DOSSIER_D_EXECUTION_INTRANET}"
	else
		info 'account %s missing' "${COMPTE_INTRANET}"
	fi
	# fichier de MachinCast : seulement une commande à lancer, si l'administrateur le veut
	annonce 'the logs stay in %s: sudo rm -r %s removes them' "${DOSSIER_DES_LOGS}" "${DOSSIER_DES_LOGS}"
	annonce 'the sound files stay in %s' "${ACCUEIL}"
	annonce 'the broadcast is launched by hand again, with Machin player; the database purge, with Machin purge'
}

conclure() {
	etape 'Installation finished'
	annonce 'Help: Machin --help'
	annonce 'Interface: MachinCast, in the applications menu, or Machin interface'
	annonce 'First indexing: Machin indexer, then Machin indexer --full-audit'
	if "${DEV}"; then
		annonce 'Development computer: Machin dev opens a shell, venv activated; Machin dev-test runs the checks'
	fi
}

principal() {
	ARGUMENTS=("$@")
	while (($# > 0)); do
		case "$1" in
			--simulation) SIMULATION=true ;;
			--dev) DEV=true ;;
			--service) SERVICE=true ;;
			--remove-service) RETIRER_SERVICE=true ;;
			--no-timers) MINUTEURS=false ;;
			--dedicated) DEDIE=true ;;
			--desktop) BUREAU=oui ;;
			--no-desktop) BUREAU=non ;;
			--restore)
				(($# > 1)) || echec '--restore needs the file of the backup'
				REIMPORTER=oui
				SAUVEGARDE="$2"
				shift
				;;
			--no-restore) REIMPORTER=non ;;
			--verbose) VERBEUX=true ;;
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
	"${RACINE}/bin/Machin" banner
	reprendre_le_service_installe
	if "${SERVICE}"; then
		"${SERVICE_DEJA_INSTALLE}" || confirmer_le_poste_dedie
		relocaliser_machincast
	fi
	verifier_systeme
	verifier_reseau
	arreter_les_programmes
	installer_paquets
	installer_venv
	preparer_configuration
	renommer_machin_intranet
	preparer_postgresql
	installer_plugins
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
