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
#   ./install.sh --retirer-service   retire ce service et ce minuteur, la diffusion se lance de nouveau à la main
#   ./install.sh --bureau      dépose aussi le raccourci de l'interface sur le bureau, sans le demander
#   ./install.sh --sans-bureau ne le dépose pas, sans le demander (https://github.com/dascritch/machincast/issues/62)
#   ./install.sh --arreter-les-programmes   arrête les programmes de MachinCast en cours, sans le demander
#   ./install.sh --laisser-les-programmes   les laisse tourner, sans le demander
#                              (https://github.com/dascritch/machincast/issues/254)
#   ./install.sh --help        aide
#
# À lancer depuis le répertoire de MachinCast (release décompressée ou dépôt git), avec son propre compte :
# le script demande sudo pour les seules étapes qui l'exigent. L'installation reste en place ; /opt/machincast
# est un lien vers ce répertoire. Le service systemd ne l'est que sur demande, avec --service
# (https://github.com/dascritch/machincast/issues/22).
#
# Règles : doc/regles/wrapper.md. Documentation : INSTALL.md (https://github.com/dascritch/machincast/issues/71).

set -euo pipefail

RACINE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
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
# Raccourci de l'interface (https://github.com/dascritch/machincast/issues/62) : dans le menu des applications du
# compte, et sur son bureau s'il le veut. Le même nom que RACCOURCI de machincast.interface.application.
RACCOURCI="machincast.desktop"
DOSSIER_APPLICATIONS="${XDG_DATA_HOME:-${HOME}/.local/share}/applications"
# L'icône de MachinCast dans le thème d'icônes du compte, sous le nom qu'annoncent les sorties audio à PipeWire et à
# PulseAudio (machincast.audio.ICONE, https://github.com/dascritch/machincast/issues/296).
ICONE_DU_THEME="${XDG_DATA_HOME:-${HOME}/.local/share}/icons/hicolor/512x512/apps/machincast.png"
CONFIGURATION="${RACINE}/machincast.toml"
VENV="${RACINE}/.venv"
ROLES=(lecture indexation interface)

# Prérequis système : ce que pip ne peut pas fournir (https://github.com/dascritch/machincast/issues/51).
# Même liste que CLAUDE.md, sans les outils de développement.
PAQUETS=(
	python3-venv python3-dev build-essential pkg-config libgirepository-2.0-dev libcairo2-dev
	gir1.2-gstreamer-1.0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad
	gstreamer1.0-alsa gstreamer1.0-pulseaudio gstreamer1.0-pipewire pipewire-bin libmagic1t64 postgresql bash-completion
)
# Outils du poste de développement, installés par --dev : ceux de CLAUDE.md.
PAQUETS_DEV=(bats shellcheck desktop-file-utils)

SIMULATION=false
DEV=false
SERVICE=false
RETIRER_SERVICE=false
# Raccourci sur le bureau : demander, oui ou non.
BUREAU=demander
# Programmes de MachinCast en cours (https://github.com/dascritch/machincast/issues/254) : demander, oui ou non ;
# ceux qu'install.sh a arrêtés, à relancer à la fin, même après un échec.
ARRETER=demander
ARRETER_DEMANDE=0
ETAT_DES_PROGRAMMES=""
PROGRAMMES_ARRETES=false
SERVICE_ARRETE=false
# Secondes laissées à un programme pour s'arrêter, avant de l'y forcer.
DELAI_D_ARRET=15
UTILISATEUR="$(id -un)"

