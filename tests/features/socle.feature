# language: fr
Fonctionnalité: Socle de test
	En tant que développeur de MachinCast,
	je veux que les tests disposent d'une base de test purgée, d'une horloge et d'un hasard contrôlables,
	afin que chaque test soit reproductible et indépendant des autres.

	# ─── Configuration et base de test ─────────────────────

	Scénario: Les tests utilisent la configuration de test du dépôt
		Alors la configuration de test désigne la base "machincast_test"
		Et la sortie audio des tests est "factice"

	Scénario: La configuration de test ne nomme pas la base de production du modèle
		Alors la base de production de la configuration de test n'est pas celle du modèle de configuration

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

	Scénario: Le code source n'affiche rien par print : les messages passent par logging
		Alors aucun fichier de src/ n'appelle print

	Scénario: Les messages d'un exécutable vont sur la sortie qui convient, préfixés de son nom
		Étant donné les messages configurés pour l'exécutable "Machin_essai"
		Quand le code émet une information « 3 sonores vérifiés » et une anomalie « fichier endommagé »
		Alors la sortie standard contient seulement « Machin_essai : 3 sonores vérifiés »
		Et la sortie d'erreur contient seulement « Machin_essai : fichier endommagé »

	Scénario: Les chaînes Python ne sont jamais composées avec la notation %
		Alors aucun fichier Python du dépôt ne compose une chaîne ou un message de journal avec la notation %

	# Revue de https://github.com/dascritch/machincast/pull/100, https://github.com/dascritch/machincast/issues/103 :
	# chaque opérande d'un enchaînement de and ou de or est entre parenthèses, et une expression conditionnelle ne
	# décide pas d'un appel. Les seuls appels permis dans ses branches sont les conversions int, str et bool.

	Plan du scénario: Le style des conditions se vérifie sur un extrait de code
		Quand je vérifie le style de l'extrait « <code> »
		Alors l'extrait est <verdict>

		Exemples:
			| code                                                  | verdict                                                         |
			| if (a) and (b): pass                                  | accepté                                                         |
			| if (actif is not None) and (f(actif)): pass           | accepté                                                         |
			| if a and (b): pass                                    | refusé : opérande sans parenthèses dans une condition enchaînée |
			| if (a) and f(b): pass                                 | refusé : opérande sans parenthèses dans une condition enchaînée |
			| x = ((a) or (b)) and (c)                              | accepté                                                         |
			| x = (a or b) and (c)                                  | refusé : opérande sans parenthèses dans une condition enchaînée |
			| x = (nom) or ("")                                     | accepté                                                         |
			| x = nom or ""                                         | refusé : opérande sans parenthèses dans une condition enchaînée |
			| f(a and b)                                            | refusé : opérande sans parenthèses dans une condition enchaînée |
			| assert (a) or (b)                                     | accepté                                                         |
			| y = [v for v in w if (v) and (z)]                     | accepté                                                         |
			| y = a if b else c                                     | accepté                                                         |
			| y = x if isinstance(x, int) else None                 | accepté                                                         |
			| y = None if v is None else int(str(v))                | accepté                                                         |
			| y = None if v is None else str(v)                     | accepté                                                         |
			| y = bool(v) if v else None                            | accepté                                                         |
			| y = None if i is None else lire(c, i)                 | refusé : appel dans une branche d'expression conditionnelle     |
			| y = a.strip() if a else ""                            | refusé : appel dans une branche d'expression conditionnelle     |
			| y = f"{d.isoformat()}" if d else ""                   | refusé : appel dans une branche d'expression conditionnelle     |
			| y = 0 if v is None else float(v)                      | refusé : appel dans une branche d'expression conditionnelle     |

	Scénario: Tout le code Python du dépôt suit le style des conditions
		Alors aucun fichier Python de src/ ni de tests/ n'enfreint le style des conditions

	Scénario: Les variables des scripts bash s'écrivent avec accolades
		Alors aucun script bash du dépôt n'écrit une variable sans accolades
