# language: fr
Fonctionnalité: Ajout de fichiers sonores depuis la liste des sonores
	En tant que programmateur de l'antenne,
	je veux ajouter un fichier depuis l'interface,
	afin de programmer un contenu sans passer par un répertoire de banque.

	https://github.com/dascritch/machincast/issues/30, spec § 8.8. La liste des sonores ajoute des fichiers choisis dans
	le sélecteur du poste, ou déposés depuis le navigateur de fichiers. Un fichier est référencé là où il se trouve, sans
	copie, et n'est jamais modifié (https://github.com/dascritch/machincast/issues/96). Il entre en base à l'état
	aperçu, puis passe aussitôt par la vérification de l'indexeur, en tâche de fond. Les fichiers de test sont ceux de
	tests/fichiers-sonores ; un chemin qui commence par « …/ » est dans le répertoire temporaire du scénario.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 19:00:00 »
		Et le fichier de test « tags.flac » copié en « …/emissions/cafe.flac »
		Et le fichier de test « sain.wav » copié en « …/emissions/jingle.wav »
		Et le fichier « …/emissions/faux.mp3 », qui n'est pas un son

	Scénario: Les fichiers choisis entrent en base, puis l'indexeur les vérifie
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ajoute les fichiers « …/emissions/cafe.flac », « …/emissions/jingle.wav », « …/emissions/faux.mp3 »
		Et la vérification des fichiers ajoutés se termine
		Alors la barre d'état a annoncé « 3 fichiers ajoutés, en cours de vérification. »
		Et la barre d'état annonce « Vérification terminée : Les Gaufres Électriques – Café à minuit, actif ; jingle.wav, actif ; faux.mp3, erroné. »
		Et les sonores ajoutés sont en base :
			| emplacement           | type    | etat   | artiste                 | titre         | duree   |
			| …/emissions/cafe.flac | fichier | actif  | Les Gaufres Électriques | Café à minuit | 0:00:01 |
			| …/emissions/jingle.wav | fichier | actif | None                    | None          | 0:00:01 |
			| …/emissions/faux.mp3  | fichier | errone | None                    | None          | None    |
		# Les fichiers de test durent un peu moins d'une seconde : la liste ne compte que les secondes pleines.
		Et la liste montre :
			| Artiste                 | Titre         | Type    | État   | Durée | Emplacement            |
			| Les Gaufres Électriques | Café à minuit | fichier | actif  | 0:00  | …/emissions/cafe.flac  |
			|                         |               | fichier | actif  | 0:00  | …/emissions/jingle.wav |
			|                         |               | fichier | erroné |       | …/emissions/faux.mp3   |
		Et les fichiers déposés sont intacts

	Scénario: Un fichier ajouté entre en base à l'état aperçu, avant sa vérification
		Étant donné une vérification des fichiers ajoutés qui attend
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ajoute les fichiers « …/emissions/jingle.wav »
		Alors la barre d'état annonce « 1 fichier ajouté, en cours de vérification. »
		Et les sonores ajoutés sont en base :
			| emplacement            | type    | etat   | artiste | titre | duree |
			| …/emissions/jingle.wav | fichier | apercu | None    | None  | None  |
		Et la liste montre :
			| Artiste | Titre | Type    | État   | Durée | Emplacement            |
			|         |       | fichier | aperçu |       | …/emissions/jingle.wav |
		Quand la vérification attendue reprend, et se termine
		Alors les sonores ajoutés sont en base :
			| emplacement            | type    | etat  | artiste | titre | duree   |
			| …/emissions/jingle.wav | fichier | actif | None    | None  | 0:00:01 |

	Scénario: Un fichier déjà en base n'est pas ajouté une seconde fois, et ce qui n'est pas un fichier sonore est ignoré
		Étant donné les dossiers « …/emissions/archives » du scénario
		Et les fichiers « …/emissions/notes.txt » du scénario
		Et les sonores :
			| artiste | titre  | type    | etat  | duree | emplacement           |
			|         | Ancien | fichier | actif | 1     | …/emissions/cafe.flac |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ajoute les fichiers « …/emissions/cafe.flac », « …/emissions/notes.txt », « …/emissions/archives », « …/emissions/jingle.wav »
		Et la vérification des fichiers ajoutés se termine
		Alors la barre d'état a annoncé « 1 fichier ajouté, en cours de vérification. Déjà en base : cafe.flac. Ignorés, ce ne sont pas des fichiers sonores : notes.txt, archives. »
		Et les sonores ajoutés sont en base :
			| emplacement            | type    | etat  | artiste | titre  | duree   |
			| …/emissions/cafe.flac  | fichier | actif | None    | Ancien | 0:00:01 |
			| …/emissions/jingle.wav | fichier | actif | None    | None   | 0:00:01 |

	Scénario: La vérification immédiate ne décode que les fichiers ajoutés
		Étant donné le fichier de test « sain.ogg » copié en « …/attente/autre.ogg »
		Et les sonores :
			| artiste | titre | type    | etat   | duree | emplacement         |
			|         | Autre | fichier | apercu |       | …/attente/autre.ogg |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ajoute les fichiers « …/emissions/jingle.wav »
		Et la vérification des fichiers ajoutés se termine
		Alors les sonores ajoutés sont en base :
			| emplacement            | type    | etat   | artiste | titre | duree   |
			| …/attente/autre.ogg    | fichier | apercu | None    | Autre | None    |
			| …/emissions/jingle.wav | fichier | actif  | None    | None  | 0:00:01 |

	Scénario: Renoncer au choix des fichiers n'ajoute rien, et laisse la barre d'état telle qu'elle était
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ajoute les fichiers aucun
		Alors la barre d'état n'a rien annoncé
		Et le compte de la liste est « aucun sonore »
		Quand j'ajoute les fichiers « …/emissions/jingle.wav »
		Et la vérification des fichiers ajoutés se termine
		Et j'ajoute les fichiers aucun
		Alors la barre d'état annonce « Vérification terminée : jingle.wav, actif. »

	Scénario: Un fichier déjà en base, seul, ne lance aucune vérification
		Étant donné les sonores :
			| artiste | titre  | type    | etat  | duree | emplacement           |
			|         | Ancien | fichier | actif | 1     | …/emissions/cafe.flac |
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ajoute les fichiers « …/emissions/cafe.flac »
		Alors la barre d'état annonce « Déjà en base : cafe.flac. »
		Et la vérification des fichiers ajoutés est terminée

	Scénario: Les vérifications demandées passent l'une après l'autre, dans l'ordre
		Étant donné une vérification des fichiers ajoutés qui attend
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ajoute les fichiers « …/emissions/jingle.wav »
		Et j'ajoute les fichiers « …/emissions/cafe.flac »
		Et j'ajoute les fichiers « …/emissions/faux.mp3 »
		Et la vérification attendue reprend, et se termine
		Alors la barre d'état a annoncé, dans l'ordre, « Vérification terminée : jingle.wav, actif. », « Vérification terminée : Les Gaufres Électriques – Café à minuit, actif. », « Vérification terminée : faux.mp3, erroné. »
		Et les vérifications ont décodé un fichier à la fois

	Scénario: Le même fichier choisi deux fois n'est ajouté qu'une fois, sous son chemin normalisé
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ajoute les fichiers « …/emissions/jingle.wav », « …/emissions/../emissions/jingle.wav »
		Et la vérification des fichiers ajoutés se termine
		Alors la barre d'état a annoncé « 1 fichier ajouté, en cours de vérification. »
		Et les sonores ajoutés sont en base :
			| emplacement            | type    | etat  | artiste | titre | duree   |
			| …/emissions/jingle.wav | fichier | actif | None    | None  | 0:00:01 |

	# ─── Dépôt depuis le navigateur de fichiers ────────────────

	Scénario: Des fichiers déposés sur la liste des sonores s'ajoutent comme une copie, sans être touchés
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je dépose sur la liste des sonores « …/emissions/cafe.flac », « …/emissions/jingle.wav »
		Et la vérification des fichiers ajoutés se termine
		Alors le dépôt est accepté comme une copie
		Et la barre d'état a annoncé « 2 fichiers ajoutés, en cours de vérification. »
		Et les sonores ajoutés sont en base :
			| emplacement            | type    | etat  | artiste                 | titre         | duree   |
			| …/emissions/cafe.flac  | fichier | actif | Les Gaufres Électriques | Café à minuit | 0:00:01 |
			| …/emissions/jingle.wav | fichier | actif | None                    | None          | 0:00:01 |
		Et les fichiers déposés sont intacts

	Scénario: Un glisser qui ne propose pas la copie est refusé
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et je dépose sur la liste des sonores « …/emissions/cafe.flac », en ne proposant que le déplacement
		Alors le dépôt est refusé
		Et les sonores ajoutés sont en base :
			| emplacement | type | etat | artiste | titre | duree |

	Scénario: Seule la liste des sonores ajoute des fichiers
		Quand la fenêtre de l'interface s'ouvre
		Alors seule la liste « Sonores » propose « Ajouter des fichiers… » et accepte les dépôts

	# ─── Vérification ──────────────────────────────────────────

	Scénario: Une vérification impossible est annoncée, et laisse le sonore en aperçu
		Étant donné un indexeur qui ne sait pas décoder les fichiers
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ajoute les fichiers « …/emissions/jingle.wav »
		Et la vérification des fichiers ajoutés se termine
		Alors la barre d'état annonce « Vérification impossible : aucun décodeur pour ce format ; la prochaine indexation reprendra les fichiers en aperçu. »
		Et les sonores ajoutés sont en base :
			| emplacement            | type    | etat   | artiste | titre | duree |
			| …/emissions/jingle.wav | fichier | apercu | None    | None  | None  |

	Scénario: Fermer la fenêtre attend la fin de la vérification en cours
		Étant donné une vérification des fichiers ajoutés qui attend
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre l'onglet « Sonores »
		Et j'ajoute les fichiers « …/emissions/jingle.wav »
		Et je ferme la fenêtre de l'interface, pendant que la vérification attendue reprend
		Alors la vérification des fichiers ajoutés est terminée
		Et les sonores ajoutés sont en base :
			| emplacement            | type    | etat  | artiste | titre | duree   |
			| …/emissions/jingle.wav | fichier | actif | None    | None  | 0:00:01 |
