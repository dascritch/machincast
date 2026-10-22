"""Étapes de l'écran par défaut de l'interface (https://github.com/dascritch/machincast/issues/23).

L'écran s'affiche hors de l'écran du poste (QT_QPA_PLATFORM=offscreen, réglé par tests/conftest.py). La socket d'état
est un vrai serveur du binaire lecture (machincast.lecture.etat.SocketEtat), qui publie les états du scénario.
"""

import json
import re
import shutil
import subprocess
import sys
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QLabel, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

import machincast.interface.__main__ as module_interface
import machincast.interface.application as module_application
import machincast.interface.ecran_par_defaut as module_ecran
import machincast.interface.erreur as module_erreur
from machincast.base import Role, connecter
from machincast.configuration import REPERTOIRE_PROJET
from machincast.horloge import HorlogeFixe
from machincast.interface.application import traduire
from machincast.interface.ecran_par_defaut import EcranParDefaut
from machincast.interface.erreur import FenetreBaseInjoignable
from machincast.interface.frise import HAUTEUR, Frise
from machincast.lecture.etat import SocketEtat
from tests.base_test import CONFIGURATION_TEST, parametres_base_test
from tests.etapes_interface import ouvrir_dans
from tests.sons import FICHIERS_SONORES

scenarios("ecran_par_defaut.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
JOUR = "2026-10-16"
ATTENTE = 3000
"""Délai laissé à l'écran pour recevoir un état, en millisecondes."""


@dataclass
class Contexte:
	repertoire: Path
	horloge: HorlogeFixe | None = None
	socket: SocketEtat | None = None
	en_cours: dict[str, Any] | None = None
	prochain: dict[str, Any] | None = None
	ecran: EcranParDefaut | None = None
	connexion: Connexion | None = None
	lectures: list[datetime] = field(default_factory=list)
	"""Instants où l'écran a lu l'airplay."""
	fiches: list[tuple[str, int, str]] = field(default_factory=list)
	"""Fiches que l'écran a demandées (ouverte) : genre, identifiant et nom."""
	processus: subprocess.CompletedProcess[str] | None = None
	fenetres: list[FenetreBaseInjoignable] = field(default_factory=list)
	"""Fenêtres d'erreur montrées par Machin interface lancé dans le test."""
	code: int | None = None
	en_base: dict[str, tuple[int, str]] = field(default_factory=dict)
	"""Sonores en base du scénario, par titre : identifiant et emplacement
	(https://github.com/dascritch/machincast/issues/230)."""
	banques: dict[str, int] = field(default_factory=dict)
	forme_du_prochain: object = None
	"""La forme d'onde de la frise du prochain sonore, retenue pour la retrouver quand il passe à l'antenne."""
	positions_demandees: list[float] = field(default_factory=list)
	plans_lus: list[int] = field(default_factory=list)
	"""Sonores dont l'écran a lu le plan en base."""
	sortie_d_erreur: str = ""
	ouverts: list[str] = field(default_factory=list)
	"""Documents ouverts par le bouton de la fenêtre d'erreur."""
	affichage: bool | None = None
	clic: str | None = None
	"""Bouton que le technicien choisit dans la fenêtre d'erreur."""

	@property
	def chemin(self) -> Path:
		return self.repertoire / "run" / "lecture.sock"


@pytest.fixture
def contexte(tmp_path: Path) -> Iterator[Contexte]:
	contexte = Contexte(tmp_path)
	yield contexte
	if contexte.ecran is not None:
		contexte.ecran.close()
	if contexte.socket is not None:
		contexte.socket.fermer()
	if contexte.connexion is not None:
		contexte.connexion.close()


def heure(texte: str) -> datetime:
	return datetime.fromisoformat(texte).astimezone()


def heure_ou_rien(texte: str) -> datetime | None:
	if texte == "":
		return None
	return heure(texte)


def a(horaire: str) -> datetime:
	return heure(f"{JOUR} {horaire}")


def secondes(texte: str) -> float:
	return float(texte.replace(",", "."))


def ecran(contexte: Contexte) -> EcranParDefaut:
	assert contexte.ecran is not None
	return contexte.ecran


def socket(contexte: Contexte) -> SocketEtat:
	assert contexte.socket is not None
	return contexte.socket


def publier(contexte: Contexte, etat: str = "diffusion") -> None:
	assert contexte.horloge is not None
	socket(contexte).publier(
		{
			"horodatage": contexte.horloge.maintenant().isoformat(),
			"etat": etat,
			"en_cours": contexte.en_cours if etat == "diffusion" else None,
			"prochain": contexte.prochain,
		}
	)


def emplacement(titre: str) -> str:
	"""Chemin d'un fichier, sans espace : un long titre donne un long chemin, que rien ne coupe."""
	return f"/srv/musique/{titre.replace(' ', '_')}.flac"


def adresse(titre: str) -> str:
	return f"https://flux.exemple/{titre.replace(' ', '_')}"


def attendre(qtbot: QtBot, condition: Callable[[], bool]) -> None:
	qtbot.waitUntil(condition, timeout=ATTENTE)


def reference(base: Connexion, table: str, nom: str) -> int | None:
	"""Identifiant de l'entrée de ce nom interne, créée au besoin ; None pour un nom vide."""
	if not nom:
		return None
	valeurs = {"evenements": ", priorite) VALUES (%s, 'fil_musical')", "banques": ", mode) VALUES (%s, 'sequentiel')"}
	ligne = base.execute(f"SELECT id FROM {table} WHERE nom_interne = %s", (nom,)).fetchone()  # noqa: S608
	if ligne is None:
		suite = valeurs.get(table, ") VALUES (%s)")
		ligne = base.execute(f"INSERT INTO {table} (nom_interne{suite} RETURNING id", (nom,)).fetchone()  # noqa: S608
	assert ligne is not None
	return int(str(ligne[0]))


def inserer_passage(
	base: Connexion,
	debut: datetime,
	fin: datetime | None,
	artiste: str,
	titre: str,
	evenement: str,
	sequence: str = "",
	banque: str = "",
	sans_incident: str = "",
) -> None:
	ligne = base.execute(
		"INSERT INTO sonores (type, emplacement, artiste, titre) VALUES ('fichier', %s, %s, %s) RETURNING id",
		(f"/musique/{uuid.uuid4()}.flac", (artiste) or (None), titre),
	).fetchone()
	assert ligne is not None
	references = (
		ligne[0],
		reference(base, "evenements", evenement),
		reference(base, "sequences", sequence),
		reference(base, "banques", banque),
	)
	passage = uuid.uuid4()
	colonnes = "passage_id, type_ligne, horodatage, sonore_id, evenement_id, sequence_id, banque_id, artiste, titre"
	base.execute(
		f"INSERT INTO airplay ({colonnes}) VALUES (%s, 'debut', %s, %s, %s, %s, %s, %s, %s)",
		(passage, debut, *references, (artiste) or (None), titre),
	)
	if fin is not None:
		base.execute(
			f"INSERT INTO airplay ({colonnes}, duree_diffusee, sans_incident)"
			" VALUES (%s, 'fin', %s, %s, %s, %s, %s, %s, %s, %s, %s)",
			(passage, fin, *references, (artiste) or (None), titre, fin - debut, sans_incident == "oui"),
		)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'horloge de l'interface au « {instant} »"))
def horloge(contexte: Contexte, instant: str) -> None:
	contexte.horloge = HorlogeFixe(heure(instant))


@given("la socket d'état du binaire lecture ouverte")
@when("la socket d'état du binaire lecture s'ouvre ensuite")
def ouvrir_la_socket(contexte: Contexte) -> None:
	contexte.socket = SocketEtat(contexte.chemin)
	contexte.socket.ouvrir()


@given(
	parsers.re(
		r"le binaire lecture diffuse « (?P<titre>[^»]+) » de « (?P<artiste>[^»]+) » dans « (?P<evenement>[^»]+) »,"
		r" commencé à (?P<debut>[\d:]+), de (?P<duree>[\d,]+) secondes, joué depuis (?P<position>[\d,]+) secondes"
	)
)
@when(
	parsers.re(
		r"le binaire lecture diffuse « (?P<titre>[^»]+) » de « (?P<artiste>[^»]+) » dans « (?P<evenement>[^»]+) »,"
		r" commencé à (?P<debut>[\d:]+), de (?P<duree>[\d,]+) secondes, joué depuis (?P<position>[\d,]+) secondes"
	)
)
def diffuse(
	contexte: Contexte, titre: str, artiste: str, evenement: str, debut: str, duree: str, position: str
) -> None:
	commence = a(debut)
	longueur = secondes(duree)
	contexte.en_cours = {
		"sonore": 12,
		"type": "fichier",
		"artiste": artiste,
		"titre": titre,
		"evenement": evenement,
		"debut": commence.isoformat(),
		"duree": longueur,
		"fin_estimee": (commence + timedelta(seconds=longueur)).isoformat(),
		"emplacement": emplacement(titre),
		"position": secondes(position),
		"progression": round(min(1.0, secondes(position) / ((longueur) or (1.0))), 3),
	}
	publier(contexte)


@given(
	parsers.re(
		r"le binaire lecture diffuse le stream « (?P<titre>[^»]+) » dans « (?P<evenement>[^»]+) »,"
		r" commencé à (?P<debut>[\d:]+), joué depuis (?P<position>[\d,]+) secondes"
	)
)
def diffuse_un_stream(contexte: Contexte, titre: str, evenement: str, debut: str, position: str) -> None:
	contexte.en_cours = {
		"sonore": 7,
		"type": "stream",
		"artiste": None,
		"titre": titre,
		"evenement": evenement,
		"debut": a(debut).isoformat(),
		"duree": None,
		"fin_estimee": None,
		"emplacement": adresse(titre),
		"position": secondes(position),
		"progression": None,
	}
	publier(contexte)


@given(
	parsers.re(
		r"le prochain sonore est « (?P<titre>[^»]+) » dans « (?P<evenement>[^»]+) », estimé de (?P<debut>[\d:]+)"
		r" à (?P<fin>[\d:]+), de (?P<duree>[\d,]+) secondes, sain : (?P<sain>oui|non)"
	)
)
def prochain(contexte: Contexte, titre: str, evenement: str, debut: str, fin: str, duree: str, sain: str) -> None:
	contexte.prochain = {
		"sonore": 31,
		"type": "fichier",
		"artiste": None,
		"titre": titre,
		"evenement": evenement,
		"debut_estime": a(debut).isoformat(),
		"duree": secondes(duree),
		"fin_estimee": a(fin).isoformat(),
		"emplacement": emplacement(titre),
		"sain": sain == "oui",
	}
	publier(contexte)


@given(parsers.re(r"le (?P<lequel>sonore en cours|prochain sonore) a pour contexte :"))
def contexte_du_sonore(contexte: Contexte, lequel: str, datatable: list[list[str]]) -> None:
	"""Les champs de contexte de la socket d'état (spec § 5.4) : identifiants en nombres, heures murales, textes."""
	sonore = contexte.en_cours if lequel == "sonore en cours" else contexte.prochain
	assert sonore is not None
	_entetes, *rangees = datatable
	for champ, valeur in ((champ.strip(), valeur.strip()) for champ, valeur in rangees):
		lu: object = (valeur) or (None)
		if (champ.endswith("_id")) and (valeur != ""):
			lu = int(valeur)
		if (champ in ("evenement_debut", "evenement_fin")) and (valeur != ""):
			lu = datetime.fromisoformat(valeur).isoformat()
		sonore[champ] = lu
	publier(contexte)


@given(parsers.re(r"le sonore en cours sera coupé à (?P<instant>[\d:]+) par l'événement « (?P<evenement>[^»]+) »"))
def coupure(contexte: Contexte, instant: str, evenement: str) -> None:
	"""La coupure annoncée par la socket (https://github.com/dascritch/machincast/issues/169) : la fin estimée devient
	celle de la coupure."""
	assert contexte.en_cours is not None
	contexte.en_cours |= {"fin_estimee": a(instant).isoformat(), "coupe_par": evenement, "coupe_par_id": 8}
	publier(contexte)


@given(parsers.parse("le prochain sonore est le stream « {titre} » dans « {evenement} », de début inconnu"))
def prochain_stream(contexte: Contexte, titre: str, evenement: str) -> None:
	contexte.prochain = {
		"sonore": 8,
		"type": "stream",
		"artiste": None,
		"titre": titre,
		"evenement": evenement,
		"debut_estime": None,
		"duree": None,
		"fin_estimee": None,
		"emplacement": adresse(titre),
		"sain": None,
	}
	publier(contexte)


@given(
	parsers.parse(
		"le binaire lecture diffuse un sonore sans artiste ni titre dans « {evenement} », commencé à {debut},"
		" de {duree:d} secondes"
	)
)
def diffuse_sans_titre(contexte: Contexte, evenement: str, debut: str, duree: int) -> None:
	commence = a(debut)
	contexte.en_cours = {
		"sonore": 13,
		"type": "fichier",
		"artiste": None,
		"titre": None,
		"evenement": evenement,
		"debut": commence.isoformat(),
		"duree": duree,
		"fin_estimee": (commence + timedelta(seconds=duree)).isoformat(),
		"emplacement": None,
		"position": 0,
		"progression": 0,
	}
	publier(contexte)


@given("le binaire lecture est en silence")
@when("le binaire lecture est en silence")
def en_silence(contexte: Contexte) -> None:
	contexte.en_cours = None
	contexte.prochain = None
	publier(contexte, "silence")


@given("les passages dans l'airplay :")
def passages(base_vide: Connexion, datatable: list[list[str]]) -> None:
	entetes, *lignes = datatable
	for valeurs in lignes:
		ligne = dict(zip(entetes, (v.strip() for v in valeurs), strict=True))
		inserer_passage(
			base_vide,
			heure(ligne["debut"]),
			heure_ou_rien(ligne["fin"]),
			ligne["artiste"],
			ligne["titre"],
			ligne["evenement"],
			ligne["sequence"],
			ligne["banque"],
			ligne["sans_incident"],
		)


@given("le masquage de tous les sonores et de tous les événements")
def masquer(base_vide: Connexion) -> None:
	base_vide.execute("UPDATE sonores SET masquer_metadonnees = true")
	base_vide.execute("UPDATE evenements SET masquer_metadonnees = true")


# ─── Quand ─────────────────────────────────────────────────


@when("l'écran par défaut s'ouvre")
def ouvrir(contexte: Contexte, base_vide: Connexion, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
	assert contexte.horloge is not None
	lire = module_ecran.lire_airplay

	def lire_et_compter(connexion: Any, depuis: datetime) -> Any:
		contexte.lectures.append(depuis)
		return lire(connexion, depuis)

	monkeypatch.setattr(module_ecran, "lire_airplay", lire_et_compter)
	lire_le_plan = module_ecran.lire_le_plan

	def lire_le_plan_et_compter(connexion: Any, sonore: int, *autres: Any) -> Any:
		contexte.plans_lus.append(sonore)
		return lire_le_plan(connexion, sonore, *autres)

	monkeypatch.setattr(module_ecran, "lire_le_plan", lire_le_plan_et_compter)
	contexte.connexion = connecter(*parametres_base_test(), Role.INTERFACE)
	contexte.ecran = EcranParDefaut(contexte.connexion, contexte.chemin, contexte.horloge)
	contexte.ecran.ouverte.connect(lambda genre, numero, nom: contexte.fiches.append((genre, numero, nom)))
	qtbot.addWidget(contexte.ecran)
	contexte.ecran.show()


@when(parsers.parse("l'écran par défaut s'ouvre, large de {largeur:d} pixels"))
def ouvrir_large(
	contexte: Contexte, base_vide: Connexion, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, largeur: int
) -> None:
	ouvrir(contexte, base_vide, qtbot, monkeypatch)
	ecran(contexte).resize(largeur, 760)


@when(parsers.re(r"le sonore en cours est bientôt « (?P<texte>[^»]+) »"))
def attendre_en_cours(contexte: Contexte, qtbot: QtBot, texte: str) -> None:
	attendre(qtbot, lambda: ecran(contexte).ui.en_cours_titre.text() == texte)


@when(parsers.parse("l'horloge de l'interface avance de {nombre:d} secondes"))
def avancer(contexte: Contexte, nombre: int) -> None:
	assert contexte.horloge is not None
	contexte.horloge.avancer(timedelta(seconds=nombre))


@when("le binaire lecture s'arrête")
def arret(contexte: Contexte) -> None:
	contexte.en_cours = None
	contexte.prochain = None
	publier(contexte, "arret")
	socket(contexte).fermer()
	contexte.socket = None


@when("l'état du binaire lecture est bientôt « En diffusion »")
def attendre_la_diffusion(contexte: Contexte, qtbot: QtBot) -> None:
	attendre(qtbot, lambda: ecran(contexte).ui.etat_lecture.text() == "En diffusion")


@when("la socket d'état se ferme sans dernier état")
def fermeture_brutale(contexte: Contexte) -> None:
	socket(contexte).fermer()
	contexte.socket = None


def envoyer_brut(contexte: Contexte, texte: str) -> None:
	"""Envoie ce texte tel quel aux clients : le serveur, lui, n'envoie que des lignes JSON complètes."""
	serveur = socket(contexte)
	with serveur._condition:
		serveur._message = texte
		serveur._numero += 1
		serveur._condition.notify_all()


def ligne_de_silence() -> str:
	return json.dumps({"version": 1, "etat": "silence", "en_cours": None, "prochain": None}) + "\n"


@when("un message illisible arrive sur la socket d'état, suivi dans le même envoi d'un état de silence")
def illisible(contexte: Contexte) -> None:
	envoyer_brut(contexte, "{ pas du JSON\n" + ligne_de_silence())


@when("un état de silence arrive sur la socket d'état en deux envois")
def en_deux_envois(contexte: Contexte, qtbot: QtBot) -> None:
	ligne = ligne_de_silence()
	moitie = len(ligne) // 2
	envoyer_brut(contexte, ligne[:moitie])
	qtbot.wait(300)
	envoyer_brut(contexte, ligne[moitie:])


@when(parsers.parse("le passage de « {titre} » commence dans l'airplay à {debut}"))
def nouveau_passage(base_vide: Connexion, titre: str, debut: str) -> None:
	inserer_passage(base_vide, a(debut), None, "Radio", titre, "Fil de jour")


def configuration_sans_base(contexte: Contexte) -> Path:
	configuration = contexte.repertoire / "sans-base.toml"
	texte = CONFIGURATION_TEST.read_text(encoding="utf-8")
	configuration.write_text(
		texte.replace('socket = "/var/run/postgresql"', f'socket = "{contexte.repertoire / "aucune-socket"}"'),
		encoding="utf-8",
	)
	return configuration


@given("un affichage graphique disponible")
def affichage_disponible(contexte: Contexte, monkeypatch: pytest.MonkeyPatch, qtbot: QtBot) -> None:
	"""La fenêtre d'erreur est créée, mais pas montrée : le test lit ce qu'elle aurait montré."""

	def montrer(fenetre: FenetreBaseInjoignable) -> int:
		if fenetre not in contexte.fenetres:
			contexte.fenetres.append(fenetre)
		if contexte.clic is not None:
			assert fenetre.bouton_installation.text() == contexte.clic
			fenetre.bouton_installation.click()
		return 0

	monkeypatch.setattr(module_interface, "affichage_disponible", lambda: True)
	monkeypatch.setattr(FenetreBaseInjoignable, "exec", montrer)
	monkeypatch.setattr(module_erreur.QDesktopServices, "openUrl", lambda url: contexte.ouverts.append(url.toString()))


@given("la traduction française de Qt chargée")
def traduction(qapp: Any) -> Iterator[None]:
	assert traduire(qapp)
	yield
	for traducteur in qapp.findChildren(module_application.QTranslator):
		qapp.removeTranslator(traducteur)
		traducteur.deleteLater()


@given("un compte qui ne peut pas endosser le rôle de l'interface")
def sans_droit(monkeypatch: pytest.MonkeyPatch) -> None:
	def refuser(*_: object) -> None:
		raise psycopg.errors.InsufficientPrivilege('permission denied to set role "machincast_interface"')

	monkeypatch.setattr(module_interface, "connecter", refuser)


@when("Machin interface démarre avec une socket PostgreSQL inexistante")
def demarrer(contexte: Contexte, capsys: pytest.CaptureFixture[str]) -> None:
	contexte.code = module_interface.main(["--config", str(configuration_sans_base(contexte))])
	contexte.sortie_d_erreur = capsys.readouterr().err


@when(parsers.parse("je clique sur « {bouton} » dans la fenêtre d'erreur"))
def cliquer(contexte: Contexte, bouton: str) -> None:
	contexte.clic = bouton
	fenetre_d_erreur(contexte).montrer()


@when(parsers.parse("l'environnement graphique est {environnement}"))
def environnement(contexte: Contexte, environnement: str) -> None:
	variables = {}
	if environnement != "vide":
		variables = dict(paire.strip().split("=", 1) for paire in environnement.split(","))
	contexte.affichage = module_interface.affichage_disponible(variables)


@when("l'application Qt de l'interface est créée dans un processus neuf")
def application_neuve(contexte: Contexte) -> None:
	programme = (
		"from PySide6.QtCore import QCoreApplication\n"
		"from machincast.interface.application import application\n"
		"application('essai')\n"
		"print(QCoreApplication.translate('QMessageBox', 'Show Details...'))\n"
	)
	contexte.processus = subprocess.run([sys.executable, "-c", programme], capture_output=True, text=True, timeout=60)


@then(parsers.parse("Qt y traduit « {anglais} » par « {francais} »"))
def traduit(contexte: Contexte, anglais: str, francais: str) -> None:
	assert contexte.processus is not None
	processus = contexte.processus
	assert processus.stdout.strip() == francais, (anglais, processus.stdout, processus.stderr)


@when("je lance Machin_interface avec une socket PostgreSQL inexistante")
def lancer(contexte: Contexte) -> None:
	configuration = configuration_sans_base(contexte)
	executable = (shutil.which("Machin_interface")) or (str(Path(sys.executable).parent / "Machin_interface"))
	contexte.processus = subprocess.run(
		[executable, "--config", str(configuration)], capture_output=True, text=True, timeout=60
	)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"l'écran affiche (?P<bientot>bientôt )?l'heure « (?P<texte>[^»]+) »"))
