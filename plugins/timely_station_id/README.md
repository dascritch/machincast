# Station ID régulier (timely_station_id)

Un station ID environ tous les quarts d'heure, quelle que soit la durée des morceaux, dans les événements choisis, pour répondre aux obligations légales de la station ([#460](https://github.com/dascritch/machincast/issues/460)), par le point du cœur « player.before_choice » ([#640](https://github.com/dascritch/machincast/issues/640)).

- Guide d'utilisation : [doc/station-id.md](doc/station-id.md).
- Écrire un plugin : [doc/fr/developpement/plugins.md](../../doc/fr/developpement/plugins.md).

## Installer

Le cocher dans l'onglet « Plugins » des « Paramètres du service… », puis valider, et le régler dans sa fenêtre, menu « Plugins », « Station ID régulier » : la banque des station ID, les autres identifiants de la station, l'écart minimal et maximal et le placement, enregistrés dans `machincast.toml`.
Il n'a ni table ni colonne : le choix de chaque événement est dans sa colonne `properties`, sous la clé `timely_station_id`.
Relancer ensuite la diffusion et l'interface, qui le chargent au démarrage ; des réglages changés dans la fenêtre valent aussitôt pour la prochaine simulation, et pour Machin player à son prochain démarrage.

Sa section, telle que la fenêtre l'écrit, ou à la main :

```toml
[plugins]
enabled = ["timely_station_id"]

[plugins.timely_station_id]
# Le nom interne de la banque des station ID à jouer ; obligatoire.
bank = "Station ID"
# Les autres identifiants de la station, des banques (un jingle saisonnier qui dit le nom de la radio) : un de leurs
# passages compte comme un station ID ; facultatif.
watched = ["Jingles saisonniers"]
# L'écart voulu entre deux station ID, en minutes ; 12 et 18 par défaut.
minimum = 12
maximum = 18
# « before » : le station ID passe avant le morceau qui ferait dépasser le maximum, au plus tôt après le minimum ;
# « after » : il passe au premier choix après le maximum, sans avancer aucun morceau. « before » par défaut.
placement = "before"
```

Des réglages refusés sont consignés dans le journal de la diffusion (`Machin logs`), et aucun station ID n'est inséré ; une banque introuvable l'est aussi, une fois.
`plugins/timely_station_id/install.sh --remove` ne retire rien : désactivé, le plugin laisse les événements jouer leur liste telle quelle.

## Ce qu'il contient

| Chemin | Rôle |
| --- | --- |
| `manifest.json` | S'accroche à `Machin_player`, pour l'antenne, les sonores à venir et la simulation, et à `Machin_interface`, pour la fiche d'un événement et sa fenêtre. |
| `src/machincast_timely_station_id/rule.py` | Ses réglages, et la règle qui fait passer un station ID avant un morceau. |
| `src/machincast_timely_station_id/station.py` | Sa réponse au point « player.before_choice ». |
| `src/machincast_timely_station_id/settings.py` | La fenêtre du plugin, menu « Plugins » : ses réglages, écrits dans `machincast.toml`. |
| `src/machincast_timely_station_id/section.py` | La case « Station ID régulier » de la fiche d'un événement, par le point « interface.event_card ». |
| `src/machincast_timely_station_id/queries.py` | La lecture et l'écriture de `properties`, sous la seule clé du plugin, et les banques par leur nom. |
| `src/machincast_timely_station_id/texts.py` | Ses textes, et leur traduction. |
| `tests/` | Ses scénarios, lancés par `bin/Machin dev-test`, après ceux du cœur. |
