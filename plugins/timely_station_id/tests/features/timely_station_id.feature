# language: fr
Fonctionnalité: Le station ID régulier : un station ID environ tous les quarts d'heure, quelle que soit la durée des morceaux
	En tant que responsable d'antenne,
	je veux qu'un jingle de la station soit diffusé environ toutes les 15 minutes malgré la durée des titres,
	afin de répondre à nos obligations légales.

	https://github.com/dascritch/machincast/issues/460, par le point « player.before_choice »
	(https://github.com/dascritch/machincast/issues/640). Ses réglages sont la section [plugins.timely_station_id] de
	machincast.toml ; un événement l'a quand sa case « Station ID régulier » est cochée, dans sa colonne properties.
	Les heures sont des minutes depuis le début de la diffusion ; chaque station ID dure une minute.

	Contexte:
		Étant donné une banque « Station ID » contenant « id1 », « id2 »
		Et une banque « Saison » contenant « noël »
		Et les morceaux, en minutes : « a » 5, « b » 7, « c » 4, « d » 13, « e » 3

	# ─── La règle ──────────────────────────────────────────

	Plan du scénario: Avant le morceau qui ferait dépasser le maximum, au plus tôt après le minimum, ou après le maximum
		Étant donné les réglages : minimum 12, maximum 18, placement « <placement> »
		Alors depuis le dernier station ID <écart>, un morceau de <durée> <décision>

		Exemples:
			| placement | écart                   | durée      | décision                |
			| before    | inconnu                 | 5 minutes  | passe après un station ID |
			| before    | 10 minutes              | 13 minutes | passe tel quel          |
			| before    | 13 minutes              | 4 minutes  | passe tel quel          |
			| before    | 17 minutes              | 13 minutes | passe après un station ID |
			| before    | 18 minutes              | 1 minutes  | passe après un station ID |
			| before    | 13 minutes              | stream     | passe tel quel          |
			| after     | 17 minutes              | 13 minutes | passe tel quel          |
			| after     | 18 minutes              | 1 minutes  | passe après un station ID |

	Plan du scénario: Des réglages invalides sont refusés
		Alors les réglages <réglages> sont refusés : « <raison> »

		Exemples:
			| réglages                                   | raison                                                                   |
			| sans banque                                | la banque des station ID manque : bank = "…"                             |
			| minimum 20, maximum 15                     | minimum et maximum sont des minutes, le minimum pas au-dessus du maximum |
			| minimum 0, maximum 15                      | minimum et maximum sont des minutes, le minimum pas au-dessus du maximum |
			| placement « pendant »                      | placement vaut « before » ou « after »                                   |
			| watched « Saison » sans liste              | watched est une liste de noms de banques                                 |

	# ─── À l'antenne ───────────────────────────────────────

	Scénario: Avant le morceau qui ferait dépasser le maximum
		Étant donné les réglages : minimum 12, maximum 18, placement « before »
		Et le fil musical « Continue », coché, jouant « a », « b », « c », « d », « e »
		Et le plugin du station ID régulier, chargé dans « Machin_player »
		Quand la diffusion se déroule pendant 36 minutes
		Alors la diffusion a été « 0 id1 », « 1 a », « 6 b », « 13 c », « 17 id2 », « 18 d », « 31 e », « 34 id1 », « 35 a »

	Scénario: Après le maximum, sans avancer aucun morceau
		Étant donné les réglages : minimum 12, maximum 18, placement « after »
		Et le fil musical « Continue », coché, jouant « a », « b », « c », « d », « e »
		Et le plugin du station ID régulier, chargé dans « Machin_player »
		Quand la diffusion se déroule pendant 35 minutes
		Alors la diffusion a été « 0 id1 », « 1 a », « 6 b », « 13 c », « 17 d », « 30 id2 », « 31 e », « 34 a »

	Scénario: Le passage d'une banque surveillée compte comme un station ID
		Étant donné les réglages : minimum 12, maximum 18, placement « before », banques surveillées « Saison »
		Et le fil musical « Continue », coché, jouant « a », « noël », « b », « c », « d »
		Et le plugin du station ID régulier, chargé dans « Machin_player »
		Quand la diffusion se déroule pendant 31 minutes
		Alors la diffusion a été « 0 id1 », « 1 a », « 6 noël », « 7 b », « 14 c », « 18 id2 », « 19 d »

	Scénario: Un événement qui n'est pas coché n'a aucun station ID inséré
		Étant donné les réglages : minimum 12, maximum 18, placement « before »
		Et le fil musical « Continue », pas coché, jouant « a », « b », « c »
		Et le plugin du station ID régulier, chargé dans « Machin_player »
		Quand la diffusion se déroule pendant 16 minutes
		Alors la diffusion a été « 0 a », « 5 b », « 12 c »

	Scénario: Une banque des station ID introuvable est consignée, et rien n'est inséré
		Étant donné les réglages : minimum 12, maximum 18, placement « before », banque « Identifiants »
		Et le fil musical « Continue », coché, jouant « a », « b »
		Et le plugin du station ID régulier, chargé dans « Machin_player »
		Quand la diffusion se déroule pendant 12 minutes
		Alors la diffusion a été « 0 a », « 5 b »
		Et le journal dit une fois « timely_station_id : aucune banque « Identifiants » »

	# ─── Le plugin ─────────────────────────────────────────

	Plan du scénario: Le plugin s'abonne aux points du binaire qui le charge
		Étant donné les réglages : minimum 12, maximum 18, placement « before »
		Quand le plugin du station ID régulier s'enregistre dans « <binaire> »
		Alors il s'abonne seulement à <points>

		Exemples:
			| binaire          | points                                            |
			| Machin_player    | « player.before_choice »                          |
			| Machin_interface | « player.before_choice », « interface.event_card » |

	Scénario: Des réglages refusés sont consignés, et le plugin ne s'abonne qu'à la fiche
		Étant donné les réglages : minimum 20, maximum 15, placement « before »
		Quand le plugin du station ID régulier s'enregistre dans « Machin_interface »
		Alors il s'abonne seulement à « interface.event_card »
		Et le journal dit « timely_station_id : réglages refusés, aucun station ID inséré : minimum et maximum sont des minutes, le minimum pas au-dessus du maximum »

	# ─── La fiche de l'événement ───────────────────────────

	Scénario: La case « Station ID régulier » est une ligne de la fiche, sous « Secours d'un stream tombé »
		Étant donné les réglages : minimum 12, maximum 18, placement « before »
		Et le fil musical « Continue », pas coché, jouant « a »
		Et le plugin du station ID régulier, chargé dans « Machin_interface »
		Quand j'ouvre la fiche de l'événement « Continue »
		Alors la ligne sous « Secours d'un stream tombé » est la case « Station ID régulier », pas cochée
		Et son infobulle dit « Un station ID de la banque « Station ID », toutes les 12 à 18 minutes, quelle que soit la durée des morceaux »
		Et la section du plugin est cachée : la liste de lecture n'est pas décalée

	Scénario: Cocher la case la range dans les propriétés de l'événement ; la décocher l'en retire
		Étant donné les réglages : minimum 12, maximum 18, placement « before »
		Et le fil musical « Continue », pas coché, jouant « a »
		Et le plugin du station ID régulier, chargé dans « Machin_interface »
		Quand j'ouvre la fiche de l'événement « Continue »
		Et je coche « Station ID régulier »
		Alors la fiche de l'événement est modifiée
		Quand j'enregistre la fiche de l'événement
		Alors les propriétés de « Continue » sont {"timely_station_id": true}
		Quand je décoche « Station ID régulier »
		Et j'enregistre la fiche de l'événement
		Alors les propriétés de « Continue » sont {}