def heure_affichee(contexte: Contexte, qtbot: QtBot, bientot: str | None, texte: str) -> None:
	if bientot:
		attendre(qtbot, lambda: ecran(contexte).ui.heure.text() == texte)
	assert ecran(contexte).ui.heure.text() == texte


@then(parsers.re(r"l'état du binaire lecture est (?P<bientot>bientôt )?« (?P<texte>[^»]+) »"))
def etat_affiche(contexte: Contexte, qtbot: QtBot, bientot: str | None, texte: str) -> None:
	if bientot:
		attendre(qtbot, lambda: ecran(contexte).ui.etat_lecture.text() == texte)
	assert ecran(contexte).ui.etat_lecture.text() == texte


@then(parsers.re(r"le sonore en cours est (?P<bientot>bientôt )?« (?P<texte>[^»]+) »"))
def en_cours_affiche(contexte: Contexte, qtbot: QtBot, bientot: str | None, texte: str) -> None:
	if bientot:
		attendre(qtbot, lambda: ecran(contexte).ui.en_cours_titre.text() == texte)
	assert ecran(contexte).ui.en_cours_titre.text() == texte


@then(parsers.re(r"le prochain sonore est (?P<bientot>bientôt )?« (?P<texte>[^»]+) »"))
def prochain_affiche(contexte: Contexte, qtbot: QtBot, bientot: str | None, texte: str) -> None:
	if bientot:
		attendre(qtbot, lambda: ecran(contexte).ui.prochain_titre.text() == texte)
	assert ecran(contexte).ui.prochain_titre.text() == texte


