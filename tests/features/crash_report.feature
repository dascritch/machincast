# language: fr
Fonctionnalité: Rapports de crash
	En tant que développeur,
	je veux un rapport détaillé de chaque plantage d'un binaire,
	afin de reproduire les conditions expérimentales.

	https://github.com/dascritch/machincast/issues/342. Un plantage laisse un fichier horodaté dans crash-dump/, à la
	racine du dépôt du code : « <binaire>-<démarrage>-<pid>.txt ». Il donne le binaire, sa version, son pid et ses
	options, l'heure de son démarrage et celle du plantage, la pile Python, ce qu'ont rendu PostgreSQL, GLib et
	GStreamer, le système ou un programme lancé, et les versions des outils. Machin indexer y ajoute le fichier en cours
	d'analyse ; Machin interface, ses cartes son, la sortie de « wpctl status » et le sonore en pré-écoute ; Machin
	player, sa carte son, la sortie de « wpctl status », et les sonores précédent, en cours et les 5 suivants annoncés.
	Un signal fatal, ou un arrêt sans un mot, laisse un rapport en cours, que le lancement suivant du même binaire
	achève. Les scénarios écrivent leurs rapports dans le répertoire du scénario ; « <pid> » est celui du lancement,
	« <version> » la version de MachinCast, et « …/ » le répertoire du scénario.

	Contexte:
		Étant donné une configuration de test pour les binaires

	Scénario: Une erreur imprévue laisse un rapport horodaté, avec la pile Python et les versions
		Étant donné Machin purge qui plante sur l'erreur imprévue « panne imitée »
		Quand je lance « Machin purge », qui plante
		Alors crash-dump contient un seul rapport, celui de « Machin_purge » pour ce lancement, et aucun rapport en cours
		Et le rapport dit :
			| texte                                     |
			| Rapport de crash de MachinCast             |
			| Binaire : Machin_purge <version>, pid <pid> |
			| Démarrage :                                |
			| Plantage :                                 |
			| Pile Python                                |
			| RuntimeError: panne imitée                 |
			| in imitated_failure                        |
			| Versions                                   |
			| MachinCast <version>                       |
			| psycopg                                    |
			| libpq                                      |
		Et le journal a signalé le rapport de crash écrit

	Scénario: Une erreur de PostgreSQL donne ce que PostgreSQL a rendu
		Étant donné Machin purge qui plante sur une requête PostgreSQL vers une table absente
		Quand je lance « Machin purge », qui plante
		Alors le rapport dit :
			| texte                                         |
			| Erreurs hors de MachinCast                     |
			| PostgreSQL (psycopg.errors.UndefinedTable) : SQLSTATE 42P01 |
			| message_primary : relation "table_absente" does not exist |
			| statement_position :                           |

	Scénario: Une erreur de GStreamer donne son domaine, son code et la version de GStreamer
		Étant donné Machin purge qui plante sur un pipeline GStreamer impossible
		Quand je lance « Machin purge », qui plante
		Alors le rapport dit :
			| texte                       |
			| Erreurs hors de MachinCast   |
			| GLib (gi.repository.GLib.GError) : domain gst_parse_error |
			| GStreamer 1.                |
			| PyGObject                   |

	Scénario: Un fil qui plante sans arrêter le binaire ne laisse pas de rapport
		Seuls les plantages comptent : le journal montre l'exception du fil.

		Étant donné Machin purge dont un fil plante sur l'erreur imprévue « panne du fil »
		Quand je lance « Machin purge »
		Alors le lancement se termine avec le code 0
		Et crash-dump ne contient aucun rapport, ni aucun rapport en cours

	Scénario: Un lancement sans plantage ne laisse ni rapport ni rapport en cours
		Quand je lance « Machin purge »
		Alors le lancement se termine avec le code 0
		Et crash-dump ne contient aucun rapport, ni aucun rapport en cours

	Scénario: Pendant le lancement, un rapport en cours attend un signal fatal
		Étant donné Machin purge qui regarde crash-dump pendant qu'il tourne
		Quand je lance « Machin purge »
		Alors crash-dump contenait, pendant le lancement, un rapport en cours de « Machin_purge » pour ce lancement

	Scénario: Un signal fatal laisse sa pile dans le rapport en cours, que le lancement suivant achève
		Étant donné un binaire « Machin_essai » qui note « /srv/musique/a.flac » comme fichier en cours d'analyse, puis plante sur un signal SIGSEGV
		Quand le lancement suivant de « Machin_essai » achève les rapports en cours
		Alors crash-dump contient un seul rapport, celui de « Machin_essai » pour le lancement planté, et aucun rapport en cours
		Et le rapport dit :
			| texte                              |
			| Binaire : Machin_essai              |
			| Fichier en cours d'analyse          |
			| /srv/musique/a.flac                 |
			| Fatal Python error: Segmentation fault |
			| Fin : inconnue                      |

	Scénario: Un arrêt sans un mot laisse le rapport en cours, que le lancement suivant achève
		Étant donné un binaire « Machin_essai » qui note « /srv/musique/b.flac » comme fichier en cours d'analyse, puis est tué par kill -9
		Quand le lancement suivant de « Machin_essai » achève les rapports en cours
		Alors le rapport dit :
			| texte                       |
			| /srv/musique/b.flac          |
			| Fin : inconnue               |

	Scénario: Le rapport en cours d'un lancement qui tourne encore n'est pas achevé
		Étant donné un binaire « Machin_essai » qui tourne encore, avec son rapport en cours
		Quand le lancement suivant de « Machin_essai » achève les rapports en cours
		Alors crash-dump ne contient aucun rapport, mais un rapport en cours

	Scénario: Sans droit d'écriture dans le dépôt, les rapports vont dans /tmp/machincast/crash-dump
		Étant donné un dépôt du code sans droit d'écriture
		Et Machin purge qui plante sur l'erreur imprévue « panne imitée »
		Quand je lance « Machin purge », qui plante
		Alors le répertoire de secours contient le rapport de « Machin_purge » pour ce lancement

	# ─── Ce que chaque binaire ajoute ──────────────────────────

	Scénario: Machin indexer donne le fichier qu'il examinait
		Étant donné une banque « Jingles » alimentée par le répertoire « jingles », où est le fichier « intro.flac »
		Et Machin indexer qui plante en enregistrant un fichier
		Quand je lance « Machin indexer », qui plante
		Alors le rapport dit :
			| texte                       |
			| Fichier en cours d'analyse  |
			| jingles/intro.flac          |

	Scénario: Machin interface donne ses cartes son, la sortie de wpctl status et le sonore en pré-écoute
		Étant donné le poste à l'heure de Paris
		Et l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et les événements :
			| name        | public_name | priority               | starts_at | ends_at | days |
			| Fil de jour |             | background_programming |           |         |      |
		Et le lancement surveillé, comme « Machin_interface »
		Et « wpctl status » qui répond « PipeWire 'pipewire-0' »
		Et le sonore « Café à minuit » de « Les Gaufres », pour une copie du fichier de test « sain.flac »
		Quand la fenêtre de l'interface s'ouvre
		Et je demande la pré-écoute du sonore « Café à minuit »
		Et une erreur imprévue « panne de l'interface » arrête le lancement surveillé
		Alors le rapport dit :
			| texte                              |
			| RuntimeError: panne de l'interface |
			| Cartes son                         |
			| Antenne : sortie dummy             |
			| Pré-écoute : sortie                |
			| wpctl status                       |
			| PipeWire 'pipewire-0'              |
			| Sonore en pré-écoute               |
			| Café à minuit : …/                 |

	Scénario: Machin player donne les sonores précédent, en cours et à venir, à chaque début de sonore
		Étant donné le poste à l'heure de Paris
		Et l'horloge du binaire au « 2026-10-14 19:59:50 »
		Et le lancement surveillé, comme « Machin_player »
		Et le fil musical permanent « Continue », avec les sonores « f1 », « f2 », « f3 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 3 pas d'une seconde
		Alors le rapport en cours dit :
			| texte                                                 |
			| Sonores de l'antenne                                  |
			| Événement / séquence / banque / sonore / fichier      |
			| Précédent : Continue / — / — / f                      |
			| À l'antenne : Continue / — / — / f                    |
			| Suivant 1 : Continue / — / — / f                      |
