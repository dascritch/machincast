"""Étapes des scénarios de vérification de l'installation (https://github.com/dascritch/machincast/issues/40)."""

import grp
import os
import pwd
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import gi
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.audio import Greffon
from machincast.configuration import REPERTOIRE_PROJET, SortieAudio
from machincast.installation import (
	UNITE,
	Compte,
	Manque,
	regle_polkit,
	unite_systemd,
	verifier_decodeurs,
	verifier_sortie,
	verifier_streams,
)
from tests.base_test import chemin_configuration_test, configuration_test

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

scenarios("installation.feature")

LECTEURS = Gst.ELEMENT_FACTORY_TYPE_DECODER | Gst.ELEMENT_FACTORY_TYPE_DEMUXER | Gst.ELEMENT_FACTORY_TYPE_PARSER


@given(parsers.parse("les éléments GStreamer qui lisent « {caps} » désactivés"))
def elements_desactives(caps: str) -> Iterator[None]:
	"""Simule un paquet absent : decodebin, comme la vérification, ignore les éléments de rang NONE."""
	Gst.init(None)
	capacites = Gst.Caps.from_string(caps)
	assert capacites is not None
	fabriques = [
		f for f in Gst.ElementFactory.list_get_elements(LECTEURS, Gst.Rank.MARGINAL) if f.can_sink_any_caps(capacites)
	]
	assert fabriques, f"aucun élément ne lit {caps}"
	rangs = [(fabrique, fabrique.get_rank()) for fabrique in fabriques]
	for fabrique in fabriques:
		fabrique.set_rank(Gst.Rank.NONE)
	yield
	for fabrique, rang in rangs:
		fabrique.set_rank(rang)


@given(parsers.parse("les sources GStreamer du protocole « {protocole} » désactivées"))
def sources_desactivees(protocole: str) -> Iterator[None]:
	Gst.init(None)
	fabriques = [
		f
		for f in Gst.ElementFactory.list_get_elements(Gst.ELEMENT_FACTORY_TYPE_SRC, Gst.Rank.MARGINAL)
		if (f.get_uri_type() == Gst.URIType.SRC) and (protocole in ((f.get_uri_protocols()) or ([])))
	]
	assert fabriques, f"aucune source pour {protocole}"
	rangs = [(fabrique, fabrique.get_rank()) for fabrique in fabriques]
	for fabrique in fabriques:
		fabrique.set_rank(Gst.Rank.NONE)
	yield
	for fabrique, rang in rangs:
		fabrique.set_rank(rang)


@when("je vérifie la source des streams", target_fixture="manques")
def streams() -> list[Manque]:
	return verifier_streams()


@then("aucun protocole de stream ne manque de source")
def aucune_source_manquante(manques: list[Manque]) -> None:
	assert manques == [], manques


@when("je vérifie les décodeurs GStreamer", target_fixture="manques")
def decodeurs() -> list[Manque]:
	return verifier_decodeurs()


@then("aucun format sonore ne manque de décodeur")
def aucun_manque(manques: list[Manque]) -> None:
	assert manques == [], manques


@then(parsers.parse("le format {format_sonore} manque, avec le paquet « {paquet} »"))
def format_manquant(manques: list[Manque], format_sonore: str, paquet: str) -> None:
	assert Manque(format_sonore, paquet) in manques, manques


@when("je vérifie la sortie audio de la configuration de test", target_fixture="manques")
def sortie_de_test() -> list[Manque]:
	return verifier_sortie(configuration_test())


@when("je vérifie une sortie audio dont le greffon GStreamer n'existe pas", target_fixture="manques")
def sortie_inexistante() -> list[Manque]:
	greffons: dict[SortieAudio, Greffon] = {
		"factice": Greffon(fabrique="elementinexistant", propriete=None, paquet="gstreamer1.0-inexistant")
	}
	return verifier_sortie(configuration_test(), greffons)


@then("la sortie audio est disponible")
def sortie_disponible(manques: list[Manque]) -> None:
	assert manques == [], manques


@then(parsers.parse("la sortie audio manque, avec le paquet « {paquet} »"))
def sortie_manquante(manques: list[Manque], paquet: str) -> None:
	assert [manque.paquet for manque in manques] == [paquet], manques


