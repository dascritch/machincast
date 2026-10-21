# language: fr
Fonctionnalité: Un fichier sonore n'est jamais supprimé par MachinCast
	En tant que responsable des archives sonores de la radio,
	je veux que MachinCast ne supprime jamais un fichier sonore, quels que soient les changements de son entrée dans la table sonores,
	afin qu'aucune manipulation dans le logiciel, ni aucune erreur de programmation, ne fasse perdre un enregistrement.

	https://github.com/dascritch/machincast/issues/96. Les fichiers d'une banque sont relevés avant leur première
	indexation : octets, taille et date de modification. « Intact » veut dire qu'aucun n'a changé, et qu'aucun n'a
	disparu.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et une banque « Musique » dont le répertoire contient « titre.flac », sain, et « abime.mp3 », endommagé
		Et les fichiers de la banque « Musique » relevés, puis la banque indexée

	# ─── Changements de l'entrée en base ───────────────────────

	Plan du scénario: Aucun changement de l'entrée d'un sonore ne touche son fichier
		Quand l'entrée du sonore « titre.flac » <changement>
		Et l'indexeur fait une indexation rapide, puis un audit complet
		Alors les fichiers sonores de la banque sont intacts

		Exemples:
			| changement                              |
			| passe à l'état « supprime »             |
			| passe à l'état « desactive »            |
			| passe à l'état « expire »               |
			| passe à l'état « errone »               |
			| change d'emplacement                    |
			| change d'artiste et de titre            |
			| est supprimée de la base                |

	Scénario: Un fichier dont l'entrée a été supprimée est réindexé comme nouveau sonore
		Quand l'entrée du sonore « titre.flac » est supprimée de la base
		Et l'indexeur fait une indexation rapide, puis un audit complet
		Alors le fichier « titre.flac » a de nouveau un sonore, à l'état « actif »
		Et les fichiers sonores de la banque sont intacts

	Scénario: Un fichier endommagé est déclaré erroné, et reste intact
		Quand l'indexeur fait une indexation rapide, puis un audit complet
		Alors le sonore de « abime.mp3 » est à l'état « errone »
		Et les fichiers sonores de la banque sont intacts

	# ─── Diffusion et simulation ───────────────────────────────

	Scénario: La diffusion et la simulation laissent les fichiers sonores intacts
		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le fil musical permanent « Continue », avec la banque « Musique »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Et une simulation d'une heure tourne
		Alors l'airplay montre 3 passages
		Et les fichiers sonores de la banque sont intacts

	Scénario: La détection de blanc, à l'audit complet puis à la diffusion, laisse les fichiers sonores intacts
		https://github.com/dascritch/machincast/issues/146 : les blancs détectés ne sont écrits qu'en base.

		Étant donné l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le fil musical permanent « Continue », avec la banque « Musique »
		Et la banque « Musique » active la détection de blanc
		Quand l'indexeur fait une indexation rapide, puis un audit complet
		Et la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Et la diffusion s'arrête
		Alors le sonore de « titre.flac » a un début et une fin détectés
		Et l'airplay montre 3 passages
		Et les fichiers sonores de la banque sont intacts

	# ─── Sorties ───────────────────────────────────────────────

	Plan du scénario: Une sortie placée sur un fichier sonore est refusée à l'écriture, et le fichier reste intact
		Étant donné la sortie <sortie> placée sur le fichier sonore « titre.flac »
		Quand un passage de « titre.flac » est publié sur les sorties
		Alors le log contient 1 alerte « sortie inaccessible », qui mentionne « fichier sonore protégé »
		Et les fichiers sonores de la banque sont intacts

		Exemples:
			| sortie |
			| html   |
			| pls    |
			| csv    |

	Scénario: La socket d'état ne prend jamais la place d'un fichier sonore
		Quand la socket d'état est ouverte sur le fichier sonore « titre.flac »
		Alors l'ouverture est refusée, car c'est un fichier sonore protégé
		Et les fichiers sonores de la banque sont intacts

	Scénario: Les sorties de la simulation ne prennent jamais la place d'un fichier sonore
		Quand une simulation est exportée sous le nom « titre », dans le répertoire de la banque
		Alors les fichiers sonores de la banque sont intacts

	# ─── Code ──────────────────────────────────────────────────

	Scénario: Le code ne supprime, ne renomme ni ne remplace aucun fichier sans dire qu'il est créé par MachinCast
		Alors chaque suppression, renommage ou remplacement de fichier de src, bin et install.sh porte la justification « fichier de MachinCast : »

	Plan du scénario: Le garde-fou repère une suppression de fichier sans justification
		Étant donné le code « <code> »
		Alors le garde-fou <verdict> ce code

		Exemples:
			| code                                                              | verdict  |
			| chemin.unlink()                                                   | refuse   |
			| os.remove(chemin)                                                 | refuse   |
			| shutil.rmtree(repertoire)                                         | refuse   |
			| os.replace(source, chemin)                                        | refuse   |
			| chemin.rename(cible)                                              | refuse   |
			| rm -rf "${REPERTOIRE}"                                            | refuse   |
			| mv "${A}" "${B}"                                                  | refuse   |
			| chemin.unlink()  # fichier de MachinCast : socket d'état          | accepte  |
			| texte.replace("a", "b")                                           | accepte  |
