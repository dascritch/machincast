# language: fr
Fonctionnalité: Écran de simulation
	En tant que programmateur de l'antenne,
	je veux lancer une simulation depuis l'interface et en exporter le résultat,
	afin de vérifier une grille sans terminal.

	https://github.com/dascritch/machincast/issues/37, spec § 8.7.
	L'onglet « Simulation », qui se ferme, s'ouvre par « Affichage → Ouvrir l'onglet Simulation ». On y règle le début et la fin ;
	« Simuler » lance Machin lecture --simulation dans un processus à part, ses sorties dans un répertoire temporaire,
	puis la table montre les passages de son CSV, et la liste, ses alertes et incidents. « Exporter… » enregistre
	le résultat en .csv, .pls ou .html, au choix du filtre du sélecteur de fichier.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et le fichier de test « sain.flac » copié en « …/musique/minuit.flac »
		Et le fichier de test « sain.flac » copié en « …/cafe/jingle.flac »
		Et les sonores :
			| artiste     | titre         | type    | etat  | duree | emplacement           |
			| Les Gaufres | Café à minuit | fichier | actif | 60    | …/musique/minuit.flac |
			|             | Jingle        | fichier | actif | 60    | …/cafe/jingle.flac    |
		Et la banque « Habillage », séquentielle, sans nom public, avec « Café à minuit », « Jingle »
		Et les événements :
			| nom      | nom_public | priorite    | debut | fin | jours |
			| Continue |            | fil_musical |       |     |       |
		Et l'événement « Continue » joue la banque « Habillage »
		Et un Machin lecture qui simule sur la base de test

	# ─── Ouverture ─────────────────────────────────────────────

	Scénario: L'onglet « Simulation » s'ouvre par le menu Affichage, une seule fois, et se ferme
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Alors l'onglet ouvert est « Simulation »
		Et seul l'onglet « Simulation » a un bouton de fermeture
		Quand j'ouvre l'onglet « Sonores »
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Alors l'onglet ouvert est « Simulation »
		Et la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Incidents », « Simulation »
		Quand je ferme l'onglet « Simulation »
		Alors la fenêtre a les onglets « Accueil », « Événements », « Séquences », « Banques », « Sonores », « Incidents »

	Scénario: La période proposée commence à l'heure qu'il est, à la minute, et dure un jour
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Alors la simulation est réglée du « 2026-10-21 09:00 » au « 2026-10-22 09:00 »
		Et le compte de la simulation est « Réglez la période, puis cliquez sur « Simuler ». »
		Et le bouton « Exporter… » de la simulation est inactif

	# ─── Simulation ────────────────────────────────────────────

	Scénario: La simulation montre les passages qui seraient joués, sans rien écrire en base
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et je règle la simulation du « 2026-10-21 09:00 » au « 2026-10-21 09:03 »
		Et je lance la simulation
		Alors la simulation montre les passages :
			| Début               | Fin                 | Artiste     | Titre         | Emplacement           | Événement | Séquence | Banque    |
			| 2026-10-21 09:00:00 | 2026-10-21 09:01:00 | Les Gaufres | Café à minuit | …/musique/minuit.flac | Continue  |          | Habillage |
			| 2026-10-21 09:01:00 | 2026-10-21 09:02:00 |             | Jingle        | …/cafe/jingle.flac    | Continue  |          | Habillage |
			| 2026-10-21 09:02:00 | 2026-10-21 09:03:00 | Les Gaufres | Café à minuit | …/musique/minuit.flac | Continue  |          | Habillage |
		Et le compte de la simulation est « 3 passages, aucune alerte ni incident. Rien n'a été écrit en base. »
		Et la simulation ne signale rien
		Et l'airplay de la base est vide
		Et le bouton « Exporter… » de la simulation est actif

	Scénario: La simulation signale ses alertes et incidents
		Étant donné le sonore « Café à minuit » est à l'état « desactive » en base
		Et le sonore « Jingle » est à l'état « desactive » en base
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et je règle la simulation du « 2026-10-21 09:00 » au « 2026-10-21 09:01 »
		Et je lance la simulation
		Alors la simulation montre aucun passage
		Et le compte de la simulation est « Aucun passage, 1 alerte ou incident. Rien n'a été écrit en base. »
		Et la simulation signale « 2026-10-21 09:00:00 : alerte : silence : rien à diffuser dans le fil musical »

	Scénario: Une fin qui ne suit pas le début ne lance rien
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et je règle la simulation du « 2026-10-21 09:00 » au « 2026-10-21 09:00 »
		Et je lance la simulation
		Alors le compte de la simulation est « La fin doit suivre le début. »
		Et aucune simulation n'a été lancée

	Scénario: Une simulation impossible le dit, avec le message de Machin lecture
		Étant donné un Machin lecture qui simule sans base joignable
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et je règle la simulation du « 2026-10-21 09:00 » au « 2026-10-21 09:03 »
		Et je lance la simulation
		Alors le compte de la simulation commence par « Simulation impossible : base de données injoignable »
		Et le bouton « Exporter… » de la simulation est inactif

	Scénario: Une nouvelle simulation remplace la précédente
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et je règle la simulation du « 2026-10-21 09:00 » au « 2026-10-21 09:03 »
		Et je lance la simulation
		Et je règle la simulation du « 2026-10-21 09:00 » au « 2026-10-21 09:01 »
		Et je lance la simulation
		Alors la simulation montre les titres « Café à minuit »
		Et le compte de la simulation est « 1 passage, aucune alerte ni incident. Rien n'a été écrit en base. »
		Et 2 simulations ont été lancées

	Scénario: Une nouvelle simulation efface les alertes de la précédente
		Étant donné le sonore « Café à minuit » est à l'état « desactive » en base
		Et le sonore « Jingle » est à l'état « desactive » en base
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et je règle la simulation du « 2026-10-21 09:00 » au « 2026-10-21 09:01 »
		Et je lance la simulation
		Et le sonore « Café à minuit » est à l'état « actif » en base
		Et je lance la simulation
		Alors la simulation ne signale rien

	Scénario: Pendant une simulation, on ne relance ni n'exporte ; fermer l'onglet l'arrête
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et je règle la simulation du « 2026-10-21 09:00 » au « 2026-10-21 09:03 »
		Et je lance la simulation
		Et Machin lecture attend avant de simuler
		Et je lance la simulation, sans attendre sa fin
		Alors le compte de la simulation est « Simulation en cours… »
		Et le bouton « Simuler » de la simulation est inactif
		Et le bouton « Exporter… » de la simulation est inactif
		Quand je ferme l'onglet « Simulation »
		Alors le Machin lecture de la simulation est arrêté
		Et le répertoire temporaire de la simulation n'existe plus

	Scénario: Un Machin lecture qui échoue après avoir écrit ses sorties ne donne aucun résultat
		Étant donné un Machin lecture qui échoue après avoir simulé
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et je règle la simulation du « 2026-10-21 09:00 » au « 2026-10-21 09:03 »
		Et je lance la simulation
		Alors le compte de la simulation est « Simulation impossible : dernier échec »
		Et la simulation montre aucun passage
		Et le bouton « Exporter… » de la simulation est inactif
		Et le bouton « Simuler » de la simulation est actif

	Scénario: La simulation est celle de Machin lecture, par le Python de l'interface, avec sa configuration
		Alors la commande de simulation pour « /etc/machincast.toml » est Machin lecture --config « /etc/machincast.toml »

	# ─── Export ────────────────────────────────────────────────

	Plan du scénario: Le résultat s'exporte au format du filtre choisi, avec son extension
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et je règle la simulation du « 2026-10-21 09:00 » au « 2026-10-21 09:03 »
		Et je lance la simulation
		Et j'exporte la simulation sous « <nom> », avec le filtre « <filtre> »
		Alors le sélecteur d'export a proposé « simulation-2026-10-21T0900-2026-10-21T0903.csv »
		Et le fichier « <fichier> » exporté est la sortie <format> de la simulation
		Et la barre d'état a annoncé l'export de la simulation dans « <fichier> »

		Exemples:
			| nom             | filtre                | fichier             | format |
			| grille.csv      | Tableur CSV (*.csv)   | grille.csv          | .csv   |
			| grille          | Playlist PLS (*.pls)  | grille.pls          | .pls   |
			| grille.html     | Page HTML (*.html)    | grille.html         | .html  |
			| matinale.flac   | Tableur CSV (*.csv)   | matinale.flac.csv   | .csv   |

	Scénario: Abandonner l'export n'écrit rien
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et je règle la simulation du « 2026-10-21 09:00 » au « 2026-10-21 09:03 »
		Et je lance la simulation
		Et j'abandonne l'export de la simulation
		Alors aucun fichier n'a été exporté
		Et la barre d'état n'a rien annoncé

	Scénario: Fermer l'onglet efface le répertoire temporaire de la simulation
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Ouvrir l'onglet Simulation » dans le menu « Affichage »
		Et je règle la simulation du « 2026-10-21 09:00 » au « 2026-10-21 09:03 »
		Et je lance la simulation
		Et je ferme l'onglet « Simulation »
		Alors le répertoire temporaire de la simulation n'existe plus