def lancer(action: str, configuration: Path) -> subprocess.CompletedProcess[str]:
	return subprocess.run(
		[sys.executable, "-m", "machincast.installation", action, "--config", str(configuration)],
		capture_output=True,
		text=True,
		timeout=60,
	)


@when(
	parsers.parse("je lance « python -m machincast.installation {action} » avec la configuration de test"),
	target_fixture="commande",
)
def lancer_avec_configuration_de_test(action: str) -> subprocess.CompletedProcess[str]:
	return lancer(action, chemin_configuration_test())


@when(
	parsers.parse(
		"je lance « python -m machincast.installation {action} » avec une configuration dont la socket n'existe pas"
	),
	target_fixture="commande",
)
def lancer_sans_base(tmp_path: Path, action: str) -> subprocess.CompletedProcess[str]:
	# Une configuration jetable, dans le répertoire temporaire du scénario, qui ne peut joindre aucune base.
	configuration = tmp_path / "sans-base.toml"
	texte = chemin_configuration_test().read_text(encoding="utf-8")
	configuration.write_text(
		texte.replace('socket = "/var/run/postgresql"', f'socket = "{tmp_path / "aucune-socket"}"'), encoding="utf-8"
	)
	return lancer(action, configuration)


@then("la commande se termine sans erreur")
def sans_erreur(commande: subprocess.CompletedProcess[str]) -> None:
	assert commande.returncode == 0, commande.stderr


@then(parsers.parse("la commande se termine avec le code {code:d}"))
def code(commande: subprocess.CompletedProcess[str], code: int) -> None:
	assert commande.returncode == code, commande.stderr


@then("elle affiche la socket, la base de production puis la base de test de cette configuration")
def parametres(commande: subprocess.CompletedProcess[str]) -> None:
	base = configuration_test().base
	assert commande.stdout.splitlines() == [str(base.socket), base.production, base.test]


@then(parsers.parse("sa sortie annonce « {texte} »"))
def sortie_annonce(commande: subprocess.CompletedProcess[str], texte: str) -> None:
	assert texte in commande.stdout, commande.stdout + commande.stderr


@then(parsers.parse("sa sortie d'erreur mentionne « {texte} »"))
def erreur_mentionne(commande: subprocess.CompletedProcess[str], texte: str) -> None:
	assert texte in commande.stderr, commande.stderr


@pytest.fixture(autouse=True)
def gstreamer() -> None:
	Gst.init(None)


# ─── Service systemd (https://github.com/dascritch/machincast/issues/22) ─────


def _compte() -> tuple[str, str, int]:
	entree = pwd.getpwuid(os.getuid())
	return entree.pw_name, grp.getgrgid(entree.pw_gid).gr_name, entree.pw_uid


def _section(texte: str, nom: str) -> dict[str, str]:
	"""Les clés d'une section d'unité systemd ; une clé répétée garde sa dernière valeur."""
	cles: dict[str, str] = {}
	dedans = False
	for ligne in texte.splitlines():
		ligne = ligne.strip()
		if ligne.startswith("["):
			dedans = ligne == f"[{nom}]"
			continue
		if (dedans) and ("=" in ligne) and (not ligne.startswith("#")):
			cle, valeur = ligne.split("=", 1)
			cles[cle] = valeur
	return cles


@then(parsers.parse("l'unité a, dans la section « {nom} » :"))
def section_de_l_unite(commande: subprocess.CompletedProcess[str], nom: str, datatable: list[list[str]]) -> None:
	compte, groupe, uid = _compte()
	remplacements = {"<compte>": compte, "<groupe>": groupe, "<uid>": str(uid), "<répertoire>": str(REPERTOIRE_PROJET)}
	_entetes, *rangees = datatable
	attendues = {}
	for cle, valeur in rangees:
		for marque, texte in remplacements.items():
			valeur = valeur.replace(marque, texte)
		attendues[cle.strip()] = valeur.strip()
	assert _section(commande.stdout, nom) == attendues, commande.stdout


@given(parsers.parse("l'outil « {outil} » du poste"))
def outil(outil: str) -> None:
	if shutil.which(outil) is None:
		pytest.skip(f"{outil} absent du poste")


