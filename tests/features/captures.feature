# language: fr
Fonctionnalité: Captures d'écran du guide utilisateur
	En tant qu'utilisateur de l'interface graphique,
	je veux voir dans le guide les écrans dont il parle,
	afin de m'y retrouver avant même d'ouvrir l'interface.

	https://github.com/dascritch/machincast/issues/128. « Machin dev-screenshots » ouvre l'interface hors de l'écran, sur
	une base de démonstration écrite dans la base de test, jamais dans celle de production, et enregistre chaque
	écran en PNG dans doc/fr/captures. Le guide utilisateur les cite toutes, et seulement elles.

	Scénario: Chaque capture produite est dans doc/fr/captures et citée par le guide utilisateur, et réciproquement
		Alors chaque capture de Machin dev-screenshots est une image de doc/fr/captures
		Et chaque image de doc/fr/captures est une capture de Machin dev-screenshots
		Et chaque capture de Machin dev-screenshots est citée par le guide utilisateur
		Et chaque image citée par le guide utilisateur est dans doc/fr/captures

	Scénario: Machin dev-screenshots enregistre une image par capture, à la taille de la fenêtre
		Quand je produis les captures dans un répertoire temporaire
		Alors le répertoire contient une image PNG par capture, et rien d'autre
		Et la capture « accueil » fait 1280 × 800 pixels
		Et aucune capture n'est d'une couleur unie
