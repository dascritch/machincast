"""Étapes des scénarios des rôles PostgreSQL (https://github.com/dascritch/machincast/issues/4)."""

import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

import psycopg
import pytest
from psycopg import sql
from pytest_bdd import given, parsers, scenarios, then, when
from yoyo import get_backend, read_migrations

from machincast.base import REPERTOIRE_MIGRATIONS, Role, autoriser_utilisateur, connecter, url_yoyo
from tests.base_test import parametres_base_test

scenarios("roles.feature")

Connexion = psycopg.Connection[tuple[object, ...]]

# Une requête par table et par opération. Les clauses WHERE false suffisent : PostgreSQL vérifie
# les droits avant d'exécuter, même quand aucune ligne n'est concernée.
INSERTIONS: dict[str, str] = {
	"sonores": "INSERT INTO sonores (type, emplacement) VALUES ('fichier', '/essai/insertion.flac')",
	"marques_pages_streams": "INSERT INTO marques_pages_streams (nom, url) VALUES ('Essai', 'https://flux.exemple/essai')",
	"banques": "INSERT INTO banques (nom_interne, mode) VALUES ('Essai', 'aleatoire')",
	"banques_repertoires": "INSERT INTO banques_repertoires (banque_id, repertoire) VALUES ({banque}, '/essai')",
	"banques_sonores": "INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES ({banque}, {sonore}, 1)",
	"evenements": "INSERT INTO evenements (nom_interne, priorite) VALUES ('Essai', 'fil_musical')",
	"evenements_elements": (
		"INSERT INTO evenements_elements (evenement_id, position, sonore_id) VALUES ({evenement}, 1, {sonore})"
	),
	"airplay": "INSERT INTO airplay (passage_id, type_ligne) VALUES (gen_random_uuid(), 'debut')",
	"log": "INSERT INTO log (niveau, nature) VALUES ('info', 'essai')",
}
MODIFICATIONS: dict[str, str] = {
	"sonores": "titre = NULL",
	"marques_pages_streams": "url = 'https://flux.exemple/autre'",
	"banques": "masquer_metadonnees = NULL",
	"banques_repertoires": "repertoire = '/autre'",
	"banques_sonores": "position = 2",
	"evenements": "nom_public = NULL",
	"evenements_elements": "position = 2",
	"airplay": "titre = NULL",
	"log": "message = ''",
}


@dataclass
class Contexte:
	connexion: Connexion
	references: dict[str, int] = field(default_factory=dict)


@pytest.fixture
def contexte(base_vide: psycopg.Connection[tuple[object, ...]]) -> Contexte:
	return Contexte(connexion=base_vide)


@contextmanager
def en_tant_que(connexion: Connexion, role: str, valider: bool = False) -> Iterator[None]:
	"""Exécute un bloc dans une transaction avec le rôle donné ; annulée sauf si valider."""
	with connexion.transaction(force_rollback=not valider):
		connexion.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
		yield


def autorise(contexte: Contexte, role: str, requete: str) -> bool:
	"""Vrai si le rôle peut exécuter la requête ; faux si PostgreSQL la refuse faute de droits."""
	try:
		with en_tant_que(contexte.connexion, role):
			contexte.connexion.execute(requete.format(**contexte.references))
	except psycopg.errors.InsufficientPrivilege:
		return False
	return True


def inserer(contexte: Contexte, requete: str) -> int:
	ligne = contexte.connexion.execute(requete + " RETURNING id").fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


# ─── Étant donné ───────────────────────────────────────────


@given("une base de test migrée avec les éléments de référence")
def base(contexte: Contexte) -> None:
	"""La fixture base_vide fournit déjà une base migrée et purgée."""
	r = contexte.references
	r["banque"] = inserer(contexte, "INSERT INTO banques (nom_interne, mode) VALUES ('Jingles', 'aleatoire')")
	r["sonore"] = inserer(
		contexte, "INSERT INTO sonores (type, emplacement, titre) VALUES ('fichier', '/reference.flac', 'Référence')"
	)
	r["evenement"] = inserer(contexte, "INSERT INTO evenements (nom_interne, priorite) VALUES ('Fil', 'fil_musical')")


