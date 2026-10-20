"""Écoute de l'antenne par un lien de PipeWire (https://github.com/dascritch/machincast/issues/24).

Quand l'antenne et la pré-écoute sont toutes deux sur PipeWire, la pré-écoute de l'antenne ne repasse pas le son par
GStreamer : elle relie, dans le graphe de PipeWire, les ports de monitoring du périphérique de l'antenne
(« <antenne>:monitor_FL ») aux entrées du périphérique de pré-écoute (« <preecoute>:playback_FL »). C'est une simple
copie du flux de sortie, que PipeWire cadence lui-même : rien ne se rejoue, rien ne saccade.

Les liens se font et se défont par pw-link (paquet pipewire-bin). Chaque canal va à l'entrée du même nom ; une entrée
unique (un casque mono) les reçoit tous ; sinon, les canaux vont aux entrées dans l'ordre.
"""

import subprocess

COMMANDE = "pw-link"
DELAI = 5.0
"""Secondes laissées à pw-link pour répondre."""

Paire = tuple[str, str]
"""Un port de sortie et le port d'entrée qu'il alimente."""


class LiaisonImpossible(Exception):
	"""Les liens ne peuvent pas se faire : le message dit pourquoi."""


def _pw_link(*arguments: str) -> str:
	try:
		resultat = subprocess.run(
			[COMMANDE, *arguments], capture_output=True, text=True, timeout=DELAI, check=False, stdin=subprocess.DEVNULL
		)
	except FileNotFoundError:
		raise LiaisonImpossible("pw-link introuvable ; installer pipewire-bin.") from None
	except subprocess.TimeoutExpired:
		raise LiaisonImpossible("pw-link ne répond pas.") from None
	if resultat.returncode != 0:
		raise LiaisonImpossible(f"pw-link {' '.join(arguments)} : {resultat.stderr.strip()}")
	return resultat.stdout


def _ports(option: str) -> list[str]:
	return [ligne.strip() for ligne in _pw_link(option).splitlines() if ligne.strip()]


def paires(antenne: str, preecoute: str) -> list[Paire]:
	"""Les liens qui copient l'antenne sur la pré-écoute ; lève LiaisonImpossible s'il n'y en a aucun."""
	sorties = [port for port in _ports("-o") if port.startswith(f"{antenne}:monitor_")]
	entrees = [port for port in _ports("-i") if port.startswith(f"{preecoute}:playback_")]
	if (not sorties) or (not entrees):
		raise LiaisonImpossible(
			f"PipeWire n'a pas de port de monitoring pour {antenne}, ou pas d'entrée pour {preecoute}."
		)
	if len(entrees) == 1:
		return [(sortie, entrees[0]) for sortie in sorties]
	par_canal = {entree.removeprefix(f"{preecoute}:playback_"): entree for entree in entrees}
	trouvees = [
		(sortie, par_canal[canal])
		for sortie in sorties
		if (canal := sortie.removeprefix(f"{antenne}:monitor_")) in par_canal
	]
	if trouvees:
		return trouvees
	return list(zip(sorties, entrees, strict=False))


def relier(liens: list[Paire]) -> None:
	"""Un lien qui existe déjà n'est pas une erreur."""
	for sortie, entree in liens:
		try:
			_pw_link(sortie, entree)
		except LiaisonImpossible as erreur:
			if "exists" not in str(erreur):
				raise


def delier(liens: list[Paire]) -> None:
	"""Un lien déjà défait, ou un PipeWire arrêté, n'est pas une erreur."""
	for sortie, entree in liens:
		try:
			_pw_link("-d", sortie, entree)
		except LiaisonImpossible:
			continue
