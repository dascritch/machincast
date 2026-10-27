"""Scénarios des programmes de MachinCast en cours pendant l'installation
(https://github.com/dascritch/machincast/issues/254).

Le /proc factice du scénario a, pour chaque processus, sa ligne de commande (les mots de la colonne « commande »),
son propriétaire, son groupe de contrôle et son répertoire. Les comptes « radio » et « xavier » y ont les uid 5001 et
5002. La relance n'ouvre rien : elle note ce qu'elle lancerait.
"""

import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import programmes
from machincast.programmes import Programme

scenarios("programmes_en_cours.feature")

COMPTES = {"radio": 5001, "xavier": 5002}
NOMS = {uid: nom for nom, uid in COMPTES.items()}
SRC = Path(__file__).parent.parent / "src"


@dataclass
class Poste:
	proc: Path
	etat: Path
	environnement: dict[str, str] = field(default_factory=dict)
	terminaux: tuple[str, ...] = ()
	liste: str = ""
	lances: list[tuple[str, str]] = field(default_factory=list)
	"""Les commandes relancées, et leur répertoire."""
	messages: list[str] = field(default_factory=list)


@pytest.fixture
def poste(tmp_path: Path) -> Poste:
	proc = tmp_path / "proc"
	proc.mkdir()
	return Poste(proc, tmp_path / "programmes.json")


def compte(uid: int) -> str:
	return NOMS[uid]


def table(datatable: list[list[str]]) -> list[dict[str, str]]:
	entetes, *rangees = datatable
	return [dict(zip((e.strip() for e in entetes), (v.strip() for v in rangee), strict=True)) for rangee in rangees]


def lisible(commande: list[str]) -> str:
	"""bin/Machin s'écrit « Machin »."""
	return " ".join("Machin" if mot == str(programmes.MACHIN) else mot for mot in commande)


# ─── Étant donné ───────────────────────────────────────────


@given("les processus :")
def processus(poste: Poste, datatable: list[list[str]]) -> None:
	for rangee in table(datatable):
		dossier = poste.proc / rangee["pid"]
		dossier.mkdir()
		dossier.joinpath("cmdline").write_bytes("".join(f"{mot}\0" for mot in rangee["commande"].split()).encode())
		uid = COMPTES[rangee["compte"]]
		dossier.joinpath("status").write_text(f"Name:\tpython3\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n")
		dossier.joinpath("cgroup").write_text(f"{rangee['cgroup']}\n")
		dossier.joinpath("cwd").symlink_to((rangee.get("répertoire")) or ("/"))


@given(parsers.parse("le processus {pid:d} sans ligne de commande, comme un fil du noyau"))
def fil_du_noyau(poste: Poste, pid: int) -> None:
	dossier = poste.proc / str(pid)
	dossier.mkdir()
	dossier.joinpath("cmdline").write_bytes(b"")
	dossier.joinpath("status").write_text("Name:\tkthreadd\nUid:\t0\t0\t0\t0\n")


@given(parsers.parse("le processus {pid:d} disparu pendant la lecture"))
def disparu(poste: Poste, pid: int) -> None:
	"""Son dossier est là, mais plus ses fichiers."""
	(poste.proc / str(pid)).mkdir()


@given(parsers.parse("le répertoire du processus {pid:d} illisible"))
def repertoire_illisible(poste: Poste, pid: int) -> Iterator[None]:
	"""Comme pour un autre compte : le lien cwd ne se lit pas. Ses droits reviennent à la fin du scénario : sans eux,
	pytest ne peut pas effacer le répertoire temporaire d'un compte qui n'est pas root."""
	lien = poste.proc / str(pid) / "cwd"
	lien.unlink()
	lien.mkdir(mode=0)
	yield
	lien.chmod(0o700)


@given(parsers.parse("une session graphique, avec le terminal « {terminal} »"))
def session_graphique(poste: Poste, terminal: str) -> None:
	poste.environnement = {"DISPLAY": ":0"}
	poste.terminaux = (terminal,)


@given("aucune session graphique, ni terminal")
def sans_session(poste: Poste) -> None:
	poste.environnement = {}
	poste.terminaux = ()


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("install.sh demande la liste des programmes en cours, sous le compte « {nom} »"))
def demander_la_liste(poste: Poste, nom: str) -> None:
	trouves = programmes.en_cours(poste.proc, compte)
	programmes.enregistrer(trouves, poste.etat)
	poste.liste = programmes.lister(trouves, nom)


@when(
	parsers.re(
		r"install\.sh (?P<simule>relance les|simule la relance des) programmes arrêtés,"
		r" sous le compte « (?P<nom>[^»]+) »"
	)
)
def relancer(poste: Poste, simule: str, nom: str) -> None:
	def lancer(commande: list[str], repertoire: str) -> None:
		poste.lances.append((lisible(commande), repertoire))

	def trouver(terminal: str) -> str | None:
		if terminal in poste.terminaux:
			return terminal
		return None

	poste.messages = programmes.relancer(
		programmes.relire(poste.etat),
		nom,
		poste.environnement,
		lancer=lancer,
		trouver=trouver,
		simulation=simule != "relance les",
	)


# ─── Alors ─────────────────────────────────────────────────


def decrire(programme: Programme) -> dict[str, str]:
	return {
		"pid": str(programme.pid),
		"compte": programme.compte,
		"programme": programme.nom,
		"nature": programme.nature,
		"arguments": " ".join(programme.arguments),
	}


@then("les programmes en cours sont :")
def en_cours(poste: Poste, datatable: list[list[str]]) -> None:
	trouves = [decrire(programme) for programme in programmes.en_cours(poste.proc, compte)]
	assert trouves == table(datatable)


@then("aucun programme n'est en cours")
def aucun(poste: Poste) -> None:
	assert programmes.en_cours(poste.proc, compte) == []


@then("la liste pour install.sh est :")
def liste_pour_install(poste: Poste, datatable: list[list[str]]) -> None:
	attendues = ["\t".join(rangee.values()) for rangee in table(datatable)]
	assert poste.liste.splitlines() == attendues


@then("l'état des programmes arrêtés est enregistré")
def etat_enregistre(poste: Poste) -> None:
	assert programmes.relire(poste.etat) == programmes.en_cours(poste.proc, compte)


@then("les programmes relancés sont :")
def relances(poste: Poste, datatable: list[list[str]]) -> None:
	attendus = [(rangee["commande"], rangee["répertoire"]) for rangee in table(datatable)]
	assert poste.lances == attendus


@then("aucun programme n'est relancé")
def aucun_relance(poste: Poste) -> None:
	assert poste.lances == []


@then("la relance dit :")
def relance_dit(poste: Poste, datatable: list[list[str]]) -> None:
	assert poste.messages == [rangee["message"] for rangee in table(datatable)]


@then("machincast.programmes liste les programmes en cours avec un Python sans paquet installé")
def sans_venv(tmp_path: Path) -> None:
	"""-S : sans site-packages, ni ceux du venv ; seules les sources de MachinCast sont sur le chemin."""
	resultat = subprocess.run(
		[sys.executable, "-S", "-m", "machincast.programmes", "lister", "--etat", str(tmp_path / "etat.json")],
		env={**os.environ, "PYTHONPATH": str(SRC)},
		capture_output=True,
		text=True,
		check=False,
	)
	assert resultat.returncode == 0, resultat.stderr
	assert (tmp_path / "etat.json").exists()
