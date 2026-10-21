"""Captures d'écran du guide utilisateur (https://github.com/dascritch/machincast/issues/128).

« bin/Machin dev-captures [REPERTOIRE] » lance ce module, depuis le répertoire de MachinCast, avec le Python du venv :
il remplit la base de TEST d'une démonstration, « Radio Exemple », ouvre l'interface hors de l'écran
(QT_QPA_PLATFORM=offscreen), à une heure fixe, le mercredi 21 octobre 2026 à 09:41:30, et enregistre chaque écran de
CAPTURES en PNG, dans doc/captures par défaut. La base de production n'est jamais ouverte : la connexion est celle des
tests (tests.base_test), sur la base de test de la configuration des tests. Ses fichiers sonores sont des copies d'un
fichier de test, dans DEMONSTRATION, un répertoire temporaire propre à ce module. L'état de la diffusion vient d'une
socket d'état publiée ici même ; aucun Machin lecture ne tourne.

Les captures sont reproductibles : même heure, mêmes données, même style de Qt (Fusion). Refaire les captures après
un changement d'écran, puis les relire avant de les livrer avec le ticket.
"""

import dataclasses
import logging
import os
import shutil
import sys
import tempfile
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["TZ"] = "Europe/Paris"
time.tzset()

import psycopg  # noqa: E402
import pytest  # noqa: E402
from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtWidgets import QApplication, QGroupBox, QWidget  # noqa: E402

from machincast import audio as sorties_audio  # noqa: E402
from machincast.base import Role, connecter  # noqa: E402
from machincast.configuration import Crossfades, Metadonnees  # noqa: E402
from machincast.horloge import HorlogeFixe  # noqa: E402
from machincast.interface import colonnes, depliable  # noqa: E402
from machincast.interface.calendrier import Calendrier  # noqa: E402
from machincast.interface.fenetre import FenetrePrincipale  # noqa: E402
from machincast.interface.preecoute import FenetrePreecoute  # noqa: E402
from machincast.interface.preferences import FenetrePreferences, Reglages  # noqa: E402
from machincast.interface.recherche import EcranRecherche  # noqa: E402
from machincast.interface.simulation import EcranSimulation, bilan  # noqa: E402
from machincast.interface.suggestions import FenetreSuggestions, Manques  # noqa: E402
from machincast.lecture.etat import SocketEtat  # noqa: E402
from machincast.lecture.simulation import simuler  # noqa: E402
from tests.base_test import (  # noqa: E402
	configuration_test,
	connexion_test,
	parametres_base_test,
	purger_base,
	reinitialiser_base,  # noqa: E402
)
from tests.sons import FICHIERS_SONORES  # noqa: E402

journal = logging.getLogger("machincast.captures")

Connexion = psycopg.Connection[tuple[object, ...]]
RACINE = Path(__file__).resolve().parents[1]
CAPTURES_DU_GUIDE = RACINE / "doc" / "captures"
DEMONSTRATION = Path(tempfile.gettempdir()) / "machincast-demonstration"
"""Les fichiers sonores de la démonstration : des copies d'un fichier de test, jamais un fichier de l'utilisateur."""
MAINTENANT = datetime.fromisoformat("2026-10-21T09:41:30").astimezone()
DEBUT_DE_L_HISTORIQUE = datetime.fromisoformat("2026-10-19T00:00:00").astimezone()
LARGEUR, HAUTEUR = 1280, 800
ATTENTE = 5.0
"""Secondes qu'un écran a pour se remplir."""
PERIPHERIQUES = (
	sorties_audio.Peripherique("antenne", "Carte son de l'antenne"),
	sorties_audio.Peripherique("casque", "Casque de la régie"),
)
"""Les périphériques de sortie que montre la démonstration, à la place de ceux du poste."""
SEMAINE = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
OUVRES = SEMAINE[:5]

CAPTURES = (
	"accueil",
	"pour-bien-demarrer",
	"menu-diffusion",
	"liste-evenements",
	"liste-sonores",
	"menu-colonnes",
	"fiche-evenement",
	"fiche-sequence",
	"fiche-banque",
	"fiche-sonore",
	"calendrier",
	"simulation",
	"recherche",
	"incidents",
	"preferences",
	"preecoute",
)
"""Les captures, par nom de fichier sans extension, dans l'ordre où elles sont prises."""