@given(parsers.parse('l\'utilisateur "{utilisateur}" autorisé à endosser les trois rôles de MachinCast'))
def utilisateur_autorise(contexte: Contexte, utilisateur: str) -> None:
	autoriser_utilisateur(contexte.connexion, utilisateur, tuple(Role))
	# L'utilisateur qui lance les tests doit aussi pouvoir endosser ces rôles, et cet utilisateur d'essai.
	courant = contexte.connexion.execute("SELECT current_user").fetchone()
	assert courant is not None
	autoriser_utilisateur(contexte.connexion, str(courant[0]), tuple(Role))
	contexte.connexion.execute(
		sql.SQL("GRANT {} TO CURRENT_USER WITH INHERIT FALSE, SET TRUE").format(sql.Identifier(utilisateur))
	)


@given("un passage du sonore de référence dans l'airplay")
def passage(contexte: Contexte) -> None:
	contexte.connexion.execute(
		"INSERT INTO airplay (passage_id, type_ligne, sonore_id, titre) "
		"VALUES (gen_random_uuid(), 'debut', %s, 'Référence')",
		(contexte.references["sonore"],),
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse('le rôle "{role}" enregistre le début et la fin d\'un passage, puis une entrée de log'))
def passage_complet(contexte: Contexte, role: str) -> None:
	with en_tant_que(contexte.connexion, role, valider=True):
		c = contexte.connexion
		c.execute(
			"INSERT INTO airplay (passage_id, type_ligne, sonore_id, titre) "
			"VALUES ('7f0c1c2e-5d39-4a87-9a52-0c3c8c1f9a01', 'debut', %s, 'Référence')",
			(contexte.references["sonore"],),
		)
		c.execute(
			"INSERT INTO airplay (passage_id, type_ligne, sonore_id, duree_diffusee, sans_incident) "
			"VALUES ('7f0c1c2e-5d39-4a87-9a52-0c3c8c1f9a01', 'fin', %s, '3 min', true)",
			(contexte.references["sonore"],),
		)
		c.execute("INSERT INTO log (niveau, nature, message) VALUES ('info', 'passage', 'Référence')")


@when(parsers.parse('le rôle "{role}" supprime le sonore de référence'))
def supprimer(contexte: Contexte, role: str) -> None:
	with en_tant_que(contexte.connexion, role, valider=True):
		contexte.connexion.execute("DELETE FROM sonores WHERE id = %s", (contexte.references["sonore"],))


@when(parsers.parse('je me connecte à la base de test avec le rôle "{role}"'), target_fixture="role_courant")
def se_connecter(role: str) -> str:
	socket, base_test = parametres_base_test()
	with connecter(socket, base_test, Role(role)) as connexion:
		ligne = connexion.execute("SELECT current_user").fetchone()
		assert ligne is not None
		return str(ligne[0])


@when("j'annule la migration des droits")
def annuler_droits() -> None:
	# Annuler une migration annule aussi les suivantes, qui peuvent en dépendre ; base_vide les réapplique ensuite.
	backend = get_backend(url_yoyo(*parametres_base_test()))
	migrations = read_migrations(str(REPERTOIRE_MIGRATIONS))
	with backend.lock():
		backend.rollback_migrations(backend.to_rollback(migrations.filter(lambda m: m.id >= "0002.droits")))


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse('le rôle "{role}" a exactement ces droits :'))
def droits(contexte: Contexte, role: str, datatable: list[list[str]]) -> None:
	ecarts = []
	for table, lire, inserer_, modifier, supprimer_ in datatable[1:]:
		requetes = {
			"lire": f"SELECT * FROM {table} LIMIT 1",
			"inserer": INSERTIONS[table],
			"modifier": f"UPDATE {table} SET {MODIFICATIONS[table]} WHERE false",
			"supprimer": f"DELETE FROM {table} WHERE false",
		}
		attendus = {"lire": lire, "inserer": inserer_, "modifier": modifier, "supprimer": supprimer_}
		for operation, requete in requetes.items():
			obtenu = "oui" if autorise(contexte, role, requete) else "non"
			if obtenu != attendus[operation]:
				ecarts.append(f"{table}.{operation} : attendu {attendus[operation]}, obtenu {obtenu}")
	assert not ecarts, f"droits de {role} :\n" + "\n".join(ecarts)


