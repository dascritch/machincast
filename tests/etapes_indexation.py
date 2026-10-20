"""Étapes partagées des scénarios de l'indexeur : fichiers sonores, sonores en base, passage de l'indexeur.

Chargé comme greffon pytest par tests/conftest.py, pour servir à verification.feature
(https://github.com/dascritch/machincast/issues/7) comme à tags.feature (https://github.com/dascritch/machincast/issues/8).
"""

import argparse
import csv
import dataclasses
import logging
import os
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, then, when

from machincast.base import Role, connecter
from machincast.indexation.__main__ import executer
from machincast.indexation.decodage import DecodeurIndisponible, Verification, verifier_fichier
from machincast.indexation.indexeur import VERROU
from machincast.indexation.indexeur import indexer as indexer_complet
from machincast.indexation.verification import Bilan, texte_bilan
from tests.base_test import configuration_test, parametres_base_test
from tests.sons import copie_de_test, corrompre

Connexion = psycopg.Connection[tuple[object, ...]]
DECIMAL = r"\d+(?:,\d+)?"


def nombre(texte: str) -> float:
	"""« 12,5 » → 12.5 : les scénarios écrivent les nombres à la française."""
	return float(texte.replace(",", "."))


@dataclass
class Execution:
	bilan: Bilan
	erreurs: str
	informations: list[str] = field(default_factory=list)
	"""Ce qui va sur la sortie standard, ligne par ligne : niveau INFO."""
	verrou_rendu: bool = False
	"""Le verrou de l'indexation était libre dès la fin de l'indexation, sa connexion encore ouverte."""


def verrou_libre() -> bool:
	"""Une autre connexion peut-elle prendre le verrou de l'indexation ? Elle le rend aussitôt."""
	with connecter(*parametres_base_test(), Role.INDEXATION) as autre:
		pris = autre.execute("SELECT pg_try_advisory_lock(%s)", (VERROU,)).fetchone()
		assert pris is not None
		autre.execute("SELECT pg_advisory_unlock(%s)", (VERROU,))
		return bool(pris[0])


@dataclass
class AutreIndexation:
	"""Une autre connexion, qui tient le verrou de l'indexation jusqu'à sa fin."""

	connexion: psycopg.Connection[tuple[object, ...]] | None = None

	def terminer(self) -> None:
		if self.connexion is not None:
			self.connexion.close()
		self.connexion = None


@pytest.fixture
def autre_indexation() -> Iterator[AutreIndexation]:
	autre = AutreIndexation()
	yield autre
	autre.terminer()


@given("une autre indexation en cours sur la base")
def indexation_en_cours(base_vide: Connexion, autre_indexation: AutreIndexation) -> None:
	autre_indexation.connexion = connecter(*parametres_base_test(), Role.INDEXATION)
	autre_indexation.connexion.execute("SELECT pg_advisory_lock(%s)", (VERROU,))
	autre_indexation.connexion.commit()


@when("l'autre indexation se termine")
def fin_de_l_autre(autre_indexation: AutreIndexation) -> None:
	autre_indexation.terminer()


# ─── Fichiers ──────────────────────────────────────────────


@given(parsers.re(r"un fichier (?P<format_sonore>\w+) sain"), target_fixture="fichier")
def fichier_sain(tmp_path: Path, format_sonore: str) -> Path:
	return copie_de_test(format_sonore, tmp_path)


@given(parsers.re(r"un fichier (?P<format_sonore>\w+) tagué"), target_fixture="fichier")
def fichier_tague(tmp_path: Path, format_sonore: str) -> Path:
	return copie_de_test(format_sonore, tmp_path, "tags")


@when("je vérifie ce fichier", target_fixture="resultat")
def verifier(fichier: Path) -> Verification | DecodeurIndisponible:
	try:
		return verifier_fichier(fichier)
	except DecodeurIndisponible as erreur:
		return erreur


# ─── Sonores en base ───────────────────────────────────────


def inserer_sonore(
	base: Connexion, emplacement: str, etat: str, champs_edites: list[str] | None = None, duree: float | None = None
) -> int:
	en_base = None
	if duree is not None:
		en_base = timedelta(seconds=duree)
	ligne = base.execute(
		"INSERT INTO sonores (type, emplacement, etat, champs_edites, duree)"
		" VALUES ('fichier', %s, %s, %s, %s) RETURNING id",
		(emplacement, etat, (champs_edites) or ([]), en_base),
	).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


@given(parsers.parse("un fichier « {nom} » qui contient du texte"), target_fixture="fichier")
def fichier_de_texte(tmp_path: Path, nom: str) -> Path:
	fichier = tmp_path / nom
	fichier.write_text("Ceci n'est pas un son, malgré son extension.\n", encoding="utf-8")
	return fichier