@dataclass(frozen=True)
class Sonore:
	artiste: str | None
	titre: str
	duree: int
	"""En secondes."""
	dossier: str
	etat: str = "actif"
	metadonnees: str = "{}"


SONORES = {
	"cafe": Sonore(
		"Les Gaufres",
		"Café à minuit",
		214,
		"lourde",
		metadonnees='{"album": "Nuits courtes", "annee": "2019", "genre": "Chanson", "label": "Disques du Canal"}',
	),
	"toulouse": Sonore(
		"Nina Lune", "Toulouse sous la pluie", 242, "lourde", metadonnees='{"annee": "2022", "genre": "Pop"}'
	),
	"brique": Sonore("Orchestre du Canal", "Brique rose", 228, "lourde", metadonnees='{"genre": "Jazz"}'),
	"nuit": Sonore("Café Noir", "Nuit blanche", 200, "normale", metadonnees='{"genre": "Rock"}'),
	"garonne": Sonore("Les Pavés", "Garonne", 255, "normale"),
	"vinyles": Sonore("Sœurs Volantes", "Vieux vinyles", 310, "rare"),
	"nocturne": Sonore("Brume", "Nocturne n° 3", 400, "nuit"),
	"identifiant": Sonore("Radio Exemple", "Identifiant", 8, "habillage"),
	"matin": Sonore("Radio Exemple", "Jingle du matin", 6, "habillage"),
	"pub-debut": Sonore("Radio Exemple", "Début de publicité", 5, "habillage"),
	"boulangerie": Sonore(None, "Spot de la boulangerie du port", 30, "publicite"),
	"librairie": Sonore(None, "Spot de la librairie des Carmes", 30, "publicite"),
	"abime": Sonore("Les Gaufres", "Démo abîmée", 180, "normale", "errone"),
	"nouveau": Sonore(None, "nouvel-arrivage", 190, "lourde", "apercu"),
}
BANQUES = {
	"identifiant": ("Identifiant station", None, "aleatoire", True, ["identifiant"], None),
	"lourde": ("Musique rotation lourde", None, "aleatoire", False, ["cafe", "toulouse", "brique"], "lourde"),
	"normale": ("Musique rotation normale", None, "aleatoire", False, ["nuit", "garonne", "abime"], "normale"),
	"rare": ("Musique rotation rare", None, "aleatoire", False, ["vinyles"], "rare"),
	"nuit": ("Musique rotation de nuit", "La nuit de Radio Exemple", "aleatoire", False, ["nocturne"], "nuit"),
	"publicite": ("Publicité", None, "sequentiel", True, ["boulangerie", "librairie"], None),
}
"""Nom interne, nom public, mode, « ne pas répéter », sonores et dossier indexé de chaque banque."""


@dataclass
class Demonstration:
	"""Les identifiants en base de la démonstration."""

	sonores: dict[str, int]
	banques: dict[str, int]
	evenements: dict[str, int]
	sequence: int
	passages: list[tuple[datetime, datetime, str, str | None, str]]
	"""Début, fin, sonore, banque et événement de chaque passage de l'historique, le dernier en cours."""


def _un(connexion: Connexion, requete: str, parametres: tuple[object, ...]) -> int:
	ligne = connexion.execute(requete, parametres).fetchone()  # type: ignore[arg-type]
	assert ligne is not None
	return int(str(ligne[0]))


def _emplacement(cle: str) -> Path:
	sonore = SONORES[cle]
	nom = sonore.titre
	if sonore.artiste is not None:
		nom = f"{sonore.artiste} - {sonore.titre}"
	return DEMONSTRATION / sonore.dossier / f"{nom}.flac"


