"""Étapes de la socket d'état du binaire lecture (https://github.com/dascritch/machincast/issues/20).

Les étapes de la diffusion viennent de tests/etapes_diffusion.py. La socket est créée dans le répertoire temporaire
du scénario.
"""

import json
import re
import socket
import stat
import threading
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.lecture.etat import SocketEtat, SocketEtatOccupee
from tests.etapes_diffusion import Banc, Connexion, creer_sonore, evenement, heure, passages, sonore

scenarios("etat.feature")

SPEC = Path(__file__).resolve().parents[1] / "doc" / "spec.md"
DELAI = 3.0


@dataclass
class Client:
	message: dict[str, Any] | None = None
	recus: list[dict[str, Any]] = field(default_factory=list)
	fil: threading.Thread | None = None


@pytest.fixture
def client() -> Client:
	return Client()


def socket_du_banc(banc: Banc) -> SocketEtat:
	assert banc.etat is not None
	return banc.etat


def connecter(banc: Banc) -> socket.socket:
	connexion = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	connexion.settimeout(DELAI)
	connexion.connect(str(socket_du_banc(banc).chemin))
	return connexion


def message(client: Client) -> dict[str, Any]:
	assert client.message is not None
	return client.message


def en_cours(client: Client) -> dict[str, Any]:
	courant = message(client)["en_cours"]
	assert isinstance(courant, dict), message(client)
	return courant


def prochain(client: Client) -> dict[str, Any]:
	suivant = message(client)["prochain"]
	assert isinstance(suivant, dict), message(client)
	return suivant


# ─── Étant donné ───────────────────────────────────────────


@given("la socket d'état dans un répertoire temporaire")
def socket_temporaire(banc: Banc, tmp_path: Path) -> None:
	banc.etat = SocketEtat(tmp_path / "run" / "machincast" / "lecture.sock")


@given(parsers.parse("la dernière lecture du sonore « {nom} » a fini en incident"))
def derniere_lecture_en_incident(base_vide: Connexion, nom: str) -> None:
	identifiant = uuid.uuid4()
	for type_ligne, fin in (("debut", ""), ("fin", ", duree_diffusee, sans_incident")):
		valeurs = ", '1 s', false" if fin else ""
		base_vide.execute(
			f"INSERT INTO airplay (passage_id, type_ligne, horodatage, sonore_id{fin})"
			f" VALUES (%s, %s, '2026-10-13 12:00', %s{valeurs})",
			(identifiant, type_ligne, sonore(base_vide, nom)),
		)


# ─── Quand ─────────────────────────────────────────────────


@when("un client lit la socket d'état")
def lire(banc: Banc, client: Client) -> None:
	with connecter(banc) as connexion, connexion.makefile("r", encoding="utf-8") as lecture:
		client.message = json.loads(lecture.readline())


@when("un client reste connecté à la socket d'état")
def rester_connecte(banc: Banc, client: Client) -> None:
	connexion = connecter(banc)
	connexion.settimeout(None)

	def recevoir() -> None:
		with connexion, connexion.makefile("r", encoding="utf-8") as lecture:
			for ligne in lecture:
				client.recus.append(json.loads(ligne))

	client.fil = threading.Thread(target=recevoir, daemon=True)
	client.fil.start()


@when("un client se connecte puis se déconnecte aussitôt")
def connexion_breve(banc: Banc) -> None:
	connecter(banc).close()


