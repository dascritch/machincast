# Couleurs des émissions (color_the_shows)

Chaque événement prend la couleur de son genre, talk, jazz, metal, reggae…, ou celle de sa priorité, dans le calendrier de Machin interface, celui de Machin webserver et les tableaux d'airplay ([#628](https://github.com/dascritch/machincast/issues/628)), par le point du cœur « grid.event_colour » ([#635](https://github.com/dascritch/machincast/issues/635)).

- Guide d'utilisation : [doc/couleurs.md](doc/couleurs.md).
- Écrire un plugin : [doc/fr/developpement/plugins.md](../../doc/fr/developpement/plugins.md).

## Installer

Le cocher dans l'onglet « Plugins » des « Paramètres du service… », puis valider : son `install.sh` crée ses tables, après une sauvegarde de la base.
Relancer ensuite le serveur intranet et l'interface, qui le chargent au démarrage.

À la main, dans `machincast.toml` :

```toml
[plugins]
enabled = ["color_the_shows"]
```

puis `plugins/color_the_shows/install.sh`.
`plugins/color_the_shows/install.sh --remove` retire ses tables, après une sauvegarde ; le genre des événements reste dans leur colonne `properties`, ignoré.

## Ce qu'il contient

| Chemin | Rôle |
| --- | --- |
| `manifest.json` | S'accroche à `Machin_interface` et `Machin_webserver`. |
| `migrations/color_the_shows.0001.colours.sql` | Les tables `color_the_shows__genres` et `color_the_shows__priorities`, et leurs valeurs par défaut. |
| `src/machincast_color_the_shows/palette.py` | Sa réponse au point « grid.event_colour », de mémoire, relue au plus toutes les 30 secondes. |
| `src/machincast_color_the_shows/section.py` | La section « Genre » de la fiche d'un événement, par le point « interface.event_card ». |
| `src/machincast_color_the_shows/settings.py` | La fenêtre du plugin, menu « Plugins » : les genres et les couleurs des priorités. |
| `src/machincast_color_the_shows/queries.py` | Ses requêtes, et l'écriture de `properties`, sous la seule clé du plugin. |
| `src/machincast_color_the_shows/texts.py` | Ses textes, et leur traduction. |
| `tests/` | Ses scénarios, lancés par `bin/Machin dev-test`, après ceux du cœur. |

## Ses données

```json
{"color_the_shows": {"genre": 2}}
```

Les couleurs par défaut : fil antenne `#b4b4b4`, émissions `#8fd19e`, spéciales `#f08c8c` ; talk `#f2c14e`, jazz `#5b8def`, metal `#3d3d3d`, reggae `#e07b39`.
