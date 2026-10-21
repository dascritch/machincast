# language: fr
Fonctionnalité: Onglets ouverts à la demande
	En tant que programmateur de l'antenne,
	je veux que les onglets « Sonores », « Marques-pages » et le calendrier ne s'ouvrent que quand je les demande,
	afin que la fenêtre ne montre au lancement que ce dont j'ai besoin chaque jour.

	https://github.com/dascritch/machincast/issues/180. Le menu « Affichage » ouvre chacun de ces onglets, ou le ramène
	au premier plan. « Sonores » et « Marques-pages » se rouvrent à leur place habituelle, après « Banques » et avant
	« Incidents » ; le calendrier, nommé « Grille horaire » dans le menu, s'ajoute après les autres onglets.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et les événements :
			| nom         | nom_public | priorite    | debut | fin | jours |
			| Fil de jour |            | fil_musical |       |     |       |
		Et les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement                  |
			| Les Gaufres | Café à minuit | fichier | actif | 214   | /srv/jingles/hiver/cafe.flac |
			| Aube        | Matin clair   | fichier | actif | 200   | /srv/jingles/hiver/matin.flac |

	Scénario: Au lancement, ni les sonores, ni les marques-pages, ni le calendrier ne sont ouverts
		Quand la fenêtre de l'interface s'ouvre
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents »
		Et aucun onglet n'a de bouton de fermeture
		Et le menu « Affichage » a les entrées :
			| entrée                          | état   | raccourci | infobulle |
			| Rafraîchir les onglets          | active | F5        |           |
			| Rechercher…                     | active | Ctrl+F    |           |
			| Ouvrir l'onglet Sonores         | active |           |           |
			| Ouvrir l'onglet Marques-pages   | active |           |           |
			| Ouvrir l'onglet Grille horaire  | active |           |           |
			| Pré-écoute…                     | active |           |           |

	Scénario: Les onglets demandés s'ouvrent à leur place, et se ferment
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Marques-pages » dans le menu « Affichage »
		Alors l'onglet ouvert est « Marques-pages »
		Quand je choisis « Ouvrir l'onglet Grille horaire » dans le menu « Affichage »
		Alors l'onglet ouvert est « Calendrier »
		Quand je choisis « Ouvrir l'onglet Sonores » dans le menu « Affichage »
		Alors l'onglet ouvert est « Sonores »
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Marques-pages », « Incidents », « Calendrier »
		Et seuls les onglets « Sonores », « Marques-pages », « Calendrier » ont un bouton de fermeture
		Quand je ferme l'onglet « Sonores »
		Et je ferme l'onglet « Marques-pages »
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Incidents », « Calendrier »

	Scénario: Un onglet déjà ouvert revient au premier plan, sans second onglet
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Sonores » dans le menu « Affichage »
		Et j'ouvre l'onglet « Accueil »
		Et je choisis « Ouvrir l'onglet Sonores » dans le menu « Affichage »
		Alors l'onglet ouvert est « Sonores »
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Incidents »

	Scénario: Une liste fermée puis rouverte garde son filtre et se relit
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Sonores » dans le menu « Affichage »
		Et je tape « Matin » dans le filtre de la liste
		Et je ferme l'onglet « Sonores »
		Et le sonore « Nuit claire » est ajouté en base
		Et je choisis « Ouvrir l'onglet Sonores » dans le menu « Affichage »
		Alors la liste montre les titres « Matin clair »
		Quand j'efface le filtre de la liste
		Alors la liste montre les titres « Matin clair », « Café à minuit », « Nuit claire »

	Scénario: Les raccourcis suivent les onglets ouverts
		https://github.com/dascritch/machincast/issues/192

		Quand la fenêtre de l'interface s'ouvre
		Et j'appuie sur « Shift+F5 »
		Alors l'onglet ouvert est « Incidents »
		Quand je choisis « Ouvrir l'onglet Sonores » dans le menu « Affichage »
		Et j'appuie sur « Shift+F6 »
		Alors l'onglet ouvert est « Incidents »