@when(parsers.parse("le sonore « {nom} » est désactivé"))
def desactiver(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = 'desactive' WHERE id = %s", (sonore(base_vide, nom),))


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le message est en version {version:d}, à l'état « {etat} »"))
def version_et_etat(client: Client, version: int, etat: str) -> None:
	assert (message(client)["version"] == version) and (message(client)["etat"] == etat), message(client)


@then(
	parsers.re(
		r"le sonore en cours est « (?P<titre>[^»]+) », un (?P<type>fichier|stream)"
		r" de l'événement « (?P<evenement>[^»]+) »"
	)
)
def sonore_en_cours(client: Client, titre: str, type: str, evenement: str) -> None:
	courant = en_cours(client)
	assert (courant["titre"], courant["type"], courant["evenement"]) == (titre, type, evenement), courant


@then(parsers.parse("il a commencé au « {debut} », dure {duree:d} seconde et finira au « {fin} »"))
def temps_en_cours(client: Client, debut: str, duree: int, fin: str) -> None:
	courant = en_cours(client)
	assert heure(courant["debut"]) == heure(debut), courant
	assert (courant["duree"] == duree) and (heure(courant["fin_estimee"]) == heure(fin)), courant


@then(parsers.re(r"l'emplacement du (?P<lequel>sonore en cours|prochain sonore) est le fichier de « (?P<nom>[^»]+) »"))
def emplacement_fichier(client: Client, banc: Banc, lequel: str, nom: str) -> None:
	if lequel == "sonore en cours":
		sonore_annonce = en_cours(client)
	else:
		sonore_annonce = prochain(client)
	assert sonore_annonce["emplacement"] == str(banc.fichiers[nom]), sonore_annonce


@then(parsers.parse("l'emplacement du sonore en cours est l'adresse du flux « {flux} »"))
def emplacement_flux(client: Client, serveur: Any, flux: str) -> None:
	assert en_cours(client)["emplacement"] == serveur.adresse(flux), en_cours(client)


@then("sa progression est entre 0 et 1")
def progression(client: Client) -> None:
	valeur = en_cours(client)["progression"]
	assert (isinstance(valeur, float)) and (0 < valeur < 1), en_cours(client)


@then("sa durée, sa fin estimée et sa progression sont inconnues")
def duree_inconnue(client: Client) -> None:
	courant = en_cours(client)
	assert (courant["duree"] is None) and (courant["fin_estimee"] is None) and (courant["progression"] is None), courant
	assert courant["position"] > 0, courant


@then("il n'y a ni sonore en cours ni prochain sonore")
def rien(client: Client) -> None:
	assert (message(client)["en_cours"] is None) and (message(client)["prochain"] is None), message(client)


@then(parsers.re(r"le prochain sonore est « (?P<titre>[^»]+) », (?P<sain>sain|pas sain|à l'état sain inconnu)$"))
def sonore_prochain(client: Client, titre: str, sain: str) -> None:
	suivant = prochain(client)
	attendu = {"sain": True, "pas sain": False, "à l'état sain inconnu": None}[sain]
	assert (suivant["titre"] == titre) and (suivant["sain"] is attendu), suivant


@then(parsers.parse("il commencera au « {debut} », dure {duree:d} seconde et finira au « {fin} »"))
def temps_prochain(client: Client, debut: str, duree: int, fin: str) -> None:
	suivant = prochain(client)
	assert heure(suivant["debut_estime"]) == heure(debut), suivant
	assert (suivant["duree"] == duree) and (heure(suivant["fin_estimee"]) == heure(fin)), suivant


@then(parsers.parse("le prochain sonore commencera au « {debut} » et finira au « {fin} »"))
def debut_et_fin_du_prochain(client: Client, debut: str, fin: str) -> None:
	suivant = prochain(client)
	assert heure(suivant["debut_estime"]) == heure(debut), suivant
	assert heure(suivant["fin_estimee"]) == heure(fin), suivant


@then(parsers.parse("le prochain sonore commencera au « {debut} »"))
def debut_du_prochain(client: Client, debut: str) -> None:
	suivant = prochain(client)
	assert heure(suivant["debut_estime"]) == heure(debut), suivant


@then("le deuxième passage est le prochain sonore annoncé")
def reservation_tenue(base_vide: Connexion, client: Client) -> None:
	noms = [p[0] for p in passages(base_vide)]
	assert (len(noms) == 2) and (noms[1] == prochain(client)["titre"]), (noms, prochain(client))


def attendre_la_fin(client: Client) -> None:
	assert client.fil is not None
	client.fil.join(DELAI)
	assert not client.fil.is_alive(), "le client attend toujours la fin de la socket"


@then(parsers.re(r"le client a vu passer en cours (?P<liste>.+)"))
def vus(client: Client, liste: str) -> None:
	attendre_la_fin(client)
	titres: list[str] = []
	for recu in client.recus:
		courant = recu["en_cours"]
		if (courant is not None) and ((not titres) or (titres[-1] != courant["titre"])):
			titres.append(courant["titre"])
	assert titres == [n.strip(" «»") for n in liste.split(",")], titres


@then(parsers.parse("son dernier message est à l'état « {etat} »"))
def dernier(client: Client, etat: str) -> None:
	attendre_la_fin(client)
	assert (client.recus) and (client.recus[-1]["etat"] == etat), client.recus[-1:]


@then("la socket d'état n'existe plus")
def socket_effacee(banc: Banc) -> None:
	assert not socket_du_banc(banc).chemin.exists()


@then("le répertoire de la socket d'état n'est accessible qu'à son propriétaire")
def repertoire_prive(banc: Banc) -> None:
	assert stat.S_IMODE(socket_du_banc(banc).chemin.parent.stat().st_mode) == 0o700


@then("la socket d'état n'est lisible et modifiable que par son propriétaire")
def socket_privee(banc: Banc) -> None:
	assert stat.S_IMODE(socket_du_banc(banc).chemin.stat().st_mode) == 0o600


@then("une seconde diffusion sur la même socket d'état est refusée, car un autre Machin lecture diffuse déjà")
def seconde_diffusion(banc: Banc) -> None:
	with pytest.raises(SocketEtatOccupee, match="un autre Machin lecture diffuse déjà"):
		SocketEtat(socket_du_banc(banc).chemin).ouvrir()
	assert socket_du_banc(banc).chemin.exists()


def champs(valeur: object) -> set[str]:
	if not isinstance(valeur, dict):
		return set()
	return set(valeur) | {cle for sous in valeur.values() for cle in champs(sous)}


@then("chaque champ du message figure dans la spécification, § 5.4")
def champs_documentes(client: Client) -> None:
	texte = SPEC.read_text(encoding="utf-8")
	section = re.search(r"### 5\.4 Socket d'état\n(.*?)\n### ", texte, re.DOTALL)
	assert section is not None
	absents = {cle for cle in champs(message(client)) if f"`{cle}`" not in section.group(1)}
	assert not absents, f"absents de spec § 5.4 : {sorted(absents)}"


# ─── Playlist immédiate (https://github.com/dascritch/machincast/issues/228) ─────


def a_venir(client: Client) -> list[dict[str, Any]]:
	sonores = message(client)["a_venir"]
	assert isinstance(sonores, list), message(client)
	return sonores


@then(parsers.re(r"la socket annonce les sonores à venir (?P<liste>.+), sains"))
def sonores_a_venir(client: Client, liste: str) -> None:
	sonores = a_venir(client)
	assert [s["titre"] for s in sonores] == [n.strip(" «»") for n in liste.split(",")], sonores
	assert all(s["sain"] is True for s in sonores), sonores


@then(
	parsers.re(
		r"le (?P<lequel>premier|dernier) sonore à venir commencera au « (?P<debut>[^»]+) »"
		r" et finira au « (?P<fin>[^»]+) »"
	)
)
def heures_a_venir(client: Client, lequel: str, debut: str, fin: str) -> None:
	sonore_lu = a_venir(client)[0 if lequel == "premier" else -1]
	assert heure(sonore_lu["debut_estime"]) == heure(debut), sonore_lu
	assert heure(sonore_lu["fin_estimee"]) == heure(fin), sonore_lu


@then(parsers.parse("le premier sonore à venir vient de l'événement « {evenement} », permanent"))
def evenement_a_venir(client: Client, evenement: str) -> None:
	sonore_lu = a_venir(client)[0]
	assert (sonore_lu["evenement"], sonore_lu["evenement_debut"], sonore_lu["evenement_fin"]) == (
		evenement,
		None,
		None,
	), sonore_lu


@then("il n'y a aucun sonore à venir")
def aucun_a_venir(client: Client) -> None:
	assert a_venir(client) == []


@then(parsers.parse("le sonore en cours est joué par un événement de priorité « {priorite} »"))
def priorite_en_cours(client: Client, priorite: str) -> None:
	assert en_cours(client)["evenement_priorite"] == priorite


# ─── Contexte du sonore (https://github.com/dascritch/machincast/issues/144) ─────


def identifiant_de(base: Connexion, table: str, nom: str | None) -> int | None:
	if nom is None:
		return None
	ligne = base.execute(f"SELECT id FROM {table} WHERE nom_interne = %s", (nom,)).fetchone()  # noqa: S608
	assert ligne is not None, nom
	return int(str(ligne[0]))


@then(
	parsers.re(
		r"le (?P<lequel>sonore en cours|prochain sonore) vient de (?:la banque « (?P<banque>[^»]+) »|la séquence"
		r" « (?P<sequence>[^»]+) »), sans (?:séquence|banque), de l'événement « (?P<evenement>[^»]+) », permanent"
	)
)
def contexte_du_sonore(
	client: Client,
	base_vide: Connexion,
	lequel: str,
	banque: str | None,
	sequence: str | None,
	evenement: str,
) -> None:
	sonore_lu = prochain(client)
	if lequel == "sonore en cours":
		sonore_lu = en_cours(client)
	attendu = {
		"banque": banque,
		"banque_id": identifiant_de(base_vide, "banques", banque),
		"sequence": sequence,
		"sequence_id": identifiant_de(base_vide, "sequences", sequence),
		"evenement": evenement,
		"evenement_id": identifiant_de(base_vide, "evenements", evenement),
		"evenement_debut": None,
		"evenement_fin": None,
	}
	assert {cle: sonore_lu.get(cle) for cle in attendu} == attendu, sonore_lu


@then(parsers.parse("l'événement du sonore en cours va du « {debut} » au « {fin} »"))
def bornes_de_l_evenement(client: Client, debut: str, fin: str) -> None:
	courant = en_cours(client)
	assert (courant["evenement_debut"], courant["evenement_fin"]) == (
		heure(debut).replace(tzinfo=None).isoformat(),
		heure(fin).replace(tzinfo=None).isoformat(),
	), courant


@then(parsers.parse("le texte public du sonore en cours est « {texte} »"))
def texte_public(client: Client, texte: str) -> None:
	assert en_cours(client)["texte_public"] == texte


@then("le prochain sonore n'a pas de texte public")
def sans_texte_public(client: Client) -> None:
	assert "texte_public" not in prochain(client)


# ─── Coupure par un événement à venir (https://github.com/dascritch/machincast/issues/169) ─────


@given(parsers.parse("le sonore « {nom} » dure {duree:d} secondes en base"))
def duree_en_base(base_vide: Connexion, nom: str, duree: int) -> None:
	"""La durée en base décide des heures annoncées ; le fichier joué reste le court fichier de test."""
	base_vide.execute("UPDATE sonores SET duree = %s WHERE id = %s", (timedelta(seconds=duree), sonore(base_vide, nom)))


@given(parsers.parse("la banque « {nom} » est marquée « ne pas répéter »"))
def ne_pas_repeter(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("UPDATE banques SET ne_pas_repeter = true WHERE nom_interne = %s", (nom,))


@given(
	parsers.re(
		r"l'émission « (?P<nom>[^»]+) » de (?P<debut>[\d:]+) à (?P<fin>[\d:]+),"
		r" qui joue la banque « (?P<banque>[^»]+) », puis le sonore « (?P<nom_sonore>[^»]+) »"
	)
)
def emission_banque_puis_sonore(
	banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, debut: str, fin: str, banque: str, nom_sonore: str
) -> None:
	evenement(banc, base_vide, tmp_path, nom, "emission", heure(f"2026-10-14 {debut}"), heure(f"2026-10-14 {fin}"), [])
	base_vide.execute(
		"INSERT INTO evenements_elements (evenement_id, position, banque_id)"
		" SELECT e.id, 1, b.id FROM evenements e, banques b WHERE e.nom_interne = %s AND b.nom_interne = %s",
		(nom, banque),
	)
	base_vide.execute(
		"INSERT INTO evenements_elements (evenement_id, position, sonore_id)"
		" SELECT id, 2, %s FROM evenements WHERE nom_interne = %s",
		(creer_sonore(banc, base_vide, tmp_path, nom_sonore), nom),
	)


@then(
	parsers.re(
		r"le sonore en cours finira au « (?P<fin>[^»]+) »,"
		r" (?:coupé par l'événement « (?P<evenement>[^»]+) »|sans être coupé)"
	)
)
def fin_du_sonore_en_cours(client: Client, base_vide: Connexion, fin: str, evenement: str | None) -> None:
	courant = en_cours(client)
	assert heure(courant["fin_estimee"]) == heure(fin), courant
	attendu = None
	if evenement is not None:
		attendu = identifiant_de(base_vide, "evenements", evenement)
	assert (courant["coupe_par"], courant["coupe_par_id"]) == (evenement, attendu), courant


@then(parsers.parse("le prochain sonore est joué par l'événement « {evenement} »"))
def evenement_du_prochain(client: Client, evenement: str) -> None:
	assert prochain(client)["evenement"] == evenement, prochain(client)


@given(
	parsers.re(
		r"l'émission « (?P<nom>[^»]+) » de (?P<debut>[\d:]+) à (?P<fin>[\d:]+), avec la banque aléatoire"
		r" « (?P<banque>[^»]+) » des sonores (?P<liste>.+)"
	)
)
def emission_banque_aleatoire(
	banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, debut: str, fin: str, banque: str, liste: str
) -> None:
	evenement(banc, base_vide, tmp_path, nom, "emission", heure(f"2026-10-14 {debut}"), heure(f"2026-10-14 {fin}"), [])
	creee = base_vide.execute(
		"INSERT INTO banques (nom_interne, mode) VALUES (%s, 'aleatoire') RETURNING id", (banque,)
	).fetchone()
	assert creee is not None
	for position, nom_sonore in enumerate((n.strip(" «»") for n in liste.split(",")), start=1):
		base_vide.execute(
			"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, %s)",
			(creee[0], creer_sonore(banc, base_vide, tmp_path, nom_sonore), position),
		)
	base_vide.execute(
		"INSERT INTO evenements_elements (evenement_id, position, banque_id)"
		" SELECT id, 1, %s FROM evenements WHERE nom_interne = %s",
		(creee[0], nom),
	)


@then("le sonore en cours n'a pas de fin estimée, sans être coupé")
def ni_fin_ni_coupure(client: Client) -> None:
	courant = en_cours(client)
	assert (courant["fin_estimee"], courant["coupe_par"], courant["coupe_par_id"]) == (None, None, None), courant
