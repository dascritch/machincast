# Émissions en alternance (alternation)

Des émissions qui se partagent le même créneau horaire, une par semaine du mois, ou une semaine sur deux : un événement « méta » joue, chaque semaine, celle qui est choisie, et l'antenne, le calendrier, l'intranet et l'affichage public la jouent et la montrent sous son nom ([#609](https://github.com/dascritch/machincast/issues/609), ticket enfant de [#606](https://github.com/dascritch/machincast/issues/606)).

- Guide d'utilisation : [doc/alternance.md](doc/alternance.md).
- Écrire un plugin : [doc/fr/developpement/plugins.md](../../doc/fr/developpement/plugins.md).

## Installer

Le cocher dans l'onglet « Plugins » des « Paramètres du service… », puis valider.
Il n'a ni table ni colonne : ses données sont dans la colonne `properties` des événements, sous la clé `alternation` ([#607](https://github.com/dascritch/machincast/issues/607)).
Relancer ensuite la diffusion, le serveur intranet et l'interface, qui le chargent au démarrage.

À la main, dans `machincast.toml` :

```toml
[plugins]
enabled = ["alternation"]
```

`plugins/alternation/install.sh --remove` ne retire rien : désactivé, le plugin laisse les événements méta jouer leur propre liste, et les émissions de l'alternance retrouvent leurs propres dates.

## Ce qu'il contient

| Chemin | Rôle |
| --- | --- |
| `manifest.json` | S'accroche à `Machin_player`, `Machin_interface` et `Machin_webserver`, les binaires qui lisent la grille. |
| `src/machincast_alternation/rotation.py` | L'alternance d'un événement, lue dans `properties`, et l'émission qui joue chaque occurrence : sa réponse au point « grid.substitutions » ([#608](https://github.com/dascritch/machincast/issues/608)). |
| `src/machincast_alternation/section.py` | La section « Émissions en alternance » de la fiche d'un événement, par le point « interface.event_card » ([#611](https://github.com/dascritch/machincast/issues/611)). |
| `src/machincast_alternation/queries.py` | La lecture et l'écriture de `properties`, sous la seule clé du plugin, et la création d'une émission sur le créneau partagé. |
| `src/machincast_alternation/labels.py` | Les noms des rythmes et des rangs de la rotation, et la règle qui fait jouer une émission. |
| `src/machincast_alternation/sharing.py` | Ce que la fiche d'une émission de l'alternance dit du créneau qu'elle partage, à la place de l'encadré de sa grille. |
| `src/machincast_alternation/texts.py` | Ses textes, et leur traduction. |
| `tests/` | Ses scénarios, lancés par `bin/Machin dev-test`, après ceux du cœur. |

## Ses données

```json
{"alternation": {"mode": "monthly", "candidates": [12, 13, 14], "rotation": {"1": 12, "2": 13, "3": 14, "4": 13, "5": null}, "choices": {"2026-12-16": 12}}}
```

- `mode` : `monthly`, par mois, `fortnightly`, par quinzaine, `three_weekly`, une semaine sur trois, ou `four_weekly`, une semaine sur quatre ; `monthly` sans lui.
- `candidates` : les émissions qui se partagent le créneau ; hors grille, elles ne jouent plus que par l'événement méta.
- `rotation` : par mois, pour la 1re à la 5e occurrence du jour de l'événement dans le mois, l'émission qui joue ; par quinzaine, une semaine sur trois ou sur quatre, pour chaque semaine du cycle, comptées depuis la semaine de la première occurrence de l'événement, d'un mois à l'autre (`rotation.cycle`) ; `null`, l'événement méta joue lui-même.
- `choices` : pour une date, l'émission qui joue, à la place de la rotation.

Une émission qui n'est pas parmi les `candidates` est ignorée.
