"""Étapes du masquage des métadonnées et des modules de sortie (https://github.com/dascritch/machincast/issues/19).

Les étapes de la diffusion viennent de tests/etapes_diffusion.py. Les sorties sont écrites dans le répertoire
temporaire du scénario, jamais aux chemins de la configuration de test.
"""

import csv
import logging
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, connecter
from machincast.configuration import Metadonnees
from machincast.configuration import Sorties as CheminsDesSorties
from machincast.lecture.sorties import Sorties
from tests.base_test import configuration_test, parametres_base_test
from tests.etapes_diffusion import Banc, Connexion

scenarios("sorties.feature")

DEBUT = datetime.fromisoformat("2026-10-14 20:00:00").astimezone()
VALEURS = {"vide": None, "oui": True, "non": False}


def sorties_du_banc(banc: Banc) -> Sorties:
	assert banc.sorties is not None
	return banc.sorties


def preparer_sorties(banc: Banc, repertoire: Path, masquer: bool, texte_public: str) -> None:
	chemins = CheminsDesSorties(
		csv=repertoire / "sorties" / "airplay.csv",
		pls=repertoire / "sorties" / "playlist.pls",
		html=repertoire / "sorties" / "airplay.html",
	)
	banc.sorties = Sorties(chemins, Metadonnees(masquer=masquer, texte_public=texte_public))


def inserer(base: Connexion, requete: str, valeurs: tuple[object, ...]) -> int:
	ligne = base.execute(requete, valeurs).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


def passage(
	base: Connexion,
	numero: int,
	artiste: str,
	titre: str,
	*,
	termine: bool = True,
	sonore_masque: bool | None = None,
	banque: int | None = None,
	evenement: int | None = None,
	sequence: int | None = None,
) -> None:
	"""Un passage dans l'airplay, numero minutes après DEBUT, d'une minute s'il est terminé."""
	emplacement = f"/musique/{numero}.flac"
	sonore = inserer(
		base,
		"INSERT INTO sonores (type, emplacement, artiste, titre, masquer_metadonnees)"
		" VALUES ('fichier', %s, %s, %s, %s) RETURNING id",
		(emplacement, artiste, titre, sonore_masque),
	)
	identifiant = uuid.uuid4()
	debut = DEBUT + timedelta(minutes=numero)
	colonnes = (
		"passage_id, type_ligne, horodatage, sonore_id, banque_id, evenement_id, sequence_id, emplacement, artiste,"
		" titre"
	)
	base.execute(
		f"INSERT INTO airplay ({colonnes}) VALUES (%s, 'debut', %s, %s, %s, %s, %s, %s, %s, %s)",
		(identifiant, debut, sonore, banque, evenement, sequence, emplacement, artiste, titre),
	)
	if termine:
		base.execute(
			f"INSERT INTO airplay ({colonnes}, duree_diffusee, sans_incident)"
			" VALUES (%s, 'fin', %s, %s, %s, %s, %s, %s, %s, %s, '1 min', true)",
			(identifiant, debut + timedelta(minutes=1), sonore, banque, evenement, sequence)
			+ (emplacement, artiste, titre),
		)


def emission(base: Connexion, nom: str, nom_public: str | None, masquer: bool | None) -> int:
	return inserer(
		base,
		"INSERT INTO evenements (nom_interne, nom_public, priorite, debut, masquer_metadonnees)"
		" VALUES (%s, %s, 'emission', '2026-10-14 19:00', %s) RETURNING id",
		(nom, nom_public, masquer),
	)


def page(banc: Banc) -> str:
	return sorties_du_banc(banc).chemins.html.read_text(encoding="utf-8")


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("des sorties dans un répertoire temporaire, avec le texte public « {texte} »"))
def sorties_temporaires(banc: Banc, tmp_path: Path, caplog: pytest.LogCaptureFixture, texte: str) -> None:
	caplog.set_level(logging.INFO, logger="machincast")
	preparer_sorties(banc, tmp_path, False, texte)


@given(
	parsers.parse(
		"le masquage {evenement} pour l'événement, {sequence} pour la séquence, {banque} pour la banque,"
		" {sonore} pour le sonore et {configuration} dans la configuration"
	)
)
def masquages(
	banc: Banc,
	base_vide: Connexion,
	tmp_path: Path,
	evenement: str,
	sequence: str,
	banque: str,
	sonore: str,
	configuration: str,
) -> None:
	preparer_sorties(banc, tmp_path, configuration == "oui", "Radio Exemple")
	identifiant_sequence = inserer(
		base_vide,
		"INSERT INTO sequences (nom_interne, masquer_metadonnees) VALUES ('Séquence', %s) RETURNING id",
		(VALEURS[sequence],),
	)
	identifiant_banque = inserer(
		base_vide,
		"INSERT INTO banques (nom_interne, mode, masquer_metadonnees) VALUES ('Banque', 'sequentiel', %s) RETURNING id",
		(VALEURS[banque],),
	)
	identifiant_evenement = emission(base_vide, "Émission", None, VALEURS[evenement])
	passage(
		base_vide,
		0,
		"Artiste secret",
		"Titre secret",
		termine=False,
		sonore_masque=VALEURS[sonore],
		banque=identifiant_banque,
		evenement=identifiant_evenement,
		sequence=identifiant_sequence,
	)


