# language: fr
Fonctionnalité: Lecture des tags
	En tant que programmateur de l'antenne,
	je veux que l'artiste, le titre et les métadonnées musicales soient pré-remplis depuis les tags du fichier,
	afin de ne pas avoir à les saisir à la main.

	Les fichiers tags.* de tests/fichiers-sonores portent : artiste « Les Gaufres Électriques », titre « Café à minuit »,
	album « Été indien », artiste de l'album « Collectif Exemple », genre « Chanson », compositeur « Jeanne Exemple »,
	label « Disques Exemple », piste 7, date 1987-06-21. Les fichiers sain.* n'ont aucun tag.

	# ─── Lecture ───────────────────────────────────────────────

	Plan du scénario: Les tags d'un fichier sont lus pendant sa vérification
		Étant donné un fichier <format> tagué
		Quand je vérifie ce fichier
		Alors l'artiste lu est « Les Gaufres Électriques » et le titre lu « Café à minuit »
		Et les métadonnées musicales lues sont <metadonnees>

		Exemples:
			| format | metadonnees                                                                                                                                                  |
			| flac   | {"annee": 1987, "album": "Été indien", "artiste_album": "Collectif Exemple", "genre": "Chanson", "compositeur": "Jeanne Exemple", "label": "Disques Exemple", "piste": 7} |
			| ogg    | {"annee": 1987, "album": "Été indien", "artiste_album": "Collectif Exemple", "genre": "Chanson", "compositeur": "Jeanne Exemple", "label": "Disques Exemple", "piste": 7} |
			| mp3    | {"annee": 1987, "album": "Été indien", "artiste_album": "Collectif Exemple", "genre": "Chanson", "compositeur": "Jeanne Exemple", "piste": 7}                             |
			| m4a    | {"annee": 1987, "album": "Été indien", "artiste_album": "Collectif Exemple", "genre": "Chanson", "compositeur": "Jeanne Exemple", "piste": 7}                             |
			| wav    | {"annee": 1987, "album": "Été indien", "artiste_album": "Collectif Exemple", "genre": "Chanson"}                                                                          |

	Plan du scénario: Un fichier sans tags n'a ni artiste, ni titre, ni métadonnées musicales
		Étant donné un fichier <format> sain
		Quand je vérifie ce fichier
		Alors aucun tag n'est lu

		Exemples:
			| format |
			| wav    |
			| flac   |
			| ogg    |
			| mp3    |
			| m4a    |

	Plan du scénario: L'année de sortie vient d'une date, jamais d'un horodatage de création
		Étant donné les tags « <tags> »
		Quand j'extrais ces tags
		Alors l'année retenue est <annee>

		Exemples:
			| tags                                                              | annee  |
			| taglist, date=(date)1987-06-21                                    | 1987   |
			| taglist, datetime=(datetime)1987                                  | 1987   |
			| taglist, datetime=(datetime)1987-06-21                            | 1987   |
			| taglist, datetime=(datetime)2026-10-15T06:35:40Z                  | aucune |
			| taglist, date=(date)1987-06-21, datetime=(datetime)2026-10-15T06:35:40Z | 1987   |

	Scénario: Le label vient de l'organisation ou de l'éditeur
		Étant donné les tags « taglist, publisher=(string)"Disques Exemple" »
		Quand j'extrais ces tags
		Alors les métadonnées musicales retenues sont {"label": "Disques Exemple"}

	Scénario: Un artiste ou un titre de plus de 255 caractères est tronqué
		Étant donné des tags dont l'artiste et le titre font 300 caractères
		Quand j'extrais ces tags
		Alors l'artiste et le titre retenus font 255 caractères

	Scénario: Des tags vides ou faits d'espaces sont ignorés
		Étant donné les tags « taglist, artist=(string)"  ", title=(string)"", album=(string)" Été indien " »
		Quand j'extrais ces tags
		Alors aucun artiste ni titre n'est retenu
		Et les métadonnées musicales retenues sont {"album": "Été indien"}

	# ─── Enregistrement en base ────────────────────────────────

	Scénario: Un sonore sain reçoit l'artiste, le titre et les métadonnées musicales de ses tags
		Étant donné un fichier flac tagué
		Et un sonore à l'état « actif » pour ce fichier
		Quand l'indexeur fait un audit complet
		Alors en base, l'artiste est « Les Gaufres Électriques » et le titre « Café à minuit »
		Et en base, les métadonnées musicales sont {"annee": 1987, "album": "Été indien", "artiste_album": "Collectif Exemple", "genre": "Chanson", "compositeur": "Jeanne Exemple", "label": "Disques Exemple", "piste": 7}

	Scénario: Les champs édités à la main ne sont jamais remplacés par les tags
		Étant donné un fichier flac tagué
		Et pour ce fichier, un sonore d'artiste « Saisi à la main » et de métadonnées {"annee": 1990, "commentaire": "Face B"}
		Et les champs « artiste » et « metadonnees_musicales.annee » de ce sonore édités à la main
		Quand l'indexeur fait un audit complet
		Alors en base, l'artiste est « Saisi à la main » et le titre « Café à minuit »
		Et en base, les métadonnées musicales sont {"annee": 1990, "commentaire": "Face B", "album": "Été indien", "artiste_album": "Collectif Exemple", "genre": "Chanson", "compositeur": "Jeanne Exemple", "label": "Disques Exemple", "piste": 7}

	Scénario: Un tag retiré du fichier efface le champ correspondant, s'il n'a pas été édité
		Étant donné un fichier flac sain
		Et pour ce fichier, un sonore de titre « Ancien titre » et de métadonnées {"album": "Ancien album", "commentaire": "Face B"}
		Quand l'indexeur fait un audit complet
		Alors en base, le sonore n'a ni artiste ni titre
		Et en base, les métadonnées musicales sont {"commentaire": "Face B"}

	Scénario: Un fichier défectueux ne change pas les tags enregistrés
		Étant donné un fichier mp3 endommagé
		Et pour ce fichier, un sonore de titre « Ancien titre » et de métadonnées {"album": "Ancien album"}
		Quand l'indexeur fait un audit complet
		Alors en base, le titre est toujours « Ancien titre »
		Et en base, les métadonnées musicales sont {"album": "Ancien album"}
