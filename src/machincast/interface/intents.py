"""L'intention d'une action, en tête de son libellé (https://github.com/dascritch/machincast/issues/294).

Un bouton ou une entrée de menu qui ajoute des lignes à un tableau commence par ➕ ; qui en retire, par ➖ ; qui
supprime une fiche, ou le confirme, par ❌. Sur l'antenne (https://github.com/dascritch/machincast/issues/322), dans le
menu « Diffusion », les menus contextuels et les boutons de l'onglet Antenne : ⏵ démarre la diffusion, ⏹ l'arrête, ⏭
saute le sonore ou l'événement en cours. L'emoji est dans le texte, suivi d'une espace : sa couleur est celle de la
police d'emoji du poste. Les titres des fenêtres et des questions n'en ont pas. Les libellés des fichiers .ui les
écrivent tels quels ; ceux du code passent par libelle().
"""

ADD = "➕"
REMOVE = "➖"
DELETE = "❌"
START = "⏵"
HALT = "⏹"
SKIP = "⏭"
"""Les actions sur l'antenne (https://github.com/dascritch/machincast/issues/322) : démarrer la diffusion, l'arrêter,
et sauter le sonore ou l'événement en cours."""
INTENTS = (ADD, REMOVE, DELETE, START, HALT, SKIP)


def label(intent: str, text: str) -> str:
	"""« ➕ Ajouter à des banques… »."""
	return f"{intent} {text}"


def without_intent(text: str) -> str:
	"""Le libellé sans son emoji : « Ajouter à des banques… »."""
	for intent in INTENTS:
		text = text.removeprefix(f"{intent} ")
	return text
