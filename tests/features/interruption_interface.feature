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
			| Sauter au sonore suivant              | active | « Café à minuit » |
			| Sauter après la séquence              | active | « Pub »           |
			| Couper l'événement par le fil musical | active | « Matinale »      |

	Scénario: Hors d'une séquence, seule l'interruption de la séquence est inactive
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Alors les interruptions du menu « Diffusion » sont :
			| entrée                                | état     | infobulle                   |
			| Sauter au sonore suivant              | active   | « Café à minuit »           |
			| Sauter après la séquence              | inactive | Aucune séquence à l'antenne |
			| Couper l'événement par le fil musical | active   | « Matinale »                |

	Scénario: Dans le fil musical, couper l'événement par le fil musical est inactif
		Étant donné Machin lecture diffuse « Café à minuit », de la séquence « Pub », dans le fil musical « Continue »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Alors les interruptions du menu « Diffusion » sont :
			| entrée                                | état     | infobulle                           |
			| Sauter au sonore suivant              | active   | « Café à minuit »                   |
			| Sauter après la séquence              | active   | « Pub »                             |
			| Couper l'événement par le fil musical | inactive | Le fil musical est déjà à l'antenne |

	Plan du scénario: Sans rien à l'antenne, aucune interruption n'est proposée
		Étant donné Machin lecture <situation>
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Alors les interruptions du menu « Diffusion » sont :
			| entrée                                | état     | infobulle        |
			| Sauter au sonore suivant              | inactive | Rien à l'antenne |
			| Sauter après la séquence              | inactive | Rien à l'antenne |
			| Couper l'événement par le fil musical | inactive | Rien à l'antenne |

		Exemples:
			| situation      |
			| est en silence |
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
			| Sauter au sonore suivant              | sonore    | Saut au sonore suivant demandé.                     |
			| Sauter après la séquence              | sequence  | Saut après la séquence demandé.                     |
			| Couper l'événement par le fil musical | evenement | Coupure de l'événement par le fil musical demandée. |

	Scénario: Une demande que Machin lecture ne peut pas recevoir n'est pas annoncée comme envoyée
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et Machin lecture ferme sa socket d'état, juste avant que je choisisse « Sauter au sonore suivant »
		Alors la barre d'état a annoncé « Interruption impossible : Machin lecture ne répond pas sur sa socket d'état. »

	Scénario: Les entrées suivent l'antenne
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et Machin lecture passe en silence
		Et l'interface a reçu l'état de Machin lecture
		Alors aucune interruption n'est active

	# ─── Clic droit sur le prochain sonore (https://github.com/dascritch/machincast/issues/257) ───
	# Le cadre « Prochain sonore » de l'accueil propose, au clic droit, sa pré-écoute, d'y sauter aussitôt, et
	# d'avancer l'événement suivant que Machin lecture annonce. La demande d'avance nomme cet événement : Machin
	# lecture l'ignore si un autre est devenu le suivant entre-temps.

	Scénario: Le clic droit sur le prochain sonore propose d'y sauter, et d'avancer l'événement suivant
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale », avant « Spot », et annonce l'événement suivant « Journal », du « 2026-10-21T12:00:00 » au « 2026-10-21T12:30:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et l'accueil a reçu l'état de Machin lecture
		Alors le clic droit sur le prochain sonore propose :
			| entrée                                                    | état   | infobulle                                                              |
			| Pré-écoute…                                               | active |                                                                        |
			| Sauter à ce sonore                                        | active | « Spot », aussitôt : « Café à minuit » s'arrête                        |
			| Avancer « Journal », prévu le mercredi 21 octobre à 12:00 | active | Il commence aussitôt, au-dessus de la grille, jusqu'à sa fin, à 12:30 |

	Scénario: Sans événement suivant annoncé, l'avance est inactive
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale », avant « Spot »
		Quand la fenêtre de l'interface s'ouvre
		Et l'accueil a reçu l'état de Machin lecture
		Alors le clic droit sur le prochain sonore propose :
			| entrée                       | état     | infobulle                                 |
			| Pré-écoute…                  | active   |                                           |
			| Sauter à ce sonore           | active   | « Spot », aussitôt : « Café à minuit » s'arrête |
			| Avancer l'événement suivant  | inactive | Aucun événement suivant dans les sept jours |

	Scénario: En silence, l'événement suivant s'avance quand même, mais il n'y a rien à sauter
		Étant donné Machin lecture est en silence, et annonce l'événement suivant « Journal », du « 2026-10-21T12:00:00 » au « 2026-10-21T12:30:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et l'accueil a reçu l'état de Machin lecture
		Alors le clic droit sur le prochain sonore propose :
			| entrée                                                    | état     | infobulle                                                              |
			| Sauter à ce sonore                                        | inactive | Aucun prochain sonore                                                  |
			| Avancer « Journal », prévu le mercredi 21 octobre à 12:00 | active   | Il commence aussitôt, au-dessus de la grille, jusqu'à sa fin, à 12:30 |

	Scénario: Machin lecture à l'arrêt, rien ne se demande depuis le prochain sonore
		Étant donné Machin lecture s'est arrêté
		Quand la fenêtre de l'interface s'ouvre
		Et l'accueil a reçu l'état de Machin lecture
		Alors le clic droit sur le prochain sonore propose :
			| entrée                      | état     | infobulle                     |
			| Sauter à ce sonore          | inactive | Machin lecture ne diffuse pas |
			| Avancer l'événement suivant | inactive | Machin lecture ne diffuse pas |

	Plan du scénario: Chaque entrée du clic droit sur le prochain sonore est envoyée à Machin lecture, et annoncée
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale », avant « Spot », et annonce l'événement suivant « Journal », du « 2026-10-21T12:00:00 » au « 2026-10-21T12:30:00 »
		Quand la fenêtre de l'interface s'ouvre
		Et l'accueil a reçu l'état de Machin lecture
		Et je choisis « <entrée> » au clic droit sur le prochain sonore
		Alors Machin lecture a reçu la demande <demande>
		Et la barre d'état a annoncé « <annonce> »
		Et aucune question n'a été posée

		Exemples:
			| entrée                                                    | demande                                | annonce                                       |
			| Sauter à ce sonore                                        | d'interrompre « sonore »               | Saut au sonore suivant demandé.               |
			| Avancer « Journal », prévu le mercredi 21 octobre à 12:00 | d'avancer l'événement n°7              | Avance de l'événement « Journal » demandée.   |