def remplir(connexion: Connexion) -> Demonstration:
	"""La démonstration, dans la base de test vide."""
	# fichier de MachinCast : les copies de fichier de test de la démonstration précédente.
	shutil.rmtree(DEMONSTRATION, ignore_errors=True)
	sonores = {}
	for cle, sonore in SONORES.items():
		chemin = _emplacement(cle)
		chemin.parent.mkdir(parents=True, exist_ok=True)
		shutil.copyfile(FICHIERS_SONORES / "sain.flac", chemin)
		verifie = None
		if sonore.etat == "actif":
			verifie = MAINTENANT - timedelta(days=2)
		sonores[cle] = _un(
			connexion,
			"INSERT INTO sonores (type, emplacement, artiste, titre, etat, duree, metadonnees_musicales, type_mime,"
			" verifie_le) VALUES ('fichier', %s, %s, %s, %s, %s, %s, 'audio/flac', %s) RETURNING id",
			(
				str(chemin),
				sonore.artiste,
				sonore.titre,
				sonore.etat,
				timedelta(seconds=sonore.duree),
				sonore.metadonnees,
				verifie,
			),
		)
	marque = _un(
		connexion,
		"INSERT INTO marques_pages_streams (nom, url) VALUES ('Studio mobile', 'https://flux.radio-exemple.test/mobile')"
		" RETURNING id",
		(),
	)
	banques = {}
	for cle, (nom, nom_public, mode, ne_pas_repeter, membres, dossier) in BANQUES.items():
		banques[cle] = _un(
			connexion,
			"INSERT INTO banques (nom_interne, nom_public, mode, ne_pas_repeter, crossfade_fin_regle, crossfade_fin)"
			" VALUES (%s, %s, %s, %s, 'a_defaut', '2 s') RETURNING id",
			(nom, nom_public, mode, ne_pas_repeter),
		)
		for position, membre in enumerate(membres, start=1):
			connexion.execute(
				"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, %s)",
				(banques[cle], sonores[membre], position),
			)
		if dossier is not None:
			connexion.execute(
				"INSERT INTO banques_repertoires (banque_id, repertoire) VALUES (%s, %s)",
				(banques[cle], str(DEMONSTRATION / dossier)),
			)
	sequence = _un(
		connexion,
		"INSERT INTO sequences (nom_interne, nom_public) VALUES ('Passage pub', 'Les partenaires de Radio Exemple')"
		" RETURNING id",
		(),
	)
	for position, (colonne, valeur) in enumerate(
		(
			("sonore_id", sonores["pub-debut"]),
			("banque_id", banques["publicite"]),
			("banque_id", banques["publicite"]),
			("banque_id", banques["identifiant"]),
		),
		start=1,
	):
		connexion.execute(
			f"INSERT INTO sequences_elements (sequence_id, position, {colonne}) VALUES (%s, %s, %s)",  # noqa: S608
			(sequence, position, valeur),
		)
	evenements = _evenements(connexion, sonores, banques, sequence)
	stream = _un(
		connexion,
		"INSERT INTO sonores (type, marque_page_id, titre, etat, secours_evenement_id)"
		" VALUES ('stream', %s, 'Studio mobile', 'actif', %s) RETURNING id",
		(marque, evenements["secours"]),
	)
	connexion.execute(
		"INSERT INTO evenements_elements (evenement_id, position, sonore_id) VALUES (%s, 1, %s)",
		(evenements["marche"], stream),
	)
	passages = _historique(connexion, sonores, banques, evenements)
	_incidents(connexion, sonores, evenements)
	return Demonstration(sonores, banques, evenements, sequence, passages)


