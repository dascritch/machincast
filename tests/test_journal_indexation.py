"""Scénarios du journal de l'indexation, la fenêtre de Machin indexation --fenetre
(https://github.com/dascritch/machincast/issues/120).

La fenêtre s'ouvre ici dans le processus des tests, sur la base de test. Les étapes des fichiers, des sonores et des
banques sont dans tests/etapes_interface.py. L'indexation décode vraiment les fichiers de test ; ses scénarios peuvent
la faire attendre, ou lui retirer ses décodeurs, en remplaçant le décodage de l'indexeur.
"""

import logging
import os
import shutil
import subprocess
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.indexation.decodage import DecodeurIndisponible, Verification, verifier_fichier
from machincast.indexation.verification import LIBELLES
from machincast.interface import dialogues, indexation
from machincast.interface.journal_indexation import FenetreJournal
from tests.base_test import chemin_configuration_test, parametres_base_test
from tests.etapes_interface import ATTENTE, NOM, Connexion, Contexte
from tests.horodatage import sans_horodatage

scenarios("journal_indexation.feature")


@dataclass
class Journal:
	fenetre: FenetreJournal | None = None
	arreter: bool = False
	"""La réponse à la question d'arrêt de l'indexation."""
	questions: list[str] = field(default_factory=list)


@pytest.fixture
def suivi(monkeypatch: pytest.MonkeyPatch) -> Iterator[Journal]:
	"""La fenêtre du scénario, et la question d'arrêt remplacée par la réponse du scénario."""
	suivi = Journal()

	def question(_parent: QWidget, titre: str) -> bool:
		suivi.questions.append(titre)
		return suivi.arreter

	monkeypatch.setattr(dialogues, "confirmer_arret_indexation", question)
	yield suivi
	if suivi.fenetre is not None:
		suivi.fenetre.indexation.arreter()


def journal(suivi: Journal) -> FenetreJournal:
	assert suivi.fenetre is not None
	return suivi.fenetre


@pytest.fixture
def reprise() -> threading.Event:
	"""Ce qu'attend une indexation qui attend."""
	return threading.Event()


@pytest.fixture
def en_attente() -> threading.Event:
	"""Une indexation qui attend en est à son premier décodage."""
	return threading.Event()


# ─── Étant donné ───────────────────────────────────────────


@given("une indexation qui attend")
def indexation_qui_attend(
	monkeypatch: pytest.MonkeyPatch, reprise: threading.Event, en_attente: threading.Event
) -> None:
	def decoder(chemin: Path) -> Verification:
		en_attente.set()
		assert reprise.wait(ATTENTE / 1000), "l'indexation attendue n'a jamais repris"
		return verifier_fichier(chemin)

	monkeypatch.setattr(indexation, "verifier_fichier", decoder)


@given("un indexeur qui ne sait pas décoder les fichiers")
def sans_decodeur(monkeypatch: pytest.MonkeyPatch) -> None:
	def decoder(_chemin: Path) -> Verification:
		raise DecodeurIndisponible("aucun décodeur pour ce format")

	monkeypatch.setattr(indexation, "verifier_fichier", decoder)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le journal « {titre} » de l'indexation s'ouvre"))
def ouvrir(suivi: Journal, base_vide: Connexion, qtbot: QtBot, titre: str) -> None:
	socket, base = parametres_base_test()
	audit_complet = {"Indexation rapide": False, "Audit complet": True}[titre]
	suivi.fenetre = FenetreJournal(socket, base, audit_complet)
	qtbot.addWidget(suivi.fenetre)
	suivi.fenetre.lancer()


@when("l'indexation se termine")
def terminer(suivi: Journal, qtbot: QtBot) -> None:
	qtbot.waitUntil(lambda: not journal(suivi).indexation.en_cours(), timeout=ATTENTE)


@when("l'indexation en est à son premier décodage")
def premier_decodage(en_attente: threading.Event) -> None:
	assert en_attente.wait(ATTENTE / 1000), "l'indexation n'a jamais commencé à décoder"


@when("l'indexation attendue reprend, et se termine")
def reprendre(suivi: Journal, qtbot: QtBot, reprise: threading.Event) -> None:
	reprise.set()
	terminer(suivi, qtbot)


@when("je ferme le journal de l'indexation")
def fermer(suivi: Journal, qtbot: QtBot) -> None:
	qtbot.mouseClick(journal(suivi).ui.fermer, Qt.MouseButton.LeftButton)


@when(parsers.parse("je ferme le journal de l'indexation, en répondant « {reponse} »"))
def fermer_en_repondant(suivi: Journal, qtbot: QtBot, reponse: str) -> None:
	suivi.arreter = reponse == "Arrêter"
	fermer(suivi, qtbot)


@when(
	parsers.parse(
		"je ferme le journal de l'indexation, en répondant « {reponse} », pendant que l'indexation attendue reprend"
	)
)
def fermer_pendant(suivi: Journal, qtbot: QtBot, reprise: threading.Event, reponse: str) -> None:
	threading.Timer(0.3, reprise.set).start()
	fermer_en_repondant(suivi, qtbot, reponse)


