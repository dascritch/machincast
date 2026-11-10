# language: fr
Fonctionnalité: Préférences de l'interface, et réglages des crossfades
	En tant que programmateur d'antenne,
	je veux un écran de préférences sur les réglages de crossfade,
	pour me faciliter l'utilisation de l'outil.

	https://github.com/dascritch/machincast/issues/145, spec § 8.11. « Préférences… », dans le menu « Fichier », ouvre
	une fenêtre dont la page « Interface » règle les crossfades : leur granularité (à la seconde ou au dixième de
	seconde), leur durée maximale, et leurs durées par défaut, pour un sonore sans crossfade paramétré que sa banque ne
	règle pas. Les préférences s'enregistrent dans la section [crossfades] du fichier de configuration, qui garde ses
	commentaires ; les fiches ouvertes ensuite les suivent, et Machin player les prend à son prochain démarrage.
	Sa page « Audio » règle les périphériques de l'antenne (audio.device) et de la pré-écoute (audio.preview,
	https://github.com/dascritch/machincast/issues/116) : chacun est grisé dans l'autre choix, et Machin player refuse
	de diffuser sans périphérique d'antenne. La fenêtre de l'interface s'ouvre sur une copie du fichier de configuration
	des tests, dans le répertoire du scénario ; sa sortie est factice, et sans périphérique d'antenne.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-19 15:30:00 »
		Et les événements :
			| name     | public_name | priority               | starts_at | ends_at | days |
			| Continue |             | background_programming |           |         |      |
		Et les sonores :
			| artist      | title         | type | state  | duration | location                     |
			| Les Gaufres | Café à minuit | file | active | 214      | /srv/jingles/hiver/cafe.flac |
		Et la banque « Jingles », séquentielle, sans nom public, avec « Café à minuit »

	# ─── Fenêtre de l'interface ────────────────────────────────

	Scénario: Les préférences s'ouvrent sur les réglages du fichier de configuration
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[crossfades]
			granularity = "second"
			maximum = 8
			start = 2
			"""
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors les préférences ont montré : granularité « second », maximum 8 s, début par défaut 2 s, fin par défaut aucune

	Scénario: Les préférences enregistrées vont dans le fichier de configuration, qui garde ses commentaires
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[crossfades]
			# Réglages de l'antenne du matin.
			maximum = 8
			"""
		Et les préférences seront réglées : granularité « tenth », maximum 6 s, début par défaut 1,5 s, fin par défaut 2 s
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors le fichier de configuration donne les crossfades : granularité « tenth », maximum 6 s, début par défaut 1,5 s, fin par défaut 2 s
		Et le fichier de configuration contient encore « # Réglages de l'antenne du matin. »
		Et le fichier de configuration contient la ligne « maximum = 6 »
		Et le fichier de configuration contient la ligne « start = 1.5 »
		Et le fichier de configuration contient encore les autres sections
		Et la barre d'état annonce « Préférences enregistrées dans …/machincast.toml ; Machin player prendra les crossfades par défaut à son prochain démarrage. »

	Scénario: Une durée par défaut retirée disparaît du fichier de configuration
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[crossfades]
			start = 2
			end = 3
			"""
		Et les préférences seront réglées : granularité « tenth », maximum 5 s, début par défaut aucune, fin par défaut 3 s
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors le fichier de configuration donne les crossfades : granularité « tenth », maximum 5 s, début par défaut aucune, fin par défaut 3 s
		Et le fichier de configuration n'a plus de clé « start »

	Scénario: Les fiches ouvertes ensuite suivent les préférences
		Étant donné les préférences seront réglées : granularité « second », maximum 8 s, début par défaut aucune, fin par défaut aucune
		Quand la fenêtre de l'interface s'ouvre
		Et j'ouvre la fiche du sonore « Café à minuit »
		Alors les crossfades de la fiche se règlent au dixième de seconde, jusqu'à 10 s
		Quand je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors le fichier de configuration donne les crossfades : granularité « second », maximum 8 s, début par défaut aucune, fin par défaut aucune
		Quand j'ouvre la fiche de la banque « Jingles »
		Alors les crossfades de la fiche se règlent à la seconde, jusqu'à 8 s
		Quand j'ouvre l'onglet « Sonore : Café à minuit »
		Alors les crossfades de la fiche se règlent au dixième de seconde, jusqu'à 10 s

	Scénario: Sans fichier de configuration, les préférences ne s'enregistrent pas
		Quand la fenêtre de l'interface s'ouvre, sans fichier de configuration
		Alors le menu « Fichier » a les entrées :
			| entrée       | état     | raccourci | infobulle                                                       |
			| Préférences de l'interface… | inactive |           | Sans fichier de configuration, les préférences ne s'enregistrent pas |
			| Paramètres du service… | inactive |           | Sans fichier de configuration, les préférences ne s'enregistrent pas |
			| —            |          |           |                                                                 |
			| Quitter      | active   | Alt+Q     |                                                                 |

	Scénario: Renoncer aux préférences ne change rien
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[crossfades]
			maximum = 8
			"""
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors le fichier de configuration n'a pas changé
		Et la barre d'état n'a rien annoncé

	Scénario: Un fichier de configuration qu'on ne peut pas écrire le dit, et les préférences ne changent pas
		Étant donné le fichier de configuration de l'interface, que le poste refuse d'écrire
		Et les préférences seront réglées : granularité « second », maximum 8 s, début par défaut aucune, fin par défaut aucune
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors le fichier de configuration n'a pas changé
		Et la barre d'état annonce une erreur qui commence par « Préférences non enregistrées dans …/machincast.toml : »
		Quand j'ouvre la fiche du sonore « Café à minuit »
		Alors les crossfades de la fiche se règlent au dixième de seconde, jusqu'à 10 s

	Scénario: Les périphériques réglés vont dans la section [audio] du fichier de configuration
		Étant donné les préférences régleront l'antenne « carte-2 » et la pré-écoute « casque-usb »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors les préférences ont montré l'antenne non renseignée et la pré-écoute « preecoute-factice »
		Et le fichier de configuration donne l'antenne « carte-2 » et la pré-écoute « casque-usb »
		Et le fichier de configuration contient encore les autres sections, hors [audio]
		Et la barre d'état annonce « Préférences enregistrées dans …/machincast.toml ; Machin player prendra les crossfades par défaut et le périphérique de l'antenne à son prochain démarrage. »

	Scénario: Sur une vraie sortie, la barre d'état signale l'antenne à renseigner, jusqu'à ce qu'elle le soit
		Étant donné la configuration audio sortie « pipewire », sans périphérique d'antenne
		Et les préférences régleront l'antenne « carte-2 » et la pré-écoute « casque-usb »
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre d'état signale « Périphérique de l'antenne à renseigner »
		Quand je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors la barre d'état ne signale pas « Périphérique de l'antenne à renseigner »

	Scénario: Sur la sortie factice des essais, l'antenne n'a pas à être renseignée
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre d'état ne signale pas « Périphérique de l'antenne à renseigner »

	Scénario: Sur l'entrée « sortie factice » d'une vraie sortie, l'antenne n'a pas à être renseignée
		Étant donné la configuration audio sortie « pipewire », avec le périphérique d'antenne « dummy »
		Quand la fenêtre de l'interface s'ouvre
		Alors la barre d'état ne signale pas « Périphérique de l'antenne à renseigner »

	Scénario: Le type de sortie réglé va aussi dans la section [audio] (https://github.com/dascritch/machincast/issues/339)
		Étant donné la configuration audio sortie « pipewire », avec le périphérique d'antenne « carte-1 »
		Et les préférences régleront la sortie « pulseaudio », l'antenne « dummy » et la pré-écoute « casque-usb »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors le fichier de configuration donne la sortie « pulseaudio », l'antenne « dummy » et la pré-écoute « casque-usb »
		Et la barre d'état annonce « Préférences enregistrées dans …/machincast.toml ; Machin player prendra les crossfades par défaut et le périphérique de l'antenne à son prochain démarrage. »

	Scénario: Machin interface ouvre sa fenêtre sur la sortie et les périphériques de sa configuration
		Étant donné un fichier de configuration sur la base de test, la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « casque-usb »
		Quand Machin interface est lancé avec ce fichier
		Alors sa fenêtre a la sortie « pipewire », l'antenne « carte-1 » et la pré-écoute « casque-usb »
		Et ses préférences montrent l'antenne « carte-1 » et la pré-écoute « casque-usb », sur la sortie « pipewire »

	Scénario: Le seuil de silence enregistré va dans la section [silences] du fichier de configuration
		https://github.com/dascritch/machincast/issues/146 : le seuil vaut pour les audits complets suivants.

		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[silences]
			# Seuil de l'antenne du matin.
			threshold = -50
			"""
		Et les préférences seront réglées avec le seuil de silence -55,5 dB
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors les préférences ont montré le seuil de silence -50 dB
		Et le fichier de configuration contient la ligne « threshold = -55.5 »
		Et le fichier de configuration contient encore « # Seuil de l'antenne du matin. »
		Et le fichier de configuration contient encore les autres sections

	Scénario: Changer le seuil de silence relance un audit complet
		https://github.com/dascritch/machincast/issues/401 : les silences mesurés au seuil précédent ne valent plus, et
		Machin player ne fait pas auditer un sonore pour un seuil changé.

		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[silences]
			threshold = -50
			"""
		Et les préférences seront réglées avec le seuil de silence -55,5 dB
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors Machin indexer a été lancé une fois, avec « --window », « --full-audit »
		Et la barre d'état annonce « Préférences enregistrées dans …/machincast.toml ; Machin player prendra les crossfades par défaut à son prochain démarrage. Seuil de silence changé : audit complet lancé, dans sa propre fenêtre. »
		Et le menu « Maintenance » propose « Indexation rapide », « Statut des indexations… »

	Scénario: Garder le seuil de silence ne relance pas d'audit complet
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[silences]
			threshold = -50
			"""
		Et les préférences seront réglées avec le seuil de silence -50 dB
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors Machin indexer n'a pas été lancé

	Scénario: Changer le seuil de silence pendant un audit complet lancé de l'interface demande de le relancer à sa fin
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[silences]
			threshold = -50
			"""
		Et les préférences seront réglées avec le seuil de silence -55,5 dB
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Audit complet » dans le menu « Maintenance »
		Et je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors Machin indexer a été lancé une fois, avec « --window », « --full-audit »
		Et la barre d'état annonce « Préférences enregistrées dans …/machincast.toml ; Machin player prendra les crossfades par défaut à son prochain démarrage. Seuil de silence changé : l'audit complet en cours garde l'ancien seuil, relancez « Audit complet » à sa fin. »

	Scénario: Le blanc dans un sonore réglé dans les préférences va dans la section [dead_air] du fichier de configuration
		https://github.com/dascritch/machincast/issues/122 : Machin player le prend à son prochain démarrage. Les
		préférences suivantes montrent le blanc enregistré.

		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[dead_air]
			# Blanc de l'antenne de nuit.
			duration = 12
			"""
		Et les préférences seront réglées avec un blanc de 4,5 secondes sous -70 dB, qui fait passer au secours
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors les préférences ont montré un blanc de 12 secondes sous -90 dB, qui est noté seulement
		Et le fichier de configuration contient la ligne « duration = 4.5 »
		Et le fichier de configuration contient la ligne « threshold = -70 »
		Et le fichier de configuration contient la ligne « fallback = true »
		Et le fichier de configuration contient encore « # Blanc de l'antenne de nuit. »
		Et le fichier de configuration donne un blanc de 4,5 secondes sous -70 dB, qui fait passer au secours
		Et le fichier de configuration contient encore les autres sections
		Quand je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors les préférences suivantes ont montré un blanc de 4,5 secondes sous -70 dB, qui fait passer au secours

	Scénario: Régler d'autres préférences garde le blanc dans un sonore du fichier de configuration
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[dead_air]
			duration = 12
			threshold = -80
			fallback = true
			"""
		Et les préférences seront réglées avec le seuil de silence -55,5 dB
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors le fichier de configuration donne un blanc de 12 secondes sous -80 dB, qui fait passer au secours

	Scénario: La durée de péremption réglée dans les préférences va dans la section [database], et les fiches la suivent
		https://github.com/dascritch/machincast/issues/268 : Machin purge la prend à son prochain passage.

		Étant donné la durée de péremption du fichier de configuration de l'interface est de 30 jours
		Et les préférences seront réglées avec la durée de péremption de 90 jours
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors les préférences ont montré la durée de péremption de 30 jours
		Et le fichier de configuration contient la ligne « retention = 90 »
		Et la durée de péremption de l'interface est de 90 jours

	Scénario: Les lignes chargées à la fois, réglées dans les préférences, vont dans la section [interface], et les fiches les suivent
		https://github.com/dascritch/machincast/issues/383

		Étant donné les préférences seront réglées avec 300 lignes chargées à la fois
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors les préférences ont montré 1000 lignes chargées à la fois
		Et le fichier de configuration contient la ligne « table_rows = 300 »
		Et les fiches de l'interface chargent 300 lignes à la fois

	Scénario: Le voyant « Saturation » réglé dans les préférences va dans la section [interface], et l'onglet Antenne le suit aussitôt
		https://github.com/dascritch/machincast/issues/191 : le voyant reste affiché par défaut.

		Étant donné les préférences seront réglées avec le voyant « Saturation » caché
		Quand la fenêtre de l'interface s'ouvre
		Alors le voyant « Saturation » de l'antenne est affiché dans l'onglet
		Quand je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors les préférences ont montré le voyant « Saturation » affiché
		Et le fichier de configuration contient la ligne « clipping = false »
		Et le fichier de configuration contient encore les autres sections
		Et le voyant « Saturation » de l'antenne est caché dans l'onglet

	Scénario: L'onglet Antenne s'ouvre sans le voyant « Saturation » quand la configuration le cache
		Étant donné le fichier de configuration de l'interface, avec :
			"""
			[interface]
			clipping = false
			"""
		Quand la fenêtre de l'interface s'ouvre
		Alors le voyant « Saturation » de l'antenne est caché dans l'onglet
		Et le voyant « Blanc » de l'antenne est affiché dans l'onglet

	# ─── Fenêtre des préférences ───────────────────────────────

	Scénario: La page « Crossfades » montre les réglages, et donne ceux qui sont saisis
		Les crossfades ont leur propre page, la première (https://github.com/dascritch/machincast/issues/234).

		Quand la fenêtre des préférences s'ouvre sur : granularité « tenth », maximum 5 s, début par défaut 1,5 s, fin par défaut aucune
		Alors elle s'intitule « Paramètres du service », avec les pages « Crossfades », « Audio »
		Et elle montre : granularité « Au dixième de seconde », maximum « 5,0 s », début par défaut « 1,5 s », fin par défaut aucune
		Et son maximum se règle par pas de 0,1 s, à partir de 0,1 s
		Quand j'y choisis la granularité « À la seconde »
		Alors son maximum se règle par pas de 1 s, à partir de 1 s
		Quand j'y saisis le maximum 3
		Et j'y retire la durée de début par défaut
		Et j'y saisis la durée de fin par défaut 2
		Alors elle montre : granularité « À la seconde », maximum « 3 s », début par défaut aucune, fin par défaut « 2 s »
		Quand j'y clique sur « OK »
		Alors elle a donné : granularité « second », maximum 3 s, début par défaut aucune, fin par défaut 2 s

	Scénario: La page « Crossfades » montre les positions des fondus, et donne celles qui sont choisies
		Quand la fenêtre des préférences s'ouvre sur : granularité « tenth », maximum 5 s, début par défaut 2 s, fin par défaut 4 s
		Alors le fade-in se propose « commence », « est en cours », « se termine » au début détecté, et « se termine » est choisi
		Et le fade-out se propose « commence », « est en cours », « se termine » à la fin détectée, et « commence » est choisi
		Quand j'y choisis le fade-in « est en cours » et le fade-out « se termine »
		Et j'y clique sur « OK »
		Alors elle a donné les positions : fade-in « ongoing », fade-out « ends »

	Scénario: La frise de démonstration montre où tombent les fondus, et suit les réglages
		Un sonore de démonstration de 30 secondes, aux silences détectés de 3 s au début et 4 s à la fin, retirés à
		l'antenne : son début détecté est à 3 s, sa fin détectée à 26 s. Ses crossfades sont les durées par défaut
		saisies, même décochées.

		Quand la fenêtre des préférences s'ouvre sur : granularité « tenth », maximum 5 s, début par défaut 2 s, fin par défaut 4 s
		Alors la frise de démonstration montre le fade-in de 1 à 3 s, et le fade-out de 26 à 30 s
		Et la frise de démonstration a sa forme d'onde, sans tête de lecture
		Quand j'y choisis le fade-in « commence » et le fade-out « se termine »
		Alors la frise de démonstration montre le fade-in de 3 à 5 s, et le fade-out de 22 à 26 s
		Quand j'y choisis le fade-in « est en cours » et le fade-out « est en cours »
		Alors la frise de démonstration montre le fade-in de 2 à 4 s, et le fade-out de 24 à 28 s
		Quand j'y retire la durée de début par défaut
		Et j'y saisis la durée de fin par défaut 2
		Alors la frise de démonstration montre le fade-in de 2 à 4 s, et le fade-out de 25 à 27 s

	Scénario: Les positions enregistrées vont dans la section [crossfades] du fichier de configuration
		Étant donné les positions des fondus seront réglées : fade-in « ongoing », fade-out « ends »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors le fichier de configuration contient la ligne « fade_in_position = "ongoing" »
		Et le fichier de configuration contient la ligne « fade_out_position = "ends" »
		Et le fichier de configuration donne les positions des fondus : fade-in « ongoing », fade-out « ends »

	Scénario: Une durée par défaut ne dépasse pas le maximum
		Quand la fenêtre des préférences s'ouvre sur : granularité « tenth », maximum 5 s, début par défaut 4 s, fin par défaut 5 s
		Et j'y saisis le maximum 3
		Alors elle montre : granularité « Au dixième de seconde », maximum « 3,0 s », début par défaut « 3,0 s », fin par défaut « 3,0 s »

	Plan du scénario: La fenêtre des préférences, modale, donne ses réglages sur « OK », et rien sur « Annuler »
		Quand je réponds « <bouton> » à la fenêtre des préférences ouverte sur : granularité « second », maximum 8 s, début par défaut 2 s, fin par défaut aucune
		Alors les réglages donnés sont <donnes>

		Exemples:
			| bouton  | donnes                                                                               |
			| OK      | granularité « second », maximum 8 s, début par défaut 2 s, fin par défaut aucune |
			| Annuler | aucun                                                                                |

	Scénario: La page « Interface » montre le voyant « Saturation », et donne ce qui est coché
		Quand la fenêtre des préférences s'ouvre sur le voyant « Saturation » affiché
		Alors elle montre la case « Afficher le voyant de saturation de l'onglet Antenne », cochée
		Quand j'y décoche la case du voyant « Saturation »
		Et j'y clique sur « OK »
		Alors elle a donné le voyant « Saturation » caché

	Scénario: La page « Interface » montre les suggestions au lancement, et donne ce qui est coché
		https://github.com/dascritch/machincast/issues/119

		Quand la fenêtre des préférences s'ouvre sur les suggestions au lancement actives
		Alors elle montre la case des suggestions « Proposer au lancement ce qui manque pour démarrer », cochée
		Quand j'y décoche la case des suggestions au lancement
		Et j'y clique sur « OK »
		Alors elle a donné les suggestions au lancement éteintes

	Scénario: Le seuil de silence est à la page « Crossfades », avec les fondus qu'il place ; le blanc reste à la page « Audio »
		https://github.com/dascritch/machincast/issues/324
		Quand la fenêtre des préférences s'ouvre sur le seuil de silence -40 dB
		Alors le champ « silence_threshold » est à la page « Crossfades »
		Et le champ « dead_air_duration » est à la page « Audio »
		Et le champ « dead_air_threshold » est à la page « Audio »

	Scénario: La page « Crossfades » montre le seuil de silence, et donne celui qui est saisi
		Quand la fenêtre des préférences s'ouvre sur le seuil de silence -40 dB
		Alors elle montre le seuil de silence « -40,0 dB », réglable de -100,0 à -0,1 dB
		Quand j'y saisis le seuil de silence -55,5
		Et j'y clique sur « OK »
		Alors elle a donné le seuil de silence -55,5 dB

	Plan du scénario: La page « Audio » montre le blanc dans un sonore, et donne celui qui est saisi
		Quand la fenêtre des préférences s'ouvre sur un blanc de <duree> secondes sous <seuil> dB, qui <suite>
		Alors elle montre un blanc de « <duree_montree> », réglable de 1,0 à 300,0 s, sous « <seuil_montre> », réglable de -100,0 à -0,1 dB, et le passage au secours <case>
		Quand j'y saisis un blanc de 4,5 secondes sous -70,5 dB, et <action> le passage au secours
		Et j'y clique sur « OK »
		Alors elle a donné un blanc de 4,5 secondes sous -70,5 dB, qui <donne>

		Exemples:
			| duree | seuil | suite                   | duree_montree | seuil_montre | case    | action  | donne                   |
			| 10    | -90   | est noté seulement      | 10,0 s        | -90,0 dB     | décoché | coche   | fait passer au secours  |
			| 12    | -80   | fait passer au secours  | 12,0 s        | -80,0 dB     | coché   | décoche | est noté seulement      |

	Scénario: La page « Interface » montre les lignes chargées à la fois, et donne celles qui sont saisies
		Quand la fenêtre des préférences s'ouvre sur 1000 lignes chargées à la fois
		Alors elle montre « 1000 » lignes chargées à la fois, réglables de 100 à 1000000
		Quand j'y saisis 2500 lignes chargées à la fois
		Et j'y clique sur « OK »
		Alors elle a donné 2500 lignes chargées à la fois

	Scénario: La page « Base » montre la durée de péremption, et donne celle qui est saisie
		Quand la fenêtre des préférences s'ouvre sur la durée de péremption de 60 jours
		Alors elle montre la durée de péremption « 60 jours », réglable de 1 à 3650 jours
		Quand j'y saisis la durée de péremption de 90 jours
		Et j'y clique sur « OK »
		Alors elle a donné la durée de péremption de 90 jours

	Scénario: La page « Audio » montre les cartes son, chacune grisée dans l'autre choix, et la sortie factice
		Étant donné les périphériques audio du poste :
			| identifiant       | nom           |
			| carte-1           | Carte 1       |
			| casque-usb        | Casque USB    |
			| preecoute-factice | Haut-parleurs |
		Quand la fenêtre des préférences s'ouvre sur l'antenne « carte-1 » et la pré-écoute « preecoute-factice »
		Alors elle s'intitule « Paramètres du service », avec les pages « Crossfades », « Audio »
		Et le choix de l'antenne propose :
			| sortie         | état     |
			| Carte 1        | active   |
			| Casque USB     | active   |
			| Haut-parleurs  | inactive |
			| Sortie factice | active   |
		Et le choix de la pré-écoute propose :
			| sortie         | état     |
			| Haut-parleurs  | active   |
			| Carte 1        | inactive |
			| Casque USB     | active   |
			| Sortie factice | active   |
		Quand j'y choisis pour l'antenne « Casque USB »
		Alors le choix de la pré-écoute propose :
			| sortie         | état     |
			| Haut-parleurs  | active   |
			| Carte 1        | active   |
			| Casque USB     | inactive |
			| Sortie factice | active   |
		Quand j'y clique sur « OK »
		Alors elle a donné l'antenne « casque-usb » et la pré-écoute « preecoute-factice »

	Scénario: Une antenne non renseignée se propose « (à renseigner) », et un périphérique absent « (introuvable) »
		Étant donné les périphériques audio du poste :
			| identifiant | nom        |
			| casque-usb  | Casque USB |
		Quand la fenêtre des préférences s'ouvre sur l'antenne non renseignée et la pré-écoute « debranche »
		Alors le choix de l'antenne propose :
			| sortie         | état   |
			| (à renseigner) | active |
			| Casque USB     | active |
			| Sortie factice | active |
		Et le choix de la pré-écoute propose :
			| sortie                  | état   |
			| debranche (introuvable) | active |
			| Casque USB              | active |
			| Sortie factice          | active |
		Quand j'y clique sur « OK »
		Alors elle a donné l'antenne non renseignée et la pré-écoute « debranche »

	Scénario: Un même périphérique ne peut pas servir à l'antenne et à la pré-écoute
		Étant donné les périphériques audio du poste :
			| identifiant | nom        |
			| casque-usb  | Casque USB |
		Quand la fenêtre des préférences s'ouvre sur l'antenne « casque-usb » et la pré-écoute « casque-usb »
		Alors son bouton « OK » est inactif

	# ─── Icône de l'interface (https://github.com/dascritch/machincast/issues/111) ───

	Scénario: L'icône choisie dans les préférences va dans la section [interface], et l'application la prend aussitôt
		Étant donné une image PNG « …/logo.png »
		Et les préférences seront réglées avec l'icône « …/logo.png »
		Quand la fenêtre de l'interface s'ouvre
		Alors l'application a l'icône de MachinCast
		Quand je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors les préférences ont montré l'icône de MachinCast
		Et le fichier de configuration donne l'icône « …/logo.png »
		Et le fichier de configuration contient encore les autres sections
		Et l'application a l'icône « …/logo.png »

	Scénario: Les raccourcis déjà installés prennent aussitôt l'icône choisie, sans qu'aucun soit créé
		Étant donné une image PNG « …/logo.png »
		Et le raccourci de MachinCast installé dans le menu des applications
		Et les préférences seront réglées avec l'icône « …/logo.png »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors le raccourci du menu des applications a l'icône « …/logo.png »
		Et il n'y a pas de raccourci de MachinCast sur le bureau
		Et la barre d'état dit « Icône mise à jour dans le menu des applications »

	Scénario: Le raccourci du bureau prend l'icône choisie, et reste exécutable
		Étant donné une image PNG « …/logo.png »
		Et le raccourci de MachinCast installé dans le menu des applications
		Et le raccourci de MachinCast installé sur le bureau
		Et les préférences seront réglées avec l'icône « …/logo.png »
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors le raccourci du menu des applications a l'icône « …/logo.png »
		Et le raccourci du bureau a l'icône « …/logo.png », et reste exécutable
		Et la barre d'état dit « Icône mise à jour dans le menu des applications et sur le bureau »

	Scénario: Revenir à l'icône de MachinCast retire la clé, et les raccourcis la reprennent
		Étant donné une image PNG « …/logo.png »
		Et le fichier de configuration de l'interface a l'icône « …/logo.png »
		Et le raccourci de MachinCast installé dans le menu des applications
		Et les préférences seront réglées avec l'icône de MachinCast
		Quand la fenêtre de l'interface s'ouvre
		Alors l'application a l'icône « …/logo.png »
		Quand je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors les préférences ont montré l'icône « …/logo.png »
		Et le fichier de configuration n'a pas d'icône
		Et l'application a l'icône de MachinCast
		Et le raccourci du menu des applications a l'icône de MachinCast

	Scénario: Garder la même icône ne réécrit pas les raccourcis
		Étant donné une image PNG « …/logo.png »
		Et le fichier de configuration de l'interface a l'icône « …/logo.png »
		Et le raccourci de MachinCast installé dans le menu des applications
		Et les préférences seront réglées avec le voyant « Saturation » caché
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors le raccourci du menu des applications a l'icône de MachinCast
		Et la barre d'état ne dit pas « Icône mise à jour »

	Scénario: Une icône introuvable au lancement laisse celle de MachinCast, et la barre d'état le dit
		Étant donné le fichier de configuration de l'interface a l'icône « …/disparu.png »
		Quand la fenêtre de l'interface s'ouvre
		Alors l'application a l'icône de MachinCast
		Et la barre d'état dit « Icône …/disparu.png illisible ou introuvable : icône de MachinCast à la place. »

	Scénario: La page « Interface » montre l'icône, en fait choisir une autre, et donne celle qui est choisie
		Étant donné une image PNG « …/logo.png »
		Quand la fenêtre des préférences s'ouvre sur l'icône de MachinCast
		Alors elle montre l'icône de MachinCast
		Et son bouton « Icône de MachinCast » est inactif
		Quand j'y choisis l'image « …/logo.png »
		Alors elle montre l'icône « …/logo.png »
		Et son bouton « Icône de MachinCast » est actif
		Quand j'y clique sur « OK »
		Alors elle a donné l'icône « …/logo.png »

	Scénario: Le bouton « Icône de MachinCast » revient à l'icône par défaut
		Étant donné une image PNG « …/logo.png »
		Quand la fenêtre des préférences s'ouvre sur l'icône « …/logo.png »
		Alors elle montre l'icône « …/logo.png »
		Quand j'y clique sur le bouton « Icône de MachinCast »
		Alors elle montre l'icône de MachinCast
		Quand j'y clique sur « OK »
		Alors elle a donné l'icône de MachinCast

	Scénario: Une image illisible n'est pas prise, et la page le dit
		Étant donné un fichier « …/faux.png » qui n'est pas une image
		Quand la fenêtre des préférences s'ouvre sur l'icône de MachinCast
		Et j'y choisis l'image « …/faux.png »
		Alors elle montre l'icône de MachinCast
		Et elle signale « Image illisible : …/faux.png »

	Scénario: Renoncer au choix d'une image ne change rien
		Étant donné une image PNG « …/logo.png »
		Quand la fenêtre des préférences s'ouvre sur l'icône « …/logo.png »
		Et j'y renonce au choix d'une image
		Alors elle montre l'icône « …/logo.png »

	# ─── Deux fenêtres (https://github.com/dascritch/machincast/issues/389) ───

	Plan du scénario: Chaque fenêtre ne montre que ses réglages
		Quand j'ouvre la fenêtre des <fenêtre>
		Alors son titre est « <titre> »
		Et ses pages sont « <pages> »
		Et elle montre <montrés>
		Et elle cache <cachés>

		Exemples:
			| fenêtre                    | titre                       | pages                                       | montrés                                                        | cachés                                                                 |
			| préférences de l'interface | Préférences de l'interface  | Crossfades et silences, Interface, Audio, Base | la granularité, le seuil de silence, la pré-écoute              | le maximum, les durées par défaut, les positions, le blanc, l'antenne, le type de sortie |
			| paramètres du service      | Paramètres du service       | Crossfades, Audio                           | le maximum, les durées par défaut, les positions, le blanc, l'antenne, le type de sortie | la granularité, le seuil de silence, la pré-écoute              |

	Scénario: Les paramètres du service rendent tels quels les réglages de l'interface qu'ils ne montrent pas
		Quand j'ouvre la fenêtre des paramètres du service, sur une granularité « second », un seuil de silence de -55 dB et la pré-écoute « casque-usb »
		Et je clique sur « OK » des préférences ouvertes
		Alors les réglages rendus gardent la granularité « second », le seuil de silence de -55 dB et la pré-écoute « casque-usb »
