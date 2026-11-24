# Normalisation du niveau (loudness_normalization)

Chaque sonore porté à une sonie visée, EBU R128, sans que sa crête dépasse un plafond, avec un ajustement manuel par sonore ([#43](https://github.com/dascritch/machincast/issues/43)).
Le plugin s'appuie sur la mesure de l'audit complet du cœur ([#642](https://github.com/dascritch/machincast/issues/642)) et sur le point « player.sound_gain » ([#643](https://github.com/dascritch/machincast/issues/643)) : sans lui, Machin player joue les sonores tels quels, et leur fiche n'en montre rien.

- Guide d'utilisation : [doc/normalisation.md](doc/normalisation.md).
- Écrire un plugin : [doc/fr/developpement/plugins.md](../../doc/fr/developpement/plugins.md).

## Installer

Le cocher dans l'onglet « Plugins » des « Paramètres du service… », puis valider, et le régler dans sa fenêtre, menu « Plugins », « Normalisation du niveau ».
Il n'a ni table ni colonne : l'ajustement manuel de chaque sonore est dans sa colonne `properties`, sous la clé `loudness_normalization`.
Relancer ensuite la diffusion, l'indexation et l'interface, qui le chargent au démarrage.

Sa section, telle que la fenêtre l'écrit, ou à la main :

```toml
[plugins]
enabled = ["loudness_normalization"]

[plugins.loudness_normalization]
# La sonie visée, en LUFS, de -40 à -5 ; -23 par défaut (EBU R128).
target = -23.0
# Le plafond de crête, en dBFS, de -12 à 0 ; -1 par défaut : la crête d'un sonore, gain compris, ne le dépasse jamais.
ceiling = -1.0
```

Des réglages refusés sont consignés dans le journal du programme, et aucun gain n'est appliqué.
`plugins/loudness_normalization/install.sh --remove` ne retire rien : désactivé, le plugin laisse Machin player jouer les sonores tels quels.

## Ce qu'il contient

| Chemin | Rôle |
| --- | --- |
| `manifest.json` | S'accroche à `Machin_player`, `Machin_indexer` et `Machin_interface`. |
| `src/machincast_loudness_normalization/rule.py` | Ses réglages, et la règle du gain : automatique plus manuel, borné par le plafond de crête. |
| `src/machincast_loudness_normalization/gain.py` | Sa réponse au point « player.sound_gain », et, au point « indexer.sound_detailed », l'ajustement manuel ramené sous le plafond après une mise à jour du fichier, avec un incident au log. |
| `src/machincast_loudness_normalization/section.py` | L'encart « Niveau » de la fiche d'un sonore, sous l'encart « Fichier », par le point « interface.sound_card ». |
| `src/machincast_loudness_normalization/bank_section.py` | La cible et le plafond propres à une banque, dans sa fiche, par le point « interface.bank_card ». |
| `src/machincast_loudness_normalization/slider.py` | Le curseur d'une sonie ou d'une crête, au demi-décibel. |
| `src/machincast_loudness_normalization/settings.py` | La fenêtre du plugin : la cible et le plafond, écrits dans `machincast.toml`. |
| `src/machincast_loudness_normalization/queries.py` | La lecture et l'écriture de `properties`, sous la seule clé du plugin, et l'incident du log. |
| `src/machincast_loudness_normalization/texts.py` | Ses textes, et leur traduction. |
| `tests/` | Ses scénarios, lancés par `bin/Machin dev-test`, après ceux du cœur. |

## Ses données

```json
{"loudness": {"integrated": -17.4, "peak": -0.3}, "loudness_normalization": {"gain": -2.5}}
```

`loudness` est la mesure du cœur ; `loudness_normalization.gain`, l'ajustement manuel, en dB.
Une banque a, dans les siennes, `{"loudness_normalization": {"target": -16.0, "ceiling": -2.0}}`, l'un ou l'autre, ou aucun.
