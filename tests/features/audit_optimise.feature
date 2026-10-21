# language: fr
Fonctionnalité: Audit complet optimisé, qui ne redécode pas un sonore déjà audité et inchangé
	En tant qu'administrateur,
	je veux que l'audit complet ne décode que les sonores qui en ont besoin,
	afin qu'il reste court sur une grosse discothèque.

	https://github.com/dascritch/machincast/issues/206. Un sonore garde la date de son dernier audit complet
	(sonores.audite_le) et le seuil de blanc auquel il a eu lieu (sonores.audit_seuil). L'audit complet ne décode un
	sonore que s'il n'a jamais été audité, si son fichier a été modifié depuis (date de modification plus récente que
	l'audit, ou date et taille différentes de celles enregistrées), ou si le seuil de blanc a changé. La règle vaut
	pour tous les audits : général, d'un seul sonore (--sonore, bouton « Vérification complète »), ou demandé depuis
	l'interface. Machin indexation --audit-complet --forcer décode tout, comme avant. Un fichier disparu est toujours
	repéré. L'indexation rapide n'est pas un audit complet : elle ne mesure pas les blancs et n'enregistre pas d'audit.

	Scénario: Un sonore jamais audité est décodé, et retient la date et le seuil de son audit
		Étant donné un fichier flac sain
		Et un sonore à l'état « actif » pour ce fichier
		Quand l'indexeur fait un audit complet
		Alors le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »
		Et le sonore a été audité au seuil de -40 dB, pendant cette indexation

	Scénario: Un sonore déjà audité, au même seuil, dont le fichier n'a pas changé, n'est pas redécodé
		Étant donné un fichier flac sain
		Et un sonore à l'état « actif » pour ce fichier
		Et l'indexeur a fait un audit complet
		Quand l'indexeur fait un audit complet
		Alors le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement, 0 retrait ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »
		Et la sortie standard annonce « 1 sonore déjà audité au seuil de -40 dB, au fichier inchangé : non décodé ; --forcer décode tous les sonores »
		Et le sonore a été audité au seuil de -40 dB, pendant l'indexation précédente

	Plan du scénario: Un fichier modifié depuis son audit est audité de nouveau
		Étant donné un fichier flac sain
		Et un sonore à l'état « actif » pour ce fichier
		Et l'indexeur a fait un audit complet
		Et <modification>
		Quand l'indexeur fait un audit complet
		Alors le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »
		Et le sonore a été audité au seuil de -40 dB, pendant cette indexation

		Exemples:
			| modification                                                                                  |
			| ce fichier touché, sans changer son contenu                                                   |
			| ce fichier remplacé, sous le même nom, par un fichier flac tagué, en gardant sa date de modification |

	Scénario: Un autre seuil de blanc fait auditer de nouveau
		Étant donné un fichier flac avec des blancs
		Et un sonore à l'état « actif » pour ce fichier
		Et l'indexeur a fait un audit complet
		Et un seuil de blanc de -60 dB dans la configuration
		Quand l'indexeur fait un audit complet
		Alors le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »
		Et le sonore a été audité au seuil de -60 dB, pendant cette indexation
		Et en base, le début détecté du sonore est de 0,5 seconde et sa fin détectée de 0,25 seconde, à 0,01 seconde près

	Scénario: --forcer décode tous les sonores, même déjà audités et inchangés
		Étant donné un fichier flac sain
		Et un sonore à l'état « actif » pour ce fichier
		Et l'indexeur a fait un audit complet
		Quand l'indexeur fait un audit complet forcé
		Alors le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »
		Et le sonore a été audité au seuil de -40 dB, pendant cette indexation

	Scénario: Le fichier disparu d'un sonore déjà audité est quand même repéré
		Étant donné un fichier flac sain
		Et un sonore à l'état « actif » pour ce fichier
		Et l'indexeur a fait un audit complet
		Et ce fichier supprimé
		Quand l'indexeur fait un audit complet
		Alors le sonore est à l'état « supprime »

	Scénario: L'audit d'un seul sonore déjà audité et inchangé ne le décode pas, et le dit
		Étant donné un fichier flac sain
		Et un sonore à l'état « actif » pour ce fichier
		Et l'indexeur a fait un audit complet
		Quand l'indexeur fait l'audit complet de ce seul sonore
		Alors le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement, 0 retrait ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »
		Et la sortie standard annonce « 1 sonore déjà audité au seuil de -40 dB, au fichier inchangé : non décodé ; --forcer décode tous les sonores »

	Scénario: Un audit demandé pour un sonore déjà audité et inchangé n'est pas refait, et la demande tombe
		Étant donné un fichier flac sain
		Et un sonore à l'état « actif » pour ce fichier
		Et l'indexeur a fait un audit complet
		Et un audit complet demandé pour ce sonore
		Quand l'indexeur fait une indexation rapide
		Alors le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 0 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »
		Et ce sonore n'a plus d'audit complet demandé

	Scénario: L'indexation rapide n'est pas un audit complet, et n'en enregistre pas
		Étant donné un fichier flac sain
		Et un sonore à l'état « apercu » pour ce fichier
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « actif »
		Et le sonore n'a jamais été audité

	Scénario: --forcer ne va qu'avec --audit-complet
		Quand je lance Machin indexation avec les options « --forcer »
		Alors Machin indexation se termine avec le code 2, en signalant « --forcer ne s'emploie qu'avec --audit-complet »