@given(parsers.parse("un fichier « {nom} » vide"), target_fixture="fichier")
def fichier_vide_nomme(tmp_path: Path, nom: str) -> Path:
	fichier = tmp_path / nom
	fichier.write_bytes(b"")
	return fichier


@given(parsers.parse("une image « {nom} »"), target_fixture="fichier")
def image(tmp_path: Path, nom: str) -> Path:
	"""Le début d'une image PNG d'un pixel : sa signature et son en-tête suffisent à libmagic."""
	fichier = tmp_path / nom
	entete = b"\x00\x00\x00\x0dIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
	fichier.write_bytes(b"\x89PNG\r\n\x1a\n" + entete)
	return fichier


@given("un fichier mp3 endommagé", target_fixture="fichier")
def fichier_endommage(tmp_path: Path) -> Path:
	fichier = copie_de_test("mp3", tmp_path)
	corrompre(fichier, 1000, 1 / 3)
	return fichier


@given(parsers.parse("un sonore à l'état « {etat} » pour ce fichier"), target_fixture="sonore")
def sonore_dans_etat(base_vide: Connexion, fichier: Path, etat: str) -> int:
	return inserer_sonore(base_vide, str(fichier), etat)


@given(
	parsers.re(
		r"un sonore à l'état « actif » pour ce fichier, dont la durée a été saisie à la main"
		rf" à (?P<secondes>{DECIMAL}) secondes"
	),
	target_fixture="sonore",
)
def sonore_duree_editee(base_vide: Connexion, fichier: Path, secondes: str) -> int:
	return inserer_sonore(base_vide, str(fichier), "actif", ["duree"], nombre(secondes))


@given(
	parsers.re(
		r"un sonore à l'état « (?P<etat>[^»]+) » pour ce fichier,"
		r" dont le titre a été saisi à la main « (?P<titre>[^»]+) »"
	),
	target_fixture="sonore",
)
def sonore_titre_edite(base_vide: Connexion, fichier: Path, etat: str, titre: str) -> int:
	sonore = inserer_sonore(base_vide, str(fichier), etat, ["titre"])
	base_vide.execute("UPDATE sonores SET titre = %s WHERE id = %s", (titre, sonore))
	return sonore


@pytest.fixture
def indexations() -> list[tuple[datetime, datetime]]:
	"""Le début et la fin de chaque indexation du scénario, à l'heure de la base."""
	return []


@given("l'indexeur a fait une indexation rapide")
def indexation_prealable(
	base_vide: Connexion, caplog: pytest.LogCaptureFixture, indexations: list[tuple[datetime, datetime]]
) -> None:
	indexer(base_vide, caplog, audit_complet=False, indexations=indexations)


@given(
	parsers.re(
		r"ce fichier remplacé, sous le même nom, par un fichier (?P<format_sonore>\w+) (?P<etat>tagué|endommagé)"
	)
)
def fichier_remplace(fichier: Path, tmp_path: Path, format_sonore: str, etat: str) -> None:
	"""Comme une synchronisation depuis un autre poste : le contenu change, la date de modification aussi."""
	repertoire = tmp_path / "remplacement"
	repertoire.mkdir(exist_ok=True)
	source = copie_de_test(format_sonore, repertoire, "tags")
	if etat == "endommagé":
		source = copie_de_test(format_sonore, repertoire)
		corrompre(source, 1000, 1 / 3)
	fichier.write_bytes(source.read_bytes())
	plus_tard = fichier.stat().st_mtime + 60
	os.utime(fichier, (plus_tard, plus_tard))