def _evenements(
	connexion: Connexion, sonores: dict[str, int], banques: dict[str, int], sequence: int
) -> dict[str, int]:
	jour = datetime.fromisoformat("2026-10-01T00:00").astimezone()

	def creer(
		nom: str, nom_public: str | None, priorite: str, debut: timedelta | None, fin: timedelta | None, jours: tuple
	) -> int:
		return _un(
			connexion,
			"INSERT INTO evenements (nom_interne, nom_public, priorite, debut, fin, jours_recurrence)"
			" VALUES (%s, %s, %s, %s, %s, %s::jour_semaine[]) RETURNING id",
			(
				nom,
				nom_public,
				priorite,
				None if debut is None else jour + debut,
				None if fin is None else jour + fin,
				list(jours),
			),
		)

	evenements = {
		"jour": creer("Fil de jour", None, "fil_musical", None, None, ()),
		"nuit": creer("Fil de nuit", None, "fil_musical", timedelta(hours=0), timedelta(hours=6), SEMAINE),
		"matinale": creer(
			"Matinale", "La Matinale de Radio Exemple", "emission", timedelta(hours=7), timedelta(hours=9), OUVRES
		),
		"journal": creer("Le Journal", None, "emission", timedelta(hours=12), timedelta(hours=12, minutes=15), OUVRES),
		"secours": creer("Secours studio", None, "secours", None, None, ()),
	}
	samedi = datetime.fromisoformat("2026-10-24T10:00").astimezone()
	evenements["marche"] = _un(
		connexion,
		"INSERT INTO evenements (nom_interne, nom_public, priorite, debut, fin)"
		" VALUES ('Direct du marché', 'En direct du marché', 'special', %s, %s) RETURNING id",
		(samedi, samedi + timedelta(hours=2)),
	)
	listes = {
		"jour": [("banque", "identifiant"), ("banque", "lourde"), ("banque", "normale"), ("banque", "lourde")],
		"nuit": [("banque", "identifiant"), ("banque", "nuit")],
		"matinale": [
			("sonore", "matin"),
			("banque", "lourde"),
			("sequence", ""),
			("banque", "normale"),
			("banque", "rare"),
		],
		"journal": [("sonore", "identifiant"), ("banque", "normale")],
		"secours": [("banque", "normale")],
	}
	ajoutes = {"jour": [("banque", "rare")]}
	for cle, elements in listes.items():
		for position, (genre, valeur) in enumerate(elements + ajoutes.get(cle, []), start=1):
			colonne, identifiant = {
				"banque": ("banque_id", banques.get(valeur)),
				"sonore": ("sonore_id", sonores.get(valeur)),
				"sequence": ("sequence_id", sequence),
			}[genre]
			connexion.execute(
				f"INSERT INTO evenements_elements (evenement_id, position, {colonne}) VALUES (%s, %s, %s)",  # noqa: S608
				(evenements[cle], position, identifiant),
			)
	return evenements


def _programme(instant: datetime) -> str:
	"""L'événement à l'antenne à l'instant, d'après la grille de la démonstration."""
	ouvre = instant.weekday() < 5
	heure = instant.hour + instant.minute / 60
	if heure < 6:
		return "nuit"
	if (ouvre) and (7 <= heure < 9):
		return "matinale"
	if (ouvre) and (12 <= heure < 12.25):
		return "journal"
	return "jour"


ROTATIONS = {
	"jour": ["identifiant", "lourde", "normale", "lourde", "rare"],
	"nuit": ["identifiant", "nuit"],
	"matinale": ["matin", "lourde", "pub-debut", "publicite", "publicite", "identifiant", "normale", "rare"],
	"journal": ["identifiant", "normale"],
}
"""Ce que chaque événement fait passer, en boucle : une banque, ou un sonore placé directement."""


def _historique(
	connexion: Connexion, sonores: dict[str, int], banques: dict[str, int], evenements: dict[str, int]
) -> list[tuple[datetime, datetime, str, str | None, str]]:
	"""Les passages, du lundi 19 octobre à maintenant, comme les aurait notés Machin lecture : le dernier est en
	cours."""
	tours = dict.fromkeys(BANQUES, 0)
	positions = dict.fromkeys(ROTATIONS, 0)
	jouables = {cle: [m for m in membres if SONORES[m].etat == "actif"] for cle, (*_, membres, _d) in BANQUES.items()}
	passages: list[tuple[datetime, datetime, str, str | None, str]] = []
	instant = DEBUT_DE_L_HISTORIQUE
	while instant <= MAINTENANT:
		evenement = _programme(instant)
		rotation = ROTATIONS[evenement]
		element = rotation[positions[evenement] % len(rotation)]
		positions[evenement] += 1
		banque: str | None = None
		sonore = element
		if element in BANQUES:
			banque = element
			membres = jouables[element]
			sonore = membres[tours[element] % len(membres)]
			tours[element] += 1
		fin = instant + timedelta(seconds=SONORES[sonore].duree)
		passages.append((instant, fin, sonore, banque, evenement))
		instant = fin
	lignes = []
	for debut, fin, sonore, banque, evenement in passages:
		passage = uuid.uuid4()
		commun = (
			passage,
			sonores[sonore],
			None if banque is None else banques[banque],
			evenements[evenement],
			str(_emplacement(sonore)),
			SONORES[sonore].artiste,
			SONORES[sonore].titre,
		)
		lignes.append((*commun, "debut", debut, None, None))
		if fin <= MAINTENANT:
			lignes.append((*commun, "fin", fin, fin - debut, True))
	with connexion.cursor() as curseur:
		curseur.executemany(
			"INSERT INTO airplay (passage_id, sonore_id, banque_id, evenement_id, emplacement, artiste, titre,"
			" type_ligne, horodatage, duree_diffusee, sans_incident)"
			" VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
			lignes,
		)
	return passages


