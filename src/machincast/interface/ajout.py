"""Ajout de fichiers sonores depuis la liste des sonores (https://github.com/dascritch/machincast/issues/30,
spec § 8.8).

Les fichiers choisis dans le sélecteur du poste, ou déposés sur la liste, sont référencés là où ils se trouvent, sans
copie : MachinCast ne fait que les lire (https://github.com/dascritch/machincast/issues/96). Chacun entre en base à
l'état aperçu, sous son chemin normalisé, jusqu'à la vérification de l'indexeur (machincast.interface.verification).
Un fichier déjà en base n'est pas ajouté une seconde fois ; ce qui n'est pas un fichier sonore est ignoré.
"""

from dataclasses import dataclass, field
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.interface.fiche import fichiers_sonores


@dataclass
class Ajout:
	ajoutes: list[int] = field(default_factory=list)
	"""Identifiants des sonores créés, dans l'ordre des fichiers."""
	deja: list[Path] = field(default_factory=list)
	"""Fichiers déjà en base."""
	ignores: list[Path] = field(default_factory=list)
	"""Ce qui n'est pas un fichier sonore : dossiers, autres fichiers."""

	def texte(self) -> str:
		"""Ce que la barre d'état annonce ; rien pour un ajout vide."""
		phrases = []
		if len(self.ajoutes) == 1:
			phrases.append("1 fichier ajouté, en cours de vérification.")
		elif self.ajoutes != []:
			phrases.append(f"{len(self.ajoutes)} fichiers ajoutés, en cours de vérification.")
		if self.deja != []:
			phrases.append(f"Déjà en base : {', '.join(chemin.name for chemin in self.deja)}.")
		if self.ignores != []:
			noms = ", ".join(chemin.name for chemin in self.ignores)
			phrases.append(f"Ignorés, ce ne sont pas des fichiers sonores : {noms}.")
		return " ".join(phrases)


def ajouter_fichiers(connexion: psycopg.Connection[TupleRow], chemins: list[Path]) -> Ajout:
	"""Enregistre les fichiers sonores à l'état aperçu, en une transaction ; un même fichier n'entre qu'une fois."""
	fichiers, ignores = fichiers_sonores(chemins)
	ajout = Ajout(ignores=ignores)
	with connexion.transaction():
		for fichier in dict.fromkeys(fichiers):
			existant = connexion.execute(
				"SELECT id FROM sonores WHERE emplacement = %s AND supprime_le IS NULL", (fichier,)
			).fetchone()
			if existant is not None:
				ajout.deja.append(Path(fichier))
				continue
			cree = connexion.execute(
				"INSERT INTO sonores (type, emplacement, etat) VALUES ('fichier', %s, 'apercu') RETURNING id",
				(fichier,),
			).fetchone()
			assert cree is not None
			ajout.ajoutes.append(int(str(cree[0])))
	return ajout
