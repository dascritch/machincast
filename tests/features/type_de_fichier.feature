# language: fr
Fonctionnalité: Type de fichier d'un sonore
	En tant que technicien,
	je veux que l'indexeur reconnaisse le type réel d'un fichier, sans se fier à son extension,
	afin qu'un document qui n'est pas du son soit écarté dès sa découverte.

	https://github.com/dascritch/machincast/issues/121, spec § 6.1. À chaque fichier qu'il examine, l'indexeur lit son
	type avec libmagic, et l'enregistre en base. Un type qui n'est pas sonore (texte, image…) passe le sonore à l'état
	« non supporté », sans décodage. Un type indéterminé (fichier vide, données brutes) laisse décider le décodage.

	Plan du scénario: Chaque format sonore est reconnu, et son type est enregistré
		Étant donné un fichier <format> sain
		Et un sonore à l'état « apercu » pour ce fichier
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « actif »
		Et le type du fichier en base est « <type> »

		Exemples:
			| format | type                |
			| mp3    | audio/mpeg          |
			| flac   | audio/flac          |
			| ogg    | audio/ogg           |
			| wav    | audio/x-wav         |
			| m4a    | video/mp4           |
			| aac    | audio/x-hx-aac-adts |

	Plan du scénario: Un fichier qui n'est pas du son, quelle que soit son extension, n'est pas supporté
		Étant donné <fichier>
		Et un sonore à l'état « apercu » pour ce fichier
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « non_supporte »
		Et le type du fichier en base est « <type> »
		Et la sortie d'erreur signale ce fichier comme « non supporté », avec « sonore passé non supporté »
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 1 non supporté, 0 supprimé, 0 rétabli, 1 sorti d'aperçu »

		Exemples:
			| fichier                                        | type       |
			| un fichier « faux.mp3 » qui contient du texte  | text/plain |
			| une image « pochette.flac »                    | image/png  |

	Scénario: Le problème d'un fichier non supporté donne son type
		Étant donné un fichier « faux.mp3 » qui contient du texte
		Et un sonore à l'état « apercu » pour ce fichier
		Quand l'indexeur fait une indexation rapide
		Alors la sortie d'erreur mentionne « non supporté : de type text/plain, ce n'est pas un fichier sonore »

	Plan du scénario: Un type indéterminé, ou un son abîmé, laisse décider le décodage
		Étant donné <fichier>
		Et un sonore à l'état « apercu » pour ce fichier
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « errone »
		Et le type du fichier en base est « <type> »

		Exemples:
			| fichier                     | type           |
			| un fichier « vide.flac » vide | inode/x-empty |
			| un fichier mp3 endommagé    | audio/mpeg     |

	Plan du scénario: Seul un sonore en aperçu, actif, erroné ou non supporté change d'état
		Étant donné un fichier « faux.mp3 » qui contient du texte
		Et un sonore à l'état « <avant> » pour ce fichier
		Quand l'indexeur fait un audit complet
		Alors le sonore est à l'état « <apres> »
		Et la sortie d'erreur signale ce fichier comme « non supporté », avec « <consequence> »

		Exemples:
			| avant        | apres        | consequence                  |
			| actif        | non_supporte | sonore passé non supporté    |
			| errone       | non_supporte | sonore passé non supporté    |
			| non_supporte | non_supporte | sonore toujours non supporté |
			| desactive    | desactive    | état désactivé conservé      |
			| expire       | expire       | état expiré conservé         |

	Scénario: Un fichier non supporté remplacé par un vrai son redevient actif
		Étant donné un fichier « faux.mp3 » qui contient du texte
		Et un sonore à l'état « apercu » pour ce fichier
		Et l'indexeur a fait une indexation rapide
		Et ce fichier remplacé, sous le même nom, par un fichier mp3 tagué
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « actif »
		Et le type du fichier en base est « audio/mpeg »
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement, 0 retrait ; 1 sonore vérifié ; 0 erroné, 0 non supporté, 0 supprimé, 1 rétabli, 0 sorti d'aperçu »

	Scénario: Le document d'audit donne le verdict « non supporté »
		Étant donné le poste à l'heure de Paris
		Et un fichier « faux.mp3 » qui contient du texte
		Et un sonore à l'état « apercu » pour ce fichier
		Quand Machin indexation est lancé sur la base de test
		Alors le document d'audit « machincast-audit-2026-10-15T08:15:00.csv » signale ce fichier, « non supporté », avec « sonore passé non supporté »
