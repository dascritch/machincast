# Règles — Base de données

À lire avant de toucher au schéma, aux requêtes ou aux droits. Modèle complet : [spec.md § 3](../spec.md#3-base-de-données).

## Principes

- PostgreSQL, accès par socket Unix locale avec psycopg 3.
- Authentification **peer** : chaque rôle correspond à un utilisateur système.
- Deux bases au schéma strictement identique : production et test.

## Migrations

- Tout changement de schéma passe par une migration **yoyo-migrations** versionnée dans `src/machincast/migrations/` (`NNNN.nom.sql` et son annulation `NNNN.nom.rollback.sql`). Jamais de modification manuelle, jamais de modification d'une migration déjà fusionnée : on en ajoute une nouvelle.
- Seule exception, avant toute mise en production : les migrations ont été fusionnées en une seule, les quatre premières ([PR #70](https://github.com/dascritch/machincast/pull/70)), puis les trois suivantes, dont la priorité `fallback` ([PR #90](https://github.com/dascritch/machincast/pull/90)), puis les deux suivantes, banque « ne pas répéter » et séquences ([PR #100](https://github.com/dascritch/machincast/pull/100)), puis les quatorze suivantes, de `0002` à `0015`, avant que le projet serve réellement ([#314](https://github.com/dascritch/machincast/issues/314)). Cette migration unique a ensuite été réécrite avec des noms anglais, sous le nom `0001.initial-schema` ([#358](https://github.com/dascritch/machincast/issues/358)). Une base de l'ancien schéma, aux noms français, n'est plus reconnue ([#384](https://github.com/dascritch/machincast/issues/384)) : aucune ne sera mise à jour avant la 1.0.0, elle se recrée. Après la première mise en production, plus aucune fusion ni réécriture : depuis la release 0.9.0, chaque changement est une nouvelle migration, comme `0002.run-log` ([#341](https://github.com/dascritch/machincast/issues/341)).
- Les valeurs énumérées sont des types `ENUM` PostgreSQL. Ajouter une valeur se fait par `ALTER TYPE … ADD VALUE` dans une nouvelle migration ; une valeur ne peut pas être retirée sans recréer le type.
- Les métadonnées non critiques d'un sonore vont dans l'objet JSON `music_metadata`, sans migration ; seules les données utilisées par la diffusion ou les filtres deviennent des colonnes.
- Texte saisi à la main : `varchar(255)` (constante `SHORT_TEXT_LENGTH` de `machincast.database`). Chemin, URL ou message libre : `text`.
- Toute nouvelle contrainte s'accompagne d'un scénario qui vérifie qu'elle refuse ce qu'elle doit refuser.
- Une migration qui transforme des données existantes s'accompagne d'un scénario qui applique les migrations antérieures, insère des données, applique la migration et vérifie la conversion.
- Annuler une migration annule aussi toutes celles qui la suivent, qui peuvent en dépendre.
- Une migration doit pouvoir s'appliquer aux deux bases sans modification.

## Droits

Le tableau des droits par binaire est dans [spec.md § 3.2](../spec.md#32-rôles-et-droits). Il est appliqué deux fois :

1. en base, par les `GRANT` des migrations, `0001.initial-schema` puis `0002.run-log` ([#341](https://github.com/dascritch/machincast/issues/341)), aux rôles `machincast_player`, `machincast_indexer` et `machincast_interface` ;
2. dans le code : chaque binaire n'exécute que les requêtes autorisées à son rôle.

Règles :

- Un binaire ouvre toujours sa connexion avec `machincast.database.open_connection(socket, base, Role.…)`, jamais avec `psycopg.connect` directement : sans `SET ROLE`, l'utilisateur n'a aucun droit. Seules exceptions, les opérations de propriétaire de la base : les migrations (`machincast.installation`) et `Machin_maintenance-db` ([#127](https://github.com/dascritch/machincast/issues/127)), dont `VACUUM` et la vérification des rôles demandent le compte lui-même, et qui ne lisent ni n'écrivent aucune donnée des tables, sauf leurs démarrages et leurs fins au log ([#341](https://github.com/dascritch/machincast/issues/341)) ; et `Machin_purge` ([#268](https://github.com/dascritch/machincast/issues/268)), seul programme qui efface des lignes de `airplay` et de `log`, ce qu'aucun rôle ne peut faire.
- Toute opération qui modifie la base hors des binaires de l'antenne (schéma, optimisation) est précédée d'une sauvegarde, et s'arrête si elle échoue ; une sauvegarde n'est jamais effacée par MachinCast.
- Toute connexion se ferme explicitement, par un `with`, y compris celle d'un backend yoyo : laissée au ramasse-miettes, elle peut épuiser les connexions du serveur ([#78](https://github.com/dascritch/machincast/issues/78)). Deux scénarios de `schema.feature` le vérifient pour les migrations, ramasse-miettes suspendu.
- Tout changement de droits passe par une nouvelle migration et par la matrice de [`tests/features/roles.feature`](../../../tests/features/roles.feature), qui vérifie chaque opération de chaque rôle sur chaque table.
- Une nouvelle table n'est accessible à aucun rôle tant qu'une migration ne lui accorde pas de droits.

Points sensibles :

- `Machin_player` n'écrit dans `sounds` que le champ `state`, pour le passer à `expired`. Dans `airplay` et `log`, il ne fait que des insertions.
- `Machin_indexer` n'écrit que dans `sounds` et `bank_sounds`, et dans `log` ses seuls démarrages, fins et plantages probables, sans le lire : `machincast_previous_start`, `SECURITY DEFINER`, lui rend le démarrage précédent ([#341](https://github.com/dascritch/machincast/issues/341)). Une fonction `SECURITY DEFINER` fixe son `search_path`, ne rend que ce dont le rôle a besoin, et n'est exécutable que par les rôles qui s'en servent (`REVOKE ALL … FROM PUBLIC`). Il ne supprime que des lignes de `bank_sounds`, pour retirer d'une banque les sonores hors de ses durées ([#195](https://github.com/dascritch/machincast/issues/195)).
- En mode simulation, `Machin_player` n'écrit **rien** en base : toute la simulation tient dans une transaction en lecture seule (`machincast.player.simulation.read_only`), où PostgreSQL refuse toute écriture ([#21](https://github.com/dascritch/machincast/issues/21)).

## Intégrité

- Les lignes `airplay` ne sont supprimées que par `Machin_purge`, passé la durée de péremption ([#268](https://github.com/dascritch/machincast/issues/268)), et toujours par passage entier (début et fin). Elles recopient emplacement, artiste et titre au moment du passage : un passage récent d'un sonore effacé se lit encore.
- Les contraintes « exactement un des deux » (stream : URL ou feed ; élément d'événement : banque ou sonore) sont posées en base par des `CHECK`.
- Une contrainte qui porte sur une autre table passe par un déclencheur qui lève une `check_violation`, comme le secours d'un stream, toujours un événement de priorité `fallback` ([#16](https://github.com/dascritch/machincast/issues/16)). La requête du déclencheur est imbriquée sous la condition qui la rend nécessaire, pour qu'un rôle qui n'a pas le droit de lire l'autre table puisse continuer à écrire.
- Une valeur ajoutée par `ALTER TYPE … ADD VALUE` ne peut pas servir dans la transaction qui l'ajoute, donc pas dans la même migration yoyo : les contraintes qui l'utilisent vont dans la migration suivante.
- Les champs listés dans `sounds.edited_fields` ne sont jamais modifiés par l'indexeur.
- **Éléments supprimés** ([#267](https://github.com/dascritch/machincast/issues/267)) : un sonore, une banque, une séquence ou un événement supprimé depuis l'interface reste en base, `deleted_at` renseigné, jusqu'à sa péremption. Toute requête qui **propose** des éléments (listes, recherche, choix, suggestions), qui les **joue** (grille), qui les **indexe**, ou qui cherche un élément par son nom ou son fichier, les écarte : `deleted_at IS NULL`. Une requête par identifiant, elle, les lit : la fiche, l'airplay et les incidents les nomment. Le nom interne et l'emplacement ne sont uniques que parmi les éléments qui ne sont pas supprimés (index uniques partiels).
