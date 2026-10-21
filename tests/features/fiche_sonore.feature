# language: fr
Fonctionnalité: Fiche d'un sonore
	En tant que programmateur de l'antenne,
	je veux éditer tous les champs d'un sonore et consulter son historique,
	afin de contrôler précisément sa diffusion.

	https://github.com/dascritch/machincast/issues/28, spec § 8.3. La fiche s'ouvre dans un onglet qui se ferme, depuis
	la liste des sonores, comme celle d'une banque (fiche_banque.feature, qui vérifie aussi l'enregistrement, l'annulation
	et la fermeture, communs aux fiches). Un champ modifié à l'enregistrement est ajouté à champs_edites, sauf l'état :
	l'indexeur ne le modifie plus. Les champs non modifiés ne sont pas réécrits.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-16 20:00:30 »
		Et les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement                  |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/jingles/hiver/cafe.flac |
		Et le sonore « Café à minuit » a en base :
			| champ                 | valeur                                                       |
			| metadonnees_musicales | {"annee": 1998, "album": "Nuit blanche", "isrc": "FR-Z03"}   |
			| crossfade_debut       | 1.5 s                                                        |
			| max_lectures          | 12                                                           |
			| debut_diffusion       | 2026-10-01 00:00                                             |
			| champs_edites         | {titre}                                                      |

	# ─── Ouverture ─────────────────────────────────────────────

	Scénario: La fiche d'un sonore s'ouvre dans un onglet, depuis la liste des sonores
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ouvre la ligne « Café à minuit »
		Alors l'onglet ouvert est « Sonore : Café à minuit »
		Et l'écran de détail de sonore « Café à minuit » est demandé
		Et la fiche du sonore montre :
			| champ                 | valeur                       |
			| Type                  | fichier                      |
			| Emplacement           | /srv/jingles/hiver/cafe.flac |
			| Durée                 | 3:34                         |
			| État                  | actif                        |
			| Artiste               | Les Gaufres                  |
			| Titre                 | Café à minuit                |
			| Année                 | 1998                         |
			| Album                 | Nuit blanche                 |
			| Artiste de l'album    |                              |
			| Genre                 |                              |
			| Compositeur           |                              |
			| Label                 |                              |
			| Piste                 |                              |
			| Crossfade de début    | 1,5 s                        |
			| Crossfade de fin      |                              |
			| Maximum de lectures   | 12                           |
			| Artiste et titre      | selon la configuration       |
			| Diffusion à partir du | 01/10/2026 00:00             |
			| Diffusion jusqu'au    |                              |
		Et la fiche du sonore montre les autres métadonnées « isrc : FR-Z03 »
		Et la fiche du sonore montre les champs saisis à la main « titre »
		Et l'emplacement de la fiche du sonore ne se modifie pas
		Et les dates de diffusion qui se saisissent sont « Diffusion à partir du »

	Scénario: Les autres métadonnées sont rangées par clé
		Étant donné le sonore « Café à minuit » a en base :
			| champ                 | valeur                                  |
			| metadonnees_musicales | {"zz": 1, "isrc": "FR-Z03", "bpm": 120} |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors la fiche du sonore montre les autres métadonnées « bpm : 120, isrc : FR-Z03, zz : 1 »

	Plan du scénario: Un sonore sans titre est nommé par son fichier, ou par son adresse
		Étant donné les sonores :
			| artiste | titre | type    | etat   | duree | emplacement                 |
			|         |       | fichier | apercu |       | /srv/jingles/brut.flac      |
			|         |       | stream  | actif  |       | https://flux.exemple/direct |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « <emplacement> »
		Alors l'onglet ouvert est « Sonore : <nom> »

		Exemples:
			| emplacement                 | nom                         |
			| /srv/jingles/brut.flac      | brut.flac                   |
			| https://flux.exemple/direct | https://flux.exemple/direct |

	Scénario: Une banque et un sonore de même identifiant ont chacun leur fiche
		Étant donné la banque « Jingles », séquentielle, sans nom public, avec « Café à minuit »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et j'ouvre la fiche de la banque « Jingles »
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors l'onglet ouvert est « Sonore : Café à minuit »
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Marques-pages », « Incidents », « Banque : Jingles », « Sonore : Café à minuit »

	# ─── Métadonnées ───────────────────────────────────────────

	Scénario: Les métadonnées modifiées partent en base, et sont marquées comme saisies à la main
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je saisis dans la fiche du sonore :
			| champ       | valeur           |
			| Artiste     | ⎵Les Gaufrettes⎵ |
			| Titre       | Café du matin    |
			| Année       | 1999             |
			| Genre       | Jazz             |
			| Piste       | 4                |
		Et j'enregistre la fiche
		Alors le sonore « Café du matin » est en base, d'artiste « Les Gaufrettes »
		Et les métadonnées musicales de « Café du matin » sont {"annee": 1999, "album": "Nuit blanche", "genre": "Jazz", "isrc": "FR-Z03", "piste": 4}
		Et les champs saisis à la main de « Café du matin » sont « titre », « artiste », « metadonnees_musicales.annee », « metadonnees_musicales.genre », « metadonnees_musicales.piste »
		Et l'onglet ouvert est « Sonore : Café du matin »
		Et la fiche du sonore montre les champs saisis à la main « titre », « artiste », « année », « genre », « piste »

	Scénario: Un champ vidé efface sa valeur, et reste marqué : l'indexeur ne le remplira plus
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je saisis dans la fiche du sonore :
			| champ   | valeur |
			| Artiste |        |
			| Album   |        |
			| Année   |        |
		Et j'enregistre la fiche
		Alors le sonore « Café à minuit » est en base, sans artiste
		Et les métadonnées musicales de « Café à minuit » sont {"isrc": "FR-Z03"}
		Et les champs saisis à la main de « Café à minuit » sont « titre », « artiste », « metadonnees_musicales.annee », « metadonnees_musicales.album »

	Scénario: Un champ remis à sa valeur n'est pas marqué
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je saisis dans la fiche du sonore :
			| champ   | valeur      |
			| Artiste | Autre       |
			| Genre   | Jazz        |
			| Artiste | Les Gaufres |
		Et j'enregistre la fiche
		Alors les champs saisis à la main de « Café à minuit » sont « titre », « metadonnees_musicales.genre »

	Scénario: Un sonore peut n'avoir ni artiste ni titre, et ses noms sont enregistrés sans les espaces qui les entourent
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je saisis dans la fiche du sonore :
			| champ   | valeur |
			| Artiste |        |
			| Titre   |        |
			| Album   | ⎵Nuit⎵ |
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et l'onglet ouvert est « Sonore : cafe.flac »
		Et le sonore « cafe.flac » est en base, sans artiste ni titre
		Et les métadonnées musicales de « cafe.flac » sont {"annee": 1998, "album": "Nuit", "isrc": "FR-Z03"}

	Scénario: Les champs que la fiche n'a pas modifiés ne sont pas réécrits, même changés entre-temps par l'indexation
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et l'indexation change le titre de « Café à minuit » en « Café de nuit », et son album en « Nuit noire »
		Et je saisis dans la fiche du sonore :
			| champ   | valeur |
			| Artiste | Aube   |
			| Genre   | Jazz   |
		Et j'enregistre la fiche
		Alors le sonore « Café de nuit » est en base, d'artiste « Aube »
		Et les métadonnées musicales de « Café de nuit » sont {"annee": 1998, "album": "Nuit noire", "genre": "Jazz", "isrc": "FR-Z03"}

	# ─── Diffusion ─────────────────────────────────────────────

	Scénario: Les réglages de diffusion modifiés partent en base, et sont marqués
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je saisis dans la fiche du sonore :
			| champ                 | valeur           |
			| Crossfade de début    | 0,5              |
			| Crossfade de fin      | 2,2              |
			| Maximum de lectures   | 3                |
			| Artiste et titre      | masqués          |
			| Diffusion à partir du | 02/10/2026 08:00 |
			| Diffusion jusqu'au    | 31/12/2026 23:30 |
		Et j'enregistre la fiche
		Alors le sonore « Café à minuit » a en base :
			| champ               | valeur                    |
			| crossfade_debut     | 0:00:00.500000            |
			| crossfade_fin       | 0:00:02.200000            |
			| max_lectures        | 3                         |
			| masquer_metadonnees | True                      |
			| debut_diffusion     | 2026-10-02 08:00:00+02:00 |
			| fin_diffusion       | 2026-12-31 23:30:00+01:00 |
		Et les champs saisis à la main de « Café à minuit » sont « titre », « crossfade_debut », « crossfade_fin », « max_lectures », « masquer_metadonnees », « debut_diffusion », « fin_diffusion »

	Scénario: Un crossfade se paramètre en le cochant, et 0 seconde en est un
		https://github.com/dascritch/machincast/issues/145 : décoché, le crossfade n'est pas paramétré ; il vient alors de la banque ou de la
		configuration (spec § 4).

		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je saisis dans la fiche du sonore :
			| champ              | valeur |
			| Crossfade de début |        |
			| Crossfade de fin   | 0      |
		Alors la fiche du sonore montre :
			| champ              | valeur |
			| Crossfade de début |        |
			| Crossfade de fin   | 0,0 s  |
		Et le champ du crossfade de début de la fiche du sonore est inactif, celui de fin actif
		Quand j'enregistre la fiche
		Alors le sonore « Café à minuit » a en base :
			| champ           | valeur  |
			| crossfade_debut | None    |
			| crossfade_fin   | 0:00:00 |
		Et les champs saisis à la main de « Café à minuit » sont « titre », « crossfade_debut », « crossfade_fin »

	# ─── Détection de blanc (https://github.com/dascritch/machincast/issues/146) ───

	Scénario: La détection de blanc et les blancs détectés se règlent dans la fiche, et sont marqués
		La détection de blanc d'un sonore n'est pas activée par défaut. Un blanc décoché n'est pas détecté (NULL) : ce côté
		du sonore n'est pas rogné. La fin détectée se compte depuis la fin du fichier.

		Étant donné le sonore « Café à minuit » a en base :
			| champ         | valeur |
			| debut_detecte | 0.5 s  |
			| fin_detectee  | 1.25 s |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors la fiche du sonore montre :
			| champ              | valeur |
			| Détection de blanc | non    |
			| Début détecté      | 0,50 s |
			| Fin détectée       | 1,25 s |
		Quand je saisis dans la fiche du sonore :
			| champ              | valeur |
			| Détection de blanc | oui    |
			| Début détecté      | 0,3    |
			| Fin détectée       |        |
		Et j'enregistre la fiche
		Alors le sonore « Café à minuit » a en base :
			| champ            | valeur         |
			| detection_blancs | True           |
			| debut_detecte    | 0:00:00.300000 |
			| fin_detectee     | None           |
		Et les champs saisis à la main de « Café à minuit » sont « titre », « detection_blancs », « debut_detecte », « fin_detectee »

	Scénario: Des blancs qui couvrent toute la durée du sonore ne sont pas enregistrés
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je saisis dans la fiche du sonore :
			| champ         | valeur |
			| Début détecté | 200    |
			| Fin détectée  | 14     |
		Et j'enregistre la fiche
		Alors la fiche signale « Les blancs détectés doivent laisser du son : ensemble, plus courts que la durée du sonore. »
		Et le sonore « Café à minuit » a en base :
			| champ         | valeur |
			| debut_detecte | None   |
			| fin_detectee  | None   |

	Scénario: Un crossfade plus long que la durée maximale des préférences reste tel quel
		https://github.com/dascritch/machincast/issues/145 : 5 secondes au plus, par défaut.

		Étant donné le sonore « Café à minuit » a en base :
			| champ         | valeur |
			| crossfade_fin | 8 s    |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors la fiche du sonore montre :
			| champ            | valeur |
			| Crossfade de fin | 8,0 s  |
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs

	Scénario: Sans maximum de lectures ni période, le sonore n'a pas de limite
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je saisis dans la fiche du sonore :
			| champ                 | valeur |
			| Maximum de lectures   | 0      |
			| Diffusion à partir du |        |
		Alors la fiche du sonore montre :
			| champ                 | valeur   |
			| Maximum de lectures   | illimité |
			| Diffusion à partir du |          |
		Quand j'enregistre la fiche
		Alors le sonore « Café à minuit » a en base :
			| champ           | valeur |
			| max_lectures    | None   |
			| debut_diffusion | None   |

	Scénario: Une période cochée part de l'heure de l'horloge, à la minute
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je coche « Diffusion jusqu'au » dans la fiche du sonore
		Alors la fiche du sonore montre :
			| champ              | valeur           |
			| Diffusion jusqu'au | 16/10/2026 20:00 |
		Et les dates de diffusion qui se saisissent sont « Diffusion à partir du », « Diffusion jusqu'au »
		Quand j'enregistre la fiche
		Alors le sonore « Café à minuit » a en base :
			| champ         | valeur                    |
			| fin_diffusion | 2026-10-16 20:00:00+02:00 |

	Plan du scénario: Une période dont la fin ne suit pas le début n'est pas enregistrée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je saisis dans la fiche du sonore :
			| champ              | valeur |
			| Diffusion jusqu'au | <fin>  |
		Et j'enregistre la fiche
		Alors la fiche signale « La fin de la diffusion doit suivre son début. »
		Et le sonore « Café à minuit » a en base :
			| champ         | valeur |
			| fin_diffusion | None   |

		Exemples:
			| fin              |
			| 01/10/2026 00:00 |
			| 30/09/2026 12:00 |

	Plan du scénario: Toute modification de la fiche d'un sonore rend « Enregistrer » et « Annuler » actifs
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je saisis dans la fiche du sonore :
			| champ   | valeur   |
			| <champ> | <valeur> |
		Alors les boutons « Enregistrer » et « Annuler » de la fiche sont actifs

		Exemples:
			| champ                 | valeur           |
			| Artiste               | Aube             |
			| Titre                 | Matin clair      |
			| Année                 | 2001             |
			| Album                 | Aube             |
			| Artiste de l'album    | Aube             |
			| Genre                 | Jazz             |
			| Compositeur           | Aube             |
			| Label                 | Thune            |
			| Piste                 | 3                |
			| Crossfade de début    | 3                |
			| Crossfade de fin      | 1                |
			| Maximum de lectures   | 5                |
			| Artiste et titre      | affichés         |
			| État                  | désactivé        |
			| Diffusion à partir du | 02/10/2026 08:00 |
			| Diffusion à partir du |                  |
			| Diffusion jusqu'au    | 31/12/2026 23:30 |

	# ─── État ──────────────────────────────────────────────────

	Plan du scénario: L'état se choisit parmi ceux que l'interface peut poser
		Étant donné le sonore « Café à minuit » a en base :
			| champ | valeur |
			| etat  | <etat> |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors l'état de la fiche du sonore se choisit parmi <choix>

		Exemples:
			| etat      | choix                                  |
			| actif     | « actif », « désactivé »               |
			| desactive | « désactivé », « actif »               |
			| expire    | « expiré », « actif », « désactivé »   |
			| errone    | « erroné », « actif », « désactivé »   |
			| non_supporte | « non supporté », « actif », « désactivé » |
			| supprime  | « supprimé », « actif », « désactivé » |
			| apercu    | « aperçu »                             |

	Scénario: L'état modifié part en base, sans être marqué : l'indexeur peut encore le changer
		Étant donné le sonore « Café à minuit » a en base :
			| champ | valeur |
			| etat  | expire |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je saisis dans la fiche du sonore :
			| champ | valeur |
			| État  | actif  |
		Et j'enregistre la fiche
		Alors le sonore « Café à minuit » a en base :
			| champ | valeur |
			| etat  | actif  |
		Et les champs saisis à la main de « Café à minuit » sont « titre »

	Scénario: L'état que la diffusion pose entre-temps n'est pas écrasé par une fiche qui ne l'a pas changé
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et la diffusion passe « Café à minuit » à l'état « expire »
		Et je saisis dans la fiche du sonore :
			| champ | valeur |
			| Genre | Jazz   |
		Et j'enregistre la fiche
		Alors le sonore « Café à minuit » a en base :
			| champ | valeur |
			| etat  | expire |

	# ─── Stream ────────────────────────────────────────────────

	Scénario: Un sonore effacé de la base pendant la modification n'est pas enregistré
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je saisis dans la fiche du sonore :
			| champ | valeur |
			| Genre | Jazz   |
		Et le sonore « Café à minuit » est effacé de la base
		Et j'enregistre la fiche
		Alors la fiche signale « Ce sonore n'est plus en base. »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs

	Scénario: Un fichier n'a pas de réglages de stream, un stream pas d'emplacement ni de durée
		Étant donné les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Direct | stream | actif |       | https://flux.exemple/direct |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors la fiche du sonore n'a pas de réglages de stream
		Quand j'ouvre la fiche du sonore « Direct »
		Alors la fiche du sonore montre :
			| champ                | valeur                      |
			| Type                 | stream                      |
			| Durée                | inconnue                    |
			| Adresse directe      | https://flux.exemple/direct |
			| Marque-page          |                             |
			| Événement de secours | aucun : le fil musical      |
		Et la fiche du sonore n'a pas d'emplacement
		Et la fiche du sonore n'a pas de détection de blanc

	Scénario: Un stream passe d'une adresse directe à un marque-page, et choisit son événement de secours
		Étant donné les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Direct | stream | actif |       | https://flux.exemple/direct |
		Et les marques-pages « Radio Machin » à « https://machin.exemple/live », « Radio Bidule » à « https://bidule.exemple/live »
		Et les événements :
			| nom          | nom_public | priorite    | debut | fin | jours |
			| Continue     |            | fil_musical |       |     |       |
			| Secours nuit |            | secours     |       |     |       |
			| Secours jour |            | secours     |       |     |       |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Alors les marques-pages proposés sont « Radio Bidule », « Radio Machin »
		Et les événements de secours proposés sont « aucun : le fil musical », « Secours jour », « Secours nuit »
		Quand je saisis dans la fiche du sonore :
			| champ                | valeur       |
			| Marque-page          | Radio Machin |
			| Événement de secours | Secours nuit |
		Et j'enregistre la fiche
		Alors le stream « Direct » est en base, sur le marque-page « Radio Machin », sans adresse directe, secouru par « Secours nuit »
		Et les champs saisis à la main de « Direct » sont « url_stream », « marque_page_id », « secours_evenement_id »
		Quand je saisis dans la fiche du sonore :
			| champ                | valeur                       |
			| Adresse directe      | https://flux.exemple/nouveau |
			| Événement de secours | aucun : le fil musical       |
		Et j'enregistre la fiche
		Alors le stream « Direct » est en base, à l'adresse « https://flux.exemple/nouveau », sans marque-page, sans événement de secours

	Scénario: Le mode d'un stream décide du champ qui se saisit, et en changer modifie la fiche
		Étant donné les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Direct | stream | actif |       | https://flux.exemple/direct |
		Et les marques-pages « Radio Machin » à « https://machin.exemple/live »
		Et le stream « Direct » est sur le marque-page « Radio Machin »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Alors la fiche du sonore montre :
			| champ           | valeur       |
			| Adresse directe |              |
			| Marque-page     | Radio Machin |
		Et seul le champ « Marque-page » du stream se saisit
		Quand je choisis l'adresse directe dans la fiche du sonore
		Alors seul le champ « Adresse directe » du stream se saisit
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs
		Quand j'enregistre la fiche
		Alors la fiche signale « L'adresse du stream est obligatoire. »

	Scénario: Une fiche de stream enregistrée se relit sans rien doubler
		Étant donné les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Direct | stream | actif |       | https://flux.exemple/direct |
		Et les marques-pages « Radio Machin » à « https://machin.exemple/live »
		Et les événements :
			| nom          | nom_public | priorite | debut | fin | jours |
			| Secours nuit |            | secours  |       |     |       |
		Et le sonore « Direct » est passé 2 fois, toutes les 5 minutes depuis « 2026-10-16 10:00:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Alors la fiche du sonore ne montre aucun champ saisi à la main
		Quand je saisis dans la fiche du sonore :
			| champ                | valeur       |
			| Événement de secours | Secours nuit |
		Et j'enregistre la fiche
		Alors l'état de la fiche du sonore se choisit parmi « actif », « désactivé »
		Et les marques-pages proposés sont « Radio Machin »
		Et les événements de secours proposés sont « aucun : le fil musical », « Secours nuit »
		Et la fiche du sonore montre 2 passages, du « 2026-10-16 10:05:00 » au « 2026-10-16 10:00:00 »
		Et la fiche du sonore montre les champs saisis à la main « événement de secours »
		Et la fiche du sonore montre :
			| champ                | valeur                      |
			| Adresse directe      | https://flux.exemple/direct |
			| Événement de secours | secours nuit                |
		Et seul le champ « Adresse directe » du stream se saisit

	Scénario: Sans marque-page en base, un stream ne peut pas en choisir
		Étant donné les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Direct | stream | actif |       | https://flux.exemple/direct |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Alors le choix d'un marque-page est inactif

	Scénario: Un stream sans adresse n'est pas enregistré
		Étant donné les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Direct | stream | actif |       | https://flux.exemple/direct |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Et je saisis dans la fiche du sonore :
			| champ           | valeur |
			| Adresse directe |        |
		Et j'enregistre la fiche
		Alors la fiche signale « L'adresse du stream est obligatoire. »

	# ─── Nouveau stream (https://github.com/dascritch/machincast/issues/30) ───

	Scénario: Un nouveau stream se crée depuis la liste des sonores, à l'état actif
		Étant donné les marques-pages « Radio Machin » à « https://machin.exemple/live »
		Et les événements :
			| nom          | nom_public | priorite | debut | fin | jours |
			| Secours nuit |            | secours  |       |     |       |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je clique sur « Nouveau stream »
		Alors l'onglet ouvert est « Nouveau stream »
		Et la fiche du sonore montre :
			| champ                | valeur                 |
			| Type                 | stream                 |
			| Durée                | inconnue               |
			| État                 | actif                  |
			| Adresse directe      |                        |
			| Événement de secours | aucun : le fil musical |
		Et la fiche du sonore n'a pas d'emplacement
		Et l'état de la fiche du sonore se choisit parmi « actif », « désactivé »
		Et le bouton « Supprimer… » de la fiche est inactif
		Quand je saisis dans la fiche du sonore :
			| champ                | valeur                      |
			| Titre                | Le direct                   |
			| Adresse directe      | https://flux.exemple/direct |
			| Événement de secours | Secours nuit                |
		Et j'enregistre la fiche
		Alors la fiche ne signale rien
		Et l'onglet ouvert est « Sonore : Le direct »
		Et le stream « Le direct » est en base, à l'adresse « https://flux.exemple/direct », sans marque-page, secouru par « Secours nuit »
		Et le sonore « Le direct » a en base :
			| champ | valeur |
			| type  | stream |
			| etat  | actif  |
		Et le bouton « Supprimer… » de la fiche est actif

	Scénario: Un nouveau stream peut suivre un marque-page, et n'a pas besoin de titre
		Étant donné les marques-pages « Radio Machin » à « https://machin.exemple/live »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je clique sur « Nouveau stream »
		Et je saisis dans la fiche du sonore :
			| champ       | valeur       |
			| Marque-page | Radio Machin |
		Et j'enregistre la fiche
		Alors l'onglet ouvert est « Sonore : https://machin.exemple/live »
		Et le stream « https://machin.exemple/live » est en base, sur le marque-page « Radio Machin », sans adresse directe, sans événement de secours

	Scénario: Un nouveau stream sans adresse n'est pas enregistré
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je clique sur « Nouveau stream »
		Et je saisis dans la fiche du sonore :
			| champ | valeur    |
			| Titre | Le direct |
		Et j'enregistre la fiche
		Alors la fiche signale « L'adresse du stream est obligatoire. »
		Et l'onglet ouvert est « Nouveau stream »

	Plan du scénario: Le test d'un flux dit s'il répond, sans attendre son enregistrement
		Étant donné un serveur de flux local, avec le flux « direct » en ligne
		Et les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Direct | stream | actif |       | https://flux.exemple/direct |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Et je saisis l'adresse du flux « <flux> » du serveur local dans la fiche du sonore
		Et je teste le flux
		Alors le test du flux est en cours
		Et le test du flux dit bientôt <verdict>
		Et le flux peut de nouveau être testé
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs

		Exemples:
			| flux   | verdict                                       |
			| direct | « Le flux répond : du son arrive. »           |
			| muet   | qu'il ne répond pas, avec l'erreur du serveur |

	Scénario: Une adresse qui n'en est pas une n'est pas testée
		Étant donné les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Direct | stream | actif |       | https://flux.exemple/direct |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Et je saisis dans la fiche du sonore :
			| champ           | valeur          |
			| Adresse directe | pas une adresse |
		Et je teste le flux
		Alors le test du flux dit « Le flux ne répond pas : « pas une adresse » n'est pas une adresse. »
		Et le flux peut de nouveau être testé

	Scénario: Un second test repart de zéro, et le test terminé ferme sa connexion
		Étant donné un serveur de flux local, avec le flux « direct » en ligne
		Et les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Direct | stream | actif |       | https://flux.exemple/direct |
		Et un test de flux limité à 1 seconde
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Et je saisis l'adresse du flux « direct » du serveur local dans la fiche du sonore
		Et je teste le flux
		Alors le test du flux dit bientôt « Le flux répond : du son arrive. »
		Et le serveur de flux local n'a bientôt plus de connexion
		Et après 2 secondes, le test du flux dit toujours « Le flux répond : du son arrive. »
		Quand le flux « avare » du serveur local est avare
		Et je saisis l'adresse du flux « avare » du serveur local dans la fiche du sonore
		Et je teste le flux
		Alors le test du flux dit bientôt « Le flux ne répond pas : le son n'arrive pas en 1 s. »
		Et le serveur de flux local n'a bientôt plus de connexion

	Plan du scénario: Fermer la fiche, ou la fenêtre, arrête le test en cours
		Étant donné un serveur de flux local, avec le flux « avare » en ligne
		Et les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Direct | stream | actif |       | https://flux.exemple/direct |
		Quand le flux « avare » du serveur local est avare
		Et la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Et je saisis l'adresse du flux « avare » du serveur local dans la fiche du sonore
		Et je teste le flux
		Et le serveur de flux local a bientôt 1 connexion
		Et je réponds « Abandonner » à la question de fermeture
		Et je ferme <quoi>
		Alors le serveur de flux local n'a bientôt plus de connexion

		Exemples:
			| quoi                            |
			| l'onglet « Sonore : Direct »    |
			| la fenêtre de l'interface       |

	Scénario: Le test d'un flux sur marque-page prend l'adresse du marque-page
		Étant donné un serveur de flux local, avec le flux « direct » en ligne
		Et les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Direct | stream | actif |       | https://flux.exemple/direct |
		Et le marque-page « Local » à l'adresse du flux « direct » du serveur local
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Et je saisis dans la fiche du sonore :
			| champ       | valeur |
			| Marque-page | Local  |
		Et je teste le flux
		Alors le test du flux dit bientôt « Le flux répond : du son arrive. »

	Scénario: Un test sans réponse s'arrête de lui-même
		Étant donné un serveur qui accepte les connexions sans jamais répondre
		Et les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Direct | stream | actif |       | https://flux.exemple/direct |
		Et un test de flux limité à 1 seconde
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Et je saisis l'adresse du serveur muet dans la fiche du sonore
		Et je teste le flux
		Alors le test du flux dit bientôt « Le flux ne répond pas : le son n'arrive pas en 1 s. »

	# ─── Derniers passages ─────────────────────────────────────

	Scénario: Les derniers passages du sonore, avec leurs incidents
		Étant donné les sonores :
			| artiste | titre | type    | etat  | duree | emplacement        |
			|         | Autre | fichier | actif | 60    | /srv/pubs/autre.mp3 |
		Et les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Et la banque « Jingles », séquentielle, sans nom public, avec « Café à minuit »
		Et les passages de sonores :
			| sonore        | debut               | fin                 | evenement | sequence | banque  | sans_incident |
			| Café à minuit | 2026-10-15 09:00:00 | 2026-10-15 09:03:34 | Continue  |          | Jingles | oui           |
			| Autre         | 2026-10-15 10:00:00 | 2026-10-15 10:01:00 | Continue  |          |         | oui           |
			| Café à minuit | 2026-10-16 19:00:00 | 2026-10-16 19:02:00 | Continue  |          | Jingles | non           |
			| Café à minuit | 2026-10-16 20:00:00 |                     | Continue  |          |         |               |
		Et le log :
			| sonore        | horodatage          | niveau   | nature             | message           |
			| Café à minuit | 2026-10-16 19:01:00 | incident | coupure            | décodeur perdu    |
			| Café à minuit | 2026-10-16 19:01:30 | alerte   | reprise            | après 30 s        |
			| Café à minuit | 2026-10-16 19:01:40 | info     | volume             | normal            |
			| Autre         | 2026-10-16 19:01:10 | incident | coupure autre      | autre sonore      |
			| Café à minuit | 2026-10-15 12:00:00 | incident | fichier introuvable | hors de tout passage |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors les derniers passages du sonore sont :
			| Début               | Fin      | Durée | Événement | Séquence | Banque  | Incidents        |
			| 2026-10-16 20:00:00 | en cours |       | Continue  |          |         |                  |
			| 2026-10-16 19:00:00 | 19:02:00 | 2:00  | Continue  |          | Jingles | coupure, reprise |
			| 2026-10-15 09:00:00 | 09:03:34 | 3:34  | Continue  |          | Jingles |                  |
		Et l'infobulle des incidents du passage de « 2026-10-16 19:00:00 » est « 19:01:00 coupure : décodeur perdu⏎19:01:30 reprise : après 30 s »

	Scénario: Seuls les 50 derniers passages sont montrés
		Étant donné le sonore « Café à minuit » est passé 55 fois, toutes les 5 minutes depuis « 2026-10-16 10:00:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors la fiche du sonore montre 50 passages, du « 2026-10-16 14:30:00 » au « 2026-10-16 10:25:00 »

	# ─── Améliorations (https://github.com/dascritch/machincast/issues/125) ─────

	Scénario: Le bouton du dossier ouvre le dossier du fichier dans le navigateur de fichiers
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur le bouton du dossier du fichier
		Alors le navigateur de fichiers a ouvert « /srv/jingles/hiver »

	Scénario: Les relations montrent les séquences, banques et événements qui citent le sonore, et s'ouvrent
		Étant donné les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Et la banque « Jingles », séquentielle, sans nom public, avec « Café à minuit »
		Et la banque « Tubes », aléatoire, sans nom public, avec aucun
		Et la séquence « Passage pub », sans nom public, avec le sonore « Café à minuit », la banque « Tubes »
		Et la séquence « Autre passage », sans nom public, avec la banque « Tubes »
		Et l'événement « Continue » joue le sonore « Café à minuit », le sonore « Café à minuit »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors les relations du sonore sont :
			| Genre     | Nom         |
			| séquence  | Passage pub |
			| banque    | Jingles     |
			| événement | Continue    |
		Et la fiche du sonore ne dit pas qu'aucun élément ne le cite
		Quand j'ouvre la relation « Passage pub » du sonore
		Alors l'onglet ouvert est « Séquence : Passage pub »

	Scénario: Les banques dont le sonore sort des durées sont marquées parmi ses relations
		https://github.com/dascritch/machincast/issues/147

		Étant donné la banque « Jingles », séquentielle, sans nom public, avec « Café à minuit »
		Et la banque « Tubes », aléatoire, sans nom public, avec « Café à minuit »
		Et la banque « Pubs », aléatoire, sans nom public, avec « Café à minuit »
		Et la banque « Jingles » veut des sonores d'au plus 1:00
		Et la banque « Tubes » veut des sonores de 2:00 à 6:00
		Et la banque « Pubs » veut des sonores d'au moins 5:00
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors la fiche du sonore marque hors des durées les banques :
			| banque  | infobulle                                                       |
			| Jingles | 3:34 : plus long que le maximum de la banque « Jingles », 1:00. |
			| Pubs    | 3:34 : plus court que le minimum de la banque « Pubs », 5:00.   |

	Scénario: Un sonore cité nulle part le dit
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors les relations du sonore sont :
			| Genre | Nom |
		Et la fiche du sonore dit « Aucune séquence, banque ni événement ne cite ce sonore. »

	# La taille et les dates viennent du fichier lui-même, qui n'est que lu ; sa création, telle que la donne stat.
	Plan du scénario: L'encart « Fichier » donne le type, l'encodage moyen, la taille et les dates du fichier
		Étant donné le fichier « …/emissions/matin.flac », de <octets> octets, modifié le « 2026-10-14 07:30:00 »
		Et les sonores :
			| artiste | titre | type    | etat  | duree | emplacement            |
			|         | Matin | fichier | actif | 100   | …/emissions/matin.flac |
		Et le sonore « Matin » a en base :
			| champ          | valeur              |
			| type_mime      | audio/flac          |
			| verifie_le     | 2026-10-15 08:15:00 |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Matin »
		Alors l'encart « Fichier » de la fiche du sonore montre :
			| champ                          | valeur              |
			| Type                           | audio/flac          |
			| Encodage moyen                 | <encodage>          |
			| Taille                         | <taille>            |
			| Créé le                        | <création du fichier> |
			| Modifié le                     | 2026-10-14 07:30:00 |
			| Dernière vérification complète | 2026-10-15 08:15:00 |

		Exemples:
			| octets  | encodage    | taille |
			| 1234567 | ≈ 99 kbit/s | 1,2 Mo |
			| 512     | ≈ 0 kbit/s  | 512 o  |

	Scénario: Sur un système de fichiers qui ne garde pas la date de création, elle est inconnue
		Étant donné le fichier « …/emissions/matin.flac », de 512 octets, modifié le « 2026-10-14 07:30:00 »
		Et les sonores :
			| artiste | titre | type    | etat  | duree | emplacement            |
			|         | Matin | fichier | actif | 100   | …/emissions/matin.flac |
		Et un système de fichiers qui ne garde pas la date de création
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Matin »
		Alors l'encart « Fichier » de la fiche du sonore montre :
			| champ   | valeur   |
			| Créé le | inconnue |

	Scénario: Un fichier jamais vérifié, ou disparu, le dit dans l'encart « Fichier »
		Étant donné les sonores :
			| artiste | titre   | type    | etat   | duree | emplacement        |
			|         | Disparu | fichier | apercu |       | …/disparu.flac     |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Disparu »
		Alors l'encart « Fichier » de la fiche du sonore montre :
			| champ                          | valeur      |
			| Type                           | inconnu     |
			| Encodage moyen                 | inconnu     |
			| Taille                         | introuvable |
			| Créé le                        | introuvable |
			| Modifié le                     | introuvable |
			| Dernière vérification complète | jamais      |

	Scénario: Un stream n'a ni encart « Fichier », ni bouton du dossier
		Étant donné les sonores :
			| artiste | titre       | type   | etat  | duree | emplacement             |
			|         | Machin soir | stream | actif |       | https://flux.exemple/a  |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Machin soir »
		Alors la fiche du sonore n'a ni encart « Fichier », ni bouton du dossier

