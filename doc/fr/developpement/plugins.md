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
	install.sh                     son installation, voir plus bas
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
| `binaries` | Les binaires où il s'accroche : `Machin_player`, `Machin_indexer`, `Machin_interface`, `Machin_webserver`. Il n'est chargé que dans ceux-là. |
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
	plugin.on("player.sound_start", lambda data: annoncer(plugin.context, data))
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

## Être prévenu de ce que joue Machin player

([#589](https://github.com/dascritch/machincast/issues/589), `machincast.player.plugin_points`)

Machin player notifie ses points, sans attendre les plugins : un plugin lent, ou qui échoue, ne retarde ni n'arrête l'antenne.

```python
def register(plugin):
	plugin.on("player.sound_start", lambda data: publier(data["artist"], data["title"]))
```

| Point | Quand | Données |
| --- | --- | --- |
| `player.service_start` | la diffusion démarre | `instant` |
| `player.service_stop` | la diffusion s'arrête | `instant`, `error` (`None` pour un arrêt demandé) |
| `player.event_start` | un événement prend l'antenne | `instant`, `event`, `name`, `public_name`, `priority`, `start` et `end` de l'occurrence, `playing` (l'événement qu'il fait jouer quand il prête son nom) |
| `player.event_stop` | il la quitte | celles de son début, à l'`instant` de sa fin |
| `player.sequence_start` | une séquence commence | `instant`, `sequence`, `name`, `public_name`, `event`, `event_name` |
| `player.sequence_stop` | elle finit | celles de son début, à l'`instant` de sa fin |
| `player.sound_start` | un sonore commence | `instant`, `play`, `sound`, `artist`, `title`, `location`, `stream`, `duration`, `start_position`, `event`, `lender`, `sequence`, `bank` |
| `player.sound_stop` | il finit | celles de son début, `instant`, `start`, `played`, `end_position`, `cut`, `error` |

Les heures sont en ISO 8601, avec leur décalage ; les durées et les positions dans le fichier en secondes, `None` pour un stream.
En simulation, aucun de ces points n'est appelé.

## Régler le gain d'un sonore

([#643](https://github.com/dascritch/machincast/issues/643), `machincast.player.plugin_points.sound_gain`)

Le point du cœur « player.sound_gain » est demandé par Machin player avant de jouer un fichier, jamais un stream ; la simulation ne le demande pas.
Ses données : `connection`, la connexion de la diffusion, `sound`, `bank` (ou `None`), `event`, et `properties`, celles du sonore, dont `loudness`, la sonie intégrée et la crête mesurées par l'audit complet ([#642](https://github.com/dascritch/machincast/issues/642)).
Le plugin répond un gain en dB : il s'applique à la voie du sonore, après la mesure des blancs et avant son enveloppe de volume (ses fondus) ; le premier nombre répondu l'emporte, borné à +20 dB.
Sans plugin, sans réponse, ou une réponse qui n'est pas un nombre : le sonore joue tel quel.

```python
CIBLE = -23.0


def gain(data):
	mesure = data["properties"].get("loudness") or {}
	sonie = mesure.get("integrated")
	if sonie is None:
		return None
	return CIBLE - sonie


def register(plugin):
	plugin.on("player.sound_gain", gain)
```

## Insérer un effet dans la voie d'un sonore

([#644](https://github.com/dascritch/machincast/issues/644), `machincast.player.plugin_points.sound_effects`)

Le point du cœur « player.sound_effects » est demandé par Machin player avant de jouer un sonore, fichier ou stream ; la simulation ne le demande pas.
Ses données sont celles de « player.sound_gain », plus `stream`, vrai pour un stream.
Le plugin répond une description d'éléments GStreamer, comme pour `gst-launch-1.0`, par exemple un compresseur ou un limiteur : elle est insérée dans la voie du sonore, après son gain et avant son enveloppe de volume (ses fondus).
Les réponses de plusieurs plugins s'enchaînent, dans leur ordre de chargement ; une description invalide est consignée dans le journal, et le sonore joue sans elle.

Un greffon LV2 installé sur le poste devient un élément de GStreamer, grâce à `gstreamer1.0-plugins-bad` : `gst-inspect-1.0 lv2` les liste, sous des noms comme `lv2-http---calf-sourceforge-net-plugins-Compressor`.
GStreamer n'a pas d'hôte VST.

```python
def register(plugin):
	plugin.on(
		"player.sound_effects",
		lambda data: "audiodynamic mode=compressor characteristics=soft-knee threshold=0.5 ratio=0.25",
	)
```

## Faire passer un sonore avant le prochain

([#640](https://github.com/dascritch/machincast/issues/640), `machincast.player.rundown`)

Le point du cœur « player.before_choice » est demandé avant chaque sonore choisi dans la liste de l'événement actif, dans Machin player, dans la prévision des sonores à venir comme à l'antenne, et dans la simulation de Machin interface.
Ni la suite d'une séquence, ni un sonore inséré à la main, ni le stream d'un feed qui coupe l'antenne ne le demandent.
Ses données :

- `instant`, le début prévu du candidat, et `forecast`, vrai pendant la prévision des sonores à venir ;
- `connection`, la connexion de la diffusion, dans sa transaction : une lecture d'un plugin se fait dans un `with connection.transaction():`, pour qu'une erreur n'interrompe pas la diffusion ;
- `event`, l'identifiant de l'événement actif, et `priority`, sa priorité ;
- `sound`, le candidat, `bank`, la banque qui l'a fourni (ou `None`), `sequence`, sa séquence (ou `None`), et `duration`, sa durée (`timedelta`, ou `None`) ;
- `last_play(banks)`, le début du dernier passage fourni par l'une de ces banques, passages prévus compris, ou `None`.

Le plugin répond l'identifiant d'une banque : l'un de ses sonores jouables passe avant le candidat, comme un sonore inséré, sans faire avancer la liste ; le candidat est choisi de nouveau au tour suivant.
`None`, ou une banque sans sonore jouable, laisse passer le candidat ; la première banque qui fournit un sonore l'emporte.

```python
STATION = 12
"""L'identifiant de la banque des station ID."""


def avant(data):
	dernier_passage = data["last_play"]
	dernier = dernier_passage((STATION,))
	if (dernier is None) or (data["instant"] - dernier > timedelta(minutes=15)):
		return STATION
	return None


def register(plugin):
	plugin.on("player.before_choice", avant)
```

## Être prévenu de ce que trouve Machin indexer

([#590](https://github.com/dascritch/machincast/issues/590), `machincast.indexer.plugin_points`)

| Point | Quand | Données |
| --- | --- | --- |
| `indexer.sound_spotted` | le parcours enregistre un nouveau fichier, en aperçu | `sound`, `location`, `bank`, `bank_name` |
| `indexer.sound_detailed` | la vérification a écrit ce qu'elle a trouvé d'un sonore | `sound`, `location`, `previous_state`, `state`, `duration`, `artist`, `title`, `metadata`, `file_type`, `detected_start`, `detected_end`, `audited`, `problem`, `loudness` (`integrated` et `peak`, ou `None` sans mesure, [#642](https://github.com/dascritch/machincast/issues/642)) |

Ils sont notifiés : l'erreur d'un plugin est consignée, et n'arrête ni le parcours ni la vérification.
Pour compléter le sonore, le plugin ouvre sa propre connexion : celle de l'indexation ne quitte pas son fil.

## Être prévenu d'un incident grave

([#592](https://github.com/dascritch/machincast/issues/592), `machincast.plugins.incidents`)

Le point `log_incident` est notifié dans chaque binaire, pour une entrée du log de niveau « incident » et pour toute erreur de son journal (ERROR ou CRITICAL) :

```python
def register(plugin):
	plugin.on("log_incident", lambda data: envoyer_un_courriel(data["executable"], data["kind"], data["message"]))
```

Ses données : `executable`, `instant`, `level` (`incident`, `error` ou `critical`), `kind`, `message`, `references` (`sound`, `bank` et `event`, ou `None`) et `origin`.
Ce que le journal consigne pendant l'appel d'un abonné de `log_incident`, son échec compris, n'est pas un incident : un plugin qui ne parvient pas à prévenir ne se prévient pas lui-même en boucle.

## Faire jouer une occurrence par un autre événement

([#608](https://github.com/dascritch/machincast/issues/608))

Le point du cœur « grid.substitutions » est demandé à chaque lecture de la grille, dans chaque binaire.
Le plugin y répond une `machincast.shared.grid.Substitution` :

```python
from machincast.shared.grid import Substitution


def register(plugin):
	plugin.on("grid.substitutions", lambda data: Substitution(cachés, jouant))
```

- `hidden(event)` : les identifiants des événements que cet événement fait jouer ; hors grille, ils ne jouent plus que par lui ;
- `playing(event, day)` : l'identifiant de l'événement qui joue son occurrence qui commence ce jour, ou `None` pour qu'il la joue lui-même.

L'un et l'autre lisent l'événement, ses `properties` comprises : c'est là qu'un plugin range ses choix.
Appelés à chaque lecture de la grille, ils ne lisent pas la base.

## Colorer un événement

([#635](https://github.com/dascritch/machincast/issues/635), `machincast.shared.colours`)

Le point du cœur « grid.event_colour » est demandé quand un binaire colore un événement : le calendrier de Machin interface (ses blocs, et les cases de ses priorités), celui de Machin webserver (sa grille et son JSON) et les tableaux d'airplay, de l'onglet Antenne et de l'onglet Airplay.
Ses données : `event`, l'identifiant de l'événement, ou `None` pour la couleur d'une priorité, et `priority`, sa priorité, ou `None` quand l'appelant ne la connaît pas, dans un tableau d'airplay.
Le plugin répond une couleur `#rrggbb`, ou `None` pour laisser celle du cœur ; la première couleur valide l'emporte, une autre réponse est ignorée.

```python
def register(plugin):
	plugin.on("grid.event_colour", lambda data: {"show": "#8fd19e"}.get(data["priority"]))
```

- Dans le calendrier de l'interface, le nom d'un bloc s'écrit en noir ou en blanc, le plus contrasté sur ce qu'il y a sous lui (`readable_text`, contraste de WCAG 2) ; une case de priorité colorée par un plugin perd le nom de sa couleur dans son infobulle.
- Dans l'intranet, la couleur passe par les attributs du SVG (`fill`, `stroke`) et la classe `colore`, sans style écrit dans la page ; `texte-clair` met le texte en blanc sur un fond trop sombre ; le JSON du calendrier la donne en `colour`.
- Dans un tableau d'airplay, la couleur d'un événement est un trait épais à gauche de sa cellule (`EventStripe`) ; seul l'événement y est connu, sans sa priorité.

Le point est demandé à chaque dessin : le plugin répond de mémoire, sans lire la base à chaque fois.

## Sa section dans une fiche

([#611](https://github.com/dascritch/machincast/issues/611), [#591](https://github.com/dascritch/machincast/issues/591))

Le point du cœur « interface.<genre>_card » est demandé à l'ouverture d'une fiche, dans Machin interface, avec `card`, la fiche, `connection`, sa connexion, et `parent` : « interface.event_card », « interface.bank_card », « interface.sequence_card », « interface.sound_card » et « interface.feed_card ».
Le plugin y répond une `machincast.interface.card.CardSection`, un `QWidget`, montrée au-dessus des boutons de la fiche, ou à côté de la liste de lecture dans celle d'un événement :

- `read(identifier)` lit l'élément, ou celui que la fiche copie, dans une transaction ; `None` pour un nouvel élément ;
- `write(identifier)` s'écrit dans la transaction de l'enregistrement de l'élément, et lève `machincast.interface.card.Refusal(message, *champs)` pour le refuser : la fiche le signale, et rien n'est écrit ;
- son signal `changed` rend la fiche modifiée ;
- dans la fiche d'un événement seulement, `replaces_items(True)` cache la liste de lecture, qu'elle remplace, `replaces_items(False)` la rend, `grid_widget()` rend ce qu'elle place sous les jours de la récurrence, au-dessus de l'explication des dates, par exemple la case qui la montre ; `None` par défaut ; `grid_replacement()` rend ce qui peut prendre la place de l'encadré de la grille, que `replaces_grid(True)` cache, et `replaces_grid(False)` rend ; `days_changed(jours)` reçoit les jours de la récurrence cochés, de 0 (lundi) à 6, à chaque changement ([#609](https://github.com/dascritch/machincast/issues/609)).
- dans toutes les fiches, son signal `opens(genre, identifiant, nom)` ouvre la fiche d'un élément.

Une section qui n'a rien à montrer à côté de la liste de lecture d'un événement se cache (`hide()`), pour ne pas la décaler par rapport au formulaire et aux autres fiches : celle des émissions en alternance ne se montre que cochée, quand elle remplace la liste ; celles de « Genre » et de « Station ID régulier » placent leur champ dans le formulaire de la fiche, sous « Secours d'un stream tombé », et restent cachées.

## Suivre et vérifier les fiches

([#591](https://github.com/dascritch/machincast/issues/591))

Pour chaque genre d'élément, `event`, `bank`, `sequence`, `sound` et `feed`, trois points du cœur :

| Point | Comment | Données |
| --- | --- | --- |
| `interface.load_<genre>` | notifié, quand la fiche a lu l'élément | `category`, `identifier` (`None` pour un nouvel élément), `copy` |
| `interface.presave_<genre>` | demandé, quand la fiche est écrite, avant que l'enregistrement ne soit validé | `category`, `identifier`, `row` (sa ligne, en JSON, telle qu'écrite), `card`, `connection` |
| `interface.save_<genre>` | notifié, une fois l'élément enregistré | `category`, `identifier`, `row` |

À `interface.presave_<genre>`, une chaîne non vide refuse l'enregistrement : la fiche la signale, et rien n'est écrit.

```python
def register(plugin):
	plugin.on("interface.presave_bank", lambda data: refuser_sans_majuscule(data["row"]["internal_name"]))
```

Les points notifiés sont appelés dans le fil des plugins : ils ne touchent pas à l'écran, et ouvrent leur propre connexion pour lire la base.

## Ses menus

([#591](https://github.com/dascritch/machincast/issues/591))

- « interface.menu » est demandé à l'ouverture de la fenêtre, avec `window`, `connection` et `parent` : le plugin répond un `QMenu`, une `QAction`, ou une liste d'entre eux, placés dans la barre de menus avant « Aide ».
- « interface.context_menu » est demandé au clic droit sur une ligne d'une liste, hors d'un choix d'éléments, avec `menu`, `category`, `identifiers` (la sélection, ou la ligne cliquée), `clicked` et `parent` : le plugin ajoute ses entrées au menu.
- Le menu « Plugins » ouvre sa fenêtre et ses réglages (ci-dessous).

## Les points d'entrée d'un nouveau plugin

À la création de chaque plugin, la liste des points d'entrée qu'il propose est revue avec le responsable du projet ([#348](https://github.com/dascritch/machincast/issues/348)) : menu général, menu contextuel, section d'une fiche, vérification avant l'enregistrement, points de Machin player, de Machin indexer ou de Machin webserver, `log_incident`, et les points qu'il déclare pour d'autres plugins (`plugin.declare`).
Un besoin qu'aucun point ne couvre est un ticket du cœur, qui ajoute son point à `points.CORE`, décrit.

## Ses réglages dans l'interface

Le menu « Plugins » de Machin interface ouvre la fenêtre de chaque plugin activé, avec son nom, sa version et sa description ([#587](https://github.com/dascritch/machincast/issues/587)).
Un plugin qui s'accroche à `Machin_interface` y ajoute ses réglages en répondant au point demandé `interface.plugin_window` un `QWidget`, dont le parent est la fenêtre (`data["parent"]`) :

```python
from PySide6.QtWidgets import QCheckBox


def register(plugin):
	plugin.on("interface.plugin_window", lambda data: QCheckBox("Sonner les heures", data["parent"]))
```

Seul le plugin de la fenêtre est demandé (`Points.collect_from`) ; ses réglages s'enregistrent où il le décide, dans sa section `[plugins.<nom>]` ou ses tables.

## Ses gabarits dans l'intranet

Les pages de Machin webserver viennent de gabarits Jinja2, dans `src/machincast/webserver/templates/` ([#597](https://github.com/dascritch/machincast/issues/597)).
Un plugin qui s'accroche à `Machin_webserver` en surcharge un en fournissant, dans son `templates/`, un fichier du même nom ; le premier plugin, dans l'ordre de `[plugins] enabled`, l'emporte.
Pour ajouter à l'original plutôt que le remplacer, le gabarit l'étend sous le nom `machincast/<nom>` :

```jinja
{# plugins/horloge/templates/documentation.html.jinja #}
{% extends "machincast/documentation.html.jinja" %}
{% block main %}{{ super() }}<p>{{ _("Next event") }}</p>{% endblock %}
```

L'échappement est automatique ; une variable absente est une erreur. Une page du plugin rend ses propres gabarits par `tools.render("horloge.html.jinja", nom=…)`.

## Ses pages dans l'intranet

Un plugin qui s'accroche à `Machin_webserver` y ajoute ses pages, ses routes d'API et ses fichiers statiques ([#588](https://github.com/dascritch/machincast/issues/588)), en répondant au point demandé `intranet.extensions` une `machincast.webserver.extensions.Extension` :

```python
from pathlib import Path

from machincast.webserver.extensions import Endpoint, Extension, HomeSection, Page

STATIC = Path(__file__).parent / "static"


async def cadran(tools, request):
	return f'<p id="horloge">{tools.session.user}</p>'


async def cadran_accueil(tools, request):
	return '<section id="horloge"><h2>Horloge</h2></section>'


async def sonner(tools, request):
	answer = await tools.ask({"command": "insert", "sequence": 12})
	return 200, {"done": answer.done, "reason": answer.reason}


def register(plugin):
	plugin.on(
		"intranet.extensions",
		lambda data: Extension(
			pages=(Page("", "Horloge", cadran, navigation="Horloge", assets=("horloge.css", "horloge.js")),),
			endpoints=(Endpoint("POST", "sonner", sonner, role="actions", summary="Fait sonner l'horloge"),),
			static=STATIC,
			home=(HomeSection(cadran_accueil, assets=("horloge.css",)),),
		),
	)
```

- Une page est servie en GET sous `/plugins/<nom>/<chemin>`, dans le gabarit de l'intranet ; avec un libellé (`navigation`), elle entre au bandeau.
- Une section de l'accueil (`HomeSection`) s'ajoute sous l'antenne en direct, sans page ni entrée au bandeau, pour un compte du rôle demandé ; vide, elle n'ajoute rien.
- Une route d'API est servie sous `/api/v1/plugins/<nom>/<chemin>`, en GET ou en POST, et rend un statut et une valeur JSON.
	Le schéma OpenAPI de l'API, `/api/v1/openapi.json`, la décrit avec son plugin, son rôle et son résumé, `summary` ([#602](https://github.com/dascritch/machincast/issues/602)).
- Le rôle demandé (`role`) est `consult`, par défaut, ou `actions` ; sans session, une page mène à la connexion et une route répond 401 ; un rôle insuffisant reçoit 403.
- Les fichiers statiques sont ceux d'un seul répertoire (`static`), servis sous `/plugins/<nom>/static/`, aux types `.css`, `.js`, `.svg`, `.png`, `.woff2` et `.json`.
	L'intranet refuse les styles et les scripts écrits dans la page : ils vont dans ces fichiers, que la page charge par `assets`.
- `tools` donne la session (`tools.session.user`, `tools.session.role`), la base au rôle `machincast_webserver` (`await tools.database(fonction)`), le dernier état de l'antenne (`await tools.state()`) et les demandes à Machin player, au nom du compte, avec leur réponse (`await tools.ask(demande)`).

Détails : [spécification, § 14.3](../spec.md#143-les-pages-et-les-routes-dun-plugin-dans-lintranet).

## Ses propriétés, dans la colonne properties

([#607](https://github.com/dascritch/machincast/issues/607))

Les éléments, `events`, `banks`, `sounds`, `sequences` et `feeds`, comme `api_users` et `api_sessions`, ont une colonne `properties`, un objet JSON.
Un plugin y range ce qui lui est propre sous la clé de son nom, `{"horloge": {…}}`, sans toucher aux autres clés : `properties = properties || jsonb_build_object('horloge', %s::jsonb)`.
C'est le premier choix, avant une table du plugin, dont la création se demande d'abord au mainteneur.

## Ses tables et son install.sh

([#586](https://github.com/dascritch/machincast/issues/586), `machincast.plugins.schema`)

Les tables d'un plugin viennent de ses migrations, dans `migrations/`, au format de celles du cœur ([règles de la base](../regles/base-de-donnees.md#migrations)) : `<nom>.NNNN.<sujet>.sql` et son annulation `<nom>.NNNN.<sujet>.rollback.sql`.
Préfixés du nom du plugin, leurs identifiants ne croisent jamais ceux du cœur ni ceux d'un autre plugin.

```sql
-- plugins/horloge/migrations/horloge.0001.sonneries.sql
CREATE TABLE horloge__sonneries (
	id bigserial PRIMARY KEY,
	sound_id bigint REFERENCES sounds (id) ON DELETE CASCADE,
	ring text NOT NULL
);
GRANT SELECT ON horloge__sonneries TO machincast_player;
```

- Une table d'un plugin peut désigner celles du cœur ; jamais l'inverse : le cœur ignore ses plugins.
	Une clé étrangère vers le cœur cascade (`ON DELETE CASCADE`) ou se met à `NULL`, pour que la suppression d'un élément du cœur ne dépende jamais d'un plugin.
- Ses `GRANT` ne donnent qu'aux rôles des binaires où il s'accroche (`machincast_player` pour `Machin_player`…) : l'installation refuse un plugin qui donne à un autre.
- Chaque table, vue, séquence ou type qu'il crée commence par son nom suivi de `__` : `horloge__sonneries`, `cartwall__buttons` ; un tiret du nom devient `_` (`mini-horloge` : `mini_horloge__`). L'installation refuse une migration qui crée une table sans ce préfixe : elle ne croise jamais celles du cœur ni d'un autre plugin.

Ses tables ne sont créées que par son `install.sh` : un plugin qui a des migrations sans `install.sh` est refusé ([#587](https://github.com/dascritch/machincast/issues/587)).
- À la validation des « Paramètres du service… » qui l'activent, Machin interface lance son `install.sh`, avec `--backups` et `--config`, sans terminal.
- `./install.sh`, celui de MachinCast, relance celui de chaque plugin activé, avec `--config` (et `--simulation` en simulation), pour ses mises à jour.
Inutile de déclarer ses propres tables dans `requires.tables` : tant que ses migrations ne sont pas appliquées, chaque binaire l'écarte, et dit comment l'installer.

Son `install.sh` lance l'installation commune, avec le Python du venv de MachinCast, `MACHINCAST_PYTHON` quand l'interface le lance ; il peut faire d'autres préparatifs avant :

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

`Machin maintenance-db` ne touche pas aux tables des plugins : seul leur `install.sh` les crée, les met à jour ou les retire.

## Le tester

Les tests d'un plugin sont dans son `tests/`, à part de ceux de MachinCast.
`bin/Machin dev-test` les lance après ceux du cœur, un `mypy --strict` et un `pytest` par plugin ; `bin/Machin dev-test --scenarios plugins` ne lance que ceux-là, avec les scénarios du socle.
