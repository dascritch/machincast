"""Étapes des scénarios de vérification de l'installation (https://github.com/dascritch/machincast/issues/40)."""

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import gi
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.audio import Greffon
from machincast.configuration import SortieAudio
from machincast.installation import Manque, verifier_decodeurs, verifier_sortie, verifier_streams
from tests.base_test import chemin_configuration_test, configuration_test

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

scenarios("installation.feature")

LECTEURS = Gst.ELEMENT_FACTORY_TYPE_DECODER | Gst.ELEMENT_FACTORY_TYPE_DEMUXER | Gst.ELEMENT_FACTORY_TYPE_PARSER


@given(parsers.parse("les éléments GStreamer qui lisent « {caps} » désactivés"))
def elements_desactives(caps: str) -> Iterator[None]:
	"""Simule un paquet absent : decodebin, comme la vérification, ignore les éléments de rang NONE."""
	Gst.init(None)
	capacites = Gst.Caps.from_string(caps)
	assert capacites is not None
	fabriques = [
		f for f in Gst.ElementFactory.list_get_elements(LECTEURS, Gst.Rank.MARGINAL) if f.can_sink_any_caps(capacites)
	]
	assert fabriques, f"aucun élément ne lit {caps}"
	rangs = [(fabrique, fabrique.get_rank()) for fabrique in fabriques]
	for fabrique in fabriques:
		fabrique.set_rank(Gst.Rank.NONE)
	yield
	for fabrique, rang in rangs:
		fabrique.set_rank(rang)


@given(parsers.parse("les sources GStreamer du protocole « {protocole} » désactivées"))
def sources_desactivees(protocole: str) -> Iterator[None]:
	Gst.init(None)
	fabriques = [
		f
		for f in Gst.ElementFactory.list_get_elements(Gst.ELEMENT_FACTORY_TYPE_SRC, Gst.Rank.MARGINAL)
		if (f.get_uri_type() == Gst.URIType.SRC) and (protocole in ((f.get_uri_protocols()) or ([])))
	]
	assert fabriques, f"aucune source pour {protocole}"
	rangs = [(fabrique, fabrique.get_rank()) for fabrique in fabriques]
	for fabrique in fabriques:
		fabrique.set_rank(Gst.Rank.NONE)
	yield
	for fabrique, rang in rangs:
		fabrique.set_rank(rang)


@when("je vérifie la source des streams", target_fixture="manques")
def streams() -> list[Manque]:
	return verifier_streams()


@then("aucun protocole de stream ne manque de source")
def aucune_source_manquante(manques: list[Manque]) -> None:
	assert manques == [], manques


@when("je vérifie les décodeurs GStreamer", target_fixture="manques")
def decodeurs() -> list[Manque]:
	return verifier_decodeurs()


@then("aucun format sonore ne manque de décodeur")
def aucun_manque(manques: list[Manque]) -> None:
	assert manques == [], manques


@then(parsers.parse("le format {format_sonore} manque, avec le paquet « {paquet} »"))
def format_manquant(manques: list[Manque], format_sonore: str, paquet: str) -> None:
	assert Manque(format_sonore, paquet) in manques, manques


@when("je vérifie la sortie audio de la configuration de test", target_fixture="manques")
def sortie_de_test() -> list[Manque]:
	return verifier_sortie(configuration_test())


@when("je vérifie une sortie audio dont le greffon GStreamer n'existe pas", target_fixture="manques")
def sortie_inexistante() -> list[Manque]:
	greffons: dict[SortieAudio, Greffon] = {
		"factice": Greffon(fabrique="elementinexistant", propriete=None, paquet="gstreamer1.0-inexistant")
	}
	return verifier_sortie(configuration_test(), greffons)


@then("la sortie audio est disponible")
def sortie_disponible(manques: list[Manque]) -> None:
	assert manques == [], manques


@then(parsers.parse("la sortie audio manque, avec le paquet « {paquet} »"))
def sortie_manquante(manques: list[Manque], paquet: str) -> None:
	assert [manque.paquet for manque in manques] == [paquet], manques


def lancer(action: str, configuration: Path) -> subprocess.CompletedProcess[str]:
	return subprocess.run(
		[sys.executable, "-m", "machincast.installation", action, "--config", str(configuration)],
		capture_output=True,
		text=True,
		timeout=60,
	)


@when(
	parsers.parse("je lance « python -m machincast.installation {action} » avec la configuration de test"),
	target_fixture="commande",
)
def lancer_avec_configuration_de_test(action: str) -> subprocess.CompletedProcess[str]:
	return lancer(action, chemin_configuration_test())


@when(
	parsers.parse(
		"je lance « python -m machincast.installation {action} » avec une configuration dont la socket n'existe pas"
	),
	target_fixture="commande",
)
def lancer_sans_base(tmp_path: Path, action: str) -> subprocess.CompletedProcess[str]:
	# Une configuration jetable, dans le répertoire temporaire du scénario, qui ne peut joindre aucune base.
	configuration = tmp_path / "sans-base.toml"
	texte = chemin_configuration_test().read_text(encoding="utf-8")
	configuration.write_text(
		texte.replace('socket = "/var/run/postgresql"', f'socket = "{tmp_path / "aucune-socket"}"'), encoding="utf-8"
	)
	return lancer(action, configuration)


@then("la commande se termine sans erreur")
def sans_erreur(commande: subprocess.CompletedProcess[str]) -> None:
	assert commande.returncode == 0, commande.stderr


@then(parsers.parse("la commande se termine avec le code {code:d}"))
def code(commande: subprocess.CompletedProcess[str], code: int) -> None:
	assert commande.returncode == code, commande.stderr


@then("elle affiche la socket, la base de production puis la base de test de cette configuration")
def parametres(commande: subprocess.CompletedProcess[str]) -> None:
	base = configuration_test().base
	assert commande.stdout.splitlines() == [str(base.socket), base.production, base.test]


@then(parsers.parse("sa sortie annonce « {texte} »"))
def sortie_annonce(commande: subprocess.CompletedProcess[str], texte: str) -> None:
	assert texte in commande.stdout, commande.stdout + commande.stderr


@then(parsers.parse("sa sortie d'erreur mentionne « {texte} »"))
def erreur_mentionne(commande: subprocess.CompletedProcess[str], texte: str) -> None:
	assert texte in commande.stderr, commande.stderr


@pytest.fixture(autouse=True)
def gstreamer() -> None:
	Gst.init(None)
