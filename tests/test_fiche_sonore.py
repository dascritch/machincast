"""Scénarios de la fiche d'un sonore (https://github.com/dascritch/machincast/issues/28).

Les étapes de la fenêtre, des listes et des fiches sont dans tests/etapes_interface.py ; le serveur de flux local, dans
tests/etapes_diffusion.py. Celles-ci manipulent la fiche d'un sonore et lisent la base de test.
"""

import json
import os
import socket
import subprocess
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import QAbstractButton, QComboBox
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import essai_flux, fiche_sonore
from machincast.interface.fiche_sonore import FicheSonore
from tests.etapes_interface import NOM, Connexion, Contexte, fenetre, identifiant, ouvrir_dans, taper
from tests.flux import ServeurDeFlux

scenarios("fiche_sonore.feature")

ESPACE = "⎵"
"""Une espace dans une cellule de tableau, que Gherkin rognerait."""
RETOUR = "⏎"
"""Un retour à la ligne dans un texte attendu."""
DATE = "dd/MM/yyyy HH:mm"


def fiche(interface: Contexte) -> FicheSonore:
	ouverte = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(ouverte, FicheSonore), ouverte
	return ouverte


def sonore_id(base: Connexion, nom: str) -> int:
	"""Un sonore par son titre ; sans titre, par le nom de son fichier, ou l'adresse de son stream ou de son
	marque-page."""
	lignes = base.execute(
		"SELECT s.id FROM sonores s LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id WHERE s.titre = %s"
		" OR (s.titre IS NULL AND (s.emplacement LIKE '%%/' || %s OR s.url_stream = %s OR m.url = %s))",
		(nom, nom, nom, nom),
	).fetchall()
	assert len(lignes) == 1, f"« {nom} » : {lignes}"
	return int(str(lignes[0][0]))


def heure_de_paris(texte: str) -> datetime:
	return datetime.fromisoformat(texte).astimezone()


def choisir_texte(choix: QComboBox, texte: str) -> None:
	indice = choix.findText(texte, Qt.MatchFlag.MatchFixedString)
	assert indice >= 0, f"« {texte} » absent : {[choix.itemText(i) for i in range(choix.count())]}"
	choix.setCurrentIndex(indice)


def textes(choix: QComboBox) -> list[str]:
	return [choix.itemText(indice).casefold() for indice in range(choix.count())]


def si_coche(case: QAbstractButton, lire: Callable[[], str]) -> Callable[[], str]:
	"""Ce que montre un champ qui ne compte que si sa case est cochée : rien sinon."""

	def lecture() -> str:
		if not case.isChecked():
			return ""
		return lire()

	return lecture


def montre(sonore: FicheSonore) -> dict[str, Callable[[], str]]:
	"""Ce que la fiche montre, par nom de champ à l'écran."""
	ui = sonore.ui

	return {
		"Type": ui.type_sonore.text,
		"Emplacement": ui.emplacement.text,
		"Durée": ui.duree.text,
		"État": lambda: ui.etat.currentText().casefold(),
		"Artiste": ui.artiste.text,
		"Titre": ui.titre.text,
		"Année": ui.annee.text,
		"Album": ui.album.text,
		"Artiste de l'album": ui.artiste_album.text,
		"Genre": ui.genre.text,
		"Compositeur": ui.compositeur.text,
		"Label": ui.label.text,
		"Piste": ui.piste.text,
		"Crossfade de début": ui.crossfade_debut.text,
		"Crossfade de fin": ui.crossfade_fin.text,
		"Maximum de lectures": ui.max_lectures.text,
		"Artiste et titre": lambda: ui.masquage.currentText().casefold(),
		"Diffusion à partir du": si_coche(ui.a_debut, ui.debut_diffusion.text),
		"Diffusion jusqu'au": si_coche(ui.a_fin, ui.fin_diffusion.text),
		"Adresse directe": si_coche(ui.par_adresse, ui.url_stream.text),
		"Marque-page": si_coche(ui.par_marque_page, ui.marque_page.currentText),
		"Événement de secours": lambda: ui.secours.currentText().casefold(),
	}


