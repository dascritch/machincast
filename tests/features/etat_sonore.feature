# language: fr
Fonctionnalité: État d'un sonore
	En tant que programmateur d'antenne,
	je veux que l'état d'un sonore dise pourquoi il ne passe pas à l'antenne,
	afin de distinguer un choix de programmation d'un incident sur le fichier.

	Scénario: Un sonore a sept états possibles, dans un ordre fixe
		Étant donné une base de test vide où les migrations sont appliquées
		Alors le type "sound_state" a pour valeurs, dans l'ordre : preview, active, disabled, expired, corrupt, unsupported, missing

	Scénario: Un nouveau sonore est actif
		Étant donné une base de test vide où les migrations sont appliquées
		Quand j'enregistre un sonore sans préciser son état
		Alors son état est « active »

	Scénario: Un état inconnu est refusé
		Étant donné une base de test vide où les migrations sont appliquées
		Alors un sonore à l'état « inactif » est refusé
