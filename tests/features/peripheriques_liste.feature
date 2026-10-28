# language: fr
Fonctionnalité: La liste des périphériques audio ne fait jamais tomber l'interface
	En tant que technicien d'antenne,
	je veux que la liste des périphériques audio ne fasse jamais planter l'interface,
	afin d'ouvrir la pré-écoute et les préférences audio sans risque, même quand des sorties du poste apparaissent
	et disparaissent, au verrouillage de la session ou à la mise en veille des écrans.

	https://github.com/dascritch/machincast/issues/289 et https://github.com/dascritch/machincast/issues/305.
	machincast.audio.appareils lit les périphériques d'un seul moniteur de périphériques GStreamer pour tout le
	processus, démarré à la première liste et jamais arrêté. Avec GStreamer 1.28.2 et PipeWire 1.6.2, ceux d'Ubuntu
	26.04, arrêter un moniteur pendant que des sorties apparaissent ou disparaissent (une sortie HDMI quand l'écran se
	met en veille, une sortie qui change par défaut) tue le processus, dans un fil de PipeWire : un moniteur gardé
	ouvert suit ces changements sans tomber. Depuis GStreamer 1.28, le démarrage est asynchrone : un fil démarre les
	fournisseurs, et annonce la fin par un message DEVICE_MONITOR_STARTED sur le bus du moniteur ; la première liste
	attend ce message, au plus DEMARRAGE_DU_MONITEUR secondes, et le journal dit si elle peut être incomplète. Avant
	GStreamer 1.28, start() rend la main une fois les fournisseurs démarrés : il n'y a rien à attendre. Un moniteur qui
	ne démarre aucun fournisseur est oublié : la liste suivante en démarre un autre. Les premiers scénarios imitent le
	moniteur ; le dernier liste les périphériques du poste, avec GStreamer, dans des processus à part.

	Scénario: La première liste démarre le moniteur et attend ses fournisseurs ; les suivantes ne font que le lire
		Étant donné un moniteur de périphériques imité, qui annonce son démarrage
		Quand je liste les appareils du poste
		Et je liste les appareils du poste
		Alors le moniteur imité a reçu « start », « attendre le démarrage », « get_devices », « get_devices »
		Et la liste des appareils est celle du moniteur imité
		Et un seul moniteur imité a été créé

	Scénario: Sans démarrage annoncé à temps, la liste rend ce qu'elle a, et le dit
		Étant donné un moniteur de périphériques imité, qui n'annonce pas son démarrage
		Quand je liste les appareils du poste
		Alors le moniteur imité a reçu « start », « attendre le démarrage », « get_devices »
		Et la liste des appareils est celle du moniteur imité
		Et le journal avertit que le moniteur de périphériques n'a pas fini de démarrer

	Scénario: Avant GStreamer 1.28, le démarrage rend la main une fois les fournisseurs démarrés : rien à attendre
		Étant donné un moniteur de périphériques imité, d'un GStreamer sans message de démarrage
		Quand je liste les appareils du poste
		Alors le moniteur imité a reçu « start », « get_devices »

	Scénario: Un moniteur qui ne démarre aucun fournisseur ne donne aucun appareil, et la liste suivante en démarre un autre
		Étant donné un moniteur de périphériques imité, qui ne démarre pas
		Quand je liste les appareils du poste
		Et je liste les appareils du poste
		Alors le moniteur imité a reçu « start », « start »
		Et la liste des appareils est vide
		Et 2 moniteurs imités ont été créés

	Scénario: La liste des périphériques du poste, en boucle, ne fait jamais tomber son processus
		Quand 10 processus listent chacun 30 fois les périphériques du poste
		Alors chaque processus a rendu la main normalement
