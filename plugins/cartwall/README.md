# Cartouchier (cartwall)

Des boutons tactiles dans Machin intranet, qui agissent sur l'antenne, réglés par compte de l'API dans Machin interface ([#512](https://github.com/dascritch/machincast/issues/512), plugin de [#348](https://github.com/dascritch/machincast/issues/348)).

- Guide d'utilisation : [doc/cartouchier.md](doc/cartouchier.md).
- Écrire un plugin : [doc/fr/developpement/plugins.md](../../doc/fr/developpement/plugins.md).

## Installer

```bash
plugins/cartwall/install.sh --simulation   # ce qui serait fait
plugins/cartwall/install.sh                # sa table cartwall_buttons, après une sauvegarde de la base
```

Puis l'activer dans `machincast.toml`, ou dans l'onglet « Plugins » des « Paramètres du service… », et relancer le serveur intranet et l'interface :

```toml
[plugins]
enabled = ["cartwall"]
```

`plugins/cartwall/install.sh --remove` retire sa table, et les boutons de tous les comptes, après une sauvegarde ; aucune table de MachinCast n'est touchée.

## Ce qu'il contient

| Chemin | Rôle |
| --- | --- |
| `manifest.json` | S'accroche à `Machin_intranet` et `Machin_interface` ; demande la table `cartwall_buttons`. |
| `migrations/` | La table `cartwall_buttons` : les boutons de chaque compte, lus par l'intranet, réglés par l'interface. |
| `src/machincast_cartwall/intranet.py` | La page `/plugins/cartwall` et les routes `GET /api/v1/plugins/cartwall/buttons`, `POST /api/v1/plugins/cartwall/press`. |
| `src/machincast_cartwall/settings.py` | Les boutons de chaque compte, dans la fenêtre du plugin, menu « Plugins » de l'interface. |
| `src/machincast_cartwall/buttons.py` | Les actions, et la demande que chacune envoie à Machin player. |
| `static/` | La feuille de style et le script de la page. |
| `tests/` | Ses scénarios, lancés par `bin/Machin dev-test`, après ceux du cœur. |

## L'API

- `GET /api/v1/plugins/cartwall/buttons`, pour tout compte : `{"buttons": [{"id", "label", "colour", "action", "target", "blank", "usable", "reason"}]}`, les boutons du compte, et pourquoi chacun ne peut pas servir maintenant.
- `POST /api/v1/plugins/cartwall/press`, `{"button": <identifiant>}`, pour un compte « actions API » : 200 `{"done": true}` si Machin player l'a fait ; 409 `{"done": false, "reason": …}` s'il l'a refusé ; 404 pour le bouton d'un autre compte ; 400 sans bouton lisible ; 403 pour un compte « consulter ».
