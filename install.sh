#!/usr/bin/env bash
# Installation de MachinCast sur un poste Ubuntu LTS (https://github.com/dascritch/machincast/issues/40).
#
#   ./install.sh               installe, ou met à jour une installation existante : le script est relançable
#   ./install.sh --simulation  affiche les commandes sans rien exécuter
#   ./install.sh --dev         installe aussi les outils du poste de développement
#                              (https://github.com/dascritch/machincast/issues/77)
#   ./install.sh --service     installe aussi le service de diffusion : pour un ordinateur dédié à l'antenne
#                              (https://github.com/dascritch/machincast/issues/22)
#   ./install.sh --retirer-service   retire ce service, la diffusion se lance de nouveau à la main
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
CONFIGURATION="${RACINE}/machincast.toml"
VENV="${RACINE}/.venv"
ROLES=(lecture indexation interface)

# Prérequis système : ce que pip ne peut pas fournir (https://github.com/dascritch/machincast/issues/51).
# Même liste que CLAUDE.md, sans les outils de développement.
PAQUETS=(
	python3-venv python3-dev build-essential pkg-config libgirepository-2.0-dev libcairo2-dev
	gir1.2-gstreamer-1.0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad
	gstreamer1.0-alsa gstreamer1.0-pulseaudio gstreamer1.0-pipewire libmagic1t64 postgresql bash-completion
)
# Outils du poste de développement, installés par --dev : ceux de CLAUDE.md.
PAQUETS_DEV=(bats shellcheck)

SIMULATION=false
DEV=false
SERVICE=false
RETIRER_SERVICE=false
UTILISATEUR="$(id -un)"

aide() {
	cat <<-FIN
		Usage : ./install.sh [--simulation] [--dev]

		Installe MachinCast en place, depuis ce répertoire (${RACINE}) :
		  1. paquets système (apt) ;
		  2. environnement virtuel Python isolé et dépendances (pip) ;
		  3. machincast.toml, copié du modèle s'il n'existe pas ;
		  4. rôle PostgreSQL du compte ${UTILISATEUR} (sans droit particulier), bases de production et de test
		     dont il est propriétaire, rôles de MachinCast, schéma ;
		  5. autorisation de ${UTILISATEUR} aux rôles ${ROLES[*]}, groupe systemd-journal ;
		  6. liens ${LIEN_INSTALLATION}, ${LIEN_WRAPPER} et l'autocomplétion bash ;
		  7. vérification des greffons GStreamer et de la sortie audio.
		Avec --dev, aussi les outils du poste de développement : ${PAQUETS_DEV[*]} (apt) et les
		dépendances de test (pip, extra [dev]), pour Machin dev et Machin dev-test.
		Avec --service, aussi le service de diffusion ${UNITE}, seulement pour un ordinateur dédié à
		l'antenne : Machin lecture démarre avec le poste, sous le compte ${UTILISATEUR}, et redémarre après un
		plantage ; une règle polkit le laisse démarrer, arrêter et redémarrer avec le mot de passe d'un
		administrateur. Sans --service, rien de cela n'est installé : la diffusion se lance à la main.

		Relançable : chaque étape déjà faite est laissée telle quelle.
		À lancer avec son propre compte, pas avec sudo : le script demande sudo quand il le faut.

		Options :
		  --simulation  affiche les commandes sans rien exécuter
		  --dev         installe aussi les outils du poste de développement
		  --service     installe aussi le service de diffusion (ordinateur dédié à l'antenne seulement)
		  --retirer-service
		                retire le service de diffusion et sa règle polkit
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
	etape "Greffons GStreamer et sortie audio"
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
	installation "${action}" >"${redige}"
	if [[ -r "${destination}" ]] && cmp --silent "${redige}" "${destination}"; then
		info "${destination} est à jour"
		rm --force "${redige}" # fichier de MachinCast : unité ou règle rédigée, temporaire
		return 1
	fi
	executer sudo install --mode=644 --owner=root --group=root "${redige}" "${destination}"
	rm --force "${redige}" # fichier de MachinCast : unité ou règle rédigée, temporaire
	return 0
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
	local unite_changee=false
	if installer_fichier unite "${FICHIER_UNITE}"; then
		unite_changee=true
		executer sudo systemctl daemon-reload
	fi
	installer_fichier regle "${FICHIER_REGLE}" || true
	executer sudo systemctl enable --now "${UNITE}"
	if "${unite_changee}"; then
		# Une unité modifiée ne vaut qu'au redémarrage du service, s'il tournait déjà.
		executer sudo systemctl try-restart "${UNITE}"
	fi
	info "suivre la diffusion : Machin logs"
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
	if [[ -e "${FICHIER_REGLE}" ]]; then
		executer sudo rm --force "${FICHIER_REGLE}" # fichier de MachinCast : règle installée par --service
	else
		info "${FICHIER_REGLE} absent"
	fi
	info "la session de ${UTILISATEUR} reste active au démarrage : sudo loginctl disable-linger ${UTILISATEUR} la retire"
	info "la diffusion se lance de nouveau à la main, par Machin lecture"
}

conclure() {
	etape "Installation terminée"
	info "Aide : Machin --help"
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
	cd "${RACINE}"
	verifier_systeme
	installer_paquets
	installer_venv
	preparer_configuration
	preparer_postgresql
	autoriser_journal
	installer_liens
	verifier_greffons
	if "${RETIRER_SERVICE}"; then
		retirer_service
	else
		installer_service
	fi
	conclure
}

principal "$@"
