"""Lecture et validation du fichier de configuration TOML de MachinCast.

Le modèle documenté clé par clé est `machincast.exemple.toml`, à la racine du dépôt.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from machincast.base import LONGUEUR_TEXTE_COURT

FICHIER_PAR_DEFAUT = Path("machincast.toml")
"""Cherché dans le répertoire courant quand aucun fichier n'est passé avec --config."""

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
class Configuration:
	chemin: Path
	base: Base
	audio: Audio
	sorties: Sorties
	metadonnees: Metadonnees


# Clés connues, par section. Toute autre clé est refusée, pour détecter les fautes de frappe.
CLES: dict[str, frozenset[str]] = {
	"base": frozenset({"socket", "production", "test"}),
	"audio": frozenset({"sortie", "peripherique", "preecoute"}),
	"sorties": frozenset({"csv", "pls", "html"}),
	"metadonnees": frozenset({"masquer", "texte_public"}),
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
		return valeur or None

	def booleen(self, section: str, cle: str) -> bool:
		valeur = self._valeur(section, cle, obligatoire=True)
		if not isinstance(valeur, bool):
			raise self.erreur(f"clé {section}.{cle} : booléen attendu (true ou false), {_decrire(valeur)} trouvé")
		return valeur

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

	Sans chemin, lit `machincast.toml` dans le répertoire courant.
	Lève ConfigurationInvalide avec un message qui nomme le fichier et la clé en cause.
	"""
	chemin = (chemin or FICHIER_PAR_DEFAUT).expanduser().absolute()
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

	return Configuration(
		chemin=chemin,
		base=base,
		audio=Audio(sortie=sortie, peripherique=peripherique, preecoute=preecoute),
		sorties=Sorties(
			csv=lecteur.chemin_fichier("sorties", "csv"),
			pls=lecteur.chemin_fichier("sorties", "pls"),
			html=lecteur.chemin_fichier("sorties", "html"),
		),
		metadonnees=Metadonnees(
			masquer=lecteur.booleen("metadonnees", "masquer"),
			texte_public=lecteur.texte_court("metadonnees", "texte_public"),
		),
	)