@pytest.fixture
def serveur_muet() -> Iterator[str]:
	"""Un serveur qui accepte les connexions sans jamais rien répondre ; son adresse."""
	ecoute = socket.socket()
	ecoute.bind(("127.0.0.1", 0))
	ecoute.listen()
	yield f"http://127.0.0.1:{ecoute.getsockname()[1]}/muet"
	ecoute.close()


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le sonore « {nom} » a en base :"))
def sonore_en_base(base_vide: Connexion, nom: str, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	identifiant_sonore = sonore_id(base_vide, nom)
	for champ, texte in ((champ.strip(), texte.strip()) for champ, texte in rangees):
		valeur: object = texte
		if champ in ("debut_diffusion", "fin_diffusion", "verifie_le"):
			valeur = heure_de_paris(texte)
		requete = f"UPDATE sonores SET {champ} = %s WHERE id = %s"
		base_vide.execute(requete, (valeur, identifiant_sonore))


@given(parsers.parse("le marque-page « {nom} » à l'adresse du flux « {flux} » du serveur local"))
def marque_page_local(serveur: ServeurDeFlux, base_vide: Connexion, nom: str, flux: str) -> None:
	base_vide.execute("INSERT INTO marques_pages_streams (nom, url) VALUES (%s, %s)", (nom, serveur.adresse(flux)))


@given(parsers.parse("le stream « {nom} » est sur le marque-page « {marque} »"))
def sur_marque_page(base_vide: Connexion, nom: str, marque: str) -> None:
	base_vide.execute(
		"UPDATE sonores SET url_stream = NULL, marque_page_id = %s WHERE id = %s",
		(identifiant(base_vide, "marques_pages_streams", "nom", marque), sonore_id(base_vide, nom)),
	)


@given("un serveur qui accepte les connexions sans jamais répondre")
def muet(serveur_muet: str) -> None:
	"""Le serveur est ouvert par le fixture."""


@given(parsers.parse("un test de flux limité à {secondes:d} seconde"))
def delai_court(monkeypatch: pytest.MonkeyPatch, secondes: int) -> None:
	monkeypatch.setattr(essai_flux, "DELAI", timedelta(seconds=secondes))


def passage(
	base: Connexion,
	sonore: int,
	debut: datetime,
	fin: datetime | None,
	references: tuple[int | None, int | None, int | None] = (None, None, None),
	sans_incident: bool | None = None,
) -> None:
	evenement, sequence, banque = references
	numero = uuid.uuid4()
	colonnes = "passage_id, type_ligne, horodatage, sonore_id, evenement_id, sequence_id, banque_id"
	base.execute(
		f"INSERT INTO airplay ({colonnes}) VALUES (%s, 'debut', %s, %s, %s, %s, %s)",  # noqa: S608
		(numero, debut, sonore, evenement, sequence, banque),
	)
	if fin is not None:
		base.execute(
			f"INSERT INTO airplay ({colonnes}, duree_diffusee, sans_incident)"  # noqa: S608
			" VALUES (%s, 'fin', %s, %s, %s, %s, %s, %s, %s)",
			(numero, fin, sonore, evenement, sequence, banque, fin - debut, sans_incident),
		)


def reference(base: Connexion, table: str, nom: str) -> int | None:
	if nom == "":
		return None
	return identifiant(base, table, "nom_interne", nom)


@given("les passages de sonores :")
def passages(base_vide: Connexion, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	for valeurs in rangees:
		ligne = dict(zip(entetes, (valeur.strip() for valeur in valeurs), strict=True))
		fin = None
		if ligne["fin"] != "":
			fin = heure_de_paris(ligne["fin"])
		sans_incident = {"oui": True, "non": False, "": None}[ligne["sans_incident"]]
		references = (
			reference(base_vide, "evenements", ligne["evenement"]),
			reference(base_vide, "sequences", ligne["sequence"]),
			reference(base_vide, "banques", ligne["banque"]),
		)
		debut = heure_de_paris(ligne["debut"])
		passage(base_vide, sonore_id(base_vide, ligne["sonore"]), debut, fin, references, sans_incident)


@given("le log :")
def log(base_vide: Connexion, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	for valeurs in rangees:
		ligne = dict(zip(entetes, (valeur.strip() for valeur in valeurs), strict=True))
		base_vide.execute(
			"INSERT INTO log (horodatage, niveau, nature, message, sonore_id) VALUES (%s, %s, %s, %s, %s)",
			(
				heure_de_paris(ligne["horodatage"]),
				ligne["niveau"],
				ligne["nature"],
				ligne["message"],
				sonore_id(base_vide, ligne["sonore"]),
			),
		)


@given(parsers.parse("le sonore « {nom} » est passé {fois:d} fois, toutes les {minutes:d} minutes depuis « {debut} »"))
def passages_reguliers(base_vide: Connexion, nom: str, fois: int, minutes: int, debut: str) -> None:
	sonore = sonore_id(base_vide, nom)
	for rang in range(fois):
		commence = heure_de_paris(debut) + timedelta(minutes=minutes * rang)
		passage(base_vide, sonore, commence, commence + timedelta(minutes=1), sans_incident=True)


# ─── Quand ─────────────────────────────────────────────────


@when("je saisis dans la fiche du sonore :")
def saisir(interface: Contexte, qtbot: QtBot, datatable: list[list[str]]) -> None:
	ui = fiche(interface).ui
	textes_libres = {
		"Artiste": ui.artiste,
		"Titre": ui.titre,
		"Année": ui.annee,
		"Album": ui.album,
		"Artiste de l'album": ui.artiste_album,
		"Genre": ui.genre,
		"Compositeur": ui.compositeur,
		"Label": ui.label,
		"Piste": ui.piste,
	}
	listes = {"Artiste et titre": ui.masquage, "État": ui.etat, "Événement de secours": ui.secours}
	dates = {
		"Diffusion à partir du": (ui.a_debut, ui.debut_diffusion),
		"Diffusion jusqu'au": (ui.a_fin, ui.fin_diffusion),
	}
	_entetes, *rangees = datatable
	for champ, brut in ((champ.strip(), brut.strip().replace(ESPACE, " ")) for champ, brut in rangees):
		if champ in textes_libres:
			taper(qtbot, textes_libres[champ], brut)
		elif champ in listes:
			choisir_texte(listes[champ], brut)
		elif champ in dates:
			case, date = dates[champ]
			case.setChecked(brut != "")
			if brut != "":
				date.setDateTime(QDateTime.fromString(brut, DATE))
		elif champ in ("Crossfade de début", "Crossfade de fin"):
			{"Crossfade de début": ui.crossfade_debut, "Crossfade de fin": ui.crossfade_fin}[champ].setValue(
				float(brut.replace(",", "."))
			)
		elif champ == "Maximum de lectures":
			ui.max_lectures.setValue(int(brut))
		elif champ == "Adresse directe":
			qtbot.mouseClick(ui.par_adresse, Qt.MouseButton.LeftButton)
			taper(qtbot, ui.url_stream, brut)
		else:
			assert champ == "Marque-page", champ
			qtbot.mouseClick(ui.par_marque_page, Qt.MouseButton.LeftButton)
			choisir_texte(ui.marque_page, brut)


@when(parsers.parse("je coche « {case} » dans la fiche du sonore"))
def cocher(interface: Contexte, qtbot: QtBot, case: str) -> None:
	ui = fiche(interface).ui
	cases = {ui.a_debut.text(): ui.a_debut, ui.a_fin.text(): ui.a_fin}
	qtbot.mouseClick(cases[case], Qt.MouseButton.LeftButton)


@when(parsers.parse("l'indexation change le titre de « {nom} » en « {titre} », et son album en « {album} »"))
def indexation(base_vide: Connexion, nom: str, titre: str, album: str) -> None:
	base_vide.execute(
		"UPDATE sonores SET titre = %s, metadonnees_musicales = metadonnees_musicales || %s::jsonb WHERE id = %s",
		(titre, json.dumps({"album": album}), sonore_id(base_vide, nom)),
	)


@when(parsers.parse("la diffusion passe « {nom} » à l'état « {etat} »"))
def diffusion(base_vide: Connexion, nom: str, etat: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = %s WHERE id = %s", (etat, sonore_id(base_vide, nom)))


@when(parsers.parse("je saisis l'adresse du flux « {flux} » du serveur local dans la fiche du sonore"))
def adresse_locale(interface: Contexte, qtbot: QtBot, serveur: ServeurDeFlux, flux: str) -> None:
	ui = fiche(interface).ui
	qtbot.mouseClick(ui.par_adresse, Qt.MouseButton.LeftButton)
	taper(qtbot, ui.url_stream, serveur.adresse(flux))


@when("je saisis l'adresse du serveur muet dans la fiche du sonore")
def adresse_muette(interface: Contexte, qtbot: QtBot, serveur_muet: str) -> None:
	taper(qtbot, fiche(interface).ui.url_stream, serveur_muet)


@when("je choisis l'adresse directe dans la fiche du sonore")
def choisir_adresse(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(fiche(interface).ui.par_adresse, Qt.MouseButton.LeftButton)


@when(parsers.parse("le flux « {flux} » du serveur local est avare"))
def avare(serveur: ServeurDeFlux, flux: str) -> None:
	serveur.avares.add(flux)
	serveur.en_ligne[flux] = True


@when(parsers.parse("le serveur de flux local a bientôt {nombre:d} connexion"))
@then(parsers.parse("le serveur de flux local a bientôt {nombre:d} connexion"))
def connexions(serveur: ServeurDeFlux, qtbot: QtBot, nombre: int) -> None:
	qtbot.waitUntil(lambda: serveur.connexions == nombre, timeout=5000)


@then("le serveur de flux local n'a bientôt plus de connexion")
def plus_de_connexion(serveur: ServeurDeFlux, qtbot: QtBot) -> None:
	# Moins que le délai du test d'un flux, qui fermerait de lui-même sa connexion.
	qtbot.waitUntil(lambda: serveur.connexions == 0, timeout=5000)


@when("je teste le flux")
def lancer_essai(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(fiche(interface).ui.tester, Qt.MouseButton.LeftButton)


# ─── Alors ─────────────────────────────────────────────────


@then("la fiche du sonore montre :")
def montres(interface: Contexte, datatable: list[list[str]]) -> None:
	lecture = montre(fiche(interface))
	_entetes, *rangees = datatable
	attendus = [(champ.strip(), valeur.strip()) for champ, valeur in rangees]
	assert [(champ, lecture[champ]()) for champ, _valeur in attendus] == attendus


@then(parsers.parse("la fiche du sonore montre les autres métadonnées « {texte} »"))
def autres(interface: Contexte, texte: str) -> None:
	assert fiche(interface).ui.autres_metadonnees.text() == texte


@then(parsers.re(r"la fiche du sonore montre les champs saisis à la main (?P<champs>.+)"))
def champs_montres(interface: Contexte, champs: str) -> None:
	attendu = f"Saisis à la main, que l'indexeur ne modifie plus : {', '.join(NOM.findall(champs))}."
	assert fiche(interface).ui.champs_edites.text() == attendu


@then("l'emplacement de la fiche du sonore ne se modifie pas")
def emplacement_fixe(interface: Contexte) -> None:
	assert fiche(interface).ui.emplacement.isReadOnly()


@then("la fiche du sonore n'a pas de réglages de stream")
def sans_stream(interface: Contexte) -> None:
	ui = fiche(interface).ui
	assert (ui.groupe_stream.isHidden(), ui.emplacement.isHidden()) == (True, False)


@then("la fiche du sonore n'a pas d'emplacement")
def sans_emplacement(interface: Contexte) -> None:
	ui = fiche(interface).ui
	assert (ui.groupe_stream.isHidden(), ui.emplacement.isHidden()) == (False, True)


@then(
	parsers.re(
		r"le sonore « (?P<nom>[^»]+) » est en base, (?P<quoi>d'artiste « [^»]+ »|sans artiste|sans artiste ni titre)"
	)
)
def artiste_en_base(base_vide: Connexion, nom: str, quoi: str) -> None:
	ligne = base_vide.execute(
		"SELECT artiste, titre FROM sonores WHERE id = %s", (sonore_id(base_vide, nom),)
	).fetchone()
	assert ligne is not None
	artiste, titre = ligne
	attendu = (None, nom)
	if quoi.startswith("d'artiste"):
		attendu = (NOM.findall(quoi)[0], nom)
	if quoi == "sans artiste ni titre":
		attendu = (None, None)
	assert (artiste, titre) == attendu


@then(parsers.re(r"les métadonnées musicales de « (?P<nom>[^»]+) » sont (?P<texte>\{.*\})"))
def metadonnees(base_vide: Connexion, nom: str, texte: str) -> None:
	ligne = base_vide.execute(
		"SELECT metadonnees_musicales FROM sonores WHERE id = %s", (sonore_id(base_vide, nom),)
	).fetchone()
	assert ligne is not None
	assert ligne[0] == json.loads(texte)


@then(parsers.re(r"les champs saisis à la main de « (?P<nom>[^»]+) » sont (?P<champs>.+)"))
def champs_en_base(base_vide: Connexion, nom: str, champs: str) -> None:
	ligne = base_vide.execute(
		"SELECT champs_edites FROM sonores WHERE id = %s", (sonore_id(base_vide, nom),)
	).fetchone()
	assert ligne is not None
	assert ligne[0] == NOM.findall(champs)


@then(parsers.parse("le sonore « {nom} » a en base :"))
def colonnes_en_base(base_vide: Connexion, nom: str, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	attendus = [(champ.strip(), valeur.strip()) for champ, valeur in rangees]
	identifiant_sonore = sonore_id(base_vide, nom)
	lus = []
	for champ, _valeur in attendus:
		ligne = base_vide.execute(f"SELECT {champ} FROM sonores WHERE id = %s", (identifiant_sonore,)).fetchone()
		assert ligne is not None
		valeur = ligne[0]
		if isinstance(valeur, datetime):
			valeur = valeur.astimezone()
		lus.append((champ, str(valeur)))
	assert lus == attendus


@then(parsers.re(r"l'état de la fiche du sonore se choisit parmi (?P<etats>.+)"))
def etats(interface: Contexte, etats: str) -> None:
	choix = fiche(interface).ui.etat
	attendus = NOM.findall(etats)
	assert (textes(choix), choix.isEnabled()) == (attendus, len(attendus) > 1)


@then(parsers.re(r"les marques-pages proposés sont (?P<noms>.+)"))
def marques_proposees(interface: Contexte, noms: str) -> None:
	assert textes(fiche(interface).ui.marque_page) == [nom.casefold() for nom in NOM.findall(noms)]


@then(parsers.re(r"les événements de secours proposés sont (?P<noms>.+)"))
def secours_proposes(interface: Contexte, noms: str) -> None:
	assert textes(fiche(interface).ui.secours) == [nom.casefold() for nom in NOM.findall(noms)]


@then(
	parsers.re(
		r"le stream « (?P<nom>[^»]+) » est en base,"
		r" (?:sur le marque-page « (?P<marque>[^»]+) »|à l'adresse « (?P<url>[^»]+) »),"
		r" (?:sans adresse directe|sans marque-page),"
		r" (?:secouru par « (?P<secours>[^»]+) »|sans événement de secours)"
	)
)
def stream_en_base(base_vide: Connexion, nom: str, marque: str | None, url: str | None, secours: str | None) -> None:
	ligne = base_vide.execute(
		"SELECT s.url_stream, m.nom, e.nom_interne FROM sonores s"
		" LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id"
		" LEFT JOIN evenements e ON e.id = s.secours_evenement_id WHERE s.id = %s",
		(sonore_id(base_vide, nom),),
	).fetchone()
	assert ligne == (url, marque, secours)


@then("le choix d'un marque-page est inactif")
def marque_page_inactif(interface: Contexte) -> None:
	assert not fiche(interface).ui.par_marque_page.isEnabled()


@then("le test du flux est en cours")
def essai_en_cours(interface: Contexte) -> None:
	ui = fiche(interface).ui
	assert (ui.resultat_essai.text(), ui.tester.isEnabled()) == ("Test du flux en cours…", False)


@then(parsers.parse("le test du flux dit bientôt « {verdict} »"))
def verdict_bientot(interface: Contexte, qtbot: QtBot, verdict: str) -> None:
	ui = fiche(interface).ui
	qtbot.waitUntil(lambda: ui.resultat_essai.text() == verdict, timeout=15000)


@then("le test du flux dit bientôt qu'il ne répond pas, avec l'erreur du serveur")
def erreur_bientot(interface: Contexte, qtbot: QtBot) -> None:
	ui = fiche(interface).ui
	debut = "Le flux ne répond pas : "

	def erreur() -> bool:
		texte = ui.resultat_essai.text()
		fin = (texte.endswith(".")) and (not texte.endswith(".."))
		return (texte.startswith(debut)) and (len(texte) > len(debut) + 1) and ("n'arrive pas" not in texte) and (fin)

	qtbot.waitUntil(erreur, timeout=15000)


@then(parsers.parse("le test du flux dit « {verdict} »"))
def verdict(interface: Contexte, verdict: str) -> None:
	assert fiche(interface).ui.resultat_essai.text() == verdict


@then(parsers.parse("après {secondes:d} secondes, le test du flux dit toujours « {verdict} »"))
def toujours(interface: Contexte, qtbot: QtBot, secondes: int, verdict: str) -> None:
	qtbot.wait(secondes * 1000)
	assert fiche(interface).ui.resultat_essai.text() == verdict


@then(parsers.re(r"les dates de diffusion qui se saisissent sont (?P<dates>.+)"))
def dates_actives(interface: Contexte, dates: str) -> None:
	ui = fiche(interface).ui
	champs = {"Diffusion à partir du": ui.debut_diffusion, "Diffusion jusqu'au": ui.fin_diffusion}
	assert [nom for nom, champ in champs.items() if champ.isEnabled()] == NOM.findall(dates)


@then(parsers.parse("seul le champ « {nom} » du stream se saisit"))
def champ_de_stream(interface: Contexte, nom: str) -> None:
	ui = fiche(interface).ui
	champs = {"Adresse directe": ui.url_stream, "Marque-page": ui.marque_page}
	assert [cle for cle, champ in champs.items() if champ.isEnabled()] == [nom]


@then("la fiche du sonore ne montre aucun champ saisi à la main")
def aucun_champ(interface: Contexte) -> None:
	assert fiche(interface).ui.champs_edites.text() == ""


@then("le flux peut de nouveau être testé")
def essai_relancable(interface: Contexte) -> None:
	ui = fiche(interface).ui
	assert (ui.tester.isEnabled(), fiche(interface).essai.en_cours()) == (True, False)


@then("les derniers passages du sonore sont :")
def derniers_passages(interface: Contexte, datatable: list[list[str]]) -> None:
	table = fiche(interface).ui.passages
	entetes, *rangees = datatable
	titres = [table.horizontalHeaderItem(colonne).text() for colonne in range(table.columnCount())]
	assert titres == [entete.strip() for entete in entetes]
	montrees = [
		[table.item(rangee, colonne).text() for colonne in range(table.columnCount())]
		for rangee in range(table.rowCount())
	]
	assert montrees == [[valeur.strip() for valeur in valeurs] for valeurs in rangees]


@then(parsers.parse("l'infobulle des incidents du passage de « {debut} » est « {texte} »"))
def infobulle(interface: Contexte, debut: str, texte: str) -> None:
	table = fiche(interface).ui.passages
	rangees = [rangee for rangee in range(table.rowCount()) if table.item(rangee, 0).text() == debut]
	assert len(rangees) == 1
	assert table.item(rangees[0], table.columnCount() - 1).toolTip() == texte.replace(RETOUR, "\n")


@then(parsers.parse("la fiche du sonore montre {nombre:d} passages, du « {premier} » au « {dernier} »"))
def nombre_de_passages(interface: Contexte, nombre: int, premier: str, dernier: str) -> None:
	table = fiche(interface).ui.passages
	debuts = [table.item(rangee, 0).text() for rangee in range(table.rowCount())]
	assert (len(debuts), debuts[0], debuts[-1]) == (nombre, premier, dernier)


# ─── Améliorations (https://github.com/dascritch/machincast/issues/125) ─────


@given(parsers.parse("le fichier « {chemin} », de {octets:d} octets, modifié le « {instant} »"))
def fichier_date(interface: Contexte, chemin: str, octets: int, instant: str) -> None:
	fichier = Path(interface.chemin(chemin))
	fichier.parent.mkdir(parents=True, exist_ok=True)
	fichier.write_bytes(b"\0" * octets)
	horodatage = heure_de_paris(instant).timestamp()
	os.utime(fichier, (horodatage, horodatage))


@when("je clique sur le bouton du dossier du fichier")
def ouvrir_le_dossier(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(fiche(interface).ui.ouvrir_dossier, Qt.MouseButton.LeftButton)


@when(parsers.parse("j'ouvre la relation « {nom} » du sonore"))
def ouvrir_relation(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	ouvrir_dans(qtbot, fiche(interface).ui.relations, nom)


@then("les relations du sonore sont :")
def relations(interface: Contexte, datatable: list[list[str]]) -> None:
	table = fiche(interface).ui.relations
	entetes, *rangees = datatable
	colonnes = [table.horizontalHeaderItem(colonne).text() for colonne in range(table.columnCount())]
	assert colonnes == [entete.strip() for entete in entetes]
	lues = [
		[table.item(rangee, colonne).text() for colonne in range(table.columnCount())]
		for rangee in range(table.rowCount())
	]
	assert lues == [[valeur.strip() for valeur in rangee] for rangee in rangees]


@then(parsers.parse("la fiche du sonore dit « {texte} »"))
def dit(interface: Contexte, texte: str) -> None:
	assert fiche(interface).ui.aucune_relation.isVisible()
	assert fiche(interface).ui.aucune_relation.text() == texte


@then("l'encart « Fichier » de la fiche du sonore montre :")
def encart_fichier(interface: Contexte, datatable: list[list[str]]) -> None:
	"""« <création du fichier> » : la date de naissance que donne stat (format W), ou « inconnue » si le système n'en a
	pas."""
	ui = fiche(interface).ui
	assert ui.groupe_fichier.isVisible()
	champs = {
		"Type": ui.type_mime,
		"Encodage moyen": ui.encodage,
		"Taille": ui.taille,
		"Créé le": ui.cree_le,
		"Modifié le": ui.modifie_le,
		"Dernière vérification complète": ui.verifie_le,
	}
	_entetes, *rangees = datatable
	emplacement = Path(ui.emplacement.text())
	for champ, valeur in ((champ.strip(), valeur.strip()) for champ, valeur in rangees):
		if valeur == "<création du fichier>":
			naissance = int(
				subprocess.run(["stat", "--format=%W", str(emplacement)], capture_output=True, text=True).stdout
			)
			valeur = "inconnue"
			if naissance > 0:
				valeur = f"{datetime.fromtimestamp(naissance).astimezone():%Y-%m-%d %H:%M:%S}"
		assert (champ, champs[champ].text()) == (champ, valeur)


@then("la fiche du sonore n'a ni encart « Fichier », ni bouton du dossier")
def sans_fichier(interface: Contexte) -> None:
	ui = fiche(interface).ui
	assert not ui.groupe_fichier.isVisible()
	assert not ui.ouvrir_dossier.isVisible()


@then("la fiche du sonore ne dit pas qu'aucun élément ne le cite")
def ne_dit_pas(interface: Contexte) -> None:
	assert not fiche(interface).ui.aucune_relation.isVisible()


@given("un système de fichiers qui ne garde pas la date de création")
def sans_date_de_creation(monkeypatch: pytest.MonkeyPatch) -> None:
	"""stat répond 0 quand le système de fichiers ne garde pas la date de naissance d'un fichier."""
	executer = subprocess.run

	def stat(commande: list[str], **options: object) -> subprocess.CompletedProcess[str]:
		if commande[:2] == ["stat", "--format=%W"]:
			return subprocess.CompletedProcess(commande, 0, "0\n", "")
		return executer(commande, **options)  # type: ignore[call-overload,no-any-return]

	monkeypatch.setattr(fiche_sonore.subprocess, "run", stat)
