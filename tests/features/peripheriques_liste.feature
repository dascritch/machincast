# language: fr
Fonctionnalité: La liste des périphériques audio ne fait jamais tomber l'interface
	En tant que technicien d'antenne,
	je veux que la liste des périphériques audio ne fasse jamais planter l'interface,
	afin d'ouvrir la pré-écoute et les préférences audio sans risque.

	https://github.com/dascritch/machincast/issues/289. machincast.audio.appareils démarre un moniteur de périphériques
	GStreamer, lit ses périphériques, puis l'arrête. Depuis GStreamer 1.28, le démarrage est asynchrone : un fil démarre
	les fournisseurs, et annonce la fin par un message DEVICE_MONITOR_STARTED sur le bus du moniteur. Avec GStreamer
	1.28.2, celui d'Ubuntu 26.04, la liste lue trop tôt est incomplète, et l'arrêt pendant le démarrage corrompt une
	liste de GLib, qui tue le processus (corrigé par GStreamer 1.28.3 :
	https://gitlab.freedesktop.org/gstreamer/gstreamer/-/merge_requests/11554). La liste attend donc ce message, au plus
	DEMARRAGE_DU_MONITEUR secondes ; sans lui, elle rend ce qu'elle a, sans arrêter le moniteur. Avant GStreamer 1.28,
	start() rend la main une fois les fournisseurs démarrés : il n'y a rien à attendre. Les premiers scénarios imitent le
	moniteur ; le dernier liste les périphériques du poste, avec GStreamer, dans des processus à part.

	Scénario: La liste attend que le moniteur ait démarré ses fournisseurs, puis l'arrête
		Étant donné un moniteur de périphériques imité, qui annonce son démarrage
		Quand je liste les appareils du poste
		Alors le moniteur imité a reçu « start », « attendre le démarrage », « get_devices », « stop »
		Et la liste des appareils est celle du moniteur imité

	Scénario: Sans démarrage annoncé à temps, la liste rend ce qu'elle a, sans arrêter le moniteur, et le dit
		Étant donné un moniteur de périphériques imité, qui n'annonce pas son démarrage
		Quand je liste les appareils du poste
		Alors le moniteur imité a reçu « start », « attendre le démarrage », « get_devices »
		Et la liste des appareils est celle du moniteur imité
		Et le journal avertit que le moniteur de périphériques n'a pas fini de démarrer

	Scénario: Avant GStreamer 1.28, le démarrage rend la main une fois les fournisseurs démarrés : rien à attendre
		Étant donné un moniteur de périphériques imité, d'un GStreamer sans message de démarrage
		Quand je liste les appareils du poste
		Alors le moniteur imité a reçu « start », « get_devices », « stop »

	Scénario: Un moniteur qui ne démarre aucun fournisseur ne donne aucun appareil
		Étant donné un moniteur de périphériques imité, qui ne démarre pas
		Quand je liste les appareils du poste
		Alors le moniteur imité a reçu « start »
		Et la liste des appareils est vide

	Scénario: La liste des périphériques du poste, en boucle, ne fait jamais tomber son processus
		Quand 10 processus listent chacun 30 fois les périphériques du poste
		Alors chaque processus a rendu la main normalement
