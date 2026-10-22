# language: fr
Fonctionnalité: VU-mètre et bargraph de la sortie d'antenne
	En tant que technicien d'antenne,
	je veux qu'un VU-mètre montre le niveau de la sortie antenne,
	afin que je voie immédiatement un silence ou une saturation.

	https://github.com/dascritch/machincast/issues/24, spec § 8.1. L'accueil a, entre le sonore en cours et le prochain,
	une colonne verticale : par canal, le VU (niveau moyen, RMS) et, par-dessus, le bargraph de crête, dont un repère
	garde le maximum 2 secondes. Les niveaux se lisent sur le port de monitoring du périphérique de l'antenne :
	pipewiresrc qui capture la sortie (stream.capture.sink) avec PipeWire, pulsesrc sur son « .monitor » avec
	PulseAudio. ALSA n'en a pas : le VU-mètre se dit indisponible, sans erreur. Au-dessus du VU-mètre, un voyant
	« Saturation » s'allume dès qu'une crête atteint -1 dBFS, et reste allumé 3 secondes ; dessous, un voyant « Silence »
	s'allume après 5 secondes à -50 dBFS ou moins. Un clic sur le VU-mètre écoute l'antenne dans la fenêtre de pré-écoute (https://github.com/dascritch/machincast/issues/116).

	Sur la sortie factice des tests, le port de monitoring est un signal de test en stéréo, que le scénario choisit ;
	le silence s'y constate après une demi-seconde.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-20 20:45:00 »
		Et le silence de l'antenne constaté après une demi-seconde

	# ─── Niveaux ───────────────────────────────────────────────

	Scénario: Le VU-mètre de l'accueil montre le niveau de chaque canal de l'antenne
		Étant donné le signal de test « sinusoïde à -10 dB » sur l'antenne factice
		Quand la fenêtre de l'interface s'ouvre
		Alors le VU-mètre de l'antenne est intitulé « Antenne », avec l'infobulle « Port de monitoring : sortie factice, signal de test. Clic : écouter l'antenne en pré-écoute. »
		Et le VU-mètre de l'antenne montre bientôt 2 canaux, entre -15 et -5 dB
		Et la crête de chaque canal est au moins au niveau du VU
		Et le VU-mètre de l'antenne est disponible
		Et les voyants de l'antenne sont éteints
		Et le voyant « Silence » de l'antenne reste éteint une seconde

	Scénario: La colonne de l'antenne montre la saturation au-dessus du VU-mètre, et le silence dessous, en petit
		Quand la fenêtre de l'interface s'ouvre
		Alors la colonne de l'antenne montre, de haut en bas : « Saturation », le VU-mètre, « Silence »
		Et ses voyants sont écrits plus petit que le titre de la colonne

	Scénario: Un silence prolongé allume le voyant « Silence »
		Étant donné le signal de test « silence » sur l'antenne factice
		Quand la fenêtre de l'interface s'ouvre
		Alors le voyant « Silence » de l'antenne s'allume bientôt
		Et le voyant « Saturation » de l'antenne est éteint

	Scénario: Une crête à pleine échelle allume le voyant « Saturation »
		Étant donné le signal de test « carré à 0 dB » sur l'antenne factice
		Quand la fenêtre de l'interface s'ouvre
		Alors le voyant « Saturation » de l'antenne s'allume bientôt
		Et le voyant « Silence » de l'antenne est éteint

	Scénario: Les voyants suivent les relevés de l'antenne : 5 secondes sous -50 dB, une crête à -1 dB gardée 3 secondes
		Étant donné le silence de l'antenne constaté après 5 secondes
		Et un moniteur de l'antenne, à l'horloge fictive
		Alors ses voyants suivent ses relevés du VU et de la crête de chaque canal :
			| instant | vu       | crete     | silence | saturation |
			| 0       | -20, -20 | -10, -10  | non     | non        |
			| 1       | -60, -50 | -55, -50  | non     | non        |
			| 4,9     | -60, -60 | -55, -55  | non     | non        |
			| 5       | -60, -60 | -55, -55  | oui     | non        |
			| 6       | -60, -49 | -10, -1   | non     | oui        |
			| 8,9     | -20, -20 | -10, -1,1 | non     | oui        |
			| 9       | -20, -20 | -10, -10  | non     | non        |

	Scénario: Le repère du bargraph garde la plus haute crête de chaque canal 2 secondes
		Étant donné un VU-mètre, à l'horloge fictive
		Alors son repère suit le VU et la crête de chaque canal qu'il montre :
			| instant | vu       | crete    | repere   |
			| 0       | -30, -30 | -10, -12 | -10, -12 |
			| 1       | -30, -30 | -20, -6  | -10, -6  |
			| 2,1     | -30, -30 | -20, -20 | -20, -6  |
			| 3,1     | -30, -30 | -25, -25 | -20, -25 |
			| 3,5     | -30, -30 | -5, -30  | -5, -25  |

	# ─── Échelle ───────────────────────────────────────────────

	Scénario: Le VU-mètre de l'antenne sépare ses canaux gauche et droit par son échelle en dB
		Étant donné le signal de test « sinusoïde à -10 dB » sur l'antenne factice
		Quand la fenêtre de l'interface s'ouvre
		Et le VU-mètre de l'antenne montre bientôt 2 canaux, entre -15 et -5 dB
		Alors de gauche à droite, le VU-mètre de l'antenne montre le canal « G », l'échelle, le canal « D »
		Et l'échelle du VU-mètre de l'antenne va de 0 dB en haut à -60 dB en bas, sans nombres qui se chevauchent

	Plan du scénario: L'échelle ne garde que les nombres qui tiennent : 0 et -60 toujours, puis -20, -6, -12, -40, -30, -50
		Combien de nombres tiennent à une taille donnée dépend de la police du poste : à mi-chemin, quelques pixels de
		largeur de chiffre font gagner ou perdre un nombre. Le scénario vérifie donc la règle, quelle que soit la police
		(https://github.com/dascritch/machincast/issues/187).

		Étant donné un VU-mètre <sens> de <largeur> × <hauteur> pixels
		Alors son échelle commence à 0 et finit à -60
		Et ses nombres ne se chevauchent pas, hors 0 et -60, toujours écrits même sur un tout petit VU-mètre
		Et chaque nombre écarté chevauche un nombre gardé plus important, dans l'ordre 0, -60, -20, -6, -12, -40, -30, -50

		Exemples:
			| sens      | largeur | hauteur |
			| vertical  | 80      | 400     |
			| vertical  | 80      | 60      |
			| vertical  | 80      | 40      |
			| vertical  | 80      | 24      |
			| couché    | 600     | 56      |
			| couché    | 60      | 56      |
			| couché    | 40      | 56      |
			| couché    | 24      | 56      |

	Plan du scénario: Loin des seuils, l'échelle porte les mêmes nombres sur tous les postes
		Tous les nombres sur un grand VU-mètre, 0 et -60 seuls sur un tout petit : ces tailles restent loin des seuils
		pour une police de 20 % plus étroite ou plus large.

		Étant donné un VU-mètre <sens> de <largeur> × <hauteur> pixels
		Alors son échelle porte les nombres « <nombres> »

		Exemples:
			| sens      | largeur | hauteur | nombres                              |
			| vertical  | 80      | 400     | 0, -6, -12, -20, -30, -40, -50, -60  |
			| vertical  | 80      | 24      | 0, -60                               |
			| couché    | 600     | 56      | 0, -6, -12, -20, -30, -40, -50, -60  |
			| couché    | 24      | 56      | 0, -60                               |

	Scénario: Le VU-mètre de la pré-écoute a son échelle en dB sous ses canaux
		Étant donné le signal de test « sinusoïde à -10 dB » sur l'antenne factice
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Alors l'échelle du VU-mètre de la pré-écoute va de -60 dB à gauche à 0 dB à droite, sous ses canaux, sans nombres qui se chevauchent

	# ─── Disponibilité ─────────────────────────────────────────

	Scénario: Avec la sortie ALSA, le VU-mètre est indisponible, sans erreur
		Étant donné la configuration audio sortie « alsa », avec le périphérique d'antenne « hw:0 »
		Et un nouvel essai du port de monitoring après une demi-seconde
		Quand la fenêtre de l'interface s'ouvre
		Alors le VU-mètre de l'antenne est indisponible : « Indisponible avec la sortie ALSA, qui n'a pas de port de monitoring. »
		Et l'accueil ne capture rien
		Et le port de monitoring ne sera pas rouvert

	Scénario: Sans périphérique d'antenne, le VU-mètre est indisponible
		Étant donné la configuration audio sortie « pipewire », sans périphérique d'antenne
		Quand la fenêtre de l'interface s'ouvre
		Alors le VU-mètre de l'antenne est indisponible : « Indisponible : périphérique de l'antenne à renseigner. »
		Et l'accueil ne capture rien
		Et le port de monitoring ne sera pas rouvert

	Scénario: Les préférences qui règlent l'antenne changent aussitôt le port du VU-mètre
		Étant donné la configuration audio sortie « pipewire », sans périphérique d'antenne
		Et les préférences régleront l'antenne « carte-2 » et la pré-écoute « casque-usb »
		Quand la fenêtre de l'interface s'ouvre
		Alors le VU-mètre de l'antenne est intitulé « Antenne », avec l'infobulle « Port de monitoring : PipeWire, périphérique à renseigner. Clic : écouter l'antenne en pré-écoute. »
		Quand je choisis « Préférences… » dans le menu « Fichier »
		Alors le VU-mètre de l'antenne est intitulé « Antenne », avec l'infobulle « Port de monitoring : PipeWire, carte-2. Clic : écouter l'antenne en pré-écoute. »
		Et le VU-mètre de l'antenne ne dit plus « Indisponible : périphérique de l'antenne à renseigner. »

	Scénario: Un port de monitoring qui ne s'ouvre pas est signalé, puis réessayé
		Étant donné le signal de test « introuvable » sur l'antenne factice
		Et un nouvel essai du port de monitoring après une demi-seconde
		Quand la fenêtre de l'interface s'ouvre
		Alors le VU-mètre de l'antenne est bientôt indisponible, avec une erreur qui commence par « Indisponible : »
		Quand le signal de test « sinusoïde à -10 dB » remplace celui de l'antenne factice
		Alors le VU-mètre de l'antenne montre bientôt 2 canaux, entre -15 et -5 dB
		Et le VU-mètre de l'antenne est disponible

	Scénario: Un port de monitoring qui se ferme est signalé
		Étant donné le signal de test « bref » sur l'antenne factice
		Quand la fenêtre de l'interface s'ouvre
		Alors le VU-mètre de l'antenne est bientôt indisponible, avec une erreur qui commence par « Indisponible : le port de monitoring s'est fermé. »

	Plan du scénario: Le port de monitoring de PipeWire et de PulseAudio est celui du périphérique de l'antenne, capté en stéréo
		Quand je construis le port de monitoring de la sortie « <sortie> », périphérique « <peripherique> »
		Alors c'est l'élément « <element> », avec <proprietes>
		Et le port de monitoring donne 2 canaux

		Exemples:
			| sortie     | peripherique             | element     | proprietes                                                                         |
			| pipewire   | alsa_output.usb-UA22.pro | pipewiresrc | target-object « alsa_output.usb-UA22.pro », stream-properties « stream.capture.sink=true » |
			| pulseaudio | alsa_output.usb-UA22.pro | pulsesrc    | device « alsa_output.usb-UA22.pro.monitor »                                        |

	# ─── Écouter l'antenne ─────────────────────────────────────

	Scénario: Un clic sur le VU-mètre écoute l'antenne dans la fenêtre de pré-écoute
		Étant donné le signal de test « sinusoïde à -10 dB » sur l'antenne factice
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Alors la fenêtre de pré-écoute est ouverte, titrée « en cours : — »
		Et la pré-écoute montre la source « Antenne : sortie factice, signal de test »
		Et les commandes de la pré-écoute sont : lecture active, arrêt inactif, position inactive
		Quand je lance la pré-écoute
		Alors la pré-écoute est bientôt « En lecture »
		Et le VU-mètre de la pré-écoute montre bientôt du son
		Et les commandes de la pré-écoute sont : pause active, arrêt actif, position inactive

	Scénario: L'écoute de l'antenne a pour titre le texte public du sonore en cours, et le suit
		https://github.com/dascritch/machincast/issues/223 : le texte public est ce que la page publique affiche.

		Étant donné le signal de test « sinusoïde à -10 dB » sur l'antenne factice
		Et la socket d'état de Machin lecture ouverte pour l'interface
		Et Machin lecture diffuse un sonore au texte public « Les Gaufres – Café à minuit »
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Alors la fenêtre de pré-écoute est bientôt titrée « en cours : Les Gaufres – Café à minuit »
		Quand Machin lecture diffuse un sonore au texte public « Radio Thune, la radio »
		Alors la fenêtre de pré-écoute est bientôt titrée « en cours : Radio Thune, la radio »

	Scénario: Un sonore pré-écouté ne prend pas le titre de l'antenne
		Étant donné le signal de test « sinusoïde à -10 dB » sur l'antenne factice
		Et la socket d'état de Machin lecture ouverte pour l'interface
		Et Machin lecture diffuse un sonore au texte public « Les Gaufres – Café à minuit »
		Et les sonores :
			| artiste | titre  | type    | etat  | duree | emplacement      |
			|         | Jingle | fichier | actif | 8     | /srv/jingle.flac |
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Et je demande la pré-écoute du sonore « Jingle »
		Et Machin lecture diffuse un sonore au texte public « Radio Thune, la radio »
		Alors la fenêtre de pré-écoute reste titrée « Pré-écoute : Jingle »

	Scénario: Le bouton « Pré-écoute » de la fenêtre, en bas à gauche, écoute l'antenne aussitôt
		Étant donné le signal de test « sinusoïde à -10 dB » sur l'antenne factice
		Quand la fenêtre de l'interface s'ouvre
		Alors le bouton « Pré-écoute » est en bas à gauche de la fenêtre, hors des onglets
		Quand je clique sur le bouton « Pré-écoute » de la fenêtre
		Alors la fenêtre de pré-écoute est ouverte, titrée « en cours : — »
		Et la pré-écoute montre la source « Antenne : sortie factice, signal de test »
		Et la pré-écoute est bientôt « En lecture »

	Scénario: Une antenne devenue indisponible ne se pré-écoute pas
		Étant donné le signal de test « sinusoïde à -10 dB » sur l'antenne factice
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Et le signal de test « introuvable » remplace celui de l'antenne factice
		Et je lance la pré-écoute
		Alors la pré-écoute signale bientôt « Lecture impossible : Indisponible : »
		Et la pré-écoute est « À l'arrêt »

	Scénario: Sous PipeWire, écouter l'antenne relie ses ports de monitoring au périphérique de pré-écoute
		Étant donné la configuration audio sortie « pipewire », avec le périphérique d'antenne « antenne-ua22 » et de pré-écoute « casque-usb »
		Et PipeWire simulé, avec les ports de sortie « antenne-ua22:monitor_FL, antenne-ua22:monitor_FR, casque-usb:monitor_FL, casque-usb:monitor_FR » et d'entrée « casque-usb:playback_FR, casque-usb:playback_FL, antenne-ua22:playback_FL, antenne-ua22:playback_FR »
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Et je lance la pré-écoute
		Alors la pré-écoute est bientôt « En lecture »
		Et PipeWire relie « antenne-ua22:monitor_FL » à « casque-usb:playback_FL », et « antenne-ua22:monitor_FR » à « casque-usb:playback_FR »
		Et le VU-mètre de la pré-écoute montre bientôt du son
		Quand je mets la pré-écoute en pause
		Alors PipeWire ne relie plus rien
		Quand je lance la pré-écoute
		Alors PipeWire relie « antenne-ua22:monitor_FL » à « casque-usb:playback_FL », et « antenne-ua22:monitor_FR » à « casque-usb:playback_FR »
		Quand j'arrête la pré-écoute
		Alors PipeWire ne relie plus rien

	Scénario: Un casque mono, sous PipeWire, reçoit les deux canaux de l'antenne
		Étant donné la configuration audio sortie « pipewire », avec le périphérique d'antenne « antenne-ua22 » et de pré-écoute « casque-mono »
		Et PipeWire simulé, avec les ports de sortie « antenne-ua22:monitor_FL, antenne-ua22:monitor_FR » et d'entrée « enceintes:playback_FL, casque-mono:playback_MONO, enceintes:playback_FR »
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Et je lance la pré-écoute
		Alors PipeWire relie « antenne-ua22:monitor_FL » à « casque-mono:playback_MONO », et « antenne-ua22:monitor_FR » à « casque-mono:playback_MONO »

	Scénario: Fermer la pré-écoute, sous PipeWire, défait ses liens
		Étant donné la configuration audio sortie « pipewire », avec le périphérique d'antenne « antenne-ua22 » et de pré-écoute « casque-usb »
		Et PipeWire simulé, avec les ports de sortie « antenne-ua22:monitor_FL, antenne-ua22:monitor_FR » et d'entrée « casque-usb:playback_FL, casque-usb:playback_FR »
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Et je lance la pré-écoute
		Et la pré-écoute est bientôt « En lecture »
		Et je ferme la fenêtre de pré-écoute
		Alors PipeWire ne relie plus rien

	Plan du scénario: Sans les ports de l'antenne ou de la pré-écoute, PipeWire ne relie rien, et la pré-écoute le dit
		Étant donné la configuration audio sortie « pipewire », avec le périphérique d'antenne « antenne-ua22 » et de pré-écoute « casque-usb »
		Et PipeWire simulé, avec les ports de sortie « <sorties> » et d'entrée « <entrees> »
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Et je lance la pré-écoute
		Alors la pré-écoute signale « Lecture impossible : PipeWire n'a pas de port de monitoring pour antenne-ua22, ou pas d'entrée pour casque-usb. »
		Et la pré-écoute est « À l'arrêt »
		Et PipeWire ne relie plus rien

		Exemples:
			| sorties                                     | entrees                                       |
			| casque-usb:monitor_FL                       | casque-usb:playback_FL                        |
			| antenne-ua22:monitor_FL, casque-usb:monitor_FL | antenne-ua22:playback_FL, enceintes:playback_FL |

	Scénario: PipeWire qui refuse un lien arrête la pré-écoute, et elle le dit
		Étant donné la configuration audio sortie « pipewire », avec le périphérique d'antenne « antenne-ua22 » et de pré-écoute « casque-usb »
		Et PipeWire simulé, avec les ports de sortie « antenne-ua22:monitor_FL » et d'entrée « casque-usb:playback_FL »
		Et PipeWire simulé refuse de relier : « failed to link ports: Operation not permitted »
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Et je lance la pré-écoute
		Alors la pré-écoute signale « Lecture impossible : pw-link antenne-ua22:monitor_FL casque-usb:playback_FL : failed to link ports: Operation not permitted »
		Et la pré-écoute est « À l'arrêt »

	Scénario: Un lien que PipeWire a déjà n'empêche pas d'écouter l'antenne
		Étant donné la configuration audio sortie « pipewire », avec le périphérique d'antenne « antenne-ua22 » et de pré-écoute « casque-usb »
		Et PipeWire simulé, avec les ports de sortie « antenne-ua22:monitor_FL » et d'entrée « casque-usb:playback_FL »
		Et PipeWire simulé refuse de relier : « failed to link ports: File exists »
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Et je lance la pré-écoute
		Alors la pré-écoute est bientôt « En lecture »

	Plan du scénario: L'écoute de l'antenne joue sur la pré-écoute avec PulseAudio, et ne fait que mesurer sous PipeWire
		Quand je construis l'écoute de l'antenne sur la sortie « <sortie> », pré-écoute « casque-usb »
		Alors l'écoute de l'antenne finit par l'élément « <element> »

		Exemples:
			| sortie     | element   |
			| pulseaudio | pulsesink |
			| pipewire   | fakesink  |

	Scénario: Sans pw-link, la pré-écoute de l'antenne le dit
		Étant donné la configuration audio sortie « pipewire », avec le périphérique d'antenne « antenne-ua22 » et de pré-écoute « casque-usb »
		Et PipeWire simulé, sans pw-link
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Et je lance la pré-écoute
		Alors la pré-écoute signale « Lecture impossible : pw-link introuvable ; installer pipewire-bin. »

	Scénario: Un VU-mètre indisponible n'écoute rien
		Étant donné la configuration audio sortie « alsa », avec le périphérique d'antenne « hw:0 »
		Quand la fenêtre de l'interface s'ouvre
		Et je clique sur le VU-mètre de l'antenne
		Alors il n'y a pas de fenêtre de pré-écoute

	Scénario: Fermer l'interface arrête la capture de l'antenne
		Étant donné le signal de test « sinusoïde à -10 dB » sur l'antenne factice
		Quand la fenêtre de l'interface s'ouvre
		Et le VU-mètre de l'antenne montre bientôt 2 canaux, entre -15 et -5 dB
		Et je ferme la fenêtre de l'interface
		Alors l'accueil ne capture rien

	Scénario: Rouvrir le port de monitoring, après les préférences, arrête la capture précédente
		Étant donné le signal de test « sinusoïde à -10 dB » sur l'antenne factice
		Quand la fenêtre de l'interface s'ouvre
		Et le VU-mètre de l'antenne montre bientôt 2 canaux, entre -15 et -5 dB
		Et l'accueil rouvre le port de monitoring de la même antenne
		Alors la capture précédente de l'antenne est arrêtée
		Et le VU-mètre de l'antenne montre bientôt 2 canaux, entre -15 et -5 dB
