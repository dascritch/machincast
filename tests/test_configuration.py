"""Étapes des scénarios du fichier de configuration."""

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import configuration as module_configuration
from machincast.cli import CODE_CONFIGURATION_INVALIDE
from machincast.cli import lancer as lancer_binaire
from machincast.configuration import Configuration, ConfigurationInvalide, charger, fichier_par_defaut
from machincast.lecture.fondus import LIBELLES

scenarios("configuration.feature")

RACINE = Path(__file__).resolve().parents[1]

# Configuration valide de référence, en littéraux TOML, section par section.
VALIDE: dict[str, dict[str, str]] = {
	"base": {"socket": '"/var/run/postgresql"', "production": '"machincast"', "test": '"machincast_test"'},
	"audio": {"sortie": '"pipewire"', "peripherique": '"antenne"', "preecoute": '"casque"'},
	"sorties": {"csv": '"airplay.csv"', "pls": '"playlist.pls"', "html": '"airplay.html"'},
	"metadonnees": {"masquer": "false", "texte_public": '"Radio FMR"'},
}


@dataclass
class Contexte:
	repertoire: Path
	chemin: Path | None = None
	configuration: Configuration | None = None
	erreur: ConfigurationInvalide | None = None
	resultat: subprocess.CompletedProcess[str] | None = None
	code: int | None = None
	recue: Configuration | None = None
	erreurs: str = ""
	cles: dict[str, dict[str, str]] = field(default_factory=lambda: {s: dict(c) for s, c in VALIDE.items()})


@pytest.fixture
def contexte(tmp_path: Path) -> Contexte:
	return Contexte(repertoire=tmp_path)


def ecrire(contexte: Contexte, nom: str = "machincast.toml") -> Path:
	lignes: list[str] = []
	for section, cles in contexte.cles.items():
		lignes.append(f"[{section}]")
		lignes += [f"{cle} = {valeur}" for cle, valeur in cles.items()]
		lignes.append("")
	chemin = contexte.repertoire / nom
	chemin.write_text("\n".join(lignes), encoding="utf-8")
	contexte.chemin = chemin
	return chemin


def lancer(executable: str, arguments: list[str], repertoire: Path) -> subprocess.CompletedProcess[str]:
	chemin = shutil.which(executable)
	assert chemin is not None, f"{executable} n'est pas installé"
	return subprocess.run(
		[chemin, *arguments], capture_output=True, text=True, timeout=30, cwd=repertoire, env=os.environ.copy()
	)


# ─── Étant donné ───────────────────────────────────────────


@given("le modèle de configuration du dépôt")
def modele(contexte: Contexte) -> None:
	contexte.chemin = RACINE / "machincast.exemple.toml"


@given("un fichier de configuration contenant :")
def fichier_contenant(contexte: Contexte, docstring: str) -> None:
	contexte.chemin = contexte.repertoire / "machincast.toml"
	contexte.chemin.write_text(docstring, encoding="utf-8")


@given(parsers.parse('une configuration valide où la clé "{cle}" est absente'))
def cle_absente(contexte: Contexte, cle: str) -> None:
	section, nom = cle.split(".")
	contexte.cles.setdefault(section, {}).pop(nom, None)
	ecrire(contexte)


@given(parsers.parse('une configuration valide où la clé "{cle}" vaut {valeur}'))
def cle_vaut(contexte: Contexte, cle: str, valeur: str) -> None:
	section, nom = cle.split(".")
	valeur = valeur.replace("<256 caractères>", "é" * 256)
	contexte.cles.setdefault(section, {})[nom] = valeur
	ecrire(contexte)


@given(parsers.parse('une configuration valide sans section "{section}"'))
def sans_section(contexte: Contexte, section: str) -> None:
	contexte.cles.pop(section, None)
	ecrire(contexte)


@given(parsers.parse('la clé "{cle}" vaut {valeur}'))
def et_la_cle_vaut(contexte: Contexte, cle: str, valeur: str) -> None:
	cle_vaut(contexte, cle, valeur)


