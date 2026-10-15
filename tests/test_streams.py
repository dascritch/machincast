"""Étapes de la diffusion des streams (https://github.com/dascritch/machincast/issues/16).

Les étapes communes aux scénarios de la diffusion, dont le serveur de flux local (tests/flux.py), sont dans
tests/etapes_diffusion.py.
"""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.etapes_diffusion import Banc, Connexion, passages, sonore, sonores_de
from tests.flux import ServeurDeFlux
from tests.sons import TAGS_DE_TEST

scenarios("streams.feature")


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le flux « {flux} » est hors ligne"))
def flux_hors_ligne(serveur: ServeurDeFlux, flux: str) -> None:
	serveur.en_ligne[flux] = False


@given(parsers.parse("le stream « {nom} » sur le marque-page « {marque_page} » du flux « {flux} »"))
def stream_marque_page(serveur: ServeurDeFlux, base_vide: Connexion, nom: str, marque_page: str, flux: str) -> None:
	cree = base_vide.execute(
		"INSERT INTO marques_pages_streams (nom, url) VALUES (%s, %s) RETURNING id",
		(marque_page, serveur.adresse(flux)),
	).fetchone()
	assert cree is not None
	base_vide.execute("INSERT INTO sonores (type, marque_page_id, titre) VALUES ('stream', %s, %s)", (cree[0], nom))


@given(parsers.parse("le stream « {nom} » est secouru par « {secours} »"))
def stream_secouru(base_vide: Connexion, nom: str, secours: str) -> None:
	base_vide.execute(
		"UPDATE sonores SET secours_evenement_id = (SELECT id FROM evenements WHERE nom_interne = %s) WHERE id = %s",
		(secours, sonore(base_vide, nom)),
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le flux « {flux} » tombe"))
def flux_tombe(serveur: ServeurDeFlux, flux: str) -> None:
	serveur.en_ligne[flux] = False


@when(parsers.parse("le flux « {flux} » revient"))
def flux_revient(serveur: ServeurDeFlux, flux: str) -> None:
	serveur.en_ligne[flux] = True


# ─── Alors ─────────────────────────────────────────────────


def emplacements(base: Connexion, nom: str) -> list[str]:
	lignes = base.execute("SELECT DISTINCT emplacement FROM airplay WHERE titre = %s", (nom,)).fetchall()
	return [str(ligne[0]) for ligne in lignes]


@then(parsers.parse("le passage « {nom} » a pour emplacement l'adresse du flux « {flux} »"))
def emplacement_du_flux(serveur: ServeurDeFlux, base_vide: Connexion, nom: str, flux: str) -> None:
	assert emplacements(base_vide, nom) == [serveur.adresse(flux)]


@then("aucun passage ne porte l'artiste ou le titre des tags du flux")
def sans_tags_du_flux(base_vide: Connexion) -> None:
	lignes = base_vide.execute("SELECT artiste, titre FROM airplay").fetchall()
	assert lignes
	for artiste, titre in lignes:
		assert artiste is None, artiste
		assert str(titre) not in TAGS_DE_TEST, titre


@then(parsers.parse("l'airplay montre « {stream} », puis des sonores de « {evenement} », puis « {stream_fin} »"))
def remplacement(base_vide: Connexion, stream: str, evenement: str, stream_fin: str) -> None:
	noms = [p[0] for p in passages(base_vide)]
	assert len(noms) >= 3 and noms[0] == stream and noms[-1] == stream_fin, noms
	assert set(noms[1:-1]) <= sonores_de(base_vide, evenement), noms


@then(parsers.parse("le premier passage « {nom} » a fini en incident"))
def premier_en_incident(base_vide: Connexion, nom: str) -> None:
	premier = next(p for p in passages(base_vide) if p[0] == nom)
	assert premier[2] is not None and premier[3] is False, premier


@then(parsers.re(r"le sonore joué avant la reprise a fini (?P<quand>au début|après le début) de la reprise"))
def fin_avant_reprise(base_vide: Connexion, quand: str) -> None:
	lignes = passages(base_vide)
	reprise = lignes[-1]
	avant = lignes[-2]
	assert avant[2] is not None, avant
	if quand == "au début":
		assert avant[2] == reprise[1], (avant, reprise)
	else:
		assert avant[2] > reprise[1], (avant, reprise)


@then(parsers.parse("l'airplay montre {nombre:d} passage « {nom} »"))
def nombre_de_passages(base_vide: Connexion, nombre: int, nom: str) -> None:
	assert [p[0] for p in passages(base_vide)].count(nom) == nombre, passages(base_vide)


@then("le stream repris joue à plein volume")
def stream_a_plein_volume(banc: Banc) -> None:
	assert banc.diffusion is not None and banc.diffusion.courant is not None
	courant = banc.diffusion.courant
	assert courant.parametres.stream, courant
	assert courant.voie.volume_a(courant.voie.position()) == pytest.approx(1.0)


def lignes_du_log(base: Connexion, nature: str) -> list[tuple[int, str, str]]:
	lignes = base.execute(
		"SELECT id, niveau::text, message FROM log WHERE nature = %s ORDER BY id", (nature,)
	).fetchall()
	return [(int(str(i)), str(n), str(m)) for i, n, m in lignes]


@then(parsers.parse("le log contient {nombre:d} incident « {nature} », qui donne l'adresse du flux « {flux} »"))
def incident_du_flux(serveur: ServeurDeFlux, base_vide: Connexion, nombre: int, nature: str, flux: str) -> None:
	lignes = lignes_du_log(base_vide, nature)
	assert len(lignes) == nombre, lignes
	assert all(niveau == "incident" and serveur.adresse(flux) in message for _, niveau, message in lignes), lignes


@then(parsers.parse("l'incident « {suivante} » suit l'incident « {premiere} »"))
def ordre_des_incidents(base_vide: Connexion, suivante: str, premiere: str) -> None:
	assert lignes_du_log(base_vide, premiere)[0][0] < lignes_du_log(base_vide, suivante)[0][0]
