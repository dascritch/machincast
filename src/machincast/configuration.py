"""Lecture et validation du fichier de configuration TOML de MachinCast.

Le modèle documenté clé par clé est `machincast.exemple.toml`, à la racine du dépôt.
"""

import os
import tomllib
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal, cast

from machincast.base import LONGUEUR_TEXTE_COURT
from machincast.protection import est_fichier_sonore

NOM_FICHIER = "machincast.toml"

REPERTOIRE_PROJET = Path(__file__).resolve().parents[2]
"""Répertoire de MachinCast : dépôt local ou release décompressée, où se trouve machincast.toml.

Déduit de l'emplacement de ce module (src/machincast/), installé en mode éditable par install.sh : le même
répertoire que celui du wrapper Machin, qui appelle les binaires de son .venv
(https://github.com/dascritch/machincast/issues/76).
"""


def fichier_par_defaut() -> Path:
	"""Fichier lu quand aucun n'est passé avec --config, quel que soit le répertoire courant."""
	return REPERTOIRE_PROJET / NOM_FICHIER


SortieAudio = Literal["alsa", "pulseaudio", "pipewire", "factice"]
SORTIES_AUDIO: tuple[SortieAudio, ...] = ("alsa", "pulseaudio", "pipewire", "factice")
"""« factice » ne joue aucun son : pour les tests et les essais."""


class ConfigurationInvalide(Exception):
	"""Le fichier de configuration est absent, mal formé ou incomplet."""


@dataclass(frozen=True)
class Base:
	socket: Path
	"""Répertoire de la socket Unix de PostgreSQL."""
	production: str
	test: str


@dataclass(frozen=True)
class Audio:
	sortie: SortieAudio
	peripherique: str | None
	"""Périphérique d'antenne ; None pour le périphérique par défaut de la sortie."""
	preecoute: str


@dataclass(frozen=True)
class Sorties:
	csv: Path
	pls: Path
	html: Path


@dataclass(frozen=True)
class Metadonnees:
	masquer: bool
	"""Masquage par défaut de l'artiste et du titre sur les sorties publiques."""
	texte_public: str
	"""Texte public affiché à la place de l'artiste et du titre masqués, quand l'événement n'a pas de nom public."""


@dataclass(frozen=True)
class Lecture:
	socket_etat: Path
	"""Socket Unix d'état du binaire lecture, lue par l'interface (https://github.com/dascritch/machincast/issues/20)."""


def socket_etat_par_defaut() -> Path:
	"""Dans le répertoire d'exécution du compte ($XDG_RUNTIME_DIR, sinon /run/user/<uid>) : privé, effacé au
	redémarrage du poste."""
	repertoire = (os.environ.get("XDG_RUNTIME_DIR")) or (f"/run/user/{os.getuid()}")
	return Path(repertoire) / "machincast" / "lecture.sock"


Granularite = Literal["seconde", "dixieme"]
GRANULARITES: tuple[Granularite, ...] = ("seconde", "dixieme")
MAXIMUM_DES_CROSSFADES = timedelta(seconds=5)


@dataclass(frozen=True)
class Crossfades:
	"""Réglages des crossfades (https://github.com/dascritch/machincast/issues/145), section [crossfades]."""

	debut: timedelta | None = None
	"""Crossfade de début d'un sonore sans crossfade paramétré, que sa banque ne règle pas ; None : 0 seconde."""
	fin: timedelta | None = None
	"""Crossfade de fin, de même."""
	maximum: timedelta = MAXIMUM_DES_CROSSFADES
	"""Durée la plus longue que l'interface propose pour un crossfade."""
	granularite: Granularite = "dixieme"
	"""Pas des crossfades dans l'interface : à la seconde ou au dixième de seconde."""


SEUIL_DE_BLANC = -40.0
"""Seuil de blanc par défaut, en dB crête : 0 dB est la pleine échelle (https://github.com/dascritch/machincast/issues/146)."""
SEUIL_DE_BLANC_MINIMUM = -100.0
"""Seuil de blanc le plus bas accepté, compris ; le plus haut est 0 dB, exclu."""


@dataclass(frozen=True)
class Blancs:
	"""Détection de blanc (https://github.com/dascritch/machincast/issues/146), section [blancs]."""

	seuil: float = SEUIL_DE_BLANC
	"""Niveau crête, en dB, sous lequel le début et la fin d'un sonore sont un blanc : l'audit complet mesure les
	blancs à ce seuil."""


@dataclass(frozen=True)
class Interface:
	"""Réglages de l'interface graphique (https://github.com/dascritch/machincast/issues/191), section [interface]."""

	saturation: bool = True
	"""Le voyant « Saturation » de la colonne Antenne de l'accueil est affiché."""
	suggestions: bool = True
	"""Au lancement, l'interface propose de créer ce qui manque pour démarrer
	(https://github.com/dascritch/machincast/issues/119)."""


@dataclass(frozen=True)
class Configuration:
	chemin: Path
	base: Base
	audio: Audio
	sorties: Sorties
	metadonnees: Metadonnees
	lecture: Lecture
	crossfades: Crossfades = field(default_factory=Crossfades)
	blancs: Blancs = field(default_factory=Blancs)
	interface: Interface = field(default_factory=Interface)