@then(
	parsers.re(
		r"le (?P<lequel>sonore en cours|prochain sonore) a pour événement « (?P<evenement>[^»]+) »"
		r" et pour horaire « (?P<horaire>.+) »$"
	)
)
def evenement_et_horaire(contexte: Contexte, lequel: str, evenement: str, horaire: str) -> None:
	ui = ecran(contexte).ui
	champs = {"sonore en cours": "en_cours", "prochain sonore": "prochain"}[lequel]
	obtenus = (getattr(ui, f"{champs}_evenement").text(), getattr(ui, f"{champs}_horaire").text())
	assert obtenus == (evenement, horaire)


@then(
	parsers.re(
		r"le (?P<lequel>sonore en cours|prochain sonore) a pour séquence « (?P<sequence>[^»]+) »"
		r" et pour banque « (?P<banque>[^»]+) »"
	)
)
def sequence_et_banque(contexte: Contexte, lequel: str, sequence: str, banque: str) -> None:
	ui = ecran(contexte).ui
	champs = {"sonore en cours": "en_cours", "prochain sonore": "prochain"}[lequel]
	obtenus = (getattr(ui, f"{champs}_sequence").text(), getattr(ui, f"{champs}_banque").text())
	assert obtenus == (sequence, banque)


@then(parsers.parse("le sonore en cours n'a pas d'intitulé « {intitule} »"))
def sans_intitule(contexte: Contexte, intitule: str) -> None:
	textes = [etiquette.text() for etiquette in ecran(contexte).ui.cadre_en_cours.findChildren(QLabel)]
	assert intitule not in textes, textes


