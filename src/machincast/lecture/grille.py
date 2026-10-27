"""Grille des événements et choix de l'événement actif (https://github.com/dascritch/machincast/issues/12, spec § 4.1).

À tout instant, l'événement actif est celui de plus haute priorité (spécial > émission > fil musical) dont une
occurrence couvre l'instant, sauf si cette occurrence s'est terminée plus tôt (liste épuisée d'un événement sans
fin). À priorité égale, une occurrence sans fin, ou un fil musical permanent, laisse la place à toute occurrence qui
a commencé après elle, et reprend après (https://github.com/dascritch/machincast/issues/32) : un fil permanent sert
de fond. Sinon, deux événements de même priorité qui se chevauchent sont départagés par leur date de modification :
le dernier modifié en base l'emporte. L'interface refuse ces chevauchements à la saisie (chevauchement).

Dates d'un événement (spec § 3.1) : debut et fin sont ceux de sa première occurrence.

- Un fil musical sans debut ni fin est permanent.
- Sans jours de récurrence, l'événement a une seule occurrence, [debut, fin[, ou [debut, ∞[ sans fin.
- Avec des jours de récurrence, il revient chacun de ces jours à partir de sa première occurrence, à la même
  heure que debut, et dure jusqu'à l'heure de fin, autant de jours plus tard que la première occurrence : un
  événement peut passer minuit, et c'est le jour de son début qui compte.
- Sans fin, une occurrence couvre l'instant à partir de son début, jusqu'à ce que sa liste soit épuisée : le
  binaire la déclare alors terminée (Occurrence.cle).

Une session sautée (https://github.com/dascritch/machincast/issues/273), désignée par le jour où elle commence
(Evenement.sautees), n'existe pas pour la grille : elle ne joue pas, ne coupe rien, ne chevauche rien. Seul le
calendrier la montre (prevoir, Prevue.sautee).

Un événement de secours (https://github.com/dascritch/machincast/issues/16) n'est jamais actif par la grille :
sans date ni jour, sa liste ne joue qu'à la place d'un stream tombé (machincast.lecture.deroule).

Le poste travaille en heure locale, celle de Paris : la grille calcule en heure murale, sans fuseau à manier.
Au changement d'heure, un événement garde donc son heure (spec § 4.1 : aucune règle particulière).
"""

from collections.abc import Iterable, Set
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

import psycopg
from psycopg.rows import TupleRow


class Priorite(StrEnum):
	"""Valeurs du type priorite_evenement, de la plus basse à la plus haute."""

	SECOURS = "secours"
	"""Hors grille : remplace un stream tombé, jamais actif à une heure donnée."""
	FIL_MUSICAL = "fil_musical"
	EMISSION = "emission"
	SPECIAL = "special"


RANGS = {priorite: rang for rang, priorite in enumerate(Priorite)}

JAMAIS = datetime.min.replace(tzinfo=UTC)
"""Date de modification d'un événement qui n'en a pas."""
JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
"""Valeurs du type jour_semaine, dans l'ordre de datetime.weekday()."""


@dataclass(frozen=True)
class Evenement:
	id: int
	nom: str
	priorite: Priorite
	debut: datetime | None
	"""Début de la première occurrence ; None pour un fil musical permanent."""
	fin: datetime | None
	jours: frozenset[int]
	"""Jours de récurrence, 0 pour lundi ; vide si l'événement n'a qu'une occurrence."""
	modifie_le: datetime
	sautees: frozenset[date] = frozenset()
	"""Les jours où commencent ses sessions sautées (https://github.com/dascritch/machincast/issues/273)."""
	supprime_le: datetime | None = None
	"""Supprimé depuis l'interface (https://github.com/dascritch/machincast/issues/267) : il ne joue plus après ;
	seul le calendrier lit un événement supprimé, pour ses occurrences d'avant
	(https://github.com/dascritch/machincast/issues/269)."""