# Clés connues, par section. Toute autre clé est refusée, pour détecter les fautes de frappe.
CLES: dict[str, frozenset[str]] = {
	"base": frozenset({"socket", "production", "test"}),
	"audio": frozenset({"sortie", "peripherique", "preecoute"}),
	"sorties": frozenset({"csv", "pls", "html"}),
	"metadonnees": frozenset({"masquer", "texte_public"}),
	"lecture": frozenset({"socket_etat"}),
	"crossfades": frozenset({"granularite", "maximum", "debut", "fin"}),
	"blancs": frozenset({"seuil"}),
	"interface": frozenset({"saturation", "suggestions"}),
}


class _Lecteur:
	"""Lit les valeurs d'un document TOML en produisant des messages d'erreur explicites."""

	def __init__(self, chemin: Path, document: dict[str, Any]) -> None:
		self.chemin = chemin
		self.document = document

	def erreur(self, message: str) -> ConfigurationInvalide:
		return ConfigurationInvalide(f"{self.chemin} : {message}")

	def verifier_cles(self) -> None:
		for section, contenu in self.document.items():
			if section not in CLES:
				raise self.erreur(f"section [{section}] inconnue")
			if not isinstance(contenu, dict):
				raise self.erreur(f"[{section}] doit être une section")
			for cle in contenu:
				if cle not in CLES[section]:
					raise self.erreur(f"clé {section}.{cle} inconnue")

	def _valeur(self, section: str, cle: str, obligatoire: bool) -> object:
		contenu = self.document.get(section, {})
		if cle not in contenu:
			if obligatoire:
				raise self.erreur(f"clé {section}.{cle} manquante")
			return None
		return cast(object, contenu[cle])

	def texte(self, section: str, cle: str) -> str:
		valeur = self._valeur(section, cle, obligatoire=True)
		if not isinstance(valeur, str):
			raise self.erreur(f"clé {section}.{cle} : texte attendu, {_decrire(valeur)} trouvé")
		if not valeur.strip():
			raise self.erreur(f"clé {section}.{cle} : la valeur ne peut pas être vide")
		return valeur

	def texte_court(self, section: str, cle: str) -> str:
		"""Texte affiché au public : limité à LONGUEUR_TEXTE_COURT caractères, comme les textes en base."""
		valeur = self.texte(section, cle)
		if len(valeur) > LONGUEUR_TEXTE_COURT:
			raise self.erreur(
				f"clé {section}.{cle} : {LONGUEUR_TEXTE_COURT} caractères au maximum, {len(valeur)} trouvés"
			)
		return valeur

	def texte_facultatif(self, section: str, cle: str) -> str | None:
		valeur = self._valeur(section, cle, obligatoire=False)
		if valeur is None:
			return None
		if not isinstance(valeur, str):
			raise self.erreur(f"clé {section}.{cle} : texte attendu, {_decrire(valeur)} trouvé")
		return (valeur) or (None)

	def chemin_facultatif(self, section: str, cle: str) -> Path | None:
		"""Comme chemin_fichier, ou None si la clé est absente."""
		if self.texte_facultatif(section, cle) is None:
			return None
		return self.chemin_fichier(section, cle)

	def booleen(self, section: str, cle: str) -> bool:
		valeur = self._valeur(section, cle, obligatoire=True)
		if not isinstance(valeur, bool):
			raise self.erreur(f"clé {section}.{cle} : booléen attendu (true ou false), {_decrire(valeur)} trouvé")
		return valeur

	def booleen_facultatif(self, section: str, cle: str, defaut: bool) -> bool:
		valeur = self._valeur(section, cle, obligatoire=False)
		if valeur is None:
			return defaut
		if not isinstance(valeur, bool):
			raise self.erreur(f"clé {section}.{cle} : booléen attendu (true ou false), {_decrire(valeur)} trouvé")
		return valeur

	def nombre_facultatif(self, section: str, cle: str) -> float | None:
		valeur = self._valeur(section, cle, obligatoire=False)
		if valeur is None:
			return None
		if (isinstance(valeur, bool)) or (not isinstance(valeur, (int, float))):
			raise self.erreur(f"clé {section}.{cle} : nombre attendu, {_decrire(valeur)} trouvé")
		return float(valeur)

	def crossfades(self) -> Crossfades:
		"""La section [crossfades], facultative, comme toutes ses clés."""
		granularite = (self.texte_facultatif("crossfades", "granularite")) or ("dixieme")
		if granularite not in GRANULARITES:
			raise self.erreur(
				f"clé crossfades.granularite : « {granularite} » inconnue,"
				f" valeurs possibles : {', '.join(GRANULARITES)}"
			)
		maximum = MAXIMUM_DES_CROSSFADES
		secondes = self.nombre_facultatif("crossfades", "maximum")
		if secondes is not None:
			if secondes <= 0:
				raise self.erreur("clé crossfades.maximum : un nombre de secondes strictement positif est attendu")
			maximum = timedelta(seconds=secondes)
		durees: list[timedelta | None] = []
		for cle in ("debut", "fin"):
			duree = self.nombre_facultatif("crossfades", cle)
			if duree is None:
				durees.append(None)
				continue
			if duree < 0:
				raise self.erreur(f"clé crossfades.{cle} : un nombre de secondes positif ou nul est attendu")
			if timedelta(seconds=duree) > maximum:
				raise self.erreur(f"clé crossfades.{cle} : au plus crossfades.maximum, {maximum.total_seconds():g} s")
			durees.append(timedelta(seconds=duree))
		return Crossfades(durees[0], durees[1], maximum, granularite)

	def blancs(self) -> Blancs:
		"""La section [blancs], facultative, comme sa clé."""
		seuil = self.nombre_facultatif("blancs", "seuil")
		if seuil is None:
			return Blancs()
		if not (SEUIL_DE_BLANC_MINIMUM <= seuil < 0):
			raise self.erreur(
				f"clé blancs.seuil : un nombre de dB de {SEUIL_DE_BLANC_MINIMUM:g} dB compris à 0 dB exclu est attendu,"
				f" {seuil:g} trouvé"
			)
		return Blancs(seuil)

	def chemin_fichier(self, section: str, cle: str) -> Path:
		"""Chemin absolu tel quel ; chemin relatif résolu depuis le répertoire du fichier de configuration."""
		chemin = Path(self.texte(section, cle)).expanduser()
		return chemin if chemin.is_absolute() else self.chemin.parent / chemin


