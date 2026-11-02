# language: fr
Fonctionnalité: Interrompre l'antenne depuis l'interface
	En tant que responsable d'antenne,
	je veux que le menu « Diffusion » propose de sauter au sonore suivant, de sauter après la séquence en cours, ou de
	couper l'événement par le fil musical, afin de corriger l'antenne sans terminal.

	https://github.com/dascritch/machincast/issues/104 et https://github.com/dascritch/machincast/issues/228,
	spec § 8.11. Les entrées suivent l'état que Machin lecture
	publie sur sa socket d'état : chacune n'est active que si son élément est à l'antenne, et son infobulle le nomme.
	Elle envoie la demande sur la socket, aussitôt, sans question ; la barre d'état l'annonce.

	Contexte:
		Étant donné l'horloge de l'interface au « 2026-10-21 09:00:00 »
		Et la socket d'état de Machin lecture ouverte pour l'interface

	Scénario: Pendant un sonore d'une séquence, les trois interruptions sont proposées, avec ce qu'elles interrompent
		Étant donné Machin lecture diffuse « Café à minuit », de la séquence « Pub », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Alors les interruptions du menu « Diffusion » sont :
			| entrée                                | état   | infobulle         |
			| ⏭ Sauter au sonore suivant              | active | « Café à minuit » |
			| ⏭ Sauter après la séquence              | active | « Pub »           |
			| ⏭ Couper l'événement par le fil musical | active | « Matinale »      |

	Scénario: Hors d'une séquence, seule l'interruption de la séquence est inactive
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Alors les interruptions du menu « Diffusion » sont :
			| entrée                                | état     | infobulle                   |
			| ⏭ Sauter au sonore suivant              | active   | « Café à minuit »           |
			| ⏭ Sauter après la séquence              | inactive | Aucune séquence à l'antenne |
			| ⏭ Couper l'événement par le fil musical | active   | « Matinale »                |

	Scénario: Dans le fil musical, couper l'événement par le fil musical est inactif
		Étant donné Machin lecture diffuse « Café à minuit », de la séquence « Pub », dans le fil musical « Continue »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Alors les interruptions du menu « Diffusion » sont :
			| entrée                                | état     | infobulle                           |
			| ⏭ Sauter au sonore suivant              | active   | « Café à minuit »                   |
			| ⏭ Sauter après la séquence              | active   | « Pub »                             |
			| ⏭ Couper l'événement par le fil musical | inactive | Le fil musical est déjà à l'antenne |

	Plan du scénario: Sans rien à l'antenne, aucune interruption n'est proposée
		Étant donné Machin lecture <situation>
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Alors les interruptions du menu « Diffusion » sont :
			| entrée                                | état     | infobulle        |
			| ⏭ Sauter au sonore suivant              | inactive | Rien à l'antenne |
			| ⏭ Sauter après la séquence              | inactive | Rien à l'antenne |
			| ⏭ Couper l'événement par le fil musical | inactive | Rien à l'antenne |

		Exemples:
			| situation      |
			| laisse un blanc |
			| s'est arrêté   |

	Plan du scénario: Chaque interruption est envoyée à Machin lecture, et annoncée
		Étant donné Machin lecture diffuse « Café à minuit », de la séquence « Pub », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et je choisis « <entrée> » dans le menu « Diffusion »
		Alors Machin lecture a reçu la demande d'interrompre « <élément> »
		Et la barre d'état a annoncé « <annonce> »
		Et aucune question n'a été posée

		Exemples:
			| entrée                                | élément   | annonce                                             |
			| ⏭ Sauter au sonore suivant              | sonore    | Saut au sonore suivant demandé.                     |
			| ⏭ Sauter après la séquence              | sequence  | Saut après la séquence demandé.                     |
			| ⏭ Couper l'événement par le fil musical | evenement | Coupure de l'événement par le fil musical demandée. |

	Scénario: Une demande que Machin lecture ne peut pas recevoir n'est pas annoncée comme envoyée
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et Machin lecture ferme sa socket d'état, juste avant que je choisisse « ⏭ Sauter au sonore suivant »
		Alors la barre d'état a annoncé « Interruption impossible : Machin lecture ne répond pas sur sa socket d'état. »

	Scénario: Les entrées suivent l'antenne
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et Machin lecture passe à un blanc
		Et l'interface a reçu l'état de Machin lecture
		Alors aucune interruption n'est active

	# ─── Clic droit sur le prochain sonore (https://github.com/dascritch/machincast/issues/257) ───
	# Le cadre « Prochain sonore » de l'onglet Antenne propose, au clic droit, sa pré-écoute, d'y sauter aussitôt, et
	# d'avancer l'événement suivant que Machin lecture annonce. La demande d'avance nomme cet événement : Machin
	# lecture l'ignore si un autre est devenu le suivant entre-temps.

	Scénario: Le clic droit sur le prochain sonore propose d'y sauter, et d'avancer l'événement suivant
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale », avant « Spot », et annonce l'événement suivant « Journal », du « 2026-10-21T12:00:00 » au « 2026-10-21T12:30:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et l'onglet Antenne a reçu l'état de Machin lecture
		Alors le clic droit sur le prochain sonore propose :
			| entrée                                                    | état   | infobulle                                                              |
			| Pré-écoute…                                               | active |                                                                        |
			| ⏭ Sauter à ce sonore                                        | active | « Spot », aussitôt : « Café à minuit » s'arrête                        |
			| ⏭ Sauter après la séquence | inactive | Aucune séquence à l'antenne |
			| ⏭ Couper l'événement par le fil musical | active | « Matinale » |
			| ⏭ Couper par le secours | inactive | Aucun événement de secours |
			| ⏭ Avancer « Journal », prévu le mercredi 21 octobre à 12:00 | active | Il commence aussitôt, au-dessus de la grille, jusqu'à sa fin, à 12:30 |

	Scénario: Sans événement suivant annoncé, l'avance est inactive
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale », avant « Spot »
		Quand la fenêtre de l'interface s'ouvre
		Et l'onglet Antenne a reçu l'état de Machin lecture
		Alors le clic droit sur le prochain sonore propose :
			| entrée                       | état     | infobulle                                 |
			| Pré-écoute…                  | active   |                                           |
			| ⏭ Sauter à ce sonore           | active   | « Spot », aussitôt : « Café à minuit » s'arrête |
			| ⏭ Sauter après la séquence | inactive | Aucune séquence à l'antenne |
			| ⏭ Couper l'événement par le fil musical | active | « Matinale » |
			| ⏭ Couper par le secours | inactive | Aucun événement de secours |
			| ⏭ Avancer l'événement suivant  | inactive | Aucun événement suivant dans les sept jours |

	Scénario: Pendant un blanc, l'événement suivant s'avance quand même, mais il n'y a rien à sauter
		Étant donné Machin lecture laisse un blanc, et annonce l'événement suivant « Journal », du « 2026-10-21T12:00:00 » au « 2026-10-21T12:30:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et l'onglet Antenne a reçu l'état de Machin lecture
		Alors le clic droit sur le prochain sonore propose :
			| entrée                                                    | état     | infobulle                                                              |
			| ⏭ Sauter à ce sonore                                        | inactive | Aucun prochain sonore                                                  |
			| ⏭ Sauter après la séquence | inactive | Rien à l'antenne |
			| ⏭ Couper l'événement par le fil musical | inactive | Rien à l'antenne |
			| ⏭ Couper par le secours | inactive | Aucun événement de secours |
			| ⏭ Avancer « Journal », prévu le mercredi 21 octobre à 12:00 | active   | Il commence aussitôt, au-dessus de la grille, jusqu'à sa fin, à 12:30 |

	Scénario: Machin lecture à l'arrêt, rien ne se demande depuis le prochain sonore
		Étant donné Machin lecture s'est arrêté
		Quand la fenêtre de l'interface s'ouvre
		Et l'onglet Antenne a reçu l'état de Machin lecture
		Alors le clic droit sur le prochain sonore propose :
			| entrée                      | état     | infobulle                     |
			| ⏭ Sauter à ce sonore          | inactive | Machin lecture ne diffuse pas |
			| ⏭ Sauter après la séquence | inactive | Rien à l'antenne |
			| ⏭ Couper l'événement par le fil musical | inactive | Rien à l'antenne |
			| ⏭ Couper par le secours | inactive | Aucun événement de secours |
			| ⏭ Avancer l'événement suivant | inactive | Machin lecture ne diffuse pas |

	Plan du scénario: Chaque entrée du clic droit sur le prochain sonore est envoyée à Machin lecture, et annoncée
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale », avant « Spot », et annonce l'événement suivant « Journal », du « 2026-10-21T12:00:00 » au « 2026-10-21T12:30:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et l'onglet Antenne a reçu l'état de Machin lecture
		Et je choisis « <entrée> » au clic droit sur le prochain sonore
		Alors Machin lecture a reçu la demande <demande>
		Et la barre d'état a annoncé « <annonce> »
		Et aucune question n'a été posée

		Exemples:
			| entrée                                                    | demande                                | annonce                                       |
			| ⏭ Sauter à ce sonore                                        | d'interrompre « sonore »               | Saut au sonore suivant demandé.               |
			| ⏭ Avancer « Journal », prévu le mercredi 21 octobre à 12:00 | d'avancer l'événement n°7              | Avance de l'événement « Journal » demandée.   |

	# ─── Coupures par le secours et par un feed (https://github.com/dascritch/machincast/issues/323) ───
	# « ⏭ Couper par le secours » est dans le menu « Diffusion » et au clic droit sur le prochain sonore : inactive sans
	# événement de secours ; avec plusieurs, un sous-menu les nomme. Au clic droit sur un feed, la coupure par son
	# stream. Le secours, ou le stream, tient l'antenne jusqu'à la fin prévue de l'événement coupé ; sous le fil
	# musical, jusqu'à l'événement suivant.

	Scénario: Avec un seul secours, l'entrée du menu « Diffusion » coupe par lui, et l'annonce
		Étant donné les événements :
			| nom            | nom_public | priorite | debut | fin | jours |
			| Coupure studio |            | secours  |       |     |       |
		Et Machin lecture diffuse « Café à minuit », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et j'ouvre le menu « Diffusion »
		Alors la coupure par le secours du menu « Diffusion » est active, sans sous-menu, avec l'infobulle « « Coupure studio », joue jusqu'à la fin prévue de l'événement coupé ; sous le fil musical, jusqu'à l'événement suivant »
		Quand je choisis « ⏭ Couper par le secours » dans le menu « Diffusion »
		Alors Machin lecture a reçu la demande de couper l'antenne par le secours « Coupure studio »
		Et la barre d'état a annoncé « Coupure par le secours « Coupure studio » demandée. »
		Et aucune question n'a été posée

	Scénario: Avec plusieurs secours, un sous-menu les nomme
		Étant donné les événements :
			| nom            | nom_public | priorite | debut | fin | jours |
			| Coupure studio |            | secours  |       |     |       |
			| Attente        |            | secours  |       |     |       |
		Et Machin lecture diffuse « Café à minuit », dans le fil musical « Continue »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et j'ouvre le menu « Diffusion »
		Alors la coupure par le secours du menu « Diffusion » a le sous-menu « « Attente » », « « Coupure studio » »
		Quand je choisis « « Coupure studio » » dans le sous-menu de la coupure par le secours
		Alors Machin lecture a reçu la demande de couper l'antenne par le secours « Coupure studio »

	Scénario: Sans rien à l'antenne, la coupure par le secours est inactive
		Étant donné les événements :
			| nom            | nom_public | priorite | debut | fin | jours |
			| Coupure studio |            | secours  |       |     |       |
		Et Machin lecture laisse un blanc
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et j'ouvre le menu « Diffusion »
		Alors la coupure par le secours du menu « Diffusion » est inactive, avec l'infobulle « Rien à l'antenne »

	Scénario: Le clic droit sur le prochain sonore coupe aussi par le secours, ou par le fil musical
		Étant donné les événements :
			| nom            | nom_public | priorite | debut | fin | jours |
			| Coupure studio |            | secours  |       |     |       |
		Et Machin lecture diffuse « Café à minuit », dans « Matinale », avant « Spot »
		Quand la fenêtre de l'interface s'ouvre
		Et l'onglet Antenne a reçu l'état de Machin lecture
		Et je choisis « ⏭ Couper par le secours » au clic droit sur le prochain sonore
		Alors Machin lecture a reçu la demande de couper l'antenne par le secours « Coupure studio »
		Quand je choisis « ⏭ Couper l'événement par le fil musical » au clic droit sur le prochain sonore
		Alors Machin lecture a reçu aussi la demande d'interrompre « evenement »
		Et la barre d'état a annoncé « Coupure de l'événement par le fil musical demandée. »

	Plan du scénario: Le clic droit sur un feed propose sa pré-écoute, et de couper l'antenne par lui
		Étant donné les feeds « Studio mobile », « https://flux.exemple/mobile »
		Et les sonores :
			| artiste | titre  | type   | etat   | duree | emplacement                 |
			|         | Relais | stream | <etat> |       | https://flux.exemple/mobile |
		Et le stream « Relais » suit le feed « Studio mobile »
		Et Machin lecture <antenne>
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et je choisis « Ouvrir l'onglet Feeds » dans le menu « Affichage »
		Alors le clic droit sur le feed « Studio mobile » propose :
			| entrée      | état   | infobulle   |
			| Pré-écoute… | active |             |
			| <coupure>   | <état> | <infobulle> |

		Exemples:
			| etat      | antenne                                                  | coupure                              | état     | infobulle                          |
			| actif     | diffuse « Café à minuit », dans « Matinale »             | ⏭ Couper l'événement par ce feed     | active   | Le stream du feed passe jusqu'à la fin prévue de l'événement coupé ; sous le fil musical, jusqu'à l'événement suivant. S'il tombe, le fil musical prend le relais |
			| actif     | diffuse « Café à minuit », dans le fil musical « Continue » | ⏭ Couper le fil musical par ce feed | active   | Le stream du feed passe jusqu'à la fin prévue de l'événement coupé ; sous le fil musical, jusqu'à l'événement suivant. S'il tombe, le fil musical prend le relais |
			| desactive | diffuse « Café à minuit », dans « Matinale »             | ⏭ Couper l'événement par ce feed     | inactive | Aucun stream actif ne suit ce feed |
			| actif     | laisse un blanc                                          | ⏭ Couper l'événement par ce feed     | inactive | Rien à l'antenne                   |

	Scénario: Couper l'antenne par un feed est envoyé à Machin lecture, et annoncé
		Étant donné les feeds « Studio mobile », « https://flux.exemple/mobile »
		Et les sonores :
			| artiste | titre  | type   | etat  | duree | emplacement                 |
			|         | Relais | stream | actif |       | https://flux.exemple/mobile |
		Et le stream « Relais » suit le feed « Studio mobile »
		Et Machin lecture diffuse « Café à minuit », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et je choisis « Ouvrir l'onglet Feeds » dans le menu « Affichage »
		Et je choisis « ⏭ Couper l'événement par ce feed » au clic droit sur le feed « Studio mobile »
		Alors Machin lecture a reçu la demande de couper l'antenne par le feed « Studio mobile »
		Et la barre d'état a annoncé « Coupure par le feed « Studio mobile » demandée. »
