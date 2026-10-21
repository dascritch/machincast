# language: fr
Fonctionnalité: Encarts dépliables et vérification complète dans la fiche d'un sonore
	En tant que programmateur musical,
	je veux une fiche de sonore plus compacte, et vérifier un fichier en entier depuis elle,
	afin de voir l'essentiel d'un coup d'œil, et de contrôler un fichier douteux sans auditer toute la discothèque.

	https://github.com/dascritch/machincast/issues/190, spec § 8.3. Les encarts « Métadonnées », « Diffusion », « Détection
	de blanc », « Relations » et « Fichier » sont repliés à l'ouverture de la fiche ; un clic sur leur titre les déplie.
	« Vérification complète », à côté de « Pré-écoute… », fait l'audit complet du fichier du sonore, en tâche de fond :
	le bouton attend la fin, puis une question propose de rafraîchir la fiche. Le décodage peut être retenu par le
	scénario, pour observer l'attente. Le fichier de test n'a pas de tags : l'audit complet efface le titre « Neige », que
	la fiche n'a pas marqué saisi à la main, et le sonore se nomme ensuite par son fichier. Un chemin qui commence par « …/ » est dans le répertoire temporaire du scénario.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et le fichier de test « sain.flac » copié en « …/jingles/neige.flac »
		Et les sonores :
			| artiste | titre  | type    | etat  | duree | emplacement                 |
			|         | Neige  | fichier | actif |       | …/jingles/neige.flac        |
			|         | Direct | stream  | actif |       | https://flux.exemple/direct |
		Et les événements :
			| nom         | nom_public | priorite    | debut | fin | jours |
			| Fil de jour |            | fil_musical |       |     |       |

	# ─── Encarts ───────────────────────────────────────────────

	Scénario: Les encarts secondaires d'un fichier sont repliés à l'ouverture de sa fiche
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Neige »
		Alors les encarts repliés de la fiche sont « Métadonnées », « Diffusion », « Détection de blanc », « Relations », « Fichier »
		Et les encarts dépliés de la fiche sont « Sonore », « Derniers passages »
		Et l'encart « Fichier » a pour titre « ▸ Fichier », et cache la dernière vérification complète

	Scénario: Un clic sur le titre d'un encart le déplie, un autre le replie
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Neige »
		Et je clique sur le titre de l'encart « Fichier »
		Alors les encarts repliés de la fiche sont « Métadonnées », « Diffusion », « Détection de blanc », « Relations »
		Et l'encart « Fichier » a pour titre « ▾ Fichier », et montre la dernière vérification complète
		Et la fiche montre la dernière vérification complète « jamais »
		Quand je clique dans l'encart « Fichier », sous son titre
		Alors les encarts repliés de la fiche sont « Métadonnées », « Diffusion », « Détection de blanc », « Relations »
		Quand je clique sur le titre de l'encart « Fichier »
		Alors les encarts repliés de la fiche sont « Métadonnées », « Diffusion », « Détection de blanc », « Relations », « Fichier »
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont inactifs

	Scénario: La fiche d'un stream n'a ni « Fichier » ni « Détection de blanc », et replie les autres
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Alors les encarts repliés de la fiche sont « Métadonnées », « Diffusion », « Relations »
		Et les encarts dépliés de la fiche sont « Sonore », « Stream », « Derniers passages »

	# ─── Vérification complète ─────────────────────────────────

	Scénario: La vérification complète attend sa fin, puis propose de rafraîchir la fiche
		Étant donné la vérification complète retenue par le scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Neige »
		Alors le bouton « Vérification complète » de la fiche est actif
		Quand je clique sur « Vérification complète »
		Alors le bouton « Vérification… » de la fiche est inactif
		Et la fiche signale « Vérification complète en cours… »
		Quand la vérification complète se termine
		Alors la question après la vérification a dit « Vérification terminée : neige.flac, actif. Rafraîchir la fiche ? »
		Et le bouton « Vérification complète » de la fiche est actif
		Et la fiche ne signale rien
		Et la fiche montre une dernière vérification complète datée
		Et le sonore du fichier « …/jingles/neige.flac » a été vérifié en entier, ses blancs mesurés

	Scénario: Refuser de rafraîchir laisse la fiche telle quelle
		Étant donné la vérification complète retenue par le scénario
		Et le refus de rafraîchir la fiche après la vérification
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Neige »
		Et je clique sur « Vérification complète »
		Et la vérification complète se termine
		Alors la question après la vérification a dit « Vérification terminée : neige.flac, actif. Rafraîchir la fiche ? »
		Et la fiche montre la dernière vérification complète « jamais »
		Et la fiche ne signale rien
		Et le bouton « Vérification complète » de la fiche est actif
		Et le sonore du fichier « …/jingles/neige.flac » a été vérifié en entier, ses blancs mesurés

	Scénario: Seule la fiche du sonore vérifié propose de se rafraîchir
		Étant donné la vérification complète retenue par le scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Neige »
		Et je clique sur « Vérification complète »
		Et j'ouvre la fiche du sonore « Direct »
		Et la vérification complète se termine
		Alors la question après la vérification a dit « Vérification terminée : neige.flac, actif. Rafraîchir la fiche ? »
		Et la barre d'état annonce « Vérification terminée : neige.flac, actif. »

	Scénario: Une fiche fermée pendant la vérification ne pose pas de question
		Étant donné la vérification complète retenue par le scénario
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Neige »
		Et je clique sur « Vérification complète »
		Et je ferme l'onglet « Sonore : Neige »
		Et la vérification complète se termine
		Alors aucune question n'a été posée
		Et le sonore du fichier « …/jingles/neige.flac » a été vérifié en entier, ses blancs mesurés

	Scénario: Un stream ne se vérifie pas
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Direct »
		Alors le bouton « Vérification complète » de la fiche est inactif
