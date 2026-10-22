"""Maintenance de la base de données : Machin maintenance-db (https://github.com/dascritch/machincast/issues/127).

Sur la base de production de la configuration, trois étapes, dans l'ordre :

1. sauvegarde : pg_dump, au format personnalisé de PostgreSQL, dans un fichier daté du répertoire des sauvegardes
   (--sauvegardes, par défaut « sauvegardes » à côté du fichier de configuration), lisible par pg_restore. Une
   sauvegarde qui échoue arrête tout : rien n'est modifié sans sauvegarde ;
2. schéma : les migrations manquantes sont appliquées, puis chaque rôle de MachinCast doit être endossable par le
   compte ; un rôle qui ne l'est pas est signalé avec les commandes, à lancer par un administrateur, qui l'autorisent ;
3. optimisation : VACUUM (ANALYZE), qui récupère la place des lignes effacées et met à jour les statistiques ;
   la diffusion peut continuer pendant ce temps.

Le compte de MachinCast est propriétaire de la base et de ses tables : il fait tout cela sans endosser de rôle, et
sans droit particulier sur le serveur. Avec --attendre, la maintenance attend Entrée avant de rendre la main, pour
qu'une fenêtre de terminal ouverte par l'interface reste lisible. Le code de sortie est 0 si tout s'est bien passé,
1 sinon.
"""

import argparse
import getpass
import logging
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import psycopg
from yoyo import get_backend, read_migrations

from machincast.base import REPERTOIRE_MIGRATIONS, Role, url_yoyo
from machincast.cli import lancer
from machincast.configuration import Configuration
from machincast.horloge import Horloge, HorlogeSysteme
from machincast.protection import verifier_ecriture

EXECUTABLE = "Machin_maintenance-db"
DESCRIPTION = "Sauvegarde, vérifie et optimise la base de données de MachinCast."
CODE_ECHEC = 1
SAUVEGARDES = "sauvegardes"
"""Répertoire des sauvegardes, à côté du fichier de configuration, sauf --sauvegardes."""
DELAI_DE_SAUVEGARDE = 3600
"""Secondes laissées à pg_dump : une grosse base, sur un disque lent, prend du temps."""
ROLES: tuple[str, ...] = tuple(role.value for role in Role)
"""Les rôles que le compte doit pouvoir endosser."""
HORLOGE: Horloge = HorlogeSysteme()
"""L'heure qui date les sauvegardes ; les scénarios la fixent."""
ENTREE = "Appuyer sur Entrée pour fermer."

# Nom explicite : lancé par son script, ce module garde le journal « machincast ».
journal = logging.getLogger("machincast.maintenance")


class EchecDeSauvegarde(Exception):
	"""La sauvegarde n'a pas pu être faite : la maintenance s'arrête."""


def sauvegardes_par_defaut(fichier_de_configuration: Path) -> Path:
	"""Le répertoire des sauvegardes sans --sauvegardes : « sauvegardes », à côté du fichier de configuration."""
	return fichier_de_configuration.parent / SAUVEGARDES


def compte() -> str:
	"""Le compte qui lance la maintenance, celui de MachinCast."""
	return getpass.getuser()


def sauvegarder(configuration: Configuration, repertoire: Path) -> Path:
	"""pg_dump de la base de production dans un nouveau fichier daté ; lève EchecDeSauvegarde."""
	base = configuration.base
	commande = shutil.which("pg_dump")
	if commande is None:
		raise EchecDeSauvegarde("pg_dump introuvable, installer postgresql-client")
	horodatage = f"{HORLOGE.maintenant().astimezone():%Y-%m-%dT%H-%M-%S}"
	fichier = repertoire / f"{base.production}-{horodatage}.dump"
	journal.info(f"sauvegarde de la base {base.production} dans {fichier}")
	verifier_ecriture(fichier)
	if fichier.exists():
		raise EchecDeSauvegarde(f"{fichier} existe déjà, relancer dans une seconde")
	try:
		repertoire.mkdir(parents=True, exist_ok=True)
		resultat = subprocess.run(
			[commande, "--format=custom", f"--file={fichier}", f"--host={base.socket}", base.production],
			capture_output=True,
			text=True,
			timeout=DELAI_DE_SAUVEGARDE,
			stdin=subprocess.DEVNULL,
		)
	except (OSError, subprocess.SubprocessError) as erreur:
		raise EchecDeSauvegarde(str(erreur)) from erreur
	if resultat.returncode != 0:
		raise EchecDeSauvegarde(resultat.stderr.strip())
	taille = fichier.stat().st_size / 1_000_000
	journal.info(f"sauvegarde faite : {taille:.1f} Mo".replace(".", ","))
	return fichier


