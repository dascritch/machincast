"""Point d'entrée de Machin_interface (https://github.com/dascritch/machincast/issues/23).

Se connecte à la base de production avec le rôle de l'interface, puis ouvre sa fenêtre à onglets, sur l'écran par
défaut (https://github.com/dascritch/machincast/issues/26). Sans base joignable, s'arrête avec le code 1, après une
fenêtre d'erreur qui renvoie à INSTALL.md quand un affichage graphique peut la montrer.
"""

import argparse
import logging
import os
from collections.abc import Mapping, Sequence

import psycopg

from machincast.base import Role, connecter
from machincast.cli import lancer
from machincast.configuration import REPERTOIRE_PROJET, Configuration
from machincast.horloge import HorlogeSysteme

EXECUTABLE = "Machin_interface"
DESCRIPTION = "Interface graphique de supervision et de programmation de MachinCast."

CODE_ECHEC = 1

# Nom explicite : lancé par python -m, ce module s'appelle __main__, hors du journal « machincast ».
journal = logging.getLogger("machincast.interface")


PLATEFORMES_INVISIBLES = frozenset({"offscreen", "minimal"})
"""Plateformes Qt qui ne montrent rien à personne, comme celle des tests."""


def affichage_disponible(environnement: Mapping[str, str] = os.environ) -> bool:
	"""Une fenêtre peut-elle être vue ? Pas sans affichage graphique, par exemple dans une session SSH, où Qt
	s'arrêterait net, ni sur une plateforme Qt invisible."""
	plateforme = environnement.get("QT_QPA_PLATFORM", "")
	if plateforme in PLATEFORMES_INVISIBLES:
		return False
	return (
		(plateforme != "")
		or (environnement.get("DISPLAY", "") != "")
		or (environnement.get("WAYLAND_DISPLAY", "") != "")
	)


def signaler_la_base(configuration: Configuration, erreur: psycopg.Error) -> None:
	"""Sans base, une fenêtre d'erreur explique pourquoi l'interface n'est pas utilisable."""
	if not affichage_disponible():
		return
	from machincast.interface.application import application
	from machincast.interface.erreur import FenetreBaseInjoignable

	# L'application doit exister tant que la fenêtre est montrée.
	qt = application(EXECUTABLE)
	base = configuration.base
	fenetre = FenetreBaseInjoignable(base.production, base.socket, str(erreur), REPERTOIRE_PROJET / "INSTALL.md")
	fenetre.montrer()
	qt.processEvents()


def executer(configuration: Configuration, options: argparse.Namespace) -> int:
	base = configuration.base
	try:
		connexion = connecter(base.socket, base.production, Role.INTERFACE)
	except psycopg.OperationalError as erreur:
		journal.error(f"base de données injoignable ({base.production} par {base.socket}) : {erreur}")
		signaler_la_base(configuration, erreur)
		return CODE_ECHEC
	except psycopg.Error as erreur:
		journal.error(f"erreur de base de données : {erreur}")
		signaler_la_base(configuration, erreur)
		return CODE_ECHEC
	with connexion:
		# PySide6 n'est importé qu'ici : l'aide et les erreurs de configuration ou de base restent disponibles sans
		# affichage graphique.
		from machincast.interface.application import application
		from machincast.interface.fenetre import FenetrePrincipale
		from machincast.interface.indexation import commande_indexation

		qt = application(EXECUTABLE)
		fenetre = FenetrePrincipale(
			connexion,
			configuration.lecture.socket_etat,
			HorlogeSysteme(),
			commande_indexation=commande_indexation(options.config),
			configuration=configuration.chemin,
			crossfades=configuration.crossfades,
			audio=configuration.audio,
			blancs=configuration.blancs,
		)
		fenetre.show()
		return qt.exec()


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, executer)


if __name__ == "__main__":
	raise SystemExit(main())
