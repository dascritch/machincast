"""Scénarios de la réactivité et de la stabilité de l'interface (https://github.com/dascritch/machincast/issues/305).

Les étapes de la fenêtre, de ses onglets et de ses fiches sont dans tests/etapes_interface.py.
"""

import gc
import weakref
from collections.abc import Callable
from types import SimpleNamespace

import psycopg
import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.interface.fiche_banque import FicheBanque
from tests.etapes_interface import Connexion, Contexte, fenetre, fiche_ouverte, identifiant

scenarios("stabilite_interface.feature")


@pytest.fixture
def lectures() -> SimpleNamespace:
	return SimpleNamespace(nombre=0, fiches=[])


@given(parsers.parse("la banque « {nom} », de {nombre:d} sonores"))
def grosse_banque(base_vide: Connexion, nom: str, nombre: int) -> None:
	base_vide.execute("INSERT INTO banques (nom_interne, mode) VALUES (%s, 'aleatoire')", (nom,))
	banque = identifiant(base_vide, "banques", "nom_interne", nom)
	base_vide.execute(
		"INSERT INTO sonores (type, emplacement, titre, artiste, duree) SELECT 'fichier', '/srv/m/' || i || '.flac',"
		" 'Titre ' || i, 'Artiste ' || i, '200 s' FROM generate_series(1, %s) i",
		(nombre,),
	)
	base_vide.execute(
		"INSERT INTO banques_sonores (banque_id, sonore_id, position)"
		" SELECT %s, id, row_number() OVER (ORDER BY id) FROM sonores",
		(banque,),
	)


@given("les lectures des fiches de banque sont comptées")
def compter(lectures: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
	lire: Callable[[FicheBanque], None] = FicheBanque._lire

	def comptee(fiche: FicheBanque) -> None:
		lectures.nombre += 1
		lire(fiche)

	monkeypatch.setattr(FicheBanque, "_lire", comptee)


@when(parsers.parse("j'ouvre puis ferme {fois:d} fois la fiche de la banque « {nom} »"))
def ouvrir_fermer(interface: Contexte, base_vide: Connexion, lectures: SimpleNamespace, fois: int, nom: str) -> None:
	principale = fenetre(interface)
	banque = identifiant(base_vide, "banques", "nom_interne", nom)
	for _ in range(fois):
		principale._ouvrir("banque", banque, nom)
		ouverte = fiche_ouverte(interface)
		lectures.fiches.append(weakref.ref(ouverte))
		principale._fermer(principale.ui.onglets.indexOf(ouverte))
		del ouverte
		QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
		QApplication.processEvents()
	gc.collect()


@then(parsers.parse("la fiche de la banque a été lue {nombre:d} fois"))
def lue(lectures: SimpleNamespace, nombre: int) -> None:
	assert lectures.nombre == nombre


@then(parsers.parse("la fiche montre {nombre:d} sonores"))
def sonores_montres(interface: Contexte, nombre: int) -> None:
	fiche = fiche_ouverte(interface)
	assert isinstance(fiche, FicheBanque)
	assert fiche.ui.sonores.topLevelItemCount() == nombre


@then("aucune des fiches fermées ne survit")
def liberees(lectures: SimpleNamespace) -> None:
	assert lectures.fiches != []
	assert [reference for reference in lectures.fiches if reference() is not None] == []


@then("psycopg n'utilise pas son implémentation en Python")
def psycopg_compile() -> None:
	assert psycopg.pq.__impl__ in ("binary", "c"), psycopg.pq.__impl__
