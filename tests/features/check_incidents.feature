# language: fr
Fonctionnalité: Incidents pendant la vérification d'un sonore
	En tant que technicien d'antenne,
	je veux qu'un sonore dont la vérification plante ou se bloque soit signalé en incident, sans arrêter les autres,
	afin qu'un seul fichier à problème n'empêche ni l'indexation ni l'audit du reste des banques.

	https://github.com/dascritch/machincast/issues/401. Chaque sonore est vérifié à part : une erreur imprévue pendant sa
	vérification est un incident, désigné par son chemin, sur la sortie d'erreur et dans le document d'audit ; le sonore
	reste tel quel et la vérification passe au suivant. L'examen d'un fichier qui dure plus de 10 minutes est abandonné
	en incident : il tourne dans un fil à part, que la vérification n'attend pas au-delà, car le module signal
	n'interrompt pas un appel bloqué dans GStreamer, libmagic ou le système de fichiers. Les scénarios imitent la panne
	ou le blocage dans l'examen du type du fichier, et ramènent la limite à 1 seconde. Un décodeur absent arrête
	toujours toute la vérification (indexing_log.feature).

	Contexte:
		Étant donné le poste à l'heure de Paris

	Scénario: Une erreur imprévue sur un sonore est un incident, et le sonore suivant est vérifié
		Étant donné un fichier flac sain
		Et un sonore à l'état « preview » pour ce fichier
		Et un deuxième fichier flac sain, dont le sonore est à l'état « preview »
		Et l'examen de ce fichier lève une erreur imprévue
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « preview »
		Et le sonore n'a pas de date de vérification complète
		Et le deuxième sonore est à l'état « active »
		Et la sortie d'erreur signale ce fichier en incident : « incident, erreur imprévue pendant la vérification : RuntimeError: panne imitée ; sonore laissé tel quel »
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 1 sorti d'aperçu ; 1 incident »

	Scénario: Un examen qui dépasse la limite est abandonné en incident, et le sonore suivant est vérifié
		Étant donné un fichier flac sain
		Et un sonore à l'état « active » pour ce fichier
		Et un deuxième fichier flac sain, dont le sonore est à l'état « preview »
		Et une limite de 1 seconde pour l'examen d'un fichier
		Et l'examen de ce fichier se bloque
		Quand l'indexeur fait un audit complet
		Alors l'audit complet a duré moins de 30 secondes
		Et le sonore est à l'état « active »
		Et le sonore n'a pas de date de vérification complète
		Et le deuxième sonore est à l'état « active »
		Et la sortie d'erreur signale ce fichier en incident : « incident, vérification abandonnée au bout de 1 seconde ; sonore laissé tel quel »
		Et le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 1 sorti d'aperçu ; 1 incident »

	Scénario: Le document d'audit liste l'incident
		Étant donné un fichier flac sain
		Et un sonore à l'état « preview » pour ce fichier
		Et l'examen de ce fichier lève une erreur imprévue
		Quand Machin indexer est lancé sur la base de test
		Alors le document d'audit « machincast-audit-2026-10-15T08:15:00.csv » signale ce fichier, « incident », avec « sonore laissé tel quel »

	Scénario: La limite de l'examen d'un fichier est de 10 minutes
		Alors l'examen d'un fichier est abandonné au bout de 10 minutes
