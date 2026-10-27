"""Étapes de la protection des fichiers sonores (https://github.com/dascritch/machincast/issues/96).

Les étapes de la diffusion viennent de tests/etapes_diffusion.py.
"""

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, connecter
from machincast.configuration import Metadonnees
from machincast.configuration import Sorties as CheminsDesSorties
from machincast.indexation.indexeur import indexer
from machincast.lecture.enregistrement import Passage
from machincast.lecture.etat import SocketEtat
from machincast.lecture.simulation import exporter, simuler
from machincast.lecture.sorties import Sorties
from machincast.protection import FichierSonoreProtege, injustifiees
from tests.base_test import parametres_base_test
from tests.etapes_diffusion import Connexion
from tests.sons import copie_de_test, corrompre

scenarios("protection.feature")

RACINE = Path(__file__).resolve().parents[1]
INSTANT = datetime.fromisoformat("2026-10-14 20:00:00").astimezone()

Releve = dict[Path, tuple[str, int, int]]


@dataclass
class Contexte:
	repertoire: Path | None = None
	banque: int | None = None
	releve: Releve = field(default_factory=dict)
	sorties: Sorties | None = None
	erreur: Exception | None = None
	code: str = ""


@pytest.fixture
def contexte() -> Contexte:
	return Contexte()


def repertoire(contexte: Contexte) -> Path:
	assert contexte.repertoire is not None
	return contexte.repertoire


def relever(dossier: Path) -> Releve:
	"""Octets, taille et date de modification de chaque fichier du répertoire."""
	return {
		chemin: (hashlib.sha256(chemin.read_bytes()).hexdigest(), chemin.stat().st_size, chemin.stat().st_mtime_ns)
		for chemin in sorted(dossier.rglob("*"))
		if chemin.is_file()
	}


def indexer_la_base(audit_complet: bool) -> None:
	with connecter(*parametres_base_test(), Role.INDEXATION) as connexion:
		indexer(connexion, audit_complet=audit_complet)


def sonore_de(base: Connexion, contexte: Contexte, nom: str) -> int:
	ligne = base.execute("SELECT id FROM sonores WHERE emplacement = %s", (str(repertoire(contexte) / nom),)).fetchone()
	assert ligne is not None, f"aucun sonore pour {nom}"
	return int(str(ligne[0]))


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("une banque « {nom} » dont le répertoire contient « {sain} », sain, et « {abime} », endommagé"))
def banque(contexte: Contexte, base_vide: Connexion, tmp_path: Path, nom: str, sain: str, abime: str) -> None:
	dossier = tmp_path / "musique"
	dossier.mkdir()
	copie_de_test("flac", dossier).rename(dossier / sain)
	endommage = copie_de_test("mp3", dossier)
	corrompre(endommage, 1000, 1 / 3)
	endommage.rename(dossier / abime)
	ligne = base_vide.execute(
		"INSERT INTO banques (nom_interne, mode) VALUES (%s, 'sequentiel') RETURNING id", (nom,)
	).fetchone()
	assert ligne is not None
	base_vide.execute("INSERT INTO banques_repertoires VALUES (%s, %s)", (ligne[0], str(dossier)))
	contexte.repertoire, contexte.banque = dossier, int(str(ligne[0]))


@given(parsers.parse("les fichiers de la banque « {nom} » relevés, puis la banque indexée"))
def indexee(contexte: Contexte, nom: str) -> None:
	contexte.releve = relever(repertoire(contexte))
	indexer_la_base(audit_complet=False)


@given(parsers.parse("le fil musical permanent « {nom} », avec la banque « {banque} »"))
def fil_de_la_banque(contexte: Contexte, base_vide: Connexion, nom: str, banque: str) -> None:
	ligne = base_vide.execute(
		"INSERT INTO evenements (nom_interne, priorite) VALUES (%s, 'fil_musical') RETURNING id", (nom,)
	).fetchone()
	assert ligne is not None
	base_vide.execute(
		"INSERT INTO evenements_elements (evenement_id, position, banque_id) VALUES (%s, 1, %s)",
		(ligne[0], contexte.banque),
	)


