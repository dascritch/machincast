"""Scénarios de la pré-écoute d'un sonore (https://github.com/dascritch/machincast/issues/116,
https://github.com/dascritch/machincast/issues/29).

Les étapes de la fenêtre et des fiches sont dans tests/etapes_interface.py, celles du serveur de flux local dans
tests/etapes_diffusion.py. La pré-écoute joue sur la sortie factice des tests, en temps réel : ses positions et son
VU-mètre avancent comme sur un vrai périphérique. Les périphériques du poste sont remplacés par ceux du scénario.
"""

import re
import shutil
import tomllib
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QApplication, QSlider
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.exceptions import TimeoutError as DelaiDepasse
from pytestqt.qtbot import QtBot

from machincast.interface.preecoute import FenetrePreecoute
from tests.etapes_interface import NOM, Contexte, fenetre, fichier_de_configuration
from tests.etapes_preecoute import fenetre_de_preecoute
from tests.sons import FICHIERS_SONORES

scenarios("preecoute.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
DELAI = 5000
"""Millisecondes laissées à GStreamer pour ce qui arrive « bientôt »."""


@given(
	parsers.re(
		r"le sonore « (?P<titre>[^»]+) », pour une copie du fichier de test « (?P<fichier>[^»]+) », de (?P<duree>\d+)"
		r" secondes, aux blancs de (?P<debut>[\d,]+) s au début et (?P<fin>[\d,]+) s à la fin, retirés à l'antenne,"
		r" aux crossfades (?:de (?P<cd>[\d,]+) s au début et (?P<cf>[\d,]+) s à la fin|non paramétrés)"
	)
)
def sonore_audite(
	interface: Contexte,
	base_vide: Connexion,
	titre: str,
	fichier: str,
	duree: str,
	debut: str,
	fin: str,
	cd: str | None,
	cf: str | None,
) -> None:
	"""Un fichier audité, ses blancs retirés à l'antenne ; ses crossfades, ou aucun de paramétré (NULL)."""
	copie = interface.repertoire / fichier
	shutil.copyfile(FICHIERS_SONORES / fichier, copie)
	crossfades = [None, None]
	if (cd is not None) and (cf is not None):
		crossfades = [timedelta(seconds=_secondes(cd)), timedelta(seconds=_secondes(cf))]
	base_vide.execute(
		"INSERT INTO sonores (type, emplacement, titre, etat, duree, debut_detecte, fin_detectee, detection_blancs,"
		" crossfade_debut, crossfade_fin, audite_le, audit_seuil)"
		" VALUES ('fichier', %s, %s, 'actif', %s, %s, %s, true, %s, %s, now(), -40)",
		(
			str(copie),
			titre,
			timedelta(seconds=int(duree)),
			timedelta(seconds=_secondes(debut)),
			timedelta(seconds=_secondes(fin)),
			*crossfades,
		),
	)


def _secondes(texte: str) -> float:
	return float(texte.replace(",", "."))


@given(parsers.parse("le crossfade de début par défaut de {duree} seconde dans la configuration"))
def crossfade_par_defaut(interface: Contexte, duree: str) -> None:
	chemin = fichier_de_configuration(interface)
	with chemin.open("a", encoding="utf-8") as fichier:
		fichier.write(f"\n[crossfades]\ndebut = {_secondes(duree)}\n")


@given(parsers.parse("le fichier du sonore « {titre} » supprimé"))
def fichier_supprime(base_vide: Connexion, titre: str) -> None:
	ligne = base_vide.execute("SELECT emplacement FROM sonores WHERE titre = %s", (titre,)).fetchone()
	assert ligne is not None
	# Une copie de test, dans le répertoire temporaire du scénario.
	Path(str(ligne[0])).unlink()


@given(parsers.parse("le périphérique de l'antenne « {identifiant} »"))
def antenne(interface: Contexte, identifiant: str) -> None:
	interface.audio["peripherique"] = identifiant


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("je clique sur la frise de la pré-écoute à {pourcentage:d} % de sa largeur"))
def placer(interface: Contexte, qtbot: QtBot, pourcentage: int) -> None:
	frise = fenetre_de_preecoute(interface).frise
	point = QPoint(round(frise.width() * pourcentage / 100), frise.height() // 2)
	qtbot.mouseClick(frise, Qt.MouseButton.LeftButton, pos=point)


@when(parsers.re(r"je (?P<geste>coche|décoche) « Écouter comme à l'antenne » dans la pré-écoute"))
def comme_a_l_antenne(interface: Contexte, geste: str) -> None:
	case = fenetre_de_preecoute(interface).ui.comme_a_l_antenne
	assert case.text() == "Écouter comme à l'antenne"
	case.setChecked(geste == "coche")


@when(parsers.re(r"je clique sur « (?P<nom>Début joué|Fin jouée) » dans la pré-écoute"))
def repere(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	ui = fenetre_de_preecoute(interface).ui
	bouton = {"Début joué": ui.debut_joue, "Fin jouée": ui.fin_jouee}[nom]
	assert nom in bouton.text(), bouton.text()
	qtbot.mouseClick(bouton, Qt.MouseButton.LeftButton)


@when(parsers.parse("je choisis la sortie « {nom} » pour la pré-écoute"))
def choisir_la_sortie(interface: Contexte, nom: str) -> None:
	choix = fenetre_de_preecoute(interface).ui.sortie
	indice = choix.findText(nom)
	assert indice >= 0, nom
	choix.setCurrentIndex(indice)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("il n'y a qu'une fenêtre de pré-écoute, titrée « {titre} »"))
def une_seule(interface: Contexte, titre: str) -> None:
	ouvertes = [w for w in QApplication.topLevelWidgets() if (isinstance(w, FenetrePreecoute)) and (w.isVisible())]
	assert len(ouvertes) == 1
	assert ouvertes[0].windowTitle() == titre


@then(parsers.parse("la sortie de la pré-écoute est « {identifiant} »"))
def sortie(interface: Contexte, identifiant: str) -> None:
	ouverte = fenetre_de_preecoute(interface)
	assert ouverte.ui.sortie.currentData() == identifiant
	assert ouverte.lecteur.peripherique == identifiant


@then("le VU-mètre de la pré-écoute est au silence")
def au_silence(interface: Contexte) -> None:
	assert fenetre_de_preecoute(interface).vumetre.niveaux == []


@then("la pré-écoute montre bientôt les informations :")
def informations(interface: Contexte, qtbot: QtBot, datatable: list[list[str]]) -> None:
	ui = fenetre_de_preecoute(interface).ui
	champs = {"Format": ui.format, "Échantillonnage": ui.echantillonnage, "Canaux": ui.canaux}
	attendues = [(nom.strip(), valeur.strip()) for nom, valeur in datatable[1:]]

	def conforme(lue: str, attendue: str) -> bool:
		"""« contient « FLAC » » : le libellé, qui vient de GStreamer, contient ce nom ; sinon, égal."""
		contenu = re.fullmatch(r"contient « (.+) »", attendue)
		if contenu is not None:
			return contenu.group(1) in lue
		return lue == attendue

	def toutes() -> bool:
		return all(conforme(champs[nom].text(), valeur) for nom, valeur in attendues)

	try:
		qtbot.waitUntil(toutes, timeout=DELAI)
	except DelaiDepasse as erreur:
		# Les valeurs lues, pour comprendre l'écart sur un autre poste.
		lues = {nom: champs[nom].text() for nom, _valeur in attendues}
		raise AssertionError(f"informations lues : {lues}, attendues : {dict(attendues)}") from erreur


@then("le débit de la pré-écoute est bientôt donné en kbit/s")
def debit(interface: Contexte, qtbot: QtBot) -> None:
	champ = fenetre_de_preecoute(interface).ui.debit
	qtbot.waitUntil(lambda: champ.text().endswith(" kbit/s"), timeout=DELAI)


@then("la pré-écoute donne bientôt des secondes pré-décodées")
def predecode(interface: Contexte, qtbot: QtBot) -> None:
	champ = fenetre_de_preecoute(interface).ui.predecode
	qtbot.waitUntil(lambda: (champ.text().endswith(" s")) and (champ.text() != "0,0 s"), timeout=DELAI)


@then(parsers.parse("la position de la pré-écoute est bientôt entre {minimum} et {maximum} seconde"))
def position(interface: Contexte, qtbot: QtBot, minimum: str, maximum: str) -> None:
	lecteur = fenetre_de_preecoute(interface).lecteur
	bas, haut = float(minimum.replace(",", ".")), float(maximum.replace(",", "."))
	qtbot.waitUntil(lambda: bas <= ((lecteur.position()) or (0.0)) <= haut, timeout=DELAI)


@then("la pré-écoute ne joue plus rien")
def plus_rien(interface: Contexte) -> None:
	assert not fenetre_de_preecoute(interface).lecteur.actif()


@then(parsers.re(r"la pré-écoute propose les sorties (?P<noms>«.+)"))
def sorties_proposees(interface: Contexte, noms: str) -> None:
	choix = fenetre_de_preecoute(interface).ui.sortie
	assert [choix.itemText(indice) for indice in range(choix.count())] == NOM.findall(noms)


@then(parsers.parse("le fichier de configuration a pour pré-écoute « {identifiant} », avec ses commentaires"))
def configuration_ecrite(interface: Contexte, identifiant: str) -> None:
	chemin = fichier_de_configuration(interface)
	texte = chemin.read_text(encoding="utf-8")
	assert tomllib.loads(texte)["audio"]["preecoute"] == identifiant
	initiale = interface.configuration_initiale.decode("utf-8")
	commentaires = [ligne for ligne in initiale.splitlines() if ligne.startswith("#")]
	assert commentaires == [ligne for ligne in texte.splitlines() if ligne.startswith("#")]


@then("le bouton « Pré-écoute… » de la fiche est inactif")
def bouton_inactif(interface: Contexte) -> None:
	fiche = fenetre(interface).ui.onglets.currentWidget()
	assert not fiche.ui.preecouter.isEnabled()


@when(parsers.parse("je force la sortie « {nom} » pour la pré-écoute"))
def forcer_la_sortie(interface: Contexte, nom: str) -> None:
	"""Une ligne grisée ne se choisit pas à la souris : le programme la choisit, comme le ferait au pire le clavier."""
	choix = fenetre_de_preecoute(interface).ui.sortie
	indice = choix.findText(nom)
	assert indice >= 0, nom
	choix.setCurrentIndex(indice)


@then("la pré-écoute propose les sorties :")
def sorties_et_etats(interface: Contexte, datatable: list[list[str]]) -> None:
	choix = fenetre_de_preecoute(interface).ui.sortie
	modele = choix.model()
	assert isinstance(modele, QStandardItemModel)
	lues = []
	for indice in range(choix.count()):
		etat_de_la_ligne = "inactive"
		if modele.item(indice).isEnabled():
			etat_de_la_ligne = "active"
		lues.append([choix.itemText(indice), etat_de_la_ligne])
	assert lues == [[cellule.strip() for cellule in rangee] for rangee in datatable[1:]]


@then(parsers.parse("le fichier de configuration a toujours pour pré-écoute « {identifiant} »"))
def configuration_intacte(interface: Contexte, identifiant: str) -> None:
	chemin = fichier_de_configuration(interface)
	assert tomllib.loads(chemin.read_text(encoding="utf-8"))["audio"]["preecoute"] == identifiant
	assert chemin.read_bytes() == interface.configuration_initiale


# ─── Frise (https://github.com/dascritch/machincast/issues/224) ───


@then("la pré-écoute a une frise")
def a_une_frise(interface: Contexte) -> None:
	ouverte = fenetre_de_preecoute(interface)
	assert ouverte.ui.zone_frise.isVisibleTo(ouverte)


@then("la pré-écoute n'a ni frise ni barre de position")
def sans_frise(interface: Contexte) -> None:
	ouverte = fenetre_de_preecoute(interface)
	assert not ouverte.ui.zone_frise.isVisibleTo(ouverte)
	assert ouverte.findChildren(QSlider) == []


@then(parsers.re(r"la frise de la pré-écoute montre les zones (?P<noms>«.+)"))
def zones(interface: Contexte, noms: str) -> None:
	plan = fenetre_de_preecoute(interface).frise.plan
	assert plan is not None
	assert [zone.nom for zone in plan.zones()] == NOM.findall(noms)


@then(parsers.parse("la frise de la pré-écoute résume « {texte} »"))
def resume(interface: Contexte, texte: str) -> None:
	assert fenetre_de_preecoute(interface).ui.plage.text() == texte


@then(parsers.parse("l'infobulle « {nom} » de la frise de la pré-écoute est « {texte} »"))
def infobulle(interface: Contexte, nom: str, texte: str) -> None:
	plan = fenetre_de_preecoute(interface).frise.plan
	assert plan is not None
	assert [zone.infobulle for zone in plan.zones() if zone.nom == nom] == [texte]


@then("la forme d'onde de la pré-écoute est bientôt complète, silencieuse au début et sonore au milieu")
def forme_complete(interface: Contexte, qtbot: QtBot) -> None:
	ouverte = fenetre_de_preecoute(interface)

	def finie() -> bool:
		forme = ouverte.forme
		return (forme is not None) and (forme.finie)

	qtbot.waitUntil(finie, timeout=DELAI)
	forme = ouverte.forme
	assert (forme is not None) and (forme.erreur is None)
	assert max(forme.amplitudes(0.0, 0.45)) < 0.01
	assert min(forme.amplitudes(0.6, 1.4)) > 0.4
	# La frise dessine ce que la forme a calculé.
	assert ouverte.frise.forme is forme


@then(parsers.parse("la frise de la pré-écoute dit « {texte} »"))
def remarque(interface: Contexte, qtbot: QtBot, texte: str) -> None:
	frise = fenetre_de_preecoute(interface).frise
	attendu = texte.replace("…/", f"{interface.repertoire}/")
	qtbot.waitUntil(lambda: frise.remarque() == attendu, timeout=DELAI)


@then(parsers.re(r"le volume de la pré-écoute est (?P<bientot>bientôt )?de (?P<volume>\d+) %"))
def volume(interface: Contexte, qtbot: QtBot, bientot: str | None, volume: str) -> None:
	lecteur = fenetre_de_preecoute(interface).lecteur
	attendu = int(volume) / 100
	if bientot is not None:
		qtbot.waitUntil(lambda: abs(lecteur.volume - attendu) < 0.001, timeout=DELAI)
	assert lecteur.volume == pytest.approx(attendu), lecteur.volume


@then(parsers.parse("le volume de la pré-écoute est sous {volume:d} %, au début de la montée"))
def volume_montant(interface: Contexte, volume: int) -> None:
	"""Juste après le lancement : la montée de 0,2 seconde commence, au plus une relève de l'affichage plus tôt."""
	lecteur = fenetre_de_preecoute(interface).lecteur
	assert lecteur.volume < volume / 100, lecteur.volume


@then(parsers.parse("la pré-écoute s'est arrêtée avant {limite} seconde, à la fin de la partie jouée"))
def arretee_avant(interface: Contexte, limite: str) -> None:
	lecteur = fenetre_de_preecoute(interface).lecteur
	derniere = lecteur.derniere_position
	assert derniere is not None
	assert 1.3 <= derniere <= _secondes(limite), derniere


@then(parsers.parse("la pré-écoute s'est arrêtée après {limite} seconde"))
def arretee_apres(interface: Contexte, limite: str) -> None:
	derniere = fenetre_de_preecoute(interface).lecteur.derniere_position
	assert (derniere is not None) and (derniere >= _secondes(limite)), derniere


@then(
	parsers.re(
		r"la position de la pré-écoute passe d'emblée au début de la partie jouée, (?P<debut>[\d,]+) seconde"
		r"(?:, .+)?$"
	)
)
def d_emblee(interface: Contexte, qtbot: QtBot, debut: str) -> None:
	"""Bien avant que la lecture ne l'atteigne d'elle-même : la lecture y a sauté."""
	lecteur = fenetre_de_preecoute(interface).lecteur
	attendu = _secondes(debut)
	qtbot.waitUntil(lambda: attendu - 0.05 <= ((lecteur.position()) or (0.0)) <= attendu + 0.3, timeout=250)


@then("la pré-écoute ne calcule plus de forme d'onde")
def plus_de_forme(interface: Contexte) -> None:
	assert fenetre_de_preecoute(interface).forme is None
