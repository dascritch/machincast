"""Parcours récursif des répertoires des banques (https://github.com/dascritch/machincast/issues/9, spec § 6.2).

Chaque fichier sonore trouvé dans l'un des répertoires d'une banque (table banques_repertoires) est enregistré
dans sonores s'il ne l'est pas encore, à l'état apercu et sans être décodé
(https://github.com/dascritch/machincast/issues/69), puis rattaché à la banque en fin de liste. La vérification
qui suit le décode dans le même passage.

- Formats de la spec : mp3, m4a et aac, ogg, flac, wav, aiff (et .aif), quelle que soit la casse de l'extension.
- Les fichiers et répertoires cachés (nom commençant par un point) sont ignorés : ce sont des fichiers de
  service, comme les « ._*.mp3 » qu'écrit macOS sur un disque partagé.
- Les sous-répertoires sont parcourus dans l'ordre de leur nom, sans suivre les liens symboliques vers d'autres
  répertoires, qui pourraient former une boucle ; un répertoire de banque qui est lui-même un lien est suivi.
- Un fichier déjà indexé n'est jamais dupliqué, même trouvé par plusieurs banques : l'emplacement est unique.
- Un sonore trouvé dans le répertoire d'une banque y est rattaché s'il n'y est pas, même retiré à la main.
- Un répertoire introuvable ou illisible est signalé en anomalie ; les autres banques sont indexées.

Chaque fichier est enregistré dans sa propre transaction, pour qu'une interruption garde le travail fait.
"""

import logging
import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.indexation.verification import Bilan, EtatSonore

journal = logging.getLogger(__name__)

EXTENSIONS = frozenset({".mp3", ".m4a", ".aac", ".ogg", ".flac", ".wav", ".aiff", ".aif"})
"""Extensions des formats de la spec § 6.2, en minuscules."""


def _cache(nom: str) -> bool:
	return nom.startswith(".")


def fichiers_sonores(repertoire: Path) -> Iterator[Path]:
	"""Fichiers sonores du répertoire et de ses sous-répertoires, dans l'ordre de leur chemin."""

	def signaler(erreur: OSError) -> None:
		journal.warning(f"{erreur.filename} : répertoire illisible ({erreur.strerror}) ; ignoré")

	for courant, sous_repertoires, fichiers in os.walk(repertoire, onerror=signaler):
		# Trié en place : os.walk descend ensuite dans cet ordre, et saute les répertoires cachés retirés.
		sous_repertoires[:] = sorted(nom for nom in sous_repertoires if not _cache(nom))
		for nom in sorted(fichiers):
			chemin = Path(courant) / nom
			if not _cache(nom) and chemin.suffix.lower() in EXTENSIONS and chemin.is_file():
				yield chemin


def _enregistrer(connexion: psycopg.Connection[TupleRow], banque: int, emplacement: str, bilan: Bilan) -> None:
	with connexion.transaction():
		ligne = connexion.execute("SELECT id FROM sonores WHERE emplacement = %s", (emplacement,)).fetchone()
		nouveau = ligne is None
		if ligne is None:
			ligne = connexion.execute(
				"INSERT INTO sonores (type, emplacement, etat, indexe_le)"
				" VALUES ('fichier', %s, %s, clock_timestamp()) RETURNING id",
				(emplacement, EtatSonore.APERCU.value),
			).fetchone()
			assert ligne is not None
		rattache = connexion.execute(
			"INSERT INTO banques_sonores (banque_id, sonore_id, position)"
			" SELECT %s, %s, COALESCE(MAX(position), 0) + 1 FROM banques_sonores WHERE banque_id = %s"
			" ON CONFLICT (banque_id, sonore_id) DO NOTHING",
			(banque, ligne[0], banque),
		).rowcount
	if nouveau:
		bilan.nouveaux += 1
	elif rattache:
		bilan.rattaches += 1


def indexer_repertoires(connexion: psycopg.Connection[TupleRow], bilan: Bilan) -> None:
	"""Enregistre et rattache à leurs banques les fichiers sonores de leurs répertoires ; complète le bilan.

	La connexion doit avoir endossé le rôle de l'indexation (machincast.base.connecter).
	"""
	with connexion.transaction():
		repertoires = connexion.execute(
			"SELECT b.id, b.nom_interne, r.repertoire FROM banques_repertoires r JOIN banques b ON b.id = r.banque_id"
			" ORDER BY b.id, r.repertoire"
		).fetchall()
	for banque, nom, repertoire in repertoires:
		chemin = Path(os.path.normpath(str(repertoire)))
		if not chemin.is_absolute():
			journal.warning(f"{repertoire} : répertoire relatif, ignoré pour la banque {nom}")
			continue
		if not chemin.is_dir():
			journal.warning(f"{chemin} : répertoire introuvable, ignoré pour la banque {nom}")
			continue
		for fichier in fichiers_sonores(chemin):
			_enregistrer(connexion, int(str(banque)), str(fichier), bilan)
