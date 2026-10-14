"""Étapes des scénarios du fichier de configuration."""

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.configuration import Configuration, ConfigurationInvalide, charger

scenarios("configuration.feature")

RACINE = Path(__file__).resolve().parents[1]

# Configuration valide de référence, en littéraux TOML, section par section.
VALIDE: dict[str, dict[str, str]] = {
	"base": {"socket": '"/var/run/postgresql"', "production": '"machincast"', "test": '"machincast_test"'},
	"audio": {"sortie": '"pipewire"', "peripherique": '"antenne"', "preecoute": '"casque"'},
	"sorties": {"csv": '"airplay.csv"', "pls": '"playlist.pls"', "html": '"airplay.html"'},
	"metadonnees": {"masquer": "false"},
}


@dataclass
class Contexte:
	repertoire: Path
	chemin: Path | None = None
	configuration: Configuration | None = None
	erreur: ConfigurationInvalide | None = None
	resultat: subprocess.CompletedProcess[str] | None = None
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
	del contexte.cles[section][nom]
	ecrire(contexte)


@given(parsers.parse('une configuration valide où la clé "{cle}" vaut {valeur}'))
def cle_vaut(contexte: Contexte, cle: str, valeur: str) -> None:
	section, nom = cle.split(".")
	contexte.cles[section][nom] = valeur
	ecrire(contexte)


@given("un chemin de configuration qui n'existe pas")
def chemin_absent(contexte: Contexte) -> None:
	contexte.chemin = contexte.repertoire / "absent.toml"


@given(parsers.parse('une configuration valide enregistrée dans "{nom}"'))
def valide_enregistree(contexte: Contexte, nom: str) -> None:
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


@when(parsers.parse('je lance "{executable}" sans option depuis ce répertoire'))
def lancer_sans_option(contexte: Contexte, executable: str) -> None:
	contexte.resultat = lancer(executable, [], contexte.repertoire)


@when(parsers.parse('je lance "{executable}" avec ce chemin de configuration'))
def lancer_avec_chemin(contexte: Contexte, executable: str) -> None:
	assert contexte.chemin is not None
	contexte.resultat = lancer(executable, ["--config", str(contexte.chemin)], contexte.repertoire)


# ─── Alors ─────────────────────────────────────────────────


def configuration(contexte: Contexte) -> Configuration:
	assert contexte.erreur is None, str(contexte.erreur)
	assert contexte.configuration is not None
	return contexte.configuration


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


@then(parsers.parse('la sortie HTML est "{absolu}"'))
def sortie_html(contexte: Contexte, absolu: str) -> None:
	assert configuration(contexte).sorties.html == Path(absolu)


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
	# Les binaires ne font encore rien d'autre : après une configuration valide, ils signalent le ticket à venir.
	assert contexte.resultat is not None
	assert "pas encore implémenté" in contexte.resultat.stderr, contexte.resultat.stderr


@then(parsers.parse("le binaire s'arrête avec le code {code:d}"))
def code_retour(contexte: Contexte, code: int) -> None:
	assert contexte.resultat is not None
	assert contexte.resultat.returncode == code


@then("l'erreur affichée mentionne le chemin du fichier")
def erreur_chemin(contexte: Contexte) -> None:
	assert contexte.resultat is not None
	assert str(contexte.chemin) in contexte.resultat.stderr