def mettre_a_jour_le_schema(configuration: Configuration) -> None:
	"""Les migrations manquantes ; aucune si le schéma est à jour."""
	base = configuration.base
	with get_backend(url_yoyo(base.socket, base.production)) as backend, backend.lock():
		manquantes = backend.to_apply(read_migrations(str(REPERTOIRE_MIGRATIONS)))
		backend.apply_migrations(manquantes)
	nombre = len(manquantes)
	if nombre == 0:
		journal.info(f"schéma de la base {base.production} à jour")
		return
	pluriel = "s" if nombre > 1 else ""
	journal.info(f"schéma de la base {base.production} : {nombre} migration{pluriel} appliquée{pluriel}")


def verifier_les_roles(connexion: psycopg.Connection[tuple[object, ...]]) -> bool:
	"""Chaque rôle de MachinCast existe, et le compte peut l'endosser ; sinon, ce qu'un administrateur doit faire."""
	en_ordre = True
	for role in ROLES:
		ligne = connexion.execute(
			"SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s)"
			" AND pg_has_role(current_user, (SELECT oid FROM pg_roles WHERE rolname = %s), 'SET')",
			(role, role),
		).fetchone()
		if (ligne is not None) and (ligne[0] is True):
			continue
		en_ordre = False
		journal.error(
			f"rôle {role} : absent du serveur, ou non endossable par le compte ; à faire par un administrateur :"
			f' sudo -u postgres psql -c "CREATE ROLE {role} NOLOGIN" ;'
			f' sudo -u postgres psql -c "GRANT {role} TO {compte()} WITH INHERIT FALSE, SET TRUE"'
		)
	if en_ordre:
		journal.info(f"rôles {', '.join(ROLES)} endossables par le compte")
	return en_ordre


def optimiser(connexion: psycopg.Connection[tuple[object, ...]], nom: str) -> None:
	"""VACUUM ne s'exécute pas dans une transaction : la connexion est en autocommit."""
	connexion.execute("VACUUM (ANALYZE)")
	journal.info(f"base {nom} optimisée (VACUUM ANALYZE)")


def maintenir(configuration: Configuration, repertoire: Path) -> bool:
	"""Les trois étapes ; vrai si tout s'est bien passé. Lève EchecDeSauvegarde, psycopg.Error."""
	base = configuration.base
	sauvegarder(configuration, repertoire)
	mettre_a_jour_le_schema(configuration)
	with psycopg.connect(host=str(base.socket), dbname=base.production, autocommit=True) as connexion:
		roles = verifier_les_roles(connexion)
		optimiser(connexion, base.production)
	return roles


def options_propres(analyseur: argparse.ArgumentParser) -> None:
	analyseur.add_argument(
		"--sauvegardes",
		type=Path,
		metavar="REPERTOIRE",
		help=f"répertoire des sauvegardes ; par défaut « {SAUVEGARDES} », à côté du fichier de configuration",
	)
	analyseur.add_argument(
		"--attendre",
		action="store_true",
		help="attend Entrée avant de rendre la main : pour une fenêtre de terminal, comme l'ouvre l'interface",
	)


def executer(configuration: Configuration, options: argparse.Namespace) -> int:
	repertoire = (options.sauvegardes) or (sauvegardes_par_defaut(configuration.chemin))
	code = CODE_ECHEC
	try:
		if maintenir(configuration, Path(repertoire).expanduser()):
			journal.info("maintenance terminée")
			code = 0
		else:
			journal.info("maintenance terminée, avec des anomalies")
	except EchecDeSauvegarde as erreur:
		journal.error(f"sauvegarde impossible : {erreur} ; maintenance arrêtée, rien n'a été modifié")
	except psycopg.OperationalError as erreur:
		journal.error(f"base de données injoignable ({configuration.base.production}) : {erreur}")
	except psycopg.Error as erreur:
		journal.error(f"erreur de base de données : {erreur}")
	if options.attendre:
		sys.stdout.write(f"{ENTREE}\n")
		sys.stdout.flush()
		sys.stdin.readline()
	return code


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, executer, options_propres)
