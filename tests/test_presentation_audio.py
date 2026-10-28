"""Scénarios de la présentation des sorties au serveur audio (https://github.com/dascritch/machincast/issues/296).

Les sorties sont de vrais éléments GStreamer, créés sans être lancés : aucun serveur audio n'est joint.
"""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import parsers, scenarios, then, when

from machincast import audio
from machincast.configuration import REPERTOIRE_PROJET, SortieAudio

scenarios("presentation_audio.feature")

PROGRAMMES = {
	"Machin lecture": audio.ANTENNE,
	"la pré-écoute": audio.PREECOUTE,
	"l'essai de la sortie": audio.ESSAI,
}
CLES_D_ICONE = {"pipewiresink": "application.icon-name", "pulsesink": "application.icon_name"}


@pytest.fixture
def contexte() -> SimpleNamespace:
	return SimpleNamespace(sortie=None)


@when(parsers.parse("je crée la sortie « {sortie} » de {programme}"))
def creer(contexte: SimpleNamespace, sortie: SortieAudio, programme: str) -> None:
	contexte.sortie = audio.creer_sortie(sortie, None, presentation=PROGRAMMES[programme])


def _fabrique(element: audio.Gst.Element) -> str:
	fabrique = element.get_factory()
	assert fabrique is not None
	return str(fabrique.get_name())


@then(parsers.parse("la sortie se présente comme « {nom} », pour le flux « {flux} », avec l'icône « {icone} »"))
def presentee(contexte: SimpleNamespace, nom: str, flux: str, icone: str) -> None:
	sortie = contexte.sortie
	proprietes = sortie.get_property("stream-properties")
	assert proprietes is not None
	assert sortie.get_property("client-name") == nom
	assert proprietes.get_string("application.name") == nom
	assert proprietes.get_string("media.name") == flux
	assert proprietes.get_string(CLES_D_ICONE[_fabrique(sortie)]) == icone


@then("la sortie est créée, sans présentation")
def sans_presentation(contexte: SimpleNamespace) -> None:
	assert contexte.sortie is not None
	assert contexte.sortie.find_property("client-name") is None


@then(parsers.parse("les propriétés du client PipeWire de la sortie nomment « {nom} », avec l'icône « {icone} »"))
def client_pipewire(contexte: SimpleNamespace, nom: str, icone: str) -> None:
	proprietes = contexte.sortie.get_property("client-properties")
	assert proprietes is not None
	assert (proprietes.get_string("application.name"), proprietes.get_string("application.icon-name")) == (nom, icone)


@then("chaque appel à creer_sortie, hors des tests, passe une présentation")
def appels_presentes() -> None:
	sans = []
	for fichier in sorted((REPERTOIRE_PROJET / "src").rglob("*.py")):
		for noeud in ast.walk(ast.parse(fichier.read_text(encoding="utf-8"))):
			if (not isinstance(noeud, ast.Call)) or (ast.unparse(noeud.func).split(".")[-1] != "creer_sortie"):
				continue
			if not any(mot.arg == "presentation" for mot in noeud.keywords):
				sans.append(f"{fichier.relative_to(REPERTOIRE_PROJET)}:{noeud.lineno}")
	assert sans == []


@then(parsers.parse("install.sh installe l'icône de MachinCast en « {chemin} » du compte"))
def icone_installee(chemin: str) -> None:
	assert chemin == f"icons/hicolor/512x512/apps/{audio.ICONE}.png"
	install = (REPERTOIRE_PROJET / "install.sh").read_text(encoding="utf-8")
	assert f'ICONE_DU_THEME="${{XDG_DATA_HOME:-${{HOME}}/.local/share}}/{chemin}"' in install
	assert Path(REPERTOIRE_PROJET / "src/machincast/interface/machincast.png").is_file()
	assert 'installer_icone "${ICONE_DU_THEME}"' in install
