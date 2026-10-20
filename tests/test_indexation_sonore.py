"""Scénarios de l'indexation d'un seul sonore (https://github.com/dascritch/machincast/issues/181).

Les étapes des fichiers, des sonores et de l'autre indexation sont dans tests/etapes_indexation.py.
"""

import argparse
import dataclasses
import logging
from datetime import datetime
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import parsers, scenarios, then, when

from machincast.indexation.__main__ import executer
from tests.base_test import configuration_test
from tests.etapes_indexation import maintenant_en_base, verifie_le

scenarios("indexation_sonore.feature")

Connexion = psycopg.Connection[tuple[object, ...]]


@dataclasses.dataclass
class Lancement:
	code: int
	messages: list[str]
	debut: datetime
	fin: datetime


def lancer(
	base: Connexion, caplog: pytest.LogCaptureFixture, sonore: int, audit_complet: bool = True, fenetre: bool = False
) -> Lancement:
	"""L'action de Machin indexation, avec une configuration dont la base de production est la base de test."""
	configuration = configuration_test()
	sur_la_base_de_test = dataclasses.replace(
		configuration, base=dataclasses.replace(configuration.base, production=configuration.base.test)
	)
	caplog.clear()
	debut = maintenant_en_base(base)
	with caplog.at_level(logging.INFO, logger="machincast"):
		options = argparse.Namespace(audit_complet=audit_complet, fenetre=fenetre, sonore=sonore)
		code = executer(sur_la_base_de_test, options)
	messages = [enregistrement.getMessage() for enregistrement in caplog.records]
	return Lancement(code, messages, debut, maintenant_en_base(base))


@when(
	"Machin indexation est lancé sur la base de test, en audit complet, pour ce sonore seulement",
	target_fixture="lancement",
)
def pour_ce_sonore(base_vide: Connexion, caplog: pytest.LogCaptureFixture, sonore: int) -> Lancement:
	return lancer(base_vide, caplog, sonore)


@when(
	parsers.parse("Machin indexation est lancé sur la base de test, en audit complet, pour le sonore {numero:d}"),
	target_fixture="lancement",
)
def pour_le_sonore(base_vide: Connexion, caplog: pytest.LogCaptureFixture, numero: int) -> Lancement:
	return lancer(base_vide, caplog, numero)


@when("Machin indexation est lancé sur la base de test, en audit complet, pour ce stream", target_fixture="lancement")
def pour_ce_stream(base_vide: Connexion, caplog: pytest.LogCaptureFixture, stream: tuple[int, object]) -> Lancement:
	return lancer(base_vide, caplog, stream[0])


@when("Machin indexation est lancé avec --fenetre et --sonore 1", target_fixture="lancement")
def avec_la_fenetre(base_vide: Connexion, caplog: pytest.LogCaptureFixture) -> Lancement:
	return lancer(base_vide, caplog, 1, audit_complet=False, fenetre=True)


@then(parsers.parse("Machin indexation se termine avec le code {code:d}"))
def termine(lancement: Lancement, code: int) -> None:
	assert lancement.code == code, lancement.messages


@then(parsers.parse("Machin indexation se termine avec le code {code:d}, en signalant « {texte} »"))
def termine_en_signalant(lancement: Lancement, code: int, texte: str) -> None:
	assert (lancement.code, texte in lancement.messages) == (code, True), lancement.messages


@then("Machin indexation refuse ce stream, qui n'est pas un fichier")
def refuse_le_stream(lancement: Lancement, stream: tuple[int, object]) -> None:
	assert lancement.code == 1
	assert f"sonore {stream[0]} : inconnu, ou pas un fichier" in lancement.messages, lancement.messages


@then("la date de vérification complète du sonore est celle de ce lancement")
def verifie_pendant_le_lancement(base_vide: Connexion, sonore: int, lancement: Lancement) -> None:
	date = verifie_le(base_vide, sonore)
	assert isinstance(date, datetime)
	assert lancement.debut <= date <= lancement.fin


@then("le deuxième sonore n'a pas de date de vérification complète")
def deuxieme_pas_verifie(base_vide: Connexion, sonore: int) -> None:
	ligne = base_vide.execute("SELECT verifie_le FROM sonores WHERE id <> %s", (sonore,)).fetchone()
	assert ligne == (None,)


@then("aucun document d'audit n'est écrit")
def sans_document(repertoire_d_audit: Path) -> None:
	assert list(repertoire_d_audit.iterdir()) == []
