# Règles — Base de données

À lire avant de toucher au schéma, aux requêtes ou aux droits. Modèle complet : [spec.md § 3](../spec.md#3-base-de-données).

## Principes

- PostgreSQL, accès par socket Unix locale avec psycopg 3.
- Authentification **peer** : chaque rôle correspond à un utilisateur système.
- Deux bases au schéma strictement identique : production et test.

## Migrations

- Tout changement de schéma passe par une migration **yoyo-migrations** versionnée dans `src/machincast/migrations/` (`NNNN.nom.sql` et son annulation `NNNN.nom.rollback.sql`). Jamais de modification manuelle, jamais de modification d'une migration déjà fusionnée : on en ajoute une nouvelle.
- Seule exception, avant toute mise en production : les migrations ont été fusionnées en `0001.schema-initial`, les quatre premières ([PR #70](https://github.com/dascritch/machincast/pull/70)), puis les trois suivantes, dont la priorité `secours` ([PR #90](https://github.com/dascritch/machincast/pull/90)), puis les deux suivantes, banque « ne pas répéter » et séquences ([PR #100](https://github.com/dascritch/machincast/pull/100)). Une base de développement ou de test créée avant une fusion se recrée (`dropdb`, `createdb`, puis `yoyo apply`) : yoyo reconnaît une migration à son nom, et ne réapplique pas une `0001.schema-initial` qui a changé. Après la première mise en production, plus aucune fusion.
- Les valeurs énumérées sont des types `ENUM` PostgreSQL. Ajouter une valeur se fait par `ALTER TYPE … ADD VALUE` dans une nouvelle migration ; une valeur ne peut pas être retirée sans recréer le type.
- Les métadonnées non critiques d'un sonore vont dans l'objet JSON `metadonnees_musicales`, sans migration ; seules les données utilisées par la diffusion ou les filtres deviennent des colonnes.
- Texte saisi à la main : `varchar(255)` (constante `LONGUEUR_TEXTE_COURT` de `machincast.base`). Chemin, URL ou message libre : `text`.
- Toute nouvelle contrainte s'accompagne d'un scénario qui vérifie qu'elle refuse ce qu'elle doit refuser.
- Une migration qui transforme des données existantes s'accompagne d'un scénario qui applique les migrations antérieures, insère des données, applique la migration et vérifie la conversion.
- Annuler une migration annule aussi toutes celles qui la suivent, qui peuvent en dépendre.
- Une migration doit pouvoir s'appliquer aux deux bases sans modification.

## Droits

Le tableau des droits par binaire est dans [spec.md § 3.2](../spec.md#32-rôles-et-droits). Il est appliqué deux fois :

1. en base, par les `GRANT` de la migration `0001.schema-initial` aux rôles `machincast_lecture`, `machincast_indexation` et `machincast_interface` ;
2. dans le code : chaque binaire n'exécute que les requêtes autorisées à son rôle.

Règles :

- Un binaire ouvre toujours sa connexion avec `machincast.base.connecter(socket, base, Role.…)`, jamais avec `psycopg.connect` directement : sans `SET ROLE`, l'utilisateur n'a aucun droit.
- Toute connexion se ferme explicitement, par un `with`, y compris celle d'un backend yoyo : laissée au ramasse-miettes, elle peut épuiser les connexions du serveur ([#78](https://github.com/dascritch/machincast/issues/78)). Deux scénarios de `schema.feature` le vérifient pour les migrations, ramasse-miettes suspendu.
- Tout changement de droits passe par une nouvelle migration et par la matrice de [`tests/features/roles.feature`](../../tests/features/roles.feature), qui vérifie chaque opération de chaque rôle sur chaque table.
- Une nouvelle table n'est accessible à aucun rôle tant qu'une migration ne lui accorde pas de droits.

Points sensibles :

- `Machin_lecture` n'écrit dans `sonores` que le champ `etat`, pour le passer à `expire`. Dans `airplay` et `log`, il ne fait que des insertions.
- `Machin_indexation` n'écrit que dans `sonores` et `banques_sonores`, et jamais dans `log`. Il ne supprime que des lignes de `banques_sonores`, pour retirer d'une banque les sonores hors de ses durées ([#195](https://github.com/dascritch/machincast/issues/195)).
- En mode simulation, `Machin_lecture` n'écrit **rien** en base : toute la simulation tient dans une transaction en lecture seule (`machincast.lecture.simulation.lecture_seule`), où PostgreSQL refuse toute écriture ([#21](https://github.com/dascritch/machincast/issues/21)).

## Intégrité

- Les lignes `airplay` ne sont jamais supprimées. Elles recopient emplacement, artiste et titre au moment du passage.
- Les contraintes « exactement un des deux » (stream : URL ou marque-page ; élément d'événement : banque ou sonore) sont posées en base par des `CHECK`.
- Une contrainte qui porte sur une autre table passe par un déclencheur qui lève une `check_violation`, comme le secours d'un stream, toujours un événement de priorité `secours` ([#16](https://github.com/dascritch/machincast/issues/16)). La requête du déclencheur est imbriquée sous la condition qui la rend nécessaire, pour qu'un rôle qui n'a pas le droit de lire l'autre table puisse continuer à écrire.
- Une valeur ajoutée par `ALTER TYPE … ADD VALUE` ne peut pas servir dans la transaction qui l'ajoute, donc pas dans la même migration yoyo : les contraintes qui l'utilisent vont dans la migration suivante.
- Les champs listés dans `sonores.champs_edites` ne sont jamais modifiés par l'indexeur.
