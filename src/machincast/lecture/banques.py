"""Choix d'un sonore dans une banque (https://github.com/dascritch/machincast/issues/13, spec § 4.4 et § 4.5).

Le choix ne garde aucun état en mémoire : il se déduit de l'airplay, où chaque passage note la banque qui l'a
fourni. Un redémarrage du binaire, ou un sonore ajouté à une banque, ne perturbe donc rien.

- Séquentiel : le premier sonore jouable qui suit, dans l'ordre des positions, le dernier joué via cette banque ;
  après le dernier, la liste reprend au début. Sans passage via la banque, le premier sonore jouable.
- Aléatoire contrôlé : un sonore joué via cette banque n'est plus tiré tant que tous les sonores jouables de la
  banque ne l'ont pas été. Les cycles se lisent dans les passages via la banque, du plus ancien au plus récent :
  un cycle se clôt quand tous les sonores jouables y sont passés. Le dernier sonore joué n'ouvre jamais le cycle
  suivant (sauf s'il est seul) : pas deux fois de suite le même sonore.
- Chaque banque a son propre cycle : seuls comptent les passages fournis par elle, même pour un sonore présent
  dans plusieurs banques.
- Sonore jouable (§ 4.5) : à l'état actif, dans sa période de diffusion quand elle est renseignée (fin exclue),
  sous son maximum de lectures, compté sur tout l'airplay, quelle que soit la banque.
- Aucun sonore jouable : la banque ne fournit rien ; l'élément de l'événement est traité comme une banque vide.

Le tirage passe par un Hasard reçu en paramètre (machincast.hasard) : reproductible avec une graine.
"""

from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import TupleRow

from machincast.hasard import Hasard

ETAT_JOUABLE = "actif"


@dataclass(frozen=True)
class Candidat:
	"""Un sonore de la banque, dans l'ordre de sa position, avec ce qui décide s'il est jouable."""

	sonore: int
	etat: str
	debut_diffusion: datetime | None
	fin_diffusion: datetime | None
	max_lectures: int | None
	lectures: int
	"""Passages du sonore dans tout l'airplay, quelle que soit la banque."""


def jouable(candidat: Candidat, instant: datetime) -> bool:
	if candidat.etat != ETAT_JOUABLE:
		return False
	if candidat.debut_diffusion is not None and instant < candidat.debut_diffusion:
		return False
	if candidat.fin_diffusion is not None and instant >= candidat.fin_diffusion:
		return False
	return candidat.max_lectures is None or candidat.lectures < candidat.max_lectures


def suivant_sequentiel(ordre: list[int], jouables: set[int], dernier: int | None) -> int | None:
	"""Premier sonore jouable après le dernier joué, en reprenant au début ; None si aucun n'est jouable."""
	if not jouables:
		return None
	depart = ordre.index(dernier) + 1 if dernier in ordre else 0
	for decalage in range(len(ordre)):
		sonore = ordre[(depart + decalage) % len(ordre)]
		if sonore in jouables:
			return sonore
	return None


def reste_du_cycle(jouables: set[int], historique: list[int]) -> set[int]:
	"""Sonores jouables pas encore joués dans le cycle en cours.

	historique : sonores joués via la banque, du passage le plus récent au plus ancien. Les cycles se suivent
	depuis le premier passage : un cycle se clôt quand tous les sonores jouables y ont été joués. Au début d'un
	nouveau cycle, le dernier sonore joué est écarté, pour ne pas passer deux fois de suite.
	"""
	vus: set[int] = set()
	for sonore in reversed(historique):
		if sonore in jouables:
			vus.add(sonore)
			if vus == jouables:
				vus = set()
	reste = jouables - vus
	if reste == jouables and len(reste) > 1 and historique:
		reste.discard(historique[0])
	return reste


def _candidats(connexion: psycopg.Connection[TupleRow], banque: int) -> list[Candidat]:
	lignes = connexion.execute(
		"SELECT s.id, s.etat::text, s.debut_diffusion, s.fin_diffusion, s.max_lectures,"
		" (SELECT count(*) FROM airplay a WHERE a.sonore_id = s.id AND a.type_ligne = 'debut')"
		" FROM banques_sonores bs JOIN sonores s ON s.id = bs.sonore_id"
		" WHERE bs.banque_id = %s ORDER BY bs.position",
		(banque,),
	).fetchall()
	return [
		Candidat(
			sonore=int(str(sonore)),
			etat=str(etat),
			debut_diffusion=debut if isinstance(debut, datetime) else None,
			fin_diffusion=fin if isinstance(fin, datetime) else None,
			max_lectures=None if maximum is None else int(str(maximum)),
			lectures=int(str(lectures)),
		)
		for sonore, etat, debut, fin, maximum, lectures in lignes
	]


def _historique(connexion: psycopg.Connection[TupleRow], banque: int) -> list[int]:
	"""Sonores joués via la banque, du passage le plus récent au plus ancien."""
	lignes = connexion.execute(
		"SELECT sonore_id FROM airplay WHERE banque_id = %s AND type_ligne = 'debut' AND sonore_id IS NOT NULL"
		" ORDER BY horodatage DESC, id DESC",
		(banque,),
	).fetchall()
	return [int(str(ligne[0])) for ligne in lignes]


def _jouables(connexion: psycopg.Connection[TupleRow], banque: int, instant: datetime) -> tuple[list[int], set[int]]:
	candidats = _candidats(connexion, banque)
	return [c.sonore for c in candidats], {c.sonore for c in candidats if jouable(c, instant)}


def restants(connexion: psycopg.Connection[TupleRow], banque: int, instant: datetime) -> set[int]:
	"""Sonores jouables d'une banque aléatoire pas encore joués dans son cycle en cours."""
	_, jouables = _jouables(connexion, banque, instant)
	return reste_du_cycle(jouables, _historique(connexion, banque))


def choisir_sonore(
	connexion: psycopg.Connection[TupleRow], banque: int, instant: datetime, hasard: Hasard
) -> int | None:
	"""Sonore que la banque fournit à l'instant, selon son mode ; None si aucun n'est jouable (banque vide).

	La connexion a endossé le rôle de la lecture (machincast.base.connecter) : tout est lu, rien n'est écrit.
	"""
	ligne = connexion.execute("SELECT mode::text FROM banques WHERE id = %s", (banque,)).fetchone()
	if ligne is None:
		return None
	ordre, jouables = _jouables(connexion, banque, instant)
	historique = _historique(connexion, banque)
	if ligne[0] == "sequentiel":
		return suivant_sequentiel(ordre, jouables, historique[0] if historique else None)
	reste = reste_du_cycle(jouables, historique)
	return hasard.choice(sorted(reste)) if reste else None
