# language: fr
Fonctionnalité: Interrompre l'antenne depuis l'interface
	En tant que responsable d'antenne,
	je veux que le menu « Diffusion » propose d'interrompre le sonore, la séquence ou l'événement en cours,
	afin de passer au suivant sans terminal.

	https://github.com/dascritch/machincast/issues/104, spec § 8.11. Les entrées suivent l'état que Machin lecture
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
			| entrée                  | état   | infobulle                                  |
			| Interrompre le sonore   | active | « Café à minuit »  |
			| Interrompre la séquence | active | « Pub »            |
			| Interrompre l'événement | active | « Matinale »       |

	Scénario: Hors d'une séquence, seule l'interruption de la séquence est inactive
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Alors les interruptions du menu « Diffusion » sont :
			| entrée                  | état     | infobulle                                  |
			| Interrompre le sonore   | active   | « Café à minuit »  |
			| Interrompre la séquence | inactive | Aucune séquence à l'antenne                |
			| Interrompre l'événement | active   | « Matinale »       |

	Plan du scénario: Sans rien à l'antenne, aucune interruption n'est proposée
		Étant donné Machin lecture <situation>
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Alors les interruptions du menu « Diffusion » sont :
			| entrée                  | état     | infobulle          |
			| Interrompre le sonore   | inactive | Rien à l'antenne   |
			| Interrompre la séquence | inactive | Rien à l'antenne   |
			| Interrompre l'événement | inactive | Rien à l'antenne   |

		Exemples:
			| situation              |
			| est en silence         |
			| s'est arrêté           |

	Plan du scénario: Chaque interruption est envoyée à Machin lecture, et annoncée
		Étant donné Machin lecture diffuse « Café à minuit », de la séquence « Pub », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et je choisis « <entrée> » dans le menu « Diffusion »
		Alors Machin lecture a reçu la demande d'interrompre « <élément> »
		Et la barre d'état a annoncé « <annonce> »
		Et aucune question n'a été posée

		Exemples:
			| entrée                  | élément   | annonce                                 |
			| Interrompre le sonore   | sonore    | Interruption du sonore demandée.        |
			| Interrompre la séquence | sequence  | Interruption de la séquence demandée.   |
			| Interrompre l'événement | evenement | Interruption de l'événement demandée.   |

	Scénario: Une demande que Machin lecture ne peut pas recevoir n'est pas annoncée comme envoyée
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et Machin lecture ferme sa socket d'état, juste avant que je choisisse « Interrompre le sonore »
		Alors la barre d'état a annoncé « Interruption impossible : Machin lecture ne répond pas sur sa socket d'état. »

	Scénario: Les entrées suivent l'antenne
		Étant donné Machin lecture diffuse « Café à minuit », dans « Matinale »
		Quand la fenêtre de l'interface s'ouvre
		Et l'interface a reçu l'état de Machin lecture
		Et Machin lecture passe en silence
		Et l'interface a reçu l'état de Machin lecture
		Alors aucune interruption n'est active
