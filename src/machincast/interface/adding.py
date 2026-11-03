"""Ajout de fichiers sonores depuis la liste des sonores (https://github.com/dascritch/machincast/issues/30,
spec § 8.8).

Les fichiers choisis dans le sélecteur du poste, ou déposés sur la liste, sont référencés là où ils se trouvent, sans
copie : MachinCast ne fait que les lire (https://github.com/dascritch/machincast/issues/96). Chacun entre en base à
l'état aperçu, sous son chemin normalisé, jusqu'à la vérification de l'indexeur (machincast.interface.check).
Un fichier déjà en base n'est pas ajouté une seconde fois ; ce qui n'est pas un fichier sonore est ignoré.
"""

from dataclasses import dataclass, field
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.interface.card import sound_files


@dataclass
class Adding:
	added_list: list[int] = field(default_factory=list)
	"""Identifiants des sonores créés, dans l'ordre des fichiers."""
	already: list[Path] = field(default_factory=list)
	"""Fichiers déjà en base."""
	ignored: list[Path] = field(default_factory=list)
	"""Ce qui n'est pas un fichier sonore : dossiers, autres fichiers."""

	def text(self) -> str:
		"""Ce que la barre d'état annonce ; rien pour un ajout vide."""
		sentences = []
		if len(self.added_list) == 1:
			sentences.append("1 fichier ajouté, en cours de vérification.")
		elif self.added_list != []:
			sentences.append(f"{len(self.added_list)} fichiers ajoutés, en cours de vérification.")
		if self.already != []:
			sentences.append(f"Déjà en base : {', '.join(path.name for path in self.already)}.")
		if self.ignored != []:
			names = ", ".join(path.name for path in self.ignored)
			sentences.append(f"Ignorés, ce ne sont pas des fichiers sonores : {names}.")
		return " ".join(sentences)


def add_files(connection: psycopg.Connection[TupleRow], paths: list[Path]) -> Adding:
	"""Enregistre les fichiers sonores à l'état aperçu, en une transaction ; un même fichier n'entre qu'une fois."""
	files, ignored = sound_files(paths)
	adding = Adding(ignored=ignored)
	with connection.transaction():
		for file in dict.fromkeys(files):
			existing = connection.execute(
				"SELECT id FROM sounds WHERE location = %s AND deleted_at IS NULL", (file,)
			).fetchone()
			if existing is not None:
				adding.already.append(Path(file))
				continue
			created = connection.execute(
				"INSERT INTO sounds (type, location, state) VALUES ('file', %s, 'preview') RETURNING id",
				(file,),
			).fetchone()
			assert created is not None
			adding.added_list.append(int(str(created[0])))
	return adding
