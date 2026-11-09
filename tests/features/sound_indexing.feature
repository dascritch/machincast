# language: fr
Fonctionnalité: Indexation d'un seul sonore
	En tant que technicien d'antenne,
	je veux pouvoir vérifier un seul sonore, sans reprendre toute l'indexation,
	afin que Machin player fasse analyser au dernier moment le sonore qu'il va jouer.

	https://github.com/dascritch/machincast/issues/181. « Machin indexer --sound N » ne vérifie que le sonore N,
	sans parcourir les répertoires des banques, avec --full-audit pour décoder son fichier quoi qu'il en soit. Il ne
	prend aucun verrou, comme la vérification des fichiers ajoutés depuis l'interface : une indexation rapide et un
	audit complet de toute la base peuvent tourner en même temps
	(https://github.com/dascritch/machincast/issues/401). Il n'écrit pas de document d'audit : une anomalie est signalée
	sur la sortie d'erreur, comme toujours.

	Scénario: Un audit complet d'un seul sonore ne vérifie que lui
		Étant donné un fichier flac sain
		Et un sonore à l'état « active » pour ce fichier
		Et un deuxième fichier flac sain, dont le sonore est à l'état « active »
		Quand Machin indexer est lancé sur la base de test, en audit complet, pour ce sonore seulement
		Alors Machin indexer se termine avec le code 0
		Et la date de vérification complète du sonore est celle de ce lancement
		Et le deuxième sonore n'a pas de date de vérification complète
		Et aucun document d'audit n'est écrit

	Plan du scénario: Un audit complet d'un seul sonore se fait même pendant une indexation générale
		Étant donné un fichier flac sain
		Et un sonore à l'état « active » pour ce fichier
		Et <autre> en cours sur la base
		Quand Machin indexer est lancé sur la base de test, en audit complet, pour ce sonore seulement
		Alors Machin indexer se termine avec le code 0
		Et la date de vérification complète du sonore est celle de ce lancement

		Exemples:
			| autre                                          |
			| une autre indexation rapide                    |
			| un autre audit complet                         |
			| une autre indexation rapide et un autre audit complet |

	Scénario: Un sonore inconnu est refusé
		Quand Machin indexer est lancé sur la base de test, en audit complet, pour le sonore 999999
		Alors Machin indexer se termine avec le code 1, en signalant « sonore 999999 : inconnu, ou pas un fichier »

	Scénario: Un stream est refusé, l'indexeur ne vérifie jamais les streams
		Étant donné un stream enregistré
		Quand Machin indexer est lancé sur la base de test, en audit complet, pour ce stream
		Alors Machin indexer refuse ce stream, qui n'est pas un fichier
		Et le stream n'a pas été modifié

	Scénario: --sound ne s'emploie pas avec --window
		Quand Machin indexer est lancé avec --window et --sound 1
		Alors Machin indexer se termine avec le code 2, en signalant « --sound ne s'emploie pas avec --window »
