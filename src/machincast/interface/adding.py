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

from machincast.i18n import _, counted
from machincast.interface.card import sound_files
from machincast.interface.queries import sounds as queries


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
		if self.added_list != []:
			sentences.append(
				counted(
					"{count} file added, being checked.", "{count} files added, being checked.", len(self.added_list)
				)
			)
		if self.already != []:
			path_list = []
			for path in self.already:
				path_list.append(path.name)
			sentences.append(_("Already in the database: {list}.").format(list=", ".join(path_list)))
		if self.ignored != []:
			ignored_names = []
			for path in self.ignored:
				ignored_names.append(path.name)
			names = ", ".join(ignored_names)
			sentences.append(_("Ignored, these are not sound files: {names}.").format(names=names))
		return " ".join(sentences)


def add_files(connection: psycopg.Connection[TupleRow], paths: list[Path]) -> Adding:
	"""Enregistre les fichiers sonores à l'état aperçu, en une transaction ; un même fichier n'entre qu'une fois."""
	files, ignored = sound_files(paths)
	adding = Adding(ignored=ignored)
	with connection.transaction():

		def add_file(file: str) -> None:
			if queries.present_file(connection, file) is not None:
				adding.already.append(Path(file))
				return
			adding.added_list.append(queries.insert_preview(connection, file))

		for file in dict.fromkeys(files):
			add_file(file)
	return adding
