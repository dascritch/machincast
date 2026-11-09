# language: fr
Fonctionnalité: Indexation récursive des répertoires de banques
	En tant que programmateur de l'antenne,
	je veux que tout fichier audio déposé dans l'un des répertoires d'une banque y soit ajouté à la prochaine indexation,
	afin que alimenter une banque se limite à déposer des fichiers.

	https://github.com/dascritch/machincast/issues/9 — spec § 6.2. Chaque indexation parcourt d'abord les répertoires
	des banques, puis vérifie les sonores : un nouveau fichier, enregistré en aperçu, est décodé dans le même passage.

	# ─── Parcours ──────────────────────────────────────────────

	Scénario: Un fichier déposé dans le répertoire d'une banque y est ajouté puis vérifié
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Jingles » contient, dans l'ordre, « jingles/intro.flac »
		Et le sonore de « jingles/intro.flac » est à l'état « active »
		Et le bilan indique « indexation rapide : 1 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 1 sorti d'aperçu »

	Scénario: Les sous-répertoires sont parcourus, les fichiers ajoutés dans l'ordre de leur chemin
		Étant donné une banque « Fond » alimentée par le répertoire « fond »
		Et le fichier « fond/b/nappe.ogg », sain
		Et le fichier « fond/a/2/pluie.wav », sain
		Et le fichier « fond/a/1/vent.mp3 », sain
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Fond » contient, dans l'ordre, « fond/a/1/vent.mp3 », « fond/a/2/pluie.wav », « fond/b/nappe.ogg »

	Scénario: Seuls les fichiers des formats sonores sont indexés, quelle que soit la casse de leur extension
		L'AIFF n'est plus indexé, comme une extension inconnue : GStreamer en bloque parfois le démarrage
		(https://github.com/dascritch/machincast/issues/284).

		Étant donné une banque « Divers » alimentée par le répertoire « divers »
		Et le fichier « divers/MAJUSCULES.MP3 », sain
		Et le fichier « divers/court.aif », quelconque
		Et le fichier « divers/session.AIFF », quelconque
		Et le fichier « divers/note.txt », quelconque
		Et le fichier « divers/pochette.jpg », quelconque
		Et le fichier « divers/._intro.mp3 », quelconque
		Et le fichier « divers/.cache/cache.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Divers » contient, dans l'ordre, « divers/MAJUSCULES.MP3 »

	Plan du scénario: Chaque format de la spécification est indexé
		Étant donné une banque « Formats » alimentée par le répertoire « formats »
		Et le fichier « formats/son.<extension> », sain
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Formats » contient, dans l'ordre, « formats/son.<extension> »
		Et le sonore de « formats/son.<extension> » est à l'état « active »

		Exemples:
			| extension |
			| mp3       |
			| m4a       |
			| aac       |
			| ogg       |
			| flac      |
			| wav       |

	# ─── Pas de doublon ────────────────────────────────────────

	Scénario: Un fichier déjà indexé n'est pas dupliqué
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Et l'indexeur a fait une indexation rapide
		Quand l'indexeur fait une indexation rapide
		Alors la base contient 1 sonore
		Et la banque « Jingles » contient, dans l'ordre, « jingles/intro.flac »
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Un répertoire qui alimente deux banques donne un seul sonore, présent dans les deux banques
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et une banque « Identifiants » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors la base contient 1 sonore
		Et la banque « Jingles » contient, dans l'ordre, « jingles/intro.flac »
		Et la banque « Identifiants » contient, dans l'ordre, « jingles/intro.flac »
		Et le bilan indique « indexation rapide : 1 nouveau sonore, 1 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 1 sorti d'aperçu »

	Scénario: Un sonore retiré à la main d'une banque y est réintégré en fin de liste
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/a.flac », sain
		Et le fichier « jingles/b.flac », sain
		Et l'indexeur a fait une indexation rapide
		Et « jingles/a.flac » a été retiré à la main de la banque « Jingles »
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Jingles » contient, dans l'ordre, « jingles/b.flac », « jingles/a.flac »
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 1 rattachement, 0 retrait ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	# ─── Durées des sonores d'une banque (https://github.com/dascritch/machincast/issues/195) ───
	# Une banque qui a une durée minimale ou maximale (https://github.com/dascritch/machincast/issues/147) ne garde que
	# les sonores dont la durée en base est connue et dans ses limites, bornes comprises. Les fichiers de test durent une
	# seconde.
	#
	# Un sonore de durée encore inconnue, trouvé dans le répertoire d'une banque qui a des durées, n'y est rattaché
	# qu'une fois vérifié, à la fin du passage, et seulement s'il est dans ses durées : un sonore qui en sort ne passe
	# jamais par la banque, et rien ne le dit, ni au journal ni au bilan
	# (https://github.com/dascritch/machincast/issues/210).

	Scénario: Un nouveau fichier hors des durées n'entre pas dans la banque, sans retrait au journal ni au bilan
		Étant donné une banque « Longs » alimentée par le répertoire « longs »
		Et la banque « Longs » n'accepte que les sonores d'au moins 2 secondes
		Et le fichier « longs/court.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Longs » ne contient aucun sonore
		Et le sonore de « longs/court.flac » est à l'état « active »
		Et le bilan indique « indexation rapide : 1 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 1 sorti d'aperçu »
		Et la sortie standard montre, ligne par ligne :
			| ligne                                              |
			| …/longs/court.flac : sain ; sonore passé actif     |
			| …/longs/court.flac : nouveau sonore                |

	Scénario: Un nouveau fichier dans les durées entre dans la banque une fois vérifié
		Étant donné une banque « Courts » alimentée par le répertoire « courts »
		Et la banque « Courts » n'accepte que les sonores d'au plus 2 secondes
		Et le fichier « courts/a.flac », sain
		Et le fichier « courts/b.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Courts » contient, dans l'ordre, « courts/a.flac », « courts/b.flac »
		Et le bilan indique « indexation rapide : 2 nouveaux sonores, 0 rattachement, 0 retrait ; 2 sonores vérifiés ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 2 sortis d'aperçu »
		Et la sortie standard montre, ligne par ligne :
			| ligne                                                       |
			| …/courts/a.flac : sain ; sonore passé actif                 |
			| …/courts/b.flac : sain ; sonore passé actif                 |
			| …/courts/a.flac : nouveau sonore, ajouté à la banque Courts |
			| …/courts/b.flac : nouveau sonore, ajouté à la banque Courts |

	Scénario: Un nouveau fichier de deux banques n'est annoncé que dans celle dont il respecte les durées
		Étant donné une banque « Identifiants » alimentée par le répertoire « jingles »
		Et la banque « Identifiants » n'accepte que les sonores d'au plus 0,5 seconde
		Et une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Quand l'indexeur fait un audit complet
		Alors la banque « Identifiants » ne contient aucun sonore
		Et la banque « Jingles » contient, dans l'ordre, « jingles/intro.flac »
		Et le bilan indique « audit complet : 1 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 1 sorti d'aperçu »
		Et la sortie standard montre, ligne par ligne :
			| ligne                                                              |
			| …/jingles/intro.flac : nouveau sonore, ajouté à la banque Jingles  |
			| …/jingles/intro.flac : sain ; sonore passé actif                   |

	Scénario: Un sonore connu, de durée encore inconnue, hors des durées, n'entre pas dans la banque, sans rien en dire
		Étant donné une banque « Longs » alimentée par le répertoire « longs »
		Et la banque « Longs » n'accepte que les sonores d'au moins 2 secondes
		Et le fichier « longs/court.flac », sain
		Et un sonore à l'état « preview », de durée inconnue, pour « longs/court.flac »
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Longs » ne contient aucun sonore
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 1 sorti d'aperçu »
		Et la sortie standard montre, ligne par ligne :
			| ligne                                              |
			| …/longs/court.flac : sain ; sonore passé actif     |

	Scénario: Une indexation arrêtée pendant la vérification rattache les sonores de durée encore inconnue, sans rien retirer
		Étant donné une banque « Longs » alimentée par le répertoire « longs »
		Et la banque « Longs » n'accepte que les sonores d'au moins 2 secondes
		Et le fichier « longs/a.flac », sain
		Et le fichier « longs/b.flac », sain
		Quand l'indexeur fait une indexation rapide, arrêtée pendant la vérification du premier sonore
		Alors la banque « Longs » contient, dans l'ordre, « longs/b.flac »
		Et le bilan indique « indexation rapide : 2 nouveaux sonores, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 1 sorti d'aperçu »
		Et la sortie standard montre, ligne par ligne :
			| ligne                                                    |
			| …/longs/a.flac : sain ; sonore passé actif               |
			| …/longs/b.flac : nouveau sonore, ajouté à la banque Longs |
			| …/longs/a.flac : nouveau sonore                          |

	Scénario: Un sonore connu, hors des durées, n'est pas rattaché à la banque de son répertoire
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/a.flac », sain
		Et l'indexeur a fait une indexation rapide
		Et « jingles/a.flac » a été retiré à la main de la banque « Jingles »
		Et la banque « Jingles » n'accepte que les sonores d'au moins 2 secondes
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Jingles » ne contient aucun sonore
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Des durées resserrées retirent les sonores dès l'indexation rapide suivante, même ajoutés à la main
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/a.flac », sain
		Et le fichier « jingles/b.flac », sain
		Et une banque « Divers » alimentée par le répertoire « ailleurs »
		Et le fichier « ailleurs/c.flac », sain
		Et l'indexeur a fait une indexation rapide
		Et « ailleurs/c.flac » est ajouté à la main à la banque « Jingles »
		Et la durée en base du sonore de « jingles/a.flac » est de 120 secondes
		Et la durée en base du sonore de « jingles/b.flac » est de 121 secondes
		Et la durée en base du sonore de « ailleurs/c.flac » est de 30 secondes
		Et la banque « Jingles » n'accepte que les sonores de 60 à 120 secondes
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Jingles » contient, dans l'ordre, « jingles/a.flac »
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 2 retraits ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »
		Et la sortie standard montre, ligne par ligne :
			| ligne                                                                                          |
			| …/jingles/b.flac : retiré de la banque Jingles, durée 2:01 plus longue que son maximum, 2:00   |
			| …/ailleurs/c.flac : retiré de la banque Jingles, durée 0:30 plus courte que son minimum, 1:00  |

	Scénario: Un sonore retiré d'une banque reste en base et dans ses autres banques
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et une banque « Identifiants » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Et l'indexeur a fait une indexation rapide
		Et la banque « Identifiants » n'accepte que les sonores d'au plus 0,5 seconde
		Quand l'indexeur fait un audit complet
		Alors la banque « Identifiants » ne contient aucun sonore
		Et la banque « Jingles » contient, dans l'ordre, « jingles/intro.flac »
		Et la base contient 1 sonore
		Et le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement, 1 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Un sonore de durée inconnue n'est jamais retiré
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et la banque « Jingles » n'accepte que les sonores de 60 à 120 secondes
		Et le stream « Direct » est ajouté à la main à la banque « Jingles »
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Jingles » contient le stream « Direct »
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Une indexation arrêtée avant son début ne retire aucun sonore
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/a.flac », sain
		Et l'indexeur a fait une indexation rapide
		Et la banque « Jingles » n'accepte que les sonores d'au moins 2 secondes
		Quand l'indexeur fait une indexation rapide, dont l'arrêt est déjà demandé
		Alors la banque « Jingles » contient, dans l'ordre, « jingles/a.flac »

	Scénario: Machin indexer --sound retire ce seul sonore des banques dont il sort des durées
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/a.flac », sain
		Et le fichier « jingles/b.flac », sain
		Et l'indexeur a fait une indexation rapide
		Et la banque « Jingles » n'accepte que les sonores d'au moins 2 secondes
		Quand l'indexeur vérifie seulement le sonore de « jingles/a.flac », en audit complet
		Alors la banque « Jingles » contient, dans l'ordre, « jingles/b.flac »
		Et le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement, 1 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	# ─── Sortie ligne par ligne ────────────────────────────────

	Scénario: Chaque sonore indexé a sa ligne sur la sortie standard, avec son statut
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Et le fichier « jingles/abime.mp3 », endommagé
		Quand l'indexeur fait une indexation rapide
		Alors la sortie standard montre, ligne par ligne :
			| ligne                                                            |
			| …/jingles/abime.mp3 : nouveau sonore, ajouté à la banque Jingles |
			| …/jingles/intro.flac : nouveau sonore, ajouté à la banque Jingles |
			| …/jingles/intro.flac : sain ; sonore passé actif                 |
		Et la sortie d'erreur signale « …/jingles/abime.mp3 », avec « sonore passé erroné »

	# ─── Une indexation rapide et un audit complet à la fois ───
	# https://github.com/dascritch/machincast/issues/401 : chaque mode a son verrou ; l'audit d'un sonore nommé n'en
	# prend aucun (sound_indexing.feature).

	Scénario: Machin indexer refuse une indexation rapide pendant une autre indexation rapide sur la même base
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Et une autre indexation rapide en cours sur la base
		Quand Machin indexer est lancé sur la base de test
		Alors Machin indexer se termine avec le code 1, en signalant « indexation refusée : une autre indexation rapide est en cours sur cette base »
		Et la base contient 0 sonore
		Quand l'autre indexation se termine
		Et Machin indexer est lancé sur la base de test
		Alors Machin indexer se termine avec le code 0, en signalant « indexation rapide : 1 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 1 sorti d'aperçu »
		Et la base contient 1 sonore

	Scénario: Machin indexer refuse un audit complet pendant un autre audit complet sur la même base
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Et un autre audit complet en cours sur la base
		Quand Machin indexer est lancé sur la base de test, en audit complet
		Alors Machin indexer se termine avec le code 1, en signalant « indexation refusée : un autre audit complet est en cours sur cette base »
		Et la base contient 0 sonore

	Plan du scénario: Une indexation rapide et un audit complet tournent en même temps
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Et <autre> en cours sur la base
		Quand Machin indexer est lancé sur la base de test<mode>
		Alors Machin indexer se termine avec le code 0
		Et la base contient 1 sonore

		Exemples:
			| autre                       | mode                 |
			| un autre audit complet      |                      |
			| une autre indexation rapide | , en audit complet   |

	Scénario: Deux indexations qui trouvent le même nouveau fichier ne l'enregistrent qu'une fois
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Et une autre indexation qui enregistre « jingles/intro.flac » dans la banque « Jingles », sans avoir fini
		Quand l'indexeur commence une indexation rapide
		Et l'autre indexation se termine
		Alors l'indexation rapide se termine sans erreur
		Et la base contient 1 sonore
		Et la banque « Jingles » contient 1 sonore

	Scénario: Une indexation arrêtée avant son début n'enregistre ni ne vérifie rien
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Quand l'indexeur fait une indexation rapide, dont l'arrêt est déjà demandé
		Alors la base contient 0 sonore
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: L'indexation rend son verrou dès sa fin
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors le verrou de l'indexation rapide a été rendu dès la fin de l'indexation

	Scénario: Un rattachement a sa ligne, et un sonore revérifié dit que son état est conservé
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/a.flac », sain
		Et l'indexeur a fait une indexation rapide
		Et « jingles/a.flac » a été retiré à la main de la banque « Jingles »
		Quand l'indexeur fait un audit complet
		Alors la sortie standard montre, ligne par ligne :
			| ligne                                       |
			| …/jingles/a.flac : rattaché à la banque Jingles |
			| …/jingles/a.flac : sain ; état actif conservé  |

	Scénario: Un nouveau fichier s'ajoute après les sonores déjà présents dans la banque
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/b.flac », sain
		Et l'indexeur a fait une indexation rapide
		Et le fichier « jingles/a.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Jingles » contient, dans l'ordre, « jingles/b.flac », « jingles/a.flac »

	# ─── Anomalies ─────────────────────────────────────────────

	Scénario: Un répertoire introuvable est signalé, les autres banques sont indexées
		Étant donné une banque « Absente » alimentée par le répertoire « nulle-part »
		Et une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Quand l'indexeur fait une indexation rapide
		Alors la sortie d'erreur signale le répertoire « nulle-part » comme introuvable, pour la banque « Absente »
		Et la banque « Jingles » contient, dans l'ordre, « jingles/intro.flac »

	Scénario: Un fichier défectueux déposé dans une banque y est ajouté, puis signalé et passé erroné
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/abime.mp3 », endommagé
		Quand l'indexeur fait une indexation rapide
		Alors la banque « Jingles » contient, dans l'ordre, « jingles/abime.mp3 »
		Et le sonore de « jingles/abime.mp3 » est à l'état « corrupt »

	# ─── Fichier déplacé (https://github.com/dascritch/machincast/issues/10) ─────

	Scénario: Un fichier déplacé est enregistré comme un nouveau sonore, et l'ancien passe supprimé
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et le fichier « jingles/intro.flac », sain
		Et l'indexeur a fait une indexation rapide
		Et « jingles/intro.flac » déplacé en « jingles/archives/intro.flac »
		Quand l'indexeur fait une indexation rapide
		Alors le sonore de « jingles/intro.flac » est à l'état « missing »
		Et le sonore de « jingles/archives/intro.flac » est à l'état « active »

	# ─── Volume (https://github.com/dascritch/machincast/issues/390) ─

	Scénario: L'indexation rapide de sonores déjà rattachés fait quelques requêtes, quel que soit leur nombre
		Un fichier déjà rattaché à la banque ne demande rien à la base au parcours des répertoires ; la vérification lit
		les sonores par lots ; les retraits se font en une requête.

		Étant donné une banque « Jingles » alimentée par le répertoire « jingles »
		Et 30 fichiers sains dans le répertoire « jingles »
		Et l'indexeur a fait une indexation rapide
		Quand l'indexeur fait une indexation rapide, en comptant ses requêtes
		Alors le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »
		Et la banque « Jingles » contient 30 sonores
		Et l'indexation a fait au plus 12 requêtes

	Scénario: La vérification lit les sonores par lots, sans en oublier aucun
		Étant donné la vérification lit les sonores par lots de 4
		Et une banque « Jingles » alimentée par le répertoire « jingles »
		Et 10 fichiers sains dans le répertoire « jingles »
		Quand l'indexeur fait une indexation rapide
		Alors le bilan indique « indexation rapide : 10 nouveaux sonores, 0 rattachement, 0 retrait ; 10 sonores vérifiés ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 10 sortis d'aperçu »
		Et la banque « Jingles » contient 10 sonores