def _decrire(valeur: object) -> str:
	match valeur:
		case bool():
			return "booléen"
		case int() | float():
			return "nombre"
		case str():
			return "texte"
		case list():
			return "liste"
		case dict():
			return "section"
		case _:
			return type(valeur).__name__


def charger(chemin: Path | None = None) -> Configuration:
	"""Charge et valide la configuration.

	Sans chemin, lit `machincast.toml` dans le répertoire de MachinCast (fichier_par_defaut).
	Lève ConfigurationInvalide avec un message qui nomme le fichier et la clé en cause.
	"""
	chemin = ((chemin) or (fichier_par_defaut())).expanduser().absolute()
	try:
		with chemin.open("rb") as fichier:
			document = tomllib.load(fichier)
	except FileNotFoundError:
		raise ConfigurationInvalide(f"{chemin} : fichier de configuration introuvable") from None
	except tomllib.TOMLDecodeError as erreur:
		raise ConfigurationInvalide(f"{chemin} : syntaxe TOML invalide ({erreur})") from None

	lecteur = _Lecteur(chemin, document)
	lecteur.verifier_cles()

	base = Base(
		socket=Path(lecteur.texte("base", "socket")),
		production=lecteur.texte("base", "production"),
		test=lecteur.texte("base", "test"),
	)
	if base.test == base.production:
		raise lecteur.erreur("clé base.test : la base de test ne peut pas être la base de production")

	sortie = lecteur.texte("audio", "sortie")
	if sortie not in SORTIES_AUDIO:
		raise lecteur.erreur(
			f"clé audio.sortie : « {sortie} » inconnue, valeurs possibles : {', '.join(SORTIES_AUDIO)}"
		)
	peripherique = lecteur.texte_facultatif("audio", "peripherique")
	preecoute = lecteur.texte("audio", "preecoute")
	if preecoute == peripherique:
		raise lecteur.erreur("clé audio.preecoute : la pré-écoute doit utiliser un autre périphérique que l'antenne")

	sorties = Sorties(
		csv=lecteur.chemin_fichier("sorties", "csv"),
		pls=lecteur.chemin_fichier("sorties", "pls"),
		html=lecteur.chemin_fichier("sorties", "html"),
	)
	lecture = Lecture(socket_etat=(lecteur.chemin_facultatif("lecture", "socket_etat")) or (socket_etat_par_defaut()))
	# Un fichier sonore n'est jamais écrit ni remplacé (https://github.com/dascritch/machincast/issues/96).
	for cle, valeur in (
		("sorties.csv", sorties.csv),
		("sorties.pls", sorties.pls),
		("sorties.html", sorties.html),
		("lecture.socket_etat", lecture.socket_etat),
	):
		if est_fichier_sonore(valeur):
			raise lecteur.erreur(
				f"clé {cle} : « {valeur} » porte l'extension d'un fichier sonore, et MachinCast n'écrit jamais dans un"
				" fichier sonore"
			)

	return Configuration(
		chemin=chemin,
		base=base,
		audio=Audio(sortie=sortie, peripherique=peripherique, preecoute=preecoute),
		sorties=sorties,
		metadonnees=Metadonnees(
			masquer=lecteur.booleen("metadonnees", "masquer"),
			texte_public=lecteur.texte_court("metadonnees", "texte_public"),
		),
		lecture=lecture,
		crossfades=lecteur.crossfades(),
		blancs=lecteur.blancs(),
		interface=Interface(
			saturation=lecteur.booleen_facultatif("interface", "saturation", True),
			suggestions=lecteur.booleen_facultatif("interface", "suggestions", True),
		),
	)
