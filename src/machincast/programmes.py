"""Programmes de MachinCast en cours, pour install.sh (https://github.com/dascritch/machincast/issues/254).

	python3 -m machincast.programmes lister   --etat FICHIER   une ligne par programme en cours ; leur état, enregistré
	python3 -m machincast.programmes relancer --etat FICHIER   relance ceux du compte, dit ce qui reste à rouvrir

Une mise à jour, et surtout ses migrations de la base, ne doit pas se faire sous un programme qui s'en sert.
install.sh liste donc, avant de toucher au venv, les programmes de MachinCast qui tournent, sous tous les comptes du
poste : Machin lecture (le service de diffusion, une diffusion d'essai, une simulation), Machin indexation et
Machin interface, lancés par bin/Machin, par leur exécutable du venv (Machin_lecture…) ou par python -m. Il les arrête
si l'administrateur l'accepte, puis, à la fin, relance le service lui-même et demande ici de relancer les autres.

Ce module n'emploie que la bibliothèque standard : install.sh le lance avec le python3 du système, le venv pouvant
manquer ou changer pendant l'installation. Il lit /proc : la ligne de commande, le propriétaire, le groupe de contrôle
(le service de diffusion est celui de l'unité machincast.service) et le répertoire de chaque processus.

« lister » écrit, séparés par des tabulations : le pid, « oui » si le programme est du compte qui installe, « oui »
s'il est le service de diffusion, et ce qu'install.sh en affiche. L'état enregistré est en JSON : ni install.sh ni la
relance n'évaluent la ligne de commande d'un autre programme.

« relancer » relance, pour le seul compte qui installe, et depuis son répertoire : la diffusion d'essai dans un
terminal (konsole, sinon x-terminal-emulator), l'interface dans la session graphique, détachées d'install.sh, avec
leurs arguments, par bin/Machin. La simulation, que lance l'interface, se relance depuis son onglet ; une indexation
interrompue se relance à la main ; les programmes des autres comptes, par leur compte.
"""

import argparse
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from machincast.service import UNITE

PROC = Path("/proc")
MACHIN = Path(__file__).resolve().parents[2] / "bin" / "Machin"
"""Le wrapper du répertoire de MachinCast, qui relance chaque programme."""
NOMS = ("lecture", "indexation", "interface")
EXECUTABLE = re.compile(r"Machin_(lecture|indexation|interface)")
MODULE = re.compile(r"machincast\.(lecture|indexation|interface)")
TERMINAUX = ("konsole", "x-terminal-emulator")
SESSION_GRAPHIQUE = ("WAYLAND_DISPLAY", "DISPLAY")


@dataclass(frozen=True)
class Programme:
	pid: int
	compte: str
	nom: str
	"""lecture, indexation ou interface."""
	arguments: tuple[str, ...]
	service: bool
	"""Machin lecture, lancé par l'unité du service de diffusion."""
	repertoire: str
	"""Répertoire où il a été lancé : ses chemins relatifs s'y lisent ; vide pour un autre compte."""

	@property
	def nature(self) -> str:
		if self.nom != "lecture":
			return self.nom
		if self.service:
			return "service de diffusion"
		if "--simulation" in self.arguments:
			return "simulation"
		return "diffusion d'essai"

	@property
	def commande(self) -> str:
		"""Comme il se lance par bin/Machin."""
		return " ".join(["Machin", self.nom, *self.arguments])

	@property
	def libelle(self) -> str:
		return f"{self.commande} ({self.nature}), compte {self.compte}"


def reconnaitre(ligne: Sequence[str]) -> tuple[str, tuple[str, ...]] | None:
	"""Le programme d'une ligne de commande, et ses arguments ; None pour tout autre processus. L'exécutable du venv
	est lancé tel quel, ou par son python ; le module, par python -m."""
	if not ligne:
		return None
	python = Path(ligne[0]).name.startswith("python")
	for rang in (0, 1):
		if (rang < len(ligne)) and ((rang == 0) or (python)):
			trouve = EXECUTABLE.fullmatch(Path(ligne[rang]).name)
			if trouve is not None:
				return trouve.group(1), tuple(ligne[rang + 1 :])
	if python:
		for rang in range(1, len(ligne) - 1):
			if ligne[rang] == "-m":
				trouve = MODULE.fullmatch(ligne[rang + 1])
				if trouve is None:
					return None
				return trouve.group(1), tuple(ligne[rang + 2 :])
	return None


def _compte(uid: int) -> str:
	try:
		return pwd.getpwuid(uid).pw_name
	except KeyError:
		return str(uid)


def _lire(processus: Path, comptes: Callable[[int], str]) -> Programme | None:
	"""Un processus disparu entre-temps, ou illisible, n'est pas un programme en cours."""
	try:
		ligne = [partie for partie in processus.joinpath("cmdline").read_bytes().decode().split("\0") if partie]
		reconnu = reconnaitre(ligne)
		if reconnu is None:
			return None
		statut = processus.joinpath("status").read_text()
		cgroup = processus.joinpath("cgroup").read_text()
	except (OSError, UnicodeDecodeError):
		return None
	# Le répertoire ne se lit que pour son propre compte : celui d'un autre compte reste inconnu.
	try:
		repertoire = str(processus.joinpath("cwd").readlink())
	except OSError:
		repertoire = ""
	uid = re.search(r"^Uid:\s+(\d+)", statut, re.MULTILINE)
	if uid is None:
		return None
	nom, arguments = reconnu
	return Programme(
		pid=int(processus.name),
		compte=comptes(int(uid.group(1))),
		nom=nom,
		arguments=arguments,
		service=f"/{UNITE}" in cgroup,
		repertoire=repertoire,
	)


