# language: fr
Fonctionnalité: La fiche d'un événement annonce sa prochaine session sautée, et la rétablit
	En tant que responsable d'antenne,
	je veux que la fiche d'un événement me dise quand sa prochaine session est sautée,
	afin de ne pas croire qu'un événement va passer à l'antenne alors qu'il ne jouera pas.

	https://github.com/dascritch/machincast/issues/295. Une session sautée
	(https://github.com/dascritch/machincast/issues/273) se note par le jour où elle commence : elle reste sautée quand
	l'heure de l'événement change. La fiche annonce la première session sautée qui n'est pas passée, en cours ou à
	venir, en haut, sous l'erreur, sur un liseret orange : c'est un avertissement, qui ne refuse rien. Son bouton
	« Rétablir » la rétablit comme le clic droit du calendrier, aux mêmes règles : pas une session commencée, ni une
	session dont un événement de même priorité a pris la place. « Matinale » revient du lundi au vendredi ; le
	20 octobre 2026 est un mardi.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et les événements :
			| nom      | nom_public | priorite    | debut            | fin              | jours                                   |
			| Continue |            | fil_musical |                  |                  |                                         |
			| Matinale | Le réveil  | emission    | 2026-10-05 07:00 | 2026-10-05 09:00 | lundi, mardi, mercredi, jeudi, vendredi |

	Scénario: La prochaine session sautée s'annonce en haut de la fiche, sur un liseret orange
		Étant donné l'horloge de l'interface au « 2026-10-20 16:40:00 »
		Et la session du 2026-10-22 de l'événement « Matinale » est sautée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Alors la fiche annonce « La session du jeudi 22 octobre 2026 à 07:00 est sautée : elle ne jouera pas. »
		Et l'annonce est sous l'erreur de la fiche, sur un liseret orange de 4 pixels
		Et le bouton « Rétablir » de l'annonce est actif
		Et la fiche ne signale rien

	Scénario: Une session sautée déjà passée ne s'annonce pas ; la suivante, si
		Étant donné l'horloge de l'interface au « 2026-10-20 16:40:00 »
		Et la session du 2026-10-19 de l'événement « Matinale » est sautée
		Et la session du 2026-10-20 de l'événement « Matinale » est sautée
		Et la session du 2026-10-23 de l'événement « Matinale » est sautée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Alors la fiche annonce « La session du vendredi 23 octobre 2026 à 07:00 est sautée : elle ne jouera pas. »

	Scénario: Sans session sautée à venir, la fiche n'annonce rien
		Étant donné l'horloge de l'interface au « 2026-10-20 16:40:00 »
		Et la session du 2026-10-19 de l'événement « Matinale » est sautée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Alors la fiche n'annonce aucune session sautée

	Scénario: Une session sautée en cours s'annonce, mais ne se rétablit plus
		Étant donné l'horloge de l'interface au « 2026-10-21 07:30:00 »
		Et la session du 2026-10-21 de l'événement « Matinale » est sautée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Alors la fiche annonce « La session du mercredi 21 octobre 2026 à 07:00 est sautée : elle ne joue pas. »
		Et le bouton « Rétablir » de l'annonce est inactif, avec l'infobulle « Elle a déjà commencé : elle ne se rétablit plus. »

	Scénario: Changer l'heure de l'événement garde la session sautée, et la fiche l'annonce à la nouvelle heure
		Étant donné l'horloge de l'interface au « 2026-10-20 16:40:00 »
		Et la session du 2026-10-22 de l'événement « Matinale » est sautée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je règle le début de la fiche de l'événement au « 2026-10-05 08:42 »
		Et j'enregistre la fiche
		Alors la fiche annonce « La session du jeudi 22 octobre 2026 à 08:42 est sautée : elle ne jouera pas. »
		Et les sessions sautées de « Matinale » en base sont « 2026-10-22 »

	Scénario: « Rétablir » rétablit la session : l'annonce disparaît, et Machin lecture relit la grille
		Étant donné l'horloge de l'interface au « 2026-10-20 16:40:00 »
		Et la socket d'état de Machin lecture ouverte pour l'interface
		Et la session du 2026-10-22 de l'événement « Matinale » est sautée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je clique sur « Rétablir »
		Alors la fiche n'annonce aucune session sautée
		Et les sessions sautées de « Matinale » en base sont aucune
		Et la barre d'état annonce « Session de « Matinale » du jeudi 22 octobre à 07:00 rétablie. »
		Et Machin lecture a reçu la demande de relire la grille

	Scénario: « Rétablir » garde les champs modifiés et pas encore enregistrés
		Étant donné l'horloge de l'interface au « 2026-10-20 16:40:00 »
		Et la session du 2026-10-22 de l'événement « Matinale » est sautée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je saisis le nom interne « Matinale d'hiver »
		Et je clique sur « Rétablir »
		Alors la fiche n'annonce aucune session sautée
		Et la fiche est modifiée, avec le nom interne « Matinale d'hiver »
		Et les sessions sautées de « Matinale » en base sont aucune

	Scénario: Une session dont une émission a pris la place ne se rétablit pas depuis la fiche
		Étant donné l'horloge de l'interface au « 2026-10-20 16:40:00 »
		Et la session du 2026-10-22 de l'événement « Matinale » est sautée
		Et les événements :
			| nom      | nom_public | priorite | debut            | fin              | jours |
			| Vacances |            | emission | 2026-10-22 07:30 | 2026-10-22 08:30 |       |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Alors le bouton « Rétablir » de l'annonce est inactif, avec l'infobulle « « Vacances », de même priorité, a pris sa place le jeudi 22 octobre à 07:30. »

	Scénario: Une session rétablie depuis le calendrier quitte l'annonce au rafraîchissement des onglets
		Étant donné l'horloge de l'interface au « 2026-10-20 16:40:00 »
		Et la session du 2026-10-22 de l'événement « Matinale » est sautée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et la session du 2026-10-22 de « Matinale » est rétablie en base
		Et je choisis « Rafraîchir les onglets » dans le menu « Affichage »
		Alors la fiche n'annonce aucune session sautée

	Scénario: La copie d'un événement n'annonce pas les sessions sautées de l'original
		Étant donné l'horloge de l'interface au « 2026-10-20 16:40:00 »
		Et la session du 2026-10-22 de l'événement « Matinale » est sautée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je clique sur « Dupliquer »
		Alors la fiche n'annonce aucune session sautée
