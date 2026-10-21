# language: fr
Fonctionnalité: Audit complet demandé pour certains sonores
	En tant que programmateur musical,
	je veux marquer des sonores pour un audit complet,
	afin que la prochaine indexation, même rapide, les revérifie en entier sans auditer toute la discothèque.

	https://github.com/dascritch/machincast/issues/114. L'interface marque des sonores (sonores.audit_demande) ; la
	prochaine indexation, rapide ou complète, les décode et mesure leurs blancs comme l'audit complet, puis efface la
	marque. Un fichier introuvable garde sa marque, jusqu'à ce qu'il soit vérifié.

	Scénario: L'indexation rapide fait l'audit complet d'un sonore marqué, puis efface sa marque
		Étant donné un fichier flac avec des blancs
		Et un sonore à l'état « actif » pour ce fichier
		Et un audit complet demandé pour ce sonore
		Et un seuil de blanc de -60 dB dans la configuration
		Quand l'indexeur fait une indexation rapide
		Alors en base, le début détecté du sonore est de 0,5 seconde et sa fin détectée de 0,25 seconde, à 0,01 seconde près
		Et ce sonore n'a plus d'audit complet demandé
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Sans marque, l'indexation rapide ne revérifie pas un sonore actif
		Étant donné un fichier flac avec des blancs
		Et un sonore à l'état « actif » pour ce fichier
		Quand l'indexeur fait une indexation rapide
		Alors en base, le sonore n'a ni début ni fin détectés
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Un sonore marqué dont le fichier est introuvable garde sa marque
		Étant donné un fichier introuvable
		Et un sonore à l'état « actif » pour ce fichier
		Et un audit complet demandé pour ce sonore
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « supprime »
		Et ce sonore a toujours un audit complet demandé

	Scénario: L'audit complet efface aussi la marque
		Étant donné un fichier flac sain
		Et un sonore à l'état « actif » pour ce fichier
		Et un audit complet demandé pour ce sonore
		Quand l'indexeur fait un audit complet
		Alors ce sonore n'a plus d'audit complet demandé

	Scénario: La vérification d'un seul sonore efface sa marque
		Étant donné un fichier flac sain
		Et un sonore à l'état « actif » pour ce fichier
		Et un audit complet demandé pour ce sonore
		Quand l'indexeur fait l'audit complet de ce seul sonore
		Alors ce sonore n'a plus d'audit complet demandé