@given(parsers.parse("le répertoire d'exécution du compte « {repertoire} »"))
def repertoire_d_execution(monkeypatch: pytest.MonkeyPatch, repertoire: str) -> None:
	monkeypatch.setenv("XDG_RUNTIME_DIR", repertoire)


@given("un chemin de configuration qui n'existe pas")
def chemin_absent(contexte: Contexte) -> None:
	contexte.chemin = contexte.repertoire / "absent.toml"


@given(parsers.parse('une configuration valide enregistrée dans "{nom}"'))
def valide_enregistree(contexte: Contexte, nom: str) -> None:
	"""Configuration passée à un binaire : sa socket PostgreSQL n'existe pas, pour qu'il ne puisse joindre aucune
	base, et surtout pas la base de production qu'elle désigne (https://github.com/dascritch/machincast/issues/7)."""
	contexte.cles["base"]["socket"] = f'"{contexte.repertoire / "aucune-socket"}"'
	ecrire(contexte, nom)


# ─── Quand ─────────────────────────────────────────────────


@when("je charge la configuration")
def charger_configuration(contexte: Contexte) -> None:
	try:
		contexte.configuration = charger(contexte.chemin)
	except ConfigurationInvalide as erreur:
		contexte.erreur = erreur


@when(parsers.parse('je lance "{executable}" avec la configuration "{nom}"'))
def lancer_avec_configuration(contexte: Contexte, executable: str, nom: str) -> None:
	contexte.resultat = lancer(executable, ["--config", nom], contexte.repertoire)


