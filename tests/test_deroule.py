"""Étapes du déroulé de la liste de lecture et des transitions (https://github.com/dascritch/machincast/issues/14).

La diffusion est simulée minute par minute : l'ordonnanceur décide ; la simulation tient le passage en cours et
note chaque passage dans l'airplay, avec sa banque, son événement et son élément, comme le fera le binaire.
"""

import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, connecter
from machincast.hasard import creer_hasard
from machincast.lecture.deroule import EnCours, Ordonnanceur, appels_ignores
from tests.base_test import parametres_base_test

scenarios("deroule.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
ELEMENT = re.compile(r"(sonore|banque|séquence) « ([^»]+) »")
COLONNES = {"sonore": "sonore_id", "banque": "banque_id", "séquence": "sequence_id"}
NOM = re.compile(r"« ([^»]+) »")
JOUR = date(2026, 10, 14)
MODES = {"séquentielle": "sequentiel", "aléatoire": "aleatoire"}


@dataclass
class Ligne:
	heure: str
	sonore: str
	evenement: str
	issue: str


@dataclass
class Contexte:
	duree: timedelta = timedelta(minutes=10)
	durees: dict[str, timedelta] = field(default_factory=dict)
	journal: list[Ligne] = field(default_factory=list)
	ordonnanceur: Ordonnanceur | None = None
	signalees: list[int] = field(default_factory=list)


@pytest.fixture
def contexte() -> Contexte:
	return Contexte()


@pytest.fixture
def lecture(base_vide: Connexion) -> Iterator[Connexion]:
	"""Connexion du binaire lecture, avec ses seuls droits."""
	with connecter(*parametres_base_test(), Role.LECTURE) as connexion:
		yield connexion


def a(heure: str, jour: date = JOUR) -> datetime:
	"""« 20:00 » le jour du scénario, en heure du poste, avec fuseau."""
	return datetime.combine(jour, time.fromisoformat(heure)).astimezone()


def sonore(base: Connexion, nom: str) -> int:
	emplacement = f"/sons/{nom}.flac"
	ligne = base.execute("SELECT id FROM sonores WHERE emplacement = %s", (emplacement,)).fetchone()
	if ligne is None:
		ligne = base.execute(
			"INSERT INTO sonores (type, emplacement, etat) VALUES ('fichier', %s, 'actif') RETURNING id", (emplacement,)
		).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


def nom_de(base: Connexion, table: str, colonne: str, identifiant: int) -> str:
	ligne = base.execute(f"SELECT {colonne} FROM {table} WHERE id = %s", (identifiant,)).fetchone()  # noqa: S608
	assert ligne is not None
	return str(ligne[0]).removeprefix("/sons/").removesuffix(".flac")


def banque(base: Connexion, nom: str) -> int:
	ligne = base.execute("SELECT id FROM banques WHERE nom_interne = %s", (nom,)).fetchone()
	assert ligne is not None, f"banque {nom} inconnue"
	return int(str(ligne[0]))


def sequence(base: Connexion, nom: str) -> int:
	ligne = base.execute("SELECT id FROM sequences WHERE nom_interne = %s", (nom,)).fetchone()
	assert ligne is not None, f"séquence {nom} inconnue"
	return int(str(ligne[0]))


def reference(base: Connexion, genre: str, nom: str) -> int:
	if genre == "sonore":
		return sonore(base, nom)
	return banque(base, nom) if genre == "banque" else sequence(base, nom)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("chaque sonore dure {minutes:d} minutes"))
def duree(contexte: Contexte, minutes: int) -> None:
	contexte.duree = timedelta(minutes=minutes)


@given(parsers.parse("le sonore « {nom} » dure {minutes:d} minutes"))
def duree_propre(contexte: Contexte, nom: str, minutes: int) -> None:
	contexte.durees[nom] = timedelta(minutes=minutes)


@given(parsers.re(r"une banque (?P<mode>séquentielle|aléatoire) « (?P<nom>[^»]+) » contenant (?P<liste>.+)"))
def banque_contenant(base_vide: Connexion, mode: str, nom: str, liste: str) -> None:
	base_vide.execute("INSERT INTO banques (nom_interne, mode) VALUES (%s, %s)", (nom, MODES[mode]))
	for position, nom_sonore in enumerate(NOM.findall(liste), start=1):
		base_vide.execute(
			"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, %s)",
			(banque(base_vide, nom), sonore(base_vide, nom_sonore), position),
		)


