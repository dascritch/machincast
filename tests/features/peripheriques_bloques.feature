# language: fr
Fonctionnalité: Un périphérique audio qui ne répond plus ne fige pas l'interface
	En tant que technicien d'antenne,
	je veux que l'interface reste utilisable quand un périphérique audio ne répond plus,
	afin de la retrouver vivante en revenant d'un écran verrouillé ou d'une mise en veille de l'écran.

	https://github.com/dascritch/machincast/issues/259, spec § 8.3. Au retour d'un écran verrouillé, le serveur audio du
	poste peut interrompre la pré-écoute, puis tarder à répondre : l'interface se figeait, à attendre qu'il arrête son
	pipeline. Tout changement d'état d'un pipeline de GStreamer de l'interface (lecture, pause, arrêt) se fait
	désormais hors de son fil, dans l'ordre demandé (machincast.interface.etats). Les scénarios simulent un serveur
	audio qui ne répond plus : chaque changement d'état d'un pipeline attend qu'il réponde de nouveau ; l'interface ne
	doit jamais l'attendre.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-20 19:10:00 »
		Et le sonore « Café à minuit » de « Les Gaufres », pour une copie du fichier de test « sain.flac »

	Scénario: Une pré-écoute que sa sortie interrompt s'arrête et le dit, sans figer l'interface
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur « Pré-écoute… »
		Et je lance la pré-écoute
		Et la pré-écoute est bientôt « En lecture »
		Et le VU-mètre de la pré-écoute montre bientôt du son
		Et le serveur audio ne répond plus
		Et la sortie de la pré-écoute signale l'erreur « Périphérique audio disparu »
		Alors la pré-écoute est bientôt « À l'arrêt »
		Et la pré-écoute signale « Lecture impossible : Périphérique audio disparu »
		Et l'interface n'a jamais attendu le serveur audio
		Quand le serveur audio répond de nouveau
		Alors le pipeline de la pré-écoute est bientôt arrêté

	Scénario: Pause, reprise, arrêt et fermeture de la pré-écoute n'attendent pas le serveur audio, et se font dans l'ordre
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Et je clique sur « Pré-écoute… »
		Et je lance la pré-écoute
		Et la pré-écoute est bientôt « En lecture »
		Et le VU-mètre de la pré-écoute montre bientôt du son
		Et le serveur audio ne répond plus
		Et je mets la pré-écoute en pause
		Et je lance la pré-écoute
		Et j'arrête la pré-écoute
		Et je ferme la fenêtre de pré-écoute
		Alors la pré-écoute est « À l'arrêt »
		Et l'interface n'a jamais attendu le serveur audio
		Quand le serveur audio répond de nouveau
		Alors le pipeline de la pré-écoute est bientôt arrêté
		Et le pipeline de la pré-écoute est passé, dans l'ordre, en pause, en lecture, puis à l'arrêt

	Scénario: Le VU-mètre de l'antenne réessaie son port de monitoring sans figer l'interface
		Étant donné le signal de test « bref » sur l'antenne factice
		Et un nouvel essai du port de monitoring après une demi-seconde
		Quand la fenêtre de l'interface s'ouvre
		Alors le VU-mètre de l'antenne est bientôt indisponible, avec une erreur qui commence par « Indisponible : le port de monitoring s'est fermé. »
		Quand le serveur audio ne répond plus
		Alors le port de monitoring de l'antenne est bientôt réessayé
		Et l'interface n'a jamais attendu le serveur audio

	Scénario: Seul machincast.interface.etats change l'état d'un pipeline de l'interface
		Alors aucun autre module de l'interface n'appelle set_state
