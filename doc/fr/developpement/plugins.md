# Écrire un plugin

Un plugin ajoute une fonction à MachinCast sans toucher au cœur, ni rejouer toute sa suite de tests ([#348](https://github.com/dascritch/machincast/issues/348)).
Ce guide décrit le socle ([#585](https://github.com/dascritch/machincast/issues/585)) ; les points d'extension de chaque binaire viennent avec leurs tickets ([#588](https://github.com/dascritch/machincast/issues/588) à [#592](https://github.com/dascritch/machincast/issues/592)).

## Le répertoire d'un plugin

Un plugin est un répertoire de `plugins/`, à la racine du dépôt, dont le nom ne contient que des lettres, des chiffres, `_` et `-` :

```text
plugins/horloge/
	README.md
	manifest.json
	check.py                       facultatif
	install.sh                     son installation (#586)
	src/machincast_horloge/__init__.py
	tests/
	bin/
	doc/
```

Son paquet Python est `machincast_<nom>`, les `-` du nom en `_` : `src/machincast_horloge/`.
MachinCast l'importe depuis `src/` quand il charge le plugin ; il n'est pas installé dans le venv.

## Le manifest

```json
{
	"name": "horloge",
	"version": "1.2.0",
	"description": "Speaks the time",
	"machincast": ">=0.9,<2",
	"binaries": ["Machin_player"],
	"requires": {
		"plugins": {"aiguille": ">=1.0"},
		"python": ["requests"],
		"programs": ["espeak-ng"],
		"tables": ["sounds"]
	},
	"l10n": {"fr": {"name": "Horloge parlante", "description": "Dit l'heure"}}
}
```

| Clé | Ce qu'elle dit |
| --- | --- |
| `name` | Le nom du répertoire. |
| `version` | Sa version, au format [PEP 440](https://peps.python.org/pep-0440/) : `1.2.0`. |
| `description` | Sa description courte, en anglais, 200 caractères au plus. |
| `machincast` | Les versions de MachinCast où il fonctionne, un spécificateur PEP 440 ; sans elle, toutes. |
| `binaries` | Les binaires où il s'accroche : `Machin_player`, `Machin_indexer`, `Machin_interface`, `Machin_intranet`. Il n'est chargé que dans ceux-là. |
| `requires` | Tout est facultatif : les plugins demandés et leurs versions, les modules Python importables, les programmes du `PATH`, les tables de la base. |
| `l10n` | Le nom et la description dans chaque langue de MachinCast. |

Une clé inconnue est refusée, avec sa raison, comme dans `machincast.toml`.

## Vérifier qu'il est activable

Avant de charger un plugin, chaque binaire vérifie, dans l'ordre :

1. que son manifest est valide ;
2. que la version de MachinCast fait partie des siennes ;
3. que les plugins qu'il demande sont activés, dans les versions qu'il demande ;
4. que ses modules Python et ses programmes sont là ;
5. que ses tables sont en base ;
6. puis son `check.py`, s'il en a un.

`check.py` définit `check(context)`, qui rend la liste des raisons qui l'empêchent d'être activé, vide s'il est activable :

```python
def check(context):
	if not context.configuration.intranet.enabled:
		return ["the intranet is off"]
	return []
```

Un plugin écarté l'est au journal du binaire, avec ses raisons ; le binaire démarre quand même.

## L'activer

Dans `machincast.toml`, et bientôt depuis l'interface ([#587](https://github.com/dascritch/machincast/issues/587)) :

```toml
[plugins]
enabled = ["horloge"]

[plugins.horloge]
# Ses réglages, que le plugin lit dans context.settings.
format = "%H:%M"
```

L'activation vaut au démarrage de chaque binaire : relancer la diffusion, l'indexation et l'interface.
Un plugin est chargé après ceux qu'il demande ; des plugins qui se demandent en cercle sont écartés.

## L'enregistrer

Au chargement, MachinCast appelle la fonction `register` du paquet du plugin, avec un objet `machincast.plugins.Plugin` :

```python
def register(plugin):
	plugin.on("service_start", lambda data: annoncer(plugin.context, data))
	plugin.declare("horloge.sonnerie", "rings: hour")
```

- `plugin.context` : la version de MachinCast, le binaire, la configuration, les plugins chargés et leurs versions, ses réglages (`settings`), et ce qui se joue (`playing`, le dernier état publié par Machin player, quand le binaire le connaît).
- `plugin.on(point, fonction)` : s'abonne à un point d'extension ; la fonction reçoit les données du point.
- `plugin.declare(point, description)` : déclare un point du plugin, préfixé de son nom, pour les plugins qui le demandent.

Un point est appelé de deux façons (`machincast.plugins.points`) :

- **notifié** : le binaire n'attend pas ; chaque abonné est appelé dans le fil des plugins, dans l'ordre des notifications ;
- **demandé** : le binaire attend la réponse de chaque abonné, par exemple les pages qu'un plugin ajoute.

L'exception d'un abonné est consignée au journal, avec le plugin et le point ; elle n'arrête ni le binaire ni les autres plugins.
Un abonnement à un point que personne ne déclare est refusé : c'est une faute de frappe, ou un plugin demandé qui manque.

## Ses tables et son install.sh

([#586](https://github.com/dascritch/machincast/issues/586), `machincast.plugins.schema`)

Les tables d'un plugin viennent de ses migrations, dans `migrations/`, au format de celles du cœur ([règles de la base](../regles/base-de-donnees.md#migrations)) : `<nom>.NNNN.<sujet>.sql` et son annulation `<nom>.NNNN.<sujet>.rollback.sql`.
Préfixés du nom du plugin, leurs identifiants ne croisent jamais ceux du cœur ni ceux d'un autre plugin.

```sql
-- plugins/horloge/migrations/horloge.0001.sonneries.sql
CREATE TABLE horloge_sonneries (
	id bigserial PRIMARY KEY,
	sound_id bigint REFERENCES sounds (id) ON DELETE CASCADE,
	ring text NOT NULL
);
GRANT SELECT ON horloge_sonneries TO machincast_player;
```

- Une table d'un plugin peut désigner celles du cœur ; jamais l'inverse : le cœur ignore ses plugins.
	Une clé étrangère vers le cœur cascade (`ON DELETE CASCADE`) ou se met à `NULL`, pour que la suppression d'un élément du cœur ne dépende jamais d'un plugin.
- Ses `GRANT` ne donnent qu'aux rôles des binaires où il s'accroche (`machincast_player` pour `Machin_player`…) : l'installation refuse un plugin qui donne à un autre.
- Préfixer ses tables de son nom évite qu'elles croisent celles d'un autre plugin.

Son `install.sh` lance l'installation commune, avec le Python du venv de MachinCast :

```bash
#!/usr/bin/env bash
# Installe ou met à jour le plugin (sans option), le désinstalle (--remove), ou dit ce qui serait fait (--simulation).
set -euo pipefail
plugin="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${MACHINCAST_PYTHON:-${plugin}/../../.venv/bin/python}" -m machincast.plugins.installation "${plugin}" "$@"
```

- Sans option, il applique les migrations qui manquent, sur la base de production, après une sauvegarde (`pg_dump`, comme `Machin maintenance-db`) ; rien s'il n'y a rien à faire.
- `--remove` annule ses migrations, après une sauvegarde : ses tables partent, aucune table du cœur ni d'un autre plugin n'est touchée.
- `--simulation` dit ce qui serait fait, sans rien faire.
- Des migrations mal nommées, sans annulation, ou qui donnent au mauvais rôle, refusent l'installation (code 2), sans sauvegarde ni changement ; une sauvegarde ou une base en échec, code 1.

`Machin maintenance-db` applique aussi les migrations qui manquent aux plugins activés, après celles du cœur.

## Le tester

Les tests d'un plugin sont dans son `tests/`, à part de ceux de MachinCast.
`bin/Machin dev-test` les lance après ceux du cœur, un `mypy --strict` et un `pytest` par plugin ; `bin/Machin dev-test --scenarios plugins` ne lance que ceux-là, avec les scénarios du socle.