@dataclass(frozen=True)
class Occurrence:
	evenement: Evenement
	debut: datetime | None
	"""Début de l'occurrence, en heure murale du poste ; None pour un fil musical permanent."""
	fin: datetime | None
	"""None pour une occurrence sans fin, qui dure jusqu'à l'épuisement de sa liste."""
	commencee: datetime | None = field(default=None, compare=False)
	"""Pour une occurrence avancée (https://github.com/dascritch/machincast/issues/257) : l'heure murale où elle a
	commencé, avant son début prévu. Sa liste se compte depuis là. Elle ne change ni la clé, ni l'égalité."""

	@property
	def cle(self) -> tuple[int, datetime | None]:
		"""Identifie l'occurrence, pour la déclarer terminée plus tôt."""
		return self.evenement.id, self.debut


def heure_murale(moment: datetime) -> datetime:
	"""Heure du poste, sans fuseau : la machine travaille en heure locale, celle de Paris."""
	if moment.tzinfo is None:
		return moment
	return moment.astimezone().replace(tzinfo=None)


def _heure_murale_ou_rien(moment: datetime | None) -> datetime | None:
	if moment is None:
		return None
	return heure_murale(moment)


def _couvre(debut: datetime, fin: datetime | None, moment: datetime) -> bool:
	return (debut <= moment) and ((fin is None) or (moment < fin))


def occurrence(evenement: Evenement, instant: datetime) -> Occurrence | None:
	"""Occurrence de l'événement qui couvre l'instant, ou None. Ses dates sont en heure murale du poste."""
	if evenement.debut is None:
		return Occurrence(evenement, None, None)
	debut = heure_murale(evenement.debut)
	fin = _heure_murale_ou_rien(evenement.fin)
	moment = heure_murale(instant)
	if not evenement.jours:
		if (not _couvre(debut, fin, moment)) or (debut.date() in evenement.sautees):
			return None
		return Occurrence(evenement, debut, fin)

	premier_jour = debut.date()
	duree_en_jours: int | None = None
	if fin is not None:
		duree_en_jours = (fin.date() - premier_jour).days
	# Une occurrence avec fin a commencé au plus tôt autant de jours avant que dure la première ; une occurrence
	# sans fin, dans la semaine qui précède.
	recul = 7 if duree_en_jours is None else duree_en_jours
	for ecart in range(recul + 1):
		jour = moment.date() - timedelta(days=ecart)
		if (jour < premier_jour) or ((jour != premier_jour) and (jour.weekday() not in evenement.jours)):
			continue
		if jour in evenement.sautees:
			continue
		depart = datetime.combine(jour, debut.time())
		arrivee = None
		if (fin is not None) and (duree_en_jours is not None):
			arrivee = datetime.combine(jour + timedelta(days=duree_en_jours), fin.time())
		if _couvre(depart, arrivee, moment):
			return Occurrence(evenement, depart, arrivee)
	return None


def evenement_actif(
	evenements: Iterable[Evenement],
	instant: datetime,
	terminees: Set[tuple[int, datetime | None]] = frozenset(),
	avancee: Occurrence | None = None,
) -> Occurrence | None:
	"""Occurrence de l'événement actif à l'instant, ou None si aucun ne le couvre.

	terminees contient les clés (Occurrence.cle) des occurrences terminées plus tôt, liste épuisée. Une occurrence
	avancée (https://github.com/dascritch/machincast/issues/257), tant qu'elle n'est pas terminée, est active avant son
	début prévu, au-dessus de tout ; à son début, la grille la retrouve, avec la même clé.
	"""
	if (
		(avancee is not None)
		and (avancee.debut is not None)
		and (avancee.cle not in terminees)
		and (heure_murale(instant) < avancee.debut)
	):
		return avancee
	candidates = [
		o
		for e in evenements
		if (e.priorite is not Priorite.SECOURS)
		and ((o := occurrence(e, instant)) is not None)
		and (o.cle not in terminees)
	]
	return _gagnante(candidates)


def _cede(ouverte: Occurrence, autres: Iterable[Occurrence]) -> bool:
	"""Une occurrence sans fin, ou permanente, laisse la place à une occurrence qui a commencé après elle."""
	if ouverte.fin is not None:
		return False
	return any(
		(autre.debut is not None) and ((ouverte.debut is None) or (autre.debut > ouverte.debut)) for autre in autres
	)