@given(parsers.re(r"une séquence « (?P<nom>[^»]+) » jouant (?P<liste>.+)"))
def sequence_jouant(base_vide: Connexion, nom: str, liste: str) -> None:
	creee = base_vide.execute("INSERT INTO sequences (nom_interne) VALUES (%s) RETURNING id", (nom,)).fetchone()
	assert creee is not None
	for position, (genre, nom_element) in enumerate(ELEMENT.findall(liste), start=1):
		base_vide.execute(
			f"INSERT INTO sequences_elements (sequence_id, position, {COLONNES[genre]})"  # noqa: S608
			" VALUES (%s, %s, %s)",
			(creee[0], position, reference(base_vide, genre, nom_element)),
		)


@given(parsers.parse("la banque « {nom} » est marquée « ne pas répéter »"))
def ne_pas_repeter(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("UPDATE banques SET ne_pas_repeter = true WHERE id = %s", (banque(base_vide, nom),))


@given(parsers.parse("le sonore « {nom} » est à l'état « {etat} »"))
def etat(base_vide: Connexion, nom: str, etat: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = %s WHERE id = %s", (etat, sonore(base_vide, nom)))


@given("les événements :")
def evenements(base_vide: Connexion, datatable: list[list[str]]) -> None:
	entetes, *lignes = datatable
	for valeurs in lignes:
		ligne = dict(zip(entetes, (v.strip() for v in valeurs), strict=True))
		jours = [j.strip() for j in ligne.get("jours", "").split(",") if j.strip()]
		cree = base_vide.execute(
			"INSERT INTO evenements (nom_interne, priorite, debut, fin, jours_recurrence)"
			" VALUES (%s, %s, %s, %s, %s::jour_semaine[]) RETURNING id",
			(
				ligne["nom"],
				ligne["priorité"],
				a(ligne["début"]) if ligne["début"] else None,
				a(ligne["fin"]) if ligne["fin"] else None,
				jours,
			),
		).fetchone()
		assert cree is not None
		for position, (genre, nom) in enumerate(ELEMENT.findall(ligne["liste"]), start=1):
			base_vide.execute(
				f"INSERT INTO evenements_elements (evenement_id, position, {COLONNES[genre]})"  # noqa: S608
				" VALUES (%s, %s, %s)",
				(cree[0], position, reference(base_vide, genre, nom)),
			)


# ─── Quand ─────────────────────────────────────────────────


def derouler(contexte: Contexte, base: Connexion, lecture: Connexion, debut: datetime, fin: datetime) -> None:
	if contexte.ordonnanceur is None:
		contexte.ordonnanceur = Ordonnanceur(lecture, creer_hasard(0))
	en_cours: EnCours | None = None
	en_silence = False
	instant = debut
	while instant < fin:
		if en_cours is not None and instant >= en_cours.fin_prevue:
			en_cours = None
		decision = contexte.ordonnanceur.decider(instant, en_cours)
		if decision.couper:
			contexte.journal[-1].issue = f"coupé à {instant:%H:%M}"
			en_cours = None
		if decision.jouer is not None:
			choix = decision.jouer
			base.execute(
				"INSERT INTO airplay (passage_id, type_ligne, horodatage, sonore_id, banque_id, evenement_id,"
				" element_id, sequence_id, sequence_element_id) VALUES (%s, 'debut', %s, %s, %s, %s, %s, %s, %s)",
				(
					uuid.uuid4(),
					instant,
					choix.sonore,
					choix.banque,
					choix.occurrence.evenement.id,
					choix.element.id,
					None if choix.ligne is None else choix.ligne.sequence,
					None if choix.ligne is None else choix.ligne.id,
				),
			)
			nom = nom_de(base, "sonores", "emplacement", choix.sonore)
			en_cours = EnCours(choix.occurrence, instant, instant + contexte.durees.get(nom, contexte.duree))
			issue = "entier" if en_cours.fin_prevue <= fin else "en cours"
			contexte.journal.append(Ligne(f"{instant:%H:%M}", nom, choix.occurrence.evenement.nom, issue))
			en_silence = False
		elif decision.silence and not en_silence:
			evenement = "" if decision.occurrence is None else decision.occurrence.evenement.nom
			contexte.journal.append(Ligne(f"{instant:%H:%M}", "silence", evenement, ""))
			en_silence = True
		instant += timedelta(minutes=1)


@when(parsers.re(r"la diffusion se déroule de (?P<debut>\d\d:\d\d) à (?P<fin>\d\d:\d\d)"))
def deroulement(contexte: Contexte, base_vide: Connexion, lecture: Connexion, debut: str, fin: str) -> None:
	derouler(contexte, base_vide, lecture, a(debut), a(fin))


@when(parsers.re(r"la diffusion se déroule le lendemain de (?P<debut>\d\d:\d\d) à (?P<fin>\d\d:\d\d)"))
def lendemain(contexte: Contexte, base_vide: Connexion, lecture: Connexion, debut: str, fin: str) -> None:
	jour = JOUR + timedelta(days=1)
	derouler(contexte, base_vide, lecture, a(debut, jour), a(fin, jour))


@when("le binaire redémarre")
def redemarrage(contexte: Contexte) -> None:
	"""Un nouvel ordonnanceur, sans rien en mémoire : tout se relit dans l'airplay."""
	contexte.ordonnanceur = None


@when(parsers.re(r"la liste « (?P<liste>[^»]+) » est vérifiée pour un événement qui (?P<boucle>boucle|ne boucle pas)"))
def verifier_la_liste(contexte: Contexte, base_vide: Connexion, liste: str, boucle: str) -> None:
	noms = [nom.strip() for nom in liste.split(",")]
	banques = [None if nom == "sonore" else banque(base_vide, nom) for nom in noms]
	marquees = {int(str(ligne[0])) for ligne in base_vide.execute("SELECT id FROM banques WHERE ne_pas_repeter")}
	contexte.signalees = appels_ignores(banques, marquees, boucle == "boucle")


# ─── Alors ─────────────────────────────────────────────────


@then("la diffusion a été :")
def diffusion(contexte: Contexte, datatable: list[list[str]]) -> None:
	_, *lignes = datatable
	attendu = [Ligne(*(v.strip() for v in valeurs)) for valeurs in lignes]
	assert contexte.journal == attendu, "\n".join(str(ligne) for ligne in contexte.journal)


@then(
	parsers.re(
		r"le log contient (?P<nombre>\d+) (?P<niveau>alerte|info) « (?P<nature>[^»]+) » pour l'événement"
		r" « (?P<evenement>[^»]+) »(?: et la banque « (?P<nom_banque>[^»]+) »)?$"
	)
)
def alertes(
	base_vide: Connexion, nombre: str, niveau: str, nature: str, evenement: str, nom_banque: str | None
) -> None:
	lignes = base_vide.execute(
		"SELECT l.niveau::text, e.nom_interne, b.nom_interne FROM log l"
		" LEFT JOIN evenements e ON e.id = l.evenement_id LEFT JOIN banques b ON b.id = l.banque_id"
		" WHERE l.nature = %s",
		(nature,),
	).fetchall()
	obtenues = [(n, e) + ((b,) if nom_banque else ()) for n, e, b in lignes]
	attendue = (niveau, evenement) + ((nom_banque,) if nom_banque else ())
	assert obtenues == [attendue] * int(nombre), lignes


@then(parsers.re(r"le log ne contient aucune (?P<niveau>alerte|info) « (?P<nature>[^»]+) »"))
def aucune_ligne(base_vide: Connexion, niveau: str, nature: str) -> None:
	lignes = base_vide.execute("SELECT message FROM log WHERE niveau = %s AND nature = %s", (niveau, nature)).fetchall()
	assert lignes == [], lignes


@then(parsers.re(r"les lignes signalées sont « (?P<lignes>[^»]*) »"))
def lignes_signalees(contexte: Contexte, lignes: str) -> None:
	assert contexte.signalees == [int(n) for n in lignes.split(",") if n.strip()]
