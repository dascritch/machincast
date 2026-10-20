"""Scénarios des périphériques de sortie du poste (https://github.com/dascritch/machincast/issues/116).

Les périphériques que voit GStreamer sont remplacés par des imitations de Gst.Device : leur type GStreamer, leur nom,
leurs propriétés et leur propriété internal-name.
"""

import dataclasses
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import audio
from machincast.configuration import Configuration
from machincast.installation import lister_peripheriques
from tests.base_test import configuration_test
from tests.etapes_interface import NOM

scenarios("peripheriques_audio.feature")


class Proprietes:
	def __init__(self, valeurs: dict[str, str]) -> None:
		self.valeurs = valeurs

	def get_string(self, cle: str) -> str | None:
		return self.valeurs.get(cle)


class AppareilImite:
	"""Ce qu'une imitation de Gst.Device doit répondre."""

	def __init__(self, type_gstreamer: str, nom: str, noeud: str, interne: str) -> None:
		self.__gtype__ = SimpleNamespace(name=type_gstreamer)
		self.nom = nom
		self.proprietes = Proprietes({"node.name": noeud} if noeud else {})
		self.interne = interne

	def get_display_name(self) -> str:
		return self.nom

	def get_properties(self) -> Proprietes:
		return self.proprietes

	def get_property(self, nom: str) -> str:
		# Comme PyGObject pour une propriété que l'objet n'a pas.
		if (nom != "internal-name") or (self.interne == ""):
			raise TypeError(f"l'objet n'a pas de propriété « {nom} »")
		return self.interne.replace("(vide)", "")


@pytest.fixture
def contexte() -> SimpleNamespace:
	return SimpleNamespace(configuration=None, liste="")


@given("les périphériques vus par GStreamer :")
def vus(monkeypatch: pytest.MonkeyPatch, datatable: list[list[str]]) -> None:
	appareils = [AppareilImite(*(cellule.strip() for cellule in rangee)) for rangee in datatable[1:]]
	monkeypatch.setattr(audio, "appareils", lambda: appareils)


@given(
	parsers.parse(
		"une configuration sur la sortie « {sortie} », avec l'antenne « {antenne} » et la pré-écoute « {preecoute} »"
	)
)
def configuration(contexte: SimpleNamespace, sortie: str, antenne: str, preecoute: str) -> None:
	source = configuration_test()
	reglee = dataclasses.replace(source.audio, sortie=sortie, peripherique=antenne, preecoute=preecoute)
	contexte.configuration = dataclasses.replace(source, audio=reglee)


@when("je liste les périphériques de la configuration")
def lister(contexte: SimpleNamespace) -> None:
	assert isinstance(contexte.configuration, Configuration)
	contexte.liste = lister_peripheriques(contexte.configuration)


@then(parsers.re(r"les périphériques de la sortie « (?P<sortie>[^»]+) » sont (?P<liste>aucun|«.+)"))
def trouves(sortie: str, liste: str) -> None:
	noms = NOM.findall(liste)
	attendus = list(zip(noms[::2], noms[1::2], strict=True))
	lus = [(p.identifiant, p.nom) for p in audio.peripheriques(sortie)]  # type: ignore[arg-type]
	assert lus == attendus


@then("la liste est :")
def liste(contexte: SimpleNamespace, docstring: str) -> None:
	assert contexte.liste == f"{docstring}\n"