aide() {
	cat <<-FIN
		Usage : ./install.sh [--simulation] [--dev] [--service | --retirer-service] [--bureau | --sans-bureau]
		                    [--arreter-les-programmes | --laisser-les-programmes]

		Installe MachinCast en place, depuis ce répertoire (${RACINE}) :
		  0. programmes de MachinCast en cours, sous tous les comptes du poste : Machin lecture (service de
		     diffusion, diffusion d'essai, simulation), Machin indexation, Machin interface. S'ils tournent,
		     la question est posée de les arrêter pendant l'installation, sauf avec --arreter-les-programmes ou
		     --laisser-les-programmes ; sans réponse possible, ils continuent. Arrêtée, la diffusion se tait
		     jusqu'à la fin, et l'interface perd ses fiches non enregistrées. À la fin, même après un échec,
		     install.sh relance le service de diffusion, et la diffusion d'essai et l'interface de ${UTILISATEUR} ;
		     il dit ce qui reste à rouvrir : l'indexation, et les programmes des autres comptes ;
		  1. paquets système (apt) ;
		  2. environnement virtuel Python isolé et dépendances (pip) ;
		  3. machincast.toml, copié du modèle s'il n'existe pas ;
		  4. rôle PostgreSQL du compte ${UTILISATEUR} (sans droit particulier), bases de production et de test
		     dont il est propriétaire, rôles de MachinCast, schéma ;
		  5. autorisation de ${UTILISATEUR} aux rôles ${ROLES[*]}, groupe systemd-journal ;
		  6. liens ${LIEN_INSTALLATION}, ${LIEN_WRAPPER} et l'autocomplétion bash ;
		  7. vérification de la version et des greffons GStreamer, et de la sortie audio ;
		  8. raccourci de l'interface dans le menu des applications de ${UTILISATEUR}, et, s'il le veut,
		     sur son bureau : la question est posée, sauf avec --bureau ou --sans-bureau ; icône de
		     MachinCast dans son thème d'icônes, pour le réglage du son du poste.
		Avec --dev, aussi les outils du poste de développement : ${PAQUETS_DEV[*]} (apt) et les
		dépendances de test (pip, extra [dev]), pour Machin dev et Machin dev-test.
		Avec --service, aussi le service de diffusion ${UNITE}, seulement pour un ordinateur dédié à
		l'antenne : Machin lecture démarre avec le poste, sous le compte ${UTILISATEUR}, et redémarre après un
		plantage ; une règle polkit le laisse démarrer, arrêter et redémarrer avec le mot de passe d'un
		administrateur ; un minuteur systemd, ${MINUTEUR_PURGE}, lance chaque jour à midi Machin purge, qui
		efface de la base ce qui dépasse la durée de péremption. Sans --service, rien de cela n'est installé :
		la diffusion et la purge se lancent à la main.

		Relançable : chaque étape déjà faite est laissée telle quelle.
		À lancer avec son propre compte, pas avec sudo : le script demande sudo quand il le faut.

		Options :
		  --simulation  affiche les commandes sans rien exécuter
		  --dev         installe aussi les outils du poste de développement
		  --service     installe aussi le service de diffusion (ordinateur dédié à l'antenne seulement)
		  --retirer-service
		                retire le service de diffusion, sa règle polkit et le minuteur de la purge
		  --bureau      dépose aussi le raccourci de l'interface sur le bureau, sans le demander
		  --sans-bureau ne le dépose pas sur le bureau, sans le demander
		  --arreter-les-programmes
		                arrête les programmes de MachinCast en cours, sans le demander
		  --laisser-les-programmes
		                les laisse tourner pendant l'installation, sans le demander
		  -h, --help    cette aide
	FIN
}

etape() {
	printf '\n==> %s\n' "$1"
}

info() {
	printf '    %s\n' "$1"
}

echec() {
	printf 'install.sh : %s\n' "$1" >&2
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

verifier_systeme() {
	etape "Système"
	[[ "$(id -u)" -ne 0 ]] || echec "lancer install.sh avec son propre compte, sans sudo : il le demande quand il faut"
	[[ -r /etc/os-release ]] || echec "/etc/os-release illisible : système non reconnu"
	local id version
	id="$(. /etc/os-release && printf '%s' "${ID:-}")"
	version="$(. /etc/os-release && printf '%s' "${VERSION_ID:-}")"
	# Les LTS d'Ubuntu sortent en avril des années paires : 24.04, 26.04…
	if [[ "${id}" != ubuntu ]] || ! [[ "${version}" =~ ^[0-9]*[02468]\.04$ ]]; then
		"${SIMULATION}" || echec "Ubuntu LTS requis (cible : 26.04 LTS), trouvé : ${id} ${version}"
		info "système non pris en charge (${id} ${version}), ignoré en simulation"
	elif [[ "${version}" != 26.04 ]]; then
		info "Ubuntu ${version} LTS : la cible est 26.04 LTS, poursuite de l'installation"
	else
		info "Ubuntu ${version} LTS"
	fi
}

# Programmes de MachinCast en cours (https://github.com/dascritch/machincast/issues/254), lus par
# machincast.programmes avec le python3 du système : le venv peut manquer, ou changer pendant l'installation.
programmes() {
	PYTHONPATH="${RACINE}/src" python3 -m machincast.programmes "$@"
}

vouloir_arreter() {
	local reponse
	case "${ARRETER}" in
		oui) return 0 ;;
		non) return 1 ;;
	esac
	if "${SIMULATION}"; then
		info "[simulation] question : les arrêter pendant l'installation ?"
		return 0
	fi
	if [[ ! -t 0 ]]; then
		info "pas de question sans terminal : ./install.sh --arreter-les-programmes les arrête"
		return 1
	fi
	read -r -p "    Les arrêter pendant l'installation, puis les relancer ? [o/N] " reponse
	[[ "${reponse}" =~ ^[oO] ]]
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
		info "pid ${pid} toujours là après ${DELAI_D_ARRET} s : arrêt forcé"
		if [[ "${du_compte}" == oui ]]; then
			kill -KILL "${pid}" 2>/dev/null || true
		else
			sudo kill -KILL "${pid}" || true
		fi
	done
}

arreter_les_programmes() {
	etape "Programmes de MachinCast en cours"
	ETAT_DES_PROGRAMMES="$(mktemp --tmpdir machincast-programmes.XXXXXX.json)"
	local liste
	if ! liste="$(programmes lister --etat "${ETAT_DES_PROGRAMMES}")"; then
		info "programmes en cours illisibles : l'installation se fait sans les arrêter"
		return
	fi
	if [[ -z "${liste}" ]]; then
		info "aucun"
		return
	fi
	local pid du_compte service libelle
	while IFS=$'\t' read -r pid du_compte service libelle; do
		info "${libelle}, pid ${pid}"
	done <<<"${liste}"
	info "une mise à jour, et ses migrations de la base, ne doit pas se faire sous eux"
	info "arrêtée, la diffusion se tait jusqu'à la fin de l'installation ; l'interface perd ses fiches non enregistrées"
	if ! vouloir_arreter; then
		info "ils continuent : la base peut changer sous eux, les relancer après l'installation"
		return
	fi
	PROGRAMMES_ARRETES=true
	trap relancer_les_programmes EXIT
	local arretes=()
	while IFS=$'\t' read -r pid du_compte service libelle; do
		if [[ "${service}" == oui ]]; then
			if ! "${SERVICE_ARRETE}"; then
				executer sudo systemctl stop "${UNITE}"
				SERVICE_ARRETE=true
			fi
		elif [[ "${du_compte}" == oui ]]; then
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
	info "arrêtés : relancés à la fin de l'installation"
}

# À la fin, ou à la sortie d'install.sh après un échec : une seule fois.
relancer_les_programmes() {
	"${PROGRAMMES_ARRETES}" || return 0
	PROGRAMMES_ARRETES=false
	etape "Relance des programmes de MachinCast"
	if "${SERVICE_ARRETE}"; then
		if "${RETIRER_SERVICE}"; then
			info "service de diffusion retiré : pas relancé"
		else
			executer sudo systemctl start "${UNITE}" || info "service de diffusion non relancé : Machin logs dit pourquoi"
		fi
	fi
	local options=() ligne
	"${SIMULATION}" && options+=(--simulation)
	while IFS= read -r ligne; do
		info "${ligne}"
	done < <(programmes relancer --etat "${ETAT_DES_PROGRAMMES}" "${options[@]}")
	rm --force "${ETAT_DES_PROGRAMMES}" # fichier de MachinCast : état des programmes arrêtés, temporaire
}

installer_paquets() {
	etape "Paquets système"
	executer sudo apt-get update
	local paquets=("${PAQUETS[@]}")
	"${DEV}" && paquets+=("${PAQUETS_DEV[@]}")
	executer sudo apt-get install --yes "${paquets[@]}"
}

installer_venv() {
	etape "Environnement virtuel Python"
	# Jamais --system-site-packages : toutes les dépendances Python viennent de pip.
	if [[ -x "${VENV}/bin/python" ]]; then
		info "${VENV} existe déjà"
	else
		executer python3 -m venv "${VENV}"
	fi
	executer "${VENV}/bin/pip" install --upgrade pip
	if "${DEV}"; then
		executer "${VENV}/bin/pip" install --editable "${RACINE}[dev]"
	else
		executer "${VENV}/bin/pip" install --editable "${RACINE}"
	fi
}

preparer_configuration() {
	etape "Configuration"
	if [[ -e "${CONFIGURATION}" ]]; then
		info "${CONFIGURATION} existe déjà : conservé"
	else
		executer cp "${RACINE}/machincast.exemple.toml" "${CONFIGURATION}"
		info "à adapter : sortie audio, périphériques, sorties (voir doc/spec.md § 9)"
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
	etape "PostgreSQL"
	[[ "${UTILISATEUR}" =~ ^[a-z_][a-z0-9_-]*$ ]] || echec "nom de compte inattendu pour PostgreSQL : ${UTILISATEUR}"
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info "[simulation] bases lues dans ${CONFIGURATION} une fois l'environnement virtuel créé"
		return
	fi
	local lus socket production test
	lus="$(installation bases)" || echec "configuration ${CONFIGURATION} à corriger, puis relancer install.sh"
	{
		read -r socket
		read -r production
		read -r test
	} <<<"${lus}"

	# Le compte courant n'a aucun droit particulier sur le serveur (ni CREATEDB ni CREATEROLE) : tout ce qui en
	# demande est fait par l'utilisateur postgres. Le compte reçoit seulement la propriété des deux bases, qui lui
	# permet d'y appliquer le schéma (doc/spec.md § 3.2).
	if existe_en_base "SELECT 1 FROM pg_roles WHERE rolname = :'nom'" "${UTILISATEUR}"; then
		info "rôle PostgreSQL ${UTILISATEUR} existant"
	else
		executer sudo -u postgres createuser "${UTILISATEUR}"
	fi
	local base
	for base in "${production}" "${test}"; do
		if existe_en_base "SELECT 1 FROM pg_database WHERE datname = :'nom'" "${base}"; then
			info "base ${base} existante"
		else
			executer sudo -u postgres createdb --host="${socket}" --owner="${UTILISATEUR}" "${base}"
		fi
	done
	# Les rôles de groupe appartiennent au serveur. La migration ne les crée que s'ils manquent, ce qui demanderait
	# CREATEROLE : postgres les crée donc d'abord.
	if "${SIMULATION}"; then
		info "[simulation] sudo -u postgres psql : CREATE ROLE ${ROLES[*]/#/machincast_} NOLOGIN, s'ils n'existent pas"
	else
		sudo -u postgres psql --no-psqlrc --quiet --set=ON_ERROR_STOP=1 <<-'SQL'
			DO $$
			DECLARE
				role text;
			BEGIN
				FOREACH role IN ARRAY ARRAY['machincast_lecture', 'machincast_indexation', 'machincast_interface'] LOOP
					IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = role) THEN
						EXECUTE format('CREATE ROLE %I NOLOGIN', role);
					END IF;
				END LOOP;
			END;
			$$;
		SQL
		info "rôles machincast_lecture, machincast_indexation et machincast_interface présents"
	fi
	executer "${VENV}/bin/python" -m machincast.installation migrer --config "${CONFIGURATION}"
	etape "Rôles"
	# Les rôles appartiennent au serveur : une seule autorisation vaut pour les deux bases. Elle est donnée par
	# l'utilisateur postgres, qui peut attribuer les rôles quel que soit le compte qui les a créés. Sans héritage
	# des droits : chaque binaire endosse son rôle par SET ROLE (doc/spec.md § 3.2).
	if "${SIMULATION}"; then
		info "[simulation] sudo -u postgres psql : GRANT machincast_lecture, machincast_indexation, machincast_interface TO ${UTILISATEUR} WITH INHERIT FALSE, SET TRUE"
	else
		sudo -u postgres psql --no-psqlrc --quiet --set=ON_ERROR_STOP=1 --variable=nom="${UTILISATEUR}" <<-'SQL'
			GRANT machincast_lecture, machincast_indexation, machincast_interface TO :"nom" WITH INHERIT FALSE, SET TRUE;
		SQL
		info "${UTILISATEUR} peut endosser les rôles ${ROLES[*]}"
	fi
	# Un superutilisateur endosse tous les rôles sans autorisation, et peut tout faire sur le serveur : l'installation
	# voulue ne donne au compte aucun droit particulier (doc/spec.md § 3.2). install.sh ne retire pas ce droit, qui peut
	# servir à autre chose sur le poste : il le signale.
	if existe_en_base "SELECT 1 FROM pg_roles WHERE rolname = :'nom' AND rolsuper" "${UTILISATEUR}"; then
		info "attention : ${UTILISATEUR} est superutilisateur de PostgreSQL, ce que MachinCast ne demande pas ; pour le"
		info "retirer : sudo -u postgres psql -c 'ALTER ROLE \"${UTILISATEUR}\" NOSUPERUSER'"
	fi
}