def nom_public(texte: str) -> str | None:
	if texte == "vide":
		return None
	return texte.strip(" «»")


@given(
	parsers.parse(
		"un passage masqué, de nom public {evenement} pour l'événement, {sequence} pour la séquence et {banque}"
		" pour la banque"
	)
)
def passage_masque_noms_publics(base_vide: Connexion, evenement: str, sequence: str, banque: str) -> None:
	identifiant_banque = inserer(
		base_vide,
		"INSERT INTO banques (nom_interne, nom_public, mode) VALUES ('Banque', %s, 'sequentiel') RETURNING id",
		(nom_public(banque),),
	)
	identifiant_sequence = inserer(
		base_vide,
		"INSERT INTO sequences (nom_interne, nom_public, masquer_metadonnees) VALUES ('Séquence', %s, true)"
		" RETURNING id",
		(nom_public(sequence),),
	)
	passage(
		base_vide,
		0,
		"Artiste secret",
		"Titre secret",
		termine=False,
		banque=identifiant_banque,
		evenement=emission(base_vide, "Émission", nom_public(evenement), None),
		sequence=identifiant_sequence,
	)


@given(
	parsers.re(
		r"le passage de « (?P<artiste>[^»]+) » – « (?P<titre>[^»]+) » dans l'émission « (?P<nom>[^»]+) »,"
		r" (?:de nom public « (?P<nom_public>[^»]+) »|sans nom public), (?P<masquage>masquée|affichée)"
	)
)
def passage_dans_une_emission(
	base_vide: Connexion, artiste: str, titre: str, nom: str, nom_public: str | None, masquage: str
) -> None:
	evenement = emission(base_vide, nom, nom_public, masquage == "masquée")
	passage(base_vide, 0, artiste, titre, termine=False, evenement=evenement)


@given(parsers.parse("{nombre:d} passages terminés, puis un passage en cours de « {artiste} » – « {titre} »"))
def passages_puis_en_cours(base_vide: Connexion, nombre: int, artiste: str, titre: str) -> None:
	for numero in range(1, nombre + 1):
		passage(base_vide, numero, f"Artiste {numero}", f"Titre {numero}")
	passage(base_vide, nombre + 1, artiste, titre, termine=False)


@given(parsers.parse("{nombre:d} passages terminés, sans passage en cours"))
def passages_termines(base_vide: Connexion, nombre: int) -> None:
	for numero in range(1, nombre + 1):
		passage(base_vide, numero, f"Artiste {numero}", f"Titre {numero}")


@given(parsers.parse("un passage terminé de « {artiste} » – « {titre} »"))
def passage_termine(base_vide: Connexion, artiste: str, titre: str) -> None:
	passage(base_vide, -1, artiste, titre)


@given(parsers.parse("{nombre:d} passages terminés, masqués"))
def passages_masques(base_vide: Connexion, nombre: int) -> None:
	for numero in range(1, nombre + 1):
		passage(base_vide, numero, f"Artiste {numero}", f"Titre {numero}", sonore_masque=True)


@given("le masquage de tous les sonores")
def masquer_tous(base_vide: Connexion) -> None:
	base_vide.execute("UPDATE sonores SET masquer_metadonnees = true")


@given("la page publique ne peut pas être écrite")
def page_impossible(banc: Banc) -> None:
	# Un répertoire à la place du fichier : même un compte administrateur ne peut pas l'écrire.
	sorties_du_banc(banc).chemins.html.mkdir(parents=True)


# ─── Quand ─────────────────────────────────────────────────


@when("les sorties sont mises à jour")
def mettre_a_jour(banc: Banc) -> None:
	with connecter(*parametres_base_test(), Role.LECTURE) as connexion:
		sorties_du_banc(banc).mettre_a_jour(connexion, DEBUT)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"l'artiste et le titre sont (?P<verdict>affichés|masqués) sur la sortie publique"))
def verdict_public(banc: Banc, verdict: str) -> None:
	mettre_a_jour(banc)
	visibles = ("Artiste secret" in page(banc)) and ("Titre secret" in page(banc))
	assert visibles is (verdict == "affichés"), page(banc)
	if verdict == "masqués":
		assert "Radio Exemple" in page(banc)


@then(parsers.parse("la page publique montre « {texte} »"))
def page_montre(banc: Banc, texte: str) -> None:
	assert texte in page(banc), page(banc)


@then(parsers.parse("la page publique montre {nombre:d} fois « {texte} »"))
def page_montre_n_fois(banc: Banc, nombre: int, texte: str) -> None:
	assert page(banc).count(texte) == nombre, page(banc)


