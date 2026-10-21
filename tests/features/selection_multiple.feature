# language: fr
Fonctionnalité: Sélection multiple dans les listes des sonores et des banques
	En tant que programmateur musical,
	je veux sélectionner plusieurs sonores ou plusieurs banques à la fois,
	afin de changer en une fois leur état, leurs banques, leur masquage ou de demander leur audit complet.

	https://github.com/dascritch/machincast/issues/114, spec § 8.2. Ctrl et Maj sélectionnent plusieurs lignes des listes
	Sonores et Banques ; le clic droit propose les actions sur la sélection. Chaque action demande confirmation, écrit
	en base, relit la liste et l'annonce dans la barre d'état. Un sonore en aperçu garde son état. Un audit complet
	demandé est fait par la prochaine indexation, même rapide (audit_demande.feature).

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et les sonores :
			| artiste     | titre         | type    | etat      | duree | emplacement                  |
			| Les Gaufres | Café à minuit | fichier | actif     | 214   | /srv/musique/cafe.flac       |
			| Les Gaufres | Gaufre royale | fichier | desactive | 180   | /srv/musique/royale.flac     |
			| Les Gaufres | Nouveauté     | fichier | apercu    |       | /srv/musique/nouveaute.flac  |
			|             | Jingle        | fichier | actif     | 5     | /srv/habillage/jingle.flac   |
			|             | Direct        | stream  | actif     |       | https://flux.exemple/direct  |
		Et la banque « Titres », aléatoire, sans nom public, avec « Café à minuit », « Gaufre royale »
		Et la banque « Habillage », séquentielle, sans nom public, avec « Jingle »
		Et la banque « Nuit », aléatoire, sans nom public, avec « Gaufre royale »
		Et les événements :
			| nom         | nom_public | priorite    | debut | fin | jours |
			| Fil de jour |            | fil_musical |       |     |       |

	# ─── Sonores ───────────────────────────────────────────────

	Scénario: Plusieurs sonores se sélectionnent, et le clic droit propose les actions sur la sélection
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je sélectionne les lignes « Café à minuit », « Gaufre royale » de la liste
		Alors le clic droit sur la sélection propose « Activer », « Désactiver », « Ajouter à des banques… », « Retirer de banques… », « Demander un audit complet »

	Scénario: Désactiver plusieurs sonores, après confirmation
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je sélectionne les lignes « Café à minuit », « Jingle », « Nouveauté » de la liste
		Et je choisis « Désactiver » au clic droit sur la sélection
		Alors la dernière question, intitulée « Désactiver », a dit « Désactiver 3 sonores ? Un sonore en aperçu reste en aperçu. »
		Et les sonores « Café à minuit », « Jingle » sont à l'état « desactive » en base
		Et le sonore « Nouveauté » est à l'état « apercu » en base
		Et la barre d'état annonce « 2 sonores désactivés. »
		Et la liste montre les titres « Café à minuit », « Gaufre royale », « Nouveauté », « Direct », « Jingle »
		Et la liste montre l'état « désactivé » pour « Café à minuit » et « Jingle »

	Scénario: Activer plusieurs sonores
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je sélectionne les lignes « Café à minuit », « Gaufre royale » de la liste
		Et je choisis « Activer » au clic droit sur la sélection
		Alors les sonores « Café à minuit », « Gaufre royale » sont à l'état « actif » en base
		Et la barre d'état annonce « 1 sonore activé. »

	Scénario: Une confirmation refusée ne change rien
		Étant donné les confirmations d'action refusées
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je sélectionne les lignes « Café à minuit », « Jingle » de la liste
		Et je choisis « Désactiver » au clic droit sur la sélection
		Alors les sonores « Café à minuit », « Jingle » sont à l'état « actif » en base
		Et la barre d'état n'a rien annoncé

	Scénario: Le clic droit hors de la sélection agit sur la seule ligne cliquée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je sélectionne les lignes « Café à minuit », « Jingle » de la liste
		Et je choisis « Désactiver » au clic droit sur la ligne « Gaufre royale »
		Alors la dernière question, intitulée « Désactiver », a dit « Désactiver 1 sonore ? Un sonore en aperçu reste en aperçu. »
		Et les sonores « Café à minuit », « Jingle » sont à l'état « actif » en base

	Scénario: Ajouter plusieurs sonores à des banques, à la fin de leur liste, sans doublon
		Étant donné les banques choisies « Titres », « Habillage »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je sélectionne les lignes « Gaufre royale », « Jingle » de la liste
		Et je choisis « Ajouter à des banques… » au clic droit sur la sélection
		Alors la dernière question, intitulée « Ajouter à des banques », a dit « Ajouter 2 sonores aux banques « Titres », « Habillage » ? Un sonore déjà dans une banque n'y est pas ajouté une seconde fois. »
		Et les sonores de la banque « Titres » sont, dans l'ordre, « Café à minuit », « Gaufre royale », « Jingle »
		Et les sonores de la banque « Habillage » sont, dans l'ordre, « Jingle », « Gaufre royale »
		Et la barre d'état annonce « 2 sonores ajoutés à 2 banques. »

	Scénario: Retirer plusieurs sonores des banques choisies parmi les leurs
		Étant donné les banques choisies « Titres », « Nuit »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je sélectionne les lignes « Café à minuit », « Gaufre royale » de la liste
		Et je choisis « Retirer de banques… » au clic droit sur la sélection
		Alors le choix des banques a proposé « Nuit », « Titres »
		Et la dernière question, intitulée « Retirer de banques », a dit « Retirer 2 sonores des banques « Titres », « Nuit » ? Un sonore dont le fichier est dans un répertoire d'une banque y reviendra à la prochaine indexation. »
		Et les sonores de la banque « Titres » sont, dans l'ordre, aucun
		Et les sonores de la banque « Nuit » sont, dans l'ordre, aucun
		Et les sonores de la banque « Habillage » sont, dans l'ordre, « Jingle »
		Et la barre d'état annonce « 2 sonores retirés de 2 banques. »

	Scénario: Abandonner le choix des banques ne change rien
		Étant donné les banques choisies aucune
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je sélectionne les lignes « Café à minuit » de la liste
		Et je choisis « Ajouter à des banques… » au clic droit sur la sélection
		Alors aucune question n'a été posée
		Et la barre d'état n'a rien annoncé

	Scénario: Demander l'audit complet de plusieurs sonores, jamais d'un stream
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je sélectionne les lignes « Café à minuit », « Gaufre royale », « Direct » de la liste
		Et je choisis « Demander un audit complet » au clic droit sur la sélection
		Alors la dernière question, intitulée « Demander un audit complet », a dit « Demander l'audit complet de 3 sonores ? La prochaine indexation, même rapide, les revérifiera en entier. »
		Et l'audit complet est demandé pour les sonores « Café à minuit », « Gaufre royale », et pas pour « Jingle »
		Et la liste montre l'état « actif, audit demandé » pour « Café à minuit »
		Et la barre d'état annonce « Audit complet demandé pour 2 sonores, à la prochaine indexation. »

	Scénario: Demander l'audit complet d'un seul sonore
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je choisis « Demander un audit complet » au clic droit sur la ligne « Jingle »
		Alors la dernière question, intitulée « Demander un audit complet », a dit « Demander l'audit complet de 1 sonore ? La prochaine indexation, même rapide, le revérifiera en entier. »
		Et la barre d'état annonce « Audit complet demandé pour 1 sonore, à la prochaine indexation. »

	Plan du scénario: Seules les banques qui changent comptent dans l'annonce, et une seule banque se dit au singulier
		Étant donné les banques choisies <banques>
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je choisis « <action> » au clic droit sur la ligne « Café à minuit »
		Alors la dernière question, intitulée « <titre> », a dit « <question> »
		Et la barre d'état annonce « <annonce> »

		Exemples:
			| banques                  | action                 | titre                | question                                                                                                                            | annonce                          |
			| « Titres », « Habillage » | Ajouter à des banques… | Ajouter à des banques | Ajouter 1 sonore aux banques « Titres », « Habillage » ? Un sonore déjà dans une banque n'y est pas ajouté une seconde fois.        | 1 sonore ajouté à 1 banque.      |
			| « Nuit »                 | Ajouter à des banques… | Ajouter à des banques | Ajouter 1 sonore à la banque « Nuit » ? Un sonore déjà dans une banque n'y est pas ajouté une seconde fois.                         | 1 sonore ajouté à 1 banque.      |
			| « Titres »               | Retirer de banques…    | Retirer de banques    | Retirer 1 sonore de la banque « Titres » ? Un sonore dont le fichier est dans un répertoire d'une banque y reviendra à la prochaine indexation. | 1 sonore retiré de 1 banque. |

	# ─── Banques ───────────────────────────────────────────────

	Scénario: Plusieurs banques se sélectionnent ; « Dupliquer » ne vaut que pour une seule
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je sélectionne les lignes « Titres », « Nuit » de la liste
		Alors le clic droit sur la sélection propose « Demander l'audit complet de leurs sonores », « Masquer l'artiste et le titre », « Afficher l'artiste et le titre », « Artiste et titre hérités du sonore »
		Quand je sélectionne les lignes « Titres » de la liste
		Alors le clic droit sur la sélection propose « Dupliquer », « Demander l'audit complet de leurs sonores », « Masquer l'artiste et le titre », « Afficher l'artiste et le titre », « Artiste et titre hérités du sonore »

	Scénario: Demander l'audit complet des sonores de plusieurs banques
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je sélectionne les lignes « Titres », « Nuit » de la liste
		Et je choisis « Demander l'audit complet de leurs sonores » au clic droit sur la sélection
		Alors la dernière question, intitulée « Demander l'audit complet de leurs sonores », a dit « Demander l'audit complet des sonores de 2 banques ? La prochaine indexation, même rapide, les revérifiera en entier. »
		Et l'audit complet est demandé pour les sonores « Café à minuit », « Gaufre royale », et pas pour « Jingle »
		Et la barre d'état annonce « Audit complet demandé pour 2 sonores, à la prochaine indexation. »

	Plan du scénario: Masquer, afficher, ou laisser au sonore l'artiste et le titre de plusieurs banques
		Étant donné le masquage « masqués » de la banque « Titres » et « affichés » de la banque « Nuit »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Banques »
		Et je sélectionne les lignes « Titres », « Nuit » de la liste
		Et je choisis « <action> » au clic droit sur la sélection
		Alors la dernière question, intitulée « <action> », a dit « <question> »
		Et le masquage des banques « Titres », « Nuit » est « <masquage> » en base, et celui de « Habillage » « hérité »
		Et la barre d'état annonce « <annonce> »

		Exemples:
			| action                              | question                                                              | masquage | annonce                                           |
			| Masquer l'artiste et le titre       | Masquer l'artiste et le titre des sonores de 2 banques ?              | masqués  | Artiste et titre masqués pour 2 banques.          |
			| Afficher l'artiste et le titre      | Afficher l'artiste et le titre des sonores de 2 banques ?             | affichés | Artiste et titre affichés pour 2 banques.         |
			| Artiste et titre hérités du sonore  | Laisser au sonore le masquage de l'artiste et du titre de 2 banques ? | hérité   | Artiste et titre hérités du sonore pour 2 banques. |

	# ─── Fiche d'une banque ────────────────────────────────────

	Scénario: Dans la fiche d'une banque, l'état choisi pour plusieurs sonores s'écrit à l'enregistrement
		Étant donné la banque « Nouveautés », aléatoire, sans nom public, avec « Café à minuit », « Nouveauté », « Gaufre royale »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Nouveautés »
		Alors les sonores de la fiche sont, avec leur état, « Les Gaufres – Café à minuit » actif, « Les Gaufres – Nouveauté » aperçu, « Les Gaufres – Gaufre royale » désactivé
		Quand je sélectionne les sonores « Les Gaufres – Café à minuit », « Les Gaufres – Nouveauté » de la fiche
		Et je choisis « Désactiver » au clic droit sur les sonores choisis de la fiche
		Alors les sonores de la fiche sont, avec leur état, « Les Gaufres – Café à minuit » désactivé, « Les Gaufres – Nouveauté » aperçu, « Les Gaufres – Gaufre royale » désactivé
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs
		Et le sonore « Café à minuit » est à l'état « actif » en base
		Quand j'enregistre la fiche
		Alors le sonore « Café à minuit » est à l'état « desactive » en base
		Et le sonore « Nouveauté » est à l'état « apercu » en base
		Et les sonores de la fiche sont, avec leur état, « Les Gaufres – Café à minuit » désactivé, « Les Gaufres – Nouveauté » aperçu, « Les Gaufres – Gaufre royale » désactivé

	Scénario: Annuler oublie l'état choisi pour des sonores de la fiche
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Titres »
		Et je sélectionne les sonores « Les Gaufres – Café à minuit », « Les Gaufres – Gaufre royale » de la fiche
		Et je choisis « Activer » au clic droit sur les sonores choisis de la fiche
		Alors les sonores de la fiche sont, avec leur état, « Les Gaufres – Café à minuit » actif, « Les Gaufres – Gaufre royale » actif
		Quand j'annule les modifications de la fiche
		Alors les sonores de la fiche sont, avec leur état, « Les Gaufres – Café à minuit » actif, « Les Gaufres – Gaufre royale » désactivé
		Et le sonore « Gaufre royale » est à l'état « desactive » en base

	Scénario: Un sonore repassé en aperçu entre-temps y reste, malgré l'état choisi dans la fiche
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Titres »
		Et je choisis « Désactiver » au clic droit sur le sonore « Les Gaufres – Café à minuit » de la fiche
		Et le sonore « Café à minuit » repasse en aperçu en base
		Et j'enregistre la fiche
		Alors le sonore « Café à minuit » est à l'état « apercu » en base

	Scénario: Le clic droit hors des sonores choisis de la fiche n'agit que sur la ligne cliquée
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Titres »
		Et je sélectionne les sonores « Les Gaufres – Café à minuit » de la fiche
		Et je choisis « Désactiver » au clic droit sur le sonore « Les Gaufres – Gaufre royale » de la fiche
		Alors les sonores de la fiche sont, avec leur état, « Les Gaufres – Café à minuit » actif, « Les Gaufres – Gaufre royale » désactivé
		Et les boutons « Enregistrer » et « Annuler » de la fiche sont actifs

	Scénario: Plusieurs sonores de la fiche se retirent d'un coup ; « Monter » et « Descendre » ne servent qu'à un seul
		Étant donné la banque « Matin », séquentielle, sans nom public, avec « Café à minuit », « Gaufre royale », « Jingle »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Matin »
		Et je sélectionne les sonores « Les Gaufres – Café à minuit », « Jingle » de la fiche
		Alors seul « Retirer le sonore » sert aux sonores choisis de la fiche
		Quand je clique sur « Retirer le sonore »
		Alors les sonores de la fiche sont, avec leur état, « Les Gaufres – Gaufre royale » désactivé
		Et aucune question n'a été posée
		Quand j'enregistre la fiche
		Alors les sonores de la banque « Matin » sont, dans l'ordre, « Gaufre royale »

	Plan du scénario: Retirer plusieurs sonores des répertoires de la banque les nomme tous, en un seul avertissement
		Étant donné la banque « Matin », séquentielle, sans nom public, avec « Café à minuit », « Gaufre royale », « Jingle »
		Et les répertoires « /srv/musique » de la banque « Matin »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Matin »
		Et je réponds « <reponse> » à l'avertissement de réintégration
		Et je sélectionne les sonores « Les Gaufres – Café à minuit », « Les Gaufres – Gaufre royale », « Jingle » de la fiche
		Et je clique sur « Retirer le sonore »
		Alors l'avertissement de réintégration a dit « « Les Gaufres – Café à minuit », « Les Gaufres – Gaufre royale » sont des fichiers du répertoire /srv/musique, indexé par cette banque : la prochaine indexation les y remettra. Pour les écarter pour de bon, déplacez leurs fichiers hors de ces répertoires, en dehors de MachinCast. »
		Et les sonores de la fiche sont, avec leur état, <sonores>
		Et le navigateur de fichiers a ouvert <dossier>

		Exemples:
			| reponse            | sonores                                                                                     | dossier            |
			| Retirer quand même | aucun                                                                                       | aucun dossier      |
			| Annuler            | « Les Gaufres – Café à minuit » actif, « Les Gaufres – Gaufre royale » désactivé, « Jingle » actif | aucun dossier      |
			| Ouvrir le dossier  | « Les Gaufres – Café à minuit » actif, « Les Gaufres – Gaufre royale » désactivé, « Jingle » actif | « /srv/musique »   |

	Scénario: Retirer un seul sonore d'un répertoire de la banque garde l'avertissement d'un sonore
		Étant donné la banque « Matin », séquentielle, sans nom public, avec « Café à minuit », « Jingle »
		Et les répertoires « /srv/musique » de la banque « Matin »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Matin »
		Et je réponds « Annuler » à l'avertissement de réintégration
		Et je sélectionne les sonores « Les Gaufres – Café à minuit » de la fiche
		Et je clique sur « Retirer le sonore »
		Alors l'avertissement de réintégration a dit « « Les Gaufres – Café à minuit » est un fichier du répertoire /srv/musique, indexé par cette banque : la prochaine indexation l'y remettra. Pour l'écarter pour de bon, déplacez son fichier hors de ce répertoire, en dehors de MachinCast. »

	Scénario: Des sonores de plusieurs répertoires de la banque les nomment tous ; « Ouvrir le dossier » ouvre celui du premier
		Étant donné la banque « Matin », séquentielle, sans nom public, avec « Jingle », « Café à minuit »
		Et les répertoires « /srv/musique », « /srv/habillage » de la banque « Matin »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Matin »
		Et je réponds « Ouvrir le dossier » à l'avertissement de réintégration
		Et je sélectionne les sonores « Jingle », « Les Gaufres – Café à minuit » de la fiche
		Et je clique sur « Retirer le sonore »
		Alors l'avertissement de réintégration a dit « « Jingle », « Les Gaufres – Café à minuit » sont des fichiers des répertoires /srv/habillage, /srv/musique, indexés par cette banque : la prochaine indexation les y remettra. Pour les écarter pour de bon, déplacez leurs fichiers hors de ces répertoires, en dehors de MachinCast. »
		Et le navigateur de fichiers a ouvert « /srv/habillage »

	# ─── Autres listes ─────────────────────────────────────────

	Scénario: Les autres listes ne sélectionnent qu'une ligne à la fois
		Quand la fenêtre de l'interface s'ouvre
		Alors les listes qui sélectionnent plusieurs lignes sont « Banques », « Sonores »
