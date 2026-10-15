# language: fr
Fonctionnalité: Déroulé de la liste de lecture et transitions entre événements
	En tant que programmateur de l'antenne,
	je veux que la liste d'un événement soit jouée dans l'ordre et que les changements d'événement suivent les règles prévues,
	afin que les émissions démarrent à l'heure et le fil musical reprenne proprement.

	https://github.com/dascritch/machincast/issues/14 — spec § 4.2 et § 4.3. La diffusion est simulée minute par
	minute : l'ordonnanceur décide, la simulation note chaque passage dans l'airplay comme le fera le binaire.
	Les heures sont celles du mercredi 14 octobre 2026, en heure de Paris.

	Contexte:
		Étant donné le poste à l'heure de Paris
		Et chaque sonore dure 10 minutes

	# ─── Liste de lecture ──────────────────────────────────────

	Scénario: Les éléments sont joués dans l'ordre, un même élément peut revenir, une banque fait jouer un seul sonore
		Étant donné une banque séquentielle « Titres » contenant « t1 », « t2 »
		Et les événements :
			| nom      | priorité | début | fin   | liste                                                       |
			| Magazine | emission | 20:00 | 20:40 | sonore « jingle », banque « Titres », sonore « jingle », banque « Titres » |
		Quand la diffusion se déroule de 20:00 à 20:40
		Alors la diffusion a été :
			| heure | sonore | événement | issue  |
			| 20:00 | jingle | Magazine  | entier |
			| 20:10 | t1     | Magazine  | entier |
			| 20:20 | jingle | Magazine  | entier |
			| 20:30 | t2     | Magazine  | entier |

	Scénario: Une liste terminée avant la fin de l'événement reprend au début
		Étant donné les événements :
			| nom      | priorité | début | fin   | liste                    |
			| Magazine | emission | 20:00 | 20:40 | sonore « a », sonore « b » |
		Quand la diffusion se déroule de 20:00 à 20:40
		Alors la diffusion a été :
			| heure | sonore | événement | issue  |
			| 20:00 | a      | Magazine  | entier |
			| 20:10 | b      | Magazine  | entier |
			| 20:20 | a      | Magazine  | entier |
			| 20:30 | b      | Magazine  | entier |

	Scénario: Une émission sans fin ne boucle pas : à la fin de sa liste, le fil musical reprend
		Étant donné les événements :
			| nom      | priorité    | début | fin | liste                      |
			| Continue | fil_musical |       |     | sonore « f »               |
			| Direct   | emission    | 20:00 |     | sonore « d1 », sonore « d2 » |
		Quand la diffusion se déroule de 20:00 à 20:40
		Alors la diffusion a été :
			| heure | sonore | événement | issue  |
			| 20:00 | d1     | Direct    | entier |
			| 20:10 | d2     | Direct    | entier |
			| 20:20 | f      | Continue  | entier |
			| 20:30 | f      | Continue  | entier |

	Scénario: Une banque sans sonore jouable est sautée, comme un sonore qui n'est pas jouable
		Étant donné une banque séquentielle « Vide » contenant « x »
		Et le sonore « x » est à l'état « desactive »
		Et le sonore « y » est à l'état « expire »
		Et les événements :
			| nom      | priorité | début | fin   | liste                                                      |
			| Magazine | emission | 20:00 | 20:30 | banque « Vide », sonore « a », sonore « y », sonore « b » |
		Quand la diffusion se déroule de 20:00 à 20:30
		Alors la diffusion a été :
			| heure | sonore | événement | issue  |
			| 20:00 | a      | Magazine  | entier |
			| 20:10 | b      | Magazine  | entier |
			| 20:20 | a      | Magazine  | entier |

	Scénario: Chaque occurrence d'un événement récurrent reprend sa liste au début
		Étant donné les événements :
			| nom      | priorité | début | fin   | jours     | liste                                   |
			| Matinale | emission | 07:00 | 07:20 | mercredi, jeudi | sonore « a », sonore « b », sonore « c » |
		Quand la diffusion se déroule de 07:00 à 07:20
		Et la diffusion se déroule le lendemain de 07:00 à 07:20
		Alors la diffusion a été :
			| heure | sonore | événement | issue  |
			| 07:00 | a      | Matinale  | entier |
			| 07:10 | b      | Matinale  | entier |
			| 07:00 | a      | Matinale  | entier |
			| 07:10 | b      | Matinale  | entier |

	# ─── Transitions ───────────────────────────────────────────

	Scénario: Le début d'un événement coupe net le sonore en cours
		Étant donné le sonore « long » dure 25 minutes
		Et les événements :
			| nom      | priorité    | début | fin   | liste           |
			| Continue | fil_musical |       |       | sonore « long » |
			| Magazine | emission    | 20:00 | 20:20 | sonore « a »    |
		Quand la diffusion se déroule de 19:50 à 20:20
		Alors la diffusion a été :
			| heure | sonore | événement | issue         |
			| 19:50 | long   | Continue  | coupé à 20:00 |
			| 20:00 | a      | Magazine  | entier        |
			| 20:10 | a      | Magazine  | entier        |

	Scénario: À la fin d'un événement sans successeur, le dernier sonore est joué jusqu'au bout
		Étant donné le sonore « long » dure 25 minutes
		Et les événements :
			| nom      | priorité    | début | fin   | liste           |
			| Continue | fil_musical |       |       | sonore « f »    |
			| Magazine | emission    | 20:00 | 20:30 | sonore « long » |
		Quand la diffusion se déroule de 20:00 à 21:00
		Alors la diffusion a été :
			| heure | sonore | événement | issue  |
			| 20:00 | long   | Magazine  | entier |
			| 20:25 | long   | Magazine  | entier |
			| 20:50 | f      | Continue  | entier |

	Scénario: Un événement qui suit immédiatement coupe net le dernier sonore du précédent
		Étant donné le sonore « long » dure 25 minutes
		Et les événements :
			| nom      | priorité | début | fin   | liste           |
			| Magazine | emission | 20:00 | 20:30 | sonore « long » |
			| Journal  | emission | 20:30 | 20:50 | sonore « j »    |
		Quand la diffusion se déroule de 20:00 à 20:50
		Alors la diffusion a été :
			| heure | sonore | événement | issue         |
			| 20:00 | long   | Magazine  | entier        |
			| 20:25 | long   | Magazine  | coupé à 20:30 |
			| 20:30 | j      | Journal   | entier        |
			| 20:40 | j      | Journal   | entier        |

	Scénario: Le fil musical reprend à l'élément qui suit le dernier qu'il a joué
		Étant donné les événements :
			| nom      | priorité    | début | fin   | liste                                    |
			| Continue | fil_musical |       |       | sonore « f1 », sonore « f2 », sonore « f3 » |
			| Magazine | emission    | 20:00 | 20:20 | sonore « m »                             |
		Quand la diffusion se déroule de 19:40 à 20:40
		Alors la diffusion a été :
			| heure | sonore | événement | issue  |
			| 19:40 | f1     | Continue  | entier |
			| 19:50 | f2     | Continue  | entier |
			| 20:00 | m      | Magazine  | entier |
			| 20:10 | m      | Magazine  | entier |
			| 20:20 | f3     | Continue  | entier |
			| 20:30 | f1     | Continue  | entier |

	Scénario: Une émission dont rien n'est jouable laisse la place au fil musical
		Étant donné le sonore « x » est à l'état « desactive »
		Et les événements :
			| nom      | priorité    | début | fin   | liste        |
			| Continue | fil_musical |       |       | sonore « f » |
			| Magazine | emission    | 20:00 | 20:20 | sonore « x » |
		Quand la diffusion se déroule de 20:00 à 20:20
		Alors la diffusion a été :
			| heure | sonore | événement | issue  |
			| 20:00 | f      | Continue  | entier |
			| 20:10 | f      | Continue  | entier |

	# ─── Silence ───────────────────────────────────────────────

	Scénario: Rien à lire dans le fil musical : silence, et une seule alerte dans le log
		Étant donné le sonore « x » est à l'état « desactive »
		Et les événements :
			| nom      | priorité    | début | fin | liste        |
			| Continue | fil_musical |       |     | sonore « x » |
		Quand la diffusion se déroule de 20:00 à 20:30
		Alors la diffusion a été :
			| heure | sonore  | événement | issue |
			| 20:00 | silence | Continue  |       |
		Et le log contient 1 alerte « silence » pour l'événement « Continue »

	Scénario: Le silence prend fin dès qu'un sonore redevient jouable
		Étant donné le sonore « x » est à l'état « desactive »
		Et les événements :
			| nom      | priorité    | début | fin   | liste        |
			| Continue | fil_musical |       |       | sonore « x » |
			| Magazine | emission    | 20:10 | 20:20 | sonore « m » |
		Quand la diffusion se déroule de 20:00 à 20:20
		Alors la diffusion a été :
			| heure | sonore  | événement | issue |
			| 20:00 | silence | Continue  |       |
			| 20:10 | m       | Magazine  | entier |
