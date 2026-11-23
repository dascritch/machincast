# language: fr
Fonctionnalité: Le cartouchier : des boutons tactiles dans Machin intranet qui agissent sur l'antenne
	En tant que technicien radio,
	je veux piloter quelques commandes simples vers Machin player, depuis une page web,
	afin de faciliter la transition d'antenne avec les directs.

	https://github.com/dascritch/machincast/issues/512, plugin de https://github.com/dascritch/machincast/issues/348.
	L'accueil de l'intranet montre, sous l'antenne en direct, les boutons du compte de la session, sans onglet à part ; chaque bouton demande une action d'antenne à Machin player, au nom du compte, qui la consigne avec lui.
	Les boutons se règlent par compte dans Machin interface. Machin player est imité par une socket qui publie un état,
	retient les demandes et y répond.

	Contexte:
		Étant donné les comptes de l'intranet :
			| nom    | mot de passe    | rôle        | état  |
			| regie  | tisane-au-micro | actions API | actif |
			| invite | cafe-sans-sucre | consulter   | actif |
		Et une session valide de « regie », de jeton « jeton-de-regie »
		Et une session valide de « invite », de jeton « jeton-d-invite »
		Et la banque « Jingles », marquée « ne pas répéter »
		Et la banque « Musiques jazz »
		Et la séquence « Chronique info »
		Et l'événement de secours « Attente »
		Et le feed « Studio mobile »
		Et les boutons de « regie » :
			| intitulé   | couleur | action            | cible          | blanc |
			| Jingle     | #aa3300 | insert_bank       | Jingles        | after |
			| Chronique  | #336699 | insert_sequence   | Chronique info |       |
			| Couper     | #990000 | cut_by_fallback   | Attente        |       |
			| Suivant    | #3a6ea5 | skip_sound        |                |       |
			| Avancer    | #3a6ea5 | advance           |                |       |
		Et les boutons de « invite » :
			| intitulé | couleur | action     | cible | blanc |
			| Suivant  | #3a6ea5 | skip_sound |       |       |
		Et Machin player, qui publie l'événement suivant « 12 » et fait les demandes
		Et l'intranet avec le cartouchier

	# ─── L'accueil ─────────────────────────────────────────

	Scénario: Les boutons du compte s'affichent sous l'antenne en direct de l'accueil, en couleurs, sans onglet à part
		Quand je demande à l'API « GET / », avec le jeton « jeton-de-regie »
		Alors l'API répond 200, une page « MachinCast - Radio Thune » du gabarit de « Radio Thune », « En diffusion », pour « regie »
		Et la page a l'antenne en direct, puis la section « Cartouchier »
		Et la page a les boutons « Jingle » #aa3300, « Chronique » #336699, « Couper » #990000, « Suivant » #3a6ea5, « Avancer » #3a6ea5
		Et la page charge la feuille de style « /plugins/cartwall/static/cartwall.css » et le script « /plugins/cartwall/static/cartwall.js »
		Et le bandeau n'a pas d'entrée « Cartouchier »
		Quand je demande à l'API « GET /plugins/cartwall », avec le jeton « jeton-de-regie »
		Alors l'API répond 404

	Scénario: Un compte « consulter » voit ses boutons grisés sous l'accueil
		Quand je demande à l'API « GET / », avec le jeton « jeton-d-invite »
		Alors la page a les boutons grisés « Suivant »
		Et la page dit « Ce compte ne fait que consulter : les boutons sont pour les comptes qui peuvent agir sur l'antenne. »

	Scénario: Un compte sans bouton garde l'accueil tel quel
		Étant donné les boutons de « regie » retirés
		Quand je demande à l'API « GET / », avec le jeton « jeton-de-regie »
		Alors la page n'a pas de section « Cartouchier », ni ses fichiers

	# ─── Les boutons, par l'API ────────────────────────────

	Scénario: L'API donne les boutons du compte, chacun utilisable ou non
		Quand je demande à l'API « GET /api/v1/plugins/cartwall/buttons », avec le jeton « jeton-de-regie »
		Alors l'API donne les boutons :
			| intitulé  | action          | cible          | blanc | utilisable |
			| Jingle    | insert_bank     | Jingles        | after | oui        |
			| Chronique | insert_sequence | Chronique info |       | oui        |
			| Couper    | cut_by_fallback | Attente        |       | oui        |
			| Suivant   | skip_sound      |                |       | oui        |
			| Avancer   | advance         |                |       | oui        |

	Scénario: Une banque « ne pas répéter » qui a donné le sonore à l'antenne grise son bouton
		Étant donné le sonore à l'antenne vient de la banque « Jingles »
		Quand je demande à l'API « GET /api/v1/plugins/cartwall/buttons », avec le jeton « jeton-de-regie »
		Alors le bouton « Jingle » n'est pas utilisable, parce que « la banque « Jingles » ne se répète pas : elle a donné le sonore à l'antenne »
		Et le bouton « Chronique » est utilisable
		Quand j'appuie sur le bouton « Jingle », avec le jeton « jeton-de-regie »
		Alors l'API répond 409, refusée parce que « la banque « Jingles » ne se répète pas : elle a donné le sonore à l'antenne »
		Et Machin player n'a reçu aucune demande

	Scénario: Une banque qui se répète garde son bouton utilisable
		Étant donné le bouton « Jingle » de « regie » insère la banque « Musiques jazz »
		Et le sonore à l'antenne vient de la banque « Musiques jazz »
		Quand je demande à l'API « GET /api/v1/plugins/cartwall/buttons », avec le jeton « jeton-de-regie »
		Alors le bouton « Jingle » est utilisable

	Scénario: Une cible supprimée grise son bouton
		Étant donné la séquence « Chronique info » supprimée
		Quand je demande à l'API « GET /api/v1/plugins/cartwall/buttons », avec le jeton « jeton-de-regie »
		Alors le bouton « Chronique » n'est pas utilisable, parce que « « Chronique info » est supprimé »

	# ─── Appuyer ───────────────────────────────────────────

	Plan du Scénario: Chaque bouton demande son action à Machin player, au nom du compte
		Quand j'appuie sur le bouton « <bouton> », avec le jeton « jeton-de-regie »
		Alors l'API répond 200, faite
		Et Machin player a reçu, de « regie », la demande « <demande> »

		Exemples:
			| bouton    | demande                                              |
			| Jingle    | {"command": "insert", "bank": 1, "blank": "after"}   |
			| Chronique | {"command": "insert", "sequence": 1}                 |
			| Couper    | {"command": "cut_by_fallback", "event": 1}           |
			| Suivant   | {"command": "interrupt", "item": "sound"}            |
			| Avancer   | {"command": "advance", "event": 12}                  |

	Scénario: Une action refusée par Machin player le dit, avec sa raison
		Étant donné Machin player, qui refuse les demandes parce que « no sequence on air »
		Quand j'appuie sur le bouton « Chronique », avec le jeton « jeton-de-regie »
		Alors l'API répond 409, refusée parce que « aucune séquence à l'antenne »

	Scénario: Sans événement suivant, avancer ne demande rien
		Étant donné Machin player, qui ne publie pas d'événement suivant
		Quand j'appuie sur le bouton « Avancer », avec le jeton « jeton-de-regie »
		Alors l'API répond 409, refusée parce que « aucun événement suivant »
		Et Machin player n'a reçu aucune demande

	Scénario: Un compte n'appuie que sur ses propres boutons
		Quand j'appuie sur le bouton « Suivant » de « invite », avec le jeton « jeton-de-regie »
		Alors l'API répond 404, avec l'erreur « Bouton inconnu. »
		Et Machin player n'a reçu aucune demande

	Scénario: Un compte « consulter » n'appuie sur aucun bouton
		Quand j'appuie sur le bouton « Suivant » de « invite », avec le jeton « jeton-d-invite »
		Alors l'API répond 403, avec l'erreur « Ce compte ne peut pas agir sur l'antenne. »
		Et Machin player n'a reçu aucune demande

	Plan du Scénario: Une demande sans bouton lisible est refusée
		Quand j'envoie « <corps> » à « /api/v1/plugins/cartwall/press », avec le jeton « jeton-de-regie »
		Alors l'API répond 400, avec l'erreur « Un bouton est demandé : {"button": <identifiant>}. »

		Exemples:
			| corps            |
			| pas du JSON      |
			| []               |
			| {"button": "1"}  |
			| {"button": true} |

	# ─── Le plugin ─────────────────────────────────────────

	Scénario: Le cartouchier s'accroche à l'intranet et à l'interface, chacun à son point
		Quand le cartouchier s'enregistre dans « Machin_intranet »
		Alors il s'abonne seulement à « intranet.extensions »
		Quand le cartouchier s'enregistre dans « Machin_interface »
		Alors il s'abonne seulement à « interface.plugin_window »

	Scénario: Ses migrations s'installent sans problème, et donnent aux seuls rôles de l'intranet et de l'interface
		Alors les migrations du cartouchier n'ont aucun problème