def _incidents(connexion: Connexion, sonores: dict[str, int], evenements: dict[str, int]) -> None:
	entrees = [
		(
			"2026-10-20T14:12:05",
			"incident",
			"fichier introuvable",
			f"{_emplacement('garonne')} : aucun fichier",
			"garonne",
			"jour",
		),
		(
			"2026-10-20T16:40:12",
			"alerte",
			"fichier modifié",
			f"{_emplacement('nuit')} : taille changée",
			"nuit",
			"jour",
		),
		("2026-10-21T03:10:00", "alerte", "silence", "rien à diffuser dans le fil musical", None, "nuit"),
		(
			"2026-10-21T07:00:00",
			"info",
			"début d'événement",
			"« Matinale », émission, de 07:00 à 09:00",
			None,
			"matinale",
		),
		("2026-10-21T08:20:31", "info", "interruption manuelle", "du sonore « Nuit blanche »", "nuit", "matinale"),
		("2026-10-21T09:00:00", "info", "fin d'événement", "« Matinale »", None, "matinale"),
	]
	for horodatage, niveau, nature, message, sonore, evenement in entrees:
		connexion.execute(
			"INSERT INTO log (horodatage, niveau, nature, message, sonore_id, evenement_id)"
			" VALUES (%s, %s, %s, %s, %s, %s)",
			(
				datetime.fromisoformat(horodatage).astimezone(),
				niveau,
				nature,
				message,
				None if sonore is None else sonores[sonore],
				evenements[evenement],
			),
		)


# ─── État de la diffusion ──────────────────────────────────


def _affiche(demonstration: Demonstration, rang: int, cle_debut: str) -> dict[str, object]:
	debut, fin, sonore, banque, evenement = demonstration.passages[rang]
	modele = SONORES[sonore]
	texte = modele.titre
	if modele.artiste is not None:
		texte = f"{modele.artiste} – {modele.titre}"
	return {
		"sonore": demonstration.sonores[sonore],
		"type": "fichier",
		"artiste": modele.artiste,
		"titre": modele.titre,
		"emplacement": str(_emplacement(sonore)),
		"evenement": {"jour": "Fil de jour", "nuit": "Fil de nuit", "matinale": "Matinale"}.get(evenement, evenement),
		"evenement_id": demonstration.evenements[evenement],
		"evenement_debut": None,
		"evenement_fin": None,
		"sequence": None,
		"sequence_id": None,
		"banque": None if banque is None else BANQUES[banque][0],
		"banque_id": None if banque is None else demonstration.banques[banque],
		cle_debut: debut.isoformat(),
		"duree": float(modele.duree),
		"fin_estimee": fin.isoformat(),
		"texte_public": texte,
		"coupe_par": None,
		"coupe_par_id": None,
	}


def publier(socket: SocketEtat, demonstration: Demonstration) -> None:
	"""L'état qu'aurait publié Machin lecture à MAINTENANT : le dernier passage en cours, le suivant réservé."""
	en_cours = _affiche(demonstration, -1, "debut")
	debut = demonstration.passages[-1][0]
	position = (MAINTENANT - debut).total_seconds()
	en_cours |= {"position": position, "progression": round(position / float(str(en_cours["duree"])), 3)}
	fin = demonstration.passages[-1][1]
	prochain = {
		**_affiche(demonstration, -6, "debut_estime"),
		"debut_estime": fin.isoformat(),
		"sain": True,
	}
	prochain["fin_estimee"] = (fin + timedelta(seconds=float(str(prochain["duree"])))).isoformat()
	socket.publier(
		{"horodatage": MAINTENANT.isoformat(), "etat": "diffusion", "en_cours": en_cours, "prochain": prochain}
	)


# ─── Captures ──────────────────────────────────────────────


