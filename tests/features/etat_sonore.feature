# language: fr
Fonctionnalité: État d'un sonore
	En tant que programmateur d'antenne,
	je veux que l'état d'un sonore dise pourquoi il ne passe pas à l'antenne,
	afin de distinguer un choix de programmation d'un incident sur le fichier.

	Scénario: Un sonore a six états possibles, dans un ordre fixe
		Étant donné une base de test vide où les migrations sont appliquées
		Alors le type "etat_sonore" a pour valeurs, dans l'ordre : apercu, actif, desactive, expire, errone, supprime

	Scénario: Un nouveau sonore est actif
		Étant donné une base de test vide où les migrations sont appliquées
		Quand j'enregistre un sonore sans préciser son état
		Alors son état est « actif »

	Scénario: Un état inconnu est refusé
		Étant donné une base de test vide où les migrations sont appliquées
		Alors un sonore à l'état « inactif » est refusé
