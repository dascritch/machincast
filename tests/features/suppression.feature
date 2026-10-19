# language: fr
Fonctionnalité: Suppression d'un élément, après confirmation qui rappelle où il figure
	En tant que programmateur de l'antenne,
	je veux que la suppression d'un élément utilisé ailleurs me demande confirmation en listant où il figure,
	afin que je ne casse pas la grille par inadvertance.

	https://github.com/dascritch/machincast/issues/33, spec § 8.9. Chaque fiche a un bouton « Supprimer… », qui demande
	toujours confirmation. Supprimer un élément supprime son entrée en base, et le retire des listes où il figure :
	jamais un fichier sonore ni un répertoire, qui restent à leur place, intacts
	(https://github.com/dascritch/machincast/issues/96). L'historique de diffusion garde ses passages. Un chemin qui
	commence par « …/ » est dans le répertoire temporaire du scénario.

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
			| texte                                                                                                                                   |
			| Supprimer de la base le sonore « Les Gaufres – Spot » ?                                                                                 |
			| Il en sera retiré :                                                                                                                     |
			| • de la banque « Publicité », qui n'aura plus aucun sonore ;                                                                            |
			| • de l'événement « Matinale ».                                                                                                          |
			| Son fichier reste à sa place, intact : …/pubs/spot.flac. Il est dans un répertoire de la banque « Publicité » : la prochaine indexation l'enregistrera de nouveau, comme un nouveau sonore. |
			| L'historique de diffusion garde ses passages.                                                                                           |
		Et le sonore « Spot » n'est plus en base
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Marques-pages »
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
			| texte                                                                     |
			| Supprimer de la base le sonore « <nom> » ?                                |
			| Il ne figure dans aucune banque, aucune séquence ni aucun événement.      |
			| Son fichier reste à sa place, intact : <emplacement>.                     |
			| L'historique de diffusion garde ses passages.                             |
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Marques-pages »

		Exemples:
			| artiste | titre  | emplacement                  | ouvert                       | nom              |
			|         | Oublié | /srv/divers/oublie.flac      | Oublié                       | Oublié           |
			| Anonyme |        | /srv/divers/anonyme.flac     | /srv/divers/anonyme.flac     | Anonyme          |
			|         |        | /srv/divers/sans-titre.flac  | /srv/divers/sans-titre.flac  | sans-titre.flac  |

	Scénario: Un sonore d'une séquence la laisse vide, et un stream n'a pas de fichier
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Isolé »
		Et je supprime l'élément de la fiche, en répondant « Annuler »
		Alors la question de suppression, intitulée « Supprimer le sonore », a dit :
			| texte                                                                      |
			| Supprimer de la base le sonore « Isolé » ?                                 |
			| Il en sera retiré :                                                        |
			| • de l'événement « Panne », qui n'aura plus rien à jouer.                  |
			| Son fichier reste à sa place, intact : …/ailleurs/isole.flac.              |
			| L'historique de diffusion garde ses passages.                              |
		Quand j'ouvre la fiche du sonore « Jingle début »
		Et je supprime l'élément de la fiche, en répondant « Annuler »
		Alors la dernière question de suppression a dit :
			| texte                                                                                                                                   |
			| Supprimer de la base le sonore « Jingle début » ?                                                                                       |
			| Il en sera retiré :                                                                                                                     |
			| • de la banque « Habillage », qui n'aura plus aucun sonore ;                                                                            |
			| • de la séquence « Passage pub ».                                                                                                       |
			| Son fichier reste à sa place, intact : …/habillage/debut.flac. Il est dans un répertoire de la banque « Habillage » : la prochaine indexation l'enregistrera de nouveau, comme un nouveau sonore. |
			| L'historique de diffusion garde ses passages.                                                                                           |
		Quand j'ouvre la fiche du sonore « Radio Thune »
		Et je supprime l'élément de la fiche, en répondant « Annuler »
		Alors la dernière question de suppression a dit :
			| texte                                                            |
			| Supprimer de la base le sonore « Radio Thune » ?                 |
			| Il ne figure dans aucune banque, aucune séquence ni aucun événement. |
			| L'historique de diffusion garde ses passages.                    |

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
			| texte                                                                                                   |
			| Supprimer de la base la banque « Publicité » ?                                                          |
			| Elle en sera retirée :                                                                                  |
			| • de la séquence « Passage pub » ;                                                                      |
			| • de la séquence « Pub seule », qui n'aura plus aucun élément ;                                         |
			| • de l'événement « Midi », qui n'aura plus rien à jouer.                                                |
			| Ses répertoires restent à leur place, avec leurs fichiers, intacts : …/pubs. Ses sonores restent en base. |
			| L'historique de diffusion garde ses passages.                                                           |
		Et la banque « Publicité » n'est plus en base
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
			| texte                                                     |
			| Supprimer de la base la banque « Vide » ?                 |
			| Elle ne figure dans aucune séquence ni aucun événement.   |
			| Ses sonores restent en base.                              |
			| L'historique de diffusion garde ses passages.             |
		Et la banque « Vide » n'est plus en base
		Et le sonore « Isolé » est toujours en base

	# ─── Séquence ──────────────────────────────────────────────

	Scénario: Une séquence supprimée quitte la base et les événements, mais ses éléments restent en base
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Passage pub »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la question de suppression, intitulée « Supprimer la séquence », a dit :
			| texte                                                        |
			| Supprimer de la base la séquence « Passage pub » ?           |
			| Elle en sera retirée :                                       |
			| • de l'événement « Matinale ».                               |
			| Ses sonores et ses banques restent en base.                  |
			| L'historique de diffusion garde ses passages.                |
		Et la séquence « Passage pub » n'est plus en base
		Et la liste en base de l'événement « Matinale » est « Habillage », « Spot »
		Et la banque « Publicité » est toujours en base

	# ─── Événement ─────────────────────────────────────────────

	Scénario: Un événement supprimé quitte la base, sa liste avec lui, et les streams qu'il secourait n'ont plus de secours
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Panne »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la question de suppression, intitulée « Supprimer l'événement », a dit :
			| texte                                                                                     |
			| Supprimer de la base l'événement « Panne » ?                                              |
			| Il est l'événement de secours des streams « Radio Machin », « Radio Thune », qui n'en auront plus. |
			| Sa liste de lecture disparaît avec lui ; ses sonores, banques et séquences restent en base. |
			| L'historique de diffusion garde ses passages.                                             |
		Et l'événement « Panne » n'est plus en base
		Et le stream « Radio Thune » n'a plus d'événement de secours
		Et le stream « Radio Machin » n'a plus d'événement de secours
		Et le sonore « Isolé » est toujours en base
		Quand j'ouvre la fiche de l'événement « Coupure »
		Et je supprime l'élément de la fiche, en répondant « Annuler »
		Alors la dernière question de suppression a dit :
			| texte                                                                                     |
			| Supprimer de la base l'événement « Coupure » ?                                            |
			| Il est l'événement de secours du stream « Radio Ondes », qui n'en aura plus.              |
			| Sa liste de lecture disparaît avec lui ; ses sonores, banques et séquences restent en base. |
			| L'historique de diffusion garde ses passages.                                             |

	Scénario: Un événement de la grille supprimé laisse l'historique de diffusion intact
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de l'événement « Matinale »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la question de suppression, intitulée « Supprimer l'événement », a dit :
			| texte                                                                                     |
			| Supprimer de la base l'événement « Matinale » ?                                           |
			| Sa liste de lecture disparaît avec lui ; ses sonores, banques et séquences restent en base. |
			| L'historique de diffusion garde ses passages.                                             |
		Et l'événement « Matinale » n'est plus en base
		Et l'historique de diffusion garde le passage de « Les Gaufres – Spot », à l'emplacement « …/pubs/spot.flac »

	# ─── Cas particuliers ──────────────────────────────────────

	Scénario: Une fiche modifiée se supprime sans demander quoi faire de ses modifications
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la banque « Habillage »
		Et je saisis le nom public « Autre »
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors seule la question de suppression a été posée
		Et la banque « Habillage » n'est plus en base
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Marques-pages »

	Scénario: Un élément déjà effacé de la base ferme simplement sa fiche, sans rien demander
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche de la séquence « Pub seule »
		Et la séquence « Pub seule » est effacée de la base
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Marques-pages »
		Quand j'ouvre la fiche du sonore « Isolé »
		Et le sonore « Isolé » est effacé de la base
		Et je supprime l'élément de la fiche, en répondant « Supprimer »
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Marques-pages »
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
