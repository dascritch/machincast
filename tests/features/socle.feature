# language: fr
Fonctionnalité: Socle de test
	En tant que développeur de MachinCast,
	je veux que les tests disposent d'une base de test purgée, d'une horloge et d'un hasard contrôlables,
	afin que chaque test soit reproductible et indépendant des autres.

	# ─── Configuration et base de test ─────────────────────

	Scénario: Les tests utilisent la configuration de test du dépôt
		Alors la configuration de test désigne la base "machincast_test"
		Et la sortie audio des tests est "factice"

	Scénario: La connexion de test refuse la base de production
		Étant donné une configuration de test dont la base de test porte le nom de la base de production
		Quand je charge cette configuration
		Alors le chargement échoue avec un message qui mentionne "base.test"

	Scénario: La base de test est purgée entre deux scénarios
		Étant donné une base de test vide
		Quand j'enregistre deux banques
		Et la base de test est purgée
		Alors la base ne contient plus aucune banque
		Et la prochaine banque enregistrée reçoit l'identifiant 1

	# ─── Horloge ───────────────────────────────────────────

	Scénario: Une horloge fixe donne l'heure choisie et avance sur demande
		Étant donné une horloge fixée au "2026-10-19 17:59:30+02:00"
		Quand l'horloge avance de 45 secondes
		Alors l'horloge indique "2026-10-19 18:00:15+02:00"

	Scénario: Une horloge fixe refuse une heure sans fuseau
		Alors une horloge fixée au "2026-10-19 18:00:00" est refusée

	Scénario: L'horloge système donne l'heure locale avec son fuseau
		Alors l'horloge système donne une heure avec fuseau, proche de l'heure réelle

	# ─── Hasard ────────────────────────────────────────────

	Scénario: Une même graine donne les mêmes tirages
		Étant donné deux générateurs de hasard créés avec la graine 42
		Alors ils tirent les mêmes 20 sonores parmi 100

	Scénario: Deux graines différentes donnent des tirages différents
		Étant donné un générateur créé avec la graine 1 et un autre avec la graine 2
		Alors leurs 20 tirages parmi 100 diffèrent

	# ─── Sortie audio ──────────────────────────────────────

	Plan du scénario: Chaque sortie audio de la configuration correspond à un élément GStreamer
		Quand je crée la sortie audio "<sortie>" sur le périphérique "<peripherique>"
		Alors l'élément GStreamer est un "<element>"
		Et son périphérique est "<peripherique>"

		Exemples:
			| sortie     | element      | peripherique  |
			| alsa       | alsasink     | hw:1,0        |
			| pulseaudio | pulsesink    | antenne       |
			| pipewire   | pipewiresink | antenne       |

	Scénario: La sortie factice ne joue aucun son
		Quand je crée la sortie audio "factice" sans périphérique
		Alors l'élément GStreamer est un "fakesink"

	Scénario: Un son de test traverse la sortie factice jusqu'au bout
		Quand je joue un son de test d'une demi-seconde sur la sortie factice
		Alors la lecture se termine sans erreur

	Scénario: Un greffon GStreamer manquant est signalé avec le paquet à installer
		Quand je crée une sortie dont le greffon GStreamer « elementinexistant » n'est pas installé
		Alors la création échoue en nommant le paquet à installer

	# ─── Garde-fous ────────────────────────────────────────

	Scénario: Le code source ne lit l'heure et le hasard qu'à travers les modules dédiés
		Alors aucun fichier de src/ ne lit l'heure ni le hasard en dehors de machincast.horloge et machincast.hasard
