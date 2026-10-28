"""Scénarios de la session sautée annoncée par la fiche d'un événement
(https://github.com/dascritch/machincast/issues/295).

Les étapes de la fenêtre, de ses fiches, des sessions sautées et de la socket d'état sont dans
tests/etapes_interface.py.
"""

from datetime import date, datetime

from PySide6.QtCore import QDateTime
from pytest_bdd import parsers, scenarios, then, when

from machincast.interface.fiche_evenement import ORANGE, FicheEvenement
from tests.etapes_interface import Connexion, Contexte, fiche_ouverte

scenarios("fiche_evenement_session_sautee.feature")


def fiche_d_evenement(interface: Contexte) -> FicheEvenement:
	fiche = fiche_ouverte(interface)
	assert isinstance(fiche, FicheEvenement), fiche
	return fiche


@when(parsers.parse("je règle le début de la fiche de l'événement au « {debut} »"))
def regler_le_debut(interface: Contexte, debut: str) -> None:
	instant = datetime.fromisoformat(debut).astimezone()
	fiche_d_evenement(interface).ui.debut.setDateTime(QDateTime.fromSecsSinceEpoch(int(instant.timestamp())))


@when(parsers.parse("la session du {jour} de « {nom} » est rétablie en base"))
def retablie_en_base(base_vide: Connexion, jour: str, nom: str) -> None:
	"""Comme depuis le calendrier, ou depuis une autre fiche."""
	base_vide.execute(
		"DELETE FROM evenements_sauts"
		" WHERE jour = %s AND evenement_id = (SELECT id FROM evenements WHERE nom_interne = %s)",
		(date.fromisoformat(jour), nom),
	)


@then(parsers.parse("la fiche annonce « {texte} »"))
def annonce(interface: Contexte, texte: str) -> None:
	fiche = fiche_d_evenement(interface)
	assert fiche.session_sautee.isVisibleTo(fiche)
	assert fiche.texte_de_session.text() == texte


@then("la fiche n'annonce aucune session sautée")
def aucune_annonce(interface: Contexte) -> None:
	fiche = fiche_d_evenement(interface)
	assert not fiche.session_sautee.isVisibleTo(fiche), fiche.texte_de_session.text()


@then("l'annonce est sous l'erreur de la fiche, sur un liseret orange de 4 pixels")
def sous_l_erreur(interface: Contexte) -> None:
	fiche = fiche_d_evenement(interface)
	disposition = fiche.layout()
	assert disposition is not None
	assert disposition.indexOf(fiche.session_sautee) == disposition.indexOf(fiche.erreur) + 1 == 1
	assert f"border: 4px solid {ORANGE}" in fiche.session_sautee.styleSheet()


@then(
	parsers.re(
		r"le bouton « Rétablir » de l'annonce est (?P<etat>actif|inactif)(?:, avec l'infobulle « (?P<bulle>.+) »)?$"
	)
)
def bouton_retablir(interface: Contexte, etat: str, bulle: str | None) -> None:
	bouton = fiche_d_evenement(interface).retablir_la_session
	assert bouton.isEnabled() is (etat == "actif")
	if bulle is not None:
		assert bouton.toolTip() == bulle


@then(parsers.re(r"les sessions sautées de « (?P<nom>[^»]+) » en base sont (?P<jours>aucune|«.+)"))
def sautees_en_base(base_vide: Connexion, nom: str, jours: str) -> None:
	lignes = base_vide.execute(
		"SELECT s.jour FROM evenements_sauts s JOIN evenements e ON e.id = s.evenement_id"
		" WHERE e.nom_interne = %s ORDER BY s.jour",
		(nom,),
	).fetchall()
	attendus: list[date] = []
	if jours != "aucune":
		attendus = [date.fromisoformat(jour) for jour in jours.strip("« »").split(" », « ")]
	assert [jour for (jour,) in lignes] == attendus


@then(parsers.parse("la fiche est modifiée, avec le nom interne « {nom} »"))
def modifiee_avec(interface: Contexte, nom: str) -> None:
	fiche = fiche_d_evenement(interface)
	assert fiche.modifiee
	assert fiche.ui.nom_interne.text() == nom