autoriser_journal() {
	etape "Journal système"
	if id -nG "${UTILISATEUR}" | tr ' ' '\n' | grep -qx systemd-journal; then
		info "${UTILISATEUR} appartient déjà au groupe systemd-journal"
	else
		# systemd-journal, jamais adm : la lecture du journal sans droits d'administration.
		executer sudo usermod --append --groups systemd-journal "${UTILISATEUR}"
		info "effectif après le redémarrage du poste"
	fi
}

relier() {
	local cible="$1" lien="$2"
	if [[ -e "${lien}" && ! -L "${lien}" ]]; then
		echec "${lien} existe et n'est pas un lien symbolique : le déplacer avant de relancer install.sh"
	fi
	if [[ -L "${lien}" && "$(readlink "${lien}")" == "${cible}" ]]; then
		info "${lien} → ${cible}"
	else
		executer sudo ln --symbolic --force --no-dereference "${cible}" "${lien}"
	fi
}

installer_liens() {
	etape "Liens"
	relier "${RACINE}" "${LIEN_INSTALLATION}"
	relier "${LIEN_INSTALLATION}/bin/Machin" "${LIEN_WRAPPER}"
	relier "${LIEN_INSTALLATION}/bash-completion/Machin" "${LIEN_COMPLETION}"
}

