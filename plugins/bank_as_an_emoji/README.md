# Banque en emoji (bank_as_an_emoji)

Un emoji au début du nom interne d'une banque, « 🌟 Publicités », choisi dans sa fiche, pour la reconnaître d'un coup d'œil dans les tableaux d'airplay et des sonores à venir ([#505](https://github.com/dascritch/machincast/issues/505)).

- Guide d'utilisation : [doc/banque-emoji.md](doc/banque-emoji.md).
- Écrire un plugin : [doc/fr/developpement/plugins.md](../../doc/fr/developpement/plugins.md).

## Installer

Le cocher dans l'onglet « Plugins » des « Paramètres du service… », puis valider.
Il n'a ni table ni colonne : l'emoji est dans les premiers caractères du nom interne de la banque, suivi d'une espace.
Relancer ensuite l'interface, qui le charge au démarrage.

À la main, dans `machincast.toml` :

```toml
[plugins]
enabled = ["bank_as_an_emoji"]
```

`plugins/bank_as_an_emoji/install.sh --remove` ne retire rien : désactivé, le plugin laisse les noms internes tels qu'ils sont, emoji compris.

## Ce qu'il contient

| Chemin | Rôle |
| --- | --- |
| `manifest.json` | S'accroche à `Machin_interface`. |
| `src/machincast_bank_as_an_emoji/section.py` | Par le point « interface.bank_card » ([#591](https://github.com/dascritch/machincast/issues/591)), le sélecteur d'emoji et le nom sans emoji, à la place du champ du nom interne de la fiche, caché, qui garde le nom complet. |
| `src/machincast_bank_as_an_emoji/names.py` | L'emoji au début d'un nom interne, et les emojis proposés. |
| `src/machincast_bank_as_an_emoji/texts.py` | Ses textes, et leur traduction. |
| `tests/` | Ses scénarios, lancés par `bin/Machin dev-test`, après ceux du cœur. |
