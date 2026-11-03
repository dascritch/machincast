# language: fr
Fonctionnalité: Environnement virtuel isolé
	En tant que développeur de MachinCast,
	je veux que toutes les dépendances Python soient installées par pip dans l'environnement virtuel,
	afin que le projet suive l'évolution des paquets sans dépendre des versions de la distribution hôte.

	Scénario: L'environnement virtuel n'utilise pas les paquets Python du système
		Alors les scénarios s'exécutent dans un environnement virtuel
		Et cet environnement virtuel n'inclut pas les paquets Python du système

	Plan du scénario: Une dépendance Python vient de l'environnement virtuel
		Alors le module "<module>" est chargé depuis l'environnement virtuel

		Exemples:
			| module  |
			| PySide6 |
			| gi      |
			| psycopg |
			| yoyo    |

	Scénario: GStreamer, installé par le système, est accessible depuis PyGObject
		Alors GStreamer s'initialise depuis Python
