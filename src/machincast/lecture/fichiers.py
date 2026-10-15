"""Vérification d'un fichier avant de le jouer (https://github.com/dascritch/machincast/issues/15, spec § 5.1).

Le binaire lecture compare la date de modification et la taille du fichier avec celles que l'indexeur a
enregistrées. Un écart est consigné dans le log, en alerte : le fichier est quand même joué, et c'est l'indexeur
qui mettra la base à jour. Un fichier introuvable n'est pas joué : incident dans le log.
"""

from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow


def _consigner(connexion: psycopg.Connection[TupleRow], niveau: str, nature: str, message: str, sonore: int) -> None:
	# Le rôle de la lecture ne lit pas le log : jamais de RETURNING ici.
	connexion.execute(
		"INSERT INTO log (niveau, nature, message, sonore_id) VALUES (%s, %s, %s, %s)",
		(niveau, nature, message, sonore),
	)


def verifier_avant_lecture(connexion: psycopg.Connection[TupleRow], sonore: int) -> Path | None:
	"""Chemin du fichier à jouer, ou None s'il est introuvable ; consigne tout écart dans le log.

	La connexion a endossé le rôle de la lecture (machincast.base.connecter).
	"""
	with connexion.transaction():
		ligne = connexion.execute(
			"SELECT emplacement, fichier_modifie_le, fichier_taille FROM sonores WHERE id = %s", (sonore,)
		).fetchone()
		if ligne is None or ligne[0] is None:
			return None
		chemin = Path(str(ligne[0]))
		modifie_le = ligne[1] if isinstance(ligne[1], datetime) else None
		taille = None if ligne[2] is None else int(str(ligne[2]))
		try:
			etat = chemin.stat()
		except OSError:
			_consigner(
				connexion, "incident", "fichier introuvable", f"{chemin} : aucun fichier à cet emplacement", sonore
			)
			return None
		ecarts = []
		sur_le_disque = datetime.fromtimestamp(etat.st_mtime, tz=UTC)
		if modifie_le is not None and sur_le_disque != modifie_le:
			ecarts.append(
				f"date de modification {modifie_le.astimezone():%Y-%m-%d %H:%M:%S} en base,"
				f" {sur_le_disque.astimezone():%Y-%m-%d %H:%M:%S} sur le disque"
			)
		if taille is not None and etat.st_size != taille:
			ecarts.append(f"taille {taille} octets en base, {etat.st_size} sur le disque")
		if ecarts:
			_consigner(
				connexion,
				"alerte",
				"fichier modifié",
				f"{chemin} : {' ; '.join(ecarts)} ; l'indexeur mettra la base à jour",
				sonore,
			)
		return chemin