@when(parsers.parse("j'enregistre sa sortie en « {nom} »"))
def enregistrer_la_sortie(tmp_path: Path, commande: subprocess.CompletedProcess[str], nom: str) -> None:
	(tmp_path / nom).write_text(commande.stdout, encoding="utf-8")


@then(parsers.parse("« systemd-analyze verify » accepte « {nom} »"))
def unite_acceptee(tmp_path: Path, nom: str) -> None:
	verification = subprocess.run(
		["systemd-analyze", "verify", "--man=no", str(tmp_path / nom)], capture_output=True, text=True, timeout=60
	)
	assert verification.returncode == 0, verification.stderr


SIMULATEUR_POLKIT = """
const polkit = {
	Result: {NO: "no", YES: "yes", AUTH_SELF: "auth_self", AUTH_SELF_KEEP: "auth_self_keep",
		AUTH_ADMIN: "auth_admin", AUTH_ADMIN_KEEP: "auth_admin_keep", NOT_HANDLED: null},
	regles: [],
	addRule(regle) { this.regles.push(regle); },
};
const [identifiant, unite, verbe, utilisateur] = process.argv.slice(2);
const action = {id: identifiant, lookup: (cle) => ({unit: unite, verb: verbe})[cle]};
const sujet = {user: utilisateur, local: true, active: true};
"""
"""Ce que polkit donne à une règle : polkit.addRule, et une action sur une unité ; la réponse s'affiche."""


@then(
	parsers.re(
		r"la règle polkit répond (?:« (?P<reponse>[^»]+) »|rien) à l'action « (?P<action>[^»]+) »"
		r" sur « (?P<unite>[^»]+) », verbe « (?P<verbe>[^»]+) », pour (?P<qui>le compte|un autre compte)"
	)
)
def reponse_polkit(
	tmp_path: Path,
	commande: subprocess.CompletedProcess[str],
	reponse: str | None,
	action: str,
	unite: str,
	verbe: str,
	qui: str,
) -> None:
	assert commande.returncode == 0, commande.stderr
	programme = tmp_path / "polkit.js"
	programme.write_text(
		SIMULATEUR_POLKIT
		+ commande.stdout
		+ "\nconst reponses = polkit.regles.map((regle) => regle(action, sujet)).filter((r) => r != null);"
		+ "\nprocess.stdout.write(reponses.length ? String(reponses[0]) : 'rien');\n",
		encoding="utf-8",
	)
	utilisateur = _compte()[0]
	if qui == "un autre compte":
		utilisateur = f"autre-que-{utilisateur}"
	resultat = subprocess.run(
		["node", str(programme), action, unite, verbe, utilisateur], capture_output=True, text=True, timeout=60
	)
	assert resultat.returncode == 0, resultat.stderr
	assert resultat.stdout == ((reponse) or ("rien")), resultat.stdout


@then("l'unité de machincast.installation est celle de « Machin logs »")
def unite_du_wrapper() -> None:
	wrapper = (REPERTOIRE_PROJET / "bin" / "Machin").read_text(encoding="utf-8")
	assert f'UNITE_LECTURE="{UNITE}"' in wrapper


@when(
	parsers.re(
		r"l'unité et la règle sont rédigées pour le compte « (?P<nom>[^»]+) », du groupe « (?P<groupe>[^»]+) »,"
		r" d'uid (?P<uid>\d+), dans « (?P<repertoire>[^»]+) »"
	),
	target_fixture="redigees",
)
def rediger(nom: str, groupe: str, uid: str, repertoire: str) -> tuple[str, str]:
	compte = Compte(nom, groupe, int(uid))
	return unite_systemd(compte, Path(repertoire)), regle_polkit(compte)


@then(parsers.parse("l'unité a, dans la section « {nom} », entre autres :"))
def section_redigee(redigees: tuple[str, str], nom: str, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	section = _section(redigees[0], nom)
	assert {cle.strip(): section.get(cle.strip()) for cle, _valeur in rangees} == {
		cle.strip(): valeur.strip() for cle, valeur in rangees
	}


@then(parsers.parse("la règle ne concerne que le compte « {nom} »"))
def regle_du_compte(redigees: tuple[str, str], nom: str) -> None:
	assert re.findall(r'subject\.user == "([^"]+)"', redigees[1]) == [nom]