@given(parsers.parse("la sortie {sortie} placée sur le fichier sonore « {nom} »"))
def sortie_sur_un_sonore(contexte: Contexte, tmp_path: Path, sortie: str, nom: str) -> None:
	cible = repertoire(contexte) / nom
	chemins = {
		"csv": tmp_path / "sorties" / "airplay.csv",
		"pls": tmp_path / "sorties" / "playlist.pls",
		"html": tmp_path / "sorties" / "airplay.html",
	}
	# Le CSV du jour ajoute la date au nom : son modèle est placé à côté du fichier sonore, avec son extension.
	chemins[sortie] = cible
	contexte.sorties = Sorties(CheminsDesSorties(**chemins), Metadonnees(masquer=False, texte_public="Radio"))


@given(parsers.parse("le code « {code} »"))
def code(contexte: Contexte, code: str) -> None:
	contexte.code = code


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"l'entrée du sonore « (?P<nom>[^»]+) » (?P<changement>.+)"))
def changer_l_entree(contexte: Contexte, base_vide: Connexion, nom: str, changement: str) -> None:
	identifiant = sonore_de(base_vide, contexte, nom)
	etat = re.fullmatch(r"passe à l'état « (\w+) »", changement)
	if etat:
		base_vide.execute("UPDATE sonores SET etat = %s WHERE id = %s", (etat.group(1), identifiant))
	elif changement == "change d'emplacement":
		base_vide.execute(
			"UPDATE sonores SET emplacement = %s WHERE id = %s",
			(str(repertoire(contexte) / "ailleurs.flac"), identifiant),
		)
	elif changement == "change d'artiste et de titre":
		base_vide.execute("UPDATE sonores SET artiste = 'Autre', titre = 'Autre' WHERE id = %s", (identifiant,))
	elif changement == "est supprimée de la base":
		base_vide.execute("DELETE FROM sonores WHERE id = %s", (identifiant,))
	else:
		raise AssertionError(f"changement inconnu : {changement}")


@when("l'indexeur fait une indexation rapide, puis un audit complet")
def indexations() -> None:
	indexer_la_base(audit_complet=False)
	indexer_la_base(audit_complet=True)


@when(parsers.parse("une simulation de {minutes:d} minutes tourne"))
def simulation(tmp_path: Path, minutes: int) -> None:
	"""Quelques minutes suffisent : des centaines de passages de sonores d'une seconde
	(https://github.com/dascritch/machincast/issues/280)."""
	with connecter(*parametres_base_test(), Role.LECTURE) as connexion:
		simuler(connexion, tmp_path / "simulation", INSTANT, INSTANT + timedelta(minutes=minutes))


@when(parsers.parse("un passage de « {nom} » est publié sur les sorties"))
def publier(contexte: Contexte, base_vide: Connexion, nom: str) -> None:
	assert contexte.sorties is not None
	identifiant = sonore_de(base_vide, contexte, nom)
	passage = Passage(uuid.uuid4(), identifiant, None, None, None, INSTANT)
	base_vide.execute(
		"INSERT INTO airplay (passage_id, type_ligne, horodatage, sonore_id, emplacement, titre)"
		" VALUES (%s, 'debut', %s, %s, %s, %s)",
		(passage.id, INSTANT, identifiant, str(repertoire(contexte) / nom), nom),
	)
	base_vide.execute(
		"INSERT INTO airplay (passage_id, type_ligne, horodatage, sonore_id, emplacement, titre, duree_diffusee,"
		" sans_incident) VALUES (%s, 'fin', %s, %s, %s, %s, '1 s', true)",
		(passage.id, INSTANT, identifiant, str(repertoire(contexte) / nom), nom),
	)
	with connecter(*parametres_base_test(), Role.LECTURE) as connexion:
		contexte.sorties.passage_commence(connexion, passage)
		contexte.sorties.passage_termine(connexion, passage, INSTANT)


@when(parsers.parse("la socket d'état est ouverte sur le fichier sonore « {nom} »"))
def ouvrir_la_socket(contexte: Contexte, nom: str) -> None:
	try:
		SocketEtat(repertoire(contexte) / nom).ouvrir()
	except OSError as erreur:
		contexte.erreur = erreur