@given("ce répertoire tient lieu de répertoire de MachinCast")
def repertoire_machincast(contexte: Contexte, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(module_configuration, "REPERTOIRE_PROJET", contexte.repertoire)


@given("un répertoire de MachinCast sans machincast.toml")
def repertoire_sans_fichier(contexte: Contexte, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(module_configuration, "REPERTOIRE_PROJET", contexte.repertoire)


@given("le répertoire courant est un autre répertoire")
def autre_repertoire(contexte: Contexte, monkeypatch: pytest.MonkeyPatch) -> None:
	ailleurs = contexte.repertoire / "ailleurs"
	ailleurs.mkdir()
	monkeypatch.chdir(ailleurs)


@when("un binaire démarre sans option")
def demarrer_sans_option(contexte: Contexte, capsys: pytest.CaptureFixture[str]) -> None:
	def action(configuration: Configuration, _options: object) -> int:
		contexte.recue = configuration
		return 0

	contexte.code = lancer_binaire("Machin_essai", "Binaire d'essai.", [], action)
	contexte.erreurs = capsys.readouterr().err


@when(parsers.parse('je lance "{executable}" avec l\'option "{option}"'))
def lancer_option(contexte: Contexte, executable: str, option: str) -> None:
	contexte.resultat = lancer(executable, [option], contexte.repertoire)


@when(parsers.parse('je lance "{executable}" avec ce chemin de configuration'))
def lancer_avec_chemin(contexte: Contexte, executable: str) -> None:
	assert contexte.chemin is not None
	contexte.resultat = lancer(executable, ["--config", str(contexte.chemin)], contexte.repertoire)


# ─── Alors ─────────────────────────────────────────────────


def configuration(contexte: Contexte) -> Configuration:
	assert contexte.erreur is None, str(contexte.erreur)
	assert contexte.configuration is not None
	return contexte.configuration


@then(parsers.parse('le fichier de configuration par défaut est "{nom}" à la racine du dépôt'))
def defaut_dans_le_depot(nom: str) -> None:
	assert fichier_par_defaut() == RACINE / nom


@then("il reçoit la configuration de ce répertoire")
def recoit_configuration(contexte: Contexte) -> None:
	assert contexte.code == 0, contexte.erreurs
	assert contexte.recue is not None
	# Les chemins relatifs sont résolus depuis le fichier lu : c'est bien celui de ce répertoire.
	assert contexte.recue.sorties.csv == contexte.repertoire / "airplay.csv"


@then(parsers.parse("il s'arrête avec le code {code:d}"))
def arret_code(contexte: Contexte, code: int) -> None:
	assert contexte.code == code


@then("son erreur mentionne le chemin complet du machincast.toml de ce répertoire")
def erreur_chemin_complet(contexte: Contexte) -> None:
	assert str(contexte.repertoire / "machincast.toml") in contexte.erreurs, contexte.erreurs


@then("la sortie mentionne le machincast.toml à la racine du dépôt")
def aide_defaut(contexte: Contexte) -> None:
	assert contexte.resultat is not None
	assert str(RACINE / "machincast.toml") in contexte.resultat.stdout, contexte.resultat.stdout


@then("la configuration est chargée sans erreur")
def chargee(contexte: Contexte) -> None:
	configuration(contexte)


@then(parsers.parse('la base de production est "{nom}"'))
def base_production(contexte: Contexte, nom: str) -> None:
	assert configuration(contexte).base.production == nom


@then(parsers.parse('la base de test est "{nom}"'))
def base_test(contexte: Contexte, nom: str) -> None:
	assert configuration(contexte).base.test == nom


@then(parsers.parse('la sortie audio est "{sortie}" sur le périphérique "{peripherique}"'))
def sortie_audio(contexte: Contexte, sortie: str, peripherique: str) -> None:
	audio = configuration(contexte).audio
	assert (audio.sortie, audio.peripherique) == (sortie, peripherique)


@then("la sortie audio utilise le périphérique par défaut")
def peripherique_defaut(contexte: Contexte) -> None:
	assert configuration(contexte).audio.peripherique is None


@then(parsers.parse('la pré-écoute utilise le périphérique "{peripherique}"'))
def preecoute(contexte: Contexte, peripherique: str) -> None:
	assert configuration(contexte).audio.preecoute == peripherique


@then(parsers.parse('la sortie CSV est "{relatif}" à côté du fichier de configuration'))
def sortie_csv(contexte: Contexte, relatif: str) -> None:
	assert configuration(contexte).sorties.csv == contexte.repertoire / relatif


@then(parsers.re(r'la socket d\'état est "(?P<chemin>[^"]+)"(?P<relatif> à côté du fichier de configuration)?$'))
def socket_etat(contexte: Contexte, chemin: str, relatif: str | None) -> None:
	assert contexte.configuration is not None
	attendu = Path(chemin)
	if relatif:
		attendu = contexte.repertoire / chemin
	assert contexte.configuration.lecture.socket_etat == attendu


@then(parsers.parse('la sortie HTML est "{absolu}"'))
def sortie_html(contexte: Contexte, absolu: str) -> None:
	assert configuration(contexte).sorties.html == Path(absolu)


@then(parsers.parse('le texte public par défaut est "{texte}"'))
def texte_public(contexte: Contexte, texte: str) -> None:
	assert configuration(contexte).metadonnees.texte_public == texte


@then("les métadonnées sont masquées par défaut")
def masquees(contexte: Contexte) -> None:
	assert configuration(contexte).metadonnees.masquer is True


@then(parsers.parse('le chargement échoue avec un message qui mentionne "{texte}"'))
def echec_mentionne(contexte: Contexte, texte: str) -> None:
	assert contexte.erreur is not None, "le chargement aurait dû échouer"
	assert texte in str(contexte.erreur)


@then(parsers.parse('le message mentionne "{texte}"'))
def message_mentionne(contexte: Contexte, texte: str) -> None:
	assert texte in str(contexte.erreur)


@then("le chargement échoue avec un message qui mentionne le chemin du fichier")
def echec_chemin(contexte: Contexte) -> None:
	assert contexte.erreur is not None, "le chargement aurait dû échouer"
	assert str(contexte.chemin) in str(contexte.erreur)


@then("la configuration est acceptée par le binaire")
def acceptee(contexte: Contexte) -> None:
	# Après une configuration acceptée, le binaire va plus loin : il signale un ticket à venir, ou ne joint pas la base.
	assert contexte.resultat is not None
	assert contexte.resultat.returncode != CODE_CONFIGURATION_INVALIDE, contexte.resultat.stderr
	assert "configuration invalide" not in contexte.resultat.stderr, contexte.resultat.stderr


@then(parsers.parse("le binaire s'arrête avec le code {code:d}"))
def code_retour(contexte: Contexte, code: int) -> None:
	assert contexte.resultat is not None
	assert contexte.resultat.returncode == code


@then("l'erreur affichée mentionne le chemin du fichier")
def erreur_chemin(contexte: Contexte) -> None:
	assert contexte.resultat is not None
	assert str(contexte.chemin) in contexte.resultat.stderr


# ─── Crossfades (https://github.com/dascritch/machincast/issues/145) ─────


@then(
	parsers.re(
		r"les crossfades se règlent (?P<granularite>au dixième de seconde|à la seconde),"
		r" jusqu'à (?P<maximum>\d+) secondes"
	)
)
def granularite_et_maximum(contexte: Contexte, granularite: str, maximum: str) -> None:
	assert contexte.configuration is not None, contexte.erreur
	crossfades = contexte.configuration.crossfades
	attendue = {"au dixième de seconde": "dixieme", "à la seconde": "seconde"}[granularite]
	assert (crossfades.granularite, crossfades.maximum) == (attendue, timedelta(seconds=int(maximum)))


@then("les crossfades n'ont pas de durée par défaut")
def sans_defaut(contexte: Contexte) -> None:
	assert contexte.configuration is not None, contexte.erreur
	assert (contexte.configuration.crossfades.debut, contexte.configuration.crossfades.fin) == (None, None)


@then(
	parsers.re(
		r"les crossfades durent par défaut (?P<debut>[\d,]+) secondes? au début et (?P<fin>[\d,]+) secondes? à la fin"
	)
)
def defauts(contexte: Contexte, debut: str, fin: str) -> None:
	assert contexte.configuration is not None, contexte.erreur
	crossfades = contexte.configuration.crossfades
	attendus = tuple(timedelta(seconds=float(valeur.replace(",", "."))) for valeur in (debut, fin))
	assert (crossfades.debut, crossfades.fin) == attendus


@then(parsers.re(r"le seuil de blanc est de (?P<seuil>-?[\d,]+) dB"))
def seuil_de_blanc(contexte: Contexte, seuil: str) -> None:
	"""https://github.com/dascritch/machincast/issues/146"""
	assert contexte.configuration is not None, contexte.erreur
	assert contexte.configuration.blancs.seuil == float(seuil.replace(",", "."))


@then(parsers.re(r"le voyant « Saturation » de l'accueil est (?P<etat>affiché|caché)"))
def voyant_de_saturation(contexte: Contexte, etat: str) -> None:
	"""https://github.com/dascritch/machincast/issues/191"""
	assert contexte.configuration is not None, contexte.erreur
	assert contexte.configuration.interface.saturation is (etat == "affiché")


@then(parsers.re(r"les suggestions au lancement sont (?P<etat>actives|éteintes)"))
def suggestions_au_lancement(contexte: Contexte, etat: str) -> None:
	"""https://github.com/dascritch/machincast/issues/119"""
	assert contexte.configuration is not None, contexte.erreur
	assert contexte.configuration.interface.suggestions is (etat == "actives")


# ─── Icône de l'interface (https://github.com/dascritch/machincast/issues/111) ───


@then("l'icône de l'interface est celle de MachinCast")
def icone_par_defaut(contexte: Contexte) -> None:
	assert contexte.configuration is not None
	assert contexte.configuration.interface.icone is None


@then(parsers.parse("l'icône de l'interface est \"{relatif}\" à côté du fichier de configuration"))
def icone_relative(contexte: Contexte, relatif: str) -> None:
	assert contexte.configuration is not None
	assert contexte.chemin is not None
	assert contexte.configuration.interface.icone == contexte.chemin.parent / relatif


@then(
	parsers.re(
		r"le fade-in (?P<entree>commence|est en cours|se termine) au début détecté, et le fade-out"
		r" (?P<sortie>commence|est en cours|se termine) à la fin détectée"
	)
)
def positions_des_fondus(contexte: Contexte, entree: str, sortie: str) -> None:
	"""https://github.com/dascritch/machincast/issues/234"""
	assert contexte.configuration is not None, contexte.erreur
	crossfades = contexte.configuration.crossfades
	assert (LIBELLES[crossfades.entree], LIBELLES[crossfades.sortie]) == (entree, sortie)
