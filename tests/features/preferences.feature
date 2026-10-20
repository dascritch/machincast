# language: fr
Fonctionnalité: Préférences de l'interface, et réglages des crossfades
	En tant que programmateur d'antenne,
	je veux un écran de préférences sur les réglages de crossfade,
	pour me faciliter l'utilisation de l'outil.

	https://github.com/dascritch/machincast/issues/145, spec § 8.11. « Préférences… », dans le menu « Fichier », ouvre
	une fenêtre dont la page « Interface » règle les crossfades : leur granularité (à la seconde ou au dixième de
	seconde), leur durée maximale, et leurs durées par défaut, pour un sonore sans crossfade paramétré que sa banque ne
	règle pas. Les préférences s'enregistrent dans la section [crossfades] du fichier de configuration, qui garde ses
	commentaires ; les fiches ouvertes ensuite les suivent, et Machin lecture les prend à son prochain démarrage.
	La fenêtre de l'interface s'ouvre sur une copie du fichier de configuration des tests, dans le répertoire du
	scénario.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 15:30:00 »
		Et les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Et les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement                  |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/jingles/hiver/cafe.flac |
		Et la banque « Jingles », séquentielle, sans nom public, avec « Café à minuit »

	# ─── Fenêtre de l'interface ────────────────────────────────

	Scénario: Les préférences s'ouvrent sur les réglages du fichier de configuration
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[crossfades]
			granularite = "seconde"
			maximum = 8
			debut = 2
			"""
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences… » dans le menu « Fichier »
		Alors les préférences ont montré : granularité « seconde », maximum 8 s, début par défaut 2 s, fin par défaut aucune

	Scénario: Les préférences enregistrées vont dans le fichier de configuration, qui garde ses commentaires
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[crossfades]
			# Réglages de l'antenne du matin.
			maximum = 8
			"""
		Et les préférences seront réglées : granularité « dixieme », maximum 6 s, début par défaut 1,5 s, fin par défaut 2 s
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences… » dans le menu « Fichier »
		Alors le fichier de configuration donne les crossfades : granularité « dixieme », maximum 6 s, début par défaut 1,5 s, fin par défaut 2 s
		Et le fichier de configuration contient encore « # Réglages de l'antenne du matin. »
		Et le fichier de configuration contient la ligne « maximum = 6 »
		Et le fichier de configuration contient la ligne « debut = 1.5 »
		Et le fichier de configuration contient encore les autres sections
		Et la barre d'état annonce « Préférences enregistrées dans …/machincast.toml ; Machin lecture prendra les crossfades par défaut à son prochain démarrage. »

	Scénario: Une durée par défaut retirée disparaît du fichier de configuration
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[crossfades]
			debut = 2
			fin = 3
			"""
		Et les préférences seront réglées : granularité « dixieme », maximum 5 s, début par défaut aucune, fin par défaut 3 s
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences… » dans le menu « Fichier »
		Alors le fichier de configuration donne les crossfades : granularité « dixieme », maximum 5 s, début par défaut aucune, fin par défaut 3 s
		Et le fichier de configuration n'a plus de clé « debut »

	Scénario: Les fiches ouvertes ensuite suivent les préférences
		Étant donné les préférences seront réglées : granularité « seconde », maximum 8 s, début par défaut aucune, fin par défaut aucune
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors les crossfades de la fiche se règlent au dixième de seconde, jusqu'à 5 s
		Quand je choisis « Préférences… » dans le menu « Fichier »
		Alors le fichier de configuration donne les crossfades : granularité « seconde », maximum 8 s, début par défaut aucune, fin par défaut aucune
		Quand j'ouvre la fiche de la banque « Jingles »
		Alors les crossfades de la fiche se règlent à la seconde, jusqu'à 8 s
		Quand j'ouvre l'onglet « Sonore : Café à minuit »
		Alors les crossfades de la fiche se règlent au dixième de seconde, jusqu'à 5 s

	Scénario: Sans fichier de configuration, les préférences ne s'enregistrent pas
		Quand la fenêtre de l'interface s'ouvre, sans fichier de configuration
		Alors le menu « Fichier » a les entrées :
			| entrée       | état     | raccourci | infobulle                                                       |
			| Préférences… | inactive |           | Sans fichier de configuration, les préférences ne s'enregistrent pas |
			| —            |          |           |                                                                 |
			| Quitter      | active   | Alt+Q     |                                                                 |

	Scénario: Renoncer aux préférences ne change rien
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[crossfades]
			maximum = 8
			"""
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences… » dans le menu « Fichier »
		Alors le fichier de configuration n'a pas changé
		Et la barre d'état n'a rien annoncé

	Scénario: Un fichier de configuration qu'on ne peut pas écrire le dit, et les préférences ne changent pas
		Étant donné le fichier de configuration de l'interface, que le poste refuse d'écrire
		Et les préférences seront réglées : granularité « seconde », maximum 8 s, début par défaut aucune, fin par défaut aucune
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences… » dans le menu « Fichier »
		Alors le fichier de configuration n'a pas changé
		Et la barre d'état annonce une erreur qui commence par « Préférences non enregistrées dans …/machincast.toml : »
		Quand j'ouvre la fiche du sonore « Café à minuit »
		Alors les crossfades de la fiche se règlent au dixième de seconde, jusqu'à 5 s

	# ─── Fenêtre des préférences ───────────────────────────────

	Scénario: La page « Interface » montre les réglages, et donne ceux qui sont saisis
		Quand la fenêtre des préférences s'ouvre sur : granularité « dixieme », maximum 5 s, début par défaut 1,5 s, fin par défaut aucune
		Alors elle s'intitule « Préférences », avec la page « Interface »
		Et elle montre : granularité « Au dixième de seconde », maximum « 5,0 s », début par défaut « 1,5 s », fin par défaut aucune
		Et son maximum se règle par pas de 0,1 s, à partir de 0,1 s
		Quand j'y choisis la granularité « À la seconde »
		Alors son maximum se règle par pas de 1 s, à partir de 1 s
		Quand j'y saisis le maximum 3
		Et j'y retire la durée de début par défaut
		Et j'y saisis la durée de fin par défaut 2
		Alors elle montre : granularité « À la seconde », maximum « 3 s », début par défaut aucune, fin par défaut « 2 s »
		Quand j'y clique sur « OK »
		Alors elle a donné : granularité « seconde », maximum 3 s, début par défaut aucune, fin par défaut 2 s

	Scénario: Une durée par défaut ne dépasse pas le maximum
		Quand la fenêtre des préférences s'ouvre sur : granularité « dixieme », maximum 5 s, début par défaut 4 s, fin par défaut 5 s
		Et j'y saisis le maximum 3
		Alors elle montre : granularité « Au dixième de seconde », maximum « 3,0 s », début par défaut « 3,0 s », fin par défaut « 3,0 s »

	Plan du scénario: La fenêtre des préférences, modale, donne ses réglages sur « OK », et rien sur « Annuler »
		Quand je réponds « <bouton> » à la fenêtre des préférences ouverte sur : granularité « seconde », maximum 8 s, début par défaut 2 s, fin par défaut aucune
		Alors les réglages donnés sont <donnes>

		Exemples:
			| bouton  | donnes                                                                               |
			| OK      | granularité « seconde », maximum 8 s, début par défaut 2 s, fin par défaut aucune |
			| Annuler | aucun                                                                                |
