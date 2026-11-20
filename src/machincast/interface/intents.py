"""L'intention d'une action, en tête de son libellé (https://github.com/dascritch/machincast/issues/294).

Un bouton ou une entrée de menu qui ajoute des lignes à un tableau commence par ➕ ; qui en retire, par ➖ ; qui
supprime une fiche, ou le confirme, par ❌. Les entrées de menu qui pilotent ou modifient l'antenne portent une icône,
plus un emoji (https://github.com/dascritch/machincast/issues/530, machincast.interface.icons). L'emoji est dans le texte, suivi d'une espace : sa couleur est celle de la
police d'emoji du poste. Les titres des fenêtres et des questions n'en ont pas. Les libellés des fichiers .ui les
écrivent tels quels ; ceux du code passent par libelle().
"""

ADD = "➕"
REMOVE = "➖"
DELETE = "❌"
INTENTS = (ADD, REMOVE, DELETE)


def label(intent: str, text: str) -> str:
	"""« ➕ Ajouter à des banques… »."""
	return f"{intent} {text}"


def without_intent(text: str) -> str:
	"""Le libellé sans son emoji : « Ajouter à des banques… »."""
	for intent in INTENTS:
		text = text.removeprefix(f"{intent} ")
	return text
