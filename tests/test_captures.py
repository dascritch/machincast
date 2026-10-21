"""Étapes des captures d'écran du guide utilisateur (https://github.com/dascritch/machincast/issues/128)."""

import re
from pathlib import Path

import psycopg
import pytest
from PySide6.QtGui import QImage
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from tests import captures

scenarios("captures.feature")

RACINE = Path(__file__).resolve().parents[1]
CAPTURES = RACINE / "doc" / "captures"
GUIDE = RACINE / "doc" / "utilisateur"
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
COULEURS_MINIMALES = 20
"""Couleurs distinctes, au moins, d'une capture qui montre un écran, sur un échantillon de ses pixels."""

Connexion = psycopg.Connection[tuple[object, ...]]


def produites() -> set[str]:
	return {f"{nom}.png" for nom in captures.CAPTURES}


def citees() -> dict[Path, Path]:
	"""Chaque image citée par le guide utilisateur, et la page qui la cite."""
	return {
		(page.parent / chemin).resolve(): page
		for page in sorted(GUIDE.glob("*.md"))
		for chemin in IMAGE.findall(page.read_text(encoding="utf-8"))
	}


@pytest.fixture
def produits() -> dict[str, Path]:
	return {}


# ─── Quand ─────────────────────────────────────────────────


@when("je produis les captures dans un répertoire temporaire")
def produire(base_vide: Connexion, qtbot: QtBot, tmp_path: Path, produits: dict[str, Path]) -> None:
	"""Sur la base de test, que base_vide a migrée ; la démonstration la remplit à sa place."""
	produits.update(captures.produire(tmp_path / "captures"))


# ─── Alors ─────────────────────────────────────────────────


@then("chaque capture de Machin dev-captures est une image de doc/captures")
def capture_presente() -> None:
	manquantes = sorted(produites() - {image.name for image in CAPTURES.glob("*")})
	assert not manquantes, f"lancer bin/Machin dev-captures : {manquantes}"


@then("chaque image de doc/captures est une capture de Machin dev-captures")
def image_produite() -> None:
	orphelines = sorted({image.name for image in CAPTURES.glob("*")} - produites())
	assert not orphelines, orphelines


@then("chaque capture de Machin dev-captures est citée par le guide utilisateur")
def capture_citee() -> None:
	absentes = sorted(nom for nom in produites() if (CAPTURES / nom).resolve() not in citees())
	assert not absentes, absentes


@then("chaque image citée par le guide utilisateur est dans doc/captures")
def citee_dans_captures() -> None:
	ailleurs = sorted(f"{page.name} : {image}" for image, page in citees().items() if image.parent != CAPTURES)
	assert not ailleurs, ailleurs


@then("le répertoire contient une image PNG par capture, et rien d'autre")
def une_par_capture(tmp_path: Path, produits: dict[str, Path]) -> None:
	assert sorted(image.name for image in (tmp_path / "captures").iterdir()) == sorted(produites())
	assert sorted(produits) == sorted(captures.CAPTURES)


@then(parsers.parse("la capture « {nom} » fait {largeur:d} × {hauteur:d} pixels"))
def taille(produits: dict[str, Path], nom: str, largeur: int, hauteur: int) -> None:
	image = QImage(str(produits[nom]))
	assert (image.width(), image.height()) == (largeur, hauteur)


@then("aucune capture n'est d'une couleur unie")
def pas_unie(produits: dict[str, Path]) -> None:
	for nom, chemin in produits.items():
		image = QImage(str(chemin))
		couleurs = {image.pixel(x, y) for x in range(0, image.width(), 7) for y in range(0, image.height(), 7)}
		assert len(couleurs) >= COULEURS_MINIMALES, f"{nom} : {len(couleurs)} couleurs"