@when(parsers.parse("une simulation est exportée sous le nom « {nom} », dans le répertoire de la banque"))
def exporter_dans_la_banque(contexte: Contexte, nom: str) -> None:
	exporter([], [], repertoire(contexte), nom, INSTANT, INSTANT.replace(hour=21))


# ─── Alors ─────────────────────────────────────────────────


@then("les fichiers sonores de la banque sont intacts")
def intacts(contexte: Contexte) -> None:
	apres = relever(repertoire(contexte))
	for chemin, releve in contexte.releve.items():
		assert apres.get(chemin) == releve, f"{chemin} a changé ou disparu"


@then(parsers.parse("le fichier « {nom} » a de nouveau un sonore, à l'état « {etat} »"))
def reindexe(contexte: Contexte, base_vide: Connexion, nom: str, etat: str) -> None:
	ligne = base_vide.execute(
		"SELECT etat::text FROM sonores WHERE id = %s", (sonore_de(base_vide, contexte, nom),)
	).fetchone()
	assert ligne == (etat,)


@then(parsers.parse("le sonore de « {nom} » est à l'état « {etat} »"))
def etat_du_sonore(contexte: Contexte, base_vide: Connexion, nom: str, etat: str) -> None:
	ligne = base_vide.execute(
		"SELECT etat::text FROM sonores WHERE id = %s", (sonore_de(base_vide, contexte, nom),)
	).fetchone()
	assert ligne == (etat,)


@then(parsers.parse("l'airplay montre {nombre:d} passages"))
def nombre_de_passages(base_vide: Connexion, nombre: int) -> None:
	assert base_vide.execute("SELECT count(*) FROM airplay WHERE type_ligne = 'debut'").fetchone() == (nombre,)


@then(parsers.parse("le log contient 1 alerte « {nature} », qui mentionne « {mention} »"))
def alerte(base_vide: Connexion, nature: str, mention: str) -> None:
	lignes = base_vide.execute("SELECT niveau::text, message FROM log WHERE nature = %s", (nature,)).fetchall()
	assert (len(lignes) >= 1) and (all((n == "alerte") and (mention in str(m)) for n, m in lignes)), lignes


@then("l'ouverture est refusée, car c'est un fichier sonore protégé")
def socket_refusee(contexte: Contexte) -> None:
	assert isinstance(contexte.erreur, FichierSonoreProtege), repr(contexte.erreur)


@then(
	parsers.parse(
		"chaque suppression, renommage ou remplacement de fichier de src, bin et install.sh porte la justification"
		" « {marque} »"
	)
)
def code_justifie(marque: str) -> None:
	fichiers = [*sorted((RACINE / "src").rglob("*.py")), RACINE / "bin" / "Machin", RACINE / "install.sh"]
	fautes = [
		f"{chemin.relative_to(RACINE)}:{numero} : {ligne.strip()}"
		for chemin in fichiers
		for numero, ligne in injustifiees(chemin.read_text(encoding="utf-8"), chemin.suffix != ".py")
	]
	assert not fautes, "suppressions sans « " + marque + " » :\n" + "\n".join(fautes)


@then(parsers.re(r"le garde-fou (?P<verdict>refuse|accepte) ce code"))
def garde_fou(contexte: Contexte, verdict: str) -> None:
	bash = contexte.code.startswith(("rm ", "mv "))
	trouvees = injustifiees(contexte.code, bash)
	assert bool(trouvees) is (verdict == "refuse"), trouvees


@then(parsers.parse("le sonore de « {nom} » a un début et une fin détectés"))
def blancs_detectes(contexte: Contexte, base_vide: Connexion, nom: str) -> None:
	"""https://github.com/dascritch/machincast/issues/146"""
	ligne = base_vide.execute(
		"SELECT debut_detecte, fin_detectee FROM sonores WHERE id = %s", (sonore_de(base_vide, contexte, nom),)
	).fetchone()
	assert (ligne is not None) and (all(isinstance(valeur, timedelta) for valeur in ligne)), ligne
