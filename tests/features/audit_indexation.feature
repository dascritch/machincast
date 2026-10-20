# language: fr
Fonctionnalité: Document d'audit de l'indexation, en CSV et en HTML
	En tant que technicien d'antenne,
	je veux que l'indexeur regroupe dans un document d'audit les anomalies relevées,
	afin de traiter les fichiers défectueux sans relire la sortie d'erreur.

	https://github.com/dascritch/machincast/issues/11, spec § 6.3. Chaque passage écrit un .csv et un .html, nommés
	avec l'horodatage de son lancement en heure locale, dans /tmp ; les scénarios les écrivent dans leur répertoire
	temporaire, et lancent toute indexation le 2026-10-15 à 08:15:00, heure de Paris. Le CSV se sépare par des
	points-virgules ; sa dernière ligne porte le bilan.

	Contexte:
		Étant donné le poste à l'heure de Paris

	Scénario: Le document liste les fichiers défectueux, par leur chemin, puis le bilan
		Étant donné un fichier introuvable
		Et un sonore à l'état « actif » pour ce fichier
		Quand Machin indexation est lancé sur la base de test
		Alors le document d'audit « machincast-audit-2026-10-15T08:15:00.csv » contient :
			| date                | chemin           | verdict     | problème                                                                                             | conséquence           |
			| 2026-10-15 08:15:00 | …/disparu.flac   | introuvable | aucun fichier à cet emplacement                                                                      | sonore passé supprimé |
			| 2026-10-15 08:15:00 |                  | bilan       | indexation rapide : 0 nouveau sonore, 0 rattachement ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 1 supprimé, 0 rétabli, 0 sorti d'aperçu |    |
		Et la page d'audit « machincast-audit-2026-10-15T08:15:00.html » s'intitule « Audit de l'indexation du 2026-10-15 08:15:00 »
		Et la page d'audit « machincast-audit-2026-10-15T08:15:00.html » montre « …/disparu.flac », « introuvable », « aucun fichier à cet emplacement », « sonore passé supprimé »
		Et la page d'audit « machincast-audit-2026-10-15T08:15:00.html » montre « indexation rapide : 0 nouveau sonore, 0 rattachement ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 1 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Le problème d'un fichier endommagé est donné sans répéter son verdict
		Étant donné un fichier mp3 endommagé
		Et un sonore à l'état « apercu » pour ce fichier
		Quand Machin indexation est lancé sur la base de test
		Alors le document d'audit « machincast-audit-2026-10-15T08:15:00.csv » signale ce fichier, « endommagé », avec « sonore passé erroné »

	Scénario: Sans anomalie, le document ne porte que le bilan, et ne liste pas les opérations normales
		Étant donné un fichier flac sain
		Et un sonore à l'état « apercu » pour ce fichier
		Quand Machin indexation est lancé sur la base de test, en audit complet
		Alors le document d'audit « machincast-audit-2026-10-15T08:15:00.csv » contient :
			| date                | chemin | verdict | problème                                                                                                 | conséquence |
			| 2026-10-15 08:15:00 |        | bilan   | audit complet : 0 nouveau sonore, 0 rattachement ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 1 sorti d'aperçu |   |
		Et la page d'audit « machincast-audit-2026-10-15T08:15:00.html » montre « Aucune anomalie. »

	Scénario: Les chemins du document sont annoncés sur la sortie standard, après le bilan
		Quand Machin indexation est lancé sur la base de test
		Alors Machin indexation se termine avec le code 0, en signalant « document d'audit : …/audit/machincast-audit-2026-10-15T08:15:00.csv, …/audit/machincast-audit-2026-10-15T08:15:00.html »
		Et l'annonce du document d'audit suit le bilan

	Scénario: Un document qui ne peut pas être écrit est signalé, sans arrêter l'indexation
		Étant donné un répertoire d'audit où l'on ne peut pas écrire
		Quand Machin indexation est lancé sur la base de test
		Alors Machin indexation se termine avec le code 0, en signalant « indexation rapide : 0 nouveau sonore, 0 rattachement ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »
		Et la sortie d'erreur de Machin indexation mentionne « document d'audit impossible à écrire dans »

	Scénario: Rien n'est écrit dans le log
		Étant donné un fichier introuvable
		Et un sonore à l'état « actif » pour ce fichier
		Quand Machin indexation est lancé sur la base de test
		Alors le log de la base est vide
