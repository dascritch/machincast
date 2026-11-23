# language: fr
Fonctionnalité: Les boutons du cartouchier, réglés par compte dans Machin interface
	En tant que responsable de l'antenne,
	je veux régler, pour chaque compte de l'API, les boutons de son cartouchier,
	afin que chaque émission ait les actions dont elle a besoin, et seulement elles.

	https://github.com/dascritch/machincast/issues/512. La fenêtre du plugin, menu « Plugins » de Machin interface,
	montre les boutons du compte choisi, dans l'ordre du cartouchier ; chaque changement s'enregistre aussitôt, au rôle
	machincast_interface.

	Contexte:
		Étant donné les comptes de l'intranet :
			| nom     | mot de passe    | rôle        | état  |
			| gaufres | tisane-au-micro | actions API | actif |
			| infos   | cafe-sans-sucre | actions API | actif |
		Et la banque « Identifiant station court »
		Et la banque « Musiques jazz »
		Et la séquence « Partenariats »
		Et l'événement de secours « Attente »
		Et les boutons de « infos » :
			| intitulé | couleur | action          | cible   | blanc |
			| Couper   | #990000 | cut_by_fallback | Attente |       |
			| Suivant  | #3a6ea5 | skip_sound      |         |       |

	Scénario: La fenêtre montre les comptes, et les boutons du compte choisi
		Quand j'ouvre les réglages du cartouchier
		Alors les comptes proposés sont « gaufres », « infos »
		Quand je choisis le compte « infos »
		Alors la liste des boutons est :
			| Couper — Couper l'antenne par un secours, « Attente » |
			| Suivant — Sauter au sonore suivant                     |

	Scénario: Ajouter un bouton qui insère un sonore d'une banque, avec un blanc après
		Quand j'ouvre les réglages du cartouchier
		Et je choisis le compte « gaufres »
		Et je remplis le bouton « Jazz », « #335500 », « Insérer un sonore d'une banque après ce sonore », « Musiques jazz », « un blanc de 5 secondes après »
		Et j'appuie sur « Ajouter »
		Alors les boutons de « gaufres » sont :
			| intitulé | couleur | action      | cible         | blanc |
			| Jazz     | #335500 | insert_bank | Musiques jazz | after |

	Scénario: La cible ne se propose qu'à une action qui en a une, le blanc qu'à une insertion
		Quand j'ouvre les réglages du cartouchier
		Et je choisis l'action « Couper l'antenne par un secours »
		Alors les cibles proposées sont « Attente », et le blanc est grisé
		Quand je choisis l'action « Insérer une séquence après ce sonore »
		Alors les cibles proposées sont « Partenariats », et le blanc se choisit
		Quand je choisis l'action « Sauter au sonore suivant »
		Alors aucune cible n'est proposée, et le blanc est grisé

	Scénario: Remplacer, monter et retirer un bouton
		Quand j'ouvre les réglages du cartouchier
		Et je choisis le compte « infos »
		Et je choisis le bouton « Suivant »
		Et j'appuie sur « Monter »
		Alors les boutons de « infos » sont :
			| intitulé | couleur | action          | cible   | blanc |
			| Suivant  | #3a6ea5 | skip_sound      |         |       |
			| Couper   | #990000 | cut_by_fallback | Attente |       |
		Quand je remplis le bouton « Après », « #123456 », « Sauter après la séquence », « », « »
		Et j'appuie sur « Remplacer »
		Et je choisis le bouton « Couper »
		Et j'appuie sur « Retirer »
		Alors les boutons de « infos » sont :
			| intitulé | couleur | action        | cible | blanc |
			| Après    | #123456 | skip_sequence |       |       |

	Plan du Scénario: Un bouton incomplet ne s'enregistre pas, et la fenêtre dit pourquoi
		Quand j'ouvre les réglages du cartouchier
		Et je choisis le compte « gaufres »
		Et je remplis le bouton « <intitulé> », « <couleur> », « Sauter au sonore suivant », « », « »
		Et j'appuie sur « Ajouter »
		Alors la fenêtre dit « <message> »
		Et les boutons de « gaufres » sont :
			| intitulé | couleur | action | cible | blanc |

		Exemples:
			| intitulé | couleur | message                          |
			|          | #123456 | Un intitulé est demandé.         |
			| Suivant  | rouge   | Une couleur s'écrit #rrggbb.     |

	Scénario: Une base injoignable le dit dans la fenêtre
		Quand j'ouvre les réglages du cartouchier, sans base
		Alors la fenêtre dit que les boutons ne se lisent ni ne s'enregistrent
