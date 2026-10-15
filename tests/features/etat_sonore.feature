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

	Scénario: Le booléen actif a disparu
		Étant donné une base de test vide où les migrations sont appliquées
		Alors la table "sonores" n'a pas de colonne "actif"

	Scénario: La migration convertit l'ancien booléen actif et les champs édités
		Étant donné une base où seules les migrations antérieures à « 0003 » sont appliquées
		Et dans cette base, les sonores :
			| emplacement | actif | champs_edites |
			| /a.flac     | true  | {}            |
			| /b.flac     | false | {}            |
			| /c.flac     | true  | {actif,titre} |
		Quand j'applique les migrations restantes
		Alors les sonores sont devenus :
			| emplacement | etat      | champs_edites |
			| /a.flac     | actif     | {}            |
			| /b.flac     | desactive | {}            |
			| /c.flac     | actif     | {etat,titre}  |

	Scénario: L'annulation de la migration rétablit le booléen actif
		Étant donné une base de test vide où les migrations sont appliquées
		Et un sonore dans chacun des cinq états
		Quand j'annule la migration « 0003 »
		Alors seul le sonore qui était à l'état « actif » est actif

	Scénario: L'annulation de la migration de l'aperçu rend actifs les sonores en aperçu
		Étant donné une base de test vide où les migrations sont appliquées
		Et un sonore à l'état « apercu » et un sonore à l'état « errone »
		Quand j'annule la migration « 0004 »
		Alors le type "etat_sonore" a pour valeurs, dans l'ordre : actif, desactive, expire, errone, supprime
		Et les sonores sont aux états « actif » et « errone »
