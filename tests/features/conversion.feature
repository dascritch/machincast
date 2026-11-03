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
			| text_or_none    | rien                | rien                |
			| text_or_none    | le nombre 12        | le texte « 12 »     |
			| text_or_none    | le texte « »        | le texte « »        |
			| integer_or_none   | rien                | rien                |
			| integer_or_none   | le texte « 42 »     | l'entier 42         |
			| boolean_or_none  | rien                | rien                |
			| boolean_or_none  | le nombre 0         | faux                |
			| boolean_or_none  | le nombre 1         | vrai                |
			| duration_or_none    | rien                | rien                |
			| duration_or_none    | le texte « 3:20 »   | rien                |
			| duration_or_none    | la durée de 200 s   | la durée de 200 s   |
			| list_or_none    | rien                | rien                |
			| list_or_none    | l'ensemble 3, 1     | la liste 1, 3       |