def sessions(evenement: Evenement, de: date, a: date) -> list[tuple[datetime, datetime | None]]:
	"""Début et fin, en heure murale, des sessions d'un événement qui commencent du premier jour, inclus, au second,
	exclu, sautées comprises : celles que l'interface peut sauter ou rétablir
	(https://github.com/dascritch/machincast/issues/273)."""
	return _occurrences(evenement, de, a, avec_les_sautees=True)


def _occurrences(
	evenement: Evenement, de: date, a: date, avec_les_sautees: bool = False
) -> list[tuple[datetime, datetime | None]]:
	"""Début et fin, en heure murale, des occurrences qui commencent du premier jour, inclus, au second, exclu ; sans
	les sessions sautées, sauf demande. Rien pour un événement sans début."""
	if evenement.debut is None:
		return []
	debut = heure_murale(evenement.debut)
	fin = _heure_murale_ou_rien(evenement.fin)
	duree_en_jours: int | None = None
	if fin is not None:
		duree_en_jours = (fin.date() - debut.date()).days
	trouvees: list[tuple[datetime, datetime | None]] = []
	for ecart in range((a - de).days):
		jour = de + timedelta(days=ecart)
		if (jour < debut.date()) or ((jour != debut.date()) and (jour.weekday() not in evenement.jours)):
			continue
		if (jour in evenement.sautees) and (not avec_les_sautees):
			continue
		arrivee = None
		if (fin is not None) and (duree_en_jours is not None):
			arrivee = datetime.combine(jour + timedelta(days=duree_en_jours), fin.time())
		trouvees.append((datetime.combine(jour, debut.time()), arrivee))
	return trouvees


def _instant_commun(
	premiere: tuple[datetime, datetime | None], seconde: tuple[datetime, datetime | None]
) -> datetime | None:
	"""Le premier instant commun à deux occurrences ; une occurrence sans fin ne compte que par son début."""
	(debut, fin), (autre_debut, autre_fin) = premiere, seconde
	if (fin is None) and (autre_fin is None):
		if debut == autre_debut:
			return debut
		return None
	if fin is None:
		if _couvre(autre_debut, autre_fin, debut):
			return debut
		return None
	if autre_fin is None:
		if _couvre(debut, fin, autre_debut):
			return autre_debut
		return None
	if (debut < autre_fin) and (autre_debut < fin):
		return max(debut, autre_debut)
	return None


def _a_partir_de(
	occurrences: list[tuple[datetime, datetime | None]], depuis: datetime | None
) -> list[tuple[datetime, datetime | None]]:
	"""Les occurrences ramenées à ce qui en reste à partir de l'instant, en heure murale : une occurrence finie avant
	disparaît, une occurrence en cours commence à l'instant, une occurrence sans fin commencée avant disparaît."""
	if depuis is None:
		return occurrences
	restes: list[tuple[datetime, datetime | None]] = []
	for debut, fin in occurrences:
		if fin is None:
			if debut >= depuis:
				restes.append((max(debut, depuis), fin))
		elif fin > depuis:
			restes.append((max(debut, depuis), fin))
	return restes


def chevauchement(
	evenement: Evenement, autres: Iterable[Evenement], depuis: datetime | None = None
) -> tuple[Evenement, datetime] | None:
	"""Le premier événement de même priorité que l'événement chevauche, avec le premier instant commun, en heure
	murale ; None s'il n'en chevauche aucun (spec § 4.1, https://github.com/dascritch/machincast/issues/32).

	Un événement sans début ne chevauche rien : un fil musical permanent sert de fond, un événement de secours est
	hors grille. Une occurrence sans fin ne compte que par son début. Les occurrences se répètent chaque semaine : il
	suffit de les comparer de part et d'autre du début le plus tardif des deux, sur une semaine et leurs durées.

	Avec un instant, seul compte ce qui chevauche à partir de lui : la grille déjà diffusée ne bloque rien, un
	chevauchement en cours compte à partir de l'instant (https://github.com/dascritch/machincast/issues/271).
	"""
	murale = _heure_murale_ou_rien(depuis)
	trouves: list[tuple[datetime, int, Evenement]] = []
	if evenement.debut is None:
		return None
	for autre in autres:
		if (autre.priorite is not evenement.priorite) or (autre.debut is None):
			continue
		duree = _jours_couverts(evenement) + _jours_couverts(autre)
		pivot = max(heure_murale(evenement.debut), heure_murale(autre.debut), (murale) or (datetime.min)).date()
		de, a = pivot - timedelta(days=duree + 1), pivot + timedelta(days=duree + 8)
		communs = [
			instant
			for premiere in _a_partir_de(_occurrences(evenement, de, a), murale)
			for seconde in _a_partir_de(_occurrences(autre, de, a), murale)
			if (instant := _instant_commun(premiere, seconde)) is not None
		]
		if communs:
			trouves.append((min(communs), autre.id, autre))
	if not trouves:
		return None
	instant, _identifiant, autre = min(trouves, key=lambda trouve: (trouve[0], trouve[1]))
	return autre, instant


