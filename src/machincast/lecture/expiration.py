"""Expiration automatique des sonores (https://github.com/dascritch/machincast/issues/18, spec § 4.5).

Le binaire lecture passe un sonore de l'état actif à l'état expire :

- quand il atteint son maximum de lectures, compté sur tout l'airplay (lignes de début), quels que soient
  l'événement et la banque ;
- quand sa période de diffusion est terminée : fin_diffusion atteinte, fin comprise (la période s'entend fin exclue).

Seule la colonne etat change, et seulement d'actif à expire : les droits PostgreSQL du binaire lecture ne lui
permettent pas d'en modifier d'autres. Chaque expiration est consignée dans le log (info, « sonore expiré »), avec
sa cause. Le sonore ne revient à l'état actif que par l'interface.
"""

from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import entier_ou_rien
from machincast.lecture.enregistrement import consigner

NATURE = "sonore expiré"


@dataclass(frozen=True)
class Expiration:
	sonore: int
	cause: str


def _cause(maximum: int | None, lectures: int, fin: datetime | None, instant: datetime) -> str:
	causes = []
	if (maximum is not None) and (lectures >= maximum):
		causes.append(f"maximum de {maximum} lecture{'s' if maximum > 1 else ''} atteint")
	if (fin is not None) and (fin <= instant):
		causes.append(f"période de diffusion terminée le {fin.astimezone():%Y-%m-%d %H:%M:%S}")
	return " ; ".join(causes)


def expirer(connexion: psycopg.Connection[TupleRow], instant: datetime, sonore: int | None = None) -> list[Expiration]:
	"""Passe à l'état expire les sonores actifs arrivés au bout, et le consigne ; sonore limite la vérification à un
	seul sonore, par exemple celui dont un passage vient de commencer.

	La connexion a endossé le rôle de la lecture (machincast.base.connecter).
	"""
	with connexion.transaction():
		lignes = connexion.execute(
			"WITH candidats AS ("
			" SELECT s.id, s.max_lectures, s.fin_diffusion,"
			" (SELECT count(*) FROM airplay a WHERE a.sonore_id = s.id AND a.type_ligne = 'debut') AS lectures"
			" FROM sonores s WHERE s.etat = 'actif' AND (%s::bigint IS NULL OR s.id = %s::bigint)"
			" AND (s.fin_diffusion <= %s OR s.max_lectures IS NOT NULL))"
			" UPDATE sonores s SET etat = 'expire' FROM candidats c"
			" WHERE s.id = c.id AND (c.fin_diffusion <= %s OR c.lectures >= c.max_lectures)"
			" RETURNING s.id, COALESCE(s.titre, s.emplacement, s.url_stream), c.max_lectures, c.lectures,"
			" c.fin_diffusion",
			(sonore, sonore, instant, instant),
		).fetchall()
		expirations = []
		for identifiant, nom, maximum, lectures, fin in lignes:
			expiration = Expiration(
				int(str(identifiant)),
				_cause(
					entier_ou_rien(maximum),
					int(str(lectures)),
					fin if isinstance(fin, datetime) else None,
					instant,
				),
			)
			consigner(
				connexion,
				"info",
				NATURE,
				f"{(nom) or (f'sonore {expiration.sonore}')} : {expiration.cause}",
				instant,
				sonore=expiration.sonore,
			)
			expirations.append(expiration)
	return expirations
