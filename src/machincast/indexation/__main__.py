"""Point d'entrée de Machin_indexation.

Parcours des répertoires des banques (https://github.com/dascritch/machincast/issues/9), puis vérification
des sonores (https://github.com/dascritch/machincast/issues/7), en indexation rapide par défaut ou en audit
complet (https://github.com/dascritch/machincast/issues/69). Avec --fenetre, l'indexation montre son journal dans une
fenêtre, ligne par ligne : c'est ainsi que l'interface la lance, dans un processus à part
(https://github.com/dascritch/machincast/issues/120). Avec --sonore, seul ce sonore est vérifié, sans parcours des
répertoires, sans verrou et sans document d'audit : c'est ainsi que Machin lecture fait analyser le prochain sonore
qu'il va jouer (https://github.com/dascritch/machincast/issues/181).
"""

import argparse
import logging
from collections.abc import Sequence

import psycopg

from machincast.base import Role, connecter
from machincast.cli import CODE_CONFIGURATION_INVALIDE, lancer
from machincast.configuration import Configuration
from machincast.indexation import audit
from machincast.indexation.decodage import DecodeurIndisponible
from machincast.indexation.indexeur import IndexationEnCours, indexer, indexer_un_sonore
from machincast.indexation.verification import texte_bilan
from machincast.interface.__main__ import affichage_disponible

EXECUTABLE = "Machin_indexation"
DESCRIPTION = "Vérifie les sonores et indexe les répertoires des banques."

CODE_ECHEC = 1

# Nom explicite : lancé par python -m, ce module s'appelle __main__, hors du journal « machincast ».
journal = logging.getLogger("machincast.indexation")


def options_propres(analyseur: argparse.ArgumentParser) -> None:
	analyseur.add_argument(
		"--audit-complet",
		action="store_true",
		help="décode tous les sonores ; par défaut, l'indexation rapide ne décode que les sonores en aperçu",
	)
	analyseur.add_argument(
		"--fenetre",
		action="store_true",
		help="montre le journal de l'indexation dans une fenêtre, ligne par ligne, comme le lance l'interface",
	)
	analyseur.add_argument(
		"--sonore",
		type=int,
		metavar="N",
		help="ne vérifie que le sonore N, sans parcourir les répertoires ni écrire de document d'audit ;"
		" avec --audit-complet, son fichier est décodé quoi qu'il en soit",
	)


def executer(configuration: Configuration, options: argparse.Namespace) -> int:
	base = configuration.base
	if (options.sonore is not None) and (options.fenetre):
		journal.error("--sonore ne s'emploie pas avec --fenetre")
		return CODE_CONFIGURATION_INVALIDE
	if options.sonore is not None:
		return verifier_un_sonore(configuration, options.sonore, options.audit_complet)
	if options.fenetre:
		if not affichage_disponible():
			journal.error(
				"--fenetre demande un affichage graphique : sans lui, lancer Machin indexation sans --fenetre"
			)
			return CODE_ECHEC
		# PySide6 n'est importé qu'ici : sans --fenetre, l'indexation ne demande aucun affichage graphique.
		from machincast.interface.journal_indexation import lancer_fenetre

		return lancer_fenetre(base.socket, base.production, options.audit_complet, configuration.blancs.seuil)
	debut = audit.HORLOGE.maintenant()
	try:
		with connecter(base.socket, base.production, Role.INDEXATION) as connexion:
			bilan = indexer(connexion, audit_complet=options.audit_complet, seuil_blancs=configuration.blancs.seuil)
	except psycopg.OperationalError as erreur:
		journal.error(f"base de données injoignable ({base.production} par {base.socket}) : {erreur}")
		return CODE_ECHEC
	except psycopg.Error as erreur:
		journal.error(f"erreur de base de données : {erreur}")
		return CODE_ECHEC
	except DecodeurIndisponible as erreur:
		journal.error(f"vérification interrompue : {erreur}")
		return CODE_ECHEC
	except IndexationEnCours as erreur:
		journal.error(f"indexation refusée : {erreur}")
		return CODE_ECHEC
	journal.info(texte_bilan(bilan))
	audit.produire(bilan.anomalies, texte_bilan(bilan), debut)
	return 0


def verifier_un_sonore(configuration: Configuration, sonore: int, audit_complet: bool) -> int:
	"""Ce sonore seulement, s'il est un fichier : sans verrou, comme la vérification des fichiers ajoutés depuis
	l'interface, car une indexation en cours peut le vérifier aussi sans dommage."""
	base = configuration.base
	try:
		with connecter(base.socket, base.production, Role.INDEXATION) as connexion:
			with connexion.transaction():
				fichier = connexion.execute(
					"SELECT 1 FROM sonores WHERE id = %s AND type = 'fichier'", (sonore,)
				).fetchone()
			if fichier is None:
				journal.error(f"sonore {sonore} : inconnu, ou pas un fichier")
				return CODE_ECHEC
			bilan = indexer_un_sonore(connexion, sonore, audit_complet, configuration.blancs.seuil)
	except psycopg.OperationalError as erreur:
		journal.error(f"base de données injoignable ({base.production} par {base.socket}) : {erreur}")
		return CODE_ECHEC
	except psycopg.Error as erreur:
		journal.error(f"erreur de base de données : {erreur}")
		return CODE_ECHEC
	except DecodeurIndisponible as erreur:
		journal.error(f"vérification interrompue : {erreur}")
		return CODE_ECHEC
	journal.info(texte_bilan(bilan))
	return 0


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, executer, options_propres)


if __name__ == "__main__":
	raise SystemExit(main())
