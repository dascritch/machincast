# language: fr
Fonctionnalité: Les effets d'un sonore, répondus par un plugin : un compresseur ou un limiteur dans sa voie
	En tant que technicien d'antenne,
	je veux qu'un plugin puisse insérer un effet audio, comme un compresseur ou un limiteur LV2, dans la voie de chaque sonore,
	afin de traiter la dynamique dans MachinCast, en plus ou à la place du compresseur matériel.

	https://github.com/dascritch/machincast/issues/644, pour https://github.com/dascritch/machincast/issues/43. Le point
	« player.sound_effects » est demandé avant de jouer un sonore, fichier ou stream : le plugin répond une description
	d'éléments GStreamer, insérée dans sa voie entre son gain et son enveloppe de volume. Un greffon LV2 installé est un
	élément de GStreamer (gstreamer1.0-plugins-bad) ; les scénarios prennent audiodynamic, le compresseur de
	gstreamer1.0-plugins-good.

	Contexte:
		Étant donné l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et le fil musical permanent « Continue », avec les sonores « a », « b »

	Scénario: Sans plugin, la voie n'a aucun effet
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Alors la voie de « a » n'a aucun effet

	Scénario: L'effet que répond le plugin est inséré entre le gain et l'enveloppe de volume
		Étant donné un plugin qui répond les effets « audiodynamic mode=compressor characteristics=soft-knee threshold=0.5 ratio=0.25 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 2 pas d'une seconde
		Alors la voie de « a » passe par « audiodynamic », entre son gain et son enveloppe de volume
		Et son « audiodynamic » a « threshold » à 0.5 et « ratio » à 0.25
		Et le plugin a reçu le sonore « a », qui n'est pas un stream

	Scénario: Les effets de deux plugins s'enchaînent, dans leur ordre de chargement
		Étant donné un plugin qui répond les effets « audiodynamic mode=compressor »
		Et un second plugin qui répond les effets « audioamplify amplification=0.9 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Alors la voie de « a » passe par « audiodynamic » puis « audioamplify »

	Scénario: Une description invalide est consignée, et le sonore joue sans effet
		Étant donné un plugin qui répond les effets « compresseur-imaginaire seuil=-12 »
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Alors la voie de « a » n'a aucun effet
		Et le journal dit que les effets « compresseur-imaginaire seuil=-12 » sont refusés
