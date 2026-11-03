"""Étapes des captures d'écran du guide utilisateur (https://github.com/dascritch/machincast/issues/128)."""

import re
from pathlib import Path

import psycopg
import pytest
from PySide6.QtGui import QImage
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from tests import screenshots

scenarios("screenshots.feature")

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS = ROOT / "doc" / "fr" / "captures"
GUIDE = ROOT / "doc" / "fr" / "utilisateur"
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
MINIMAL_COLOURS = 20
"""Couleurs distinctes, au moins, d'une capture qui montre un écran, sur un échantillon de ses pixels."""

Connection = psycopg.Connection[tuple[object, ...]]


def produced_list() -> set[str]:
	return {f"{name}.png" for name in screenshots.SCREENSHOTS}


def cited_list() -> dict[Path, Path]:
	"""Chaque image citée par le guide utilisateur, et la page qui la cite."""
	return {
		(page.parent / path).resolve(): page
		for page in sorted(GUIDE.glob("*.md"))
		for path in IMAGE.findall(page.read_text(encoding="utf-8"))
	}


@pytest.fixture
def products() -> dict[str, Path]:
	return {}


# ─── Quand ─────────────────────────────────────────────────


@when("je produis les captures dans un répertoire temporaire")
def produce(empty_database: Connection, qtbot: QtBot, tmp_path: Path, products: dict[str, Path]) -> None:
	"""Sur la base de test, que empty_database a migrée ; la démonstration la remplit à sa place."""
	products.update(screenshots.produce(tmp_path / "captures"))


# ─── Alors ─────────────────────────────────────────────────


@then("chaque capture de Machin dev-screenshots est une image de doc/fr/captures")
def presented_screenshot() -> None:
	missing_list = sorted(produced_list() - {image.name for image in SCREENSHOTS.glob("*")})
	assert not missing_list, f"lancer bin/Machin dev-screenshots : {missing_list}"


@then("chaque image de doc/fr/captures est une capture de Machin dev-screenshots")
def produced_image() -> None:
	orphaned = sorted({image.name for image in SCREENSHOTS.glob("*")} - produced_list())
	assert not orphaned, orphaned


@then("chaque capture de Machin dev-screenshots est citée par le guide utilisateur")
def cited_screenshot() -> None:
	absent_list = sorted(name for name in produced_list() if (SCREENSHOTS / name).resolve() not in cited_list())
	assert not absent_list, absent_list


@then("chaque image citée par le guide utilisateur est dans doc/fr/captures")
def cited_in_screenshots() -> None:
	elsewhere = sorted(f"{page.name} : {image}" for image, page in cited_list().items() if image.parent != SCREENSHOTS)
	assert not elsewhere, elsewhere


@then("le répertoire contient une image PNG par capture, et rien d'autre")
def a_by_screenshot(tmp_path: Path, products: dict[str, Path]) -> None:
	assert sorted(image.name for image in (tmp_path / "captures").iterdir()) == sorted(produced_list())
	assert sorted(products) == sorted(screenshots.SCREENSHOTS)


@then(parsers.parse("la capture « {name} » fait {width:d} × {height:d} pixels"))
def size(products: dict[str, Path], name: str, width: int, height: int) -> None:
	image = QImage(str(products[name]))
	assert (image.width(), image.height()) == (width, height)


@then("aucune capture n'est d'une couleur unie")
def not_united(products: dict[str, Path]) -> None:
	for name, path in products.items():
		image = QImage(str(path))
		colours = {image.pixel(x, y) for x in range(0, image.width(), 7) for y in range(0, image.height(), 7)}
		assert len(colours) >= MINIMAL_COLOURS, f"{name} : {len(colours)} couleurs"