@then(parsers.parse("la page publique ne montre pas « {texte} »"))
def page_ne_montre_pas_texte(banc: Banc, texte: str) -> None:
	assert texte not in page(banc), page(banc)


@then(parsers.parse("la page publique ne montre ni « {premier} » ni « {second} »"))
def page_ne_montre_pas(banc: Banc, premier: str, second: str) -> None:
	assert (premier not in page(banc)) and (second not in page(banc)), page(banc)


@then(parsers.parse("la page publique montre « {titre} » comme sonore à l'antenne"))
def a_l_antenne(banc: Banc, titre: str) -> None:
	en_cours = re.search(r'<section class="en-cours">(.*?)</section>', page(banc), re.DOTALL)
	assert (en_cours is not None) and (titre in en_cours.group(1)), page(banc)


@then(parsers.parse("la page publique liste {nombre:d} passages précédents, du plus récent au plus ancien"))
def precedents(banc: Banc, nombre: int) -> None:
	liste = re.search(r'<ol class="precedents">(.*?)</ol>', page(banc), re.DOTALL)
	assert liste is not None, page(banc)
	titres = re.findall(r"Titre (\d+)", liste.group(1))
	assert titres == [str(n) for n in range(25, 25 - nombre, -1)], titres


@then("la page publique se rafraîchit toutes les 30 secondes")
def rafraichie(banc: Banc) -> None:
	assert '<meta http-equiv="refresh" content="30">' in page(banc)


@then("la page publique ne montre pas l'emplacement du fichier")
def sans_emplacement(banc: Banc) -> None:
	assert ("/musique/" not in page(banc)) and (".flac" not in page(banc)), page(banc)


@then(parsers.parse("la playlist compte {nombre:d} entrées, du passage {premier:d} au passage {dernier:d}"))
def playlist(banc: Banc, nombre: int, premier: int, dernier: int) -> None:
	texte = sorties_du_banc(banc).chemins.pls.read_text(encoding="utf-8")
	fichiers = re.findall(r"^File\d+=(.*)$", texte, re.MULTILINE)
	assert texte.startswith("[playlist]\n")
	assert (f"NumberOfEntries={nombre}" in texte) and ("Version=2" in texte)
	assert fichiers == [f"/musique/{n}.flac" for n in range(premier, dernier + 1)], fichiers


@then("chaque entrée de la playlist donne l'artiste et le titre")
def titres_de_la_playlist(banc: Banc) -> None:
	texte = sorties_du_banc(banc).chemins.pls.read_text(encoding="utf-8")
	titres = re.findall(r"^Title(\d+)=(.*)$", texte, re.MULTILINE)
	assert (titres) and (all(re.fullmatch(r"Artiste \d+ – Titre \d+", titre) for _, titre in titres)), titres


def lignes_csv(banc: Banc, nom: str) -> list[dict[str, str]]:
	chemin = sorties_du_banc(banc).chemins.csv.parent / nom
	with chemin.open(encoding="utf-8-sig", newline="") as fichier:
		return list(csv.DictReader(fichier, delimiter=";"))


@then(parsers.parse("le CSV « {nom} » commence par l'en-tête et le BOM"))
def entete_csv(banc: Banc, nom: str) -> None:
	octets = (sorties_du_banc(banc).chemins.csv.parent / nom).read_bytes()
	entete = "﻿debut;fin;duree;artiste;titre;emplacement;evenement;sequence;banque;sans_incident\r\n"
	assert octets.startswith(entete.encode()), octets[:120]


@then(parsers.parse("le CSV « {nom} » a les lignes :"))
def lignes_attendues(banc: Banc, nom: str, datatable: list[list[str]]) -> None:
	colonnes, *attendues = datatable
	lues = [[ligne[colonne] for colonne in colonnes] for ligne in lignes_csv(banc, nom)]
	assert lues == attendues, lues


@then(parsers.re(r"le CSV « (?P<nom>[^»]+) » a (?P<nombre>\d+) lignes? de passage"))
def nombre_de_lignes(banc: Banc, nom: str, nombre: str) -> None:
	assert len(lignes_csv(banc, nom)) == int(nombre)


@then(parsers.parse("le journal du binaire a annoncé « {texte} », en information"))
def annonce(caplog: pytest.LogCaptureFixture, texte: str) -> None:
	assert any((r.levelno == logging.INFO) and (texte in r.getMessage()) for r in caplog.records), caplog.text


@then(parsers.parse("le journal du binaire a signalé « {texte} », en anomalie"))
def anomalie(caplog: pytest.LogCaptureFixture, texte: str) -> None:
	assert any((r.levelno == logging.WARNING) and (texte in r.getMessage()) for r in caplog.records), caplog.text


@then("les sorties de Machin lecture sont celles de la configuration de test")
def sorties_de_la_configuration() -> None:
	configuration = configuration_test()
	sorties = Sorties.depuis(configuration)
	assert sorties.chemins == configuration.sorties
	assert sorties.metadonnees == configuration.metadonnees