verifier_greffons() {
	etape "Version et greffons GStreamer, sortie audio"
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info "[simulation] vérification faite une fois l'environnement virtuel créé"
		return
	fi
	installation verifier || echec "installer les paquets indiqués, puis relancer install.sh"
}

# Installe le fichier rédigé par machincast.installation, s'il diffère de celui en place ; vrai s'il a changé.
installer_fichier() {
	local action="$1" destination="$2" redige
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info "[simulation] ${destination}, rédigé par machincast.installation ${action}"
		return 0
	fi
	redige="$(mktemp)"
	# Appelée par if ou ||, la fonction ne s'arrête pas d'elle-même sur une erreur (set -e) : jamais de fichier vide.
	installation "${action}" >"${redige}" || echec "machincast.installation ${action} a échoué : ${destination} non installé"
	if [[ -r "${destination}" ]] && cmp --silent "${redige}" "${destination}"; then
		info "${destination} est à jour"
		rm --force "${redige}" # fichier de MachinCast : unité ou règle rédigée, temporaire
		return 1
	fi
	executer sudo install --mode=644 --owner=root --group=root "${redige}" "${destination}"
	rm --force "${redige}" # fichier de MachinCast : unité ou règle rédigée, temporaire
	return 0
}

# Installe pour le compte, sans sudo, le raccourci rédigé par machincast.installation, s'il diffère de celui en place
# ou n'a pas les droits voulus ; vrai s'il a changé.
installer_raccourci_en() {
	local destination="$1" droits="$2" redige
	if "${SIMULATION}" && [[ ! -x "${VENV}/bin/python" ]]; then
		info "[simulation] ${destination}, rédigé par machincast.installation raccourci"
		return 0
	fi
	redige="$(mktemp)"
	installation raccourci >"${redige}" || echec "machincast.installation raccourci a échoué : ${destination} non installé"
	if [[ -r "${destination}" ]] && cmp --silent "${redige}" "${destination}" \
		&& [[ "$(stat --format=%a "${destination}")" == "${droits}" ]]; then
		info "${destination} est à jour"
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

# Vrai si le raccourci va sur le bureau : déjà là, demandé par --bureau, ou accepté à la question.
vouloir_le_bureau() {
	local raccourci="$1" reponse
	case "${BUREAU}" in
		oui) return 0 ;;
		non) return 1 ;;
	esac
	[[ -e "${raccourci}" ]] && return 0
	if "${SIMULATION}"; then
		info "[simulation] question : déposer aussi le raccourci sur le bureau ?"
		return 0
	fi
	if [[ ! -t 0 ]]; then
		info "pas de question sans terminal : ./install.sh --bureau le dépose sur le bureau"
		return 1
	fi
	read -r -p "    Déposer aussi le raccourci de MachinCast sur le bureau ? [O/n] " reponse
	[[ ! "${reponse}" =~ ^[nN] ]]
}

