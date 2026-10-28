"""Scénarios d'une lecture qui ne démarre pas (https://github.com/dascritch/machincast/issues/281).

La diffusion tourne sur le moteur simulé, qui suit l'horloge du binaire. Un lecteur bloqué est imité par une voie
simulée dont la position n'avance pas, et qui se dit bloquée passé le délai de démarrage, comme la voie GStreamer
(machincast.lecture.moteur.Voie.bloquee). Les étapes partagées de la diffusion sont dans tests/etapes_diffusion.py.
"""

from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios

from machincast.horloge import HorlogeFixe
from machincast.lecture.moteur import DELAI_DE_GARDE, VoieLecture
from machincast.lecture.simulation import MoteurSimule, VoieSimulee

scenarios("lecture_bloquee.feature")

Connexion = psycopg.Connection[tuple[object, ...]]


class VoieBloquee(VoieSimulee):
	"""Un lecteur qui ne démarre jamais : ni son, ni erreur, ni fin."""

	def position(self) -> timedelta:
		return timedelta(0)

	def traiter(self) -> None:
		pass

	def bloquee(self) -> bool:
		return (self.etat == "en cours") and (self.horloge.maintenant() - self.debut >= DELAI_DE_GARDE)


@given(parsers.parse("le lecteur du sonore « {nom} » se bloque à son premier démarrage"))
def lecteur_bloque(monkeypatch: pytest.MonkeyPatch, nom: str) -> None:
	"""Les fichiers des sonores sont dans un répertoire à leur nom (etapes_diffusion.creer_sonore) ; l'adresse d'un
	stream factice finit par son nom."""
	vrai_jouer = MoteurSimule.jouer
	bloques: list[str] = []

	def jouer(
		self: MoteurSimule, chemin: Path | str, duree: timedelta | None, *args: object, **options: object
	) -> VoieLecture:
		vise = (Path(str(chemin)).parent.name == nom) or (str(chemin).endswith(f"/{nom}"))
		if (vise) and (bloques == []):
			bloques.append(nom)
			assert isinstance(self.horloge, HorlogeFixe)
			voie = VoieBloquee(self.horloge, duree)
			self._voies.append(voie)
			return voie
		return vrai_jouer(self, chemin, duree, *args, **options)  # type: ignore[arg-type]

	monkeypatch.setattr(MoteurSimule, "jouer", jouer)