def _jours_couverts(evenement: Evenement) -> int:
	"""Jours que touche une occurrence, au-delà de celui de son début ; aucun pour une occurrence sans fin."""
	if (evenement.debut is None) or (evenement.fin is None):
		return 0
	return (heure_murale(evenement.fin).date() - heure_murale(evenement.debut).date()).days


def prochain_changement(evenements: Iterable[Evenement], instant: datetime) -> datetime | None:
	"""Prochain début ou fin d'une occurrence après l'instant, ou None : la grille ne change plus.

	Sert à la simulation (https://github.com/dascritch/machincast/issues/21), qui avance d'échéance en échéance.
	"""
	moment = heure_murale(instant)
	candidats: list[datetime] = []
	for evenement in evenements:
		if (evenement.priorite is Priorite.SECOURS) or (evenement.debut is None):
			continue
		debut = heure_murale(evenement.debut)
		fin = _heure_murale_ou_rien(evenement.fin)
		if not evenement.jours:
			if debut.date() not in evenement.sautees:
				candidats += [c for c in (debut, fin) if c is not None]
			continue
		duree_en_jours: int | None = None
		if fin is not None:
			duree_en_jours = (fin.date() - debut.date()).days
		# Les occurrences commencées dans la semaine passée peuvent encore finir ; celles de la semaine à venir,
		# commencer.
		for ecart in range(-8 - ((duree_en_jours) or (0)), 8):
			jour = moment.date() + timedelta(days=ecart)
			if (jour < debut.date()) or ((jour != debut.date()) and (jour.weekday() not in evenement.jours)):
				continue
			if jour in evenement.sautees:
				continue
			candidats.append(datetime.combine(jour, debut.time()))
			if (fin is not None) and (duree_en_jours is not None):
				candidats.append(datetime.combine(jour + timedelta(days=duree_en_jours), fin.time()))
	apres = [candidat for candidat in candidats if candidat > moment]
	if not apres:
		return None
	return min(apres).astimezone()


HORIZON_DE_L_EVENEMENT_SUIVANT = timedelta(days=7)
"""Jusqu'où chercher l'événement suivant (https://github.com/dascritch/machincast/issues/257)."""


def evenement_suivant(
	evenements: Iterable[Evenement],
	instant: datetime,
	terminees: Set[tuple[int, datetime | None]] = frozenset(),
	avancee: Occurrence | None = None,
	horizon: timedelta = HORIZON_DE_L_EVENEMENT_SUIVANT,
) -> Occurrence | None:
	"""La première occurrence qui commencera après l'instant et prendra l'antenne, jusqu'à l'horizon compris ; None
	sans elle (https://github.com/dascritch/machincast/issues/257). Un fil musical qui reprend, ou une occurrence
	commencée avant l'instant qui retrouve l'antenne, n'en est pas une : c'est ce que fait couper l'événement. Une
	occurrence avancée est l'occurrence en cours : le suivant est celui qui viendra après elle."""
	evenements = list(evenements)
	actuelle = evenement_actif(evenements, instant, terminees, avancee)
	# En heure murale : sept jours d'horloge, même au changement d'heure.
	depart = heure_murale(instant)
	limite = depart + horizon
	moment = prochain_changement(evenements, instant)
	while (moment is not None) and (heure_murale(moment) <= limite):
		actif = evenement_actif(evenements, moment, terminees, avancee)
		if (
			(actif is not None)
			and (actif.debut is not None)
			and (actif.debut > depart)
			and ((actuelle is None) or (actif.cle != actuelle.cle))
		):
			return actif
		moment = prochain_changement(evenements, moment)
	return None