# Installe pour le compte, sans sudo, l'icône de MachinCast dans son thème d'icônes, si elle diffère de celle en place.
installer_icone() {
	local destination="$1" source="${RACINE}/src/machincast/interface/machincast.png"
	if [[ -r "${destination}" ]] && cmp --silent "${source}" "${destination}"; then
		info "${destination} est à jour"
		return
	fi
	executer install -D --mode=644 "${source}" "${destination}"
}

installer_raccourci() {
	etape "Raccourci de l'interface"
	installer_raccourci_en "${DOSSIER_APPLICATIONS}/${RACCOURCI}" 644 || true
	installer_icone "${ICONE_DU_THEME}"
	local bureau
	bureau="$(dossier_du_bureau)"
	if [[ -z "${bureau}" ]]; then
		info "pas de dossier de bureau pour ${UTILISATEUR} : raccourci dans le menu des applications seulement"
		return
	fi
	if vouloir_le_bureau "${bureau}/${RACCOURCI}"; then
		# Exécutable : Plasma lance alors le raccourci du bureau sans demander de confirmation.
		installer_raccourci_en "${bureau}/${RACCOURCI}" 755 || true
	elif [[ -e "${bureau}/${RACCOURCI}" ]]; then
		info "${bureau}/${RACCOURCI} laissé tel quel"
	else
		info "pas de raccourci sur le bureau ; ./install.sh --bureau l'y dépose"
	fi
}

