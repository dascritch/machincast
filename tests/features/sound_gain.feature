# language: fr
Fonctionnalité: Le gain d'un sonore, répondu par un plugin
	En tant que développeur d'un plugin,
	je veux un point d'extension de Machin player demandé quand il prépare la lecture d'un sonore,
	afin d'en régler le gain, par exemple pour normaliser le niveau de l'antenne.

	https://github.com/dascritch/machincast/issues/643, pour https://github.com/dascritch/machincast/issues/43. Le point
	« player.sound_gain » est demandé avant de jouer un fichier, avec ses properties, la mesure de son niveau comprise ;
	le gain, en dB, s'applique à sa voie, avant son enveloppe de volume. Sans plugin, le sonore joue tel quel.

	Contexte:
		Étant donné l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et le fil musical permanent « Continue », avec les sonores « a », « b »

	Scénario: Sans plugin, chaque sonore joue tel quel
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 2 pas d'une seconde
		Alors la voie de « a » a un gain de 0 dB
		Et la voie de « b » a un gain de 0 dB

	Scénario: Le gain que répond le plugin s'applique à la voie du sonore
		Étant donné les propriétés du sonore « a » {"loudness": {"integrated": -17.0, "peak": -1.0}}
		Et un plugin qui répond un gain de « -23 moins la sonie intégrée »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 2 pas d'une seconde
		Alors la voie de « a » a un gain de -6 dB
		Et la voie de « b » a un gain de 0 dB
		Et le plugin a reçu les propriétés du sonore « a », avec sa sonie

	Scénario: Un gain au-delà de +20 dB est borné
		Étant donné un plugin qui répond un gain de « 30 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Alors la voie de « a » a un gain de 20 dB

	Scénario: Une réponse qui n'est pas un nombre est ignorée
		Étant donné un plugin qui répond un gain de « fort »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Alors la voie de « a » a un gain de 0 dB
