"""Fil musical garanti (https://github.com/dascritch/machincast/issues/39, spec § 8.10).

Sans événement de priorité fil musical, l'antenne n'a rien à jouer quand aucun autre événement ne la tient.
L'interface le vérifie au lancement, après la suppression d'un événement et après l'enregistrement d'un événement
(machincast.interface.fenetre) : s'il n'en existe aucun, elle crée « Fil musical », permanent (sans début ni fin), et
sans élément, sa liste restant à remplir dans sa fiche. Si ce nom est déjà pris par un autre événement, le fil prend le
premier libre parmi « Fil musical 2 », « Fil musical 3 »…
"""

import psycopg
from psycopg.rows import TupleRow

NOM = "Fil musical"


def garantir(connexion: psycopg.Connection[TupleRow]) -> str | None:
	"""Crée un fil musical permanent et vide s'il n'en existe aucun ; son nom, ou None s'il en existait un."""
	with connexion.transaction():
		existant = connexion.execute(
			"SELECT 1 FROM evenements WHERE priorite = 'fil_musical' AND supprime_le IS NULL LIMIT 1"
		).fetchone()
		if existant is not None:
			return None
		pris = {
			str(nom)
			for (nom,) in connexion.execute(
				"SELECT nom_interne FROM evenements WHERE (nom_interne = %s OR nom_interne LIKE %s || ' %%')"
				" AND supprime_le IS NULL",
				(NOM, NOM),
			)
		}
		nom = NOM
		numero = 1
		while nom in pris:
			numero += 1
			nom = f"{NOM} {numero}"
		connexion.execute("INSERT INTO evenements (nom_interne, priorite) VALUES (%s, 'fil_musical')", (nom,))
	return nom