installer_service() {
	etape "Service de diffusion"
	if ! "${SERVICE}"; then
		info "non installé : la diffusion se lance à la main, par Machin lecture"
		info "sur un ordinateur dédié à l'antenne : ./install.sh --service"
		return
	fi
	info "pour un ordinateur dédié à l'antenne : Machin lecture démarre avec le poste, sous ${UTILISATEUR}"
	# La session du compte reste active sans connexion : PipeWire ou PulseAudio y tournent, comme la socket d'état.
	if [[ "$(loginctl show-user "${UTILISATEUR}" --property=Linger --value 2>/dev/null)" == yes ]]; then
		info "la session de ${UTILISATEUR} reste active au démarrage du poste"
	else
		executer sudo loginctl enable-linger "${UTILISATEUR}"
	fi
	local unite_changee=false purge_changee=false
	if installer_fichier unite "${FICHIER_UNITE}"; then
		unite_changee=true
	fi
	if installer_fichier unite-purge "${FICHIER_UNITE_PURGE}"; then
		purge_changee=true
	fi
	if installer_fichier minuteur-purge "${FICHIER_MINUTEUR_PURGE}"; then
		purge_changee=true
	fi
	if "${unite_changee}" || "${purge_changee}"; then
		executer sudo systemctl daemon-reload
	fi
	installer_fichier regle "${FICHIER_REGLE}" || true
	executer sudo systemctl enable --now "${UNITE}"
	if "${unite_changee}"; then
		# Une unité modifiée ne vaut qu'au redémarrage du service, s'il tournait déjà.
		executer sudo systemctl try-restart "${UNITE}"
	fi
	# La purge de la base, chaque jour à midi : Machin purge, sous le même compte.
	executer sudo systemctl enable --now "${MINUTEUR_PURGE}"
	info "suivre la diffusion : Machin logs ; la purge quotidienne : journalctl --unit=${UNITE_PURGE}"
}

