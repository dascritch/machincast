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
	Sa page « Audio » règle les périphériques de l'antenne (audio.peripherique) et de la pré-écoute (audio.preecoute,
	https://github.com/dascritch/machincast/issues/116) : chacun est grisé dans l'autre choix, et Machin lecture refuse
	de diffuser sans périphérique d'antenne. La fenêtre de l'interface s'ouvre sur une copie du fichier de configuration
	des tests, dans le répertoire du scénario ; sa sortie est factice, et sans périphérique d'antenne.

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

	Scénario: Les périphériques réglés vont dans la section [audio] du fichier de configuration
		Étant donné les préférences régleront l'antenne « carte-2 » et la pré-écoute « casque-usb »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences… » dans le menu « Fichier »
		Alors les préférences ont montré l'antenne non renseignée et la pré-écoute « preecoute-factice »
		Et le fichier de configuration donne l'antenne « carte-2 » et la pré-écoute « casque-usb »
		Et le fichier de configuration contient encore les autres sections, hors [audio]
		Et la barre d'état annonce « Préférences enregistrées dans …/machincast.toml ; Machin lecture prendra les crossfades par défaut et le périphérique de l'antenne à son prochain démarrage. »

	Scénario: Sur une vraie sortie, la barre d'état signale l'antenne à renseigner, jusqu'à ce qu'elle le soit
		Étant donné la configuration audio sortie « pipewire », sans périphérique d'antenne
		Et les préférences régleront l'antenne « carte-2 » et la pré-écoute « casque-usb »
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre d'état signale « Périphérique de l'antenne à renseigner »
		Quand je choisis « Préférences… » dans le menu « Fichier »
		Alors la barre d'état ne signale pas « Périphérique de l'antenne à renseigner »

	Scénario: Sur la sortie factice des essais, l'antenne n'a pas à être renseignée
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre d'état ne signale pas « Périphérique de l'antenne à renseigner »

	Scénario: Machin interface ouvre sa fenêtre sur la sortie et les périphériques de sa configuration
		Étant donné un fichier de configuration sur la base de test, la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « casque-usb »
		Quand Machin interface est lancé avec ce fichier
		Alors sa fenêtre a la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « casque-usb »
		Et ses préférences montrent l'antenne « carte-1 » et la pré-écoute « casque-usb », sur la sortie « pipewire »

	Scénario: Le seuil de blanc enregistré va dans la section [blancs] du fichier de configuration
		https://github.com/dascritch/machincast/issues/146 : le seuil vaut pour les audits complets suivants.

		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[blancs]
			# Seuil de l'antenne du matin.
			seuil = -50
			"""
		Et les préférences seront réglées avec le seuil de blanc -55,5 dB
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences… » dans le menu « Fichier »
		Alors les préférences ont montré le seuil de blanc -50 dB
		Et le fichier de configuration contient la ligne « seuil = -55.5 »
		Et le fichier de configuration contient encore « # Seuil de l'antenne du matin. »
		Et le fichier de configuration contient encore les autres sections

	Scénario: Le voyant « Saturation » réglé dans les préférences va dans la section [interface], et l'accueil le suit aussitôt
		https://github.com/dascritch/machincast/issues/191 : le voyant reste affiché par défaut.

		Étant donné les préférences seront réglées avec le voyant « Saturation » caché
		Quand la fenêtre de l'interface s'ouvre
		Alors le voyant « Saturation » de l'antenne est affiché à l'accueil
		Quand je choisis « Préférences… » dans le menu « Fichier »
		Alors les préférences ont montré le voyant « Saturation » affiché
		Et le fichier de configuration contient la ligne « saturation = false »
		Et le fichier de configuration contient encore les autres sections
		Et le voyant « Saturation » de l'antenne est caché à l'accueil

	Scénario: L'accueil s'ouvre sans le voyant « Saturation » quand la configuration le cache
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[interface]
			saturation = false
			"""
		Quand la fenêtre de l'interface s'ouvre
		Alors le voyant « Saturation » de l'antenne est caché à l'accueil
		Et le voyant « Silence » de l'antenne est affiché à l'accueil

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

	Scénario: La page « Interface » montre le voyant « Saturation », et donne ce qui est coché
		Quand la fenêtre des préférences s'ouvre sur le voyant « Saturation » affiché
		Alors elle montre la case « Afficher le voyant de saturation de l'accueil », cochée
		Quand j'y décoche la case du voyant « Saturation »
		Et j'y clique sur « OK »
		Alors elle a donné le voyant « Saturation » caché

	Scénario: La page « Audio » montre le seuil de blanc, et donne celui qui est saisi
		Quand la fenêtre des préférences s'ouvre sur le seuil de blanc -40 dB
		Alors elle montre le seuil de blanc « -40,0 dB », réglable de -100,0 à -0,1 dB
		Quand j'y saisis le seuil de blanc -55,5
		Et j'y clique sur « OK »
		Alors elle a donné le seuil de blanc -55,5 dB

	Scénario: La page « Audio » montre les périphériques, chacun grisé dans l'autre choix
		Étant donné les périphériques audio du poste :
			| identifiant       | nom           |
			| carte-1           | Carte 1       |
			| casque-usb        | Casque USB    |
			| preecoute-factice | Haut-parleurs |
		Quand la fenêtre des préférences s'ouvre sur l'antenne « carte-1 » et la pré-écoute « preecoute-factice »
		Alors elle s'intitule « Préférences », avec la page « Interface »
		Et le choix de l'antenne propose :
			| sortie        | état     |
			| Carte 1       | active   |
			| Casque USB    | active   |
			| Haut-parleurs | inactive |
		Et le choix de la pré-écoute propose :
			| sortie        | état     |
			| Haut-parleurs | active   |
			| Carte 1       | inactive |
			| Casque USB    | active   |
		Quand j'y choisis pour l'antenne « Casque USB »
		Alors le choix de la pré-écoute propose :
			| sortie        | état     |
			| Haut-parleurs | active   |
			| Carte 1       | active   |
			| Casque USB    | inactive |
		Quand j'y clique sur « OK »
		Alors elle a donné l'antenne « casque-usb » et la pré-écoute « preecoute-factice »

	Scénario: Une antenne non renseignée se propose « (à renseigner) », et un périphérique absent « (introuvable) »
		Étant donné les périphériques audio du poste :
			| identifiant | nom        |
			| casque-usb  | Casque USB |
		Quand la fenêtre des préférences s'ouvre sur l'antenne non renseignée et la pré-écoute « debranche »
		Alors le choix de l'antenne propose :
			| sortie          | état   |
			| (à renseigner)  | active |
			| Casque USB      | active |
		Et le choix de la pré-écoute propose :
			| sortie                   | état   |
			| debranche (introuvable)  | active |
			| Casque USB               | active |
		Quand j'y clique sur « OK »
		Alors elle a donné l'antenne non renseignée et la pré-écoute « debranche »

	Scénario: Un même périphérique ne peut pas servir à l'antenne et à la pré-écoute
		Étant donné les périphériques audio du poste :
			| identifiant | nom        |
			| casque-usb  | Casque USB |
		Quand la fenêtre des préférences s'ouvre sur l'antenne « casque-usb » et la pré-écoute « casque-usb »
		Alors son bouton « OK » est inactif
