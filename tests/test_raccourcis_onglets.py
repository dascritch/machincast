"""Scénarios des raccourcis des onglets (https://github.com/dascritch/machincast/issues/192).

Les étapes de la fenêtre et des fiches sont dans tests/etapes_interface.py.
"""

from pytest_bdd import parsers, scenarios, then

from tests.etapes_interface import NOM, Contexte, fenetre

scenarios("raccourcis_onglets.feature")


def infobulles(interface: Contexte) -> dict[str, str]:
	onglets = fenetre(interface).ui.onglets
	return {onglets.tabText(indice): onglets.tabToolTip(indice) for indice in range(onglets.count())}


@then(parsers.re(r"les onglets ont pour infobulles (?P<textes>«.+)"))
def toutes_les_infobulles(interface: Contexte, textes: str) -> None:
	assert list(infobulles(interface).values()) == NOM.findall(textes)


@then(parsers.parse("l'onglet « {titre} » a pour infobulle « {texte} »"))
def infobulle(interface: Contexte, titre: str, texte: str) -> None:
	assert infobulles(interface)[titre] == texte


@then(parsers.parse("l'onglet « {titre} » n'a pas d'infobulle"))
def sans_infobulle(interface: Contexte, titre: str) -> None:
	assert infobulles(interface)[titre] == ""