def attendre(condition: Callable[[], bool], delai: float = ATTENTE) -> None:
	limite = time.monotonic() + delai
	while (not condition()) and (time.monotonic() < limite):
		QApplication.processEvents()
		time.sleep(0.02)
	for _ in range(5):
		QApplication.processEvents()


def enregistrer(widget: QWidget, chemin: Path) -> Path:
	attendre(lambda: False, 0.2)
	assert widget.grab().save(str(chemin), "PNG"), chemin
	journal.info(f"capture : {chemin}")
	return chemin


def _onglet(fenetre: FenetrePrincipale, titre: str) -> None:
	onglets = fenetre.ui.onglets
	(indice,) = [indice for indice in range(onglets.count()) if onglets.tabText(indice) == titre]
	onglets.setCurrentIndex(indice)


def _ecran[T](fenetre: FenetrePrincipale, genre: type[T]) -> T:
	onglets = fenetre.ui.onglets
	(trouve,) = [ecran for indice in range(onglets.count()) if isinstance(ecran := onglets.widget(indice), genre)]
	return trouve


def _fermer_l_onglet(fenetre: FenetrePrincipale) -> None:
	"""L'onglet capturé se ferme : la barre d'onglets ne déborde pas dans les captures suivantes."""
	fenetre._fermer(fenetre.ui.onglets.currentIndex())
	attendre(lambda: False, 0.1)


def _deplier(fenetre: FenetrePrincipale, titre: str) -> None:
	ouvert = fenetre.ui.onglets.currentWidget()
	assert ouvert is not None
	(groupe,) = [groupe for groupe in ouvert.findChildren(QGroupBox) if groupe.property(depliable.TITRE) == titre]
	depliable.montrer(groupe, True)


def produire(repertoire: Path) -> dict[str, Path]:
	"""Les captures de CAPTURES, dans le répertoire, sur la base de test déjà migrée, qu'elles remplacent."""
	repertoire.mkdir(parents=True, exist_ok=True)
	application = QApplication.instance()
	if application is None:
		application = QApplication(sys.argv[:1])
	assert isinstance(application, QApplication)
	application.setStyle("Fusion")
	with connexion_test() as proprietaire:
		purger_base(proprietaire)
		demonstration = remplir(proprietaire)
	travail = Path(tempfile.mkdtemp(prefix="machincast-captures-"))
	configuration = travail / "machincast.toml"
	# Les colonnes d'origine, ajustées au contenu : jamais la disposition gardée par le compte qui fait les captures.
	vues, colonnes.FICHIER = colonnes.FICHIER, travail / "vues.ini"
	shutil.copyfile(RACINE / "tests" / "configuration-test.toml", configuration)
	socket = SocketEtat(travail / "lecture.sock")
	socket.ouvrir()
	publier(socket, demonstration)
	horloge = HorlogeFixe(MAINTENANT)
	connexion = connecter(*parametres_base_test(), Role.INTERFACE)
	audio = dataclasses.replace(configuration_test().audio, peripherique="antenne", preecoute="casque")
	peripheriques, sorties_audio.peripheriques = sorties_audio.peripheriques, lambda _sortie: list(PERIPHERIQUES)
	fenetre = FenetrePrincipale(connexion, socket.chemin, horloge, configuration=configuration, audio=audio)
	captures: dict[str, Path] = {}

	def prendre(nom: str, widget: QWidget) -> None:
		captures[nom] = enregistrer(widget, repertoire / f"{nom}.png")

	try:
		fenetre.resize(LARGEUR, HAUTEUR)
		fenetre.show()
		attendre(lambda: fenetre.accueil.ui.etat_lecture.text() == "En diffusion")
		prendre("accueil", fenetre)
		suggestions = FenetreSuggestions(
			Manques(True, ("Identifiant station", "Musique rotation lourde", "Musique rotation de nuit")), fenetre
		)
		suggestions.show()
		prendre("pour-bien-demarrer", suggestions)
		suggestions.close()
		fenetre.menu_diffusion.aboutToShow.emit()
		fenetre.menu_diffusion.popup(fenetre.mapToGlobal(QPoint(200, 30)))
		attendre(lambda: fenetre.menu_diffusion.isVisible())
		prendre("menu-diffusion", fenetre.menu_diffusion)
		fenetre.menu_diffusion.hide()
		_onglet(fenetre, "Événements")
		prendre("liste-evenements", fenetre)
		fenetre.ouvrir_liste("Sonores")
		prendre("liste-sonores", fenetre)
		(sonores,) = [liste for liste in fenetre.listes if fenetre._titres[liste] == "Sonores"]
		menu = sonores.colonnes.menu()
		menu.popup(fenetre.mapToGlobal(QPoint(400, 110)))
		attendre(lambda: menu.isVisible())
		prendre("menu-colonnes", menu)
		menu.hide()
		for nom, genre, identifiant in (
			("fiche-evenement", "événement", demonstration.evenements["matinale"]),
			("fiche-sequence", "séquence", demonstration.sequence),
			("fiche-banque", "banque", demonstration.banques["lourde"]),
			("fiche-sonore", "sonore", demonstration.sonores["cafe"]),
		):
			fenetre._ouvrir(genre, identifiant, "")
			if genre == "sonore":
				_deplier(fenetre, "Métadonnées")
			prendre(nom, fenetre)
			_fermer_l_onglet(fenetre)
		fenetre._ouvrir_calendrier()
		attendre(lambda: _ecran(fenetre, Calendrier).isVisible())
		prendre("calendrier", fenetre)
		_fermer_l_onglet(fenetre)
		_simuler(fenetre)
		prendre("simulation", fenetre)
		_fermer_l_onglet(fenetre)
		fenetre._ouvrir_recherche()
		_ecran(fenetre, EcranRecherche).champ.setText("café")
		prendre("recherche", fenetre)
		_fermer_l_onglet(fenetre)
		_onglet(fenetre, "Incidents")
		prendre("incidents", fenetre)
		preferences = FenetrePreferences(
			Reglages(Crossfades(), audio.peripherique, audio.preecoute), audio.sortie, fenetre
		)
		preferences.show()
		prendre("preferences", preferences)
		preferences.close()
		preecoute = FenetrePreecoute(connexion, audio, configuration)
		preecoute.ecouter_l_antenne()
		preecoute.show()
		prendre("preecoute", preecoute)
		preecoute.close()
	finally:
		fenetre.close()
		connexion.close()
		socket.fermer()
		sorties_audio.peripheriques = peripheriques
		colonnes.FICHIER = vues
		# fichier de MachinCast : le répertoire de travail des captures, sa configuration et sa socket.
		shutil.rmtree(travail, ignore_errors=True)
	return captures


