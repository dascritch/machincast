"""Étapes de l'indexation récursive des répertoires de banques (https://github.com/dascritch/machincast/issues/9)."""

import logging
import re
import shutil
import threading
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, connecter
from machincast.indexation.decodage import Verification, verifier_fichier
from machincast.indexation.indexeur import indexer as indexer_complet
from machincast.indexation.indexeur import indexer_un_sonore
from tests.base_test import parametres_base_test
from tests.etapes_indexation import Execution, inserer_sonore, nombre
from tests.sons import copie_de_test, corrompre

scenarios("repertoires.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
ELEMENT = re.compile(r"« ([^»]+) »")
# Extension du fichier demandé → fichier de test à copier (tests/fichiers-sonores).
FORMATS = {
	"mp3": "mp3",
	"m4a": "m4a",
	"aac": "aac",
	"ogg": "ogg",
	"flac": "flac",
	"wav": "wav",
}


@pytest.fixture
def racine(tmp_path: Path) -> Path:
	"""Répertoire temporaire où se trouvent les répertoires des banques du scénario."""
	chemin = tmp_path / "radio"
	chemin.mkdir()
	return chemin


def banque(base: Connexion, nom: str) -> int:
	ligne = base.execute("SELECT id FROM banques WHERE nom_interne = %s", (nom,)).fetchone()
	if ligne is None:
		ligne = base.execute(
			"INSERT INTO banques (nom_interne, mode) VALUES (%s, 'sequentiel') RETURNING id", (nom,)
		).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


@given(parsers.parse("une banque « {nom} » alimentée par le répertoire « {repertoire} »"))
def banque_alimentee(base_vide: Connexion, racine: Path, nom: str, repertoire: str) -> None:
	base_vide.execute(
		"INSERT INTO banques_repertoires (banque_id, repertoire) VALUES (%s, %s)",
		(banque(base_vide, nom), str(racine / repertoire)),
	)


@given(parsers.re(r"le fichier « (?P<relatif>[^»]+) », (?P<etat>sain|endommagé|quelconque)"))
def fichier(tmp_path: Path, racine: Path, relatif: str, etat: str) -> None:
	cible = racine / relatif
	cible.parent.mkdir(parents=True, exist_ok=True)
	if etat == "quelconque":
		cible.write_bytes(b"pas du son")
		return
	extension = cible.suffix.lstrip(".").lower()
	source = copie_de_test(FORMATS[extension] if etat == "sain" else "mp3", tmp_path)
	if etat == "endommagé":
		corrompre(source, 1000, 1 / 3)
	shutil.move(source, cible)


@given(parsers.parse("« {relatif} » a été retiré à la main de la banque « {nom} »"))
def retire(base_vide: Connexion, racine: Path, relatif: str, nom: str) -> None:
	base_vide.execute(
		"DELETE FROM banques_sonores WHERE banque_id = %s"
		" AND sonore_id = (SELECT id FROM sonores WHERE emplacement = %s)",
		(banque(base_vide, nom), str(racine / relatif)),
	)


@then(parsers.re(r"la banque « (?P<nom>[^»]+) » contient, dans l'ordre, (?P<liste>.+)"))
def contenu(base_vide: Connexion, racine: Path, nom: str, liste: str) -> None:
	lignes = base_vide.execute(
		"SELECT s.emplacement FROM banques_sonores bs JOIN sonores s ON s.id = bs.sonore_id"
		" WHERE bs.banque_id = %s ORDER BY bs.position",
		(banque(base_vide, nom),),
	).fetchall()
	assert [str(ligne[0]) for ligne in lignes] == [str(racine / relatif) for relatif in ELEMENT.findall(liste)]


@then(parsers.parse("le sonore de « {relatif} » est à l'état « {etat} »"))
def etat_du_sonore(base_vide: Connexion, racine: Path, relatif: str, etat: str) -> None:
	ligne = base_vide.execute(
		"SELECT etat::text FROM sonores WHERE emplacement = %s", (str(racine / relatif),)
	).fetchone()
	assert ligne is not None, f"aucun sonore pour {relatif}"
	assert ligne[0] == etat


@then(parsers.re(r"la base contient (?P<nombre>\d+) sonores?"))
def nombre_de_sonores(base_vide: Connexion, nombre: str) -> None:
	ligne = base_vide.execute("SELECT count(*) FROM sonores").fetchone()
	assert (ligne is not None) and (ligne[0] == int(nombre))


@then(
	parsers.parse(
		"la sortie d'erreur signale le répertoire « {repertoire} » comme introuvable, pour la banque « {nom} »"
	)
)
def repertoire_signale(execution: Execution, racine: Path, repertoire: str, nom: str) -> None:
	lignes = [ligne for ligne in execution.erreurs.splitlines() if str(racine / repertoire) in ligne]
	assert lignes, execution.erreurs
	assert ("introuvable" in lignes[0]) and (nom in lignes[0]), lignes[0]


@then("la sortie standard montre, ligne par ligne :")
def sortie_standard(execution: Execution, racine: Path, datatable: list[list[str]]) -> None:
	"""Un chemin qui commence par « …/ » est dans le répertoire du scénario."""
	_entete, *lignes = datatable
	assert execution.informations == [ligne.strip().replace("…/", f"{racine}/") for (ligne,) in lignes]


@then(parsers.parse("la sortie d'erreur signale « {chemin} », avec « {consequence} »"))
def erreur_signalee(execution: Execution, racine: Path, chemin: str, consequence: str) -> None:
	(ligne,) = execution.erreurs.splitlines()
	assert ligne.startswith(f"{chemin.replace('…/', f'{racine}/')} : "), ligne
	assert ligne.endswith(f" ; {consequence}"), ligne


@then("le verrou de l'indexation a été rendu dès la fin de l'indexation")
def verrou_rendu(execution: Execution) -> None:
	assert execution.verrou_rendu


@given(parsers.parse("« {relatif} » déplacé en « {destination} »"))
def deplacer(racine: Path, relatif: str, destination: str) -> None:
	"""Un déplacement hors de MachinCast, comme le ferait le navigateur de fichiers."""
	cible = racine / destination
	cible.parent.mkdir(parents=True, exist_ok=True)
	shutil.move(racine / relatif, cible)


# ─── Durées des sonores d'une banque (https://github.com/dascritch/machincast/issues/195) ───


@given(
	parsers.re(
		r"la banque « (?P<nom>[^»]+) » n'accepte que les sonores (?:d'au moins (?P<minimum>[\d,]+)"
		r"|d'au plus (?P<maximum>[\d,]+)|de (?P<de>[\d,]+) à (?P<a>[\d,]+)) secondes?"
	)
)
def durees_de_la_banque(
	base_vide: Connexion, nom: str, minimum: str | None, maximum: str | None, de: str | None, a: str | None
) -> None:
	bornes: list[timedelta | None] = []
	for valeur in ((minimum) or (de), (maximum) or (a)):
		borne = None
		if valeur is not None:
			borne = timedelta(seconds=nombre(valeur))
		bornes.append(borne)
	base_vide.execute(
		"UPDATE banques SET duree_min = %s, duree_max = %s WHERE id = %s", (*bornes, banque(base_vide, nom))
	)


def _ajouter(base: Connexion, nom: str, sonore: object) -> None:
	identifiant = banque(base, nom)
	base.execute(
		"INSERT INTO banques_sonores (banque_id, sonore_id, position)"
		" SELECT %s, %s, COALESCE(MAX(position), 0) + 1 FROM banques_sonores WHERE banque_id = %s",
		(identifiant, sonore, identifiant),
	)


def sonore_de(base: Connexion, racine: Path, relatif: str) -> int:
	ligne = base.execute("SELECT id FROM sonores WHERE emplacement = %s", (str(racine / relatif),)).fetchone()
	assert ligne is not None, f"aucun sonore pour {relatif}"
	return int(str(ligne[0]))


@given(parsers.parse("« {relatif} » est ajouté à la main à la banque « {nom} »"))
def ajoute_a_la_main(base_vide: Connexion, racine: Path, relatif: str, nom: str) -> None:
	_ajouter(base_vide, nom, sonore_de(base_vide, racine, relatif))


@given(parsers.parse("le stream « {titre} » est ajouté à la main à la banque « {nom} »"))
def stream_ajoute(base_vide: Connexion, titre: str, nom: str) -> None:
	ligne = base_vide.execute(
		"INSERT INTO sonores (type, url_stream, titre, etat) VALUES ('stream', 'https://flux.exemple', %s, 'actif')"
		" RETURNING id",
		(titre,),
	).fetchone()
	assert ligne is not None
	_ajouter(base_vide, nom, ligne[0])


@given(parsers.re(r"la durée en base du sonore de « (?P<relatif>[^»]+) » est de (?P<secondes>[\d,]+) secondes"))
def duree_en_base(base_vide: Connexion, racine: Path, relatif: str, secondes: str) -> None:
	base_vide.execute(
		"UPDATE sonores SET duree = %s WHERE id = %s",
		(timedelta(seconds=nombre(secondes)), sonore_de(base_vide, racine, relatif)),
	)


@given(parsers.parse("un sonore à l'état « {etat} », de durée inconnue, pour « {relatif} »"))
def sonore_sans_duree(base_vide: Connexion, racine: Path, etat: str, relatif: str) -> None:
	"""Comme un fichier enregistré par une indexation interrompue avant de le vérifier."""
	inserer_sonore(base_vide, str(racine / relatif), etat)


@when(
	"l'indexeur fait une indexation rapide, arrêtée pendant la vérification du premier sonore",
	target_fixture="execution",
)
def arretee_pendant_la_verification(base_vide: Connexion, caplog: pytest.LogCaptureFixture) -> Execution:
	"""L'arrêt est demandé pendant le décodage du premier sonore : la vérification s'arrête avant le suivant."""
	arret = threading.Event()

	def verifier(chemin: Path, *, seuil_silences: float | None = None) -> Verification:
		arret.set()
		return verifier_fichier(chemin, seuil_silences=seuil_silences)

	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"), connecter(*parametres_base_test(), Role.INDEXATION) as c:
		bilan = indexer_complet(c, verifier=verifier, arret=arret)
	anomalies = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
	informations = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
	return Execution(bilan, "\n".join(anomalies), informations)


@when(
	parsers.parse("l'indexeur vérifie seulement le sonore de « {relatif} », en audit complet"),
	target_fixture="execution",
)
def un_seul_sonore(base_vide: Connexion, racine: Path, caplog: pytest.LogCaptureFixture, relatif: str) -> Execution:
	"""Comme Machin_indexation --audit-complet --sonore N."""
	caplog.clear()
	sonore = sonore_de(base_vide, racine, relatif)
	with caplog.at_level(logging.INFO, logger="machincast"), connecter(*parametres_base_test(), Role.INDEXATION) as c:
		bilan = indexer_un_sonore(c, sonore, audit_complet=True)
	anomalies = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
	informations = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
	return Execution(bilan, "\n".join(anomalies), informations)


@then(parsers.parse("la banque « {nom} » ne contient aucun sonore"))
def banque_vide(base_vide: Connexion, nom: str) -> None:
	ligne = base_vide.execute(
		"SELECT count(*) FROM banques_sonores WHERE banque_id = %s", (banque(base_vide, nom),)
	).fetchone()
	assert ligne == (0,), ligne


@then(parsers.parse("la banque « {nom} » contient le stream « {titre} »"))
def contient_le_stream(base_vide: Connexion, nom: str, titre: str) -> None:
	ligne = base_vide.execute(
		"SELECT count(*) FROM banques_sonores bs JOIN sonores s ON s.id = bs.sonore_id"
		" WHERE bs.banque_id = %s AND s.titre = %s",
		(banque(base_vide, nom), titre),
	).fetchone()
	assert ligne == (1,), ligne
