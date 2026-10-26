# language: fr
Fonctionnalité: Suppression d'un élément, après confirmation qui rappelle où il figure
	En tant que programmateur de l'antenne,
	je veux que la suppression d'un élément utilisé ailleurs me demande confirmation en listant où il figure,
	afin que je ne casse pas la grille par inadvertance.

	https://github.com/dascritch/machincast/issues/33, spec § 8.9. Chaque fiche a un bouton « Supprimer… », qui demande
	toujours confirmation. Supprimer un élément le retire des listes où il figure : jamais un fichier sonore ni un
	répertoire, qui restent à leur place, intacts (https://github.com/dascritch/machincast/issues/96). L'historique de
	diffusion garde ses passages. Un sonore, une banque, une séquence ou un événement supprimé reste en base, marqué
	« supprimé », hors des listes et de la recherche, jusqu'à sa péremption : sa fiche se rouvre depuis l'historique,
	et se restaure (https://github.com/dascritch/machincast/issues/267). Un feed quitte la base. Un chemin qui commence
	par « …/ » est dans le répertoire temporaire du scénario.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 15:30:00 »
		Et les dossiers « …/pubs », « …/habillage » du scénario
		Et les fichiers « …/pubs/spot.flac », « …/habillage/debut.flac », « …/ailleurs/isole.flac » du scénario
		Et les sonores :
			| artiste     | titre        | type    | etat  | duree | emplacement             |
			|             | Jingle début | fichier | actif | 5     | …/habillage/debut.flac  |
			| Les Gaufres | Spot         | fichier | actif | 30    | …/pubs/spot.flac        |
			|             | Isolé        | fichier | actif | 12    | …/ailleurs/isole.flac   |
			|             | Radio Thune  | stream  | actif |       | https://flux.exemple/rt |
			|             | Radio Machin | stream  | actif |       | https://flux.exemple/rm |
			|             | Radio Ondes  | stream  | actif |       | https://flux.exemple/ro |
		Et la banque « Publicité », aléatoire, sans nom public, avec « Spot »
		Et les répertoires « …/pubs » de la banque « Publicité »
		Et la banque « Habillage », séquentielle, sans nom public, avec « Jingle début »
		Et les répertoires « …/habillage » de la banque « Habillage »
		Et la séquence « Passage pub », sans nom public, avec le sonore « Jingle début », la banque « Publicité »
		Et la séquence « Pub seule », sans nom public, avec la banque « Publicité »
		Et les événements :
			| nom      | nom_public | priorite    | debut            | fin              | jours |
			| Continue |            | fil_musical |                  |                  |       |
			| Matinale |            | emission    | 2026-10-19 07:00 | 2026-10-19 09:00 | lundi |
			| Midi     |            | emission    | 2026-10-19 12:00 | 2026-10-19 13:00 | lundi |
			| Panne    |            | secours     |                  |                  |       |
			| Coupure  |            | secours     |                  |                  |       |
		Et l'événement « Matinale » joue la banque « Habillage », la séquence « Passage pub », le sonore « Spot »
		Et l'événement « Continue » joue la banque « Habillage »
		Et l'événement « Midi » joue la banque « Publicité »
		Et l'événement « Panne » joue le sonore « Isolé »
		Et le stream « Radio Thune » a pour événement de secours « Panne »
		Et le stream « Radio Machin » a pour événement de secours « Panne »
		Et le stream « Radio Ondes » a pour événement de secours « Coupure »
		Et « Spot » qui est passé à l'antenne pendant « Matinale »

	# ─── Sonore ────────────────────────────────────────────────

	Scénario: Un sonore supprimé quitte la base et les listes, mais son fichier reste en place, intact
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Spot »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la question de suppression, intitulée « Supprimer le sonore », a dit :
			| texte                                                                                                                                                                                       |
			| Supprimer le sonore « Les Gaufres – Spot » ?                                                                                                                                                |
			| Il en sera retiré :                                                                                                                                                                         |
			| • de la banque « Publicité », qui n'aura plus aucun sonore ;                                                                                                                                |
			| • de l'événement « Matinale ».                                                                                                                                                              |
			| Son fichier reste à sa place, intact : …/pubs/spot.flac. Il est dans un répertoire de la banque « Publicité » : la prochaine indexation l'enregistrera de nouveau, comme un nouveau sonore. |
			| L'historique de diffusion garde ses passages.                                                                                                                                               |
			| Marqué « supprimé », il se restaure depuis sa fiche.                                                                                                                                        |
		Et le sonore « Spot » est marqué « supprimé » en base
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Incidents »
		Et la liste en base de la banque « Publicité » est rien
		Et la liste en base de l'événement « Matinale » est « Habillage », « Passage pub »
		Et l'historique de diffusion garde le passage de « Les Gaufres – Spot », à l'emplacement « …/pubs/spot.flac »
		Et les fichiers du scénario sont intacts
		Quand j'ouvre l'onglet « Sonores »
		Alors la liste montre les titres « Isolé », « Jingle début », « Radio Machin », « Radio Ondes », « Radio Thune »

	Plan du scénario: Un sonore qui ne figure nulle part est supprimé après confirmation aussi, et se nomme comme il peut
		Étant donné les sonores :
			| artiste   | titre   | type    | etat  | duree | emplacement   |
			| <artiste> | <titre> | fichier | actif | 3     | <emplacement> |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « <ouvert> »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la question de suppression, intitulée « Supprimer le sonore », a dit :
			| texte                                                                |
			| Supprimer le sonore « <nom> » ?                                      |
			| Il ne figure dans aucune banque, aucune séquence ni aucun événement. |
			| Son fichier reste à sa place, intact : <emplacement>.                |
			| L'historique de diffusion garde ses passages.                        |
			| Marqué « supprimé », il se restaure depuis sa fiche.                 |
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Incidents »

		Exemples:
			| artiste | titre  | emplacement                 | ouvert                      | nom             |
			|         | Oublié | /srv/divers/oublie.flac     | Oublié                      | Oublié          |
			| Anonyme |        | /srv/divers/anonyme.flac    | /srv/divers/anonyme.flac    | Anonyme         |
			|         |        | /srv/divers/sans-titre.flac | /srv/divers/sans-titre.flac | sans-titre.flac |

	Scénario: Un sonore d'une séquence la laisse vide, et un stream n'a pas de fichier
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Isolé »
		Et je supprime l'élément de la fiche, en répondant « Annuler »
		Alors la question de suppression, intitulée « Supprimer le sonore », a dit :
			| texte                                                         |
			| Supprimer le sonore « Isolé » ?                               |
			| Il en sera retiré :                                           |
			| • de l'événement « Panne », qui n'aura plus rien à jouer.     |
			| Son fichier reste à sa place, intact : …/ailleurs/isole.flac. |
			| L'historique de diffusion garde ses passages.                 |
			| Marqué « supprimé », il se restaure depuis sa fiche.          |
		Quand j'ouvre la fiche du sonore « Jingle début »
		Et je supprime l'élément de la fiche, en répondant « Annuler »
		Alors la dernière question de suppression a dit :
			| texte                                                                                                                                                                                             |
			| Supprimer le sonore « Jingle début » ?                                                                                                                                                            |
			| Il en sera retiré :                                                                                                                                                                               |
			| • de la banque « Habillage », qui n'aura plus aucun sonore ;                                                                                                                                      |
			| • de la séquence « Passage pub ».                                                                                                                                                                 |
			| Son fichier reste à sa place, intact : …/habillage/debut.flac. Il est dans un répertoire de la banque « Habillage » : la prochaine indexation l'enregistrera de nouveau, comme un nouveau sonore. |
			| L'historique de diffusion garde ses passages.                                                                                                                                                     |
			| Marqué « supprimé », il se restaure depuis sa fiche.                                                                                                                                              |
		Quand j'ouvre la fiche du sonore « Radio Thune »
		Et je supprime l'élément de la fiche, en répondant « Annuler »
		Alors la dernière question de suppression a dit :
			| texte                                                                |
			| Supprimer le sonore « Radio Thune » ?                                |
			| Il ne figure dans aucune banque, aucune séquence ni aucun événement. |
			| L'historique de diffusion garde ses passages.                        |
			| Marqué « supprimé », il se restaure depuis sa fiche.                 |

	Scénario: Renoncer à la suppression ne change rien, et la fiche reste ouverte
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Spot »
		Et je supprime l'élément de la fiche, en répondant « Annuler »
		Alors la liste en base de la banque « Publicité » est « Spot »
		Et l'onglet ouvert est « Sonore : Spot »

	# ─── Banque ────────────────────────────────────────────────

	Scénario: Une banque supprimée quitte la base et les listes, mais ses répertoires, leurs fichiers et ses sonores restent
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Publicité »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la question de suppression, intitulée « Supprimer la banque », a dit :
			| texte                                                                                                     |
			| Supprimer la banque « Publicité » ?                                                                       |
			| Elle en sera retirée :                                                                                    |
			| • de la séquence « Passage pub » ;                                                                        |
			| • de la séquence « Pub seule », qui n'aura plus aucun élément ;                                           |
			| • de l'événement « Midi », qui n'aura plus rien à jouer.                                                  |
			| Ses répertoires restent à leur place, avec leurs fichiers, intacts : …/pubs. Ses sonores restent en base. |
			| L'historique de diffusion garde ses passages.                                                             |
			| Marquée « supprimée », elle se restaure depuis sa fiche.                                                  |
		Et la banque « Publicité » est marquée « supprimée » en base
		Et la liste en base de la séquence « Passage pub » est « Jingle début »
		Et la liste en base de la séquence « Pub seule » est rien
		Et la liste en base de l'événement « Midi » est rien
		Et le sonore « Spot » est toujours en base
		Et le dossier « …/pubs » est toujours là
		Et les fichiers du scénario sont intacts

	Scénario: Une banque sans répertoire ni liste qui la contienne se supprime aussi
		Étant donné la banque « Vide », séquentielle, sans nom public, avec « Isolé »
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Vide »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la question de suppression, intitulée « Supprimer la banque », a dit :
			| texte                                                    |
			| Supprimer la banque « Vide » ?                           |
			| Elle ne figure dans aucune séquence ni aucun événement.  |
			| Ses sonores restent en base.                             |
			| L'historique de diffusion garde ses passages.            |
			| Marquée « supprimée », elle se restaure depuis sa fiche. |
		Et la banque « Vide » est marquée « supprimée » en base
		Et le sonore « Isolé » est toujours en base

	# ─── Séquence ──────────────────────────────────────────────

	Scénario: Une séquence supprimée quitte la base et les événements, mais ses éléments restent en base
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la question de suppression, intitulée « Supprimer la séquence », a dit :
			| texte                                                    |
			| Supprimer la séquence « Passage pub » ?                  |
			| Elle en sera retirée :                                   |
			| • de l'événement « Matinale ».                           |
			| Ses sonores et ses banques restent en base.              |
			| L'historique de diffusion garde ses passages.            |
			| Marquée « supprimée », elle se restaure depuis sa fiche. |
		Et la séquence « Passage pub » est marquée « supprimée » en base
		Et la liste en base de l'événement « Matinale » est « Habillage », « Spot »
		Et la banque « Publicité » est toujours en base

	# ─── Événement ─────────────────────────────────────────────

	Scénario: Un événement supprimé quitte la base, sa liste avec lui, et les streams qu'il secourait n'ont plus de secours
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Panne »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la question de suppression, intitulée « Supprimer l'événement », a dit :
			| texte                                                                                                    |
			| Supprimer l'événement « Panne » ?                                                                        |
			| Il est l'événement de secours des streams « Radio Machin », « Radio Thune », qui n'en auront plus.       |
			| Il ne joue plus ; sa liste de lecture reste avec lui. Ses sonores, banques et séquences restent en base. |
			| L'historique de diffusion garde ses passages.                                                            |
			| Marqué « supprimé », il se restaure depuis sa fiche.                                                     |
		Et l'événement « Panne » est marqué « supprimé » en base
		Et le stream « Radio Thune » n'a plus d'événement de secours
		Et le stream « Radio Machin » n'a plus d'événement de secours
		Et le sonore « Isolé » est toujours en base
		Quand j'ouvre la fiche de l'événement « Coupure »
		Et je supprime l'élément de la fiche, en répondant « Annuler »
		Alors la dernière question de suppression a dit :
			| texte                                                                                                    |
			| Supprimer l'événement « Coupure » ?                                                                      |
			| Il est l'événement de secours du stream « Radio Ondes », qui n'en aura plus.                             |
			| Il ne joue plus ; sa liste de lecture reste avec lui. Ses sonores, banques et séquences restent en base. |
			| L'historique de diffusion garde ses passages.                                                            |
			| Marqué « supprimé », il se restaure depuis sa fiche.                                                     |

	Scénario: Un événement de la grille supprimé laisse l'historique de diffusion intact
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la question de suppression, intitulée « Supprimer l'événement », a dit :
			| texte                                                                                                    |
			| Supprimer l'événement « Matinale » ?                                                                     |
			| Il ne joue plus ; sa liste de lecture reste avec lui. Ses sonores, banques et séquences restent en base. |
			| L'historique de diffusion garde ses passages.                                                            |
			| Marqué « supprimé », il se restaure depuis sa fiche.                                                     |
		Et l'événement « Matinale » est marqué « supprimé » en base
		Et l'historique de diffusion garde le passage de « Les Gaufres – Spot », à l'emplacement « …/pubs/spot.flac »

	# ─── Suppression différée (https://github.com/dascritch/machincast/issues/267) ───

	Scénario: Un élément supprimé n'est plus proposé : ni dans les listes, ni dans la recherche, ni dans le choix des sonores
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Isolé »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Et j'ouvre la fiche de la banque « Publicité »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Et j'ouvre l'onglet « Sonores »
		Alors la liste montre les titres « Spot », « Jingle début », « Radio Machin », « Radio Ondes », « Radio Thune »
		Quand j'ouvre l'onglet « Banques »
		Alors la liste montre les noms « Habillage »
		Et la recherche de « Isolé » ne trouve rien
		Et la recherche de « Publicité » ne trouve rien
		Et le choix des sonores d'une banque ne propose pas « Isolé »

	Scénario: La fiche d'un sonore supprimé se rouvre depuis l'historique, marquée « Supprimé », sans se modifier, puis se restaure
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Spot »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Et j'ouvre depuis l'historique la fiche du sonore « Spot »
		Alors l'onglet ouvert est « Sonore : Spot »
		Et la fiche signale « Supprimé le 19/10/2026 à 15:30 : « Restaurer » le remet en service. »
		Et les champs de la fiche ne se modifient pas
		Et la fiche propose « Restaurer », pas « Supprimer… »
		Quand je clique sur « Restaurer »
		Alors le sonore « Spot » est toujours en base
		Et la fiche ne signale rien
		Et les champs de la fiche se modifient
		Et la fiche propose « Supprimer… », pas « Restaurer »
		Et la liste en base de la banque « Publicité » est rien
		Quand j'ouvre l'onglet « Sonores »
		Alors la liste montre les titres « Spot », « Isolé », « Jingle début », « Radio Machin », « Radio Ondes », « Radio Thune »

	Plan du scénario: Une banque, une séquence ou un événement supprimé se restaure aussi, marqué au féminin ou au masculin
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche <de> « <nom> »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Et j'ouvre depuis l'historique la fiche <de> « <nom> »
		Alors la fiche signale « <marque> le 19/10/2026 à 15:30 : « Restaurer » <pronom> remet en service. »
		Quand je clique sur « Restaurer »
		Alors <genre> « <nom> » est toujours en base

		Exemples:
			| de             | genre       | nom         | marque    | pronom |
			| de la banque   | la banque   | Habillage   | Supprimée | la     |
			| de la séquence | la séquence | Passage pub | Supprimée | la     |
			| de l'événement | l'événement | Matinale    | Supprimé  | le     |

	Scénario: Un élément qui a perdu son nom au profit d'un autre ne se restaure pas, et la fiche dit pourquoi
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Publicité »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Et une autre banque « Publicité » est créée en base
		Et j'ouvre depuis l'historique la fiche de la banque « Publicité »
		Et je clique sur « Restaurer »
		Alors la fiche signale « Restauration impossible : une autre banque s'appelle déjà « Publicité ». »
		Et la fiche propose « Restaurer », pas « Supprimer… »

	Scénario: Un événement supprimé ne secourt plus, et restauré, il ne le fait pas de nouveau
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Panne »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Et j'ouvre depuis l'historique la fiche de l'événement « Panne »
		Et je clique sur « Restaurer »
		Alors le stream « Radio Thune » n'a plus d'événement de secours
		Et la liste en base de l'événement « Panne » est « Isolé »

	# ─── Cas particuliers ──────────────────────────────────────

	Scénario: Une fiche modifiée se supprime sans demander quoi faire de ses modifications
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Habillage »
		Et je saisis le nom public « Autre »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors seule la question de suppression a été posée
		Et la banque « Habillage » est marquée « supprimée » en base
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents »

	Scénario: Un élément déjà effacé de la base ferme simplement sa fiche, sans rien demander
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Pub seule »
		Et la séquence « Pub seule » est effacée de la base
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents »
		Quand j'ouvre la fiche du sonore « Isolé »
		Et le sonore « Isolé » est effacé de la base
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Incidents »
		Et aucune question n'a été posée

	Scénario: Une base injoignable empêche la suppression, et la fiche le dit
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Habillage »
		Et la base devient injoignable pour l'interface
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la fiche signale une suppression impossible
		Et l'onglet ouvert est « Banque : Habillage »

	Plan du scénario: Une nouvelle fiche n'a rien à supprimer
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « <onglet> »
		Et je clique sur « <bouton> »
		Alors le bouton « Supprimer… » de la fiche est inactif

		Exemples:
			| onglet     | bouton            |
			| Événements | Nouvel événement  |
			| Séquences  | Nouvelle séquence |
			| Banques    | Nouvelle banque   |

	Scénario: Une fiche enregistrée pour la première fois peut se supprimer
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Séquences »
		Et je clique sur « Nouvelle séquence »
		Et je saisis le nom interne « Brève »
		Et j'ajoute les sonores « Isolé »
		Et j'enregistre la fiche
		Alors le bouton « Supprimer… » de la fiche est actif
