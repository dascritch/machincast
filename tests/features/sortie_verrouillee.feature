# language: fr
Fonctionnalité: La sortie de l'antenne ne joue jamais ailleurs que sur son périphérique
	En tant que technicien d'antenne,
	je veux que l'antenne ne passe jamais sur une autre carte son que la sienne, même quand la sienne disparaît un temps,
	afin de ne jamais entendre l'antenne dans le casque de la pré-écoute, et de la retrouver dès que sa carte revient.

	https://github.com/dascritch/machincast/issues/345. Avec PipeWire, une sortie qui vise un périphérique absent, ou
	dont le périphérique disparaît, est reliée par WirePlumber au périphérique par défaut du poste : souvent celui de la
	pré-écoute. Un périphérique peut disparaître un temps, par exemple quand la carte son change de profil à la mise en
	veille des écrans. machincast.audio.creer_sortie verrouille donc chaque sortie PipeWire sur son périphérique
	(VERROU) : node.dont-fallback, jamais de repli sur le périphérique par défaut ; node.linger, attendre le périphérique
	plutôt que d'échouer ; node.dont-move, aucun déplacement par les réglages du son du poste. Le flux reste sans
	sortie le temps que son périphérique manque, puis WirePlumber le relie à lui dès qu'il revient. La source du
	VU-mètre de l'interface, qui écoute l'antenne, l'est de même.

	Les scénarios de comportement font tourner un PipeWire et un WirePlumber à part, sans rapport avec ceux du poste,
	avec deux sorties muettes : la pré-écoute, périphérique par défaut, et l'antenne. Ils sont ignorés sans pipewire ni
	wireplumber.

	# ─── Propriétés ────────────────────────────────────────────

	Plan du scénario: Une sortie PipeWire est verrouillée sur son périphérique, présentation comprise
		Quand je crée la sortie « pipewire » de <programme>, sur le périphérique « carte-1 »
		Alors la sortie vise « carte-1 », sans repli, en l'attendant, sans déplacement
		Et la sortie se présente toujours comme « <nom> »

		Exemples:
			| programme            | nom                     |
			| Machin lecture       | MachinCast lecteur      |
			| la pré-écoute        | MachinCast interface    |
			| l'essai de la sortie | MachinCast installation |

	Plan du scénario: Une sortie sans périphérique, ou d'une autre sortie que PipeWire, n'a pas de verrou
		Quand je crée la sortie « <sortie> » de Machin lecture, sur le périphérique « <peripherique> »
		Alors la sortie n'a pas de verrou

		Exemples:
			| sortie     | peripherique |
			| pipewire   |              |
			| pulseaudio | carte-1      |
			| alsa       | default      |
			| factice    |              |

	Scénario: La source du VU-mètre, qui écoute l'antenne, est verrouillée de même
		Quand je crée la source du VU-mètre de l'antenne « carte-1 », sur PipeWire
		Alors la source vise « carte-1 », sans repli, en l'attendant, sans déplacement

	# ─── Comportement, sur un PipeWire à part ──────────────────

	@pipewire
	Scénario: Quand le périphérique de l'antenne disparaît, l'antenne attend, sans passer sur la pré-écoute, puis le retrouve
		Étant donné un PipeWire à part, avec la pré-écoute par défaut et l'antenne
		Quand l'antenne joue sur sa sortie
		Alors l'antenne est reliée à « antenne »
		Quand le périphérique « antenne » disparaît
		Alors l'antenne n'est reliée à rien
		Et l'antenne joue toujours
		Quand le périphérique « antenne » revient
		Alors l'antenne est reliée à « antenne »

	@pipewire
	Scénario: Une antenne lancée avant que son périphérique n'existe l'attend, au lieu de jouer sur la pré-écoute
		Étant donné un PipeWire à part, avec la pré-écoute par défaut
		Quand l'antenne joue sur sa sortie
		Alors l'antenne n'est reliée à rien
		Et l'antenne joue toujours
		Quand le périphérique « antenne » revient
		Alors l'antenne est reliée à « antenne »

	@pipewire
	Scénario: Un déplacement de l'antenne par les réglages du son du poste est refusé
		Étant donné un PipeWire à part, avec la pré-écoute par défaut et l'antenne
		Quand l'antenne joue sur sa sortie
		Et les réglages du son du poste déplacent l'antenne vers « preecoute »
		Alors l'antenne est reliée à « antenne »

	@pipewire
	Scénario: Sans verrou, la même sortie passe sur la pré-écoute quand l'antenne disparaît : c'est le défaut corrigé
		Étant donné un PipeWire à part, avec la pré-écoute par défaut et l'antenne
		Quand une sortie sans verrou joue sur l'antenne
		Et le périphérique « antenne » disparaît
		Alors la sortie sans verrou est reliée à « preecoute »