@then(parsers.parse('le rôle "{role}" {verdict} modifier la colonne "{colonne}" des sonores'))
def colonne(contexte: Contexte, role: str, verdict: str, colonne: str) -> None:
	requete = f"UPDATE sonores SET {colonne} = {colonne} WHERE false"
	assert autorise(contexte, role, requete) is (verdict == "peut")


@then("les deux lignes d'airplay et l'entrée de log sont en base")
def passage_enregistre(contexte: Contexte) -> None:
	lignes = contexte.connexion.execute("SELECT type_ligne::text FROM airplay ORDER BY id").fetchall()
	assert [ligne[0] for ligne in lignes] == ["debut", "fin"]
	log = contexte.connexion.execute("SELECT nature FROM log").fetchall()
	assert log == [("passage",)]


@then("la ligne d'airplay existe toujours, sans référence au sonore")
def airplay_conserve(contexte: Contexte) -> None:
	lignes = contexte.connexion.execute("SELECT sonore_id, titre FROM airplay").fetchall()
	assert lignes == [(None, "Référence")]


@then(parsers.parse('l\'utilisateur "{utilisateur}" ne peut pas lire les sonores sans endosser un rôle'))
def sans_heritage(contexte: Contexte, utilisateur: str) -> None:
	assert not autorise(contexte, utilisateur, "SELECT * FROM sonores LIMIT 1")


@then(parsers.parse('l\'utilisateur "{utilisateur}" peut endosser chacun des trois rôles'))
def peut_endosser(contexte: Contexte, utilisateur: str) -> None:
	lignes = contexte.connexion.execute(
		"SELECT r.rolname, m.inherit_option, m.set_option FROM pg_auth_members m "
		"JOIN pg_roles r ON r.oid = m.roleid JOIN pg_roles u ON u.oid = m.member WHERE u.rolname = %s",
		(utilisateur,),
	).fetchall()
	assert sorted(lignes) == sorted((str(role), False, True) for role in Role)


@then(parsers.parse('la connexion agit en tant que "{role}"'))
def agit_en_tant_que(role_courant: str, role: str) -> None:
	assert role_courant == role


@then("les trois rôles existent toujours")
def roles_existent(contexte: Contexte) -> None:
	lignes = contexte.connexion.execute(
		"SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)", ([str(r) for r in Role],)
	).fetchall()
	assert len(lignes) == 3


@then(parsers.parse('le rôle "{role}" ne peut plus lire les sonores'))
def ne_lit_plus(contexte: Contexte, role: str) -> None:
	assert not autorise(contexte, role, "SELECT * FROM sonores LIMIT 1")


@when(
	parsers.re(
		r'je lance « python -m machincast\.droits » pour autoriser "(?P<utilisateur>[^"]*)" '
		r'aux rôles "(?P<premier>[^"]+)" et "(?P<second>[^"]+)"'
	),
	target_fixture="resultat",
)
def lancer_droits(utilisateur: str, premier: str, second: str) -> subprocess.CompletedProcess[str]:
	socket, base_test = parametres_base_test()
	return subprocess.run(
		[sys.executable, "-m", "machincast.droits", "--socket", str(socket), "--base", base_test]
		+ ["autoriser", utilisateur, premier, second],
		capture_output=True,
		text=True,
		timeout=30,
	)


@then("la commande se termine sans erreur")
def sans_erreur(resultat: subprocess.CompletedProcess[str]) -> None:
	assert resultat.returncode == 0, resultat.stderr


@then(parsers.parse('la commande échoue en mentionnant "{texte}"'))
def echec(resultat: subprocess.CompletedProcess[str], texte: str) -> None:
	assert resultat.returncode != 0
	assert texte in resultat.stderr


@then(parsers.parse('l\'utilisateur "{utilisateur}" peut endosser les rôles "{premier}" et "{second}"'))
def peut_endosser_deux(contexte: Contexte, utilisateur: str, premier: str, second: str) -> None:
	lignes = contexte.connexion.execute(
		"SELECT r.rolname, m.inherit_option, m.set_option FROM pg_auth_members m "
		"JOIN pg_roles r ON r.oid = m.roleid JOIN pg_roles u ON u.oid = m.member WHERE u.rolname = %s",
		(utilisateur,),
	).fetchall()
	assert sorted(lignes) == sorted([(premier, False, True), (second, False, True)])
