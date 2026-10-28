"""L'intention d'une action, en tête de son libellé (https://github.com/dascritch/machincast/issues/294).

Un bouton ou une entrée de menu qui ajoute des lignes à un tableau commence par ➕ ; qui en retire, par ➖ ; qui
supprime une fiche, ou le confirme, par ❌. L'emoji est dans le texte, suivi d'une espace : sa couleur est celle de la
police d'emoji du poste. Les titres des fenêtres et des questions n'en ont pas. Les libellés des fichiers .ui les
écrivent tels quels ; ceux du code passent par libelle().
"""

AJOUTER = "➕"
RETIRER = "➖"
SUPPRIMER = "❌"
INTENTIONS = (AJOUTER, RETIRER, SUPPRIMER)


def libelle(intention: str, texte: str) -> str:
	"""« ➕ Ajouter à des banques… »."""
	return f"{intention} {texte}"


def sans_intention(texte: str) -> str:
	"""Le libellé sans son emoji : « Ajouter à des banques… »."""
	for intention in INTENTIONS:
		texte = texte.removeprefix(f"{intention} ")
	return texte
