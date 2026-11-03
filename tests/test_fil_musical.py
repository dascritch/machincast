"""Scénarios du fil musical garanti (https://github.com/dascritch/machincast/issues/39).

Les étapes de la fenêtre, des listes, des fiches et de la suppression sont dans tests/etapes_interface.py.
"""

from pytest_bdd import parsers, scenarios, then, when

from tests.etapes_interface import NOM, Connexion

scenarios("fil_musical.feature")


@when("la base perd son dernier fil musical")
def perdre(base_vide: Connexion) -> None:
	base_vide.execute("DELETE FROM events WHERE priority = 'background_programming'")


@then(parsers.parse("le fil musical « {nom} » est en base, permanent et sans élément"))
def permanent(base_vide: Connexion, nom: str) -> None:
	lignes = base_vide.execute(
		"SELECT e.priority::text, e.starts_at, e.ends_at, e.recurrence_days::text[], e.public_name, e.hide_metadata,"
		" (SELECT count(*) FROM event_items x WHERE x.event_id = e.id) FROM events e"
		" WHERE e.internal_name = %s",
		(nom,),
	).fetchall()
	assert lignes == [("background_programming", None, None, [], None, None, 0)]


@then(parsers.re(r"les fils musicaux en base sont (?P<noms>aucun|«.+)"))
def fils(base_vide: Connexion, noms: str) -> None:
	lignes = base_vide.execute(
		"SELECT internal_name FROM events WHERE priority = 'background_programming' AND deleted_at IS NULL"
		" ORDER BY internal_name"
	).fetchall()
	assert [str(nom) for (nom,) in lignes] == NOM.findall(noms)
