# language: fr
Fonctionnalité: Indexation d'un seul sonore
	En tant que technicien d'antenne,
	je veux pouvoir vérifier un seul sonore, sans reprendre toute l'indexation,
	afin que Machin lecture fasse analyser au dernier moment le sonore qu'il va jouer.

	https://github.com/dascritch/machincast/issues/181. « Machin indexation --sonore N » ne vérifie que le sonore N,
	sans parcourir les répertoires des banques, avec --audit-complet pour décoder son fichier quoi qu'il en soit. Il ne
	prend pas le verrou de l'indexation, comme la vérification des fichiers ajoutés depuis l'interface : une
	indexation complète peut tourner en même temps. Il n'écrit pas de document d'audit : une anomalie est signalée
	sur la sortie d'erreur, comme toujours.

	Scénario: Un audit complet d'un seul sonore ne vérifie que lui
		Étant donné un fichier flac sain
		Et un sonore à l'état « actif » pour ce fichier
		Et un deuxième fichier flac sain, dont le sonore est à l'état « actif »
		Quand Machin indexation est lancé sur la base de test, en audit complet, pour ce sonore seulement
		Alors Machin indexation se termine avec le code 0
		Et la date de vérification complète du sonore est celle de ce lancement
		Et le deuxième sonore n'a pas de date de vérification complète
		Et aucun document d'audit n'est écrit

	Scénario: Un audit complet d'un seul sonore se fait même pendant une autre indexation
		Étant donné un fichier flac sain
		Et un sonore à l'état « actif » pour ce fichier
		Et une autre indexation en cours sur la base
		Quand Machin indexation est lancé sur la base de test, en audit complet, pour ce sonore seulement
		Alors Machin indexation se termine avec le code 0
		Et la date de vérification complète du sonore est celle de ce lancement

	Scénario: Un sonore inconnu est refusé
		Quand Machin indexation est lancé sur la base de test, en audit complet, pour le sonore 999999
		Alors Machin indexation se termine avec le code 1, en signalant « sonore 999999 : inconnu, ou pas un fichier »

	Scénario: Un stream est refusé, l'indexeur ne vérifie jamais les streams
		Étant donné un stream enregistré
		Quand Machin indexation est lancé sur la base de test, en audit complet, pour ce stream
		Alors Machin indexation refuse ce stream, qui n'est pas un fichier
		Et le stream n'a pas été modifié

	Scénario: --sonore ne s'emploie pas avec --fenetre
		Quand Machin indexation est lancé avec --fenetre et --sonore 1
		Alors Machin indexation se termine avec le code 2, en signalant « --sonore ne s'emploie pas avec --fenetre »