@when("je lance Machin indexation --fenetre sans affichage graphique", target_fixture="commande")
def sans_affichage() -> subprocess.CompletedProcess[str]:
	chemin = shutil.which("Machin_indexation")
	assert chemin is not None, 'Machin_indexation n\'est pas installé : lancer pip install -e ".[dev]"'
	environnement = {
		cle: valeur
		for cle, valeur in os.environ.items()
		if cle not in ("DISPLAY", "WAYLAND_DISPLAY", "QT_QPA_PLATFORM")
	}
	return subprocess.run(
		[chemin, "--fenetre", "--config", str(chemin_configuration_test())],
		capture_output=True,
		text=True,
		timeout=60,
		env=environnement,
	)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le journal « {titre} » de l'indexation conclut « {texte} »"))
def conclusion(suivi: Journal, titre: str, texte: str) -> None:
	assert (journal(suivi).windowTitle(), journal(suivi).ui.conclusion.text()) == (titre, texte)


@then(parsers.parse("le journal « {titre} » de l'indexation est ouvert"))
def journal_ouvert(suivi: Journal, titre: str) -> None:
	assert journal(suivi).isVisible()
	assert journal(suivi).windowTitle() == titre


@then("le journal de l'indexation est fermé")
def journal_ferme(suivi: Journal) -> None:
	assert not journal(suivi).isVisible()


@then("aucune question n'a été posée")
def sans_question(suivi: Journal) -> None:
	assert suivi.questions == []


@then(parsers.parse("la question d'arrêt de l'indexation a nommé « {titre} »"))
def question_d_arret(suivi: Journal, titre: str) -> None:
	assert suivi.questions == [titre]


@then("l'indexation est arrêtée")
def arretee(suivi: Journal) -> None:
	assert not journal(suivi).indexation.en_cours()


@then("le journal de l'indexeur n'est plus écouté")
def journal_libre() -> None:
	assert logging.getLogger("machincast.indexation").handlers == []


@then("le journal de l'indexation montre :")
def lignes_du_journal(suivi: Journal, interface: Contexte, datatable: list[list[str]]) -> None:
	"""Les lignes, comme dans le terminal ; un chemin qui commence par « …/ » est dans le répertoire du scénario."""
	_entete, *lignes = datatable
	montrees = [sans_horodatage(ligne) for ligne in journal(suivi).lignes()]
	assert montrees == [interface.chemin_dans(ligne.strip()) for (ligne,) in lignes]


@then("le journal de l'indexation ne signale aucune anomalie")
def sans_anomalie(suivi: Journal) -> None:
	assert journal(suivi).anomalies == []


@then(parsers.re(r"le journal de l'indexation signale (?P<nombre>\d+) anomalies?, sur (?P<chemins>«.+)"))
def anomalies(suivi: Journal, interface: Contexte, nombre: str, chemins: str) -> None:
	signalees = journal(suivi).anomalies
	assert len(signalees) == int(nombre), signalees
	for anomalie, chemin in zip(signalees, NOM.findall(chemins), strict=True):
		assert sans_horodatage(anomalie).startswith(f"[horodatage] {interface.chemin(chemin)} : "), anomalie


@then(parsers.parse("les sonores de la banque « {nom} » en base sont :"))
def sonores_de_la_banque(interface: Contexte, base_vide: Connexion, nom: str, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	lus = base_vide.execute(
		"SELECT s.emplacement, s.etat::text, s.titre FROM sonores s"
		" JOIN banques_sonores bs ON bs.sonore_id = s.id JOIN banques b ON b.id = bs.banque_id"
		" WHERE b.nom_interne = %s ORDER BY bs.position",
		(nom,),
	).fetchall()
	assert [entete.strip() for entete in entetes] == ["emplacement", "etat", "titre"]
	attendus = [tuple(interface.chemin(valeur.strip()) for valeur in rangee) for rangee in rangees]
	assert [tuple(str(valeur) for valeur in ligne) for ligne in lus] == attendus


@then(parsers.parse("le sonore « {titre} » est à l'état « {libelle} »"))
def etat(base_vide: Connexion, titre: str, libelle: str) -> None:
	lu = base_vide.execute("SELECT etat::text FROM sonores WHERE titre = %s", (titre,)).fetchone()
	assert lu is not None, f"sonore « {titre} » absent"
	assert LIBELLES[lu[0]] == libelle


@then(parsers.parse("la commande se termine avec le code {code:d}"))
def code_de_sortie(commande: subprocess.CompletedProcess[str], code: int) -> None:
	assert commande.returncode == code, commande.stderr


@then(parsers.parse("la sortie d'erreur de la commande mentionne « {texte} »"))
def erreur_commande(commande: subprocess.CompletedProcess[str], texte: str) -> None:
	assert texte in commande.stderr, commande.stderr