@dataclass(frozen=True)
class Prevue:
	"""Une occurrence prévue, telle que la montre le calendrier (https://github.com/dascritch/machincast/issues/36)."""

	occurrence: Occurrence
	debut: datetime
	"""Début dessiné : celui de l'occurrence, ou celui de la période pour un fil musical permanent."""
	fin: datetime
	"""Fin dessinée : celle de l'occurrence ; pour une occurrence sans fin, le début suivant d'une priorité égale ou
	plus haute, au plus tard minuit ; pour un fil musical permanent, la fin de la période."""
	joue: tuple[tuple[datetime, datetime], ...]
	"""Les moments de la période où l'occurrence serait à l'antenne, dans l'ordre."""
	sautee: bool = False
	"""Une session sautée (https://github.com/dascritch/machincast/issues/273) : elle ne joue rien, ne cache rien."""


def prevoir(evenements: Iterable[Evenement], de: datetime, a: datetime) -> list[Prevue]:
	"""Les occurrences qui touchent la période [de, a[, en heure murale, et ce que chacune en joue.

	Ce qui joue suit evenement_actif, avec la fin dessinée d'une occurrence sans fin : la durée réelle de sa liste
	n'est connue qu'à la diffusion. Les événements de secours, hors grille, n'y sont pas. Un événement supprimé
	n'a que ses occurrences commencées avant sa suppression, arrêtées à elle
	(https://github.com/dascritch/machincast/issues/269). Une session sautée est montrée à part (Prevue.sautee) : elle
	ne joue rien, et ne compte ni pour ce qui joue, ni pour la fin dessinée d'une autre
	(https://github.com/dascritch/machincast/issues/273).
	"""
	de, a = heure_murale(de), heure_murale(a)
	grille = [evenement for evenement in evenements if evenement.priorite is not Priorite.SECOURS]
	occurrences: list[Occurrence] = []
	sautees: list[Occurrence] = []
	for evenement in grille:
		supprime = _heure_murale_ou_rien(evenement.supprime_le)
		if evenement.debut is None:
			if (supprime is None) or (supprime > de):
				occurrences.append(Occurrence(evenement, None, None))
			continue
		# Une occurrence commencée avant la période peut encore la toucher : autant de jours qu'elle en couvre.
		depuis = de.date() - timedelta(days=_jours_couverts(evenement) + 1)
		for debut, fin in _occurrences(evenement, depuis, a.date() + timedelta(days=1), avec_les_sautees=True):
			if (supprime is not None) and (debut >= supprime):
				continue
			if debut.date() in evenement.sautees:
				sautees.append(Occurrence(evenement, debut, fin))
			else:
				occurrences.append(Occurrence(evenement, debut, fin))
	fins = {o.cle: _fin_dessinee(o, occurrences, a) for o in occurrences}
	for o in occurrences:
		supprime = _heure_murale_ou_rien(o.evenement.supprime_le)
		if supprime is not None:
			fins[o.cle] = min(fins[o.cle], supprime)
	# Une occurrence hors de la période n'y couvre aucun moment : elle n'y joue pas, et n'y est pas dessinée.
	gardees = occurrences
	bornes = sorted(
		{de, a}
		| {o.debut for o in gardees if (o.debut is not None) and (de < o.debut < a)}
		| {fins[o.cle] for o in gardees if de < fins[o.cle] < a}
	)
	joue: dict[tuple[int, datetime | None], list[tuple[datetime, datetime]]] = {o.cle: [] for o in gardees}
	for depart, arrivee in zip(bornes, bornes[1:], strict=False):
		couvrantes = [o for o in gardees if ((o.debut is None) or (o.debut <= depart)) and (fins[o.cle] > depart)]
		gagnante = _gagnante(couvrantes)
		if gagnante is None:
			continue
		moments = joue[gagnante.cle]
		if (moments) and (moments[-1][1] == depart):
			moments[-1] = (moments[-1][0], arrivee)
			continue
		moments.append((depart, arrivee))
	prevues = [Prevue(o, (o.debut) or (de), fins[o.cle], tuple(joue[o.cle])) for o in gardees]
	prevues += [Prevue(o, (o.debut) or (de), _fin_dessinee(o, occurrences, a), (), sautee=True) for o in sautees]
	return sorted(prevues, key=lambda p: (p.debut, RANGS[p.occurrence.evenement.priorite], p.occurrence.evenement.id))


