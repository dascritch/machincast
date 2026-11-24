# language: fr
Fonctionnalité: La normalisation du niveau : chaque sonore porté à la sonie visée, sans dépasser le plafond de crête
	En tant que technicien d'antenne,
	je veux que le niveau sonore soit normalisé par le logiciel,
	afin que l'antenne reste homogène sans dépendre uniquement du compresseur matériel.

	https://github.com/dascritch/machincast/issues/43. La mesure, sonie intégrée EBU R128 et crête absolue, est celle de
	l'audit complet (https://github.com/dascritch/machincast/issues/642), dans la colonne properties du sonore ; le
	plugin répond son gain à Machin player (https://github.com/dascritch/machincast/issues/643). Ses réglages sont la
	section [plugins.loudness_normalization] de machincast.toml ; l'ajustement manuel d'un sonore est dans sa colonne
	properties, sous la clé « loudness_normalization ».

	# ─── La règle ──────────────────────────────────────────

	Plan du scénario: Le gain porte la sonie à la cible, plus l'ajustement manuel, sans que la crête dépasse le plafond
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Alors un sonore de sonie <sonie>, de crête <crête>, ajusté de <manuel> dB, reçoit un gain de <gain> dB

		Exemples:
			| sonie   | crête   | manuel | gain |
			| -17     | -3      | 0      | -6   |
			| -30     | -3      | 0      | 2    |
			| -20     | -2      | 4      | 1    |
			| -20     | -10     | 4      | 1    |
			| -40     | -20     | 0      | 17   |
			| inconnue | -10    | 3      | 3    |
			| inconnue | inconnue | 5     | 5    |
			| -23     | -5      | -2,5   | -2,5 |

	Plan du scénario: Des réglages invalides sont refusés
		Alors les réglages <réglages> sont refusés : « <raison> »

		Exemples:
			| réglages       | raison                                     |
			| cible -50      | target est une sonie en LUFS, de -40 à -5  |
			| cible « fort » | target est une sonie en LUFS, de -40 à -5  |
			| plafond 2      | ceiling est une crête en dBFS, de -12 à 0  |

	# ─── Le plugin ─────────────────────────────────────────

	Plan du scénario: Le plugin s'abonne aux points du binaire qui le charge
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Quand le plugin de la normalisation du niveau s'enregistre dans « <binaire> »
		Alors il s'abonne seulement à <points>

		Exemples:
			| binaire          | points                                             |
			| Machin_player    | « player.sound_gain »                              |
			| Machin_indexer   | « indexer.sound_detailed »                         |
			| Machin_interface | « interface.sound_card », « interface.bank_card », « interface.plugin_window » |
			| Machin_intranet  | aucun point                                        |

	# ─── À l'antenne ───────────────────────────────────────

	Scénario: Machin player joue chaque sonore avec le gain du plugin
		Étant donné l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et le fil musical permanent « Continue », avec les sonores « a », « b »
		Et les propriétés du sonore « a » {"loudness": {"integrated": -17.0, "peak": -3.0}}
		Et les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le plugin de la normalisation du niveau, chargé dans Machin player
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 2 pas d'une seconde
		Alors la voie de « a » joue avec un gain de -6 dB
		Et la voie de « b », pas encore mesuré, joue avec un gain de 0 dB

	Scénario: Des réglages refusés laissent Machin player jouer les sonores tels quels
		Étant donné les réglages : cible -50 LUFS, plafond -1 dBFS
		Quand le plugin de la normalisation du niveau s'enregistre dans « Machin_player »
		Alors le journal dit « loudness_normalization : réglages refusés, aucun gain appliqué : target est une sonie en LUFS, de -40 à -5 »
		Et le gain répondu pour un sonore de sonie -17 est nul

	Scénario: Un sonore fourni par une banque prend la cible et le plafond propres à la banque
		Étant donné l'horloge du binaire au « 2026-10-14 20:00:00 »
		Et le fil musical permanent « Continue », avec la banque séquentielle « Pubs » des sonores « a »
		Et les propriétés du sonore « a » {"loudness": {"integrated": -20.0, "peak": -10.0}}
		Et les propriétés de la banque « Pubs » {"loudness_normalization": {"target": -16.0}}
		Et les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le plugin de la normalisation du niveau, chargé dans Machin player
		Quand la diffusion démarre au plus vite
		Et la diffusion tourne 1 pas d'une seconde
		Alors la voie de « a » joue avec un gain de 4 dB

	# ─── Machin indexer ────────────────────────────────────

	Scénario: Après une mise à jour du fichier, un ajustement manuel qui ferait saturer est ramené, et le log le dit
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le sonore « nouveau.flac », de propriétés {"loudness": {"integrated": -20.0, "peak": -2.0}, "loudness_normalization": {"gain": 6.0}}
		Et le plugin de la normalisation du niveau, chargé dans Machin indexer
		Quand l'audit complet de Machin indexer le mesure
		Alors ses propriétés sont {"loudness": {"integrated": -20.0, "peak": -2.0}, "loudness_normalization": {"gain": 4.0}}
		Et le log a l'incident « niveau ajusté » : « « nouveau.flac » : sa crête de −2,0 dBFS dépasserait le plafond de −1,0 dBFS avec un gain de +3,0 dB : ajustement manuel ramené de +6,0 à +4,0 dB »

	Scénario: Un ajustement manuel qui ne fait pas saturer reste tel quel, sans rien au log
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le sonore « calme.flac », de propriétés {"loudness": {"integrated": -20.0, "peak": -10.0}, "loudness_normalization": {"gain": 4.0}}
		Et le plugin de la normalisation du niveau, chargé dans Machin indexer
		Quand l'audit complet de Machin indexer le mesure
		Alors ses propriétés sont {"loudness": {"integrated": -20.0, "peak": -10.0}, "loudness_normalization": {"gain": 4.0}}
		Et le log n'a aucun incident

	Scénario: Le plafond le plus bas, celui du plugin ou d'une banque qui contient le sonore, borne l'ajustement manuel
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le sonore « nouveau.flac », de propriétés {"loudness": {"integrated": -20.0, "peak": -10.0}, "loudness_normalization": {"gain": 6.0}}
		Et la banque « Pubs », de propriétés {"loudness_normalization": {"ceiling": -6.0}}, qui contient ce sonore
		Et le plugin de la normalisation du niveau, chargé dans Machin indexer
		Quand l'audit complet de Machin indexer le mesure
		Alors ses propriétés sont {"loudness": {"integrated": -20.0, "peak": -10.0}, "loudness_normalization": {"gain": 6.0}}
		Et le log n'a aucun incident

	Scénario: Le plafond d'une banque fait ramener un ajustement qui ferait saturer
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le sonore « nouveau.flac », de propriétés {"loudness": {"integrated": -20.0, "peak": -10.0}, "loudness_normalization": {"gain": 8.0}}
		Et la banque « Pubs », de propriétés {"loudness_normalization": {"ceiling": -6.0}}, qui contient ce sonore
		Et le plugin de la normalisation du niveau, chargé dans Machin indexer
		Quand l'audit complet de Machin indexer le mesure
		Alors ses propriétés sont {"loudness": {"integrated": -20.0, "peak": -10.0}, "loudness_normalization": {"gain": 7.0}}
		Et le log a l'incident « niveau ajusté » : « « nouveau.flac » : sa crête de −10,0 dBFS dépasserait le plafond de −6,0 dBFS avec un gain de +5,0 dB : ajustement manuel ramené de +8,0 à +7,0 dB »

	# ─── La fiche d'un sonore ──────────────────────────────

	Scénario: La fiche montre la mesure, l'ajustement manuel borné par le plafond, et le gain appliqué
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le sonore « a.flac », de propriétés {"loudness": {"integrated": -20.0, "peak": -2.0}, "loudness_normalization": {"gain": 1.5}}
		Quand la section « Niveau » de ce sonore s'ouvre
		Alors elle montre « Sonie −20,0 LUFS, crête −2,0 dBFS »
		Et l'ajustement manuel vaut 1,5 dB, au plus 4,0 dB
		Et elle montre « Gain appliqué : −1,5 dB (automatique −3,0 dB, cible −23,0 LUFS, plafond −1,0 dBFS) »

	Scénario: Un sonore pas encore mesuré le dit, et son ajustement n'est borné qu'à 20 dB
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le sonore « a.flac », de propriétés {}
		Quand la section « Niveau » de ce sonore s'ouvre
		Alors elle montre « Pas encore mesuré : l'audit complet de Machin indexer le mesure. »
		Et l'ajustement manuel vaut 0,0 dB, au plus 20,0 dB

	Scénario: L'ajustement manuel s'enregistre dans les propriétés du sonore ; à 0, la clé du plugin en part
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le sonore « a.flac », de propriétés {"loudness": {"integrated": -20.0, "peak": -10.0}}
		Quand la section « Niveau » de ce sonore s'ouvre
		Et je règle l'ajustement manuel à 2,5 dB
		Alors la fiche est modifiée
		Et elle montre « Gain appliqué : −0,5 dB (automatique −3,0 dB, cible −23,0 LUFS, plafond −1,0 dBFS) »
		Quand la section s'enregistre
		Alors ses propriétés sont {"loudness": {"integrated": -20.0, "peak": -10.0}, "loudness_normalization": {"gain": 2.5}}
		Quand je règle l'ajustement manuel à 0 dB
		Et la section s'enregistre
		Alors ses propriétés sont {"loudness": {"integrated": -20.0, "peak": -10.0}}

	Scénario: Dans la fiche d'un sonore, l'encart « Niveau » est dépliable, sous l'encart « Fichier »
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le sonore « a.flac », de propriétés {"loudness": {"integrated": -20.0, "peak": -2.0}}
		Et le plugin de la normalisation du niveau, chargé dans Machin interface
		Quand j'ouvre la fiche de ce sonore
		Alors l'encart « Niveau » est juste sous l'encart « Fichier », replié, et se déplie d'un clic sur son titre
		Et la section du plugin est cachée

	Scénario: La fiche d'un stream n'a pas d'encart « Niveau », comme pas d'encart « Fichier »
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le stream « Direct »
		Et le plugin de la normalisation du niveau, chargé dans Machin interface
		Quand j'ouvre la fiche de ce sonore
		Alors l'encart « Niveau » est caché

	Scénario: La fiche d'un sonore montre aussi le gain dans chaque banque qui a ses propres réglages
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le sonore « a.flac », de propriétés {"loudness": {"integrated": -20.0, "peak": -10.0}}
		Et la banque « Pubs », de propriétés {"loudness_normalization": {"target": -16.0, "ceiling": -6.0}}, qui contient ce sonore
		Quand la section « Niveau » de ce sonore s'ouvre
		Alors l'ajustement manuel vaut 0,0 dB, au plus 0,0 dB
		Et elle montre « Gain appliqué : −3,0 dB (automatique −3,0 dB, cible −23,0 LUFS, plafond −1,0 dBFS) »
		Et elle montre « Dans la banque « Pubs » : Gain appliqué : +4,0 dB (automatique +4,0 dB, cible −16,0 LUFS, plafond −6,0 dBFS) »

	# ─── La fiche d'une banque ─────────────────────────────

	Scénario: Une banque suit les réglages du plugin, que ses curseurs grisés montrent
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et la banque « Pubs », de propriétés {}
		Quand la section « Niveau » de cette banque s'ouvre
		Alors « Sonie visée propre à la banque » est décochée, son curseur grisé sur « −23,0 LUFS »
		Et « Plafond de crête propre à la banque » est décochée, son curseur grisé sur « −1,0 dBFS »

	Scénario: Cocher et régler une sonie visée propre à la banque l'enregistre dans ses propriétés ; décochée, elle en part
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et la banque « Pubs », de propriétés {}
		Quand la section « Niveau » de cette banque s'ouvre
		Et je coche « Sonie visée propre à la banque » et règle son curseur à -16 LUFS
		Alors la fiche est modifiée
		Quand la section de la banque s'enregistre
		Alors les propriétés de la banque sont {"loudness_normalization": {"target": -16.0}}
		Quand je décoche « Sonie visée propre à la banque »
		Et la section de la banque s'enregistre
		Alors les propriétés de la banque sont {}

	# ─── La fenêtre du plugin ──────────────────────────────

	Scénario: La fenêtre règle la cible et le plafond, et les écrit dans machincast.toml
		Étant donné les réglages : cible -23 LUFS, plafond -1 dBFS
		Et le plugin de la normalisation du niveau, chargé dans Machin interface
		Quand j'ouvre la fenêtre du plugin
		Alors la sonie visée et le plafond sont des curseurs, à -23,0 LUFS et -1,0 dBFS
		Et la fenêtre est assez large pour lire ses textes
		Quand je règle la sonie visée à -16 LUFS et le plafond à -2 dBFS
		Et j'enregistre les réglages du plugin
		Alors le message de la fenêtre dit « Enregistré. Relancez la diffusion et l'indexation pour qu'elles prennent ces réglages. »
		Et le fichier de configuration a gardé son commentaire et ses autres sections
		Et sa section [plugins.loudness_normalization] est target -16.0, ceiling -2.0
		Et la fiche d'un sonore de sonie -20 montre aussitôt un gain automatique de +4,0 dB
