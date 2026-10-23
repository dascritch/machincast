# language: fr
Fonctionnalité: Conformation des textes
	En tant que technicien antenne,
	je veux conformer les textes entrés dans l'interface et ceux lus dans les tags des fichiers,
	afin d'éviter les caractères spéciaux qui posent problème sur le reste de la chaîne de diffusion.

	https://github.com/dascritch/machincast/issues/108. machincast.conformation.conformer ne fait que filtrer : tout
	espace Unicode devient une espace simple (0x20), les espaces de début et de fin sont retirées, et jamais deux
	espaces ne se suivent ; les caractères de contrôle, les sélecteurs de variante, les caractères spéciaux
	(U+FFF0 à U+FFFF), les caractères à usage privé, les caractères non attribués et les espaces sans largeur
	(U+200B, U+FEFF) sont supprimés. Le reste est gardé tel quel, sans normalisation : lettres accentuées, écritures
	non latines, emoji.

	Dans les scénarios, « \u{a0} » écrit le caractère U+00A0, et une case vide un texte vide.

	Plan du scénario: Un texte est conformé
		Quand je conforme le texte « <texte> »
		Alors le texte conformé est « <conforme> »

		Exemples:
			| texte                                     | conforme                 |
			| Café\u{a0}à\u{202f}minuit                 | Café à minuit            |
			| \u{20}\u{3000}Les Gaufres\u{2003}\u{20}   | Les Gaufres              |
			| Tabulation\u{9}et\u{a}retour\u{d}\u{a}    | Tabulation et retour     |
			| Deux  espaces   et plus                   | Deux espaces et plus     |
			| Cloche\u{7}\u{1b}[0m et\u{0} nul          | Cloche[0m et nul         |
			| Effacement\u{7f} et C1\u{9b}              | Effacement et C1         |
			| Étoile ⭐\u{fe0f}                          | Étoile ⭐                 |
			| Idéogramme 葛\u{e0100}                     | Idéogramme 葛             |
			| Mongol\u{180b}                            | Mongol                   |
			| Spécial\u{fff0}\u{fffc}\u{fffd}            | Spécial                  |
			| Privé\u{e000}\u{f8ff}\u{f0000}\u{10fffd}   | Privé                    |
			| Sans\u{200b}largeur\u{feff}               | Sanslargeur              |
			| Non attribué\u{378}                       | Non attribué             |
			| Demi\u{d800}codet                         | Demicodet                |
			| \u{a0}\u{a0}\u{2028}                      |                          |
			| Ærø, straße, Ωμέγα, 日本語, 🎵             | Ærø, straße, Ωμέγα, 日本語, 🎵 |

	Scénario: Les tags lus dans un fichier sont conformés
		Étant donné les tags d'un fichier :
			| tag    | valeur                             |
			| artist | \u{20}Les\u{a0}\u{a0}Gaufres\u{feff} |
			| title  | Café\u{9}à minuit\u{fe0f}          |
			| album  | Nuit\u{e000} blanche               |
			| genre  | \u{a0}\u{200b}                     |
		Quand l'indexeur extrait ces tags
		Alors l'artiste extrait est « Les Gaufres », le titre « Café à minuit »
		Et les métadonnées musicales extraites sont « album » « Nuit blanche », sans genre

	Plan du scénario: Un texte saisi dans une fiche est enregistré conformé
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-20 18:50:00 »
		Et la banque « Jingles », séquentielle, sans nom public, avec aucun
		Et la séquence « Pub », sans nom public, avec rien
		Et les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Et les feeds « Radio » « https://flux.exemple/radio »
		Et les sonores :
			| artiste | titre  | type    | etat  | duree | emplacement        |
			| Gaufres | Minuit | fichier | actif | 180   | /musique/minuit.ogg |
		Quand la fenêtre de l'interface s'ouvre
		Et <ouverture>
		Et je saisis « <saisie> » dans le champ « <champ> » de la fiche
		Et j'enregistre la fiche
		Alors en base, <colonne> de <table> vaut « <enregistre> »

		Exemples:
			| ouverture                                  | champ       | saisie                        | table         | colonne                            | enregistre       |
			| j'ouvre la fiche de la banque « Jingles »  | nom_interne | \u{20}Jingles\u{a0}\u{a0}soir | banques       | nom_interne                        | Jingles soir     |
			| j'ouvre la fiche de la banque « Jingles »  | nom_public  | Les\u{2003}jingles\u{fe0f}    | banques       | nom_public                         | Les jingles      |
			| j'ouvre la fiche de la séquence « Pub »    | nom_interne | Pub\u{9}du\u{e000} soir       | sequences     | nom_interne                        | Pub du soir      |
			| j'ouvre la fiche de la séquence « Pub »    | nom_public  | \u{a0}                        | sequences     | nom_public                         |                  |
			| j'ouvre la fiche de l'événement « Continue » | nom_interne | Continue\u{200b}  nuit      | evenements    | nom_interne                        | Continue nuit    |
			| j'ouvre la fiche de l'événement « Continue » | nom_public  | La\u{202f}nuit\u{7}         | evenements    | nom_public                         | La nuit          |
			| j'ouvre la fiche du feed « Radio »  | nom         | Radio\u{a0}\u{a0}locale\u{feff} | feeds | nom                       | Radio locale     |
			| j'ouvre la fiche du sonore « Minuit »      | artiste     | Les\u{a0}Gaufres\u{20}        | sonores       | artiste                            | Les Gaufres      |
			| j'ouvre la fiche du sonore « Minuit »      | titre       | Café\u{2028}à minuit          | sonores       | titre                              | Café à minuit    |
			| j'ouvre la fiche du sonore « Minuit »      | album       | Nuit\u{fffd} blanche          | sonores       | metadonnees_musicales.album        | Nuit blanche     |
