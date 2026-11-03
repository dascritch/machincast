"""Étapes des scénarios des rôles PostgreSQL (https://github.com/dascritch/machincast/issues/4)."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

import psycopg
import pytest
from psycopg import sql
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, annuler_migrations, connecter, url_yoyo
from tests.base_test import commande_d_autorisation, parametres_base_test

scenarios("roles.feature")

Connexion = psycopg.Connection[tuple[object, ...]]

# Une requête par table et par opération. Les clauses WHERE false suffisent : PostgreSQL vérifie
# les droits avant d'exécuter, même quand aucune ligne n'est concernée.
INSERTIONS: dict[str, str] = {
	"sounds": "INSERT INTO sounds (type, location) VALUES ('file', '/essai/insertion.flac')",
	"feeds": "INSERT INTO feeds (name, url) VALUES ('Essai', 'https://flux.exemple/essai')",
	"banks": "INSERT INTO banks (internal_name, mode) VALUES ('Essai', 'random')",
	"bank_directories": "INSERT INTO bank_directories (bank_id, directory) VALUES ({banque}, '/essai')",
	"bank_sounds": "INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES ({banque}, {sonore}, 1)",
	"events": "INSERT INTO events (internal_name, priority) VALUES ('Essai', 'background_programming')",
	"event_items": ("INSERT INTO event_items (event_id, position, sound_id) VALUES ({evenement}, 1, {sonore})"),
	"event_skips": "INSERT INTO event_skips (event_id, day) VALUES ({evenement}, '2026-10-21')",
	"sequences": "INSERT INTO sequences (internal_name) VALUES ('Essai')",
	"sequence_items": ("INSERT INTO sequence_items (sequence_id, position, sound_id) VALUES ({sequence}, 1, {sonore})"),
	"airplay": "INSERT INTO airplay (play_id, line_type) VALUES (gen_random_uuid(), 'start')",
	"log": "INSERT INTO log (level, kind) VALUES ('info', 'essai')",
}
MODIFICATIONS: dict[str, str] = {
	"sounds": "title = NULL",
	"feeds": "url = 'https://flux.exemple/autre'",
	"banks": "hide_metadata = NULL",
	"bank_directories": "directory = '/autre'",
	"bank_sounds": "position = 2",
	"events": "public_name = NULL",
	"event_items": "position = 2",
	"event_skips": "day = '2026-10-22'",
	"sequences": "public_name = NULL",
	"sequence_items": "position = 2",
	"airplay": "title = NULL",
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
	r["banque"] = inserer(contexte, "INSERT INTO banks (internal_name, mode) VALUES ('Jingles', 'random')")
	r["sonore"] = inserer(
		contexte, "INSERT INTO sounds (type, location, title) VALUES ('file', '/reference.flac', 'Référence')"
	)
	r["evenement"] = inserer(
		contexte, "INSERT INTO events (internal_name, priority) VALUES ('Fil', 'background_programming')"
	)
	r["sequence"] = inserer(contexte, "INSERT INTO sequences (internal_name) VALUES ('Passage publicitaire')")


@given("un passage du sonore de référence dans l'airplay")
def passage(contexte: Contexte) -> None:
	contexte.connexion.execute(
		"INSERT INTO airplay (play_id, line_type, sound_id, title) "
		"VALUES (gen_random_uuid(), 'start', %s, 'Référence')",
		(contexte.references["sonore"],),
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse('le rôle "{role}" enregistre le début et la fin d\'un passage, puis une entrée de log'))
def passage_complet(contexte: Contexte, role: str) -> None:
	with en_tant_que(contexte.connexion, role, valider=True):
		c = contexte.connexion
		c.execute(
			"INSERT INTO airplay (play_id, line_type, sound_id, title) "
			"VALUES ('7f0c1c2e-5d39-4a87-9a52-0c3c8c1f9a01', 'start', %s, 'Référence')",
			(contexte.references["sonore"],),
		)
		c.execute(
			"INSERT INTO airplay (play_id, line_type, sound_id, played_duration, without_incident) "
			"VALUES ('7f0c1c2e-5d39-4a87-9a52-0c3c8c1f9a01', 'end', %s, '3 min', true)",
			(contexte.references["sonore"],),
		)
		c.execute("INSERT INTO log (level, kind, message) VALUES ('info', 'passage', 'Référence')")


@when(parsers.parse('le rôle "{role}" supprime le sonore de référence'))
def supprimer(contexte: Contexte, role: str) -> None:
	with en_tant_que(contexte.connexion, role, valider=True):
		contexte.connexion.execute("DELETE FROM sounds WHERE id = %s", (contexte.references["sonore"],))


@when(parsers.parse('je me connecte à la base de test avec le rôle "{role}"'), target_fixture="role_courant")
def se_connecter(role: str) -> str:
	socket, base_test = parametres_base_test()
	with connecter(socket, base_test, Role(role)) as connexion:
		ligne = connexion.execute("SELECT current_user").fetchone()
		assert ligne is not None
		return str(ligne[0])


@when("j'annule toutes les migrations")
def annuler_migrations_droits() -> None:
	# Les rôles appartiennent au serveur : l'annulation retire les droits, pas les rôles. base_vide réapplique ensuite.
	annuler_migrations(url_yoyo(*parametres_base_test()))


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
	requete = f"UPDATE sounds SET {colonne} = {colonne} WHERE false"
	assert autorise(contexte, role, requete) is (verdict == "peut")


@then("les deux lignes d'airplay et l'entrée de log sont en base")
def passage_enregistre(contexte: Contexte) -> None:
	lignes = contexte.connexion.execute("SELECT line_type::text FROM airplay ORDER BY id").fetchall()
	assert [ligne[0] for ligne in lignes] == ["start", "end"]
	log = contexte.connexion.execute("SELECT kind FROM log").fetchall()
	assert log == [("passage",)]


@then("la ligne d'airplay existe toujours, sans référence au sonore")
def airplay_conserve(contexte: Contexte) -> None:
	lignes = contexte.connexion.execute("SELECT sound_id, title FROM airplay").fetchall()
	assert lignes == [(None, "Référence")]


@then(parsers.parse('la connexion agit en tant que "{role}"'))
def agit_en_tant_que(role_courant: str, role: str) -> None:
	assert role_courant == role


@then("les trois rôles existent toujours")
def roles_existent(contexte: Contexte) -> None:
	lignes = contexte.connexion.execute(
		"SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)", ([str(r) for r in Role],)
	).fetchall()
	assert len(lignes) == 3


@then("le compte courant peut endosser chacun des trois rôles, sans en hériter les droits")
def compte_courant(contexte: Contexte) -> None:
	lignes = contexte.connexion.execute(
		"SELECT r.rolname, m.inherit_option, m.set_option FROM pg_auth_members m"
		" JOIN pg_roles r ON r.oid = m.roleid WHERE m.member = (SELECT oid FROM pg_roles WHERE rolname = current_user)"
		" AND r.rolname = ANY(%s)",
		([str(role) for role in Role],),
	).fetchall()
	compte = contexte.connexion.execute(
		"SELECT current_user, rolsuper FROM pg_roles WHERE rolname = current_user"
	).fetchone()
	assert compte is not None
	nom, superutilisateur = compte
	explication = (
		f"le compte {nom} n'a aucune autorisation sur les rôles de MachinCast : {commande_d_autorisation(str(nom))}"
	)
	if superutilisateur:
		# Un superutilisateur endosse tous les rôles sans autorisation : les autres scénarios passent, celui-ci non.
		explication = (
			f"le compte {nom} est superutilisateur de PostgreSQL, et endosse les rôles sans autorisation ;"
			f" l'installation voulue ne lui donne aucun droit particulier sur le serveur (doc/fr/regles/tests.md,"
			f" Base de test). Lancer :"
			f" {commande_d_autorisation(str(nom))}, puis sudo -u postgres psql -c 'ALTER ROLE \"{nom}\" NOSUPERUSER'"
		)
	assert lignes != [], explication
	# Aucune autorisation n'hérite des droits, et chaque rôle peut être endossé par au moins l'une d'elles.
	assert not any(heritage for _, heritage, _ in lignes), lignes
	assert {str(nom) for nom, _, endossable in lignes if endossable} == {str(role) for role in Role}, lignes
