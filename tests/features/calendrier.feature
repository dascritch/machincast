# language: fr
Fonctionnalité: Calendrier de la grille
	En tant que programmateur de l'antenne,
	je veux un calendrier qui montre à la fois ce qui est prévu et ce qui a été diffusé,
	afin de visualiser la grille et son exécution réelle, et d'ajuster les événements spéciaux.

	https://github.com/dascritch/machincast/issues/36 et https://github.com/dascritch/machincast/issues/118, spec § 8.2.
	Le calendrier s'ouvre dans son onglet, depuis le menu « Affichage », sur la semaine du jour : du lundi au dimanche,
	de 0 h à 24 h. Il se pagine par semaine, ou par jour en vue jour, jusqu'à 28 jours après aujourd'hui, et pas avant
	la durée de péremption (https://github.com/dascritch/machincast/issues/269) : Machin purge efface de la base ce qui
	est plus vieux (https://github.com/dascritch/machincast/issues/268). En vue semaine, les jours d'avant sont grisés,
	vides. Un événement supprimé (https://github.com/dascritch/machincast/issues/267) garde ses occurrences d'avant sa
	suppression, jusqu'à leur péremption.

	Chaque occurrence d'un événement prévu est un bloc ; deux blocs qui se chevauchent se placent côte à côte. Un bloc
	« joue » quand son événement serait à l'antenne pendant toute l'occurrence (machincast.lecture.grille) ; il est
	« estompé » quand un autre événement le masque entièrement, et ne « joue qu'en partie » entre les deux. Une
	occurrence de 24 heures ou plus, ou un fil musical permanent, se montre dans la bande de la journée entière, entre
	le nom du jour et les heures. Une occurrence sans fin se dessine jusqu'au début suivant d'une priorité égale ou plus
	haute, au plus tard jusqu'à minuit ; ce qui joue se calcule avec cette fin. L'airplay du passé se superpose en bandes étroites, à droite de chaque jour :
	les passages successifs d'un même événement n'en font qu'une ; un passage interrompu, sans fin, dure jusqu'au
	suivant. Une case par priorité montre ou cache ses blocs et ses
	bandes d'airplay, sans changer ce qui joue.

	Les jours se nomment « mardi 20 » ; les heures, « 16:30 ». « 24:00 » est la fin du jour.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-20 16:40:00 »
		Et les événements :
			| nom      | nom_public | priorite    | debut            | fin              | jours                                    |
			| Week-end |            | fil_musical | 2026-10-24 10:00 | 2026-10-24 18:00 |                                          |
			| Continue |            | fil_musical |                  |                  |                                          |
			| Matinale | Le réveil  | emission    | 2026-10-05 07:00 | 2026-10-05 09:00 | lundi, mardi, mercredi, jeudi, vendredi  |
			| Concert  |            | special     | 2026-10-21 08:00 | 2026-10-21 10:00 |                                          |
			| Nuit     |            | emission    | 2026-10-18 23:00 | 2026-10-19 01:00 | dimanche                                 |
			| Festival |            | special     | 2026-10-23 00:00 | 2026-10-24 00:00 |                                          |
			| Direct   |            | emission    | 2026-10-22 14:00 |                  |                                          |
			| Soirée   |            | emission    | 2026-10-22 20:00 | 2026-10-22 21:00 |                                          |
			| Midi     |            | emission    | 2026-10-21 12:00 | 2026-10-21 13:00 |                                          |
			| Flash    |            | special     | 2026-10-24 12:00 | 2026-10-24 13:00 |                                          |
			| Rediff   |            | emission    | 2026-10-24 17:30 | 2026-10-24 19:00 |                                          |

	# ─── Ouverture ─────────────────────────────────────────────

	Scénario: Le calendrier s'ouvre depuis le menu « Affichage », dans son onglet, sur la semaine du jour
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors l'onglet ouvert est « Calendrier »
		Et le calendrier montre « Semaine du lundi 19 au dimanche 25 octobre 2026 »
		Et le calendrier a les jours « lundi 19 », « mardi 20 », « mercredi 21 », « jeudi 22 », « vendredi 23 », « samedi 24 », « dimanche 25 »

	Scénario: Le calendrier n'a qu'un onglet, qui se ferme
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et j'ouvre l'onglet « Accueil »
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents », « Calendrier »
		Et l'onglet ouvert est « Calendrier »
		Et seul l'onglet « Calendrier » a un bouton de fermeture
		Quand je ferme l'onglet « Calendrier »
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents »

	# ─── Prévu ─────────────────────────────────────────────────

	Scénario: Les occurrences prévues de la semaine, récurrences comprises, et ce qui en joue
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors le calendrier montre les blocs :
			| jour        | début | fin   | événement | état           |
			| lundi 19    | 00:00 | 01:00 | Nuit      | joue           |
			| lundi 19    | 07:00 | 09:00 | Matinale  | joue           |
			| mardi 20    | 07:00 | 09:00 | Matinale  | joue           |
			| mercredi 21 | 07:00 | 09:00 | Matinale  | joue en partie |
			| mercredi 21 | 08:00 | 10:00 | Concert   | joue           |
			| mercredi 21 | 12:00 | 13:00 | Midi      | joue           |
			| jeudi 22    | 07:00 | 09:00 | Matinale  | joue           |
			| jeudi 22    | 14:00 | 20:00 | Direct    | joue           |
			| jeudi 22    | 20:00 | 21:00 | Soirée    | joue           |
			| vendredi 23 | 07:00 | 09:00 | Matinale  | estompé        |
			| samedi 24   | 10:00 | 18:00 | Week-end  | joue en partie |
			| samedi 24   | 12:00 | 13:00 | Flash     | joue           |
			| samedi 24   | 17:30 | 19:00 | Rediff    | joue           |
			| dimanche 25 | 23:00 | 24:00 | Nuit      | joue           |
		Et la bande de la journée entière montre :
			| jour        | événement | état           |
			| lundi 19    | Continue  | joue en partie |
			| mardi 20    | Continue  | joue en partie |
			| mercredi 21 | Continue  | joue en partie |
			| jeudi 22    | Continue  | joue en partie |
			| vendredi 23 | Continue  | estompé        |
			| vendredi 23 | Festival  | joue           |
			| samedi 24   | Continue  | joue en partie |
			| dimanche 25 | Continue  | joue en partie |

	Scénario: Des blocs qui se chevauchent sont côte à côte, chacun à la première place libre
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors les blocs « Matinale » et « Concert » du mercredi 21 sont côte à côte
		Et le bloc « Midi » du mercredi 21 a toute la largeur des blocs prévus
		Et les blocs « Week-end » et « Flash » du samedi 24 sont côte à côte
		Et les blocs « Week-end » et « Rediff » du samedi 24 sont côte à côte
		Et le bloc « Rediff » du samedi 24 est à la place du bloc « Flash »

	Scénario: Survoler un bloc dit l'événement, ses heures, sa récurrence et ce qui en joue
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors le bloc « Matinale » du mercredi 21 a l'infobulle :
			"""
			Matinale (Le réveil) — Émission
			mercredi 21 octobre, 07:00 – 09:00
			Revient le lundi, mardi, mercredi, jeudi, vendredi
			Joue de 07:00 à 08:00 ; masqué le reste du temps par un autre événement
			Double-clic : ouvrir l'événement
			"""
		Et le bloc « Direct » du jeudi 22 a l'infobulle :
			"""
			Direct — Émission
			jeudi 22 octobre, à partir de 14:00, sans fin : jusqu'à l'épuisement de sa liste
			Joue en entier
			Double-clic : ouvrir l'événement
			"""
		Et le bloc « Continue » de la journée du lundi 19 a l'infobulle :
			"""
			Continue — Fil musical
			Fil musical permanent
			Joue de 01:00 à 07:00 et de 09:00 à 24:00 ; masqué le reste du temps par un autre événement
			Double-clic : ouvrir l'événement
			"""
		Et le bloc « Continue » de la journée du vendredi 23 a l'infobulle :
			"""
			Continue — Fil musical
			Fil musical permanent
			Masqué en entier par un autre événement
			Double-clic : ouvrir l'événement
			"""

	# ─── Diffusé ───────────────────────────────────────────────

	Scénario: L'airplay du passé se superpose, un événement joué à la suite n'en faisant qu'une bande
		Étant donné les passages de l'airplay :
			| événement | début               | fin                 |
			| Matinale  | 2026-10-20 07:00:00 | 2026-10-20 07:03:30 |
			| Matinale  | 2026-10-20 07:03:30 | 2026-10-20 07:58:10 |
			| Continue  | 2026-10-20 07:58:10 |                     |
			| Matinale  | 2026-10-20 08:02:00 | 2026-10-20 09:00:00 |
			| (supprimé)| 2026-10-20 16:00:00 | 2026-10-20 16:20:00 |
			| Continue  | 2026-10-20 16:20:00 |                     |
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors le calendrier montre les bandes d'airplay :
			| jour     | début | fin   | événement          | passages |
			| mardi 20 | 07:00 | 07:58 | Matinale           | 2        |
			| mardi 20 | 07:58 | 08:02 | Continue           | 1        |
			| mardi 20 | 08:02 | 09:00 | Matinale           | 1        |
			| mardi 20 | 16:00 | 16:20 | Événement supprimé | 1        |
			| mardi 20 | 16:20 | 16:40 | Continue           | 1        |
		Et la bande d'airplay « Matinale » de 07:00 du mardi 20 a l'infobulle :
			"""
			Diffusé : Matinale
			mardi 20 octobre, 07:00:00 – 07:58:10
			2 passages
			Double-clic : ouvrir l'événement
			"""
		Et la bande d'airplay « Événement supprimé » de 16:00 du mardi 20 a l'infobulle :
			"""
			Diffusé : Événement supprimé
			mardi 20 octobre, 16:00:00 – 16:20:00
			1 passage
			"""
		Et la bande d'airplay « Continue » de 16:20 du mardi 20 a l'infobulle :
			"""
			Diffusé : Continue
			mardi 20 octobre, depuis 16:20:00, en cours
			1 passage
			Double-clic : ouvrir l'événement
			"""

	# ─── Priorités ─────────────────────────────────────────────

	Scénario: Une case par priorité montre ou cache ses blocs et son airplay, sans changer ce qui joue
		Étant donné les passages de l'airplay :
			| événement | début               | fin                 |
			| Matinale  | 2026-10-20 07:00:00 | 2026-10-20 09:00:00 |
			| Continue  | 2026-10-20 09:00:00 | 2026-10-20 09:03:00 |
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors le calendrier a les cases cochées « Spécial », « Émission », « Fil musical »
		Quand je décoche la case « Émission » du calendrier
		Alors le calendrier montre les blocs :
			| jour        | début | fin   | événement | état           |
			| mercredi 21 | 08:00 | 10:00 | Concert   | joue           |
			| samedi 24   | 10:00 | 18:00 | Week-end  | joue en partie |
			| samedi 24   | 12:00 | 13:00 | Flash     | joue           |
		Et la bande de la journée entière montre :
			| jour        | événement | état           |
			| lundi 19    | Continue  | joue en partie |
			| mardi 20    | Continue  | joue en partie |
			| mercredi 21 | Continue  | joue en partie |
			| jeudi 22    | Continue  | joue en partie |
			| vendredi 23 | Continue  | estompé        |
			| vendredi 23 | Festival  | joue           |
			| samedi 24   | Continue  | joue en partie |
			| dimanche 25 | Continue  | joue en partie |
		Et le calendrier montre les bandes d'airplay :
			| jour     | début | fin   | événement | passages |
			| mardi 20 | 09:00 | 09:03 | Continue  | 1        |
		Quand je décoche la case « Fil musical » du calendrier
		Et je décoche la case « Spécial » du calendrier
		Alors le calendrier ne montre aucun bloc
		Quand je coche la case « Émission » du calendrier
		Alors le calendrier montre 11 blocs

	# ─── Navigation ────────────────────────────────────────────

	Scénario: Le calendrier se pagine par semaine, jusqu'à 28 jours après aujourd'hui, et jusqu'à la péremption avant
		Étant donné la durée de péremption du fichier de configuration de l'interface est de 28 jours
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique 4 fois sur « Semaine suivante » du calendrier
		Alors le calendrier montre « Semaine du lundi 16 au dimanche 22 novembre 2026 »
		Et le bouton « Semaine suivante » du calendrier est inactif
		Quand je clique sur « Aujourd'hui » du calendrier
		Et je clique 4 fois sur « Semaine précédente » du calendrier
		Alors le calendrier montre « Semaine du lundi 21 au dimanche 27 septembre 2026 »
		Et le bouton « Semaine précédente » du calendrier est inactif
		Quand je clique sur « Aujourd'hui » du calendrier
		Alors le calendrier montre « Semaine du lundi 19 au dimanche 25 octobre 2026 »

	Scénario: La vue jour montre un seul jour, et se pagine par jour
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique sur « Jour » du calendrier
		Alors le calendrier montre « mardi 20 octobre 2026 »
		Et le calendrier a les jours « mardi 20 »
		Quand je clique sur « Jour suivant » du calendrier
		Alors le calendrier montre « mercredi 21 octobre 2026 »
		Et le calendrier montre les blocs :
			| jour        | début | fin   | événement | état           |
			| mercredi 21 | 07:00 | 09:00 | Matinale  | joue en partie |
			| mercredi 21 | 08:00 | 10:00 | Concert   | joue           |
			| mercredi 21 | 12:00 | 13:00 | Midi      | joue           |
		Quand je clique sur « Semaine » du calendrier
		Alors le calendrier montre « Semaine du lundi 19 au dimanche 25 octobre 2026 »

	Scénario: La vue jour va aussi de la péremption à 28 jours après aujourd'hui
		Étant donné la durée de péremption du fichier de configuration de l'interface est de 28 jours
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique sur « Jour » du calendrier
		Et je clique 28 fois sur « Jour suivant » du calendrier
		Alors le calendrier montre « mardi 17 novembre 2026 »
		Et le bouton « Jour suivant » du calendrier est inactif
		Quand je clique 56 fois sur « Jour précédent » du calendrier
		Alors le calendrier montre « mardi 22 septembre 2026 »
		Et le bouton « Jour précédent » du calendrier est inactif

	Scénario: Le calendrier ne remonte pas avant la péremption, 60 jours par défaut, et grise les jours d'avant
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique 9 fois sur « Semaine précédente » du calendrier
		Alors le calendrier montre « Semaine du lundi 17 au dimanche 23 août 2026 »
		Et le bouton « Semaine précédente » du calendrier est inactif
		Et le calendrier grise les jours « lundi 17 », « mardi 18 », « mercredi 19 », « jeudi 20 »

	Scénario: Un jour grisé ne montre ni ce qui était prévu, ni ce qui a été diffusé
		Étant donné les passages de l'airplay :
			| événement | début               | fin                 |
			| Continue  | 2026-08-20 10:00:00 | 2026-08-20 11:00:00 |
			| Continue  | 2026-08-21 10:00:00 | 2026-08-21 11:00:00 |
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique 9 fois sur « Semaine précédente » du calendrier
		Alors la bande de la journée entière montre :
			| jour        | événement | état |
			| vendredi 21 | Continue  | joue |
			| samedi 22   | Continue  | joue |
			| dimanche 23 | Continue  | joue |
		Et le calendrier montre les bandes d'airplay :
			| jour        | début | fin   | événement | passages |
			| vendredi 21 | 10:00 | 11:00 | Continue  | 1        |

	Scénario: La vue jour ne remonte pas avant la péremption, que les préférences changent
		Étant donné la durée de péremption du fichier de configuration de l'interface est de 30 jours
		Et les préférences seront réglées avec la durée de péremption de 10 jours
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique sur « Jour » du calendrier
		Et je clique 30 fois sur « Jour précédent » du calendrier
		Alors le calendrier montre « dimanche 20 septembre 2026 »
		Et le bouton « Jour précédent » du calendrier est inactif
		Quand je choisis « Préférences… » dans le menu « Fichier »
		Et j'appuie sur « F5 »
		Alors le calendrier montre « samedi 10 octobre 2026 »
		Et le bouton « Jour précédent » du calendrier est inactif

	Scénario: Un événement supprimé garde ses occurrences d'avant sa suppression, et l'infobulle le dit
		Étant donné l'événement « Matinale » supprimé le « 2026-10-20 08:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors le calendrier montre les blocs :
			| jour        | début | fin   | événement | état           |
			| lundi 19    | 00:00 | 01:00 | Nuit      | joue           |
			| lundi 19    | 07:00 | 09:00 | Matinale  | joue           |
			| mardi 20    | 07:00 | 08:00 | Matinale  | joue           |
			| mercredi 21 | 08:00 | 10:00 | Concert   | joue           |
			| mercredi 21 | 12:00 | 13:00 | Midi      | joue           |
			| jeudi 22    | 14:00 | 20:00 | Direct    | joue           |
			| jeudi 22    | 20:00 | 21:00 | Soirée    | joue           |
			| samedi 24   | 10:00 | 18:00 | Week-end  | joue en partie |
			| samedi 24   | 12:00 | 13:00 | Flash     | joue           |
			| samedi 24   | 17:30 | 19:00 | Rediff    | joue           |
			| dimanche 25 | 23:00 | 24:00 | Nuit      | joue           |
		Et le bloc « Continue » de la journée du mardi 20 a l'infobulle :
			"""
			Continue — Fil musical
			Fil musical permanent
			Joue de 00:00 à 07:00 et de 08:00 à 24:00 ; masqué le reste du temps par un autre événement
			Double-clic : ouvrir l'événement
			"""
		Et le bloc « Matinale » du mardi 20 a l'infobulle :
			"""
			Matinale (Le réveil) — Émission
			mardi 20 octobre, 07:00 – 09:00
			Revient le lundi, mardi, mercredi, jeudi, vendredi
			Supprimé le mardi 20 octobre à 08:00 : la suite n'est plus prévue
			Joue en entier
			Double-clic : ouvrir l'événement
			"""

	Scénario: Une occurrence d'un événement supprimé, prévue après sa suppression, n'arrête plus une émission sans fin
		Étant donné l'événement « Soirée » supprimé le « 2026-10-20 08:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors le bloc « Direct » du jeudi 22 a l'infobulle :
			"""
			Direct — Émission
			jeudi 22 octobre, à partir de 14:00, sans fin : jusqu'à l'épuisement de sa liste
			Joue en entier
			Double-clic : ouvrir l'événement
			"""
		Et le calendrier montre les blocs :
			| jour        | début | fin   | événement | état           |
			| lundi 19    | 00:00 | 01:00 | Nuit      | joue           |
			| lundi 19    | 07:00 | 09:00 | Matinale  | joue           |
			| mardi 20    | 07:00 | 09:00 | Matinale  | joue           |
			| mercredi 21 | 07:00 | 09:00 | Matinale  | joue en partie |
			| mercredi 21 | 08:00 | 10:00 | Concert   | joue           |
			| mercredi 21 | 12:00 | 13:00 | Midi      | joue           |
			| jeudi 22    | 07:00 | 09:00 | Matinale  | joue           |
			| jeudi 22    | 14:00 | 24:00 | Direct    | joue           |
			| vendredi 23 | 07:00 | 09:00 | Matinale  | estompé        |
			| samedi 24   | 10:00 | 18:00 | Week-end  | joue en partie |
			| samedi 24   | 12:00 | 13:00 | Flash     | joue           |
			| samedi 24   | 17:30 | 19:00 | Rediff    | joue           |
			| dimanche 25 | 23:00 | 24:00 | Nuit      | joue           |

	Scénario: Une semaine à cheval sur deux années les nomme toutes les deux
		Étant donné l'horloge de l'interface au « 2026-12-30 10:00:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors le calendrier montre « Semaine du lundi 28 décembre 2026 au dimanche 3 janvier 2027 »
		Et le calendrier a les jours « lundi 28 », « mardi 29 », « mercredi 30 », « jeudi 31 », « vendredi 1er », « samedi 2 », « dimanche 3 »

	Scénario: Une semaine à cheval sur deux mois les nomme tous les deux
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique 2 fois sur « Semaine suivante » du calendrier
		Alors le calendrier montre « Semaine du lundi 2 au dimanche 8 novembre 2026 »
		Quand je clique sur « Semaine précédente » du calendrier
		Alors le calendrier montre « Semaine du lundi 26 octobre au dimanche 1er novembre 2026 »

	Scénario: Le calendrier se relit à l'ouverture de son onglet et par « Rafraîchir les onglets »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et l'événement « Matinale » est effacé de la base
		Et j'appuie sur « F5 »
		Alors le calendrier montre les blocs :
			| jour        | début | fin   | événement | état           |
			| lundi 19    | 00:00 | 01:00 | Nuit      | joue           |
			| mercredi 21 | 08:00 | 10:00 | Concert   | joue           |
			| mercredi 21 | 12:00 | 13:00 | Midi      | joue           |
			| jeudi 22    | 14:00 | 20:00 | Direct    | joue           |
			| jeudi 22    | 20:00 | 21:00 | Soirée    | joue           |
			| samedi 24   | 10:00 | 18:00 | Week-end  | joue en partie |
			| samedi 24   | 12:00 | 13:00 | Flash     | joue           |
			| samedi 24   | 17:30 | 19:00 | Rediff    | joue           |
			| dimanche 25 | 23:00 | 24:00 | Nuit      | joue           |

	# ─── Sessions sautées (https://github.com/dascritch/machincast/issues/273) ───
	# Une session à venir d'un événement récurrent se saute au clic droit sur son bloc, seule ou jusqu'à un jour choisi ;
	# sautée, elle reste dessinée, hachurée, et se rétablit au clic droit. Le créneau revient à ce qui joue sans elle :
	# on y crée l'émission de remplacement d'un clic, comme sur une heure libre. Machin lecture est prévenu aussitôt.

	Scénario: Le clic droit propose de sauter une session à venir d'un événement récurrent, et rien d'autre
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors le clic droit sur le bloc « Matinale » du mercredi 21 propose « Sauter cette session », « Sauter les sessions jusqu'au… »
		Et le clic droit sur le bloc « Matinale » du mardi 20 ne propose rien
		Et le clic droit sur le bloc « Concert » du mercredi 21 ne propose rien
		Et le clic droit sur le bloc « Continue » de la journée du mercredi 21 ne propose rien

	Scénario: Une session sautée reste hachurée, et le créneau revient à ce qui joue sans elle
		Étant donné la socket d'état de Machin lecture ouverte pour l'interface
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je choisis « Sauter cette session » au clic droit sur le bloc « Matinale » du mercredi 21
		Alors la barre d'état annonce « Session de « Matinale » du mercredi 21 octobre à 07:00 sautée. »
		Et les sessions sautées de « Matinale » sont « 2026-10-21 »
		Et Machin lecture a reçu la demande de relire la grille
		Et le calendrier montre les blocs :
			| jour        | début | fin   | événement | état           |
			| lundi 19    | 00:00 | 01:00 | Nuit      | joue           |
			| lundi 19    | 07:00 | 09:00 | Matinale  | joue           |
			| mardi 20    | 07:00 | 09:00 | Matinale  | joue           |
			| mercredi 21 | 07:00 | 09:00 | Matinale  | sauté          |
			| mercredi 21 | 08:00 | 10:00 | Concert   | joue           |
			| mercredi 21 | 12:00 | 13:00 | Midi      | joue           |
			| jeudi 22    | 07:00 | 09:00 | Matinale  | joue           |
			| jeudi 22    | 14:00 | 20:00 | Direct    | joue           |
			| jeudi 22    | 20:00 | 21:00 | Soirée    | joue           |
			| vendredi 23 | 07:00 | 09:00 | Matinale  | estompé        |
			| samedi 24   | 10:00 | 18:00 | Week-end  | joue en partie |
			| samedi 24   | 12:00 | 13:00 | Flash     | joue           |
			| samedi 24   | 17:30 | 19:00 | Rediff    | joue           |
			| dimanche 25 | 23:00 | 24:00 | Nuit      | joue           |
		Et le bloc « Matinale » du mercredi 21 a l'infobulle :
			"""
			Matinale (Le réveil) — Émission
			mercredi 21 octobre, 07:00 – 09:00
			Revient le lundi, mardi, mercredi, jeudi, vendredi
			Session sautée : « Rétablir cette session » au clic droit
			Double-clic : ouvrir l'événement
			"""
		Et le bloc « Continue » de la journée du mercredi 21 a l'infobulle :
			"""
			Continue — Fil musical
			Fil musical permanent
			Joue de 00:00 à 08:00 et de 10:00 à 12:00 et de 13:00 à 24:00 ; masqué le reste du temps par un autre événement
			Double-clic : ouvrir l'événement
			"""

	Scénario: Les sessions se sautent jusqu'au jour choisi, celles déjà sautées comprises
		Étant donné la session du 2026-10-23 de l'événement « Matinale » est sautée
		Et je choisirai le jour « 2026-10-28 » jusqu'où sauter
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je choisis « Sauter les sessions jusqu'au… » au clic droit sur le bloc « Matinale » du jeudi 22
		Alors le choix du jour a proposé « Sauter les sessions de « Matinale » à partir du jeudi 22 octobre, jusqu'au : », à partir du « 2026-10-22 »
		Et la barre d'état annonce « 4 sessions de « Matinale » sautées, du jeudi 22 octobre au mercredi 28 octobre. »
		Et les sessions sautées de « Matinale » sont « 2026-10-22 », « 2026-10-23 », « 2026-10-26 », « 2026-10-27 », « 2026-10-28 »

	Scénario: Renoncer au choix du jour ne saute rien
		Étant donné que j'annulerai le choix du jour jusqu'où sauter
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je choisis « Sauter les sessions jusqu'au… » au clic droit sur le bloc « Matinale » du jeudi 22
		Alors aucune session de « Matinale » n'est sautée
		Et la barre d'état n'a rien annoncé

	Scénario: Une session sautée se rétablit au clic droit
		Étant donné la socket d'état de Machin lecture ouverte pour l'interface
		Et la session du 2026-10-21 de l'événement « Matinale » est sautée
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors le clic droit sur le bloc « Matinale » du mercredi 21 propose « Rétablir cette session »
		Quand je choisis « Rétablir cette session » au clic droit sur le bloc « Matinale » du mercredi 21
		Alors la barre d'état annonce « Session de « Matinale » du mercredi 21 octobre à 07:00 rétablie. »
		Et aucune session de « Matinale » n'est sautée
		Et Machin lecture a reçu la demande de relire la grille
		Et le bloc « Matinale » du mercredi 21 est « joue en partie »

	Scénario: Une session passée, même sautée, ne se rétablit plus
		Étant donné la session du 2026-10-20 de l'événement « Matinale » est sautée
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors le clic droit sur le bloc « Matinale » du mardi 20 ne propose rien
		Et le bloc « Matinale » du mardi 20 a l'infobulle :
			"""
			Matinale (Le réveil) — Émission
			mardi 20 octobre, 07:00 – 09:00
			Revient le lundi, mardi, mercredi, jeudi, vendredi
			Session sautée
			Double-clic : ouvrir l'événement
			"""

	Scénario: Le créneau d'une session sautée se clique comme une heure libre, et la remplaçante s'enregistre
		Étant donné la session du 2026-10-22 de l'événement « Matinale » est sautée
		Et que je répondrai « Créer » à la question de création
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique dans le calendrier le jeudi 22 à 07:20
		Alors la question de création a dit « Créer un événement le jeudi 22 octobre 2026 de 07:00 à 08:00 ? »
		Quand je saisis le nom interne « Vacances »
		Et j'enregistre la fiche
		Alors la base a toujours 12 événements

	Scénario: Une session ne se rétablit pas sur une émission qui a pris sa place
		Étant donné la session du 2026-10-22 de l'événement « Matinale » est sautée
		Et les événements :
			| nom      | nom_public | priorite | debut            | fin              | jours |
			| Vacances |            | emission | 2026-10-22 07:30 | 2026-10-22 08:30 |       |
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je choisis « Rétablir cette session » au clic droit sur le bloc « Matinale » du jeudi 22
		Alors la barre d'état annonce « Session de « Matinale » du jeudi 22 octobre non rétablie : elle chevaucherait « Vacances » à 07:30. »
		Et les sessions sautées de « Matinale » sont « 2026-10-22 »

	# ─── Ouvrir, créer ─────────────────────────────────────────

	Scénario: Un double-clic sur un bloc ouvre la fiche de son événement
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je double-clique sur le bloc « Concert » du mercredi 21
		Alors l'onglet ouvert est « Événement : Concert »

	Scénario: Un double-clic sur une bande d'airplay ouvre la fiche de son événement
		Étant donné les passages de l'airplay :
			| événement | début               | fin                 |
			| Matinale  | 2026-10-20 07:00:00 | 2026-10-20 09:00:00 |
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je double-clique sur la bande d'airplay « Matinale » de 07:00 du mardi 20
		Alors l'onglet ouvert est « Événement : Matinale »

	Scénario: Un clic sur une heure libre propose un événement sur l'heure entière, qui s'ouvre prérempli sans être enregistré
		Étant donné que je répondrai « Créer » à la question de création
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique dans le calendrier le dimanche 25 à 13:37
		Alors la question de création a dit « Créer un événement le dimanche 25 octobre 2026 de 13:00 à 14:00 ? »
		Et l'onglet ouvert est « Nouvel événement »
		Et la fiche de l'événement a pour début « 2026-10-25 13:00 » et pour fin « 2026-10-25 14:00 »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs
		Et la base a toujours 11 événements

	Scénario: Refuser la création ne crée rien
		Étant donné que je répondrai « Annuler » à la question de création
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique dans le calendrier le samedi 24 à 20:10
		Alors l'onglet ouvert est « Calendrier »

	Scénario: Un clic sur un bloc, ou sur une heure passée, ne propose rien
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique dans le calendrier le mercredi 21 à 08:30
		Et je clique dans le calendrier le mardi 20 à 15:50
		Alors aucune question n'a été posée
		Et l'onglet ouvert est « Calendrier »

	Scénario: L'heure en cours est libre jusqu'à sa fin
		Étant donné que je répondrai « Annuler » à la question de création
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique dans le calendrier le mardi 20 à 16:55
		Alors la question de création a dit « Créer un événement le mardi 20 octobre 2026 de 16:00 à 17:00 ? »

	Scénario: Une heure qui vient de finir est passée
		Étant donné l'horloge de l'interface au « 2026-10-20 17:00:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Et je clique dans le calendrier le mardi 20 à 16:30
		Alors aucune question n'a été posée
