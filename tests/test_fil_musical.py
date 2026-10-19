"""Scénarios du fil musical garanti (https://github.com/dascritch/machincast/issues/39).

Les étapes de la fenêtre, des listes, des fiches et de la suppression sont dans tests/etapes_interface.py.
"""

from pytest_bdd import parsers, scenarios, then, when

from tests.etapes_interface import NOM, Connexion

scenarios("fil_musical.feature")


@when("la base perd son dernier fil musical")
def perdre(base_vide: Connexion) -> None:
	base_vide.execute("DELETE FROM evenements WHERE priorite = 'fil_musical'")


@then(parsers.parse("le fil musical « {nom} » est en base, permanent et sans élément"))
def permanent(base_vide: Connexion, nom: str) -> None:
	lignes = base_vide.execute(
		"SELECT e.priorite::text, e.debut, e.fin, e.jours_recurrence::text[], e.nom_public, e.masquer_metadonnees,"
		" (SELECT count(*) FROM evenements_elements x WHERE x.evenement_id = e.id) FROM evenements e"
		" WHERE e.nom_interne = %s",
		(nom,),
	).fetchall()
	assert lignes == [("fil_musical", None, None, [], None, None, 0)]


@then(parsers.re(r"les fils musicaux en base sont (?P<noms>aucun|«.+)"))
def fils(base_vide: Connexion, noms: str) -> None:
	lignes = base_vide.execute(
		"SELECT nom_interne FROM evenements WHERE priorite = 'fil_musical' ORDER BY nom_interne"
	).fetchall()
	assert [str(nom) for (nom,) in lignes] == NOM.findall(noms)
