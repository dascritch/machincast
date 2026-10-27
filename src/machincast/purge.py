"""Purge de la base de données : Machin purge (https://github.com/dascritch/machincast/issues/268).

Efface de la base de production ce qui dépasse la durée de péremption (base.peremption de la configuration, 60 jours
par défaut, réglable aussi dans Fichier → Préférences… de l'interface), comptée depuis l'heure du lancement :

- les passages de l'airplay finis avant la limite : un passage commencé avant et fini après reste entier ;
- les lignes du log d'avant la limite ;
- les sonores, banques, séquences et événements supprimés depuis l'interface avant la limite
  (https://github.com/dascritch/machincast/issues/267) ;
- les sonores dont l'indexation a constaté la disparition du fichier avant la limite.
- les sessions sautées des événements récurrents d'avant la limite (https://github.com/dascritch/machincast/issues/273),
  sans les compter dans le bilan.

Les passages plus récents d'un sonore effacé gardent l'emplacement, l'artiste et le titre recopiés lors du passage.
Tout est effacé en une seule transaction ; le bilan va au journal et, ligne « purge », au log de la base. Seules des
lignes de la base sont effacées : jamais un fichier sonore, ni un répertoire
(https://github.com/dascritch/machincast/issues/96).

Le compte de MachinCast est propriétaire de la base et de ses tables : il efface sans endosser de rôle, aucun des
trois rôles n'ayant le droit d'effacer l'airplay ou le log. install.sh --service installe un minuteur systemd qui
lance la purge chaque jour à midi. Le code de sortie est 0 si la purge s'est faite, 1 sinon.
"""

import argparse
import logging
from collections.abc import Sequence
from datetime import datetime, timedelta

import psycopg

from machincast.cli import lancer
from machincast.configuration import Configuration
from machincast.horloge import Horloge, HorlogeSysteme

EXECUTABLE = "Machin_purge"
DESCRIPTION = "Efface de la base de données ce qui dépasse la durée de péremption."
CODE_ECHEC = 1
HORLOGE: Horloge = HorlogeSysteme()
"""L'heure d'où se compte la péremption ; les scénarios la fixent."""

# Nom explicite : lancé par son script, ce module garde le journal « machincast ».
journal = logging.getLogger("machincast.purge")

PASSAGES = """
	DELETE FROM airplay WHERE passage_id IN (
		SELECT passage_id FROM airplay GROUP BY passage_id HAVING max(horodatage) < %s
	) RETURNING passage_id
"""
ELEMENTS = (
	# LEAST ignore les valeurs vides : la suppression, ou la disparition du fichier, que l'indexation ne date que pour
	# un sonore à l'état supprime, et efface quand le fichier revient.
	("sonore", "sonores", "LEAST(supprime_le, disparu_le)"),
	("banque", "banques", "supprime_le"),
	("séquence", "sequences", "supprime_le"),
	("événement", "evenements", "supprime_le"),
)
"""Le genre, sa table, et la date d'où se compte la péremption d'une ligne."""


def _nombre(nombre: int, nom: str, complement: str = "") -> str:
	"""« 0 sonore », « 1 sonore », « 2 sonores » : le pluriel français commence à deux."""
	if nombre > 1:
		nom = f"{nom}s"
	return f"{nombre} {nom}{complement}"


def purger(connexion: psycopg.Connection[tuple[object, ...]], limite: datetime) -> list[str]:
	"""Efface ce qui est d'avant la limite, dans la transaction de la connexion ; le bilan, genre par genre."""
	passages = {passage for (passage,) in connexion.execute(PASSAGES, (limite,)).fetchall()}
	lignes = connexion.execute("DELETE FROM log WHERE horodatage < %s", (limite,)).rowcount
	bilan = [_nombre(len(passages), "passage", " de l'airplay"), _nombre(lignes, "ligne", " du log")]
	for genre, table, date in ELEMENTS:
		effaces = connexion.execute(f"DELETE FROM {table} WHERE {date} < %s", (limite,)).rowcount  # noqa: S608
		bilan.append(_nombre(effaces, genre))
	# Une session sautée d'avant la limite ne compte plus pour rien (https://github.com/dascritch/machincast/issues/273).
	connexion.execute("DELETE FROM evenements_sauts WHERE jour < %s", (limite.date(),))
	return bilan


def executer(configuration: Configuration, _options: argparse.Namespace) -> int:
	base = configuration.base
	limite = (HORLOGE.maintenant() - timedelta(days=base.peremption)).astimezone()
	try:
		with (
			psycopg.connect(host=str(base.socket), dbname=base.production) as connexion,
			connexion.transaction(),
		):
			bilan = purger(connexion, limite)
			annonce = (
				f"purge de la base {base.production}, au-delà de {base.peremption} jours"
				f" (avant le {limite:%d/%m/%Y %H:%M}) : {', '.join(bilan)} effacés"
			)
			connexion.execute("INSERT INTO log (niveau, nature, message) VALUES ('info', 'purge', %s)", (annonce,))
	except psycopg.OperationalError as erreur:
		journal.error(f"base de données injoignable ({base.production}) : {erreur} ; rien n'a été effacé")
		return CODE_ECHEC
	except psycopg.Error as erreur:
		journal.error(f"erreur de base de données : {erreur} ; rien n'a été effacé")
		return CODE_ECHEC
	journal.info(annonce)
	return 0


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, executer)
