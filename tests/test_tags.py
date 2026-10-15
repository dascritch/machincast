"""Étapes des scénarios de lecture des tags (https://github.com/dascritch/machincast/issues/8).

Les étapes des fichiers, des sonores en base et du passage de l'indexeur sont dans tests/etapes_indexation.py.
"""

import json
from pathlib import Path

import gi
import psycopg
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import LONGUEUR_TEXTE_COURT
from machincast.indexation.decodage import Verification
from machincast.indexation.tags import Tags, extraire
from tests.etapes_indexation import lire_tags_en_base as lire

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

scenarios("tags.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
JSON = r"(?P<objet>\{.*\})"


def liste_de_tags(texte: str) -> Gst.TagList:
	Gst.init(None)
	liste = Gst.TagList.new_from_string(texte)
	assert liste is not None, f"tags illisibles : {texte}"
	return liste


# ─── Lecture ───────────────────────────────────────────────


@given(parsers.parse("les tags « {texte} »"), target_fixture="liste")
def tags_donnes(texte: str) -> Gst.TagList:
	return liste_de_tags(texte)


@given("des tags dont l'artiste et le titre font 300 caractères", target_fixture="liste")
def tags_longs() -> Gst.TagList:
	return liste_de_tags(f'taglist, artist=(string)"{"a" * 300}", title=(string)"{"t" * 300}"')


@when("j'extrais ces tags", target_fixture="tags")
def extraire_tags(liste: Gst.TagList) -> Tags:
	return extraire(liste)


@then(parsers.parse("l'artiste lu est « {artiste} » et le titre lu « {titre} »"))
def artiste_et_titre_lus(resultat: Verification, artiste: str, titre: str) -> None:
	assert (resultat.tags.artiste, resultat.tags.titre) == (artiste, titre)


@then(parsers.re(rf"les métadonnées musicales lues sont {JSON}"))
def metadonnees_lues(resultat: Verification, objet: str) -> None:
	assert resultat.tags.metadonnees == json.loads(objet)


@then("aucun tag n'est lu")
def aucun_tag(resultat: Verification) -> None:
	assert resultat.tags == Tags(None, None, {})


@then(parsers.re(r"l'année retenue est (?P<annee>\d+|aucune)"))
def annee_retenue(tags: Tags, annee: str) -> None:
	assert tags.metadonnees.get("annee") == (None if annee == "aucune" else int(annee))


@then(parsers.re(rf"les métadonnées musicales retenues sont {JSON}"))
def metadonnees_retenues(tags: Tags, objet: str) -> None:
	assert tags.metadonnees == json.loads(objet)


@then("l'artiste et le titre retenus font 255 caractères")
def tronques(tags: Tags) -> None:
	assert tags.artiste is not None and tags.titre is not None
	assert len(tags.artiste) == len(tags.titre) == LONGUEUR_TEXTE_COURT


@then("aucun artiste ni titre n'est retenu")
def ni_artiste_ni_titre(tags: Tags) -> None:
	assert (tags.artiste, tags.titre) == (None, None)


# ─── Enregistrement en base ────────────────────────────────


def inserer(base: Connexion, fichier: Path, colonne: str, valeur: str, metadonnees: str) -> int:
	ligne = base.execute(
		f"INSERT INTO sonores (type, emplacement, {colonne}, metadonnees_musicales) VALUES ('fichier', %s, %s, %s)"
		" RETURNING id",
		(str(fichier), valeur, metadonnees),
	).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


@given(
	parsers.re(rf"pour ce fichier, un sonore d'artiste « (?P<artiste>[^»]+) » et de métadonnées {JSON}"),
	target_fixture="sonore",
)
def sonore_avec_artiste(base_vide: Connexion, fichier: Path, artiste: str, objet: str) -> int:
	return inserer(base_vide, fichier, "artiste", artiste, objet)


@given(
	parsers.re(rf"pour ce fichier, un sonore de titre « (?P<titre>[^»]+) » et de métadonnées {JSON}"),
	target_fixture="sonore",
)
def sonore_avec_titre(base_vide: Connexion, fichier: Path, titre: str, objet: str) -> int:
	return inserer(base_vide, fichier, "titre", titre, objet)


@given(parsers.parse("les champs « {premier} » et « {second} » de ce sonore édités à la main"))
def champs_edites(base_vide: Connexion, sonore: int, premier: str, second: str) -> None:
	base_vide.execute("UPDATE sonores SET champs_edites = %s WHERE id = %s", ([premier, second], sonore))


@then(parsers.re(rf"en base, les métadonnées musicales sont {JSON}"))
def metadonnees_en_base(base_vide: Connexion, sonore: int, objet: str) -> None:
	assert lire(base_vide, sonore)[2] == json.loads(objet)


@then("en base, le sonore n'a ni artiste ni titre")
def sans_artiste_ni_titre(base_vide: Connexion, sonore: int) -> None:
	assert lire(base_vide, sonore)[:2] == (None, None)


@then(parsers.parse("en base, le titre est toujours « {titre} »"))
def titre_inchange(base_vide: Connexion, sonore: int, titre: str) -> None:
	assert lire(base_vide, sonore)[1] == titre