retirer_service() {
	etape "Retrait du service de diffusion"
	if [[ -e "${FICHIER_UNITE}" ]]; then
		executer sudo systemctl disable --now "${UNITE}"
		executer sudo rm --force "${FICHIER_UNITE}" # fichier de MachinCast : unité installée par --service
		executer sudo systemctl daemon-reload
	else
		info "${FICHIER_UNITE} absent"
	fi
	if [[ -e "${FICHIER_MINUTEUR_PURGE}" ]]; then
		executer sudo systemctl disable --now "${MINUTEUR_PURGE}"
		executer sudo rm --force "${FICHIER_MINUTEUR_PURGE}" # fichier de MachinCast : minuteur installé par --service
	else
		info "${FICHIER_MINUTEUR_PURGE} absent"
	fi
	if [[ -e "${FICHIER_UNITE_PURGE}" ]]; then
		executer sudo rm --force "${FICHIER_UNITE_PURGE}" # fichier de MachinCast : unité installée par --service
		executer sudo systemctl daemon-reload
	else
		info "${FICHIER_UNITE_PURGE} absent"
	fi
	if [[ -e "${FICHIER_REGLE}" ]]; then
		executer sudo rm --force "${FICHIER_REGLE}" # fichier de MachinCast : règle installée par --service
	else
		info "${FICHIER_REGLE} absent"
	fi
	info "la session de ${UTILISATEUR} reste active au démarrage : sudo loginctl disable-linger ${UTILISATEUR} la retire"
	info "la diffusion se lance de nouveau à la main, par Machin lecture ; la purge de la base, par Machin purge"
}

conclure() {
	etape "Installation terminée"
	info "Aide : Machin --help"
	info "Interface : MachinCast, dans le menu des applications, ou Machin interface"
	info "Première indexation : Machin indexation, puis Machin indexation --audit-complet"
	if "${DEV}"; then
		info "Poste de développement : Machin dev ouvre un shell, venv activé ; Machin dev-test lance les vérifications"
	fi
}

principal() {
	while (($# > 0)); do
		case "$1" in
			--simulation) SIMULATION=true ;;
			--dev) DEV=true ;;
			--service) SERVICE=true ;;
			--retirer-service) RETIRER_SERVICE=true ;;
			--bureau) BUREAU=oui ;;
			--sans-bureau) BUREAU=non ;;
			--arreter-les-programmes)
				ARRETER=oui
				ARRETER_DEMANDE=$((ARRETER_DEMANDE + 1))
				;;
			--laisser-les-programmes)
				ARRETER=non
				ARRETER_DEMANDE=$((ARRETER_DEMANDE + 1))
				;;
			-h | --help)
				aide
				exit 0
				;;
			*)
				aide >&2
				echec "option inconnue : $1"
				;;
		esac
		shift
	done
	if "${SERVICE}" && "${RETIRER_SERVICE}"; then
		echec "--service et --retirer-service ne vont pas ensemble"
	fi
	if [[ "${ARRETER}" != demander ]] && ((ARRETER_DEMANDE > 1)); then
		echec "--arreter-les-programmes et --laisser-les-programmes ne vont pas ensemble"
	fi
	cd "${RACINE}"
	verifier_systeme
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
