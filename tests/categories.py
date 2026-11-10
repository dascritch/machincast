"""Les genres d'éléments, tels que les scénarios les écrivent, et leur nom dans le code
(https://github.com/dascritch/machincast/issues/368)."""


def inverted[K, V](mapping: dict[K, V]) -> dict[V, K]:
	"""Le dictionnaire retourné : chaque valeur donne sa clé."""
	keys = {}
	for key, value in mapping.items():
		keys[value] = key
	return keys


CATEGORY = {"sonore": "sound", "banque": "bank", "séquence": "sequence", "événement": "event", "feed": "feed"}
"""Le genre dans le code, par son mot des scénarios."""
SCENARIO = inverted(CATEGORY)
"""Le mot des scénarios, par le genre dans le code."""
AIRPLAY_KEYS = {
	"start": "debut",
	"end": "fin",
	"duration": "duree",
	"artist": "artiste",
	"title": "titre",
	"event": "evenement",
	"bank": "banque",
}
"""Les colonnes de l'airplay de l'onglet Antenne et de l'onglet Airplay, par leur nom des scénarios."""
HATCHINGS = {"full": "pleines", "pale": "pâles", "none": "aucune"}
"""Les hachures d'une zone de la frise, par leur mot des scénarios."""
