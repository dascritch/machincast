"""Scénarios de l'ajout de fichiers sonores depuis la liste des sonores
(https://github.com/dascritch/machincast/issues/30).

Les étapes de la fenêtre, des listes et des fenêtres de dialogue sont dans tests/etapes_interface.py. La vérification
des fichiers ajoutés décode vraiment les fichiers de test ; ses scénarios peuvent la faire attendre, ou lui retirer ses
décodeurs, en remplaçant le décodage de l'indexeur.
"""

import re
import threading
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.indexation.decodage import DecodeurIndisponible, Verification, verifier_fichier
from machincast.interface import verification
from machincast.interface.listes import Liste
from tests.etapes_interface import ATTENTE, Connexion, Contexte, attendre_la_verification, fenetre, glisser, liste

scenarios("ajout_fichiers.feature")


@pytest.fixture
def reprise() -> threading.Event:
	"""Ce qu'attend une vérification qui attend."""
	return threading.Event()


@dataclass
class Decodages:
	"""Décodages en cours, et le plus grand nombre qui l'ont été à la fois."""

	en_cours: int = 0
	maximum: int = 0
	verrou: threading.Lock = field(default_factory=threading.Lock)


@pytest.fixture
def decodages() -> Decodages:
	return Decodages()


# ─── Étant donné ───────────────────────────────────────────


@given("une vérification des fichiers ajoutés qui attend")
def verification_qui_attend(monkeypatch: pytest.MonkeyPatch, reprise: threading.Event, decodages: Decodages) -> None:
	def decoder(chemin: Path) -> Verification:
		with decodages.verrou:
			decodages.en_cours += 1
			decodages.maximum = max(decodages.maximum, decodages.en_cours)
		try:
			assert reprise.wait(ATTENTE / 1000), "la vérification attendue n'a jamais repris"
			return verifier_fichier(chemin)
		finally:
			with decodages.verrou:
				decodages.en_cours -= 1

	monkeypatch.setattr(verification, "verifier_fichier", decoder)


@given("un indexeur qui ne sait pas décoder les fichiers")
def sans_decodeur(monkeypatch: pytest.MonkeyPatch) -> None:
	def decoder(_chemin: Path) -> Verification:
		raise DecodeurIndisponible("aucun décodeur pour ce format")

	monkeypatch.setattr(verification, "verifier_fichier", decoder)


# ─── Quand ─────────────────────────────────────────────────


@when(
	parsers.re(
		r"je dépose sur la liste des sonores (?P<quoi>.+?)(?P<deplacement>, en ne proposant que le déplacement)?"
	)
)
def deposer(interface: Contexte, quoi: str, deplacement: str | None) -> None:
	glisser(interface, liste(interface).table, quoi, True, deplacement is not None)


@when("la vérification attendue reprend, et se termine")
def reprendre(interface: Contexte, qtbot: QtBot, reprise: threading.Event) -> None:
	reprise.set()
	attendre_la_verification(interface, qtbot)


@when("je ferme la fenêtre de l'interface, pendant que la vérification attendue reprend")
def fermer_pendant(interface: Contexte, reprise: threading.Event) -> None:
	assert fenetre(interface).verificateur.en_cours()
	threading.Timer(0.3, reprise.set).start()
	fenetre(interface).close()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"la barre d'état a annoncé, dans l'ordre, (?P<textes>.+)"))
def annonces_ordonnees(interface: Contexte, textes: str) -> None:
	attendues = re.findall(r"« (.+?) »(?:, |$)", textes)
	finales = [annonce for annonce in interface.annonces if annonce.startswith("Vérification")]
	assert finales == attendues


@then("les vérifications ont décodé un fichier à la fois")
def un_a_la_fois(decodages: Decodages) -> None:
	assert decodages.maximum == 1


@then("la vérification des fichiers ajoutés est terminée")
def terminee(interface: Contexte) -> None:
	assert not fenetre(interface).verificateur.en_cours()


@then("les sonores ajoutés sont en base :")
def en_base(interface: Contexte, base_vide: Connexion, datatable: list[list[str]]) -> None:
	"""Les sonores dont le fichier est dans le répertoire du scénario, par emplacement ; la durée à la seconde."""
	entetes, *rangees = datatable
	attendus = [dict(zip(entetes, (interface.chemin(v.strip()) for v in valeurs), strict=True)) for valeurs in rangees]
	lus = base_vide.execute(
		"SELECT emplacement, type::text, etat::text, artiste, titre, duree FROM sonores"
		" WHERE emplacement LIKE %s || '/%%' ORDER BY emplacement",
		(str(interface.repertoire),),
	).fetchall()
	trouves = []
	for emplacement, type_sonore, etat, artiste, titre, duree in lus:
		if isinstance(duree, timedelta):
			duree = timedelta(seconds=round(duree.total_seconds()))
		valeurs = (emplacement, type_sonore, etat, artiste, titre, duree)
		trouves.append(dict(zip([entete.strip() for entete in entetes], (str(v) for v in valeurs), strict=True)))
	assert trouves == sorted(attendus, key=lambda ligne: ligne["emplacement"])


@then(parsers.parse("seule la liste « {titre} » propose « ➕ Ajouter des fichiers… » et accepte les dépôts"))
def seule_liste(interface: Contexte, titre: str) -> None:
	onglets = fenetre(interface).ui.onglets
	avec = []
	for indice in range(onglets.count()):
		ouverte = onglets.widget(indice)
		if isinstance(ouverte, Liste):
			bouton = ouverte.ui.ajouter_fichiers
			if (not bouton.isHidden()) or (ouverte.table.acceptDrops()):
				assert (bouton.text(), ouverte.table.acceptDrops()) == ("➕ Ajouter des fichiers…", True)
				avec.append(onglets.tabText(indice))
	assert avec == [titre]