@then(parsers.re(r"le bandeau montre (?P<bientot>bientôt )?le texte public « (?P<texte>.+) »$"))
def texte_public(contexte: Contexte, qtbot: QtBot, bientot: str | None, texte: str) -> None:
	etiquette = ecran(contexte).ui.texte_public
	if bientot:
		attendre(qtbot, lambda: etiquette.text() == texte)
	assert etiquette.text() == texte


@then(parsers.re(r"l'événement à l'antenne est (?P<bientot>bientôt )?« (?P<texte>[^»]+) »"))
def evenement_antenne(contexte: Contexte, qtbot: QtBot, bientot: str | None, texte: str) -> None:
	etiquette = ecran(contexte).ui.evenement_antenne
	if bientot:
		attendre(qtbot, lambda: etiquette.text() == texte)
	assert etiquette.text() == texte


@when(parsers.parse("je clique sur le bouton « {nom} » de l'accueil"))
def cliquer_bouton(contexte: Contexte, qtbot: QtBot, nom: str) -> None:
	bouton = getattr(ecran(contexte).ui, nom)
	assert bouton.isEnabled(), nom
	qtbot.mouseClick(bouton, Qt.MouseButton.LeftButton)


@then("l'accueil a demandé les fiches :")
def fiches_demandees(contexte: Contexte, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	attendues = [(genre.strip(), int(numero), nom.strip()) for genre, numero, nom in rangees]
	assert contexte.fiches == attendues


@then("les boutons de fiche de l'accueil sont inactifs")
def boutons_inactifs(contexte: Contexte) -> None:
	ui = ecran(contexte).ui
	boutons = [
		getattr(ui, f"ouvrir_{genre}_{lequel}")
		for lequel in ("en_cours", "prochain")
		for genre in ("sonore", "evenement", "sequence", "banque")
	]
	assert [bouton.isEnabled() for bouton in boutons] == [False] * 8


@then(
	parsers.re(
		r"les boutons de séquence et de banque de l'accueil sont, pour le sonore en cours puis le prochain :"
		r" (?P<etats>.+)"
	)
)
def etats_sequence_banque(contexte: Contexte, etats: str) -> None:
	ui = ecran(contexte).ui
	obtenus = []
	for lequel in ("en_cours", "prochain"):
		for genre in ("sequence", "banque"):
			obtenus.append("actif" if getattr(ui, f"ouvrir_{genre}_{lequel}").isEnabled() else "inactif")
	assert obtenus == etats.split(", ")


@then(
	parsers.re(
		r"les boutons de fiche de l'accueil sont, dans l'ordre sonore en cours, son événement, prochain sonore,"
		r" son événement : (?P<etats>.+)"
	)
)
def etats_des_boutons(contexte: Contexte, etats: str) -> None:
	ui = ecran(contexte).ui
	boutons = (ui.ouvrir_sonore_en_cours, ui.ouvrir_evenement_en_cours, ui.ouvrir_sonore_prochain)
	obtenus = ["actif" if bouton.isEnabled() else "inactif" for bouton in (*boutons, ui.ouvrir_evenement_prochain)]
	assert obtenus == etats.split(", ")


@given(parsers.parse("le sonore « {titre} » est effacé de la base"))
def effacer_sonore(base_vide: Connexion, titre: str) -> None:
	base_vide.execute("DELETE FROM sonores WHERE titre = %s", (titre,))


@when(parsers.parse("j'ouvre dans l'airplay la cellule de la colonne « {colonne} »"))
def ouvrir_colonne(contexte: Contexte, qtbot: QtBot, colonne: str) -> None:
	"""Double-clic sur la première ligne de l'airplay, dans cette colonne, même vide."""
	table_airplay = ecran(contexte).ui.table_airplay
	titres = [titre for _nom, titre in ecran(contexte).COLONNES_AIRPLAY]
	index = table_airplay.model().index(0, titres.index(colonne))
	table_airplay.scrollTo(index)
	position = table_airplay.visualRect(index).center()
	qtbot.mouseClick(table_airplay.viewport(), Qt.MouseButton.LeftButton, pos=position)
	qtbot.mouseDClick(table_airplay.viewport(), Qt.MouseButton.LeftButton, pos=position)


@then("l'accueil n'a demandé aucune fiche")
def aucune_fiche(contexte: Contexte) -> None:
	assert contexte.fiches == []


@when(parsers.parse("j'ouvre dans l'airplay la cellule « {texte} »"))
def ouvrir_cellule(contexte: Contexte, qtbot: QtBot, texte: str) -> None:
	ouvrir_dans(qtbot, ecran(contexte).ui.table_airplay, texte)


@then("l'accueil a demandé les fiches de l'airplay :")
def fiches_de_l_airplay(contexte: Contexte, base_vide: Connexion, datatable: list[list[str]]) -> None:
	"""Chaque fiche par son identifiant en base : le sonore par son titre, les autres par leur nom interne."""
	tables = {"sonore": ("sonores", "titre"), "événement": ("evenements", "nom_interne")}
	tables |= {"séquence": ("sequences", "nom_interne"), "banque": ("banques", "nom_interne")}
	_entetes, *rangees = datatable
	attendues = []
	for genre, nom in ((genre.strip(), nom.strip()) for genre, nom in rangees):
		table_en_base, colonne = tables[genre]
		ligne = base_vide.execute(f"SELECT id FROM {table_en_base} WHERE {colonne} = %s", (nom,)).fetchone()  # noqa: S608
		assert ligne is not None, nom
		attendues.append((genre, int(str(ligne[0])), nom))
	assert contexte.fiches == attendues


@then("le sonore en cours et le prochain sonore ont la même largeur, de part et d'autre de la colonne de l'antenne")
def moities(contexte: Contexte, qtbot: QtBot) -> None:
	"""La colonne de l'antenne est entre eux (https://github.com/dascritch/machincast/issues/24) : ils se partagent
	le reste de la largeur."""
	ui = ecran(contexte).ui
	qtbot.wait(100)
	gauche, colonne, droite = ui.cadre_en_cours.width(), ui.colonne_antenne.width(), ui.cadre_prochain.width()
	assert abs(gauche - droite) <= 1, (gauche, droite)
	espace = ui.sonores.spacing()
	disponible = ui.sonores.geometry().width()
	assert abs((gauche + colonne + droite + 2 * espace) - disponible) <= 1, (gauche, colonne, droite, disponible)
	assert ui.cadre_en_cours.geometry().right() < ui.colonne_antenne.geometry().left()
	assert ui.colonne_antenne.geometry().right() < ui.cadre_prochain.geometry().left()


@then(parsers.re(r"le (?P<lequel>sonore en cours|prochain sonore) a pour emplacement « (?P<texte>[^»]+) »"))
def emplacement_affiche(contexte: Contexte, lequel: str, texte: str) -> None:
	ui = ecran(contexte).ui
	champ = ui.en_cours_emplacement if lequel == "sonore en cours" else ui.prochain_emplacement
	assert champ.text() == texte, champ.text()
	assert champ.isReadOnly()
	# Un long chemin dépasse le champ : l'infobulle le donne en entier.
	assert champ.toolTip() == ("" if texte == "—" else texte), champ.toolTip()
	assert champ.cursorPosition() == len(texte), "la fin du chemin, le nom du fichier, doit rester visible"


@then(parsers.parse("le prochain sonore est sain : « {texte} »"))
def sain(contexte: Contexte, texte: str) -> None:
	assert ecran(contexte).ui.prochain_sain.text() == texte


@then(
	parsers.re(
		r"l'avancement du sonore en cours est (?P<bientot>bientôt )?à « (?P<texte>.+?) »"
		r"(?:, à (?P<valeur>\d+) %)?$"
	)
)
def progression(contexte: Contexte, qtbot: QtBot, bientot: str | None, texte: str, valeur: str | None) -> None:
	"""Sur la barre de progression d'un stream, ou sous la frise d'un fichier
	(https://github.com/dascritch/machincast/issues/230) : le texte montré, et la part jouée."""
	ouvert = ecran(contexte)

	def montre() -> str:
		if ouvert.ui.en_cours_progression.isVisibleTo(ouvert):
			return ouvert.ui.en_cours_progression.text()
		return ouvert.frise_en_cours.legende

	if bientot:
		attendre(qtbot, lambda: montre() == texte)
	assert montre() == texte
	if valeur is not None:
		assert ouvert.avancement_en_cours == int(valeur), ouvert.avancement_en_cours


def table(contexte: Contexte) -> list[dict[str, str]]:
	modele = ecran(contexte).modele_airplay
	colonnes = ecran(contexte).COLONNES_AIRPLAY
	return [
		{cle: modele.item(rangee, colonne).text() for colonne, (cle, _) in enumerate(colonnes)}
		for rangee in range(modele.rowCount())
	]


@then("la table de l'airplay montre :")
def table_attendue(contexte: Contexte, datatable: list[list[str]]) -> None:
	entetes, *lignes = datatable
	attendues = [dict(zip(entetes, (v.strip() for v in valeurs), strict=True)) for valeurs in lignes]
	assert table(contexte) == attendues, table(contexte)


@then(parsers.re(r"l'airplay a (?P<bientot>bientôt )?été lu (?P<nombre>\d+) fois"))
def lectures(contexte: Contexte, qtbot: QtBot, bientot: str | None, nombre: str) -> None:
	if bientot:
		attendre(qtbot, lambda: len(contexte.lectures) == int(nombre))
	else:
		# Laisse arriver les états publiés : aucun ne doit relire l'airplay.
		qtbot.wait(500)
	assert len(contexte.lectures) == int(nombre), contexte.lectures


@then(parsers.parse("la première ligne de la table de l'airplay est « {titre} »"))
def premiere_ligne(contexte: Contexte, titre: str) -> None:
	assert table(contexte)[0]["titre"] == titre, table(contexte)


def fenetre_d_erreur(contexte: Contexte) -> FenetreBaseInjoignable:
	assert len(contexte.fenetres) == 1, contexte.fenetres
	return contexte.fenetres[0]


@then(parsers.parse("il s'arrête avec le code {code:d}, après une fenêtre d'erreur « {titre} »"))
def code_et_fenetre(contexte: Contexte, code: int, titre: str) -> None:
	assert contexte.code == code
	assert fenetre_d_erreur(contexte).windowTitle() == titre


@then("la fenêtre d'erreur explique que l'interface n'est pas utilisable sans sa base de données")
def explication(contexte: Contexte) -> None:
	texte = fenetre_d_erreur(contexte).text()
	assert "n'est pas utilisable" in texte, texte
	assert "base de données" in texte, texte


@then("la fenêtre d'erreur invite à lire le document INSTALL.md du répertoire de MachinCast")
def invitation(contexte: Contexte) -> None:
	texte = fenetre_d_erreur(contexte).informativeText()
	assert str(REPERTOIRE_PROJET / "INSTALL.md") in texte, texte


@then("la fenêtre d'erreur détaille l'erreur de PostgreSQL")
def details(contexte: Contexte) -> None:
	assert "aucune-socket" in fenetre_d_erreur(contexte).detailedText()


@then(parsers.parse("le message « {motif} » est aussi sur la sortie d'erreur"))
def aussi_sur_la_sortie(contexte: Contexte, motif: str) -> None:
	assert motif in contexte.sortie_d_erreur, contexte.sortie_d_erreur


@then(parsers.parse("la fenêtre d'erreur a les boutons « {premier} », « {deuxieme} » et « {troisieme} »"))
def boutons(contexte: Contexte, premier: str, deuxieme: str, troisieme: str) -> None:
	textes = sorted(bouton.text() for bouton in fenetre_d_erreur(contexte).buttons())
	assert textes == sorted([premier, deuxieme, troisieme]), textes


@then("le document INSTALL.md du répertoire de MachinCast est ouvert")
def installation_ouverte(contexte: Contexte) -> None:
	assert contexte.ouverts == [f"file://{REPERTOIRE_PROJET / 'INSTALL.md'}"], contexte.ouverts


@then(parsers.re(r"une fenêtre d'erreur (?P<verdict>peut|ne peut pas) s'ouvrir"))
def verdict_affichage(contexte: Contexte, verdict: str) -> None:
	assert contexte.affichage is (verdict == "peut")


@then(parsers.parse("Machin_interface s'arrête avec le code {code:d}, en signalant « {motif} »"))
def arret_du_binaire(contexte: Contexte, code: int, motif: str) -> None:
	assert contexte.processus is not None
	assert contexte.processus.returncode == code, contexte.processus.stderr
	assert motif in contexte.processus.stderr, contexte.processus.stderr


@then(parsers.re(r"l'écran n'a aucun intitulé (?P<textes>«.+)"))
def sans_intitule_au_bandeau(contexte: Contexte, textes: str) -> None:
	"""https://github.com/dascritch/machincast/issues/191"""
	montres = {etiquette.text() for etiquette in ecran(contexte).findChildren(QLabel)}
	for texte in re.findall(r"« ([^»]+) »", textes):
		assert texte not in montres, texte


@then(parsers.re(r"(?P<quoi>l'état du binaire lecture|l'événement à l'antenne) a pour infobulle « (?P<texte>[^»]+) »"))
def infobulle_du_bandeau(contexte: Contexte, quoi: str, texte: str) -> None:
	ui = ecran(contexte).ui
	etiquette = {"l'état du binaire lecture": ui.etat_lecture, "l'événement à l'antenne": ui.evenement_antenne}[quoi]
	assert etiquette.toolTip() == texte


@then(parsers.parse("l'heure a pour infobulle « {texte} »"))
def infobulle_de_l_heure(contexte: Contexte, texte: str) -> None:
	assert ecran(contexte).ui.heure.toolTip() == texte


# ─── Frises (https://github.com/dascritch/machincast/issues/230) ───


@given(
	parsers.re(
		r"le sonore « (?P<titre>[^»]+) » en base, pour une copie du fichier de test « (?P<fichier>[^»]+) », de"
		r" (?P<duree>\d+) secondes, aux blancs de (?P<debut>[\d,]+) s au début et (?P<fin>[\d,]+) s à la fin,"
		r" sans détection de blanc, aux crossfades de (?P<cd>[\d,]+) s au début et (?P<cf>[\d,]+) s à la fin"
	)
)
def sonore_en_base(
	contexte: Contexte,
	base_vide: Connexion,
	titre: str,
	fichier: str,
	duree: str,
	debut: str,
	fin: str,
	cd: str,
	cf: str,
) -> None:
	copie = contexte.repertoire / fichier
	shutil.copyfile(FICHIERS_SONORES / fichier, copie)
	ligne = base_vide.execute(
		"INSERT INTO sonores (type, emplacement, titre, etat, duree, debut_detecte, fin_detectee, crossfade_debut,"
		" crossfade_fin, audite_le, audit_seuil) VALUES ('fichier', %s, %s, 'actif', %s, %s, %s, %s, %s, now(), -40)"
		" RETURNING id",
		(
			str(copie),
			titre,
			timedelta(seconds=int(duree)),
			timedelta(seconds=secondes(debut)),
			timedelta(seconds=secondes(fin)),
			timedelta(seconds=secondes(cd)),
			timedelta(seconds=secondes(cf)),
		),
	).fetchone()
	assert ligne is not None
	contexte.en_base[titre] = (int(str(ligne[0])), str(copie))


@given(
	parsers.re(
		r"la banque « (?P<nom>[^»]+) » en base, qui retire les blancs et impose un crossfade de fin de"
		r" (?P<cf>[\d,]+) s, avec « (?P<titre>[^»]+) »"
	)
)
def banque_en_base(contexte: Contexte, base_vide: Connexion, nom: str, cf: str, titre: str) -> None:
	ligne = base_vide.execute(
		"INSERT INTO banques (nom_interne, mode, detection_blancs, crossfade_fin_regle, crossfade_fin)"
		" VALUES (%s, 'aleatoire', true, 'impose', %s) RETURNING id",
		(nom, timedelta(seconds=secondes(cf))),
	).fetchone()
	assert ligne is not None
	contexte.banques[nom] = int(str(ligne[0]))
	base_vide.execute(
		"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, 1)",
		(ligne[0], contexte.en_base[titre][0]),
	)


@given(
	parsers.re(
		r"le binaire lecture diffuse « (?P<titre>[^»]+) », (?:de la banque « (?P<banque>[^»]+) »|sans banque),"
		r" commencé à (?P<debut>[\d:]+), joué depuis (?P<position>[\d,]+) seconde"
	)
)
@when(
	parsers.re(
		r"le binaire lecture diffuse « (?P<titre>[^»]+) », (?:de la banque « (?P<banque>[^»]+) »|sans banque),"
		r" commencé à (?P<debut>[\d:]+), joué depuis (?P<position>[\d,]+) seconde"
	)
)
def diffuse_en_base(contexte: Contexte, titre: str, banque: str | None, debut: str, position: str) -> None:
	"""Un sonore en base ; la durée annoncée par la socket est celle de la partie jouée, sans les blancs retirés."""
	identifiant, chemin = contexte.en_base[titre]
	commence = a(debut)
	contexte.en_cours = {
		"sonore": identifiant,
		"type": "fichier",
		"artiste": None,
		"titre": titre,
		"evenement": "Fil de nuit",
		"debut": commence.isoformat(),
		"duree": 1.0,
		"fin_estimee": (commence + timedelta(seconds=1.0)).isoformat(),
		"emplacement": chemin,
		"position": secondes(position),
		"progression": round(secondes(position), 3),
		"banque": banque,
		"banque_id": contexte.banques.get((banque) or ("")),
	}
	publier(contexte)


@given(parsers.parse("le prochain sonore est « {titre} » en base, sans banque"))
def prochain_en_base(contexte: Contexte, titre: str) -> None:
	identifiant, chemin = contexte.en_base[titre]
	contexte.prochain = {
		"sonore": identifiant,
		"type": "fichier",
		"artiste": None,
		"titre": titre,
		"evenement": "Fil de jour",
		"debut_estime": a("20:03:34").isoformat(),
		"duree": 2.0,
		"fin_estimee": a("20:03:36").isoformat(),
		"emplacement": chemin,
		"sain": True,
	}
	publier(contexte)


def _frise(contexte: Contexte, lequel: str) -> Frise:
	ouvert = ecran(contexte)
	if lequel == "sonore en cours":
		return ouvert.frise_en_cours
	return ouvert.frise_prochain


@then(
	parsers.re(
		r"le (?P<lequel>sonore en cours|prochain sonore) a une frise(?P<sans_tete>, sans tête de lecture)?"
		r"(?P<sans_barre>, sans barre de progression)?$"
	)
)
def a_une_frise(contexte: Contexte, qtbot: QtBot, lequel: str, sans_tete: str | None, sans_barre: str | None) -> None:
	ouvert = ecran(contexte)
	frise = _frise(contexte, lequel)
	attendre(qtbot, lambda: frise.isVisibleTo(ouvert))
	if sans_barre is not None:
		assert not ouvert.ui.en_cours_progression.isVisibleTo(ouvert)
	if sans_tete is not None:
		assert frise.tete is None


@then(
	parsers.re(r"le (?P<lequel>sonore en cours|prochain sonore) (?:a une barre de progression, sans|n'a pas de) frise")
)
def sans_frise(contexte: Contexte, lequel: str) -> None:
	ouvert = ecran(contexte)
	assert not _frise(contexte, lequel).isVisibleTo(ouvert)
	if lequel == "sonore en cours":
		assert ouvert.ui.en_cours_progression.isVisibleTo(ouvert)


@then(parsers.parse("la frise du sonore en cours montre bientôt les zones :"))
def zones_en_cours(contexte: Contexte, qtbot: QtBot, datatable: list[list[str]]) -> None:
	frise = _frise(contexte, "sonore en cours")
	attendre(qtbot, lambda: frise.plan is not None)
	assert frise.plan is not None
	lues = [
		[
			zone.nom,
			f"{zone.debut:.2f}".replace(".", ","),
			f"{zone.fin:.2f}".replace(".", ","),
			zone.hachures,
			zone.infobulle,
		]
		for zone in frise.plan.zones()
	]
	assert lues == [[cellule.strip() for cellule in rangee] for rangee in datatable[1:]]


@then(parsers.re(r"la frise du prochain sonore montre bientôt les zones (?P<noms>«.+»), ses blancs joués à l'antenne"))
def zones_du_prochain(contexte: Contexte, qtbot: QtBot, noms: str) -> None:
	frise = _frise(contexte, "prochain sonore")
	attendre(qtbot, lambda: frise.plan is not None)
	assert frise.plan is not None
	zones = frise.plan.zones()
	assert [zone.nom for zone in zones] == re.findall(r"« ([^»]+) »", noms)
	assert {zone.hachures for zone in zones if zone.nom.startswith("blanc")} == {"pâles"}


@then(
	parsers.parse(
		"la tête de lecture de la frise du sonore en cours est à {position} seconde, la position jouée comptée depuis"
		" le début de la lecture"
	)
)
def tete(contexte: Contexte, qtbot: QtBot, position: str) -> None:
	frise = _frise(contexte, "sonore en cours")
	attendre(qtbot, lambda: (frise.tete is not None) and (abs(frise.tete - secondes(position)) < 0.001))


@when(parsers.re(r"la forme d'onde de la frise du (?P<lequel>sonore en cours|prochain sonore) est bientôt complète"))
@then(parsers.re(r"la forme d'onde de la frise du (?P<lequel>sonore en cours|prochain sonore) est bientôt complète"))
def forme_complete(contexte: Contexte, qtbot: QtBot, lequel: str) -> None:
	frise = _frise(contexte, lequel)

	def finie() -> bool:
		return (frise.forme is not None) and (frise.forme.finie)

	attendre(qtbot, finie)
	assert (frise.forme is not None) and (frise.forme.erreur is None), frise.remarque()
	assert max(frise.forme.amplitudes(0.6, 1.4)) > 0.4
	if lequel == "prochain sonore":
		contexte.forme_du_prochain = frise.forme


@then("la frise du sonore en cours dessine bientôt la forme d'onde qu'avait le prochain sonore")
def meme_forme(contexte: Contexte, qtbot: QtBot) -> None:
	frise = _frise(contexte, "sonore en cours")
	assert contexte.forme_du_prochain is not None
	attendre(qtbot, lambda: frise.forme is contexte.forme_du_prochain)


@when("je clique au milieu de la frise du sonore en cours")
def cliquer_la_frise(contexte: Contexte, qtbot: QtBot) -> None:
	frise = _frise(contexte, "sonore en cours")
	attendre(qtbot, lambda: frise.isVisibleTo(ecran(contexte)))
	contexte.positions_demandees = []
	frise.placee.connect(contexte.positions_demandees.append)
	avant = frise.tete
	qtbot.mouseClick(frise, Qt.MouseButton.LeftButton, pos=frise.rect().center())
	assert frise.tete == avant


@then("la frise du sonore en cours n'a demandé aucune position")
def aucune_position(contexte: Contexte) -> None:
	assert contexte.positions_demandees == []


@then(parsers.parse("le plan du sonore « {titre} » n'a été lu qu'une fois en base"))
def plan_lu_une_fois(contexte: Contexte, titre: str) -> None:
	assert contexte.plans_lus.count(contexte.en_base[titre][0]) == 1, contexte.plans_lus


def _haut(contexte: Contexte, widget: QWidget) -> int:
	"""L'ordonnée du haut d'un élément, dans l'écran."""
	return widget.mapTo(ecran(contexte), QPoint(0, 0)).y()


@then("les frises du sonore en cours et du prochain sonore sont au-dessus de leur titre, à la même hauteur")
def frises_en_tete(contexte: Contexte, qtbot: QtBot) -> None:
	ouvert = ecran(contexte)
	en_cours, prochain = ouvert.frise_en_cours, ouvert.frise_prochain
	attendre(qtbot, lambda: (en_cours.isVisible()) and (prochain.isVisible()))
	assert _haut(contexte, en_cours) == _haut(contexte, prochain)
	assert _haut(contexte, en_cours) + en_cours.height() <= _haut(contexte, ouvert.ui.en_cours_titre)
	assert _haut(contexte, prochain) + prochain.height() <= _haut(contexte, ouvert.ui.prochain_titre)


@then("le temps qui reste au sonore en cours est écrit au milieu de sa frise, sans autre ligne sous elle")
def reste_dans_la_frise(contexte: Contexte) -> None:
	ouvert = ecran(contexte)
	frise = ouvert.frise_en_cours
	assert frise.legende.startswith("reste "), frise.legende
	assert frise.fond_de_la_legende() is not None
	assert not hasattr(ouvert.ui, "en_cours_reste")
	espace = ouvert.ui.disposition_en_cours.spacing()
	assert _haut(contexte, frise) + frise.height() + espace >= _haut(contexte, ouvert.ui.en_cours_titre) - 1


@when("la colonne de l'antenne est plus haute qu'il ne lui faut")
def colonne_haute(contexte: Contexte, qtbot: QtBot) -> None:
	"""Les frises font les sonores plus hauts que la colonne de l'antenne ne le demande : il y a de la hauteur à
	prendre. Sans assez de hauteur, l'écran s'allonge, comme sur un poste où les textes sont plus grands."""
	ouvert = ecran(contexte)
	colonne = ouvert.ui.colonne_antenne
	ouvert.ui.cadre_en_cours.setMinimumHeight(colonne.sizeHint().height() + 2 * HAUTEUR)
	attendre(qtbot, lambda: colonne.height() > colonne.sizeHint().height() + HAUTEUR)


@then("le VU-mètre de l'antenne occupe sa colonne : ses voyants gardent leur hauteur, il prend le reste")
def vumetre_dans_sa_colonne(contexte: Contexte) -> None:
	ui = ecran(contexte).ui
	for voyant in (ui.voyant_saturation, ui.voyant_silence, ui.etat_moniteur):
		# Un texte qui passe à la ligne a la hauteur de ses lignes, à sa largeur.
		attendue = voyant.sizeHint().height()
		if voyant.hasHeightForWidth():
			attendue = voyant.heightForWidth(voyant.width())
		assert voyant.height() == attendue, (voyant.objectName(), voyant.height(), attendue)
	assert ui.colonne_antenne.height() == ui.cadre_en_cours.height()
