# language: fr
Fonctionnalité: Indexation rapide
	En tant qu'administrateur,
	je veux un mode d'indexation rapide,
	afin de ne pas lancer d'opérations trop longues.

	Un nouveau fichier est enregistré à l'état « aperçu », sans être décodé. L'indexation rapide, par défaut,
	ne décode que les sonores en aperçu ; l'audit complet décode tous les sonores.

	Plan du scénario: L'indexation rapide décode les sonores en aperçu et les fait sortir de l'aperçu
		Étant donné un fichier <fichier>
		Et un sonore à l'état « apercu » pour ce fichier
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « <apres> »

		Exemples:
			| fichier       | apres    |
			| mp3 sain      | actif    |
			| mp3 endommagé | errone   |
			| introuvable   | supprime |

	Scénario: Un sonore en aperçu reçoit sa durée et ses tags à l'indexation rapide
		Étant donné un fichier flac tagué
		Et un sonore à l'état « apercu » pour ce fichier
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « actif »
		Et sa durée en base est de 1 seconde à 0,05 seconde près
		Et en base, l'artiste est « Les Gaufres Électriques » et le titre « Café à minuit »

	Plan du scénario: L'indexation rapide ne décode pas les sonores qui ne sont pas en aperçu
		Étant donné un fichier <fichier>
		Et un sonore à l'état « <avant> » pour ce fichier
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « <avant> »
		Et le sonore n'a pas de durée en base
		Et rien n'est signalé sur la sortie d'erreur

		Exemples:
			| fichier       | avant     |
			| mp3 sain      | actif     |
			| mp3 endommagé | actif     |
			| mp3 sain      | errone    |
			| mp3 endommagé | desactive |

	Plan du scénario: L'indexation rapide repère quand même les fichiers disparus
		Étant donné un fichier introuvable
		Et un sonore à l'état « <avant> » pour ce fichier
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « <apres> »
		Et la sortie d'erreur signale ce fichier comme « introuvable », avec « <consequence> »

		Exemples:
			| avant     | apres     | consequence             |
			| actif     | supprime  | sonore passé supprimé   |
			| errone    | supprime  | sonore passé supprimé   |
			| desactive | desactive | état désactivé conservé |
			| expire    | expire    | état expiré conservé    |

	Scénario: L'audit complet fait aussi sortir les sonores de l'aperçu
		Étant donné un fichier mp3 sain
		Et un sonore à l'état « apercu » pour ce fichier
		Quand l'indexeur fait un audit complet
		Alors le sonore est à l'état « actif »
		Et le bilan indique « audit complet : 0 nouveau sonore, 0 rattachement ; 1 sonore vérifié ; 0 erroné, 0 supprimé, 0 rétabli, 1 sorti d'aperçu »

	Scénario: Le bilan de l'indexation rapide compte les sonores sortis de l'aperçu et les fichiers disparus
		Étant donné un fichier mp3 sain
		Et un sonore à l'état « apercu » pour ce fichier
		Et un deuxième fichier wav sain, dont le sonore est à l'état « actif »
		Et un troisième sonore, actif, dont le fichier a disparu
		Quand l'indexeur fait une indexation rapide
		Alors le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement ; 1 sonore vérifié ; 0 erroné, 1 supprimé, 0 rétabli, 1 sorti d'aperçu »

	Scénario: Machin_indexation propose l'audit complet en option
		Quand je lance "Machin_indexation" avec l'option "--help"
		Alors la sortie mentionne "--audit-complet"

	# ─── Fichiers modifiés (https://github.com/dascritch/machincast/issues/10) ─────

	Scénario: L'indexation rapide revérifie un fichier remplacé sous le même nom
		Étant donné un fichier flac sain
		Et un sonore à l'état « apercu » pour ce fichier
		Et l'indexeur a fait une indexation rapide
		Et ce fichier remplacé, sous le même nom, par un fichier flac tagué
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « actif »
		Et en base, l'artiste est « Les Gaufres Électriques » et le titre « Café à minuit »
		Et la date de modification et la taille du fichier sont enregistrées
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement ; 1 sonore vérifié ; 0 erroné, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Un fichier dont seule la date de modification a changé est aussi revérifié
		Étant donné un fichier flac sain
		Et un sonore à l'état « apercu » pour ce fichier
		Et l'indexeur a fait une indexation rapide
		Et ce fichier touché, sans changer son contenu
		Quand l'indexeur fait une indexation rapide
		Alors la date de modification et la taille du fichier sont enregistrées
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement ; 1 sonore vérifié ; 0 erroné, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Un fichier remplacé en gardant sa date de modification est revérifié, sa taille ayant changé
		Étant donné un fichier flac sain
		Et un sonore à l'état « apercu » pour ce fichier
		Et l'indexeur a fait une indexation rapide
		Et ce fichier remplacé, sous le même nom, par un fichier flac tagué, en gardant sa date de modification
		Quand l'indexeur fait une indexation rapide
		Alors en base, l'artiste est « Les Gaufres Électriques » et le titre « Café à minuit »

	Scénario: Un fichier déjà vérifié qui disparaît passe supprimé, sans compter comme vérifié
		Étant donné un fichier flac sain
		Et un sonore à l'état « apercu » pour ce fichier
		Et l'indexeur a fait une indexation rapide
		Et ce fichier supprimé
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « supprime »
		Et le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement ; 0 sonore vérifié ; 0 erroné, 1 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Un fichier inchangé depuis sa dernière vérification n'est pas redécodé
		Étant donné un fichier flac sain
		Et un sonore à l'état « apercu » pour ce fichier
		Et l'indexeur a fait une indexation rapide
		Quand l'indexeur fait une indexation rapide
		Alors le bilan indique « indexation rapide : 0 nouveau sonore, 0 rattachement ; 0 sonore vérifié ; 0 erroné, 0 supprimé, 0 rétabli, 0 sorti d'aperçu »

	Scénario: Un fichier remplacé par un fichier endommagé est signalé, et son sonore passe erroné
		Étant donné un fichier mp3 sain
		Et un sonore à l'état « apercu » pour ce fichier
		Et l'indexeur a fait une indexation rapide
		Et ce fichier remplacé, sous le même nom, par un fichier mp3 endommagé
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « errone »
		Et la sortie d'erreur signale ce fichier comme « endommagé », avec « sonore passé erroné »

	Plan du scénario: Un fichier remplacé garde les champs saisis à la main, et l'état que l'indexeur ne change pas
		Étant donné un fichier flac sain
		Et un sonore à l'état « apercu » pour ce fichier, dont le titre a été saisi à la main « Rediffusion du matin »
		Et l'indexeur a fait une indexation rapide
		Et le sonore est passé à l'état « <etat> »
		Et ce fichier remplacé, sous le même nom, par un fichier flac tagué
		Quand l'indexeur fait une indexation rapide
		Alors le sonore est à l'état « <etat> »
		Et en base, l'artiste est « Les Gaufres Électriques » et le titre « Rediffusion du matin »

		Exemples:
			| etat      |
			| actif     |
			| desactive |
			| expire    |
