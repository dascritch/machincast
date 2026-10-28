"""Scénarios de l'audit complet optimisé (https://github.com/dascritch/machincast/issues/206).

Les étapes des fichiers, des sonores et de l'indexeur sont dans tests/etapes_indexation.py.
"""

import logging
from datetime import datetime

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.indexation.__main__ import main
from tests.base_test import chemin_configuration_test
from tests.etapes_indexation import DECIMAL, Execution, indexer, nombre

scenarios("audit_optimise.feature")

Connexion = psycopg.Connection[tuple[object, ...]]


def _audit(base: Connexion, sonore: int) -> tuple[object, object]:
	ligne = base.execute("SELECT audite_le, audit_seuil FROM sonores WHERE id = %s", (sonore,)).fetchone()
	assert ligne is not None
	return ligne[0], ligne[1]


@given("l'indexeur a fait un audit complet")
def audit_prealable(
	base_vide: Connexion,
	caplog: pytest.LogCaptureFixture,
	indexations: list[tuple[datetime, datetime]],
	seuil_silences: list[float],
) -> None:
	indexer(base_vide, caplog, audit_complet=True, indexations=indexations, seuil_silences=seuil_silences)


@when("l'indexeur fait un audit complet forcé", target_fixture="execution")
def audit_force(
	base_vide: Connexion,
	caplog: pytest.LogCaptureFixture,
	indexations: list[tuple[datetime, datetime]],
	seuil_silences: list[float],
) -> Execution:
	return indexer(
		base_vide, caplog, audit_complet=True, indexations=indexations, seuil_silences=seuil_silences, forcer=True
	)


@given("un audit complet demandé pour ce sonore")
def demander(base_vide: Connexion, sonore: int) -> None:
	base_vide.execute("UPDATE sonores SET audit_demande = true WHERE id = %s", (sonore,))


@then("ce sonore n'a plus d'audit complet demandé")
def plus_demande(base_vide: Connexion, sonore: int) -> None:
	ligne = base_vide.execute("SELECT audit_demande FROM sonores WHERE id = %s", (sonore,)).fetchone()
	assert ligne == (False,), ligne


@then(
	parsers.re(
		rf"le sonore a été audité au seuil de (?P<seuil>-?{DECIMAL}) dB,"
		r" pendant (?P<quand>cette indexation|l'indexation précédente)"
	)
)
def audite(
	base_vide: Connexion, sonore: int, indexations: list[tuple[datetime, datetime]], seuil: str, quand: str
) -> None:
	debut, fin = indexations[-1 if quand == "cette indexation" else -2]
	date, seuil_de_l_audit = _audit(base_vide, sonore)
	assert isinstance(date, datetime), date
	assert debut <= date <= fin, (debut, date, fin)
	assert seuil_de_l_audit == nombre(seuil), seuil_de_l_audit


@then("le sonore n'a jamais été audité")
def jamais_audite(base_vide: Connexion, sonore: int) -> None:
	assert _audit(base_vide, sonore) == (None, None)


@then(parsers.parse("la sortie standard annonce « {texte} »"))
def annonce(execution: Execution, texte: str) -> None:
	assert texte in execution.informations, execution.informations


@when(parsers.parse("je lance Machin indexation avec les options « {options} »"), target_fixture="lancement")
def lancer(caplog: pytest.LogCaptureFixture, options: str) -> tuple[int, list[str]]:
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"):
		code = main(["--config", str(chemin_configuration_test()), *options.split()])
	return code, [enregistrement.getMessage() for enregistrement in caplog.records]