def en_cours(proc: Path = PROC, comptes: Callable[[int], str] = _compte) -> list[Programme]:
	"""Les programmes de MachinCast en cours, sous tous les comptes, par pid ; jamais ce processus-ci."""
	trouves = []
	for processus in proc.iterdir():
		if (not processus.name.isdigit()) or (int(processus.name) == os.getpid()):
			continue
		programme = _lire(processus, comptes)
		if programme is not None:
			trouves.append(programme)
	return sorted(trouves, key=lambda programme: programme.pid)


def _oui(vrai: bool) -> str:
	if vrai:
		return "oui"
	return "non"


def lister(programmes: list[Programme], compte_courant: str) -> str:
	"""Les lignes pour install.sh : pid, du compte, service, et ce qu'il en affiche."""
	return "".join(f"{p.pid}\t{_oui(p.compte == compte_courant)}\t{_oui(p.service)}\t{p.libelle}\n" for p in programmes)


def enregistrer(programmes: list[Programme], etat: Path) -> None:
	etat.write_text(json.dumps([asdict(programme) for programme in programmes], ensure_ascii=False))


def relire(etat: Path) -> list[Programme]:
	return [
		Programme(**{**valeurs, "arguments": tuple(valeurs["arguments"])}) for valeurs in json.loads(etat.read_text())
	]


Lancer = Callable[[list[str], str], None]
"""Lance une commande, détachée, depuis un répertoire."""


def lancer_detache(commande: list[str], repertoire: str) -> None:
	"""Détachée d'install.sh : elle survit à son terminal. Un répertoire disparu depuis laisse le répertoire courant."""
	if not Path(repertoire).is_dir():
		repertoire = os.getcwd()
	subprocess.Popen(  # noqa: S603 : la commande est bin/Machin, et les arguments, ceux du programme arrêté
		commande,
		cwd=repertoire,
		start_new_session=True,
		stdin=subprocess.DEVNULL,
		stdout=subprocess.DEVNULL,
		stderr=subprocess.DEVNULL,
	)


def _terminal(trouver: Callable[[str], str | None]) -> str | None:
	for terminal in TERMINAUX:
		chemin = trouver(terminal)
		if chemin is not None:
			return chemin
	return None


def relancer(
	programmes: list[Programme],
	compte_courant: str,
	environnement: Mapping[str, str],
	lancer: Lancer = lancer_detache,
	trouver: Callable[[str], str | None] = shutil.which,
	simulation: bool = False,
) -> list[str]:
	"""Relance la diffusion d'essai et l'interface du compte ; ce qu'il faut en dire, ligne par ligne. Le service de
	diffusion n'y est pas : install.sh le relance lui-même."""
	relances: list[str] = []
	reste: list[str] = []
	graphique = any(environnement.get(variable) for variable in SESSION_GRAPHIQUE)
	terminal = _terminal(trouver)
	prefixe = ""
	if simulation:
		prefixe = "[simulation] "
	for programme in programmes:
		commande = [str(MACHIN), programme.nom, *programme.arguments]
		if programme.service:
			continue
		if programme.compte != compte_courant:
			reste.append(f"à rouvrir par le compte {programme.compte} : {programme.commande}")
		elif programme.nature == "simulation":
			reste.append("simulation interrompue : la relancer depuis l'onglet Simulation de l'interface")
		elif programme.nom == "indexation":
			reste.append(f"indexation interrompue : relancer {programme.commande}")
		elif not graphique:
			ou = "un terminal"
			if programme.nom == "interface":
				ou = "la session graphique"
			reste.append(f"à rouvrir dans {ou} : {programme.commande}")
		elif programme.nom == "interface":
			if not simulation:
				lancer(commande, programme.repertoire)
			relances.append(f"{prefixe}relancé : {programme.commande}")
		elif terminal is None:
			reste.append(f"à rouvrir dans un terminal : {programme.commande}")
		else:
			if not simulation:
				lancer([terminal, "-e", *commande], programme.repertoire)
			relances.append(f"{prefixe}relancé dans un terminal : {programme.commande}")
	return relances + reste


def main(arguments: Sequence[str] | None = None) -> int:
	analyseur = argparse.ArgumentParser(prog="machincast.programmes", description=__doc__.splitlines()[0])
	analyseur.add_argument("action", choices=("lister", "relancer"))
	analyseur.add_argument("--etat", type=Path, required=True, help="état des programmes en cours, en JSON")
	analyseur.add_argument("--proc", type=Path, default=PROC, help=argparse.SUPPRESS)
	analyseur.add_argument("--simulation", action="store_true", help="dit ce qui serait relancé, sans rien lancer")
	options = analyseur.parse_args(arguments)
	compte_courant = _compte(os.getuid())
	if options.action == "lister":
		programmes = en_cours(options.proc)
		enregistrer(programmes, options.etat)
		sys.stdout.write(lister(programmes, compte_courant))
		return 0
	for message in relancer(relire(options.etat), compte_courant, os.environ, simulation=options.simulation):
		sys.stdout.write(f"{message}\n")
	return 0


if __name__ == "__main__":
	sys.exit(main())