def _fin_dessinee(occurrence: Occurrence, toutes: list[Occurrence], a: datetime) -> datetime:
	if occurrence.debut is None:
		return a
	if occurrence.fin is not None:
		return occurrence.fin
	minuit = datetime.combine(occurrence.debut.date() + timedelta(days=1), datetime.min.time())
	rang = RANGS[occurrence.evenement.priorite]
	suivantes = [
		autre.debut
		for autre in toutes
		if (autre.debut is not None) and (autre.debut > occurrence.debut) and (RANGS[autre.evenement.priorite] >= rang)
	]
	return min([minuit, *suivantes])


def _gagnante(couvrantes: list[Occurrence]) -> Occurrence | None:
	"""Comme evenement_actif : la plus haute priorité, puis ce qui ne cède pas, puis la dernière modifiée."""
	if not couvrantes:
		return None
	rang = max(RANGS[o.evenement.priorite] for o in couvrantes)
	egales = [o for o in couvrantes if RANGS[o.evenement.priorite] == rang]
	gardees = [o for o in egales if not _cede(o, egales)]
	return max(gardees, key=lambda o: (o.evenement.modifie_le, o.evenement.id))


COLONNES = (
	"id, nom_interne, priorite::text, debut, fin, jours_recurrence::text[], modifie_le, supprime_le,"
	" ARRAY(SELECT s.jour FROM evenements_sauts s WHERE s.evenement_id = evenements.id)"
)


def lire_grille(connexion: psycopg.Connection[TupleRow], supprimes: bool = False) -> list[Evenement]:
	"""Événements de la grille, sans les événements de secours ; la connexion a endossé le rôle de la lecture
	(machincast.base.connecter). Un événement supprimé ne joue plus
	(https://github.com/dascritch/machincast/issues/267) : seul le calendrier les demande (supprimes), pour leurs
	occurrences d'avant leur suppression."""
	condition = "supprime_le IS NULL"
	if supprimes:
		condition = "TRUE"
	lignes = connexion.execute(
		f"SELECT {COLONNES} FROM evenements WHERE priorite <> 'secours' AND {condition} ORDER BY id"  # noqa: S608
	).fetchall()
	return _evenements(lignes)


def lire_evenement(connexion: psycopg.Connection[TupleRow], identifiant: int) -> Evenement | None:
	"""Un événement, quelle que soit sa priorité : par exemple l'événement de secours d'un stream."""
	lignes = connexion.execute(
		f"SELECT {COLONNES} FROM evenements WHERE id = %s",
		(identifiant,),
	).fetchall()
	return next(iter(_evenements(lignes)), None)


def _evenements(lignes: list[TupleRow]) -> list[Evenement]:
	return [
		Evenement(
			id=int(str(identifiant)),
			nom=str(nom),
			priorite=Priorite(str(priorite)),
			debut=debut if isinstance(debut, datetime) else None,
			fin=fin if isinstance(fin, datetime) else None,
			jours=frozenset(JOURS.index(str(jour)) for jour in (jours if isinstance(jours, list) else [])),
			modifie_le=modifie_le if isinstance(modifie_le, datetime) else JAMAIS,
			sautees=frozenset(
				jour for jour in (sautees if isinstance(sautees, list) else []) if isinstance(jour, date)
			),
			supprime_le=supprime_le if isinstance(supprime_le, datetime) else None,
		)
		for identifiant, nom, priorite, debut, fin, jours, modifie_le, supprime_le, sautees in lignes
	]
