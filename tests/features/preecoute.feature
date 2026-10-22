# language: fr
Fonctionnalité: Pré-écoute d'un sonore
	En tant que technicien radio,
	je veux pré-écouter un sonore, fichier ou stream, sur une sortie distincte de l'antenne,
	afin de m'assurer qu'il est correct sans le diffuser.

	https://github.com/dascritch/machincast/issues/116 et https://github.com/dascritch/machincast/issues/29, spec § 8.3.
	La fiche d'un sonore a un bouton « Pré-écoute… », qui ouvre la fenêtre de pré-écoute : une fenêtre indépendante,
	une seule pour toute l'interface, avec son lecteur (lecture et pause, arrêt, position), son VU-mètre et des
	informations techniques. La position d'un fichier se règle sur sa frise (https://github.com/dascritch/machincast/issues/224,
	frise.feature), qui ne sert que pendant sa lecture, ou sa pause ; un stream n'a ni frise ni barre de position. Elle
	joue sur le périphérique de pré-écoute de la configuration (audio.preecoute), jamais
	sur celui de l'antenne ; son choix de sortie liste les périphériques du poste, celui de l'antenne grisé, et
	s'enregistre dans le fichier de configuration. Le menu « Affichage » l'ouvre aussi, pour choisir sa sortie.
	L'écoute de l'antenne viendra avec le VU-mètre de la sortie (https://github.com/dascritch/machincast/issues/24).

	Les scénarios jouent sur la sortie factice de la configuration des tests, en temps réel ; les périphériques du poste
	sont ceux que donne le scénario. Le libellé du format vient de GStreamer, et change avec sa version : un scénario
	n'en vérifie que le nom court, « FLAC » ou « MP3 » (https://github.com/dascritch/machincast/issues/187).

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-20 19:10:00 »
		Et le sonore « Café à minuit » de « Les Gaufres », pour une copie du fichier de test « sain.flac »
		Et le sonore « Jingle », pour une copie du fichier de test « sain.mp3 »

	# ─── Ouverture ─────────────────────────────────────────────

	Scénario: La fiche d'un sonore ouvre sa pré-écoute, à l'arrêt, sur la sortie de pré-écoute
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur « Pré-écoute… »
		Alors la fenêtre de pré-écoute est ouverte, titrée « Pré-écoute : Les Gaufres – Café à minuit »
		Et la pré-écoute montre la source « …/sain.flac »
		Et la pré-écoute est « À l'arrêt », à « 0:00 / 0:01 »
		Et la sortie de la pré-écoute est « preecoute-factice »
		Et les commandes de la pré-écoute sont : lecture active, arrêt inactif, position inactive

	Scénario: Une seule pré-écoute : la fenêtre passe au sonore demandé, à l'arrêt
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur « Pré-écoute… »
		Et je lance la pré-écoute
		Et j'ouvre la fiche du sonore « Jingle »
		Et je clique sur « Pré-écoute… »
		Alors il n'y a qu'une fenêtre de pré-écoute, titrée « Pré-écoute : Jingle »
		Et la pré-écoute est « À l'arrêt », à « 0:00 / 0:01 »

	Scénario: Le menu « Affichage » ouvre la pré-écoute, sans sonore, pour choisir sa sortie
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Pré-écoute… » dans le menu « Affichage »
		Alors la fenêtre de pré-écoute est ouverte, titrée « Pré-écoute »
		Et la pré-écoute est « Aucun sonore », à « — »
		Et les commandes de la pré-écoute sont : lecture inactive, arrêt inactif, position inactive
		Et la pré-écoute n'a ni frise ni barre de position

	Scénario: Le menu « Affichage » ramène au premier plan la pré-écoute ouverte, avec son sonore
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur « Pré-écoute… »
		Et je choisis « Pré-écoute… » dans le menu « Affichage »
		Alors la fenêtre de pré-écoute est ouverte, titrée « Pré-écoute : Les Gaufres – Café à minuit »

	Scénario: Un nouveau stream, pas encore enregistré, ne se pré-écoute pas
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je clique sur « Nouveau stream »
		Alors le bouton « Pré-écoute… » de la fiche est inactif

	# ─── Lecteur ───────────────────────────────────────────────

	Scénario: La pré-écoute joue le fichier, avec son VU-mètre et ses informations techniques
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur « Pré-écoute… »
		Et je lance la pré-écoute
		Alors la pré-écoute est bientôt « En lecture »
		Et le VU-mètre de la pré-écoute montre bientôt du son
		Et la pré-écoute montre bientôt les informations :
			| information     | valeur           |
			| Format          | contient « FLAC » |
			| Échantillonnage | 44 100 Hz        |
			| Canaux          | mono             |
		Et le débit de la pré-écoute est bientôt donné en kbit/s
		Et les commandes de la pré-écoute sont : pause active, arrêt actif, position active

	Scénario: La pré-écoute se met en pause, puis reprend
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur « Pré-écoute… »
		Et je lance la pré-écoute
		Et la pré-écoute est bientôt « En lecture »
		Et je mets la pré-écoute en pause
		Alors la pré-écoute est bientôt « En pause »
		Et les commandes de la pré-écoute sont : lecture active, arrêt actif, position active

	Scénario: Arrêter la pré-écoute la ramène au début
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur « Pré-écoute… »
		Et je lance la pré-écoute
		Et la pré-écoute est bientôt « En lecture »
		Et le VU-mètre de la pré-écoute montre bientôt du son
		Et j'arrête la pré-écoute
		Alors la pré-écoute est « À l'arrêt », à « 0:00 / 0:01 »
		Et le VU-mètre de la pré-écoute est au silence

	Scénario: Un clic sur la frise déplace la lecture dans le fichier
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur « Pré-écoute… »
		Et je lance la pré-écoute
		Et je mets la pré-écoute en pause
		Et la pré-écoute est bientôt « En pause »
		Et je clique sur la frise de la pré-écoute à 60 % de sa largeur
		Alors la position de la pré-écoute est bientôt entre 0,5 et 0,7 seconde

	Scénario: À la fin du fichier, la pré-écoute revient à l'arrêt
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur « Pré-écoute… »
		Et je lance la pré-écoute
		Alors la pré-écoute est bientôt « À l'arrêt », à « 0:00 / 0:01 »

	Scénario: Fermer la fenêtre arrête la pré-écoute
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur « Pré-écoute… »
		Et je lance la pré-écoute
		Et la pré-écoute est bientôt « En lecture »
		Et je ferme la fenêtre de pré-écoute
		Alors la pré-écoute ne joue plus rien
		Et la pré-écoute ne calcule plus de forme d'onde

	Scénario: Un fichier introuvable est signalé
		Étant donné le fichier du sonore « Jingle » supprimé
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Jingle »
		Et je clique sur « Pré-écoute… »
		Et je lance la pré-écoute
		Alors la pré-écoute signale « Lecture impossible : fichier introuvable, …/sain.mp3 »
		Et la pré-écoute est « À l'arrêt », à « 0:00 / 0:01 »

	# ─── Frise (https://github.com/dascritch/machincast/issues/224) ───

	Scénario: La frise d'un fichier montre ses blancs et ses crossfades enregistrés, et dessine sa forme d'onde en tâche de fond
		Étant donné le sonore « Respiration », pour une copie du fichier de test « blancs.flac », de 2 secondes, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, aux crossfades de 0,2 s au début et 0,3 s à la fin
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Respiration »
		Et je clique sur « Pré-écoute… »
		Alors la pré-écoute a une frise
		Et la frise de la pré-écoute montre les zones « blanc de début », « fondu d'entrée », « fondu de sortie », « blanc de fin »
		Et la frise de la pré-écoute résume « Joué à l'antenne : 0:00,50 → 0:01,50 (0:01,00) »
		Et la forme d'onde de la pré-écoute est bientôt complète, silencieuse au début et sonore au milieu

	Scénario: Un crossfade non paramétré montre celui de la configuration, marqué « (défaut) »
		Étant donné le sonore « Respiration », pour une copie du fichier de test « blancs.flac », de 2 secondes, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, aux crossfades non paramétrés
		Et le crossfade de début par défaut de 0,4 seconde dans la configuration
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Respiration »
		Et je clique sur « Pré-écoute… »
		Alors l'infobulle « fondu d'entrée » de la frise de la pré-écoute est « Crossfade de début : 0,40 s (défaut), montée si le sonore précédent a un crossfade de fin »

	Scénario: Écoutée comme à l'antenne, la pré-écoute ne joue que la partie jouée, en montant depuis le silence
		Étant donné le sonore « Respiration », pour une copie du fichier de test « blancs.flac », de 2 secondes, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, aux crossfades de 0,2 s au début et 0,3 s à la fin
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Respiration »
		Et je clique sur « Pré-écoute… »
		Et je coche « Écouter comme à l'antenne » dans la pré-écoute
		Et je lance la pré-écoute
		Alors le volume de la pré-écoute est sous 25 %, au début de la montée
		Et la position de la pré-écoute passe d'emblée au début de la partie jouée, 0,5 seconde
		Et le volume de la pré-écoute est bientôt de 100 %
		Et la pré-écoute est bientôt « À l'arrêt »
		Et la pré-écoute s'est arrêtée avant 1,7 seconde, à la fin de la partie jouée

	Scénario: Décocher l'écoute comme à l'antenne rend aussitôt le plein volume
		Étant donné le sonore « Respiration », pour une copie du fichier de test « blancs.flac », de 2 secondes, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, aux crossfades de 0,2 s au début et 0,3 s à la fin
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Respiration »
		Et je clique sur « Pré-écoute… »
		Et je coche « Écouter comme à l'antenne » dans la pré-écoute
		Et je lance la pré-écoute
		Et je décoche « Écouter comme à l'antenne » dans la pré-écoute
		Alors le volume de la pré-écoute est de 100 %

	Scénario: Sans l'écoute comme à l'antenne, la pré-écoute joue tout le fichier, à plein volume
		Étant donné le sonore « Respiration », pour une copie du fichier de test « blancs.flac », de 2 secondes, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, aux crossfades de 0,2 s au début et 0,3 s à la fin
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Respiration »
		Et je clique sur « Pré-écoute… »
		Et je lance la pré-écoute
		Alors le volume de la pré-écoute est de 100 %
		Et la position de la pré-écoute est bientôt entre 0 et 0,4 seconde
		Et la pré-écoute est bientôt « À l'arrêt »
		Et la pré-écoute s'est arrêtée après 1,8 seconde

	Scénario: « Début joué » lance la lecture au début de la partie jouée
		Étant donné le sonore « Respiration », pour une copie du fichier de test « blancs.flac », de 2 secondes, aux blancs de 0,5 s au début et 0,5 s à la fin, retirés à l'antenne, aux crossfades de 0,2 s au début et 0,3 s à la fin
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Respiration »
		Et je clique sur « Pré-écoute… »
		Et je clique sur « Début joué » dans la pré-écoute
		Alors la pré-écoute est bientôt « En lecture »
		Et la position de la pré-écoute est bientôt entre 0,5 et 0,8 seconde

	Scénario: Un fichier introuvable n'a pas de forme d'onde
		Étant donné le fichier du sonore « Jingle » supprimé
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Jingle »
		Et je clique sur « Pré-écoute… »
		Alors la frise de la pré-écoute dit « Forme d'onde indisponible : fichier introuvable, …/sain.mp3 »

	# ─── Stream ────────────────────────────────────────────────

	Scénario: La pré-écoute d'un stream donne le son pré-décodé, sans barre de position
		Étant donné un serveur de flux local, avec le flux « direct » en ligne
		Et le stream « Radio » à l'adresse du flux « direct »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Radio »
		Et je clique sur « Pré-écoute… »
		Alors la pré-écoute est « À l'arrêt », à « — »
		Et les commandes de la pré-écoute sont : lecture active, arrêt inactif, position inactive
		Et la pré-écoute n'a ni frise ni barre de position
		Quand je lance la pré-écoute
		Alors la pré-écoute est bientôt « En lecture »
		Et les commandes de la pré-écoute sont : pause active, arrêt actif, position inactive
		Et la pré-écoute n'a ni frise ni barre de position
		Et le VU-mètre de la pré-écoute montre bientôt du son
		Et la pré-écoute donne bientôt des secondes pré-décodées
		Et le débit de la pré-écoute est bientôt donné en kbit/s
		Et la pré-écoute montre bientôt les informations :
			| information | valeur           |
			| Format      | contient « MP3 » |

	# ─── Sortie ────────────────────────────────────────────────

	Scénario: Le choix de sortie liste les périphériques du poste, celui de la diffusion grisé
		Étant donné les périphériques audio du poste :
			| identifiant       | nom                 |
			| antenne-factice   | Carte de l'antenne  |
			| casque-usb        | Casque USB          |
			| preecoute-factice | Haut-parleurs       |
		Et le périphérique de l'antenne « antenne-factice »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Pré-écoute… » dans le menu « Affichage »
		Alors la pré-écoute propose les sorties :
			| sortie                         | état     |
			| Haut-parleurs                  | active   |
			| Carte de l'antenne (diffusion) | inactive |
			| Casque USB                     | active   |
		Et la sortie de la pré-écoute est « preecoute-factice »

	Scénario: La sortie de la diffusion ne peut pas être choisie, même au clavier
		Étant donné les périphériques audio du poste :
			| identifiant       | nom                 |
			| antenne-factice   | Carte de l'antenne  |
			| preecoute-factice | Haut-parleurs       |
		Et le périphérique de l'antenne « antenne-factice »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Pré-écoute… » dans le menu « Affichage »
		Et je force la sortie « Carte de l'antenne (diffusion) » pour la pré-écoute
		Alors la sortie de la pré-écoute est « preecoute-factice »
		Et la pré-écoute signale « Le périphérique de la diffusion ne peut pas servir à la pré-écoute. »
		Et le fichier de configuration a toujours pour pré-écoute « preecoute-factice »

	Scénario: La sortie configurée, absente du poste, reste proposée
		Étant donné les périphériques audio du poste :
			| identifiant | nom        |
			| casque-usb  | Casque USB |
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Pré-écoute… » dans le menu « Affichage »
		Alors la pré-écoute propose les sorties « preecoute-factice (introuvable) », « Casque USB »

	Scénario: Choisir une sortie l'enregistre dans le fichier de configuration
		Étant donné les périphériques audio du poste :
			| identifiant       | nom           |
			| casque-usb        | Casque USB    |
			| preecoute-factice | Haut-parleurs |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur « Pré-écoute… »
		Et je lance la pré-écoute
		Et je choisis la sortie « Casque USB » pour la pré-écoute
		Alors la sortie de la pré-écoute est « casque-usb »
		Et la pré-écoute est « À l'arrêt », à « 0:00 / 0:01 »
		Et la pré-écoute signale « Sortie de pré-écoute enregistrée dans …/machincast.toml. »
		Et le fichier de configuration a pour pré-écoute « casque-usb », avec ses commentaires

	Scénario: La pré-écoute suit les périphériques réglés dans les préférences
		Étant donné les périphériques audio du poste :
			| identifiant       | nom           |
			| carte-2           | Carte 2       |
			| casque-usb        | Casque USB    |
			| preecoute-factice | Haut-parleurs |
		Et les préférences régleront l'antenne « carte-2 » et la pré-écoute « casque-usb »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Pré-écoute… » dans le menu « Affichage »
		Et je choisis « Préférences… » dans le menu « Fichier »
		Et je choisis « Pré-écoute… » dans le menu « Affichage »
		Alors la sortie de la pré-écoute est « casque-usb »
		Et la pré-écoute propose les sorties :
			| sortie              | état     |
			| Casque USB          | active   |
			| Carte 2 (diffusion) | inactive |
			| Haut-parleurs       | active   |
