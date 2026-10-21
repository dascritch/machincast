# language: fr
Fonctionnalité: Conversion des valeurs lues en base ou dans un message
	En tant que développeur,
	je veux une seule façon de lire une valeur facultative, partagée par tous les modules,
	afin de ne pas la réécrire dans chacun.

	https://github.com/dascritch/machincast/issues/187. machincast.conversion remplace les fonctions _texte, _entier,
	_booleen, _duree et _liste que plusieurs modules réécrivaient à l'identique. Une valeur absente (None, NULL en
	base) reste absente.

	Plan du scénario: Chaque conversion garde une valeur absente, et convertit les autres
		Alors <conversion> de <entrée> donne <sortie>

		Exemples:
			| conversion       | entrée              | sortie              |
			| texte_ou_rien    | rien                | rien                |
			| texte_ou_rien    | le nombre 12        | le texte « 12 »     |
			| texte_ou_rien    | le texte « »        | le texte « »        |
			| entier_ou_rien   | rien                | rien                |
			| entier_ou_rien   | le texte « 42 »     | l'entier 42         |
			| booleen_ou_rien  | rien                | rien                |
			| booleen_ou_rien  | le nombre 0         | faux                |
			| booleen_ou_rien  | le nombre 1         | vrai                |
			| duree_ou_rien    | rien                | rien                |
			| duree_ou_rien    | le texte « 3:20 »   | rien                |
			| duree_ou_rien    | la durée de 200 s   | la durée de 200 s   |
			| liste_ou_rien    | rien                | rien                |
			| liste_ou_rien    | l'ensemble 3, 1     | la liste 1, 3       |