def _simuler(fenetre: FenetrePrincipale) -> None:
	"""La simulation de la fin de la matinée, faite ici sur la base de test, comme l'aurait faite Machin lecture."""
	fenetre._ouvrir_simulation()
	ecran = _ecran(fenetre, EcranSimulation)
	debut, fin = MAINTENANT.replace(minute=0, second=0), MAINTENANT.replace(hour=12, minute=30, second=0)
	ecran.debut.setDateTime(ecran.debut.dateTime().fromSecsSinceEpoch(int(debut.timestamp())))
	ecran.fin.setDateTime(ecran.fin.dateTime().fromSecsSinceEpoch(int(fin.timestamp())))
	with connecter(*parametres_base_test(), Role.LECTURE) as lecture:
		resultat = simuler(
			lecture,
			ecran.temporaire,
			debut,
			fin,
			graine=1,
			nom="simulation",
			metadonnees=Metadonnees(masquer=False, texte_public="Radio Exemple"),
		)
	anomalies = [message for niveau, _nature, message in resultat.log if niveau != "info"]
	passages = ecran._lire(ecran.temporaire / "simulation.csv")
	ecran.anomalies.addItems(anomalies)
	ecran.anomalies.setVisible(bool(anomalies))
	ecran.compte.setText(bilan(passages, len(anomalies)))
	ecran.periode = (debut, fin)
	ecran.exporter.setEnabled(True)


def main(arguments: list[str]) -> int:
	logging.basicConfig(level=logging.INFO, format="{message}", style="{")
	repertoire = CAPTURES_DU_GUIDE
	if arguments:
		repertoire = Path(arguments[0])
	try:
		with connexion_test() as proprietaire:
			reinitialiser_base(proprietaire)
	except pytest.skip.Exception as raison:
		journal.error(f"captures impossibles : {raison}")
		return 1
	produire(repertoire)
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