@given(parsers.parse("le sonore est passé à l'état « {etat} »"))
def changer_etat(base_vide: Connexion, sonore: int, etat: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = %s WHERE id = %s", (etat, sonore))


@given("ce fichier remplacé, sous le même nom, par un fichier flac tagué, en gardant sa date de modification")
def fichier_remplace_meme_date(fichier: Path, tmp_path: Path) -> None:
	"""Comme une copie qui garde la date d'origine : seule la taille trahit le changement."""
	etat = fichier.stat()
	repertoire = tmp_path / "remplacement"
	repertoire.mkdir(exist_ok=True)
	fichier.write_bytes(copie_de_test("flac", repertoire, "tags").read_bytes())
	assert fichier.stat().st_size != etat.st_size
	os.utime(fichier, ns=(etat.st_atime_ns, etat.st_mtime_ns))


@given("ce fichier supprimé")
def fichier_supprime(fichier: Path) -> None:
	fichier.unlink()


@given("ce fichier touché, sans changer son contenu")
def fichier_touche(fichier: Path) -> None:
	plus_tard = fichier.stat().st_mtime + 60
	os.utime(fichier, (plus_tard, plus_tard))


@given(parsers.parse("un deuxième fichier {format_sonore} sain, dont le sonore est à l'état « {etat} »"))
def deuxieme_sonore(base_vide: Connexion, tmp_path: Path, format_sonore: str, etat: str) -> None:
	repertoire = tmp_path / "deuxieme"
	repertoire.mkdir()
	inserer_sonore(base_vide, str(copie_de_test(format_sonore, repertoire)), etat)


@given("un fichier introuvable", target_fixture="fichier")
def fichier_introuvable(tmp_path: Path) -> Path:
	return tmp_path / "disparu.flac"


@given("un stream enregistré", target_fixture="stream")
def stream(base_vide: Connexion) -> tuple[int, object]:
	ligne = base_vide.execute(
		"INSERT INTO sonores (type, url_stream) VALUES ('stream', 'https://flux.exemple/direct')"
		" RETURNING id, modifie_le"
	).fetchone()
	assert ligne is not None
	return int(str(ligne[0])), ligne[1]


def maintenant_en_base(base: Connexion) -> datetime:
	ligne = base.execute("SELECT clock_timestamp()").fetchone()
	assert (ligne is not None) and (isinstance(ligne[0], datetime))
	return ligne[0]


def indexer(
	base_vide: Connexion,
	caplog: pytest.LogCaptureFixture,
	audit_complet: bool,
	arret: threading.Event | None = None,
	indexations: list[tuple[datetime, datetime]] | None = None,
) -> Execution:
	# Le compte qui lance les tests endosse déjà le rôle de l'indexation (vérifié par base_vide).
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"), connecter(*parametres_base_test(), Role.INDEXATION) as c:
		debut = maintenant_en_base(base_vide)
		bilan = indexer_complet(c, audit_complet=audit_complet, arret=arret)
		if indexations is not None:
			indexations.append((debut, maintenant_en_base(base_vide)))
		verrou_rendu = verrou_libre()
	# Les anomalies et les erreurs vont sur la sortie d'erreur : niveau WARNING et au-delà.
	anomalies = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
	informations = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
	return Execution(bilan, "\n".join(anomalies), informations, verrou_rendu)


@when("l'indexeur fait un audit complet", target_fixture="execution")
def audit_complet(
	base_vide: Connexion, caplog: pytest.LogCaptureFixture, indexations: list[tuple[datetime, datetime]]
) -> Execution:
	return indexer(base_vide, caplog, audit_complet=True, indexations=indexations)


@when("l'indexeur fait une indexation rapide, dont l'arrêt est déjà demandé", target_fixture="execution")
def indexation_arretee(base_vide: Connexion, caplog: pytest.LogCaptureFixture) -> Execution:
	arret = threading.Event()
	arret.set()
	return indexer(base_vide, caplog, audit_complet=False, arret=arret)


@when("l'indexeur fait une indexation rapide", target_fixture="execution")
def indexation_rapide(
	base_vide: Connexion, caplog: pytest.LogCaptureFixture, indexations: list[tuple[datetime, datetime]]
) -> Execution:
	return indexer(base_vide, caplog, audit_complet=False, indexations=indexations)


def lire_sonore(base: Connexion, sonore: int) -> tuple[object, ...]:
	ligne = base.execute(
		"SELECT etat::text, duree, fichier_modifie_le, fichier_taille, modifie_le FROM sonores WHERE id = %s",
		(sonore,),
	).fetchone()
	assert ligne is not None
	return ligne


@then(parsers.parse("le sonore est à l'état « {etat} »"))
def sonore_etat(base_vide: Connexion, sonore: int, etat: str) -> None:
	assert lire_sonore(base_vide, sonore)[0] == etat


@then(parsers.re(rf"sa durée en base est de (?P<attendue>{DECIMAL}) secondes? à (?P<marge>{DECIMAL}) seconde près"))
def duree_en_base(base_vide: Connexion, sonore: int, attendue: str, marge: str) -> None:
	duree = lire_sonore(base_vide, sonore)[1]
	assert isinstance(duree, timedelta), duree
	assert abs(duree.total_seconds() - nombre(attendue)) <= nombre(marge), duree


@then("la date de modification et la taille du fichier sont enregistrées")
def date_et_taille(base_vide: Connexion, sonore: int, fichier: Path) -> None:
	_, _, modifie_le, taille, _ = lire_sonore(base_vide, sonore)
	etat = fichier.stat()
	assert taille == etat.st_size
	assert modifie_le == datetime.fromtimestamp(etat.st_mtime, tz=UTC)


@then("rien n'est signalé sur la sortie d'erreur")
def rien_signale(execution: Execution) -> None:
	assert execution.erreurs == ""


@then(parsers.parse("la sortie d'erreur signale ce fichier comme « {verdict} », avec « {consequence} »"))
def erreur_signalee(execution: Execution, fichier: Path, verdict: str, consequence: str) -> None:
	lignes = [ligne for ligne in execution.erreurs.splitlines() if ligne.startswith(f"{fichier} : ")]
	assert len(lignes) == 1, execution.erreurs
	assert (f" : {verdict} : " in lignes[0]) and (lignes[0].endswith(f" ; {consequence}")), lignes[0]


@then(parsers.parse("le bilan indique « {texte} »"))
def bilan_indique(execution: Execution, texte: str) -> None:
	assert texte_bilan(execution.bilan) == texte


@then("le stream n'a pas été modifié")
def stream_intact(base_vide: Connexion, stream: tuple[int, object]) -> None:
	etat, duree, modifie_le_fichier, taille, modifie_le = lire_sonore(base_vide, stream[0])
	assert (etat, duree, modifie_le_fichier, taille) == ("actif", None, None, None)
	assert modifie_le == stream[1]


def lire_tags_en_base(base: Connexion, sonore: int) -> tuple[object, object, object]:
	ligne = base.execute(
		"SELECT artiste, titre, metadonnees_musicales FROM sonores WHERE id = %s", (sonore,)
	).fetchone()
	assert ligne is not None
	return ligne[0], ligne[1], ligne[2]


@then(parsers.parse("en base, l'artiste est « {artiste} » et le titre « {titre} »"))
def artiste_et_titre_en_base(base_vide: Connexion, sonore: int, artiste: str, titre: str) -> None:
	assert lire_tags_en_base(base_vide, sonore)[:2] == (artiste, titre)


# ─── Machin indexation ─────────────────────────────────────


@when(
	parsers.re(r"Machin indexation est lancé sur la base de test(?P<audit>, en audit complet)?"),
	target_fixture="lancement",
)
def lancer_sur_la_base_de_test(
	base_vide: Connexion, caplog: pytest.LogCaptureFixture, audit: str | None
) -> tuple[int, list[str]]:
	"""Son action, avec une configuration dont la base de production est la base de test."""
	configuration = configuration_test()
	sur_la_base_de_test = dataclasses.replace(
		configuration, base=dataclasses.replace(configuration.base, production=configuration.base.test)
	)
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"):
		code = executer(sur_la_base_de_test, argparse.Namespace(audit_complet=audit is not None, fenetre=False))
	return code, [enregistrement.getMessage() for enregistrement in caplog.records]


@then(parsers.parse("Machin indexation se termine avec le code {code:d}, en signalant « {texte} »"))
def lancement_termine(lancement: tuple[int, list[str]], tmp_path: Path, code: int, texte: str) -> None:
	"""Un « …/ » désigne le répertoire du scénario."""
	obtenu, messages = lancement
	texte = texte.replace("…/", f"{tmp_path}/")
	assert (obtenu, texte in messages) == (code, True), messages


@then(parsers.parse("le type du fichier en base est « {type_mime} »"))
def type_en_base(base_vide: Connexion, sonore: int, type_mime: str) -> None:
	assert base_vide.execute("SELECT type_mime FROM sonores WHERE id = %s", (sonore,)).fetchone() == (type_mime,)


@then(parsers.parse("la sortie d'erreur mentionne « {texte} »"))
def erreur_mentionne(execution: Execution, texte: str) -> None:
	assert texte in execution.erreurs, execution.erreurs


def lire_csv(repertoire: Path, nom: str) -> list[list[str]]:
	with (repertoire / nom).open(encoding="utf-8-sig", newline="") as fichier:
		return list(csv.reader(fichier, delimiter=";"))


@then(parsers.parse("le document d'audit « {nom} » signale ce fichier, « {verdict} », avec « {consequence} »"))
def anomalie_csv(repertoire_d_audit: Path, fichier: Path, nom: str, verdict: str, consequence: str) -> None:
	_entete, anomalie, _bilan = lire_csv(repertoire_d_audit, nom)
	_date, chemin, lu, probleme, suite = anomalie
	assert (chemin, lu, suite) == (str(fichier), verdict, consequence)
	assert (probleme != "") and (not probleme.startswith(verdict)), probleme


def verifie_le(base: Connexion, sonore: int) -> object:
	ligne = base.execute("SELECT verifie_le FROM sonores WHERE id = %s", (sonore,)).fetchone()
	assert ligne is not None
	return ligne[0]


@then(parsers.re(r"la date de vérification complète du sonore est celle de l'indexation(?P<precedente> précédente)?"))
def date_de_verification(
	base_vide: Connexion, sonore: int, indexations: list[tuple[datetime, datetime]], precedente: str | None
) -> None:
	debut, fin = indexations[-2 if precedente is not None else -1]
	date = verifie_le(base_vide, sonore)
	assert isinstance(date, datetime)
	assert debut <= date <= fin, (debut, date, fin)


@then("le sonore n'a pas de date de vérification complète")
def sans_date_de_verification(base_vide: Connexion, sonore: int) -> None:
	assert verifie_le(base_vide, sonore) is None
